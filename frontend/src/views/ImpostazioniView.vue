<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { api, type Impostazioni, type Sito } from '@/api/qdc'
import IntestazioneGruppo from '@/components/IntestazioneGruppo.vue'
import LinkPagamento from '@/components/LinkPagamento.vue'
import { useErrore } from '@/composables/useErrore'
import { riempi, SEGNAPOSTO_TITOLO } from '@/sito/segnaposto'
import { useSitoStore } from '@/stores/sito'

// One page for the installation's settings (DEC-248); each section only for who may
// change it (the API decides).
const { errore, inCorso, esegui } = useErrore()
const sito = useSitoStore()
const dati = ref<Impostazioni | null>(null)
const esito = ref('')

onMounted(async () => {
  dati.value = (await esegui(() => api.impostazioni())) ?? null
})

// The titles as they will look, with the values being typed.
const anteprima = computed<Sito | null>(() =>
  dati.value
    ? {
        ...sito.sito,
        nome_sito: dati.value.nome_sito,
        sigla_sito: dati.value.sigla_sito,
        gruppo: dati.value.nome_gruppo || dati.value.gruppo_predefinito,
        sigla_gruppo: dati.value.sigla_gruppo,
      }
    : null,
)
const esempio = (testo: string) => (anteprima.value ? riempi(testo, anteprima.value, 'Eventi') : '')

async function salva() {
  if (!dati.value) return
  esito.value = ''
  const nuovi = await esegui(() => api.salvaImpostazioniSito(dati.value!))
  if (!nuovi) return
  dati.value = nuovi
  esito.value = 'Impostazioni salvate.'
  await sito.carica()
}
</script>

<template>
  <section>
    <h1 class="h4 mb-5">Impostazioni</h1>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <template v-if="dati">
      <section v-if="dati.puo_modificare" class="mb-7">
        <h2 class="h5">Nome e titolo del sito</h2>
        <p class="small fg-2">
          Questi nomi servono solo per il titolo e il piè di pagina: i dati ufficiali del gruppo per
          le stampe sono più sotto. L'app installata sul telefono si chiama sempre Quaderno di
          Caccia.
        </p>
        <div v-if="esito" class="alert theme-success small" role="status">
          <div>{{ esito }}</div>
        </div>
        <form class="card card-body" @submit.prevent="salva">
          <div class="row g-3">
            <div class="col-12 md:col-6">
              <label class="form-label small mb-0" for="imp-nome-sito">Nome del sito</label>
              <input
                id="imp-nome-sito"
                v-model="dati.nome_sito"
                class="form-control form-control-sm"
                required
              />
            </div>
            <div class="col-12 md:col-6">
              <label class="form-label small mb-0" for="imp-sigla-sito">Sigla del sito</label>
              <input
                id="imp-sigla-sito"
                v-model="dati.sigla_sito"
                class="form-control form-control-sm"
                placeholder="QdC"
              />
            </div>
            <div class="col-12 md:col-6">
              <label class="form-label small mb-0" for="imp-nome-gruppo">Nome del gruppo</label>
              <input
                id="imp-nome-gruppo"
                v-model="dati.nome_gruppo"
                class="form-control form-control-sm"
                :placeholder="dati.gruppo_predefinito"
              />
              <div class="form-text">Se lo lasci vuoto: {{ dati.gruppo_predefinito }}</div>
            </div>
            <div class="col-12 md:col-6">
              <label class="form-label small mb-0" for="imp-sigla-gruppo">Sigla del gruppo</label>
              <input
                id="imp-sigla-gruppo"
                v-model="dati.sigla_gruppo"
                class="form-control form-control-sm"
                placeholder="AV1"
              />
              <div class="form-text">Se la lasci vuota si usa il nome del gruppo.</div>
            </div>
            <div class="col-12">
              <label class="form-label small mb-0" for="imp-titolo">
                Titolo completo, nella barra in alto
              </label>
              <input
                id="imp-titolo"
                v-model="dati.titolo_completo"
                class="form-control form-control-sm"
                required
              />
              <div class="form-text">Diventa: {{ esempio(dati.titolo_completo) }}</div>
            </div>
            <div class="col-12">
              <label class="form-label small mb-0" for="imp-titolo-breve">
                Titolo breve, nella scheda del browser
              </label>
              <input
                id="imp-titolo-breve"
                v-model="dati.titolo_breve"
                class="form-control form-control-sm"
                required
              />
              <div class="form-text">Diventa: {{ esempio(dati.titolo_breve) }}</div>
            </div>
            <div class="col-12">
              <label class="form-label small mb-0" for="imp-piede">
                Riga del piè di pagina (facoltativa)
              </label>
              <input
                id="imp-piede"
                v-model="dati.riga_piede"
                class="form-control form-control-sm"
              />
              <div class="form-text">
                Compare sopra la riga fissa «Sviluppato da Andrea Bruno e distribuito con licenza
                MIT».
                <template v-if="dati.riga_piede">Diventa: {{ esempio(dati.riga_piede) }}</template>
              </div>
            </div>
          </div>
          <details class="small mt-3">
            <summary>Cosa puoi scrivere tra parentesi quadre</summary>
            <ul class="mb-0 mt-1">
              <li v-for="[nome, spiegazione] in SEGNAPOSTO_TITOLO" :key="nome">
                <code>[{{ nome }}]</code>: {{ spiegazione }}
              </li>
            </ul>
          </details>
          <div class="mt-3">
            <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
              Salva
            </button>
          </div>
        </form>
      </section>
      <IntestazioneGruppo v-if="dati.puo_modificare_intestazione" />
      <LinkPagamento v-if="dati.puo_modificare_pagamenti" />
    </template>
  </section>
</template>
