<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { allauth, flussoInSospeso, type SessioneAllauth } from '@/api/allauth'
import { useErrore } from '@/composables/useErrore'
import { MESSAGGI_CANCELLAZIONE, protetta, type MotivoCancellazione } from '@/sicurezza/cassaforte'
import { ricollegaDispositivo } from '@/sicurezza/dispositivo'
import { useSessioneStore } from '@/stores/sessione'

type Modo = 'password' | 'codice'

const route = useRoute()
const router = useRouter()
const codiceIscrizione = ref('')
const usaCodice = () =>
  router.push({ name: 'iscrizione', params: { codice: codiceIscrizione.value.trim() } })
const sessione = useSessioneStore()
const { errore, inCorso, esegui } = useErrore()

const modo = ref<Modo>('codice')
const email = ref('')
const password = ref('')
const codice = ref('')
const codiceInviato = ref(false)
const secondoFattore = ref(false)
// After a wipe (revocation, expiry, wrong PINs) App.vue sends here with the reason.
const motivo = route.query.motivo as MotivoCancellazione | undefined
const avviso = ref<string | null>((motivo && MESSAGGI_CANCELLAZIONE[motivo]) || null)

const passkeyDisponibile = typeof window !== 'undefined' && 'PublicKeyCredential' in window

async function dopoRisposta(risposta: SessioneAllauth | undefined) {
  if (!risposta) return
  if (risposta.meta?.is_authenticated) {
    // Vault still on the phone but a new server session: bind it to the same device.
    if (protetta()) await ricollegaDispositivo().catch(() => undefined)
    await sessione.carica()
    const prossima = typeof route.query.prossima === 'string' ? route.query.prossima : '/'
    await router.replace(prossima)
    return
  }
  const flusso = flussoInSospeso(risposta)
  if (flusso === 'mfa_authenticate') secondoFattore.value = true
  else if (flusso === 'verify_email')
    avviso.value = "Conferma prima l'indirizzo email con il link che ti abbiamo inviato."
  else if (flusso === 'login_by_code') codiceInviato.value = true
  else errore.value = 'Accesso non riuscito.'
}

const accedi = () => esegui(() => allauth.accedi(email.value, password.value)).then(dopoRisposta)
const chiediCodice = () => esegui(() => allauth.richiediCodice(email.value)).then(dopoRisposta)
const confermaCodice = () =>
  esegui(() => allauth.confermaCodice(codice.value.trim())).then(dopoRisposta)
const confermaTotp = () =>
  esegui(() => allauth.confermaSecondoFattore(codice.value.trim())).then(dopoRisposta)
const passkey = () => esegui(() => allauth.accediConPasskey()).then(dopoRisposta)
const provider = (nome: 'google' | 'apple') =>
  allauth.accediConProvider(nome, `${window.location.origin}/`)
</script>

<template>
  <section class="mx-auto" style="max-width: 26rem">
    <h1 class="h4 mb-5">Accedi</h1>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <div v-if="avviso" class="alert theme-info" role="status">{{ avviso }}</div>

    <form v-if="secondoFattore" class="vstack gap-3" @submit.prevent="confermaTotp">
      <label class="form-label" for="totp">Codice dell'app di autenticazione</label>
      <input
        id="totp"
        v-model="codice"
        class="form-control"
        inputmode="numeric"
        autocomplete="one-time-code"
        required
      />
      <button class="btn btn-solid theme-primary" :disabled="inCorso">Conferma</button>
    </form>

    <template v-else>
      <button
        v-if="passkeyDisponibile"
        type="button"
        class="btn btn-solid theme-primary w-100 mb-5"
        :disabled="inCorso"
        @click="passkey"
      >
        Accedi con passkey
      </button>

      <ul class="nav nav-tabs mb-5">
        <li class="nav-item">
          <button
            type="button"
            class="nav-link"
            :class="{ active: modo === 'codice' }"
            @click="modo = 'codice'"
          >
            Codice via email
          </button>
        </li>
        <li class="nav-item">
          <button
            type="button"
            class="nav-link"
            :class="{ active: modo === 'password' }"
            @click="modo = 'password'"
          >
            Password
          </button>
        </li>
      </ul>

      <form v-if="modo === 'password'" class="vstack gap-3" @submit.prevent="accedi">
        <input
          v-model="email"
          class="form-control"
          type="email"
          placeholder="Email"
          autocomplete="username"
          required
        />
        <input
          v-model="password"
          class="form-control"
          type="password"
          placeholder="Password"
          autocomplete="current-password"
          required
        />
        <button class="btn btn-solid theme-primary" :disabled="inCorso">Accedi</button>
        <RouterLink :to="{ name: 'reimposta-password' }" class="small"
          >Password dimenticata?</RouterLink
        >
      </form>

      <form v-else-if="!codiceInviato" class="vstack gap-3" @submit.prevent="chiediCodice">
        <input
          v-model="email"
          class="form-control"
          type="email"
          placeholder="Email"
          autocomplete="username"
          required
        />
        <button class="btn btn-solid theme-primary" :disabled="inCorso">Inviami il codice</button>
      </form>

      <form v-else class="vstack gap-3" @submit.prevent="confermaCodice">
        <p class="small mb-1">Abbiamo inviato un codice a {{ email }}.</p>
        <input
          v-model="codice"
          class="form-control"
          placeholder="Codice"
          autocomplete="one-time-code"
          required
        />
        <button class="btn btn-solid theme-primary" :disabled="inCorso">Accedi</button>
      </form>

      <hr />
      <div class="vstack gap-3">
        <button type="button" class="btn btn-outline theme-secondary" @click="provider('google')">
          Accedi con Google
        </button>
        <button type="button" class="btn btn-outline theme-secondary" @click="provider('apple')">
          Accedi con Apple
        </button>
      </div>
      <p class="small fg-2 mt-5 mb-1">
        Non hai un account? Ti serve un invito, oppure un codice di iscrizione dai capi.
      </p>
      <form class="d-flex gap-3" @submit.prevent="usaCodice">
        <input
          v-model="codiceIscrizione"
          class="form-control form-control-sm"
          aria-label="Codice di iscrizione"
          placeholder="Codice di iscrizione"
          autocapitalize="characters"
          required
        />
        <button type="submit" class="btn btn-sm btn-outline theme-primary">Usa</button>
      </form>
    </template>
  </section>
</template>
