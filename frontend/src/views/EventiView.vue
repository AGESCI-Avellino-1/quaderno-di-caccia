<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import {
  api,
  nomeUnita,
  type Evento,
  type EventoIn,
  type RiunioneRicorrente,
  type Squadriglia,
  type Unita,
} from '@/api/qdc'
import CopiaLocale from '@/components/CopiaLocale.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'
import { useSessioneStore } from '@/stores/sessione'

// Events of the user and their children, all of them for the capi (DEC-75). The list is
// cached for offline use. Who may create what is decided by the API: the form offers
// what the profile suggests.
const sessione = useSessioneStore()
const { errore, inCorso, esegui } = useErrore()
const eventi = ref<Evento[]>([])
const copiaDel = ref<string | null>(null)
const passati = ref(false)
const unita = ref<Unita[]>([])
const squadriglie = ref<(Squadriglia & { reparto: string })[]>([])
const oggi = () => new Date().toLocaleDateString('sv')

const csq = computed(() => (sessione.profilo?.squadriglie_guidate.length ?? 0) > 0)
// A member the CSQ delegated creates the patrol's meetings only.
const delegato = computed(() => (sessione.profilo?.squadriglie_delegate.length ?? 0) > 0)
const soloRiunioni = computed(() => !sessione.capo && !csq.value && delegato.value)
const creaEventi = computed(() => sessione.capo || csq.value || delegato.value)

async function carica() {
  const filtri = passati.value ? { al: oggi() } : { dal: oggi() }
  const letto = await esegui(() =>
    leggiConCache(`eventi:${passati.value ? 'passati' : 'prossimi'}`, () => api.eventi(filtri)),
  )
  if (!letto) return
  eventi.value = passati.value ? [...letto.dati].reverse() : letto.dati
  copiaDel.value = letto.copiaDel
}
watch(passati, carica, { immediate: true })

onMounted(async () => {
  if (!creaEventi.value) return
  try {
    unita.value = (await leggiConCache('unita', () => api.unita())).dati
  } catch {
    unita.value = []
  }
  if (sessione.capo) {
    for (const reparto of unita.value.filter((u) => u.tipo === 'REPARTO')) {
      try {
        const dettaglio = await api.dettaglioUnita(reparto.id)
        squadriglie.value.push(
          ...dettaglio.squadriglie
            .filter((s) => s.attiva)
            .map((s) => ({ ...s, reparto: nomeUnita(reparto) })),
        )
      } catch {
        /* offline: patrol events wait for the network */
      }
    }
  } else {
    const delegate = sessione.profilo?.squadriglie_delegate ?? []
    try {
      const mie = await api.miaSquadriglia()
      squadriglie.value = mie
        .filter((s) => s.sono_capo || delegate.includes(s.id))
        .map(
          (s) =>
            ({ id: s.id, nome: s.nome, reparto: s.reparto }) as Squadriglia & {
              reparto: string
            },
        )
    } catch {
      squadriglie.value = []
    }
  }
})

// --- New event -----------------------------------------------------------------------------

const vuoto = (): EventoIn => ({
  titolo: '',
  tipo: soloRiunioni.value ? 'RIUNIONE' : 'USCITA',
  livello: sessione.capo ? 'UNITA' : 'SQUADRIGLIA',
  branca: null,
  unita: [],
  squadriglia_id: null,
  inizio: '',
  fine: '',
  luogo: '',
  descrizione: '',
  note_genitori: '',
  cerchia: 'TUTTI',
})
const modulo = ref<EventoIn | null>(null)

const daLocale = (valore: string) => (valore ? new Date(valore).toISOString() : '')

async function salva() {
  if (!modulo.value) return
  const dati = {
    ...modulo.value,
    inizio: daLocale(modulo.value.inizio),
    fine: daLocale(modulo.value.fine || modulo.value.inizio),
  }
  const fatto = await esegui(() => api.creaEvento(dati))
  if (!fatto) return
  modulo.value = null
  passati.value = false
  await carica()
}

// --- Recurring meetings ----------------------------------------------------------------

const GIORNI = ['lunedì', 'martedì', 'mercoledì', 'giovedì', 'venerdì', 'sabato', 'domenica']
const unitaRiunioni = ref<number | null>(null)
const riunioni = ref<RiunioneRicorrente[]>([])
const nuoveRiunioni = reactive({
  aperto: false,
  giorno_settimana: 5,
  ora_inizio: '16:00',
  ora_fine: '18:00',
  luogo: '',
  dal: oggi(),
  al: '',
})

