<script setup lang="ts">
import { defineAsyncComponent, onMounted, ref } from 'vue'

import { api, type OrdineDelGiorno } from '@/api/qdc'
import { ErroreApi } from '@/api/http'
import { useErrore } from '@/composables/useErrore'

// The agenda of a meeting (DEC-362, DEC-365): asked for on its own and never kept on the
// device, like the minutes. Without the network the card only says so.
const EditorTesto = defineAsyncComponent(() => import('@/components/EditorTesto.vue'))
const props = defineProps<{ evento: number }>()
const { errore, inCorso, esegui } = useErrore()
const dati = ref<OrdineDelGiorno | null>(null)
const senzaRete = ref(false)
const testo = ref<string | null>(null)

onMounted(async () => {
  try {
    dati.value = await api.ordineDelGiorno(props.evento)
  } catch (e) {
    senzaRete.value = !(e instanceof ErroreApi)
  }
})

async function salva() {
  const salvato = await esegui(() => api.scriviOrdineDelGiorno(props.evento, testo.value ?? ''))
  if (!salvato) return
  dati.value = salvato
  testo.value = null
}
</script>

<template>
  <section v-if="dati || senzaRete" class="card card-body mb-5">
    <h2 class="h5">Ordine del giorno</h2>
    <p v-if="senzaRete" class="small fg-2 mb-0">Per leggerlo serve la rete.</p>
    <template v-else-if="dati">
      <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
      <form v-if="testo !== null" @submit.prevent="salva">
        <EditorTesto v-model="testo" etichetta="Testo dell'ordine del giorno" />
        <div class="d-flex gap-3 mt-3">
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Salva
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="testo = null">Annulla</button>
        </div>
      </form>
      <template v-else>
        <!-- eslint-disable-next-line vue/no-v-html -- HTML cleaned by the server (DEC-362) -->
        <div v-if="dati.testo" class="mb-3" v-html="dati.testo"></div>
        <p v-else class="small fg-2 mb-3">Non è ancora stato scritto.</p>
        <button
          v-if="dati.puo_scrivere"
          type="button"
          class="btn btn-sm btn-outline theme-primary align-self-start"
          @click="testo = dati?.testo ?? ''"
        >
          {{ dati.testo ? 'Modifica' : 'Scrivilo' }}
        </button>
      </template>
    </template>
  </section>
</template>
