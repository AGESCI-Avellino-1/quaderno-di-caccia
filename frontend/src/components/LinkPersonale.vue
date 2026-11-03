<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api } from '@/api/qdc'
import CondividiLink from '@/components/CondividiLink.vue'
import { useErrore } from '@/composables/useErrore'

// A ragazzo's personal link to create their account (DEC-309), from 14 to 18 and without
// an account: shown once, to send by any channel. A new one voids the old. Hidden to who
// may not generate it (the server answers 404). Online only.
const props = defineProps<{ persona: number; nome: string; sempre?: boolean }>()
const { errore, inCorso, esegui } = useErrore()
const visibile = ref(!!props.sempre)
const attivoFinoAl = ref<string | null>(null)
const generato = ref<{ link: string; scadenza: string } | null>(null)

onMounted(async () => {
  if (props.sempre) return
  try {
    attivoFinoAl.value = (await api.statoLinkAttivazione(props.persona)).attivo_fino_al
    visibile.value = true
  } catch {
    visibile.value = false
  }
})

async function genera() {
  generato.value = (await esegui(() => api.generaLinkAttivazione(props.persona))) ?? null
  if (generato.value) attivoFinoAl.value = generato.value.scadenza
}

const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
</script>

<template>
  <section v-if="visibile" class="card card-body mb-5">
    <h2 class="h5">Link personale per l'app</h2>
    <p class="small fg-2">
      Un link solo per {{ nome }}, da mandare come vuoi (per esempio su WhatsApp): aprendolo
      conferma la sua data di nascita e scrive la sua email, poi crea l'account. Vale 30 giorni e
      una volta sola; se ne generi un altro, quello di prima non vale più. I genitori ricevono
      un'email quando l'account è creato.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <p v-if="attivoFinoAl && !generato" class="small">
      C'è già un link valido fino al {{ data(attivoFinoAl) }}: per rimandarlo generane uno nuovo
      (l'app non lo conserva).
    </p>
    <div v-if="generato" class="mb-3">
      <p class="small text-break mb-3">
        <strong>{{ generato.link }}</strong>
      </p>
      <CondividiLink
        :url="generato.link"
        titolo="Il tuo account del Quaderno di Caccia"
        :testo="`Ciao ${nome}, con questo link crei il tuo account:`"
      />
      <p class="small fg-2 mt-3 mb-0">
        Il link si vede solo adesso: mandalo prima di lasciare la pagina.
      </p>
    </div>
    <div>
      <button
        type="button"
        class="btn btn-sm btn-outline theme-primary"
        :disabled="inCorso"
        @click="genera"
      >
        {{ attivoFinoAl || generato ? 'Genera un link nuovo' : 'Genera il link' }}
      </button>
    </div>
  </section>
</template>
