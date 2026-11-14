<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { api, nomeUnita, type Evento, type EventoIn, type Squadriglia, type Unita } from '@/api/qdc'
import CopiaLocale from '@/components/CopiaLocale.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'
import { giornoDaQuery, puoCreareEventi } from '@/eventi/creazione'
import { quandoEvento } from '@/eventi/orario'
import { useSessioneStore } from '@/stores/sessione'

// Events of the user and their children, all of them for the capi (DEC-75). The list is
// cached for offline use. Who may create what is decided by the API: the form offers
// what the profile suggests. Meetings have their own page (DEC-310).
const sessione = useSessioneStore()
const { errore, inCorso, esegui } = useErrore()
const eventi = ref<Evento[]>([])
const copiaDel = ref<string | null>(null)
const passati = ref(false)
const unita = ref<Unita[]>([])
const squadriglie = ref<(Squadriglia & { reparto: string })[]>([])
const oggi = () => new Date().toLocaleDateString('sv')
const route = useRoute()
const router = useRouter()

const creaEventi = computed(() => puoCreareEventi(sessione.profilo))

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
  // From the calendar's «+»: the form open on that day (DEC-412).
  const giorno = giornoDaQuery(route.query.giorno)
  if (giorno) {
    modulo.value = { ...vuoto(), inizio: `${giorno}T09:00` }
    void router.replace({ query: {} })
  }
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
    try {
      const mie = await api.miaSquadriglia()
      squadriglie.value = mie
        .filter((s) => s.sono_capo)
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
  tipo: 'USCITA',
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

const quando = (e: Evento) => quandoEvento(e)

// Type, who it is for, circle and place: only the parts there are, never an empty one
// between dots. An event on BuonaCaccia has no unit: «BuonaCaccia» and its type there
// (DEC-398).
function sottotitolo(e: Evento): string {
  if (e.livello === 'ESTERNO')
    return ['BuonaCaccia', e.tipologia_bc, e.luogo].filter(Boolean).join(' · ')
  const per =
    e.livello === 'GRUPPO'
      ? 'tutto il gruppo'
      : e.squadriglia
        ? `Sq. ${e.squadriglia}`
        : e.unita_nomi.join(', ')
  const cerchia = e.cerchia !== 'TUTTI' ? e.cerchia_nome : ''
  return [e.tipo_nome, per, cerchia, e.luogo].filter(Boolean).join(' · ')
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
        <div class="switch">
          <input id="eventi-passati" v-model="passati" type="checkbox" role="switch" />
        </div>
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
      <!-- To the search: an event on BuonaCaccia is in the app once only (DEC-390). -->
      <RouterLink
        v-if="sessione.profilo?.eventi_buonacaccia && !modulo"
        to="/buonacaccia"
        class="btn btn-sm btn-outline theme-primary"
      >
        Nuovo evento su BuonaCaccia
      </RouterLink>
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
          <select id="ev-tipo" v-model="modulo.tipo" class="form-control form-control-sm">
            <option value="USCITA">Uscita</option>
            <option value="CAMPO">Campo</option>
            <option v-if="sessione.capo && modulo.livello === 'SQUADRIGLIA'" value="MISSIONE">
              Missione di squadriglia
            </option>
            <option value="AUTOFINANZIAMENTO">Autofinanziamento</option>
            <option value="ALTRO">Altro evento</option>
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
            <option value="CDA">Consiglio degli Anziani (branchi e cerchi)</option>
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
            Note per i genitori (le leggono i genitori e i capi, non i ragazzi/e)
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
        <div class="small fg-2">{{ sottotitolo(e) }}</div>
        <div
          v-for="m in e.mie.filter((x) => x.stato !== 'INVITATO')"
          :key="m.persona_id"
          class="small"
        >
          {{ m.persona }}: {{ statoMio[m.stato] }}
        </div>
      </li>
    </ul>

    <p v-if="!passati" class="small mb-3">
      Vuoi gli eventi nel calendario del telefono? Vai al
      <RouterLink to="/calendario">Calendario</RouterLink>.
    </p>

    <p v-if="!passati" class="small mb-5">
      Le riunioni sono nella pagina <RouterLink to="/riunioni">Riunioni</RouterLink>.
    </p>
  </section>
</template>
