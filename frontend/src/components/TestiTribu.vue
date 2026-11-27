<script setup lang="ts">
import { ref, watch } from 'vue'

import { api, type Impostazioni } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// «La mia tribù» (DEC-416): the description at the top of the page, with the base text
// one click away. The capigruppo. The totem ceremony is an entry of the book of ceremonies
// (DEC-437).
const props = defineProps<{ impostazioni: Impostazioni }>()
const emit = defineEmits<{ aggiornate: [Impostazioni] }>()
const { errore, inCorso, esegui } = useErrore()

const descrizione = ref('')
const salvato = ref(false)
watch(
  () => props.impostazioni,
  (imp) => {
    descrizione.value = imp.descrizione_tribu ?? ''
  },
  { immediate: true },
)

function testoDiBase() {
  descrizione.value = props.impostazioni.descrizione_tribu_base ?? ''
}

async function salva() {
  salvato.value = false
  const nuove = await esegui(() => api.salvaTribu(descrizione.value))
  if (nuove) {
    salvato.value = true
    emit('aggiornate', nuove)
  }
}
</script>

<template>
  <section id="tribu" class="mb-7" data-totem>
    <h2 class="h5">La mia tribù</h2>
    <p class="small fg-2">
      La descrizione in cima alla pagina dei nomi di totem, che leggono i capi e chi ha un nome di
      totem; una riga vuota separa i paragrafi. La cerimonia del totem è nel libro delle cerimonie e
      tradizioni.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="salvato" class="alert theme-success small" role="status">Descrizione salvata.</div>
    <form class="card card-body" @submit.prevent="salva">
      <label class="form-label small" for="tribu-descrizione">Descrizione della tribù</label>
      <textarea
        id="tribu-descrizione"
        v-model="descrizione"
        class="form-control mb-3"
        rows="6"
        maxlength="2000"
      />
      <div class="d-flex flex-wrap gap-3">
        <button class="btn btn-solid theme-primary" :disabled="inCorso">Salva</button>
        <button type="button" class="btn btn-link" @click="testoDiBase">
          Torna alla descrizione di base
        </button>
      </div>
    </form>
  </section>
</template>
