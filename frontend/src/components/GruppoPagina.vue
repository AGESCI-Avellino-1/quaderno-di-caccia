<script setup lang="ts">
import Icona from '@/components/Icona.vue'
import { useGruppo } from '@/composables/useGruppiPagina'

// One group of a long page (DEC-426), inside a `<div class="accordion">` of a page that called
// `useGruppiPagina`. Its content stays mounted while closed: forms and data loaded keep their
// state when one opens another group.
const props = defineProps<{ chiave: string; titolo: string }>()
const gruppi = useGruppo()

function cambia(evento: Event) {
  if (!gruppi) return
  const aperto = (evento.target as HTMLDetailsElement).open
  if (aperto) gruppi.apri(props.chiave)
  else if (gruppi.aperto.value === props.chiave) gruppi.apri(null)
}
</script>

<template>
  <details
    class="accordion-item"
    :name="gruppi?.nome"
    :open="gruppi?.aperto.value === chiave"
    :data-gruppo="chiave"
    @toggle="cambia"
  >
    <summary class="accordion-header">
      <span class="d-flex flex-wrap align-items-center gap-3">
        <span class="h6 mb-0">{{ titolo }}</span>
        <slot name="accanto" />
      </span>
      <Icona nome="chevron-down" class="accordion-icon" />
    </summary>
    <div class="accordion-body">
      <slot />
    </div>
  </details>
</template>
