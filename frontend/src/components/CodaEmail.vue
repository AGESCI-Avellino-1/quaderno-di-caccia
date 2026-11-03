<script setup lang="ts">
import { reactive, watch } from 'vue'

import { api, type Impostazioni } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The emails to many go out a few at a time (DEC-311), for the technical administrator:
// a block, a pause, a daily cap; what is waiting now. Codes and password resets never wait.
const props = defineProps<{ impostazioni: Impostazioni }>()
const emit = defineEmits<{ aggiornate: [Impostazioni] }>()
const { errore, inCorso, esegui } = useErrore()

const dati = reactive({ blocco: 20, pausa_minuti: 2, massimo_giorno: 400 })
function leggi(imp: Impostazioni) {
  Object.assign(dati, {
    blocco: imp.coda_blocco ?? 20,
    pausa_minuti: imp.coda_pausa_minuti ?? 2,
    massimo_giorno: imp.coda_massimo_giorno ?? 400,
  })
}
leggi(props.impostazioni)
watch(() => props.impostazioni, leggi)

async function salva() {
  const imp = await esegui(() => api.salvaCodaEmail({ ...dati }))
  if (imp) emit('aggiornate', imp)
}

async function riprova() {
  const imp = await esegui(() => api.riprovaCodaEmail())
  if (imp) emit('aggiornate', imp)
}
</script>

<template>
  <section class="mb-7">
    <h2 class="h5">Invio un po' alla volta</h2>
    <p class="small fg-2">
      Le email a molte persone (inviti, avvisi, promemoria) partono a blocchi, con una pausa tra un
      blocco e l'altro e un massimo al giorno, perché la casella del gruppo non finisca tra gli
      spammer. Un indirizzo Gmail ne manda circa 500 al giorno, un account Google Workspace 2000.
      Partono subito i codici per entrare, il cambio della password e la conferma dell'indirizzo.
    </p>
    <div v-if="!impostazioni.coda_attiva" class="alert theme-info small" role="status">
      <div>Su questo server la coda è spenta: tutte le email partono subito.</div>
    </div>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <form class="card card-body" @submit.prevent="salva">
      <div class="row g-3">
        <div class="col-12 md:col-4">
          <label class="form-label small" for="coda-blocco">Email per blocco</label>
          <input
            id="coda-blocco"
            v-model.number="dati.blocco"
            type="number"
            min="1"
            max="500"
            class="form-control form-control-sm"
          />
        </div>
        <div class="col-12 md:col-4">
          <label class="form-label small" for="coda-pausa">Minuti di pausa tra i blocchi</label>
          <input
            id="coda-pausa"
            v-model.number="dati.pausa_minuti"
            type="number"
            min="0"
            max="120"
            class="form-control form-control-sm"
          />
        </div>
        <div class="col-12 md:col-4">
          <label class="form-label small" for="coda-massimo">Email al giorno, al massimo</label>
          <input
            id="coda-massimo"
            v-model.number="dati.massimo_giorno"
            type="number"
            min="1"
            class="form-control form-control-sm"
          />
        </div>
      </div>
      <p class="small mt-3 mb-3" role="status">
        In attesa: {{ impostazioni.coda_in_attesa ?? 0 }} · partite oggi:
        {{ impostazioni.coda_inviate_oggi ?? 0 }}
        <template v-if="impostazioni.coda_abbandonate">
          · non partite dopo 5 tentativi: {{ impostazioni.coda_abbandonate }}
        </template>
      </p>
      <div class="d-flex flex-wrap gap-3">
        <button type="submit" class="btn btn-solid theme-primary btn-sm" :disabled="inCorso">
          Salva
        </button>
        <button
          v-if="impostazioni.coda_abbandonate"
          type="button"
          class="btn btn-outline theme-primary btn-sm"
          :disabled="inCorso"
          @click="riprova"
        >
          Riprova quelle non partite
        </button>
      </div>
    </form>
  </section>
</template>
