<script setup lang="ts">
import { WebAuthnError } from '@simplewebauthn/browser'
import { onMounted, ref, watch } from 'vue'

import { passkey, RiautenticazioneRichiesta, type Passkey } from '@/api/allauth'
import CampoPassword from '@/components/CampoPassword.vue'
import { testoErrore } from '@/composables/useErrore'
import {
  base64url,
  dimenticaCredenziale,
  passkeyGiaSulDispositivo,
  SbloccoNonDisponibile,
} from '@/sicurezza/biometria'
import {
  attivaBiometria,
  biometriaAttiva,
  credenzialeDiSblocco,
  disattivaBiometria,
  protetta,
  sbloccata,
} from '@/sicurezza/cassaforte'

// Login passkeys (DEC-22, DEC-240): created here, used with "Accedi con passkey". The one
// created on this device, when its data are protected and unlocked, also unlocks them with
// fingerprint or face (DEC-295): one passkey per device.
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

/** base64url of the passkey that unlocks this device, if any. */
const sblocca = () => {
  if (!biometriaAttiva.value) return null
  const id = credenzialeDiSblocco()
  return id ? base64url(id) : null
}

async function crea() {
  const nomePasskey = nome.value.trim() || props.nomePredefinito
  if (!(protetta() && sbloccata())) {
    let giaPresente = false
    await esegui(async () => {
      try {
        await passkey.crea(nomePasskey)
      } catch (e) {
        // Synced from another device of the same person (DEC-388): nothing to create.
        if (!passkeyGiaSulDispositivo(e)) throw e
        giaPresente = true
      }
    }, 'Passkey creata: la prossima volta tocca «Accedi con passkey».')
    if (giaPresente) {
      fatto.value =
        'Su questo dispositivo c’è già una passkey del tuo account: tocca «Accedi con passkey».'
    }
    return
  }
  let senzaSblocco: string | null = null
  let esistente = false
  await esegui(async () => {
    try {
      esistente = await attivaBiometria(undefined, nomePasskey)
    } catch (e) {
      // Created, but it cannot unlock here: it still lets you in.
      if (!(e instanceof SbloccoNonDisponibile)) throw e
      senzaSblocco = e.message
    }
  }, 'Passkey creata: ti fa entrare con «Accedi con passkey» e sblocca l’app su questo dispositivo.')
  if (senzaSblocco) fatto.value = senzaSblocco
  else if (esistente) {
    fatto.value =
      'Su questo dispositivo c’era già una passkey del tuo account: ora sblocca anche l’app qui.'
  }
}

const inRinomina = ref<{ id: number; nome: string } | null>(null)

async function rinomina() {
  const scelta = inRinomina.value
  if (!scelta?.nome.trim()) return
  await esegui(async () => {
    await passkey.rinomina(scelta.id, scelta.nome.trim())
    inRinomina.value = null
  }, 'Nome cambiato.')
}

const rimuovi = (p: Passkey) =>
  esegui(async () => {
    const eraSblocco = p.id_credenziale !== undefined && p.id_credenziale === sblocca()
    await passkey.rimuovi(p.id)
    if (eraSblocco) await disattivaBiometria()
    // No longer valid to log in: the password manager would keep offering it.
    if (p.id_credenziale) void dimenticaCredenziale(p.id_credenziale)
  }, 'Passkey rimossa. Se sbloccava questo dispositivo, ora si sblocca con il PIN.')

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
      password, e, se i dati di questo dispositivo sono protetti, li sblocchi allo stesso modo. Il
      codice via email resta sempre una via d'accesso.
    </p>
    <p v-if="!disponibile" class="small fg-2 mb-0">Questo browser non gestisce le passkey.</p>
    <template v-else>
      <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
      <div v-if="fatto" class="alert theme-success small" role="status">{{ fatto }}</div>

      <form v-if="conferma" class="vstack gap-3" @submit.prevent="confermaCon('password')">
        <p class="small mb-0">Per sicurezza, conferma che sei tu.</p>
        <template v-if="conferma.conPassword">
          <label class="form-label mb-0" for="password-conferma">La tua password</label>
          <CampoPassword
            id="password-conferma"
            v-model="password"
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
              <span
                v-if="p.id_credenziale && p.id_credenziale === sblocca()"
                class="badge theme-primary"
                >sblocca questo dispositivo</span
              >
              <span class="small fg-2 ms-auto">
                creata il {{ data(p.created_at) }}
                <template v-if="p.last_used_at"> · usata il {{ data(p.last_used_at) }}</template>
              </span>
            </div>
            <div class="mt-3">
              <form
                v-if="inRinomina?.id === p.id"
                class="d-flex flex-wrap align-items-end gap-3"
                @submit.prevent="rinomina"
              >
                <div>
                  <label class="form-label small mb-0" :for="`rinomina-${p.id}`">Nuovo nome</label>
                  <input
                    :id="`rinomina-${p.id}`"
                    v-model="inRinomina.nome"
                    class="form-control form-control-sm"
                    maxlength="100"
                    required
                  />
                </div>
                <button class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
                  Salva
                </button>
                <button type="button" class="btn btn-sm btn-link" @click="inRinomina = null">
                  Annulla
                </button>
              </form>
              <template v-else-if="daRimuovere === p.id">
                <span class="small me-3">
                  Non potrai più entrare con questa passkey, né sbloccare con lei l'app. Se è
                  sincronizzata, smette di funzionare anche sugli altri tuoi dispositivi.
                </span>
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
              <div v-else class="d-flex flex-wrap gap-3">
                <button
                  type="button"
                  class="btn btn-sm btn-outline theme-primary"
                  @click="inRinomina = { id: p.id, nome: p.name }"
                >
                  Rinomina…
                </button>
                <button
                  type="button"
                  class="btn btn-sm btn-outline theme-danger"
                  @click="daRimuovere = p.id"
                >
                  Rimuovi…
                </button>
              </div>
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
