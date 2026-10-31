<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { api, euro, type FasciaPaypal, type ImpostazioniPagamenti } from '@/api/qdc'
import Icona from '@/components/Icona.vue'
import { useErrore } from '@/composables/useErrore'

// How families pay (DEC-83, DEC-253): each way enabled on its own; the families see in
// their fees only the enabled ones. The server checks the IBAN and the bands.
const { errore, inCorso, esegui } = useErrore()
const dati = ref<ImpostazioniPagamenti | null>(null)
const esito = ref('')
// PayPal by bands: the bands with their limit, and apart what is added above the highest
// one ("oltre"); the API keeps "oltre" as the last band, without a limit.
const fasce = ref<FasciaPaypal[]>([])
const oltre = ref<string | number>('')

function mostra(nuovi: ImpostazioniPagamenti) {
  dati.value = nuovi
  const ultima = nuovi.paypal_fasce.at(-1)
  const conOltre = ultima !== undefined && ultima.fino_a === null
  fasce.value = conOltre ? nuovi.paypal_fasce.slice(0, -1) : [...nuovi.paypal_fasce]
  oltre.value = conOltre ? ultima.quota : ''
  if (!fasce.value.length) fasce.value.push({ fino_a: '', quota: '' })
}

onMounted(async () => {
  const letti = await esegui(() => api.impostazioniQuote())
  if (letti) mostra(letti)
})

// Number inputs give numbers, or '' when empty: the API wants decimals as text or null.
const testo = (v: unknown) => (v === '' || v === null || v === undefined ? null : String(v))

async function salva() {
  const d = dati.value
  if (!d) return
  esito.value = ''
  const corpo: ImpostazioniPagamenti = {
    ...d,
    paypal_valore: testo(d.paypal_valore),
    paypal_fasce:
      d.paypal_maggiorazione === 'FASCE'
        ? [
            ...fasce.value.map((f) => ({ fino_a: testo(f.fino_a), quota: testo(f.quota) ?? '0' })),
            { fino_a: null, quota: testo(oltre.value) ?? '' },
          ]
        : [],
  }
  const nuovi = await esegui(() => api.salvaImpostazioniQuote(corpo))
  if (!nuovi) return
  mostra(nuovi)
  esito.value = nuovi.conto_paypal_creato
    ? 'Pagamenti salvati. Ho creato in prima nota il conto PayPal, con saldo zero da oggi: ' +
      'se il conto ha già dei soldi, correggi il saldo iniziale nella Prima nota.'
    : 'Pagamenti salvati.'
}

function aggiungiFascia() {
  fasce.value.push({ fino_a: '', quota: '' })
}

function togliFascia(i: number) {
  fasce.value.splice(i, 1)
}

/** What a family paying 35 € would add, as a hint while typing (the server decides). */
const esempio = computed(() => {
  const d = dati.value
  if (!d || d.paypal_maggiorazione === 'NESSUNA') return ''
  const importo = 35
  const fascia = fasce.value.find((f) => f.fino_a && importo <= Number(f.fino_a))
  const aggiunta =
    d.paypal_maggiorazione === 'FISSA'
      ? Number(d.paypal_valore || 0)
      : d.paypal_maggiorazione === 'PERCENTUALE'
        ? Math.round(importo * Number(d.paypal_valore || 0)) / 100
        : Number(fascia ? fascia.quota || 0 : oltre.value || 0)
  return `Per una quota di ${euro(importo)} la famiglia paga ${euro(importo + aggiunta)}.`
})
</script>

