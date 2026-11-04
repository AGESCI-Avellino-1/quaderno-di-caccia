<script setup lang="ts">
import { defineAsyncComponent, onMounted, ref } from 'vue'

import { api, fileProgettoCapo, type ProgettoCapo } from '@/api/qdc'
import { misura } from '@/components/allegatiVerbale'
import { useErrore } from '@/composables/useErrore'

// The capo's project (DEC-335): read like the file, written only by the capo, text with the
// editor (preferred) or PDF. Versions with their date. Online only. Editor and PDF reader
// load only when opened: pdf.js alone weighs more than a megabyte.
const EditorTesto = defineAsyncComponent(() => import('@/components/EditorTesto.vue'))
const LettorePdf = defineAsyncComponent(() => import('@/components/LettorePdf.vue'))
const props = defineProps<{ persona: number }>()
const { errore, inCorso, esegui } = useErrore()
const progetto = ref<ProgettoCapo | null>(null)
const testi = ref<Record<number, string>>({})
const pdfAperti = ref<Record<number, boolean>>({})
const aperto = ref(false)
const modo = ref<'testo' | 'pdf'>('testo')
const testo = ref('')
const file = ref<File | null>(null)
const daTogliere = ref<number | null>(null)

onMounted(async () => {
  progetto.value = (await esegui(() => api.progettoCapo(props.persona))) ?? null
})

const giorno = (iso: string) => new Date(iso).toLocaleDateString('it-IT')

function scegliFile(evento: Event) {
  file.value = (evento.target as HTMLInputElement).files?.[0] ?? null
}

async function apriTesto(id: number) {
  const dati = await esegui(() => api.testoProgettoCapo(id))
  if (dati) testi.value[id] = dati.testo
}

async function nuovaVersione() {
  // A new version starts from the one in force, when it is a text.
  const vigente = progetto.value?.versioni[0]
  if (vigente?.ha_testo) {
    const dati = await esegui(() => api.testoProgettoCapo(vigente.id))
    testo.value = dati?.testo ?? ''
  }
  aperto.value = true
}

async function salva() {
  const corpo = new FormData()
  if (modo.value === 'testo') corpo.append('testo', testo.value)
  else if (file.value) corpo.append('file', file.value)
  const dati = await esegui(() => api.nuovoProgettoCapo(props.persona, corpo))
  if (!dati) return
  progetto.value = dati
  aperto.value = false
  testo.value = ''
  file.value = null
}

async function togli(id: number) {
  const dati = await esegui(() => api.togliProgettoCapo(id))
  daTogliere.value = null
  if (dati) progetto.value = dati
}
</script>

<template>
  <section v-if="progetto" class="mb-5">
    <h2 class="h5">Progetto del capo</h2>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <p v-if="!progetto.versioni.length" class="fg-2 small">Non è ancora stato inserito.</p>
    <ul class="list-unstyled mb-3">
      <li v-for="v in progetto.versioni" :key="v.id" class="mb-3">
        <div class="d-flex flex-wrap align-items-center gap-3">
          <strong>{{ giorno(v.data) }}</strong>
          <span v-if="v.in_vigore" class="badge theme-success">In vigore</span>
          <button
            v-if="v.ha_testo && testi[v.id] === undefined"
            type="button"
            class="btn btn-link btn-sm p-0"
            @click="apriTesto(v.id)"
          >
            Leggi
          </button>
          <button
            v-if="!v.ha_testo && !pdfAperti[v.id]"
            type="button"
            class="btn btn-link btn-sm p-0"
            @click="pdfAperti[v.id] = true"
          >
            Leggi
          </button>
          <a :href="fileProgettoCapo(v.id)" :data-dimensione="v.dimensione">Scarica il PDF</a>
          <span v-if="v.nome_file" class="small fg-2">
            {{ v.nome_file }} · {{ misura(v.dimensione) }}
          </span>
          <template v-if="progetto.puo_modificare">
            <button
              v-if="daTogliere !== v.id"
              type="button"
              class="btn btn-link btn-sm p-0"
              @click="daTogliere = v.id"
            >
              Elimina
            </button>
            <span v-else class="small">
              Eliminarla?
              <button
                type="button"
                class="btn btn-sm btn-solid theme-danger py-0"
                :disabled="inCorso"
                @click="togli(v.id)"
              >
                Sì
              </button>
              <button type="button" class="btn btn-sm btn-link py-0" @click="daTogliere = null">
                No
              </button>
            </span>
          </template>
        </div>
        <!-- eslint-disable-next-line vue/no-v-html -- HTML cleaned by the server -->
        <div v-if="testi[v.id]" class="mt-3" v-html="testi[v.id]"></div>
        <LettorePdf v-if="pdfAperti[v.id]" class="mt-3" :url="fileProgettoCapo(v.id)" />
      </li>
    </ul>

    <template v-if="progetto.puo_modificare">
      <button
        v-if="!aperto"
        type="button"
        class="btn btn-sm btn-outline theme-primary"
        :disabled="inCorso"
        @click="nuovaVersione"
      >
        {{ progetto.versioni.length ? 'Nuova versione' : 'Inserisci il progetto' }}
      </button>
      <form v-else class="card card-body" @submit.prevent="salva">
        <div class="form-field mb-1">
          <input
            :id="`progetto-testo-${persona}`"
            v-model="modo"
            type="radio"
            class="radio"
            name="progetto-modo"
            value="testo"
          />
          <label :for="`progetto-testo-${persona}`">Scrivo il testo</label>
        </div>
        <div class="form-field mb-3">
          <input
            :id="`progetto-pdf-${persona}`"
            v-model="modo"
            type="radio"
            class="radio"
            name="progetto-modo"
            value="pdf"
          />
          <label :for="`progetto-pdf-${persona}`">
            Carico un PDF, al massimo {{ misura(progetto.massimo) }}
          </label>
        </div>
        <div v-if="modo === 'testo'" class="mb-3">
          <EditorTesto v-model="testo" etichetta="Testo del progetto" />
        </div>
        <input
          v-else
          type="file"
          accept="application/pdf"
          class="form-control form-control-sm mb-3"
          aria-label="Il PDF del progetto"
          @change="scegliFile"
        />
        <div class="d-flex gap-3">
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Salva
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="aperto = false">Annulla</button>
        </div>
      </form>
    </template>
  </section>
</template>
