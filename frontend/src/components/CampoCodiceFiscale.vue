<script setup lang="ts">
import { reactive, ref } from 'vue'

import { api } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// A codice fiscale field with "Calcola": the server proposes it from name, surname, sex,
// date and place of birth (standard rules, municipalities from ISTAT); whoever types it
// checks it against the documents (homonyms may differ). What the form does not know is
// asked here, only for the calculation.
const codice = defineModel<string>({ required: true })
const props = defineProps<{
  id: string
  etichetta: string
  nome: string
  cognome: string
  sesso?: string
  dataNascita?: string
  luogoNascita?: string
  obbligatorio?: boolean
}>()

const { errore, inCorso, esegui } = useErrore()
const aperto = ref(false)
const proposta = ref<{ codice_fiscale: string; comune: string } | null>(null)
const extra = reactive({ sesso: '', data: '', luogo: '' })
const suggeriti = ref<string[]>([])

function apri() {
  aperto.value = true
  proposta.value = null
  extra.sesso = props.sesso ?? ''
  extra.data = props.dataNascita ?? ''
  extra.luogo = props.luogoNascita ?? ''
}

let attesa: ReturnType<typeof setTimeout> | undefined
function suggerisci() {
  clearTimeout(attesa)
  attesa = setTimeout(async () => {
    suggeriti.value =
      extra.luogo.trim().length >= 2 ? await api.comuni(extra.luogo).catch(() => []) : []
  }, 250)
}

async function calcola() {
  proposta.value =
    (await esegui(() =>
      api.proponiCodiceFiscale({
        nome: props.nome,
        cognome: props.cognome,
        sesso: extra.sesso,
        data_nascita: extra.data,
        luogo_nascita: extra.luogo,
      }),
    )) ?? null
}

function usa() {
  if (!proposta.value) return
  codice.value = proposta.value.codice_fiscale
  aperto.value = false
}
</script>

<template>
  <div>
    <label class="form-label small" :for="id">{{ etichetta }}</label>
    <div class="d-flex gap-1">
      <input
        :id="id"
        v-model="codice"
        class="form-control"
        maxlength="16"
        autocapitalize="characters"
        :required="obbligatorio"
      />
      <button
        type="button"
        class="btn btn-sm btn-outline theme-primary"
        :disabled="!nome || !cognome"
        :title="nome && cognome ? 'Calcola il codice fiscale' : 'Scrivi prima nome e cognome'"
        @click="apri"
      >
        Calcola
      </button>
    </div>
    <div v-if="aperto" class="card card-body mt-1 small">
      <div class="row g-3">
        <div v-if="!sesso" class="col-12 sm:col-4">
          <label class="form-label small mb-0" :for="`${id}-sesso`">Sesso</label>
          <select :id="`${id}-sesso`" v-model="extra.sesso" class="form-control form-control-sm">
            <option value="" disabled>Scegli</option>
            <option value="F">Femmina</option>
            <option value="M">Maschio</option>
          </select>
        </div>
        <div v-if="!dataNascita" class="col-12 sm:col-4">
          <label class="form-label small mb-0" :for="`${id}-data`">Data di nascita</label>
          <input
            :id="`${id}-data`"
            v-model="extra.data"
            type="date"
            class="form-control form-control-sm"
          />
        </div>
        <div v-if="!luogoNascita" class="col-12 sm:col-4">
          <label class="form-label small mb-0" :for="`${id}-luogo`">Comune di nascita</label>
          <input
            :id="`${id}-luogo`"
            v-model="extra.luogo"
            :list="`${id}-comuni`"
            class="form-control form-control-sm"
            autocomplete="off"
            @input="suggerisci"
          />
          <datalist :id="`${id}-comuni`">
            <option v-for="c in suggeriti" :key="c" :value="c" />
          </datalist>
        </div>
      </div>
      <div class="d-flex flex-wrap gap-3 mt-3">
        <button
          type="button"
          class="btn btn-sm btn-solid theme-primary"
          :disabled="inCorso || !extra.sesso || !extra.data || !extra.luogo"
          @click="calcola"
        >
          Calcola
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="aperto = false">Chiudi</button>
      </div>
      <div v-if="errore" class="alert theme-danger small mt-3" role="alert">{{ errore }}</div>
      <div v-if="proposta" class="mt-3">
        <p class="mb-1">
          Proposta: <strong class="user-select-all">{{ proposta.codice_fiscale }}</strong> (nato a
          {{ proposta.comune }}). Controllala sulla tessera sanitaria: a volte l'Agenzia delle
          Entrate ne assegna uno diverso.
        </p>
        <button type="button" class="btn btn-sm btn-outline theme-primary" @click="usa">
          Usa questo codice
        </button>
      </div>
    </div>
  </div>
</template>
