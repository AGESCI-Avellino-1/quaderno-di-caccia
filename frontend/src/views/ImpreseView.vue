<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import {
  api,
  type CataloghiPP,
  type DataParziale,
  type ImpreseReparto,
  type LivelloImpresa,
} from '@/api/qdc'
import CompetenzaEG from '@/components/CompetenzaEG.vue'
import CopiaLocale from '@/components/CopiaLocale.vue'
import InputDataParziale from '@/components/InputDataParziale.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'
import { useSessioneStore } from '@/stores/sessione'

// Imprese of the reparto, of a patrol, of the Alta Squadriglia with the posti d'azione
// and their verification (DEC-65; artt. 32, 42–43), and the specialità di squadriglia,
// held by the patrol, never by its members (DEC-64, V19). The reparto staff writes; any
// capo reads. A CSQ runs the imprese of their patrol; the Consiglio d'impresa appointed
// by the staff assigns and verifies the posti of a reparto or Alta Squadriglia impresa
// (DEC-187): they see only those imprese. Cached for meetings without network.
const props = defineProps<{ id: number }>()
const { errore, inCorso, esegui } = useErrore()
const dati = ref<ImpreseReparto | null>(null)
const copiaDel = ref<string | null>(null)
const cataloghi = ref<CataloghiPP | null>(null)
const esito = ref('')
const oggi = () => new Date().toLocaleDateString('sv')
const sessione = useSessioneStore()

async function carica() {
  const letto = await esegui(() =>
    leggiConCache(`imprese:${props.id}`, () => api.impreseReparto(props.id)),
  )
  dati.value = letto?.dati ?? null
  copiaDel.value = letto?.copiaDel ?? null
}
watch(() => props.id, carica, { immediate: true })

async function fatto(azione: () => Promise<ImpreseReparto>, messaggio: string) {
  const nuovi = await esegui(azione)
  if (!nuovi) return false
  dati.value = nuovi
  esito.value = messaggio
  return true
}

async function dopoScrittura(inCoda: boolean) {
  esito.value = inCoda ? 'Salvato sul telefono: sarà inviato appena torna la rete.' : 'Salvato.'
  if (!inCoda) await carica()
}

// --- Imprese -------------------------------------------------------------------------------

const impresa = reactive({
  aperta: false,
  livello: 'SQUADRIGLIA' as LivelloImpresa,
  squadriglia_id: null as number | null,
  titolo: '',
  descrizione: '',
  dal: oggi(),
  al: '',
})

async function nuovaImpresa() {
  const ok = await fatto(
    () =>
      api.nuovaImpresa(props.id, {
        livello: impresa.livello,
        squadriglia_id: impresa.livello === 'SQUADRIGLIA' ? impresa.squadriglia_id : null,
        titolo: impresa.titolo,
        descrizione: impresa.descrizione,
        dal: impresa.dal,
        al: impresa.al || null,
      }),
    'Impresa salvata.',
  )
  if (ok) Object.assign(impresa, { aperta: false, titolo: '', descrizione: '', al: '' })
}

// The staff appoints the Consiglio d'impresa among the ragazzi of the reparto.
const consiglio = reactive({ impresa: 0, persone: [] as number[] })
async function salvaConsiglio() {
  const ok = await fatto(
    () => api.consiglioImpresa(consiglio.impresa, consiglio.persone),
    "Consiglio d'impresa salvato.",
  )
  if (ok) consiglio.impresa = 0
}

const posto = reactive({ impresa: 0, persona_id: 0, ruolo: '' })
async function nuovoPosto() {
  const ok = await fatto(
    () => api.nuovoPosto(posto.impresa, { persona_id: posto.persona_id, ruolo: posto.ruolo }),
    "Posto d'azione salvato.",
  )
  if (ok) Object.assign(posto, { impresa: 0, persona_id: 0, ruolo: '' })
}

const verifica = reactive({ posto: 0, il: oggi(), sede: '', sede_descrizione: '' })
async function verificaPosto() {
  const ok = await fatto(
    () =>
      api.verificaPosto(verifica.posto, {
        il: verifica.il,
        sede: verifica.sede,
        sede_descrizione: verifica.sede_descrizione,
      }),
    'Verifica registrata.',
  )
  if (ok) verifica.posto = 0
}

// --- Specialità di squadriglia ------------------------------------------------------------

