<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'

import { api, type PropostaIndirizzo } from '@/api/qdc'

// The address of a place (DEC-360): proposals while writing, from the server. It is only a
// help: with no network or no answer the proposals are not there and the address is written by
// hand. Online only, nothing kept on the device.
const props = defineProps<{ idCampo: string }>()
const indirizzo = defineModel<string>({ required: true })
const civico = defineModel<string>('civico', { required: true })
const emit = defineEmits<{ scelta: [proposta: PropostaIndirizzo] }>()

// Each search takes the public service some seconds: only when the writing pauses.
const ATTESA_MS = 600
const MINIMO = 3
const proposte = ref<PropostaIndirizzo[]>([])
const cercando = ref(false)
let timer: number | undefined
let giro = 0

function scritto() {
  window.clearTimeout(timer)
  // An answer still on its way is no longer about what is written.
  const questo = ++giro
  proposte.value = []
  cercando.value = false
  const testo = indirizzo.value.trim()
  if (testo.length < MINIMO || !navigator.onLine) return
  timer = window.setTimeout(async () => {
    cercando.value = true
    try {
      const trovate = await api.cercaIndirizzi(testo)
      if (questo === giro) proposte.value = trovate
    } catch {
      /* only a help: it stays a field to write in */
    } finally {
      if (questo === giro) cercando.value = false
    }
  }, ATTESA_MS)
}

function scegli(proposta: PropostaIndirizzo) {
  giro++
  cercando.value = false
  indirizzo.value = proposta.indirizzo
  // A number written by hand stays: the service often has only the street (DEC-366).
  if (proposta.civico) civico.value = proposta.civico
  proposte.value = []
  emit('scelta', proposta)
}

onBeforeUnmount(() => {
  window.clearTimeout(timer)
  giro++
})
</script>

<template>
  <input
    :id="props.idCampo"
    v-model="indirizzo"
    class="form-control form-control-sm"
    autocomplete="off"
    @input="scritto"
  />
  <div v-if="cercando" class="form-text small" role="status">Cerco…</div>
  <template v-if="proposte.length">
    <div class="list-group small mt-1">
      <button
        v-for="p in proposte"
        :key="`${p.nome}|${p.indirizzo}`"
        type="button"
        class="list-group-item list-group-item-action"
        @click="scegli(p)"
      >
        <template v-if="p.nome">{{ p.nome }} · </template>{{ p.indirizzo
        }}<template v-if="p.civico"> · n. {{ p.civico }}</template>
      </button>
    </div>
    <div class="form-text small">© OpenStreetMap</div>
  </template>
  <div class="form-text small">
    Scrivi per cercare sedi e basi, mai l'indirizzo di una persona: quello che scrivi passa da un
    servizio esterno. Puoi anche scriverlo a mano.
  </div>
</template>
