<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { volantinoListaAttesa } from '@/api/qdc'
import CondividiLink from '@/components/CondividiLink.vue'
import Icona from '@/components/Icona.vue'
import QrCode from '@/components/QrCode.vue'
import { useRete } from '@/composables/useRete'
import { indirizzoListaAttesa, pngQr } from '@/navigazione/condividi'
import { useSessioneStore } from '@/stores/sessione'
import { useSitoStore } from '@/stores/sito'

// «Invita nel gruppo» (DEC-304): anyone with an account shares the public waiting list.
// Link and QR come from the device and work offline; the flyer is a PDF from the server.
const sessione = useSessioneStore()
const sito = useSitoStore()
const { online } = useRete()

const url = indirizzoListaAttesa()
const gruppo = computed(() => sito.sito.gruppo || 'il gruppo')
const errore = ref('')

async function scaricaQr() {
  errore.value = ''
  try {
    const immagine = await pngQr(url)
    const link = document.createElement('a')
    link.href = URL.createObjectURL(immagine)
    link.download = 'lista-d-attesa-qr.png'
    link.click()
    URL.revokeObjectURL(link.href)
  } catch (e) {
    errore.value = (e as Error).message
  }
}
</script>

<template>
  <section>
    <h1 class="h4 mb-1">Invita nel gruppo</h1>
    <p class="fg-2">
      Chi vuole entrare in {{ gruppo }} si mette in lista d'attesa da questo link, senza account. I
      capi chiamano a inizio anno scout, secondo l'età e i posti nelle unità.
    </p>

    <div class="card card-body mb-5">
      <label class="form-label small" for="link-lista-attesa">Link della lista d'attesa</label>
      <input id="link-lista-attesa" class="form-control mb-3" readonly :value="url" />
      <CondividiLink
        :url="url"
        titolo="Lista d'attesa"
        :testo="`Per entrare in ${gruppo}: mettiti in lista d'attesa.`"
      />
    </div>

    <div class="card card-body mb-5 text-center">
      <QrCode :valore="url" etichetta="QR code della lista d'attesa" />
      <p class="small fg-2 mt-3">Fallo inquadrare con la fotocamera del telefono.</p>
      <div class="d-flex flex-wrap justify-content-center gap-3">
        <button type="button" class="btn btn-outline theme-primary" @click="scaricaQr">
          <Icona nome="download" /> Scarica il QR
        </button>
        <a
          v-if="online"
          :href="volantinoListaAttesa"
          download
          class="btn btn-outline theme-primary"
        >
          <Icona nome="printer" /> Volantino da stampare
        </a>
        <button v-else type="button" class="btn btn-outline theme-primary" disabled>
          <Icona nome="printer" /> Volantino da stampare
        </button>
      </div>
      <p v-if="!online" class="small fg-2 mt-3 mb-0">Il volantino si scarica con la rete.</p>
      <div v-if="errore" class="alert theme-danger small mt-3 mb-0" role="alert">{{ errore }}</div>
    </div>

    <p v-if="sessione.profilo?.capogruppo" class="small fg-2">
      Il testo del volantino si cambia nelle
      <RouterLink :to="{ name: 'impostazioni', hash: '#volantino' }">Impostazioni</RouterLink>.
    </p>
  </section>
</template>
