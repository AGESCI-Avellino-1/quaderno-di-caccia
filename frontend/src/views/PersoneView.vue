<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { api, nomeUnita, type PersonaElenco, type Unita } from '@/api/qdc'
import Avatar from '@/components/Avatar.vue'
import BarraRubrica from '@/components/BarraRubrica.vue'
import CopiaLocale from '@/components/CopiaLocale.vue'
import InvitiMultipli from '@/components/InvitiMultipli.vue'
import SceltaChip from '@/components/SceltaChip.vue'
import { useErrore } from '@/composables/useErrore'
import { useRubrica } from '@/composables/useRubrica'
import { leggiConCache } from '@/offline/cache'
import { useNavigazioneStore } from '@/stores/navigazione'
import { useSessioneStore } from '@/stores/sessione'

// Members (capi and ragazzi) or parents, each with its own search.
const props = defineProps<{ tipo: 'soci' | 'genitori' }>()
const sessione = useSessioneStore()
const navigazione = useNavigazioneStore()
const route = useRoute()
const { errore, inCorso, esegui } = useErrore()

const persone = ref<PersonaElenco[]>([])
const unita = ref<Unita[]>([])
const unitaScelta = ref<number | undefined>(
  route.query.unita ? Number(route.query.unita) : undefined,
)
const filtro = ref('')
// From the unit page, «Aggiungi alla rubrica» opens this list ready to choose (DEC-302).
const rubrica = useRubrica()
rubrica.attiva.value = route.query.rubrica === '1'
const copiaDel = ref<string | null>(null)
// Several invitations at once (DEC-308): the list gives way to the candidates.
const invitando = ref(false)

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
watch(
  () => props.tipo,
  (tipo) => (navigazione.elencoPersone = tipo === 'genitori' ? 'genitori' : 'persone'),
  { immediate: true },
)
</script>

<template>
  <section>
    <h1 class="h4 mb-5">{{ tipo === 'soci' ? 'Soci' : 'Genitori' }}</h1>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <CopiaLocale :del="copiaDel" />
    <div class="row g-3 mb-5">
      <div v-if="unita.length" class="col-12">
        <SceltaChip
          v-model="unitaScelta"
          :scelte="[
            { valore: undefined, nome: 'Tutte le unità' },
            ...unita.map((u) => ({ valore: u.id, nome: nomeUnita(u) })),
          ]"
          etichetta="Unità"
        />
      </div>
      <div class="col-12">
        <input v-model="filtro" class="form-control" type="search" placeholder="Cerca per nome" />
      </div>
    </div>
    <BarraRubrica v-if="!invitando" :rubrica="rubrica" :tutti="visibili.map((p) => p.id)" />
    <InvitiMultipli
      v-if="sessione.capo && !rubrica.attiva.value"
      v-model:attivo="invitando"
      :unita="unitaScelta"
      :tipo="tipo"
    />
    <p v-if="inCorso" class="fg-2">Caricamento…</p>
    <div v-else-if="!invitando" class="list-group">
      <template v-for="p in visibili" :key="p.id">
        <!-- Choosing whom to put in the phone's contacts (DEC-302). -->
        <label
          v-if="rubrica.attiva.value"
          class="list-group-item list-group-item-action d-flex align-items-center gap-3"
        >
          <input
            type="checkbox"
            class="check"
            :checked="rubrica.scelti.value.has(p.id)"
            @change="rubrica.alterna(p.id)"
          />
          <!-- The row ticks the person; the avatar still opens the file (DEC-314). -->
          <Avatar
            :nome="`${p.nome} ${p.cognome}`"
            :scheda="p.id"
            dimensione="sm"
            tenue
            aria-hidden="true"
          />
          <span class="me-auto">{{ p.cognome }} {{ p.nome }}</span>
        </label>
        <RouterLink
          v-else
          :to="{ name: 'persona', params: { id: p.id } }"
          class="list-group-item list-group-item-action d-flex align-items-center gap-3"
        >
          <Avatar :nome="`${p.nome} ${p.cognome}`" dimensione="sm" tenue aria-hidden="true" />
          <span class="me-auto">{{ p.cognome }} {{ p.nome }}</span>
          <span v-if="p.codice_socio" class="fg-2 small">{{ p.codice_socio }}</span>
        </RouterLink>
      </template>
      <p v-if="!visibili.length" class="fg-2">
        {{ tipo === 'soci' ? 'Nessun socio.' : 'Nessun genitore.' }}
      </p>
    </div>
  </section>
</template>
