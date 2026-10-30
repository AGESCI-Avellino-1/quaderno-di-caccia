<script setup lang="ts">
import { reactive, ref } from 'vue'

import { api, moduloSanitarioPdf, type Sanitarie } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Paper stays paper (DEC-52, DEC-54): print the AGESCI form filled in (DEC-51), and, for
// the unit staff and the capigruppo, the date it came back signed and of the
// prescription handed over (DEC-193). Online only: it is done at the desk, not at camp.
const props = defineProps<{ persona: number; dati: Sanitarie }>()
const emit = defineEmits<{ cambiata: [dati: Sanitarie] }>()
const { errore, inCorso, esegui } = useErrore()
const oggi = () => new Date().toLocaleDateString('sv')
const data = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleDateString('it-IT') : ''

const aperta = ref(false)
const modulo = reactive({ firmata_il: '', prescrizione_consegnata_il: '' })

function apri() {
  modulo.firmata_il = props.dati.firmata_il ?? oggi()
  modulo.prescrizione_consegnata_il = props.dati.prescrizione_consegnata_il ?? ''
  aperta.value = true
}

async function salva() {
  const nuovi = await esegui(() =>
    api.cartaSanitaria(props.persona, {
      firmata_il: modulo.firmata_il || null,
      prescrizione_consegnata_il: modulo.prescrizione_consegnata_il || null,
    }),
  )
  if (!nuovi) return
  aperta.value = false
  emit('cambiata', nuovi)
}
</script>

<template>
  <div class="mt-3">
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <p class="small mb-1">
      <template v-if="dati.firmata_il">
        Modulo firmato consegnato il {{ data(dati.firmata_il) }}.
      </template>
      <template v-else>Modulo firmato non ancora consegnato.</template>
      <template v-if="dati.prescrizione_consegnata_il">
        Prescrizione consegnata il {{ data(dati.prescrizione_consegnata_il) }}.
      </template>
    </p>
    <div v-if="dati.da_rifirmare" class="alert theme-warning small" role="status">
      <div>La scheda è cambiata dopo l'ultima firma: va stampata e firmata di nuovo.</div>
    </div>
    <div class="d-flex flex-wrap gap-3">
      <a :href="moduloSanitarioPdf(persona)" class="btn btn-sm btn-outline theme-primary">
        Stampa il modulo da firmare
      </a>
      <button
        v-if="dati.puo_registrare_firma && dati.compilate && !aperta"
        type="button"
        class="btn btn-sm btn-link"
        @click="apri"
      >
        Segna la consegna su carta…
      </button>
    </div>
    <form v-if="aperta" class="d-flex flex-wrap align-items-end gap-3 mt-3" @submit.prevent="salva">
      <div>
        <label class="form-label small" :for="`firma-${persona}`">Modulo firmato il</label>
        <input
          :id="`firma-${persona}`"
          v-model="modulo.firmata_il"
          type="date"
          :max="oggi()"
          class="form-control form-control-sm"
        />
      </div>
      <div>
        <label class="form-label small" :for="`prescr-${persona}`">
          Prescrizione consegnata il (se serve)
        </label>
        <input
          :id="`prescr-${persona}`"
          v-model="modulo.prescrizione_consegnata_il"
          type="date"
          :max="oggi()"
          class="form-control form-control-sm"
        />
      </div>
      <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
        Salva
      </button>
      <button type="button" class="btn btn-sm btn-link" @click="aperta = false">Annulla</button>
    </form>
  </div>
</template>
