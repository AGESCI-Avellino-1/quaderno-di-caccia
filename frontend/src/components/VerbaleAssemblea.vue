<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, type DatiVerbaleAssemblea, type VerbaleModello } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The assembly's minutes from the AGESCI template (DEC-338): only data, the text comes out of
// them. For and against, or unanimity without numbers. The result of the budget is typed: the
// one in the app is a draft, the real one comes from the association's own app.
const props = defineProps<{ evento: number }>()
const emit = defineEmits<{ salvato: [] }>()
const { errore, inCorso, esegui } = useErrore()
const modello = ref<VerbaleModello | null>(null)
const dati = ref<DatiVerbaleAssemblea | null>(null)
const salvato = ref(false)

function mostra(ricevuto: VerbaleModello) {
  modello.value = ricevuto
  dati.value = ricevuto.dati
  for (const punto of Object.keys(ricevuto.delibere)) {
    dati.value.voti[punto] ??= { unanimita: false, favorevoli: null, contrari: null }
  }
}

onMounted(async () => {
  const ricevuto = await esegui(() => api.verbaleModello(props.evento))
  if (ricevuto) mostra(ricevuto)
})

async function salva() {
  if (!dati.value) return
  salvato.value = false
  const corpo = dati.value
  const ricevuto = await esegui(() => api.salvaVerbaleModello(props.evento, corpo))
  if (!ricevuto) return
  mostra(ricevuto)
  salvato.value = true
  emit('salvato')
}
</script>

<template>
  <div v-if="modello && dati" class="mb-3">
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <form class="mb-3" @submit.prevent="salva">
      <div class="row g-3 mb-3">
        <div class="col-12 sm:col-6">
          <label class="form-label small" :for="`apertura-${evento}`">Ora di apertura</label>
          <input
            :id="`apertura-${evento}`"
            v-model="dati.ora_apertura"
            type="time"
            class="form-control form-control-sm"
          />
        </div>
        <div class="col-12 sm:col-6">
          <label class="form-label small" :for="`chiusura-${evento}`">Ora di chiusura</label>
          <input
            :id="`chiusura-${evento}`"
            v-model="dati.ora_chiusura"
            type="time"
            class="form-control form-control-sm"
          />
        </div>
      </div>

      <fieldset class="mb-3">
        <legend class="form-label small">Scrutatori</legend>
        <p v-if="!modello.candidati_scrutatori.length" class="small fg-2 mb-1">
          Si scelgono tra i presenti: segna prima le presenze.
        </p>
        <div v-for="p in modello.candidati_scrutatori" :key="p.id" class="form-field mb-1">
          <input
            :id="`scrutatore-${evento}-${p.id}`"
            v-model="dati.scrutatori"
            type="checkbox"
            class="check"
            :value="p.id"
          />
          <label :for="`scrutatore-${evento}-${p.id}`">{{ p.cognome }} {{ p.nome }}</label>
        </div>
      </fieldset>

      <fieldset v-for="(nome, punto) in modello.delibere" :key="punto" class="mb-3">
        <legend class="form-label small">Voti: {{ nome }}</legend>
        <div class="form-field mb-1">
          <input
            :id="`unanimita-${evento}-${punto}`"
            v-model="dati.voti[punto]!.unanimita"
            type="checkbox"
            class="check"
          />
          <label :for="`unanimita-${evento}-${punto}`">All'unanimità</label>
        </div>
        <div v-if="!dati.voti[punto]!.unanimita" class="row g-3">
          <div class="col-6">
            <label class="form-label small" :for="`favorevoli-${evento}-${punto}`">
              Favorevoli
            </label>
            <input
              :id="`favorevoli-${evento}-${punto}`"
              v-model.number="dati.voti[punto]!.favorevoli"
              type="number"
              min="0"
              class="form-control form-control-sm"
            />
          </div>
          <div class="col-6">
            <label class="form-label small" :for="`contrari-${evento}-${punto}`">Contrari</label>
            <input
              :id="`contrari-${evento}-${punto}`"
              v-model.number="dati.voti[punto]!.contrari"
              type="number"
              min="0"
              class="form-control form-control-sm"
            />
          </div>
        </div>
      </fieldset>

      <template v-if="modello.punti.includes('BILANCIO')">
        <div class="mb-3">
          <label class="form-label small" :for="`risultato-${evento}`">
            Risultato di bilancio in euro (dal Modello D dell'associazione)
          </label>
          <input
            :id="`risultato-${evento}`"
            v-model="dati.risultato"
            inputmode="decimal"
            class="form-control form-control-sm"
            placeholder="150.50"
          />
        </div>
        <div class="form-field mb-3">
          <input
            :id="`bilancio-separato-${evento}`"
            v-model="dati.bilancio_separato"
            type="checkbox"
            class="check"
          />
          <label :for="`bilancio-separato-${evento}`">
            Produci anche il verbale separato del bilancio
          </label>
        </div>
      </template>

      <template v-if="modello.punti.includes('QUOTA')">
        <div class="row g-3 mb-3">
          <div class="col-12 sm:col-6">
            <label class="form-label small" :for="`quota-${evento}`">Quota di gruppo in euro</label>
            <input
              :id="`quota-${evento}`"
              v-model="dati.quota_gruppo"
              inputmode="decimal"
              class="form-control form-control-sm"
            />
          </div>
          <div class="col-12 sm:col-6">
            <label class="form-label small" :for="`totale-${evento}`">
              Totale delle quote in euro
            </label>
            <input
              :id="`totale-${evento}`"
              v-model="dati.quota_totale"
              inputmode="decimal"
              class="form-control form-control-sm"
            />
          </div>
        </div>
        <div class="mb-3">
          <label class="form-label small" :for="`modalita-${evento}`">
            Modalità e termini per pagarle
          </label>
          <input
            :id="`modalita-${evento}`"
            v-model="dati.quota_modalita"
            class="form-control form-control-sm"
            placeholder="entro il 30 novembre, con bonifico sul conto del Gruppo"
          />
        </div>
      </template>

      <div v-if="modello.punti.includes('VARIE')" class="mb-3">
        <label class="form-label small" :for="`varie-${evento}`">Varie ed eventuali</label>
        <textarea
          :id="`varie-${evento}`"
          v-model="dati.varie"
          class="form-control form-control-sm"
          rows="3"
        ></textarea>
      </div>

      <div class="d-flex flex-wrap align-items-center gap-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Salva i dati
        </button>
        <span v-if="salvato" class="small fg-2" role="status">Salvato.</span>
      </div>
    </form>

    <div v-if="modello.mancanti.length" class="alert theme-warning small" role="status">
      <div>Per renderlo definitivo manca: {{ modello.mancanti.join('; ') }}.</div>
    </div>
    <details class="mb-3">
      <summary>Anteprima del verbale</summary>
      <!-- eslint-disable-next-line vue/no-v-html -- built by the server from escaped data -->
      <div class="mt-3" v-html="modello.testo"></div>
    </details>
  </div>
</template>
