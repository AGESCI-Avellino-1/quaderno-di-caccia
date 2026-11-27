<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { api, type LibroCerimonie, type VoceLibroBreve } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The book of ceremonies and traditions (DEC-437): the entries one reads, ceremonies first,
// then traditions; who writes some entry also starts a new one. Off, the API answers 404
// (DEC-421). Online only for now.
const { errore, esegui } = useErrore()
const libro = ref<LibroCerimonie | null>(null)

onMounted(async () => {
  libro.value = (await esegui(() => api.libroCerimonie())) ?? null
})

const SEZIONI = [
  { tipo: 'CERIMONIA', titolo: 'Cerimonie' },
  { tipo: 'TRADIZIONE', titolo: 'Tradizioni' },
] as const
const perTipo = computed(() =>
  SEZIONI.map((s) => ({
    ...s,
    voci: (libro.value?.voci ?? []).filter((v: VoceLibroBreve) => v.tipo === s.tipo),
  })).filter((s) => s.voci.length),
)
</script>

<template>
  <section>
    <h1 class="h4">Cerimonie e tradizioni</h1>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>

    <template v-if="libro">
      <p class="fg-2 small">
        Le cerimonie e le tradizioni del gruppo. Alcune sono riservate: custodisci quello che leggi.
      </p>
      <RouterLink
        v-if="libro.puo_scrivere"
        :to="{ name: 'nuova-voce-libro' }"
        class="btn btn-solid theme-primary mb-5"
        >Nuova voce</RouterLink
      >
      <p v-if="!libro.voci.length" class="fg-2">Nessuna voce, per ora.</p>
      <section v-for="s in perTipo" :key="s.tipo" class="mb-7">
        <h2 class="h5">{{ s.titolo }}</h2>
        <div class="list-group">
          <RouterLink
            v-for="v in s.voci"
            :key="v.id"
            :to="{ name: 'voce-libro', params: { id: v.id } }"
            class="list-group-item list-group-item-action"
            :data-totem="v.cerimonia_del_totem || undefined"
          >
            <div>{{ v.titolo }}</div>
            <div class="small fg-2">{{ v.unita }}</div>
          </RouterLink>
        </div>
      </section>
    </template>
  </section>
</template>