watch(unitaRiunioni, async (id) => {
  riunioni.value = id === null ? [] : ((await esegui(() => api.riunioni(id))) ?? [])
})

async function creaRiunioni() {
  if (unitaRiunioni.value === null) return
  const dati = {
    giorno_settimana: nuoveRiunioni.giorno_settimana,
    ora_inizio: nuoveRiunioni.ora_inizio,
    ora_fine: nuoveRiunioni.ora_fine,
    luogo: nuoveRiunioni.luogo,
    dal: nuoveRiunioni.dal,
    al: nuoveRiunioni.al,
  }
  const fatte = await esegui(() => api.creaRiunioni(unitaRiunioni.value!, dati))
  if (!fatte) return
  nuoveRiunioni.aperto = false
  riunioni.value = (await esegui(() => api.riunioni(unitaRiunioni.value!))) ?? []
  await carica()
}

async function togliRiunioni(id: number) {
  if (!(await esegui(() => api.togliRiunioni(id)))) return
  riunioni.value = (await esegui(() => api.riunioni(unitaRiunioni.value!))) ?? []
  await carica()
}

const quando = (e: Evento) => {
  const inizio = new Date(e.inizio)
  const fine = new Date(e.fine)
  const giorno = (d: Date) =>
    d.toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'short' })
  const ora = (d: Date) => d.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
  return inizio.toDateString() === fine.toDateString()
    ? `${giorno(inizio)}, ${ora(inizio)}–${ora(fine)}`
    : `dal ${giorno(inizio)} al ${giorno(fine)}`
}
const statoMio = {
  INVITATO: '',
  NON_PARTECIPA: 'non partecipa',
  NON_INVITATO: 'non invitato',
}
</script>

