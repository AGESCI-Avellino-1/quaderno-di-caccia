<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, esportazioneBuonaStrada, type DaInserire } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// For the capigruppo: completed registrations, with the data to enter in BuonaStrada by
// hand; also as XLSX and PDF. Once entered, "inserita"; the next import finds the member
// by codice fiscale and replaces the provisional code. Online only: every read is logged.
const { errore, inCorso, esegui } = useErrore()
const iscrizioni = ref<DaInserire[]>([])

async function carica() {
  iscrizioni.value = (await esegui(() => api.iscrizioniBuonaStrada())) ?? []
}
onMounted(carica)

async function inserita(id: number) {
  if (await esegui(() => api.segnaInserita(id))) await carica()
}
</script>

<template>
  <section>
    <h1 class="h4 mb-1">Iscrizioni da inserire in BuonaStrada</h1>
    <p class="fg-2 small">
      Iscrizioni dall'app complete di dati e moduli. Inseriscile in BuonaStrada e segnale come
      inserite: con la prossima importazione il codice socio provvisorio diventa quello vero.
    </p>
    <div class="d-flex flex-wrap gap-3 mb-5">
      <a class="btn btn-sm btn-outline theme-primary" :href="esportazioneBuonaStrada('xlsx')">
        Scarica in Excel (XLSX)
      </a>
      <a class="btn btn-sm btn-outline theme-primary" :href="esportazioneBuonaStrada('pdf')">
        Scarica in PDF
      </a>
    </div>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <p v-if="!inCorso && !iscrizioni.length" class="fg-2">Nessuna iscrizione da inserire.</p>
    <article v-for="i in iscrizioni" :key="i.id" class="card card-body mb-5">
      <div class="d-flex flex-wrap align-items-baseline gap-3 mb-3">
        <h2 class="h5 mb-0">{{ i.valori[1] }} {{ i.valori[2] }}</h2>
        <span v-if="i.stato === 'INSERITA'" class="badge theme-info">
          inserita, in attesa dell'importazione
        </span>
        <button
          v-else
          type="button"
          class="btn btn-sm btn-solid theme-primary ms-auto"
          :disabled="inCorso"
          @click="inserita(i.id)"
        >
          Segna come inserita
        </button>
      </div>
      <dl class="row small mb-0">
        <template v-for="(colonna, n) in i.colonne" :key="colonna">
          <dt class="col-5 md:col-3 fw-normal fg-2">{{ colonna }}</dt>
          <dd class="col-7 md:col-9">{{ i.valori[n] || '—' }}</dd>
        </template>
      </dl>
    </article>
  </section>
</template>
