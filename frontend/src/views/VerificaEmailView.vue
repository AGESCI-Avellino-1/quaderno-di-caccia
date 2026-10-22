<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { allauth } from '@/api/allauth'
import { useErrore } from '@/composables/useErrore'
import { useSessioneStore } from '@/stores/sessione'

const props = defineProps<{ chiave: string }>()
const router = useRouter()
const sessione = useSessioneStore()
const { errore, esegui } = useErrore()
const confermata = ref(false)

onMounted(async () => {
  const risposta = await esegui(() => allauth.verificaEmail(props.chiave))
  if (!risposta) return
  confermata.value = true
  if (risposta.meta?.is_authenticated) {
    await sessione.carica()
    await router.replace('/')
  }
})
</script>

<template>
  <section class="mx-auto" style="max-width: 26rem">
    <h1 class="h4 mb-3">Conferma email</h1>
    <div v-if="errore" class="alert alert-danger" role="alert">{{ errore }}</div>
    <div v-else-if="confermata" class="alert alert-success" role="status">
      Indirizzo confermato. <RouterLink to="/accesso">Accedi</RouterLink>
    </div>
    <p v-else>Verifica in corso…</p>
  </section>
</template>
