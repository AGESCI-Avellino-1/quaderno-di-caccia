<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

import { inviaCoda } from '@/offline/outbox'
import { useSitoStore } from '@/stores/sito'

// Shown instead of the page while the app is in maintenance (DEC-268). Asks again every
// minute: when it is over the page comes back by itself. No "Esci" here: it would wipe the
// changes still waiting on this phone.
const sito = useSitoStore()
const controllo = ref(false)
let timer: ReturnType<typeof setInterval> | undefined

async function riprova() {
  controllo.value = true
  try {
    await sito.carica()
    if (!sito.sito.manutenzione) void inviaCoda()
  } finally {
    controllo.value = false
  }
}

onMounted(() => {
  timer = setInterval(() => void riprova(), 60_000)
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <section class="text-center py-12 mx-auto" style="max-width: 36rem">
    <h1 class="h4">L'app è in manutenzione</h1>
    <p class="my-5">{{ sito.sito.messaggio_manutenzione }}</p>
    <p class="fg-2 small">
      Le modifiche che hai fatto senza rete restano su questo telefono e partono da sole quando la
      manutenzione finisce. Questa pagina si aggiorna da sola ogni minuto.
    </p>
    <button
      type="button"
      class="btn btn-solid theme-primary"
      :disabled="controllo"
      @click="riprova"
    >
      Riprova ora
    </button>
  </section>
</template>
