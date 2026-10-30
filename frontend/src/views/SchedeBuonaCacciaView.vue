<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, TIPI_DOMANDA, type Domanda, type SchedaBC, type TipoDomanda } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Event forms (DEC-161): the questions BuonaCaccia asks the participant, saved and reused
// over the years. Saving a change makes a new version: events already using the old one
// keep it. Kept questions keep their id, so answers already given still match.
const { errore, inCorso, esegui } = useErrore()
const schede = ref<SchedaBC[]>([])
const modulo = ref<{ id: number | null; nome: string; domande: Domanda[] } | null>(null)
const esito = ref('')

async function carica() {
  schede.value = (await esegui(() => api.schedeBC())) ?? []
}
onMounted(carica)

const nuova = () => (modulo.value = { id: null, nome: '', domande: [domanda()] })
const domanda = (tipo: TipoDomanda = 'BREVE'): Domanda => ({
  id: '',
  tipo,
  testo: '',
  opzioni: [],
  obbligatoria: false,
})
function modifica(s: SchedaBC) {
  modulo.value = {
    id: s.id,
    nome: s.nome,
    domande: s.ultima.domande.map((d) => ({ ...d, opzioni: [...d.opzioni] })),
  }
  esito.value = ''
}

const scelta = (d: Domanda) => d.tipo === 'SCELTA_SINGOLA' || d.tipo === 'SCELTA_MULTIPLA'
const opzioniTesto = (d: Domanda) => d.opzioni.join('\n')
function opzioni(d: Domanda, testo: string) {
  d.opzioni = testo.split('\n')
}

function sposta(n: number, verso: number) {
  const domande = modulo.value!.domande
  const [d] = domande.splice(n, 1)
  domande.splice(n + verso, 0, d!)
}

async function salva() {
  if (!modulo.value) return
  const dati = {
    nome: modulo.value.nome,
    domande: modulo.value.domande.map((d) => ({
      ...d,
      opzioni: scelta(d) ? d.opzioni.map((o) => o.trim()).filter(Boolean) : [],
    })),
  }
  const id = modulo.value.id
  const salvata = await esegui(() =>
    id === null ? api.creaSchedaBC(dati) : api.nuovaVersioneSchedaBC(id, dati),
  )
  if (!salvata) return
  esito.value = `Salvata: «${salvata.nome}», versione ${salvata.ultima.numero}.`
  modulo.value = null
  await carica()
}
</script>

<template>
  <section>
    <h1 class="h4">Schede degli eventi su BuonaCaccia</h1>
    <p class="small fg-2">
      Le domande che BuonaCaccia fa al partecipante. Il ragazzo o i genitori rispondono dall'app; lo
      staff ricopia tutto su BuonaCaccia in una volta. Le schede si riusano negli anni: cambia le
      domande che sono cambiate e salva, l'app ne fa una nuova versione.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>

    <template v-if="!modulo">
      <ul v-if="schede.length" class="list-group mb-3">
        <li v-for="s in schede" :key="s.id" class="list-group-item">
          <div class="d-flex flex-wrap align-items-center justify-content-between gap-3">
            <span>
              <strong>{{ s.nome }}</strong>
              <span class="small fg-2">
                · versione {{ s.ultima.numero }} · {{ s.ultima.domande.length }} domande · usata da
                {{ s.usata }} {{ s.usata === 1 ? 'evento' : 'eventi' }}
              </span>
            </span>
            <button type="button" class="btn btn-sm btn-outline theme-primary" @click="modifica(s)">
              Modifica
            </button>
          </div>
        </li>
      </ul>
      <p v-else class="small">Nessuna scheda ancora.</p>
      <button type="button" class="btn btn-sm btn-solid theme-primary" @click="nuova">
        Nuova scheda
      </button>
    </template>

    <form v-else class="d-flex flex-column gap-5" @submit.prevent="salva">
      <div>
        <label class="form-label small" for="nome-scheda">Nome della scheda</label>
        <input
          id="nome-scheda"
          v-model="modulo.nome"
          class="form-control form-control-sm"
          required
          placeholder="es. Piccole Orme"
        />
      </div>
      <fieldset v-for="(d, n) in modulo.domande" :key="n" class="card card-body">
        <legend class="small fg-2">Domanda {{ n + 1 }}</legend>
        <div class="row g-3">
          <div class="col-12 md:col-8">
            <label class="form-label small" :for="`testo-${n}`">Testo</label>
            <input
              :id="`testo-${n}`"
              v-model="d.testo"
              class="form-control form-control-sm"
              required
            />
          </div>
          <div class="col-12 md:col-4">
            <label class="form-label small" :for="`tipo-${n}`">Tipo</label>
            <select :id="`tipo-${n}`" v-model="d.tipo" class="form-control form-control-sm">
              <option v-for="[valore, nome] in TIPI_DOMANDA" :key="valore" :value="valore">
                {{ nome }}
              </option>
            </select>
          </div>
          <div v-if="scelta(d)" class="col-12">
            <label class="form-label small" :for="`opzioni-${n}`">Scelte, una per riga</label>
            <textarea
              :id="`opzioni-${n}`"
              class="form-control form-control-sm"
              rows="3"
              :value="opzioniTesto(d)"
              @input="opzioni(d, ($event.target as HTMLTextAreaElement).value)"
            />
          </div>
          <div class="col-12 d-flex flex-wrap align-items-center gap-3">
            <div class="form-field mb-0">
              <input :id="`obbl-${n}`" v-model="d.obbligatoria" type="checkbox" class="check" />
              <label class="small" :for="`obbl-${n}`">Obbligatoria</label>
            </div>
            <button v-if="n > 0" type="button" class="btn btn-sm btn-link" @click="sposta(n, -1)">
              Su
            </button>
            <button
              v-if="n < modulo.domande.length - 1"
              type="button"
              class="btn btn-sm btn-link"
              @click="sposta(n, 1)"
            >
              Giù
            </button>
            <button
              type="button"
              class="btn btn-sm btn-link"
              :disabled="modulo.domande.length === 1"
              @click="modulo.domande.splice(n, 1)"
            >
              Togli
            </button>
          </div>
        </div>
      </fieldset>
      <div class="d-flex flex-wrap gap-3">
        <button
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          @click="modulo.domande.push(domanda())"
        >
          Aggiungi una domanda
        </button>
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Salva
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="modulo = null">Annulla</button>
      </div>
    </form>
  </section>
</template>
