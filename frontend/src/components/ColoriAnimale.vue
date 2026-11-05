<script setup lang="ts">
import type { ColoreAnimale } from '@/api/qdc'

// The colours of a patrol, drawn and named, with their meaning (DEC-353). The codes come
// from the catalog: they are the data here, not a colour of the interface.
defineProps<{ colori: ColoreAnimale[] }>()
</script>

<template>
  <ul v-if="colori.length" class="list-unstyled small mb-0">
    <li v-for="c in colori" :key="c.nome" class="d-flex align-items-baseline gap-1">
      <span class="campione" :style="{ backgroundColor: c.codice }" aria-hidden="true"></span>
      <span>
        <strong>{{ c.nome }}</strong
        ><template v-if="c.significato">: {{ c.significato }}</template>
      </span>
    </li>
  </ul>
</template>

<style scoped>
.campione {
  display: inline-block;
  flex: none;
  width: 0.85rem;
  height: 0.85rem;
  /* The text's colour: a white patrol colour must show on a white page. */
  border: 1px solid currentColor;
  border-radius: 50%;
}
</style>
