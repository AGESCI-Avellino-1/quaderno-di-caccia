<script setup lang="ts">
import { ref, watch } from 'vue'

import { api, type IncarichiDiSquadriglia, type PersonaBreve } from '@/api/qdc'
import ElencoIncarichi from '@/components/ElencoIncarichi.vue'
import ImmagineAnimale from '@/components/ImmagineAnimale.vue'
import { leggiConCache } from '@/offline/cache'

// The roles of a patrol (DEC-321), from the patrol's page (`squadriglia`, with its members
// to choose from: the CSQ assigns them there) or from a person's file (`persona`: read by
// the parents). The backend answers 404 to anyone else, and the box stays hidden.
const props = defineProps<{ squadriglia?: number; persona?: number; membri?: PersonaBreve[] }>()
const dati = ref<IncarichiDiSquadriglia | null>(null)

async function carica() {
  const { squadriglia, persona } = props
  try {
    const letti =
      squadriglia !== undefined
        ? await leggiConCache(`incarichi-squadriglia-${squadriglia}`, () =>
            api.incarichiSquadriglia(squadriglia),
          )
        : await leggiConCache(`incarichi-squadriglia-di-${persona}`, () =>
            api.incarichiSquadrigliaDi(persona!),
          )
    dati.value = letti.dati
  } catch {
    dati.value = null
  }
}

watch(() => [props.squadriglia, props.persona], carica, { immediate: true })
</script>

<template>
  <section v-if="dati" :class="persona !== undefined && 'card card-body mb-5'">
    <h2 v-if="persona !== undefined" class="h5 mb-3">
      <ImmagineAnimale :animale="dati.animale" />
      Incarichi nella squadriglia {{ dati.nome }}
    </h2>
    <h3 v-else class="h6 mb-3">Incarichi</h3>
    <ElencoIncarichi
      :incarichi="dati.incarichi"
      :nomina="membri ? dati.nomina : []"
      :dove="{ squadriglia_id: dati.id }"
      :candidati="async () => membri ?? []"
      @cambiato="carica()"
    />
  </section>
</template>
