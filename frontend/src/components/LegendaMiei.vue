<script setup lang="ts">
import { computed } from 'vue'

import { conAltri } from '@/eventi/miei'

// Where one's own events are mixed with others (DEC-432), what tells them apart.
const props = defineProps<{ eventi: { mio?: boolean }[]; mese?: boolean }>()
const serve = computed(() => conAltri(props.eventi))
</script>

<template>
  <p v-if="serve" class="d-flex flex-wrap align-items-center gap-3 small fg-2 mb-3">
    <template v-if="mese">
      <span><span class="qdc-evento-mio px-1 rounded">Titolo</span> i miei eventi</span>
      <span><span class="qdc-evento-altro px-1 rounded">Titolo</span> gli altri</span>
    </template>
    <span v-else class="qdc-riga-mia px-3">Con la barra i miei, senza gli altri</span>
  </p>
</template>
