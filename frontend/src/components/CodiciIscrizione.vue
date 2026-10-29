<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

import { api, qrCodice, type CodiceIscrizione } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Registration codes of a unit: reusable until the deadline (open day, poster) or
// personal (one registration). The QR code encodes the link. Shown only to who may
// create them (the API answers puo_creare: false otherwise). Online only.
const props = defineProps<{ unita: number }>()
const { errore, inCorso, esegui } = useErrore()
const puoCreare = ref(false)
const codici = ref<CodiceIscrizione[]>([])
const aperto = ref(false)
const qrAperto = ref<number | null>(null)
const copiato = ref<number | null>(null)
const tra = (giorni: number) => {
  const giorno = new Date()
  giorno.setDate(giorno.getDate() + giorni)
  return giorno.toLocaleDateString('sv')
}
const modulo = reactive({ tipo: 'UNITA', scadenza: tra(14) })

async function carica(id: number) {
  try {
    const dati = await api.codiciIscrizione(id)
    puoCreare.value = dati.puo_creare
    codici.value = dati.codici
  } catch {
    puoCreare.value = false
  }
}
watch(() => props.unita, carica, { immediate: true })

async function crea() {
  const nuovo = await esegui(() => api.creaCodiceIscrizione(props.unita, { ...modulo }))
  if (!nuovo) return
  aperto.value = false
  qrAperto.value = nuovo.id
  await carica(props.unita)
}

async function disattiva(id: number) {
  if (await esegui(() => api.disattivaCodice(id))) await carica(props.unita)
}

async function copia(c: CodiceIscrizione) {
  try {
    await navigator.clipboard.writeText(c.link)
    copiato.value = c.id
  } catch {
    copiato.value = null
  }
}

const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
</script>

<template>
  <section v-if="puoCreare" class="card card-body mb-5">
    <div class="d-flex align-items-center">
      <h2 class="h5 mb-0">Codici di iscrizione</h2>
      <button
        v-if="!aperto"
        type="button"
        class="btn btn-sm btn-outline theme-primary ms-auto"
        @click="
          () => {
            modulo.tipo = 'UNITA'
            modulo.scadenza = tra(14)
            aperto = true
          }
        "
      >
        Nuovo codice
      </button>
    </div>
    <p class="form-text mb-3">
      Chi riceve il codice (o il link, o il QR code) chiede di iscriversi a questa unità; la
      richiesta va poi accolta.
    </p>
    <div v-if="errore" class="alert theme-danger py-3 small" role="alert">{{ errore }}</div>

    <form v-if="aperto" class="row g-3 mb-3" @submit.prevent="crea">
      <div class="col-12 sm:col-7">
        <label class="form-label small" for="codice-tipo">Tipo</label>
        <select id="codice-tipo" v-model="modulo.tipo" class="form-control form-control-sm">
          <option value="UNITA">Per l'unità: più persone, fino alla scadenza</option>
          <option value="PERSONALE">Personale: una sola iscrizione</option>
        </select>
      </div>
      <div class="col-12 sm:col-5">
        <label class="form-label small" for="codice-scadenza">Valido fino al</label>
        <input
          id="codice-scadenza"
          v-model="modulo.scadenza"
          type="date"
          class="form-control form-control-sm"
          :min="tra(0)"
          required
        />
      </div>
      <div class="col-12 d-flex gap-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Crea
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="aperto = false">Annulla</button>
      </div>
    </form>

    <p v-if="!codici.length" class="fg-2 small mb-0">Nessun codice.</p>
    <div v-for="c in codici" :key="c.id" class="border-top pt-3 mt-1 small">
      <div class="d-flex flex-wrap align-items-baseline gap-3">
        <strong class="font-monospace">{{ c.codice }}</strong>
        <span>{{ c.tipo === 'UNITA' ? "per l'unità" : 'personale' }}</span>
        <span v-if="c.valido" class="badge theme-success"
          >valido fino al {{ data(c.scadenza) }}</span
        >
        <span v-else class="badge theme-secondary">non più valido</span>
        <span class="fg-2">usato {{ c.usi }} {{ c.usi === 1 ? 'volta' : 'volte' }}</span>
      </div>
      <div v-if="c.valido" class="d-flex flex-wrap gap-3 mt-1">
        <button
          type="button"
          class="btn btn-link btn-sm p-0"
          @click="qrAperto = qrAperto === c.id ? null : c.id"
        >
          {{ qrAperto === c.id ? 'nascondi QR code' : 'QR code' }}
        </button>
        <button type="button" class="btn btn-link btn-sm p-0" @click="copia(c)">
          {{ copiato === c.id ? 'link copiato' : 'copia il link' }}
        </button>
        <button type="button" class="btn btn-link btn-sm p-0" @click="disattiva(c.id)">
          disattiva
        </button>
      </div>
      <img
        v-if="qrAperto === c.id"
        :src="qrCodice(c.id)"
        :alt="`QR code per iscriversi con il codice ${c.codice}`"
        width="200"
        height="200"
        class="mt-3"
      />
    </div>
  </section>
</template>
