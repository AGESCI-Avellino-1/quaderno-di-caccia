<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { api, type SchedaIncarichi, type TipoIncarico, type TipoIncaricoIn } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Every role of the capi: the fixed ones to read, those the capigruppo defined to change
// (DEC-347...DEC-349). They give no permission. Online only, like the appointments.
const { errore, inCorso, esegui } = useErrore()
const scheda = ref<SchedaIncarichi | null>(null)

const vuoto = (): TipoIncaricoIn => ({
  nome: '',
  ambito: 'GRUPPO',
  di_servizio: false,
  educativo: true,
  attivo: true,
})
const modulo = reactive(vuoto())
const aperto = ref(false)
// The role being changed; null = a new one.
const inModifica = ref<TipoIncarico | null>(null)
const daEliminare = ref<number | null>(null)

async function carica() {
  scheda.value = (await esegui(() => api.schedaIncarichi())) ?? null
}
onMounted(carica)

function nuovo() {
  Object.assign(modulo, vuoto())
  inModifica.value = null
  aperto.value = true
}

function modifica(tipo: TipoIncarico) {
  Object.assign(modulo, {
    nome: tipo.nome,
    ambito: tipo.ambito,
    di_servizio: tipo.di_servizio,
    educativo: tipo.educativo,
    attivo: tipo.attivo,
  })
  inModifica.value = tipo
  aperto.value = true
}

async function salva() {
  const dati = { ...modulo, nome: modulo.nome.trim() }
  const id = inModifica.value?.id
  const fatto = await esegui(() =>
    id ? api.modificaTipoIncarico(id, dati) : api.creaTipoIncarico(dati),
  )
  if (!fatto) return
  aperto.value = false
  await carica()
}

async function alternaAttivo(tipo: TipoIncarico) {
  const { nome, ambito, di_servizio, educativo } = tipo
  const dati = { nome, ambito, di_servizio, educativo, attivo: !tipo.attivo }
  if (await esegui(() => api.modificaTipoIncarico(tipo.id, dati))) await carica()
}

async function elimina(id: number) {
  daEliminare.value = null
  await esegui(() => api.eliminaTipoIncarico(id))
  if (!errore.value) await carica()
}

// What a role in use is no longer changes: its history would change meaning.
const bloccato = computed(() => inModifica.value?.usato ?? false)
const ambito = (valore: string) => (valore === 'UNITA' ? 'Di unità' : 'Di gruppo')
const natura = (servizio: boolean) => (servizio ? 'di servizio' : 'aggiuntivo')
</script>

