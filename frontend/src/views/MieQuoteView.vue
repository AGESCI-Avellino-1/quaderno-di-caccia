<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { api, euro, ricevutaPdf, ricevutaSegnalazione, type MieQuote, type Quota } from '@/api/qdc'
import CopiaLocale from '@/components/CopiaLocale.vue'
import Icona from '@/components/Icona.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'

// The family's fees (DEC-16): own and children's (an adult child's while still linked,
// DEC-26), with discount and agevolazione, the payments and their receipts, and where to
// pay (DEC-83: never inside the app). Cached for offline reading.
const { errore, inCorso, esegui } = useErrore()
const dati = ref<MieQuote | null>(null)
const copiaDel = ref<string | null>(null)

async function carica() {
  const letto = await esegui(() => leggiConCache('mie-quote', () => api.mieQuote()))
  if (!letto) return
  dati.value = letto.dati
  copiaDel.value = letto.copiaDel
}

onMounted(carica)

const perPersona = computed(() => {
  const gruppi = new Map<number, { nome: string; quote: Quota[] }>()
  for (const q of dati.value?.quote ?? []) {
    if (!gruppi.has(q.persona_id)) gruppi.set(q.persona_id, { nome: q.persona, quote: [] })
    gruppi.get(q.persona_id)!.quote.push(q)
  }
  return [...gruppi.values()]
})
// Fees with a payment reported are waiting for the check, not to pay again (DEC-255).
const aperte = computed(() =>
  (dati.value?.quote ?? []).filter((q) => Number(q.residuo) > 0 && !q.in_verifica),
)
const daPagare = computed(() => aperte.value.reduce((somma, q) => somma + Number(q.residuo), 0))
const segnalazioni = computed(() => dati.value?.segnalazioni ?? [])

// After PayPal (the app cannot know whether it went through) or for a bank transfer, the
// family says "I paid": the fees go "in verifica" (DEC-255).
interface DaSegnalare {
  metodo: 'PAYPAL' | 'BONIFICO'
  quote: number[]
  totale: string | null
}
const daSegnalare = ref<DaSegnalare | null>(null)
const dataPagamento = ref(new Date().toLocaleDateString('sv'))
const fileRicevuta = ref<File | null>(null)
const esito = ref('')

function dopoPaypal(quote: number[], totale: string) {
  daSegnalare.value = { metodo: 'PAYPAL', quote, totale }
  fileRicevuta.value = null
}

function bonifico() {
  daSegnalare.value = { metodo: 'BONIFICO', quote: aperte.value.map((q) => q.id), totale: null }
  fileRicevuta.value = null
}

function sceltoFile(evento: Event) {
  fileRicevuta.value = (evento.target as HTMLInputElement).files?.[0] ?? null
}

async function segnala() {
  const d = daSegnalare.value
  if (!d || !d.quote.length) return
  esito.value = ''
  const nuova = await esegui(() =>
    api.segnalaPagamento({ metodo: d.metodo, quote: d.quote, data: dataPagamento.value }),
  )
  if (!nuova) return
  if (fileRicevuta.value) {
    const file = fileRicevuta.value
    await esegui(() => api.caricaRicevutaSegnalazione(nuova.id, file))
  }
  daSegnalare.value = null
  esito.value = 'Pagamento segnalato: le quote restano in verifica finché un capo non lo conferma.'
  await carica()
}

