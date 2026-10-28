<script setup lang="ts">
import { reactive } from 'vue'

import { AMBIENTI, COMPOSIZIONI, TIPI_UNITA, type Unita, type UnitaIn } from '@/api/qdc'

// Create or edit a unit (DEC-10). BuonaStrada codes are not here: the import owns them.
const props = defineProps<{
  iniziale?: UnitaIn
  /** Units it can be linked to: parallel male/female units (DEC-36). */
  altre: Unita[]
  inCorso?: boolean
  etichetta: string
}>()
const emit = defineEmits<{ salva: [dati: UnitaIn]; annulla: [] }>()

const dati = reactive<UnitaIn>(
  props.iniziale
    ? { ...props.iniziale }
    : {
        nome: '',
        tipo: 'REPARTO',
        composizione: 'X',
        ambiente: 'NESSUNO',
        collegata_a: null,
        nota_collegamento: '',
        attiva: true,
      },
)
</script>

<template>
  <form class="row g-2" @submit.prevent="emit('salva', { ...dati })">
    <div class="col-12 col-md-6">
      <label class="form-label small" for="unita-nome">Nome</label>
      <input id="unita-nome" v-model="dati.nome" class="form-control form-control-sm" required />
    </div>
    <div class="col-6 col-md-3">
      <label class="form-label small" for="unita-tipo">Tipo</label>
      <select id="unita-tipo" v-model="dati.tipo" class="form-select form-select-sm">
        <option v-for="t in TIPI_UNITA" :key="t.valore" :value="t.valore">{{ t.etichetta }}</option>
      </select>
    </div>
    <div class="col-6 col-md-3">
      <label class="form-label small" for="unita-composizione">Composizione</label>
      <select
        id="unita-composizione"
        v-model="dati.composizione"
        class="form-select form-select-sm"
      >
        <option v-for="c in COMPOSIZIONI" :key="c.valore" :value="c.valore">
          {{ c.etichetta }}
        </option>
      </select>
    </div>
    <div class="col-6 col-md-3">
      <label class="form-label small" for="unita-ambiente">Ambiente</label>
      <select id="unita-ambiente" v-model="dati.ambiente" class="form-select form-select-sm">
        <option v-for="a in AMBIENTI" :key="a.valore" :value="a.valore">{{ a.etichetta }}</option>
      </select>
    </div>
    <div class="col-6 col-md-3">
      <label class="form-label small" for="unita-collegata">Collegata a</label>
      <select id="unita-collegata" v-model="dati.collegata_a" class="form-select form-select-sm">
        <option :value="null">Nessuna</option>
        <option v-for="u in altre" :key="u.id" :value="u.id">{{ u.nome }}</option>
      </select>
    </div>
    <div v-if="dati.collegata_a" class="col-12 col-md-6">
      <label class="form-label small" for="unita-nota">Nota sul collegamento</label>
      <input
        id="unita-nota"
        v-model="dati.nota_collegamento"
        class="form-control form-control-sm"
        placeholder="Es. reparto parallelo, attività comuni"
      />
    </div>
    <div v-if="iniziale" class="col-12">
      <div class="form-check">
        <input id="unita-attiva" v-model="dati.attiva" type="checkbox" class="form-check-input" />
        <label class="form-check-label small" for="unita-attiva">Unità attiva</label>
      </div>
    </div>
    <div class="col-12 d-flex gap-2">
      <button type="submit" class="btn btn-sm btn-primary" :disabled="inCorso">
        {{ etichetta }}
      </button>
      <button type="button" class="btn btn-sm btn-link" @click="emit('annulla')">Annulla</button>
    </div>
  </form>
</template>
