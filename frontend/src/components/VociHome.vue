<script setup lang="ts">
import { RouterLink } from 'vue-router'

import Icona from '@/components/Icona.vue'
import type { Voce } from '@/navigazione/menu'

// The cards of one group of the Home (DEC-241).
defineProps<{ voci: Voce[] }>()
</script>

<template>
  <div class="row g-5">
    <div v-for="v in voci" :key="`${v.nome}-${JSON.stringify(v.to)}`" class="col-12 md:col-6">
      <a
        v-if="v.esterna"
        :href="String(v.to)"
        target="_blank"
        rel="noopener"
        class="card card-body h-100 text-decoration-none"
      >
        <strong class="d-flex align-items-center gap-3">
          <Icona :nome="v.icona" />
          {{ v.nome }}
        </strong>
        <span v-if="v.descrizione" class="fg-2 small">{{ v.descrizione }}</span>
      </a>
      <RouterLink v-else :to="v.to" class="card card-body h-100 text-decoration-none">
        <strong class="d-flex align-items-center gap-3">
          <Icona :nome="v.icona" />
          {{ v.nome }}
          <span v-if="v.contatore" class="badge theme-warning">{{ v.contatore }}</span>
        </strong>
        <span v-if="v.descrizione" class="fg-2 small">{{ v.descrizione }}</span>
      </RouterLink>
    </div>
  </div>
</template>
