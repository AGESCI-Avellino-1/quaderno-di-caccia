<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { api, type PassaggiUnita, type PassaggioBranca } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Passages to the next branch, decided by the Co.Ca. in a block for a unit (DEC-69):
// prepared by the unit staff or a capogruppo with a summary for the new capi, then
// executed on their date: the branch periods close and open, the ragazzi move to the new
// unit as assigned in the app (BuonaStrada confirms at the next import). Tappe and
// specialità are never converted. Online only: an execution changes many records.
const props = defineProps<{ id: number }>()
const { errore, inCorso, esegui } = useErrore()
const dati = ref<PassaggiUnita | null>(null)
const esito = ref('')
const oggi = () => new Date().toLocaleDateString('sv')
const data = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString('it-IT') : '')

async function carica() {
  dati.value = (await esegui(() => api.passaggiUnita(props.id))) ?? null
}
watch(() => props.id, carica, { immediate: true })

const modulo = reactive({
  id: 0,
  aperto: false,
  unita_destinazione_id: 0,
  data: oggi(),
  data_decisione: '',
  data_cerimonia: '',
  scelti: [] as number[],
  sintesi: {} as Record<number, string>,
})

function nuovo() {
  Object.assign(modulo, {
    id: 0,
    aperto: true,
    unita_destinazione_id: dati.value?.destinazioni[0]?.id ?? 0,
    data: oggi(),
    data_decisione: '',
    data_cerimonia: '',
    scelti: [],
    sintesi: {},
  })
}

function modifica(p: PassaggioBranca) {
  Object.assign(modulo, {
    id: p.id,
    aperto: true,
    unita_destinazione_id: p.unita_destinazione_id,
    data: p.data,
    data_decisione: p.data_decisione ?? '',
    data_cerimonia: p.data_cerimonia ?? '',
    scelti: p.persone.map((r) => r.persona_id),
    sintesi: Object.fromEntries(p.persone.map((r) => [r.persona_id, r.sintesi])),
  })
}

async function salva() {
  const corpo = {
    unita_destinazione_id: modulo.unita_destinazione_id,
    data: modulo.data,
    data_decisione: modulo.data_decisione || null,
    data_cerimonia: modulo.data_cerimonia || null,
    persone: modulo.scelti.map((id) => ({ persona_id: id, sintesi: modulo.sintesi[id] ?? '' })),
  }
  const nuovi = await esegui(() =>
    modulo.id ? api.modificaPassaggio(modulo.id, corpo) : api.preparaPassaggio(props.id, corpo),
  )
  if (!nuovi) return
  dati.value = nuovi
  modulo.aperto = false
  esito.value = 'Passaggio preparato: si esegue dalla sua data.'
}

const annullamento = reactive({ id: 0, motivo: '' })
// Executing changes many records at once: an explicit confirmation first.
const conferma = ref(0)
// Correcting an executed passage (DEC-178): undo for some or all, or move the date.
const rettifica = reactive({
  id: 0,
  tipo: '' as '' | 'annulla' | 'data',
  persone: [] as number[],
  data: '',
  motivo: '',
})

function apriRettifica(p: PassaggioBranca, tipo: 'annulla' | 'data') {
  Object.assign(rettifica, {
    id: p.id,
    tipo,
    persone: p.persone.filter((r) => !r.rettificata).map((r) => r.persona_id),
    data: p.data,
    motivo: '',
  })
}

async function applicaRettifica() {
  const p = [...(dati.value?.in_uscita ?? []), ...(dati.value?.in_entrata ?? [])].find(
    (x) => x.id === rettifica.id,
  )
  const tutti = p
    ? p.persone.filter((r) => !r.rettificata).length === rettifica.persone.length
    : true
  const nuovi = await esegui(() =>
    rettifica.tipo === 'data'
      ? api.correggiDataPassaggio(rettifica.id, rettifica.data, rettifica.motivo)
      : api.annullaEsecuzione(rettifica.id, rettifica.motivo, tutti ? null : rettifica.persone),
  )
  if (!nuovi) return
  dati.value = nuovi
  esito.value =
    rettifica.tipo === 'data'
      ? 'Data corretta: periodi e unità spostati al giorno giusto.'
      : 'Passaggio annullato: i ragazzi sono tornati dove erano.'
  rettifica.id = 0
}

async function eseguiPassaggio(p: PassaggioBranca) {
  const nuovi = await esegui(() => api.eseguiPassaggio(p.id))
  if (!nuovi) return
  dati.value = nuovi
  conferma.value = 0
  esito.value = `Passaggio eseguito: ora sono in ${p.unita_destinazione}.`
}

async function annulla() {
  const nuovi = await esegui(() => api.annullaPassaggio(annullamento.id, annullamento.motivo))
  if (!nuovi) return
  dati.value = nuovi
  annullamento.id = 0
  esito.value = 'Passaggio annullato: non è cambiato nulla.'
}

