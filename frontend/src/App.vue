<script setup lang="ts">
import { onBeforeUnmount } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'

import AggiornamentoApp from '@/components/AggiornamentoApp.vue'
import BarraImpersonazione from '@/components/BarraImpersonazione.vue'
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
    <nav class="container d-flex align-items-center gap-5 py-3">
      <RouterLink to="/" class="d-flex align-items-center gap-3 fw-bold">
        <img src="/icons/icon-192.png" alt="" width="32" height="32" class="rounded" />
        <span>Quaderno di Caccia</span>
      </RouterLink>
      <template v-if="sessione.autenticato && stato !== 'bloccata'">
        <RouterLink to="/persone" class="ms-auto">Persone</RouterLink>
        <button
          v-if="stato === 'sbloccata' && !sessione.profilo?.impersonazione"
          type="button"
          class="btn btn-sm btn-outline"
          title="Blocca l'app: per riaprirla servirà il PIN"
          @click="bloccaOra"
        >
          Blocca
        </button>
        <!-- Logging out while acting as someone else would wipe the capo's device. -->
        <button
          v-if="!sessione.profilo?.impersonazione"
          type="button"
          class="btn btn-sm btn-outline"
          @click="esci"
        >
          Esci
        </button>
      </template>
    </nav>
  </header>
  <BarraImpersonazione />
  <BarraOffline />
  <main class="container py-5">
    <RouterView />
  </main>
  <AggiornamentoApp />
</template>
