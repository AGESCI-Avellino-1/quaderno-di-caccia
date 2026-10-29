<script setup lang="ts">
import { computed, ref } from 'vue'

import { api, type Calendario } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The personal calendar feed (DEC-79): a secret address to add once to Google Calendar
// or the iPhone Calendar, which then stay up to date by themselves. It holds only
// titles, dates and places. Online only.
const { errore, inCorso, esegui } = useErrore()
const calendario = ref<Calendario | null>(null)
const copiato = ref<string | null>(null)
const aperto = ref(false)

async function mostra() {
  aperto.value = true
  calendario.value = (await esegui(() => api.calendario())) ?? null
}

async function rigenera() {
  copiato.value = null
  calendario.value = (await esegui(() => api.rigeneraCalendario())) ?? calendario.value
}

async function copia(url: string) {
  try {
    await navigator.clipboard.writeText(url)
    copiato.value = url
  } catch {
    copiato.value = null
  }
}

const webcal = (url: string) => url.replace(/^https?:/, 'webcal:')
// A capo picks one of three views; everyone else has one address.
const indirizzi = computed(() =>
  calendario.value
    ? calendario.value.viste.length
      ? calendario.value.viste
      : [{ vista: '', nome: '', url: calendario.value.url }]
    : [],
)
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
      <template v-if="calendario">
        <p class="small mb-3">
          Link personale: non condividerlo, chi lo ha vede i tuoi eventi.
          <template v-if="calendario.viste.length">
            Scegli quanti eventi vedere: puoi aggiungerne anche più di uno.
          </template>
        </p>
        <div v-for="i in indirizzi" :key="i.vista" class="mb-3">
          <label v-if="i.nome" class="form-label small" :for="`calendario-${i.vista}`">{{
            i.nome
          }}</label>
          <input
            :id="`calendario-${i.vista || 'mio'}`"
            :value="i.url"
            class="form-control form-control-sm mb-1"
            :aria-label="i.nome || 'Link del calendario'"
            readonly
          />
          <div class="d-flex flex-wrap align-items-center gap-3">
            <button type="button" class="btn btn-sm btn-solid theme-primary" @click="copia(i.url)">
              Copia
            </button>
            <a :href="webcal(i.url)" class="btn btn-sm btn-outline theme-primary">
              Apri nel Calendario
            </a>
            <span v-if="copiato === i.url" class="small fg-success">Copiato.</span>
          </div>
        </div>
        <button
          type="button"
          class="btn btn-sm btn-link align-self-start"
          :disabled="inCorso"
          @click="rigenera"
        >
          Crea un link nuovo
        </button>
        <p class="form-text mb-0">
          Su Google Calendar: Altri calendari, Da URL, incolla il link. Se l'hai condiviso per
          sbaglio, crea un link nuovo: il vecchio smette di funzionare.
        </p>
      </template>
    </template>
  </section>
</template>
