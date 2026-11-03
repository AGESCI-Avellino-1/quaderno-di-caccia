<script setup lang="ts">
import { computed } from 'vue'

import { moduliQr, percorsoQr } from '@/navigazione/condividi'

// A QR code drawn on the device (DEC-304): black on white whatever the theme, so phones
// read it; `etichetta` says what it opens, for screen readers.
const props = defineProps<{ valore: string; etichetta: string }>()

const moduli = computed(() => moduliQr(props.valore))
const percorso = computed(() => percorsoQr(moduli.value))
</script>

<template>
  <svg
    class="qdc-qr"
    :viewBox="`0 0 ${moduli.length} ${moduli.length}`"
    role="img"
    :aria-label="etichetta"
    shape-rendering="crispEdges"
  >
    <rect :width="moduli.length" :height="moduli.length" fill="#fff" />
    <path :d="percorso" fill="#000" />
  </svg>
</template>

<style scoped>
.qdc-qr {
  display: block;
  width: 100%;
  max-width: 18rem;
  height: auto;
  margin-inline: auto;
}
</style>
