<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

import { api, type Completamento, type RichiestaIscrizione } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The data still missing after the approval, written straight on the member (BuonaStrada
// has no record of them yet). Online only.
const props = defineProps<{ id: number }>()
const emit = defineEmits<{ cambiata: [richiesta: RichiestaIscrizione] }>()
const { errore, inCorso, esegui } = useErrore()
const dati = reactive<Completamento>({
  sesso: '',
  luogo_nascita: '',
  indirizzo: '',
  civico: '',
  comune: '',
  provincia: '',
  cap: '',
  cellulare_genitore: null,
})
const caricato = ref(false)
const salvato = ref(false)

watch(
  () => props.id,
  async (id) => {
    const letto = await esegui(() => api.completamento(id))
    if (!letto) return
    for (const campo of Object.keys(dati) as (keyof Completamento)[]) {
      ;(dati as Record<string, unknown>)[campo] = letto[campo]
    }
    caricato.value = true
  },
  { immediate: true },
)

async function salva() {
  salvato.value = false
  const esito = await esegui(() => api.completa(props.id, { ...dati }))
  if (!esito) return
  salvato.value = true
  emit('cambiata', esito.richiesta)
}
</script>

<template>
  <form v-if="caricato" class="row g-3 mt-1" @submit.prevent="salva">
    <div v-if="errore" class="col-12 alert theme-danger py-3 small" role="alert">{{ errore }}</div>
    <div class="col-6 sm:col-3">
      <label class="form-label small" :for="`sesso-${id}`">Sesso</label>
      <select :id="`sesso-${id}`" v-model="dati.sesso" class="form-control form-control-sm">
        <option value="">—</option>
        <option value="F">F</option>
        <option value="M">M</option>
      </select>
    </div>
    <div class="col-6 sm:col-9">
      <label class="form-label small" :for="`luogo-${id}`">Luogo di nascita</label>
      <input
        :id="`luogo-${id}`"
        v-model="dati.luogo_nascita"
        class="form-control form-control-sm"
      />
    </div>
    <div class="col-9">
      <label class="form-label small" :for="`indirizzo-${id}`">Indirizzo</label>
      <input
        :id="`indirizzo-${id}`"
        v-model="dati.indirizzo"
        class="form-control form-control-sm"
      />
    </div>
    <div class="col-3">
      <label class="form-label small" :for="`civico-${id}`">Civico</label>
      <input :id="`civico-${id}`" v-model="dati.civico" class="form-control form-control-sm" />
    </div>
    <div class="col-12 sm:col-6">
      <label class="form-label small" :for="`comune-${id}`">Comune</label>
      <input :id="`comune-${id}`" v-model="dati.comune" class="form-control form-control-sm" />
    </div>
    <div class="col-6 sm:col-3">
      <label class="form-label small" :for="`provincia-${id}`">Provincia</label>
      <input
        :id="`provincia-${id}`"
        v-model="dati.provincia"
        class="form-control form-control-sm"
        maxlength="2"
        placeholder="AV"
      />
    </div>
    <div class="col-6 sm:col-3">
      <label class="form-label small" :for="`cap-${id}`">CAP</label>
      <input
        :id="`cap-${id}`"
        v-model="dati.cap"
        class="form-control form-control-sm"
        maxlength="5"
        inputmode="numeric"
      />
    </div>
    <div v-if="dati.cellulare_genitore !== null" class="col-12 sm:col-6">
      <label class="form-label small" :for="`cellulare-${id}`">Il tuo cellulare (genitore)</label>
      <input
        :id="`cellulare-${id}`"
        v-model="dati.cellulare_genitore"
        type="tel"
        class="form-control form-control-sm"
      />
    </div>
    <div class="col-12 d-flex align-items-center gap-3">
      <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
        Salva
      </button>
      <span v-if="salvato" class="small fg-success" role="status">Salvato</span>
    </div>
  </form>
</template>
