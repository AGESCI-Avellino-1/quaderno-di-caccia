<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

import { api, pdfCartaClan, type CartaClan } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The Carta di clan as PDF versions (DEC-227…DEC-229): a rover or a scolta proposes a
// new version, the clan staff or a capogruppo puts it in force from a day; the versions
// in force stay, and every signature refers to the one in force on its day. Read by the
// clan, the novices, their parents and every capo. Online only.
const props = defineProps<{ id: number }>()
const { errore, inCorso, esegui } = useErrore()
const dati = ref<CartaClan | null>(null)
const esito = ref('')

async function carica() {
  dati.value = (await esegui(() => api.cartaClan(props.id))) ?? null
}
watch(() => props.id, carica, { immediate: true })

const oggi = new Date().toLocaleDateString('sv')
const nuova = reactive({ file: null as File | null, nota: '', in_vigore_dal: '' })

async function invia() {
  if (!nuova.file) return
  const file = nuova.file
  const fatto = await esegui(() =>
    api.caricaCartaClan(props.id, file, nuova.nota, nuova.in_vigore_dal),
  )
  if (!fatto) return
  dati.value = fatto
  esito.value = nuova.in_vigore_dal ? 'Nuova versione in vigore.' : 'Proposta caricata.'
  Object.assign(nuova, { file: null, nota: '', in_vigore_dal: '' })
}

// The proposal being put in force, and from when.
const daApprovare = reactive({ id: 0, dal: oggi })
async function approva() {
  const fatto = await esegui(() => api.approvaCartaClan(daApprovare.id, daApprovare.dal))
  if (!fatto) return
  dati.value = fatto
  daApprovare.id = 0
  esito.value = 'La versione è in vigore.'
}

async function togli(id: number) {
  dati.value = (await esegui(() => api.togliCartaClan(id))) ?? dati.value
}

const data = (d: string) => new Date(d).toLocaleDateString('it-IT')
</script>

<template>
  <section style="max-width: 50rem">
    <h1 class="h4 mb-1">Carta di clan</h1>
    <p v-if="dati" class="fg-2 small">{{ dati.unita }}</p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>
    <p v-if="inCorso && !dati" class="fg-2">Caricamento…</p>

    <template v-if="dati">
      <p v-if="!dati.versioni.length" class="small">La Carta non è ancora stata caricata.</p>
      <ul v-else class="list-group mb-5">
        <li v-for="v in dati.versioni" :key="v.id" class="list-group-item small">
          <div class="d-flex flex-wrap align-items-center gap-1">
            <a :href="pdfCartaClan(v.id)" target="_blank" rel="noopener">
              <strong v-if="v.in_vigore_dal">In vigore dal {{ data(v.in_vigore_dal) }}</strong>
              <strong v-else>Proposta</strong>
            </a>
            <span v-if="v.corrente" class="badge theme-success">attuale</span>
            <span v-if="!v.in_vigore_dal" class="badge theme-warning">da approvare</span>
          </div>
          <div class="fg-2">
            Caricata il {{ data(v.caricata_il)
            }}<template v-if="v.caricata_da"> da {{ v.caricata_da }}</template
            ><template v-if="v.in_vigore_dal"> · firmata da {{ v.firme }}</template>
          </div>
          <div v-if="v.nota">{{ v.nota }}</div>
          <div
            v-if="!v.in_vigore_dal && (dati.puo_approvare || v.puo_togliere)"
            class="d-flex flex-wrap align-items-end gap-3 mt-1"
          >
            <template v-if="dati.puo_approvare">
              <button
                v-if="daApprovare.id !== v.id"
                type="button"
                class="btn btn-sm btn-outline theme-primary"
                @click="Object.assign(daApprovare, { id: v.id, dal: oggi })"
              >
                Metti in vigore
              </button>
              <form v-else class="d-flex flex-wrap align-items-end gap-3" @submit.prevent="approva">
                <div>
                  <label class="form-label small" :for="`dal-${v.id}`">In vigore dal</label>
                  <input
                    :id="`dal-${v.id}`"
                    v-model="daApprovare.dal"
                    type="date"
                    :max="oggi"
                    class="form-control form-control-sm"
                    required
                  />
                </div>
                <button
                  type="submit"
                  class="btn btn-sm btn-solid theme-primary"
                  :disabled="inCorso"
                >
                  Conferma
                </button>
                <button type="button" class="btn btn-sm btn-link" @click="daApprovare.id = 0">
                  Annulla
                </button>
              </form>
            </template>
            <button
              v-if="v.puo_togliere"
              type="button"
              class="btn btn-sm btn-link"
              :disabled="inCorso"
              @click="togli(v.id)"
            >
              Togli la proposta
            </button>
          </div>
        </li>
      </ul>

      <form v-if="dati.puo_proporre" class="card card-body" @submit.prevent="invia">
        <h2 class="h6">
          {{ dati.puo_approvare ? 'Nuova versione' : 'Proponi una nuova versione' }}
        </h2>
        <div class="row g-3">
          <div class="col-12 md:col-6">
            <label class="form-label small" for="carta-file">Il testo in PDF</label>
            <input
              id="carta-file"
              type="file"
              accept="application/pdf"
              class="form-control form-control-sm"
              required
              @change="nuova.file = ($event.target as HTMLInputElement).files?.[0] ?? null"
            />
          </div>
          <div v-if="dati.puo_approvare" class="col-12 md:col-6">
            <label class="form-label small" for="carta-dal">
              In vigore dal (vuoto: resta una proposta)
            </label>
            <input
              id="carta-dal"
              v-model="nuova.in_vigore_dal"
              type="date"
              :max="oggi"
              class="form-control form-control-sm"
            />
          </div>
          <div class="col-12">
            <label class="form-label small" for="carta-nota">Nota</label>
            <input
              id="carta-nota"
              v-model="nuova.nota"
              class="form-control form-control-sm"
              maxlength="300"
              placeholder="Es. revisione dopo la route estiva"
            />
          </div>
        </div>
        <p class="small fg-2 mt-1 mb-0">
          Chi ha già firmato resta legato alla versione in vigore il giorno della firma.
        </p>
        <div class="mt-3">
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Carica
          </button>
        </div>
      </form>
    </template>
  </section>
</template>
