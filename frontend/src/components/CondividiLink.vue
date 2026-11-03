<script setup lang="ts">
import { ref } from 'vue'

import Icona from '@/components/Icona.vue'

// Share a link (DEC-304): the phone's own share sheet where there is one (WhatsApp,
// email…), and always «Copia il link».
const props = defineProps<{ url: string; titolo: string; testo?: string }>()

const puoCondividere = typeof navigator !== 'undefined' && typeof navigator.share === 'function'
const copiato = ref(false)
const errore = ref('')

async function condividi() {
  errore.value = ''
  try {
    await navigator.share({ title: props.titolo, text: props.testo, url: props.url })
  } catch (e) {
    // Closing the share sheet is not an error.
    if ((e as DOMException)?.name !== 'AbortError')
      errore.value = 'Non sono riuscito a condividere.'
  }
}

async function copia() {
  errore.value = ''
  copiato.value = false
  try {
    await navigator.clipboard.writeText(props.url)
    copiato.value = true
  } catch {
    errore.value = 'Non sono riuscito a copiare il link: selezionalo e copialo a mano.'
  }
}
</script>

<template>
  <div>
    <div class="d-flex flex-wrap gap-3">
      <button
        v-if="puoCondividere"
        type="button"
        class="btn btn-solid theme-primary"
        @click="condividi"
      >
        <Icona nome="share" /> Condividi
      </button>
      <button type="button" class="btn btn-outline theme-primary" @click="copia">
        <Icona nome="clipboard" /> Copia il link
      </button>
    </div>
    <div v-if="copiato" class="alert theme-success small mt-3 mb-0" role="status">
      Link copiato.
    </div>
    <div v-if="errore" class="alert theme-danger small mt-3 mb-0" role="alert">{{ errore }}</div>
  </div>
</template>
