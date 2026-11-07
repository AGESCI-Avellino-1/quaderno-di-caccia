<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import VociHome from '@/components/VociHome.vue'
import { useNomePagina } from '@/composables/useNomePagina'
import { gruppiMenu } from '@/navigazione/menu'
import { useNavigazioneStore } from '@/stores/navigazione'
import { useSessioneStore } from '@/stores/sessione'

// A group of the menu on a page of its own, only its entries, where the breadcrumb leads
// (DEC-382). The same list as the menu: it hides, the server decides (DEC-09).
const props = defineProps<{ chiave: string }>()

const sessione = useSessioneStore()
const navigazione = useNavigazioneStore()
const gruppo = computed(() => {
  const p = sessione.profilo
  return p ? gruppiMenu(p, navigazione.contatori).find((g) => g.chiave === props.chiave) : undefined
})
useNomePagina(() => gruppo.value?.titolo)
</script>

<template>
  <section>
    <template v-if="gruppo">
      <h1 class="h4 mb-5">{{ gruppo.titolo }}</h1>
      <VociHome :voci="gruppo.voci" />
    </template>
    <p v-else class="fg-2">
      Questa sezione non è disponibile. <RouterLink to="/">Torna alla Home</RouterLink>
    </p>
  </section>
</template>
