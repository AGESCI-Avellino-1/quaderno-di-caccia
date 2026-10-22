<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { api, temaDellaBranca, type Unita } from '@/api/qdc'
import CopiaLocale from '@/components/CopiaLocale.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'

const { errore, esegui } = useErrore()
const unita = ref<Unita[]>([])
const copiaDel = ref<string | null>(null)

onMounted(async () => {
  const letto = await esegui(() => leggiConCache('unita', api.unita))
  if (letto) {
    unita.value = letto.dati
    copiaDel.value = letto.copiaDel
  }
})
</script>

<template>
  <section>
    <h1 class="h4 mb-3">Unità</h1>
    <div v-if="errore" class="alert alert-danger" role="alert">{{ errore }}</div>
    <CopiaLocale :del="copiaDel" />
    <div class="list-group">
      <RouterLink
        v-for="u in unita"
        :key="u.id"
        :to="{ name: 'persone', query: { unita: u.id } }"
        class="list-group-item list-group-item-action"
        :data-branca="temaDellaBranca(u.branca)"
      >
        <strong>{{ u.nome }}</strong>
        <span class="badge ms-2" style="background: var(--ag-primary); color: var(--ag-on-primary)">
          {{ u.branca }}
        </span>
      </RouterLink>
    </div>
  </section>
</template>
