<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api, type Impostazioni, type SmtpIn } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// How the emails go out, for the technical administrator: an SMTP server (DEC-277) or a
// Gmail mailbox linked once with a Google login (DEC-278). Passwords, secrets and tokens
// are encrypted on the server and never come back.
const props = defineProps<{ impostazioni: Impostazioni }>()
const emit = defineEmits<{ aggiornate: [Impostazioni] }>()
const { errore, inCorso, esegui } = useErrore()
const esito = ref('')
const route = useRoute()
const router = useRouter()

const SICUREZZE = [
  { valore: 'STARTTLS', nome: 'STARTTLS (di solito porta 587)' },
  { valore: 'SSL', nome: 'SSL/TLS (di solito porta 465)' },
  { valore: 'NESSUNA', nome: 'Nessuna (solo in una rete fidata)' },
]

const dati = reactive<SmtpIn>({
  host: '',
  porta: 587,
  sicurezza: 'STARTTLS',
  utente: '',
  password: '',
  mittente: '',
  modo: 'SMTP',
  gmail_client_id: '',
  gmail_client_secret: '',
})
function leggi(imp: Impostazioni) {
  Object.assign(dati, {
    host: imp.smtp_host ?? '',
    porta: imp.smtp_porta ?? 587,
    sicurezza: imp.smtp_sicurezza ?? 'STARTTLS',
    utente: imp.smtp_utente ?? '',
    password: '',
    mittente: imp.mittente ?? '',
    modo: imp.modo_invio ?? 'SMTP',
    gmail_client_id: imp.gmail_client_id ?? '',
    gmail_client_secret: '',
  })
}
leggi(props.impostazioni)
watch(() => props.impostazioni, leggi)

// Back from Google's login: say how it went, then clean the address.
onMounted(async () => {
  const gmail = route.query.gmail
  if (!gmail) return
  if (gmail === 'collegato') esito.value = 'Gmail collegato: manda un’email di prova.'
  else errore.value = String(route.query.motivo ?? 'Il collegamento a Gmail non è riuscito.')
  await router.replace({ query: {} })
})

async function salva() {
  esito.value = ''
  const nuove = await esegui(() => api.salvaSmtp({ ...dati }))
  if (!nuove) return
  emit('aggiornate', nuove)
  esito.value = 'Impostazioni della posta salvate.'
}

async function collega() {
  esito.value = ''
  const risposta = await esegui(() => api.collegaGmail())
  if (risposta) window.location.assign(risposta.url)
}

async function scollega() {
  esito.value = ''
  const nuove = await esegui(() => api.scollegaGmail())
  if (!nuove) return
  emit('aggiornate', nuove)
  esito.value = 'Gmail scollegato.'
}

async function prova() {
  esito.value = ''
  const risposta = await esegui(() => api.provaSmtp())
  if (risposta) esito.value = `Email di prova mandata a ${risposta.inviata_a}: controlla la posta.`
}
</script>

