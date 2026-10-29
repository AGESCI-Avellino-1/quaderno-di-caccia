<script setup lang="ts">
// Service worker in "prompt" mode: a new version is installed only when the user agrees,
// so nobody loses a half-filled form at camp.
import { useRegisterSW } from 'virtual:pwa-register/vue'

const { needRefresh, updateServiceWorker } = useRegisterSW()
</script>

<template>
  <div
    v-if="needRefresh"
    class="toast show position-fixed bottom-0 end-0 m-5"
    role="alert"
    aria-live="assertive"
  >
    <div class="toast-body d-flex align-items-center gap-3">
      <span>È disponibile una nuova versione.</span>
      <button
        type="button"
        class="btn btn-sm btn-solid theme-primary"
        @click="updateServiceWorker(true)"
      >
        Aggiorna
      </button>
      <button type="button" class="btn btn-sm btn-link" @click="needRefresh = false">
        Più tardi
      </button>
    </div>
  </div>
</template>
