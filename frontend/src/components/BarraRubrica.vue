<script setup lang="ts">
import { computed } from 'vue'

import Icona from '@/components/Icona.vue'
import type { Rubrica } from '@/composables/useRubrica'

// The bar to put phone numbers into the phone's contacts (DEC-302): the page shows a
// checkbox on each row while it is on. `tutti` are the people of the page.
const props = defineProps<{ rubrica: Rubrica; tutti: number[] }>()

const r = computed(() => props.rubrica)
const quanti = computed(() => r.value.scelti.value.size)
// A parent of two members of the patrol is there twice.
const tutti = computed(() => new Set(props.tutti))

function tuttiONessuno() {
  r.value.scelti.value = quanti.value === tutti.value.size ? new Set() : new Set(tutti.value)
}
</script>

<template>
  <div v-if="r.disponibile.value" class="mb-3">
    <button
      v-if="!r.attiva.value"
      type="button"
      class="btn btn-sm btn-outline theme-primary"
      @click="r.attiva.value = true"
    >
      <Icona nome="person-plus" /> Aggiungi alla rubrica del telefono
    </button>
    <div v-else class="card card-body">
      <p class="small mb-3">
        Spunta le persone e tocca <strong>Scarica i contatti</strong>: il telefono ti propone di
        salvarli in rubrica. Nel file ci sono nome, numeri e, come azienda, il gruppo con il ruolo o
        l'unità.
      </p>
      <div v-if="r.errore.value" class="alert theme-danger small" role="alert">
        {{ r.errore.value }}
      </div>
      <div class="d-flex flex-wrap align-items-center gap-3">
        <button
          type="button"
          class="btn btn-sm btn-solid theme-primary"
          :disabled="!quanti || r.inCorso.value"
          @click="r.scarica()"
        >
          Scarica i contatti ({{ quanti }})
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="tuttiONessuno">
          {{ quanti === tutti.size ? 'Nessuno' : 'Tutti' }}
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="r.chiudi()">Annulla</button>
      </div>
    </div>
  </div>
</template>
