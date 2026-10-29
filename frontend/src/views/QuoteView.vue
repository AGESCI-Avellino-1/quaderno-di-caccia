<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import {
  api,
  euro,
  nomeUnita,
  type Coniugi,
  type PersonaElenco,
  type RigaSituazione,
  type TipoQuota,
  type TipoQuotaIn,
  type Unita,
} from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'
import { useSessioneStore } from '@/stores/sessione'

// The group sets the fees (capigruppo and group treasurer); the Co.Ca. and the unit
// treasurers see who paid (DEC-92). The backend decides; this page only hides what the
// profile says the user cannot use. Online only.
const sessione = useSessioneStore()
const { errore, inCorso, esegui } = useErrore()
const gestisce = computed(() => !!sessione.profilo?.gestisce_quote)

const annoCorrente = (() => {
  const oggi = new Date()
  return oggi.getMonth() >= 9 ? oggi.getFullYear() + 1 : oggi.getFullYear()
})()
const anno = ref(annoCorrente)
const etichetta = (fine: number) => `${fine - 1}/${String(fine).slice(-2)}`

const NOMI_MESI = [
  'gen',
  'feb',
  'mar',
  'apr',
  'mag',
  'giu',
  'lug',
  'ago',
  'set',
  'ott',
  'nov',
  'dic',
]
const MESI_ANNO = [10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8, 9]

const tipi = ref<TipoQuota[]>([])
const unita = ref<Unita[]>([])
const unitaScelta = ref<number | null>(null)
const situazione = ref<RigaSituazione[]>([])
const linkPagamento = ref('')
const coniugi = ref<Coniugi[]>([])
const persone = ref<PersonaElenco[]>([])
const nuoviConiugi = reactive({ a: '', b: '' })
const messaggio = ref('')

const vuoto = (): TipoQuotaIn => ({
  nome: '',
  categoria: 'GRUPPO',
  anno: anno.value,
  importo: '',
  sconto_famiglia: '0',
  destinatari: 'TUTTI',
  unita: [],
  scadenza: null,
  mesi: [10, 11, 12, 1, 2, 3, 4, 5, 6],
  giorno_scadenza: 10,
})
const modulo = ref<TipoQuotaIn | null>(null)
const inModifica = ref<number | null>(null)

const unitaVisibili = computed(() =>
  unita.value.filter((u) => sessione.profilo?.unita_quote.includes(u.id)),
)

async function caricaTipi() {
  tipi.value = (await esegui(() => api.tipiQuota(anno.value))) ?? []
}

async function caricaSituazione() {
  if (unitaScelta.value === null) return
  situazione.value = (await esegui(() => api.situazioneQuote(unitaScelta.value!, anno.value))) ?? []
}

onMounted(async () => {
  unita.value = (await esegui(() => api.unita())) ?? []
  unitaScelta.value = unitaVisibili.value[0]?.id ?? null
  if (gestisce.value) {
    linkPagamento.value = (await esegui(() => api.impostazioniQuote()))?.link_pagamento ?? ''
    coniugi.value = (await esegui(() => api.coniugi())) ?? []
    persone.value = (await esegui(() => api.persone())) ?? []
  }
})
watch(anno, () => Promise.all([caricaTipi(), caricaSituazione()]), { immediate: true })
watch(unitaScelta, caricaSituazione)

function nuovo() {
  modulo.value = vuoto()
  inModifica.value = null
}

function modifica(tipo: TipoQuota) {
  modulo.value = {
    nome: tipo.nome,
    categoria: tipo.categoria,
    anno: tipo.anno,
    importo: tipo.importo,
    sconto_famiglia: tipo.sconto_famiglia,
    destinatari: tipo.destinatari,
    unita: [...tipo.unita],
    scadenza: tipo.scadenza,
    mesi: tipo.mesi.length ? [...tipo.mesi] : vuoto().mesi,
    giorno_scadenza: tipo.giorno_scadenza ?? 10,
  }
  inModifica.value = tipo.id
}

