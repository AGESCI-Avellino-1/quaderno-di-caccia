<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import {
  api,
  quandoParziale,
  type DataParziale,
  type FascicoloCapo,
  type FormazioneIn,
} from '@/api/qdc'
import InputDataParziale from '@/components/InputDataParziale.vue'
import { useErrore } from '@/composables/useErrore'
import { useNomePersona } from '@/composables/useNomePagina'

// The capi's file (DEC-47, DEC-134, DEC-206…DEC-208): read by the capo and the whole
// Co.Ca.; the years before the app and the training are written by the capo or a
// capogruppo. The years with the app come from the roles; the BuonaStrada level stays
// BuonaStrada's; the capi training camps recorded as BuonaCaccia events show by
// themselves. Online only.
const props = defineProps<{ id: number }>()
const { errore, inCorso, esegui } = useErrore()
const dati = ref<FascicoloCapo | null>(null)
useNomePersona(
  () => props.id,
  () => dati.value?.persona,
)
const esito = ref('')

async function carica() {
  dati.value = (await esegui(() => api.fascicoloCapo(props.id))) ?? null
}
watch(() => props.id, carica, { immediate: true })

async function fatto(azione: () => Promise<FascicoloCapo>, messaggio: string) {
  esito.value = ''
  const nuovi = await esegui(azione)
  if (!nuovi) return false
  dati.value = nuovi
  esito.value = messaggio
  return true
}

// --- Years before the app ------------------------------------------------------------
const servizio = reactive({ aperto: false, anno: 0, unita_testo: '', ruolo: 'STAFF', note: '' })
async function salvaServizio() {
  const ok = await fatto(
    () =>
      api.nuovoServizioPassato(props.id, {
        anno: servizio.anno,
        unita_testo: servizio.unita_testo,
        ruolo: servizio.ruolo,
        note: servizio.note,
      }),
    'Anno di servizio aggiunto.',
  )
  if (ok) Object.assign(servizio, { aperto: false, unita_testo: '', note: '' })
}

// --- Training -----------------------------------------------------------------------
const vuota = (): FormazioneIn => ({
  tipo: 'CFT',
  specifica: '',
  data: '',
  precisione: 'ANNO',
  luogo: '',
  note: '',
})
// 0: closed; -1: new; otherwise the entry being changed.
const aperta = ref(0)
const formazione = reactive<FormazioneIn>(vuota())
const quando = ref<DataParziale>({ data: null, precisione: 'ANNO' })

function apri(voce: FascicoloCapo['formazione'][number] | null) {
  aperta.value = voce?.id ?? -1
  Object.assign(formazione, voce ? { ...voce } : vuota())
  quando.value = voce
    ? { data: voce.data, precisione: voce.precisione }
    : { data: null, precisione: 'ANNO' }
}

async function salvaFormazione() {
  if (!quando.value.data) {
    errore.value = 'Indica almeno l’anno.'
    return
  }
  const corpo = { ...formazione, data: quando.value.data, precisione: quando.value.precisione }
  const ok = await fatto(
    () =>
      aperta.value === -1
        ? api.nuovaFormazione(props.id, corpo)
        : api.modificaFormazione(aperta.value, corpo),
    'Formazione salvata.',
  )
  if (ok) aperta.value = 0
}

const togliServizio = (id: number) => fatto(() => api.togliServizioPassato(id), 'Tolto.')
const togliFormazione = (id: number) => fatto(() => api.togliFormazione(id), 'Tolta.')

const oggi = new Date().toLocaleDateString('sv')

const serveSpecifica = () => formazione.tipo === 'MODULO' || formazione.tipo === 'ALTRO'
</script>

