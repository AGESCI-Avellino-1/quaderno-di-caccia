<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, allegatoVerbale, convocazionePdf, type Convocazione } from '@/api/qdc'
import { caricaAPezzi, misura } from '@/components/allegatiVerbale'
import ConvocazioneAssemblea from '@/components/ConvocazioneAssemblea.vue'
import SceltaPersona from '@/components/SceltaPersona.vue'
import { opzioniDa } from '@/components/sceltaPersona'
import { useErrore } from '@/composables/useErrore'

// The convocation of a meeting of the parents (DEC-327): the documents first, then one
// email to who is invited; a document added later goes out by itself. Online only.
const props = defineProps<{ evento: number }>()
const { errore, inCorso, esegui } = useErrore()
const convocazione = ref<Convocazione | null>(null)
const caricamento = ref<{ nome: string; percentuale: number } | null>(null)
const conferma = ref(false)
const daTogliere = ref<number | null>(null)
const presenzeDa = ref<number | null>(null)

function mostra(dati: Convocazione) {
  convocazione.value = dati
  presenzeDa.value = dati.presenze_da?.id ?? null
}

async function leggi() {
  mostra(await api.convocazione(props.evento))
}

async function indicaPresenze() {
  const dati = await esegui(() => api.indicaPresenze(props.evento, presenzeDa.value))
  if (dati) mostra(dati)
}

onMounted(async () => {
  try {
    await leggi()
  } catch {
    convocazione.value = null
  }
})

async function invia() {
  const dati = await esegui(() => api.inviaConvocazione(props.evento))
  conferma.value = false
  if (dati) mostra(dati)
}

async function carica(evento: Event) {
  const campo = evento.target as HTMLInputElement
  const file = campo.files?.[0]
  campo.value = ''
  if (!file || !convocazione.value) return
  const pezzo = convocazione.value.pezzo
  caricamento.value = { nome: file.name, percentuale: 0 }
  await esegui(async () => {
    const allegato = await api.nuovoAllegatoConvocazione(props.evento, file.name, file.size)
    await caricaAPezzi(allegato.id, file, pezzo, (percentuale) => {
      caricamento.value = { nome: file.name, percentuale }
    })
    await leggi()
  })
  caricamento.value = null
}

async function togli(id: number) {
  const fatto = await esegui(async () => {
    await api.togliAllegatoVerbale(id)
    await leggi()
    return true
  })
  if (fatto) daTogliere.value = null
}

const quando = (iso: string) => new Date(iso).toLocaleString('it-IT')
</script>

<template>
  <section v-if="convocazione" class="card card-body mb-5">
    <h2 class="h5 mb-3">Convocazione</h2>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <p v-if="convocazione.convocata_il" class="small fg-2 mb-3">
      Inviata il {{ quando(convocazione.convocata_il) }}.
      <template v-if="convocazione.puo_gestire">
        Un documento aggiunto ora arriva per email agli invitati.
      </template>
    </p>
    <p v-else-if="convocazione.puo_gestire" class="small fg-2 mb-3">
      Non è ancora stata inviata: aggiungi i documenti, poi invia la convocazione agli invitati.
    </p>

    <ConvocazioneAssemblea
      v-if="convocazione.da_modello && convocazione.puo_gestire"
      :evento="evento"
      @salvata="leggi"
    />
    <a
      v-else-if="convocazione.da_modello && convocazione.convocata_il"
      :href="convocazionePdf(evento)"
      class="btn btn-sm btn-outline theme-primary align-self-start mb-3"
    >
      Scarica il PDF della convocazione
    </a>

    <h3 class="h6">Documenti</h3>
    <ul class="list-unstyled mb-3">
      <li
        v-for="a in convocazione.allegati"
        :key="a.id"
        class="d-flex flex-wrap align-items-center gap-3"
      >
        <a :href="allegatoVerbale(a.id)" :data-dimensione="a.dimensione">{{ a.nome_file }}</a>
        <span class="small fg-2">{{ misura(a.dimensione) }}</span>
        <template v-if="convocazione.puo_gestire">
          <button
            v-if="daTogliere !== a.id"
            type="button"
            class="btn btn-link btn-sm p-0"
            @click="daTogliere = a.id"
          >
            togli
          </button>
          <span v-else class="small">
            Toglierlo?
            <button
              type="button"
              class="btn btn-sm btn-solid theme-danger py-0"
              :disabled="inCorso"
              @click="togli(a.id)"
            >
              Sì
            </button>
            <button type="button" class="btn btn-sm btn-link py-0" @click="daTogliere = null">
              No
            </button>
          </span>
        </template>
      </li>
      <li v-if="!convocazione.allegati.length" class="fg-2 small">Nessun documento.</li>
    </ul>
    <div v-if="convocazione.puo_gestire" class="mb-3">
      <label class="form-label small" :for="`convocazione-${evento}`">
        Aggiungi un documento, al massimo {{ misura(convocazione.massimo_allegato) }}
      </label>
      <input
        :id="`convocazione-${evento}`"
        type="file"
        class="form-control form-control-sm"
        :disabled="!!caricamento"
        @change="carica"
      />
      <p v-if="caricamento" class="small fg-2 mb-0 mt-1" role="status">
        Carico {{ caricamento.nome }}: {{ caricamento.percentuale }}%. Non chiudere la pagina.
      </p>
    </div>

    <form
      v-if="convocazione.puo_indicare_presenze"
      class="row g-3 align-items-end mb-3"
      @submit.prevent="indicaPresenze"
    >
      <div class="col-12 sm:col-8">
        <label class="form-label small" :for="`presenze-da-${evento}`">
          Chi segna le presenze, oltre ai capigruppo
        </label>
        <SceltaPersona
          :id="`presenze-da-${evento}`"
          v-model="presenzeDa"
          :opzioni="opzioniDa(convocazione.candidati_presenze)"
          vuoto="Nessun altro"
        />
      </div>
      <div class="col-12 sm:col-4">
        <button
          type="submit"
          class="btn btn-sm btn-outline theme-primary w-100"
          :disabled="inCorso"
        >
          Indica
        </button>
      </div>
    </form>

    <template v-if="convocazione.puo_inviare">
      <button
        v-if="!conferma"
        type="button"
        class="btn btn-sm btn-solid theme-primary align-self-start"
        @click="conferma = true"
      >
        Invia la convocazione
      </button>
      <p v-else class="small mb-0">
        L'email parte per tutti gli invitati e si invia una volta sola. Confermi?
        <button
          type="button"
          class="btn btn-sm btn-solid theme-primary py-0"
          :disabled="inCorso"
          @click="invia"
        >
          Sì
        </button>
        <button type="button" class="btn btn-sm btn-link py-0" @click="conferma = false">No</button>
      </p>
    </template>
  </section>
</template>
