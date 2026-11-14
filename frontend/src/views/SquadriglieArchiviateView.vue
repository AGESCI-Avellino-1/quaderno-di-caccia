<script setup lang="ts">
import { ref, watch } from 'vue'

import { api, type SquadrigliaArchiviata } from '@/api/qdc'
import ImmagineAnimale from '@/components/ImmagineAnimale.vue'
import { useErrore } from '@/composables/useErrore'

// The archived patrols of a unit, kept as a memory (DEC-403): read only, no way back.
// Reached only from the unit's page; online only.
const props = defineProps<{ id: number }>()
const { errore, esegui } = useErrore()
const archiviate = ref<SquadrigliaArchiviata[] | null>(null)
const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')

watch(
  () => props.id,
  async (id) => {
    archiviate.value = (await esegui(() => api.squadriglieArchiviate(id))) ?? null
  },
  { immediate: true },
)
</script>

<template>
  <section>
    <h1 class="h4">Squadriglie archiviate</h1>
    <p class="small fg-2">
      Restano qui per memoria e non si riattivano. Una squadriglia nuova può avere lo stesso
      animale, ma è un'altra squadriglia.
    </p>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <p v-else-if="archiviate && !archiviate.length" class="fg-2 small">
      Nessuna squadriglia archiviata.
    </p>
    <ul v-else-if="archiviate" class="list-unstyled">
      <li
        v-for="s in archiviate"
        :key="s.id"
        class="d-flex align-items-center flex-wrap gap-3 border-top py-3"
      >
        <ImmagineAnimale :animale="s.animale" />
        <strong>Sq. {{ s.nome }}</strong>
        <span class="fg-2 small">{{ s.sesso === 'F' ? 'femminile' : 'maschile' }}</span>
        <span class="small ms-auto">
          dal {{ data(s.dal) }}<template v-if="s.al"> al {{ data(s.al) }}</template>
        </span>
      </li>
    </ul>
  </section>
</template>
