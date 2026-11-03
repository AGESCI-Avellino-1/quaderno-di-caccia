<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The ragazzo opens their personal link (DEC-309): birth date, their own email, then the
// app sends there the invitation to create the account.
const props = defineProps<{ codice: string; segreto: string }>()
const { errore, inCorso, esegui } = useErrore()
const nome = ref<string | null>(null)
const dataNascita = ref('')
const email = ref('')
const inviataA = ref<string | null>(null)

onMounted(async () => {
  nome.value =
    (await esegui(() => api.apriLinkAttivazione(props.codice, props.segreto)))?.nome ?? null
})

async function conferma() {
  const fatto = await esegui(() =>
    api.usaLinkAttivazione({
      codice_socio: props.codice,
      segreto: props.segreto,
      data_nascita: dataNascita.value,
      email: email.value.trim(),
    }),
  )
  if (fatto) inviataA.value = fatto.email
}
</script>

<template>
  <section class="mx-auto" style="max-width: 26rem">
    <h1 class="h4 mb-5">Crea il tuo account</h1>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <div v-if="inviataA" class="alert theme-success" role="status">
      <div>
        Ti abbiamo mandato un'email a <strong>{{ inviataA }}</strong
        >: aprila e tocca il link per creare l'account. Non la trovi? Guarda nella posta
        indesiderata, oppure riapri questo link e scrivi l'indirizzo giusto.
      </div>
    </div>
    <form v-else-if="nome" class="vstack gap-3" @submit.prevent="conferma">
      <p>
        Ciao <strong>{{ nome }}</strong
        >, questo è il tuo link per entrare nell'app del gruppo. Prima conferma che sei tu.
      </p>
      <div>
        <label class="form-label" for="attiva-nascita">La tua data di nascita</label>
        <input
          id="attiva-nascita"
          v-model="dataNascita"
          type="date"
          class="form-control"
          required
        />
      </div>
      <div>
        <label class="form-label" for="attiva-email">La tua email</label>
        <input
          id="attiva-email"
          v-model="email"
          type="email"
          class="form-control"
          autocomplete="email"
          required
        />
        <div class="form-text small">
          Deve essere tua, non di un genitore: ti arriva lì il link per creare l'account.
        </div>
      </div>
      <button type="submit" class="btn btn-solid theme-primary" :disabled="inCorso">
        Continua
      </button>
    </form>
  </section>
</template>
