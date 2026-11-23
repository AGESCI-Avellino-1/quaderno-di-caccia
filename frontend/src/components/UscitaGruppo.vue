<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { ErroreApi } from '@/api/http'
import { api, euro, type UscitaGruppo } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Who left the group, recorded in the app without waiting for BuonaStrada (DEC-420): the
// staff of the unit for its ragazzi, the capigruppo for everyone. From the chosen day the
// units, the patrol and the roles end; the unpaid fees ticked are cancelled. It goes to the
// capigruppo as a correction to forward, and can be undone. Online only.
const props = defineProps<{ persona: number; nome: string }>()
const emit = defineEmits<{ cambiato: [] }>()
const { errore, inCorso, esegui } = useErrore()
const dati = ref<UscitaGruppo | null>(null)
const aperto = ref(false)
const conferma = ref(false)
const oggi = new Date().toLocaleDateString('sv')
const giorno = ref(oggi)
const quote = ref<number[]>([])

onMounted(async () => {
  try {
    dati.value = await api.uscita(props.persona)
  } catch (e) {
    // Not one who may record or undo it: nothing to show.
    if (!(e instanceof ErroreApi && e.stato === 404)) throw e
  }
})

function apri() {
  giorno.value = oggi
  quote.value = dati.value?.quote.map((q) => q.id) ?? []
  aperto.value = true
}

async function registra() {
  const esito = await esegui(() => api.registraUscita(props.persona, giorno.value, quote.value))
  if (!esito) return
  dati.value = esito
  aperto.value = false
  emit('cambiato')
}

async function annulla() {
  const esito = await esegui(() => api.annullaUscita(props.persona))
  if (!esito) return
  dati.value = esito
  conferma.value = false
  emit('cambiato')
}

const data = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString('it-IT')
</script>

<template>
  <section v-if="dati" class="card card-body mb-5" data-uscita>
    <h2 class="h5">Uscita dal gruppo</h2>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>

    <template v-if="dati.uscita">
      <p class="mb-3">
        {{ nome }} ha lasciato il gruppo il {{ data(dati.uscita.data) }}
        <template v-if="dati.uscita.registrata_da">
          (registrato da {{ dati.uscita.registrata_da }})</template
        >.
      </p>
      <p v-if="dati.uscita.stato" class="small fg-2">
        Per BuonaStrada: {{ dati.uscita.stato.toLowerCase() }}.
      </p>
      <div v-if="dati.uscita.puo_annullare" class="d-flex flex-wrap gap-3 align-items-center">
        <button
          v-if="!conferma"
          type="button"
          class="btn btn-sm btn-outline theme-danger"
          @click="conferma = true"
        >
          Annulla l'uscita…
        </button>
        <template v-else>
          <span class="small">
            Tornano le unità, la squadriglia, gli incarichi e le quote di prima. Annullare?
          </span>
          <button
            type="button"
            class="btn btn-sm btn-solid theme-danger"
            :disabled="inCorso"
            @click="annulla"
          >
            Annulla l'uscita
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="conferma = false">No</button>
        </template>
      </div>
    </template>

    <template v-else-if="dati.puo_registrare">
      <p class="small fg-2">
        Se {{ nome }} ha lasciato il gruppo, registralo qui senza aspettare BuonaStrada: esce dalle
        unità, dalla squadriglia e dagli incarichi; l'account resta, per i suoi dati e le quote da
        pagare. I capigruppo lo inoltrano alla segreteria.
      </p>
      <button
        v-if="!aperto"
        type="button"
        class="btn btn-sm btn-outline theme-danger"
        @click="apri"
      >
        Ha lasciato il gruppo…
      </button>
      <form v-else @submit.prevent="registra">
        <label class="form-label small" :for="`uscita-${persona}`">Dal giorno</label>
        <input
          :id="`uscita-${persona}`"
          v-model="giorno"
          type="date"
          class="form-control w-auto mb-3"
          :max="oggi"
          required
        />
        <template v-if="dati.quote.length">
          <p class="small mb-1">Quote non pagate da annullare («Ha lasciato il gruppo»):</p>
          <div v-for="q in dati.quote" :key="q.id" class="form-field mb-1">
            <input
              :id="`uscita-quota-${q.id}`"
              v-model="quote"
              type="checkbox"
              class="check"
              :value="q.id"
            />
            <label :for="`uscita-quota-${q.id}`">{{ q.descrizione }}, {{ euro(q.importo) }}</label>
          </div>
          <p class="small fg-2">Quelle non spuntate restano da pagare.</p>
        </template>
        <div class="d-flex flex-wrap gap-3 mt-3">
          <button type="submit" class="btn btn-sm btn-solid theme-danger" :disabled="inCorso">
            Registra l'uscita
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="aperto = false">Annulla</button>
        </div>
      </form>
    </template>
  </section>
</template>
