<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import {
  api,
  TIPI_CAMPO,
  type EventoBCIn,
  type EventoBCTrovato,
  type IscrizioneBC,
} from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'
import { useSessioneStore } from '@/stores/sessione'

// The staff's notebook for BuonaCaccia (DEC-158): the registrations to follow, nearest
// deadline first; an event is searched before it is created, so two members at the same
// event share it. Adults use this page to add the events they registered for (DEC-164).
const sessione = useSessioneStore()
const router = useRouter()
const { errore, inCorso, esegui } = useErrore()
const iscrizioni = ref<IscrizioneBC[]>([])
const cerca = ref('')
const trovati = ref<EventoBCTrovato[] | null>(null)
const oggi = () => new Date().toLocaleDateString('sv')
const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')

onMounted(async () => {
  if (sessione.capo) iscrizioni.value = (await esegui(() => api.iscrizioniBC())) ?? []
})

async function trova() {
  trovati.value = (await esegui(() => api.cercaEventiBC(cerca.value))) ?? []
}

const manca = (i: IscrizioneBC) =>
  [
    (!i.liberatoria_caricata_il || i.esito_liberatoria === 'RIGETTATA') && 'liberatoria',
    !i.scheda_inviata_il && 'scheda',
    !i.pagata_il && 'pagamento',
  ].filter(Boolean)
const scaduta = (i: IscrizioneBC) => manca(i).length > 0 && i.scadenza < oggi()

// --- New event -----------------------------------------------------------------------------

const modulo = ref<EventoBCIn | null>(null)
const apri = () =>
  (modulo.value = {
    titolo: cerca.value,
    tipo: 'CAMPO',
    inizio: '',
    fine: '',
    luogo: '',
    descrizione: '',
    formazione_capi: false,
    piccole_orme: false,
    tipo_campo: null,
    specifica: '',
  })
const daLocale = (valore: string) => (valore ? new Date(valore).toISOString() : '')
const serveSpecifica = computed(
  () => modulo.value?.tipo_campo === 'MODULO' || modulo.value?.tipo_campo === 'ALTRO',
)

async function crea() {
  if (!modulo.value) return
  const dati = {
    ...modulo.value,
    inizio: daLocale(modulo.value.inizio),
    fine: daLocale(modulo.value.fine || modulo.value.inizio),
  }
  const evento = await esegui(() => api.creaEventoBC(dati))
  if (evento) await router.push(`/eventi/${evento.id}`)
}
</script>

