<script setup lang="ts">
import { computed, onBeforeUnmount, watch } from 'vue'

import { useSessioneStore } from '@/stores/sessione'

// Always visible while a capo uses the app as another user: who, until when, the way
// back. The server ends it after 30 minutes; the page reloads then.
const sessione = useSessioneStore()
const impersonazione = computed(() => sessione.profilo?.impersonazione ?? null)
let timer: ReturnType<typeof setTimeout> | undefined

watch(
  impersonazione,
  (attuale) => {
    clearTimeout(timer)
    if (!attuale) return
    const mancano = new Date(attuale.scade_il).getTime() - Date.now()
    timer = setTimeout(() => window.location.assign('/'), Math.max(mancano, 0) + 1000)
  },
  { immediate: true },
)
onBeforeUnmount(() => clearTimeout(timer))

const ora = (iso: string) =>
  new Date(iso).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
</script>

<template>
  <div v-if="impersonazione" class="alert theme-warning rounded-0 mb-0 py-3" role="status">
    <div class="container d-flex flex-wrap align-items-center justify-content-between gap-3">
      <span>
        Stai usando l'app al posto di <strong>{{ impersonazione.impersonato }}</strong> ({{
          impersonazione.email
        }}) fino alle {{ ora(impersonazione.scade_il) }}. Quello che fai resta registrato a tuo
        nome.
      </span>
      <button type="button" class="btn btn-sm btn-solid theme-primary" @click="sessione.tornaATe">
        Torna a te
      </button>
    </div>
  </div>
</template>
