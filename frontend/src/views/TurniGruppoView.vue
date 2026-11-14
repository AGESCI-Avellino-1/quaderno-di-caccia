<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import {
  api,
  type PeriodoTurno,
  type TurniGruppo,
  type TurnoGruppo,
  type TurnoGruppoIn,
} from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Turns that go round the units (DEC-406), e.g. cleaning the shared rooms of the sede: the
// capigruppo and the capi of the Co.Ca. choose the units in their order, the first day and
// the period; one period may go by hand to another unit. Everyone in the units sees the
// turn on the meetings of the unit that has it. Online only.
const { errore, inCorso, esegui } = useErrore()
const dati = ref<TurniGruppo | null>(null)
const esito = ref('')

const PERIODI: Record<PeriodoTurno, string> = {
  SETTIMANA: 'Ogni settimana',
  MESE: 'Ogni mese',
  TRIMESTRE: 'Ogni tre mesi',
}

onMounted(async () => {
  dati.value = (await esegui(() => api.turniGruppo())) ?? null
})

const vuoto = (): TurnoGruppoIn & { id: number } => ({
  id: 0,
  nome: '',
  unita: [],
  periodo: 'MESE',
  dal: new Date().toLocaleDateString('sv'),
})
const modulo = reactive({ aperto: false, ...vuoto() })

function nuovo() {
  Object.assign(modulo, { aperto: true, ...vuoto() })
}

function modifica(t: TurnoGruppo) {
  Object.assign(modulo, {
    aperto: true,
    id: t.id,
    nome: t.nome,
    unita: t.unita.map((u) => u.id),
    periodo: t.periodo,
    dal: t.dal,
  })
}

// The order of the rotation is the order in which the units are ticked; ↑ moves one up.
function scegli(id: number, scelta: boolean) {
  modulo.unita = scelta ? [...modulo.unita, id] : modulo.unita.filter((u) => u !== id)
}
function su(i: number) {
  const elenco = [...modulo.unita]
  ;[elenco[i - 1], elenco[i]] = [elenco[i]!, elenco[i - 1]!]
  modulo.unita = elenco
}
const nomeUnita = (id: number) => dati.value?.unita.find((u) => u.id === id)?.nome ?? ''

async function salva() {
  esito.value = ''
  const corpo: TurnoGruppoIn = {
    nome: modulo.nome,
    unita: modulo.unita,
    periodo: modulo.periodo,
    dal: modulo.dal,
  }
  const fatti = await esegui(() =>
    modulo.id ? api.modificaTurnoGruppo(modulo.id, corpo) : api.creaTurnoGruppo(corpo),
  )
  if (!fatti) return
  dati.value = fatti
  modulo.aperto = false
  esito.value = 'Turno salvato.'
}

const eliminando = ref<number | null>(null)
async function elimina(id: number) {
  eliminando.value = null
  dati.value = (await esegui(() => api.eliminaTurnoGruppo(id))) ?? dati.value
}

async function cambia(t: TurnoGruppo, indice: number, evento: Event) {
  const scelta = evento.target as HTMLSelectElement
  const valore = scelta.value
  scelta.value = ''
  if (!valore) return
  const unita = valore === 'rotazione' ? null : Number(valore)
  dati.value = (await esegui(() => api.cambiaPeriodo(t.id, indice, unita))) ?? dati.value
}

const data = (iso: string) =>
  new Date(iso).toLocaleDateString('it-IT', { day: 'numeric', month: 'short', year: 'numeric' })
</script>

