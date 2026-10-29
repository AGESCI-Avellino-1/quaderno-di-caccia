<script setup lang="ts">
import { ref } from 'vue'

import { allauth } from '@/api/allauth'
import { useErrore } from '@/composables/useErrore'

// Without a key: ask for the email. With the key from the email link: choose a new one.
const props = defineProps<{ chiave?: string }>()
const { errore, inCorso, esegui } = useErrore()
const email = ref('')
const password = ref('')
const fatto = ref<string | null>(null)

async function richiedi() {
  await esegui(() => allauth.richiediRecuperoPassword(email.value))
  if (!errore.value) fatto.value = 'Se l’indirizzo è registrato riceverai un’email con il link.'
}

async function reimposta() {
  await esegui(() => allauth.reimpostaPassword(props.chiave!, password.value))
  if (!errore.value) fatto.value = 'Password aggiornata.'
}
</script>

<template>
  <section class="mx-auto" style="max-width: 26rem">
    <h1 class="h4 mb-5">Reimposta password</h1>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <div v-if="fatto" class="alert theme-success" role="status">
      <div>{{ fatto }} <RouterLink to="/accesso">Torna all'accesso</RouterLink></div>
    </div>
    <form v-else-if="!props.chiave" class="vstack gap-3" @submit.prevent="richiedi">
      <input v-model="email" class="form-control" type="email" placeholder="Email" required />
      <button class="btn btn-solid theme-primary" :disabled="inCorso">Invia il link</button>
    </form>
    <form v-else class="vstack gap-3" @submit.prevent="reimposta">
      <input
        v-model="password"
        class="form-control"
        type="password"
        placeholder="Nuova password"
        autocomplete="new-password"
        minlength="8"
        required
      />
      <button class="btn btn-solid theme-primary" :disabled="inCorso">Salva</button>
    </form>
  </section>
</template>
