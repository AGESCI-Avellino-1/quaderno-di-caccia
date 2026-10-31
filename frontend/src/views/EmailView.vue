<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { api, type PreferenzeEmail } from '@/api/qdc'
import VisibilitaGenitori from '@/components/VisibilitaGenitori.vue'
import { useErrore } from '@/composables/useErrore'
import { useSessioneStore } from '@/stores/sessione'

// Privacy (DEC-251): what an adult's parents see (DEC-26), and which optional emails
// the user receives (right to object, GDPR art. 21). What the
// app needs to work or what proves a payment is always sent. Online only.
const sessione = useSessioneStore()
const { errore, inCorso, esegui } = useErrore()
const scelte = reactive<PreferenzeEmail>({
  eventi: true,
  promemoria_quote: true,
  maggiore_eta: true,
  riepiloghi: true,
  avvisi: true,
})
const caricate = ref(false)
const salvate = ref(false)

onMounted(async () => {
  const dati = await esegui(() => api.preferenzeEmail())
  if (!dati) return
  Object.assign(scelte, dati)
  caricate.value = true
})

async function salva() {
  salvate.value = false
  const dati = await esegui(() => api.scegliPreferenzeEmail({ ...scelte }))
  if (!dati) return
  Object.assign(scelte, dati)
  salvate.value = true
}

const voci = [
  { chiave: 'eventi', etichetta: 'Eventi: nuovi eventi, cambi di date o luogo, annullamenti' },
  { chiave: 'promemoria_quote', etichetta: 'Promemoria delle quote in scadenza' },
  { chiave: 'maggiore_eta', etichetta: 'Avvisi per i 18 anni (tuoi o dei tuoi figli)' },
  {
    chiave: 'avvisi',
    etichetta: 'Avvisi della bacheca, quando chi li pubblica li manda anche per email',
  },
] as const
</script>

<template>
  <section>
    <h1 class="h4 mb-5">Privacy</h1>
    <VisibilitaGenitori v-if="sessione.profilo?.persona" :id="sessione.profilo.persona.id" />
    <h2 class="h5 mb-1">Le email che ricevi</h2>
    <p class="fg-2 small">
      Scegli quali email ricevere. Quello che non ricevi per email lo trovi comunque nell'app.
    </p>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <form v-if="caricate" class="card card-body mb-5" @submit.prevent="salva">
      <div v-for="v in voci" :key="v.chiave" class="form-field">
        <div class="switch">
          <input
            :id="`email-${v.chiave}`"
            v-model="scelte[v.chiave]"
            type="checkbox"
            role="switch"
          />
        </div>
        <label :for="`email-${v.chiave}`">{{ v.etichetta }}</label>
      </div>
      <div v-if="sessione.capo" class="form-field">
        <div class="switch">
          <input id="email-riepiloghi" v-model="scelte.riepiloghi" type="checkbox" role="switch" />
        </div>
        <label for="email-riepiloghi">
          Riepiloghi per i capi: correzioni da inoltrare, richieste di iscrizione da decidere
        </label>
      </div>
      <div class="d-flex align-items-center gap-3 mt-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Salva
        </button>
        <span v-if="salvate" class="small fg-success">Salvate.</span>
      </div>
    </form>
    <p class="small">
      Arrivano sempre, perché servono a usare l'app o sono documenti: i codici per entrare, gli
      inviti, gli avvisi di sicurezza, le email dell'iscrizione dall'app e le ricevute dei
      pagamenti.
    </p>
  </section>
</template>