<template>
  <section>
    <h1 class="h4 mb-3">Scheda incarichi</h1>
    <p class="small fg-2">
      Gli incarichi che si possono dare ai capi. Quelli definiti dal gruppo non danno nessun
      permesso nell'app: servono a dire chi fa cosa, nell'organigramma e nel fascicolo del capo.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <template v-if="scheda">
      <div class="d-flex align-items-center mb-3">
        <h2 class="h5 mb-0">Definiti dal gruppo</h2>
        <button
          v-if="scheda.puo_modificare && !aperto"
          type="button"
          class="btn btn-sm btn-outline theme-primary ms-auto"
          @click="nuovo"
        >
          Nuovo incarico
        </button>
      </div>

      <form v-if="aperto" class="card card-body mb-5" @submit.prevent="salva">
        <div class="mb-5">
          <label for="incarico-nome" class="form-label small fw-bold">Nome</label>
          <input id="incarico-nome" v-model="modulo.nome" class="form-control" required />
        </div>
        <fieldset class="mb-5" :disabled="bloccato">
          <legend class="small fw-bold">Dove vale</legend>
          <div class="form-field">
            <input
              id="incarico-gruppo"
              v-model="modulo.ambito"
              type="radio"
              class="radio"
              value="GRUPPO"
            />
            <label for="incarico-gruppo">Di gruppo</label>
          </div>
          <div class="form-field">
            <input
              id="incarico-unita"
              v-model="modulo.ambito"
              type="radio"
              class="radio"
              value="UNITA"
            />
            <label for="incarico-unita">Di unità: si assegna dalla pagina dell'unità</label>
          </div>
        </fieldset>
        <fieldset class="mb-5" :disabled="bloccato">
          <legend class="small fw-bold">Rispetto al servizio del capo</legend>
          <div class="form-field">
            <input
              id="incarico-aggiuntivo"
              v-model="modulo.di_servizio"
              type="radio"
              class="radio"
              :value="false"
            />
            <label for="incarico-aggiuntivo">Aggiuntivo: si somma al servizio che il capo fa</label>
          </div>
          <div class="form-field">
            <input
              id="incarico-servizio"
              v-model="modulo.di_servizio"
              type="radio"
              class="radio"
              :value="true"
            />
            <label for="incarico-servizio">Di servizio: è il servizio del capo</label>
          </div>
          <p v-if="modulo.di_servizio && modulo.ambito === 'GRUPPO'" class="form-text mb-0">
            Funziona come un servizio di supporto: esclude il servizio in un'unità e gli altri
            servizi di supporto, e finisce da sé quando il capo viene assegnato a un'unità.
          </p>
          <p v-if="modulo.di_servizio && modulo.ambito === 'UNITA'" class="form-text mb-0">
            Conta come fare servizio nell'unità ed esclude i servizi di supporto, ma non dà i
            permessi dello staff: il capo non vede i dati dell'unità.
          </p>
        </fieldset>
        <p v-if="bloccato" class="form-text">
          È già stato assegnato: dove vale e il rapporto col servizio non cambiano più. Se serve,
          disattivalo e definiscine un altro.
        </p>
        <div class="form-field mb-5">
          <input id="incarico-educativo" v-model="modulo.educativo" type="checkbox" class="check" />
          <label for="incarico-educativo">
            Educativo: conta solo per la scelta rapida nel PDF dell'elenco degli incarichi
          </label>
        </div>
        <div class="d-flex gap-1">
          <button type="submit" class="btn btn-solid theme-primary" :disabled="inCorso">
            Salva
          </button>
          <button type="button" class="btn btn-link" @click="aperto = false">Annulla</button>
        </div>
      </form>

      <p v-if="!scheda.definiti.length" class="fg-2 small">Nessun incarico definito dal gruppo.</p>
      <ul v-else class="list-group mb-5">
        <li v-for="t in scheda.definiti" :key="t.id" class="list-group-item">
          <div class="d-flex flex-wrap align-items-center gap-3">
            <strong>{{ t.nome }}</strong>
            <span class="fg-2 small">
              {{ ambito(t.ambito) }}, {{ natura(t.di_servizio) }},
              {{ t.educativo ? 'educativo' : 'non educativo' }}
            </span>
            <span v-if="!t.attivo" class="badge theme-secondary">Disattivato</span>
            <span v-if="scheda.puo_modificare" class="ms-auto d-flex flex-wrap gap-3">
              <button type="button" class="btn btn-link btn-sm p-0" @click="modifica(t)">
                modifica
              </button>
              <button
                type="button"
                class="btn btn-link btn-sm p-0"
                :disabled="inCorso"
                @click="alternaAttivo(t)"
              >
                {{ t.attivo ? 'disattiva' : 'riattiva' }}
              </button>
              <template v-if="!t.usato">
                <button
                  v-if="daEliminare !== t.id"
                  type="button"
                  class="btn btn-link btn-sm p-0"
                  @click="daEliminare = t.id"
                >
                  elimina
                </button>
                <span v-else class="small">
                  Eliminare?
                  <button
                    type="button"
                    class="btn btn-sm btn-solid theme-danger py-0"
                    :disabled="inCorso"
                    @click="elimina(t.id)"
                  >
                    Sì
                  </button>
                  <button
                    type="button"
                    class="btn btn-sm btn-link py-0"
                    @click="daEliminare = null"
                  >
                    No
                  </button>
                </span>
              </template>
            </span>
          </div>
        </li>
      </ul>

      <h2 class="h5">Incarichi dell'app</h2>
      <p class="small fg-2">Sono uguali per tutti i gruppi e non si modificano.</p>
      <ul class="list-group">
        <li v-for="e in scheda.esistenti" :key="e.nome" class="list-group-item">
          <div class="d-flex flex-wrap align-items-center gap-3">
            <span>{{ e.nome }}</span>
            <span class="fg-2 small">
              {{ ambito(e.ambito) }}, {{ natura(e.di_servizio) }},
              {{ e.educativo ? 'educativo' : 'non educativo' }}
            </span>
          </div>
        </li>
      </ul>
    </template>
  </section>
</template>
