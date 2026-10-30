<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { api, testoDataParziale, type SentieroUnita } from '@/api/qdc'
import CopiaLocale from '@/components/CopiaLocale.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'

// The reparto at a glance (DEC-72): who has impegni to verify or drafts to agree, in
// alphabetical order, never ranked by "level" (DEC-71, spec §12.2). Cached for meetings
// without network (DEC-95).
const props = defineProps<{ id: number }>()
const { errore, esegui } = useErrore()
const dati = ref<SentieroUnita | null>(null)
const copiaDel = ref<string | null>(null)

watch(
  () => props.id,
  async (id) => {
    const letto = await esegui(() =>
      leggiConCache(`sentiero-unita:${id}`, () => api.sentieroUnita(id)),
    )
    dati.value = letto?.dati ?? null
    copiaDel.value = letto?.copiaDel ?? null
  },
  { immediate: true },
)
</script>

<template>
  <section>
    <div class="d-flex flex-wrap align-items-baseline gap-3">
      <h1 class="h4 mb-1">Sentiero del reparto</h1>
      <CopiaLocale :del="copiaDel" />
    </div>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <template v-if="dati">
      <p class="small fg-2">
        {{ dati.unita }}. <RouterLink :to="`/unita/${props.id}`">Pagina dell'unità</RouterLink> ·
        <RouterLink :to="`/unita/${props.id}/imprese`"
          >Imprese e specialità di squadriglia</RouterLink
        >
      </p>
      <p v-if="!dati.ragazzi.length" class="small">Nessun ragazzo nell'unità.</p>
      <ul v-else class="list-group">
        <li v-for="r in dati.ragazzi" :key="r.persona_id" class="list-group-item">
          <RouterLink
            :to="`/persone/${r.persona_id}/sentiero`"
            class="d-block text-decoration-none"
          >
            <div class="d-flex flex-wrap justify-content-between gap-3">
              <strong>{{ r.persona }}</strong>
              <span v-if="r.sentiero_aperto" class="small">
                {{ r.tappa }} dal {{ testoDataParziale(r.tappa_dal) }}
              </span>
              <span v-else class="small fg-2">sentiero da aprire</span>
            </div>
            <div v-if="r.sentiero_aperto" class="small d-flex flex-wrap gap-3">
              <span v-if="!r.promessa">Promessa da registrare</span>
              <span v-if="!r.distintivo">distintivo da consegnare</span>
              <span v-if="r.impegni_da_verificare" class="badge theme-warning">
                {{ r.impegni_da_verificare }} da verificare
              </span>
              <span v-if="r.bozze" class="badge theme-secondary">{{ r.bozze }} da concordare</span>
              <span>
                {{ r.impegni_in_corso }} impegni in corso · {{ r.mete_aperte }} mete ·
                {{ r.specialita }} specialità ·
                {{ r.brevetto ? `brevetto ${r.brevetto}` : 'nessun brevetto' }}
              </span>
            </div>
          </RouterLink>
        </li>
      </ul>
    </template>
  </section>
</template>
