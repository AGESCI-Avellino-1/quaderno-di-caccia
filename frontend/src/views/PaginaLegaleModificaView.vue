<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { api, type PaginaLegaleModifica } from '@/api/qdc'
import EditorTesto from '@/components/EditorTesto.vue'
import { useErrore } from '@/composables/useErrore'
import { useNomePagina } from '@/composables/useNomePagina'

// Editing the privacy policy or the terms (DEC-266): capigruppo and the technical
// administrator; the default text can always come back.
const props = defineProps<{ chiave: 'privacy' | 'termini' }>()
const { errore, inCorso, esegui } = useErrore()
const pagina = ref<PaginaLegaleModifica | null>(null)
const testo = ref('')
const esito = ref('')
const editor = ref<InstanceType<typeof EditorTesto> | null>(null)

useNomePagina(() => pagina.value?.titolo)

function mostra(dati: PaginaLegaleModifica) {
  pagina.value = dati
  testo.value = dati.testo
}

onMounted(async () => {
  const dati = await esegui(() => api.paginaLegaleDaModificare(props.chiave))
  if (dati) mostra(dati)
})

async function salva() {
  esito.value = ''
  const dati = await esegui(() => api.salvaPaginaLegale(props.chiave, testo.value))
  if (!dati) return
  mostra(dati)
  esito.value = 'Pubblicata: è già quella che vedono tutti.'
}

async function base() {
  esito.value = ''
  const dati = await esegui(() => api.paginaLegaleDiBase(props.chiave))
  if (!dati) return
  mostra(dati)
  esito.value = 'Tornata al testo di base.'
}
</script>

<template>
  <section>
    <RouterLink to="/impostazioni" class="small">Torna alle impostazioni</RouterLink>
    <div v-if="errore" class="alert theme-danger small mt-3" role="alert">{{ errore }}</div>
    <template v-if="pagina">
      <h1 class="h4 mb-1 mt-3">{{ pagina.titolo }}</h1>
      <div class="alert theme-info small" role="note">
        <div>
          Il testo di base è un punto di partenza: fatelo controllare a chi segue la privacy per il
          gruppo (o all'ufficio privacy nazionale) prima di considerarlo definitivo.
        </div>
      </div>
      <div v-if="esito" class="alert theme-success small" role="status">
        <div>{{ esito }}</div>
      </div>
      <form class="card card-body" @submit.prevent="salva">
        <EditorTesto ref="editor" v-model="testo" :etichetta="pagina.titolo" immagini />
        <div class="mt-3">
          <span class="small">Segnaposto: tocca per inserirlo nel testo</span>
          <div class="d-flex flex-wrap gap-1 mt-1">
            <button
              v-for="s in pagina.segnaposto"
              :key="s"
              type="button"
              class="btn btn-sm btn-outline theme-primary"
              @click="editor?.inserisci(`[${s}]`)"
            >
              [{{ s }}]
            </button>
          </div>
        </div>
        <div class="d-flex flex-wrap gap-3 mt-3">
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Pubblica
          </button>
          <RouterLink :to="`/${chiave}`" class="btn btn-sm btn-link" target="_blank"
            >Vedi la pagina</RouterLink
          >
          <button
            v-if="pagina.personalizzata"
            type="button"
            class="btn btn-sm btn-link"
            :disabled="inCorso"
            @click="base"
          >
            Torna al testo di base
          </button>
        </div>
      </form>
    </template>
  </section>
</template>
