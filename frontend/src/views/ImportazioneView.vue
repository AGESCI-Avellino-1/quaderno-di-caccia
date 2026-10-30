<script setup lang="ts">
import { computed, ref } from 'vue'

import { api, valoreLeggibile, type EsitoImportazione, type Lato } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Two steps (DEC-33): the file is first read in preview, nothing is saved; the capogruppo
// checks the summary and only then applies it. Where the app and BuonaStrada disagree
// the user picks the winner; the more recent side is proposed, comparing the date of
// the change in the app with the date the BuonaStrada data were updated (DEC-130).
const { errore, inCorso, esegui } = useErrore()
const file = ref<File | null>(null)
// Local date as YYYY-MM-DD (toISOString would give the UTC day around midnight).
const oggi = new Date().toLocaleDateString('sv')
const aggiornatoAl = ref(oggi)
const esito = ref<EsitoImportazione | null>(null)
const scelte = ref<Record<string, Lato>>({})

const conteggi = computed(() => {
  const r = esito.value?.riepilogo
  if (!r) return []
  return [
    ['Persone nuove', r.persone_create.length],
    ['Persone aggiornate', r.persone_aggiornate.length],
    ['Genitori nuovi', r.genitori_creati.length],
    ['Unità nuove', r.unita_create.length],
    ['Appartenenze aperte', r.appartenenze_aperte.length],
    ['Appartenenze chiuse', r.appartenenze_chiuse.length],
    ['Correzioni recepite da BuonaStrada', r.correzioni_recepite?.length ?? 0],
    ["Iscrizioni dall'app ora in BuonaStrada", r.iscrizioni_recepite?.length ?? 0],
    ['Rientri dopo l’archiviazione', r.rientri?.length ?? 0],
  ] as const
})

function scegli(evento: Event) {
  file.value = (evento.target as HTMLInputElement).files?.[0] ?? null
  esito.value = null
}

async function anteprima() {
  if (!file.value) return
  esito.value = (await esegui(() => api.caricaExport(file.value!, aggiornatoAl.value))) ?? null
  scelte.value = Object.fromEntries(
    (esito.value?.riepilogo.differenze ?? [])
      .filter((d) => d.chiave && d.proposta)
      .map((d) => [d.chiave!, d.proposta!]),
  )
}

async function applica() {
  if (!esito.value) return
  const id = esito.value.id
  esito.value = (await esegui(() => api.applicaImportazione(id, scelte.value))) ?? esito.value
}

const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
</script>

<template>
  <section>
    <h1 class="h4 mb-5">Importa da BuonaStrada</h1>
    <p class="small fg-2">
      Su BuonaStrada: <em>Ricerca soci</em> → esporta in CSV. Il file resta riservato: lo vede solo
      chi può importare.
    </p>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <div class="row g-3 mb-5 align-items-end">
      <div class="col-12 md:col-6">
        <label class="form-label small" for="file-export">Export "Ricerca soci"</label>
        <input
          id="file-export"
          class="form-control"
          type="file"
          accept=".csv,text/csv"
          @change="scegli"
        />
      </div>
      <div class="col-7 md:col-3">
        <label class="form-label small" for="aggiornato-al"
          >Dati di BuonaStrada aggiornati al</label
        >
        <input
          id="aggiornato-al"
          v-model="aggiornatoAl"
          class="form-control"
          type="date"
          :max="oggi"
          required
          @change="esito = null"
        />
      </div>
      <div class="col-5 md:col-3">
        <button
          class="btn btn-solid theme-primary w-100"
          :disabled="!file || !aggiornatoAl || inCorso"
          @click="anteprima"
        >
          Anteprima
        </button>
      </div>
      <p class="form-text col-12 mb-0">
        La data serve a proporre il dato più recente quando l'app e BuonaStrada non coincidono.
      </p>
    </div>

    <template v-if="esito">
      <div
        class="alert"
        :class="esito.stato === 'APPLICATA' ? 'theme-success' : 'theme-info'"
        role="status"
      >
        {{
          esito.stato === 'APPLICATA'
            ? 'Importazione applicata.'
            : 'Anteprima: nessun dato è stato ancora salvato.'
        }}
      </div>
      <table class="table table-sm w-auto">
        <tbody>
          <tr v-for="[etichetta, n] in conteggi" :key="etichetta">
            <th scope="row" class="fw-normal">{{ etichetta }}</th>
            <td class="text-end">{{ n }}</td>
          </tr>
        </tbody>
      </table>

      <template v-if="esito.riepilogo.differenze.length">
        <h2 class="h6">L'app e BuonaStrada non coincidono</h2>
        <p v-if="esito.stato === 'ANTEPRIMA'" class="small fg-2">
          Scegli quale dato tenere. È proposto il più recente: la modifica fatta nell'app o i dati
          di BuonaStrada aggiornati al
          {{ esito.dati_aggiornati_al ? data(esito.dati_aggiornati_al) : '—' }}. Se vince l'app,
          ricordati di correggere BuonaStrada.
        </p>
        <ul class="list-group mb-5">
          <li
            v-for="(d, i) in esito.riepilogo.differenze"
            :key="d.chiave || i"
            class="list-group-item small"
          >
            <div>
              <strong>{{ d.persona }}</strong> — {{ d.campo }}
              <span v-if="d.data_app" class="fg-2">
                (cambiato nell'app il {{ data(d.data_app) }})</span
              >
            </div>
            <fieldset v-if="esito.stato === 'ANTEPRIMA' && d.chiave" class="d-flex flex-wrap gap-5">
              <legend class="visually-hidden">Quale dato tenere per {{ d.persona }}</legend>
              <div v-for="lato in ['APP', 'BUONASTRADA'] as const" :key="lato" class="form-field">
                <input
                  :id="`scelta-${i}-${lato}`"
                  v-model="scelte[d.chiave]"
                  type="radio"
                  class="radio"
                  :name="`scelta-${i}`"
                  :value="lato"
                />
                <label :for="`scelta-${i}-${lato}`">
                  {{ lato === 'APP' ? 'App' : 'BuonaStrada' }}: «{{
                    valoreLeggibile(lato === 'APP' ? d.valore_app : d.valore_buonastrada)
                  }}»
                  <span v-if="d.proposta === lato" class="badge theme-info ms-1">più recente</span>
                </label>
              </div>
            </fieldset>
            <div v-else>
              App «{{ valoreLeggibile(d.valore_app) }}», BuonaStrada «{{
                valoreLeggibile(d.valore_buonastrada)
              }}»: {{ d.motivo }}
            </div>
          </li>
        </ul>
      </template>

      <template v-if="esito.riepilogo.avvisi.length">
        <h2 class="h6">Avvisi</h2>
        <ul class="small">
          <li v-for="(a, i) in esito.riepilogo.avvisi" :key="i">
            <span v-if="a.riga">Riga {{ a.riga }}: </span>{{ a.messaggio }}
          </li>
        </ul>
      </template>

      <button
        v-if="esito.stato === 'ANTEPRIMA'"
        class="btn btn-solid theme-primary"
        :disabled="inCorso"
        @click="applica"
      >
        Applica l'importazione
      </button>
    </template>
  </section>
</template>
