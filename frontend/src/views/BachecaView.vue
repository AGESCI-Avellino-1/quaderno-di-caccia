<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import {
  allegatoAvviso,
  api,
  type Avviso,
  type AvvisoIn,
  type Bacheca,
  type DestinatariAvviso,
} from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The notice board (DEC-03, DEC-218…DEC-220): notices only, no replies, no read
// receipts. The unit staff publish for their unit, the capigruppo for the group; the
// capi also see the expired ones. Online only.
const { errore, inCorso, esegui } = useErrore()
const dati = ref<Bacheca | null>(null)
const archivio = ref(false)
const esito = ref('')

async function carica() {
  dati.value = (await esegui(() => api.bacheca(archivio.value))) ?? dati.value
}
onMounted(carica)

const DESTINATARI: { valore: DestinatariAvviso; nome: string }[] = [
  { valore: 'FAMIGLIE', nome: 'Famiglie e ragazzi' },
  { valore: 'GENITORI', nome: 'Solo i genitori' },
  { valore: 'RAGAZZI', nome: 'Solo i ragazzi' },
  { valore: 'CAPI', nome: 'Comunità capi' },
]

function traGiorni(giorni: number): string {
  const d = new Date()
  d.setDate(d.getDate() + giorni)
  return d.toLocaleDateString('sv')
}
const oggi = traGiorni(0)

// 0: closed; -1: new; otherwise the notice being changed.
const aperto = ref(0)
const modulo = reactive<AvvisoIn & { dove: string }>({
  titolo: '',
  testo: '',
  unita_id: null,
  dove: '',
  destinatari: 'FAMIGLIE',
  scade_il: traGiorni(14),
  invia_email: false,
})
// Who the user may address there: any capo writes to the Co.Ca. (DEC-218).
const destinatariPossibili = computed(() => {
  const dove = dati.value?.pubblica_in.find((d) => String(d.unita_id ?? '') === modulo.dove)
  return DESTINATARI.filter((d) => dove?.destinatari.includes(d.valore))
})

function adattaDestinatari() {
  const possibili = destinatariPossibili.value
  if (possibili.length && !possibili.some((d) => d.valore === modulo.destinatari)) {
    modulo.destinatari = possibili[0]!.valore
  }
}

function apri(avviso: Avviso | null) {
  esito.value = ''
  aperto.value = avviso?.id ?? -1
  const primo = dati.value?.pubblica_in[0]
  Object.assign(modulo, {
    titolo: avviso?.titolo ?? '',
    testo: avviso?.testo ?? '',
    dove: String(avviso ? (avviso.unita_id ?? '') : (primo?.unita_id ?? '')),
    destinatari: avviso?.destinatari ?? primo?.destinatari[0] ?? 'FAMIGLIE',
    scade_il: avviso?.scade_il ?? traGiorni(14),
    invia_email: false,
  })
}

async function salva() {
  const corpo: AvvisoIn = {
    titolo: modulo.titolo,
    testo: modulo.testo,
    unita_id: modulo.dove === '' ? null : Number(modulo.dove),
    destinatari: modulo.destinatari,
    scade_il: modulo.scade_il,
    invia_email: modulo.invia_email,
  }
  const nuovo = aperto.value === -1
  const salvato = await esegui(() =>
    nuovo ? api.pubblicaAvviso(corpo) : api.modificaAvviso(aperto.value, corpo),
  )
  if (!salvato) return
  aperto.value = 0
  esito.value = nuovo ? 'Avviso pubblicato.' : 'Avviso modificato.'
  await carica()
}

// The notice whose removal waits for a confirmation.
const daTogliere = ref(0)
async function togli(id: number) {
  if ((await esegui(() => api.togliAvviso(id))) === undefined) return
  daTogliere.value = 0
  esito.value = 'Avviso tolto.'
  await carica()
}

const allegato = reactive({ avviso: 0, titolo: '', file: null as File | null })
function scegliFile(evento: Event) {
  allegato.file = (evento.target as HTMLInputElement).files?.[0] ?? null
}
async function caricaAllegato() {
  if (!allegato.file) return
  const file = allegato.file
  const fatto = await esegui(() => api.caricaAllegatoAvviso(allegato.avviso, allegato.titolo, file))
  if (!fatto) return
  Object.assign(allegato, { avviso: 0, titolo: '', file: null })
  await carica()
}
async function togliAllegato(id: number) {
  if (await esegui(() => api.togliAllegatoAvviso(id))) await carica()
}

const data = (d: string) => new Date(d).toLocaleDateString('it-IT')
</script>

