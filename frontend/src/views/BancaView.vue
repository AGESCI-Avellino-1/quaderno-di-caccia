<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'

import {
  api,
  euro,
  nomeUnita,
  type Cassa,
  type CarteUnita,
  type ConfermaRiga,
  type RigaBanca,
  type RigheBanca,
  type Unita,
  type VoceModelloD,
} from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The bank statement (DEC-93, DEC-221…DEC-224): the group treasurer and the
// capigruppo load the bank's movements and confirm, line by line, what each one is in
// the cash book. The app proposes; nothing is recorded without a confirmation. Online
// only: the bank's text holds personal data and is never stored on the device.
const { errore, inCorso, esegui } = useErrore()
const conti = ref<Cassa[]>([])
const contanti = ref<Cassa[]>([])
const conto = ref<number | null>(null)
const dati = ref<RigheBanca | null>(null)
const carte = ref<CarteUnita | null>(null)
const unita = ref<Unita[]>([])
const voci = ref<VoceModelloD[]>([])
const esito = ref('')

onMounted(async () => {
  const casse = await esegui(() => api.casse())
  if (!casse) return
  conti.value = casse.filter((c) => c.tipo === 'BANCA' && c.attiva)
  contanti.value = casse.filter((c) => c.tipo === 'CONTANTI' && c.attiva)
  conto.value = conti.value[0]?.id ?? null
  unita.value = (await esegui(() => api.unita())) ?? []
  voci.value = (await esegui(() => api.vociModelloD())) ?? []
  carte.value = (await esegui(() => api.carteUnita())) ?? null
  await caricaRighe()
})

async function caricaRighe() {
  if (conto.value === null) return
  const letto = await esegui(() => api.righeBanca(conto.value!))
  if (!letto) return
  dati.value = letto
  for (const r of letto.righe) prepara(r)
}

// --- Loading the file -----------------------------------------------------------------
const file = ref<File | null>(null)
async function carica() {
  if (!file.value || conto.value === null) return
  const f = file.value
  const fatto = await esegui(() => api.caricaEstratto(conto.value!, f))
  if (!fatto) return
  esito.value =
    `Caricate ${fatto.righe_nuove} righe nuove` +
    (fatto.righe_gia_presenti ? `, ${fatto.righe_gia_presenti} erano già state caricate` : '') +
    '.'
  file.value = null
  await caricaRighe()
}

// --- One line ---------------------------------------------------------------------------
interface Scelta {
  versato_da: string
  importi: Record<number, string>
  famiglia: number
  descrizione: string
  voce_id: string
  unita_id: number | null
  cassa_destinazione_id: number | null
}
const scelte = reactive<Record<number, Scelta>>({})

function prepara(r: RigaBanca) {
  const famiglia = r.famiglie[0]
  scelte[r.id] = {
    versato_da: r.ordinante,
    famiglia: 0,
    importi: Object.fromEntries(
      (famiglia?.quote ?? []).map((q) => [q.id, Number(q.proposto) ? q.proposto : '']),
    ),
    descrizione: '',
    voce_id: r.uscita?.voce_id ?? '',
    unita_id: r.uscita?.unita_id ?? null,
    cassa_destinazione_id: r.uscita?.cassa_destinazione_id ?? null,
  }
}

function scegliFamiglia(r: RigaBanca, indice: number) {
  const s = scelte[r.id]!
  s.famiglia = indice
  s.importi = Object.fromEntries(
    r.famiglie[indice]!.quote.map((q) => [q.id, Number(q.proposto) ? q.proposto : '']),
  )
}

const entrata = (r: RigaBanca) => Number(r.importo) > 0
const vociPer = (r: RigaBanca) => voci.value.filter((v) => v.lato === (entrata(r) ? 'E' : 'U'))
const unitaVere = computed(() => unita.value.filter((u) => u.tipo !== 'COMUNITA_CAPI'))

async function conferma(r: RigaBanca, corpo: ConfermaRiga, messaggio: string) {
  esito.value = ''
  const fatto = await esegui(() => api.confermaRigaBanca(r.id, corpo))
  if (!fatto) return
  esito.value = messaggio
  await caricaRighe()
}

