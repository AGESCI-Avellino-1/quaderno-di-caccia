<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

import {
  api,
  percorsoAzioneCompetenza,
  quandoParziale,
  type AzioneCompetenza,
  type Competenza,
  type DataParziale,
} from '@/api/qdc'
import InputDataParziale from '@/components/InputDataParziale.vue'
import { useErrore } from '@/composables/useErrore'
import { scrivi } from '@/offline/outbox'

// A specialità, a brevetto or a specialità di squadriglia (DEC-62…DEC-64): the carta, the
// maestro (a name, never an account), the steps up to the conquest in the Consiglio della
// Legge and the badge. A brevetto shows the conditions of art. 38 (V09) and links the
// specialità judged suitable; a patrol's path links the members' specialità born from it.
// Steps go through the offline queue (DEC-95).
const props = defineProps<{
  voce: Competenza
  gestisce: boolean
  proponeVerifica: boolean
  /** Paths that may be linked: { id, testo }. */
  collegabili: { id: number; testo: string }[]
}>()
const emit = defineEmits<{ cambiata: [inCoda: boolean] }>()
const { errore, inCorso, esegui } = useErrore()
const oggi = () => new Date().toLocaleDateString('sv')

const aperta = ref<'' | 'modifica' | 'interrompi' | 'distintivo'>('')
const modulo = reactive({
  carta: props.voce.carta,
  maestro: props.voce.maestro,
  confronto: props.voce.confronto,
  collegati: [...props.voce.collegati],
  motivo: '',
})
const consegna = ref<DataParziale>({ data: oggi(), precisione: 'GIORNO' })

const collegabile = computed(() => props.voce.tipo !== 'SPECIALITA')
const nomiCollegati = computed(() =>
  props.voce.collegati
    .map((id) => props.collegabili.find((c) => c.id === id)?.testo)
    .filter(Boolean)
    .join('; '),
)
const COLORI: Record<string, string> = {
  PROPOSTO: 'theme-secondary',
  IN_CORSO: 'theme-primary',
  DA_VERIFICARE: 'theme-warning',
  RICONOSCIUTO: 'theme-success',
  INTERROTTO: 'theme-secondary',
}

async function passo(azione: AzioneCompetenza, corpo: Record<string, string> = {}) {
  const esito = await esegui(() =>
    scrivi({
      metodo: 'POST',
      percorso: percorsoAzioneCompetenza(props.voce.id, azione),
      corpo,
      // Stored in clear in the queue: no names.
      descrizione: `Specialità o brevetto: ${azione.replace('_', ' ')} (n. ${props.voce.id})`,
    }),
  )
  if (!esito) return
  aperta.value = ''
  emit('cambiata', esito.inCoda)
}

async function salva() {
  const dati = {
    carta: modulo.carta,
    maestro: modulo.maestro,
    confronto: modulo.confronto,
    collegati: modulo.collegati,
  }
  if (await esegui(() => api.modificaCompetenza(props.voce.id, dati))) {
    aperta.value = ''
    emit('cambiata', false)
  }
}

async function distintivo() {
  if (await esegui(() => api.distintivoCompetenza(props.voce.id, consegna.value))) {
    aperta.value = ''
    emit('cambiata', false)
  }
}
</script>

