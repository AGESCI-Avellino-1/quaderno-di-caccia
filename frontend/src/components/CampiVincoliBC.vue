<script setup lang="ts">
import { useId } from 'vue'

import { BRANCHE_VINCOLO, type BrancaVincolo, type VincoliBC } from '@/api/qdc'

// Who may register to a BuonaCaccia event (DEC-398): branches, age in full years on the first
// day, minimum training level; the two maximums only warn. Empty = no limit. Used for a type's
// defaults and for one event.
const vincoli = defineModel<VincoliBC>({ required: true })
const id = useId()

function branca(b: BrancaVincolo, scelta: boolean) {
  const altre = vincoli.value.branche.filter((x) => x !== b)
  vincoli.value.branche = scelta ? [...altre, b] : altre
}

const NUMERI = [
  ['eta_minima', 'Età minima', 'anni alla partenza'],
  ['eta_massima', 'Età massima', 'anni alla partenza'],
  ['livello_minimo', 'Livello Fo.Ca. minimo', 'per i capi'],
  ['massimo_per_unita', 'Massimo per unità', 'solo un avviso'],
  ['massimo_per_gruppo', 'Massimo per gruppo', 'solo un avviso'],
] as const

function numero(campo: (typeof NUMERI)[number][0], valore: string) {
  vincoli.value[campo] = valore === '' ? null : Number(valore)
}
</script>

<template>
  <fieldset class="row g-3">
    <legend class="small mb-0">
      Chi può iscriversi <span class="fg-2">(vuoto: nessun limite)</span>
    </legend>
    <div class="col-12 d-flex flex-wrap gap-3">
      <div v-for="[valore, nome] in BRANCHE_VINCOLO" :key="valore" class="form-field">
        <input
          :id="`${id}-${valore}`"
          type="checkbox"
          class="check"
          :checked="vincoli.branche.includes(valore)"
          @change="branca(valore, ($event.target as HTMLInputElement).checked)"
        />
        <label class="small" :for="`${id}-${valore}`">{{ nome }}</label>
      </div>
    </div>
    <div v-for="[campo, nome, nota] in NUMERI" :key="campo" class="col-6 md:col-4">
      <label class="form-label small" :for="`${id}-${campo}`">
        {{ nome }} <span class="fg-2">({{ nota }})</span>
      </label>
      <input
        :id="`${id}-${campo}`"
        type="number"
        min="0"
        max="99"
        class="form-control form-control-sm"
        :value="vincoli[campo] ?? ''"
        @input="numero(campo, ($event.target as HTMLInputElement).value)"
      />
    </div>
  </fieldset>
</template>
