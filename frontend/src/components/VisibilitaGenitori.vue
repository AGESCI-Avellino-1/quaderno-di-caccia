<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

import { api, type VisibilitaGenitori } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// At 18 the member chooses what their parents keep seeing (DEC-26): by category, the
// same for all parents; until they choose, everything stays visible. The backend
// answers 404 to anyone but the adult member themself. Online only.
const props = defineProps<{ id: number }>()
const { errore, inCorso, esegui } = useErrore()
const stato = ref<VisibilitaGenitori | null>(null)
const scelte = reactive({ contatti: true, sanitarie: true, scheda: true, quote: true })
const salvato = ref(false)

const voci = [
  { chiave: 'contatti', etichetta: 'Contatti e indirizzo' },
  { chiave: 'sanitarie', etichetta: 'Farmaci, allergie e alimentazione' },
  { chiave: 'scheda', etichetta: 'La mia scheda e le attività (unità, presenze, progressione)' },
  { chiave: 'quote', etichetta: 'Le mie quote, i pagamenti e le ricevute' },
] as const

function mostra(dati: VisibilitaGenitori) {
  stato.value = dati
  Object.assign(scelte, {
    contatti: dati.contatti,
    sanitarie: dati.sanitarie,
    scheda: dati.scheda,
    quote: dati.quote,
  })
}

watch(
  () => props.id,
  async (id) => {
    try {
      mostra(await api.visibilitaGenitori(id))
    } catch {
      stato.value = null
    }
  },
  { immediate: true },
)

async function salva() {
  salvato.value = false
  const dati = await esegui(() => api.scegliVisibilitaGenitori(props.id, { ...scelte }))
  if (!dati) return
  mostra(dati)
  salvato.value = true
}
</script>

<template>
  <section v-if="stato?.genitori.length" class="card card-body mb-5">
    <h2 class="h5 mb-1">Cosa vedono i tuoi genitori</h2>
    <p class="form-text mb-3">
      Sei maggiorenne: decidi tu cosa possono vedere {{ stato.genitori.join(' e ') }}.
      <template v-if="!stato.decisa_il">Finché non scegli, vedono tutto.</template>
      I tuoi capi vedono comunque tutto.
    </p>
    <div v-if="errore" class="alert theme-danger py-3 small" role="alert">{{ errore }}</div>
    <form class="vstack gap-3" @submit.prevent="salva">
      <div v-for="v in voci" :key="v.chiave" class="form-field">
        <input
          :id="`visibile-${v.chiave}`"
          v-model="scelte[v.chiave]"
          type="checkbox"
          class="switch"
          role="switch"
          @change="salvato = false"
        />
        <label :for="`visibile-${v.chiave}`">{{ v.etichetta }}</label>
      </div>
      <div class="d-flex align-items-center gap-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Salva
        </button>
        <span v-if="salvato" class="small fg-success" role="status">Salvato</span>
        <span v-else-if="stato.decisa_il" class="small fg-2">
          Scelta del {{ new Date(stato.decisa_il).toLocaleDateString('it-IT') }}
        </span>
      </div>
    </form>
  </section>
</template>
