<script setup lang="ts">
import Menu from 'bootstrap/js/dist/menu.js'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import Icona from '@/components/Icona.vue'

// Several choices from a drop-down list (DEC-306): Bootstrap 6's combobox markup with
// its menu, the choice kept here (Bootstrap's own combobox writes its summary in
// English). The menu stays open while ticking. `gruppi` adds quick choices next to «Tutti»
// and «Nessuno»: each picks exactly its values (DEC-318).
const props = defineProps<{
  id: string
  scelte: { valore: string; nome: string }[]
  gruppi?: { nome: string; valori: string[] }[]
}>()
const valori = defineModel<string[]>({ required: true })

const pulsante = ref<HTMLButtonElement | null>(null)
const menu = ref<HTMLElement | null>(null)
let tendina: Menu | null = null

onMounted(() => {
  if (pulsante.value && menu.value) {
    tendina = new Menu(pulsante.value, { menu: menu.value, autoClose: 'outside' })
    pulsante.value.addEventListener('show.bs.menu', allarga)
  }
})

onBeforeUnmount(() => {
  pulsante.value?.removeEventListener('show.bs.menu', allarga)
  tendina?.dispose()
})

// As wide as the field it opens from.
function allarga() {
  if (pulsante.value && menu.value) menu.value.style.width = `${pulsante.value.offsetWidth}px`
}

const riepilogo = computed(() => {
  const n = valori.value.length
  if (n === 0) return 'Nessuno'
  if (n === props.scelte.length) return 'Tutti'
  if (n === 1) return props.scelte.find((s) => s.valore === valori.value[0])?.nome ?? '1 scelto'
  return `${n} scelti su ${props.scelte.length}`
})

function cambia(valore: string) {
  valori.value = valori.value.includes(valore)
    ? valori.value.filter((v) => v !== valore)
    : // In the order of the list, whatever the order of the taps.
      props.scelte.map((s) => s.valore).filter((v) => v === valore || valori.value.includes(v))
}

const tutti = (si: boolean) => (valori.value = si ? props.scelte.map((s) => s.valore) : [])

const scegli = (gruppo: string[]) =>
  (valori.value = props.scelte.map((s) => s.valore).filter((v) => gruppo.includes(v)))
</script>

<template>
  <div>
    <button
      :id="id"
      ref="pulsante"
      type="button"
      class="form-control combobox-toggle"
      data-bs-toggle="menu"
      aria-haspopup="listbox"
      aria-expanded="false"
    >
      <span class="combobox-value" :class="{ 'combobox-placeholder': !valori.length }">
        {{ riepilogo }}
      </span>
      <Icona nome="chevron-down" class="combobox-caret" />
    </button>
    <div ref="menu" class="menu" role="listbox" aria-multiselectable="true">
      <div class="d-flex flex-wrap column-gap-3 px-3 pb-1 small">
        <button type="button" class="btn btn-link btn-sm p-0" @click="tutti(true)">Tutti</button>
        <button type="button" class="btn btn-link btn-sm p-0" @click="tutti(false)">Nessuno</button>
        <button
          v-for="g in gruppi"
          :key="g.nome"
          type="button"
          class="btn btn-link btn-sm p-0"
          @click="scegli(g.valori)"
        >
          {{ g.nome }}
        </button>
      </div>
      <button
        v-for="s in scelte"
        :key="s.valore"
        type="button"
        class="menu-item"
        role="option"
        :class="{ selected: valori.includes(s.valore) }"
        :aria-selected="valori.includes(s.valore)"
        @click="cambia(s.valore)"
      >
        <span class="menu-item-content">{{ s.nome }}</span>
        <Icona nome="check2" class="menu-item-check" />
      </button>
    </div>
  </div>
</template>
