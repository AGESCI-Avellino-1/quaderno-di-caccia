<script setup lang="ts">
import CampoIndirizzo from '@/components/CampoIndirizzo.vue'
import { onMounted, reactive, ref } from 'vue'

import { api, type Localita } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The group's places for meetings and events (DEC-310), kept by the capigruppo: a new one
// written while creating a meeting enters the list at once, and is fixed or taken away
// here. A place taken away stays on the meetings that used it.
const { errore, inCorso, esegui } = useErrore()
const elenco = ref<Localita[]>([])
const aperta = ref<number | 'nuova' | null>(null)
const dati = reactive({ nome: '', indirizzo: '', mappa: '' })

async function carica() {
  elenco.value = (await esegui(() => api.localita())) ?? elenco.value
}
onMounted(carica)

function apri(l: Localita | null) {
  aperta.value = l ? l.id : 'nuova'
  Object.assign(
    dati,
    l
      ? { nome: l.nome, indirizzo: l.indirizzo, mappa: l.mappa }
      : {
          nome: '',
          indirizzo: '',
          mappa: '',
        },
  )
}

async function salva() {
  const fatta = await esegui(() =>
    aperta.value === 'nuova'
      ? api.creaLocalita({ ...dati })
      : api.modificaLocalita(aperta.value as number, { ...dati }),
  )
  if (!fatta) return
  aperta.value = null
  await carica()
}

async function togli(l: Localita) {
  await esegui(() => api.togliLocalita(l.id))
  if (!errore.value) await carica()
}
</script>

<template>
  <section class="mb-7">
    <h2 class="h5">Località</h2>
    <p class="small fg-2">
      Le sedi e le basi del gruppo, da scegliere quando si crea una riunione. Chi crea una riunione
      può scriverne una nuova, che entra subito qui: correggila o toglila se serve.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div class="card card-body">
      <p v-if="!elenco.length" class="small mb-3">Nessuna località.</p>
      <ul v-else class="list-unstyled mb-3">
        <li v-for="l in elenco" :key="l.id" class="py-1 border-bottom">
          <div class="d-flex flex-wrap align-items-center gap-3">
            <strong>{{ l.nome }}</strong>
            <span v-if="l.indirizzo" class="small fg-2">{{ l.indirizzo }}</span>
            <button type="button" class="btn btn-link btn-sm p-0 ms-auto" @click="apri(l)">
              modifica
            </button>
            <button type="button" class="btn btn-link btn-sm p-0" @click="togli(l)">togli</button>
          </div>
        </li>
      </ul>
      <form v-if="aperta !== null" class="row g-3" @submit.prevent="salva">
        <div class="md:col-6">
          <label class="form-label small" for="loc-nome">Nome</label>
          <input id="loc-nome" v-model="dati.nome" class="form-control form-control-sm" required />
        </div>
        <div class="md:col-6">
          <label class="form-label small" for="loc-indirizzo">Indirizzo</label>
          <CampoIndirizzo
            v-model="dati.indirizzo"
            id-campo="loc-indirizzo"
            @scelta="
              (p) => {
                if (!dati.nome.trim()) dati.nome = p.nome
              }
            "
          />
        </div>
        <div class="col-12">
          <label class="form-label small" for="loc-mappa">Link alla mappa (facoltativo)</label>
          <input
            id="loc-mappa"
            v-model="dati.mappa"
            type="url"
            class="form-control form-control-sm"
            placeholder="https://maps.google.com/…"
          />
          <div class="form-text small">Senza link, la mappa si apre dall'indirizzo.</div>
        </div>
        <div class="col-12 d-flex gap-3">
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Salva
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="aperta = null">Annulla</button>
        </div>
      </form>
      <div v-else>
        <button type="button" class="btn btn-sm btn-outline theme-primary" @click="apri(null)">
          Aggiungi una località
        </button>
      </div>
    </div>
  </section>
</template>
