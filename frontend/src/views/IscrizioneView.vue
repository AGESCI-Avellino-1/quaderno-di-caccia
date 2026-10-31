<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { allauth, flussoInSospeso } from '@/api/allauth'
import { api, type InfoCodice } from '@/api/qdc'
import CampoCodiceFiscale from '@/components/CampoCodiceFiscale.vue'
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
const dati = reactive({
  nome: '',
  cognome: '',
  data_nascita: '',
  codice_fiscale: '',
  email: '',
  genitore_nome: '',
  genitore_cognome: '',
  genitore_codice_fiscale: '',
  // Asked at once since DEC-264: sex, who holds the parental responsibility, contacts.
  sesso: '',
  luogo_nascita: '',
  responsabilita: '' as '' | 'GENITORI' | 'UNICO_GENITORE' | 'TUTORE',
  genitore_cellulare: '',
  altro_nome: '',
  altro_cognome: '',
  altro_codice_fiscale: '',
  altro_cellulare: '',
  altro_email: '',
})
const account = reactive({ email: '', password: '' })
const verificaInviata = ref(false)
// Local date as YYYY-MM-DD (toISOString would give the UTC day around midnight).
const oggi = new Date().toLocaleDateString('sv')

onMounted(async () => {
  if (!sessione.pronta) await sessione.carica()
  info.value = (await esegui(() => api.infoCodice(props.codice))) ?? null
  const persona = sessione.profilo?.persona
  if (persona)
    Object.assign(dati, { genitore_nome: persona.nome, genitore_cognome: persona.cognome })
  // From the waiting list (DEC-261): what the family wrote there.
  const p = info.value?.proposti
  if (p?.nome) {
    Object.assign(dati, {
      nome: p.nome,
      cognome: p.cognome ?? '',
      data_nascita: p.data_nascita ?? '',
      sesso: p.sesso ?? '',
      luogo_nascita: p.luogo_nascita ?? '',
      genitore_cellulare: p.da_se ? '' : (p.telefono ?? ''),
      ...(p.da_se
        ? { email: p.email ?? '' }
        : { genitore_nome: p.contatto_nome ?? '', genitore_cognome: p.contatto_cognome ?? '' }),
    })
    account.email ||= p.email ?? ''
  }
})

// Who fills in depends on the age, not on a choice (DEC-121): a parent for a minor, the
// adult themself; the Co.Ca. only adults.
const maggiorenne = computed(() => {
  if (!dati.data_nascita) return false
  const nascita = new Date(dati.data_nascita)
  return new Date(nascita.getFullYear() + 18, nascita.getMonth(), nascita.getDate()) <= new Date()
})
const perFiglio = computed(() => !info.value?.per_capi && !maggiorenne.value)
// A personal link from the waiting list is for one person: who it is cannot change.
const bloccato = computed(() => !!info.value?.proposti?.nome)

