<script setup lang="ts">
import { computed, useAttrs } from 'vue'

// An amount in euro, with the € inside the field (Bootstrap 6 form adorn, DEC-298). The
// label of the form names the field; the € is decorative.
defineOptions({ inheritAttrs: false })

const valore = defineModel<number | string | null | undefined>()

// class goes to the field's border (w-auto…), everything else to the input.
const attributi = useAttrs()
const perIlCampo = computed(() =>
  Object.fromEntries(Object.entries(attributi).filter(([nome]) => nome !== 'class')),
)
</script>

<template>
  <label class="form-control form-control-sm form-adorn" :class="attributi.class">
    <span class="form-adorn-text" aria-hidden="true">€</span>
    <input
      v-model="valore"
      type="number"
      step="0.01"
      inputmode="decimal"
      class="form-ghost"
      v-bind="perIlCampo"
    />
  </label>
</template>
