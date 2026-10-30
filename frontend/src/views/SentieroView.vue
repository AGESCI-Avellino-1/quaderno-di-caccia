<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import {
  api,
  percorsoNuovoImpegno,
  quandoParziale,
  testoDataParziale,
  type CataloghiPP,
  type DataParziale,
  type FaseProgressione,
  type TipoCompetenza,
  type SchedaProgressione,
  type TappaSentiero,
  type TipoConclusione,
} from '@/api/qdc'
import CompetenzaEG from '@/components/CompetenzaEG.vue'
import CopiaLocale from '@/components/CopiaLocale.vue'
import InputDataParziale from '@/components/InputDataParziale.vue'
import PercorsoEG from '@/components/PercorsoEG.vue'
import PuntiStrada from '@/components/PuntiStrada.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'
import { scrivi } from '@/offline/outbox'

// The sentiero of one E/G (DEC-56…DEC-74): tappe, Promessa, badges, mete and impegni.
// The strada of one R/S (DEC-67, DEC-179…DEC-181): passi opened by the Carta di clan and
// by the confronto on the Partenza, obiettivi and impegni, Punti della Strada, the
// conclusione. The staff of the unit registers and validates; the ragazzo proposes their
// own mete (obiettivi) and impegni and asks for verification; the CSQ asks too; parents
// and other capi read. A private meta is not shown to the CSQ (DEC-173). Cached for
// meetings without network; new impegni and their steps go through the offline queue
// (DEC-95).
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
// The most recent period: after a conclusione the page says how the way ended.
const ultimo = computed(() => passati.value.at(-1) ?? null)
const tappa = computed(() => periodo.value?.tappe.find((t) => t.in_corso) ?? null)
// The tools of each branch.
const eg = computed(() => periodo.value?.branca === 'EG')
const lc = computed(() => periodo.value?.branca === 'LC')
// L/C names (DEC-185): giungla in a branco, bosco in a cerchio, by the child in a mixed
// unit; generic when the sex is not known.
const giungla = computed(() => scheda.value?.ambiente === 'GIUNGLA')
const bosco = computed(() => scheda.value?.ambiente === 'BOSCO')
const nomePrede = computed(() => (giungla.value ? 'Prede' : bosco.value ? 'Voli' : 'Prede e voli'))
const nomePreda = computed(() => (giungla.value ? 'preda' : bosco.value ? 'volo' : 'preda o volo'))
// Momenti and recognitions (spec §4.1, appendix A1): the recognition name never shows as
// already conquered while the child walks towards it.
const MOMENTI: Record<string, [string, string, string, string]> = {
  SCOPERTA: [
    'In caccia con Baloo',
    'lupo della legge',
    'In volo nel prato',
    'coccinella del prato',
  ],
  COMPETENZA: [
    'In caccia con Bagheera',
    'lupo della rupe',
    'In volo nel bosco',
    'coccinella del bosco',
  ],
  RESPONSABILITA: [
    'In caccia con Akela',
    'lupo anziano',
    'In volo sulla montagna',
    'coccinella della montagna',
  ],
}
function momento(fase: string) {
  const [caccia, lupo, volo, coccinella] = MOMENTI[fase] ?? ['', '', '', '']
  if (giungla.value) return { cammino: caccia, traguardo: lupo }
  if (bosco.value) return { cammino: volo, traguardo: coccinella }
  return { cammino: '', traguardo: `${lupo} o ${coccinella}` }
}
// L/C: the badge follows the recognition (V05), so it belongs to the last recognised one.
const daConsegnare = computed(
  () =>
    [...(periodo.value?.tappe ?? [])].reverse().find((t) => t.completata && !t.distintivo) ?? null,
)
const storico = ref(false)
const rs = computed(() => periodo.value?.branca === 'RS')
const strumenti = computed(() => eg.value || rs.value || lc.value)
// Made in an earlier branch: in clan it is not asked again.
const promessaPrima = computed(
  () => [...passati.value].reverse().find((p) => p.promessa)?.promessa ?? null,
)
const obiettiviAperti = computed(() =>
  (scheda.value?.mete ?? [])
    .filter((m) => aperti(m.stato))
    .map((m) => ({ id: m.id, testo: m.testo })),
)
const nomiMete = computed(() =>
  Object.fromEntries((scheda.value?.mete ?? []).map((m) => [m.id, m.testo])),
)
const aperti = (stato: string) => !['CONCLUSO', 'INTERROTTO'].includes(stato)

