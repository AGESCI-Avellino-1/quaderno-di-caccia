<script setup lang="ts">
import { computed, ref, watch } from 'vue'

// Bootstrap 6 avatar, as the theme's ag_avatar (DEC-298): the photo when there is one and
// it loads, otherwise the initials of the first two words of the name.
const props = withDefaults(
  defineProps<{
    nome: string
    foto?: string | null
    dimensione?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
    tenue?: boolean
  }>(),
  { foto: null, dimensione: 'md', tenue: false },
)
const emit = defineEmits<{ errore: [] }>()

const fallita = ref(false)
watch(
  () => props.foto,
  () => (fallita.value = false),
)

const iniziali = computed(() =>
  props.nome
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((parola) => parola[0])
    .join('')
    .toUpperCase(),
)
const conFoto = computed(() => !!props.foto && !fallita.value)

function suErrore() {
  fallita.value = true
  emit('errore')
}
</script>

<template>
  <span
    class="avatar"
    :class="[
      dimensione !== 'md' && `avatar-${dimensione}`,
      !conFoto && 'theme-primary',
      !conFoto && tenue && 'avatar-subtle',
    ]"
    :title="conFoto ? undefined : nome"
  >
    <img v-if="conFoto" class="avatar-img" :src="foto!" :alt="nome" @error="suErrore" />
    <template v-else>
      <span aria-hidden="true">{{ iniziali }}</span>
      <span class="visually-hidden">{{ nome }}</span>
    </template>
  </span>
</template>
