<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

import type { AnimaleBreve } from '@/api/qdc'

// The image next to a patrol's name (DEC-353). A symbol of the catalog takes the theme's
// colour; an uploaded file is only ever an image, never put inside the page (DEC-354).
const props = defineProps<{
  animale?: Pick<AnimaleBreve, 'nome' | 'immagine' | 'simbolo'> | null
  /** Larger, in the list and on the patrol's page. */
  grande?: boolean
  /** In a long list: the file is asked for only when it comes into view. */
  pigra?: boolean
}>()

const contenitore = ref<HTMLElement | null>(null)
const visibile = ref(!props.pigra || typeof IntersectionObserver === 'undefined')
let osservatore: IntersectionObserver | null = null

onMounted(() => {
  if (visibile.value || !contenitore.value) return
  osservatore = new IntersectionObserver(([voce]) => {
    if (!voce.isIntersecting) return
    visibile.value = true
    osservatore?.disconnect()
  })
  osservatore.observe(contenitore.value)
})
onBeforeUnmount(() => osservatore?.disconnect())
</script>

<template>
  <span
    v-if="animale?.immagine"
    ref="contenitore"
    class="immagine-animale"
    :class="{ grande }"
    role="img"
    :aria-label="animale.nome"
  >
    <template v-if="visibile">
      <svg v-if="animale.simbolo" aria-hidden="true">
        <use :href="`${animale.immagine}#${animale.simbolo}`"></use>
      </svg>
      <img v-else :src="animale.immagine" alt="" />
    </template>
  </span>
</template>

<style scoped>
.immagine-animale {
  display: inline-block;
  flex: none;
  width: 1.75rem;
  height: 1.75rem;
  color: var(--ag-primary);
  vertical-align: middle;
}
.immagine-animale.grande {
  width: 4rem;
  height: 4rem;
}
.immagine-animale svg,
.immagine-animale img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
}
</style>
