<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

import {
  api,
  percorsoAzione,
  type AzionePercorso,
  type ImpegnoEG,
  type MetaEG,
  type Scelta,
} from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'
import { scrivi } from '@/offline/outbox'

// One meta or impegno of the sentiero (DEC-59…DEC-61). The steps go through the offline
// queue (DEC-95): a step already applied is answered as done by the server (DEC-96).
const props = defineProps<{
  tipo: 'mete' | 'impegni'
  voce: MetaEG | ImpegnoEG
  gestisce: boolean
  proponeVerifica: boolean
  propone: boolean
  sedi: Scelta[]
  nomiMete: Record<number, string>
  /** R/S: the mete are called obiettivi, verified outside the Consiglio della Legge. */
  rs?: boolean
  /** L/C: prede and voli, verified with the vecchi lupi or the coccinelle anziane. */
  lc?: boolean
}>()
const emit = defineEmits<{ cambiata: [inCoda: boolean] }>()
const { errore, inCorso, esegui } = useErrore()
const oggi = () => new Date().toLocaleDateString('sv')
const data = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString('it-IT') : '')

const aperta = ref<'' | 'convalida' | 'interrompi' | 'riformula' | 'storia'>('')
const modulo = reactive({
  il: oggi(),
  sede: props.lc ? 'ANZIANI' : props.tipo === 'mete' && !props.rs ? 'CONSIGLIO_LEGGE' : '',
  sede_descrizione: '',
  motivo: '',
  testo: props.voce.testo,
  termine: props.voce.termine ?? '',
  criterio: 'criterio_verifica' in props.voce ? props.voce.criterio_verifica : '',
})

const impegno = computed(() => (props.tipo === 'impegni' ? (props.voce as ImpegnoEG) : null))
const meta = computed(() => (props.tipo === 'mete' ? (props.voce as MetaEG) : null))
const puoRiformulare = computed(
  () =>
    ['BOZZA', 'CONCORDATO', 'IN_CORSO', 'DA_VERIFICARE'].includes(props.voce.stato) &&
    (props.gestisce || (props.propone && props.voce.stato === 'BOZZA')),
)

const COLORI: Record<string, string> = {
  BOZZA: 'theme-secondary',
  CONCORDATO: 'theme-info',
  IN_CORSO: 'theme-primary',
  DA_VERIFICARE: 'theme-warning',
  CONCLUSO: 'theme-success',
  INTERROTTO: 'theme-secondary',
}

async function passo(azione: AzionePercorso, corpo: Record<string, string> = {}) {
  const esito = await esegui(() =>
    scrivi({
      metodo: 'POST',
      percorso: percorsoAzione(props.tipo, props.voce.id, azione),
      corpo,
      // Stored in clear in the queue: no names, no text.
      descrizione: `Progressione: ${azione.replace('_', ' ')} (n. ${props.voce.id})`,
    }),
  )
  if (!esito) return
  aperta.value = ''
  emit('cambiata', esito.inCoda)
}

const convalida = () =>
  passo('convalida', {
    il: modulo.il,
    sede: modulo.sede,
    sede_descrizione: modulo.sede_descrizione,
  })
const interrompi = () => passo('interrompi', { il: modulo.il, motivo: modulo.motivo })

async function riformula() {
  const dati = {
    testo: modulo.testo,
    termine: modulo.termine || null,
    ...(impegno.value ? { criterio_verifica: modulo.criterio } : {}),
  }
  if (await esegui(() => api.riformula(props.tipo, props.voce.id, dati))) {
    aperta.value = ''
    emit('cambiata', false)
  }
}
</script>