<template>
  <section v-if="dati" class="mb-7">
    <h2 class="h5">Pagamenti</h2>
    <p class="small fg-2">
      Come le famiglie possono pagare: nella pagina delle quote vedono solo i modi abilitati. I
      pagamenti non passano dall'app: chi li riceve li registra.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>
    <form class="card card-body" @submit.prevent="salva">
      <div class="form-field">
        <div class="switch">
          <input id="pag-contanti" v-model="dati.contanti_attivo" type="checkbox" role="switch" />
        </div>
        <label for="pag-contanti" class="d-flex align-items-center gap-3">
          <Icona nome="cash" /> Contanti, ai capi
        </label>
      </div>
      <div class="form-field mt-3">
        <div class="switch">
          <input id="pag-carte" v-model="dati.carte_attivo" type="checkbox" role="switch" />
        </div>
        <label for="pag-carte" class="d-flex align-items-center gap-3">
          <Icona nome="credit-card" /> Carte di credito o di debito, ai capi
        </label>
      </div>

      <hr />
      <div class="form-field">
        <div class="switch">
          <input id="pag-bonifico" v-model="dati.bonifico_attivo" type="checkbox" role="switch" />
        </div>
        <label for="pag-bonifico" class="d-flex align-items-center gap-3">
          <Icona nome="bank2" /> Bonifico
        </label>
      </div>
      <div v-if="dati.bonifico_attivo" class="row g-3 mt-1">
        <div class="col-12 md:col-6">
          <label class="form-label small mb-0" for="pag-iban">IBAN del gruppo</label>
          <input
            id="pag-iban"
            v-model="dati.iban"
            class="form-control form-control-sm"
            autocomplete="off"
            placeholder="IT00 X000 0000 0000 0000 0000 000"
          />
        </div>
        <div class="col-12 md:col-6">
          <label class="form-label small mb-0" for="pag-intestatario">Conto intestato a</label>
          <input
            id="pag-intestatario"
            v-model="dati.intestatario_conto"
            class="form-control form-control-sm"
          />
        </div>
        <div class="col-12 md:col-6">
          <label class="form-label small mb-0" for="pag-banca">Banca (facoltativa)</label>
          <input id="pag-banca" v-model="dati.banca" class="form-control form-control-sm" />
        </div>
        <div class="col-12 md:col-6">
          <label class="form-label small mb-0" for="pag-bic">BIC/SWIFT (facoltativo)</label>
          <input
            id="pag-bic"
            v-model="dati.bic"
            class="form-control form-control-sm"
            autocomplete="off"
          />
          <div class="form-text">Serve per i bonifici dall'estero.</div>
        </div>
      </div>

      <hr />
      <div class="form-field">
        <div class="switch">
          <input id="pag-paypal" v-model="dati.paypal_attivo" type="checkbox" role="switch" />
        </div>
        <label for="pag-paypal" class="d-flex align-items-center gap-3">
          <Icona nome="paypal" /> PayPal
        </label>
      </div>
      <template v-if="dati.paypal_attivo">
        <div class="row g-3 mt-1">
          <div class="col-12 md:col-6">
            <label class="form-label small mb-0" for="pag-link">Link PayPal</label>
            <input
              id="pag-link"
              v-model="dati.link_pagamento"
              type="url"
              class="form-control form-control-sm"
              placeholder="https://paypal.me/…"
            />
            <div class="form-text">
              Il pulsante delle famiglie aggiunge in fondo l'importo da pagare: il link deve essere
              quello a cui PayPal attacca l'importo (es. https://paypal.me/nome).
            </div>
          </div>
          <div class="col-12 md:col-6">
            <label class="form-label small mb-0" for="pag-maggiorazione">
              Quota aggiuntiva per i costi di PayPal
            </label>
            <select
              id="pag-maggiorazione"
              v-model="dati.paypal_maggiorazione"
              class="form-control form-control-sm"
            >
              <option value="NESSUNA">Nessuna</option>
              <option value="FISSA">Fissa</option>
              <option value="PERCENTUALE">In percentuale</option>
              <option value="FASCE">A fasce di importo</option>
            </select>
          </div>
          <div
            v-if="
              dati.paypal_maggiorazione === 'FISSA' || dati.paypal_maggiorazione === 'PERCENTUALE'
            "
            class="col-12 md:col-6"
          >
            <label class="form-label small mb-0" for="pag-valore">
              {{ dati.paypal_maggiorazione === 'FISSA' ? 'Euro in più' : 'Percentuale in più' }}
            </label>
            <input
              id="pag-valore"
              v-model="dati.paypal_valore"
              type="number"
              min="0"
              step="0.01"
              class="form-control form-control-sm"
            />
          </div>
        </div>
        <div v-if="dati.paypal_maggiorazione === 'FASCE'" class="mt-3">
          <p class="small fg-2 mb-1">
            Per ogni fascia: fino a quale importo vale e quanto si aggiunge; poi quanto si aggiunge
            per gli importi più alti.
          </p>
          <div v-for="(f, i) in fasce" :key="i" class="d-flex flex-wrap align-items-end gap-3 mb-1">
            <div>
              <label class="form-label small mb-0" :for="`fascia-fino-${i}`"
                >Fino a € (incluso)</label
              >
              <input
                :id="`fascia-fino-${i}`"
                v-model="f.fino_a"
                type="number"
                min="0"
                step="0.01"
                required
                class="form-control form-control-sm"
              />
            </div>
            <div>
              <label class="form-label small mb-0" :for="`fascia-quota-${i}`"
                >Si aggiungono €</label
              >
              <input
                :id="`fascia-quota-${i}`"
                v-model="f.quota"
                type="number"
                min="0"
                step="0.01"
                required
                class="form-control form-control-sm"
              />
            </div>
            <button
              v-if="fasce.length > 1"
              type="button"
              class="btn btn-sm btn-link"
              :aria-label="`Togli la fascia ${i + 1}`"
              @click="togliFascia(i)"
            >
              <Icona nome="trash" />
            </button>
          </div>
          <button
            type="button"
            class="btn btn-sm btn-outline theme-primary mb-3"
            @click="aggiungiFascia"
          >
            <Icona nome="plus-lg" /> Aggiungi una fascia
          </button>
          <div class="d-flex">
            <div>
              <label class="form-label small mb-0" for="fascia-oltre"
                >Oltre la fascia più alta si aggiungono €</label
              >
              <input
                id="fascia-oltre"
                v-model="oltre"
                type="number"
                min="0"
                step="0.01"
                required
                class="form-control form-control-sm"
              />
            </div>
          </div>
        </div>
        <p v-if="esempio" class="form-text mb-0 mt-3">{{ esempio }}</p>
      </template>

      <div class="mt-5">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Salva
        </button>
      </div>
    </form>
  </section>
</template>
