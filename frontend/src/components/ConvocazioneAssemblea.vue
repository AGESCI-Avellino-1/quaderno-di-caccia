<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { api, convocazionePdf, type ConvocazioneModello, type DatiConvocazione } from '@/api/qdc'
import CampiLuogo from '@/components/CampiLuogo.vue'
import { useErrore } from '@/composables/useErrore'

// The assembly's convocation from the AGESCI template (DEC-337): the data make the letter,
// which goes with the email on the group's letterhead. Once sent it stays as it is.
const props = defineProps<{ evento: number }>()
const emit = defineEmits<{ salvata: [] }>()
const { errore, inCorso, esegui } = useErrore()
const modello = ref<ConvocazioneModello | null>(null)
const dati = ref<DatiConvocazione | null>(null)
const prima = ref('')
const salvato = ref(false)

const PUNTI = [
  { valore: 'REGOLAMENTO', nome: 'Regolamento dell’Assemblea (solo se ci sono modifiche)' },
  { valore: 'ELEZIONE', nome: 'Elezione dell’organo esecutivo e di amministrazione' },
  { valore: 'BILANCIO', nome: 'Bilancio d’esercizio' },
  { valore: 'QUOTA', nome: 'Quota associativa di Gruppo' },
  { valore: 'VARIE', nome: 'Varie ed eventuali' },
]

/** As datetime-local wants it: local time, no zone. */
function perIlCampo(iso: string): string {
  const d = new Date(iso)
  const due = (n: number) => String(n).padStart(2, '0')
  return (
    `${d.getFullYear()}-${due(d.getMonth() + 1)}-${due(d.getDate())}` +
    `T${due(d.getHours())}:${due(d.getMinutes())}`
  )
}

function mostra(ricevuto: ConvocazioneModello) {
  modello.value = ricevuto
  dati.value = ricevuto.dati
  prima.value = perIlCampo(ricevuto.prima_il)
}

onMounted(async () => {
  const ricevuto = await esegui(() => api.convocazioneModello(props.evento))
  if (ricevuto) mostra(ricevuto)
})

const anni = computed(() => {
  const adesso = new Date().getFullYear()
  return Array.from({ length: 6 }, (_, i) => adesso - 2 + i)
})
const etichetta = (anno: number) => `${anno - 1}/${anno}`
const servonoAnniElezione = computed(() =>
  dati.value?.punti.some((p) => p === 'ELEZIONE' || p === 'QUOTA'),
)
const serveAnnoBilancio = computed(() => dati.value?.punti.includes('BILANCIO'))

async function salva() {
  if (!dati.value) return
  salvato.value = false
  const corpo = {
    ...dati.value,
    prima_il: prima.value ? new Date(prima.value).toISOString() : null,
  }
  const ricevuto = await esegui(() => api.salvaConvocazioneModello(props.evento, corpo))
  if (!ricevuto) return
  mostra(ricevuto)
  salvato.value = true
  emit('salvata')
}
</script>

<template>
  <div v-if="modello && dati" class="mb-3">
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <form v-if="modello.puo_modificare" class="mb-3" @submit.prevent="salva">
      <fieldset class="mb-3">
        <legend class="form-label small">Ordine del giorno</legend>
        <div v-for="p in PUNTI" :key="p.valore" class="form-field mb-1">
          <input
            :id="`punto-${evento}-${p.valore}`"
            v-model="dati.punti"
            type="checkbox"
            class="check"
            :value="p.valore"
          />
          <label :for="`punto-${evento}-${p.valore}`">{{ p.nome }}</label>
        </div>
      </fieldset>
      <div class="row g-3 mb-3">
        <div class="col-12 sm:col-6">
          <label class="form-label small" :for="`prima-${evento}`">Prima convocazione</label>
          <input
            :id="`prima-${evento}`"
            v-model="prima"
            type="datetime-local"
            class="form-control form-control-sm"
          />
          <p class="small fg-2 mb-0 mt-1">
            Compare solo nella convocazione. La seconda è all'orario della riunione.
          </p>
        </div>
        <div v-if="serveAnnoBilancio" class="col-12 sm:col-3">
          <label class="form-label small" :for="`anno-bilancio-${evento}`">Anno del bilancio</label>
          <select
            :id="`anno-bilancio-${evento}`"
            v-model="dati.anno_bilancio"
            class="form-control form-control-sm"
          >
            <option v-for="a in anni" :key="a" :value="a">{{ etichetta(a) }}</option>
          </select>
        </div>
        <div v-if="servonoAnniElezione" class="col-12 sm:col-3">
          <label class="form-label small" :for="`anno-elezione-${evento}`">
            Anno di elezione e quota
          </label>
          <select
            :id="`anno-elezione-${evento}`"
            v-model="dati.anno_elezione"
            class="form-control form-control-sm"
          >
            <option v-for="a in anni" :key="a" :value="a">{{ etichetta(a) }}</option>
          </select>
        </div>
      </div>
      <h3 class="h6">Dove</h3>
      <CampiLuogo :id="`luogo-convocazione-${evento}`" v-model="dati.luogo" con-presso />
      <div class="d-flex flex-wrap align-items-center gap-3">
        <button type="submit" class="btn btn-sm btn-outline theme-primary" :disabled="inCorso">
          Salva i dati
        </button>
        <span v-if="salvato" class="small fg-2" role="status">Salvato.</span>
      </div>
    </form>

    <div v-if="modello.mancanti.length" class="alert theme-warning small" role="status">
      <div>Per inviarla manca: {{ modello.mancanti.join('; ') }}.</div>
    </div>
    <details class="mb-3">
      <summary>Anteprima della convocazione</summary>
      <!-- eslint-disable-next-line vue/no-v-html -- built by the server from escaped data -->
      <div class="mt-3" v-html="modello.testo"></div>
    </details>
    <a :href="convocazionePdf(evento)" class="btn btn-sm btn-outline theme-primary">
      Scarica il PDF della convocazione
    </a>
  </div>
</template>
