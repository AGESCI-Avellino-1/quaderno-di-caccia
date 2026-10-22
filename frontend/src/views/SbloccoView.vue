<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import {
  DatiCancellati,
  PinErrato,
  biometriaAttiva,
  cancella,
  sbloccaConBiometria,
  sbloccaConPin,
  verificaScadenza,
} from '@/sicurezza/cassaforte'

const route = useRoute()
const router = useRouter()
const pin = ref('')
const errore = ref<string | null>(null)
const inCorso = ref(false)

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
    <h1 class="h4 mb-3">App bloccata</h1>
    <p class="small">Inserisci il PIN per vedere i dati salvati su questo telefono.</p>
    <div v-if="errore" class="alert alert-danger" role="alert">{{ errore }}</div>
    <button
      v-if="biometriaAttiva"
      type="button"
      class="btn btn-primary w-100 mb-3"
      @click="conBiometria"
    >
      Sblocca con impronta o volto
    </button>
    <form class="vstack gap-2" @submit.prevent="conPin">
      <input
        v-model="pin"
        class="form-control form-control-lg text-center"
        type="password"
        inputmode="numeric"
        autocomplete="current-password"
        placeholder="PIN"
        aria-label="PIN"
        required
      />
      <button class="btn btn-primary" :disabled="inCorso || !pin">
        {{ inCorso ? 'Verifica…' : 'Sblocca' }}
      </button>
    </form>
    <button type="button" class="btn btn-link btn-sm mt-3" @click="esciECancella">
      Non sei tu? Esci e cancella i dati da questo telefono
    </button>
  </section>
</template>
