<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, type Impersonazione } from '@/api/qdc'

// Who used the app in my place, when and why: always visible to the person.
const elenco = ref<Impersonazione[]>([])
onMounted(async () => {
  try {
    elenco.value = await api.impersonazioniMie()
  } catch {
    elenco.value = []
  }
})

const quando = (iso: string) =>
  new Date(iso).toLocaleString('it-IT', { dateStyle: 'short', timeStyle: 'short' })
</script>

<template>
  <section class="mb-5">
    <h2 class="h5">Chi ha usato l'app al tuo posto</h2>
    <p v-if="!elenco.length" class="small fg-2">Nessuno.</p>
    <ul v-else class="list-group small">
      <li v-for="i in elenco" :key="i.id" class="list-group-item">
        <strong>{{ i.impersonatore }}</strong
        >, {{ quando(i.iniziata_il) }} – {{ quando(i.finita_il ?? i.scade_il) }}: {{ i.motivo }}
      </li>
    </ul>
  </section>
</template>
