<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { api, euro, type QuotaEvento, type RataEvento, type SituazioneQuoteEvento } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The event's fee (DEC-77): everyone sees the instalments; the event's capi set them
// and may change one person's amount, down to zero. Online only for the changes.
const props = defineProps<{
  evento: number
  quota: QuotaEvento | null
  puoGestire: boolean
  inFamiglia: boolean
}>()
const emit = defineEmits<{ cambiata: [] }>()
const { errore, inCorso, esegui } = useErrore()
const situazione = ref<SituazioneQuoteEvento[]>([])
const modulo = reactive({
  aperto: false,
  nome: '',
  sconto_famiglia: '0',
  rate: [] as RataEvento[],
})
const modifica = reactive({ quota: 0, importo: '' })

async function caricaSituazione() {
  if (!props.puoGestire || !props.quota) {
    situazione.value = []
    return
  }
  situazione.value = (await esegui(() => api.quoteEvento(props.evento))) ?? []
}
watch(() => [props.evento, props.quota], caricaSituazione, { immediate: true })

function apri() {
  Object.assign(modulo, {
    aperto: true,
    nome: props.quota?.nome ?? '',
    sconto_famiglia: props.quota?.sconto_famiglia ?? '0',
    rate: props.quota
      ? props.quota.rate.map((r) => ({ ...r }))
      : [{ descrizione: '', importo: '', scadenza: '' }],
  })
}

const totale = computed(() => modulo.rate.reduce((s, r) => s + (Number(r.importo) || 0), 0))

async function salva() {
  const dati = {
    nome: modulo.nome,
    sconto_famiglia: Number(modulo.sconto_famiglia || 0).toFixed(2),
    rate: modulo.rate.map((r) => ({ ...r, importo: Number(r.importo).toFixed(2) })),
  }
  if (!(await esegui(() => api.fissaQuotaEvento(props.evento, dati)))) return
  modulo.aperto = false
  emit('cambiata')
}

async function salvaImporto() {
  const fatto = await esegui(() =>
    api.importoPartecipante(props.evento, modifica.quota, Number(modifica.importo).toFixed(2)),
  )
  if (!fatto) return
  modifica.quota = 0
  await caricaSituazione()
}

const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
const pagate = (r: SituazioneQuoteEvento) =>
  r.quote.filter((q) => !q.annullata).every((q) => Number(q.residuo) <= 0)
</script>

