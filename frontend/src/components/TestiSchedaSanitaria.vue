<script setup lang="ts">
import { ref, watch } from 'vue'

import { api, type Impostazioni } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The declaration and the consent printed on the group's medical form (DEC-289): the
// capigruppo change them; the model's text is the base, one click away.
const props = defineProps<{ impostazioni: Impostazioni }>()
const emit = defineEmits<{ aggiornate: [Impostazioni] }>()
const { errore, inCorso, esegui } = useErrore()

const dichiarazione = ref('')
const consenso = ref('')
const salvati = ref(false)
watch(
  () => props.impostazioni,
  (imp) => {
    dichiarazione.value = imp.scheda_dichiarazione ?? ''
    consenso.value = imp.scheda_consenso ?? ''
  },
  { immediate: true },
)

function testoDiBase() {
  dichiarazione.value = props.impostazioni.scheda_dichiarazione_base ?? ''
  consenso.value = props.impostazioni.scheda_consenso_base ?? ''
}

async function salva() {
  salvati.value = false
  const nuove = await esegui(() =>
    api.salvaTestiScheda({ dichiarazione: dichiarazione.value, consenso: consenso.value }),
  )
  if (nuove) {
    salvati.value = true
    emit('aggiornate', nuove)
  }
}
</script>

<template>
  <section class="mb-7">
    <h2 class="h5">Testi della scheda sanitaria</h2>
    <p class="small fg-2">
      La dichiarazione e il consenso stampati sulla scheda sanitaria, sopra le firme.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="salvati" class="alert theme-success small" role="status">Testi salvati.</div>
    <form class="card card-body" @submit.prevent="salva">
      <label class="form-label small" for="scheda-dichiarazione">Dichiarazione</label>
      <textarea
        id="scheda-dichiarazione"
        v-model="dichiarazione"
        class="form-control mb-3"
        rows="3"
        maxlength="2000"
      />
      <label class="form-label small" for="scheda-consenso">Consenso al trattamento dei dati</label>
      <textarea
        id="scheda-consenso"
        v-model="consenso"
        class="form-control mb-3"
        rows="3"
        maxlength="2000"
      />
      <div class="d-flex flex-wrap gap-3">
        <button class="btn btn-solid theme-primary" :disabled="inCorso">Salva</button>
        <button type="button" class="btn btn-link" @click="testoDiBase">
          Torna al testo di base
        </button>
      </div>
    </form>
  </section>
</template>
