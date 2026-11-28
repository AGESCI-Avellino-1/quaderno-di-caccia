<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import {
  api,
  pdfVoceLibro,
  type LibroCerimonie,
  type PersonaScelta,
  type VoceLibro,
  type VoceLibroIn,
} from '@/api/qdc'
import AllegatiVoce from '@/components/AllegatiVoce.vue'
import { NOMI_AMBITO, ambitiPossibili, condizioniProposte, unitaPer } from '@/components/ambitoVoce'
import CondizioniVoce from '@/components/CondizioniVoce.vue'
import CopiaLocale from '@/components/CopiaLocale.vue'
import Icona from '@/components/Icona.vue'
import RegistroVoce from '@/components/RegistroVoce.vue'
import SceltaPersone from '@/components/SceltaPersone.vue'
import { opzioniDa, type Opzione } from '@/components/sceltaDaElenco'
import { useErrore } from '@/composables/useErrore'
import { leggiVoce } from '@/offline/cerimonie'

const EditorTesto = defineAsyncComponent(() => import('@/components/EditorTesto.vue'))

// One entry of the book of ceremonies (DEC-437): its text and PDF for who reads it; for who
// writes it (the staff of its unit, the capigruppo) the form, with the conditions, the
// ragazzi/e added by hand and who would read it today. Attachments: `AllegatiVoce`.
// Without an id: a new entry. Offline, only its text from the copy on the device (the book's
// page saves it): no PDF, attachments, register nor changes.
const props = defineProps<{ id?: number }>()
const router = useRouter()
const { errore, inCorso, esegui } = useErrore()

const voce = ref<VoceLibro | null>(null)
const libro = ref<LibroCerimonie | null>(null)
const aggiungibili = ref<Opzione[]>([])
const modulo = ref<VoceLibroIn | null>(null)
const salvata = ref(false)
const conferma = ref(false)
// Who would read it with the conditions being written; null until asked.
const lettori = ref<PersonaScelta[] | null>(null)
const copiaDel = ref<string | null>(null)

const nuova = computed(() => props.id === undefined)

function vuoto(l: LibroCerimonie): VoceLibroIn {
  const unita = unitaPer('UNITA', l.unita)[0]
  return {
    titolo: '',
    tipo: 'CERIMONIA',
    ambito: l.puo_tutto_il_gruppo || !unita ? 'GRUPPO' : 'UNITA',
    unita_ids: !l.puo_tutto_il_gruppo && unita ? [unita.id] : [],
    squadriglie_ids: [],
    testo: '',
    aggiunti: [],
    condizioni: [],
    cerimonia_del_totem: false,
    cerimonia_ingresso_alta: false,
  }
}

async function apriModulo() {
  if (!libro.value) libro.value = (await esegui(() => api.libroCerimonie())) ?? null
  if (!aggiungibili.value.length)
    aggiungibili.value = opzioniDa((await esegui(() => api.aggiungibiliVoci())) ?? [])
  if (!libro.value) return
  modulo.value = voce.value
    ? {
        titolo: voce.value.titolo,
        tipo: voce.value.tipo,
        ambito: voce.value.ambito,
        unita_ids: [...voce.value.unita_ids],
        squadriglie_ids: [...voce.value.squadriglie_ids],
        testo: voce.value.testo,
        aggiunti: [...voce.value.aggiunti],
        condizioni: JSON.parse(JSON.stringify(voce.value.condizioni)),
        cerimonia_del_totem: voce.value.cerimonia_del_totem,
        cerimonia_ingresso_alta: !!voce.value.cerimonia_ingresso_alta,
      }
    : vuoto(libro.value)
}

onMounted(async () => {
  if (nuova.value) {
    await apriModulo()
    return
  }
  const letta = await esegui(() => leggiVoce(props.id!))
  voce.value = letta?.dati ?? null
  copiaDel.value = letta?.copiaDel ?? null
})

