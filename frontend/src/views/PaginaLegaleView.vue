<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import { api, type PaginaLegale } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'
import { useNomePagina } from '@/composables/useNomePagina'

// Privacy policy or terms (DEC-266): public, as the group published them. The HTML is
// cleaned by the server before it is saved.
const props = defineProps<{ chiave: 'privacy' | 'termini' }>()
const { errore, esegui } = useErrore()
const pagina = ref<PaginaLegale | null>(null)

useNomePagina(() => pagina.value?.titolo)

async function carica() {
  pagina.value = (await esegui(() => api.paginaLegale(props.chiave))) ?? null
}

onMounted(carica)
watch(() => props.chiave, carica)
</script>

<template>
  <section>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <template v-if="pagina">
      <h1 class="h4 mb-1">{{ pagina.titolo }}</h1>
      <p v-if="pagina.aggiornata_il" class="small fg-2">
        Aggiornata il {{ new Date(pagina.aggiornata_il).toLocaleDateString('it-IT') }}
      </p>
      <!-- eslint-disable-next-line vue/no-v-html -- HTML cleaned by the server (nh3) -->
      <article class="qdc-pagina-legale mt-5" v-html="pagina.html"></article>
    </template>
  </section>
</template>
