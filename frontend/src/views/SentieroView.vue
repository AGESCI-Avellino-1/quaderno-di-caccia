<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import {
  api,
  percorsoNuovoImpegno,
  testoDataParziale,
  type DataParziale,
  type FaseProgressione,
  type SchedaProgressione,
  type TappaSentiero,
} from '@/api/qdc'
import CopiaLocale from '@/components/CopiaLocale.vue'
import InputDataParziale from '@/components/InputDataParziale.vue'
import PercorsoEG from '@/components/PercorsoEG.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'
import { scrivi } from '@/offline/outbox'

// The sentiero of one E/G (DEC-56…DEC-74): tappe, Promessa, badges, mete and impegni.
// The staff of the unit registers and validates; the ragazzo proposes their own mete and
// impegni and asks for verification; the CSQ asks too; parents and other capi read. A
// private meta is not shown to the CSQ (DEC-173). Cached for meetings without network;
// new impegni and their steps go through the offline queue (DEC-95).
const props = defineProps<{ id: number }>()
const { errore, inCorso, esegui } = useErrore()
const scheda = ref<SchedaProgressione | null>(null)
const copiaDel = ref<string | null>(null)
const esito = ref('')
const oggi = () => new Date().toLocaleDateString('sv')
const dataOggi = (): DataParziale => ({ data: oggi(), precisione: 'GIORNO' })

async function carica() {
  const letto = await esegui(() =>
    leggiConCache(`sentiero:${props.id}`, () => api.progressione(props.id)),
  )
  if (!letto) return
  scheda.value = letto.dati
  copiaDel.value = letto.copiaDel
}
watch(() => props.id, carica, { immediate: true })

const periodo = computed(() => scheda.value?.periodi.find((p) => p.attivo) ?? null)
const passati = computed(() => scheda.value?.periodi.filter((p) => !p.attivo) ?? [])
const tappa = computed(() => periodo.value?.tappe.find((t) => t.in_corso) ?? null)
const nomiMete = computed(() =>
  Object.fromEntries((scheda.value?.mete ?? []).map((m) => [m.id, m.testo])),
)
const aperti = (stato: string) => !['CONCLUSO', 'INTERROTTO'].includes(stato)

async function online(azione: () => Promise<SchedaProgressione>, messaggio: string) {
  const dati = await esegui(azione)
  if (!dati) return false
  scheda.value = dati
  esito.value = messaggio
  apertura.value = ''
  return true
}

async function dopoScrittura(inCoda: boolean) {
  esito.value = inCoda ? 'Salvato sul telefono: sarà inviato appena torna la rete.' : 'Salvato.'
  if (!inCoda) await carica()
}

// --- Staff: sentiero, Promessa, tappe -----------------------------------------------------

const apertura = ref<
  '' | 'sentiero' | 'promessa' | 'riconosci' | 'distintivo' | 'colloca' | 'rettifica'
>('')
const quando = ref<DataParziale>(dataOggi())
const collocamento = reactive({ fase: 'COMPETENZA' as FaseProgressione, motivazione: '' })
const rettifica = reactive({ motivo: '' })

function apri(cosa: typeof apertura.value) {
  apertura.value = apertura.value === cosa ? '' : cosa
  quando.value = dataOggi()
}

const apriSentiero = () =>
  online(() => api.apriSentiero(props.id, quando.value), 'Sentiero aperto: inizia la Scoperta.')
const promessa = () =>
  online(() => api.promessa(periodo.value!.id, quando.value), 'Promessa registrata.')
const correggiPromessa = () =>
  online(
    () => api.rettificaPromessa(periodo.value!.id, quando.value, rettifica.motivo),
    'Data della Promessa corretta.',
  )
const riconosci = (t: TappaSentiero) =>
  online(
    () => api.riconosciTappa(t.id, quando.value),
    t.fase === 'RESPONSABILITA'
      ? 'Responsabilità conclusa: il sentiero continua fino al passaggio.'
      : 'Tappa riconosciuta: inizia la successiva.',
  )
const distintivo = (t: TappaSentiero) =>
  online(() => api.distintivoTappa(t.id, quando.value), 'Consegna del distintivo registrata.')
