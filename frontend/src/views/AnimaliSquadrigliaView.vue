<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { api, type AnimaleIn, type AnimaleSquadriglia, type ElencoAnimali } from '@/api/qdc'
import ColoriAnimale from '@/components/ColoriAnimale.vue'
import ImmagineAnimale from '@/components/ImmagineAnimale.vue'
import { useErrore } from '@/composables/useErrore'

// The patrol animals, one list for the group (DEC-350): the ragazzi and the staff of the
// reparti read it, the staff and the capigruppo change it. Online only (DEC-353).
const { errore, inCorso, esegui } = useErrore()
const elenco = ref<ElencoAnimali | null>(null)
const cerca = ref('')

const vuoto = (): AnimaleIn => ({
  nome: '',
  plurale: '',
  tipo: 'GENERALE',
  colore_1: '',
  significato_1: '',
  colore_2: '',
  significato_2: '',
  richiamo: '',
  attivo: true,
})
const modulo = reactive(vuoto())
const aperto = ref(false)
const inModifica = ref<AnimaleSquadriglia | null>(null)
const file = ref<File | null>(null)
const daEliminare = ref<number | null>(null)

async function carica() {
  elenco.value = (await esegui(() => api.animali())) ?? null
}
onMounted(carica)

const gruppi = computed(() => {
  const testo = cerca.value.trim().toLowerCase()
  const trovati = (elenco.value?.animali ?? []).filter(
    (a) =>
      !testo || a.nome.toLowerCase().includes(testo) || a.plurale.toLowerCase().includes(testo),
  )
  return [
    { titolo: 'Generali', voci: trovati.filter((a) => a.tipo === 'GENERALE') },
    { titolo: 'Nautici', voci: trovati.filter((a) => a.tipo === 'NAUTICO') },
  ].filter((g) => g.voci.length)
})

function nuovo() {
  Object.assign(modulo, vuoto())
  inModifica.value = null
  file.value = null
  aperto.value = true
}

function modifica(animale: AnimaleSquadriglia) {
  Object.assign(modulo, {
    nome: animale.nome,
    plurale: animale.plurale,
    tipo: animale.tipo,
    colore_1: animale.colore_1,
    significato_1: animale.significato_1,
    colore_2: animale.colore_2,
    significato_2: animale.significato_2,
    richiamo: animale.richiamo,
    attivo: animale.attivo,
  })
  inModifica.value = animale
  file.value = null
  aperto.value = true
}

function sceltoFile(evento: Event) {
  file.value = (evento.target as HTMLInputElement).files?.[0] ?? null
}

async function salva() {
  const id = inModifica.value?.id
  const salvato = await esegui(() =>
    id ? api.modificaAnimale(id, { ...modulo }) : api.creaAnimale({ ...modulo }),
  )
  if (!salvato) return
  // The animal is saved even if its image is refused: the form stays open on it, with why.
  inModifica.value = salvato
  const scelto = file.value
  if (scelto && !(await esegui(() => api.caricaImmagineAnimale(salvato.id, scelto)))) {
    await carica()
    return
  }
  aperto.value = false
  await carica()
}

async function alternaAttivo(animale: AnimaleSquadriglia) {
  const dati: AnimaleIn = {
    nome: animale.nome,
    plurale: animale.plurale,
    tipo: animale.tipo,
    colore_1: animale.colore_1,
    significato_1: animale.significato_1,
    colore_2: animale.colore_2,
    significato_2: animale.significato_2,
    richiamo: animale.richiamo,
    attivo: !animale.attivo,
  }
  if (await esegui(() => api.modificaAnimale(animale.id, dati))) await carica()
}

async function elimina(id: number) {
  daEliminare.value = null
  await esegui(() => api.eliminaAnimale(id))
  if (!errore.value) await carica()
}
</script>