const specialita = reactive({
  squadriglia: 0,
  codice: '',
  carta: '',
  passata: false,
  quando: { data: oggi(), precisione: 'GIORNO' } as DataParziale,
})

async function apriSpecialita(squadriglia: number) {
  specialita.squadriglia = squadriglia
  if (!cataloghi.value) {
    cataloghi.value =
      (await esegui(async () => (await leggiConCache('cataloghi-pp', api.cataloghiPP)).dati)) ??
      null
  }
}

async function nuovaSpecialita() {
  const ok = await fatto(
    () =>
      api.nuovaSpecialitaSquadriglia(specialita.squadriglia, {
        codice: specialita.codice,
        carta: specialita.carta,
        conquistata: specialita.passata ? specialita.quando : null,
      }),
    'Specialità di squadriglia salvata.',
  )
  if (ok) Object.assign(specialita, { squadriglia: 0, codice: '', carta: '', passata: false })
}

const data = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString('it-IT') : '')
</script>

<template>
  <section>
    <div class="d-flex flex-wrap align-items-baseline gap-3">
      <h1 class="h4 mb-1">
        {{ sessione.profilo?.capo ? 'Imprese e specialità di squadriglia' : 'Imprese' }}
      </h1>
      <CopiaLocale :del="copiaDel" />
    </div>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>
    <template v-if="dati">
      <p class="small fg-2">
        {{ dati.reparto }}.
        <RouterLink v-if="sessione.profilo?.capo" :to="`/unita/${dati.reparto_id}/sentiero`"
          >Sentiero del reparto</RouterLink
        >
      </p>

      <section class="mb-5">
        <div class="d-flex flex-wrap align-items-center gap-3 mb-3">
          <h2 class="h5 mb-0">Imprese</h2>
          <button
            v-if="dati.puo_creare && !impresa.aperta"
            type="button"
            class="btn btn-sm btn-outline theme-primary"
            @click="Object.assign(impresa, { aperta: true, livello: 'SQUADRIGLIA' })"
          >
            Nuova impresa
          </button>
        </div>
        <form v-if="impresa.aperta" class="card card-body mb-3" @submit.prevent="nuovaImpresa">
          <div class="row g-3">
            <div v-if="dati.puo_gestire" class="col-12 md:col-6">
              <label class="form-label small" for="imp-livello">Di chi</label>
              <select
                id="imp-livello"
                v-model="impresa.livello"
                class="form-control form-control-sm"
              >
                <option value="SQUADRIGLIA">Di squadriglia</option>
                <option value="REPARTO">Di reparto</option>
                <option value="ALTA_SQ">Di Alta Squadriglia</option>
              </select>
            </div>
            <div v-if="impresa.livello === 'SQUADRIGLIA'" class="col-12 md:col-6">
              <label class="form-label small" for="imp-sq">Squadriglia</label>
              <select
                id="imp-sq"
                v-model="impresa.squadriglia_id"
                class="form-control form-control-sm"
                required
              >
                <option :value="null" disabled>—</option>
                <option v-for="s in dati.squadriglie" :key="s.id" :value="s.id">
                  {{ s.nome }}
                </option>
              </select>
            </div>
            <div class="col-12">
              <label class="form-label small" for="imp-titolo">Titolo</label>
              <input
                id="imp-titolo"
                v-model="impresa.titolo"
                class="form-control form-control-sm"
                required
              />
            </div>
            <div class="col-12">
              <label class="form-label small" for="imp-descr">Descrizione</label>
              <textarea
                id="imp-descr"
                v-model="impresa.descrizione"
                class="form-control form-control-sm"
                rows="2"
              />
            </div>
            <div class="col-12 md:col-6">
              <label class="form-label small" for="imp-dal">Dal</label>
              <input
                id="imp-dal"
                v-model="impresa.dal"
                type="date"
                class="form-control form-control-sm"
                required
              />
            </div>
            <div class="col-12 md:col-6">
              <label class="form-label small" for="imp-al">Al</label>
              <input
                id="imp-al"
                v-model="impresa.al"
                type="date"
                class="form-control form-control-sm"
              />
            </div>
          </div>
          <div class="d-flex gap-3 mt-3">
            <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
              Salva
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="impresa.aperta = false">
              Annulla
            </button>
          </div>
        </form>
        <p v-if="!dati.imprese.length" class="small fg-2">Nessuna impresa.</p>
        <div v-for="i in dati.imprese" :key="i.id" class="card card-body mb-3">
          <div class="d-flex flex-wrap justify-content-between gap-3">
            <strong>{{ i.titolo }}</strong>
            <span class="small fg-2">
              {{ i.livello_nome }}<template v-if="i.squadriglia"> · {{ i.squadriglia }}</template> ·
              dal {{ data(i.dal) }}<template v-if="i.al"> al {{ data(i.al) }}</template>
            </span>
          </div>
          <p v-if="i.descrizione" class="small testo-a-capo mb-1">{{ i.descrizione }}</p>
          <ul v-if="i.posti.length" class="small mb-1">
            <li v-for="p in i.posti" :key="p.id">
              {{ p.persona }}: <strong>{{ p.ruolo }}</strong>
              <template v-if="p.verificato_il">
                · verificato il {{ data(p.verificato_il) }} ({{ p.sede_nome }})</template
              >
              <button
                v-else-if="i.puo_gestire_posti"
                type="button"
                class="btn btn-sm btn-link"
                @click="
                  Object.assign(verifica, {
                    posto: p.id,
                    il: oggi(),
                    sede: '',
                    sede_descrizione: '',
                  })
                "
              >
                Verifica…
              </button>
              <form
                v-if="verifica.posto === p.id"
                class="d-flex flex-wrap align-items-end gap-3 my-1"
                @submit.prevent="verificaPosto"
              >
                <div>
                  <label class="form-label small" :for="`v-il-${p.id}`">Il</label>
                  <input
                    :id="`v-il-${p.id}`"
                    v-model="verifica.il"
                    type="date"
                    :max="oggi()"
                    class="form-control form-control-sm"
                    required
                  />
                </div>
                <div>
                  <label class="form-label small" :for="`v-sede-${p.id}`">Dove</label>
                  <select
                    :id="`v-sede-${p.id}`"
                    v-model="verifica.sede"
                    class="form-control form-control-sm"
                    required
                  >
                    <option value="" disabled>—</option>
                    <option v-for="s in dati.sedi" :key="s.valore" :value="s.valore">
                      {{ s.etichetta }}
                    </option>
                  </select>
                </div>
                <div v-if="verifica.sede === 'ALTRO'">
                  <label class="form-label small" :for="`v-d-${p.id}`">Quale</label>
                  <input
                    :id="`v-d-${p.id}`"
                    v-model="verifica.sede_descrizione"
                    class="form-control form-control-sm"
                    required
                  />
                </div>
                <button
                  type="submit"
                  class="btn btn-sm btn-solid theme-success"
                  :disabled="inCorso"
                >
                  Registra
                </button>
              </form>
            </li>
          </ul>
          <p v-if="i.livello !== 'SQUADRIGLIA'" class="small mb-1">
            <strong>Consiglio d'impresa</strong>:
            {{ i.consiglio.length ? i.consiglio.map((c) => c.nome).join(', ') : 'non nominato' }}
            <button
              v-if="dati.puo_gestire && consiglio.impresa !== i.id"
              type="button"
              class="btn btn-sm btn-link"
              @click="
                Object.assign(consiglio, { impresa: i.id, persone: i.consiglio.map((c) => c.id) })
              "
            >
              Nomina…
            </button>
          </p>
          <form
            v-if="consiglio.impresa === i.id"
            class="card card-body mb-1"
            @submit.prevent="salvaConsiglio"
          >
            <fieldset class="mb-3">
              <legend class="form-label small">
                Chi fa parte del Consiglio d'impresa (assegna e verifica i posti d'azione)
              </legend>
              <div v-for="r in dati.ragazzi" :key="r.id" class="form-field">
                <input
                  :id="`ci-${i.id}-${r.id}`"
                  v-model="consiglio.persone"
                  type="checkbox"
                  class="check"
                  :value="r.id"
                />
                <label class="small" :for="`ci-${i.id}-${r.id}`">{{ r.nome }}</label>
              </div>
            </fieldset>
            <div class="d-flex gap-3">
              <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
                Salva
              </button>
              <button type="button" class="btn btn-sm btn-link" @click="consiglio.impresa = 0">
                Annulla
              </button>
            </div>
          </form>
          <template v-if="i.puo_gestire_posti">
            <button
              v-if="posto.impresa !== i.id"
              type="button"
              class="btn btn-sm btn-link align-self-start"
              @click="Object.assign(posto, { impresa: i.id, persona_id: 0, ruolo: '' })"
            >
              Aggiungi un posto d'azione
            </button>
            <form
              v-else
              class="d-flex flex-wrap align-items-end gap-3"
              @submit.prevent="nuovoPosto"
            >
              <div>
                <label class="form-label small" :for="`p-chi-${i.id}`">Chi</label>
                <select
                  :id="`p-chi-${i.id}`"
                  v-model="posto.persona_id"
                  class="form-control form-control-sm"
                  required
                >
                  <option :value="0" disabled>—</option>
                  <option v-for="r in dati.ragazzi" :key="r.id" :value="r.id">{{ r.nome }}</option>
                </select>
              </div>
              <div class="flex-grow-1">
                <label class="form-label small" :for="`p-ruolo-${i.id}`">Posto d'azione</label>
                <input
                  :id="`p-ruolo-${i.id}`"
                  v-model="posto.ruolo"
                  class="form-control form-control-sm"
                  required
                />
              </div>
              <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
                Aggiungi
              </button>
              <button type="button" class="btn btn-sm btn-link" @click="posto.impresa = 0">
                Annulla
              </button>
            </form>
          </template>
        </div>
      </section>

      <section v-if="sessione.profilo?.capo" class="mb-5">
        <h2 class="h5">Specialità di squadriglia</h2>
        <p class="small fg-2">
          Le conquista la squadriglia: i suoi membri non ricevono per questo una specialità
          personale. Si possono collegare le specialità e i brevetti dei singoli nati dal percorso.
        </p>
        <div v-for="s in dati.squadriglie" :key="s.id" class="mb-3">
          <div class="d-flex flex-wrap align-items-center gap-3 mb-1">
            <h3 class="h6 fw-bold mb-0">{{ s.nome }}</h3>
            <button
              v-if="dati.puo_gestire && specialita.squadriglia !== s.id"
              type="button"
              class="btn btn-sm btn-link"
              @click="apriSpecialita(s.id)"
            >
              Aggiungi
            </button>
          </div>
          <form
            v-if="specialita.squadriglia === s.id"
            class="card card-body mb-1"
            @submit.prevent="nuovaSpecialita"
          >
            <label class="form-label small" :for="`sq-voce-${s.id}`"
              >Specialità di squadriglia</label
            >
            <select
              :id="`sq-voce-${s.id}`"
              v-model="specialita.codice"
              class="form-control form-control-sm mb-3"
              required
            >
              <option value="" disabled>—</option>
              <option
                v-for="v in cataloghi?.specialita_squadriglia ?? []"
                :key="v.codice"
                :value="v.codice"
              >
                {{ v.nome }}
              </option>
            </select>
            <div class="form-field mb-3">
              <input
                :id="`sq-passata-${s.id}`"
                v-model="specialita.passata"
                type="checkbox"
                class="check"
              />
              <label class="small" :for="`sq-passata-${s.id}`">Già conquistata in passato</label>
            </div>
            <InputDataParziale
              v-if="specialita.passata"
              :id="`sq-quando-${s.id}`"
              v-model="specialita.quando"
              etichetta="Conquistata il"
              class="mb-3"
            />
            <template v-else>
              <label class="form-label small" :for="`sq-carta-${s.id}`">Carta</label>
              <textarea
                :id="`sq-carta-${s.id}`"
                v-model="specialita.carta"
                class="form-control form-control-sm mb-3"
                rows="2"
              />
            </template>
            <div class="d-flex gap-3">
              <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
                Salva
              </button>
              <button type="button" class="btn btn-sm btn-link" @click="specialita.squadriglia = 0">
                Annulla
              </button>
            </div>
          </form>
          <p v-if="!s.competenze.length" class="small fg-2 mb-0">Nessuna.</p>
          <ul v-else class="list-group">
            <CompetenzaEG
              v-for="c in s.competenze"
              :key="c.id"
              :voce="c"
              :gestisce="dati.puo_gestire"
              :propone-verifica="dati.puo_gestire"
              :collegabili="s.individuali"
              @cambiata="dopoScrittura"
            />
          </ul>
        </div>
      </section>
    </template>
  </section>
</template>
