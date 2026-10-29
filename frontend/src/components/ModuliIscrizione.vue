<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'

import {
  api,
  fileModulo,
  fileModuloFirmato,
  type ModuliFirmati,
  type ModuloVuoto,
  type RichiestaIscrizione,
} from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Signed forms of a registration. The family downloads the blank forms, signs them by
// hand and uploads the scans (PDF or photo, up to 10 MB). Who approves opens them,
// checks them and reports the consents on the member: only then the forms count. Scans
// are personal data with signatures: online only, every read by a capo is logged.
const props = defineProps<{ id: number }>()
const emit = defineEmits<{ cambiata: [richiesta: RichiestaIscrizione]; aggiorna: [] }>()
const { errore, inCorso, esegui } = useErrore()
const moduli = ref<ModuliFirmati | null>(null)
const vuoti = ref<ModuloVuoto[]>([])
const scelto = ref<File | null>(null)
const consensi = reactive({
  consenso_iscrizione: false,
  consenso_foto: false,
  consenso_commerciale: false,
  consenso_riviste: false,
})
const voci = [
  ['consenso_iscrizione', "Consenso per l'iscrizione (2A)"],
  ['consenso_foto', 'Consenso per le foto (2B)'],
  ['consenso_commerciale', 'Consenso commerciale (2C)'],
  ['consenso_riviste', 'Consenso per le riviste'],
] as const

async function carica(id: number) {
  moduli.value = (await esegui(() => api.moduliFirmati(id))) ?? null
}
watch(() => props.id, carica, { immediate: true })
onMounted(async () => {
  vuoti.value = (await esegui(() => api.modulistica()))?.moduli.filter((m) => m.attivo) ?? []
})

function scegli(evento: Event) {
  scelto.value = (evento.target as HTMLInputElement).files?.[0] ?? null
}

async function invia() {
  if (!scelto.value) return
  const nuovi = await esegui(() => api.caricaModuloFirmato(props.id, scelto.value!))
  if (nuovi) {
    moduli.value = nuovi
    scelto.value = null
    emit('aggiorna') // what is missing changes
  }
}

async function togli(id: number) {
  const nuovi = await esegui(() => api.togliModuloFirmato(id))
  if (nuovi) {
    moduli.value = nuovi
    emit('aggiorna')
  }
}

async function verifica() {
  const richiesta = await esegui(() => api.verificaModuli(props.id, { ...consensi }))
  if (!richiesta) return
  await carica(props.id)
  emit('cambiata', richiesta)
}

const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
</script>

<template>
  <div v-if="moduli" class="mt-3">
    <h3 class="h6">Moduli firmati</h3>
    <div v-if="errore" class="alert theme-danger py-3 small" role="alert">{{ errore }}</div>
    <p v-if="vuoti.length && !moduli.puo_verificare" class="small mb-1">
      Scarica, stampa e firma:
      <template v-for="(m, i) in vuoti" :key="m.id">
        <a :href="fileModulo(m.id)">{{ m.titolo }}</a
        ><template v-if="i < vuoti.length - 1">, </template>
      </template>
    </p>
    <ul v-if="moduli.allegati.length" class="list-unstyled small mb-1">
      <li v-for="a in moduli.allegati" :key="a.id">
        <a :href="fileModuloFirmato(a.id)" target="_blank" rel="noopener">{{ a.nome_file }}</a>
        <span class="fg-2"> · {{ data(a.caricato_il) }}</span>
        <button
          v-if="!moduli.verificati_il"
          type="button"
          class="btn btn-link btn-sm py-0"
          @click="togli(a.id)"
        >
          togli
        </button>
      </li>
    </ul>
    <p v-else class="small fg-2 mb-1">Nessun modulo caricato.</p>
    <p v-if="moduli.verificati_il" class="small fg-success mb-1">
      Moduli verificati dai capi il {{ data(moduli.verificati_il) }}.
    </p>

    <form class="d-flex flex-wrap gap-3 align-items-center" @submit.prevent="invia">
      <input
        class="form-control form-control-sm w-auto"
        type="file"
        accept="application/pdf,image/jpeg,image/png"
        aria-label="Scansione di un modulo firmato"
        @change="scegli"
      />
      <button
        type="submit"
        class="btn btn-sm btn-outline theme-primary"
        :disabled="!scelto || inCorso"
      >
        Carica
      </button>
    </form>

    <form
      v-if="moduli.puo_verificare && moduli.allegati.length && !moduli.verificati_il"
      class="vstack gap-1 mt-3"
      @submit.prevent="verifica"
    >
      <p class="small mb-1">Dopo aver controllato i moduli, riporta i consensi firmati:</p>
      <div v-for="[chiave, etichetta] in voci" :key="chiave" class="form-field">
        <input :id="`${chiave}-${id}`" v-model="consensi[chiave]" type="checkbox" class="check" />
        <label class="small" :for="`${chiave}-${id}`">{{ etichetta }}</label>
      </div>
      <button
        type="submit"
        class="btn btn-sm btn-solid theme-primary align-self-start mt-1"
        :disabled="inCorso"
      >
        Moduli verificati
      </button>
    </form>
  </div>
</template>
