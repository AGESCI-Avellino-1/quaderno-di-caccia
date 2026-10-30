<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { api, euro, ricevutaPdf, type MieQuote, type Quota } from '@/api/qdc'
import CopiaLocale from '@/components/CopiaLocale.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'

// The family's fees (DEC-16): own and children's (an adult child's while still linked,
// DEC-26), with discount and agevolazione, the payments and their receipts, and where to
// pay (DEC-83: never inside the app). Cached for offline reading.
const { errore, inCorso, esegui } = useErrore()
const dati = ref<MieQuote | null>(null)
const copiaDel = ref<string | null>(null)

onMounted(async () => {
  const letto = await esegui(() => leggiConCache('mie-quote', () => api.mieQuote()))
  if (!letto) return
  dati.value = letto.dati
  copiaDel.value = letto.copiaDel
})

const perPersona = computed(() => {
  const gruppi = new Map<number, { nome: string; quote: Quota[] }>()
  for (const q of dati.value?.quote ?? []) {
    if (!gruppi.has(q.persona_id)) gruppi.set(q.persona_id, { nome: q.persona, quote: [] })
    gruppi.get(q.persona_id)!.quote.push(q)
  }
  return [...gruppi.values()]
})
const daPagare = computed(() =>
  (dati.value?.quote ?? []).reduce((somma, q) => somma + Number(q.residuo), 0),
)
const oggi = new Date().toLocaleDateString('sv')
const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
</script>

<template>
  <section>
    <div class="d-flex flex-wrap align-items-baseline gap-3 mb-5">
      <h1 class="h4 mb-0">Le mie quote</h1>
      <CopiaLocale :del="copiaDel" />
    </div>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <template v-if="dati">
      <p v-if="!dati.quote.length && !inCorso" class="fg-2">Nessuna quota per quest'anno.</p>
      <div v-else class="card card-body mb-5">
        <div class="d-flex flex-wrap align-items-center gap-3">
          <span v-if="daPagare > 0"
            >Da pagare: <strong>{{ euro(daPagare) }}</strong></span
          >
          <span v-else class="badge theme-success">Tutto pagato</span>
          <a
            v-if="dati.link_pagamento && daPagare > 0"
            :href="dati.link_pagamento"
            target="_blank"
            rel="noopener noreferrer"
            class="btn btn-sm btn-solid theme-primary"
          >
            Paga online
          </a>
        </div>
        <p class="form-text mb-0">
          Si paga ai capi, con bonifico o al link indicato dal gruppo: l'app registra il pagamento e
          ti manda la ricevuta per email.
        </p>
      </div>

      <section v-for="p in perPersona" :key="p.nome" class="mb-5">
        <h2 class="h5">{{ p.nome }}</h2>
        <ul class="list-group">
          <li v-for="q in p.quote" :key="q.id" class="list-group-item">
            <div class="d-flex flex-wrap justify-content-between gap-3">
              <span>
                {{ q.descrizione }}
                <span v-if="q.arretrata" class="badge theme-warning ms-1">anno precedente</span>
              </span>
              <strong v-if="Number(q.residuo) > 0">{{ euro(q.residuo) }}</strong>
              <span v-else class="badge theme-success">Pagata</span>
            </div>
            <div class="small fg-2">
              Entro il
              <span :class="{ 'fg-danger': Number(q.residuo) > 0 && q.scadenza < oggi }">{{
                data(q.scadenza)
              }}</span>
              · quota {{ euro(q.importo) }}
              <template v-if="Number(q.sconto)"> · sconto famiglia {{ euro(q.sconto) }}</template>
              <template v-if="q.agevolazione">
                · coperto dal gruppo {{ euro(q.agevolazione.importo) }}</template
              >
              <template v-if="Number(q.pagato)"> · già pagato {{ euro(q.pagato) }}</template>
            </div>
          </li>
        </ul>
      </section>

      <section v-if="dati.pagamenti.length">
        <h2 class="h5">Ricevute</h2>
        <ul class="list-group">
          <li v-for="pg in dati.pagamenti" :key="pg.id" class="list-group-item">
            <div class="d-flex flex-wrap align-items-baseline gap-3">
              <strong :class="{ 'text-decoration-line-through': pg.annullato }"
                >N. {{ pg.numero }}</strong
              >
              <span>{{ data(pg.data) }} · {{ euro(pg.importo) }} · {{ pg.metodo_nome }}</span>
              <a :href="ricevutaPdf(pg.id)" class="small">Scarica</a>
            </div>
            <div v-for="r in pg.righe" :key="r.quota_id" class="small fg-2">
              {{ r.persona }} · {{ r.descrizione }}: {{ euro(r.importo) }}
            </div>
            <div v-if="pg.annullato" class="small">Annullata: {{ pg.motivo_annullamento }}</div>
          </li>
        </ul>
      </section>
    </template>
  </section>
</template>