async function online(azione: () => Promise<SchedaProgressione>, messaggio: string) {
  esito.value = ''
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
  | ''
  | 'sentiero'
  | 'promessa'
  | 'riconosci'
  | 'distintivo'
  | 'colloca'
  | 'rettifica'
  | 'carta'
  | 'rettifica-carta'
  | 'responsabilita'
  | 'conclusione'
>('')
const conclusione = reactive({ tipo: '' as TipoConclusione | '', nota: '' })
const quando = ref<DataParziale>(dataOggi())
const collocamento = reactive({ fase: 'COMPETENZA' as FaseProgressione, motivazione: '' })
const rettifica = reactive({ motivo: '' })

function apri(cosa: typeof apertura.value) {
  apertura.value = apertura.value === cosa ? '' : cosa
  quando.value = dataOggi()
}

const apriSentiero = () =>
  online(() => api.apriSentiero(props.id, quando.value), 'Percorso aperto: inizia la Scoperta.')
const promessa = () =>
  online(() => api.promessa(periodo.value!.id, quando.value), 'Promessa registrata.')
const correggiPromessa = () =>
  online(
    () => api.rettificaPromessa(periodo.value!.id, quando.value, rettifica.motivo),
    'Data della Promessa corretta.',
  )
const firmaCarta = () =>
  online(
    () => api.firmaCarta(periodo.value!.id, quando.value),
    'Carta di clan firmata: iniziano i passi di competenza.',
  )
const correggiCarta = () =>
  online(
    () => api.rettificaCarta(periodo.value!.id, quando.value, rettifica.motivo),
    'Data della firma corretta.',
  )
const avviaResponsabilita = (t: TappaSentiero) =>
  online(() => api.avviaResponsabilita(t.id, quando.value), 'Iniziano i passi di responsabilità.')
const concludi = () =>
  online(
    () =>
      api.concludi(periodo.value!.id, {
        ...quando.value,
        tipo: conclusione.tipo as TipoConclusione,
        nota: conclusione.nota,
      }),
    'Percorso concluso.',
  )
const riconosci = (t: TappaSentiero) =>
  online(
    () => api.riconosciTappa(t.id, quando.value, lc.value && storico.value),
    lc.value
      ? `Riconosciuto: ${momento(t.fase).traguardo}.`
      : t.fase === 'RESPONSABILITA'
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

// --- Specialità and brevetti (DEC-62, DEC-63) -------------------------------------------

const cataloghi = ref<CataloghiPP | null>(null)
const nuovaCompetenza = reactive({
  aperta: false,
  tipo: 'SPECIALITA' as TipoCompetenza,
  codice: '',
  carta: '',
  maestro: '',
  passata: false,
  quando: dataOggi(),
})
const vociCatalogo = computed(() =>
  nuovaCompetenza.tipo === 'BREVETTO'
    ? cataloghi.value?.brevetti
    : nuovaCompetenza.tipo === 'SPECIALITA_LC'
      ? cataloghi.value?.specialita_lc
      : cataloghi.value?.specialita,
)
const specialitaCollegabili = computed(() =>
  (scheda.value?.competenze ?? [])
    .filter((c) => c.tipo === 'SPECIALITA')
    .map((c) => ({ id: c.id, testo: `${c.nome} (${c.stato_nome.toLowerCase()})` })),
)

async function apriCompetenza() {
  nuovaCompetenza.aperta = true
  nuovaCompetenza.tipo = lc.value ? 'SPECIALITA_LC' : 'SPECIALITA'
  nuovaCompetenza.codice = ''
  if (!cataloghi.value) {
    cataloghi.value =
      (await esegui(async () => (await leggiConCache('cataloghi-pp', api.cataloghiPP)).dati)) ??
      null
  }
}

async function salvaCompetenza() {
  const fatto = await online(
    () =>
      api.nuovaCompetenza(props.id, {
        tipo: nuovaCompetenza.tipo,
        codice: nuovaCompetenza.codice,
        carta: nuovaCompetenza.carta,
        maestro: nuovaCompetenza.maestro,
        conquistata: nuovaCompetenza.passata ? nuovaCompetenza.quando : null,
      }),
    'Salvato.',
  )
  if (fatto)
    Object.assign(nuovaCompetenza, {
      aperta: false,
      codice: '',
      carta: '',
      maestro: '',
      passata: false,
    })
}

// --- Mete and impegni ----------------------------------------------------------------------

const nuova = reactive({
  tipo: '' as '' | 'mete' | 'impegni',
  testo: '',
  termine: '',
  criterio: '',
  riservata: false,
  mete: [] as number[],
  // L/C: the stagione of the preda or volo.
  stagione: null as number | null,
})

function apriNuovoImpegno() {
  nuova.tipo = 'impegni'
  // The open season first, if any.
  const aperta = scheda.value?.stagioni.find((st) => st.stato === 'APERTA')
  nuova.stagione = lc.value ? (aperta?.id ?? null) : null
}

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
        ...(lc.value && nuova.stagione ? { stagione_id: nuova.stagione } : {}),
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
      <h1 class="h4 mb-1">
        {{
          (periodo ?? ultimo)?.branca === 'RS'
            ? 'Strada'
            : (periodo ?? ultimo)?.branca === 'LC'
              ? giungla
                ? 'Pista'
                : bosco
                  ? 'Sentiero'
                  : 'Pista o sentiero'
              : 'Sentiero'
        }}
        di {{ scheda.persona }}
      </h1>
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
      <p v-if="ultimo?.conclusione" class="mb-0">
        Percorso concluso: {{ ultimo.conclusione.tipo_nome }}
        {{ quandoParziale(ultimo.conclusione.data) }}.
        <template v-if="ultimo.conclusione.nota">{{ ultimo.conclusione.nota }}.</template>
      </p>
      <p v-else class="mb-3">Il percorso non è ancora aperto.</p>
      <template
        v-if="
          scheda.puo_gestire && (!ultimo?.conclusione || ultimo.conclusione.tipo !== 'PARTENZA')
        "
      >
        <button
          v-if="apertura !== 'sentiero'"
          type="button"
          class="btn btn-sm btn-solid theme-primary align-self-start"
          @click="apri('sentiero')"
        >
          {{ ultimo?.conclusione ? 'Rientro: apri un nuovo percorso' : 'Apri il percorso' }}
        </button>
        <form v-else class="d-flex flex-wrap align-items-end gap-3" @submit.prevent="apriSentiero">
          <InputDataParziale
            id="ingresso"
            v-model="quando"
            etichetta="Ingresso in reparto, noviziato o clan (per chi c'era già, anche solo l'anno)"
          />
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Apri
          </button>
        </form>
      </template>
    </div>

    <!-- Tappe, Promessa, badges -->
    <section v-if="periodo" class="card card-body mb-5">
      <h2 class="h5">{{ rs ? 'Passi' : lc ? 'Momenti' : 'Tappe' }}</h2>
      <div v-if="periodo.passaggio" class="alert theme-info small">
        <div>
          Passaggio da {{ periodo.passaggio.da }} il
          {{ new Date(periodo.passaggio.data).toLocaleDateString('it-IT') }}.
          <template v-if="periodo.passaggio.sintesi">
            Sintesi per i nuovi capi:
            <span class="testo-a-capo">{{ periodo.passaggio.sintesi }}</span>
          </template>
        </div>
      </div>
      <p class="small mb-3">
        {{ rs ? 'Nella strada' : lc ? (giungla ? 'Nella pista' : 'Nel sentiero') : 'Nel sentiero' }}
        dal
        {{ testoDataParziale(periodo.inizio) }}.
        <template v-if="periodo.promessa"
          >Promessa: {{ testoDataParziale(periodo.promessa) }}.</template
        >
        <template v-else-if="promessaPrima"
          >Promessa: {{ testoDataParziale(promessaPrima) }}, in una branca precedente.</template
        >
        <template v-else>Promessa non ancora registrata.</template>
        <template v-if="periodo.branca === 'RS'">
          <template v-if="periodo.firma_carta">
            Carta di clan firmata {{ quandoParziale(periodo.firma_carta) }}.</template
          >
          <template v-else> Carta di clan non ancora firmata.</template>
        </template>
      </p>
      <ol class="mb-3">
        <li v-for="t in periodo.tappe" :key="t.id" class="mb-1">
          <strong>{{ t.fase_nome }}</strong>
          <span v-if="lc && !t.completata && momento(t.fase).cammino" class="small">
            · {{ momento(t.fase).cammino }} per diventare {{ momento(t.fase).traguardo }}
          </span>
          <span class="small">
            dal {{ testoDataParziale(t.inizio) }}
            <template v-if="t.collocamento"> (collocamento: {{ t.motivazione }})</template>
            <template v-if="t.distintivo">
              · distintivo consegnato {{ quandoParziale(t.distintivo) }}</template
            >
            <template v-else-if="t.in_corso && periodo.branca === 'EG'">
              · distintivo non ancora consegnato</template
            >
            <template v-if="t.completata && periodo.branca === 'RS'">
              · fino {{ quandoParziale(t.completata) }}</template
            >
            <template v-else-if="t.completata && lc">
              · riconosciuto: {{ momento(t.fase).traguardo }}
              {{ quandoParziale(t.completata) }}</template
            >
            <template v-else-if="t.completata">
              · riconosciuta nel Consiglio della Legge
              {{ quandoParziale(t.completata) }}</template
            >
            <template v-else-if="t.in_corso"> · in corso</template>
          </span>
        </li>
      </ol>
      <p v-if="tappa?.fase === 'RESPONSABILITA' && tappa.completata && eg" class="small fg-2">
        Il sentiero continua fino al passaggio in noviziato.
      </p>
      <p v-if="tappa?.fase === 'RESPONSABILITA' && tappa.completata && lc" class="small fg-2">
        La responsabilità continua con gli altri strumenti fino al passaggio in reparto.
      </p>

      <div v-if="scheda.puo_gestire && tappa && lc" class="d-flex flex-wrap gap-1">
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
          v-if="!tappa.completata"
          type="button"
          class="btn btn-sm btn-outline theme-success"
          @click="apri('riconosci')"
        >
          Riconosci: {{ momento(tappa.fase).traguardo }}
        </button>
        <button
          v-if="daConsegnare"
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          @click="apri('distintivo')"
        >
          Distintivo consegnato
        </button>
        <button
          v-if="tappa.fase === 'SCOPERTA' && periodo.promessa"
          type="button"
          class="btn btn-sm btn-link"
          @click="apri('colloca')"
        >
          Entrato più grande: colloca in un altro momento
        </button>
      </div>

      <div v-if="scheda.puo_gestire && tappa && rs" class="d-flex flex-wrap gap-1">
        <button
          v-if="!periodo.promessa && !promessaPrima"
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          @click="apri('promessa')"
        >
          Registra la Promessa
        </button>
        <button
          v-if="!periodo.firma_carta"
          type="button"
          class="btn btn-sm btn-outline theme-success"
          @click="apri('carta')"
        >
          Firma della Carta di clan
        </button>
        <button v-else type="button" class="btn btn-sm btn-link" @click="apri('rettifica-carta')">
          Correggi la data della firma
        </button>
        <button
          v-if="tappa.fase === 'COMPETENZA'"
          type="button"
          class="btn btn-sm btn-outline theme-success"
          @click="apri('responsabilita')"
        >
          Inizia il confronto sulla Partenza
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="apri('conclusione')">
          Concludi il percorso…
        </button>
      </div>
      <form
        v-if="apertura === 'carta'"
        class="d-flex flex-wrap align-items-end gap-3 mt-3"
        @submit.prevent="firmaCarta"
      >
        <InputDataParziale id="carta" v-model="quando" etichetta="Firma della Carta di clan" />
        <button type="submit" class="btn btn-sm btn-solid theme-success" :disabled="inCorso">
          Registra
        </button>
        <span class="small fg-2 w-100">Dallo stesso giorno iniziano i passi di competenza.</span>
      </form>
      <form
        v-if="apertura === 'rettifica-carta'"
        class="d-flex flex-wrap align-items-end gap-3 mt-3"
        @submit.prevent="correggiCarta"
      >
        <InputDataParziale id="carta-r" v-model="quando" etichetta="Data giusta della firma" />
        <div class="flex-grow-1">
          <label class="form-label small" for="motivo-carta">Perché la correggi</label>
          <input
            id="motivo-carta"
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
        v-if="apertura === 'responsabilita' && tappa"
        class="d-flex flex-wrap align-items-end gap-3 mt-3"
        @submit.prevent="avviaResponsabilita(tappa)"
      >
        <InputDataParziale
          id="responsabilita"
          v-model="quando"
          etichetta="Inizio del confronto con la comunità sulle scelte della Partenza"
        />
        <button type="submit" class="btn btn-sm btn-solid theme-success" :disabled="inCorso">
          Registra
        </button>
      </form>
      <form
        v-if="apertura === 'conclusione'"
        class="d-flex flex-wrap align-items-end gap-3 mt-3"
        @submit.prevent="concludi"
      >
        <div>
          <label class="form-label small" for="tipo-concl">Come si conclude</label>
          <select
            id="tipo-concl"
            v-model="conclusione.tipo"
            class="form-control form-control-sm"
            required
          >
            <option value="" disabled>—</option>
            <option v-for="t in scheda.tipi_conclusione" :key="t.valore" :value="t.valore">
              {{ t.etichetta }}
            </option>
          </select>
        </div>
        <InputDataParziale id="concl" v-model="quando" etichetta="Data" />
        <div class="flex-grow-1">
          <label class="form-label small" for="nota-concl">Nota (facoltativa)</label>
          <input id="nota-concl" v-model="conclusione.nota" class="form-control form-control-sm" />
        </div>
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Concludi
        </button>
        <span class="small fg-2 w-100">
          Chiude il percorso nella Progressione; l'uscita dal clan la registra BuonaStrada.
        </span>
      </form>

      <div v-if="scheda.puo_gestire && tappa && eg" class="d-flex flex-wrap gap-1">
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
        @submit.prevent="distintivo(lc && daConsegnare ? daConsegnare : tappa)"
      >
        <InputDataParziale
          id="distintivo"
          v-model="quando"
          :etichetta="
            lc && daConsegnare
              ? `Consegna del distintivo: ${momento(daConsegnare.fase).traguardo}`
              : `Consegna del distintivo della ${tappa.fase_nome}`
          "
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
          :etichetta="lc ? 'Data del riconoscimento' : 'Data del Consiglio della Legge'"
        />
        <div v-if="lc" class="form-field w-100">
          <input id="storico" v-model="storico" type="checkbox" class="check" />
          <label class="small" for="storico">
            Storia di chi c'era già: le prede e i voli di allora non sono registrati
          </label>
        </div>
        <button type="submit" class="btn btn-sm btn-solid theme-success" :disabled="inCorso">
          Riconosci
        </button>
        <span class="small fg-2 w-100">
          <template v-if="lc && tappa.fase !== 'RESPONSABILITA'"
            >Serve almeno una {{ nomePreda }} conquistata in questo momento; dallo stesso giorno
            inizia il successivo.</template
          >
          <template v-else-if="tappa.fase !== 'RESPONSABILITA'"
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

    <!-- Mete (obiettivi in R/S) and impegni -->
    <template v-if="periodo && strumenti">
      <div class="d-flex flex-wrap gap-3 mb-3">
        <template v-if="scheda.puo_proporre && !nuova.tipo">
          <button
            type="button"
            class="btn btn-sm btn-solid theme-primary"
            @click="apriNuovoImpegno"
          >
            {{ lc ? `Nuova ${nomePreda}` : 'Nuovo impegno' }}
          </button>
          <button
            v-if="!lc"
            type="button"
            class="btn btn-sm btn-outline theme-primary"
            @click="nuova.tipo = 'mete'"
          >
            {{ rs ? 'Nuovo obiettivo' : 'Nuova meta' }}
          </button>
        </template>
      </div>
      <form v-if="nuova.tipo" class="card card-body mb-5" @submit.prevent="salvaNuova">
        <h2 class="h6">
          {{
            nuova.tipo === 'impegni'
              ? lc
                ? `Nuova ${nomePreda}`
                : 'Nuovo impegno'
              : rs
                ? 'Nuovo obiettivo'
                : 'Nuova meta'
          }}
        </h2>
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
        <div v-if="lc && scheda.stagioni.length" class="mb-3">
          <label class="form-label small" for="nuova-stagione">Stagione</label>
          <select
            id="nuova-stagione"
            v-model="nuova.stagione"
            class="form-control form-control-sm w-auto"
          >
            <option :value="null">—</option>
            <option v-for="st in scheda.stagioni" :key="st.id" :value="st.id">
              {{ st.nome }}
            </option>
          </select>
        </div>
        <template v-if="nuova.tipo === 'impegni'">
          <label class="form-label small" for="nuovo-criterio">Come si verifica</label>
          <input
            id="nuovo-criterio"
            v-model="nuova.criterio"
            class="form-control form-control-sm mb-3"
          />
          <fieldset v-if="scheda.mete.some((m) => aperti(m.stato))" class="mb-3">
            <legend class="form-label small">
              Per quale {{ rs ? 'obiettivo' : 'meta' }} (facoltativo)
            </legend>
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
        <div v-if="nuova.tipo === 'mete' && eg" class="form-field mb-3">
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

      <section v-if="!lc" class="mb-5">
        <h2 class="h5">{{ rs ? 'Obiettivi' : 'Mete' }}</h2>
        <p v-if="!scheda.mete.length && rs" class="small fg-2">
          Nessun obiettivo: si fissano o si ricalibrano nel Punto della Strada.
        </p>
        <p v-else-if="!scheda.mete.length" class="small fg-2">
          Nessuna meta: si introducono quando il ragazzo sa formularle; prima bastano gli impegni.
        </p>
        <ul v-else class="list-group">
          <PercorsoEG
            v-for="m in scheda.mete"
            :key="m.id"
            tipo="mete"
            :voce="m"
            :rs="rs"
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
        <h2 class="h5">{{ lc ? nomePrede : 'Impegni' }}</h2>
        <p v-if="!scheda.impegni.length" class="small fg-2">Nessun impegno.</p>
        <ul v-else class="list-group">
          <PercorsoEG
            v-for="i in scheda.impegni"
            :key="i.id"
            tipo="impegni"
            :voce="i"
            :rs="rs"
            :lc="lc"
            :gestisce="scheda.puo_gestire"
            :propone="scheda.puo_proporre"
            :propone-verifica="scheda.puo_proporre_verifica"
            :sedi="scheda.sedi"
            :nomi-mete="nomiMete"
            @cambiata="dopoScrittura"
          />
        </ul>
      </section>
      <PuntiStrada
        v-if="rs"
        :periodo="periodo.id"
        :punti="scheda.punti_strada.filter((p) => p.periodo_id === periodo!.id)"
        :obiettivi="obiettiviAperti"
        :gestisce="scheda.puo_gestire"
        :scrive-voce="scheda.puo_scrivere_voce"
        @salvata="
          (dati) => {
            scheda = dati
            esito = 'Punto della Strada salvato.'
          }
        "
      />
    </template>

    <template v-if="periodo && (eg || lc)">
      <section class="mb-5">
        <div class="d-flex flex-wrap align-items-center gap-3 mb-3">
          <h2 class="h5 mb-0">{{ lc ? 'Specialità' : 'Specialità e brevetti' }}</h2>
          <button
            v-if="scheda.puo_gestire && !nuovaCompetenza.aperta"
            type="button"
            class="btn btn-sm btn-outline theme-primary"
            @click="apriCompetenza"
          >
            Aggiungi
          </button>
        </div>
        <form
          v-if="nuovaCompetenza.aperta"
          class="card card-body mb-3"
          @submit.prevent="salvaCompetenza"
        >
          <div class="d-flex flex-wrap gap-3 mb-3">
            <div v-if="!lc">
              <label class="form-label small" for="nc-tipo">Cosa</label>
              <select
                id="nc-tipo"
                v-model="nuovaCompetenza.tipo"
                class="form-control form-control-sm"
                @change="nuovaCompetenza.codice = ''"
              >
                <option value="SPECIALITA">Specialità</option>
                <option value="BREVETTO">Brevetto di competenza</option>
              </select>
            </div>
            <div class="flex-grow-1">
              <label class="form-label small" for="nc-voce">Quale</label>
              <select
                id="nc-voce"
                v-model="nuovaCompetenza.codice"
                class="form-control form-control-sm"
                required
              >
                <option value="" disabled>—</option>
                <option v-for="v in vociCatalogo ?? []" :key="v.codice" :value="v.codice">
                  {{ v.nome }}
                </option>
              </select>
            </div>
          </div>
          <div class="form-field mb-3">
            <input
              id="nc-passata"
              v-model="nuovaCompetenza.passata"
              type="checkbox"
              class="check"
            />
            <label class="small" for="nc-passata"
              >Già conquistata in passato (per ricostruire la storia)</label
            >
          </div>
          <InputDataParziale
            v-if="nuovaCompetenza.passata"
            id="nc-quando"
            v-model="nuovaCompetenza.quando"
            etichetta="Conquistata il"
            class="mb-3"
          />
          <template v-else>
            <label class="form-label small" for="nc-carta"
              >Carta (si può scrivere anche dopo)</label
            >
            <textarea
              id="nc-carta"
              v-model="nuovaCompetenza.carta"
              class="form-control form-control-sm mb-3"
              rows="2"
            />
            <label class="form-label small" for="nc-maestro"
              >Maestro o maestra (anche un adulto esterno)</label
            >
            <input
              id="nc-maestro"
              v-model="nuovaCompetenza.maestro"
              class="form-control form-control-sm mb-3"
              maxlength="120"
            />
          </template>
          <div class="d-flex gap-3">
            <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
              Salva
            </button>
            <button
              type="button"
              class="btn btn-sm btn-link"
              @click="nuovaCompetenza.aperta = false"
            >
              Annulla
            </button>
          </div>
        </form>
        <p v-if="!scheda.competenze.length" class="small fg-2">
          {{ lc ? 'Nessuna specialità.' : 'Nessuna specialità o brevetto.' }}
        </p>
        <ul v-else class="list-group">
          <CompetenzaEG
            v-for="c in scheda.competenze"
            :key="c.id"
            :voce="c"
            :gestisce="scheda.puo_gestire"
            :propone-verifica="scheda.puo_proporre_verifica"
            :collegabili="specialitaCollegabili"
            :allega="scheda.puo_proporre"
            @cambiata="dopoScrittura"
          />
        </ul>
      </section>
      <section v-if="lc && scheda.piccole_orme.length" class="mb-5">
        <h2 class="h5">Piccole Orme</h2>
        <ul class="small">
          <li v-for="(po, n) in scheda.piccole_orme" :key="n">
            {{ po.evento }}, dal {{ new Date(po.inizio).toLocaleDateString('it-IT') }} al
            {{ new Date(po.fine).toLocaleDateString('it-IT') }} ({{ po.stato.toLowerCase() }})
          </li>
        </ul>
      </section>
      <section v-if="scheda.posti_azione.length" class="mb-5">
        <h2 class="h5">Posti d'azione nelle imprese</h2>
        <ul class="list-group">
          <li v-for="p in scheda.posti_azione" :key="p.id" class="list-group-item small">
            <strong>{{ p.ruolo }}</strong> · {{ p.impresa }} ({{ p.impresa_livello.toLowerCase() }})
            <template v-if="p.verificato_il">
              · verificato il {{ new Date(p.verificato_il).toLocaleDateString('it-IT') }} ({{
                p.sede_nome
              }})
            </template>
          </li>
        </ul>
      </section>
    </template>

    <p v-if="periodo && !strumenti" class="small fg-2 mb-5">
      Gli strumenti della progressione di questa branca arriveranno nei prossimi aggiornamenti.
    </p>

    <section v-if="passati.length" class="mb-5">
      <h2 class="h5">Percorsi precedenti</h2>
      <ul class="small">
        <li v-for="p in passati" :key="p.id">
          {{ p.branca_nome }}: dal {{ testoDataParziale(p.inizio) }} al
          {{ p.fine ? new Date(p.fine).toLocaleDateString('it-IT') : '' }}
          <template v-if="p.motivo_fine"> ({{ p.motivo_fine }})</template>
          ·
          {{
            p.tappe
              .map((t) => t.fase_nome + (t.completata && p.branca !== 'RS' ? ' riconosciuta' : ''))
              .join(', ')
          }}
        </li>
      </ul>
    </section>
  </section>
  <div v-else-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
</template>
