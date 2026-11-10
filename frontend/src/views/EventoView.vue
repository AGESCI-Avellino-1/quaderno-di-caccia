<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

import {
  api,
  eventoIcs,
  foglioPresenze,
  percorsoPresenze,
  schedeSanitarieEventoPdf,
  type DettaglioEvento,
  type Partecipante,
  type StatoPresenza,
  type TipoEvento,
} from '@/api/qdc'
import ImmagineAnimale from '@/components/ImmagineAnimale.vue'
import ConvocazioneRiunione from '@/components/ConvocazioneRiunione.vue'
import OrdineDelGiorno from '@/components/OrdineDelGiorno.vue'
import CopiaLocale from '@/components/CopiaLocale.vue'
import ReperibilitaEvento from '@/components/ReperibilitaEvento.vue'
import VerbaleRiunione from '@/components/VerbaleRiunione.vue'
import VerbaliCollegati from '@/components/VerbaliCollegati.vue'
import EventoBC from '@/components/EventoBC.vue'
import { dataEOra } from '@/eventi/orario'
import ModificaRiunione from '@/components/ModificaRiunione.vue'
import QuotaEvento from '@/components/QuotaEvento.vue'
import RendicontoEvento from '@/components/RendicontoEvento.vue'
import { useErrore } from '@/composables/useErrore'
import { useNomePagina } from '@/composables/useNomePagina'
import { leggiConCache, salvaInCache } from '@/offline/cache'
import { scrivi } from '@/offline/outbox'

