<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch, watchEffect } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'

import AggiornamentoApp from '@/components/AggiornamentoApp.vue'
import BannerCookie from '@/components/BannerCookie.vue'
import BannerInstallazione from '@/components/BannerInstallazione.vue'
import InvitoNotifiche from '@/components/InvitoNotifiche.vue'
import BarraEmailDiProva from '@/components/BarraEmailDiProva.vue'
import BarraImpersonazione from '@/components/BarraImpersonazione.vue'
import BarraManutenzione from '@/components/BarraManutenzione.vue'
import BarraOffline from '@/components/BarraOffline.vue'
import Briciole from '@/components/Briciole.vue'
import FileDaSalvare from '@/components/FileDaSalvare.vue'
import Icona from '@/components/Icona.vue'
import MenuLaterale from '@/components/MenuLaterale.vue'
import PiePagina from '@/components/PiePagina.vue'
import SchermataManutenzione from '@/components/SchermataManutenzione.vue'
import { useBloccoAutomatico } from '@/composables/useBloccoAutomatico'
import { EVENTO_CANCELLAZIONE, stato, type MotivoCancellazione } from '@/sicurezza/cassaforte'
import { useNavigazioneStore } from '@/stores/navigazione'
import { useSessioneStore } from '@/stores/sessione'
import { useSitoStore } from '@/stores/sito'

const sessione = useSessioneStore()
const sito = useSitoStore()

// The browser tab shows the short title (DEC-246).
watchEffect(() => {
  document.title = sito.titoloBreve
})
// Once unlocked, read it again so the device keeps a copy for offline starts.
watch(stato, (nuovo) => {
  if (nuovo === 'sbloccata') void sito.carica()
})
const router = useRouter()

useBloccoAutomatico()

// Maintenance (DEC-268): everyone but the technical administrators sees the message
// instead of the page. Open: privacy and terms, and the way in of an administrator
// (login, password reset, unlocking the phone: the profile is not read before it).
const APERTE_IN_MANUTENZIONE = new Set([
  'accesso',
  'reimposta-password',
  'sblocco',
  'protezione',
  'privacy',
  'termini',
])
const fermato = computed(
  () =>
    !!sito.sito.manutenzione &&
    !sessione.profilo?.amministratore_tecnico &&
    !APERTE_IN_MANUTENZIONE.has(String(router.currentRoute.value.name)),
)

// The side menu (DEC-241) once logged in and unlocked; lock and logout are in it.
const menu = ref<InstanceType<typeof MenuLaterale> | null>(null)
const conMenu = computed(() => sessione.autenticato && stato.value !== 'bloccata' && !fermato.value)
const navigazione = useNavigazioneStore()

// Only the content scrolls (.qdc-scorrevole): a new page starts from its top.
const scorrevole = ref<HTMLElement | null>(null)
watch(
  () => router.currentRoute.value.path,
  () => scorrevole.value?.scrollTo({ top: 0 }),
)
watch(
  () => sessione.profilo,
  (p) => {
    if (p) void navigazione.caricaContatori(p.capogruppo || p.amministratore_tecnico)
  },
  { immediate: true },
)

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
  <div class="qdc-cornice">
    <MenuLaterale v-if="conMenu" ref="menu" />
    <div class="qdc-colonna">
      <header class="qdc-intestazione shadow-sm">
        <nav class="container d-flex align-items-center gap-3 py-3">
          <button
            v-if="conMenu"
            type="button"
            class="btn btn-sm btn-outline lg:d-none"
            aria-label="Apri il menu"
            @click="menu?.apri()"
          >
            <Icona nome="list" />
          </button>
          <RouterLink to="/" class="d-flex align-items-center gap-3 fw-bold min-w-0">
            <img src="/icons/icon-192.png" alt="" width="32" height="32" class="rounded" />
            <span class="text-truncate">{{ sito.titoloCompleto }}</span>
          </RouterLink>
        </nav>
      </header>
      <BarraEmailDiProva />
      <BarraManutenzione v-if="!fermato" />
      <BarraImpersonazione />
      <BarraOffline />
      <BannerInstallazione />
      <InvitoNotifiche v-if="sessione.profilo" />
      <Briciole v-if="conMenu" />
      <div ref="scorrevole" class="qdc-scorrevole">
        <main class="container py-5">
          <SchermataManutenzione v-if="fermato" />
          <RouterView v-else />
        </main>
        <!-- Phone: the footer at the end of the content, seen when scrolled to the bottom. -->
        <PiePagina class="lg:d-none" />
      </div>
      <!-- Computer: always at the bottom of the window. -->
      <PiePagina class="d-none lg:d-block" />
    </div>
  </div>
  <BannerCookie />
  <AggiornamentoApp />
  <FileDaSalvare />
</template>