async function salva() {
  if (!modulo.value) return
  const dati = { ...modulo.value }
  if (dati.categoria === 'CENSIMENTO') dati.sconto_famiglia = '0'
  const fatto = await esegui(() =>
    inModifica.value ? api.modificaTipoQuota(inModifica.value, dati) : api.creaTipoQuota(dati),
  )
  if (!fatto) return
  modulo.value = null
  await caricaTipi()
}

async function emetti(tipo: TipoQuota) {
  const esito = await esegui(() => api.emettiQuote(tipo.id))
  if (!esito) return
  messaggio.value = esito.emesse
    ? `${tipo.nome}: ${esito.emesse} quote emesse.`
    : `${tipo.nome}: nessuna quota nuova da emettere.`
  await Promise.all([caricaTipi(), caricaSituazione()])
}

async function salvaLink() {
  const fatto = await esegui(() => api.salvaImpostazioniQuote(linkPagamento.value))
  if (fatto) messaggio.value = 'Link di pagamento salvato.'
}

async function aggiungiConiugi() {
  const fatto = await esegui(() =>
    api.aggiungiConiugi(Number(nuoviConiugi.a), Number(nuoviConiugi.b)),
  )
  if (!fatto) return
  Object.assign(nuoviConiugi, { a: '', b: '' })
  coniugi.value = (await esegui(() => api.coniugi())) ?? []
}

async function togliConiugi(id: number) {
  await esegui(() => api.togliConiugi(id))
  if (errore.value) return
  coniugi.value = coniugi.value.filter((c) => c.id !== id)
}

const scadenzaTipo = (t: TipoQuota) =>
  t.categoria === 'MENSILE'
    ? `entro il ${t.giorno_scadenza} di ${MESI_ANNO.filter((m) => t.mesi.includes(m))
        .map((m) => NOMI_MESI[m - 1])
        .join(', ')}`
    : t.scadenza
      ? `entro il ${new Date(t.scadenza).toLocaleDateString('it-IT')}`
      : ''
</script>

