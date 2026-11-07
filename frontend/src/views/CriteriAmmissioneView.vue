<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, reactive, ref } from 'vue'

import { api, criteriPdf, type GestioneCriteri } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The capigruppo write the criteria of the year (DEC-355). A change is a new version from a day
// of the year; the others stay, each valid until the next begins (DEC-356). Online only.
const EditorTesto = defineAsyncComponent(() => import('@/components/EditorTesto.vue'))

const { errore, inCorso, esegui } = useErrore()
const dati = ref<GestioneCriteri | null>(null)
const aperto = ref(false)
const daEliminare = ref<number | null>(null)
const modulo = reactive({
  anno: 0,
  valida_dal: '',
  verbale_numero: '',
  verbale_data: '',
  testo: '',
})
// By unit, as written in the field: empty = no limit.
const massimi = reactive<Record<number, string>>({})

const oggi = () => new Date().toISOString().slice(0, 10)

async function carica() {
  dati.value = (await esegui(() => api.gestioneCriteri())) ?? null
}
onMounted(carica)

function nuova() {
  const d = dati.value!
  Object.assign(modulo, {
    anno: d.anni[0].valore,
    valida_dal: oggi(),
    verbale_numero: d.verbale_numero,
    verbale_data: d.verbale_data ?? '',
    testo: d.testo,
  })
  for (const u of d.unita) massimi[u.id] = ''
  for (const m of d.massimi) massimi[m.unita_id] = String(m.massimo)
  aperto.value = true
}

const massimiScritti = computed(() =>
  Object.entries(massimi)
    .filter(([, valore]) => valore !== '' && valore !== null)
    .map(([unita, valore]) => ({ unita_id: Number(unita), massimo: Number(valore) })),
)

async function salva() {
  const fatto = await esegui(() =>
    api.nuovaVersioneCriteri({ ...modulo, massimi: massimiScritti.value }),
  )
  if (!fatto) return
  aperto.value = false
  await carica()
}

async function elimina(id: number) {
  daEliminare.value = null
  await esegui(() => api.eliminaVersioneCriteri(id))
  if (!errore.value) await carica()
}

const giorno = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
const futura = (iso: string) => iso > oggi()
</script>

<template>
  <section>
    <h1 class="h4 mb-3">Criteri di ammissione</h1>
    <p class="small fg-2">
      I requisiti e i criteri che la Comunità capi delibera ogni anno. Sono pubblici: chiunque li
      scarica quando si mette in lista d'attesa, anche senza un account. Non scrivere nomi né dati
      di persone.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <template v-if="dati">
      <button
        v-if="!aperto"
        type="button"
        class="btn btn-sm btn-solid theme-primary mb-5"
        @click="nuova"
      >
        Nuova versione
      </button>

      <form v-if="aperto" class="card card-body mb-5" @submit.prevent="salva">
        <div class="row g-3 mb-5">
          <div class="col-12 sm:col-6">
            <label for="criteri-anno" class="form-label small fw-bold">Anno associativo</label>
            <select id="criteri-anno" v-model.number="modulo.anno" class="form-control">
              <option v-for="a in dati.anni" :key="a.valore" :value="a.valore">{{ a.nome }}</option>
            </select>
          </div>
          <div class="col-12 sm:col-6">
            <label for="criteri-dal" class="form-label small fw-bold">Valida dal</label>
            <input
              id="criteri-dal"
              v-model="modulo.valida_dal"
              type="date"
              class="form-control"
              required
            />
            <p class="form-text mb-0">
              La versione precedente dello stesso anno resta visibile, valida fino al giorno prima.
              Una data futura si vede solo da quel giorno.
            </p>
          </div>
          <div class="col-12 sm:col-6">
            <label for="criteri-numero" class="form-label small fw-bold"
              >Verbale della Co.Ca. n.</label
            >
            <input
              id="criteri-numero"
              v-model="modulo.verbale_numero"
              class="form-control"
              required
            />
          </div>
          <div class="col-12 sm:col-6">
            <label for="criteri-data" class="form-label small fw-bold">Del</label>
            <input
              id="criteri-data"
              v-model="modulo.verbale_data"
              type="date"
              class="form-control"
              required
            />
          </div>
        </div>
        <EditorTesto v-model="modulo.testo" etichetta="Testo dei criteri" class="mb-5" />
        <fieldset class="mb-5">
          <legend class="small fw-bold">Numero massimo di ragazzi/e per unità</legend>
          <p class="form-text">
            Vuoto vuol dire nessun limite. Compaiono in una tabella in fondo al PDF. Oltre il
            massimo chi accoglie una richiesta riceve un avviso, ma può accoglierla lo stesso.
          </p>
          <div v-for="u in dati.unita" :key="u.id" class="row g-3 align-items-center mb-1">
            <label :for="`massimo-${u.id}`" class="col-8 small mb-0">{{ u.nome }}</label>
            <div class="col-4">
              <input
                :id="`massimo-${u.id}`"
                v-model="massimi[u.id]"
                type="number"
                min="1"
                class="form-control form-control-sm"
              />
            </div>
          </div>
        </fieldset>
        <div class="d-flex gap-1">
          <button type="submit" class="btn btn-solid theme-primary" :disabled="inCorso">
            Salva la versione
          </button>
          <button type="button" class="btn btn-link" @click="aperto = false">Annulla</button>
        </div>
      </form>

      <p v-if="!dati.versioni.length" class="fg-2 small">
        Nessuna versione: la prima parte da un testo di esempio, da verificare con lo Statuto e il
        Regolamento e adattare alle decisioni della Comunità capi.
      </p>
      <ul v-else class="list-group">
        <li v-for="v in dati.versioni" :key="v.id" class="list-group-item">
          <div class="d-flex flex-wrap align-items-center gap-3">
            <strong>{{ v.anno_nome }}</strong>
            <span class="small"
              >dal {{ giorno(v.valida_dal) }} al {{ giorno(v.valida_fino_al) }}</span
            >
            <span v-if="v.in_vigore" class="badge theme-success">In vigore</span>
            <span v-else-if="futura(v.valida_dal)" class="badge theme-info"
              >Non ancora iniziata</span
            >
            <span class="fg-2 small">
              verbale n. {{ v.verbale_numero }} del {{ giorno(v.verbale_data) }}
            </span>
            <span class="ms-auto d-flex flex-wrap gap-3 small">
              <a :href="criteriPdf(v.id)">PDF</a>
              <button
                v-if="daEliminare !== v.id"
                type="button"
                class="btn btn-link btn-sm p-0"
                @click="daEliminare = v.id"
              >
                elimina
              </button>
              <span v-else>
                Eliminare?
                <button
                  type="button"
                  class="btn btn-sm btn-solid theme-danger py-0"
                  :disabled="inCorso"
                  @click="elimina(v.id)"
                >
                  Sì
                </button>
                <button type="button" class="btn btn-sm btn-link py-0" @click="daEliminare = null">
                  No
                </button>
              </span>
            </span>
          </div>
        </li>
      </ul>
    </template>
  </section>
</template>
