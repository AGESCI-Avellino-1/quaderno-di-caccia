<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { api, CATEGORIE_BC, type TipologiaBC, type TipologiaBCIn } from '@/api/qdc'
import CampiVincoliBC from '@/components/CampiVincoliBC.vue'
import { coincide } from '@/components/sceltaDaElenco'
import { useErrore } from '@/composables/useErrore'

// The types of BuonaCaccia events with their default constraints (DEC-398): filled at
// installation from BuonaCaccia's menu, changed by any capo. A type already used is
// deactivated, never removed; «Altro» has no constraints and stays.
const { errore, inCorso, esegui } = useErrore()
const tipologie = ref<TipologiaBC[]>([])
const cerca = ref('')
const aperta = ref<number | 'nuova' | null>(null)
const modulo = ref<TipologiaBCIn | null>(null)
const daTogliere = ref<number | null>(null)

onMounted(carica)
async function carica() {
  tipologie.value = (await esegui(() => api.tipologieBC(true))) ?? tipologie.value
}

const filtrate = computed(() =>
  tipologie.value.filter((t) => coincide({ id: t.id, nome: t.nome }, cerca.value)),
)
const perCategoria = computed(() =>
  [...CATEGORIE_BC, ['ALTRO', 'Altro'] as const]
    .map(([categoria, nome]) => ({
      nome,
      voci: filtrate.value.filter((t) => t.categoria === categoria),
    }))
    .filter((g) => g.voci.length),
)

function vuoto(): TipologiaBCIn {
  return {
    nome: '',
    categoria: 'SPECIALE',
    attiva: true,
    branche: [],
    eta_minima: null,
    eta_massima: null,
    livello_minimo: null,
    massimo_per_unita: null,
    massimo_per_gruppo: null,
  }
}

function apri(t: TipologiaBC | null) {
  aperta.value = t?.id ?? 'nuova'
  modulo.value = t
    ? {
        nome: t.nome,
        categoria: t.categoria,
        attiva: t.attiva,
        branche: [...t.branche],
        eta_minima: t.eta_minima,
        eta_massima: t.eta_massima,
        livello_minimo: t.livello_minimo,
        massimo_per_unita: t.massimo_per_unita,
        massimo_per_gruppo: t.massimo_per_gruppo,
      }
    : vuoto()
}

async function salva() {
  const dati = modulo.value!
  const id = aperta.value
  const fatta = await esegui(() =>
    id === 'nuova' ? api.creaTipologiaBC(dati) : api.modificaTipologiaBC(id!, dati),
  )
  if (!fatta) return
  aperta.value = null
  await carica()
}

async function togli(id: number) {
  await esegui(() => api.eliminaTipologiaBC(id))
  daTogliere.value = null
  if (!errore.value) await carica()
}

function vincoli(t: TipologiaBC): string {
  const sigle = { LC: 'L/C', EG: 'E/G', RS: 'R/S', COCA: 'Co.Ca.' }
  const parti: string[] = t.branche.map((b) => sigle[b])
  if (t.eta_minima != null || t.eta_massima != null)
    parti.push(`${t.eta_minima ?? '…'}–${t.eta_massima ?? '…'} anni`)
  if (t.livello_minimo != null) parti.push(`Fo.Ca. ≥ ${t.livello_minimo}`)
  if (t.massimo_per_unita != null) parti.push(`max ${t.massimo_per_unita} per unità`)
  if (t.massimo_per_gruppo != null) parti.push(`max ${t.massimo_per_gruppo} per gruppo`)
  return parti.join(' · ')
}
</script>

