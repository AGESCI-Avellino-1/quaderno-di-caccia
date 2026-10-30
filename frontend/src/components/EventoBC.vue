<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import {
  api,
  euro,
  nomeUnita,
  type DettaglioBC,
  type IscrizioneBC,
  type IscrizioneBCIn,
  type PersonaElenco,
  type SchedaBC,
  type Unita,
} from '@/api/qdc'
import IscrizioneBCVue from '@/components/IscrizioneBC.vue'
import { useErrore } from '@/composables/useErrore'
import { useSessioneStore } from '@/stores/sessione'

// An event on BuonaCaccia (DEC-158…DEC-164): the registrations of minors, recorded by the
// staff of their unit, with what the family has to do; the adults who take part (for a
// capi training camp also the fee they paid). Online only.
const props = defineProps<{ evento: number }>()
const sessione = useSessioneStore()
const { errore, inCorso, esegui } = useErrore()
const dettaglio = ref<DettaglioBC | null>(null)
const schede = ref<SchedaBC[]>([])
const oggi = () => new Date().toLocaleDateString('sv')

async function carica() {
  dettaglio.value = (await esegui(() => api.eventoBC(props.evento))) ?? null
}
watch(() => props.evento, carica, { immediate: true })

function cambiata(nuova: IscrizioneBC) {
  if (!dettaglio.value) return
  dettaglio.value.iscrizioni = dettaglio.value.iscrizioni.map((i) =>
    i.id === nuova.id ? nuova : i,
  )
}

// --- The event form -----------------------------------------------------------------

const sceltaScheda = ref<number | null>(null)
async function apriSchede() {
  schede.value = (await esegui(() => api.schedeBC())) ?? []
  sceltaScheda.value = dettaglio.value?.scheda?.id ?? null
}
async function salvaScheda() {
  const dati = await esegui(() => api.schedaEventoBC(props.evento, sceltaScheda.value))
  if (dati) {
    dettaglio.value = dati
    schede.value = []
  }
}

// --- New registration ---------------------------------------------------------------

const unita = ref<Unita[]>([])
const persone = ref<PersonaElenco[]>([])
const unitaScelta = ref<number | null>(null)
const nuova = ref<IscrizioneBCIn | null>(null)

async function apriIscrizione() {
  nuova.value = {
    persona_id: 0,
    iscritto_il: oggi(),
    stato: 'AMMESSO',
    link_gestione: '',
    modo_liberatoria: 'APP',
    scadenza_liberatoria: null,
    importo: null,
    scadenza_quota: null,
  }
  unita.value = ((await esegui(() => api.unita())) ?? []).filter((u) => u.tipo !== 'COMUNITA_CAPI')
}
watch(unitaScelta, async (id) => {
  persone.value = id === null ? [] : ((await esegui(() => api.persone(id))) ?? [])
})

async function iscrivi() {
  if (!nuova.value) return
  const dati = { ...nuova.value, importo: nuova.value.importo || null }
  if (!dati.importo) dati.scadenza_quota = null
  if (await esegui(() => api.iscriviBC(props.evento, dati))) {
    nuova.value = null
    await carica()
  }
}

// --- Adults (DEC-164) ----------------------------------------------------------------

const quote = reactive<Record<number, string>>({})
watch(dettaglio, (d) => {
  for (const a of d?.adulti ?? []) quote[a.persona_id] = a.quota_versata ?? ''
})

async function partecipo(persona: number, partecipa: boolean) {
  const dati = await esegui(() =>
    api.partecipanteBC(props.evento, {
      persona_id: persona,
      partecipa,
      quota_versata: quote[persona] || null,
    }),
  )
  if (dati) dettaglio.value = dati
}

const io = () => sessione.profilo?.persona?.id
</script>

