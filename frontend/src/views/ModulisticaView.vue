<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, fileModulo, type ModuloVuoto } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Blank forms (privacy notice, consents…) the families download, sign and upload with
// the registration. The capigruppo keep them up to date; PDF only. Online only.
const { errore, inCorso, esegui } = useErrore()
const moduli = ref<ModuloVuoto[]>([])
const titolo = ref('')
const file = ref<File | null>(null)

async function carica() {
  moduli.value = (await esegui(() => api.modulistica()))?.moduli ?? []
}
onMounted(carica)

async function aggiungi() {
  if (!file.value) return
  if (!(await esegui(() => api.caricaModulo(titolo.value, file.value!)))) return
  titolo.value = ''
  file.value = null
  await carica()
}

async function attiva(m: ModuloVuoto) {
  if (await esegui(() => api.attivaModulo(m.id, !m.attivo))) await carica()
}
</script>

<template>
  <section>
    <h1 class="h4 mb-1">Modulistica</h1>
    <p class="fg-2 small">
      I moduli vuoti che le famiglie scaricano con l'iscrizione, firmano a mano e ricaricano.
      Aggiornali a ogni anno; quelli disattivati non si vedono più.
    </p>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <form class="card card-body row g-3 mb-5 mx-0" @submit.prevent="aggiungi">
      <div class="col-12 md:col-6">
        <label class="form-label small" for="modulo-titolo">Titolo</label>
        <input
          id="modulo-titolo"
          v-model="titolo"
          class="form-control form-control-sm"
          placeholder="Es. Informativa e consensi 2026/27"
          required
        />
      </div>
      <div class="col-12 md:col-6">
        <label class="form-label small" for="modulo-file">File PDF</label>
        <input
          id="modulo-file"
          class="form-control form-control-sm"
          type="file"
          accept="application/pdf"
          required
          @change="file = ($event.target as HTMLInputElement).files?.[0] ?? null"
        />
      </div>
      <div class="col-12">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Aggiungi
        </button>
      </div>
    </form>
    <p v-if="!inCorso && !moduli.length" class="fg-2">Nessun modulo.</p>
    <ul class="list-group">
      <li
        v-for="m in moduli"
        :key="m.id"
        class="list-group-item d-flex flex-wrap align-items-baseline gap-3"
      >
        <a :href="fileModulo(m.id)" :class="{ 'fg-2': !m.attivo }">{{ m.titolo }}</a>
        <span v-if="!m.attivo" class="badge theme-secondary">disattivato</span>
        <button type="button" class="btn btn-link btn-sm p-0 ms-auto" @click="attiva(m)">
          {{ m.attivo ? 'disattiva' : 'riattiva' }}
        </button>
      </li>
    </ul>
  </section>
</template>
