<script setup lang="ts">
import { computed } from 'vue'

import type { Localita, NuovaLocalita, PropostaIndirizzo } from '@/api/qdc'
import CampoIndirizzo from '@/components/CampoIndirizzo.vue'

// The place of a meeting (DEC-310): one of the group's places, or a new one written here,
// which enters the group's list when saved.
const props = defineProps<{ localita: Localita[]; idCampo: string }>()
const scelta = defineModel<{
  id: number | null
  nuova: NuovaLocalita | null
}>({ required: true })

const NUOVA = -1
const valore = computed({
  get: () => (scelta.value.nuova ? NUOVA : scelta.value.id),
  set: (v: number | null) => {
    scelta.value =
      v === NUOVA
        ? { id: null, nuova: { nome: '', denominazione: '', indirizzo: '', civico: '' } }
        : { id: v, nuova: null }
  },
})
const attuale = computed(() => props.localita.find((l) => l.id === scelta.value.id))

function proposta(p: PropostaIndirizzo) {
  const nuova = scelta.value.nuova
  if (nuova && !nuova.denominazione.trim()) nuova.denominazione = p.nome
}
</script>

<template>
  <div class="row g-3">
    <div class="md:col-6">
      <label class="form-label small" :for="idCampo">Località</label>
      <select :id="idCampo" v-model="valore" class="form-control form-control-sm">
        <option :value="null">Nessuna</option>
        <option v-for="l in localita" :key="l.id" :value="l.id">{{ l.nome }}</option>
        <option :value="NUOVA">Nuova località…</option>
      </select>
      <div v-if="attuale?.indirizzo_completo" class="form-text small">
        {{ attuale.indirizzo_completo }}
      </div>
    </div>
    <template v-if="scelta.nuova">
      <div class="md:col-6">
        <label class="form-label small" :for="`${idCampo}-nome`">Nome della località</label>
        <input
          :id="`${idCampo}-nome`"
          v-model="scelta.nuova.nome"
          class="form-control form-control-sm"
          placeholder="Per esempio: Sede di via Roma"
          required
        />
      </div>
      <div class="col-12">
        <label class="form-label small" :for="`${idCampo}-denominazione`"
          >Nome completo (facoltativo)</label
        >
        <input
          :id="`${idCampo}-denominazione`"
          v-model="scelta.nuova.denominazione"
          class="form-control form-control-sm"
          placeholder="Per esempio: Parrocchia di San Rocco"
        />
        <div class="form-text small">Se c'è, è quello che leggono gli invitati.</div>
      </div>
      <div class="md:col-9">
        <label class="form-label small" :for="`${idCampo}-indirizzo`"
          >Indirizzo (facoltativo)</label
        >
        <CampoIndirizzo
          v-model="scelta.nuova.indirizzo"
          v-model:civico="scelta.nuova.civico"
          :id-campo="`${idCampo}-indirizzo`"
          @scelta="proposta"
        />
        <div class="form-text small">Entra nell'elenco delle località del gruppo.</div>
      </div>
      <div class="md:col-3">
        <label class="form-label small" :for="`${idCampo}-civico`">Numero civico</label>
        <input
          :id="`${idCampo}-civico`"
          v-model="scelta.nuova.civico"
          class="form-control form-control-sm"
          maxlength="20"
        />
      </div>
    </template>
  </div>
</template>
