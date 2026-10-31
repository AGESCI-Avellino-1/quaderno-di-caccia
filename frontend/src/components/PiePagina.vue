<script setup lang="ts">
import { RouterLink } from 'vue-router'

import { useSitoStore } from '@/stores/sito'

// The group's line (optional, with placeholders) above the fixed one (DEC-247).
const sito = useSitoStore()
</script>

<template>
  <footer class="qdc-piede small fg-2 text-center py-3">
    <div class="container">
      <p v-if="sito.rigaPiede" class="mb-1">{{ sito.rigaPiede }}</p>
      <p class="mb-0">
        <RouterLink to="/privacy">Privacy policy</RouterLink> ·
        <RouterLink to="/termini">Termini e condizioni</RouterLink> · Sviluppato da
        <a href="https://bruand81.it" target="_blank" rel="noopener">Andrea Bruno</a> e distribuito
        con licenza MIT
      </p>
    </div>
  </footer>
</template>
