<script setup lang="ts">
import { computed, ref } from 'vue'

import { api, type VoceLibro } from '@/api/qdc'
import SceltaPersone from '@/components/SceltaPersone.vue'
import { opzioniDa, type Opzione } from '@/components/sceltaDaElenco'
import { useErrore } from '@/composables/useErrore'

// The register of an entry of the book (DEC-437): who lived it and when. Every capo and the
// participants read it; who writes the entry marks active ragazzi/e and capi, also for past
// years, and takes someone off.
const props = defineProps<{ voce: VoceLibro }>()
const emit = defineEmits<{ aggiornata: [VoceLibro] }>()
const { errore, inCorso, esegui } = useErrore()

const oggi = () => new Date().toLocaleDateString('sv-SE')
const segnabili = ref<Opzione[]>([])
const scelti = ref<number[]>([])
const giorno = ref(oggi())
const aperto = ref(false)
const data = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString('it-IT')

const giaSegnati = computed(() => new Set(props.voce.partecipanti.map((p) => p.id)))

async function apri() {
  aperto.value = true
  if (!segnabili.value.length)
    segnabili.value = opzioniDa((await esegui(() => api.segnabiliRegistro())) ?? [])
}

async function segna() {
  const voce = await esegui(() => api.segnaPartecipanti(props.voce.id, scelti.value, giorno.value))
  if (!voce) return
  emit('aggiornata', voce)
  scelti.value = []
  aperto.value = false
}

async function togli(persona: number) {
  const voce = await esegui(() => api.togliPartecipante(props.voce.id, persona))
  if (voce) emit('aggiornata', voce)
}
</script>

<template>
  <section class="mb-7" data-registro>
    <h2 class="h5">Chi l'ha vissuta</h2>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <p v-if="!voce.partecipanti.length" class="small fg-2">Nessuno, per ora.</p>
    <ul v-else class="list-group mb-3">
      <li
        v-for="p in voce.partecipanti"
        :key="p.id"
        class="list-group-item d-flex flex-wrap gap-3 align-items-center"
      >
        <span class="flex-grow-1">
          {{ p.cognome }} {{ p.nome }} <span class="small fg-2">{{ p.unita }}</span>
        </span>
        <span class="small">{{ data(p.data) }}</span>
        <button
          v-if="voce.puo_modificare"
          type="button"
          class="btn btn-sm btn-link"
          :aria-label="`Togli ${p.cognome} ${p.nome} dal registro`"
          :disabled="inCorso"
          @click="togli(p.id)"
        >
          Togli
        </button>
      </li>
    </ul>
    <template v-if="voce.puo_modificare">
      <button
        v-if="!aperto"
        type="button"
        class="btn btn-sm btn-outline theme-primary"
        @click="apri"
      >
        Segna chi l'ha vissuta
      </button>
      <form v-else class="card card-body" @submit.prevent="segna">
        <p class="small fg-2">
          Ragazzi, ragazze e capi del gruppo. Puoi segnare anche chi l'ha vissuta negli anni
          passati, con il suo giorno; chi è già segnato prende il giorno nuovo.
          <template v-if="giaSegnati.size">Già segnati: {{ giaSegnati.size }}.</template>
        </p>
        <div class="mb-3">
          <label class="form-label small mb-0" for="registro-giorno">Il giorno</label>
          <input
            id="registro-giorno"
            v-model="giorno"
            type="date"
            class="form-control w-auto"
            :max="oggi()"
            required
          />
        </div>
        <div class="mb-3">
          <SceltaPersone id="registro" v-model="scelti" :opzioni="segnabili" titolo="Da segnare" />
        </div>
        <div class="d-flex flex-wrap gap-3">
          <button class="btn btn-solid theme-primary" :disabled="inCorso || !scelti.length">
            Segna
          </button>
          <button type="button" class="btn btn-link" @click="aperto = false">Annulla</button>
        </div>
      </form>
    </template>
  </section>
</template>