<template>
  <section class="mb-7">
    <h2 class="h5">Server di posta</h2>
    <p class="small fg-2">
      Da dove partono le email. Se non imposti niente vale quello configurato sul server da chi ha
      installato l'app.
    </p>
    <div v-if="!impostazioni.smtp_disponibile" class="alert theme-warning small" role="status">
      <div>
        Manca la chiave per conservare password e segreti in modo sicuro: la imposta chi ha
        installato l'app.
      </div>
    </div>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">{{ esito }}</div>
    <form class="card card-body" @submit.prevent="salva">
      <div class="row g-3">
        <fieldset class="col-12">
          <legend class="form-label small">Come partono le email</legend>
          <div class="d-flex flex-wrap gap-5">
            <div class="form-field">
              <input
                id="posta-smtp"
                v-model="dati.modo"
                type="radio"
                class="radio"
                name="posta-modo"
                value="SMTP"
              />
              <label class="small" for="posta-smtp">Server SMTP</label>
            </div>
            <div class="form-field">
              <input
                id="posta-gmail"
                v-model="dati.modo"
                type="radio"
                class="radio"
                name="posta-modo"
                value="GMAIL"
              />
              <label class="small" for="posta-gmail">Gmail con accesso Google</label>
            </div>
          </div>
        </fieldset>

        <template v-if="dati.modo === 'SMTP'">
          <p class="col-12 small fg-2 mb-0">
            Con Google Workspace o Gmail: server <code>smtp.gmail.com</code>, porta 587, STARTTLS, e
            una <strong>password per le app</strong>; con il relay SMTP di Google
            <code>smtp-relay.gmail.com</code>, porta 587, STARTTLS, senza utente né password. Con
            Microsoft 365: <code>smtp.office365.com</code>, porta 587, STARTTLS, finché il tenant
            accetta utente e password.
          </p>
          <div class="md:col-6">
            <label class="form-label small" for="smtp-host">Server</label>
            <input
              id="smtp-host"
              v-model="dati.host"
              class="form-control form-control-sm"
              autocomplete="off"
              placeholder="smtp.gmail.com"
            />
          </div>
          <div class="col-6 md:col-2">
            <label class="form-label small" for="smtp-porta">Porta</label>
            <input
              id="smtp-porta"
              v-model.number="dati.porta"
              type="number"
              min="1"
              max="65535"
              class="form-control form-control-sm"
            />
          </div>
          <div class="col-6 md:col-4">
            <label class="form-label small" for="smtp-sicurezza">Sicurezza</label>
            <select
              id="smtp-sicurezza"
              v-model="dati.sicurezza"
              class="form-control form-control-sm"
            >
              <option v-for="s in SICUREZZE" :key="s.valore" :value="s.valore">
                {{ s.nome }}
              </option>
            </select>
          </div>
          <div class="md:col-6">
            <label class="form-label small" for="smtp-utente">Utente</label>
            <input
              id="smtp-utente"
              v-model="dati.utente"
              class="form-control form-control-sm"
              autocomplete="off"
            />
          </div>
          <div class="md:col-6">
            <label class="form-label small" for="smtp-password">Password</label>
            <input
              id="smtp-password"
              v-model="dati.password"
              type="password"
              class="form-control form-control-sm"
              autocomplete="new-password"
              :placeholder="
                impostazioni.smtp_password_salvata ? 'Salvata: lascia vuoto per non cambiarla' : ''
              "
            />
          </div>
        </template>

        <template v-else>
          <p class="col-12 small fg-2 mb-0">
            Accedi una volta con l'account Google da cui partono le email: l'app chiede solo il
            permesso di inviare, senza leggere la posta. Prima crea il client OAuth in Google Cloud
            (lo spiega la guida di installazione) e registra come indirizzo di reindirizzamento
            autorizzato <code>{{ impostazioni.gmail_redirect_uri }}</code
            >.
          </p>
          <div class="md:col-6">
            <label class="form-label small" for="gmail-client">ID client OAuth</label>
            <input
              id="gmail-client"
              v-model="dati.gmail_client_id"
              class="form-control form-control-sm"
              autocomplete="off"
              placeholder="….apps.googleusercontent.com"
            />
          </div>
          <div class="md:col-6">
            <label class="form-label small" for="gmail-segreto">Segreto client</label>
            <input
              id="gmail-segreto"
              v-model="dati.gmail_client_secret"
              type="password"
              class="form-control form-control-sm"
              autocomplete="new-password"
              :placeholder="
                impostazioni.gmail_secret_salvato ? 'Salvato: lascia vuoto per non cambiarlo' : ''
              "
            />
          </div>
          <div class="col-12 small d-flex flex-wrap align-items-center gap-3">
            <template v-if="impostazioni.gmail_indirizzo">
              <span>
                Collegato a <strong>{{ impostazioni.gmail_indirizzo }}</strong>
              </span>
              <button
                type="button"
                class="btn btn-sm btn-link"
                :disabled="inCorso"
                @click="scollega"
              >
                Scollega
              </button>
            </template>
            <template v-else>
              <span class="fg-2">Nessuna casella collegata.</span>
            </template>
            <button
              type="button"
              class="btn btn-sm btn-outline theme-primary"
              :disabled="inCorso || !impostazioni.gmail_secret_salvato"
              @click="collega"
            >
              {{ impostazioni.gmail_indirizzo ? 'Collega un’altra casella' : 'Collega Gmail' }}
            </button>
            <span v-if="!impostazioni.gmail_secret_salvato" class="fg-2">
              Prima salva ID e segreto.
            </span>
          </div>
        </template>

        <div class="col-12">
          <label class="form-label small" for="smtp-mittente">Mittente</label>
          <input
            id="smtp-mittente"
            v-model="dati.mittente"
            class="form-control form-control-sm"
            :placeholder="impostazioni.mittente_predefinito"
          />
          <div class="small fg-2">
            Come «Nome &lt;indirizzo@dominio.it&gt;». Con Gmail e Microsoft 365 l'indirizzo deve
            essere quello dell'account, o un alias che l'account può usare.
          </div>
        </div>
        <div class="col-12 d-flex flex-wrap gap-3">
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Salva
          </button>
          <button
            type="button"
            class="btn btn-sm btn-outline theme-primary"
            :disabled="inCorso"
            @click="prova"
          >
            Manda un'email di prova a me
          </button>
        </div>
      </div>
    </form>
  </section>
</template>
