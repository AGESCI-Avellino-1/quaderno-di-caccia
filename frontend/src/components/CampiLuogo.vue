<script setup lang="ts">
import type { LuogoModello } from '@/api/qdc'

// A place in pieces, as the AGESCI templates ask for it (DEC-338).
defineProps<{ id: string; conPresso?: boolean; disabled?: boolean }>()
const luogo = defineModel<LuogoModello>({ required: true })
</script>

<template>
  <div class="row g-3 mb-3">
    <div v-if="conPresso" class="col-12">
      <label class="form-label small" :for="`${id}-presso`">Presso</label>
      <input
        :id="`${id}-presso`"
        v-model="luogo.presso"
        class="form-control form-control-sm"
        :disabled="disabled"
      />
    </div>
    <div class="col-12 sm:col-8">
      <label class="form-label small" :for="`${id}-via`">Via o piazza</label>
      <input
        :id="`${id}-via`"
        v-model="luogo.via"
        class="form-control form-control-sm"
        placeholder="Via Roma"
        :disabled="disabled"
      />
    </div>
    <div class="col-12 sm:col-4">
      <label class="form-label small" :for="`${id}-civico`">Numero</label>
      <input
        :id="`${id}-civico`"
        v-model="luogo.civico"
        class="form-control form-control-sm"
        :disabled="disabled"
      />
    </div>
    <div class="col-12 sm:col-3">
      <label class="form-label small" :for="`${id}-cap`">CAP</label>
      <input
        :id="`${id}-cap`"
        v-model="luogo.cap"
        class="form-control form-control-sm"
        maxlength="5"
        :disabled="disabled"
      />
    </div>
    <div class="col-12 sm:col-6">
      <label class="form-label small" :for="`${id}-citta`">Città</label>
      <input
        :id="`${id}-citta`"
        v-model="luogo.citta"
        class="form-control form-control-sm"
        :disabled="disabled"
      />
    </div>
    <div class="col-12 sm:col-3">
      <label class="form-label small" :for="`${id}-provincia`">Provincia</label>
      <input
        :id="`${id}-provincia`"
        v-model="luogo.provincia"
        class="form-control form-control-sm"
        maxlength="2"
        :disabled="disabled"
      />
    </div>
  </div>
</template>
