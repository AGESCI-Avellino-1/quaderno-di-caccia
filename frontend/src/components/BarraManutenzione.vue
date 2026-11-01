<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import { useSessioneStore } from '@/stores/sessione'
import { useSitoStore } from '@/stores/sito'

// Maintenance (DEC-268): the technical administrator knows it is on and where to switch it
// off; anyone else sees the message (the pages they may still open: login, privacy).
const sito = useSitoStore()
const sessione = useSessioneStore()
const amministratore = computed(() => !!sessione.profilo?.amministratore_tecnico)
</script>

<template>
  <div
    v-if="sito.sito.manutenzione"
    class="alert theme-warning rounded-0 mb-0 small justify-content-center"
    role="status"
  >
    <div v-if="amministratore">
      <strong>Manutenzione in corso:</strong> entrano solo gli amministratori tecnici. La togli da
      <RouterLink to="/impostazioni">Impostazioni</RouterLink>.
    </div>
    <div v-else><strong>Manutenzione in corso.</strong> {{ sito.sito.messaggio_manutenzione }}</div>
  </div>
</template>
