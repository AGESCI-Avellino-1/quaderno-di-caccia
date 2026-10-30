<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import {
  api,
  euro,
  giustificativoMovimento,
  giustificativoSpesa,
  nomeUnita,
  PERCORSO_MOVIMENTI,
  type Cassa,
  type Evento,
  type CassaIn,
  type ModelloD,
  type Movimento,
  type SpesaAnticipata,
  type Unita,
  type Verifica,
  type VoceModelloD,
} from '@/api/qdc'
import CopiaLocale from '@/components/CopiaLocale.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'
import { leggiGiustificativo } from '@/offline/giustificativo'
import { scrivi } from '@/offline/outbox'
import { useSessioneStore } from '@/stores/sessione'

// Cash book (DEC-85…DEC-88): the Co.Ca. sees every box, an R/S treasurer their unit's.
// Boxes, categories and movements are cached for offline use; a movement recorded
// offline waits in the queue with its photo. Never edited: reversed with a reason.
const sessione = useSessioneStore()
const { errore, inCorso, esegui } = useErrore()
const gestisce = computed(() => !!sessione.profilo?.gestisce_quote)

const annoCorrente = (() => {
  const oggi = new Date()
  return oggi.getMonth() >= 9 ? oggi.getFullYear() + 1 : oggi.getFullYear()
})()
const anno = ref(annoCorrente)
const etichetta = (fine: number) => `${fine - 1}/${String(fine).slice(-2)}`
const oggi = () => new Date().toLocaleDateString('sv')
const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')

const casse = ref<Cassa[]>([])
const voci = ref<VoceModelloD[]>([])
const unita = ref<Unita[]>([])
// Events a movement may belong to (a fundraising, a camp): those of the year shown.
const eventi = ref<Evento[]>([])
const scelta = ref<number | null>(null)
const movimenti = ref<Movimento[]>([])
const copiaDel = ref<string | null>(null)
const verifiche = ref<Verifica[]>([])
const spese = ref<SpesaAnticipata[]>([])
const rendiconto = ref<ModelloD | null>(null)
const esito = ref('')
const vista = ref<'movimenti' | 'spese' | 'rendiconto' | 'casse'>('movimenti')

const cassa = computed(() => casse.value.find((c) => c.id === scelta.value) ?? null)
const nomeDellUnita = (id: number | null) =>
  id === null ? 'Gruppo' : (unita.value.find((u) => u.id === id)?.nome ?? '')
const etichettaUnita = (id: number | null) => {
  const trovata = unita.value.find((u) => u.id === id)
  return trovata ? nomeUnita(trovata) : 'Gruppo'
}

async function caricaCasse() {
  const letto = await esegui(() => leggiConCache('casse', () => api.casse()))
  if (!letto) return
  casse.value = letto.dati
  copiaDel.value = letto.copiaDel
  if (scelta.value === null || !casse.value.some((c) => c.id === scelta.value)) {
    scelta.value = casse.value[0]?.id ?? null
  }
}

async function caricaMovimenti() {
  if (scelta.value === null) return
  const chiave = `movimenti:${scelta.value}:${anno.value}`
  const letto = await esegui(() =>
    leggiConCache(chiave, () => api.movimenti({ cassa: scelta.value!, anno: anno.value })),
  )
  movimenti.value = letto?.dati ?? []
  try {
    verifiche.value = await api.verifiche(scelta.value)
  } catch {
    verifiche.value = []
  }
}

async function caricaSpese() {
  spese.value = (await esegui(() => api.speseAnticipate())) ?? []
}

async function caricaRendiconto() {
  try {
    rendiconto.value = await api.modelloD(anno.value)
  } catch {
    rendiconto.value = null // the Co.Ca. only
  }
}

onMounted(async () => {
  await caricaCasse()
  voci.value =
    (await esegui(() => leggiConCache('voci-modello-d', () => api.vociModelloD())))?.dati ?? []
  try {
    unita.value = (await leggiConCache('unita', () => api.unita())).dati
  } catch {
    unita.value = []
  }
  await Promise.all([caricaSpese(), caricaRendiconto()])
})
watch([scelta, anno], caricaMovimenti, { immediate: true })
watch(
  anno,
  async (fine) => {
    try {
      const dati = await leggiConCache(`eventi:anno:${fine}`, () =>
        api.eventi({ dal: `${fine - 1}-10-01`, al: `${fine}-09-30` }),
      )
      eventi.value = dati.dati.filter((e) => !e.riunione && !e.annullato)
    } catch {
      eventi.value = []
    }
  },
  { immediate: true },
)
watch(anno, caricaRendiconto)
watch(vista, (nuova) => {
  esito.value = ''
  if (nuova === 'rendiconto') void caricaRendiconto()
})

