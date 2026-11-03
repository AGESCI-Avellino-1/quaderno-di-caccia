<script setup lang="ts">
import OtpInput from 'bootstrap/js/dist/otp-input.js'
import { computed, onBeforeUnmount, onMounted, ref, useAttrs, watch, type StyleValue } from 'vue'

// A code of known length in one box per character (DEC-298): the code sent by email, the
// authenticator app's code, the PIN. Bootstrap's OTP input keeps a single <input>, so
// password managers and the code suggested by the phone keep working; `completo` fires
// as soon as every box is filled, and the page goes on without a button press.
defineOptions({ inheritAttrs: false })

const valore = defineModel<string>({ required: true })
const props = withDefaults(
  defineProps<{
    lunghezza: number
    tipo?: 'numeric' | 'alphanumeric'
    gruppi?: number[]
    maschera?: boolean
    invalido?: boolean
  }>(),
  { tipo: 'numeric', gruppi: undefined, maschera: false, invalido: false },
)
const emit = defineEmits<{ completo: [valore: string] }>()

// class and style go to the boxes, everything else (id, aria-label, autocomplete,
// disabled) to the input.
const attributi = useAttrs()
const perIlCampo = computed(() =>
  Object.fromEntries(
    Object.entries(attributi).filter(([nome]) => !['class', 'style'].includes(nome)),
  ),
)

const contenitore = ref<HTMLElement | null>(null)
let otp: OtpInput | null = null

function suInput(evento: Event) {
  valore.value = (evento as Event & { value: string }).value
}

function suCompleto(evento: Event) {
  emit('completo', (evento as Event & { value: string }).value)
}

onMounted(() => {
  const elemento = contenitore.value!
  otp = new OtpInput(elemento, {
    length: props.lunghezza,
    type: props.tipo,
    groups: props.gruppi ?? null,
    mask: props.maschera,
    separator: '-',
  })
  elemento.addEventListener('input.bs.otpInput', suInput)
  elemento.addEventListener('complete.bs.otpInput', suCompleto)
  if (valore.value) otp.setValue(valore.value)
})

onBeforeUnmount(() => {
  contenitore.value?.removeEventListener('input.bs.otpInput', suInput)
  contenitore.value?.removeEventListener('complete.bs.otpInput', suCompleto)
  otp?.dispose()
})

// The page clears the code after a wrong one: show the empty boxes again.
watch(valore, (nuovo) => {
  if (otp && nuovo !== otp.getValue()) otp.setValue(nuovo)
})

defineExpose({ focus: () => otp?.focus() })
</script>

<template>
  <div
    ref="contenitore"
    class="otp"
    :class="[attributi.class, { 'is-invalid': invalido }]"
    :style="attributi.style as StyleValue"
  >
    <input type="text" class="form-control" v-bind="perIlCampo" />
  </div>
</template>
