<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

import {
  api,
  euro,
  PERCORSO_PAGAMENTI,
  ricevutaPdf,
  type MetodoPagamento,
  type Pagamento,
  type Quota,
  type QuotePersona,
} from '@/api/qdc'
import CopiaLocale from '@/components/CopiaLocale.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'
import { scrivi } from '@/offline/outbox'

// Fees of one member for the current associative year (DEC-80…DEC-84, DEC-92). The
// backend answers 404 to whoever may not see them, and leaves the agevolazione out for
// an R/S treasurer. Fees are cached for offline use; a payment recorded offline waits in
// the queue and gets its receipt number when it reaches the server (DEC-96).
const props = defineProps<{ id: number }>()
const { errore, inCorso, esegui } = useErrore()
const dati = ref<QuotePersona | null>(null)
const copiaDel = ref<string | null>(null)
const pagamenti = ref<Pagamento[]>([])
const esito = ref('')

const oggi = () => new Date().toLocaleDateString('sv')
const modulo = reactive({
  aperto: false,
  data: oggi(),
  metodo: 'CONTANTI' as MetodoPagamento,
  versato_da: '',
  note: '',
  importi: {} as Record<number, string>,
})
const agevolazione = reactive({ quota: 0, importo: '', decisa_il: oggi(), nota: '' })
const annullamento = reactive({ tipo: '' as '' | 'quota' | 'pagamento', id: 0, motivo: '' })

async function carica(id: number) {
  try {
    const letto = await leggiConCache(`quote:${id}`, () => api.quotePersona(id))
    dati.value = letto.dati
    copiaDel.value = letto.copiaDel
  } catch {
    dati.value = null
    return
  }
  try {
    pagamenti.value = await api.pagamentiPersona(id)
  } catch {
    pagamenti.value = [] // offline: the payments list needs the network
  }
}
watch(() => props.id, carica, { immediate: true })

const aperte = computed(() =>
  [...(dati.value?.quote ?? []), ...(dati.value?.famiglia ?? [])].filter(
    (q) => !q.annullata && Number(q.residuo) > 0,
  ),
)
const totale = computed(() =>
  Object.values(modulo.importi).reduce((somma, v) => somma + (Number(v) || 0), 0),
)
const scaduta = (q: Quota) => Number(q.residuo) > 0 && q.scadenza < oggi()
const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')

function apriPagamento() {
  modulo.aperto = true
  modulo.data = oggi()
  modulo.note = ''
  modulo.importi = {}
  esito.value = ''
}

function scegli(q: Quota, scelta: boolean) {
  if (scelta) modulo.importi[q.id] = q.residuo
  else delete modulo.importi[q.id]
}

async function registra() {
  const righe = Object.entries(modulo.importi)
    .filter(([, importo]) => Number(importo) > 0)
    .map(([quota, importo]) => ({ quota_id: Number(quota), importo: Number(importo).toFixed(2) }))
  const risultato = await esegui(() =>
    scrivi({
      metodo: 'POST',
      percorso: PERCORSO_PAGAMENTI,
      corpo: {
        data: modulo.data,
        metodo: modulo.metodo,
        versato_da: modulo.versato_da,
        note: modulo.note,
        righe,
      },
      // Stored in clear in the queue: no names.
      descrizione: `Pagamento di ${euro(totale.value)} (scheda n. ${props.id})`,
    }),
  )
  if (!risultato) return
  modulo.aperto = false
  esito.value = risultato.inCoda
    ? 'Pagamento salvato sul telefono: sarà registrato, con la sua ricevuta, appena torna la rete.'
    : 'Pagamento registrato: la ricevuta è partita per email.'
  if (!risultato.inCoda) await carica(props.id)
}

function apriAgevolazione(q: Quota) {
  Object.assign(agevolazione, {
    quota: q.id,
    importo: q.agevolazione?.importo ?? '',
    decisa_il: q.agevolazione?.decisa_il ?? oggi(),
    nota: q.agevolazione?.nota ?? '',
  })
}

async function salvaAgevolazione() {
  const fatto = await esegui(() =>
    api.agevola(agevolazione.quota, {
      importo: Number(agevolazione.importo).toFixed(2),
      decisa_il: agevolazione.decisa_il,
      nota: agevolazione.nota,
    }),
  )
  if (!fatto) return
  agevolazione.quota = 0
  await carica(props.id)
}

async function togliAgevolazione() {
  if (!(await esegui(() => api.togliAgevolazione(agevolazione.quota)))) return
  agevolazione.quota = 0
  await carica(props.id)
}

async function annulla() {
  const { tipo, id, motivo } = annullamento
  const fatto = await esegui<unknown>(() =>
    tipo === 'quota' ? api.annullaQuota(id, motivo) : api.annullaPagamento(id, motivo),
  )
  if (!fatto) return
  annullamento.tipo = ''
  await carica(props.id)
}

