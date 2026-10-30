<script setup lang="ts">
import { WebAuthnError } from '@simplewebauthn/browser'
import { onMounted, ref, watch } from 'vue'

import { passkey, RiautenticazioneRichiesta, type Passkey } from '@/api/allauth'
import { testoErrore } from '@/composables/useErrore'

// Login passkeys (DEC-22, DEC-240): created here, used with "Accedi con passkey". Separate from
// the local passkey that unlocks the data on this phone (biometria.ts).
const props = defineProps<{ nomePredefinito: string }>()

const disponibile = typeof window !== 'undefined' && 'PublicKeyCredential' in window
const elenco = ref<Passkey[]>([])
const nome = ref('')
const inCorso = ref(false)
const errore = ref<string | null>(null)
const fatto = ref<string | null>(null)
const daRimuovere = ref<number | null>(null)
// allauth asks to confirm who you are before adding or removing a passkey.
const conferma = ref<RiautenticazioneRichiesta | null>(null)
const password = ref('')
let dopoConferma: (() => Promise<void>) | null = null

function testo(e: unknown): string {
  if (e instanceof WebAuthnError && e.code === 'ERROR_AUTHENTICATOR_PREVIOUSLY_REGISTERED') {
    return 'Su questo dispositivo c’è già una passkey per il tuo account.'
  }
  if (e instanceof Error && (e.name === 'NotAllowedError' || e.name === 'AbortError')) {
    return 'Operazione annullata.'
  }
  if (e instanceof WebAuthnError) return 'Il dispositivo non ha creato la passkey.'
  return testoErrore(e)
}

async function esegui(azione: () => Promise<void>, messaggio: string) {
  errore.value = null
  fatto.value = null
  inCorso.value = true
  try {
    await azione()
    fatto.value = messaggio
    daRimuovere.value = null
    await carica()
  } catch (e) {
    if (e instanceof RiautenticazioneRichiesta) {
      conferma.value = e
      dopoConferma = () => esegui(azione, messaggio)
    } else {
      errore.value = testo(e)
    }
  } finally {
    inCorso.value = false
  }
}

async function carica() {
  try {
    elenco.value = await passkey.elenco()
  } catch (e) {
    errore.value = testo(e)
  }
}

onMounted(() => {
  nome.value = props.nomePredefinito
  if (disponibile) void carica()
})
// The device name arrives later: it replaces the default, never what was typed.
watch(
  () => props.nomePredefinito,
  (nuovo, vecchio) => {
    if (nome.value === vecchio) nome.value = nuovo
  },
)

const crea = () =>
  esegui(
    () => passkey.crea(nome.value.trim() || props.nomePredefinito),
    'Passkey creata: la prossima volta tocca «Accedi con passkey».',
  )

const rimuovi = (p: Passkey) =>
  esegui(async () => {
    await passkey.rimuovi(p.id)
  }, 'Passkey rimossa.')

async function confermaCon(modo: 'password' | 'passkey') {
  errore.value = null
  inCorso.value = true
  try {
    if (modo === 'password') await passkey.riautenticaConPassword(password.value)
    else await passkey.riautenticaConPasskey()
  } catch (e) {
    errore.value = testo(e)
    return
  } finally {
    inCorso.value = false
  }
  conferma.value = null
  password.value = ''
  const azione = dopoConferma
  dopoConferma = null
  await azione?.()
}

function annullaConferma() {
  conferma.value = null
  password.value = ''
  dopoConferma = null
}

const data = (secondi: number) => new Date(secondi * 1000).toLocaleDateString('it-IT')
</script>

<template>
  <div class="card card-body mb-5">
    <h2 class="h6">Passkey per entrare</h2>
    <p class="small mb-3">
      Con una passkey entri con l'impronta, il volto o il blocco schermo del dispositivo, senza
      password. Il codice via email resta sempre una via d'accesso.
    </p>
    <p v-if="!disponibile" class="small fg-2 mb-0">Questo browser non gestisce le passkey.</p>
    <template v-else>
      <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
      <div v-if="fatto" class="alert theme-success small" role="status">{{ fatto }}</div>

      <form v-if="conferma" class="vstack gap-3" @submit.prevent="confermaCon('password')">
        <p class="small mb-0">Per sicurezza, conferma che sei tu.</p>
        <template v-if="conferma.conPassword">
          <label class="form-label mb-0" for="password-conferma">La tua password</label>
          <input
            id="password-conferma"
            v-model="password"
            class="form-control"
            type="password"
            autocomplete="current-password"
            required
          />
        </template>
        <div class="d-flex flex-wrap gap-3">
          <button
            v-if="conferma.conPassword"
            class="btn btn-sm btn-solid theme-primary"
            :disabled="inCorso"
          >
            Conferma
          </button>
          <button
            v-if="conferma.conPasskey"
            type="button"
            class="btn btn-sm btn-outline theme-primary"
            :disabled="inCorso"
            @click="confermaCon('passkey')"
          >
            Conferma con una passkey
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="annullaConferma">
            Annulla
          </button>
        </div>
        <p v-if="!conferma.conPassword && !conferma.conPasskey" class="small fg-2 mb-0">
          Esci e rientra, poi riprova entro cinque minuti.
        </p>
      </form>

      <template v-else>
        <ul v-if="elenco.length" class="list-group mb-3">
          <li v-for="p in elenco" :key="p.id" class="list-group-item">
            <div class="d-flex flex-wrap align-items-center gap-3">
              <strong>{{ p.name }}</strong>
              <span class="small fg-2 ms-auto">
                creata il {{ data(p.created_at) }}
                <template v-if="p.last_used_at"> · usata il {{ data(p.last_used_at) }}</template>
              </span>
            </div>
            <div class="mt-3">
              <template v-if="daRimuovere === p.id">
                <span class="small me-3">Non potrai più entrare con questa passkey.</span>
                <button
                  type="button"
                  class="btn btn-sm btn-solid theme-danger me-1"
                  :disabled="inCorso"
                  @click="rimuovi(p)"
                >
                  Rimuovi
                </button>
                <button type="button" class="btn btn-sm btn-link" @click="daRimuovere = null">
                  Annulla
                </button>
              </template>
              <button
                v-else
                type="button"
                class="btn btn-sm btn-outline theme-danger"
                @click="daRimuovere = p.id"
              >
                Rimuovi…
              </button>
            </div>
          </li>
        </ul>
        <form class="vstack gap-3" @submit.prevent="crea">
          <label class="form-label mb-0" for="nome-passkey">Nome della nuova passkey</label>
          <input id="nome-passkey" v-model="nome" class="form-control" maxlength="100" />
          <div>
            <button class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
              Crea una passkey su questo dispositivo
            </button>
          </div>
        </form>
      </template>
    </template>
  </div>
</template>
