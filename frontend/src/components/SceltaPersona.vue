<script setup lang="ts">
import { computed, ref, useAttrs, useId, watch } from 'vue'

import { coincide, type Opzione } from '@/components/sceltaPersona'

// Choosing a person (DEC-395): a field where one writes and the list narrows, by name or
// surname, ignoring case and accents; only a person of the list is accepted, also from the
// keyboard. The unit is next to the name, to tell namesakes apart. ARIA combobox pattern.
// With `multipla` the chosen ones line up below, each with its ×, and the value is a list
// (DEC-396).
const props = defineProps<{
  id: string
  opzioni: Opzione[]
  /** Required: the form does not go without a choice. */
  richiesto?: boolean
  /** The label of «nobody», for an optional choice. */
  vuoto?: string
  multipla?: boolean
  segnaposto?: string
}>()
// The class goes to the box around, aria-label and the rest to the field itself.
defineOptions({ inheritAttrs: false })
const attrs = useAttrs()
const attributiCampo = computed(() => {
  const altri = { ...attrs }
  delete altri.class
  return altri
})

const modello = defineModel<number | null | number[]>({ required: true })

const lista = `${useId()}-lista`
const testo = ref('')
const aperta = ref(false)
const attiva = ref(-1)
const campo = ref<HTMLInputElement | null>(null)

const scelte = computed<number[]>(() =>
  Array.isArray(modello.value) ? modello.value : modello.value == null ? [] : [modello.value],
)
const etichetta = (o: Opzione) => o.nome
const scelta = computed(() =>
  props.multipla ? undefined : props.opzioni.find((o) => o.id === modello.value),
)
const filtrate = computed(() =>
  props.opzioni.filter(
    (o) =>
      !(props.multipla && scelte.value.includes(o.id)) &&
      (scelta.value && testo.value === etichetta(scelta.value) ? true : coincide(o, testo.value)),
  ),
)

// The field shows the chosen name; writing something else undoes the choice, and keeps what
// is being written. A choice emptied from outside (a form reset) empties the field.
let scrivendo = false
watch(
  () => [modello.value, props.opzioni],
  () => {
    if (props.multipla) return
    if (scelta.value) testo.value = etichetta(scelta.value)
    else if (!scrivendo) testo.value = ''
    scrivendo = false
  },
  { immediate: true },
)
watch([scelte, testo], () => {
  const manca = props.richiesto && !scelte.value.length
  campo.value?.setCustomValidity(manca ? "Scegli una persona dall'elenco." : '')
})

function scrivi() {
  aperta.value = true
  attiva.value = filtrate.value.length ? 0 : -1
  if (!props.multipla && scelta.value && testo.value !== etichetta(scelta.value)) {
    scrivendo = true
    modello.value = null
  }
}

function scegli(o: Opzione) {
  if (props.multipla) {
    modello.value = [...scelte.value, o.id]
    testo.value = ''
  } else {
    modello.value = o.id
    testo.value = etichetta(o)
    aperta.value = false
  }
  attiva.value = -1
}

function togli(id: number) {
  modello.value = scelte.value.filter((s) => s !== id)
}

function svuota() {
  modello.value = props.multipla ? [] : null
  testo.value = ''
  campo.value?.focus()
}

function tasto(evento: KeyboardEvent) {
  if (evento.key === 'ArrowDown') {
    evento.preventDefault()
    aperta.value = true
    attiva.value = Math.min(attiva.value + 1, filtrate.value.length - 1)
  } else if (evento.key === 'ArrowUp') {
    evento.preventDefault()
    attiva.value = Math.max(attiva.value - 1, 0)
  } else if (evento.key === 'Enter' && aperta.value && filtrate.value[attiva.value]) {
    evento.preventDefault()
    scegli(filtrate.value[attiva.value]!)
  } else if (evento.key === 'Escape') {
    aperta.value = false
  }
}

// A click on the list arrives after the blur: the list closes a moment later.
function lascia() {
  setTimeout(() => {
    aperta.value = false
    if (!props.multipla && !scelta.value) testo.value = ''
  }, 150)
}

const nomeDi = (id: number) => props.opzioni.find((o) => o.id === id)
</script>

<template>
  <div class="qdc-scelta-persona" :class="attrs.class">
    <div class="d-flex gap-1">
      <input
        v-bind="attributiCampo"
        :id="id"
        ref="campo"
        v-model="testo"
        type="text"
        role="combobox"
        autocomplete="off"
        class="form-control form-control-sm"
        :placeholder="segnaposto ?? (multipla ? 'Scrivi per aggiungere…' : 'Scrivi un nome…')"
        :aria-expanded="aperta"
        :aria-controls="lista"
        aria-autocomplete="list"
        :aria-activedescendant="attiva >= 0 ? `${lista}-${attiva}` : undefined"
        @focus="aperta = true"
        @input="scrivi"
        @keydown="tasto"
        @blur="lascia"
      />
      <button
        v-if="!multipla && vuoto && scelta"
        type="button"
        class="btn btn-sm btn-link"
        :aria-label="vuoto"
        @click="svuota"
      >
        ×
      </button>
    </div>
    <ul
      v-show="aperta && (filtrate.length || testo)"
      :id="lista"
      role="listbox"
      class="list-group qdc-scelta-elenco"
    >
      <li
        v-for="(o, n) in filtrate"
        :id="`${lista}-${n}`"
        :key="o.id"
        role="option"
        :aria-selected="n === attiva"
        class="list-group-item list-group-item-action small"
        :class="{ active: n === attiva }"
        @mousedown.prevent="scegli(o)"
      >
        {{ o.nome }}<span v-if="o.dettaglio" class="fg-2"> · {{ o.dettaglio }}</span>
      </li>
      <li v-if="!filtrate.length" class="list-group-item small fg-2">Nessuno con questo nome.</li>
    </ul>
    <p v-if="!multipla && vuoto && !scelta && !testo" class="form-text mb-0">{{ vuoto }}.</p>
    <ul v-if="multipla && scelte.length" class="list-unstyled d-flex flex-wrap gap-1 mt-1 mb-0">
      <li v-for="sid in scelte" :key="sid" class="badge theme-primary">
        {{ nomeDi(sid)?.nome }}
        <button
          type="button"
          class="btn btn-sm btn-link p-0 ms-1 text-reset"
          :aria-label="`Togli ${nomeDi(sid)?.nome}`"
          @click="togli(sid)"
        >
          ×
        </button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.qdc-scelta-persona {
  position: relative;
}
.qdc-scelta-elenco {
  position: absolute;
  z-index: 10;
  inset-inline: 0;
  max-height: 16rem;
  overflow-y: auto;
  margin-top: 0.125rem;
}
</style>
