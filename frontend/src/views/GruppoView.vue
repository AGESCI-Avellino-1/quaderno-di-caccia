<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, type IncarichiGruppo } from '@/api/qdc'
import CopiaLocale from '@/components/CopiaLocale.vue'
import ElencoIncarichi from '@/components/ElencoIncarichi.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'

// Capigruppo (diarchy, DEC-18) and group treasurers. Appointed by the capigruppo in
// office; by the technical administrator only when there is none (first start).
const { errore, esegui } = useErrore()
const dati = ref<IncarichiGruppo | null>(null)
const copiaDel = ref<string | null>(null)

async function carica() {
  const letto = await esegui(() => leggiConCache('gruppo:incarichi', api.incarichiDiGruppo))
  dati.value = letto?.dati ?? null
  copiaDel.value = letto?.copiaDel ?? null
}
onMounted(carica)

const capi = () => api.capi()
</script>

<template>
  <section>
    <h1 class="h4 mb-3">Capigruppo e tesorieri di gruppo</h1>
    <div v-if="errore" class="alert alert-danger" role="alert">{{ errore }}</div>
    <CopiaLocale :del="copiaDel" />
    <div v-if="dati" class="card card-body">
      <ElencoIncarichi
        :incarichi="dati.incarichi"
        :nomina="dati.nomina"
        :dove="{}"
        :candidati="capi"
        vuoto="Nessun capogruppo registrato."
        @cambiato="carica"
      />
    </div>
  </section>
</template>