async function caricaRicevuta(id: number, evento: Event) {
  const file = (evento.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (await esegui(() => api.caricaRicevutaSegnalazione(id, file))) await carica()
}

async function annulla(id: number) {
  await esegui(() => api.annullaSegnalazione(id))
  await carica() // also after an error: the list shows how things stand
}
// The ways the group enabled (DEC-253); a device copy from before may lack them.
const modi = computed(() => dati.value?.modi_pagamento)
const aiCapi = computed(() => {
  const m = modi.value
  if (m?.contanti && m.carte) return 'In contanti o con carta, ai capi.'
  if (m?.contanti) return 'In contanti, ai capi.'
  if (m?.carte) return 'Con carta di credito o di debito, ai capi.'
  return ''
})
/** PayPal for one fee, with its own amount in the link. */
const paypalDi = (quota: number) => modi.value?.paypal?.per_quota?.find((p) => p.quota_id === quota)
const ibanLeggibile = computed(() => modi.value?.bonifico?.iban.replace(/(.{4})/g, '$1 ').trim())
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
          <span v-else-if="segnalazioni.length" class="badge theme-warning"
            >Pagamento in verifica</span
          >
          <span v-else class="badge theme-success">Tutto pagato</span>
        </div>
        <template v-if="daPagare > 0 && modi">
          <h2 class="h6 mt-3 mb-1">Come pagare</h2>
          <ul class="list-unstyled mb-1">
            <li v-if="aiCapi" class="d-flex align-items-start gap-3 mb-3">
              <Icona :nome="modi.contanti ? 'cash' : 'credit-card'" />
              <span>{{ aiCapi }}</span>
            </li>
            <li v-if="modi.bonifico" class="d-flex align-items-start gap-3 mb-3">
              <Icona nome="bank2" />
              <span>
                Con bonifico a {{ modi.bonifico.intestatario }}<br />
                IBAN <strong class="user-select-all">{{ ibanLeggibile }}</strong>
                <span v-if="modi.bonifico.banca || modi.bonifico.bic" class="d-block small fg-2">
                  <template v-if="modi.bonifico.banca">{{ modi.bonifico.banca }}</template>
                  <template v-if="modi.bonifico.banca && modi.bonifico.bic"> · </template>
                  <template v-if="modi.bonifico.bic">BIC/SWIFT {{ modi.bonifico.bic }}</template>
                </span>
                <button
                  type="button"
                  class="btn btn-sm btn-outline theme-primary mt-1 d-block"
                  @click="bonifico"
                >
                  Ho fatto il bonifico
                </button>
              </span>
            </li>
            <li v-if="modi.paypal" class="d-flex align-items-start gap-3 mb-3">
              <Icona nome="paypal" />
              <span>
                Con PayPal<template v-if="Number(modi.paypal.maggiorazione)"
                  >: {{ euro(daPagare) }} più {{ euro(modi.paypal.maggiorazione) }} per i costi, in
                  tutto <strong>{{ euro(modi.paypal.totale) }}</strong></template
                >.
                <span v-if="modi.paypal.regola" class="d-block small fg-2">{{
                  modi.paypal.regola
                }}</span>
                <a
                  :href="modi.paypal.link"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="btn btn-sm btn-solid theme-primary mt-1"
                  @click="
                    dopoPaypal(
                      aperte.map((q) => q.id),
                      modi.paypal.totale,
                    )
                  "
                >
                  Paga tutto con PayPal ({{ euro(modi.paypal.totale) }})
                </a>
              </span>
            </li>
          </ul>
        </template>
        <p class="form-text mb-0">
          Chi riceve il pagamento lo registra nell'app, e ti arriva la ricevuta per email. Se paghi
          con PayPal o con bonifico, segnalalo qui: un capo lo verifica.
        </p>
      </div>

      <div v-if="esito" class="alert theme-success small" role="status">
        <div>{{ esito }}</div>
      </div>

      <form v-if="daSegnalare" class="card card-body mb-5" @submit.prevent="segnala">
        <h2 class="h6 d-flex align-items-center gap-3">
          <Icona :nome="daSegnalare.metodo === 'PAYPAL' ? 'paypal' : 'bank2'" />
          {{
            daSegnalare.metodo === 'PAYPAL'
              ? `Hai completato il pagamento con PayPal${daSegnalare.totale ? ` di ${euro(daSegnalare.totale)}` : ''}?`
              : 'Quali quote hai pagato con il bonifico?'
          }}
        </h2>
        <template v-if="daSegnalare.metodo === 'BONIFICO'">
          <div v-for="q in aperte" :key="q.id" class="form-field">
            <input
              :id="`segnala-${q.id}`"
              v-model="daSegnalare.quote"
              class="check"
              type="checkbox"
              :value="q.id"
            />
            <label :for="`segnala-${q.id}`"
              >{{ q.persona }}: {{ q.descrizione }}, {{ euro(q.residuo) }}</label
            >
          </div>
        </template>
        <div class="d-flex flex-wrap gap-5 mt-3">
          <div>
            <label class="form-label small mb-0" for="segnala-data">Giorno del pagamento</label>
            <input
              id="segnala-data"
              v-model="dataPagamento"
              type="date"
              :max="oggi"
              class="form-control form-control-sm"
              required
            />
          </div>
          <div>
            <label class="form-label small mb-0" for="segnala-ricevuta"
              >Ricevuta (facoltativa, anche dopo)</label
            >
            <input
              id="segnala-ricevuta"
              type="file"
              accept="application/pdf,image/jpeg,image/png"
              class="form-control form-control-sm"
              @change="sceltoFile"
            />
          </div>
        </div>
        <div class="d-flex flex-wrap gap-3 mt-3">
          <button
            type="submit"
            class="btn btn-sm btn-solid theme-primary"
            :disabled="inCorso || !daSegnalare.quote.length"
          >
            Sì, ho pagato
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="daSegnalare = null">
            {{ daSegnalare.metodo === 'PAYPAL' ? 'No, non ho pagato' : 'Annulla' }}
          </button>
        </div>
      </form>

      <section v-if="segnalazioni.length" class="mb-5">
        <h2 class="h5">Pagamenti in verifica</h2>
        <ul class="list-group">
          <li v-for="s in segnalazioni" :key="s.id" class="list-group-item">
            <div class="d-flex flex-wrap align-items-center gap-3">
              <Icona :nome="s.metodo === 'PAYPAL' ? 'paypal' : 'bank2'" />
              <strong>{{ euro(Number(s.importo) + Number(s.maggiorazione)) }}</strong>
              <span>{{ s.metodo_nome }} del {{ data(s.data) }}</span>
              <span class="badge theme-warning">in verifica</span>
            </div>
            <div class="small fg-2">
              {{ s.quote.map((q) => `${q.persona}: ${q.descrizione}`).join(' · ') }}
            </div>
            <div v-if="s.puo_modificare" class="d-flex flex-wrap align-items-center gap-3 mt-1">
              <a v-if="s.ricevuta" :href="ricevutaSegnalazione(s.id)" class="small"
                >Ricevuta caricata</a
              >
              <label class="btn btn-sm btn-outline theme-primary mb-0" :for="`ricevuta-${s.id}`">
                {{ s.ricevuta ? 'Cambia la ricevuta' : 'Carica la ricevuta' }}
              </label>
              <input
                :id="`ricevuta-${s.id}`"
                type="file"
                accept="application/pdf,image/jpeg,image/png"
                class="d-none"
                @change="caricaRicevuta(s.id, $event)"
              />
              <button
                type="button"
                class="btn btn-sm btn-link"
                :disabled="inCorso"
                @click="annulla(s.id)"
              >
                Annulla la segnalazione
              </button>
            </div>
          </li>
        </ul>
      </section>

      <section v-for="p in perPersona" :key="p.nome" class="mb-5">
        <h2 class="h5">{{ p.nome }}</h2>
        <ul class="list-group">
          <li v-for="q in p.quote" :key="q.id" class="list-group-item">
            <div class="d-flex flex-wrap justify-content-between gap-3">
              <span>
                {{ q.descrizione }}
                <span v-if="q.arretrata" class="badge theme-warning ms-1">anno precedente</span>
              </span>
              <span v-if="Number(q.residuo) > 0" class="d-flex align-items-center gap-3">
                <strong>{{ euro(q.residuo) }}</strong>
                <span v-if="q.in_verifica" class="badge theme-warning">in verifica</span>
                <a
                  v-else-if="paypalDi(q.id)"
                  :href="paypalDi(q.id)!.link"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="btn btn-sm btn-outline theme-primary"
                  :title="`Paga questa quota con PayPal: ${euro(paypalDi(q.id)!.totale)}`"
                  @click="dopoPaypal([q.id], paypalDi(q.id)!.totale)"
                >
                  <Icona nome="paypal" /> {{ euro(paypalDi(q.id)!.totale) }}
                </a>
              </span>
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
