<script setup lang="ts">
import { ref, watch } from 'vue'

import { api, type Impostazioni } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The birthday wishes (DEC-435): the push that whoever has the birthday gets at 8. The
// capigruppo and the technical administrator change it; [Nome] is required.
const props = defineProps<{ impostazioni: Impostazioni }>()
const emit = defineEmits<{ aggiornate: [Impostazioni] }>()
const { errore, inCorso, esegui } = useErrore()

const testo = ref('')
const salvato = ref(false)
watch(
  () => props.impostazioni,
  (imp) => {
    testo.value = imp.testo_auguri ?? ''
  },
  { immediate: true },
)

function testoDiBase() {
  testo.value = props.impostazioni.testo_auguri_base ?? ''
}

async function salva() {
  salvato.value = false
  const nuove = await esegui(() => api.salvaTestoAuguri(testo.value))
  if (nuove) {
    salvato.value = true
    emit('aggiornate', nuove)
  }
}
</script>

<template>
  <section id="auguri" class="mb-7">
    <h2 class="h5">Auguri di compleanno</h2>
    <p class="small fg-2">
      La notifica che riceve alle 8 chi compie gli anni, sul telefono. [Nome] diventa il suo nome di
      battesimo e deve esserci; niente formattazione.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="salvato" class="alert theme-success small" role="status">Testo salvato.</div>
    <form class="card card-body" @submit.prevent="salva">
      <label class="form-label small" for="auguri-testo">Testo degli auguri</label>
      <input id="auguri-testo" v-model="testo" class="form-control mb-3" maxlength="200" required />
      <div class="d-flex flex-wrap gap-3">
        <button class="btn btn-solid theme-primary" :disabled="inCorso">Salva</button>
        <button type="button" class="btn btn-link" @click="testoDiBase">
          Torna al testo di base
        </button>
      </div>
    </form>
  </section>
</template>
