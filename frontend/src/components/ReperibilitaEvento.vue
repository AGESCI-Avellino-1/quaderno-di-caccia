<script setup lang="ts">
import { reactive, ref } from 'vue'

import { api } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The emergency contact for this camp or outing only, instead of the yearly one
// (DEC-53): the medical forms printed for the event use it. Written by the parents or
// the adult member; online only.
const props = defineProps<{ evento: number; persona: number }>()
const { errore, inCorso, esegui } = useErrore()
const aperta = ref(false)
const attuale = ref<{ nome: string; telefono: string } | null>(null)
const modulo = reactive({ nome: '', telefono: '' })

async function apri() {
  const letto = await esegui(() => api.reperibilitaEvento(props.evento, props.persona))
  if (letto === undefined) return
  attuale.value = letto
  modulo.nome = letto?.nome ?? ''
  modulo.telefono = letto?.telefono ?? ''
  aperta.value = true
}

async function salva(togli = false) {
  const nuovo = await esegui(() =>
    api.salvaReperibilitaEvento(
      props.evento,
      props.persona,
      togli ? '' : modulo.nome,
      togli ? '' : modulo.telefono,
    ),
  )
  if (nuovo === undefined) return
  attuale.value = nuovo
  aperta.value = false
}
</script>

<template>
  <div class="mt-1">
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <p v-if="attuale && !aperta" class="small mb-0">
      In caso di emergenza per questo evento: <strong>{{ attuale.nome }}</strong>
      {{ attuale.telefono }}
    </p>
    <button v-if="!aperta" type="button" class="btn btn-sm btn-link px-0" @click="apri">
      Un altro recapito per le emergenze, solo per questo evento…
    </button>
    <form v-else class="d-flex flex-wrap align-items-end gap-3" @submit.prevent="salva()">
      <div class="flex-grow-1">
        <label class="form-label small" :for="`rep-n-${persona}`">Chi chiamare</label>
        <input
          :id="`rep-n-${persona}`"
          v-model="modulo.nome"
          class="form-control form-control-sm"
          maxlength="120"
          required
        />
      </div>
      <div>
        <label class="form-label small" :for="`rep-t-${persona}`">Telefono</label>
        <input
          :id="`rep-t-${persona}`"
          v-model="modulo.telefono"
          type="tel"
          class="form-control form-control-sm"
          maxlength="30"
          required
        />
      </div>
      <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
        Salva
      </button>
      <button
        v-if="attuale"
        type="button"
        class="btn btn-sm btn-link"
        :disabled="inCorso"
        @click="salva(true)"
      >
        Torna a quello di sempre
      </button>
      <button type="button" class="btn btn-sm btn-link" @click="aperta = false">Annulla</button>
    </form>
  </div>
</template>