<template>
  <li class="list-group-item">
    <div class="d-flex flex-wrap align-items-start justify-content-between gap-3">
      <div class="flex-grow-1">
        <span class="testo-a-capo">{{ voce.testo }}</span>
        <span
          v-if="meta?.riservata"
          class="badge theme-inverse ms-1"
          title="Non la vede il capo squadriglia"
        >
          riservata
        </span>
        <div class="small fg-2">
          <template v-if="impegno?.stagione">{{ impegno.stagione }}. </template>
          <template v-if="voce.termine">Entro il {{ data(voce.termine) }}. </template>
          <template v-if="impegno?.criterio_verifica">
            Come si verifica: {{ impegno.criterio_verifica }}.
          </template>
          <template v-if="impegno?.mete.length">
            {{ rs ? "Per l'obiettivo:" : 'Per la meta:' }}
            {{
              impegno.mete
                .map((m) => nomiMete[m] ?? '')
                .filter(Boolean)
                .join('; ')
            }}.
          </template>
          <template v-if="voce.proposto_dal_ragazzo && voce.stato === 'BOZZA'">
            Proposto dal ragazzo, da concordare con lo staff.
          </template>
          <template v-if="voce.verificato_il">
            Verificato il {{ data(voce.verificato_il) }} ({{ voce.sede_nome }}).
          </template>
          <template v-if="voce.interrotto_il">
            Interrotto il {{ data(voce.interrotto_il) }}: {{ voce.motivo_interruzione }}.
          </template>
        </div>
      </div>
      <span class="badge" :class="COLORI[voce.stato]">{{ voce.stato_nome }}</span>
    </div>
    <div v-if="errore" class="alert theme-danger small mt-1" role="alert">{{ errore }}</div>

    <div class="d-flex flex-wrap gap-1 mt-1">
      <template v-if="gestisce">
        <button
          v-if="voce.stato === 'BOZZA'"
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          :disabled="inCorso"
          @click="passo('concorda')"
        >
          Concorda
        </button>
        <button
          v-if="voce.stato === 'CONCORDATO'"
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
            @click="aperta = 'convalida'"
          >
            Convalida…
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
      <button
        v-if="puoRiformulare"
        type="button"
        class="btn btn-sm btn-link"
        @click="aperta = aperta === 'riformula' ? '' : 'riformula'"
      >
        Riformula
      </button>
      <button
        v-if="gestisce && ['BOZZA', 'CONCORDATO', 'IN_CORSO', 'DA_VERIFICARE'].includes(voce.stato)"
        type="button"
        class="btn btn-sm btn-link"
        @click="aperta = aperta === 'interrompi' ? '' : 'interrompi'"
      >
        Interrompi
      </button>
      <button
        v-if="voce.revisioni.length"
        type="button"
        class="btn btn-sm btn-link"
        @click="aperta = aperta === 'storia' ? '' : 'storia'"
      >
        Versioni precedenti ({{ voce.revisioni.length }})
      </button>
    </div>

    <form
      v-if="aperta === 'convalida'"
      class="d-flex flex-wrap align-items-end gap-3 mt-1"
      @submit.prevent="convalida"
    >
      <div>
        <label class="form-label small" :for="`il-${tipo}-${voce.id}`">Verificato il</label>
        <input
          :id="`il-${tipo}-${voce.id}`"
          v-model="modulo.il"
          type="date"
          :max="oggi()"
          class="form-control form-control-sm"
          required
        />
      </div>
      <div>
        <label class="form-label small" :for="`sede-${tipo}-${voce.id}`">Dove</label>
        <select
          :id="`sede-${tipo}-${voce.id}`"
          v-model="modulo.sede"
          class="form-control form-control-sm"
          required
        >
          <option value="" disabled>—</option>
          <option v-for="s in sedi" :key="s.valore" :value="s.valore">{{ s.etichetta }}</option>
        </select>
      </div>
      <div v-if="modulo.sede === 'ALTRO'" class="flex-grow-1">
        <label class="form-label small" :for="`sede-d-${tipo}-${voce.id}`">Quale</label>
        <input
          :id="`sede-d-${tipo}-${voce.id}`"
          v-model="modulo.sede_descrizione"
          class="form-control form-control-sm"
          required
        />
      </div>
      <button type="submit" class="btn btn-sm btn-solid theme-success" :disabled="inCorso">
        Convalida
      </button>
    </form>

    <form
      v-if="aperta === 'interrompi'"
      class="d-flex flex-wrap align-items-end gap-3 mt-1"
      @submit.prevent="interrompi"
    >
      <div class="flex-grow-1">
        <label class="form-label small" :for="`motivo-${tipo}-${voce.id}`"
          >Perché si interrompe</label
        >
        <input
          :id="`motivo-${tipo}-${voce.id}`"
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
      v-if="aperta === 'riformula'"
      class="d-flex flex-column gap-3 mt-1"
      @submit.prevent="riformula"
    >
      <div>
        <label class="form-label small" :for="`testo-${tipo}-${voce.id}`">Testo</label>
        <textarea
          :id="`testo-${tipo}-${voce.id}`"
          v-model="modulo.testo"
          class="form-control form-control-sm"
          rows="2"
          required
        />
      </div>
      <div v-if="impegno">
        <label class="form-label small" :for="`crit-${tipo}-${voce.id}`">Come si verifica</label>
        <input
          :id="`crit-${tipo}-${voce.id}`"
          v-model="modulo.criterio"
          class="form-control form-control-sm"
        />
      </div>
      <div>
        <label class="form-label small" :for="`term-${tipo}-${voce.id}`">Entro il</label>
        <input
          :id="`term-${tipo}-${voce.id}`"
          v-model="modulo.termine"
          type="date"
          class="form-control form-control-sm w-auto"
        />
      </div>
      <div>
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Salva (la versione di prima resta)
        </button>
      </div>
    </form>

    <ul v-if="aperta === 'storia'" class="small fg-2 mt-1">
      <li v-for="(r, n) in voce.revisioni" :key="n">
        Fino al {{ data(r.sostituita_il) }}: «{{ r.testo }}»
      </li>
    </ul>
  </li>
</template>
