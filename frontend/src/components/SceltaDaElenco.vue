<script setup lang="ts" generic="K extends number | string">
import { computed, ref, useAttrs, useId, watch } from 'vue'

import { coincide, type Opzione } from '@/components/sceltaDaElenco'

// Choosing from a list (DEC-395): a field where one writes and the list narrows, by every
// word of the name, ignoring case and accents; only an item of the list is accepted, also from
// the keyboard. For a person the unit is next to the name, to tell namesakes apart. ARIA
// combobox pattern. With `multipla` the chosen ones line up below, each with its ×, and the
// value is a list (DEC-396). Also for the catalogs of specialità and brevetti (DEC-397).
const props = defineProps<{
  id: string
  opzioni: Opzione<K>[]
  /** Required: the form does not go without a choice. */
  richiesto?: boolean
  /** The label of «nobody», for an optional choice. */
  vuoto?: string
  multipla?: boolean
  segnaposto?: string
  /** Shown while nothing is chosen in a required field; the default is for people. */
  avviso?: string
  /** Shown when nothing matches; the default is for people. */
  nessuno?: string
}>()
// The class goes to the box around, aria-label and the rest to the field itself.
defineOptions({ inheritAttrs: false })
const attrs = useAttrs()
const attributiCampo = computed(() => {
  const altri = { ...attrs }
  delete altri.class
  return altri
})

const modello = defineModel<K | null | K[]>({ required: true })

const lista = `${useId()}-lista`
const testo = ref('')
const aperta = ref(false)
const attiva = ref(-1)
const campo = ref<HTMLInputElement | null>(null)

const scelte = computed<K[]>(() =>
  Array.isArray(modello.value) ? modello.value : modello.value == null ? [] : [modello.value],
)
const etichetta = (o: Opzione<K>) => o.nome
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
  modello,
  () => {
    if (props.multipla) return
    if (scelta.value) testo.value = etichetta(scelta.value)
    else if (!scrivendo) testo.value = ''
    scrivendo = false
  },
  { immediate: true },
)
// A list arriving late shows the name of the choice, never erases what is being written.
watch(
  () => props.opzioni,
  () => {
    if (!props.multipla && scelta.value) testo.value = etichetta(scelta.value)
    // What is being written finds its first match, ready for Enter.
    if (aperta.value) attiva.value = filtrate.value.length ? 0 : -1
  },
)
// Also before anything is written: an untouched required field must stop the form too.
watch([scelte, testo, campo], () => {
  const manca = props.richiesto && !scelte.value.length
  campo.value?.setCustomValidity(manca ? (props.avviso ?? "Scegli una persona dall'elenco.") : '')
})

function scrivi() {
  aperta.value = true
  attiva.value = filtrate.value.length ? 0 : -1
  if (!props.multipla && scelta.value && testo.value !== etichetta(scelta.value)) {
    scrivendo = true
    modello.value = null
  }
}

function scegli(o: Opzione<K>) {
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

function togli(id: K) {
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

const nomeDi = (id: K) => props.opzioni.find((o) => o.id === id)
</script>

<template>
  <div class="qdc-scelta" :class="attrs.class">
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
      <li v-if="!filtrate.length" class="list-group-item small fg-2">
        {{ nessuno ?? 'Nessuno con questo nome.' }}
      </li>
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
.qdc-scelta {
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
