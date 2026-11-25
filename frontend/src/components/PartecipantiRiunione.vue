<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { api, type DettaglioEvento } from '@/api/qdc'
import { opzioniDa, type Opzione } from '@/components/sceltaDaElenco'
import SceltaPersone from '@/components/SceltaPersone.vue'
import { useErrore } from '@/composables/useErrore'

// Who is invited to a meeting of people chosen one by one (DEC-430): added and taken away by
// who manages it, with an email to the new ones if wanted (DEC-431). Online only.
const props = defineProps<{ riunione: DettaglioEvento }>()
const emit = defineEmits<{ salvati: [dati: DettaglioEvento]; chiusa: [] }>()
const { errore, inCorso, esegui } = useErrore()
const possibili = ref<Opzione[]>([])
const scelti = ref(props.riunione.partecipanti.map((p) => p.persona_id))
const avvisa = ref(true)

// Who is invited already stays in the list, also if this user could not choose them.
const opzioni = computed(() => {
  const ids = new Set(possibili.value.map((o) => o.id))
  const altri = props.riunione.partecipanti
    .filter((p) => !ids.has(p.persona_id))
    .map((p) => ({ id: p.persona_id, nome: `${p.cognome} ${p.nome}` }))
  return [...possibili.value, ...altri]
})

onMounted(async () => {
  possibili.value = opzioniDa((await esegui(() => api.personeSelezionabili())) ?? [])
})

async function salva() {
  const dati = await esegui(() =>
    api.scegliPartecipanti(props.riunione.id, {
      persone: scelti.value,
      avvisa: avvisa.value,
    }),
  )
  if (dati) emit('salvati', dati)
}
</script>

<template>
  <form class="card card-body mb-5" @submit.prevent="salva">
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <SceltaPersone id="partecipanti" v-model="scelti" :opzioni="opzioni" />
    <div class="form-field mt-3 mb-0">
      <input id="partecipanti-avvisa" v-model="avvisa" type="checkbox" class="check" />
      <label for="partecipanti-avvisa">Avvisa chi aggiungi</label>
    </div>
    <p class="form-text mb-0">Chi togli non vede più la riunione e non riceve email.</p>
    <div class="d-flex gap-3 mt-3">
      <button
        type="submit"
        class="btn btn-sm btn-solid theme-primary"
        :disabled="inCorso || !scelti.length"
      >
        Salva
      </button>
      <button type="button" class="btn btn-sm btn-link" @click="emit('chiusa')">Annulla</button>
    </div>
  </form>
</template>
