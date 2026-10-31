<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { useSitoStore } from '@/stores/sito'

// The cookie notice (DEC-266): informational only, the app uses technical cookies alone.
// "Ho capito" is remembered in the browser, the one exception to the rule of keeping
// nothing in clear on the device (no personal data, only the policy's date); it shows
// again when the privacy policy changes.
const CHIAVE = 'qdc-cookie-informativa'
const sito = useSitoStore()
const versione = computed(() => sito.sito.privacy_aggiornata_il || 'base')

function letta(): string | null {
  try {
    return localStorage.getItem(CHIAVE)
  } catch {
    return null
  }
}

const vista = ref(letta())
const mostra = computed(() => vista.value !== versione.value)

function hoCapito() {
  vista.value = versione.value
  try {
    localStorage.setItem(CHIAVE, versione.value)
  } catch {
    // Private browsing: it shows again next time.
  }
}
</script>

<template>
  <div v-if="mostra" class="qdc-banner-cookie shadow" role="region" aria-label="Cookie">
    <div class="container d-flex flex-wrap align-items-center gap-3 py-3">
      <p class="small mb-0 flex-grow-1">
        Questa app usa solo cookie tecnici, necessari per farla funzionare: nessuna statistica,
        nessuna pubblicità. Dettagli nella
        <RouterLink to="/privacy">privacy policy</RouterLink>.
      </p>
      <button type="button" class="btn btn-sm btn-solid theme-primary" @click="hoCapito">
        Ho capito
      </button>
    </div>
  </div>
</template>
