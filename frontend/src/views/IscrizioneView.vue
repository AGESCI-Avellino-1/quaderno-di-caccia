<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { allauth, flussoInSospeso } from '@/api/allauth'
import { api, type InfoCodice } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'
import { useSessioneStore } from '@/stores/sessione'

// Joining from the app with a registration code (QR code, link or typed). A parent
// registers a minor; an adult registers themself. Without an account, the request is
// kept by the server in this browser session and becomes real when the account is
// created. Only the essentials here: the rest after the approval.
const props = defineProps<{ codice: string }>()
const router = useRouter()
const sessione = useSessioneStore()
const { errore, inCorso, esegui } = useErrore()

const info = ref<InfoCodice | null>(null)
const chi = ref<'figlio' | 'io'>('figlio')
const dati = reactive({
  nome: '',
  cognome: '',
  data_nascita: '',
  codice_fiscale: '',
  email: '',
  genitore_nome: '',
  genitore_cognome: '',
  genitore_codice_fiscale: '',
})
const account = reactive({ email: '', password: '' })
const verificaInviata = ref(false)
// Local date as YYYY-MM-DD (toISOString would give the UTC day around midnight).
const oggi = new Date().toLocaleDateString('sv')

onMounted(async () => {
  if (!sessione.pronta) await sessione.carica()
  info.value = (await esegui(() => api.infoCodice(props.codice))) ?? null
  if (info.value?.per_capi) chi.value = 'io'
  const persona = sessione.profilo?.persona
  if (persona)
    Object.assign(dati, { genitore_nome: persona.nome, genitore_cognome: persona.cognome })
})

const perFiglio = computed(() => chi.value === 'figlio')

async function invia() {
  const corpo = perFiglio.value
    ? { ...dati, email: '' }
    : {
        ...dati,
        email: account.email,
        genitore_nome: '',
        genitore_cognome: '',
        genitore_codice_fiscale: '',
      }
  const esito = await esegui(() => api.chiediIscrizione(props.codice, corpo))
  if (!esito) return
  if (!esito.serve_account) {
    await sessione.carica()
    await router.replace('/mia-iscrizione')
    return
  }
  const risposta = await esegui(() => allauth.registrati(account.email, account.password))
  if (!risposta) return
  if (risposta.meta?.is_authenticated) {
    await sessione.carica()
    await router.replace('/mia-iscrizione')
  } else if (flussoInSospeso(risposta) === 'verify_email') {
    verificaInviata.value = true
  }
}
</script>

<template>
  <section class="mx-auto" style="max-width: 32rem">
    <h1 class="h4 mb-3">Iscrizione</h1>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <div v-if="verificaInviata" class="alert theme-success" role="status">
      <div>
        Richiesta inviata. Ti abbiamo mandato un'email: apri il link per confermare l'indirizzo. Poi
        i capi dell'unità esamineranno la richiesta.
      </div>
    </div>

    <form v-else-if="info" class="vstack gap-3" @submit.prevent="invia">
      <p class="mb-0">
        Iscrizione a <strong>{{ info.unita }}</strong
        >.
        <template v-if="info.per_capi">Riservata ai capi.</template>
      </p>

      <fieldset v-if="!info.per_capi">
        <legend class="form-label small">Chi iscrivi?</legend>
        <div class="d-flex flex-wrap gap-5">
          <div class="form-field">
            <input id="chi-figlio" v-model="chi" type="radio" class="radio" value="figlio" />
            <label for="chi-figlio">Mio figlio o mia figlia</label>
          </div>
          <div class="form-field">
            <input id="chi-io" v-model="chi" type="radio" class="radio" value="io" />
            <label for="chi-io">Me stesso (maggiorenne)</label>
          </div>
        </div>
      </fieldset>

      <fieldset class="card card-body vstack gap-3">
        <legend class="h6">{{ perFiglio ? 'Il ragazzo o la ragazza' : 'I tuoi dati' }}</legend>
        <div class="row g-3">
          <div class="col-12 sm:col-6">
            <label class="form-label small" for="isc-nome">Nome</label>
            <input id="isc-nome" v-model="dati.nome" class="form-control" required />
          </div>
          <div class="col-12 sm:col-6">
            <label class="form-label small" for="isc-cognome">Cognome</label>
            <input id="isc-cognome" v-model="dati.cognome" class="form-control" required />
          </div>
          <div class="col-12 sm:col-6">
            <label class="form-label small" for="isc-nascita">Data di nascita</label>
            <input
              id="isc-nascita"
              v-model="dati.data_nascita"
              type="date"
              class="form-control"
              :max="oggi"
              required
            />
          </div>
          <div class="col-12 sm:col-6">
            <label class="form-label small" for="isc-cf">Codice fiscale</label>
            <input
              id="isc-cf"
              v-model="dati.codice_fiscale"
              class="form-control"
              maxlength="16"
              autocapitalize="characters"
              required
            />
          </div>
        </div>
      </fieldset>

      <fieldset v-if="perFiglio" class="card card-body vstack gap-3">
        <legend class="h6">Tu, il genitore</legend>
        <div class="row g-3">
          <div class="col-12 sm:col-6">
            <label class="form-label small" for="gen-nome">Nome</label>
            <input id="gen-nome" v-model="dati.genitore_nome" class="form-control" required />
          </div>
          <div class="col-12 sm:col-6">
            <label class="form-label small" for="gen-cognome">Cognome</label>
            <input id="gen-cognome" v-model="dati.genitore_cognome" class="form-control" required />
          </div>
          <div class="col-12">
            <label class="form-label small" for="gen-cf">Il tuo codice fiscale</label>
            <input
              id="gen-cf"
              v-model="dati.genitore_codice_fiscale"
              class="form-control"
              maxlength="16"
              autocapitalize="characters"
              required
            />
          </div>
        </div>
      </fieldset>

      <fieldset v-if="!sessione.autenticato" class="card card-body vstack gap-3">
        <legend class="h6">Il tuo account</legend>
        <p class="form-text mb-0">
          Con questo account segui l'iscrizione e, dopo l'approvazione, completi dati e moduli.
          <template v-if="perFiglio">Usa la tua email, non quella del figlio.</template>
        </p>
        <div>
          <label class="form-label small" for="acc-email">Email</label>
          <input
            id="acc-email"
            v-model="account.email"
            type="email"
            class="form-control"
            autocomplete="email"
            required
          />
        </div>
        <div>
          <label class="form-label small" for="acc-password">Scegli una password</label>
          <input
            id="acc-password"
            v-model="account.password"
            type="password"
            class="form-control"
            autocomplete="new-password"
            required
          />
        </div>
      </fieldset>

      <p class="form-text mb-0">
        Gli altri dati e i moduli firmati si completano dopo che i capi hanno accolto la richiesta.
      </p>
      <button type="submit" class="btn btn-solid theme-primary" :disabled="inCorso">
        Invia la richiesta
      </button>
    </form>
  </section>
</template>
