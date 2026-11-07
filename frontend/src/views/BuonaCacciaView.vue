<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { api, type EventoBCIn, type EventoBCTrovato, type IscrizioneBC } from '@/api/qdc'
import ModuloEventoBC from '@/components/ModuloEventoBC.vue'
import { useErrore } from '@/composables/useErrore'
import { useRicercaMentreScrivi } from '@/composables/useRicercaMentreScrivi'
import { useSessioneStore } from '@/stores/sessione'

// The staff's notebook for BuonaCaccia (DEC-158): the registrations to follow, nearest
// deadline first; an event is searched before it is created, so two members at the same
// event share it. Adults use this page to add the events they registered for (DEC-164).
const sessione = useSessioneStore()
const router = useRouter()
const { errore, esegui } = useErrore()
const iscrizioni = ref<IscrizioneBC[]>([])
const cerca = ref('')
const oggi = () => new Date().toLocaleDateString('sv')
const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')

onMounted(async () => {
  if (sessione.capo) iscrizioni.value = (await esegui(() => api.iscrizioniBC())) ?? []
})

// The events appear while one writes (DEC-397).
const { trovati, subito } = useRicercaMentreScrivi<EventoBCTrovato[]>(cerca, (testo) =>
  esegui(() => api.cercaEventiBC(testo)),
)

const scaduta = (i: IscrizioneBC) => i.mancanti.length > 0 && i.scadenza < oggi()

// --- New event -----------------------------------------------------------------------------

const nuovo = ref(false)

async function crea(dati: EventoBCIn) {
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
        Nessuna iscrizione aperta dei ragazzi/e delle tue unità.
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
              <template v-if="i.mancanti.length">
                Entro il {{ data(i.scadenza) }} manca: {{ i.mancanti.join(', ') }}
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
      <form class="mb-3" role="search" @submit.prevent="subito">
        <label class="form-label small" for="cerca-bc">Nome o luogo dell'evento</label>
        <input
          id="cerca-bc"
          v-model="cerca"
          type="search"
          class="form-control form-control-sm"
          autocomplete="off"
          placeholder="Scrivi almeno due lettere…"
        />
      </form>
      <div aria-live="polite">
        <template v-if="trovati">
          <ul v-if="trovati.length" class="list-group mb-3">
            <li v-for="e in trovati" :key="e.id" class="list-group-item">
              <RouterLink :to="`/eventi/${e.id}`">{{ e.titolo }}</RouterLink>
              <span class="small fg-2">
                · {{ data(e.inizio) }}<template v-if="e.luogo"> · {{ e.luogo }}</template> ·
                {{ e.tipologia }}
              </span>
            </li>
          </ul>
          <p v-else class="small">Nessun evento trovato.</p>
        </template>
      </div>
      <button
        v-if="!nuovo && cerca.trim()"
        type="button"
        class="btn btn-sm btn-outline theme-primary"
        @click="nuovo = true"
      >
        Non c'è: aggiungilo
      </button>

      <ModuloEventoBC
        v-if="nuovo"
        :titolo-iniziale="cerca"
        etichetta="Aggiungi l'evento"
        @salva="crea"
        @annulla="nuovo = false"
      />
    </section>
  </section>
</template>
