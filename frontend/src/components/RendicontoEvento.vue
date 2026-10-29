<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

import { api, euro, type RendicontoEvento } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Budget (DEC-91) and accounts (DEC-90) of an event, for its capi and the Co.Ca.: the
// API answers 403 to anyone else and the section stays hidden. Online only.
const props = defineProps<{ evento: number; campo: boolean }>()
const { errore, inCorso, esegui } = useErrore()
const conti = ref<RendicontoEvento | null>(null)
const modulo = reactive({
  aperto: false,
  calcola: 'totale' as 'quota' | 'contributo' | 'totale',
  quota: '',
  contributo: '',
  totale: '',
  quota_staff: '0',
})

watch(
  () => props.evento,
  async (id) => {
    try {
      conti.value = await api.rendicontoEvento(id)
    } catch {
      conti.value = null
    }
  },
  { immediate: true },
)

function apri() {
  const b = conti.value?.budget
  Object.assign(modulo, {
    aperto: true,
    calcola: b?.calcolato ?? 'totale',
    quota: b?.quota ?? '',
    contributo: b?.contributo ?? '',
    totale: b?.totale ?? '',
    quota_staff: b?.quota_staff ?? '0',
  })
}

async function salva() {
  const valore = (campo: 'quota' | 'contributo' | 'totale') =>
    modulo.calcola === campo ? null : Number(modulo[campo] || 0).toFixed(2)
  const dati = await esegui(() =>
    api.fissaBudget(props.evento, {
      quota: valore('quota'),
      contributo: valore('contributo'),
      totale: valore('totale'),
      quota_staff: Number(modulo.quota_staff || 0).toFixed(2),
    }),
  )
  if (!dati) return
  conti.value = dati
  modulo.aperto = false
}

const ETICHETTE = {
  quota: 'Quota pro capite dei ragazzi',
  contributo: 'Contributo dalla cassa',
  totale: 'Budget complessivo',
} as const
</script>

<template>
  <section v-if="conti" class="card card-body mb-5">
    <h2 class="h5">{{ campo ? 'Budget e rendiconto' : 'Rendiconto' }}</h2>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>

    <template v-if="campo">
      <div v-if="conti.budget" class="mb-3">
        <div v-for="(etichetta, chiave) in ETICHETTE" :key="chiave">
          {{ etichetta }}:
          <strong>{{ conti.budget[chiave] === null ? '—' : euro(conti.budget[chiave]!) }}</strong>
          <span v-if="conti.budget.calcolato === chiave" class="small fg-2"> (calcolato)</span>
        </div>
        <div>
          Contributo pro capite dello staff: <strong>{{ euro(conti.budget.quota_staff) }}</strong>
        </div>
        <div class="small fg-2">
          Su {{ conti.budget.partecipanti }} ragazzi e {{ conti.budget.staff }} capi dello staff
        </div>
      </div>
      <p v-else class="fg-2 small">Budget non ancora fissato.</p>
      <button
        v-if="conti.puo_gestire && !modulo.aperto"
        type="button"
        class="btn btn-sm btn-outline theme-primary align-self-start mb-3"
        @click="apri"
      >
        {{ conti.budget ? 'Cambia il budget' : 'Fissa il budget' }}
      </button>
      <form v-if="modulo.aperto" class="border rounded p-5 mb-3" @submit.prevent="salva">
        <p class="form-text">
          Fissa due valori, il terzo lo calcola l'app sul numero dei partecipanti: budget = quota
          dei ragazzi × ragazzi + contributo dello staff × capi dello staff + contributo dalla
          cassa. Lo staff è quello delle unità coinvolte.
        </p>
        <div class="mb-3">
          <label class="form-label small" for="budget-calcola">L'app calcola</label>
          <select
            id="budget-calcola"
            v-model="modulo.calcola"
            class="form-control form-control-sm w-auto"
          >
            <option v-for="(etichetta, chiave) in ETICHETTE" :key="chiave" :value="chiave">
              {{ etichetta }}
            </option>
          </select>
        </div>
        <div class="row g-3">
          <template v-for="(etichetta, chiave) in ETICHETTE" :key="chiave">
            <div v-if="modulo.calcola !== chiave" class="md:col-6">
              <label class="form-label small" :for="`budget-${chiave}`">{{ etichetta }} (€)</label>
              <input
                :id="`budget-${chiave}`"
                v-model="modulo[chiave]"
                type="number"
                min="0"
                step="0.01"
                class="form-control form-control-sm"
                required
              />
            </div>
          </template>
          <div class="md:col-6">
            <label class="form-label small" for="budget-quota-staff">
              Contributo pro capite dello staff (€, anche 0)
            </label>
            <input
              id="budget-quota-staff"
              v-model="modulo.quota_staff"
              type="number"
              min="0"
              step="0.01"
              class="form-control form-control-sm"
            />
          </div>
        </div>
        <div class="d-flex gap-3 mt-3">
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Salva
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="modulo.aperto = false">
            Annulla
          </button>
        </div>
      </form>
    </template>

    <table class="table table-sm mb-0">
      <tbody>
        <tr>
          <td>Entrate in prima nota</td>
          <td class="text-end">{{ euro(conti.entrate) }}</td>
        </tr>
        <tr>
          <td>Uscite in prima nota</td>
          <td class="text-end">{{ euro(conti.uscite) }}</td>
        </tr>
        <tr>
          <th>Saldo</th>
          <th class="text-end">{{ euro(conti.saldo) }}</th>
        </tr>
        <tr v-if="Number(conti.quote_dovute) || Number(conti.agevolazioni)">
          <td>Quote: incassate su dovute</td>
          <td class="text-end">
            {{ euro(conti.quote_incassate) }} / {{ euro(conti.quote_dovute) }}
          </td>
        </tr>
        <tr v-if="Number(conti.agevolazioni)">
          <td>Agevolazioni (contributo dalla cassa)</td>
          <td class="text-end">{{ euro(conti.agevolazioni) }}</td>
        </tr>
      </tbody>
    </table>
    <p class="form-text mb-0 mt-3">
      Le entrate e le uscite sono i movimenti di prima nota collegati all'evento; gli incassi delle
      quote si collegano da soli.
    </p>
  </section>
</template>