async function reinvia(id: number) {
  if (await esegui(() => api.reinviaRicevuta(id))) esito.value = 'Ricevuta inviata di nuovo.'
}
</script>

<template>
  <section v-if="dati" class="card card-body mb-5">
    <div class="d-flex flex-wrap align-items-baseline gap-3 mb-3">
      <h2 class="h5 mb-0">Quote</h2>
      <CopiaLocale :del="copiaDel" />
    </div>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>
    <p v-if="!dati.quote.length" class="fg-2 mb-0">Nessuna quota per quest'anno.</p>

    <div v-else class="table-responsive">
      <table class="table table-sm align-middle">
        <thead>
          <tr>
            <th>Quota</th>
            <th>Scadenza</th>
            <th class="text-end">Importo</th>
            <th class="text-end">Da pagare</th>
            <th class="text-end">Resta</th>
            <th v-if="dati.puo_gestire || dati.puo_agevolare"></th>
          </tr>
        </thead>
        <tbody>
          <template v-for="q in dati.quote" :key="q.id">
            <tr :class="{ 'fg-2': q.annullata }">
              <td>
                <span :class="{ 'text-decoration-line-through': q.annullata }">{{
                  q.descrizione
                }}</span>
                <div v-if="Number(q.sconto)" class="small fg-2">
                  Sconto famiglia {{ euro(q.sconto) }}
                </div>
                <div v-if="q.agevolazione" class="small fg-2">
                  Agevolazione {{ euro(q.agevolazione.importo) }}
                  <template v-if="q.agevolazione.nota"> · {{ q.agevolazione.nota }}</template>
                </div>
                <div v-if="q.annullata" class="small">Annullata: {{ q.motivo_annullamento }}</div>
              </td>
              <td :class="{ 'fg-danger': scaduta(q) }">{{ data(q.scadenza) }}</td>
              <td class="text-end">{{ euro(q.importo) }}</td>
              <td class="text-end">{{ euro(q.dovuto) }}</td>
              <td class="text-end">
                <strong v-if="Number(q.residuo) > 0">{{ euro(q.residuo) }}</strong>
                <span v-else-if="!q.annullata" class="badge theme-success">Pagata</span>
              </td>
              <td v-if="dati.puo_gestire || dati.puo_agevolare" class="text-end text-nowrap">
                <button
                  v-if="dati.puo_agevolare && !q.annullata"
                  type="button"
                  class="btn btn-sm btn-link"
                  @click="apriAgevolazione(q)"
                >
                  Agevolazione
                </button>
                <button
                  v-if="dati.puo_gestire && !q.annullata && Number(q.pagato) === 0"
                  type="button"
                  class="btn btn-sm btn-link"
                  @click="Object.assign(annullamento, { tipo: 'quota', id: q.id, motivo: '' })"
                >
                  Annulla
                </button>
              </td>
            </tr>
            <tr v-if="agevolazione.quota === q.id">
              <td colspan="6">
                <form
                  class="d-flex flex-wrap align-items-end gap-3"
                  @submit.prevent="salvaAgevolazione"
                >
                  <div>
                    <label class="form-label small" for="agev-importo">Importo coperto (€)</label>
                    <input
                      id="agev-importo"
                      v-model="agevolazione.importo"
                      type="number"
                      min="0.01"
                      step="0.01"
                      class="form-control form-control-sm"
                      required
                    />
                  </div>
                  <div>
                    <label class="form-label small" for="agev-data">Decisa dalla Co.Ca. il</label>
                    <input
                      id="agev-data"
                      v-model="agevolazione.decisa_il"
                      type="date"
                      class="form-control form-control-sm"
                      required
                    />
                  </div>
                  <div class="flex-grow-1">
                    <label class="form-label small" for="agev-nota">
                      Nota (la vedono solo i capi)
                    </label>
                    <input
                      id="agev-nota"
                      v-model="agevolazione.nota"
                      class="form-control form-control-sm"
                    />
                  </div>
                  <button
                    type="submit"
                    class="btn btn-sm btn-solid theme-primary"
                    :disabled="inCorso"
                  >
                    Salva
                  </button>
                  <button
                    v-if="q.agevolazione"
                    type="button"
                    class="btn btn-sm btn-outline theme-danger"
                    @click="togliAgevolazione"
                  >
                    Togli
                  </button>
                  <button type="button" class="btn btn-sm btn-link" @click="agevolazione.quota = 0">
                    Chiudi
                  </button>
                </form>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <form
      v-if="annullamento.tipo"
      class="d-flex flex-wrap align-items-end gap-3 mb-3"
      @submit.prevent="annulla"
    >
      <div class="flex-grow-1">
        <label class="form-label small" for="motivo-annullamento">
          Perché annulli {{ annullamento.tipo === 'quota' ? 'la quota' : 'il pagamento' }}?
        </label>
        <input
          id="motivo-annullamento"
          v-model="annullamento.motivo"
          class="form-control form-control-sm"
          required
        />
      </div>
      <button type="submit" class="btn btn-sm btn-solid theme-danger" :disabled="inCorso">
        Annulla {{ annullamento.tipo === 'quota' ? 'la quota' : 'il pagamento' }}
      </button>
      <button type="button" class="btn btn-sm btn-link" @click="annullamento.tipo = ''">
        Lascia stare
      </button>
    </form>

    <template v-if="dati.puo_registrare && aperte.length">
      <button
        v-if="!modulo.aperto"
        type="button"
        class="btn btn-sm btn-solid theme-primary align-self-start"
        @click="apriPagamento"
      >
        Registra un pagamento
      </button>
      <form v-else class="border rounded p-5" @submit.prevent="registra">
        <h3 class="h6">Pagamento ricevuto</h3>
        <p class="form-text">
          Scegli le quote che paga e quanto per ciascuna: si può pagare anche solo una parte.
          Compaiono anche le quote aperte di fratelli e genitori.
        </p>
        <div v-for="q in aperte" :key="q.id" class="d-flex flex-wrap align-items-center gap-3 mb-3">
          <div class="form-field mb-0 flex-grow-1">
            <input
              :id="`paga-${q.id}`"
              type="checkbox"
              class="check"
              :checked="q.id in modulo.importi"
              @change="scegli(q, ($event.target as HTMLInputElement).checked)"
            />
            <label :for="`paga-${q.id}`">
              {{ q.persona }} · {{ q.descrizione }}
              <span class="fg-2 small">(resta {{ euro(q.residuo) }})</span>
            </label>
          </div>
          <input
            v-if="q.id in modulo.importi"
            v-model="modulo.importi[q.id]"
            type="number"
            min="0.01"
            :max="q.residuo"
            step="0.01"
            class="form-control form-control-sm w-auto"
            :aria-label="`Importo per ${q.descrizione}`"
            required
          />
        </div>
        <div class="row g-3">
          <div class="md:col-4">
            <label class="form-label small" for="paga-data">Data</label>
            <input
              id="paga-data"
              v-model="modulo.data"
              type="date"
              :max="oggi()"
              class="form-control form-control-sm"
              required
            />
          </div>
          <div class="md:col-4">
            <label class="form-label small" for="paga-metodo">Come</label>
            <select id="paga-metodo" v-model="modulo.metodo" class="form-control form-control-sm">
              <option value="CONTANTI">Contanti</option>
              <option value="BONIFICO">Bonifico</option>
              <option value="ALTRO">Altro</option>
            </select>
          </div>
          <div class="md:col-4">
            <label class="form-label small" for="paga-chi">Chi ha pagato</label>
            <input
              id="paga-chi"
              v-model="modulo.versato_da"
              class="form-control form-control-sm"
              placeholder="Nome e cognome, per la ricevuta"
              required
            />
          </div>
          <div class="col-12">
            <label class="form-label small" for="paga-note">Note (vanno sulla ricevuta)</label>
            <input id="paga-note" v-model="modulo.note" class="form-control form-control-sm" />
          </div>
        </div>
        <div class="d-flex flex-wrap align-items-center gap-3 mt-3">
          <button
            type="submit"
            class="btn btn-sm btn-solid theme-primary"
            :disabled="inCorso || totale <= 0"
          >
            Registra {{ euro(totale) }}
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="modulo.aperto = false">
            Annulla
          </button>
        </div>
      </form>
    </template>

    <template v-if="pagamenti.length">
      <h3 class="h6 mt-5">Pagamenti</h3>
      <ul class="list-group">
        <li v-for="p in pagamenti" :key="p.id" class="list-group-item">
          <div class="d-flex flex-wrap align-items-baseline gap-3">
            <strong :class="{ 'text-decoration-line-through': p.annullato }"
              >Ricevuta {{ p.numero }}</strong
            >
            <span>{{ data(p.data) }} · {{ euro(p.importo) }} · {{ p.metodo_nome }}</span>
            <a :href="ricevutaPdf(p.id)" class="small">Scarica</a>
            <button
              v-if="dati.puo_registrare && !p.annullato"
              type="button"
              class="btn btn-sm btn-link"
              @click="reinvia(p.id)"
            >
              Invia di nuovo
            </button>
            <button
              v-if="dati.puo_gestire && !p.annullato"
              type="button"
              class="btn btn-sm btn-link"
              @click="Object.assign(annullamento, { tipo: 'pagamento', id: p.id, motivo: '' })"
            >
              Annulla
            </button>
          </div>
          <div class="small fg-2">
            Versato da {{ p.versato_da }}
            <template v-if="p.registrato_da"> · registrato da {{ p.registrato_da }}</template>
          </div>
          <div v-for="r in p.righe" :key="r.quota_id" class="small">
            {{ r.persona }} · {{ r.descrizione }}: {{ euro(r.importo) }}
          </div>
          <div v-if="p.annullato" class="small">Annullato: {{ p.motivo_annullamento }}</div>
        </li>
      </ul>
    </template>
  </section>
</template>
