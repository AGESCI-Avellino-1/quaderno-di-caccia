<script setup lang="ts">
import { ref, watch } from 'vue'

import { api, type RichiestaIscrizione } from '@/api/qdc'
import ModuliIscrizione from '@/components/ModuliIscrizione.vue'
import { useErrore } from '@/composables/useErrore'

// Registration requests to decide: the unit staff for their units, the capigruppo for
// every unit (only they for the Co.Ca.). Approving sets the deadline to complete data
// and signed forms. Online only: the API lists only what this user decides.
const { errore, inCorso, esegui } = useErrore()
const richieste = ref<RichiestaIscrizione[]>([])
const aperta = ref<{ id: number; azione: 'approva' | 'rifiuta' } | null>(null)
const tra30giorni = () => {
  const giorno = new Date()
  giorno.setDate(giorno.getDate() + 30)
  return giorno.toLocaleDateString('sv')
}
const scadenza = ref(tra30giorni())
const motivo = ref('')
const oggi = new Date().toLocaleDateString('sv')
// Also the accepted ones still to complete: their signed forms are checked here.
const accolte = ref(false)

async function carica() {
  const tutte = (await esegui(() => api.iscrizioniDaDecidere(accolte.value))) ?? []
  richieste.value = accolte.value
    ? tutte.filter((r) => ['IN_ATTESA', 'APPROVATA', 'SOSPESA'].includes(r.stato))
    : tutte
}
watch(accolte, carica, { immediate: true })

function apri(id: number, azione: 'approva' | 'rifiuta') {
  aperta.value = { id, azione }
  scadenza.value = tra30giorni()
  motivo.value = ''
}

async function decidi(r: RichiestaIscrizione) {
  const fatta = await esegui(() =>
    aperta.value?.azione === 'approva'
      ? api.approvaIscrizione(r.id, scadenza.value)
      : api.rifiutaIscrizione(r.id, motivo.value),
  )
  if (!fatta) return
  aperta.value = null
  await carica()
}

const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
</script>

<template>
  <section>
    <h1 class="h4 mb-1">Richieste di iscrizione</h1>
    <p class="fg-2 small">
      Chi si iscrive dall'app con un codice. Accolta la richiesta, il socio entra nell'unità con un
      codice socio provvisorio, finché il gruppo non lo inserisce in BuonaStrada.
    </p>
    <div class="form-field mb-5">
      <div class="switch">
        <input id="anche-accolte" v-model="accolte" type="checkbox" role="switch" />
      </div>
      <label for="anche-accolte">Anche quelle accolte, da completare</label>
    </div>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <p v-if="!inCorso && !richieste.length" class="fg-2">Nessuna richiesta da esaminare.</p>
    <ul class="list-group">
      <li v-for="r in richieste" :key="r.id" class="list-group-item">
        <div class="d-flex flex-wrap align-items-baseline gap-3">
          <strong>{{ r.cognome }} {{ r.nome }}</strong>
          <span class="fg-2 small">{{ r.unita }}</span>
        </div>
        <div class="small">
          Nato/a il {{ data(r.data_nascita) }} · codice fiscale {{ r.codice_fiscale }}
          <template v-if="r.genitore"> · genitore {{ r.genitore }}</template>
        </div>
        <div class="fg-2 small">
          Richiesta da {{ r.richiesta_da ?? '—' }} il {{ data(r.creata_il) }}
        </div>
        <template v-if="r.stato !== 'IN_ATTESA'">
          <div class="small">
            <span class="badge" :class="r.stato === 'SOSPESA' ? 'theme-danger' : 'theme-info'">{{
              r.stato_nome
            }}</span>
            <template v-if="r.scadenza_completamento">
              entro il {{ data(r.scadenza_completamento) }}</template
            >
            <template v-if="r.mancanti.length"> · mancano: {{ r.mancanti.join(', ') }}</template>
          </div>
          <ModuliIscrizione :id="r.id" @cambiata="carica" @aggiorna="carica" />
        </template>

        <form
          v-if="aperta?.id === r.id"
          class="d-flex flex-wrap align-items-end gap-3 mt-3"
          @submit.prevent="decidi(r)"
        >
          <div v-if="aperta.azione === 'approva'">
            <label class="form-label small" :for="`scadenza-${r.id}`">
              Dati e moduli da completare entro
            </label>
            <input
              :id="`scadenza-${r.id}`"
              v-model="scadenza"
              type="date"
              class="form-control form-control-sm"
              :min="oggi"
              required
            />
          </div>
          <div v-else class="flex-grow-1">
            <label class="form-label small" :for="`motivo-${r.id}`">
              Perché non la accogli? Lo legge chi ha chiesto.
            </label>
            <input
              :id="`motivo-${r.id}`"
              v-model="motivo"
              class="form-control form-control-sm"
              required
            />
          </div>
          <button
            type="submit"
            class="btn btn-sm btn-solid"
            :class="aperta.azione === 'approva' ? 'theme-primary' : 'theme-danger'"
            :disabled="inCorso"
          >
            {{ aperta.azione === 'approva' ? 'Accogli' : 'Non accogliere' }}
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="aperta = null">Annulla</button>
        </form>
        <div v-else-if="r.stato === 'IN_ATTESA'" class="d-flex gap-3 mt-3">
          <button
            type="button"
            class="btn btn-sm btn-solid theme-primary"
            @click="apri(r.id, 'approva')"
          >
            Accogli…
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="apri(r.id, 'rifiuta')">
            Non accogliere…
          </button>
        </div>
      </li>
    </ul>
  </section>
</template>
