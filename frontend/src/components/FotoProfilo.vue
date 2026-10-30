<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref } from 'vue'

import { api, fotoProfilo, type PersonaDettaglio } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The profile photo, to recognise the ragazzi (DEC-42, DEC-201). The photo is cropped
// on the device to a square around the person (DEC-205): only that square leaves the
// phone, so the other people in a group photo are never uploaded. The server reduces it
// to a JPEG of at most 1 MB without metadata; the earlier photos stay for the capi.
const props = defineProps<{ persona: PersonaDettaglio }>()
const emit = defineEmits<{ cambiata: [persona: PersonaDettaglio] }>()
const { errore, inCorso, esegui } = useErrore()

const LATO = 280 // the square on screen
const USCITA = 800 // the square uploaded
const versione = ref(Date.now())
const sorgente = ref<HTMLImageElement | null>(null)
const url = ref('')
const stato = reactive({ zoom: 1, x: 0, y: 0 })
let trascina: { x: number; y: number; ox: number; oy: number } | null = null

// The smallest scale that still covers the square.
const minimo = computed(() =>
  sorgente.value
    ? Math.max(LATO / sorgente.value.naturalWidth, LATO / sorgente.value.naturalHeight)
    : 1,
)
const scala = computed(() => minimo.value * stato.zoom)
const larghezza = computed(() => (sorgente.value?.naturalWidth ?? 0) * scala.value)
const altezza = computed(() => (sorgente.value?.naturalHeight ?? 0) * scala.value)

function limita() {
  stato.x = Math.min(0, Math.max(LATO - larghezza.value, stato.x))
  stato.y = Math.min(0, Math.max(LATO - altezza.value, stato.y))
}

function scegli(evento: Event) {
  const file = (evento.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (url.value) URL.revokeObjectURL(url.value)
  url.value = URL.createObjectURL(file)
  const immagine = new Image()
  immagine.onload = () => {
    sorgente.value = immagine
    stato.zoom = 1
    // Centred.
    stato.x = (LATO - immagine.naturalWidth * minimo.value) / 2
    stato.y = (LATO - immagine.naturalHeight * minimo.value) / 2
  }
  immagine.onerror = () => (errore.value = 'Questo file non è una foto.')
  immagine.src = url.value
}

function ingrandisci(valore: number) {
  // Zoom around the centre of the square.
  const centroX = (LATO / 2 - stato.x) / scala.value
  const centroY = (LATO / 2 - stato.y) / scala.value
  stato.zoom = valore
  stato.x = LATO / 2 - centroX * scala.value
  stato.y = LATO / 2 - centroY * scala.value
  limita()
}

function inizio(e: PointerEvent) {
  ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
  trascina = { x: e.clientX, y: e.clientY, ox: stato.x, oy: stato.y }
}
function muovi(e: PointerEvent) {
  if (!trascina) return
  stato.x = trascina.ox + e.clientX - trascina.x
  stato.y = trascina.oy + e.clientY - trascina.y
  limita()
}
function fine() {
  trascina = null
}
function tasto(e: KeyboardEvent) {
  const passo = { ArrowLeft: [10, 0], ArrowRight: [-10, 0], ArrowUp: [0, 10], ArrowDown: [0, -10] }[
    e.key
  ]
  if (!passo) return
  e.preventDefault()
  stato.x += passo[0]
  stato.y += passo[1]
  limita()
}

function annulla() {
  sorgente.value = null
  if (url.value) URL.revokeObjectURL(url.value)
  url.value = ''
}

async function salva() {
  const immagine = sorgente.value
  if (!immagine) return
  const tela = document.createElement('canvas')
  tela.width = USCITA
  tela.height = USCITA
  const lato = LATO / scala.value
  tela
    .getContext('2d')!
    .drawImage(
      immagine,
      -stato.x / scala.value,
      -stato.y / scala.value,
      lato,
      lato,
      0,
      0,
      USCITA,
      USCITA,
    )
  const blob = await new Promise<Blob | null>((ok) => tela.toBlob(ok, 'image/jpeg', 0.9))
  if (!blob) {
    errore.value = 'Non riesco a preparare la foto: provane un’altra.'
    return
  }
  const nuova = await esegui(() => api.caricaFotoProfilo(props.persona.id, blob))
  if (!nuova) return
  annulla()
  versione.value = Date.now()
  emit('cambiata', nuova)
}

onBeforeUnmount(annulla)
</script>

<template>
  <div class="d-flex flex-wrap align-items-start gap-3 mb-3">
    <img
      v-if="persona.foto && !sorgente"
      :src="`${fotoProfilo(persona.id)}?v=${versione}`"
      :alt="`Foto di ${persona.nome} ${persona.cognome}`"
      width="96"
      height="96"
      class="rounded"
    />
    <div v-if="persona.puo_caricare_foto && !sorgente">
      <label class="btn btn-sm btn-outline theme-primary mb-0" :for="`foto-${persona.id}`">
        {{ persona.foto ? 'Cambia la foto' : 'Aggiungi una foto' }}
      </label>
      <input
        :id="`foto-${persona.id}`"
        type="file"
        accept="image/*"
        class="d-none"
        @change="scegli"
      />
      <p class="small fg-2 mb-0 mt-1">Serve ai capi per riconoscerlo; non viene pubblicata.</p>
    </div>

    <div v-if="sorgente" class="w-100">
      <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
      <p class="small mb-1">
        Sposta la foto e ingrandiscila finché nel riquadro c'è solo
        {{ persona.nome }}: le altre persone non vengono caricate.
      </p>
      <div
        class="ritaglio"
        :style="{ width: `${LATO}px`, height: `${LATO}px` }"
        tabindex="0"
        role="application"
        aria-label="Riquadro della foto: trascina o usa le frecce per spostarla"
        @pointerdown="inizio"
        @pointermove="muovi"
        @pointerup="fine"
        @pointercancel="fine"
        @keydown="tasto"
      >
        <img
          :src="url"
          alt=""
          draggable="false"
          :style="{
            width: `${larghezza}px`,
            height: `${altezza}px`,
            transform: `translate(${stato.x}px, ${stato.y}px)`,
          }"
        />
      </div>
      <label class="form-label small mt-1" :for="`zoom-${persona.id}`">Ingrandisci</label>
      <input
        :id="`zoom-${persona.id}`"
        type="range"
        min="1"
        max="5"
        step="0.05"
        :value="stato.zoom"
        class="d-block mb-3"
        :style="{ width: `${LATO}px` }"
        @input="ingrandisci(Number(($event.target as HTMLInputElement).value))"
      />
      <div class="d-flex gap-3">
        <button
          type="button"
          class="btn btn-sm btn-solid theme-primary"
          :disabled="inCorso"
          @click="salva"
        >
          Salva la foto
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="annulla">Annulla</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ritaglio {
  position: relative;
  overflow: hidden;
  touch-action: none;
  cursor: grab;
  border-radius: 0.5rem;
  outline: 2px solid var(--ag-primary);
  background: var(--ag-primary-subtle);
}
.ritaglio:focus-visible {
  outline-width: 4px;
}
.ritaglio img {
  position: absolute;
  top: 0;
  left: 0;
  max-width: none;
  user-select: none;
  pointer-events: none;
}
</style>