<template>
  <section>
    <div class="d-flex flex-wrap align-items-center gap-3 mb-3">
      <h1 class="h4 mb-0">Eventi</h1>
      <CopiaLocale :del="copiaDel" />
    </div>
    <div class="d-flex flex-wrap gap-3 mb-5">
      <div class="form-field mb-0">
        <input id="eventi-passati" v-model="passati" type="checkbox" class="switch" role="switch" />
        <label for="eventi-passati">Eventi passati</label>
      </div>
      <button
        v-if="creaEventi && !modulo"
        type="button"
        class="btn btn-sm btn-solid theme-primary"
        @click="modulo = vuoto()"
      >
        Nuovo evento
      </button>
    </div>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>

    <form v-if="modulo" class="border rounded p-5 mb-5" @submit.prevent="salva">
      <div class="row g-3">
        <div class="md:col-8">
          <label class="form-label small" for="ev-titolo">Titolo</label>
          <input
            id="ev-titolo"
            v-model="modulo.titolo"
            class="form-control form-control-sm"
            required
          />
        </div>
        <div class="md:col-4">
          <label class="form-label small" for="ev-tipo">Tipo</label>
          <select
            id="ev-tipo"
            v-model="modulo.tipo"
            class="form-control form-control-sm"
            :disabled="soloRiunioni"
          >
            <option value="RIUNIONE">Riunione</option>
            <template v-if="!soloRiunioni">
              <option value="USCITA">Uscita</option>
              <option value="CAMPO">Campo</option>
              <option v-if="sessione.capo && modulo.livello === 'SQUADRIGLIA'" value="MISSIONE">
                Missione di squadriglia
              </option>
              <option value="AUTOFINANZIAMENTO">Autofinanziamento</option>
              <option value="ALTRO">Altro evento</option>
            </template>
          </select>
        </div>
        <div class="md:col-4">
          <label class="form-label small" for="ev-livello">Per chi</label>
          <select id="ev-livello" v-model="modulo.livello" class="form-control form-control-sm">
            <option v-if="sessione.capogruppo" value="GRUPPO">Tutto il gruppo</option>
            <option v-if="sessione.capo" value="BRANCA">Una branca</option>
            <option v-if="sessione.capo" value="UNITA">Una o più unità</option>
            <option v-if="squadriglie.length" value="SQUADRIGLIA">Una squadriglia</option>
          </select>
        </div>
        <div v-if="modulo.livello === 'BRANCA'" class="md:col-8">
          <label class="form-label small" for="ev-branca">Branca</label>
          <select
            id="ev-branca"
            v-model="modulo.branca"
            class="form-control form-control-sm"
            required
          >
            <option value="LC">Lupetti e Coccinelle</option>
            <option value="EG">Esploratori e Guide</option>
            <option value="RS">Rover e Scolte</option>
            <option value="COCA">Comunità Capi</option>
          </select>
        </div>
        <fieldset v-if="modulo.livello === 'UNITA'" class="md:col-8">
          <legend class="form-label small">Unità</legend>
          <div class="d-flex flex-wrap gap-5">
            <div v-for="u in unita" :key="u.id" class="form-field mb-0">
              <input
                :id="`ev-unita-${u.id}`"
                v-model="modulo.unita"
                type="checkbox"
                class="check"
                :value="u.id"
              />
              <label :for="`ev-unita-${u.id}`">{{ nomeUnita(u) }}</label>
            </div>
          </div>
        </fieldset>
        <div v-if="modulo.livello === 'UNITA'" class="md:col-4">
          <label class="form-label small" for="ev-cerchia">Chi è invitato</label>
          <select id="ev-cerchia" v-model="modulo.cerchia" class="form-control form-control-sm">
            <option value="TUTTI">Tutti i soci delle unità</option>
            <option value="CONCA">Consiglio Capi (reparti)</option>
            <option value="CONCAVI">Con.Ca.Vi., capi e vice (reparti)</option>
            <option value="ALTA_SQ">Alta Squadriglia (reparti)</option>
          </select>
        </div>
        <div v-if="modulo.livello === 'SQUADRIGLIA'" class="md:col-8">
          <label class="form-label small" for="ev-squadriglia">Squadriglia</label>
          <select
            id="ev-squadriglia"
            v-model="modulo.squadriglia_id"
            class="form-control form-control-sm"
            required
          >
            <option v-for="s in squadriglie" :key="s.id" :value="s.id">
              {{ s.nome }} · {{ s.reparto }}
            </option>
          </select>
        </div>
        <div class="md:col-6">
          <label class="form-label small" for="ev-inizio">Inizio</label>
          <input
            id="ev-inizio"
            v-model="modulo.inizio"
            type="datetime-local"
            class="form-control form-control-sm"
            required
          />
        </div>
        <div class="md:col-6">
          <label class="form-label small" for="ev-fine">Fine</label>
          <input
            id="ev-fine"
            v-model="modulo.fine"
            type="datetime-local"
            :min="modulo.inizio"
            class="form-control form-control-sm"
            required
          />
        </div>
        <div class="col-12">
          <label class="form-label small" for="ev-luogo">Luogo</label>
          <input id="ev-luogo" v-model="modulo.luogo" class="form-control form-control-sm" />
        </div>
        <div class="col-12">
          <label class="form-label small" for="ev-descrizione">Descrizione</label>
          <textarea
            id="ev-descrizione"
            v-model="modulo.descrizione"
            class="form-control form-control-sm"
            rows="3"
          ></textarea>
        </div>
        <div v-if="modulo.tipo === 'MISSIONE'" class="col-12">
          <label class="form-label small" for="ev-note-genitori">
            Note per i genitori (le leggono i genitori e i capi, non i ragazzi)
          </label>
          <textarea
            id="ev-note-genitori"
            v-model="modulo.note_genitori"
            class="form-control form-control-sm"
            rows="3"
          ></textarea>
        </div>
      </div>
      <p class="form-text mt-3 mb-0">
        Partecipano di default tutti i soci delle unità coinvolte: le famiglie possono dire che non
        partecipano, lo staff può non invitare qualcuno indicando il motivo.
      </p>
      <div class="d-flex gap-3 mt-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Crea l'evento
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="modulo = null">Annulla</button>
      </div>
    </form>

    <p v-if="!eventi.length && !inCorso" class="fg-2">Nessun evento.</p>
    <ul class="list-group mb-7">
      <li v-for="e in eventi" :key="e.id" class="list-group-item">
        <div class="d-flex flex-wrap align-items-baseline gap-3">
          <RouterLink
            :to="{ name: 'evento', params: { id: e.id } }"
            :class="{ 'text-decoration-line-through': e.annullato }"
          >
            <strong>{{ e.titolo }}</strong>
          </RouterLink>
          <span class="small fg-2">{{ quando(e) }}</span>
          <span v-if="e.annullato" class="badge theme-danger">Annullato</span>
        </div>
        <div class="small fg-2">
          {{ e.tipo_nome }} ·
          {{
            e.livello === 'GRUPPO'
              ? 'tutto il gruppo'
              : e.squadriglia
                ? `Sq. ${e.squadriglia}`
                : e.unita_nomi.join(', ')
          }}
          <template v-if="e.cerchia !== 'TUTTI'"> · {{ e.cerchia_nome }}</template>
          <template v-if="e.luogo"> · {{ e.luogo }}</template>
        </div>
        <div
          v-for="m in e.mie.filter((x) => x.stato !== 'INVITATO')"
          :key="m.persona_id"
          class="small"
        >
          {{ m.persona }}: {{ statoMio[m.stato] }}
        </div>
      </li>
    </ul>

    <section v-if="sessione.capo && !passati">
      <h2 class="h5">Riunioni ricorrenti</h2>
      <p class="form-text">
        Lo staff stabilisce le riunioni di ogni settimana: l'app crea una riunione per ogni data,
        con le sue presenze. Una singola data si annulla dalla riunione stessa.
      </p>
      <div class="mb-3">
        <label class="form-label small" for="riunioni-unita">Unità</label>
        <select
          id="riunioni-unita"
          v-model="unitaRiunioni"
          class="form-control form-control-sm w-auto"
        >
          <option :value="null" disabled>Scegli…</option>
          <option v-for="u in unita" :key="u.id" :value="u.id">{{ nomeUnita(u) }}</option>
        </select>
      </div>
      <template v-if="unitaRiunioni !== null">
        <ul v-if="riunioni.length" class="list-group mb-3">
          <li
            v-for="r in riunioni"
            :key="r.id"
            class="list-group-item d-flex flex-wrap justify-content-between align-items-center gap-3"
          >
            <span>
              Ogni {{ GIORNI[r.giorno_settimana] }}, {{ r.ora_inizio.slice(0, 5) }}–{{
                r.ora_fine.slice(0, 5)
              }}<template v-if="r.luogo"> · {{ r.luogo }}</template>
              <span class="small fg-2">
                · dal {{ new Date(r.dal).toLocaleDateString('it-IT') }} al
                {{ new Date(r.al).toLocaleDateString('it-IT') }} · {{ r.riunioni }} riunioni
              </span>
            </span>
            <button type="button" class="btn btn-sm btn-link" @click="togliRiunioni(r.id)">
              Togli le prossime
            </button>
          </li>
        </ul>
        <button
          v-if="!nuoveRiunioni.aperto"
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          @click="nuoveRiunioni.aperto = true"
        >
          Aggiungi riunioni ricorrenti
        </button>
        <form v-else class="border rounded p-5" @submit.prevent="creaRiunioni">
          <div class="row g-3">
            <div class="md:col-4">
              <label class="form-label small" for="riu-giorno">Ogni</label>
              <select
                id="riu-giorno"
                v-model.number="nuoveRiunioni.giorno_settimana"
                class="form-control form-control-sm"
              >
                <option v-for="(g, i) in GIORNI" :key="g" :value="i">{{ g }}</option>
              </select>
            </div>
            <div class="md:col-4">
              <label class="form-label small" for="riu-inizio">Dalle</label>
              <input
                id="riu-inizio"
                v-model="nuoveRiunioni.ora_inizio"
                type="time"
                class="form-control form-control-sm"
                required
              />
            </div>
            <div class="md:col-4">
              <label class="form-label small" for="riu-fine">Alle</label>
              <input
                id="riu-fine"
                v-model="nuoveRiunioni.ora_fine"
                type="time"
                class="form-control form-control-sm"
                required
              />
            </div>
            <div class="md:col-4">
              <label class="form-label small" for="riu-dal">Dal</label>
              <input
                id="riu-dal"
                v-model="nuoveRiunioni.dal"
                type="date"
                class="form-control form-control-sm"
                required
              />
            </div>
            <div class="md:col-4">
              <label class="form-label small" for="riu-al">Al</label>
              <input
                id="riu-al"
                v-model="nuoveRiunioni.al"
                type="date"
                :min="nuoveRiunioni.dal"
                class="form-control form-control-sm"
                required
              />
            </div>
            <div class="md:col-4">
              <label class="form-label small" for="riu-luogo">Luogo</label>
              <input
                id="riu-luogo"
                v-model="nuoveRiunioni.luogo"
                class="form-control form-control-sm"
              />
            </div>
          </div>
          <div class="d-flex gap-3 mt-3">
            <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
              Crea le riunioni
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="nuoveRiunioni.aperto = false">
              Annulla
            </button>
          </div>
        </form>
      </template>
    </section>
  </section>
</template>