// Whose it is (DEC-438). The units and patrols already there stay a choice even for who does
// not serve them: the staff adds only its own, the capigruppo any.
const unita = computed(() => {
  const elenco = [...(libro.value?.unita ?? [])]
  for (const id of voce.value?.unita_ids ?? []) {
    const u = libro.value?.unita_condizioni.find((x) => x.id === id)
    if (u && !elenco.some((x) => x.id === id)) elenco.push(u)
  }
  return elenco
})
const squadriglie = computed(() => {
  const elenco = [...(libro.value?.squadriglie ?? [])]
  for (const id of voce.value?.squadriglie_ids ?? []) {
    const q = libro.value?.squadriglie_condizioni.find((x) => x.id === id)
    if (q && !elenco.some((x) => x.id === id)) elenco.push(q)
  }
  return elenco
})
const ambiti = computed(() => {
  if (!libro.value) return []
  const elenco = ambitiPossibili(libro.value, unita.value, squadriglie.value)
  const attuale = modulo.value?.ambito
  return attuale && !elenco.includes(attuale) ? [attuale, ...elenco] : elenco
})
const unitaDellAmbito = computed(() =>
  modulo.value ? unitaPer(modulo.value.ambito, unita.value) : [],
)
const unitaSingola = computed({
  get: () => modulo.value?.unita_ids[0] ?? null,
  set: (id: number | null) => {
    if (modulo.value) modulo.value.unita_ids = id === null ? [] : [id]
  },
})

/** A new kind keeps the units that still fit, or takes the first one. */
function cambiaAmbito() {
  const m = modulo.value
  if (!m) return
  const possibili = unitaPer(m.ambito, unita.value).map((u) => u.id)
  const tenute = m.unita_ids.filter((id) => possibili.includes(id))
  const scelte = tenute.length ? tenute : possibili.slice(0, 1)
  m.unita_ids = m.ambito === 'UNITA' ? scelte : scelte.slice(0, 1)
  if (m.ambito !== 'SQUADRIGLIE') m.squadriglie_ids = []
  if (m.ambito !== 'GRUPPO') m.cerimonia_del_totem = false
  if (m.ambito !== 'ALTA_SQ') m.cerimonia_ingresso_alta = false
}

// The conditions follow whose the entry is while who writes has not changed them (DEC-438).
watch(
  () =>
    modulo.value && [
      modulo.value.ambito,
      [...modulo.value.unita_ids],
      [...modulo.value.squadriglie_ids],
    ],
  (nuovo, vecchio) => {
    const m = modulo.value
    if (!m || !nuovo || !vecchio) return
    const [ambito, u, q] = vecchio as [VoceLibroIn['ambito'], number[], number[]]
    const prima = JSON.stringify(condizioniProposte(ambito, u, q))
    if (m.condizioni.length && JSON.stringify(m.condizioni) !== prima) return
    m.condizioni = condizioniProposte(m.ambito, m.unita_ids, m.squadriglie_ids)
  },
)

async function chiLegge() {
  if (!modulo.value) return
  const { condizioni, aggiunti, ambito, unita_ids } = modulo.value
  lettori.value =
    (await esegui(() =>
      api.anteprimaLettori(condizioni, aggiunti, props.id, { ambito, unita_ids }),
    )) ?? null
}

async function salva() {
  if (!modulo.value) return
  salvata.value = false
  const dati = modulo.value
  const esito = await esegui(() =>
    nuova.value ? api.creaVoceLibro(dati) : api.modificaVoceLibro(props.id!, dati),
  )
  if (!esito) return
  const eraNuova = nuova.value
  voce.value = esito
  // The same page, now of the entry just created.
  if (eraNuova) await router.replace({ name: 'voce-libro', params: { id: esito.id } })
  modulo.value = null
  salvata.value = true
}

async function elimina() {
  if ((await esegui(() => api.eliminaVoceLibro(props.id!))) !== undefined)
    await router.push({ name: 'cerimonie' })
}
</script>

