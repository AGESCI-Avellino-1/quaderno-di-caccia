<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { api, type PiedeEmail } from '@/api/qdc'
import EditorTesto from '@/components/EditorTesto.vue'
import { useErrore } from '@/composables/useErrore'

// The common footer of the emails (DEC-250): formatted, with images (they travel inside
// the email), added to every email whose template keeps it on. The plain-text version is
// derived, or written here.
const { errore, inCorso, esegui } = useErrore()
const piede = ref<PiedeEmail | null>(null)
const html = ref('')
const testo = ref('')
const esito = ref('')
const editor = ref<InstanceType<typeof EditorTesto> | null>(null)

function mostra(dati: PiedeEmail) {
  piede.value = dati
  html.value = dati.html
  testo.value = dati.testo
}

onMounted(async () => {
  const dati = await esegui(() => api.piedeEmail())
  if (dati) mostra(dati)
})

async function salva() {
  esito.value = ''
  const dati = await esegui(() => api.salvaPiedeEmail({ html: html.value, testo: testo.value }))
  if (!dati) return
  mostra(dati)
  esito.value = dati.html
    ? 'Piè di pagina salvato: da ora è nelle email che lo prevedono.'
    : 'Piè di pagina tolto: le email partono senza.'
}
</script>

<template>
  <section>
    <RouterLink to="/impostazioni" class="small">Torna alle impostazioni</RouterLink>
    <h1 class="h4 mb-1 mt-3">Piè di pagina delle email</h1>
    <p class="small fg-2">
      Si aggiunge in fondo a tutte le email, tranne quelle in cui lo togli dal loro modello. Le
      immagini (per esempio il logo) viaggiano dentro l'email. Per toglierlo del tutto, svuota il
      testo e salva.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>
    <form v-if="piede" class="card card-body mb-5" @submit.prevent="salva">
      <EditorTesto ref="editor" v-model="html" etichetta="Piè di pagina" immagini />
      <div class="d-flex flex-wrap gap-1 mt-3">
        <button
          v-for="s in piede.segnaposto"
          :key="s"
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          @click="editor?.inserisci(`[${s}]`)"
        >
          [{{ s }}]
        </button>
      </div>
      <label class="form-label small mt-5 mb-0" for="piede-testo">
        Versione solo testo (facoltativa: se la lasci vuota si ricava da quella formattata)
      </label>
      <textarea
        id="piede-testo"
        v-model="testo"
        rows="4"
        class="form-control"
        :placeholder="piede.anteprima_testo"
      ></textarea>
      <div class="mt-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Salva
        </button>
      </div>
    </form>
    <section v-if="piede?.anteprima_html" class="mb-5">
      <h2 class="h5">Come compare (salvato)</h2>
      <iframe
        class="qdc-anteprima-email card w-100"
        sandbox=""
        :srcdoc="piede.anteprima_html"
        title="Anteprima del piè di pagina"
      ></iframe>
      <details class="small mt-3">
        <summary>Versione solo testo</summary>
        <pre class="mt-1 mb-0 qdc-testo-email">{{ piede.anteprima_testo }}</pre>
      </details>
    </section>
  </section>
</template>