<template>
  <section>
    <h1 class="h4">Eventi su BuonaCaccia</h1>
    <p class="small fg-2">
      Piccole Orme, campetti, EPPPI, campi di formazione e gli altri eventi di Zona, Regione e
      nazionali. L'app non parla con BuonaCaccia: qui lo staff tiene le scadenze e raccoglie dalle
      famiglie liberatoria, risposte alla scheda e foto.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <p class="d-flex flex-wrap gap-5 small">
      <RouterLink v-if="sessione.capo" to="/buonacaccia/schede">Schede degli eventi</RouterLink>
      <RouterLink v-if="sessione.profilo?.formazione_capi" to="/buonacaccia/formazione">
        Formazione capi per la Zona
      </RouterLink>
    </p>

    <section v-if="sessione.capo" class="mb-5">
      <h2 class="h5">Iscrizioni da seguire</h2>
      <p v-if="!iscrizioni.length" class="small fg-2">
        Nessuna iscrizione aperta dei ragazzi delle tue unità.
      </p>
      <ul v-else class="list-group">
        <li v-for="i in iscrizioni" :key="i.id" class="list-group-item">
          <RouterLink :to="`/eventi/${i.evento_id}`" class="d-block text-decoration-none">
            <div class="d-flex flex-wrap justify-content-between gap-3">
              <strong>{{ i.persona }}</strong>
              <span class="small">{{ i.evento }} · {{ data(i.inizio) }}</span>
            </div>
            <div class="small">
              <span v-if="i.stato === 'IN_ATTESA'" class="badge theme-warning me-1">
                In lista d'attesa
              </span>
              <span v-if="scaduta(i)" class="badge theme-danger me-1">Scaduta</span>
              <template v-if="manca(i).length">
                Entro il {{ data(i.scadenza) }} manca: {{ manca(i).join(', ') }}
              </template>
              <template v-else>Tutto fatto su BuonaCaccia</template>
              <template v-if="i.risposte_mancanti.length">
                · la famiglia deve ancora rispondere alla scheda
              </template>
            </div>
          </RouterLink>
        </li>
      </ul>
    </section>

    <section v-if="sessione.profilo?.eventi_buonacaccia" class="mb-5">
      <h2 class="h5">Cerca o aggiungi un evento</h2>
      <p class="small fg-2">
        Se un altro capo o un altro socio ha già aggiunto l'evento, usa quello: nell'app ogni evento
        di BuonaCaccia c'è una volta sola.
      </p>
      <form class="d-flex flex-wrap align-items-end gap-3 mb-3" @submit.prevent="trova">
        <div class="flex-grow-1">
          <label class="form-label small" for="cerca-bc">Nome o luogo dell'evento</label>
          <input id="cerca-bc" v-model="cerca" class="form-control form-control-sm" />
        </div>
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Cerca
        </button>
      </form>
      <template v-if="trovati">
        <ul v-if="trovati.length" class="list-group mb-3">
          <li v-for="e in trovati" :key="e.id" class="list-group-item">
            <RouterLink :to="`/eventi/${e.id}`">{{ e.titolo }}</RouterLink>
            <span class="small fg-2">
              · {{ data(e.inizio) }}<template v-if="e.luogo"> · {{ e.luogo }}</template>
              <template v-if="e.formazione_capi"> · formazione capi</template>
              <template v-if="e.piccole_orme"> · Piccole Orme</template>
            </span>
          </li>
        </ul>
        <p v-else class="small">Nessun evento trovato.</p>
        <button
          v-if="!modulo"
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          @click="apri"
        >
          Non c'è: aggiungilo
        </button>
      </template>

      <form v-if="modulo" class="card card-body mt-3" @submit.prevent="crea">
        <div class="row g-3">
          <div class="col-12">
            <label class="form-label small" for="bc-titolo">Nome (come su BuonaCaccia)</label>
            <input
              id="bc-titolo"
              v-model="modulo.titolo"
              class="form-control form-control-sm"
              required
            />
          </div>
          <div class="col-12 md:col-6">
            <label class="form-label small" for="bc-inizio">Inizio</label>
            <input
              id="bc-inizio"
              v-model="modulo.inizio"
              type="datetime-local"
              class="form-control form-control-sm"
              required
            />
          </div>
          <div class="col-12 md:col-6">
            <label class="form-label small" for="bc-fine">Fine</label>
            <input
              id="bc-fine"
              v-model="modulo.fine"
              type="datetime-local"
              class="form-control form-control-sm"
            />
          </div>
          <div class="col-12">
            <label class="form-label small" for="bc-luogo">Località</label>
            <input id="bc-luogo" v-model="modulo.luogo" class="form-control form-control-sm" />
          </div>
          <div class="col-12">
            <label class="form-label small" for="bc-descrizione">Note</label>
            <textarea
              id="bc-descrizione"
              v-model="modulo.descrizione"
              class="form-control form-control-sm"
              rows="2"
            />
          </div>
          <div class="col-12 form-field">
            <input
              id="bc-formazione"
              v-model="modulo.formazione_capi"
              type="checkbox"
              class="check"
            />
            <label class="small" for="bc-formazione">Campo di formazione capi</label>
          </div>
          <div v-if="!modulo.formazione_capi" class="col-12 form-field">
            <input id="bc-po" v-model="modulo.piccole_orme" type="checkbox" class="check" />
            <label class="small" for="bc-po">
              Piccole Orme (si vivono una volta sola: l'app avvisa se un bambino le ha già fatte)
            </label>
          </div>
          <template v-if="modulo.formazione_capi">
            <div class="col-12 md:col-6">
              <label class="form-label small" for="bc-tipo-campo">Tipo di campo</label>
              <select
                id="bc-tipo-campo"
                v-model="modulo.tipo_campo"
                class="form-control form-control-sm"
                required
              >
                <option v-for="[valore, nome] in TIPI_CAMPO" :key="valore" :value="valore">
                  {{ nome }}
                </option>
              </select>
            </div>
            <div v-if="serveSpecifica" class="col-12 md:col-6">
              <label class="form-label small" for="bc-specifica">
                {{ modulo.tipo_campo === 'MODULO' ? 'Titolo del modulo' : 'Specifica' }}
              </label>
              <input
                id="bc-specifica"
                v-model="modulo.specifica"
                class="form-control form-control-sm"
                required
              />
            </div>
          </template>
        </div>
        <div class="d-flex gap-3 mt-3">
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Aggiungi l'evento
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="modulo = null">Annulla</button>
        </div>
      </form>
    </section>
  </section>
</template>
