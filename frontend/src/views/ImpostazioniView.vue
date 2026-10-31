<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { api, type Impostazioni, type ModelloEmailBreve, type Sito } from '@/api/qdc'
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

const modelli = ref<ModelloEmailBreve[]>([])

onMounted(async () => {
  dati.value = (await esegui(() => api.impostazioni())) ?? null
  if (dati.value?.puo_modificare) modelli.value = (await esegui(() => api.modelliEmail())) ?? []
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

async function emailDiProva(attiva: boolean) {
  const nuovi = await esegui(() => api.emailDiProva(attiva))
  if (!nuovi) return
  dati.value = nuovi
  await sito.carica()
}

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
      <section v-if="modelli.length" class="mb-7">
        <h2 class="h5">Modelli delle email</h2>
        <p class="small fg-2">
          Il testo di ogni email che l'app manda. Puoi cambiarlo e tornare quando vuoi al testo di
          base; quello che serve davvero (link, codici, le informazioni da mandare) deve restare.
        </p>
        <div class="list-group">
          <RouterLink
            v-for="m in modelli"
            :key="m.chiave"
            :to="{ name: 'modello-email', params: { chiave: m.chiave } }"
            class="list-group-item list-group-item-action"
          >
            <div class="d-flex flex-wrap align-items-center gap-3">
              <strong>{{ m.nome }}</strong>
              <span v-if="m.da_correggere" class="badge theme-warning">Da correggere</span>
              <span v-else-if="m.personalizzato" class="badge theme-success">Personalizzato</span>
            </div>
            <div class="small fg-2">{{ m.descrizione }}</div>
          </RouterLink>
        </div>
      </section>
      <IntestazioneGruppo v-if="dati.puo_modificare_intestazione" />
      <LinkPagamento v-if="dati.puo_modificare_pagamenti" />
      <section v-if="dati.puo_email_di_prova" class="mb-7">
        <h2 class="h5">Email di prova</h2>
        <p class="small fg-2">
          Per provare l'app senza disturbare nessuno: le email non partono e restano in Mailpit, che
          puoi aprire solo tu dal menu Amministrazione. Tutti vedono un avviso finché è attiva.
          Attenzione: in Mailpit trovi anche i codici di accesso e gli inviti degli altri.
        </p>
        <div v-if="!dati.email_di_prova_consentita" class="alert theme-info small" role="status">
          <div>
            Su questo server non è permessa: la può attivare solo chi lo installa, ed è pensata per
            un server di prova, non per quello con i dati veri.
          </div>
        </div>
        <div v-else class="card card-body">
          <div class="form-field">
            <div class="switch">
              <input
                id="imp-email-prova"
                type="checkbox"
                role="switch"
                :checked="dati.email_di_prova"
                :disabled="inCorso"
                @change="emailDiProva(($event.target as HTMLInputElement).checked)"
              />
            </div>
            <label for="imp-email-prova">Trattieni le email in Mailpit</label>
          </div>
        </div>
      </section>
    </template>
  </section>
</template>
