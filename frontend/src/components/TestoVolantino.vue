<script setup lang="ts">
import { ref, watch } from 'vue'

import { api, type Impostazioni, volantinoListaAttesa as volantino } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The text of the waiting list flyer (DEC-304): the capigruppo change it; the base text
// is one click away. [Gruppo] and [Sigla gruppo] are filled in on the flyer.
const props = defineProps<{ impostazioni: Impostazioni }>()
const emit = defineEmits<{ aggiornate: [Impostazioni] }>()
const { errore, inCorso, esegui } = useErrore()

const testo = ref('')
const salvato = ref(false)
watch(
  () => props.impostazioni,
  (imp) => {
    testo.value = imp.volantino_attesa ?? ''
  },
  { immediate: true },
)

function testoDiBase() {
  testo.value = props.impostazioni.volantino_attesa_base ?? ''
}

async function salva() {
  salvato.value = false
  const nuove = await esegui(() => api.salvaTestoVolantino(testo.value))
  if (nuove) {
    salvato.value = true
    emit('aggiornate', nuove)
  }
}
</script>

<template>
  <section id="volantino" class="mb-7">
    <h2 class="h5">Volantino della lista d'attesa</h2>
    <p class="small fg-2">
      Il testo stampato sul volantino di «Invita nel gruppo», sopra il QR code. Puoi usare [Gruppo]
      e [Sigla gruppo]; una riga vuota separa i paragrafi.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="salvato" class="alert theme-success small" role="status">Testo salvato.</div>
    <form class="card card-body" @submit.prevent="salva">
      <label class="form-label small" for="volantino-testo">Testo del volantino</label>
      <textarea
        id="volantino-testo"
        v-model="testo"
        class="form-control mb-3"
        rows="5"
        maxlength="1000"
      />
      <div class="d-flex flex-wrap gap-3">
        <button class="btn btn-solid theme-primary" :disabled="inCorso">Salva</button>
        <button type="button" class="btn btn-link" @click="testoDiBase">
          Torna al testo di base
        </button>
        <a :href="volantino" download class="btn btn-link">Scarica il volantino</a>
      </div>
    </form>
  </section>
</template>
