<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { api, valoreLeggibile, type SchedaCorrezioni } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Corrections to BuonaStrada data (DEC-31): valid at once in the app, then forwarded by
// the capigruppo to the regional office. The backend lists only the fields this user
// may correct (404 when none). Online only: contacts are not cached for this.
const props = defineProps<{ id: number }>()
const emit = defineEmits<{ cambiato: [] }>()
const { errore, inCorso, esegui } = useErrore()
const scheda = ref<SchedaCorrezioni | null>(null)
const aperto = ref(false)
const scelto = ref('')
const valore = ref('')

async function carica(id: number) {
  try {
    scheda.value = await api.correzioniPersona(id)
  } catch {
    scheda.value = null
  }
}
watch(() => props.id, carica, { immediate: true })

const campo = computed(() => scheda.value?.campi.find((c) => c.campo === scelto.value))
const aperte = computed(() => scheda.value?.campi.filter((c) => c.correzione) ?? [])
// Not accepted: discarded by a capogruppo, or BuonaStrada's value chosen at import.
const scartate = computed(
  () =>
    scheda.value?.chiuse
      .filter((c) => c.stato === 'SCARTATA' || c.stato === 'SUPERATA')
      .slice(0, 5) ?? [],
)

watch(campo, (c) => (valore.value = c?.valore ?? ''))

function apri(nome = '') {
  scelto.value = nome || scheda.value?.campi[0]?.campo || ''
  valore.value = campo.value?.valore ?? ''
  aperto.value = true
}

async function salva() {
  const nuova = await esegui(() =>
    api.correggi(props.id, { campo: scelto.value, valore: valore.value }),
  )
  if (!nuova) return
  scheda.value = nuova
  aperto.value = false
  emit('cambiato')
}

const tipoInput = (nome: string) =>
  nome === 'email' ? 'email' : nome === 'cellulare' ? 'tel' : 'text'
const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
</script>

<template>
  <section v-if="scheda" class="card card-body mb-5">
    <div class="d-flex align-items-center">
      <h2 class="h5 mb-0">Dati di BuonaStrada</h2>
      <button
        v-if="!aperto"
        type="button"
        class="btn btn-sm btn-outline theme-primary ms-auto"
        @click="apri()"
      >
        Correggi un dato
      </button>
    </div>
    <p class="form-text mb-3">
      La correzione vale subito qui. I capigruppo la mandano alla segreteria, che aggiorna
      BuonaStrada.
    </p>
    <div v-if="errore" class="alert theme-danger py-3 small" role="alert">{{ errore }}</div>

    <form v-if="aperto" class="row g-3 mb-3" @submit.prevent="salva">
      <div class="col-12 sm:col-5">
        <label class="form-label small" for="correzione-campo">Dato</label>
        <select id="correzione-campo" v-model="scelto" class="form-control form-control-sm">
          <option v-for="c in scheda.campi" :key="c.campo" :value="c.campo">
            {{ c.etichetta }}
          </option>
        </select>
      </div>
      <div v-if="campo" class="col-12 sm:col-7">
        <label class="form-label small" for="correzione-valore">Valore giusto</label>
        <select
          v-if="campo.tipo === 'si_no'"
          id="correzione-valore"
          v-model="valore"
          class="form-control form-control-sm"
        >
          <option value="True">Sì</option>
          <option value="False">No</option>
          <option value="">Non indicato</option>
        </select>
        <select
          v-else-if="campo.tipo === 'scelta'"
          id="correzione-valore"
          v-model="valore"
          class="form-control form-control-sm"
        >
          <option value="">Non indicato</option>
          <option v-for="s in campo.scelte" :key="s.valore" :value="s.valore">
            {{ s.etichetta }}
          </option>
        </select>
        <input
          v-else
          id="correzione-valore"
          v-model="valore"
          class="form-control form-control-sm"
          :type="
            campo.tipo === 'data'
              ? 'date'
              : campo.tipo === 'numero'
                ? 'number'
                : tipoInput(campo.campo)
          "
        />
        <p class="form-text mb-0">
          Ora: {{ valoreLeggibile(campo.valore, campo.scelte) }}
          <template v-if="campo.correzione">
            (in BuonaStrada:
            {{ valoreLeggibile(campo.correzione.valore_precedente, campo.scelte) }})
          </template>
        </p>
      </div>
      <div class="col-12 d-flex gap-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Salva
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="aperto = false">Annulla</button>
      </div>
    </form>

    <p v-if="!aperte.length && !scartate.length" class="fg-2 small mb-0">
      Nessuna correzione in sospeso.
    </p>
    <div v-for="c in aperte" :key="c.campo" class="border-top pt-3 mt-1 small">
      <div class="d-flex flex-wrap align-items-baseline gap-3">
        <strong>{{ c.etichetta }}</strong>
        <span>{{ valoreLeggibile(c.valore, c.scelte) }}</span>
        <span class="badge theme-warning">In attesa di BuonaStrada</span>
        <button
          v-if="!aperto"
          type="button"
          class="btn btn-link btn-sm p-0 ms-auto"
          @click="apri(c.campo)"
        >
          modifica
        </button>
      </div>
      <div v-if="c.correzione" class="fg-2">
        Prima: {{ valoreLeggibile(c.correzione.valore_precedente, c.scelte) }} ·
        {{ c.correzione.stato_nome }}
        <template v-if="c.correzione.richiesta_da">
          · corretto da {{ c.correzione.richiesta_da }}</template
        >
        il {{ data(c.correzione.creata_il) }}
      </div>
    </div>
    <div v-for="c in scartate" :key="c.id" class="border-top pt-3 mt-1 small">
      <div class="d-flex flex-wrap align-items-baseline gap-3">
        <strong>{{ c.etichetta }}</strong>
        <span class="badge theme-secondary">{{
          c.stato === 'SUPERATA' ? 'Correzione superata da BuonaStrada' : 'Correzione scartata'
        }}</span>
      </div>
      <div class="fg-2">
        {{ valoreLeggibile(c.valore_corretto) }} non è stato accettato<template v-if="c.chiusa_il">
          il {{ data(c.chiusa_il) }}</template
        ><template v-if="c.motivo_scarto">: {{ c.motivo_scarto }}</template
        ><template v-else>: all'importazione è stato tenuto il dato di BuonaStrada.</template>
      </div>
    </div>
  </section>
</template>