<template>
  <section>
    <div class="d-flex flex-wrap align-items-center gap-3 mb-5">
      <h1 class="h4 mb-0">Quote</h1>
      <div class="d-flex align-items-center gap-1">
        <button
          type="button"
          class="btn btn-sm btn-link"
          aria-label="Anno precedente"
          @click="anno--"
        >
          ‹
        </button>
        <span>Anno {{ etichetta(anno) }}</span>
        <button
          type="button"
          class="btn btn-sm btn-link"
          aria-label="Anno successivo"
          @click="anno++"
        >
          ›
        </button>
      </div>
    </div>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <div v-if="messaggio" class="alert theme-success small" role="status">
      <div>{{ messaggio }}</div>
    </div>

    <section v-if="unitaVisibili.length" class="mb-7">
      <h2 class="h5">Chi ha pagato</h2>
      <div class="mb-3">
        <label class="form-label small" for="situazione-unita">Unità</label>
        <select
          id="situazione-unita"
          v-model="unitaScelta"
          class="form-control form-control-sm w-auto"
        >
          <option v-for="u in unitaVisibili" :key="u.id" :value="u.id">{{ nomeUnita(u) }}</option>
        </select>
      </div>
      <p v-if="!inCorso && !situazione.length" class="fg-2">Nessun socio con quote.</p>
      <div v-else class="table-responsive">
        <table class="table table-sm align-middle">
          <thead>
            <tr>
              <th>Socio</th>
              <th class="text-end">Da pagare</th>
              <th class="text-end">Pagato</th>
              <th class="text-end">Resta</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in situazione" :key="r.persona_id">
              <td>
                <RouterLink :to="{ name: 'persona', params: { id: r.persona_id } }">{{
                  r.persona
                }}</RouterLink>
              </td>
              <td class="text-end">{{ euro(r.dovuto) }}</td>
              <td class="text-end">{{ euro(r.pagato) }}</td>
              <td class="text-end">{{ euro(r.residuo) }}</td>
              <td>
                <span v-if="r.scadute" class="badge theme-danger">{{ r.scadute }} scadute</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <template v-if="gestisce">
      <section class="mb-7">
        <div class="d-flex flex-wrap align-items-center gap-3 mb-3">
          <h2 class="h5 mb-0">Tipi di quota</h2>
          <button type="button" class="btn btn-sm btn-outline theme-primary" @click="nuovo">
            Nuovo tipo di quota
          </button>
        </div>
        <p class="form-text">
          Le quote si emettono da sole ogni giorno, quando inizia il loro periodo (la mensile il
          primo del mese). Importo e sconto si copiano all'emissione: cambiarli dopo non tocca le
          quote già emesse.
        </p>

        <form v-if="modulo" class="border rounded p-5 mb-5" @submit.prevent="salva">
          <div class="row g-3">
            <div class="md:col-6">
              <label class="form-label small" for="tipo-nome">Nome</label>
              <input
                id="tipo-nome"
                v-model="modulo.nome"
                class="form-control form-control-sm"
                required
              />
            </div>
            <div class="md:col-6">
              <label class="form-label small" for="tipo-categoria">Tipo</label>
              <select
                id="tipo-categoria"
                v-model="modulo.categoria"
                class="form-control form-control-sm"
              >
                <option value="CENSIMENTO">Censimento (quota nazionale)</option>
                <option value="GRUPPO">Quota di gruppo</option>
                <option value="MENSILE">Quota mensile di unità</option>
              </select>
            </div>
            <div class="md:col-4">
              <label class="form-label small" for="tipo-importo">Importo (€)</label>
              <input
                id="tipo-importo"
                v-model="modulo.importo"
                type="number"
                min="0.01"
                step="0.01"
                class="form-control form-control-sm"
                required
              />
            </div>
            <div v-if="modulo.categoria !== 'CENSIMENTO'" class="md:col-4">
              <label class="form-label small" for="tipo-sconto">Sconto famiglia (€)</label>
              <input
                id="tipo-sconto"
                v-model="modulo.sconto_famiglia"
                type="number"
                min="0"
                step="0.01"
                class="form-control form-control-sm"
              />
              <div class="form-text">
                Si toglie alla quota di ognuno quando la famiglia ha almeno due soci. 0 = nessuno.
              </div>
            </div>
            <div class="md:col-4">
              <label class="form-label small" for="tipo-destinatari">Chi la paga</label>
              <select
                id="tipo-destinatari"
                v-model="modulo.destinatari"
                class="form-control form-control-sm"
              >
                <option value="TUTTI">Tutti i soci</option>
                <option value="RAGAZZI">Solo i ragazzi</option>
                <option value="CAPI">Solo i capi</option>
                <option value="UNITA">Le unità indicate</option>
              </select>
            </div>
            <fieldset v-if="modulo.destinatari === 'UNITA'" class="col-12">
              <legend class="form-label small">Unità</legend>
              <div class="d-flex flex-wrap gap-5">
                <div v-for="u in unita" :key="u.id" class="form-field mb-0">
                  <input
                    :id="`tipo-unita-${u.id}`"
                    v-model="modulo.unita"
                    type="checkbox"
                    class="check"
                    :value="u.id"
                  />
                  <label :for="`tipo-unita-${u.id}`">{{ nomeUnita(u) }}</label>
                </div>
              </div>
            </fieldset>
            <template v-if="modulo.categoria === 'MENSILE'">
              <fieldset class="md:col-8">
                <legend class="form-label small">Mesi</legend>
                <div class="d-flex flex-wrap gap-3">
                  <div v-for="m in MESI_ANNO" :key="m" class="form-field mb-0">
                    <input
                      :id="`tipo-mese-${m}`"
                      v-model="modulo.mesi"
                      type="checkbox"
                      class="check"
                      :value="m"
                    />
                    <label :for="`tipo-mese-${m}`">{{ NOMI_MESI[m - 1] }}</label>
                  </div>
                </div>
              </fieldset>
              <div class="md:col-4">
                <label class="form-label small" for="tipo-giorno">Da pagare entro il giorno</label>
                <input
                  id="tipo-giorno"
                  v-model.number="modulo.giorno_scadenza"
                  type="number"
                  min="1"
                  max="28"
                  class="form-control form-control-sm"
                  required
                />
              </div>
            </template>
            <div v-else class="md:col-4">
              <label class="form-label small" for="tipo-scadenza">Scadenza</label>
              <input
                id="tipo-scadenza"
                v-model="modulo.scadenza"
                type="date"
                class="form-control form-control-sm"
                required
              />
            </div>
          </div>
          <div class="d-flex gap-3 mt-3">
            <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
              Salva
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="modulo = null">
              Annulla
            </button>
          </div>
        </form>

        <p v-if="!tipi.length" class="fg-2">
          Nessun tipo di quota per l'anno {{ etichetta(anno) }}.
        </p>
        <ul class="list-group">
          <li v-for="t in tipi" :key="t.id" class="list-group-item">
            <div class="d-flex flex-wrap align-items-baseline gap-3">
              <strong>{{ t.nome }}</strong>
              <span class="fg-2 small">{{ t.categoria_nome }} · {{ t.destinatari_nome }}</span>
            </div>
            <div class="small">
              {{ euro(t.importo) }}
              <template v-if="Number(t.sconto_famiglia)">
                · sconto famiglia {{ euro(t.sconto_famiglia) }}</template
              >
              · {{ scadenzaTipo(t) }} · {{ t.emesse }} quote emesse
            </div>
            <div class="d-flex gap-3 mt-1">
              <button type="button" class="btn btn-sm btn-link" @click="modifica(t)">
                Modifica
              </button>
              <button
                type="button"
                class="btn btn-sm btn-link"
                :disabled="inCorso"
                @click="emetti(t)"
              >
                Emetti ora
              </button>
            </div>
          </li>
        </ul>
      </section>

      <section class="mb-7">
        <h2 class="h5">Link di pagamento</h2>
        <form class="d-flex flex-wrap align-items-end gap-3" @submit.prevent="salvaLink">
          <div class="flex-grow-1">
            <label class="form-label small" for="link-pagamento">
              Dove le famiglie possono pagare (es. paypal.me): lo vedono nella pagina delle quote
            </label>
            <input
              id="link-pagamento"
              v-model="linkPagamento"
              type="url"
              class="form-control form-control-sm"
              placeholder="https://"
            />
          </div>
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Salva
          </button>
        </form>
      </section>

      <section>
        <h2 class="h5">Coniugi</h2>
        <p class="form-text">
          Per lo sconto famiglia l'app riconosce da sola fratelli, genitori e figli, e i due
          genitori di uno stesso figlio. Qui si indicano i coniugi soci che non hanno figli
          nell'app.
        </p>
        <ul v-if="coniugi.length" class="list-group mb-3">
          <li
            v-for="c in coniugi"
            :key="c.id"
            class="list-group-item d-flex justify-content-between align-items-center"
          >
            {{ c.persona }} e {{ c.coniuge }}
            <button type="button" class="btn btn-sm btn-link" @click="togliConiugi(c.id)">
              Togli
            </button>
          </li>
        </ul>
        <form class="d-flex flex-wrap align-items-end gap-3" @submit.prevent="aggiungiConiugi">
          <div>
            <label class="form-label small" for="coniuge-a">Socio</label>
            <select
              id="coniuge-a"
              v-model="nuoviConiugi.a"
              class="form-control form-control-sm"
              required
            >
              <option value="" disabled>Scegli…</option>
              <option v-for="p in persone" :key="p.id" :value="p.id">
                {{ p.cognome }} {{ p.nome }}
              </option>
            </select>
          </div>
          <div>
            <label class="form-label small" for="coniuge-b">Coniuge</label>
            <select
              id="coniuge-b"
              v-model="nuoviConiugi.b"
              class="form-control form-control-sm"
              required
            >
              <option value="" disabled>Scegli…</option>
              <option v-for="p in persone" :key="p.id" :value="p.id">
                {{ p.cognome }} {{ p.nome }}
              </option>
            </select>
          </div>
          <button type="submit" class="btn btn-sm btn-outline theme-primary" :disabled="inCorso">
            Aggiungi
          </button>
        </form>
      </section>
    </template>
  </section>
</template>
