<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { api, type LibroCerimonie, type VoceLibroBreve } from '@/api/qdc'
import CopiaLocale from '@/components/CopiaLocale.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'
import { aggiornaTesti } from '@/offline/cerimonie'

// The book of ceremonies and traditions (DEC-437): the entries one reads, ceremonies first,
// then traditions; who writes some entry also starts a new one. Off, the API answers 404
// (DEC-421). Opened with the network, it saves the list and the texts on the device.
const { errore, esegui } = useErrore()
const libro = ref<LibroCerimonie | null>(null)
const copiaDel = ref<string | null>(null)

onMounted(async () => {
  const letto = await esegui(() => leggiConCache('cerimonie', () => api.libroCerimonie()))
  libro.value = letto?.dati ?? null
  copiaDel.value = letto?.copiaDel ?? null
  // Also when the book is refused: the texts' copy goes with it.
  if (!copiaDel.value) await aggiornaTesti()
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
      <CopiaLocale :del="copiaDel" />
      <p class="fg-2 small">
        Le cerimonie e le tradizioni del gruppo. Alcune sono riservate: custodisci quello che leggi.
      </p>
      <RouterLink
        v-if="libro.puo_scrivere && !copiaDel"
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
