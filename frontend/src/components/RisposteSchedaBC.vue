<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

import {
  api,
  fileFotoBC,
  type IscrizioneBC,
  type RispostaScheda,
  type VersioneScheda,
} from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The event form on BuonaCaccia, answered in the app by the participant or a parent
// (DEC-161), or written by who manages the registration from a paper form; the photo becomes a JPEG of at most 1 MB on the server (DEC-162). Saved also
// when incomplete; closed once the staff filled it in on BuonaCaccia. Online only: the
// answers and the photo are personal data that do not need to wait offline.
const props = defineProps<{ iscrizione: IscrizioneBC; scheda: VersioneScheda; modifica: boolean }>()
const emit = defineEmits<{ cambiata: [iscrizione: IscrizioneBC] }>()
const { errore, inCorso, esegui } = useErrore()
const risposte = reactive<Record<string, RispostaScheda>>({})
const salvate = ref(false)

watch(
  () => props.iscrizione.risposte,
  (date) => {
    for (const chiave of Object.keys(risposte)) delete risposte[chiave]
    for (const d of props.scheda.domande) {
      const data = date[d.id]
      if (d.tipo === 'SCELTA_MULTIPLA') risposte[d.id] = Array.isArray(data) ? [...data] : []
      else if (d.tipo !== 'FOTO') risposte[d.id] = data ?? ''
    }
  },
  { immediate: true },
)

const chiusa = () => !!props.iscrizione.scheda_inviata_il || !props.iscrizione.attiva

function scelta(id: string, opzione: string, presa: boolean) {
  const attuali = (risposte[id] as string[]).filter((o) => o !== opzione)
  risposte[id] = presa ? [...attuali, opzione] : attuali
}

function scrivi(id: string, evento: Event) {
  risposte[id] = (evento.target as HTMLInputElement | HTMLTextAreaElement).value
}

function siNo(id: string, valore: string) {
  risposte[id] = valore === '' ? '' : valore === 'si'
}

async function salva() {
  salvate.value = false
  const dati = await esegui(() => api.risposteBC(props.iscrizione.id, { ...risposte }))
  if (!dati) return
  salvate.value = true
  emit('cambiata', dati)
}

async function foto(evento: Event) {
  const input = evento.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  const dati = await esegui(() => api.caricaFotoBC(props.iscrizione.id, file))
  input.value = ''
  if (dati) emit('cambiata', dati)
}

async function fotoProfilo() {
  const dati = await esegui(() => api.usaFotoProfiloBC(props.iscrizione.id))
  if (dati) emit('cambiata', dati)
}

const testoSiNo = (valore: RispostaScheda | undefined) =>
  valore === true ? 'Sì' : valore === false ? 'No' : ''
const testo = (valore: RispostaScheda | undefined) =>
  Array.isArray(valore)
    ? valore.join(', ')
    : typeof valore === 'boolean'
      ? testoSiNo(valore)
      : (valore ?? '')
</script>

