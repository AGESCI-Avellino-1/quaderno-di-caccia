<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, PEG_PUBBLICO_PDF, type PegPubblico } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Open to anyone, without an account: only the version in force (DEC-344).
const { errore, esegui } = useErrore()
const peg = ref<PegPubblico | null>(null)
onMounted(async () => {
  peg.value = (await esegui(() => api.pegPubblico())) ?? null
})
const giorno = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
</script>

<template>
  <main class="container py-5">
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <template v-if="peg">
      <h1 class="h4 mb-1">Progetto Educativo di Gruppo</h1>
      <p v-if="peg.gruppo" class="fg-2 mb-3">{{ peg.gruppo }}</p>
      <div v-if="peg.in_redazione" class="alert theme-warning small" role="status">
        <div>È in redazione una nuova versione: quella qui sotto resta valida.</div>
      </div>
      <p v-if="!peg.ha_pdf" class="fg-2">Non è ancora stato pubblicato.</p>
      <template v-else>
        <p v-if="peg.approvato_il" class="small fg-2 mb-3">
          Approvato il {{ giorno(peg.approvato_il)
          }}<template v-if="peg.durata"> · {{ peg.durata }}</template>
        </p>
        <a :href="PEG_PUBBLICO_PDF" class="btn btn-sm btn-solid theme-primary mb-5">
          Scarica il PDF
        </a>
        <!-- eslint-disable-next-line vue/no-v-html -- HTML cleaned by the server -->
        <div v-if="peg.testo" v-html="peg.testo"></div>
      </template>
    </template>
  </main>
</template>
