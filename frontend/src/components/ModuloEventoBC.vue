<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { api, type DettaglioBC, type EventoBCIn, type TipologiaBC, type VincoliBC } from '@/api/qdc'
import CampiVincoliBC from '@/components/CampiVincoliBC.vue'
import SceltaDaElenco from '@/components/SceltaDaElenco.vue'

// An event on BuonaCaccia, new or to change (DEC-158, DEC-391): the day is required, the hour of
// start and end may come later. Its type is required and brings its default constraints, which
// may be changed for this event (DEC-398). Who may save it is decided by the server.
const props = defineProps<{
  evento?: DettaglioBC
  titoloIniziale?: string
  etichetta: string
  inCorso?: boolean
}>()
const emit = defineEmits<{ salva: [dati: EventoBCIn]; annulla: [] }>()

const giorno = (iso: string) => new Date(iso).toLocaleDateString('sv')
const ora = (iso: string) =>
  new Date(iso).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })

const e = props.evento
const modulo = reactive({
  titolo: e?.titolo ?? props.titoloIniziale ?? '',
  giornoInizio: e ? giorno(e.inizio) : '',
  oraInizio: e && !e.senza_ora_inizio ? ora(e.inizio) : '',
  giornoFine: e ? giorno(e.fine) : '',
  oraFine: e && !e.senza_ora_fine ? ora(e.fine) : '',
  luogo: e?.luogo ?? '',
  descrizione: e?.descrizione ?? '',
  link: e?.link ?? '',
})

const vincoliDi = (v: VincoliBC): VincoliBC => ({
  branche: [...v.branche],
  eta_minima: v.eta_minima,
  eta_massima: v.eta_massima,
  livello_minimo: v.livello_minimo,
  massimo_per_unita: v.massimo_per_unita,
  massimo_per_gruppo: v.massimo_per_gruppo,
})
const vincoli = ref<VincoliBC>(
  e
    ? vincoliDi(e)
    : {
        branche: [],
        eta_minima: null,
        eta_massima: null,
        livello_minimo: null,
        massimo_per_unita: null,
        massimo_per_gruppo: null,
      },
)
const tipologie = ref<TipologiaBC[]>([])
onMounted(async () => {
  tipologie.value = await api.tipologieBC()
})
// An event keeps its type even when no longer offered (deactivated, or a branch gone).
const opzioni = computed(() => {
  const elenco = tipologie.value.map((t) => ({
    id: t.id,
    nome: t.nome,
    dettaglio: t.categoria_nome,
  }))
  if (e && !elenco.some((o) => o.id === e.tipologia_id))
    elenco.push({ id: e.tipologia_id, nome: e.tipologia, dettaglio: '' })
  return elenco
})
const tipologiaId = ref<number | null>(e?.tipologia_id ?? null)
const tipologia = computed({
  get: () => tipologiaId.value,
  // A type chosen brings its default constraints (DEC-398).
  set: (id: number | null) => {
    tipologiaId.value = id
    const scelta = tipologie.value.find((t) => t.id === id)
    if (scelta) vincoli.value = vincoliDi(scelta)
  },
})

function invia() {
  const fine = modulo.giornoFine || modulo.giornoInizio
  emit('salva', {
    titolo: modulo.titolo,
    tipo: e?.tipo ?? 'CAMPO',
    inizio: new Date(`${modulo.giornoInizio}T${modulo.oraInizio || '00:00'}`).toISOString(),
    fine: new Date(`${fine}T${modulo.oraFine || '23:59'}`).toISOString(),
    senza_ora_inizio: !modulo.oraInizio,
    senza_ora_fine: !modulo.oraFine,
    luogo: modulo.luogo,
    descrizione: modulo.descrizione,
    link: modulo.link,
    tipologia_id: tipologiaId.value!,
    ...vincoli.value,
  })
}
</script>

<template>
  <form class="card card-body mt-3" @submit.prevent="invia">
    <div class="row g-3">
      <div class="col-12">
        <label class="form-label small" for="bc-titolo">Nome (come su BuonaCaccia)</label>
        <input
          id="bc-titolo"
          v-model="modulo.titolo"
          class="form-control form-control-sm"
          required
        />
      </div>
      <div class="col-7 md:col-3">
        <label class="form-label small" for="bc-inizio">Giorno di inizio</label>
        <input
          id="bc-inizio"
          v-model="modulo.giornoInizio"
          type="date"
          class="form-control form-control-sm"
          required
        />
      </div>
      <div class="col-5 md:col-3">
        <label class="form-label small" for="bc-ora-inizio">Ora (se la sai)</label>
        <input
          id="bc-ora-inizio"
          v-model="modulo.oraInizio"
          type="time"
          class="form-control form-control-sm"
        />
      </div>
      <div class="col-7 md:col-3">
        <label class="form-label small" for="bc-fine">Giorno di fine</label>
        <input
          id="bc-fine"
          v-model="modulo.giornoFine"
          type="date"
          :min="modulo.giornoInizio"
          class="form-control form-control-sm"
        />
      </div>
      <div class="col-5 md:col-3">
        <label class="form-label small" for="bc-ora-fine">Ora (se la sai)</label>
        <input
          id="bc-ora-fine"
          v-model="modulo.oraFine"
          type="time"
          class="form-control form-control-sm"
        />
      </div>
      <div class="col-12">
        <label class="form-label small" for="bc-luogo">Località</label>
        <input id="bc-luogo" v-model="modulo.luogo" class="form-control form-control-sm" />
      </div>
      <div class="col-12">
        <label class="form-label small" for="bc-link"
          >Link alla pagina su BuonaCaccia (facoltativo)</label
        >
        <input
          id="bc-link"
          v-model="modulo.link"
          type="url"
          placeholder="https://…"
          class="form-control form-control-sm"
        />
        <div class="form-text">Lo vedono anche gli iscritti e le loro famiglie.</div>
      </div>
      <div class="col-12">
        <label class="form-label small" for="bc-descrizione">Note</label>
        <textarea
          id="bc-descrizione"
          v-model="modulo.descrizione"
          class="form-control form-control-sm"
          rows="2"
        />
      </div>
      <div class="col-12">
        <label class="form-label small" for="bc-tipologia">Tipo di evento</label>
        <SceltaDaElenco
          id="bc-tipologia"
          v-model="tipologia"
          :opzioni="opzioni"
          richiesto
          segnaposto="Scrivi il tipo, come su BuonaCaccia…"
          avviso="Scegli il tipo dall'elenco."
          nessuno="Nessun tipo con questo nome."
        />
        <div class="form-text">
          I vincoli qui sotto vengono dal tipo: cambiali se per questo evento sono diversi.
        </div>
      </div>
      <div class="col-12">
        <CampiVincoliBC v-model="vincoli" />
      </div>
    </div>
    <div class="d-flex gap-3 mt-3">
      <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
        {{ etichetta }}
      </button>
      <button type="button" class="btn btn-sm btn-link" @click="emit('annulla')">Annulla</button>
    </div>
  </form>
</template>
