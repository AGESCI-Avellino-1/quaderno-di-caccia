<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { api, type Rotazione, type TurniUnita } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The turns of a reparto (to its patrols) or of a branco/cerchio (to its sestiglie),
// DEC-312: the staff writes them, one per line, and chooses how often they change. Hidden
// to who may not manage them (the server answers 403). Online only.
// `nome`: the unit's name, with a linked unit's on the same page (DEC-405).
const props = defineProps<{ unita: number; nome?: string }>()
const { errore, inCorso, esegui } = useErrore()
const visibile = ref(false)
const turni = ref<TurniUnita | null>(null)
const testo = ref('')
const rotazione = ref<Rotazione>('SETTIMANALE')
const dal = ref(new Date().toLocaleDateString('sv'))
const conCollegata = ref(false)
const esito = ref('')

function leggi(t: TurniUnita) {
  turni.value = t
  testo.value = t.nomi.join('\n')
  rotazione.value = t.rotazione
  if (t.dal) dal.value = t.dal
  conCollegata.value = t.con_collegata
}

onMounted(async () => {
  try {
    leggi(await api.turniUnita(props.unita))
    visibile.value = true
  } catch {
    visibile.value = false
  }
})

const nomi = computed(() =>
  testo.value
    .split('\n')
    .map((n) => n.trim())
    .filter(Boolean),
)

async function salva() {
  esito.value = ''
  const fatti = await esegui(() =>
    api.impostaTurni(props.unita, {
      nomi: nomi.value,
      rotazione: rotazione.value,
      dal: dal.value,
      con_collegata: conCollegata.value,
    }),
  )
  if (!fatti) return
  leggi(fatti)
  esito.value = fatti.nomi.length ? 'Turni salvati.' : 'Turni tolti.'
}

const giorno = (iso: string) =>
  new Date(iso).toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'short' })
</script>

<template>
  <section v-if="visibile && turni" class="card card-body mb-5">
    <h2 class="h5">
      Turni<template v-if="nome"> · {{ nome }}</template>
    </h2>
    <p class="small fg-2">
      I turni (per esempio pulizia, preghiera, cassa) passano a rotazione tra
      {{ turni.gruppi.length ? turni.gruppi.join(', ') : 'le squadriglie o le sestiglie' }}. Con
      «ogni settimana» il turno passa al gruppo dopo a ogni riunione dell'unità che si fa (una
      settimana senza riunione non conta); con «ogni mese» alla prima riunione del mese. Ragazzi/e e
      genitori vedono il loro turno nelle riunioni.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>
    <form class="row g-3" @submit.prevent="salva">
      <div class="md:col-6">
        <label class="form-label small" :for="`turni-${unita}`">I turni, uno per riga</label>
        <textarea
          :id="`turni-${unita}`"
          v-model="testo"
          class="form-control form-control-sm"
          rows="4"
          placeholder="Pulizia&#10;Preghiera"
        ></textarea>
      </div>
      <div class="md:col-6">
        <label class="form-label small" :for="`turni-rotazione-${unita}`">Cambiano</label>
        <select
          :id="`turni-rotazione-${unita}`"
          v-model="rotazione"
          class="form-control form-control-sm mb-3"
        >
          <option value="SETTIMANALE">Ogni settimana</option>
          <option value="MENSILE">Ogni mese</option>
        </select>
        <label class="form-label small" :for="`turni-dal-${unita}`">Dal</label>
        <input
          :id="`turni-dal-${unita}`"
          v-model="dal"
          type="date"
          class="form-control form-control-sm"
          required
        />
        <div v-if="turni.collegata" class="form-field mt-3 mb-0">
          <input
            :id="`turni-insieme-${unita}`"
            v-model="conCollegata"
            type="checkbox"
            class="check"
          />
          <label :for="`turni-insieme-${unita}`">Insieme a {{ turni.collegata }}</label>
        </div>
      </div>
      <div class="col-12">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Salva i turni
        </button>
      </div>
    </form>
    <div v-if="turni.prossime.length" class="mt-5">
      <h3 class="h6">Prossime riunioni</h3>
      <ul class="list-unstyled small mb-0">
        <li v-for="p in turni.prossime" :key="p.id" class="py-1 border-bottom">
          <RouterLink :to="{ name: 'riunione', params: { id: p.id } }">{{
            giorno(p.inizio)
          }}</RouterLink
          >:
          <span v-for="(t, n) in p.turni" :key="t.turno">
            {{ n ? ' · ' : '' }}{{ t.turno }} {{ t.gruppo }}
          </span>
        </li>
      </ul>
    </div>
  </section>
</template>
