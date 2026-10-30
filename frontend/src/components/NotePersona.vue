<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

import { api, percorsoNota, percorsoNote, type Nota, type NotaIn, type NoteSchede } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'
import { scrivi } from '@/offline/outbox'

// Notes on a ragazzo (DEC-39, DEC-40): staff notes, read by the whole Co.Ca. and, if
// chosen, by the ragazzo, the parents and (E/G only) the CSQ; CSQ notes, read by the
// staff and, if chosen, by the member and the parents. What goes beyond the Co.Ca. is
// marked. Read from the device copy offline; written also offline through the queue
// (DEC-95), the last write wins (DEC-96). The queue description has no text and no name.
const props = defineProps<{ persona: number }>()
const { errore, inCorso, esegui } = useErrore()
const dati = ref<NoteSchede | null>(null)
const esito = ref('')

async function carica() {
  const letto = await esegui(() =>
    leggiConCache(`note:${props.persona}`, () => api.note(props.persona)),
  )
  dati.value = letto?.dati ?? null
}
watch(() => props.persona, carica, { immediate: true })

const vuota = (): NotaIn => ({
  testo: '',
  visibile_ragazzo: false,
  visibile_genitori: false,
  visibile_csq: false,
})
// 0: closed; -1: new; otherwise the note being changed.
const aperta = ref(0)
const modulo = reactive<NotaIn>(vuota())

function apri(nota: Nota | null) {
  aperta.value = nota ? nota.id : -1
  Object.assign(
    modulo,
    nota
      ? {
          testo: nota.testo,
          visibile_ragazzo: nota.visibile_ragazzo,
          visibile_genitori: nota.visibile_genitori,
          visibile_csq: nota.visibile_csq,
        }
      : vuota(),
  )
}

async function dopo(inCoda: boolean) {
  aperta.value = 0
  esito.value = inCoda ? 'Salvata sul telefono: sarà inviata appena torna la rete.' : 'Salvata.'
  if (!inCoda) await carica()
}

async function salva() {
  const nuova = aperta.value === -1
  const risultato = await esegui(() =>
    scrivi({
      metodo: nuova ? 'POST' : 'PUT',
      percorso: nuova ? percorsoNote(props.persona) : percorsoNota(aperta.value),
      corpo: { ...modulo },
      descrizione: nuova ? `Nuova nota (scheda n. ${props.persona})` : `Nota n. ${aperta.value}`,
    }),
  )
  if (risultato) await dopo(risultato.inCoda)
}

async function cancella(nota: Nota) {
  const risultato = await esegui(() =>
    scrivi({
      metodo: 'DELETE',
      percorso: percorsoNota(nota.id),
      descrizione: `Nota n. ${nota.id} cancellata`,
    }),
  )
  if (risultato) await dopo(risultato.inCoda)
}

function chiLaLegge(n: Nota): string {
  const chi = [
    n.visibile_ragazzo ? 'il ragazzo' : '',
    n.visibile_genitori ? 'i genitori' : '',
    n.visibile_csq ? 'il capo squadriglia' : '',
  ].filter(Boolean)
  return chi.length ? `la leggono anche ${chi.join(', ')}` : 'solo la Co.Ca.'
}
const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
</script>

<template>
  <section v-if="dati && (dati.note.length || dati.scrive)" class="card card-body mb-5">
    <div class="d-flex flex-wrap align-items-center gap-3 mb-3">
      <h2 class="h5 mb-0">Note</h2>
      <button
        v-if="dati.scrive && !aperta"
        type="button"
        class="btn btn-sm btn-outline theme-primary ms-auto"
        @click="apri(null)"
      >
        Nuova nota
      </button>
    </div>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>

    <form v-if="aperta" class="mb-3" @submit.prevent="salva">
      <label class="form-label small" for="nota-testo">Nota</label>
      <textarea
        id="nota-testo"
        v-model="modulo.testo"
        class="form-control form-control-sm mb-3"
        rows="3"
        required
        :readonly="aperta > 0 && !dati.note.find((n) => n.id === aperta)?.puo_modificare"
      />
      <fieldset class="mb-3">
        <legend class="form-label small">La Co.Ca. la legge sempre. Mostrala anche a:</legend>
        <div class="form-field">
          <input
            id="nota-ragazzo"
            v-model="modulo.visibile_ragazzo"
            type="checkbox"
            class="check"
          />
          <label class="small" for="nota-ragazzo">il ragazzo o la ragazza</label>
        </div>
        <div class="form-field">
          <input
            id="nota-genitori"
            v-model="modulo.visibile_genitori"
            type="checkbox"
            class="check"
          />
          <label class="small" for="nota-genitori">i genitori</label>
        </div>
        <div v-if="dati.scrive === 'STAFF' && dati.csq_possibile" class="form-field">
          <input id="nota-csq" v-model="modulo.visibile_csq" type="checkbox" class="check" />
          <label class="small" for="nota-csq"
            >il capo squadriglia (mai gli altri squadriglieri)</label
          >
        </div>
      </fieldset>
      <div class="d-flex gap-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Salva
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="aperta = 0">Annulla</button>
      </div>
    </form>

    <p v-if="!dati.note.length" class="small fg-2 mb-0">Nessuna nota.</p>
    <ul v-else class="list-group">
      <li v-for="n in dati.note" :key="n.id" class="list-group-item">
        <div class="d-flex flex-wrap justify-content-between gap-3">
          <span class="small fg-2">
            {{ n.tipo_nome }}<template v-if="n.autore"> · {{ n.autore }}</template> ·
            {{ data(n.aggiornata_il) }}
          </span>
          <span class="badge" :class="n.condivisa_fuori_coca ? 'theme-warning' : 'theme-secondary'">
            {{ chiLaLegge(n) }}
          </span>
        </div>
        <p class="testo-a-capo mb-1">{{ n.testo }}</p>
        <div v-if="!aperta" class="d-flex gap-1">
          <button
            v-if="n.puo_modificare || n.puo_cambiare_visibilita"
            type="button"
            class="btn btn-sm btn-link px-0"
            @click="apri(n)"
          >
            {{ n.puo_modificare ? 'Modifica' : 'Cambia chi la legge' }}
          </button>
          <button
            v-if="n.puo_modificare"
            type="button"
            class="btn btn-sm btn-link"
            :disabled="inCorso"
            @click="cancella(n)"
          >
            Cancella
          </button>
        </div>
      </li>
    </ul>
  </section>
</template>
