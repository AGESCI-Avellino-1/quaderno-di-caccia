<script setup lang="ts" generic="V">
// One choice among a few, as Bootstrap 6 chips (DEC-298): all of them in sight and one
// tap to choose, instead of a menu. A radio group for screen readers.
defineProps<{ scelte: { valore: V; nome: string }[]; etichetta: string; disabilitata?: boolean }>()
const valore = defineModel<V>({ required: true })
</script>

<template>
  <div class="d-flex flex-wrap gap-1" role="radiogroup" :aria-label="etichetta">
    <button
      v-for="s in scelte"
      :key="String(s.valore)"
      type="button"
      role="radio"
      class="chip theme-primary"
      :class="{ active: s.valore === valore }"
      :aria-checked="s.valore === valore"
      :disabled="disabilitata"
      @click="valore = s.valore"
    >
      {{ s.nome }}
    </button>
  </div>
</template>