// --- New movement --------------------------------------------------------------------

const nuovo = reactive({
  aperto: false,
  tipo: 'USCITA' as 'ENTRATA' | 'USCITA' | 'GIROCONTO',
  data: oggi(),
  importo: '',
  descrizione: '',
  voce_id: '',
  unita_id: null as number | null,
  cassa_destinazione_id: null as number | null,
  evento_id: null as number | null,
  giustificativo: '',
  nomeFile: '',
})
const vociDelTipo = computed(() =>
  voci.value.filter((v) => v.lato === (nuovo.tipo === 'ENTRATA' ? 'E' : 'U')),
)

function apriNuovo() {
  verifica.aperta = false
  Object.assign(nuovo, {
    aperto: true,
    data: oggi(),
    importo: '',
    descrizione: '',
    voce_id: '',
    unita_id: cassa.value?.unita_id ?? null,
    cassa_destinazione_id: null,
    evento_id: null,
    giustificativo: '',
    nomeFile: '',
  })
  esito.value = ''
}

async function scegliFile(
  evento: Event,
  destinazione: { giustificativo: string; nomeFile: string },
) {
  const file = (evento.target as HTMLInputElement).files?.[0]
  if (!file) return
  try {
    destinazione.giustificativo = await leggiGiustificativo(file)
    destinazione.nomeFile = file.name
  } catch (e) {
    errore.value = e instanceof Error ? e.message : 'File non leggibile.'
  }
}

async function registra() {
  if (!cassa.value) return
  const corpo = {
    cassa_id: cassa.value.id,
    tipo: nuovo.tipo,
    data: nuovo.data,
    importo: Number(nuovo.importo).toFixed(2),
    descrizione: nuovo.descrizione,
    voce_id: nuovo.tipo === 'GIROCONTO' ? '' : nuovo.voce_id,
    unita_id: nuovo.unita_id,
    cassa_destinazione_id: nuovo.tipo === 'GIROCONTO' ? nuovo.cassa_destinazione_id : null,
    evento_id: nuovo.tipo === 'GIROCONTO' ? null : nuovo.evento_id,
    giustificativo: nuovo.giustificativo,
  }
  const risultato = await esegui(() =>
    scrivi({
      metodo: 'POST',
      percorso: PERCORSO_MOVIMENTI,
      corpo,
      // Stored in clear in the queue: no names, no descriptions.
      descrizione: `${nuovo.tipo === 'ENTRATA' ? 'Entrata' : nuovo.tipo === 'USCITA' ? 'Uscita' : 'Giroconto'} di ${euro(corpo.importo)} (cassa n. ${corpo.cassa_id})`,
    }),
  )
  if (!risultato) return
  nuovo.aperto = false
  esito.value = risultato.inCoda
    ? 'Movimento salvato sul telefono: sarà registrato appena torna la rete.'
    : 'Movimento registrato.'
  if (!risultato.inCoda) await Promise.all([caricaCasse(), caricaMovimenti()])
}

// --- Reversal and late photo --------------------------------------------------------------

const storno = reactive({ id: 0, motivo: '' })
async function storna() {
  if (!(await esegui(() => api.storna(storno.id, storno.motivo)))) return
  storno.id = 0
  esito.value = 'Movimento stornato.'
  await Promise.all([caricaCasse(), caricaMovimenti()])
}

async function fotoDopo(evento: Event, movimento: Movimento) {
  const file = (evento.target as HTMLInputElement).files?.[0]
  if (!file) return
  const contenuto = await esegui(() => leggiGiustificativo(file))
  if (!contenuto) return
  if (await esegui(() => api.aggiungiGiustificativo(movimento.id, contenuto))) {
    await Promise.all([caricaCasse(), caricaMovimenti()])
  }
}

