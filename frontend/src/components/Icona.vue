<script setup lang="ts">
import { ICONE, type NomeIcona } from '@/navigazione/icone'

// One icon, decorative: the text next to it says what it is.
defineProps<{ nome: NomeIcona }>()
</script>

<template>
  <!-- eslint-disable-next-line vue/no-v-html -- SVG files of the bundled icon set -->
  <span class="qdc-icona" aria-hidden="true" v-html="ICONE[nome]"></span>
</template>
