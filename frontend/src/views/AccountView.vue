<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  api,
  type AccountPiattaforma,
  type AzioneAccountFatta,
  type TipoAzioneAccount,
} from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Every account of the platform, for the technical administrator (DEC-313): what it has
// and what may be done to it. Every action asks a reason; the person is told by email when
// the address or the ways in change or the account is deleted. No data of the person's
// file: deleting an account removes only the way in.
const { errore, inCorso, esegui } = useErrore()
const account = ref<AccountPiattaforma[] | null>(null)
const azioni = ref<AzioneAccountFatta[]>([])
const cerca = ref('')
const aperto = ref<number | null>(null)
const tipo = ref<TipoAzioneAccount | ''>('')
const motivo = ref('')
const nuovaEmail = ref('')
const esito = ref('')

async function carica() {
  account.value = (await esegui(() => api.accountPiattaforma(cerca.value))) ?? account.value
  azioni.value = (await esegui(() => api.azioniAccount())) ?? azioni.value
}
onMounted(carica)

const AZIONI: {
  tipo: TipoAzioneAccount
  nome: string
  quando: (a: AccountPiattaforma) => boolean
}[] = [
  { tipo: 'SBLOCCA', nome: 'Sblocca i tentativi di accesso', quando: (a) => a.bloccato },
  { tipo: 'DISATTIVA', nome: 'Disattiva l’account', quando: (a) => a.attivo },
  { tipo: 'RIATTIVA', nome: 'Riattiva l’account', quando: (a) => !a.attivo },
  { tipo: 'CAMBIA_EMAIL', nome: 'Cambia l’email', quando: () => true },
  { tipo: 'REVOCA_DISPOSITIVI', nome: 'Revoca i dispositivi', quando: (a) => a.dispositivi > 0 },
  { tipo: 'TOGLI_PASSKEY', nome: 'Togli le passkey', quando: (a) => a.passkey > 0 },
  {
    tipo: 'TOGLI_SECONDO_FATTORE',
    nome: 'Togli il secondo fattore',
    quando: (a) => a.secondo_fattore,
  },
  { tipo: 'CANCELLA', nome: 'Cancella l’account', quando: () => true },
]

// What the person will be told, so the administrator knows before confirming.
const AVVISA = new Set<TipoAzioneAccount>([
  'CAMBIA_EMAIL',
  'TOGLI_PASSKEY',
  'TOGLI_SECONDO_FATTORE',
  'CANCELLA',
])

function apri(a: AccountPiattaforma) {
  aperto.value = aperto.value === a.id ? null : a.id
  tipo.value = ''
  motivo.value = ''
  nuovaEmail.value = ''
  esito.value = ''
}

const pronta = computed(
  () =>
    !!tipo.value &&
    !!motivo.value.trim() &&
    (tipo.value !== 'CAMBIA_EMAIL' || !!nuovaEmail.value.trim()),
)

async function conferma(a: AccountPiattaforma) {
  if (!tipo.value) return
  const scelta = AZIONI.find((x) => x.tipo === tipo.value)!
  const elenco = await esegui(() =>
    api.azioneAccount(a.id, tipo.value as TipoAzioneAccount, motivo.value, nuovaEmail.value),
  )
  if (!elenco) return
  account.value = cerca.value ? elenco.filter((x) => x.email.includes(cerca.value)) : elenco
  azioni.value = (await esegui(() => api.azioniAccount())) ?? azioni.value
  esito.value = `${scelta.nome}: fatto per ${a.email}.`
  aperto.value = null
}

function metodi(a: AccountPiattaforma): string {
  const elenco = [
    a.password && 'password',
    a.passkey && (a.passkey === 1 ? '1 passkey' : `${a.passkey} passkey`),
    a.secondo_fattore && 'secondo fattore',
    ...a.accessi_esterni.map((p) => (p === 'google' ? 'Google' : p === 'apple' ? 'Apple' : p)),
  ].filter(Boolean)
  return elenco.length ? elenco.join(', ') : 'solo codice via email'
}

const data = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString('it-IT', { dateStyle: 'short', timeStyle: 'short' }) : 'mai'
</script>

