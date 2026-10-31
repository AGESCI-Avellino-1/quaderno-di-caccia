<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { api, type DatiAttesa, type MiaAttesa } from '@/api/qdc'
import ModuloAttesa from '@/components/ModuloAttesa.vue'
import { useErrore } from '@/composables/useErrore'

// The family's page on the waiting list, reached from the personal link (DEC-257):
// correct the data, confirm the interest after two years (DEC-262), leave the list.
// Never the place in the list.
const props = defineProps<{ token: string }>()
const { errore, inCorso, esegui } = useErrore()
const voce = ref<MiaAttesa | null>(null)
const dati = ref<DatiAttesa | null>(null)
const esito = ref('')
const uscito = ref(false)
const chiediUscita = ref(false)

function mostra(letta: MiaAttesa) {
  voce.value = letta
  dati.value = {
    nome: letta.nome,
    cognome: letta.cognome,
    sesso: letta.sesso,
    data_nascita: letta.data_nascita,
    luogo_nascita: letta.luogo_nascita,
    da_se: letta.da_se,
    contatto_nome: letta.contatto_nome,
    contatto_cognome: letta.contatto_cognome,
    telefono: letta.telefono,
    email: letta.email,
    indirizzo: letta.indirizzo,
    comune: letta.comune,
    provincia: letta.provincia,
    cap: letta.cap,
  }
}

onMounted(async () => {
  const letta = await esegui(() => api.miaAttesa(props.token))
  if (letta) mostra(letta)
})

async function salva() {
  if (!dati.value) return
  esito.value = ''
  const letta = await esegui(() => api.correggiAttesa(props.token, dati.value!))
  if (!letta) return
  mostra(letta)
  esito.value = 'Dati corretti.'
}

async function conferma() {
  const letta = await esegui(() => api.confermaAttesa(props.token))
  if (!letta) return
  mostra(letta)
  esito.value = 'Grazie: restate in lista. Ve lo richiederemo tra due anni.'
}

async function esci() {
  await esegui(() => api.esciDallaLista(props.token))
  if (!errore.value) uscito.value = true
}
</script>

<template>
  <section>
    <h1 class="h4 mb-5">La vostra iscrizione alla lista d'attesa</h1>
    <div v-if="errore" class="alert theme-danger" role="alert">
      <div>
        {{ errore }}
        <RouterLink to="/lista-attesa" class="d-block mt-1">Torna alla lista d'attesa</RouterLink>
      </div>
    </div>
    <div v-if="uscito" class="alert theme-success" role="status">
      <div>Siete usciti dalla lista d'attesa: i dati sono stati cancellati.</div>
    </div>
    <template v-else-if="voce && dati">
      <div v-if="esito" class="alert theme-success small" role="status">
        <div>{{ esito }}</div>
      </div>
      <div v-if="voce.conferma_chiesta" class="card card-body mb-5">
        <h2 class="h6">Volete restare in lista?</h2>
        <p class="small mb-3">
          Siete in lista da due anni: confermate entro 30 giorni, altrimenti l'iscrizione alla lista
          si cancella.
        </p>
        <div>
          <button
            type="button"
            class="btn btn-sm btn-solid theme-primary"
            :disabled="inCorso"
            @click="conferma"
          >
            Sì, restiamo in lista
          </button>
        </div>
      </div>
      <p class="small fg-2">
        <template v-if="voce.contattabile_dal"
          >{{ voce.nome }} potrà essere contattato dall'anno scout
          {{ voce.contattabile_dal }}.</template
        >
        I capi chiamano a inizio anno, secondo i posti nelle unità.
      </p>
      <form class="card card-body mb-5" @submit.prevent="salva">
        <ModuloAttesa v-model="dati" prefisso="mia" />
        <div>
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Salva le correzioni
          </button>
        </div>
      </form>
      <section class="card card-body">
        <h2 class="h6">Uscire dalla lista</h2>
        <p class="small fg-2">I dati si cancellano subito e non si possono recuperare.</p>
        <div v-if="!chiediUscita">
          <button
            type="button"
            class="btn btn-sm btn-outline theme-danger"
            @click="chiediUscita = true"
          >
            Esci dalla lista
          </button>
        </div>
        <div v-else class="d-flex flex-wrap gap-3">
          <button
            type="button"
            class="btn btn-sm btn-solid theme-danger"
            :disabled="inCorso"
            @click="esci"
          >
            Sì, uscite dalla lista
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="chiediUscita = false">
            No, restiamo
          </button>
        </div>
      </section>
    </template>
  </section>
</template>