const colloca = (t: TappaSentiero) =>
  online(
    () => api.collocaTappa(t.id, { ...quando.value, ...collocamento }),
    'Collocato nella tappa.',
  )

// --- Mete and impegni ----------------------------------------------------------------------

const nuova = reactive({
  tipo: '' as '' | 'mete' | 'impegni',
  testo: '',
  termine: '',
  criterio: '',
  riservata: false,
  mete: [] as number[],
})

async function salvaNuova() {
  if (nuova.tipo === 'mete') {
    const fatto = await online(
      () =>
        api.nuovaMeta(props.id, {
          testo: nuova.testo,
          termine: nuova.termine || null,
          riservata: nuova.riservata,
        }),
      'Meta salvata.',
    )
    if (fatto) Object.assign(nuova, { tipo: '', testo: '', termine: '', riservata: false })
    return
  }
  const risultato = await esegui(() =>
    scrivi({
      metodo: 'POST',
      percorso: percorsoNuovoImpegno(props.id),
      corpo: {
        testo: nuova.testo,
        termine: nuova.termine || null,
        criterio_verifica: nuova.criterio,
        mete: nuova.mete,
      },
      // Stored in clear in the queue: no names, no text.
      descrizione: `Nuovo impegno (scheda n. ${props.id})`,
    }),
  )
  if (!risultato) return
  Object.assign(nuova, { tipo: '', testo: '', termine: '', criterio: '', mete: [] })
  await dopoScrittura(risultato.inCoda)
}
</script>

