<script setup lang="ts">
import { RouterLink } from 'vue-router'
import CriteriAmmissione from '@/components/CriteriAmmissione.vue'
import { computed, defineAsyncComponent, onMounted, reactive, ref } from 'vue'

import {
  api,
  fileDocumento,
  fileVersionePeg,
  type DocumentoDownload,
  type Download,
  type DurataDocumento,
} from '@/api/qdc'
import { misura } from '@/components/allegatiVerbale'
import { useErrore } from '@/composables/useErrore'

// Documents of the group and the Progetto Educativo di Gruppo with its history (DEC-341…
// DEC-344). What each user sees and may do comes from the backend. Online only.
const EditorTesto = defineAsyncComponent(() => import('@/components/EditorTesto.vue'))
const { errore, inCorso, esegui } = useErrore()
const pagina = ref<Download | null>(null)
const aperto = ref(false)
const inModifica = ref<number | null>(null)
const daEliminare = ref<number | null>(null)
const file = ref<File | null>(null)
const vuoto = () => ({
  titolo: '',
  descrizione: '',
  durata: 'SEMPRE' as DurataDocumento,
  anno: null as number | null,
  scade_il: '',
  per_coca: false,
  per_genitori: false,
  unita: [] as number[],
  unita_ragazzi: false,
  unita_genitori: false,
  avvisa: false,
})
const modulo = reactive(vuoto())

const pegAperto = ref(false)
const pegFile = ref<File | null>(null)
const pegModo = ref<'pdf' | 'testo'>('pdf')
const pegTesto = ref('')
const oggi = () => new Date().toISOString().slice(0, 10)
const pegApprovato = ref(oggi())
const pegDurata = ref('')
const pegAvvisa = ref(false)
const pegDaEliminare = ref<number | null>(null)
const testiPeg = ref<Record<number, string>>({})

const durate: { valore: DurataDocumento; nome: string }[] = [
  { valore: 'SEMPRE', nome: 'Finché non viene eliminato' },
  { valore: 'ANNO', nome: 'Per un anno associativo' },
  { valore: 'DATA', nome: 'Fino a una data' },
]
const massimo = computed(() => misura(pagina.value?.massimo ?? 0))
const giorno = (iso: string) => new Date(iso).toLocaleDateString('it-IT')

async function leggi() {
  pagina.value = (await esegui(() => api.download())) ?? null
}
onMounted(leggi)

function nuovo() {
  Object.assign(modulo, vuoto())
  file.value = null
  inModifica.value = null
  aperto.value = true
}

function modifica(d: DocumentoDownload) {
  Object.assign(modulo, {
    titolo: d.titolo,
    descrizione: d.descrizione,
    durata: d.durata,
    anno: d.anno,
    scade_il: d.scade_il ?? '',
    per_coca: d.per_coca,
    per_genitori: d.per_genitori,
    unita: [...d.unita_ids],
    unita_ragazzi: d.unita_ragazzi,
    unita_genitori: d.unita_genitori,
    avvisa: false,
  })
  file.value = null
  inModifica.value = d.id
  aperto.value = true
}

function scegliFile(evento: Event) {
  file.value = (evento.target as HTMLInputElement).files?.[0] ?? null
}

function corpo(): FormData {
  const dati = new FormData()
  dati.append('titolo', modulo.titolo)
  dati.append('descrizione', modulo.descrizione)
  dati.append('durata', modulo.durata)
  if (modulo.durata === 'ANNO' && modulo.anno) dati.append('anno', String(modulo.anno))
  if (modulo.durata === 'DATA' && modulo.scade_il) dati.append('scade_il', modulo.scade_il)
  dati.append('per_coca', String(modulo.per_coca))
  dati.append('per_genitori', String(modulo.per_genitori))
  dati.append('unita', modulo.unita.join(','))
  dati.append('unita_ragazzi', String(modulo.unita_ragazzi))
  dati.append('unita_genitori', String(modulo.unita_genitori))
  dati.append('avvisa', String(modulo.avvisa))
  if (file.value) dati.append('file', file.value)
  return dati
}

async function salva() {
  const id = inModifica.value
  const fatto = await esegui(() =>
    id === null ? api.caricaDocumento(corpo()) : api.modificaDocumento(id, corpo()),
  )
  if (!fatto) return
  aperto.value = false
  await leggi()
}

