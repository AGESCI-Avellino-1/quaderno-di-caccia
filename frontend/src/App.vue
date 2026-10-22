<script setup lang="ts">
import { onBeforeUnmount } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'

import AggiornamentoApp from '@/components/AggiornamentoApp.vue'
import BarraOffline from '@/components/BarraOffline.vue'
import { useBloccoAutomatico } from '@/composables/useBloccoAutomatico'
import {
  EVENTO_CANCELLAZIONE,
  blocca,
  stato,
  type MotivoCancellazione,
} from '@/sicurezza/cassaforte'
import { useSessioneStore } from '@/stores/sessione'

const sessione = useSessioneStore()
const router = useRouter()

useBloccoAutomatico()

async function esci() {
  await sessione.esci()
  await router.push({ name: 'accesso' })
}

function bloccaOra() {
  blocca()
  void router.push({ name: 'sblocco' })
}

// Data wiped while the app is in use (revocation, expiry, too many PINs): navigating
// lets the router guard show the login page with the reason (router/index.ts).
function suCancellazione(evento: Event) {
  const motivo = (evento as CustomEvent<MotivoCancellazione>).detail
  if (motivo === 'uscita') return
  void router.push({ name: 'accesso', query: { motivo } })
}
window.addEventListener(EVENTO_CANCELLAZIONE, suCancellazione)
onBeforeUnmount(() => window.removeEventListener(EVENTO_CANCELLAZIONE, suCancellazione))
</script>

<template>
  <header class="qdc-intestazione shadow-sm">
    <nav class="container d-flex align-items-center gap-3 py-2">
      <RouterLink to="/" class="d-flex align-items-center gap-2 fw-bold">
        <img src="/icons/icon-192.png" alt="" width="32" height="32" class="rounded" />
        <span>Quaderno di Caccia</span>
      </RouterLink>
      <template v-if="sessione.autenticato && stato !== 'bloccata'">
        <RouterLink to="/persone" class="ms-auto">Persone</RouterLink>
        <button
          v-if="stato === 'sbloccata'"
          type="button"
          class="btn btn-sm btn-outline-light"
          title="Blocca l'app: per riaprirla servirà il PIN"
          @click="bloccaOra"
        >
          Blocca
        </button>
        <button type="button" class="btn btn-sm btn-outline-light" @click="esci">Esci</button>
      </template>
    </nav>
  </header>
  <BarraOffline />
  <main class="container py-3">
    <RouterView />
  </main>
  <AggiornamentoApp />
</template>
