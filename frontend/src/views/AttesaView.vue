<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { api, type DatiAttesa, type ListaAttesa, type VoceAttesa } from '@/api/qdc'
import ModuloAttesa from '@/components/ModuloAttesa.vue'
import { useErrore } from '@/composables/useErrore'

// The waiting list for the capi (DEC-259…DEC-261): by age in this associative year,
// with the units suggested; the order of arrival shows but does not bind. The staff of
// a unit and the capigruppo mark contacts and enrol; enrolling sends the family the
// link to join and takes the entry off the list.
const { errore, inCorso, esegui } = useErrore()
const lista = ref<ListaAttesa | null>(null)
const esito = ref('')
const unitaScelta = reactive<Record<number, number | ''>>({})
const nuovo = ref<DatiAttesa | null>(null)
const daTogliere = ref<number | null>(null)

async function carica() {
  lista.value = (await esegui(() => api.listaAttesa())) ?? null
  for (const v of lista.value?.voci ?? []) {
    unitaScelta[v.id] ??=
      v.contattato_per?.id ??
      (lista.value!.unita.find((u) => v.consigliate.some((c) => c.id === u.id))?.id || '')
  }
}

onMounted(carica)

/** Groups by age in the current associative year, youngest first. */
const perEta = computed(() => {
  const gruppi = new Map<number, VoceAttesa[]>()
  for (const v of lista.value?.voci ?? []) {
    if (!gruppi.has(v.eta)) gruppi.set(v.eta, [])
    gruppi.get(v.eta)!.push(v)
  }
  return [...gruppi.entries()].sort((a, b) => a[0] - b[0])
})

const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
const puoAgire = (id: number | '') => !!id && !!lista.value?.unita.some((u) => u.id === id)

async function contattato(v: VoceAttesa) {
  const unita = unitaScelta[v.id]
  if (!unita) return
  await esegui(() => api.contattoAttesa(v.id, unita))
  await carica()
}

async function daContattare(v: VoceAttesa) {
  await esegui(() => api.contattoAttesa(v.id, null))
  await carica()
}

async function iscrivi(v: VoceAttesa) {
  const unita = unitaScelta[v.id]
  if (!unita) return
  esito.value = ''
  await esegui(() => api.iscriviDallaLista(v.id, unita))
  if (errore.value) return
  esito.value = `${v.nome} ${v.cognome}: la famiglia riceve il link per l'iscrizione.`
  await carica()
}

async function togli(v: VoceAttesa) {
  await esegui(() => api.togliDallaLista(v.id))
  daTogliere.value = null
  await carica()
}

function nuovoInLista() {
  nuovo.value = {
    nome: '',
    cognome: '',
    sesso: '',
    data_nascita: '',
    luogo_nascita: '',
    da_se: false,
    contatto_nome: '',
    contatto_cognome: '',
    telefono: '',
    email: '',
    indirizzo: '',
    comune: '',
    provincia: '',
    cap: '',
  }
}

async function inserisci() {
  if (!nuovo.value) return
  await esegui(() => api.inserisciInLista(nuovo.value!))
  if (errore.value) return
  esito.value = "In lista: la famiglia riceve l'email di conferma."
  nuovo.value = null
  await carica()
}
</script>

