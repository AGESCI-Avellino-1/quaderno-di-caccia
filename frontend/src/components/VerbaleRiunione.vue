<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, ref } from 'vue'

import {
  api,
  allegatoVerbale,
  verbalePdf,
  verbaleZip,
  type PersonaBreve,
  type Verbale,
} from '@/api/qdc'
import { caricaAPezzi, misura } from '@/components/allegatiVerbale'
import { useErrore } from '@/composables/useErrore'

// The minutes of a meeting (DEC-322…DEC-331): online only, never kept on the device. What
// each user may do comes from the backend, which answers 404 to who may not read: then
// there is nothing here. The text is asked for only when opened, because a read of the
// Co.Ca.'s minutes goes to the access log (DEC-329).
const EditorTesto = defineAsyncComponent(() => import('@/components/EditorTesto.vue'))
const props = defineProps<{ evento: number }>()
const { errore, inCorso, esegui } = useErrore()
const verbale = ref<Verbale | null>(null)
const aperto = ref(false)
const testo = ref('')
const salvato = ref(false)
const redattore = ref<number | null>(null)
const confermaDefinitivo = ref(false)
const riapertura = ref<string | null>(null)
const caricamento = ref<{ nome: string; percentuale: number } | null>(null)
const daTogliere = ref<number | null>(null)

const definitivo = computed(() => verbale.value?.stato === 'DEFINITIVO')
const dimensioneAllegati = computed(() =>
  (verbale.value?.allegati ?? []).reduce((somma, a) => somma + a.dimensione, 0),
)

function mostra(dati: Verbale) {
  verbale.value = dati
  redattore.value = dati.redattore?.id ?? null
}

onMounted(async () => {
  try {
    mostra(await api.verbale(props.evento))
  } catch {
    verbale.value = null
  }
})

async function apri() {
  const dati = await esegui(() => api.verbale(props.evento, true))
  if (!dati) return
  mostra(dati)
  testo.value = dati.testo
  aperto.value = true
}

async function salva() {
  salvato.value = false
  const dati = await esegui(() => api.scriviVerbale(props.evento, testo.value))
  if (!dati) return
  mostra(dati)
  salvato.value = true
}

async function indica() {
  const dati = await esegui(() => api.indicaRedattore(props.evento, redattore.value))
  if (dati) mostra(dati)
}

async function nonPrevisto(valore: boolean) {
  const dati = await esegui(() => api.verbaleNonPrevisto(props.evento, valore))
  if (dati) mostra(dati)
}

async function rendiDefinitivo() {
  // What is on screen is what becomes definitive.
  const scritto = await esegui(() => api.scriviVerbale(props.evento, testo.value))
  if (!scritto) return
  const dati = await esegui(() => api.verbaleDefinitivo(props.evento))
  confermaDefinitivo.value = false
  if (dati) mostra({ ...dati, testo: testo.value })
}

async function riapri() {
  const dati = await esegui(() => api.riapriVerbale(props.evento, riapertura.value ?? ''))
  if (!dati) return
  mostra(dati)
  testo.value = dati.testo
  aperto.value = true
  riapertura.value = null
}

async function carica(evento: Event) {
  const campo = evento.target as HTMLInputElement
  const file = campo.files?.[0]
  campo.value = ''
  if (!file || !verbale.value) return
  const pezzo = verbale.value.pezzo
  caricamento.value = { nome: file.name, percentuale: 0 }
  await esegui(async () => {
    const allegato = await api.nuovoAllegatoVerbale(props.evento, file.name, file.size)
    await caricaAPezzi(allegato.id, file, pezzo, (percentuale) => {
      caricamento.value = { nome: file.name, percentuale }
    })
    mostra({ ...(await api.verbale(props.evento)), testo: testo.value })
  })
  caricamento.value = null
}

async function togli(id: number) {
  const fatto = await esegui(async () => {
    await api.togliAllegatoVerbale(id)
    mostra({ ...(await api.verbale(props.evento)), testo: testo.value })
    return true
  })
  if (fatto) daTogliere.value = null
}

