<script setup lang="ts">
import { reactive, ref } from 'vue'

import { api, type PuntoStrada, type SchedaProgressione } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The Punti della Strada of a rover or a scolta (DEC-67): simple and repeatable, with the
// service verified and the obiettivi set or recalibrated. The private part (what was
// faced in confidence with the capi and the assistente ecclesiastico) comes as null to
// who may not read it, the parents too (DEC-180). Written online by the staff: it is
// not a camp task and the private text must not wait in the queue.
const props = defineProps<{
  periodo: number
  punti: PuntoStrada[]
  obiettivi: { id: number; testo: string }[]
  gestisce: boolean
}>()
const emit = defineEmits<{ salvata: [scheda: SchedaProgressione] }>()
const { errore, inCorso, esegui } = useErrore()
const oggi = () => new Date().toLocaleDateString('sv')
const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')

// 0: closed; -1: new; otherwise the id being edited.
const aperto = ref(0)
const modulo = reactive({
  data: oggi(),
  sintesi: '',
  servizio: '',
  riservato: '',
  obiettivi: [] as number[],
})

function apri(punto: PuntoStrada | null) {
  aperto.value = punto ? punto.id : -1
  Object.assign(modulo, {
    data: punto?.data ?? oggi(),
    sintesi: punto?.sintesi ?? '',
    servizio: punto?.servizio ?? '',
    riservato: punto?.riservato ?? '',
    obiettivi: [...(punto?.obiettivi ?? [])],
  })
}

async function salva() {
  const dati = { ...modulo, obiettivi: [...modulo.obiettivi] }
  const scheda = await esegui(() =>
    aperto.value === -1
      ? api.nuovoPuntoStrada(props.periodo, dati)
      : api.modificaPuntoStrada(aperto.value, dati),
  )
  if (!scheda) return
  aperto.value = 0
  emit('salvata', scheda)
}

const nomi = (ids: number[]) =>
  ids
    .map((id) => props.obiettivi.find((o) => o.id === id)?.testo)
    .filter(Boolean)
    .join('; ')
</script>

<template>
  <section class="mb-5">
    <div class="d-flex flex-wrap align-items-center gap-3 mb-3">
      <h2 class="h5 mb-0">Punti della Strada</h2>
      <button
        v-if="gestisce && !aperto"
        type="button"
        class="btn btn-sm btn-outline theme-primary"
        @click="apri(null)"
      >
        Nuovo Punto della Strada
      </button>
    </div>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>

    <form v-if="aperto" class="card card-body mb-3" @submit.prevent="salva">
      <label class="form-label small" for="ps-data">Data</label>
      <input
        id="ps-data"
        v-model="modulo.data"
        type="date"
        :max="oggi()"
        class="form-control form-control-sm w-auto mb-3"
        required
      />
      <label class="form-label small" for="ps-sintesi">Com'è la strada (sintesi)</label>
      <textarea
        id="ps-sintesi"
        v-model="modulo.sintesi"
        class="form-control form-control-sm mb-3"
        rows="3"
      />
      <label class="form-label small" for="ps-servizio">Il servizio, verificato</label>
      <textarea
        id="ps-servizio"
        v-model="modulo.servizio"
        class="form-control form-control-sm mb-3"
        rows="2"
      />
      <label class="form-label small" for="ps-riservato">
        Parte riservata (la leggono solo il rover o la scolta e i capi, non i genitori)
      </label>
      <textarea
        id="ps-riservato"
        v-model="modulo.riservato"
        class="form-control form-control-sm mb-3"
        rows="2"
      />
      <fieldset v-if="obiettivi.length" class="mb-3">
        <legend class="form-label small">Obiettivi fissati o ricalibrati</legend>
        <div v-for="o in obiettivi" :key="o.id" class="form-field">
          <input
            :id="`ps-ob-${o.id}`"
            v-model="modulo.obiettivi"
            type="checkbox"
            class="check"
            :value="o.id"
          />
          <label class="small" :for="`ps-ob-${o.id}`">{{ o.testo }}</label>
        </div>
      </fieldset>
      <div class="d-flex gap-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Salva
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="aperto = 0">Annulla</button>
      </div>
    </form>

    <p v-if="!punti.length" class="small fg-2">
      Nessun Punto della Strada: si fa quando serve, quante volte serve.
    </p>
    <ul v-else class="list-group">
      <li v-for="p in [...punti].reverse()" :key="p.id" class="list-group-item">
        <div class="d-flex flex-wrap justify-content-between gap-3">
          <strong>{{ data(p.data) }}</strong>
          <button
            v-if="gestisce && !aperto"
            type="button"
            class="btn btn-sm btn-link"
            @click="apri(p)"
          >
            Modifica
          </button>
        </div>
        <p v-if="p.sintesi" class="small testo-a-capo mb-1">{{ p.sintesi }}</p>
        <p v-if="p.servizio" class="small testo-a-capo mb-1">
          <strong>Servizio</strong>: {{ p.servizio }}
        </p>
        <p v-if="p.riservato" class="small testo-a-capo mb-1">
          <span class="badge theme-inverse">riservato</span> {{ p.riservato }}
        </p>
        <p v-if="p.obiettivi.length" class="small fg-2 mb-0">Obiettivi: {{ nomi(p.obiettivi) }}.</p>
      </li>
    </ul>
  </section>
</template>