// --- Cash check (DEC-11) --------------------------------------------------------------------

const verifica = reactive({ aperta: false, data: oggi(), saldo_contato: '', motivo: '' })
const puoVerificare = computed(
  () => !!cassa.value?.puo_registrare && (cassa.value.unita_id !== null || gestisce.value),
)
async function registraVerifica() {
  if (!cassa.value) return
  const fatta = await esegui(() =>
    api.verificaCassa(cassa.value!.id, {
      data: verifica.data,
      saldo_contato: Number(verifica.saldo_contato).toFixed(2),
      motivo: verifica.motivo,
    }),
  )
  if (!fatta) return
  verifica.aperta = false
  esito.value = Number(fatta.differenza)
    ? `Verifica registrata, con una rettifica di ${euro(fatta.differenza)}.`
    : 'Verifica registrata: il saldo torna.'
  await Promise.all([caricaCasse(), caricaMovimenti()])
}

// --- Expenses paid by capi (DEC-86) --------------------------------------------------------

const rimborso = reactive({ id: 0, cassa_id: null as number | null, motivo: '', azione: '' })
async function rimborsa() {
  const fatto = await esegui(() =>
    rimborso.azione === 'rimborsa'
      ? api.rimborsaSpesa(rimborso.id, rimborso.cassa_id!)
      : api.respingiSpesa(rimborso.id, rimborso.motivo),
  )
  if (!fatto) return
  rimborso.id = 0
  await Promise.all([caricaSpese(), caricaCasse(), caricaMovimenti()])
}

// --- Cash boxes (the group) -------------------------------------------------------------

// Fee payments recorded before the boxes were set up (DEC-152).
const fuori = ref<{ pagamenti: number; importo: string } | null>(null)
const cassaRiporto = ref<number | null>(null)
watch(vista, async (nuova) => {
  if (nuova !== 'casse' || !gestisce.value) return
  fuori.value = (await esegui(() => api.fuoriPrimaNota())) ?? null
})
async function riporta() {
  const esitoRiporto = await esegui(() => api.riportaInPrimaNota(cassaRiporto.value))
  if (!esitoRiporto) return
  esito.value = `${esitoRiporto.riportati} pagamenti riportati in prima nota.`
  fuori.value = (await esegui(() => api.fuoriPrimaNota())) ?? null
  await caricaCasse()
}

const modificaCassa = ref<(CassaIn & { id: number | null }) | null>(null)
function apriCassa(c: Cassa | null) {
  modificaCassa.value = c
    ? { ...c }
    : {
        id: null,
        nome: '',
        tipo: 'CONTANTI',
        unita_id: null,
        saldo_iniziale: '0',
        data_saldo_iniziale: oggi(),
        attiva: true,
      }
}
async function salvaCassa() {
  const dati = modificaCassa.value
  if (!dati) return
  const corpo: CassaIn = { ...dati, unita_id: dati.tipo === 'BANCA' ? null : dati.unita_id }
  const fatto = await esegui(() =>
    dati.id ? api.modificaCassa(dati.id, corpo) : api.creaCassa(corpo),
  )
  if (!fatto) return
  modificaCassa.value = null
  await caricaCasse()
}
</script>