const nomeDi = (p: PersonaBreve) => `${p.cognome} ${p.nome}`
const quando = (iso: string) => new Date(iso).toLocaleString('it-IT')
</script>

<template>
  <section v-if="verbale" class="card card-body mb-5">
    <div class="d-flex flex-wrap align-items-center gap-3 mb-3">
      <h2 class="h5 mb-0">Verbale</h2>
      <span v-if="verbale.non_previsto" class="badge theme-secondary">Non previsto</span>
      <span v-else-if="definitivo" class="badge theme-success">Definitivo</span>
      <span v-else class="badge theme-warning">Bozza</span>
    </div>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <p v-if="verbale.redattore && !definitivo" class="small fg-2 mb-3">
      Lo scrive {{ verbale.redattore.nome }} {{ verbale.redattore.cognome }}.
    </p>
    <p v-else-if="verbale.autore_nome" class="small fg-2 mb-3">
      Scritto da {{ verbale.autore_nome }}.
    </p>

    <button
      v-if="!aperto"
      type="button"
      class="btn btn-sm btn-outline theme-primary align-self-start mb-3"
      :disabled="inCorso"
      @click="apri"
    >
      {{ verbale.puo_scrivere ? 'Scrivi il verbale' : 'Leggi il verbale' }}
    </button>

    <template v-if="aperto">
      <form v-if="verbale.puo_scrivere" class="mb-3" @submit.prevent="salva">
        <EditorTesto v-model="testo" etichetta="Testo del verbale" />
        <div class="d-flex flex-wrap align-items-center gap-3 mt-3">
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Salva la bozza
          </button>
          <span v-if="salvato" class="small fg-2" role="status">Salvato.</span>
          <template v-if="verbale.puo_indicare">
            <button
              v-if="!confermaDefinitivo"
              type="button"
              class="btn btn-sm btn-outline theme-primary"
              @click="confermaDefinitivo = true"
            >
              Rendi definitivo
            </button>
            <span v-else class="small">
              Da definitivo lo leggono tutti quelli che ne hanno diritto. Confermi?
              <button
                type="button"
                class="btn btn-sm btn-solid theme-primary py-0"
                :disabled="inCorso"
                @click="rendiDefinitivo"
              >
                Sì
              </button>
              <button
                type="button"
                class="btn btn-sm btn-link py-0"
                @click="confermaDefinitivo = false"
              >
                No
              </button>
            </span>
          </template>
        </div>
      </form>
      <!-- eslint-disable-next-line vue/no-v-html -- HTML cleaned by the server (DEC-322) -->
      <div v-else-if="verbale.testo" class="mb-3" v-html="verbale.testo"></div>
      <p v-else class="fg-2 small mb-3">Il verbale è ancora vuoto.</p>
    </template>

    <form v-if="verbale.puo_indicare" class="row g-3 align-items-end mb-3" @submit.prevent="indica">
      <div class="col-12 sm:col-8">
        <label class="form-label small" :for="`redattore-${evento}`">Chi lo scrive</label>
        <select
          :id="`redattore-${evento}`"
          v-model="redattore"
          class="form-control form-control-sm"
        >
          <option :value="null">Nessuno in particolare</option>
          <option v-for="p in verbale.candidati" :key="p.id" :value="p.id">{{ nomeDi(p) }}</option>
        </select>
      </div>
      <div class="col-12 sm:col-4">
        <button
          type="submit"
          class="btn btn-sm btn-outline theme-primary w-100"
          :disabled="inCorso"
        >
          Indica
        </button>
      </div>
    </form>

    <div v-if="verbale.puo_dire_non_previsto" class="form-field mb-3">
      <input
        :id="`non-previsto-${evento}`"
        type="checkbox"
        class="check"
        :checked="verbale.non_previsto"
        :disabled="inCorso"
        @change="nonPrevisto(($event.target as HTMLInputElement).checked)"
      />
      <label :for="`non-previsto-${evento}`">
        Per questa riunione il verbale non c'è (non arrivano più promemoria)
      </label>
    </div>

    <h3 class="h6">Allegati</h3>
    <ul class="list-unstyled mb-3">
      <li
        v-for="a in verbale.allegati"
        :key="a.id"
        class="d-flex flex-wrap align-items-center gap-3"
      >
        <a :href="allegatoVerbale(a.id)" :data-dimensione="a.dimensione">{{ a.nome_file }}</a>
        <span class="small fg-2">{{ misura(a.dimensione) }}</span>
        <template v-if="verbale.puo_scrivere && (!a.di_convocazione || verbale.puo_indicare)">
          <button
            v-if="daTogliere !== a.id"
            type="button"
            class="btn btn-link btn-sm p-0"
            @click="daTogliere = a.id"
          >
            togli
          </button>
          <span v-else class="small">
            Toglierlo?
            <button
              type="button"
              class="btn btn-sm btn-solid theme-danger py-0"
              :disabled="inCorso"
              @click="togli(a.id)"
            >
              Sì
            </button>
            <button type="button" class="btn btn-sm btn-link py-0" @click="daTogliere = null">
              No
            </button>
          </span>
        </template>
      </li>
      <li v-if="!verbale.allegati.length" class="fg-2 small">Nessun allegato.</li>
    </ul>
    <div v-if="verbale.puo_scrivere" class="mb-3">
      <label class="form-label small" :for="`allegato-${evento}`">
        Aggiungi un file (PDF, immagini, Word, Excel, PowerPoint, audio, video), al massimo
        {{ misura(verbale.massimo_allegato) }}
      </label>
      <input
        :id="`allegato-${evento}`"
        type="file"
        class="form-control form-control-sm"
        :disabled="!!caricamento"
        @change="carica"
      />
      <p v-if="caricamento" class="small fg-2 mb-0 mt-1" role="status">
        Carico {{ caricamento.nome }}: {{ caricamento.percentuale }}%. Non chiudere la pagina.
      </p>
    </div>

    <div v-if="verbale.puo_stampare" class="d-flex flex-wrap gap-3 mb-3">
      <a :href="verbalePdf(evento)" class="btn btn-sm btn-outline theme-primary">Scarica il PDF</a>
      <a
        v-if="verbale.zip_possibile && verbale.allegati.length"
        :href="verbaleZip(evento)"
        :data-dimensione="dimensioneAllegati"
        class="btn btn-sm btn-outline theme-primary"
      >
        Scarica lo ZIP con gli allegati
      </a>
      <span v-else-if="verbale.allegati.length && !verbale.zip_possibile" class="small fg-2">
        Gli allegati superano 2 GB: scaricali uno per uno.
      </span>
    </div>

    <form
      v-if="verbale.puo_riaprire && riapertura !== null"
      class="row g-3 align-items-end mb-3"
      @submit.prevent="riapri"
    >
      <div class="col-12 sm:col-8">
        <label class="form-label small" :for="`riapertura-${evento}`">Perché lo riapri</label>
        <input
          :id="`riapertura-${evento}`"
          v-model="riapertura"
          class="form-control form-control-sm"
          maxlength="300"
          required
        />
      </div>
      <div class="col-12 sm:col-4 d-flex gap-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Riapri
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="riapertura = null">
          Annulla
        </button>
      </div>
    </form>
    <button
      v-else-if="verbale.puo_riaprire"
      type="button"
      class="btn btn-link btn-sm p-0 align-self-start"
      @click="riapertura = ''"
    >
      Riapri il verbale
    </button>

    <details v-if="verbale.accessi" class="mt-3 small">
      <summary>Chi l'ha letto</summary>
      <ul class="list-unstyled mb-0 mt-1">
        <li v-for="(a, i) in verbale.accessi" :key="i">
          {{ quando(a.quando) }} · {{ a.chi }} · {{ a.azione }}
        </li>
        <li v-if="!verbale.accessi.length" class="fg-2">Nessuna lettura.</li>
      </ul>
    </details>
  </section>
</template>
