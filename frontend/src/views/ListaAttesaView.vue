<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'

import { api, type DatiAttesa } from '@/api/qdc'
import ModuloAttesa from '@/components/ModuloAttesa.vue'
import { useErrore } from '@/composables/useErrore'
import { useSitoStore } from '@/stores/sito'

// The public waiting list form (DEC-256): no account. The family never sees its place
// in the list, only that it is on it (DEC-257).
const { errore, inCorso, esegui } = useErrore()
const sito = useSitoStore()

const vuoti = (): DatiAttesa => ({
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
})
const dati = ref<DatiAttesa>(vuoti())
const privacy = ref(false)
const inviato = ref(false)
const emailLink = ref('')
const linkChiesto = ref(false)

async function invia() {
  const fatto = await esegui(() => api.mettitiInLista({ ...dati.value, privacy: privacy.value }))
  if (fatto === undefined && errore.value) return
  inviato.value = true
}

async function chiediLink() {
  linkChiesto.value = false
  await esegui(() => api.chiediLinkAttesa(emailLink.value))
  if (!errore.value) linkChiesto.value = true
}
</script>

<template>
  <section>
    <h1 class="h4 mb-1">Lista d'attesa</h1>
    <p class="fg-2">Per entrare in {{ sito.sito.gruppo || 'gruppo' }}.</p>

    <div v-if="inviato" class="alert theme-success" role="status">
      <div>
        <strong>Siete in lista d'attesa.</strong> Vi abbiamo mandato un'email con un link per
        correggere i dati o uscire dalla lista, e con l'anno scout da cui il ragazzo potrà essere
        contattato. I capi chiamano a inizio anno, secondo i posti nelle unità.
      </div>
    </div>

    <form v-else class="card card-body mb-7" @submit.prevent="invia">
      <p class="small">
        Un genitore mette in lista il figlio; chi è maggiorenne può mettersi in lista da solo. Non
        si sceglie l'unità: dipende dall'età. I capi chiamano a inizio anno, non secondo l'ordine di
        arrivo.
      </p>
      <ModuloAttesa v-model="dati" prefisso="lista" />
      <div class="alert theme-info small" role="note">
        <div>
          I dati servono solo per contattarvi quando ci sarà posto: li vedono i capi del gruppo.
          Potete correggerli o cancellarli quando volete dal link che vi arriva per email; dopo due
          anni vi chiediamo se volete restare in lista, e chi esce dalla lista non lascia dati.
        </div>
      </div>
      <div class="form-field">
        <input id="lista-privacy" v-model="privacy" class="check" type="checkbox" required />
        <label for="lista-privacy">
          Ho letto la
          <RouterLink to="/privacy" target="_blank">privacy policy</RouterLink> e accetto che i dati
          siano usati per la lista d'attesa
        </label>
      </div>
      <div v-if="errore" class="alert theme-danger small mt-3" role="alert">{{ errore }}</div>
      <div class="mt-3">
        <button type="submit" class="btn btn-solid theme-primary" :disabled="inCorso">
          Mettiti in lista
        </button>
      </div>
    </form>

    <section class="card card-body">
      <h2 class="h6">Sei già in lista?</h2>
      <p class="small fg-2 mb-1">
        Scrivi l'email che avete dato: se è in lista, vi rimandiamo il link per correggere i dati o
        uscire.
      </p>
      <form class="d-flex flex-wrap align-items-end gap-3" @submit.prevent="chiediLink">
        <div class="flex-grow-1">
          <label class="form-label small mb-0" for="lista-link-email">Email</label>
          <input
            id="lista-link-email"
            v-model="emailLink"
            type="email"
            autocomplete="email"
            class="form-control"
            required
          />
        </div>
        <button type="submit" class="btn btn-outline theme-primary" :disabled="inCorso">
          Mandami il link
        </button>
      </form>
      <p v-if="linkChiesto" class="small mt-3 mb-0" role="status">
        Se l'indirizzo è in lista, tra poco arriva l'email con il link.
      </p>
    </section>
  </section>
</template>
