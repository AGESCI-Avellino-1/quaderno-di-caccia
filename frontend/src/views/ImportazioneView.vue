<script setup lang="ts">
import { computed, ref } from 'vue'

import { api, type EsitoImportazione } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Two steps (DEC-33): the file is first read in preview, nothing is saved; the capogruppo
// checks the summary and only then applies it.
const { errore, inCorso, esegui } = useErrore()
const file = ref<File | null>(null)
const esito = ref<EsitoImportazione | null>(null)

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
  ] as const
})

function scegli(evento: Event) {
  file.value = (evento.target as HTMLInputElement).files?.[0] ?? null
  esito.value = null
}

async function anteprima() {
  if (file.value) esito.value = (await esegui(() => api.caricaExport(file.value!))) ?? null
}

async function applica() {
  if (esito.value)
    esito.value = (await esegui(() => api.applicaImportazione(esito.value!.id))) ?? esito.value
}
</script>

<template>
  <section>
    <h1 class="h4 mb-5">Importa da BuonaStrada</h1>
    <p class="small fg-2">
      Su BuonaStrada: <em>Ricerca soci</em> → esporta in CSV. Il file resta riservato: lo vede solo
      chi può importare.
    </p>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <div class="d-flex flex-wrap gap-3 mb-5">
      <input class="form-control" type="file" accept=".csv,text/csv" @change="scegli" />
      <button class="btn btn-solid theme-primary" :disabled="!file || inCorso" @click="anteprima">
        Anteprima
      </button>
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
        <h2 class="h6">Differenze da verificare</h2>
        <p class="small fg-2">
          Dati corretti nell'app e diversi da BuonaStrada: l'app non li sovrascrive. Vanno allineati
          su BuonaStrada.
        </p>
        <ul class="small">
          <li v-for="(d, i) in esito.riepilogo.differenze" :key="i">
            <strong>{{ d.persona }}</strong> — {{ d.campo }}: app «{{ d.valore_app }}», BuonaStrada
            «{{ d.valore_buonastrada }}» ({{ d.motivo }})
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
