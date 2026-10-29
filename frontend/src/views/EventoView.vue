<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

import {
  api,
  foglioPresenze,
  percorsoPresenze,
  type DettaglioEvento,
  type Partecipante,
  type StatoPresenza,
} from '@/api/qdc'
import CopiaLocale from '@/components/CopiaLocale.vue'
import QuotaEvento from '@/components/QuotaEvento.vue'
import RendicontoEvento from '@/components/RendicontoEvento.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache, salvaInCache } from '@/offline/cache'
import { scrivi } from '@/offline/outbox'

// One event: the family says whether their child takes part; the staff sees everyone,
// may not invite someone (with a reason the family reads) and marks attendance, also
// offline (DEC-75, DEC-78). Cached for offline use.
const props = defineProps<{ id: number }>()
const { errore, inCorso, esegui } = useErrore()
const evento = ref<DettaglioEvento | null>(null)
const copiaDel = ref<string | null>(null)
const esito = ref('')
const presenze = reactive<Record<number, StatoPresenza | null>>({})
const esclusione = reactive({ persona: 0, motivo: '' })
const annullamento = reactive({ aperto: false, motivo: '' })

const chiave = () => `evento:${props.id}`

function mostra(dati: DettaglioEvento) {
  evento.value = dati
  for (const p of dati.partecipanti) presenze[p.persona_id] = p.presenza
}

async function carica() {
  const letto = await esegui(() => leggiConCache(chiave(), () => api.evento(props.id)))
  if (!letto) return
  mostra(letto.dati)
  copiaDel.value = letto.copiaDel
}
watch(() => props.id, carica, { immediate: true })

const invitati = computed(
  () => evento.value?.partecipanti.filter((p) => p.stato !== 'NON_INVITATO') ?? [],
)
const modificate = computed(() =>
  invitati.value.filter((p) => (presenze[p.persona_id] ?? null) !== p.presenza),
)
const conteggio = computed(() => {
  const valori = invitati.value.map((p) => presenze[p.persona_id])
  return {
    presenti: valori.filter((v) => v === 'PRESENTE').length,
    assenti: valori.filter((v) => v === 'ASSENTE').length,
    giustificati: valori.filter((v) => v === 'GIUSTIFICATO').length,
  }
})

function tuttiPresenti() {
  for (const p of invitati.value) {
    if (!presenze[p.persona_id]) {
      presenze[p.persona_id] = p.stato === 'NON_PARTECIPA' ? 'GIUSTIFICATO' : 'PRESENTE'
    }
  }
}

async function salvaPresenze() {
  if (!evento.value) return
  const segni = modificate.value.map((p) => ({
    persona_id: p.persona_id,
    stato: presenze[p.persona_id]!,
  }))
  const risultato = await esegui(() =>
    scrivi({
      metodo: 'PUT',
      percorso: percorsoPresenze(props.id),
      corpo: { segni },
      // Stored in clear in the queue: no names.
      descrizione: `Presenze di ${segni.length} soci (evento n. ${props.id})`,
    }),
  )
  if (!risultato) return
  // Keep the device copy in step, so the marks are there offline too.
  const copia: DettaglioEvento = {
    ...evento.value,
    partecipanti: evento.value.partecipanti.map((p) => ({
      ...p,
      presenza: presenze[p.persona_id] ?? p.presenza,
    })),
  }
  await salvaInCache(chiave(), copia)
  mostra(copia)
  esito.value = risultato.inCoda
    ? 'Presenze salvate sul telefono: saranno inviate appena torna la rete.'
    : 'Presenze salvate.'
}

async function partecipa(persona: number, si: boolean) {
  esito.value = ''
  if (await esegui(() => api.partecipa(props.id, persona, si))) await carica()
}

async function nonInvitare(p: Partecipante) {
  const dati = await esegui(() => api.nonInvitare(props.id, p.persona_id, esclusione.motivo))
  if (!dati) return
  esclusione.persona = 0
  mostra(dati)
}

async function reinvita(p: Partecipante) {
  const dati = await esegui(() => api.reinvita(props.id, p.persona_id))
  if (dati) mostra(dati)
}

async function annulla() {
  if (!(await esegui(() => api.annullaEvento(props.id, annullamento.motivo)))) return
  annullamento.aperto = false
  await carica()
}

