<script setup lang="ts">
import Strength from 'bootstrap/js/dist/strength.js'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import Icona from '@/components/Icona.vue'

// Every password input (DEC-298): a button shows it in clear, as the theme's
// ag_password_field does. A new password also shows how strong it is (Bootstrap's
// strength meter): a hint only, the server's validators decide.
defineOptions({ inheritAttrs: false })

const valore = defineModel<string>({ required: true })
const props = withDefaults(
  defineProps<{ id: string; robustezza?: boolean; lunghezzaMinima?: number }>(),
  { robustezza: false, lunghezzaMinima: 8 },
)

const MESSAGGI = { weak: 'Debole', fair: 'Discreta', good: 'Buona', strong: 'Robusta' }

const visibile = ref(false)
const campo = ref<HTMLInputElement | null>(null)
const misura = ref<HTMLElement | null>(null)
let misuratore: Strength | null = null

onMounted(() => {
  if (props.robustezza && misura.value && campo.value) {
    misuratore = new Strength(misura.value, {
      input: campo.value,
      minLength: props.lunghezzaMinima,
      messages: MESSAGGI,
    })
  }
})

onBeforeUnmount(() => misuratore?.dispose())

// The meter listens to typing; a value set by the page (a reset) is measured here.
watch(valore, () => nextTick(() => misuratore?.evaluate()))
</script>

<template>
  <div>
    <div class="input-group">
      <input
        :id="id"
        ref="campo"
        v-model="valore"
        :type="visibile ? 'text' : 'password'"
        class="form-control"
        v-bind="$attrs"
      />
      <button
        type="button"
        class="btn-outline theme-secondary input-group-btn"
        :aria-pressed="visibile"
        :aria-controls="id"
        :aria-label="visibile ? 'Nascondi password' : 'Mostra password'"
        :title="visibile ? 'Nascondi password' : 'Mostra password'"
        @click="visibile = !visibile"
      >
        <Icona :nome="visibile ? 'eye-slash' : 'eye'" />
      </button>
    </div>
    <template v-if="robustezza">
      <div ref="misura" class="strength mt-2">
        <div class="strength-segment"></div>
        <div class="strength-segment"></div>
        <div class="strength-segment"></div>
        <div class="strength-segment"></div>
      </div>
      <small class="strength-text form-text" aria-live="polite"></small>
    </template>
  </div>
</template>