<template>
  <section v-if="dettaglio" class="mb-5">
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <p v-if="dettaglio.formazione_capi" class="small">
      <strong>Formazione capi</strong> · {{ dettaglio.tipo_campo_nome }}
    </p>

    <!-- Event form -->
    <section v-if="dettaglio.iscrizioni.length || dettaglio.puo_gestire" class="mb-5">
      <h2 class="h5">Scheda dell'evento</h2>
      <p class="small mb-1">
        <template v-if="dettaglio.scheda">
          {{ dettaglio.scheda.nome }} (versione {{ dettaglio.scheda.numero }}):
          {{ dettaglio.scheda.domande.length }} domande{{
            dettaglio.scheda.chiede_foto ? ', con foto' : ''
          }}.
        </template>
        <template v-else>Nessuna scheda: le domande le prepara lo staff.</template>
      </p>
      <template v-if="dettaglio.puo_gestire">
        <button
          v-if="!schede.length"
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          @click="apriSchede"
        >
          {{ dettaglio.scheda ? 'Cambia la scheda' : 'Scegli la scheda' }}
        </button>
        <form v-else class="d-flex flex-wrap align-items-end gap-3" @submit.prevent="salvaScheda">
          <div>
            <label class="form-label small" for="scheda-evento">Scheda</label>
            <select id="scheda-evento" v-model="sceltaScheda" class="form-control form-control-sm">
              <option :value="null">Nessuna</option>
              <option v-for="s in schede" :key="s.id" :value="s.ultima.id">
                {{ s.nome }} (versione {{ s.ultima.numero }})
              </option>
              <option
                v-if="
                  dettaglio.scheda && !schede.some((s) => s.ultima.id === dettaglio!.scheda!.id)
                "
                :value="dettaglio.scheda.id"
              >
                {{ dettaglio.scheda.nome }} (versione {{ dettaglio.scheda.numero }})
              </option>
            </select>
          </div>
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Salva
          </button>
          <RouterLink to="/buonacaccia/schede" class="small">Prepara o cambia le schede</RouterLink>
        </form>
      </template>
    </section>

    <!-- Registrations of minors -->
    <section class="mb-5">
      <div class="d-flex flex-wrap align-items-center gap-3 mb-3">
        <h2 class="h5 mb-0">Iscrizioni su BuonaCaccia</h2>
        <button
          v-if="dettaglio.puo_iscrivere && !nuova && !dettaglio.annullato"
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          @click="apriIscrizione"
        >
          Registra un'iscrizione
        </button>
      </div>
      <form v-if="nuova" class="card card-body mb-3" @submit.prevent="iscrivi">
        <p class="small fg-2">
          Registra qui un ragazzo minorenne che lo staff ha già iscritto su BuonaCaccia. I
          maggiorenni si iscrivono da soli: segna solo la loro partecipazione qui sotto.
        </p>
        <div class="row g-3">
          <div class="col-12 md:col-6">
            <label class="form-label small" for="bc-unita">Unità</label>
            <select id="bc-unita" v-model="unitaScelta" class="form-control form-control-sm">
              <option :value="null">—</option>
              <option v-for="u in unita" :key="u.id" :value="u.id">{{ nomeUnita(u) }}</option>
            </select>
          </div>
          <div class="col-12 md:col-6">
            <label class="form-label small" for="bc-persona">Ragazzo</label>
            <select
              id="bc-persona"
              v-model="nuova.persona_id"
              class="form-control form-control-sm"
              required
            >
              <option :value="0" disabled>—</option>
              <option v-for="p in persone" :key="p.id" :value="p.id">
                {{ p.cognome }} {{ p.nome }}
              </option>
            </select>
          </div>
          <div class="col-12 md:col-6">
            <label class="form-label small" for="bc-data">Iscritto su BuonaCaccia il</label>
            <input
              id="bc-data"
              v-model="nuova.iscritto_il"
              type="date"
              :max="oggi()"
              class="form-control form-control-sm"
              required
            />
          </div>
          <div class="col-12 md:col-6">
            <label class="form-label small" for="bc-stato">Stato</label>
            <select id="bc-stato" v-model="nuova.stato" class="form-control form-control-sm">
              <option value="AMMESSO">Ammesso</option>
              <option value="IN_ATTESA">In lista d'attesa</option>
            </select>
          </div>
          <div class="col-12">
            <label class="form-label small" for="bc-link">
              Link di gestione (dalla prima email di BuonaCaccia; lo vedono solo i capi che
              gestiscono l'iscrizione)
            </label>
            <input
              id="bc-link"
              v-model="nuova.link_gestione"
              type="url"
              class="form-control form-control-sm"
            />
          </div>
          <div class="col-12 md:col-6">
            <label class="form-label small" for="bc-modo">La liberatoria</label>
            <select
              id="bc-modo"
              v-model="nuova.modo_liberatoria"
              class="form-control form-control-sm"
            >
              <option value="APP">passa dall'app</option>
              <option value="ALTRI_CANALI">arriva per altri canali</option>
            </select>
          </div>
          <div class="col-12 md:col-6">
            <label class="form-label small" for="bc-scad-lib">
              Scadenza della liberatoria (vuota: 2 giorni prima della scadenza dell'iscrizione)
            </label>
            <input
              id="bc-scad-lib"
              v-model="nuova.scadenza_liberatoria"
              type="date"
              class="form-control form-control-sm"
            />
          </div>
          <div class="col-12 md:col-6">
            <label class="form-label small" for="bc-importo">
              Quota per la famiglia (€, anche in lista d'attesa)
            </label>
            <input
              id="bc-importo"
              v-model="nuova.importo"
              type="number"
              min="0"
              step="0.01"
              class="form-control form-control-sm"
            />
          </div>
          <div class="col-12 md:col-6">
            <label class="form-label small" for="bc-scad-q">Da pagare entro</label>
            <input
              id="bc-scad-q"
              v-model="nuova.scadenza_quota"
              type="date"
              class="form-control form-control-sm"
              :required="!!nuova.importo"
            />
          </div>
        </div>
        <div class="d-flex gap-3 mt-3">
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Registra
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="nuova = null">Annulla</button>
        </div>
      </form>
      <ul v-if="dettaglio.iscrizioni.length" class="list-group">
        <IscrizioneBCVue
          v-for="i in dettaglio.iscrizioni"
          :key="i.id"
          :iscrizione="i"
          :scheda="dettaglio.scheda"
          @cambiata="cambiata"
        />
      </ul>
      <p v-else class="small fg-2">Nessuna iscrizione di ragazzi minorenni.</p>
    </section>

    <!-- Adults (DEC-164) -->
    <section v-if="dettaglio.adulti.length || dettaglio.puo_partecipare" class="mb-5">
      <h2 class="h5">Maggiorenni che partecipano</h2>
      <p class="small fg-2">
        R/S maggiorenni e capi si iscrivono da soli su BuonaCaccia: qui si segna solo che
        partecipano<template v-if="dettaglio.formazione_capi">
          e la quota versata, per l'elenco della Zona</template
        >.
      </p>
      <ul v-if="dettaglio.adulti.length" class="list-group mb-3">
        <li v-for="a in dettaglio.adulti" :key="a.persona_id" class="list-group-item">
          <div class="d-flex flex-wrap align-items-end justify-content-between gap-3">
            <span>
              {{ a.persona }}
              <span v-if="!a.partecipa" class="badge theme-warning ms-1">Non partecipa</span>
              <span v-if="a.quota_versata && !a.puo_modificare" class="small">
                · quota {{ euro(a.quota_versata) }}
              </span>
            </span>
            <form
              v-if="a.puo_modificare"
              class="d-flex flex-wrap align-items-end gap-3"
              @submit.prevent="partecipo(a.persona_id, true)"
            >
              <div v-if="dettaglio.formazione_capi">
                <label class="form-label small" :for="`versata-${a.persona_id}`"
                  >Quota versata (€)</label
                >
                <input
                  :id="`versata-${a.persona_id}`"
                  v-model="quote[a.persona_id]"
                  type="number"
                  min="0"
                  step="0.01"
                  class="form-control form-control-sm"
                />
              </div>
              <button
                v-if="dettaglio.formazione_capi"
                type="submit"
                class="btn btn-sm btn-outline theme-primary"
                :disabled="inCorso"
              >
                Salva
              </button>
              <button
                type="button"
                class="btn btn-sm btn-link"
                :disabled="inCorso"
                @click="partecipo(a.persona_id, false)"
              >
                Togli
              </button>
            </form>
          </div>
        </li>
      </ul>
      <button
        v-if="
          dettaglio.puo_partecipare && io() && !dettaglio.adulti.some((a) => a.persona_id === io())
        "
        type="button"
        class="btn btn-sm btn-outline theme-primary"
        :disabled="inCorso || dettaglio.annullato"
        @click="partecipo(io()!, true)"
      >
        Partecipo anch'io
      </button>
    </section>
  </section>
</template>