function pagaQuote(r: RigaBanca) {
  const s = scelte[r.id]!
  const quote = Object.entries(s.importi)
    .filter(([, importo]) => Number(importo) > 0)
    .map(([id, importo]) => ({ quota_id: Number(id), importo: String(importo) }))
  return conferma(
    r,
    { azione: 'quote', quote, versato_da: s.versato_da },
    'Pagamento registrato, con la sua ricevuta.',
  )
}

function nuovoMovimento(r: RigaBanca) {
  const s = scelte[r.id]!
  return conferma(
    r,
    { azione: 'movimento', descrizione: s.descrizione, voce_id: s.voce_id, unita_id: s.unita_id },
    'Movimento registrato in prima nota.',
  )
}

function giroconto(r: RigaBanca) {
  const s = scelte[r.id]!
  return conferma(
    r,
    {
      azione: 'giroconto',
      descrizione: s.descrizione,
      cassa_destinazione_id: s.cassa_destinazione_id,
    },
    'Giroconto registrato.',
  )
}

const totaleScelto = (r: RigaBanca) =>
  Object.values(scelte[r.id]?.importi ?? {}).reduce((t, i) => t + (Number(i) || 0), 0)

// --- Cards ------------------------------------------------------------------------------
const carta = reactive({ unita_id: null as number | null, ultime_cifre: '' })
async function aggiungiCarta() {
  if (carta.unita_id === null) return
  const nuove = await esegui(() => api.nuovaCarta(carta.unita_id!, carta.ultime_cifre))
  if (!nuove) return
  carte.value = nuove
  Object.assign(carta, { unita_id: null, ultime_cifre: '' })
}
async function togliCarta(id: number) {
  carte.value = (await esegui(() => api.togliCarta(id))) ?? carte.value
}

const data = (d: string) => new Date(d).toLocaleDateString('it-IT')
</script>

