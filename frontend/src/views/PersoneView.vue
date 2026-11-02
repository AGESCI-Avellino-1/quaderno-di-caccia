<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { api, nomeUnita, type PersonaElenco, type Unita } from '@/api/qdc'
import CopiaLocale from '@/components/CopiaLocale.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'
import { useSessioneStore } from '@/stores/sessione'

// Members (capi and ragazzi) or parents, each with its own search.
const props = defineProps<{ tipo: 'soci' | 'genitori' }>()
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
    leggiConCache(`persone:${props.tipo}:${unitaScelta.value ?? 'tutte'}`, () =>
      api.persone(unitaScelta.value, props.tipo),
    ),
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
watch(
  () => props.tipo,
  () => {
    filtro.value = ''
    caricaPersone()
  },
)
</script>

<template>
  <section>
    <h1 class="h4 mb-5">{{ tipo === 'soci' ? 'Soci' : 'Genitori' }}</h1>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <CopiaLocale :del="copiaDel" />
    <div class="row g-3 mb-5">
      <div v-if="unita.length" class="col-12 md:col-5">
        <select v-model="unitaScelta" class="form-control" aria-label="Unità">
          <option :value="undefined">Tutte le unità</option>
          <option v-for="u in unita" :key="u.id" :value="u.id">{{ nomeUnita(u) }}</option>
        </select>
      </div>
      <div class="col">
        <input v-model="filtro" class="form-control" type="search" placeholder="Cerca per nome" />
      </div>
    </div>
    <p v-if="inCorso" class="fg-2">Caricamento…</p>
    <div v-else class="list-group">
      <RouterLink
        v-for="p in visibili"
        :key="p.id"
        :to="{ name: 'persona', params: { id: p.id } }"
        class="list-group-item list-group-item-action d-flex justify-content-between"
      >
        <span>{{ p.cognome }} {{ p.nome }}</span>
        <span v-if="p.codice_socio" class="fg-2 small">{{ p.codice_socio }}</span>
      </RouterLink>
      <p v-if="!visibili.length" class="fg-2">
        {{ tipo === 'soci' ? 'Nessun socio.' : 'Nessun genitore.' }}
      </p>
    </div>
  </section>
</template>
