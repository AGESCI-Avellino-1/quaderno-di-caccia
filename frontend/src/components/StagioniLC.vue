<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

import { api, type Stagione, type StagioniUnita } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The stagioni di caccia o di volo of a branco or cerchio (DEC-66, DEC-183; L/C art. 38):
// planned, launched after the Promesse, closed before the holidays. Closing never
// conquers anything: what is still open is listed to look at again (V04). Online only:
// it is planned at the staff meeting, not at camp.
const props = defineProps<{ unita: number }>()
const { errore, inCorso, esegui } = useErrore()
const dati = ref<StagioniUnita | null>(null)
const oggi = () => new Date().toLocaleDateString('sv')
const data = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString('it-IT') : '')

watch(
  () => props.unita,
  async (id) => {
    dati.value = (await esegui(() => api.stagioni(id))) ?? null
  },
  { immediate: true },
)

// 0: closed; -1: new; otherwise the id being edited.
const aperta = ref(0)
const modulo = reactive({ nome: '', inizio_previsto: oggi(), fine_prevista: '' })
const passo = reactive({ id: 0, azione: '' as '' | 'lancia' | 'chiudi', il: oggi() })

function apri(s: Stagione | null) {
  aperta.value = s ? s.id : -1
  Object.assign(modulo, {
    nome: s?.nome ?? '',
    inizio_previsto: s?.inizio_previsto ?? oggi(),
    fine_prevista: s?.fine_prevista ?? '',
  })
}

async function salva() {
  const nuovi = await esegui(() =>
    aperta.value === -1
      ? api.nuovaStagione(props.unita, { ...modulo })
      : api.modificaStagione(aperta.value, { ...modulo }),
  )
  if (!nuovi) return
  dati.value = nuovi
  aperta.value = 0
}

async function fai(id: number, azione: 'lancia' | 'chiudi' | 'annulla', il: string | null) {
  const nuovi = await esegui(() => api.passoStagione(id, azione, il))
  if (!nuovi) return
  dati.value = nuovi
  passo.id = 0
}

const COLORI: Record<string, string> = {
  PREVISTA: 'theme-info',
  APERTA: 'theme-success',
  CHIUSA: 'theme-secondary',
  ANNULLATA: 'theme-secondary',
}
</script>

<template>
  <section v-if="dati" class="mb-5">
    <div class="d-flex flex-wrap align-items-center gap-3 mb-3">
      <h2 class="h5 mb-0">Stagioni di caccia o di volo</h2>
      <button
        v-if="dati.puo_gestire && !aperta"
        type="button"
        class="btn btn-sm btn-outline theme-primary"
        @click="apri(null)"
      >
        Nuova stagione
      </button>
    </div>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>

    <form v-if="aperta" class="card card-body mb-3" @submit.prevent="salva">
      <label class="form-label small" for="st-nome">Nome</label>
      <input
        id="st-nome"
        v-model="modulo.nome"
        class="form-control form-control-sm mb-3"
        maxlength="120"
        placeholder="Stagione di caccia 2026/27"
        required
      />
      <div class="d-flex flex-wrap gap-3 mb-3">
        <div>
          <label class="form-label small" for="st-inizio">Inizio previsto</label>
          <input
            id="st-inizio"
            v-model="modulo.inizio_previsto"
            type="date"
            class="form-control form-control-sm"
            required
          />
        </div>
        <div>
          <label class="form-label small" for="st-fine">Fine prevista (prima delle vacanze)</label>
          <input
            id="st-fine"
            v-model="modulo.fine_prevista"
            type="date"
            class="form-control form-control-sm"
            required
          />
        </div>
      </div>
      <p class="small fg-2">
        Dura di solito tre o quattro mesi e inizia dopo le Promesse, con il lancio.
      </p>
      <div class="d-flex gap-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Salva
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="aperta = 0">Annulla</button>
      </div>
    </form>

    <p v-if="!dati.stagioni.length" class="small fg-2">Nessuna stagione.</p>
    <ul v-else class="list-group">
      <li v-for="s in dati.stagioni" :key="s.id" class="list-group-item">
        <div class="d-flex flex-wrap justify-content-between gap-3">
          <strong>{{ s.nome }}</strong>
          <span class="badge" :class="COLORI[s.stato]">{{ s.stato_nome }}</span>
        </div>
        <p class="small mb-1">
          Prevista dal {{ data(s.inizio_previsto) }} al {{ data(s.fine_prevista) }}.
          <template v-if="s.lancio">Lancio il {{ data(s.lancio) }}.</template>
          <template v-if="s.chiusa_il">Chiusa il {{ data(s.chiusa_il) }}.</template>
          {{ s.prede }} prede o voli, {{ s.conquistate }} conquistati.
        </p>
        <div v-if="s.avvisi.length" class="alert theme-warning small mb-1" role="status">
          <div>
            <p v-for="a in s.avvisi" :key="a" class="mb-0">{{ a }}</p>
          </div>
        </div>
        <div v-if="s.da_rileggere.length && s.stato !== 'PREVISTA'" class="small mb-1">
          {{ s.stato === 'CHIUSA' ? 'Da rileggere con i capi' : 'Ancora aperti' }}:
          <ul class="mb-0">
            <li v-for="r in s.da_rileggere" :key="r">{{ r }}</li>
          </ul>
        </div>
        <div v-if="dati.puo_gestire && passo.id !== s.id" class="d-flex flex-wrap gap-1">
          <template v-if="s.stato === 'PREVISTA'">
            <button
              type="button"
              class="btn btn-sm btn-outline theme-success"
              @click="Object.assign(passo, { id: s.id, azione: 'lancia', il: oggi() })"
            >
              Lancio…
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="apri(s)">Modifica</button>
            <button
              type="button"
              class="btn btn-sm btn-link"
              :disabled="inCorso"
              @click="fai(s.id, 'annulla', null)"
            >
              Annulla la stagione
            </button>
          </template>
          <template v-if="s.stato === 'APERTA'">
            <button
              type="button"
              class="btn btn-sm btn-outline theme-primary"
              @click="Object.assign(passo, { id: s.id, azione: 'chiudi', il: oggi() })"
            >
              Chiudi la stagione…
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="apri(s)">Modifica</button>
          </template>
        </div>
        <form
          v-if="passo.id === s.id"
          class="d-flex flex-wrap align-items-end gap-3 mt-1"
          @submit.prevent="fai(s.id, passo.azione as 'lancia' | 'chiudi', passo.il)"
        >
          <div>
            <label class="form-label small" :for="`st-il-${s.id}`">
              {{ passo.azione === 'lancia' ? 'Giorno del lancio' : 'Giorno della chiusura' }}
            </label>
            <input
              :id="`st-il-${s.id}`"
              v-model="passo.il"
              type="date"
              :max="oggi()"
              class="form-control form-control-sm"
              required
            />
          </div>
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            {{ passo.azione === 'lancia' ? 'Lancia' : 'Chiudi' }}
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="passo.id = 0">
            Lascia stare
          </button>
          <span v-if="passo.azione === 'chiudi'" class="small fg-2 w-100">
            Prede e voli ancora aperti restano aperti: nessuno viene conquistato dalla chiusura.
          </span>
        </form>
      </li>
    </ul>
  </section>
</template>