<template>
  <section>
    <div class="d-flex flex-wrap align-items-center gap-3 mb-3">
      <h1 class="h4 mb-0">Prima nota</h1>
      <RouterLink
        v-if="gestisce"
        :to="{ name: 'banca' }"
        class="btn btn-sm btn-outline theme-primary"
      >
        Estratto conto della banca
      </RouterLink>
      <div class="d-flex align-items-center gap-1">
        <button
          type="button"
          class="btn btn-sm btn-link"
          aria-label="Anno precedente"
          @click="anno--"
        >
          ‹
        </button>
        <span>Anno {{ etichetta(anno) }}</span>
        <button
          type="button"
          class="btn btn-sm btn-link"
          aria-label="Anno successivo"
          @click="anno++"
        >
          ›
        </button>
      </div>
      <CopiaLocale :del="copiaDel" />
    </div>
    <nav class="d-flex flex-wrap gap-3 mb-5" aria-label="Sezioni della prima nota">
      <button
        v-for="[chiave, titolo] in [
          ['movimenti', 'Movimenti'],
          ['spese', 'Spese da rimborsare'],
          ...(rendiconto ? [['rendiconto', 'Rendiconto']] : []),
          ...(gestisce ? [['casse', 'Casse']] : []),
        ]"
        :key="chiave"
        type="button"
        class="btn btn-sm"
        :class="vista === chiave ? 'btn-solid theme-primary' : 'btn-outline theme-primary'"
        @click="vista = chiave as typeof vista"
      >
        {{ titolo }}
      </button>
    </nav>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>

    <!-- Movements of one box -->
    <template v-if="vista === 'movimenti'">
      <p v-if="!casse.length && !inCorso" class="fg-2">
        Nessuna cassa configurata.<template v-if="gestisce">
          Aggiungile nella sezione Casse.</template
        >
      </p>
      <div class="row g-3 mb-5">
        <div v-for="c in casse" :key="c.id" class="col-12 md:col-4">
          <button
            type="button"
            class="card card-body h-100 w-100 text-start"
            :class="{ 'border-primary': c.id === scelta }"
            :aria-pressed="c.id === scelta"
            @click="scelta = c.id"
          >
            <strong>{{ c.nome }}</strong>
            <span class="small fg-2">{{
              c.tipo === 'BANCA' ? 'Conto bancario' : etichettaUnita(c.unita_id)
            }}</span>
            <span v-if="c.saldo !== null">Saldo {{ euro(c.saldo) }}</span>
            <span v-if="c.senza_giustificativo" class="badge theme-warning align-self-start">
              {{
                c.senza_giustificativo === 1
                  ? '1 uscita senza giustificativo'
                  : `${c.senza_giustificativo} uscite senza giustificativo`
              }}
            </span>
            <span v-if="!c.attiva" class="badge theme-secondary align-self-start">Non attiva</span>
          </button>
        </div>
      </div>

      <template v-if="cassa">
        <div class="d-flex flex-wrap gap-3 mb-3">
          <button
            v-if="cassa.puo_registrare && !nuovo.aperto"
            type="button"
            class="btn btn-sm btn-solid theme-primary"
            @click="apriNuovo"
          >
            Registra un movimento
          </button>
          <button
            v-if="puoVerificare && !verifica.aperta"
            type="button"
            class="btn btn-sm btn-outline theme-primary"
            @click="
              Object.assign(verifica, { aperta: true, data: oggi(), saldo_contato: '', motivo: '' })
            "
          >
            Verifica di cassa
          </button>
        </div>

        <form v-if="nuovo.aperto" class="border rounded p-5 mb-5" @submit.prevent="registra">
          <div class="row g-3">
            <div class="md:col-4">
              <label class="form-label small" for="mov-tipo">Tipo</label>
              <select id="mov-tipo" v-model="nuovo.tipo" class="form-control form-control-sm">
                <option value="USCITA">Uscita</option>
                <option value="ENTRATA">Entrata</option>
                <option value="GIROCONTO">Giroconto verso un'altra cassa</option>
              </select>
            </div>
            <div class="md:col-4">
              <label class="form-label small" for="mov-data">Data</label>
              <input
                id="mov-data"
                v-model="nuovo.data"
                type="date"
                :max="oggi()"
                class="form-control form-control-sm"
                required
              />
            </div>
            <div class="md:col-4">
              <label class="form-label small" for="mov-importo">Importo (€)</label>
              <input
                id="mov-importo"
                v-model="nuovo.importo"
                type="number"
                min="0.01"
                step="0.01"
                class="form-control form-control-sm"
                required
              />
            </div>
            <div class="col-12">
              <label class="form-label small" for="mov-descrizione">Descrizione</label>
              <input
                id="mov-descrizione"
                v-model="nuovo.descrizione"
                class="form-control form-control-sm"
                required
              />
            </div>
            <div v-if="nuovo.tipo !== 'GIROCONTO'" class="col-12">
              <label class="form-label small" for="mov-voce">Voce del Modello D</label>
              <select
                id="mov-voce"
                v-model="nuovo.voce_id"
                class="form-control form-control-sm"
                required
              >
                <option value="" disabled>Scegli…</option>
                <option v-for="v in vociDelTipo" :key="v.id" :value="v.id">
                  {{ v.riga }} · {{ v.nome }}
                </option>
              </select>
            </div>
            <div v-else class="md:col-6">
              <label class="form-label small" for="mov-destinazione">Verso la cassa</label>
              <select
                id="mov-destinazione"
                v-model="nuovo.cassa_destinazione_id"
                class="form-control form-control-sm"
                required
              >
                <option
                  v-for="c in casse.filter((x) => x.id !== cassa!.id && x.attiva)"
                  :key="c.id"
                  :value="c.id"
                >
                  {{ c.nome }}
                </option>
              </select>
            </div>
            <div v-if="nuovo.tipo !== 'GIROCONTO' && eventi.length" class="md:col-6">
              <label class="form-label small" for="mov-evento">Per l'evento (facoltativo)</label>
              <select
                id="mov-evento"
                v-model="nuovo.evento_id"
                class="form-control form-control-sm"
              >
                <option :value="null">Nessuno</option>
                <option v-for="e in eventi" :key="e.id" :value="e.id">
                  {{ e.titolo }} ({{ new Date(e.inizio).toLocaleDateString('it-IT') }})
                </option>
              </select>
            </div>
            <div v-if="cassa.tipo === 'BANCA'" class="md:col-6">
              <label class="form-label small" for="mov-unita">Per l'unità</label>
              <select id="mov-unita" v-model="nuovo.unita_id" class="form-control form-control-sm">
                <option :value="null">Gruppo</option>
                <option v-for="u in unita" :key="u.id" :value="u.id">{{ nomeUnita(u) }}</option>
              </select>
            </div>
            <div class="col-12">
              <label class="form-label small" for="mov-foto">
                Foto dello scontrino o della fattura (facoltativa)
              </label>
              <input
                id="mov-foto"
                type="file"
                accept="image/*,application/pdf"
                capture="environment"
                class="form-control form-control-sm"
                @change="scegliFile($event, nuovo)"
              />
              <div v-if="nuovo.tipo === 'USCITA' && !nuovo.giustificativo" class="form-text">
                Senza giustificativo l'uscita resta segnalata finché non lo aggiungi.
              </div>
            </div>
          </div>
          <div class="d-flex gap-3 mt-3">
            <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
              Registra
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="nuovo.aperto = false">
              Annulla
            </button>
          </div>
        </form>

        <form
          v-if="verifica.aperta"
          class="border rounded p-5 mb-5"
          @submit.prevent="registraVerifica"
        >
          <p class="form-text">
            Conta i soldi (o guarda l'estratto conto) e scrivi quanto c'è: se non torna con il saldo
            dell'app, la differenza diventa una rettifica con il motivo che indichi.
          </p>
          <div class="row g-3">
            <div class="md:col-4">
              <label class="form-label small" for="ver-data">Data</label>
              <input
                id="ver-data"
                v-model="verifica.data"
                type="date"
                :max="oggi()"
                class="form-control form-control-sm"
                required
              />
            </div>
            <div class="md:col-4">
              <label class="form-label small" for="ver-contato">Saldo contato (€)</label>
              <input
                id="ver-contato"
                v-model="verifica.saldo_contato"
                type="number"
                step="0.01"
                class="form-control form-control-sm"
                required
              />
            </div>
            <div class="md:col-4">
              <label class="form-label small" for="ver-motivo">Motivo di una differenza</label>
              <input
                id="ver-motivo"
                v-model="verifica.motivo"
                class="form-control form-control-sm"
              />
            </div>
          </div>
          <div class="d-flex gap-3 mt-3">
            <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
              Registra la verifica
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="verifica.aperta = false">
              Annulla
            </button>
          </div>
        </form>

        <p v-if="!movimenti.length && !inCorso" class="fg-2">
          Nessun movimento nell'anno {{ etichetta(anno) }}.
        </p>
        <ul class="list-group mb-5">
          <li v-for="m in movimenti" :key="m.id" class="list-group-item">
            <div class="d-flex flex-wrap justify-content-between gap-3">
              <span :class="{ 'text-decoration-line-through': m.stornato }">
                {{ data(m.data) }} · {{ m.descrizione }}
              </span>
              <strong
                :class="
                  Number(m.cassa_id === cassa.id ? m.effetto : m.importo) < 0 ? 'fg-danger' : ''
                "
              >
                {{ euro(m.cassa_id === cassa.id ? m.effetto : m.importo) }}
              </strong>
            </div>
            <div class="small fg-2">
              {{ m.tipo_nome }}
              <template v-if="m.voce_riga"> · {{ m.voce_riga }} {{ m.voce_nome }}</template>
              <template v-if="m.cassa_destinazione">
                ·
                {{
                  m.cassa_id === cassa.id ? `verso ${m.cassa_destinazione}` : `da ${m.cassa}`
                }}</template
              >
              <template v-if="cassa.tipo === 'BANCA'"> · {{ nomeDellUnita(m.unita_id) }}</template>
              <template v-if="m.evento"> · {{ m.evento }}</template>
              <template v-if="m.registrato_da"> · {{ m.registrato_da }}</template>
            </div>
            <div v-if="m.storno_di" class="small">Storno: {{ m.motivo_storno }}</div>
            <div class="d-flex flex-wrap align-items-center gap-3 small">
              <a v-if="m.ha_giustificativo" :href="giustificativoMovimento(m.id)" target="_blank">
                Giustificativo
              </a>
              <template v-else-if="m.senza_giustificativo">
                <span class="badge theme-warning">Senza giustificativo</span>
                <label v-if="cassa.puo_registrare" class="btn btn-sm btn-link mb-0">
                  Aggiungi foto
                  <input
                    type="file"
                    accept="image/*,application/pdf"
                    capture="environment"
                    class="d-none"
                    @change="fotoDopo($event, m)"
                  />
                </label>
              </template>
              <button
                v-if="
                  cassa.puo_registrare &&
                  !m.stornato &&
                  m.tipo !== 'RETTIFICA' &&
                  !m.storno_di &&
                  !m.da_quote &&
                  m.cassa_id === cassa.id
                "
                type="button"
                class="btn btn-sm btn-link"
                @click="Object.assign(storno, { id: m.id, motivo: '' })"
              >
                Storna
              </button>
            </div>
            <form
              v-if="storno.id === m.id"
              class="d-flex flex-wrap align-items-end gap-3 mt-3"
              @submit.prevent="storna"
            >
              <div class="flex-grow-1">
                <label class="form-label small" :for="`storno-${m.id}`">Perché lo storni?</label>
                <input
                  :id="`storno-${m.id}`"
                  v-model="storno.motivo"
                  class="form-control form-control-sm"
                  required
                />
              </div>
              <button type="submit" class="btn btn-sm btn-solid theme-danger" :disabled="inCorso">
                Storna
              </button>
              <button type="button" class="btn btn-sm btn-link" @click="storno.id = 0">
                Lascia stare
              </button>
            </form>
          </li>
        </ul>

        <template v-if="verifiche.length">
          <h2 class="h6">Verifiche di cassa</h2>
          <ul class="list-group">
            <li v-for="v in verifiche" :key="v.id" class="list-group-item small">
              {{ data(v.data) }}: contati {{ euro(v.saldo_contato) }}, nell'app
              {{ euro(v.saldo_app) }}
              <template v-if="Number(v.differenza)">
                · differenza {{ euro(v.differenza) }} ({{ v.motivo }})</template
              >
              <template v-if="v.registrata_da"> · {{ v.registrata_da }}</template>
            </li>
          </ul>
        </template>
      </template>
    </template>

    <!-- Expenses paid by capi -->
    <template v-if="vista === 'spese'">
      <p class="form-text">
        Le spese pagate di tasca propria dai capi: diventano un'uscita, alla voce Rimborsi spese
        volontari, quando le rimborsi. Ogni capo le registra dalla pagina Le mie spese.
      </p>
      <p v-if="!spese.length && !inCorso" class="fg-2">Nessuna spesa.</p>
      <ul class="list-group">
        <li v-for="s in spese" :key="s.id" class="list-group-item">
          <div class="d-flex flex-wrap justify-content-between gap-3">
            <span>{{ data(s.data) }} · {{ s.capo }} · {{ s.descrizione }}</span>
            <strong>{{ euro(s.importo) }}</strong>
          </div>
          <div class="small fg-2">
            {{ etichettaUnita(s.unita_id) }}
            <template v-if="s.stato === 'rimborsata'">
              · rimborsata il {{ data(s.rimborsata_il!) }}</template
            >
            <template v-else-if="s.stato === 'respinta'">
              · respinta: {{ s.motivo_rifiuto }}</template
            >
            <template v-else> · da rimborsare</template>
            ·
            <a v-if="s.ha_giustificativo" :href="giustificativoSpesa(s.id)" target="_blank"
              >giustificativo</a
            >
            <template v-else>senza giustificativo</template>
          </div>
          <div v-if="s.puo_rimborsare && rimborso.id !== s.id" class="d-flex gap-3 mt-1">
            <button
              type="button"
              class="btn btn-sm btn-link"
              @click="Object.assign(rimborso, { id: s.id, azione: 'rimborsa', cassa_id: null })"
            >
              Rimborsa
            </button>
            <button
              type="button"
              class="btn btn-sm btn-link"
              @click="Object.assign(rimborso, { id: s.id, azione: 'respingi', motivo: '' })"
            >
              Respingi
            </button>
          </div>
          <form
            v-if="rimborso.id === s.id"
            class="d-flex flex-wrap align-items-end gap-3 mt-3"
            @submit.prevent="rimborsa"
          >
            <div v-if="rimborso.azione === 'rimborsa'">
              <label class="form-label small" :for="`rimborso-${s.id}`">Da quale cassa</label>
              <select
                :id="`rimborso-${s.id}`"
                v-model="rimborso.cassa_id"
                class="form-control form-control-sm"
                required
              >
                <option
                  v-for="c in casse.filter((x) => x.puo_registrare && x.attiva)"
                  :key="c.id"
                  :value="c.id"
                >
                  {{ c.nome }}
                </option>
              </select>
            </div>
            <div v-else class="flex-grow-1">
              <label class="form-label small" :for="`respingi-${s.id}`">Perché la respingi?</label>
              <input
                :id="`respingi-${s.id}`"
                v-model="rimborso.motivo"
                class="form-control form-control-sm"
                required
              />
            </div>
            <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
              {{ rimborso.azione === 'rimborsa' ? 'Rimborsa' : 'Respingi' }}
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="rimborso.id = 0">
              Annulla
            </button>
          </form>
        </li>
      </ul>
    </template>

    <!-- Totals for the national report -->
    <template v-if="vista === 'rendiconto' && rendiconto">
      <p class="form-text">
        Totali dell'anno {{ rendiconto.anno_etichetta }} nell'ordine del Modello D (catalogo
        {{ rendiconto.anno_bilancio }}), da ricopiare sull'app nazionale. I giroconti non sono né
        entrate né uscite.
      </p>
      <div class="row g-5">
        <div
          v-for="[lato, titolo] in [
            ['E', 'Entrate'],
            ['U', 'Uscite'],
          ]"
          :key="lato"
          class="col-12 md:col-6"
        >
          <h2 class="h6">{{ titolo }}</h2>
          <table class="table table-sm">
            <tbody>
              <tr v-for="r in rendiconto.righe.filter((x) => x.lato === lato)" :key="r.riga">
                <td class="text-nowrap">{{ r.riga }}</td>
                <td class="small">{{ r.titolo }}</td>
                <td class="text-end text-nowrap" :class="{ 'fg-2': !Number(r.totale) }">
                  {{ euro(r.totale) }}
                </td>
              </tr>
              <tr>
                <th colspan="2">Totale</th>
                <th class="text-end text-nowrap">
                  {{ euro(lato === 'E' ? rendiconto.entrate : rendiconto.uscite) }}
                </th>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <p v-if="Number(rendiconto.rettifiche)" class="small">
        Rettifiche dopo le verifiche di cassa: {{ euro(rendiconto.rettifiche) }}: non sono entrate
        né uscite, quindi non sono nei totali del Modello D.
      </p>
      <h2 class="h6">Saldi di oggi</h2>
      <ul class="list-group">
        <li
          v-for="c in rendiconto.saldi"
          :key="c.id"
          class="list-group-item d-flex justify-content-between"
        >
          {{ c.nome }} <strong>{{ c.saldo === null ? '—' : euro(c.saldo) }}</strong>
        </li>
      </ul>
    </template>

    <!-- Cash boxes (the group) -->
    <template v-if="vista === 'casse' && gestisce">
      <p class="form-text">
        Un conto bancario per il gruppo (le unità si indicano su ogni movimento, anche quelli con la
        carta) e una cassa contanti per unità. Il saldo iniziale non si cambia dopo i primi
        movimenti.
      </p>
      <div v-if="fuori?.pagamenti" class="alert theme-warning small">
        <div>
          {{ fuori.pagamenti }} pagamenti di quote ({{ euro(fuori.importo) }}) sono stati registrati
          prima di configurare le casse e non sono in prima nota.
          <form class="d-flex flex-wrap align-items-end gap-3 mt-3" @submit.prevent="riporta">
            <div>
              <label class="form-label small" for="riporto-cassa">In quale cassa</label>
              <select
                id="riporto-cassa"
                v-model="cassaRiporto"
                class="form-control form-control-sm"
              >
                <option :value="null">
                  Automatica: contanti nella cassa dell'unità, il resto nel conto
                </option>
                <option v-for="c in casse" :key="c.id" :value="c.id">{{ c.nome }}</option>
              </select>
            </div>
            <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
              Riportali in prima nota
            </button>
          </form>
        </div>
      </div>
      <button
        v-if="!modificaCassa"
        type="button"
        class="btn btn-sm btn-outline theme-primary mb-3"
        @click="apriCassa(null)"
      >
        Nuova cassa
      </button>
      <form v-if="modificaCassa" class="border rounded p-5 mb-5" @submit.prevent="salvaCassa">
        <div class="row g-3">
          <div class="md:col-6">
            <label class="form-label small" for="cassa-nome">Nome</label>
            <input
              id="cassa-nome"
              v-model="modificaCassa.nome"
              class="form-control form-control-sm"
              required
            />
          </div>
          <div class="md:col-6">
            <label class="form-label small" for="cassa-tipo">Tipo</label>
            <select
              id="cassa-tipo"
              v-model="modificaCassa.tipo"
              class="form-control form-control-sm"
            >
              <option value="CONTANTI">Contanti</option>
              <option value="BANCA">Conto bancario</option>
            </select>
          </div>
          <div v-if="modificaCassa.tipo === 'CONTANTI'" class="md:col-6">
            <label class="form-label small" for="cassa-unita">Unità</label>
            <select
              id="cassa-unita"
              v-model="modificaCassa.unita_id"
              class="form-control form-control-sm"
            >
              <option :value="null">Gruppo</option>
              <option v-for="u in unita" :key="u.id" :value="u.id">{{ nomeUnita(u) }}</option>
            </select>
          </div>
          <div class="md:col-3">
            <label class="form-label small" for="cassa-saldo">Saldo iniziale (€)</label>
            <input
              id="cassa-saldo"
              v-model="modificaCassa.saldo_iniziale"
              type="number"
              step="0.01"
              class="form-control form-control-sm"
              required
            />
          </div>
          <div class="md:col-3">
            <label class="form-label small" for="cassa-data">Alla data</label>
            <input
              id="cassa-data"
              v-model="modificaCassa.data_saldo_iniziale"
              type="date"
              class="form-control form-control-sm"
              required
            />
          </div>
          <div class="col-12 form-field">
            <div class="switch">
              <input
                id="cassa-attiva"
                v-model="modificaCassa.attiva"
                type="checkbox"
                role="switch"
              />
            </div>
            <label for="cassa-attiva">Attiva</label>
          </div>
        </div>
        <div class="d-flex gap-3 mt-3">
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Salva
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="modificaCassa = null">
            Annulla
          </button>
        </div>
      </form>
      <ul class="list-group">
        <li
          v-for="c in casse"
          :key="c.id"
          class="list-group-item d-flex justify-content-between align-items-center"
        >
          <span>
            {{ c.nome }}
            <span class="small fg-2">
              · {{ c.tipo === 'BANCA' ? 'Conto bancario' : etichettaUnita(c.unita_id) }} · saldo
              iniziale {{ euro(c.saldo_iniziale) }} al {{ data(c.data_saldo_iniziale) }}
            </span>
          </span>
          <button type="button" class="btn btn-sm btn-link" @click="apriCassa(c)">Modifica</button>
        </li>
      </ul>
    </template>
  </section>
</template>
