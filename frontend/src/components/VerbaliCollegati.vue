<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  api,
  verbaleCollegatoPdf,
  type DatiCapiGruppo,
  type PersonaBreve,
  type VerbaleCollegato,
} from '@/api/qdc'
import CampiLuogo from '@/components/CampiLuogo.vue'
import SceltaPersona from '@/components/SceltaPersona.vue'
import { opzioniDa } from '@/components/sceltaPersona'
import { useErrore } from '@/composables/useErrore'

// Separate minutes of the same meeting from a template, produced only when needed, with
// their own state and PDF (DEC-339). Online only. The text is asked for when opened: reading
// the Co.Ca.'s goes to the access log (DEC-329).
const props = defineProps<{ evento: number }>()
const { errore, inCorso, esegui } = useErrore()
const collegati = ref<VerbaleCollegato[]>([])
const daAggiungere = ref<string[]>([])
const candidati = ref<PersonaBreve[]>([])
const caricato = ref(false)
const aperti = ref<Record<string, VerbaleCollegato>>({})
const riapertura = ref<Record<string, string>>({})
const conferma = ref<string | null>(null)
const daTogliere = ref<string | null>(null)
const salvato = ref(false)
const dati = ref<DatiCapiGruppo | null>(null)

const nuovoLuogo = () => ({ presso: '', via: '', civico: '', cap: '', citta: '', provincia: '' })

async function leggi() {
  const elenco = await api.verbaliCollegati(props.evento)
  collegati.value = elenco.collegati
  daAggiungere.value = elenco.da_aggiungere
  candidati.value = elenco.candidati_capi_gruppo
  caricato.value = true
}

onMounted(async () => {
  try {
    await leggi()
  } catch {
    // This meeting has none, or they are not for this user: nothing to show.
    caricato.value = false
  }
})

function apriDati(collegato: VerbaleCollegato) {
  aperti.value[collegato.tipo] = collegato
  if (collegato.dati) dati.value = collegato.dati
}

async function apri(tipo: string) {
  const collegato = await esegui(() => api.verbaleCollegato(props.evento, tipo))
  if (collegato) apriDati(collegato)
}

async function aggiungi() {
  const vuoti: DatiCapiGruppo = {
    ora_apertura: '',
    ora_chiusura: '',
    luogo: nuovoLuogo(),
    cambia_capi_gruppo: false,
    capi_gruppo: [],
    cambia_rappresentante: false,
    rappresentante: null,
    cambia_sede: false,
    sede: nuovoLuogo(),
    varie: '',
  }
  const collegato = await esegui(() => api.salvaCapiGruppo(props.evento, vuoti))
  if (!collegato) return
  await leggi()
  apriDati(collegato)
}

async function salva() {
  if (!dati.value) return
  salvato.value = false
  const corpo = dati.value
  const collegato = await esegui(() => api.salvaCapiGruppo(props.evento, corpo))
  if (!collegato) return
  apriDati(collegato)
  salvato.value = true
}

async function definitivo(tipo: string) {
  const collegato = await esegui(() => api.verbaleCollegatoDefinitivo(props.evento, tipo))
  conferma.value = null
  if (!collegato) return
  await leggi()
  apriDati(collegato)
}

async function riapri(tipo: string) {
  const motivo = riapertura.value[tipo] ?? ''
  const collegato = await esegui(() => api.riapriVerbaleCollegato(props.evento, tipo, motivo))
  if (!collegato) return
  delete riapertura.value[tipo]
  await leggi()
  apriDati(collegato)
}

async function togli(tipo: string) {
  const fatto = await esegui(async () => {
    await api.togliVerbaleCollegato(props.evento, tipo)
    await leggi()
    return true
  })
  daTogliere.value = null
  if (fatto) delete aperti.value[tipo]
}

const quando = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
</script>

