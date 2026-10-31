<script setup lang="ts">
import { useSitoStore } from '@/stores/sito'

// Email test mode (DEC-249): everyone, the login page included, knows that emails are
// not delivered. No link to Mailpit here: only the technical administrator uses it.
const sito = useSitoStore()
</script>

<template>
  <div
    v-if="sito.sito.email_di_prova"
    class="alert theme-warning rounded-0 mb-0 small justify-content-center"
    role="status"
  >
    <div>
      <strong>Modalità di prova:</strong> le email non vengono consegnate. Codici di accesso, inviti
      e avvisi non arrivano a nessuno.
    </div>
  </div>
</template>