<template>
  <section>
    <h1 class="h4">Tipi di evento su BuonaCaccia</h1>
    <p class="small fg-2">
      Il tipo di ogni evento su BuonaCaccia, con i vincoli di base: chi crea un evento li trova già
      scritti e può cambiarli per quell'evento. Chi non rispetta branche, età o livello di
      formazione non si può iscrivere; i massimi danno solo un avviso. Nella scelta compaiono solo i
      tipi delle branche che il gruppo ha. Un tipo già usato non si toglie: si disattiva.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div class="d-flex flex-wrap gap-3 align-items-center mb-5">
      <input
        v-model="cerca"
        type="search"
        class="form-control form-control-sm flex-grow-1"
        style="max-width: 24rem"
        placeholder="Cerca un tipo"
        aria-label="Cerca un tipo"
      />
      <button
        v-if="aperta !== 'nuova'"
        type="button"
        class="btn btn-sm btn-solid theme-primary"
        @click="apri(null)"
      >
        Nuovo tipo
      </button>
    </div>

    <form v-if="aperta !== null && modulo" class="card card-body mb-5" @submit.prevent="salva">
      <h2 class="h6">{{ aperta === 'nuova' ? 'Nuovo tipo' : modulo.nome }}</h2>
      <div class="row g-3 mb-3">
        <div class="col-12 md:col-6">
          <label class="form-label small" for="tbc-nome">Nome</label>
          <input
            id="tbc-nome"
            v-model="modulo.nome"
            class="form-control form-control-sm"
            maxlength="120"
            required
          />
        </div>
        <div v-if="modulo.categoria !== 'ALTRO'" class="col-12 md:col-4">
          <label class="form-label small" for="tbc-categoria">Categoria</label>
          <select
            id="tbc-categoria"
            v-model="modulo.categoria"
            class="form-control form-control-sm"
          >
            <option v-for="[valore, nome] in CATEGORIE_BC" :key="valore" :value="valore">
              {{ nome }}
            </option>
          </select>
        </div>
        <div v-if="modulo.categoria !== 'ALTRO'" class="col-12 form-field">
          <input id="tbc-attiva" v-model="modulo.attiva" type="checkbox" class="check" />
          <label class="small" for="tbc-attiva"
            >Attivo (si può scegliere per un evento nuovo)</label
          >
        </div>
      </div>
      <CampiVincoliBC v-if="modulo.categoria !== 'ALTRO'" v-model="modulo" class="mb-3" />
      <p v-else class="small fg-2">«Altro» non ha vincoli e resta sempre attivo.</p>
      <div class="d-flex gap-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Salva
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="aperta = null">Annulla</button>
      </div>
    </form>

    <section v-for="g in perCategoria" :key="g.nome" class="mb-5">
      <h2 class="h5">{{ g.nome }}</h2>
      <ul class="list-group">
        <li v-for="t in g.voci" :key="t.id" class="list-group-item">
          <div class="d-flex flex-wrap align-items-center justify-content-between gap-3">
            <div>
              {{ t.nome }}
              <span v-if="!t.attiva" class="badge theme-secondary ms-1">disattivato</span>
              <div class="small fg-2">
                <template v-if="vincoli(t)">{{ vincoli(t) }}</template>
                <template v-else>Senza vincoli</template>
                <template v-if="t.eventi"> · {{ t.eventi }} eventi</template>
              </div>
            </div>
            <div class="d-flex gap-3 align-items-center">
              <button type="button" class="btn btn-sm btn-link" @click="apri(t)">Modifica</button>
              <template v-if="!t.altro && !t.eventi">
                <button
                  v-if="daTogliere !== t.id"
                  type="button"
                  class="btn btn-sm btn-link"
                  @click="daTogliere = t.id"
                >
                  Togli
                </button>
                <template v-else>
                  <span class="small">Togliere {{ t.nome }}?</span>
                  <button
                    type="button"
                    class="btn btn-sm btn-solid theme-danger"
                    :disabled="inCorso"
                    @click="togli(t.id)"
                  >
                    Togli
                  </button>
                  <button type="button" class="btn btn-sm btn-link" @click="daTogliere = null">
                    No
                  </button>
                </template>
              </template>
            </div>
          </div>
        </li>
      </ul>
    </section>
  </section>
</template>