<template>
  <section v-if="caricato && (collegati.length || daAggiungere.length)" class="card card-body mb-5">
    <h2 class="h5 mb-3">Verbali collegati</h2>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>

    <article v-for="c in collegati" :key="c.tipo" class="mb-3">
      <div class="d-flex flex-wrap align-items-center gap-3 mb-1">
        <h3 class="h6 mb-0">{{ c.nome }}</h3>
        <span v-if="c.stato === 'DEFINITIVO'" class="badge theme-success">Definitivo</span>
        <span v-else class="badge theme-warning">Bozza</span>
      </div>
      <p v-if="c.definitivo_il" class="small fg-2 mb-1">Del {{ quando(c.definitivo_il) }}.</p>

      <button
        v-if="!aperti[c.tipo]"
        type="button"
        class="btn btn-sm btn-outline theme-primary mb-3"
        :disabled="inCorso"
        @click="apri(c.tipo)"
      >
        {{ c.stato === 'DEFINITIVO' ? 'Leggi' : 'Apri' }}
      </button>

      <template v-if="aperti[c.tipo]">
        <form
          v-if="c.tipo === 'CAPI_GRUPPO' && c.puo_gestire && c.stato === 'BOZZA' && dati"
          class="mb-3"
          @submit.prevent="salva"
        >
          <div class="row g-3 mb-3">
            <div class="col-12 sm:col-6">
              <label class="form-label small" for="cg-apertura">Ora di apertura</label>
              <input
                id="cg-apertura"
                v-model="dati.ora_apertura"
                type="time"
                class="form-control form-control-sm"
              />
            </div>
            <div class="col-12 sm:col-6">
              <label class="form-label small" for="cg-chiusura">Ora di chiusura</label>
              <input
                id="cg-chiusura"
                v-model="dati.ora_chiusura"
                type="time"
                class="form-control form-control-sm"
              />
            </div>
          </div>
          <h4 class="h6">Dove</h4>
          <CampiLuogo id="cg-luogo" v-model="dati.luogo" con-presso />

          <h4 class="h6">Cosa cambia</h4>
          <div class="form-field mb-1">
            <input
              id="cg-cambia-capi"
              v-model="dati.cambia_capi_gruppo"
              type="checkbox"
              class="check"
            />
            <label for="cg-cambia-capi">Espressione dei Capi Gruppo</label>
          </div>
          <fieldset v-if="dati.cambia_capi_gruppo" class="mb-3 ms-3">
            <legend class="form-label small">Capi Gruppo</legend>
            <div v-for="p in candidati" :key="p.id" class="form-field mb-1">
              <input
                :id="`cg-capo-${p.id}`"
                v-model="dati.capi_gruppo"
                type="checkbox"
                class="check"
                :value="p.id"
              />
              <label :for="`cg-capo-${p.id}`">{{ p.cognome }} {{ p.nome }}</label>
            </div>
          </fieldset>
          <div class="form-field mb-1">
            <input
              id="cg-cambia-rappresentante"
              v-model="dati.cambia_rappresentante"
              type="checkbox"
              class="check"
            />
            <label for="cg-cambia-rappresentante">Rappresentante legale</label>
          </div>
          <div v-if="dati.cambia_rappresentante" class="mb-3 ms-3">
            <label class="form-label small" for="cg-rappresentante">Rappresentante legale</label>
            <SceltaPersona
              id="cg-rappresentante"
              v-model="dati.rappresentante"
              :opzioni="opzioniDa(candidati)"
              vuoto="Nessuno scelto"
            />
          </div>
          <div class="form-field mb-3">
            <input id="cg-cambia-sede" v-model="dati.cambia_sede" type="checkbox" class="check" />
            <label for="cg-cambia-sede">Sede legale</label>
          </div>
          <CampiLuogo v-if="dati.cambia_sede" id="cg-sede" v-model="dati.sede" />

          <div class="mb-3">
            <label class="form-label small" for="cg-varie">Varie ed eventuali</label>
            <textarea
              id="cg-varie"
              v-model="dati.varie"
              class="form-control form-control-sm"
              rows="2"
            ></textarea>
          </div>
          <div class="d-flex flex-wrap align-items-center gap-3">
            <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
              Salva i dati
            </button>
            <span v-if="salvato" class="small fg-2" role="status">Salvato.</span>
          </div>
        </form>

        <div v-if="aperti[c.tipo]!.mancanti.length" class="alert theme-warning small" role="status">
          <div>Per renderlo definitivo manca: {{ aperti[c.tipo]!.mancanti.join('; ') }}.</div>
        </div>
        <details class="mb-3" :open="c.stato === 'DEFINITIVO'">
          <summary>{{ c.stato === 'DEFINITIVO' ? 'Testo' : 'Anteprima' }}</summary>
          <!-- eslint-disable-next-line vue/no-v-html -- built by the server from escaped data -->
          <div class="mt-3" v-html="aperti[c.tipo]!.testo"></div>
        </details>

        <div class="d-flex flex-wrap align-items-center gap-3 mb-3">
          <a
            v-if="c.stato === 'DEFINITIVO'"
            :href="verbaleCollegatoPdf(evento, c.tipo)"
            class="btn btn-sm btn-outline theme-primary"
          >
            Scarica il PDF
          </a>
          <template v-if="c.puo_gestire && c.stato === 'BOZZA'">
            <button
              v-if="conferma !== c.tipo"
              type="button"
              class="btn btn-sm btn-outline theme-primary"
              @click="conferma = c.tipo"
            >
              Rendi definitivo
            </button>
            <span v-else class="small">
              Da definitivo lo leggono tutti quelli che ne hanno diritto. Confermi?
              <button
                type="button"
                class="btn btn-sm btn-solid theme-primary py-0"
                :disabled="inCorso"
                @click="definitivo(c.tipo)"
              >
                Sì
              </button>
              <button type="button" class="btn btn-sm btn-link py-0" @click="conferma = null">
                No
              </button>
            </span>
            <button
              v-if="daTogliere !== c.tipo"
              type="button"
              class="btn btn-link btn-sm p-0"
              @click="daTogliere = c.tipo"
            >
              Non serve più
            </button>
            <span v-else class="small">
              Toglierlo?
              <button
                type="button"
                class="btn btn-sm btn-solid theme-danger py-0"
                :disabled="inCorso"
                @click="togli(c.tipo)"
              >
                Sì
              </button>
              <button type="button" class="btn btn-sm btn-link py-0" @click="daTogliere = null">
                No
              </button>
            </span>
          </template>
        </div>

        <template v-if="c.puo_gestire && c.stato === 'DEFINITIVO'">
          <form
            v-if="riapertura[c.tipo] !== undefined"
            class="row g-3 align-items-end mb-3"
            @submit.prevent="riapri(c.tipo)"
          >
            <div class="col-12 sm:col-8">
              <label class="form-label small" :for="`riapri-${c.tipo}`">Perché lo riapri</label>
              <input
                :id="`riapri-${c.tipo}`"
                v-model="riapertura[c.tipo]"
                class="form-control form-control-sm"
                maxlength="300"
                required
              />
            </div>
            <div class="col-12 sm:col-4">
              <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
                Riapri
              </button>
            </div>
          </form>
          <button
            v-else
            type="button"
            class="btn btn-link btn-sm p-0"
            @click="riapertura[c.tipo] = ''"
          >
            Riapri il verbale
          </button>
        </template>
      </template>
    </article>

    <button
      v-if="daAggiungere.includes('CAPI_GRUPPO')"
      type="button"
      class="btn btn-sm btn-outline theme-primary align-self-start"
      :disabled="inCorso"
      @click="aggiungi"
    >
      Aggiungi il verbale su Capi Gruppo, rappresentante legale o sede
    </button>
  </section>
</template>