const dataOra = (iso: string) =>
  new Date(iso).toLocaleString('it-IT', {
    weekday: 'short',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
const STATI: [StatoPresenza, string][] = [
  ['PRESENTE', 'Presente'],
  ['ASSENTE', 'Assente'],
  ['GIUSTIFICATO', 'Giustificato'],
]
</script>

<template>
  <section v-if="evento">
    <div class="d-flex flex-wrap align-items-baseline gap-3">
      <h1 class="h4 mb-1" :class="{ 'text-decoration-line-through': evento.annullato }">
        {{ evento.titolo }}
      </h1>
      <span v-if="evento.annullato" class="badge theme-danger">Annullato</span>
      <CopiaLocale :del="copiaDel" />
    </div>
    <p class="fg-2 small mb-3">
      {{ evento.tipo_nome }}
      <template v-if="evento.cerchia !== 'TUTTI'"> · {{ evento.cerchia_nome }}</template> ·
      {{
        evento.livello === 'GRUPPO'
          ? 'tutto il gruppo'
          : evento.squadriglia
            ? `Sq. ${evento.squadriglia}`
            : evento.unita_nomi.join(', ')
      }}
    </p>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>
    <div v-if="evento.annullato" class="alert theme-warning small">
      <div>Annullato: {{ evento.motivo_annullamento }}</div>
    </div>

    <div class="card card-body mb-5">
      <div>
        <strong>Inizio</strong> {{ dataOra(evento.inizio) }}<br />
        <strong>Fine</strong> {{ dataOra(evento.fine) }}
      </div>
      <div v-if="evento.luogo"><strong>Luogo</strong> {{ evento.luogo }}</div>
      <p v-if="evento.descrizione" class="mb-0 mt-3 testo-a-capo">{{ evento.descrizione }}</p>
      <div v-if="evento.note_genitori" class="mt-3">
        <strong>Note per i genitori</strong>
        <span class="small fg-2">(non le vedono i ragazzi)</span>
        <p class="mb-0 testo-a-capo">{{ evento.note_genitori }}</p>
      </div>
    </div>

    <QuotaEvento
      :evento="evento.id"
      :quota="evento.quota"
      :puo-gestire="evento.puo_gestire && !evento.annullato"
      :in-famiglia="evento.mie.length > 0"
      @cambiata="carica"
    />

    <RendicontoEvento
      v-if="evento.puo_gestire || evento.partecipanti.length"
      :evento="evento.id"
      :campo="evento.tipo === 'CAMPO'"
    />

    <!-- The family -->
    <section v-if="evento.mie.length" class="mb-5">
      <h2 class="h5">Partecipazione</h2>
      <ul class="list-group">
        <li v-for="m in evento.mie" :key="m.persona_id" class="list-group-item">
          <div class="d-flex flex-wrap align-items-center justify-content-between gap-3">
            <strong>{{ m.persona }}</strong>
            <span v-if="m.stato === 'NON_INVITATO'" class="badge theme-danger">Non invitato</span>
            <template v-else-if="m.puo_segnalare && !evento.annullato">
              <div class="form-field mb-0">
                <input
                  :id="`partecipa-${m.persona_id}`"
                  type="checkbox"
                  class="switch"
                  role="switch"
                  :checked="m.stato === 'INVITATO'"
                  :disabled="inCorso"
                  @change="partecipa(m.persona_id, ($event.target as HTMLInputElement).checked)"
                />
                <label :for="`partecipa-${m.persona_id}`">
                  {{ m.stato === 'INVITATO' ? 'Partecipa' : 'Non partecipa' }}
                </label>
              </div>
            </template>
          </div>
          <div v-if="m.stato === 'NON_INVITATO'" class="small">
            Lo staff ha deciso di non invitarlo: {{ m.motivo }}
          </div>
        </li>
      </ul>
    </section>

    <!-- The staff -->
    <section v-if="evento.partecipanti.length" class="mb-5">
      <div class="d-flex flex-wrap align-items-center gap-3 mb-3">
        <h2 class="h5 mb-0">Partecipanti</h2>
        <span class="small fg-2">
          {{ conteggio.presenti }} {{ conteggio.presenti === 1 ? 'presente' : 'presenti' }} ·
          {{ conteggio.assenti }} {{ conteggio.assenti === 1 ? 'assente' : 'assenti' }} ·
          {{ conteggio.giustificati }}
          {{ conteggio.giustificati === 1 ? 'giustificato' : 'giustificati' }}
        </span>
        <a v-if="evento.puo_presenze" :href="foglioPresenze(evento.id)" class="small">
          Foglio da stampare
        </a>
      </div>
      <div v-if="evento.puo_presenze && !evento.annullato" class="d-flex gap-3 mb-3">
        <button type="button" class="btn btn-sm btn-outline theme-primary" @click="tuttiPresenti">
          Segna gli altri presenti
        </button>
        <button
          type="button"
          class="btn btn-sm btn-solid theme-primary"
          :disabled="inCorso || !modificate.length"
          @click="salvaPresenze"
        >
          Salva le presenze
        </button>
      </div>
      <ul class="list-group">
        <li v-for="p in evento.partecipanti" :key="p.persona_id" class="list-group-item">
          <div class="d-flex flex-wrap align-items-center justify-content-between gap-3">
            <span>
              {{ p.cognome }} {{ p.nome }}
              <span v-if="p.stato === 'NON_PARTECIPA'" class="badge theme-warning ms-1">
                Non partecipa
              </span>
              <span v-if="p.stato === 'NON_INVITATO'" class="badge theme-danger ms-1">
                Non invitato
              </span>
            </span>
            <div
              v-if="evento.puo_presenze && p.stato !== 'NON_INVITATO' && !evento.annullato"
              class="d-flex gap-1"
              role="group"
              :aria-label="`Presenza di ${p.nome} ${p.cognome}`"
            >
              <button
                v-for="[stato, etichetta] in STATI"
                :key="stato"
                type="button"
                class="btn btn-sm"
                :class="
                  presenze[p.persona_id] === stato
                    ? 'btn-solid theme-primary'
                    : 'btn-outline theme-secondary'
                "
                :aria-pressed="presenze[p.persona_id] === stato"
                @click="presenze[p.persona_id] = stato"
              >
                {{ etichetta }}
              </button>
            </div>
            <span v-else-if="p.presenza" class="small">
              {{ STATI.find(([s]) => s === p.presenza)?.[1] }}
            </span>
          </div>
          <div v-if="p.stato === 'NON_INVITATO'" class="small fg-2">{{ p.motivo }}</div>
          <div v-if="evento.puo_non_invitare && !evento.annullato" class="small">
            <button
              v-if="p.stato === 'NON_INVITATO'"
              type="button"
              class="btn btn-sm btn-link"
              @click="reinvita(p)"
            >
              Invita di nuovo
            </button>
            <button
              v-else-if="esclusione.persona !== p.persona_id"
              type="button"
              class="btn btn-sm btn-link"
              @click="Object.assign(esclusione, { persona: p.persona_id, motivo: '' })"
            >
              Non invitare…
            </button>
            <form
              v-else
              class="d-flex flex-wrap align-items-end gap-3 mt-1"
              @submit.prevent="nonInvitare(p)"
            >
              <div class="flex-grow-1">
                <label class="form-label small" :for="`motivo-${p.persona_id}`">
                  Motivo (la famiglia lo legge)
                </label>
                <input
                  :id="`motivo-${p.persona_id}`"
                  v-model="esclusione.motivo"
                  class="form-control form-control-sm"
                  required
                />
              </div>
              <button type="submit" class="btn btn-sm btn-solid theme-danger" :disabled="inCorso">
                Non invitare
              </button>
              <button type="button" class="btn btn-sm btn-link" @click="esclusione.persona = 0">
                Annulla
              </button>
            </form>
          </div>
        </li>
      </ul>
    </section>

    <section v-if="evento.puo_gestire && !evento.annullato">
      <button
        v-if="!annullamento.aperto"
        type="button"
        class="btn btn-sm btn-outline theme-danger"
        @click="annullamento.aperto = true"
      >
        Annulla l'evento
      </button>
      <form v-else class="d-flex flex-wrap align-items-end gap-3" @submit.prevent="annulla">
        <div class="flex-grow-1">
          <label class="form-label small" for="motivo-annullamento">Perché lo annulli?</label>
          <input
            id="motivo-annullamento"
            v-model="annullamento.motivo"
            class="form-control form-control-sm"
            required
          />
        </div>
        <button type="submit" class="btn btn-sm btn-solid theme-danger" :disabled="inCorso">
          Annulla l'evento
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="annullamento.aperto = false">
          Lascia stare
        </button>
      </form>
    </section>
  </section>
</template>