<template>
  <section style="max-width: 50rem">
    <h1 class="h4 mb-1">Bacheca</h1>
    <p class="fg-2 small">Gli avvisi dei capi per la tua unità e per il gruppo.</p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>
    <p v-if="inCorso && !dati" class="fg-2">Caricamento…</p>

    <template v-if="dati">
      <div class="d-flex flex-wrap align-items-center gap-3 mb-3">
        <button
          v-if="dati.pubblica_in.length && !aperto"
          type="button"
          class="btn btn-sm btn-solid theme-primary"
          @click="apri(null)"
        >
          Nuovo avviso
        </button>
        <div v-if="dati.vede_archivio" class="form-field mb-0">
          <input
            id="bacheca-archivio"
            v-model="archivio"
            type="checkbox"
            class="switch"
            role="switch"
            @change="carica"
          />
          <label for="bacheca-archivio">Mostra anche gli avvisi scaduti</label>
        </div>
      </div>

      <form v-if="aperto" class="card card-body mb-5" @submit.prevent="salva">
        <div class="row g-3">
          <div class="col-12">
            <label class="form-label small" for="avv-titolo">Titolo</label>
            <input
              id="avv-titolo"
              v-model="modulo.titolo"
              class="form-control form-control-sm"
              maxlength="160"
              required
            />
          </div>
          <div class="col-12">
            <label class="form-label small" for="avv-testo">Testo</label>
            <textarea
              id="avv-testo"
              v-model="modulo.testo"
              class="form-control form-control-sm"
              rows="5"
              required
            ></textarea>
          </div>
          <div class="col-12 md:col-6">
            <label class="form-label small" for="avv-dove">Per</label>
            <select
              id="avv-dove"
              v-model="modulo.dove"
              class="form-control form-control-sm"
              @change="adattaDestinatari"
            >
              <option
                v-for="d in dati.pubblica_in"
                :key="d.unita_id ?? 'gruppo'"
                :value="String(d.unita_id ?? '')"
              >
                {{ d.nome }}
              </option>
            </select>
          </div>
          <div class="col-12 md:col-6">
            <label class="form-label small" for="avv-destinatari">A chi</label>
            <select
              id="avv-destinatari"
              v-model="modulo.destinatari"
              class="form-control form-control-sm"
            >
              <option v-for="d in destinatariPossibili" :key="d.valore" :value="d.valore">
                {{ d.nome }}
              </option>
            </select>
          </div>
          <div class="col-12 md:col-6">
            <label class="form-label small" for="avv-scade">Mostralo fino al</label>
            <input
              id="avv-scade"
              v-model="modulo.scade_il"
              type="date"
              :min="oggi"
              class="form-control form-control-sm"
              required
            />
          </div>
          <div v-if="aperto === -1" class="col-12 md:col-6 d-flex align-items-end">
            <div class="form-field mb-0">
              <input
                id="avv-email"
                v-model="modulo.invia_email"
                type="checkbox"
                class="switch"
                role="switch"
              />
              <label for="avv-email">Manda anche un'email</label>
            </div>
          </div>
        </div>
        <p v-if="aperto === -1" class="small fg-2 mt-1 mb-0">
          Gli allegati si aggiungono dopo la pubblicazione. Chi ha scelto di non ricevere le email
          degli avvisi lo trova solo in bacheca.
        </p>
        <div class="d-flex gap-3 mt-3">
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            {{ aperto === -1 ? 'Pubblica' : 'Salva' }}
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="aperto = 0">Annulla</button>
        </div>
      </form>

      <p v-if="!dati.avvisi.length" class="fg-2 small">Nessun avviso.</p>
      <article v-for="a in dati.avvisi" :key="a.id" class="card card-body mb-3">
        <div class="d-flex flex-wrap align-items-center gap-1 mb-1">
          <h2 class="h5 mb-0 me-1">{{ a.titolo }}</h2>
          <span v-if="a.scaduto" class="badge theme-secondary">scaduto</span>
        </div>
        <p class="small fg-2 mb-3">
          {{ a.dove }} · {{ a.destinatari_nome }} · pubblicato il {{ data(a.pubblicato_il) }}
          <template v-if="a.autore"> da {{ a.autore }}</template>
          · fino al {{ data(a.scade_il) }}
          <template v-if="a.email_inviata"> · mandato anche per email</template>
        </p>
        <p class="mb-3" style="white-space: pre-line">{{ a.testo }}</p>
        <ul v-if="a.allegati.length" class="list-unstyled small mb-3">
          <li v-for="f in a.allegati" :key="f.id">
            <a :href="allegatoAvviso(f.id)" target="_blank" rel="noopener">{{ f.titolo }}</a>
            <button
              v-if="a.puo_modificare"
              type="button"
              class="btn btn-sm btn-link py-0"
              :disabled="inCorso"
              @click="togliAllegato(f.id)"
            >
              Togli
            </button>
          </li>
        </ul>
        <form
          v-if="allegato.avviso === a.id"
          class="d-flex flex-wrap align-items-end gap-3 mb-3"
          @submit.prevent="caricaAllegato"
        >
          <div>
            <label class="form-label small" :for="`all-titolo-${a.id}`">Che cos'è</label>
            <input
              :id="`all-titolo-${a.id}`"
              v-model="allegato.titolo"
              class="form-control form-control-sm"
              maxlength="120"
              placeholder="Es. Programma del campo"
              required
            />
          </div>
          <div>
            <label class="form-label small" :for="`all-file-${a.id}`">PDF o immagine</label>
            <input
              :id="`all-file-${a.id}`"
              type="file"
              accept="application/pdf,image/jpeg,image/png"
              class="form-control form-control-sm"
              required
              @change="scegliFile"
            />
          </div>
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Carica
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="allegato.avviso = 0">
            Annulla
          </button>
        </form>
        <div v-if="a.puo_modificare && !aperto" class="d-flex flex-wrap gap-3">
          <button type="button" class="btn btn-sm btn-link px-0" @click="apri(a)">Modifica</button>
          <button
            v-if="allegato.avviso !== a.id"
            type="button"
            class="btn btn-sm btn-link px-0"
            @click="Object.assign(allegato, { avviso: a.id, titolo: '', file: null })"
          >
            Aggiungi un allegato
          </button>
          <button
            v-if="daTogliere !== a.id"
            type="button"
            class="btn btn-sm btn-link px-0"
            @click="daTogliere = a.id"
          >
            Togli
          </button>
          <template v-else>
            <span class="small">Togliere l'avviso e i suoi allegati?</span>
            <button
              type="button"
              class="btn btn-sm btn-outline theme-danger"
              :disabled="inCorso"
              @click="togli(a.id)"
            >
              Sì, togli
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="daTogliere = 0">No</button>
          </template>
        </div>
      </article>
    </template>
  </section>
</template>