async function invia() {
  const corpo = perFiglio.value
    ? { ...dati, email: '' }
    : {
        ...dati,
        email: account.email,
        genitore_nome: '',
        genitore_cognome: '',
        genitore_codice_fiscale: '',
        responsabilita: '' as const,
        genitore_cellulare: '',
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

      <p v-if="!info.per_capi && !bloccato" class="small fg-2">
        Per un minorenne compila un genitore; chi è maggiorenne si iscrive da sé.
      </p>

      <fieldset class="card card-body vstack gap-3">
        <legend class="h6">{{ perFiglio ? 'Il ragazzo o la ragazza' : 'I tuoi dati' }}</legend>
        <div class="row g-3">
          <div class="col-12 sm:col-6">
            <label class="form-label small" for="isc-nome">Nome</label>
            <input
              id="isc-nome"
              v-model="dati.nome"
              class="form-control"
              :readonly="bloccato"
              required
            />
          </div>
          <div class="col-12 sm:col-6">
            <label class="form-label small" for="isc-cognome">Cognome</label>
            <input
              id="isc-cognome"
              v-model="dati.cognome"
              class="form-control"
              :readonly="bloccato"
              required
            />
          </div>
          <div class="col-12 sm:col-6">
            <label class="form-label small" for="isc-nascita">Data di nascita</label>
            <input
              id="isc-nascita"
              v-model="dati.data_nascita"
              type="date"
              :readonly="bloccato"
              class="form-control"
              :max="oggi"
              required
            />
          </div>
          <div class="col-12 sm:col-6">
            <label class="form-label small" for="isc-sesso">Sesso</label>
            <select id="isc-sesso" v-model="dati.sesso" class="form-control" required>
              <option value="" disabled>Scegli</option>
              <option value="F">Femmina</option>
              <option value="M">Maschio</option>
            </select>
          </div>
          <div class="col-12 sm:col-6">
            <label class="form-label small" for="isc-luogo">Comune di nascita</label>
            <input id="isc-luogo" v-model="dati.luogo_nascita" class="form-control" />
          </div>
          <div class="col-12 sm:col-6">
            <CampoCodiceFiscale
              id="isc-cf"
              v-model="dati.codice_fiscale"
              etichetta="Codice fiscale"
              :nome="dati.nome"
              :cognome="dati.cognome"
              :sesso="dati.sesso"
              :data-nascita="dati.data_nascita"
              :luogo-nascita="dati.luogo_nascita"
              obbligatorio
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
          <div class="col-12 sm:col-6">
            <CampoCodiceFiscale
              id="gen-cf"
              v-model="dati.genitore_codice_fiscale"
              etichetta="Il tuo codice fiscale"
              :nome="dati.genitore_nome"
              :cognome="dati.genitore_cognome"
              obbligatorio
            />
          </div>
          <div class="col-12 sm:col-6">
            <label class="form-label small" for="gen-cell">Il tuo telefono</label>
            <input
              id="gen-cell"
              v-model="dati.genitore_cellulare"
              type="tel"
              autocomplete="tel"
              class="form-control"
              required
            />
          </div>
        </div>
        <div>
          <span class="form-label small d-block">Chi ha la responsabilità genitoriale?</span>
          <div class="form-field">
            <input
              id="resp-genitori"
              v-model="dati.responsabilita"
              class="radio"
              type="radio"
              value="GENITORI"
              required
            />
            <label for="resp-genitori">Entrambi i genitori</label>
          </div>
          <div class="form-field">
            <input
              id="resp-unico"
              v-model="dati.responsabilita"
              class="radio"
              type="radio"
              value="UNICO_GENITORE"
            />
            <label for="resp-unico">Solo io (genitore con affidamento esclusivo)</label>
          </div>
          <div class="form-field">
            <input
              id="resp-tutore"
              v-model="dati.responsabilita"
              class="radio"
              type="radio"
              value="TUTORE"
            />
            <label for="resp-tutore">Io, come tutore</label>
          </div>
        </div>
      </fieldset>

      <fieldset
        v-if="perFiglio && dati.responsabilita === 'GENITORI'"
        class="card card-body vstack gap-3"
      >
        <legend class="h6">L'altro genitore</legend>
        <div class="row g-3">
          <div class="col-12 sm:col-6">
            <label class="form-label small" for="altro-nome">Nome</label>
            <input id="altro-nome" v-model="dati.altro_nome" class="form-control" required />
          </div>
          <div class="col-12 sm:col-6">
            <label class="form-label small" for="altro-cognome">Cognome</label>
            <input id="altro-cognome" v-model="dati.altro_cognome" class="form-control" required />
          </div>
          <div class="col-12 sm:col-6">
            <CampoCodiceFiscale
              id="altro-cf"
              v-model="dati.altro_codice_fiscale"
              etichetta="Codice fiscale"
              :nome="dati.altro_nome"
              :cognome="dati.altro_cognome"
              obbligatorio
            />
          </div>
          <div class="col-12 sm:col-6">
            <label class="form-label small" for="altro-cell">Telefono</label>
            <input
              id="altro-cell"
              v-model="dati.altro_cellulare"
              type="tel"
              class="form-control"
              required
            />
          </div>
          <div class="col-12">
            <label class="form-label small" for="altro-email">Email</label>
            <input
              id="altro-email"
              v-model="dati.altro_email"
              type="email"
              class="form-control"
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
        Residenza, luogo di nascita e moduli firmati si completano dopo che i capi hanno accolto la
        richiesta.
      </p>
      <button type="submit" class="btn btn-solid theme-primary" :disabled="inCorso">
        Invia la richiesta
      </button>
    </form>
  </section>
</template>