async function elimina(id: number) {
  const fatto = await esegui(async () => {
    await api.eliminaDocumento(id)
    return true
  })
  daEliminare.value = null
  if (fatto) await leggi()
}

function scegliPegFile(evento: Event) {
  pegFile.value = (evento.target as HTMLInputElement).files?.[0] ?? null
}

async function salvaPeg() {
  const dati = new FormData()
  dati.append('approvato_il', pegApprovato.value)
  dati.append('durata', pegDurata.value)
  dati.append('avvisa', String(pegAvvisa.value))
  if (pegModo.value === 'testo') dati.append('testo', pegTesto.value)
  else if (pegFile.value) dati.append('file', pegFile.value)
  const fatto = await esegui(() => api.nuovaVersionePeg(dati))
  if (!fatto) return
  pegAperto.value = false
  pegFile.value = null
  pegTesto.value = ''
  pegDurata.value = ''
  pegAvvisa.value = false
  await leggi()
}

async function eliminaPeg(id: number) {
  const fatto = await esegui(async () => {
    await api.eliminaVersionePeg(id)
    return true
  })
  pegDaEliminare.value = null
  if (fatto) await leggi()
}

async function inRedazione(valore: boolean) {
  await esegui(async () => {
    await api.pegInRedazione(valore)
    return true
  })
  await leggi()
}

async function leggiTesto(id: number) {
  const dati = await esegui(() => api.testoVersionePeg(id))
  if (dati) testiPeg.value[id] = dati.testo
}
</script>

