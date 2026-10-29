<script setup lang="ts">
import { computed, ref } from 'vue'

import { api } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The personal calendar feed (DEC-79): a secret address to add once to Google Calendar
// or the iPhone Calendar, which then stay up to date by themselves. It holds only
// titles, dates and places. Online only.
const { errore, inCorso, esegui } = useErrore()
const url = ref('')
const copiato = ref(false)
const aperto = ref(false)

async function mostra() {
  aperto.value = true
  url.value = (await esegui(() => api.calendario()))?.url ?? ''
}

async function rigenera() {
  copiato.value = false
  url.value = (await esegui(() => api.rigeneraCalendario()))?.url ?? url.value
}

async function copia() {
  try {
    await navigator.clipboard.writeText(url.value)
    copiato.value = true
  } catch {
    copiato.value = false
  }
}

const webcal = computed(() => url.value.replace(/^https?:/, 'webcal:'))
</script>

<template>
  <section class="card card-body mb-5">
    <h2 class="h5 mb-1">Il mio calendario</h2>
    <p class="form-text mb-3">
      Aggiungi una volta i tuoi eventi (e quelli dei tuoi figli) a Google Calendar o al Calendario
      dell'iPhone: si aggiornano da soli. Ci sono solo titolo, date e luogo.
    </p>
    <button
      v-if="!aperto"
      type="button"
      class="btn btn-sm btn-outline theme-primary align-self-start"
      @click="mostra"
    >
      Mostra il link
    </button>
    <template v-else>
      <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
      <template v-if="url">
        <label class="form-label small" for="calendario-url">
          Link personale: non condividerlo, chi lo ha vede i tuoi eventi
        </label>
        <input
          id="calendario-url"
          :value="url"
          class="form-control form-control-sm mb-3"
          readonly
        />
        <div class="d-flex flex-wrap align-items-center gap-3">
          <button type="button" class="btn btn-sm btn-solid theme-primary" @click="copia">
            Copia
          </button>
          <a :href="webcal" class="btn btn-sm btn-outline theme-primary">Apri nel Calendario</a>
          <button type="button" class="btn btn-sm btn-link" :disabled="inCorso" @click="rigenera">
            Crea un link nuovo
          </button>
          <span v-if="copiato" class="small fg-success">Copiato.</span>
        </div>
        <p class="form-text mb-0 mt-3">
          Su Google Calendar: Altri calendari, Da URL, incolla il link. Se l'hai condiviso per
          sbaglio, crea un link nuovo: il vecchio smette di funzionare.
        </p>
      </template>
    </template>
  </section>
</template>