// One event: the family says whether their child takes part; the staff sees everyone,
// may not invite someone (with a reason the family reads) and marks attendance, also
// offline (DEC-75, DEC-78). Cached for offline use. An event on BuonaCaccia shows its
// registrations instead (DEC-158…DEC-164), online only. A meeting (DEC-310) shows here
// too: its place, the uniform, the staff's notes; no fee.
const props = defineProps<{ id: number }>()
const { errore, inCorso, esegui } = useErrore()
const evento = ref<DettaglioEvento | null>(null)
useNomePagina(() => evento.value?.titolo)
const copiaDel = ref<string | null>(null)
const esito = ref('')
const presenze = reactive<Record<number, StatoPresenza | null>>({})
const esclusione = reactive({ persona: 0, motivo: '' })
const annullamento = reactive({ aperto: false, motivo: '' })
const riunione = computed(() => evento.value?.tipo === 'RIUNIONE')
// The place's own link or, without one, a search of its address (DEC-360).
const linkMappa = computed(() => {
  const localita = evento.value?.localita
  if (localita?.mappa) return localita.mappa
  if (!localita?.indirizzo_completo) return ''
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(localita.indirizzo_completo)}`
})
const modificaRiunione = ref(false)
// The parents' meetings and the assembly: a convocation, no uniform (DEC-327).
const convocata = computed(() => ['GENITORI', 'SOCI'].includes(evento.value?.cerchia ?? ''))

// One turn of this meeting to another group (DEC-312); the rotation goes on as planned.
const chiaveGruppo = (g: { squadriglia_id: number | null; sestiglia_id: number | null }) =>
  g.squadriglia_id ? `sq-${g.squadriglia_id}` : `se-${g.sestiglia_id}`

async function cambiaTurno(turno: string, valore: string) {
  if (!valore) return
  const [tipo, id] = valore.split('-')
  const fatto = await esegui(() =>
    api.cambiaTurno(props.id, {
      turno,
      squadriglia_id: tipo === 'sq' ? Number(id) : null,
      sestiglia_id: tipo === 'se' ? Number(id) : null,
    }),
  )
  if (fatto) await carica()
}

async function riunioneSalvata() {
  modificaRiunione.value = false
  esito.value = 'Riunione modificata.'
  await carica()
}

// Changing an event (DEC-75): what it is, when and where. Who is invited does not change
// (the API refuses it): for that, a new event. Families get an email if the dates or the
// place change (DEC-79). Online only, like creating it.
const modifica = ref<{
  titolo: string
  tipo: TipoEvento
  inizio: string
  fine: string
  luogo: string
  descrizione: string
  note_genitori: string
} | null>(null)
// An ISO instant as the value of a datetime-local field, in local time.
const inLocale = (iso: string) => {
  const d = new Date(iso)
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}

function apriModifica() {
  const e = evento.value!
  modifica.value = {
    titolo: e.titolo,
    tipo: e.tipo,
    inizio: inLocale(e.inizio),
    fine: inLocale(e.fine),
    luogo: e.luogo,
    descrizione: e.descrizione,
    note_genitori: e.note_genitori ?? '',
  }
}

async function salvaModifica() {
  const e = evento.value!
  const m = modifica.value!
  const fatto = await esegui(() =>
    api.modificaEvento(e.id, {
      ...m,
      inizio: new Date(m.inizio).toISOString(),
      fine: new Date(m.fine || m.inizio).toISOString(),
      livello: e.livello,
      branca: e.branca || null,
      unita: e.unita,
      squadriglia_id: e.squadriglia_id,
      cerchia: e.cerchia,
    }),
  )
  if (!fatto) return
  modifica.value = null
  esito.value = 'Evento modificato.'
  await carica()
}

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
    ? 'Presenze salvate su questo dispositivo: saranno inviate appena torna la rete.'
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
      <ImmagineAnimale :animale="evento.animale" />
      {{ evento.tipo_nome }}
      <template v-if="evento.cerchia !== 'TUTTI'"> · {{ evento.cerchia_nome }}</template> ·
      {{
        evento.livello === 'GRUPPO'
          ? 'tutto il gruppo'
          : evento.livello === 'ESTERNO'
            ? 'evento su BuonaCaccia'
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
        <strong>Inizio</strong> {{ dataEOra(evento.inizio, evento.senza_ora_inizio) }}<br />
        <strong>Fine</strong> {{ dataEOra(evento.fine, evento.senza_ora_fine) }}
      </div>
      <div v-if="evento.luogo">
        <strong>Luogo</strong> {{ evento.luogo }}
        <template v-if="evento.localita?.indirizzo_completo">
          · {{ evento.localita.indirizzo_completo }}</template
        >
        <a v-if="linkMappa" :href="linkMappa" target="_blank" rel="noopener" class="small ms-1"
          >mappa</a
        >
      </div>
      <!-- Online or mixed: the platform's link (DEC-402). -->
      <div v-if="evento.modalita && evento.modalita !== 'PRESENZA' && evento.link">
        <strong>{{ evento.modalita === 'ONLINE' ? 'Online' : 'Anche online' }}</strong>
        <a :href="evento.link" target="_blank" rel="noopener" class="ms-1">Entra nella riunione</a>
      </div>
      <div
        v-if="
          riunione &&
          !convocata &&
          evento.cerchia !== 'STAFF' &&
          evento.uniforme !== null &&
          evento.uniforme !== undefined
        "
      >
        <strong>Uniforme</strong> {{ evento.uniforme ? 'sì' : 'no' }}
      </div>
      <div v-if="!evento.annullato" class="mt-1">
        <a :href="eventoIcs(evento.id)" class="small" download>Aggiungi al calendario</a>
      </div>
      <p v-if="evento.descrizione" class="mb-0 mt-3 testo-a-capo">{{ evento.descrizione }}</p>
      <!-- eslint-disable-next-line vue/no-v-html -- HTML cleaned by the server (DEC-310) -->
      <div v-if="evento.informazioni" class="mt-3" v-html="evento.informazioni"></div>
      <div v-if="evento.note_genitori" class="mt-3">
        <strong>Note per i genitori</strong>
        <span class="small fg-2">(non le vedono i ragazzi/e)</span>
        <p class="mb-0 testo-a-capo">{{ evento.note_genitori }}</p>
      </div>
    </div>

    <OrdineDelGiorno
      v-if="riunione && evento.con_ordine_del_giorno"
      :key="`ordine-${evento.id}`"
      :evento="evento.id"
    />
    <ConvocazioneRiunione
      v-if="riunione && convocata"
      :key="`convocazione-${evento.id}`"
      :evento="evento.id"
    />
    <VerbaleRiunione v-if="riunione" :key="evento.id" :evento="evento.id" />
    <VerbaliCollegati v-if="riunione" :key="`collegati-${evento.id}`" :evento="evento.id" />

    <section v-if="riunione && evento.turni?.length" class="card card-body mb-5">
      <h2 class="h5">Turni</h2>
      <ul class="list-unstyled mb-0">
        <li
          v-for="t in evento.turni"
          :key="t.turno"
          class="d-flex flex-wrap align-items-center gap-3 py-1"
        >
          <strong>{{ t.turno }}</strong>
          <span>{{ t.gruppo }}</span>
          <span v-if="t.mio" class="badge theme-primary">il tuo</span>
          <span v-if="t.cambiato" class="small fg-2">cambiato a mano</span>
          <select
            v-if="evento.gruppi_turni?.length && !evento.annullato"
            class="form-control form-control-sm w-auto ms-auto"
            :aria-label="`Chi ha il turno ${t.turno}`"
            :disabled="inCorso"
            @change="cambiaTurno(t.turno, ($event.target as HTMLSelectElement).value)"
          >
            <option value="">Cambia…</option>
            <option v-for="g in evento.gruppi_turni" :key="g.nome" :value="chiaveGruppo(g)">
              {{ g.nome }}
            </option>
            <option v-if="t.cambiato" value="rotazione">Come da rotazione</option>
          </select>
        </li>
      </ul>
    </section>

    <section v-if="riunione && evento.puo_gestire && !evento.annullato" class="mb-5">
      <button
        v-if="!modificaRiunione"
        type="button"
        class="btn btn-sm btn-outline theme-primary"
        @click="modificaRiunione = true"
      >
        Modifica la riunione
      </button>
      <ModificaRiunione
        v-else
        :riunione="evento"
        @salvata="riunioneSalvata"
        @chiusa="modificaRiunione = false"
      />
    </section>
    <section
      v-else-if="evento.puo_gestire && !evento.annullato && evento.livello !== 'ESTERNO'"
      class="mb-5"
    >
      <button
        v-if="!modifica"
        type="button"
        class="btn btn-sm btn-outline theme-primary"
        @click="apriModifica"
      >
        Modifica
      </button>
      <form v-else class="card card-body" @submit.prevent="salvaModifica">
        <div class="row g-3">
          <div class="md:col-8">
            <label class="form-label small" for="mod-titolo">Titolo</label>
            <input
              id="mod-titolo"
              v-model="modifica.titolo"
              class="form-control form-control-sm"
              required
            />
          </div>
          <div class="md:col-4">
            <label class="form-label small" for="mod-tipo">Tipo</label>
            <select
              id="mod-tipo"
              v-model="modifica.tipo"
              class="form-control form-control-sm"
              :disabled="evento.tipo === 'MISSIONE'"
            >
              <option value="RIUNIONE">Riunione</option>
              <option value="USCITA">Uscita</option>
              <option value="CAMPO">Campo</option>
              <option v-if="evento.tipo === 'MISSIONE'" value="MISSIONE">
                Missione di squadriglia
              </option>
              <option value="AUTOFINANZIAMENTO">Autofinanziamento</option>
              <option value="ALTRO">Altro evento</option>
            </select>
          </div>
          <div class="md:col-6">
            <label class="form-label small" for="mod-inizio">Inizio</label>
            <input
              id="mod-inizio"
              v-model="modifica.inizio"
              type="datetime-local"
              class="form-control form-control-sm"
              required
            />
          </div>
          <div class="md:col-6">
            <label class="form-label small" for="mod-fine">Fine</label>
            <input
              id="mod-fine"
              v-model="modifica.fine"
              type="datetime-local"
              class="form-control form-control-sm"
              required
            />
          </div>
          <div class="col-12">
            <label class="form-label small" for="mod-luogo">Luogo</label>
            <input id="mod-luogo" v-model="modifica.luogo" class="form-control form-control-sm" />
          </div>
          <div class="col-12">
            <label class="form-label small" for="mod-descrizione">Descrizione</label>
            <textarea
              id="mod-descrizione"
              v-model="modifica.descrizione"
              rows="3"
              class="form-control form-control-sm"
            />
          </div>
          <div v-if="modifica.tipo === 'MISSIONE'" class="col-12">
            <label class="form-label small" for="mod-note"
              >Note per i genitori (le leggono i genitori e i capi, non i ragazzi/e)</label
            >
            <textarea
              id="mod-note"
              v-model="modifica.note_genitori"
              rows="3"
              class="form-control form-control-sm"
            />
          </div>
        </div>
        <p class="form-text mt-3 mb-0">
          Chi è invitato non cambia: per altre unità o un'altra squadriglia crea un evento nuovo. Se
          cambiano date o luogo, gli invitati ricevono un'email.
        </p>
        <div class="d-flex gap-3 mt-3">
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Salva
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="modifica = null">
            Annulla
          </button>
        </div>
      </form>
    </section>

    <EventoBC v-if="evento.livello === 'ESTERNO'" :evento="evento.id" @cambiato="carica" />

    <template v-else>
      <QuotaEvento
        v-if="!riunione"
        :evento="evento.id"
        :quota="evento.quota"
        :puo-gestire="evento.puo_gestire && !evento.annullato"
        :in-famiglia="evento.mie.length > 0"
        @cambiata="carica"
      />

      <RendicontoEvento
        v-if="!riunione && (evento.puo_gestire || evento.partecipanti.length)"
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
                  <div class="switch">
                    <input
                      :id="`partecipa-${m.persona_id}`"
                      type="checkbox"
                      role="switch"
                      :checked="m.stato === 'INVITATO'"
                      :disabled="inCorso"
                      @change="partecipa(m.persona_id, ($event.target as HTMLInputElement).checked)"
                    />
                  </div>
                  <label :for="`partecipa-${m.persona_id}`">
                    {{ m.stato === 'INVITATO' ? 'Partecipa' : 'Non partecipa' }}
                  </label>
                </div>
              </template>
            </div>
            <div v-if="m.stato === 'NON_INVITATO'" class="small">
              Lo staff ha deciso di non invitarlo: {{ m.motivo }}
            </div>
            <ReperibilitaEvento
              v-else-if="m.stato === 'INVITATO' && !evento.annullato"
              :evento="evento.id"
              :persona="m.persona_id"
            />
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
          <a
            v-if="evento.puo_stampare_schede"
            :href="schedeSanitarieEventoPdf(evento.id)"
            class="small"
          >
            Schede sanitarie dei partecipanti
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
    </template>

    <section v-if="evento.puo_gestire && !evento.annullato">
      <button
        v-if="!annullamento.aperto"
        type="button"
        class="btn btn-sm btn-outline theme-danger"
        @click="annullamento.aperto = true"
      >
        {{ riunione ? 'Annulla la riunione' : "Annulla l'evento" }}
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
          {{ riunione ? 'Annulla la riunione' : "Annulla l'evento" }}
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="annullamento.aperto = false">
          Lascia stare
        </button>
      </form>
    </section>
  </section>
</template>