<template>
  <li class="list-group-item">
    <div class="d-flex flex-wrap align-items-start justify-content-between gap-3">
      <div class="flex-grow-1">
        <strong>{{ voce.nome }}</strong>
        <span class="small fg-2"> · {{ voce.tipo_nome }}</span>
        <div class="small fg-2">
          <template v-if="voce.maestro">Maestro: {{ voce.maestro }}. </template>
          <template v-if="voce.riconosciuto">
            Conquistata {{ quandoParziale(voce.riconosciuto)
            }}<template v-if="voce.storico"> (registrata dopo)</template>.
          </template>
          <template v-if="voce.distintivo">
            Distintivo consegnato {{ quandoParziale(voce.distintivo) }}.
          </template>
          <template v-if="voce.interrotto_il">
            Interrotto: {{ voce.motivo_interruzione }}.
          </template>
          <template v-if="nomiCollegati">
            {{ voce.tipo === 'BREVETTO' ? 'Specialità collegate' : 'Nate da questo percorso' }}:
            {{ nomiCollegati }}.
          </template>
        </div>
        <p v-if="voce.carta" class="small testo-a-capo mb-0 mt-1">
          <strong>Carta</strong>: {{ voce.carta }}
        </p>
        <p v-if="voce.confronto" class="small mb-0">
          <strong>Occasione di confronto</strong>: {{ voce.confronto }}
        </p>
      </div>
      <span class="badge" :class="COLORI[voce.stato]">{{ voce.stato_nome }}</span>
    </div>
    <div v-if="errore" class="alert theme-danger small mt-1" role="alert">{{ errore }}</div>

    <div class="d-flex flex-wrap gap-1 mt-1">
      <template v-if="gestisce">
        <button
          v-if="voce.stato === 'PROPOSTO'"
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          :disabled="inCorso"
          @click="passo('avvia')"
        >
          Avvia
        </button>
        <template v-if="voce.stato === 'DA_VERIFICARE'">
          <button
            type="button"
            class="btn btn-sm btn-solid theme-success"
            :disabled="inCorso"
            @click="passo('riconosci', { il: oggi() })"
          >
            {{
              voce.tipo === 'SPECIALITA_SQ' || voce.tipo === 'SPECIALITA_LC'
                ? 'Conquistata'
                : 'Conquistata (Consiglio della Legge)'
            }}
          </button>
          <button
            type="button"
            class="btn btn-sm btn-outline theme-secondary"
            :disabled="inCorso"
            @click="passo('prosegui')"
          >
            Non ancora: prosegue
          </button>
        </template>
        <button
          v-if="voce.stato === 'RICONOSCIUTO' && !voce.distintivo"
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          @click="aperta = 'distintivo'"
        >
          Distintivo consegnato
        </button>
      </template>
      <button
        v-if="voce.stato === 'IN_CORSO' && proponeVerifica"
        type="button"
        class="btn btn-sm btn-outline theme-warning"
        :disabled="inCorso"
        @click="passo('proponi_verifica')"
      >
        Pronto per la verifica
      </button>
      <template v-if="gestisce && ['PROPOSTO', 'IN_CORSO', 'DA_VERIFICARE'].includes(voce.stato)">
        <button
          type="button"
          class="btn btn-sm btn-link"
          @click="aperta = aperta === 'modifica' ? '' : 'modifica'"
        >
          {{ voce.tipo === 'SPECIALITA_SQ' ? 'Carta e specialità nate' : 'Carta e maestro' }}
        </button>
        <button
          type="button"
          class="btn btn-sm btn-link"
          @click="aperta = aperta === 'interrompi' ? '' : 'interrompi'"
        >
          Interrompi
        </button>
      </template>
    </div>

    <form
      v-if="aperta === 'modifica'"
      class="d-flex flex-column gap-3 mt-1"
      @submit.prevent="salva"
    >
      <div>
        <label class="form-label small" :for="`carta-${voce.id}`">Carta</label>
        <textarea
          :id="`carta-${voce.id}`"
          v-model="modulo.carta"
          class="form-control form-control-sm"
          rows="3"
        />
      </div>
      <div v-if="voce.tipo !== 'SPECIALITA_SQ'">
        <label class="form-label small" :for="`maestro-${voce.id}`"
          >Maestro o maestra (anche esterno)</label
        >
        <input
          :id="`maestro-${voce.id}`"
          v-model="modulo.maestro"
          class="form-control form-control-sm"
          maxlength="120"
        />
      </div>
      <template v-if="voce.tipo === 'BREVETTO'">
        <p class="small fg-2 mb-0">
          Per il brevetto (art. 38): specialità ritenute idonee, approfondimento nelle imprese e
          nella vita di squadriglia e reparto, un'occasione di confronto sulla competenza (anche
          fuori dall'Associazione), sperimentazione nel Consiglio d'impresa e come maestro di
          specialità.
        </p>
        <div>
          <label class="form-label small" :for="`confronto-${voce.id}`"
            >Occasione di confronto</label
          >
          <input
            :id="`confronto-${voce.id}`"
            v-model="modulo.confronto"
            class="form-control form-control-sm"
          />
        </div>
      </template>
      <fieldset v-if="collegabile && collegabili.length">
        <legend class="form-label small">
          {{
            voce.tipo === 'BREVETTO'
              ? 'Specialità collegate'
              : 'Specialità e brevetti nati da questo percorso'
          }}
        </legend>
        <div v-for="c in collegabili" :key="c.id" class="form-field">
          <input
            :id="`coll-${voce.id}-${c.id}`"
            v-model="modulo.collegati"
            type="checkbox"
            class="check"
            :value="c.id"
          />
          <label class="small" :for="`coll-${voce.id}-${c.id}`">{{ c.testo }}</label>
        </div>
      </fieldset>
      <div>
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Salva
        </button>
      </div>
    </form>

    <form
      v-if="aperta === 'interrompi'"
      class="d-flex flex-wrap align-items-end gap-3 mt-1"
      @submit.prevent="passo('interrompi', { motivo: modulo.motivo })"
    >
      <div class="flex-grow-1">
        <label class="form-label small" :for="`motivo-c-${voce.id}`">Perché si interrompe</label>
        <input
          :id="`motivo-c-${voce.id}`"
          v-model="modulo.motivo"
          class="form-control form-control-sm"
          required
        />
      </div>
      <button type="submit" class="btn btn-sm btn-solid theme-danger" :disabled="inCorso">
        Interrompi
      </button>
    </form>

    <form
      v-if="aperta === 'distintivo'"
      class="d-flex flex-wrap align-items-end gap-3 mt-1"
      @submit.prevent="distintivo"
    >
      <InputDataParziale
        :id="`dist-c-${voce.id}`"
        v-model="consegna"
        etichetta="Consegna del distintivo"
      />
      <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
        Registra
      </button>
    </form>
  </li>
</template>
