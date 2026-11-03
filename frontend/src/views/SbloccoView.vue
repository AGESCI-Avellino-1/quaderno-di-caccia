<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import CampoOtp from '@/components/CampoOtp.vue'
import {
  DatiCancellati,
  LUNGHEZZA_PIN,
  PinErrato,
  biometriaAttiva,
  cambiaPin,
  cancella,
  pinValido,
  sbloccaConBiometria,
  sbloccaConPin,
  verificaScadenza,
} from '@/sicurezza/cassaforte'

const route = useRoute()
const router = useRouter()
const pin = ref('')
const errore = ref<string | null>(null)
const inCorso = ref(false)
// The PIN is 6 digits in six boxes, and unlocks at the sixth (DEC-298). A longer PIN
// chosen before goes in the old field once, then a new one of 6 digits is asked.
const pinLungo = ref(false)
const nuovoPin = ref(false)
const pinNuovo = ref('')
const conferma = ref('')

async function dopoSblocco() {
  await verificaScadenza()
  const prossima = typeof route.query.prossima === 'string' ? route.query.prossima : '/'
  await router.replace(prossima)
}

async function conPin() {
  errore.value = null
  inCorso.value = true
  try {
    await sbloccaConPin(pin.value)
    if (!pinValido(pin.value)) {
      pin.value = ''
      nuovoPin.value = true
      return
    }
    await dopoSblocco()
  } catch (e) {
    pin.value = ''
    if (e instanceof PinErrato) errore.value = e.message
    else if (!(e instanceof DatiCancellati)) errore.value = 'Sblocco non riuscito.'
    // DatiCancellati: App.vue moves to the login page with the reason.
  } finally {
    inCorso.value = false
  }
}

async function salvaNuovoPin() {
  errore.value = null
  if (!pinValido(pinNuovo.value)) {
    errore.value = `Il PIN deve avere ${LUNGHEZZA_PIN} cifre.`
    return
  }
  if (pinNuovo.value !== conferma.value) {
    errore.value = 'I due PIN non coincidono.'
    conferma.value = ''
    return
  }
  inCorso.value = true
  try {
    await cambiaPin(pinNuovo.value)
    await dopoSblocco()
  } catch {
    errore.value = 'PIN non cambiato: riprova.'
  } finally {
    inCorso.value = false
  }
}

async function conBiometria() {
  errore.value = null
  try {
    await sbloccaConBiometria()
    await dopoSblocco()
  } catch {
    errore.value = 'Impronta o volto non riconosciuti: usa il PIN.'
  }
}

async function esciECancella() {
  await cancella('uscita')
  await router.replace({ name: 'accesso' })
}
</script>

<template>
  <section class="mx-auto text-center" style="max-width: 22rem">
    <h1 class="h4 mb-5">App bloccata</h1>
    <p class="small">Inserisci il PIN per vedere i dati salvati su questo dispositivo.</p>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <form v-if="nuovoPin" class="vstack gap-3 text-start" @submit.prevent="salvaNuovoPin">
      <p class="small mb-0">
        Ora il PIN è di {{ LUNGHEZZA_PIN }} cifre: scegline uno nuovo. I dati su questo dispositivo
        restano.
      </p>
      <label class="form-label mb-0" for="pin-nuovo">Nuovo PIN</label>
      <CampoOtp
        id="pin-nuovo"
        v-model="pinNuovo"
        :lunghezza="LUNGHEZZA_PIN"
        maschera
        autocomplete="off"
      />
      <label class="form-label mb-0" for="pin-conferma">Ripeti il PIN</label>
      <CampoOtp
        id="pin-conferma"
        v-model="conferma"
        :lunghezza="LUNGHEZZA_PIN"
        maschera
        autocomplete="off"
        @completo="salvaNuovoPin"
      />
      <button class="btn btn-solid theme-primary" :disabled="inCorso">Salva il PIN</button>
    </form>
    <template v-else>
      <button
        v-if="biometriaAttiva"
        type="button"
        class="btn btn-solid theme-primary w-100 mb-5"
        @click="conBiometria"
      >
        Sblocca con impronta o volto
      </button>
      <form class="vstack gap-3" @submit.prevent="conPin">
        <input
          v-if="pinLungo"
          v-model="pin"
          class="form-control form-control-lg text-center"
          type="password"
          inputmode="numeric"
          autocomplete="off"
          placeholder="PIN"
          aria-label="PIN"
          required
        />
        <CampoOtp
          v-else
          v-model="pin"
          class="justify-content-center"
          :lunghezza="LUNGHEZZA_PIN"
          maschera
          autocomplete="off"
          aria-label="PIN"
          :disabled="inCorso"
          @completo="conPin"
        />
        <button class="btn btn-solid theme-primary" :disabled="inCorso || !pin">
          {{ inCorso ? 'Verifica…' : 'Sblocca' }}
        </button>
      </form>
      <button
        v-if="!pinLungo"
        type="button"
        class="btn btn-link btn-sm mt-3"
        @click="((pinLungo = true), (pin = ''))"
      >
        Il tuo PIN è più lungo di {{ LUNGHEZZA_PIN }} cifre?
      </button>
    </template>
    <button type="button" class="btn btn-link btn-sm mt-5" @click="esciECancella">
      Non sei tu? Esci e cancella i dati da questo dispositivo
    </button>
  </section>
</template>
