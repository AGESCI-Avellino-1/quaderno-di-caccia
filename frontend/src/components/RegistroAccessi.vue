<script setup lang="ts">
import { ref } from 'vue'

import { api, type AccessoSensibile } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Who read, printed or downloaded this person's sensitive data (DEC-101): for the
// Co.Ca., opened on request and online only, like the data it is about.
const props = defineProps<{ id: number }>()
const { errore, inCorso, esegui } = useErrore()
const righe = ref<AccessoSensibile[] | null>(null)
const quando = (iso: string) =>
  new Date(iso).toLocaleString('it-IT', { dateStyle: 'short', timeStyle: 'short' })

async function alterna() {
  if (righe.value) {
    righe.value = null
    return
  }
  righe.value = (await esegui(() => api.accessiSensibili(props.id))) ?? null
}
</script>

<template>
  <section class="card card-body mb-5">
    <div class="d-flex flex-wrap align-items-center gap-3">
      <h2 class="h5 mb-0">Chi ha visto i dati delicati</h2>
      <button
        type="button"
        class="btn btn-sm btn-outline theme-primary ms-auto"
        :disabled="inCorso"
        @click="alterna"
      >
        {{ righe ? 'Nascondi' : 'Mostra il registro' }}
      </button>
    </div>
    <p class="small fg-2 mb-0 mt-1">
      Ogni lettura, stampa o scaricamento dei dati delicati resta qui: dati sanitari, regole sul
      rapporto con il minore, eccezioni sulle squadriglie, moduli firmati, fascicolo completo.
    </p>
    <div v-if="errore" class="alert theme-danger small mt-3" role="alert">{{ errore }}</div>
    <template v-if="righe">
      <p v-if="!righe.length" class="small fg-2 mt-3 mb-0">Nessun accesso registrato.</p>
      <ul v-else class="list-group mt-3">
        <li v-for="(r, n) in righe" :key="n" class="list-group-item small">
          <strong>{{ quando(r.quando) }}</strong> · {{ r.chi ?? 'sconosciuto' }} · {{ r.azione }} ·
          {{ r.categoria }}
          <span v-if="r.dispositivo" class="fg-2"> · {{ r.dispositivo }}</span>
        </li>
      </ul>
    </template>
  </section>
</template>
