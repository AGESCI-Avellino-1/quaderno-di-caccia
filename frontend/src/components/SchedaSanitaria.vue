<script setup lang="ts">
// Medicines, allergies and intolerances (DEC-48 core). Severe allergies come first and
// stand out: at camp this is read in a hurry.
import { computed } from 'vue'

import type { Sanitarie } from '@/api/qdc'

const props = defineProps<{ dati: Sanitarie; compatta?: boolean }>()

const ordineGravita = { GRAVE: 0, MODERATA: 1, LIEVE: 2 } as const
const allergie = computed(() =>
  [...props.dati.allergie].sort((a, b) => ordineGravita[a.gravita] - ordineGravita[b.gravita]),
)
const etichettaGravita = { GRAVE: 'Grave', MODERATA: 'Moderata', LIEVE: 'Lieve' } as const
const classeGravita = {
  GRAVE: 'text-bg-danger',
  MODERATA: 'text-bg-warning',
  LIEVE: 'text-bg-secondary',
} as const
</script>

<template>
  <div>
    <p v-if="!dati.compilate" class="text-body-secondary small mb-0">
      Farmaci e allergie non ancora compilati.
    </p>
    <template v-else>
      <h3 v-if="!compatta" class="h6 mt-2">Allergie e intolleranze</h3>
      <p v-if="dati.nessuna_allergia" class="small mb-1">Nessuna allergia o intolleranza.</p>
      <ul v-else-if="allergie.length" class="list-unstyled mb-2">
        <li v-for="(a, i) in allergie" :key="i" class="mb-1">
          <span class="badge me-1" :class="classeGravita[a.gravita]">{{
            etichettaGravita[a.gravita]
          }}</span>
          <strong>{{ a.sostanza }}</strong>
          <span class="text-body-secondary small">
            ({{ a.tipo === 'ALLERGIA' ? 'allergia' : 'intolleranza' }})</span
          >
          <div v-if="a.reazione" class="small">Reazione: {{ a.reazione }}</div>
          <div v-if="a.cosa_fare" class="small fw-semibold">Cosa fare: {{ a.cosa_fare }}</div>
        </li>
      </ul>
      <p v-else class="small text-body-secondary mb-1">Allergie non indicate.</p>

      <h3 v-if="!compatta" class="h6 mt-2">Farmaci</h3>
      <p v-if="dati.nessun_farmaco" class="small mb-1">Nessun farmaco.</p>
      <ul v-else-if="dati.farmaci.length" class="list-unstyled mb-1">
        <li v-for="(f, i) in dati.farmaci" :key="i" class="mb-1">
          <strong>{{ f.nome }}</strong> — {{ f.posologia }}
          <span v-if="f.orari" class="small">({{ f.orari }})</span>
          <span class="badge text-bg-light border ms-1">{{
            f.autonomo ? 'lo prende da solo' : 'glielo dà un capo'
          }}</span>
          <div v-if="f.note" class="small">{{ f.note }}</div>
        </li>
      </ul>
      <p v-else class="small text-body-secondary mb-1">Farmaci non indicati.</p>

      <p v-if="!compatta && dati.aggiornate_il" class="small text-body-secondary mb-0">
        Aggiornate il {{ new Date(dati.aggiornate_il).toLocaleDateString('it-IT') }}
        <template v-if="dati.inserite_da"> · {{ dati.inserite_da }}</template>
      </p>
    </template>
  </div>
</template>
