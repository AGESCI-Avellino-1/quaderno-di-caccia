<script setup lang="ts">
import { computed } from 'vue'

import type { DatiAttesa } from '@/api/qdc'

// The waiting list's data (DEC-256): the child, who to contact, where they live. The
// same form for the family, for its corrections and for a capo (DEC-258).
const dati = defineModel<DatiAttesa>({ required: true })
defineProps<{ prefisso: string }>()

const maggiorenne = computed(() => {
  if (!dati.value.data_nascita) return false
  const nascita = new Date(dati.value.data_nascita)
  const diciotto = new Date(nascita.getFullYear() + 18, nascita.getMonth(), nascita.getDate())
  return diciotto <= new Date()
})
</script>

<template>
  <fieldset class="mb-5">
    <legend class="h6">Chi vuole entrare nel gruppo</legend>
    <div class="row g-3">
      <div class="col-12 md:col-6">
        <label class="form-label small mb-0" :for="`${prefisso}-nome`">Nome</label>
        <input :id="`${prefisso}-nome`" v-model="dati.nome" class="form-control" required />
      </div>
      <div class="col-12 md:col-6">
        <label class="form-label small mb-0" :for="`${prefisso}-cognome`">Cognome</label>
        <input :id="`${prefisso}-cognome`" v-model="dati.cognome" class="form-control" required />
      </div>
      <div class="col-12 md:col-4">
        <label class="form-label small mb-0" :for="`${prefisso}-sesso`">Sesso</label>
        <select :id="`${prefisso}-sesso`" v-model="dati.sesso" class="form-control" required>
          <option value="" disabled>Scegli</option>
          <option value="F">Femmina</option>
          <option value="M">Maschio</option>
        </select>
      </div>
      <div class="col-12 md:col-4">
        <label class="form-label small mb-0" :for="`${prefisso}-nascita`">Data di nascita</label>
        <input
          :id="`${prefisso}-nascita`"
          v-model="dati.data_nascita"
          type="date"
          class="form-control"
          required
        />
      </div>
      <div class="col-12 md:col-4">
        <label class="form-label small mb-0" :for="`${prefisso}-luogo`">Luogo di nascita</label>
        <input
          :id="`${prefisso}-luogo`"
          v-model="dati.luogo_nascita"
          class="form-control"
          required
        />
      </div>
    </div>
    <div v-if="maggiorenne" class="form-field mt-3">
      <input :id="`${prefisso}-da-se`" v-model="dati.da_se" class="check" type="checkbox" />
      <label :for="`${prefisso}-da-se`">Sono io: sono maggiorenne e mi iscrivo da solo</label>
    </div>
  </fieldset>

  <fieldset class="mb-5">
    <legend class="h6">{{ dati.da_se ? 'I tuoi contatti' : 'Il genitore da contattare' }}</legend>
    <div class="row g-3">
      <template v-if="!dati.da_se">
        <div class="col-12 md:col-6">
          <label class="form-label small mb-0" :for="`${prefisso}-g-nome`">Nome</label>
          <input
            :id="`${prefisso}-g-nome`"
            v-model="dati.contatto_nome"
            class="form-control"
            required
          />
        </div>
        <div class="col-12 md:col-6">
          <label class="form-label small mb-0" :for="`${prefisso}-g-cognome`">Cognome</label>
          <input
            :id="`${prefisso}-g-cognome`"
            v-model="dati.contatto_cognome"
            class="form-control"
            required
          />
        </div>
      </template>
      <div class="col-12 md:col-6">
        <label class="form-label small mb-0" :for="`${prefisso}-telefono`">Telefono</label>
        <input
          :id="`${prefisso}-telefono`"
          v-model="dati.telefono"
          type="tel"
          autocomplete="tel"
          class="form-control"
          required
        />
      </div>
      <div class="col-12 md:col-6">
        <label class="form-label small mb-0" :for="`${prefisso}-email`">Email</label>
        <input
          :id="`${prefisso}-email`"
          v-model="dati.email"
          type="email"
          autocomplete="email"
          class="form-control"
          required
        />
      </div>
    </div>
  </fieldset>

  <fieldset class="mb-5">
    <legend class="h6">Residenza</legend>
    <div class="row g-3">
      <div class="col-12">
        <label class="form-label small mb-0" :for="`${prefisso}-indirizzo`"
          >Indirizzo e numero civico</label
        >
        <input
          :id="`${prefisso}-indirizzo`"
          v-model="dati.indirizzo"
          autocomplete="street-address"
          class="form-control"
          required
        />
      </div>
      <div class="col-12 md:col-6">
        <label class="form-label small mb-0" :for="`${prefisso}-comune`">Comune</label>
        <input :id="`${prefisso}-comune`" v-model="dati.comune" class="form-control" required />
      </div>
      <div class="col-6 md:col-3">
        <label class="form-label small mb-0" :for="`${prefisso}-provincia`"
          >Provincia (sigla)</label
        >
        <input
          :id="`${prefisso}-provincia`"
          v-model="dati.provincia"
          maxlength="2"
          class="form-control"
          required
        />
      </div>
      <div class="col-6 md:col-3">
        <label class="form-label small mb-0" :for="`${prefisso}-cap`">CAP</label>
        <input
          :id="`${prefisso}-cap`"
          v-model="dati.cap"
          inputmode="numeric"
          maxlength="5"
          class="form-control"
          required
        />
      </div>
    </div>
  </fieldset>
</template>
