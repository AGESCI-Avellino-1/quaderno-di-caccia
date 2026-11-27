<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import {
  api,
  pdfVoceLibro,
  type LibroCerimonie,
  type PersonaScelta,
  type VoceLibro,
  type VoceLibroIn,
} from '@/api/qdc'
import CondizioniVoce from '@/components/CondizioniVoce.vue'
import Icona from '@/components/Icona.vue'
import SceltaPersone from '@/components/SceltaPersone.vue'
import { opzioniDa, type Opzione } from '@/components/sceltaDaElenco'
import { useErrore } from '@/composables/useErrore'

const EditorTesto = defineAsyncComponent(() => import('@/components/EditorTesto.vue'))

// One entry of the book of ceremonies (DEC-437): its text and PDF for who reads it; for who
// writes it (the staff of its unit, the capigruppo) the form, with the conditions, the
// ragazzi/e added by hand and who would read it today.
// Without an id: a new entry. Online only for now.
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

const nuova = computed(() => props.id === undefined)

function vuoto(l: LibroCerimonie): VoceLibroIn {
  return {
    titolo: '',
    tipo: 'CERIMONIA',
    unita_id: l.puo_tutto_il_gruppo ? null : (l.unita[0]?.id ?? null),
    testo: '',
    aggiunti: [],
    condizioni: [],
    cerimonia_del_totem: false,
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
        unita_id: voce.value.unita_id,
        testo: voce.value.testo,
        aggiunti: [...voce.value.aggiunti],
        condizioni: JSON.parse(JSON.stringify(voce.value.condizioni)),
        cerimonia_del_totem: voce.value.cerimonia_del_totem,
      }
    : vuoto(libro.value)
}

onMounted(async () => {
  if (nuova.value) {
    await apriModulo()
    return
  }
  voce.value = (await esegui(() => api.voceLibro(props.id!))) ?? null
})

// The unit being kept stays a choice even for who no longer serves it.
const unita = computed(() => {
  const elenco = [...(libro.value?.unita ?? [])]
  const attuale = voce.value?.unita_id
  if (attuale && !elenco.some((u) => u.id === attuale))
    elenco.unshift({ id: attuale, nome: voce.value!.unita })
  return elenco
})

async function chiLegge() {
  if (!modulo.value) return
  const { condizioni, aggiunti } = modulo.value
  lettori.value = (await esegui(() => api.anteprimaLettori(condizioni, aggiunti))) ?? null
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
          <label class="form-label small mb-0" for="voce-unita">Di</label>
          <select id="voce-unita" v-model="modulo.unita_id" class="form-control">
            <option v-if="libro?.puo_tutto_il_gruppo" :value="null">Tutto il gruppo</option>
            <option v-for="u in unita" :key="u.id" :value="u.id">{{ u.nome }}</option>
          </select>
        </div>
      </div>
      <div
        v-if="libro?.puo_tutto_il_gruppo && modulo.unita_id === null"
        class="form-field mb-3"
        data-totem
      >
        <input id="voce-totem" v-model="modulo.cerimonia_del_totem" type="checkbox" class="check" />
        <label for="voce-totem">È la cerimonia del totem: «La mia tribù» rimanda qui</label>
      </div>
      <div class="mb-5">
        <EditorTesto v-model="modulo.testo" etichetta="Testo" :immagini="false" />
      </div>
      <h2 class="h5">Chi la legge</h2>
      <p class="small fg-2">
        Tutti i capi leggono ogni voce; i genitori mai. Dei ragazzi/e la leggono, finché sono nel
        gruppo, quelli che soddisfano le condizioni e quelli scelti a mano.
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
      <div class="d-flex flex-wrap gap-3 mb-5">
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