<template>
  <div>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <p v-if="iscrizione.scheda_inviata_il" class="small fg-2">
      Lo staff ha compilato la scheda su BuonaCaccia il
      {{ new Date(iscrizione.scheda_inviata_il).toLocaleDateString('it-IT') }}: le risposte non si
      cambiano più.
    </p>

    <!-- Read only: capi who do not manage, or a closed form. -->
    <dl v-if="!modifica || chiusa()" class="small mb-0">
      <template v-for="d in scheda.domande" :key="d.id">
        <dt>{{ d.testo }}</dt>
        <dd v-if="d.tipo === 'FOTO'">
          <a v-if="iscrizione.foto" :href="fileFotoBC(iscrizione.id)">Foto (JPG)</a>
          <span v-else class="fg-2">nessuna foto</span>
        </dd>
        <dd v-else class="testo-a-capo">
          {{ testo(iscrizione.risposte[d.id]) || '—' }}
        </dd>
      </template>
    </dl>

    <form v-else class="d-flex flex-column gap-5" @submit.prevent="salva">
      <div v-for="d in scheda.domande" :key="d.id">
        <template v-if="d.tipo === 'FOTO'">
          <label class="form-label small" :for="`foto-${iscrizione.id}`">
            {{ d.testo }}<span v-if="d.obbligatoria"> *</span>
          </label>
          <div class="small fg-2 mb-1">
            Va bene una foto qualsiasi: l'app la prepara per BuonaCaccia (JPG, al massimo 1 MB).
            <template v-if="iscrizione.foto">
              Già caricata: <a :href="fileFotoBC(iscrizione.id)">guarda la foto</a>.
            </template>
          </div>
          <input
            :id="`foto-${iscrizione.id}`"
            type="file"
            accept="image/*"
            class="form-control form-control-sm"
            :disabled="inCorso"
            @change="foto"
          />
          <button
            type="button"
            class="btn btn-sm btn-link px-0"
            :disabled="inCorso"
            @click="fotoProfilo"
          >
            Usa la foto profilo
          </button>
        </template>
        <fieldset v-else-if="d.tipo === 'SCELTA_SINGOLA' || d.tipo === 'SCELTA_MULTIPLA'">
          <legend class="form-label small">
            {{ d.testo }}<span v-if="d.obbligatoria"> *</span>
          </legend>
          <div v-for="(o, n) in d.opzioni" :key="o" class="form-field">
            <input
              v-if="d.tipo === 'SCELTA_SINGOLA'"
              :id="`d-${iscrizione.id}-${d.id}-${n}`"
              type="radio"
              class="radio"
              :name="`d-${iscrizione.id}-${d.id}`"
              :checked="risposte[d.id] === o"
              @change="risposte[d.id] = o"
            />
            <input
              v-else
              :id="`d-${iscrizione.id}-${d.id}-${n}`"
              type="checkbox"
              class="check"
              :checked="(risposte[d.id] as string[]).includes(o)"
              @change="scelta(d.id, o, ($event.target as HTMLInputElement).checked)"
            />
            <label class="small" :for="`d-${iscrizione.id}-${d.id}-${n}`">{{ o }}</label>
          </div>
        </fieldset>
        <template v-else-if="d.tipo === 'SI_NO'">
          <label class="form-label small" :for="`d-${iscrizione.id}-${d.id}`">
            {{ d.testo }}<span v-if="d.obbligatoria"> *</span>
          </label>
          <select
            :id="`d-${iscrizione.id}-${d.id}`"
            class="form-control form-control-sm"
            :value="risposte[d.id] === true ? 'si' : risposte[d.id] === false ? 'no' : ''"
            @change="siNo(d.id, ($event.target as HTMLSelectElement).value)"
          >
            <option value="">—</option>
            <option value="si">Sì</option>
            <option value="no">No</option>
          </select>
        </template>
        <template v-else>
          <label class="form-label small" :for="`d-${iscrizione.id}-${d.id}`">
            {{ d.testo }}<span v-if="d.obbligatoria"> *</span>
          </label>
          <textarea
            v-if="d.tipo === 'LUNGA'"
            :id="`d-${iscrizione.id}-${d.id}`"
            :value="String(risposte[d.id] ?? '')"
            class="form-control form-control-sm"
            rows="4"
            maxlength="5000"
            @input="scrivi(d.id, $event)"
          />
          <input
            v-else
            :id="`d-${iscrizione.id}-${d.id}`"
            :value="String(risposte[d.id] ?? '')"
            class="form-control form-control-sm"
            maxlength="300"
            @input="scrivi(d.id, $event)"
          />
        </template>
      </div>
      <div class="d-flex flex-wrap align-items-center gap-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Salva le risposte
        </button>
        <span v-if="salvate" class="small" role="status">Salvate.</span>
        <span class="small fg-2">* obbligatoria; puoi salvare anche a metà e tornare dopo.</span>
      </div>
    </form>
  </div>
</template>