<template>
  <h1 class="h4">Account</h1>
  <p class="small fg-2">
    Tutti gli account dell'app, senza i dati delle schede. Ogni azione chiede un motivo e resta nel
    registro delle modifiche. Cancellare un account toglie solo l'accesso: la persona e i suoi dati
    restano.
  </p>
  <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
  <div v-if="esito" class="alert theme-success small" role="status">
    <div>{{ esito }}</div>
  </div>
  <form class="d-flex gap-3 mb-5" role="search" @submit.prevent="carica">
    <label for="account-cerca" class="visually-hidden">Cerca per email</label>
    <input
      id="account-cerca"
      v-model="cerca"
      type="search"
      class="form-control"
      placeholder="Cerca per email"
    />
    <button type="submit" class="btn btn-outline theme-primary" :disabled="inCorso">Cerca</button>
  </form>
  <p v-if="account && !account.length" class="fg-2">Nessun account.</p>
  <ul v-else-if="account" class="list-group mb-7">
    <li v-for="a in account" :key="a.id" class="list-group-item">
      <div class="d-flex flex-wrap align-items-center gap-3">
        <strong class="text-break">{{ a.email }}</strong>
        <span v-if="!a.attivo" class="badge theme-danger">Disattivato</span>
        <span v-if="a.bloccato" class="badge theme-warning">Bloccato</span>
        <span v-if="a.amministratore_tecnico" class="badge theme-secondary">
          Amministratore tecnico
        </span>
        <button
          type="button"
          class="btn btn-link btn-sm p-0 ms-auto"
          :aria-expanded="aperto === a.id"
          @click="apri(a)"
        >
          {{ aperto === a.id ? 'Chiudi' : 'Gestisci' }}
        </button>
      </div>
      <div class="small fg-2">
        {{ a.persona ? `${a.persona.nome} ${a.persona.cognome}` : 'Nessuna persona collegata' }}
        · entra con: {{ metodi(a) }} · dispositivi: {{ a.dispositivi }}
      </div>
      <div class="small fg-2">
        Creato il {{ data(a.creato_il) }} · ultimo accesso {{ data(a.ultimo_accesso) }}
      </div>
      <form v-if="aperto === a.id" class="mt-3" @submit.prevent="conferma(a)">
        <div class="row g-3">
          <div class="col-12 md:col-6">
            <label :for="`azione-${a.id}`" class="form-label small">Cosa fare</label>
            <select :id="`azione-${a.id}`" v-model="tipo" class="form-control form-control-sm">
              <option value="" disabled>Scegli…</option>
              <option v-for="x in AZIONI.filter((x) => x.quando(a))" :key="x.tipo" :value="x.tipo">
                {{ x.nome }}
              </option>
            </select>
          </div>
          <div v-if="tipo === 'CAMBIA_EMAIL'" class="col-12 md:col-6">
            <label :for="`email-${a.id}`" class="form-label small">Nuovo indirizzo</label>
            <input
              :id="`email-${a.id}`"
              v-model="nuovaEmail"
              type="email"
              class="form-control form-control-sm"
              autocomplete="off"
            />
          </div>
          <div class="col-12">
            <label :for="`motivo-${a.id}`" class="form-label small">Motivo</label>
            <input
              :id="`motivo-${a.id}`"
              v-model="motivo"
              class="form-control form-control-sm"
              maxlength="500"
              placeholder="Per esempio: telefono perso, chiesto dalla persona"
            />
          </div>
        </div>
        <p v-if="tipo === 'CANCELLA'" class="small mt-3 mb-0">
          L'account sparisce con le sue passkey, i dispositivi e le sessioni. Per entrare di nuovo
          servirà un nuovo invito.
        </p>
        <p v-if="tipo && AVVISA.has(tipo)" class="small fg-2 mt-3 mb-0">
          La persona riceverà un'email che le dice cosa è cambiato.
        </p>
        <button
          type="submit"
          class="btn btn-solid btn-sm mt-3"
          :class="tipo === 'CANCELLA' || tipo === 'DISATTIVA' ? 'theme-danger' : 'theme-primary'"
          :disabled="inCorso || !pronta"
        >
          Conferma
        </button>
      </form>
    </li>
  </ul>
  <h2 class="h5">Ultime azioni</h2>
  <p v-if="!azioni.length" class="small fg-2">Nessuna azione finora.</p>
  <ul v-else class="list-unstyled small">
    <li v-for="(x, n) in azioni" :key="n" class="py-1 border-bottom">
      <strong>{{ x.tipo_nome }}</strong> · {{ x.email }}
      <template v-if="x.dettaglio"> → {{ x.dettaglio }}</template>
      <div class="fg-2">
        {{ data(x.creato_il) }}, {{ x.fatta_da || 'account cancellato' }}: {{ x.motivo }}
      </div>
    </li>
  </ul>
</template>