<template>
  <section>
    <div class="d-flex align-items-center flex-wrap gap-3 mb-3">
      <h1 class="h4 mb-0">Turni del gruppo</h1>
      <button
        v-if="dati?.puo_gestire && !modulo.aperto"
        type="button"
        class="btn btn-sm btn-outline theme-primary ms-auto"
        @click="nuovo"
      >
        Nuovo turno
      </button>
    </div>
    <p class="small fg-2">
      Turni che passano da un'unità all'altra, per esempio la pulizia dei locali della sede. Ogni
      periodo tocca all'unità dopo, nell'ordine scelto; un periodo si può dare a mano a un'altra
      unità e poi si riprende dall'ordine previsto. Capi, ragazzi/e e genitori vedono il turno sulle
      riunioni dell'unità a cui tocca.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>

    <form v-if="modulo.aperto && dati" class="card card-body mb-5" @submit.prevent="salva">
      <div class="row g-3">
        <div class="md:col-6">
          <label class="form-label small" for="turno-nome">Turno</label>
          <input
            id="turno-nome"
            v-model="modulo.nome"
            class="form-control form-control-sm"
            maxlength="80"
            placeholder="Pulizia della sede"
            required
          />
        </div>
        <div class="col-6 md:col-3">
          <label class="form-label small" for="turno-periodo">Cambia</label>
          <select id="turno-periodo" v-model="modulo.periodo" class="form-control form-control-sm">
            <option v-for="(nome, valore) in PERIODI" :key="valore" :value="valore">
              {{ nome }}
            </option>
          </select>
        </div>
        <div class="col-6 md:col-3">
          <label class="form-label small" for="turno-dal">Dal</label>
          <input
            id="turno-dal"
            v-model="modulo.dal"
            type="date"
            class="form-control form-control-sm"
            required
          />
        </div>
        <fieldset class="md:col-6">
          <legend class="form-label small">Unità, nell'ordine in cui le spunti</legend>
          <div v-for="u in dati.unita" :key="u.id" class="form-field mb-1">
            <input
              :id="`turno-unita-${u.id}`"
              type="checkbox"
              class="check"
              :checked="modulo.unita.includes(u.id)"
              @change="scegli(u.id, ($event.target as HTMLInputElement).checked)"
            />
            <label :for="`turno-unita-${u.id}`">{{ u.nome }}</label>
          </div>
        </fieldset>
        <div class="md:col-6">
          <p class="form-label small mb-1">Ordine</p>
          <ol v-if="modulo.unita.length" class="small ps-5 mb-0">
            <li v-for="(id, i) in modulo.unita" :key="id">
              {{ nomeUnita(id) }}
              <button
                v-if="i > 0"
                type="button"
                class="btn btn-link btn-sm p-0 ms-1"
                :aria-label="`Sposta su ${nomeUnita(id)}`"
                @click="su(i)"
              >
                ↑
              </button>
            </li>
          </ol>
          <p v-else class="small fg-2 mb-0">Spunta almeno due unità.</p>
        </div>
        <div class="col-12 d-flex gap-1">
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Salva
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="modulo.aperto = false">
            Annulla
          </button>
        </div>
      </div>
    </form>

    <p v-if="dati && !dati.turni.length" class="fg-2 small">Nessun turno del gruppo.</p>
    <section v-for="t in dati?.turni ?? []" :key="t.id" class="card card-body mb-5">
      <div class="d-flex align-items-center flex-wrap gap-3 mb-1">
        <h2 class="h5 mb-0">{{ t.nome }}</h2>
        <span class="small fg-2">{{ PERIODI[t.periodo] }}, dal {{ data(t.dal) }}</span>
        <template v-if="dati?.puo_gestire">
          <button
            type="button"
            class="btn btn-link btn-sm p-0 ms-auto"
            :disabled="inCorso"
            @click="modifica(t)"
          >
            modifica
          </button>
          <button
            v-if="eliminando !== t.id"
            type="button"
            class="btn btn-link btn-sm p-0"
            @click="eliminando = t.id"
          >
            elimina
          </button>
          <span v-else class="d-flex align-items-center gap-1 small">
            Eliminarlo?
            <button
              type="button"
              class="btn btn-sm btn-solid theme-danger"
              :disabled="inCorso"
              @click="elimina(t.id)"
            >
              Elimina
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="eliminando = null">No</button>
          </span>
        </template>
      </div>
      <p class="small mb-3">{{ t.unita.map((u) => u.nome).join(' → ') }}</p>
      <ul class="list-unstyled small mb-0">
        <li
          v-for="p in t.prossimi"
          :key="p.indice"
          class="d-flex align-items-center flex-wrap gap-3 py-1 border-bottom"
        >
          <span>{{ data(p.dal) }} – {{ data(p.al) }}</span>
          <strong>{{ p.unita }}</strong>
          <span v-if="p.cambiato" class="fg-2">cambiato a mano</span>
          <select
            v-if="dati?.puo_gestire"
            class="form-control form-control-sm w-auto ms-auto"
            :aria-label="`Chi ha il turno dal ${data(p.dal)}`"
            :disabled="inCorso"
            @change="cambia(t, p.indice, $event)"
          >
            <option value="">Cambia…</option>
            <option v-for="u in t.unita" :key="u.id" :value="u.id">{{ u.nome }}</option>
            <option v-if="p.cambiato" value="rotazione">Come da rotazione</option>
          </select>
        </li>
      </ul>
    </section>
  </section>
</template>
