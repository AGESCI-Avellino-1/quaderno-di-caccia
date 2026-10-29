<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { api, type AnteprimaCancellazione, type Fascicolo } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Full personal file for a data subject's request (DEC-102), capigruppo only: JSON for
// portability, this page to print or save as PDF, and erasure. Online only: never
// cached on the device; every export is in the access log.
const props = defineProps<{ id: number }>()
const { errore, inCorso, esegui } = useErrore()
const fascicolo = ref<Fascicolo | null>(null)
const anteprima = ref<AnteprimaCancellazione | null>(null)
const cognome = ref('')
const cancellata = ref<AnteprimaCancellazione | null>(null)

const TITOLI: Record<string, string> = {
  anagrafica: 'Dati anagrafici',
  account: 'Account',
  genitori_e_tutori: 'Genitori e tutori',
  figli_o_tutelati: 'Figli o tutelati',
  unita: 'Unità',
  squadriglie: 'Squadriglie',
  incarichi: 'Incarichi',
  telefono_in_squadriglia: 'Telefono in squadriglia',
  informazioni_sanitarie: 'Farmaci, allergie e alimentazione',
  eccezioni_squadriglia: 'Eccezioni sulla squadriglia',
  visibilita_ai_genitori: 'Cosa vedono i genitori',
  quote: 'Quote e pagamenti',
  email_scelte: 'Email scelte',
  correzioni_ai_dati: 'Correzioni ai dati',
  inviti: 'Inviti',
  accessi_ai_dati_delicati: 'Chi ha visto i dati delicati',
  iscrizioni_dall_app: "Iscrizioni dall'app",
  richieste_dei_diritti: 'Richieste fatte',
}

onMounted(async () => {
  fascicolo.value = (await esegui(() => api.fascicolo(props.id))) ?? null
})

const sezioni = () => Object.entries(fascicolo.value ?? {}).filter(([chiave]) => chiave in TITOLI)

const testo = (v: unknown): string => {
  if (v === true) return 'Sì'
  if (v === false) return 'No'
  if (v === null || v === '') return '—'
  const s = String(v)
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s.split('-').reverse().join('/')
  if (/^\d{4}-\d{2}-\d{2}T/.test(s)) return new Date(s).toLocaleString('it-IT')
  return s
}
const elenco = (v: unknown): v is Record<string, unknown>[] => Array.isArray(v)
const oggetto = (v: unknown): v is Record<string, unknown> =>
  !!v && typeof v === 'object' && !Array.isArray(v)

function scarica() {
  if (!fascicolo.value) return
  const file = new Blob([JSON.stringify(fascicolo.value, null, 2)], { type: 'application/json' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(file)
  link.download = `fascicolo-${props.id}.json`
  link.click()
  URL.revokeObjectURL(link.href)
}

const stampa = () => window.print()

async function preparaCancellazione() {
  cognome.value = ''
  anteprima.value = (await esegui(() => api.anteprimaCancellazione(props.id))) ?? null
}

async function cancella() {
  const esito = await esegui(() => api.cancella(props.id, cognome.value))
  if (!esito) return
  cancellata.value = esito
  anteprima.value = null
  fascicolo.value = null
}
</script>

<template>
  <section>
    <p class="qdc-non-stampare small">
      <RouterLink :to="{ name: 'persona', params: { id } }">← Torna alla scheda</RouterLink> ·
      <RouterLink to="/diritti">Richieste degli interessati</RouterLink>
    </p>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <div v-if="cancellata" class="alert theme-success" role="status">
      <div>
        Dati cancellati.
        <template v-if="cancellata.anonimizza">La persona è stata resa anonima.</template>
        <template v-else>{{ cancellata.motivo_anagrafica }}</template>
        Ricordati di segnare la richiesta come chiusa.
      </div>
    </div>

    <template v-if="fascicolo">
      <h1 class="h4 mb-1">
        Fascicolo di {{ fascicolo.persona.nome }} {{ fascicolo.persona.cognome }}
      </h1>
      <p class="fg-2 small">
        Tutti i dati che il Quaderno di Caccia conserva su questa persona, al
        {{ new Date(fascicolo.generato_il).toLocaleString('it-IT') }}. Questa consultazione è
        registrata.
      </p>
      <div class="qdc-non-stampare d-flex flex-wrap gap-3 mb-5">
        <button type="button" class="btn btn-sm btn-solid theme-primary" @click="scarica">
          Scarica il file (JSON)
        </button>
        <button type="button" class="btn btn-sm btn-outline theme-primary" @click="stampa">
          Stampa o salva in PDF
        </button>
      </div>

      <section v-for="[chiave, valore] in sezioni()" :key="chiave" class="mb-5">
        <h2 class="h6">{{ TITOLI[chiave] }}</h2>
        <p v-if="valore === null || (elenco(valore) && !valore.length)" class="small fg-2">
          Nessun dato.
        </p>
        <table v-else-if="elenco(valore)" class="table table-sm small">
          <thead>
            <tr>
              <th v-for="k in Object.keys(valore[0] ?? {})" :key="k" scope="col">{{ k }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(riga, i) in valore" :key="i">
              <td v-for="(v, k) in riga" :key="k">{{ testo(v) }}</td>
            </tr>
          </tbody>
        </table>
        <dl v-else-if="oggetto(valore)" class="row small mb-0">
          <template v-for="(v, k) in valore" :key="k">
            <dt class="col-5 md:col-4 fw-normal fg-2">{{ k }}</dt>
            <dd v-if="elenco(v)" class="col-7 md:col-8">
              <div v-for="(riga, i) in v" :key="i">
                {{ Object.values(riga).map(testo).join(' · ') }}
              </div>
              <span v-if="!v.length">—</span>
            </dd>
            <dd v-else class="col-7 md:col-8">{{ testo(v) }}</dd>
          </template>
        </dl>
      </section>

      <section class="qdc-non-stampare card card-body mb-5">
        <h2 class="h5 mb-1">Cancellazione</h2>
        <p class="form-text mb-3">
          Solo su richiesta dell'interessato o di chi esercita la responsabilità genitoriale. Non si
          può annullare.
        </p>
        <button
          v-if="!anteprima"
          type="button"
          class="btn btn-sm btn-outline theme-danger align-self-start"
          @click="preparaCancellazione"
        >
          Vedi cosa verrebbe cancellato
        </button>
        <form v-else class="vstack gap-3" @submit.prevent="cancella">
          <ul class="small mb-0">
            <li v-for="v in anteprima.voci" :key="v">{{ v }}</li>
          </ul>
          <p v-if="anteprima.motivo_anagrafica" class="small mb-0">
            I dati anagrafici restano: {{ anteprima.motivo_anagrafica }}
          </p>
          <div>
            <label class="form-label small" for="conferma-cognome">
              Per confermare scrivi il cognome: {{ fascicolo.persona.cognome }}
            </label>
            <input
              id="conferma-cognome"
              v-model="cognome"
              class="form-control form-control-sm"
              autocomplete="off"
              required
            />
          </div>
          <div class="d-flex gap-3">
            <button type="submit" class="btn btn-sm btn-solid theme-danger" :disabled="inCorso">
              Cancella definitivamente
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="anteprima = null">
              Annulla
            </button>
          </div>
        </form>
      </section>
    </template>
  </section>
</template>
