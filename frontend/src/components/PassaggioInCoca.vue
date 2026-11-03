<script setup lang="ts">
import { ref } from 'vue'

import { api } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// A parent who becomes a capo, in two steps (DEC-307): a capogruppo brings them into the
// Co.Ca. with the data the app has and a provisional codice socio, then invites them from
// «Accesso all'app» if they have no account. Undone while the code is still provisional.
const props = defineProps<{ persona: number; nome: string; annullabile: boolean }>()
const emit = defineEmits<{ cambiato: [] }>()
const { errore, inCorso, esegui } = useErrore()
const conferma = ref(false)
const fatto = ref('')

async function porta() {
  await esegui(() => api.portaInCoca(props.persona))
  if (errore.value) return
  fatto.value = `${props.nome} è in Comunità capi. Se non ha ancora un account, manda l'invito da «Accesso all'app».`
  conferma.value = false
  emit('cambiato')
}

async function annulla() {
  await esegui(() => api.annullaPassaggioInCoca(props.persona))
  if (errore.value) return
  fatto.value = `${props.nome} non è più in Comunità capi: resta genitore.`
  conferma.value = false
  emit('cambiato')
}
</script>

<template>
  <section class="card card-body mb-5">
    <h2 class="h5">Comunità capi</h2>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="fatto" class="alert theme-success small" role="status">
      <div>{{ fatto }}</div>
    </div>
    <template v-if="annullabile">
      <p class="small fg-2">
        {{ nome }} è in Comunità capi dall'app e ha ancora il codice socio provvisorio: finché non è
        in BuonaStrada non vede i dati delicati degli altri. Se è stato un errore puoi annullare il
        passaggio: torna solo genitore, e gli incarichi che ha avuto nel frattempo si chiudono.
      </p>
      <div class="d-flex flex-wrap gap-3 align-items-center">
        <button
          v-if="!conferma"
          type="button"
          class="btn btn-sm btn-outline theme-danger"
          @click="conferma = true"
        >
          Annulla il passaggio in Comunità capi…
        </button>
        <template v-else>
          <span class="small">Annullare il passaggio?</span>
          <button
            type="button"
            class="btn btn-sm btn-solid theme-danger"
            :disabled="inCorso"
            @click="annulla"
          >
            Annulla il passaggio
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="conferma = false">No</button>
        </template>
      </div>
    </template>
    <template v-else>
      <p class="small fg-2">
        Se {{ nome }} diventa capo, con «Porta in Comunità capi» entra con i dati che l'app ha già:
        avrà un codice socio provvisorio fino all'iscrizione in BuonaStrada, e resta genitore dei
        figli. Poi, se non ha un account, manda l'invito da «Accesso all'app». Finché il codice è
        provvisorio puoi annullare il passaggio.
      </p>
      <div class="d-flex flex-wrap gap-3 align-items-center">
        <button
          v-if="!conferma"
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          @click="conferma = true"
        >
          Porta in Comunità capi…
        </button>
        <template v-else>
          <span class="small">Portare {{ nome }} in Comunità capi?</span>
          <button
            type="button"
            class="btn btn-sm btn-solid theme-primary"
            :disabled="inCorso"
            @click="porta"
          >
            Porta in Comunità capi
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="conferma = false">No</button>
        </template>
      </div>
    </template>
  </section>
</template>
