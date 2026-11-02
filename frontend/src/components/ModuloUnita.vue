<script setup lang="ts">
import { computed, reactive, watch } from 'vue'

import { AMBIENTI, COMPOSIZIONI, nomeUnita, TIPI_UNITA, type Unita, type UnitaIn } from '@/api/qdc'

// Create or edit a unit (DEC-10). BuonaStrada codes are not here: the import owns them.
const props = defineProps<{
  iniziale?: UnitaIn
  /** The group's units, among which the one to link: parallel units (DEC-36). */
  altre: Unita[]
  /** The unit being edited; absent for a new one. */
  unitaId?: number
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

// Links are two-way and in pairs (DEC-279): only active units with no link yet are
// offered; a unit already linked offers only its current link, to remove it first.
const collegabili = computed(() =>
  props.altre.filter((u) =>
    props.iniziale?.collegata_a
      ? u.id === props.iniziale.collegata_a
      : u.id !== props.unitaId && u.attiva && !u.archiviata_il && u.collegata_a === null,
  ),
)

// The setting is chosen only for a Branco/Cerchio (DEC-225): a Branco is giungla, a
// Cerchio bosco, the other units have none. The server applies the same rule.
const conAmbientazione = computed(() => dati.tipo === 'BRANCO_CERCHIO')
watch(
  () => dati.tipo,
  (tipo) => {
    if (tipo === 'BRANCO') dati.ambiente = 'GIUNGLA'
    else if (tipo === 'CERCHIO') dati.ambiente = 'BOSCO'
    else if (tipo !== 'BRANCO_CERCHIO') dati.ambiente = 'NESSUNO'
  },
)
</script>

<template>
  <form class="row g-3" @submit.prevent="emit('salva', { ...dati })">
    <div class="col-12 md:col-6">
      <label class="form-label small" for="unita-nome">
        Nome<template v-if="dati.tipo === 'COMUNITA_CAPI'"> (facoltativo per la Co.Ca.)</template>
      </label>
      <input
        id="unita-nome"
        v-model="dati.nome"
        class="form-control form-control-sm"
        :required="dati.tipo !== 'COMUNITA_CAPI'"
        placeholder="Es. Millennium"
      />
    </div>
    <div class="col-6 md:col-3">
      <label class="form-label small" for="unita-tipo">Tipo</label>
      <select id="unita-tipo" v-model="dati.tipo" class="form-control form-control-sm">
        <option v-for="t in TIPI_UNITA" :key="t.valore" :value="t.valore">{{ t.etichetta }}</option>
      </select>
    </div>
    <div class="col-6 md:col-3">
      <label class="form-label small" for="unita-composizione">Composizione</label>
      <select
        id="unita-composizione"
        v-model="dati.composizione"
        class="form-control form-control-sm"
      >
        <option v-for="c in COMPOSIZIONI" :key="c.valore" :value="c.valore">
          {{ c.etichetta }}
        </option>
      </select>
    </div>
    <div v-if="conAmbientazione" class="col-6 md:col-3">
      <label class="form-label small" for="unita-ambiente">Ambientazione</label>
      <select id="unita-ambiente" v-model="dati.ambiente" class="form-control form-control-sm">
        <option v-for="a in AMBIENTI" :key="a.valore" :value="a.valore">{{ a.etichetta }}</option>
      </select>
    </div>
    <div class="col-6 md:col-3">
      <label class="form-label small" for="unita-collegata">Collegata a</label>
      <select id="unita-collegata" v-model="dati.collegata_a" class="form-control form-control-sm">
        <option :value="null">Nessuna</option>
        <option v-for="u in collegabili" :key="u.id" :value="u.id">{{ nomeUnita(u) }}</option>
      </select>
      <div v-if="iniziale?.collegata_a" class="form-text small fg-2">
        Per collegarla a un'altra unità, prima togli questo collegamento.
      </div>
    </div>
    <div v-if="dati.collegata_a" class="col-12 md:col-6">
      <label class="form-label small" for="unita-nota">Nota sul collegamento</label>
      <input
        id="unita-nota"
        v-model="dati.nota_collegamento"
        class="form-control form-control-sm"
        placeholder="Es. reparto parallelo, attività comuni"
      />
    </div>
    <div v-if="iniziale" class="col-12">
      <div class="form-field">
        <input id="unita-attiva" v-model="dati.attiva" type="checkbox" class="check" />
        <label class="small" for="unita-attiva">Unità attiva</label>
      </div>
    </div>
    <div class="col-12 d-flex gap-3">
      <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
        {{ etichetta }}
      </button>
      <button type="button" class="btn btn-sm btn-link" @click="emit('annulla')">Annulla</button>
    </div>
  </form>
</template>
