<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import Icona from '@/components/Icona.vue'
import type { Voce } from '@/navigazione/menu'

// The cards of one group of the Home (DEC-241). The entries of one unit served are one
// card titled with the unit, its pages as links inside (DEC-303).
const props = defineProps<{ voci: Voce[] }>()

type Blocco = { voce: Voce } | { sezione: string; voci: Voce[] }

const blocchi = computed<Blocco[]>(() => {
  const fuori: Blocco[] = []
  for (const v of props.voci) {
    const ultimo = fuori[fuori.length - 1]
    if (v.sezione && ultimo && 'sezione' in ultimo && ultimo.sezione === v.sezione) {
      ultimo.voci.push(v)
    } else if (v.sezione) {
      fuori.push({ sezione: v.sezione, voci: [v] })
    } else {
      fuori.push({ voce: v })
    }
  }
  return fuori
})

const chiave = (v: Voce) => `${v.nome}-${JSON.stringify(v.to)}`
</script>

<template>
  <div class="row g-5">
    <div
      v-for="b in blocchi"
      :key="'sezione' in b ? `sezione-${b.sezione}` : chiave(b.voce)"
      class="col-12 md:col-6"
    >
      <div v-if="'sezione' in b" class="card card-body h-100">
        <strong class="d-flex align-items-center gap-3 mb-1">
          <Icona :nome="b.voci[0]!.icona" />
          {{ b.sezione }}
        </strong>
        <nav class="d-flex flex-wrap column-gap-5 row-gap-1" :aria-label="b.sezione">
          <RouterLink v-for="v in b.voci" :key="chiave(v)" :to="v.to">
            {{ v.nomeInSezione ?? v.nome }}
          </RouterLink>
        </nav>
      </div>
      <a
        v-else-if="b.voce.esterna"
        :href="String(b.voce.to)"
        target="_blank"
        rel="noopener"
        class="card card-body h-100 text-decoration-none"
      >
        <strong class="d-flex align-items-center gap-3">
          <Icona :nome="b.voce.icona" />
          {{ b.voce.nome }}
        </strong>
        <span v-if="b.voce.descrizione" class="fg-2 small">{{ b.voce.descrizione }}</span>
      </a>
      <RouterLink v-else :to="b.voce.to" class="card card-body h-100 text-decoration-none">
        <strong class="d-flex align-items-center gap-3">
          <Icona :nome="b.voce.icona" />
          {{ b.voce.nome }}
          <span v-if="b.voce.contatore" class="badge theme-warning">{{ b.voce.contatore }}</span>
        </strong>
        <span v-if="b.voce.descrizione" class="fg-2 small">{{ b.voce.descrizione }}</span>
      </RouterLink>
    </div>
  </div>
</template>
