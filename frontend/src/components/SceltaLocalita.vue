<script setup lang="ts">
import { computed } from 'vue'

import type { Localita, PropostaIndirizzo } from '@/api/qdc'
import CampoIndirizzo from '@/components/CampoIndirizzo.vue'

// The place of a meeting (DEC-310): one of the group's places, or a new one written here,
// which enters the group's list when saved.
const props = defineProps<{ localita: Localita[]; idCampo: string }>()
const scelta = defineModel<{
  id: number | null
  nuova: { nome: string; indirizzo: string } | null
}>({ required: true })

const NUOVA = -1
const valore = computed({
  get: () => (scelta.value.nuova ? NUOVA : scelta.value.id),
  set: (v: number | null) => {
    scelta.value =
      v === NUOVA ? { id: null, nuova: { nome: '', indirizzo: '' } } : { id: v, nuova: null }
  },
})
const attuale = computed(() => props.localita.find((l) => l.id === scelta.value.id))

function proposta(p: PropostaIndirizzo) {
  if (scelta.value.nuova && !scelta.value.nuova.nome.trim()) scelta.value.nuova.nome = p.nome
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
      <div v-if="attuale?.indirizzo" class="form-text small">{{ attuale.indirizzo }}</div>
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
        <label class="form-label small" :for="`${idCampo}-indirizzo`"
          >Indirizzo (facoltativo)</label
        >
        <CampoIndirizzo
          v-model="scelta.nuova.indirizzo"
          :id-campo="`${idCampo}-indirizzo`"
          @scelta="proposta"
        />
        <div class="form-text small">Entra nell'elenco delle località del gruppo.</div>
      </div>
    </template>
  </div>
</template>
