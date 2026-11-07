<script setup lang="ts">
import { computed, reactive } from 'vue'

import { TIPI_CAMPO, type DettaglioBC, type EventoBCIn } from '@/api/qdc'

// An event on BuonaCaccia, new or to change (DEC-158, DEC-391): the day is required, the hour of
// start and end may come later. Who may save it is decided by the server.
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
  formazione_capi: e?.formazione_capi ?? false,
  piccole_orme: e?.piccole_orme ?? false,
  tipo_campo: (e?.tipo_campo || null) as EventoBCIn['tipo_campo'],
  specifica: e?.specifica ?? '',
})
const serveSpecifica = computed(
  () => modulo.tipo_campo === 'MODULO' || modulo.tipo_campo === 'ALTRO',
)

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
    formazione_capi: modulo.formazione_capi,
    piccole_orme: modulo.piccole_orme,
    tipo_campo: modulo.tipo_campo,
    specifica: modulo.specifica,
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
      <div class="col-12 form-field">
        <input id="bc-formazione" v-model="modulo.formazione_capi" type="checkbox" class="check" />
        <label class="small" for="bc-formazione">Campo di formazione capi</label>
      </div>
      <div v-if="!modulo.formazione_capi" class="col-12 form-field">
        <input id="bc-po" v-model="modulo.piccole_orme" type="checkbox" class="check" />
        <label class="small" for="bc-po">
          Piccole Orme (si vivono una volta sola: l'app avvisa se un bambino le ha già fatte)
        </label>
      </div>
      <template v-if="modulo.formazione_capi">
        <div class="col-12 md:col-6">
          <label class="form-label small" for="bc-tipo-campo">Tipo di campo</label>
          <select
            id="bc-tipo-campo"
            v-model="modulo.tipo_campo"
            class="form-control form-control-sm"
            required
          >
            <option v-for="[valore, nome] in TIPI_CAMPO" :key="valore" :value="valore">
              {{ nome }}
            </option>
          </select>
        </div>
        <div v-if="serveSpecifica" class="col-12 md:col-6">
          <label class="form-label small" for="bc-specifica">
            {{ modulo.tipo_campo === 'MODULO' ? 'Titolo del modulo' : 'Specifica' }}
          </label>
          <input
            id="bc-specifica"
            v-model="modulo.specifica"
            class="form-control form-control-sm"
            required
          />
        </div>
      </template>
    </div>
    <div class="d-flex gap-3 mt-3">
      <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
        {{ etichetta }}
      </button>
      <button type="button" class="btn btn-sm btn-link" @click="emit('annulla')">Annulla</button>
    </div>
  </form>
</template>
