<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, type Intestazione } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The group's letterhead on every print: the AGESCI forms, receipts (DEC-192). The
// capigruppo write it; the other capi read it.
const { errore, inCorso, esegui } = useErrore()
const dati = ref<Intestazione | null>(null)
const esito = ref('')

onMounted(async () => {
  dati.value = (await esegui(() => api.intestazione())) ?? null
})

async function salva() {
  if (!dati.value) return
  const nuovi = await esegui(() => api.salvaIntestazione(dati.value!))
  if (nuovi) {
    dati.value = nuovi
    esito.value = 'Salvato.'
  }
}

async function logo(evento: Event) {
  const file = (evento.target as HTMLInputElement).files?.[0]
  if (!file) return
  const nuovi = await esegui(() => api.caricaLogo(file))
  if (nuovi) {
    dati.value = nuovi
    esito.value = 'Logo caricato.'
  }
}

async function togliLogo() {
  const nuovi = await esegui(() => api.togliLogo())
  if (nuovi) dati.value = nuovi
}

const CAMPI: [keyof Intestazione, string, string][] = [
  ['denominazione', 'Nome del gruppo in BuonaStrada', 'AVELLINO 1'],
  ['denominazione_sociale', 'Denominazione sociale', 'AGESCI Gruppo Avellino 1'],
  ['codice_fiscale', 'Codice fiscale', ''],
  ['sede_indirizzo', 'Sede: via e numero', ''],
  ['sede_cap', 'CAP', ''],
  ['sede_comune', 'Comune', ''],
  ['sede_provincia', 'Provincia (sigla)', 'AV'],
  ['telefono', 'Telefono', ''],
  ['cellulare', 'Cellulare', ''],
  ['email', 'Email', ''],
  ['pec', 'PEC', ''],
  ['sito', 'Sito', 'https://…'],
  ['runts_repertorio', 'Iscrizione al RUNTS: numero di repertorio', ''],
]
</script>

<template>
  <section v-if="dati" class="mb-7">
    <h2 class="h5">Intestazione delle stampe</h2>
    <p class="small fg-2">
      I dati ufficiali del gruppo: compaiono sui moduli da firmare (come la scheda sanitaria) e
      sulle ricevute, non nel titolo del sito. RUNTS è il Registro unico nazionale del Terzo
      settore.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>
    <form class="card card-body" @submit.prevent="salva">
      <fieldset :disabled="!dati.puo_modificare" class="row g-3">
        <div v-for="[campo, etichetta, esempio] in CAMPI" :key="campo" class="col-12 md:col-6">
          <label class="form-label small mb-0" :for="`int-${campo}`">{{ etichetta }}</label>
          <input
            :id="`int-${campo}`"
            v-model="dati[campo] as string"
            class="form-control form-control-sm"
            :placeholder="esempio"
          />
        </div>
        <div class="col-12 md:col-6">
          <label class="form-label small mb-0" for="int-runts-data"
            >Iscrizione al RUNTS: data</label
          >
          <input
            id="int-runts-data"
            v-model="dati.runts_data"
            type="date"
            class="form-control form-control-sm"
          />
        </div>
      </fieldset>
      <div v-if="dati.puo_modificare" class="d-flex flex-wrap align-items-center gap-3 mt-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Salva
        </button>
        <label class="btn btn-sm btn-outline theme-primary mb-0" for="int-logo">
          {{ dati.logo ? 'Cambia il logo' : 'Carica il logo' }}
        </label>
        <input
          id="int-logo"
          type="file"
          accept="image/png,image/jpeg"
          class="d-none"
          @change="logo"
        />
        <button v-if="dati.logo" type="button" class="btn btn-sm btn-link" @click="togliLogo">
          Togli il logo
        </button>
      </div>
    </form>
  </section>
</template>
