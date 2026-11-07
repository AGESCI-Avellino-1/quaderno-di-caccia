<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import {
  api,
  euro,
  giustificativoSpesa,
  nomeUnita,
  type Cassa,
  type SpesaAnticipata,
  type Unita,
} from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Expenses paid by capi (DEC-86): every one in the cash book, those this user must still
// refund on their own page (DEC-379). The buttons follow what the server says.
const props = defineProps<{
  casse: Cassa[]
  unita: Unita[]
  soloDaRimborsare?: boolean
}>()
const emit = defineEmits<{ cambiato: [] }>()

const { errore, inCorso, esegui } = useErrore()
const spese = ref<SpesaAnticipata[]>([])
const elenco = computed(() =>
  props.soloDaRimborsare ? spese.value.filter((s) => s.puo_rimborsare) : spese.value,
)
const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
const etichettaUnita = (id: number | null) => {
  const trovata = props.unita.find((u) => u.id === id)
  return trovata ? nomeUnita(trovata) : 'Gruppo'
}

async function carica() {
  spese.value = (await esegui(() => api.speseAnticipate())) ?? []
}
onMounted(carica)

const rimborso = reactive({ id: 0, cassa_id: null as number | null, motivo: '', azione: '' })
async function rimborsa() {
  const fatto = await esegui(() =>
    rimborso.azione === 'rimborsa'
      ? api.rimborsaSpesa(rimborso.id, rimborso.cassa_id!)
      : api.respingiSpesa(rimborso.id, rimborso.motivo),
  )
  if (!fatto) return
  rimborso.id = 0
  await carica()
  emit('cambiato')
}
</script>

<template>
  <div>
    <p class="form-text">
      Le spese pagate di tasca propria dai capi: diventano un'uscita, alla voce Rimborsi spese
      volontari, quando le rimborsi. Ogni capo le registra dalla pagina Le mie spese.
    </p>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <p v-if="!elenco.length && !inCorso" class="fg-2">
      {{ soloDaRimborsare ? 'Nessuna spesa da rimborsare.' : 'Nessuna spesa.' }}
    </p>
    <ul class="list-group">
      <li v-for="s in elenco" :key="s.id" class="list-group-item">
        <div class="d-flex flex-wrap justify-content-between gap-3">
          <span>{{ data(s.data) }} · {{ s.capo }} · {{ s.descrizione }}</span>
          <strong>{{ euro(s.importo) }}</strong>
        </div>
        <div class="small fg-2">
          {{ etichettaUnita(s.unita_id) }}
          <template v-if="s.stato === 'rimborsata'">
            · rimborsata il {{ data(s.rimborsata_il!) }}</template
          >
          <template v-else-if="s.stato === 'respinta'">
            · respinta: {{ s.motivo_rifiuto }}</template
          >
          <template v-else> · da rimborsare</template>
          ·
          <a v-if="s.ha_giustificativo" :href="giustificativoSpesa(s.id)" target="_blank"
            >giustificativo</a
          >
          <template v-else>senza giustificativo</template>
        </div>
        <div v-if="s.puo_rimborsare && rimborso.id !== s.id" class="d-flex gap-3 mt-1">
          <button
            type="button"
            class="btn btn-sm btn-link"
            @click="Object.assign(rimborso, { id: s.id, azione: 'rimborsa', cassa_id: null })"
          >
            Rimborsa
          </button>
          <button
            type="button"
            class="btn btn-sm btn-link"
            @click="Object.assign(rimborso, { id: s.id, azione: 'respingi', motivo: '' })"
          >
            Respingi
          </button>
        </div>
        <form
          v-if="rimborso.id === s.id"
          class="d-flex flex-wrap align-items-end gap-3 mt-3"
          @submit.prevent="rimborsa"
        >
          <div v-if="rimborso.azione === 'rimborsa'">
            <label class="form-label small" :for="`rimborso-${s.id}`">Da quale cassa</label>
            <select
              :id="`rimborso-${s.id}`"
              v-model="rimborso.cassa_id"
              class="form-control form-control-sm"
              required
            >
              <option
                v-for="c in casse.filter((x) => x.puo_registrare && x.attiva)"
                :key="c.id"
                :value="c.id"
              >
                {{ c.nome }}
              </option>
            </select>
          </div>
          <div v-else class="flex-grow-1">
            <label class="form-label small" :for="`respingi-${s.id}`">Perché la respingi?</label>
            <input
              :id="`respingi-${s.id}`"
              v-model="rimborso.motivo"
              class="form-control form-control-sm"
              required
            />
          </div>
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            {{ rimborso.azione === 'rimborsa' ? 'Rimborsa' : 'Respingi' }}
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="rimborso.id = 0">
            Annulla
          </button>
        </form>
      </li>
    </ul>
  </div>
</template>