<template>
  <section style="max-width: 60rem">
    <div class="d-flex flex-wrap align-items-center gap-3 mb-1">
      <h1 class="h4 mb-0">Estratto conto della banca</h1>
      <RouterLink :to="{ name: 'cassa' }" class="small">Prima nota</RouterLink>
    </div>
    <p class="fg-2 small">
      Carica i movimenti scaricati dalla banca («Lista movimenti», file Excel) e conferma cosa è
      ogni riga: un pagamento di quote, un movimento già registrato, una spesa o un prelievo con la
      carta di un'unità. Nulla entra in prima nota senza la tua conferma.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>
    <p v-if="!inCorso && !conti.length" class="small">
      Non c'è un conto bancario in prima nota: lo configurano i capigruppo o il tesoriere di gruppo.
    </p>

    <template v-if="conti.length">
      <form class="card card-body mb-5" @submit.prevent="carica">
        <div class="row g-3 align-items-end">
          <div v-if="conti.length > 1" class="col-12 md:col-4">
            <label class="form-label small" for="banca-conto">Conto</label>
            <select
              id="banca-conto"
              v-model="conto"
              class="form-control form-control-sm"
              @change="caricaRighe"
            >
              <option v-for="c in conti" :key="c.id" :value="c.id">{{ c.nome }}</option>
            </select>
          </div>
          <div class="col-12 md:col-6">
            <label class="form-label small" for="banca-file">File della banca</label>
            <input
              id="banca-file"
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              class="form-control form-control-sm"
              required
              @change="file = ($event.target as HTMLInputElement).files?.[0] ?? null"
            />
          </div>
          <div class="col-12 md:col-2">
            <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
              Carica
            </button>
          </div>
        </div>
        <p class="small fg-2 mt-1 mb-0">
          Le righe già caricate non si ripetono; il file non viene conservato.
        </p>
      </form>

      <template v-if="dati">
        <div
          v-if="dati.saldo"
          class="alert small"
          :class="Number(dati.saldo.differenza) ? 'theme-warning' : 'theme-success'"
          role="status"
        >
          <div>
            Al {{ data(dati.saldo.al) }} la banca dice {{ euro(dati.saldo.banca) }}, la prima nota
            {{ euro(dati.saldo.prima_nota)
            }}<template v-if="Number(dati.saldo.differenza)">
              : differenza di {{ euro(dati.saldo.differenza) }}, da sistemare confermando le righe
              qui sotto</template
            ><template v-else>: tornano</template>.
          </div>
        </div>

        <h2 class="h5">Da confermare ({{ dati.righe.length }})</h2>
        <p v-if="!dati.righe.length" class="small fg-2">
          Nessuna riga da confermare<template v-if="dati.confermate">
            ({{ dati.confermate }} già in prima nota)</template
          >.
        </p>
        <article v-for="r in dati.righe" :key="r.id" class="card card-body mb-3">
          <div class="d-flex flex-wrap justify-content-between gap-3">
            <div>
              <strong>{{ data(r.data) }} · {{ r.operazione }}</strong>
              <div v-if="r.ordinante" class="small">Da: {{ r.ordinante }}</div>
            </div>
            <strong :class="entrata(r) ? 'fg-success' : ''">{{ euro(r.importo) }}</strong>
          </div>
          <p class="small fg-2 mb-3 text-break">{{ r.dettaglio }}</p>

          <div v-for="(g, n) in r.registrati" :key="n" class="d-flex flex-wrap gap-3 mb-3">
            <span class="small">
              Già in prima nota? {{ g.descrizione }} del {{ data(g.data) }}
            </span>
            <button
              type="button"
              class="btn btn-sm btn-solid theme-primary"
              :disabled="inCorso"
              @click="conferma(r, { azione: 'collega', movimenti: g.movimenti }, 'Collegata.')"
            >
              Sì, è questo
            </button>
          </div>

          <div v-if="entrata(r) && r.famiglie.length && scelte[r.id]" class="mb-3">
            <h3 class="h6">Pagamento di quote</h3>
            <div v-if="r.famiglie.length > 1" class="d-flex flex-wrap gap-1 mb-1">
              <button
                v-for="(f, n) in r.famiglie"
                :key="n"
                type="button"
                class="btn btn-sm"
                :class="scelte[r.id]!.famiglia === n ? 'btn-solid theme-primary' : 'btn-outline'"
                @click="scegliFamiglia(r, n)"
              >
                {{ f.quote[0]?.persona }}
              </button>
            </div>
            <table class="table table-sm small mb-1">
              <tbody>
                <tr v-for="q in r.famiglie[scelte[r.id]!.famiglia]!.quote" :key="q.id">
                  <td>{{ q.persona }}</td>
                  <td>{{ q.descrizione }}</td>
                  <td class="text-end">resta {{ euro(q.residuo) }}</td>
                  <td style="width: 8rem">
                    <input
                      v-model="scelte[r.id]!.importi[q.id]"
                      type="number"
                      step="0.01"
                      min="0"
                      :max="q.residuo"
                      class="form-control form-control-sm"
                      :aria-label="`Importo per ${q.descrizione} di ${q.persona}`"
                    />
                  </td>
                </tr>
              </tbody>
            </table>
            <div class="d-flex flex-wrap align-items-end gap-3">
              <div>
                <label class="form-label small" :for="`versato-${r.id}`">Versato da</label>
                <input
                  :id="`versato-${r.id}`"
                  v-model="scelte[r.id]!.versato_da"
                  class="form-control form-control-sm"
                />
              </div>
              <span class="small">Totale {{ euro(totaleScelto(r)) }} su {{ euro(r.importo) }}</span>
              <button
                type="button"
                class="btn btn-sm btn-solid theme-primary"
                :disabled="inCorso || totaleScelto(r) !== Number(r.importo)"
                @click="pagaQuote(r)"
              >
                Registra il pagamento
              </button>
            </div>
          </div>

          <div
            v-if="r.uscita?.tipo === 'GIROCONTO' && scelte[r.id]"
            class="d-flex flex-wrap align-items-end gap-3 mb-3"
          >
            <div>
              <label class="form-label small" :for="`giro-${r.id}`">Prelievo verso la cassa</label>
              <select
                :id="`giro-${r.id}`"
                v-model="scelte[r.id]!.cassa_destinazione_id"
                class="form-control form-control-sm"
              >
                <option v-for="c in contanti" :key="c.id" :value="c.id">{{ c.nome }}</option>
              </select>
            </div>
            <button
              type="button"
              class="btn btn-sm btn-solid theme-primary"
              :disabled="inCorso || !scelte[r.id]!.cassa_destinazione_id"
              @click="giroconto(r)"
            >
              Registra il giroconto
            </button>
          </div>

          <details v-if="scelte[r.id]" :open="!entrata(r) && r.uscita?.tipo !== 'GIROCONTO'">
            <summary class="small">
              {{ entrata(r) ? 'Altra entrata' : 'Spesa o altra uscita' }}
            </summary>
            <div class="row g-3 mt-1">
              <div class="col-12 md:col-5">
                <label class="form-label small" :for="`voce-${r.id}`">Voce del Modello D</label>
                <select
                  :id="`voce-${r.id}`"
                  v-model="scelte[r.id]!.voce_id"
                  class="form-control form-control-sm"
                >
                  <option value="">—</option>
                  <option v-for="v in vociPer(r)" :key="v.id" :value="v.id">
                    {{ v.riga }} · {{ v.nome }}
                  </option>
                </select>
              </div>
              <div class="col-12 md:col-3">
                <label class="form-label small" :for="`unita-${r.id}`">Unità</label>
                <select
                  :id="`unita-${r.id}`"
                  v-model="scelte[r.id]!.unita_id"
                  class="form-control form-control-sm"
                >
                  <option :value="null">Gruppo</option>
                  <option v-for="u in unitaVere" :key="u.id" :value="u.id">
                    {{ nomeUnita(u) }}
                  </option>
                </select>
              </div>
              <div class="col-12 md:col-4">
                <label class="form-label small" :for="`descr-${r.id}`">Descrizione</label>
                <input
                  :id="`descr-${r.id}`"
                  v-model="scelte[r.id]!.descrizione"
                  class="form-control form-control-sm"
                  maxlength="300"
                />
              </div>
            </div>
            <button
              type="button"
              class="btn btn-sm btn-outline theme-primary mt-3"
              :disabled="inCorso || !scelte[r.id]!.voce_id"
              @click="nuovoMovimento(r)"
            >
              Registra in prima nota
            </button>
          </details>
        </article>
      </template>

      <section v-if="carte" class="mt-7">
        <h2 class="h5">Carte delle unità</h2>
        <p class="small fg-2">
          Con le ultime quattro cifre della carta, l'app riconosce l'unità di un prelievo o di un
          pagamento.
        </p>
        <ul class="list-group mb-3">
          <li v-if="!carte.carte.length" class="list-group-item small fg-2">Nessuna carta.</li>
          <li v-for="c in carte.carte" :key="c.id" class="list-group-item small d-flex gap-3">
            <span>…{{ c.ultime_cifre }} · {{ c.unita }}</span>
            <button
              v-if="carte.puo_configurare"
              type="button"
              class="btn btn-sm btn-link py-0"
              :disabled="inCorso"
              @click="togliCarta(c.id)"
            >
              Togli
            </button>
          </li>
        </ul>
        <form
          v-if="carte.puo_configurare"
          class="d-flex flex-wrap align-items-end gap-3"
          @submit.prevent="aggiungiCarta"
        >
          <div>
            <label class="form-label small" for="carta-unita">Unità</label>
            <select id="carta-unita" v-model="carta.unita_id" class="form-control form-control-sm">
              <option v-for="u in unitaVere" :key="u.id" :value="u.id">{{ nomeUnita(u) }}</option>
            </select>
          </div>
          <div>
            <label class="form-label small" for="carta-cifre">Ultime 4 cifre</label>
            <input
              id="carta-cifre"
              v-model="carta.ultime_cifre"
              class="form-control form-control-sm"
              inputmode="numeric"
              pattern="\d{4}"
              maxlength="4"
              required
            />
          </div>
          <button type="submit" class="btn btn-sm btn-outline theme-primary" :disabled="inCorso">
            Aggiungi
          </button>
        </form>
      </section>
    </template>
  </section>
</template>
