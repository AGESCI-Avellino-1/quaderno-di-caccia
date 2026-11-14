<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, type StoriaReparto } from '@/api/qdc'
import ImmagineAnimale from '@/components/ImmagineAnimale.vue'
import { useErrore } from '@/composables/useErrore'

// Every patrol of one's reparto and of the linked one, of today and of the past, with no
// names of people: for esploratori and guide (DEC-407). Online only.
const { errore, esegui } = useErrore()
const reparti = ref<StoriaReparto[] | null>(null)
const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')

onMounted(async () => {
  reparti.value = (await esegui(() => api.storiaSquadriglie())) ?? null
})
</script>

<template>
  <section>
    <h1 class="h4">Storia delle squadriglie</h1>
    <p class="small fg-2">Le squadriglie del reparto, di oggi e del passato.</p>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <section v-for="r in reparti ?? []" :key="r.id" class="card card-body mb-5">
      <h2 v-if="(reparti?.length ?? 0) > 1" class="h5">{{ r.nome }}</h2>
      <p v-if="!r.squadriglie.length" class="fg-2 small mb-0">Nessuna squadriglia.</p>
      <ul class="list-unstyled mb-0">
        <li
          v-for="s in r.squadriglie"
          :key="s.id"
          class="d-flex align-items-center flex-wrap gap-3 border-top py-3"
          :class="{ 'opacity-75': !s.attiva }"
        >
          <ImmagineAnimale :animale="s.animale" />
          <strong>Sq. {{ s.nome }}</strong>
          <span class="fg-2 small">{{ s.sesso === 'F' ? 'femminile' : 'maschile' }}</span>
          <span v-if="!s.attiva" class="badge theme-secondary">Archiviata</span>
          <span class="small ms-auto">
            dal {{ data(s.dal) }}<template v-if="s.al"> al {{ data(s.al) }}</template>
            <template v-else> a oggi</template>
          </span>
        </li>
      </ul>
    </section>
  </section>
</template>
