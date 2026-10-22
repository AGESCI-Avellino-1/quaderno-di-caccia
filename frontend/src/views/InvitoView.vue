<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { allauth, flussoInSospeso } from '@/api/allauth'
import { api } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'
import { useSessioneStore } from '@/stores/sessione'

const props = defineProps<{ token: string }>()
const router = useRouter()
const sessione = useSessioneStore()
const { errore, inCorso, esegui } = useErrore()

const invito = ref<{ email: string; persona: string } | null>(null)
const password = ref('')
const verificaInviata = ref(false)

// Accepting stores the invitation in the server session: sign-up is open only then (DEC-21).
onMounted(async () => {
  invito.value = (await esegui(() => api.accettaInvito(props.token))) ?? null
})

async function registrati() {
  if (!invito.value) return
  const risposta = await esegui(() => allauth.registrati(invito.value!.email, password.value))
  if (!risposta) return
  if (risposta.meta?.is_authenticated) {
    await sessione.carica()
    await router.replace('/')
  } else if (flussoInSospeso(risposta) === 'verify_email') {
    verificaInviata.value = true
  }
}

const provider = (nome: 'google' | 'apple') =>
  allauth.accediConProvider(nome, `${window.location.origin}/`)
</script>

<template>
  <section class="mx-auto" style="max-width: 26rem">
    <h1 class="h4 mb-3">Invito al Quaderno di Caccia</h1>
    <div v-if="errore" class="alert alert-danger" role="alert">{{ errore }}</div>
    <div v-if="verificaInviata" class="alert alert-success" role="status">
      Ti abbiamo inviato un'email: apri il link per confermare l'indirizzo e completare
      l'iscrizione.
    </div>
    <template v-else-if="invito">
      <p>
        Account per <strong>{{ invito.persona }}</strong> con l'indirizzo
        <strong>{{ invito.email }}</strong
        >.
      </p>
      <form class="vstack gap-2" @submit.prevent="registrati">
        <label class="form-label" for="nuova-password">Scegli una password</label>
        <input
          id="nuova-password"
          v-model="password"
          class="form-control"
          type="password"
          autocomplete="new-password"
          minlength="8"
          required
        />
        <button class="btn btn-primary" :disabled="inCorso">Crea l'account</button>
      </form>
      <hr />
      <p class="small">Oppure usa un account esistente con la stessa email:</p>
      <div class="vstack gap-2">
        <button type="button" class="btn btn-outline-secondary" @click="provider('google')">
          Continua con Google
        </button>
        <button type="button" class="btn btn-outline-secondary" @click="provider('apple')">
          Continua con Apple
        </button>
      </div>
    </template>
  </section>
</template>
