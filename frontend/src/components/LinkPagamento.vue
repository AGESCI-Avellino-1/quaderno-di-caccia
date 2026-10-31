<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Where families pay outside the app, e.g. paypal.me (DEC-83): the group's fee managers.
const { errore, inCorso, esegui } = useErrore()
const link = ref('')
const esito = ref('')

onMounted(async () => {
  link.value = (await esegui(() => api.impostazioniQuote()))?.link_pagamento ?? ''
})

async function salva() {
  esito.value = ''
  const fatto = await esegui(() => api.salvaImpostazioniQuote(link.value))
  if (fatto) esito.value = 'Link di pagamento salvato.'
}
</script>

<template>
  <section class="mb-7">
    <h2 class="h5">Link di pagamento</h2>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>
    <form class="card card-body d-flex flex-wrap align-items-end gap-3" @submit.prevent="salva">
      <div class="flex-grow-1">
        <label class="form-label small" for="link-pagamento">
          Dove le famiglie possono pagare (es. paypal.me): lo vedono nella pagina delle quote
        </label>
        <input
          id="link-pagamento"
          v-model="link"
          type="url"
          class="form-control form-control-sm"
          placeholder="https://"
        />
      </div>
      <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
        Salva
      </button>
    </form>
  </section>
</template>