<template>
  <section v-if="quota || puoGestire" class="card card-body mb-5">
    <h2 class="h5">Quota</h2>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <template v-if="quota">
      <p class="mb-1">
        <strong>{{ quota.nome }}</strong
        >: {{ euro(quota.totale) }}
        <template v-if="Number(quota.sconto_famiglia)">
          (sconto famiglia {{ euro(quota.sconto_famiglia) }} sul saldo)</template
        >
      </p>
      <ul v-if="quota.rate.length > 1" class="list-unstyled small mb-1">
        <li v-for="r in quota.rate" :key="r.scadenza">
          {{ r.descrizione || 'Rata' }}: {{ euro(r.importo) }} entro il {{ data(r.scadenza) }}
        </li>
      </ul>
      <p v-else class="small mb-1">Entro il {{ data(quota.rate[0]!.scadenza) }}</p>
      <p v-if="inFamiglia" class="small mb-0">
        Le trovi, con quello che resta da pagare, in
        <RouterLink :to="{ name: 'mie-quote' }">Le mie quote</RouterLink>.
      </p>
    </template>
    <p v-else class="fg-2 small">Nessuna quota per questo evento.</p>

    <template v-if="puoGestire">
      <button
        v-if="!modulo.aperto"
        type="button"
        class="btn btn-sm btn-outline theme-primary align-self-start mt-3"
        @click="apri"
      >
        {{ quota ? 'Cambia la quota' : 'Fissa una quota' }}
      </button>
      <form v-else class="border rounded p-5 mt-3" @submit.prevent="salva">
        <p class="form-text">
          Arriva a tutti i partecipanti, rata per rata; chi non partecipa non la paga. Le quote già
          emesse non cambiano importo: si correggono persona per persona.
        </p>
        <div class="row g-3 mb-3">
          <div class="md:col-8">
            <label class="form-label small" for="quota-nome">Nome</label>
            <input
              id="quota-nome"
              v-model="modulo.nome"
              class="form-control form-control-sm"
              placeholder="Es. Campo estivo"
            />
          </div>
          <div class="md:col-4">
            <label class="form-label small" for="quota-sconto">Sconto famiglia sul saldo (€)</label>
            <input
              id="quota-sconto"
              v-model="modulo.sconto_famiglia"
              type="number"
              min="0"
              step="0.01"
              class="form-control form-control-sm"
            />
          </div>
        </div>
        <div v-for="(r, i) in modulo.rate" :key="i" class="row g-3 mb-3 align-items-end">
          <div class="md:col-5">
            <label class="form-label small" :for="`rata-descrizione-${i}`">Rata</label>
            <input
              :id="`rata-descrizione-${i}`"
              v-model="r.descrizione"
              class="form-control form-control-sm"
              :placeholder="i === modulo.rate.length - 1 ? 'Saldo' : 'Acconto'"
            />
          </div>
          <div class="md:col-3">
            <label class="form-label small" :for="`rata-importo-${i}`">Importo (€)</label>
            <input
              :id="`rata-importo-${i}`"
              v-model="r.importo"
              type="number"
              min="0.01"
              step="0.01"
              class="form-control form-control-sm"
              required
            />
          </div>
          <div class="md:col-3">
            <label class="form-label small" :for="`rata-scadenza-${i}`">Entro il</label>
            <input
              :id="`rata-scadenza-${i}`"
              v-model="r.scadenza"
              type="date"
              class="form-control form-control-sm"
              required
            />
          </div>
          <div class="md:col-1">
            <button
              v-if="modulo.rate.length > 1"
              type="button"
              class="btn btn-sm btn-link"
              :aria-label="`Togli la rata ${i + 1}`"
              @click="modulo.rate.splice(i, 1)"
            >
              Togli
            </button>
          </div>
        </div>
        <div class="d-flex flex-wrap align-items-center gap-3">
          <button
            type="button"
            class="btn btn-sm btn-link"
            @click="modulo.rate.push({ descrizione: '', importo: '', scadenza: '' })"
          >
            Aggiungi una rata
          </button>
          <span class="small">Totale {{ euro(totale) }}</span>
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Salva la quota
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="modulo.aperto = false">
            Annulla
          </button>
        </div>
      </form>

      <template v-if="situazione.length">
        <h3 class="h6 mt-5">Chi ha pagato</h3>
        <ul class="list-group">
          <li v-for="r in situazione" :key="r.persona_id" class="list-group-item">
            <div class="d-flex flex-wrap align-items-baseline gap-3">
              <RouterLink :to="{ name: 'persona', params: { id: r.persona_id } }">{{
                r.persona
              }}</RouterLink>
              <span v-if="pagate(r)" class="badge theme-success">In regola</span>
            </div>
            <div
              v-for="q in r.quote"
              :key="q.quota_id"
              class="d-flex flex-wrap align-items-center gap-3 small"
              :class="{ 'fg-2 text-decoration-line-through': q.annullata }"
            >
              <span>{{ q.descrizione }} · {{ euro(q.importo) }}</span>
              <span v-if="!q.annullata"
                >pagato {{ euro(q.pagato) }}, resta {{ euro(q.residuo) }}</span
              >
              <button
                v-if="!q.annullata && modifica.quota !== q.quota_id"
                type="button"
                class="btn btn-sm btn-link"
                @click="Object.assign(modifica, { quota: q.quota_id, importo: q.importo })"
              >
                Cambia importo
              </button>
              <form
                v-else-if="modifica.quota === q.quota_id"
                class="d-flex align-items-center gap-1"
                @submit.prevent="salvaImporto"
              >
                <input
                  v-model="modifica.importo"
                  type="number"
                  min="0"
                  step="0.01"
                  class="form-control form-control-sm w-auto"
                  :aria-label="`Importo di ${q.descrizione} per ${r.persona}`"
                  required
                />
                <button
                  type="submit"
                  class="btn btn-sm btn-solid theme-primary"
                  :disabled="inCorso"
                >
                  Salva
                </button>
                <button type="button" class="btn btn-sm btn-link" @click="modifica.quota = 0">
                  Annulla
                </button>
              </form>
            </div>
          </li>
        </ul>
      </template>
    </template>
  </section>
</template>
