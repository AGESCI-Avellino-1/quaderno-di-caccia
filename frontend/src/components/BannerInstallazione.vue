<script setup lang="ts">
import { computed, ref } from 'vue'

import Icona from '@/components/Icona.vue'
import {
  appInstallata,
  installa,
  installata,
  leggiChiusura,
  modoInstallazione,
  pulsanteDisponibile,
  ricompare,
  salvaChiusura,
} from '@/pwa/installazione'
import { useSitoStore } from '@/stores/sito'

// The banner suggesting to install the app (DEC-283): before and after the login,
// wherever the browser can install it; closed, it may show again after some days.
const sito = useSitoStore()
const chiusa = ref(leggiChiusura())
const giaInstallata = appInstallata()

const modo = computed(() =>
  modoInstallazione(navigator.userAgent, navigator.maxTouchPoints ?? 0, {
    installata: giaInstallata || installata.value,
    pulsante: pulsanteDisponibile.value,
  }),
)
const mostra = computed(
  () => modo.value !== null && ricompare(chiusa.value, sito.sito.banner_installazione_giorni ?? 14),
)

function chiudi() {
  salvaChiusura()
  chiusa.value = leggiChiusura() ?? new Date().toISOString()
}
</script>

<template>
  <div
    v-if="mostra"
    class="qdc-barra-installazione small py-2"
    role="region"
    aria-label="Installa l'app"
  >
    <div class="container d-flex align-items-center gap-3">
      <p class="mb-0 flex-grow-1">
        <template v-if="modo === 'pulsante'">
          Installa l'app su questo dispositivo: la apri dalla sua icona, come le altre app.
        </template>
        <template v-else-if="modo === 'ios'">
          Per installare l'app tocca il tasto Condividi
          <Icona nome="box-arrow-up" />
          (il quadrato con la freccia) e poi <strong>Aggiungi alla schermata Home</strong>.
        </template>
        <template v-else-if="modo === 'mac'">
          Per installare l'app scegli nel menu <strong>Archivio</strong> la voce
          <strong>Aggiungi al Dock</strong>.
        </template>
        <template v-else>
          Per installare l'app apri il menu (i tre puntini) e tocca <strong>Installa</strong> (o
          <strong>Aggiungi alla schermata principale</strong>).
        </template>
      </p>
      <button
        v-if="modo === 'pulsante'"
        type="button"
        class="btn btn-sm btn-solid theme-primary"
        @click="installa()"
      >
        Installa
      </button>
      <button type="button" class="btn btn-sm btn-outline" aria-label="Chiudi" @click="chiudi">
        <Icona nome="x-lg" />
      </button>
    </div>
  </div>
</template>