<template>
  <section style="max-width: 50rem">
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>
    <p v-if="inCorso && !dati" class="fg-2">Caricamento…</p>
    <template v-if="dati">
      <h1 class="h4 mb-1">Servizio e formazione di {{ dati.persona }}</h1>
      <RouterLink :to="{ name: 'persona', params: { id: dati.persona_id } }" class="small">
        Scheda della persona
      </RouterLink>

      <dl class="row small mt-3 mb-5">
        <dt class="col-12 md:col-5">Anni di servizio registrati</dt>
        <dd class="col-12 md:col-7">{{ dati.anni_di_servizio }}</dd>
        <dt class="col-12 md:col-5">In Comunità capi dal (BuonaStrada)</dt>
        <dd class="col-12 md:col-7">{{ dati.anno_ingresso_coca ?? 'non indicato' }}</dd>
        <dt class="col-12 md:col-5">Livello di formazione (BuonaStrada)</dt>
        <dd class="col-12 md:col-7">{{ dati.livello_formazione ?? 'non indicato' }}</dd>
        <template v-if="dati.numero_nomina || dati.data_nomina">
          <dt class="col-12 md:col-5">Nomina a capo</dt>
          <dd class="col-12 md:col-7">
            {{ dati.numero_nomina }}
            <template v-if="dati.data_nomina">
              del {{ new Date(dati.data_nomina).toLocaleDateString('it-IT') }}
            </template>
          </dd>
        </template>
      </dl>

      <section class="mb-5">
        <div class="d-flex flex-wrap align-items-center gap-3 mb-3">
          <h2 class="h5 mb-0">Anni di servizio</h2>
          <button
            v-if="dati.puo_modificare && !servizio.aperto"
            type="button"
            class="btn btn-sm btn-outline theme-primary"
            @click="Object.assign(servizio, { aperto: true, anno: dati.anni.at(-1)?.anno ?? 2020 })"
          >
            Aggiungi un anno prima dell'app
          </button>
        </div>
        <form v-if="servizio.aperto" class="card card-body mb-3" @submit.prevent="salvaServizio">
          <div class="row g-3">
            <div class="col-6 md:col-3">
              <label class="form-label small" for="srv-anno">Anno (fine)</label>
              <input
                id="srv-anno"
                v-model.number="servizio.anno"
                type="number"
                min="1951"
                class="form-control form-control-sm"
                required
              />
            </div>
            <div class="col-6 md:col-4">
              <label class="form-label small" for="srv-ruolo">Ruolo</label>
              <select id="srv-ruolo" v-model="servizio.ruolo" class="form-control form-control-sm">
                <option v-for="r in dati.ruoli_passati" :key="r.valore" :value="r.valore">
                  {{ r.etichetta }}
                </option>
              </select>
            </div>
            <div class="col-12 md:col-5">
              <label class="form-label small" for="srv-unita">Unità</label>
              <input
                id="srv-unita"
                v-model="servizio.unita_testo"
                class="form-control form-control-sm"
                maxlength="120"
                placeholder="Es. Reparto Orsa Maggiore"
              />
            </div>
            <div class="col-12">
              <label class="form-label small" for="srv-note">
                Note{{ servizio.ruolo === 'ALTRO' ? ' (quale ruolo)' : '' }}
              </label>
              <input
                id="srv-note"
                v-model="servizio.note"
                class="form-control form-control-sm"
                maxlength="300"
              />
            </div>
          </div>
          <p class="small fg-2 mt-1 mb-3">
            L'anno associativo si indica con l'anno in cui finisce: 2014/15 è 2015.
          </p>
          <div class="d-flex gap-3">
            <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
              Salva
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="servizio.aperto = false">
              Annulla
            </button>
          </div>
        </form>
        <p v-if="!dati.anni.length" class="small fg-2">Nessun anno registrato.</p>
        <ul v-else class="list-group">
          <li v-for="a in dati.anni" :key="a.anno" class="list-group-item small">
            <strong>{{ a.etichetta }}</strong>
            <template v-if="a.ruoli.length"> · {{ a.ruoli.join('; ') }}</template>
            <template v-else-if="a.in_coca && !a.ricostruiti.length"> · in Comunità capi</template>
            <div v-for="r in a.ricostruiti" :key="r.id">
              <span class="badge theme-secondary me-1">ricostruito</span>{{ r.testo }}
              <button
                v-if="dati.puo_modificare"
                type="button"
                class="btn btn-sm btn-link py-0"
                :disabled="inCorso"
                @click="togliServizio(r.id)"
              >
                Togli
              </button>
            </div>
          </li>
        </ul>
      </section>

      <section class="mb-5">
        <div class="d-flex flex-wrap align-items-center gap-3 mb-3">
          <h2 class="h5 mb-0">Formazione</h2>
          <button
            v-if="dati.puo_modificare && !aperta"
            type="button"
            class="btn btn-sm btn-outline theme-primary"
            @click="apri(null)"
          >
            Aggiungi
          </button>
        </div>
        <form v-if="aperta" class="card card-body mb-3" @submit.prevent="salvaFormazione">
          <div class="row g-3">
            <div class="col-12 md:col-6">
              <label class="form-label small" for="frm-tipo">Tipo</label>
              <select id="frm-tipo" v-model="formazione.tipo" class="form-control form-control-sm">
                <option v-for="t in dati.tipi_formazione" :key="t.valore" :value="t.valore">
                  {{ t.etichetta }}
                </option>
              </select>
            </div>
            <div v-if="serveSpecifica()" class="col-12 md:col-6">
              <label class="form-label small" for="frm-spec">
                {{ formazione.tipo === 'MODULO' ? 'Titolo del modulo' : 'Che cosa' }}
              </label>
              <input
                id="frm-spec"
                v-model="formazione.specifica"
                class="form-control form-control-sm"
                maxlength="160"
                required
              />
            </div>
            <div class="col-12 md:col-6">
              <InputDataParziale id="frm-data" v-model="quando" etichetta="Quando" />
            </div>
            <div class="col-12 md:col-6">
              <label class="form-label small" for="frm-luogo">Luogo</label>
              <input
                id="frm-luogo"
                v-model="formazione.luogo"
                class="form-control form-control-sm"
                maxlength="120"
              />
            </div>
            <div class="col-12">
              <label class="form-label small" for="frm-note">Note</label>
              <input
                id="frm-note"
                v-model="formazione.note"
                class="form-control form-control-sm"
                maxlength="300"
              />
            </div>
          </div>
          <div class="d-flex gap-3 mt-3">
            <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
              Salva
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="aperta = 0">Annulla</button>
          </div>
        </form>
        <p v-if="!dati.formazione.length" class="small fg-2">Nessuna formazione registrata.</p>
        <ul v-else class="list-group">
          <li
            v-for="(f, n) in dati.formazione"
            :key="f.id ?? `bc-${n}`"
            class="list-group-item small"
          >
            <strong>{{ f.tipo_nome }}</strong>
            <template v-if="f.specifica"> · {{ f.specifica }}</template>
            · {{ quandoParziale({ data: f.data, precisione: f.precisione }) }}
            <template v-if="f.luogo"> · {{ f.luogo }}</template>
            <span v-if="f.da_buonacaccia" class="badge theme-info ms-1">da BuonaCaccia</span>
            <span v-if="f.data > oggi" class="badge theme-warning ms-1">in programma</span>
            <div v-if="f.note" class="fg-2">{{ f.note }}</div>
            <div v-if="dati.puo_modificare && f.id && !aperta" class="d-flex gap-1">
              <button type="button" class="btn btn-sm btn-link px-0" @click="apri(f)">
                Modifica
              </button>
              <button
                type="button"
                class="btn btn-sm btn-link"
                :disabled="inCorso"
                @click="togliFormazione(f.id!)"
              >
                Togli
              </button>
            </div>
          </li>
        </ul>
      </section>
    </template>
  </section>
</template>
