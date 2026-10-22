<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { api, type PersonaElenco, type Unita } from '@/api/qdc'
import CopiaLocale from '@/components/CopiaLocale.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'
import { useSessioneStore } from '@/stores/sessione'

const sessione = useSessioneStore()
const route = useRoute()
const { errore, inCorso, esegui } = useErrore()

const persone = ref<PersonaElenco[]>([])
const unita = ref<Unita[]>([])
const unitaScelta = ref<number | undefined>(
  route.query.unita ? Number(route.query.unita) : undefined,
)
const filtro = ref('')
const copiaDel = ref<string | null>(null)

const visibili = computed(() => {
  const testo = filtro.value.trim().toLowerCase()
  if (!testo) return persone.value
  return persone.value.filter((p) => `${p.cognome} ${p.nome}`.toLowerCase().includes(testo))
})

async function caricaPersone() {
  const letto = await esegui(() =>
    leggiConCache(`persone:${unitaScelta.value ?? 'tutte'}`, () => api.persone(unitaScelta.value)),
  )
  if (letto) {
    persone.value = letto.dati
    copiaDel.value = letto.copiaDel
  }
}

onMounted(async () => {
  if (sessione.capo) {
    const letto = await esegui(() => leggiConCache('unita', api.unita))
    if (letto) unita.value = letto.dati
  }
  await caricaPersone()
})
watch(unitaScelta, caricaPersone)
</script>

<template>
  <section>
    <h1 class="h4 mb-3">Persone</h1>
    <div v-if="errore" class="alert alert-danger" role="alert">{{ errore }}</div>
    <CopiaLocale :del="copiaDel" />
    <div class="row g-2 mb-3">
      <div v-if="unita.length" class="col-12 col-md-5">
        <select v-model="unitaScelta" class="form-select" aria-label="Unità">
          <option :value="undefined">Tutte le unità</option>
          <option v-for="u in unita" :key="u.id" :value="u.id">{{ u.nome }}</option>
        </select>
      </div>
      <div class="col">
        <input v-model="filtro" class="form-control" type="search" placeholder="Cerca per nome" />
      </div>
    </div>
    <p v-if="inCorso" class="text-body-secondary">Caricamento…</p>
    <div v-else class="list-group">
      <RouterLink
        v-for="p in visibili"
        :key="p.id"
        :to="{ name: 'persona', params: { id: p.id } }"
        class="list-group-item list-group-item-action d-flex justify-content-between"
      >
        <span>{{ p.cognome }} {{ p.nome }}</span>
        <span v-if="p.codice_socio" class="text-body-secondary small">{{ p.codice_socio }}</span>
      </RouterLink>
      <p v-if="!visibili.length" class="text-body-secondary">Nessuna persona.</p>
    </div>
  </section>
</template>
