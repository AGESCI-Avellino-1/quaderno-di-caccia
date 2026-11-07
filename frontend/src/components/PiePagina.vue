<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { aggiornaOra, versioneInferiore } from '@/pwa/aggiornamento'
import { useSitoStore } from '@/stores/sito'

// The group's line (optional, with placeholders) above the fixed one (DEC-247). Above it, for
// everyone and before the login too, the button when the server is ahead of this copy (DEC-380).
const sito = useSitoStore()
const daAggiornare = computed(() => versioneInferiore(__VERSIONE_APP__, sito.versioneServer))
const inCorso = ref(false)

async function aggiorna() {
  inCorso.value = true
  try {
    await aggiornaOra()
  } finally {
    inCorso.value = false
  }
}

// An app left open for days asks again when it comes back in front.
function suVisibilita() {
  if (document.visibilityState === 'visible' && navigator.onLine) void sito.carica()
}
onMounted(() => document.addEventListener('visibilitychange', suVisibilita))
onBeforeUnmount(() => document.removeEventListener('visibilitychange', suVisibilita))
</script>

<template>
  <footer class="qdc-piede small fg-2 text-center py-3">
    <div class="container">
      <p v-if="daAggiornare" class="mb-1">
        È disponibile la versione v{{ sito.versioneServer }}.
        <button
          type="button"
          class="btn btn-sm btn-solid theme-primary"
          :disabled="inCorso"
          @click="aggiorna"
        >
          Aggiorna
        </button>
      </p>
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