<template>
  <section>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <div v-if="salvata" class="alert theme-success small" role="status">Voce salvata.</div>

    <form v-if="modulo" class="card card-body" @submit.prevent="salva">
      <h1 class="h4">{{ nuova ? 'Nuova voce' : 'Modifica la voce' }}</h1>
      <div class="row g-3 mb-3">
        <div class="col-12 md:col-6">
          <label class="form-label small mb-0" for="voce-titolo">Titolo</label>
          <input
            id="voce-titolo"
            v-model="modulo.titolo"
            class="form-control"
            maxlength="200"
            required
          />
        </div>
        <div class="col-12 md:col-3">
          <label class="form-label small mb-0" for="voce-tipo">Tipo</label>
          <select id="voce-tipo" v-model="modulo.tipo" class="form-control">
            <option value="CERIMONIA">Cerimonia</option>
            <option value="TRADIZIONE">Tradizione</option>
          </select>
        </div>
        <div class="col-12 md:col-3">
          <label class="form-label small mb-0" for="voce-ambito">Di</label>
          <select
            id="voce-ambito"
            v-model="modulo.ambito"
            class="form-control"
            @change="cambiaAmbito"
          >
            <option v-for="a in ambiti" :key="a" :value="a">{{ NOMI_AMBITO[a] }}</option>
          </select>
        </div>
      </div>
      <fieldset v-if="modulo.ambito === 'UNITA'" class="mb-3" data-unita-voce>
        <legend class="form-label small mb-0">Unità</legend>
        <div class="d-flex flex-wrap gap-5">
          <div v-for="u in unitaDellAmbito" :key="u.id" class="form-field mb-0">
            <input
              :id="`voce-unita-${u.id}`"
              v-model="modulo.unita_ids"
              type="checkbox"
              class="check"
              :value="u.id"
            />
            <label :for="`voce-unita-${u.id}`">{{ u.nome }}</label>
          </div>
        </div>
      </fieldset>
      <fieldset v-else-if="modulo.ambito === 'SQUADRIGLIE'" class="mb-3" data-squadriglie-voce>
        <legend class="form-label small mb-0">Squadriglie</legend>
        <div class="d-flex flex-wrap gap-5">
          <div v-for="q in squadriglie" :key="q.id" class="form-field mb-0">
            <input
              :id="`voce-sq-${q.id}`"
              v-model="modulo.squadriglie_ids"
              type="checkbox"
              class="check"
              :value="q.id"
            />
            <label :for="`voce-sq-${q.id}`">{{ q.nome }}</label>
          </div>
        </div>
      </fieldset>
      <div v-else-if="unitaDellAmbito.length" class="mb-3 md:col-6">
        <label class="form-label small mb-0" for="voce-unita">
          {{ modulo.ambito === 'CONSIGLIO_ANZIANI' ? 'Branco o cerchio' : 'Reparto' }}
        </label>
        <select id="voce-unita" v-model="unitaSingola" class="form-control">
          <option v-for="u in unitaDellAmbito" :key="u.id" :value="u.id">{{ u.nome }}</option>
        </select>
      </div>
      <div
        v-if="libro?.puo_tutto_il_gruppo && modulo.ambito === 'GRUPPO'"
        class="form-field mb-3"
        data-totem
      >
        <input id="voce-totem" v-model="modulo.cerimonia_del_totem" type="checkbox" class="check" />
        <label for="voce-totem">È la cerimonia del totem: «La mia tribù» rimanda qui</label>
      </div>
      <div v-if="modulo.ambito === 'ALTA_SQ'" class="form-field mb-3" data-ingresso-alta>
        <input
          id="voce-ingresso"
          v-model="modulo.cerimonia_ingresso_alta"
          type="checkbox"
          class="check"
        />
        <label for="voce-ingresso">
          È la cerimonia d'ingresso: chi è segnato tra chi l'ha vissuta entra nell'Alta Squadriglia
        </label>
      </div>
      <div class="mb-5">
        <EditorTesto v-model="modulo.testo" etichetta="Testo" :immagini="false" />
      </div>
      <h2 class="h5">Chi la legge</h2>
      <p class="small fg-2">
        Tutti i capi leggono ogni voce; i genitori mai. Dei ragazzi/e la leggono, finché sono nel
        gruppo, quelli che soddisfano le condizioni, quelli scelti a mano e chi è nel registro di
        chi l'ha vissuta. Scegliendo di chi è la voce, le condizioni si compilano da sole: puoi
        cambiarle.
      </p>
      <div v-if="libro" class="mb-5">
        <CondizioniVoce v-model="modulo.condizioni" :libro="libro" />
      </div>
      <div class="mb-5">
        <SceltaPersone
          id="voce-aggiunti"
          v-model="modulo.aggiunti"
          :opzioni="aggiungibili"
          titolo="Scelti a mano"
        />
      </div>
      <div class="mb-5" data-anteprima>
        <button
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          :disabled="inCorso"
          @click="chiLegge"
        >
          Chi la legge oggi
        </button>
        <template v-if="lettori">
          <p v-if="!lettori.length" class="small fg-2 mt-3 mb-0">Nessun ragazzo o ragazza.</p>
          <template v-else>
            <p class="small mt-3 mb-1">
              {{ lettori.length }} tra ragazzi e ragazze, oltre ai capi:
            </p>
            <ul class="small mb-0">
              <li v-for="p in lettori" :key="p.id">
                {{ p.cognome }} {{ p.nome }} <span class="fg-2">{{ p.unita }}</span>
              </li>
            </ul>
          </template>
        </template>
      </div>
      <div class="d-flex flex-wrap gap-3">
        <button class="btn btn-solid theme-primary" :disabled="inCorso">Salva</button>
        <button v-if="!nuova" type="button" class="btn btn-link" @click="modulo = null">
          Annulla
        </button>
      </div>
    </form>

    <template v-else-if="voce">
      <h1 class="h4 mb-1">{{ voce.titolo }}</h1>
      <p class="small fg-2">
        {{ voce.tipo === 'CERIMONIA' ? 'Cerimonia' : 'Tradizione' }} · {{ voce.unita }}
      </p>
      <template v-if="copiaDel">
        <CopiaLocale :del="copiaDel" />
        <p class="small fg-2" data-senza-rete>
          Senza rete leggi solo il testo: PDF, allegati e chi l'ha vissuta tornano con la rete.
        </p>
      </template>
      <div v-else class="d-flex flex-wrap gap-3 mb-5">
        <a :href="pdfVoceLibro(voce.id)" download class="btn btn-sm btn-outline theme-primary">
          <Icona nome="download" /> Scarica in PDF
        </a>
        <button
          v-if="voce.puo_modificare"
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          @click="apriModulo"
        >
          Modifica
        </button>
      </div>
      <div v-if="voce.testo" class="card card-body mb-5">
        <!-- eslint-disable-next-line vue/no-v-html -- HTML cleaned by the server -->
        <div v-html="voce.testo"></div>
      </div>
      <p v-else class="fg-2">Il testo non è ancora stato scritto.</p>
      <AllegatiVoce v-if="!copiaDel" :voce="voce" @aggiornata="voce = $event" />
      <RegistroVoce v-if="voce.vede_registro" :voce="voce" @aggiornata="voce = $event" />
      <div v-if="voce.puo_modificare" class="mt-7">
        <button
          v-if="!conferma"
          type="button"
          class="btn btn-sm btn-outline theme-danger"
          @click="conferma = true"
        >
          Elimina la voce
        </button>
        <div v-else class="d-flex flex-wrap gap-3 align-items-center">
          <span class="small">La voce sparisce per tutti.</span>
          <button
            type="button"
            class="btn btn-sm btn-solid theme-danger"
            :disabled="inCorso"
            @click="elimina"
          >
            Conferma l'eliminazione
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="conferma = false">
            Annulla
          </button>
        </div>
      </div>
    </template>
  </section>
</template>
