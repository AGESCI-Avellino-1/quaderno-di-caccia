<script setup lang="ts">
import { computed, ref, useAttrs, watch } from 'vue'

// Bootstrap 6 avatar, as the theme's ag_avatar (DEC-298): the photo when there is one and
// it loads, otherwise the initials of the first two words of the name. With `scheda`
// (the person's id, given when the server says the user may open their file) the
// avatar, and only the avatar, opens the file (DEC-314).
defineOptions({ inheritAttrs: false })
const props = withDefaults(
  defineProps<{
    nome: string
    foto?: string | null
    dimensione?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
    tenue?: boolean
    scheda?: number | null
  }>(),
  { foto: null, dimensione: 'md', tenue: false, scheda: null },
)
const attributi = useAttrs()
// A link must reach screen readers even where the plain avatar is hidden from them.
const attributiLink = computed(() => {
  const altri = { ...attributi }
  delete altri['aria-hidden']
  return altri
})
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
  <RouterLink
    v-if="scheda !== null"
    :to="{ name: 'persona', params: { id: scheda } }"
    class="qdc-avatar-link"
    :aria-label="`Apri la scheda di ${nome}`"
    :title="`Apri la scheda di ${nome}`"
    v-bind="attributiLink"
  >
    <span
      class="avatar"
      :class="[
        dimensione !== 'md' && `avatar-${dimensione}`,
        !conFoto && 'theme-primary',
        !conFoto && tenue && 'avatar-subtle',
      ]"
    >
      <img v-if="conFoto" class="avatar-img" :src="foto!" :alt="nome" @error="suErrore" />
      <template v-else>
        <span aria-hidden="true">{{ iniziali }}</span>
        <span class="visually-hidden">{{ nome }}</span>
      </template>
    </span>
  </RouterLink>
  <span
    v-else
    v-bind="attributi"
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