<template>
  <div v-if="pagina">
    <h1 class="h4 mb-5">Download</h1>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>

    <section v-if="pagina.peg" class="card card-body mb-5">
      <div class="d-flex flex-wrap align-items-center gap-3 mb-3">
        <h2 class="h5 mb-0">Progetto Educativo di Gruppo</h2>
        <span v-if="pagina.peg.in_redazione" class="badge theme-warning">
          In redazione una nuova versione
        </span>
      </div>
      <ul class="list-unstyled mb-3">
        <li v-for="v in pagina.peg.versioni" :key="v.id" class="mb-3">
          <div class="d-flex flex-wrap align-items-center gap-3">
            <strong>Approvato il {{ giorno(v.approvato_il) }}</strong>
            <span v-if="v.durata" class="small fg-2">{{ v.durata }}</span>
            <span v-if="v.in_vigore" class="badge theme-success">In vigore</span>
            <a :href="fileVersionePeg(v.id)" :data-dimensione="v.dimensione">Scarica il PDF</a>
            <button
              v-if="v.ha_testo && testiPeg[v.id] === undefined"
              type="button"
              class="btn btn-link btn-sm p-0"
              @click="leggiTesto(v.id)"
            >
              Leggi
            </button>
            <template v-if="pagina.peg.puo_gestire">
              <button
                v-if="pegDaEliminare !== v.id"
                type="button"
                class="btn btn-link btn-sm p-0"
                @click="pegDaEliminare = v.id"
              >
                Elimina
              </button>
              <span v-else class="small">
                Eliminarla? Torna in vigore la precedente.
                <button
                  type="button"
                  class="btn btn-sm btn-solid theme-danger py-0"
                  :disabled="inCorso"
                  @click="eliminaPeg(v.id)"
                >
                  Sì
                </button>
                <button
                  type="button"
                  class="btn btn-sm btn-link py-0"
                  @click="pegDaEliminare = null"
                >
                  No
                </button>
              </span>
            </template>
          </div>
          <!-- eslint-disable-next-line vue/no-v-html -- HTML cleaned by the server -->
          <div v-if="testiPeg[v.id]" class="mt-3" v-html="testiPeg[v.id]"></div>
        </li>
        <li v-if="!pagina.peg.versioni.length" class="fg-2 small">Non è ancora stato caricato.</li>
      </ul>

      <template v-if="pagina.peg.puo_gestire">
        <div class="form-field mb-3">
          <input
            id="peg-in-redazione"
            type="checkbox"
            class="check"
            :checked="pagina.peg.in_redazione"
            :disabled="inCorso"
            @change="inRedazione(($event.target as HTMLInputElement).checked)"
          />
          <label for="peg-in-redazione">Segnala che è in redazione una nuova versione</label>
        </div>
        <button
          v-if="!pegAperto"
          type="button"
          class="btn btn-sm btn-outline theme-primary align-self-start"
          @click="pegAperto = true"
        >
          Carica una nuova versione
        </button>
        <form v-else @submit.prevent="salvaPeg">
          <p class="alert theme-warning small">
            <span
              >La versione in vigore è pubblica: la può leggere chiunque, anche senza account.</span
            >
          </p>
          <div class="row g-3 mb-3">
            <div class="col-12 sm:col-6">
              <label class="form-label small" for="peg-approvato">
                Approvato dalla Co.Ca. il
              </label>
              <input
                id="peg-approvato"
                v-model="pegApprovato"
                type="date"
                class="form-control form-control-sm"
                required
              />
            </div>
            <div class="col-12 sm:col-6">
              <label class="form-label small" for="peg-durata">Durata indicativa</label>
              <input
                id="peg-durata"
                v-model="pegDurata"
                class="form-control form-control-sm"
                maxlength="40"
                placeholder="2026/2029"
              />
            </div>
          </div>
          <div class="form-field mb-1">
            <input
              id="peg-modo-pdf"
              v-model="pegModo"
              type="radio"
              class="radio"
              name="peg-modo"
              value="pdf"
            />
            <label for="peg-modo-pdf">Carico il PDF, al massimo {{ massimo }}</label>
          </div>
          <div class="form-field mb-3">
            <input
              id="peg-modo-testo"
              v-model="pegModo"
              type="radio"
              class="radio"
              name="peg-modo"
              value="testo"
            />
            <label for="peg-modo-testo">Scrivo il testo</label>
          </div>
          <input
            v-if="pegModo === 'pdf'"
            type="file"
            accept="application/pdf"
            class="form-control form-control-sm mb-3"
            aria-label="Il PDF"
            @change="scegliPegFile"
          />
          <div v-else class="mb-3">
            <EditorTesto v-model="pegTesto" etichetta="Testo del progetto" />
          </div>
          <div class="form-field mb-3">
            <input id="peg-avvisa" v-model="pegAvvisa" type="checkbox" class="check" />
            <label for="peg-avvisa">Avvisa soci e genitori per email</label>
          </div>
          <div class="d-flex gap-3">
            <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
              Carica
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="pegAperto = false">
              Annulla
            </button>
          </div>
        </form>
      </template>
    </section>

    <section class="card card-body mb-5">
      <div class="d-flex flex-wrap align-items-center gap-3 mb-3">
        <h2 class="h5 mb-0">Criteri di ammissione</h2>
        <RouterLink
          v-if="pagina.peg?.puo_gestire"
          :to="{ name: 'criteri-ammissione' }"
          class="btn btn-sm btn-outline theme-primary ms-auto"
        >
          Compila o aggiorna
        </RouterLink>
      </div>
      <CriteriAmmissione />
    </section>
    <section class="mb-5">
      <div class="d-flex flex-wrap align-items-center gap-3 mb-3">
        <h2 class="h5 mb-0">Documenti</h2>
        <button
          v-if="pagina.puo_caricare && !aperto"
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          @click="nuovo"
        >
          Carica un documento
        </button>
      </div>

      <form v-if="aperto" class="card card-body mb-5" @submit.prevent="salva">
        <div class="mb-3">
          <label class="form-label small" for="doc-titolo">Titolo</label>
          <input
            id="doc-titolo"
            v-model="modulo.titolo"
            class="form-control form-control-sm"
            maxlength="160"
            required
          />
        </div>
        <div class="mb-3">
          <label class="form-label small" for="doc-descrizione">Breve descrizione</label>
          <input
            id="doc-descrizione"
            v-model="modulo.descrizione"
            class="form-control form-control-sm"
            maxlength="500"
            required
          />
        </div>
        <div class="mb-3">
          <label class="form-label small" for="doc-file">
            {{ inModifica === null ? 'File' : 'Sostituisci il file (facoltativo)' }}: PDF, Word,
            Excel o PowerPoint, al massimo {{ massimo }}
          </label>
          <input
            id="doc-file"
            type="file"
            class="form-control form-control-sm"
            @change="scegliFile"
          />
        </div>
        <div class="row g-3 mb-3">
          <div class="col-12 sm:col-6">
            <label class="form-label small" for="doc-durata">Fino a quando si vede</label>
            <select id="doc-durata" v-model="modulo.durata" class="form-control form-control-sm">
              <option v-for="d in durate" :key="d.valore" :value="d.valore">{{ d.nome }}</option>
            </select>
          </div>
          <div v-if="modulo.durata === 'ANNO'" class="col-12 sm:col-6">
            <label class="form-label small" for="doc-anno">Anno associativo</label>
            <select id="doc-anno" v-model="modulo.anno" class="form-control form-control-sm">
              <option :value="null">Scegli…</option>
              <option v-for="a in pagina.anni" :key="a.anno" :value="a.anno">
                {{ a.etichetta }}
              </option>
            </select>
          </div>
          <div v-if="modulo.durata === 'DATA'" class="col-12 sm:col-6">
            <label class="form-label small" for="doc-scade">Ultimo giorno</label>
            <input
              id="doc-scade"
              v-model="modulo.scade_il"
              type="date"
              class="form-control form-control-sm"
            />
          </div>
        </div>
        <p v-if="modulo.durata !== 'SEMPRE'" class="small fg-2 mb-3">
          Alla scadenza il documento si cancella anche dal server.
        </p>
        <fieldset class="mb-3">
          <legend class="form-label small">Chi lo vede (i capi lo vedono sempre)</legend>
          <div class="form-field mb-1">
            <input id="doc-coca" v-model="modulo.per_coca" type="checkbox" class="check" />
            <label for="doc-coca">Comunità capi</label>
          </div>
          <div class="form-field mb-1">
            <input id="doc-genitori" v-model="modulo.per_genitori" type="checkbox" class="check" />
            <label for="doc-genitori">Tutti i genitori del gruppo</label>
          </div>
          <div v-for="u in pagina.unita" :key="u.id" class="form-field mb-1">
            <input
              :id="`doc-unita-${u.id}`"
              v-model="modulo.unita"
              type="checkbox"
              class="check"
              :value="u.id"
            />
            <label :for="`doc-unita-${u.id}`">{{ u.nome }}</label>
          </div>
        </fieldset>
        <fieldset v-if="modulo.unita.length" class="mb-3">
          <legend class="form-label small">Delle unità scelte, oltre allo staff</legend>
          <div class="form-field mb-1">
            <input
              id="doc-unita-ragazzi"
              v-model="modulo.unita_ragazzi"
              type="checkbox"
              class="check"
            />
            <label for="doc-unita-ragazzi">I ragazzi</label>
          </div>
          <div class="form-field mb-1">
            <input
              id="doc-unita-genitori"
              v-model="modulo.unita_genitori"
              type="checkbox"
              class="check"
            />
            <label for="doc-unita-genitori">I genitori</label>
          </div>
        </fieldset>
        <div class="form-field mb-3">
          <input id="doc-avvisa" v-model="modulo.avvisa" type="checkbox" class="check" />
          <label for="doc-avvisa">Avvisa i destinatari per email</label>
        </div>
        <div class="d-flex gap-3">
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Salva
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="aperto = false">Annulla</button>
        </div>
      </form>

      <p v-if="!pagina.documenti.length" class="fg-2 small">Nessun documento per ora.</p>
      <article v-for="d in pagina.documenti" :key="d.id" class="card card-body mb-3">
        <div class="d-flex flex-wrap align-items-center gap-3 mb-1">
          <a :href="fileDocumento(d.id)" :data-dimensione="d.dimensione">
            <strong>{{ d.titolo }}</strong>
          </a>
          <span v-if="d.aggiornato" class="badge theme-success">Aggiornato</span>
        </div>
        <p class="mb-1">{{ d.descrizione }}</p>
        <p class="small fg-2 mb-0">
          {{ d.nome_file }} · {{ misura(d.dimensione) }}
          <template v-if="d.ultimo_giorno"> · fino al {{ giorno(d.ultimo_giorno) }}</template>
        </p>
        <div v-if="d.puo_modificare" class="d-flex flex-wrap gap-3 mt-3">
          <button type="button" class="btn btn-link btn-sm p-0" @click="modifica(d)">
            Modifica
          </button>
          <button
            v-if="daEliminare !== d.id"
            type="button"
            class="btn btn-link btn-sm p-0"
            @click="daEliminare = d.id"
          >
            Elimina
          </button>
          <span v-else class="small">
            Eliminarlo anche dal server?
            <button
              type="button"
              class="btn btn-sm btn-solid theme-danger py-0"
              :disabled="inCorso"
              @click="elimina(d.id)"
            >
              Sì
            </button>
            <button type="button" class="btn btn-sm btn-link py-0" @click="daEliminare = null">
              No
            </button>
          </span>
        </div>
      </article>
    </section>
  </div>
  <div v-else-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
</template>
