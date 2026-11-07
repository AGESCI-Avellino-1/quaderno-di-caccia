<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, type Cassa, type Unita } from '@/api/qdc'
import SpeseCapi from '@/components/SpeseCapi.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'
import { useSessioneStore } from '@/stores/sessione'

// What this user must still refund, straight from Gestione economica (DEC-379).
const sessione = useSessioneStore()
const { errore, esegui } = useErrore()
const casse = ref<Cassa[]>([])
const unita = ref<Unita[]>([])

async function caricaCasse() {
  casse.value = (await esegui(() => leggiConCache('casse', () => api.casse())))?.dati ?? []
}

onMounted(async () => {
  await caricaCasse()
  unita.value = (await esegui(() => leggiConCache('unita', () => api.unita())))?.dati ?? []
})

async function cambiate() {
  await Promise.all([caricaCasse(), sessione.carica()]) // the balances, the menu counter
}
</script>

<template>
  <section>
    <h1 class="h4 mb-3">Spese da rimborsare</h1>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <SpeseCapi :casse="casse" :unita="unita" solo-da-rimborsare @cambiato="cambiate" />
  </section>
</template>
