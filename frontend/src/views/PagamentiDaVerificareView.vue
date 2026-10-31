<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { api, euro, ricevutaSegnalazione, type Segnalazione } from '@/api/qdc'
import Icona from '@/components/Icona.vue'
import { useErrore } from '@/composables/useErrore'
import { useSessioneStore } from '@/stores/sessione'

// Payments the families reported (DEC-255): who may record payments for those members
// checks them, from the proof or the PayPal or bank statement, and confirms (payment,
// receipt, cash book as DEC-254) or refuses with a reason the family receives. Online.
const { errore, inCorso, esegui } = useErrore()
const sessione = useSessioneStore()
const elenco = ref<Segnalazione[]>([])
const esito = ref('')
// Per report: the day to record, what PayPal credited, the reason of a refusal.
const scelte = reactive<
  Record<number, { data: string; accreditato: string; motivo: string; rifiuto: boolean }>
>({})

async function carica() {
  elenco.value = (await esegui(() => api.segnalazioni())) ?? []
  for (const s of elenco.value) {
    scelte[s.id] ??= { data: s.data, accreditato: '', motivo: '', rifiuto: false }
  }
  await sessione.carica() // the menu counter
}

onMounted(carica)

const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
const totale = (s: Segnalazione) => Number(s.importo) + Number(s.maggiorazione)

async function conferma(s: Segnalazione) {
  const scelta = scelte[s.id]!
  esito.value = ''
  const pagamento = await esegui(() =>
    api.confermaSegnalazione(s.id, {
      data: scelta.data,
      accreditato: scelta.accreditato === '' ? null : String(scelta.accreditato),
    }),
  )
  if (!pagamento) return
  esito.value = `Pagamento confermato: ricevuta n. ${pagamento.numero}, mandata alla famiglia.`
  await carica()
}

async function rifiuta(s: Segnalazione) {
  const scelta = scelte[s.id]!
  esito.value = ''
  if (!(await esegui(() => api.rifiutaSegnalazione(s.id, scelta.motivo)))) return
  esito.value = 'Segnalazione non confermata: la famiglia riceve il motivo per email.'
  await carica()
}
</script>

<template>
  <section>
    <h1 class="h4 mb-1">Pagamenti da verificare</h1>
    <p class="small fg-2">
      Pagamenti con PayPal o con bonifico segnalati dalle famiglie. Controllali con la ricevuta, se
      c'è, o con l'estratto conto di PayPal o della banca: confermati, diventano pagamenti con la
      loro ricevuta.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>
    <p v-if="!elenco.length && !inCorso" class="fg-2">Nessun pagamento da verificare.</p>
    <div v-for="s in elenco" :key="s.id" class="card card-body mb-5">
      <div class="d-flex flex-wrap align-items-center gap-3">
        <Icona :nome="s.metodo === 'PAYPAL' ? 'paypal' : 'bank2'" />
        <strong>{{ euro(totale(s)) }}</strong>
        <span>{{ s.metodo_nome }} del {{ data(s.data) }}, segnalato da {{ s.segnalata_da }}</span>
      </div>
      <ul class="small mb-1 mt-1">
        <li v-for="q in s.quote" :key="q.id">
          {{ q.persona }}: {{ q.descrizione }}, {{ euro(q.residuo) }}
        </li>
      </ul>
      <p v-if="Number(s.maggiorazione)" class="small fg-2 mb-1">
        Di cui {{ euro(s.maggiorazione) }} di quota aggiuntiva PayPal: va in prima nota come «Quota
        PayPal».
      </p>
      <p class="small mb-3">
        <a v-if="s.ricevuta" :href="ricevutaSegnalazione(s.id)" target="_blank" rel="noopener"
          >Apri la ricevuta caricata</a
        >
        <span v-else class="fg-2">Nessuna ricevuta caricata: controlla l'estratto conto.</span>
      </p>
      <form
        v-if="s.puo_verificare && !scelte[s.id]!.rifiuto"
        class="d-flex flex-wrap align-items-end gap-3"
        @submit.prevent="conferma(s)"
      >
        <div>
          <label class="form-label small mb-0" :for="`data-${s.id}`">Giorno del pagamento</label>
          <input
            :id="`data-${s.id}`"
            v-model="scelte[s.id]!.data"
            type="date"
            class="form-control form-control-sm"
            required
          />
        </div>
        <div v-if="s.metodo === 'PAYPAL'">
          <label class="form-label small mb-0" :for="`accreditato-${s.id}`"
            >Accreditato da PayPal € (facoltativo)</label
          >
          <input
            :id="`accreditato-${s.id}`"
            v-model="scelte[s.id]!.accreditato"
            type="number"
            min="0"
            step="0.01"
            class="form-control form-control-sm"
          />
        </div>
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Conferma
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="scelte[s.id]!.rifiuto = true">
          Non lo trovo
        </button>
      </form>
      <p
        v-if="s.puo_verificare && s.metodo === 'PAYPAL' && !scelte[s.id]!.rifiuto"
        class="form-text mb-0"
      >
        Se scrivi quanto ha accreditato PayPal, la differenza va in prima nota come «Trattenuta
        PayPal».
      </p>
      <form
        v-if="s.puo_verificare && scelte[s.id]!.rifiuto"
        class="d-flex flex-wrap align-items-end gap-3"
        @submit.prevent="rifiuta(s)"
      >
        <div class="flex-grow-1">
          <label class="form-label small mb-0" :for="`motivo-${s.id}`"
            >Perché non lo confermi (lo legge la famiglia)</label
          >
          <input
            :id="`motivo-${s.id}`"
            v-model="scelte[s.id]!.motivo"
            class="form-control form-control-sm"
            required
          />
        </div>
        <button type="submit" class="btn btn-sm btn-solid theme-danger" :disabled="inCorso">
          Non confermare
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="scelte[s.id]!.rifiuto = false">
          Indietro
        </button>
      </form>
    </div>
  </section>
</template>