<template>
  <section>
    <div class="d-flex flex-wrap align-items-baseline gap-3 mb-1">
      <h1 class="h4 mb-0">Lista d'attesa</h1>
      <button
        v-if="lista?.puo_inserire && !nuovo"
        type="button"
        class="btn btn-sm btn-outline theme-primary ms-auto"
        @click="nuovoInLista"
      >
        Metti in lista
      </button>
    </div>
    <p class="small fg-2">
      Divisa per età nell'anno scout {{ lista?.anno }} (tra parentesi nel
      {{ lista?.anno_prossimo }}). Si chiama secondo i posti e il bilanciamento delle unità, non
      secondo l'ordine di arrivo. Le età delle unità si cambiano nella pagina di ogni unità.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>

    <form v-if="nuovo" class="card card-body mb-7" @submit.prevent="inserisci">
      <ModuloAttesa v-model="nuovo" prefisso="nuovo" />
      <div class="d-flex gap-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Metti in lista
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="nuovo = null">Annulla</button>
      </div>
    </form>

    <p v-if="lista && !lista.voci.length" class="fg-2">Nessuno in lista d'attesa.</p>
    <section v-for="[eta, voci] in perEta" :key="eta" class="mb-7">
      <h2 class="h5">
        {{ eta }} anni <span class="small fg-2">({{ voci.length }})</span>
      </h2>
      <div v-for="v in voci" :key="v.id" class="card card-body mb-3">
        <div class="d-flex flex-wrap align-items-center gap-3">
          <strong>{{ v.nome }} {{ v.cognome }}</strong>
          <span class="badge theme-secondary">{{ v.sesso === 'F' ? 'F' : 'M' }}</span>
          <span class="small">{{ v.eta }} anni ({{ v.eta_prossimo }})</span>
          <span v-if="v.stato === 'CONTATTATO'" class="badge theme-info"
            >contattato per {{ v.contattato_per?.nome }} il {{ data(v.contattato_il!) }}</span
          >
          <span v-if="v.possibile_doppione" class="badge theme-warning">possibile doppione</span>
          <span v-if="v.conferma_chiesta_il" class="badge theme-warning"
            >conferma chiesta il {{ data(v.conferma_chiesta_il) }}</span
          >
        </div>
        <div class="small mt-1">
          Consigliata:
          <template v-if="v.consigliate.length">{{
            v.consigliate.map((u) => u.nome).join(', ')
          }}</template>
          <span v-else class="fg-2">nessuna unità quest'anno</span>
          <template v-if="v.consigliate_prossimo.length">
            · l'anno prossimo: {{ v.consigliate_prossimo.map((u) => u.nome).join(', ') }}</template
          >
        </div>
        <div class="small fg-2">
          {{
            v.da_se ? 'Si contatta lui/lei' : `Genitore: ${v.contatto_nome} ${v.contatto_cognome}`
          }}
          · <a :href="`tel:${v.telefono}`">{{ v.telefono }}</a> ·
          <a :href="`mailto:${v.email}`">{{ v.email }}</a> · {{ v.comune }} · in lista dal
          {{ data(v.inserito_il) }}<template v-if="v.inserito_da_un_capo"> da un capo</template>
        </div>
        <div v-if="lista?.unita.length" class="d-flex flex-wrap align-items-end gap-3 mt-3">
          <div>
            <label class="form-label small mb-0" :for="`unita-${v.id}`">Unità</label>
            <select
              :id="`unita-${v.id}`"
              v-model="unitaScelta[v.id]"
              class="form-control form-control-sm"
            >
              <option value="" disabled>Scegli</option>
              <option v-for="u in lista.unita" :key="u.id" :value="u.id">{{ u.nome }}</option>
            </select>
          </div>
          <button
            type="button"
            class="btn btn-sm btn-outline theme-primary"
            :disabled="inCorso || !puoAgire(unitaScelta[v.id]!)"
            @click="contattato(v)"
          >
            Contattato
          </button>
          <button
            type="button"
            class="btn btn-sm btn-solid theme-primary"
            :disabled="inCorso || !puoAgire(unitaScelta[v.id]!)"
            @click="iscrivi(v)"
          >
            Iscrivi
          </button>
          <button
            v-if="v.stato === 'CONTATTATO'"
            type="button"
            class="btn btn-sm btn-link"
            :disabled="inCorso"
            @click="daContattare(v)"
          >
            Di nuovo da contattare
          </button>
          <button
            v-if="daTogliere !== v.id"
            type="button"
            class="btn btn-sm btn-link ms-auto"
            @click="daTogliere = v.id"
          >
            Togli dalla lista
          </button>
          <span v-else class="ms-auto d-flex gap-3 align-items-center">
            <span class="small">I dati si cancellano.</span>
            <button
              type="button"
              class="btn btn-sm btn-solid theme-danger"
              :disabled="inCorso"
              @click="togli(v)"
            >
              Togli
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="daTogliere = null">No</button>
          </span>
        </div>
      </div>
    </section>
  </section>
</template>
