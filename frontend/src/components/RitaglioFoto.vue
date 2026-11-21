<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'

// A square cropped on the device (DEC-205): only that square leaves the phone. Used by
// the profile photo and by the image of a totem (DEC-416).
const props = defineProps<{
  file: File
  /** Unique on the page: names the zoom slider. */
  id: string
  inCorso?: boolean
  etichettaSalva?: string
}>()
const emit = defineEmits<{ pronta: [blob: Blob]; annulla: []; errore: [messaggio: string] }>()

const LATO = 280 // the square on screen
const USCITA = 800 // the square uploaded
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

function libera() {
  if (url.value) URL.revokeObjectURL(url.value)
  url.value = ''
}

watch(
  () => props.file,
  (file) => {
    libera()
    sorgente.value = null
    url.value = URL.createObjectURL(file)
    const immagine = new Image()
    immagine.onload = () => {
      sorgente.value = immagine
      stato.zoom = 1
      // Centred.
      stato.x = (LATO - immagine.naturalWidth * minimo.value) / 2
      stato.y = (LATO - immagine.naturalHeight * minimo.value) / 2
    }
    immagine.onerror = () => emit('errore', 'Questo file non è una foto.')
    immagine.src = url.value
  },
  { immediate: true },
)

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
    emit('errore', 'Non riesco a preparare la foto: provane un’altra.')
    return
  }
  emit('pronta', blob)
}

onBeforeUnmount(libera)
</script>

<template>
  <div v-if="sorgente">
    <slot />
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
    <label class="form-label small mt-1" :for="`zoom-${id}`">Ingrandisci</label>
    <input
      :id="`zoom-${id}`"
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
        {{ etichettaSalva ?? 'Salva la foto' }}
      </button>
      <button type="button" class="btn btn-sm btn-link" @click="emit('annulla')">Annulla</button>
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