<template>
  <section v-if="scheda">
    <div class="d-flex flex-wrap align-items-baseline gap-3">
      <h1 class="h4 mb-1">Sentiero di {{ scheda.persona }}</h1>
      <CopiaLocale :del="copiaDel" />
    </div>
    <p class="small mb-3">
      <RouterLink :to="`/persone/${scheda.persona_id}`">Scheda della persona</RouterLink>
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>

    <!-- No sentiero yet -->
    <div v-if="!periodo" class="card card-body mb-5">
      <p class="mb-3">Il sentiero non è ancora aperto.</p>
      <template v-if="scheda.puo_gestire">
        <button
          v-if="apertura !== 'sentiero'"
          type="button"
          class="btn btn-sm btn-solid theme-primary align-self-start"
          @click="apri('sentiero')"
        >
          Apri il sentiero
        </button>
        <form v-else class="d-flex flex-wrap align-items-end gap-3" @submit.prevent="apriSentiero">
          <InputDataParziale
            id="ingresso"
            v-model="quando"
            etichetta="Ingresso nel sentiero (per chi c'era già, anche solo l'anno)"
          />
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Apri
          </button>
        </form>
      </template>
    </div>

    <!-- Tappe, Promessa, badges -->
    <section v-if="periodo" class="card card-body mb-5">
      <h2 class="h5">Tappe</h2>
      <p class="small mb-3">
        Nel sentiero dal {{ testoDataParziale(periodo.inizio) }}.
        <template v-if="periodo.promessa"
          >Promessa: {{ testoDataParziale(periodo.promessa) }}.</template
        >
        <template v-else>Promessa non ancora registrata.</template>
      </p>
      <ol class="mb-3">
        <li v-for="t in periodo.tappe" :key="t.id" class="mb-1">
          <strong>{{ t.fase_nome }}</strong>
          <span class="small">
            dal {{ testoDataParziale(t.inizio) }}
            <template v-if="t.collocamento"> (collocamento: {{ t.motivazione }})</template>
            <template v-if="t.distintivo">
              · distintivo consegnato il {{ testoDataParziale(t.distintivo) }}</template
            >
            <template v-else-if="t.in_corso"> · distintivo non ancora consegnato</template>
            <template v-if="t.completata">
              · riconosciuta nel Consiglio della Legge il
              {{ testoDataParziale(t.completata) }}</template
            >
            <template v-else-if="t.in_corso"> · in corso</template>
          </span>
        </li>
      </ol>
      <p v-if="tappa?.fase === 'RESPONSABILITA' && tappa.completata" class="small fg-2">
        Il sentiero continua fino al passaggio in noviziato.
      </p>

      <div v-if="scheda.puo_gestire && tappa" class="d-flex flex-wrap gap-1">
        <button
          v-if="!periodo.promessa"
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          @click="apri('promessa')"
        >
          Registra la Promessa
        </button>
        <button v-else type="button" class="btn btn-sm btn-link" @click="apri('rettifica')">
          Correggi la data della Promessa
        </button>
        <button
          v-if="!tappa.distintivo"
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          @click="apri('distintivo')"
        >
          Distintivo consegnato
        </button>
        <button
          v-if="!tappa.completata"
          type="button"
          class="btn btn-sm btn-outline theme-success"
          @click="apri('riconosci')"
        >
          Riconosci la {{ tappa.fase_nome }} (Consiglio della Legge)
        </button>
        <button
          v-if="tappa.fase === 'SCOPERTA' && periodo.promessa"
          type="button"
          class="btn btn-sm btn-link"
          @click="apri('colloca')"
        >
          Entrato più grande: colloca in un'altra tappa
        </button>
      </div>

      <form
        v-if="apertura === 'promessa'"
        class="d-flex flex-wrap align-items-end gap-3 mt-3"
        @submit.prevent="promessa"
      >
        <InputDataParziale id="promessa" v-model="quando" etichetta="Data della Promessa" />
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Registra
        </button>
      </form>
      <form
        v-if="apertura === 'rettifica'"
        class="d-flex flex-wrap align-items-end gap-3 mt-3"
        @submit.prevent="correggiPromessa"
      >
        <InputDataParziale
          id="promessa-r"
          v-model="quando"
          etichetta="Data giusta della Promessa"
        />
        <div class="flex-grow-1">
          <label class="form-label small" for="motivo-r">Perché la correggi</label>
          <input
            id="motivo-r"
            v-model="rettifica.motivo"
            class="form-control form-control-sm"
            required
          />
        </div>
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Correggi
        </button>
      </form>
      <form
        v-if="apertura === 'distintivo' && tappa"
        class="d-flex flex-wrap align-items-end gap-3 mt-3"
        @submit.prevent="distintivo(tappa)"
      >
        <InputDataParziale
          id="distintivo"
          v-model="quando"
          :etichetta="`Consegna del distintivo della ${tappa.fase_nome}`"
        />
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Registra
        </button>
      </form>
      <form
        v-if="apertura === 'riconosci' && tappa"
        class="d-flex flex-wrap align-items-end gap-3 mt-3"
        @submit.prevent="riconosci(tappa)"
      >
        <InputDataParziale
          id="riconosci"
          v-model="quando"
          etichetta="Data del Consiglio della Legge"
        />
        <button type="submit" class="btn btn-sm btn-solid theme-success" :disabled="inCorso">
          Riconosci
        </button>
        <span class="small fg-2 w-100">
          <template v-if="tappa.fase !== 'RESPONSABILITA'"
            >Dallo stesso giorno inizia la tappa successiva.</template
          >
          <template v-else>Il sentiero resta aperto fino al passaggio.</template>
        </span>
      </form>
      <form
        v-if="apertura === 'colloca' && tappa"
        class="d-flex flex-wrap align-items-end gap-3 mt-3"
        @submit.prevent="colloca(tappa)"
      >
        <div>
          <label class="form-label small" for="fase-c">Tappa</label>
          <select id="fase-c" v-model="collocamento.fase" class="form-control form-control-sm">
            <option value="COMPETENZA">Competenza</option>
            <option value="RESPONSABILITA">Responsabilità</option>
          </select>
        </div>
        <InputDataParziale id="colloca" v-model="quando" etichetta="Dal" />
        <div class="flex-grow-1">
          <label class="form-label small" for="motivazione-c">Motivazione</label>
          <input
            id="motivazione-c"
            v-model="collocamento.motivazione"
            class="form-control form-control-sm"
            required
          />
        </div>
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Colloca
        </button>
      </form>
    </section>

    <!-- Mete and impegni -->
    <template v-if="periodo">
      <div class="d-flex flex-wrap gap-3 mb-3">
        <template v-if="scheda.puo_proporre && !nuova.tipo">
          <button
            type="button"
            class="btn btn-sm btn-solid theme-primary"
            @click="nuova.tipo = 'impegni'"
          >
            Nuovo impegno
          </button>
          <button
            type="button"
            class="btn btn-sm btn-outline theme-primary"
            @click="nuova.tipo = 'mete'"
          >
            Nuova meta
          </button>
        </template>
      </div>
      <form v-if="nuova.tipo" class="card card-body mb-5" @submit.prevent="salvaNuova">
        <h2 class="h6">{{ nuova.tipo === 'mete' ? 'Nuova meta' : 'Nuovo impegno' }}</h2>
        <p v-if="!scheda.puo_gestire" class="small fg-2">
          Resta una bozza finché non la concordi con lo staff.
        </p>
        <label class="form-label small" for="nuovo-testo">
          {{
            nuova.tipo === 'mete'
              ? 'Il cambiamento che vuoi raggiungere'
              : 'Cosa farai, in concreto'
          }}
        </label>
        <textarea
          id="nuovo-testo"
          v-model="nuova.testo"
          class="form-control form-control-sm mb-3"
          rows="2"
          required
        />
        <template v-if="nuova.tipo === 'impegni'">
          <label class="form-label small" for="nuovo-criterio">Come si verifica</label>
          <input
            id="nuovo-criterio"
            v-model="nuova.criterio"
            class="form-control form-control-sm mb-3"
          />
          <fieldset v-if="scheda.mete.some((m) => aperti(m.stato))" class="mb-3">
            <legend class="form-label small">Per quale meta (facoltativo)</legend>
            <div
              v-for="m in scheda.mete.filter((m) => aperti(m.stato))"
              :key="m.id"
              class="form-field"
            >
              <input
                :id="`nm-${m.id}`"
                v-model="nuova.mete"
                type="checkbox"
                class="check"
                :value="m.id"
              />
              <label class="small" :for="`nm-${m.id}`">{{ m.testo }}</label>
            </div>
          </fieldset>
        </template>
        <label class="form-label small" for="nuovo-termine">Entro il</label>
        <input
          id="nuovo-termine"
          v-model="nuova.termine"
          type="date"
          :min="oggi()"
          class="form-control form-control-sm w-auto mb-3"
        />
        <div v-if="nuova.tipo === 'mete'" class="form-field mb-3">
          <input id="nuova-riservata" v-model="nuova.riservata" type="checkbox" class="check" />
          <label class="small" for="nuova-riservata"
            >Riservata: non la vede il capo squadriglia</label
          >
        </div>
        <div class="d-flex gap-3">
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Salva
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="nuova.tipo = ''">
            Annulla
          </button>
        </div>
      </form>

      <section class="mb-5">
        <h2 class="h5">Mete</h2>
        <p v-if="!scheda.mete.length" class="small fg-2">
          Nessuna meta: si introducono quando il ragazzo sa formularle; prima bastano gli impegni.
        </p>
        <ul v-else class="list-group">
          <PercorsoEG
            v-for="m in scheda.mete"
            :key="m.id"
            tipo="mete"
            :voce="m"
            :gestisce="scheda.puo_gestire"
            :propone="scheda.puo_proporre"
            :propone-verifica="scheda.puo_proporre_verifica"
            :sedi="scheda.sedi"
            :nomi-mete="nomiMete"
            @cambiata="dopoScrittura"
          />
        </ul>
      </section>
      <section class="mb-5">
        <h2 class="h5">Impegni</h2>
        <p v-if="!scheda.impegni.length" class="small fg-2">Nessun impegno.</p>
        <ul v-else class="list-group">
          <PercorsoEG
            v-for="i in scheda.impegni"
            :key="i.id"
            tipo="impegni"
            :voce="i"
            :gestisce="scheda.puo_gestire"
            :propone="scheda.puo_proporre"
            :propone-verifica="scheda.puo_proporre_verifica"
            :sedi="scheda.sedi"
            :nomi-mete="nomiMete"
            @cambiata="dopoScrittura"
          />
        </ul>
      </section>
    </template>

    <section v-if="passati.length" class="mb-5">
      <h2 class="h5">Percorsi precedenti</h2>
      <ul class="small">
        <li v-for="p in passati" :key="p.id">
          {{ p.branca_nome }}: dal {{ testoDataParziale(p.inizio) }} al
          {{ p.fine ? new Date(p.fine).toLocaleDateString('it-IT') : '' }}
        </li>
      </ul>
    </section>
  </section>
  <div v-else-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
</template>