<template>
  <section>
    <h1 class="h4 mb-3">Animali di squadriglia</h1>
    <p class="small fg-2">
      L'animale dà il nome alla squadriglia: colori e significati servono per il guidoncino.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <template v-if="elenco">
      <div class="d-flex flex-wrap align-items-center gap-3 mb-5">
        <input
          v-model="cerca"
          type="search"
          class="form-control form-control-sm flex-grow-1"
          placeholder="Cerca un animale"
          aria-label="Cerca un animale"
        />
        <button
          v-if="elenco.puo_modificare && !aperto"
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          @click="nuovo"
        >
          Nuovo animale
        </button>
      </div>

      <form v-if="aperto" class="card card-body mb-5" @submit.prevent="salva">
        <div class="row g-3 mb-5">
          <div class="col-12 sm:col-6">
            <label for="animale-nome" class="form-label small fw-bold">Nome</label>
            <input id="animale-nome" v-model="modulo.nome" class="form-control" required />
          </div>
          <div class="col-12 sm:col-6">
            <label for="animale-plurale" class="form-label small fw-bold">Plurale</label>
            <input id="animale-plurale" v-model="modulo.plurale" class="form-control" required />
            <p class="form-text mb-0">
              È il nome della squadriglia: cambiandolo, cambia in tutte quelle con questo animale.
            </p>
          </div>
          <div class="col-12 sm:col-6">
            <label for="animale-tipo" class="form-label small fw-bold">Tipo</label>
            <select id="animale-tipo" v-model="modulo.tipo" class="form-control">
              <option value="GENERALE">Generale</option>
              <option value="NAUTICO">Nautico</option>
            </select>
          </div>
          <div class="col-12 sm:col-6">
            <label for="animale-richiamo" class="form-label small fw-bold">Richiamo</label>
            <input id="animale-richiamo" v-model="modulo.richiamo" class="form-control" />
          </div>
          <template v-for="n in [1, 2] as const" :key="n">
            <div class="col-12 sm:col-4">
              <label :for="`animale-colore-${n}`" class="form-label small fw-bold">
                Colore {{ n }}
              </label>
              <select
                :id="`animale-colore-${n}`"
                v-model="modulo[`colore_${n}`]"
                class="form-control"
              >
                <option value="">Nessuno</option>
                <option v-for="c in elenco.colori" :key="c" :value="c">{{ c }}</option>
              </select>
            </div>
            <div class="col-12 sm:col-8">
              <label :for="`animale-significato-${n}`" class="form-label small fw-bold">
                Significato
              </label>
              <input
                :id="`animale-significato-${n}`"
                v-model="modulo[`significato_${n}`]"
                class="form-control"
              />
            </div>
          </template>
          <div class="col-12">
            <label for="animale-immagine" class="form-label small fw-bold">Immagine</label>
            <input
              id="animale-immagine"
              type="file"
              class="form-control"
              accept=".svg,.png,.jpg,.jpeg"
              @change="sceltoFile"
            />
            <p class="form-text mb-0">
              SVG, PNG o JPEG. Un SVG viene ripulito: resta solo il disegno. Se contiene
              collegamenti esterni viene rifiutato. L'immagine caricata resta con i suoi colori.
            </p>
          </div>
        </div>
        <div class="d-flex gap-1">
          <button type="submit" class="btn btn-solid theme-primary" :disabled="inCorso">
            Salva
          </button>
          <button type="button" class="btn btn-link" @click="aperto = false">Annulla</button>
        </div>
      </form>

      <p v-if="!gruppi.length" class="fg-2 small">Nessun animale trovato.</p>
      <template v-for="g in gruppi" :key="g.titolo">
        <h2 class="h5">{{ g.titolo }}</h2>
        <ul class="list-group mb-5">
          <li v-for="a in g.voci" :key="a.id" class="list-group-item">
            <div class="d-flex gap-3">
              <ImmagineAnimale :animale="a" grande pigra />
              <div class="flex-grow-1">
                <div class="d-flex flex-wrap align-items-center gap-3 mb-1">
                  <strong>{{ a.nome }}</strong>
                  <span class="fg-2 small">Sq. {{ a.plurale }}</span>
                  <span v-if="!a.attivo" class="badge theme-secondary">Disattivato</span>
                </div>
                <ColoriAnimale :colori="a.colori" />
                <p v-if="a.richiamo" class="small mb-0">Richiamo: {{ a.richiamo }}</p>
                <div v-if="elenco.puo_modificare" class="d-flex flex-wrap gap-3 mt-1">
                  <button type="button" class="btn btn-link btn-sm p-0" @click="modifica(a)">
                    modifica
                  </button>
                  <button
                    type="button"
                    class="btn btn-link btn-sm p-0"
                    :disabled="inCorso"
                    @click="alternaAttivo(a)"
                  >
                    {{ a.attivo ? 'disattiva' : 'riattiva' }}
                  </button>
                  <template v-if="!a.usato">
                    <button
                      v-if="daEliminare !== a.id"
                      type="button"
                      class="btn btn-link btn-sm p-0"
                      @click="daEliminare = a.id"
                    >
                      elimina
                    </button>
                    <span v-else class="small">
                      Eliminare?
                      <button
                        type="button"
                        class="btn btn-sm btn-solid theme-danger py-0"
                        :disabled="inCorso"
                        @click="elimina(a.id)"
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
                </div>
              </div>
            </div>
          </li>
        </ul>
      </template>
    </template>
  </section>
</template>