const COLORI: Record<string, string> = {
  PREPARATO: 'theme-warning',
  ESEGUITO: 'theme-success',
  ANNULLATO: 'theme-secondary',
  RETTIFICATO: 'theme-secondary',
}
</script>

<template>
  <section>
    <h1 class="h4 mb-1">Passaggi</h1>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>
    <template v-if="dati">
      <p class="small fg-2">
        {{ dati.unita }}. Li decide la Co.Ca.: qui si prepara il passaggio con una sintesi per i
        nuovi capi e si esegue dalla sua data. Tappe e specialità restano nella storia, non si
        convertono. <RouterLink :to="`/unita/${props.id}`">Pagina dell'unità</RouterLink>
      </p>

      <button
        v-if="dati.puo_preparare && !modulo.aperto"
        type="button"
        class="btn btn-sm btn-solid theme-primary mb-3"
        @click="nuovo"
      >
        Prepara un passaggio
      </button>

      <form v-if="modulo.aperto" class="card card-body mb-5" @submit.prevent="salva">
        <div class="row g-3">
          <div class="col-12 md:col-6">
            <label class="form-label small" for="pa-dest">Verso</label>
            <select
              id="pa-dest"
              v-model="modulo.unita_destinazione_id"
              class="form-control form-control-sm"
              required
            >
              <option v-for="u in dati.destinazioni" :key="u.id" :value="u.id">{{ u.nome }}</option>
            </select>
          </div>
          <div class="col-12 md:col-6">
            <label class="form-label small" for="pa-data">Dal (data del passaggio)</label>
            <input
              id="pa-data"
              v-model="modulo.data"
              type="date"
              class="form-control form-control-sm"
              required
            />
          </div>
          <div class="col-12 md:col-6">
            <label class="form-label small" for="pa-dec">Decisione della Co.Ca. (data)</label>
            <input
              id="pa-dec"
              v-model="modulo.data_decisione"
              type="date"
              class="form-control form-control-sm"
            />
          </div>
          <div class="col-12 md:col-6">
            <label class="form-label small" for="pa-cer">Cerimonia (se in un altro giorno)</label>
            <input
              id="pa-cer"
              v-model="modulo.data_cerimonia"
              type="date"
              class="form-control form-control-sm"
            />
          </div>
        </div>
        <fieldset class="mt-3">
          <legend class="form-label small">Chi passa, con la sintesi per i nuovi capi</legend>
          <div v-for="r in dati.ragazzi" :key="r.id" class="mb-3">
            <div class="form-field mb-1">
              <input
                :id="`pa-${r.id}`"
                v-model="modulo.scelti"
                type="checkbox"
                class="check"
                :value="r.id"
              />
              <label class="small" :for="`pa-${r.id}`">{{ r.nome }}</label>
            </div>
            <textarea
              v-if="modulo.scelti.includes(r.id)"
              v-model="modulo.sintesi[r.id]"
              class="form-control form-control-sm"
              rows="2"
              :aria-label="`Sintesi per i nuovi capi: ${r.nome}`"
              placeholder="Esperienze, competenze, interessi: ciò che serve ai nuovi capi"
            />
          </div>
        </fieldset>
        <div class="d-flex gap-3">
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Salva
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="modulo.aperto = false">
            Annulla
          </button>
        </div>
      </form>

      <section
        v-for="[titolo, elenco] in [
          ['In uscita', dati.in_uscita],
          ['In arrivo', dati.in_entrata],
        ] as const"
        :key="titolo"
        class="mb-5"
      >
        <h2 class="h5">{{ titolo }}</h2>
        <p v-if="!elenco.length" class="small fg-2">Nessuno.</p>
        <div v-for="p in elenco" :key="p.id" class="card card-body mb-3">
          <div class="d-flex flex-wrap justify-content-between gap-3">
            <strong>{{ p.unita_origine }} → {{ p.unita_destinazione }}</strong>
            <span class="badge" :class="COLORI[p.stato]">{{ p.stato_nome }}</span>
          </div>
          <p class="small mb-1">
            Dal {{ data(p.data)
            }}<template v-if="p.data_decisione">
              · decisione della Co.Ca. del {{ data(p.data_decisione) }}</template
            ><template v-if="p.data_cerimonia">
              · cerimonia il {{ data(p.data_cerimonia) }}</template
            >
            <template v-if="p.motivo_annullamento">
              · annullato: {{ p.motivo_annullamento }}</template
            >
            <template v-if="p.nota_rettifica"> · data corretta: {{ p.nota_rettifica }}</template>
          </p>
          <ul class="small mb-1">
            <li v-for="r in p.persone" :key="r.persona_id">
              <RouterLink :to="`/persone/${r.persona_id}/sentiero`">{{ r.persona }}</RouterLink>
              <span v-if="r.sintesi" class="fg-2 testo-a-capo"> — {{ r.sintesi }}</span>
              <span v-if="r.rettificata" class="badge theme-secondary ms-1">
                annullato dopo l'esecuzione: {{ r.motivo_rettifica }}
              </span>
            </li>
          </ul>
          <div v-if="p.puo_gestire && p.stato === 'PREPARATO'" class="d-flex flex-wrap gap-1">
            <button
              type="button"
              class="btn btn-sm btn-solid theme-success"
              :disabled="inCorso || p.data > oggi()"
              @click="conferma = p.id"
            >
              Esegui…
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="modifica(p)">Modifica</button>
            <button
              type="button"
              class="btn btn-sm btn-link"
              @click="Object.assign(annullamento, { id: p.id, motivo: '' })"
            >
              Annulla…
            </button>
            <span v-if="p.data > oggi()" class="small fg-2">Si esegue dal {{ data(p.data) }}.</span>
          </div>
          <div v-if="conferma === p.id" class="alert theme-warning small mt-1" role="alert">
            <div>
              <p class="mb-1">
                Dal {{ data(p.data) }} {{ p.persone.length === 1 ? 'passa' : 'passano' }} in
                <strong>{{ p.unita_destinazione }}</strong
                >: {{ p.persone.map((r) => r.persona).join(', ') }}. Si chiude il percorso nella
                branca di oggi e se ne apre uno nuovo; cambiano unità, squadriglia e incarichi di
                squadriglia.
              </p>
              <button
                type="button"
                class="btn btn-sm btn-solid theme-success"
                :disabled="inCorso"
                @click="eseguiPassaggio(p)"
              >
                Confermo, esegui
              </button>
              <button type="button" class="btn btn-sm btn-link" @click="conferma = 0">
                Lascia stare
              </button>
            </div>
          </div>
          <div
            v-if="p.puo_gestire && p.stato === 'ESEGUITO' && rettifica.id !== p.id"
            class="d-flex flex-wrap gap-1"
          >
            <span class="small fg-2">Eseguito per errore?</span>
            <button type="button" class="btn btn-sm btn-link" @click="apriRettifica(p, 'annulla')">
              Annulla l'esecuzione…
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="apriRettifica(p, 'data')">
              Correggi la data…
            </button>
          </div>
          <form
            v-if="rettifica.id === p.id"
            class="card card-body mt-1"
            @submit.prevent="applicaRettifica"
          >
            <fieldset v-if="rettifica.tipo === 'annulla'" class="mb-3">
              <legend class="form-label small">
                Per chi si annulla (torna dove era, con il suo percorso)
              </legend>
              <div
                v-for="r in p.persone.filter((x) => !x.rettificata)"
                :key="r.persona_id"
                class="form-field"
              >
                <input
                  :id="`ret-${p.id}-${r.persona_id}`"
                  v-model="rettifica.persone"
                  type="checkbox"
                  class="check"
                  :value="r.persona_id"
                />
                <label class="small" :for="`ret-${p.id}-${r.persona_id}`">{{ r.persona }}</label>
              </div>
            </fieldset>
            <div v-else class="mb-3">
              <label class="form-label small" :for="`ret-data-${p.id}`"
                >Data giusta del passaggio</label
              >
              <input
                :id="`ret-data-${p.id}`"
                v-model="rettifica.data"
                type="date"
                :max="oggi()"
                class="form-control form-control-sm w-auto"
                required
              />
            </div>
            <label class="form-label small" :for="`ret-mot-${p.id}`"
              >Perché (resta nella storia)</label
            >
            <input
              :id="`ret-mot-${p.id}`"
              v-model="rettifica.motivo"
              class="form-control form-control-sm mb-3"
              required
            />
            <p class="small fg-2">
              Non si può se il nuovo staff ha già registrato qualcosa nel nuovo percorso, o se dopo
              il passaggio è stata applicata un'importazione da BuonaStrada: l'app dice cosa fare.
            </p>
            <div class="d-flex gap-3">
              <button
                type="submit"
                class="btn btn-sm btn-solid theme-danger"
                :disabled="inCorso || (rettifica.tipo === 'annulla' && !rettifica.persone.length)"
              >
                {{ rettifica.tipo === 'data' ? 'Correggi la data' : "Annulla l'esecuzione" }}
              </button>
              <button type="button" class="btn btn-sm btn-link" @click="rettifica.id = 0">
                Lascia stare
              </button>
            </div>
          </form>
          <form
            v-if="annullamento.id === p.id"
            class="d-flex flex-wrap align-items-end gap-3 mt-1"
            @submit.prevent="annulla"
          >
            <div class="flex-grow-1">
              <label class="form-label small" :for="`pa-mot-${p.id}`">Perché si annulla</label>
              <input
                :id="`pa-mot-${p.id}`"
                v-model="annullamento.motivo"
                class="form-control form-control-sm"
                required
              />
            </div>
            <button type="submit" class="btn btn-sm btn-solid theme-danger" :disabled="inCorso">
              Annulla il passaggio
            </button>
          </form>
        </div>
      </section>
    </template>
  </section>
</template>
