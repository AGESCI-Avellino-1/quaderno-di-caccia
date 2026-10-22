<script setup lang="ts">
import { RouterLink } from 'vue-router'

import { useRete } from '@/composables/useRete'
import { useSessioneStore } from '@/stores/sessione'

const { online, inCoda, conErrori } = useRete()
const sessione = useSessioneStore()
</script>

<template>
  <div
    v-if="!online || inCoda > 0 || conErrori > 0"
    class="qdc-barra-offline small py-1"
    role="status"
  >
    <div class="container d-flex flex-wrap gap-3">
      <span v-if="!online">
        Sei offline<template v-if="sessione.profiloDel">
          · dati del {{ new Date(sessione.profiloDel).toLocaleString('it-IT') }}</template
        >
      </span>
      <RouterLink v-if="inCoda > 0" to="/modifiche"> {{ inCoda }} modifiche da inviare </RouterLink>
      <RouterLink v-if="conErrori > 0" to="/modifiche" class="fw-bold">
        {{ conErrori }} modifiche da controllare
      </RouterLink>
    </div>
  </div>
</template>
