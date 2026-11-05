<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import {
  api,
  nomeUnita,
  type Cerchia,
  type Evento,
  type Localita,
  type NuovaLocalita,
  type SerieRiunioni,
  type Unita,
} from '@/api/qdc'
import ImmagineAnimale from '@/components/ImmagineAnimale.vue'
import CopiaLocale from '@/components/CopiaLocale.vue'
import SceltaLocalita from '@/components/SceltaLocalita.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'
import { useSessioneStore } from '@/stores/sessione'

// Meetings, apart from the events (DEC-310): of the unit (the Co.Ca. too), of a patrol
// (the CSQ), the councils of a unit and of the unit linked to it. Weekly series or a
// single meeting, with the place and whether the uniform is worn; never a fee. The list
// is cached for offline use; creating needs the network. The API decides who may.
const sessione = useSessioneStore()
const { errore, inCorso, esegui } = useErrore()
const riunioni = ref<Evento[]>([])
const copiaDel = ref<string | null>(null)
const passate = ref(false)
const serie = ref<SerieRiunioni[]>([])
const unita = ref<Unita[]>([])
const squadriglie = ref<{ id: number; nome: string; reparto: string }[]>([])
const localita = ref<Localita[]>([])
const esito = ref('')
const oggi = () => new Date().toLocaleDateString('sv')

const csq = computed(() => (sessione.profilo?.squadriglie_guidate.length ?? 0) > 0)
const delegato = computed(() => (sessione.profilo?.squadriglie_delegate.length ?? 0) > 0)
const creaRiunioni = computed(() => sessione.capo || csq.value || delegato.value)

async function carica() {
  const filtri = passate.value ? { al: oggi() } : { dal: oggi() }
  const letto = await esegui(() =>
    leggiConCache(`riunioni:${passate.value ? 'passate' : 'prossime'}`, () => api.riunioni(filtri)),
  )
  if (!letto) return
  riunioni.value = passate.value ? [...letto.dati].reverse() : letto.dati
  copiaDel.value = letto.copiaDel
}
watch(passate, carica, { immediate: true })

async function caricaSerie() {
  try {
    serie.value = await api.serieRiunioni()
  } catch {
    serie.value = []
  }
}

onMounted(async () => {
  if (sessione.capogruppo) {
    try {
      mancanti.value = await api.verbaliMancanti()
    } catch {
      mancanti.value = []
    }
  }
  if (!creaRiunioni.value) return
  await caricaSerie()
  try {
    localita.value = await api.localita()
  } catch {
    localita.value = []
  }
  if (sessione.capo) {
    try {
      unita.value = (await leggiConCache('unita', () => api.unita())).dati
    } catch {
      unita.value = []
    }
    for (const reparto of unita.value.filter((u) => u.tipo === 'REPARTO')) {
      try {
        const dettaglio = await api.dettaglioUnita(reparto.id)
        squadriglie.value.push(
          ...dettaglio.squadriglie
            .filter((s) => s.attiva)
            .map((s) => ({ id: s.id, nome: s.nome, reparto: nomeUnita(reparto) })),
        )
      } catch {
        /* offline: patrol meetings wait for the network */
      }
    }
  } else {
    const delegate = sessione.profilo?.squadriglie_delegate ?? []
    try {
      squadriglie.value = (await api.miaSquadriglia())
        .filter((s) => s.sono_capo || delegate.includes(s.id))
        .map((s) => ({ id: s.id, nome: s.nome, reparto: s.reparto }))
    } catch {
      squadriglie.value = []
    }
  }
})

// --- New meetings ------------------------------------------------------------------------

const GIORNI = ['lunedì', 'martedì', 'mercoledì', 'giovedì', 'venerdì', 'sabato', 'domenica']
const LC = ['BRANCO', 'CERCHIO', 'BRANCO_CERCHIO']

// An assembly held whose minutes are not definitive: they must exist (DEC-331).
const mancanti = ref<{ id: number; titolo: string; inizio: string }[]>([])
const vuoto = () => ({
  perChi: (sessione.capo ? 'unita' : 'squadriglia') as
    'unita' | 'squadriglia' | 'genitori' | 'assemblea',
  // A meeting of the parents (DEC-325): of the whole group, or of one or more units.
  diGruppo: false,
  unitaGenitori: [] as number[],
  unita: null as number | null,
  insieme: false,
  squadriglia: null as number | null,
  cerchia: 'TUTTI' as Cerchia,
  titolo: '',
  ripeti: true,
  giorno_settimana: 5,
  giorno: oggi(),
  dal: oggi(),
  al: '',
  ora_inizio: '16:30',
  ora_fine: '18:30',
  localita: {
    id: null as number | null,
    nuova: null as NuovaLocalita | null,
  },
  uniforme: true,
  ordine_del_giorno: '',
})
const modulo = ref<ReturnType<typeof vuoto> | null>(null)
const EditorTesto = defineAsyncComponent(() => import('@/components/EditorTesto.vue'))

// The Co.Ca. has no parents to convene.
const unitaConGenitori = computed(() => unita.value.filter((u) => u.tipo !== 'COMUNITA_CAPI'))
// The parents' meetings and the assembly: one at a time, no uniform.
const unaAllaVolta = computed(() => ['genitori', 'assemblea'].includes(modulo.value?.perChi ?? ''))
const unitaScelta = computed(() => unita.value.find((u) => u.id === modulo.value?.unita))
// Co.Ca. and parents have an agenda (DEC-362): in a series, written on each meeting.
const diCoca = computed(
  () => modulo.value?.perChi === 'unita' && unitaScelta.value?.tipo === 'COMUNITA_CAPI',
)
const conOrdineDelGiorno = computed(
  () => modulo.value?.perChi === 'genitori' || (diCoca.value && !modulo.value?.ripeti),
)
const collegata = computed(() => unita.value.find((u) => u.id === unitaScelta.value?.collegata_a))
// Who of the unit is invited: a reparto has its councils, a branco or cerchio its
// Consiglio degli Anziani.
const cerchie = computed(() => {
  const tipo = unitaScelta.value?.tipo ?? ''
  const scelte: { valore: Cerchia; nome: string }[] = [{ valore: 'TUTTI', nome: 'Tutta l’unità' }]
  if (tipo === 'REPARTO')
    scelte.push(
      { valore: 'ALTA_SQ', nome: 'Alta Squadriglia' },
      { valore: 'CONCA', nome: 'Consiglio Capi' },
      { valore: 'CONCAVI', nome: 'Con.Ca.Vi., capi e vice' },
    )
  if (LC.includes(tipo)) scelte.push({ valore: 'CDA', nome: 'Consiglio degli Anziani' })
  return scelte
})
watch(
  () => modulo.value?.unita,
  () => {
    if (modulo.value) {
      modulo.value.cerchia = 'TUTTI'
      modulo.value.insieme = false
    }
  },
)

async function salva() {
  const m = modulo.value
  if (!m) return
  const perSquadriglia = m.perChi === 'squadriglia'
  const assemblea = m.perChi === 'assemblea'
  const genitori = m.perChi === 'genitori' || assemblea
  const fatte = await esegui(() =>
    api.creaRiunioni({
      titolo: m.titolo,
      cerchia: assemblea ? 'SOCI' : genitori ? 'GENITORI' : perSquadriglia ? 'TUTTI' : m.cerchia,
      di_gruppo: assemblea || (genitori && m.diGruppo),
      unita: genitori
        ? m.diGruppo || assemblea
          ? []
          : m.unitaGenitori
        : perSquadriglia
          ? []
          : [m.unita!, ...(m.insieme && collegata.value ? [collegata.value.id] : [])],
      squadriglia_id: perSquadriglia ? m.squadriglia : null,
      ora_inizio: m.ora_inizio,
      ora_fine: m.ora_fine,
      ...(m.ripeti && !genitori
        ? { giorno_settimana: m.giorno_settimana, dal: m.dal, al: m.al }
        : { giorno: m.giorno }),
      localita_id: m.localita.nuova ? null : m.localita.id,
      nuova_localita: m.localita.nuova,
      uniforme: !genitori && m.uniforme,
      ordine_del_giorno: conOrdineDelGiorno.value ? m.ordine_del_giorno : '',
    }),
  )
  if (!fatte) return
  esito.value = fatte.length === 1 ? 'Riunione creata.' : `Create ${fatte.length} riunioni.`
  modulo.value = null
  passate.value = false
  await Promise.all([carica(), caricaSerie()])
  try {
    localita.value = await api.localita()
  } catch {
    /* the list stays as it was */
  }
}

// --- Series --------------------------------------------------------------------------------

async function cambiaUniforme(s: SerieRiunioni, uniforme: boolean) {
  const fatta = await esegui(() =>
    api.modificaSerie(s.id, {
      uniforme,
      localita_id: s.localita?.id ?? null,
      nuova_localita: null,
    }),
  )
  if (!fatta) return
  await Promise.all([carica(), caricaSerie()])
}

const daTogliere = ref<number | null>(null)
async function togli(s: SerieRiunioni) {
  if (!(await esegui(() => api.togliSerie(s.id)))) return
  daTogliere.value = null
  await Promise.all([carica(), caricaSerie()])
}

const quando = (e: Evento) => {
  const inizio = new Date(e.inizio)
  const fine = new Date(e.fine)
  const ora = (d: Date) => d.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
  const giorno = inizio.toLocaleDateString('it-IT', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  })
  return `${giorno}, ${ora(inizio)}–${ora(fine)}`
}
const perChi = (e: Evento) =>
  [
    e.squadriglia ? `Sq. ${e.squadriglia}` : e.unita_nomi.join(' e '),
    e.cerchia !== 'TUTTI' && e.cerchia_nome,
  ]
    .filter(Boolean)
    .join(' · ')
const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
</script>

<template>
  <section>
    <div class="d-flex flex-wrap align-items-center gap-3 mb-3">
      <h1 class="h4 mb-0">Riunioni</h1>
      <CopiaLocale :del="copiaDel" />
    </div>
    <div class="d-flex flex-wrap gap-3 mb-5">
      <div class="form-field mb-0">
        <div class="switch">
          <input id="riunioni-passate" v-model="passate" type="checkbox" role="switch" />
        </div>
        <label for="riunioni-passate">Riunioni passate</label>
      </div>
      <button
        v-if="creaRiunioni && !modulo"
        type="button"
        class="btn btn-sm btn-solid theme-primary"
        @click="modulo = vuoto()"
      >
        Nuove riunioni
      </button>
    </div>
    <div v-for="m in mancanti" :key="m.id" class="alert theme-warning small" role="status">
      <div>
        Verbale mancante:
        <RouterLink :to="{ name: 'riunione', params: { id: m.id } }">
          {{ m.titolo }} del {{ new Date(m.inizio).toLocaleDateString('it-IT') }}
        </RouterLink>
      </div>
    </div>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>

    <form v-if="modulo" class="border rounded p-5 mb-5" @submit.prevent="salva">
      <div class="row g-3">
        <div class="md:col-4">
          <label class="form-label small" for="riu-per">Di chi</label>
          <select id="riu-per" v-model="modulo.perChi" class="form-control form-control-sm">
            <option v-if="sessione.capo" value="unita">Di un'unità</option>
            <option v-if="squadriglie.length" value="squadriglia">Di una squadriglia</option>
            <option v-if="sessione.capo" value="genitori">Dei genitori</option>
            <option v-if="sessione.capogruppo" value="assemblea">Assemblea dei soci</option>
          </select>
        </div>
        <template v-if="modulo.perChi === 'unita'">
          <div class="md:col-4">
            <label class="form-label small" for="riu-unita">Unità</label>
            <select
              id="riu-unita"
              v-model="modulo.unita"
              class="form-control form-control-sm"
              required
            >
              <option :value="null" disabled>Scegli…</option>
              <option v-for="u in unita" :key="u.id" :value="u.id">{{ nomeUnita(u) }}</option>
            </select>
          </div>
          <div class="md:col-4">
            <label class="form-label small" for="riu-cerchia">Chi è invitato</label>
            <select id="riu-cerchia" v-model="modulo.cerchia" class="form-control form-control-sm">
              <option v-for="c in cerchie" :key="c.valore" :value="c.valore">{{ c.nome }}</option>
            </select>
          </div>
          <div v-if="collegata" class="col-12 form-field mb-0">
            <input id="riu-insieme" v-model="modulo.insieme" type="checkbox" class="check" />
            <label for="riu-insieme">Insieme a {{ nomeUnita(collegata) }}</label>
          </div>
        </template>
        <fieldset v-else-if="modulo.perChi === 'genitori'" class="md:col-8">
          <legend class="form-label small">Genitori di</legend>
          <div v-if="sessione.capogruppo" class="form-field mb-1">
            <input id="riu-gruppo" v-model="modulo.diGruppo" type="checkbox" class="check" />
            <label for="riu-gruppo">Tutto il gruppo</label>
          </div>
          <template v-if="!modulo.diGruppo">
            <div v-for="u in unitaConGenitori" :key="u.id" class="form-field mb-1">
              <input
                :id="`riu-gen-${u.id}`"
                v-model="modulo.unitaGenitori"
                type="checkbox"
                class="check"
                :value="u.id"
              />
              <label :for="`riu-gen-${u.id}`">{{ nomeUnita(u) }}</label>
            </div>
          </template>
          <p class="form-text mb-0">
            Sono invitati i genitori e lo staff. Gli invitati ricevono l'email quando invii la
            convocazione dalla pagina della riunione, dopo aver aggiunto i documenti.
          </p>
        </fieldset>
        <p v-else-if="modulo.perChi === 'assemblea'" class="form-text md:col-8 mb-0">
          Sono invitati i capi, i rover e le scolte maggiorenni e i genitori. Gli invitati ricevono
          l'email quando invii la convocazione dalla pagina dell'assemblea.
        </p>
        <div v-else class="md:col-8">
          <label class="form-label small" for="riu-squadriglia">Squadriglia</label>
          <select
            id="riu-squadriglia"
            v-model="modulo.squadriglia"
            class="form-control form-control-sm"
            required
          >
            <option :value="null" disabled>Scegli…</option>
            <option v-for="s in squadriglie" :key="s.id" :value="s.id">
              {{ s.nome }} · {{ s.reparto }}
            </option>
          </select>
        </div>
        <fieldset v-if="!unaAllaVolta" class="col-12">
          <legend class="form-label small">Quando</legend>
          <div class="d-flex flex-wrap gap-5">
            <div class="form-field mb-0">
              <input
                id="riu-ripeti"
                v-model="modulo.ripeti"
                type="radio"
                class="radio"
                :value="true"
              />
              <label for="riu-ripeti">Ogni settimana</label>
            </div>
            <div class="form-field mb-0">
              <input
                id="riu-una"
                v-model="modulo.ripeti"
                type="radio"
                class="radio"
                :value="false"
              />
              <label for="riu-una">Una volta</label>
            </div>
          </div>
        </fieldset>
        <template v-if="modulo.ripeti && !unaAllaVolta">
          <div class="md:col-4">
            <label class="form-label small" for="riu-giorno">Ogni</label>
            <select
              id="riu-giorno"
              v-model.number="modulo.giorno_settimana"
              class="form-control form-control-sm"
            >
              <option v-for="(g, i) in GIORNI" :key="g" :value="i">{{ g }}</option>
            </select>
          </div>
          <div class="md:col-4">
            <label class="form-label small" for="riu-dal">Dal</label>
            <input
              id="riu-dal"
              v-model="modulo.dal"
              type="date"
              class="form-control form-control-sm"
              required
            />
          </div>
          <div class="md:col-4">
            <label class="form-label small" for="riu-al">Al</label>
            <input
              id="riu-al"
              v-model="modulo.al"
              type="date"
              :min="modulo.dal"
              class="form-control form-control-sm"
              required
            />
          </div>
        </template>
        <div v-else class="md:col-4">
          <label class="form-label small" for="riu-data">Giorno</label>
          <input
            id="riu-data"
            v-model="modulo.giorno"
            type="date"
            class="form-control form-control-sm"
            required
          />
        </div>
        <div class="md:col-4">
          <label class="form-label small" for="riu-inizio">Dalle</label>
          <input
            id="riu-inizio"
            v-model="modulo.ora_inizio"
            type="time"
            class="form-control form-control-sm"
            required
          />
        </div>
        <div class="md:col-4">
          <label class="form-label small" for="riu-fine">Alle</label>
          <input
            id="riu-fine"
            v-model="modulo.ora_fine"
            type="time"
            class="form-control form-control-sm"
            required
          />
        </div>
        <div class="col-12">
          <SceltaLocalita v-model="modulo.localita" id-campo="riu-localita" :localita="localita" />
        </div>
        <fieldset v-if="!unaAllaVolta" class="col-12">
          <legend class="form-label small">Uniforme</legend>
          <div class="d-flex flex-wrap gap-5">
            <div class="form-field mb-0">
              <input
                id="riu-uniforme-si"
                v-model="modulo.uniforme"
                type="radio"
                class="radio"
                :value="true"
              />
              <label for="riu-uniforme-si">Con l'uniforme</label>
            </div>
            <div class="form-field mb-0">
              <input
                id="riu-uniforme-no"
                v-model="modulo.uniforme"
                type="radio"
                class="radio"
                :value="false"
              />
              <label for="riu-uniforme-no">Senza uniforme</label>
            </div>
          </div>
        </fieldset>
        <div v-if="conOrdineDelGiorno" class="col-12">
          <EditorTesto
            v-model="modulo.ordine_del_giorno"
            etichetta="Ordine del giorno (facoltativo)"
          />
        </div>
        <p v-else-if="diCoca" class="form-text col-12 mb-0">
          L'ordine del giorno lo scrivi poi sulla singola riunione.
        </p>
        <div class="col-12">
          <label class="form-label small" for="riu-titolo">Titolo (facoltativo)</label>
          <input
            id="riu-titolo"
            v-model="modulo.titolo"
            class="form-control form-control-sm"
            placeholder="Di base: «Riunione di…», «Consiglio Capi»…"
          />
        </div>
      </div>
      <p class="form-text mt-3 mb-0">
        Le riunioni non hanno quote e non si annunciano per email: le famiglie le vedono nell'app e
        nel calendario. Un'email parte solo se sposti o annulli una singola riunione.
      </p>
      <div class="d-flex gap-3 mt-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Crea
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="modulo = null">Annulla</button>
      </div>
    </form>

    <p v-if="!riunioni.length && !inCorso" class="fg-2">Nessuna riunione.</p>
    <ul class="list-group mb-7">
      <li v-for="r in riunioni" :key="r.id" class="list-group-item">
        <div class="d-flex flex-wrap align-items-baseline gap-3">
          <RouterLink
            :to="{ name: 'riunione', params: { id: r.id } }"
            :class="{ 'text-decoration-line-through': r.annullato }"
          >
            <strong>{{ r.titolo }}</strong>
          </RouterLink>
          <span class="small fg-2">{{ quando(r) }}</span>
          <span v-if="r.annullato" class="badge theme-danger">Annullata</span>
          <span
            v-else-if="r.uniforme === false && r.cerchia !== 'GENITORI'"
            class="badge theme-secondary"
          >
            Senza uniforme
          </span>
        </div>
        <div class="small fg-2">
          <ImmagineAnimale :animale="r.animale" />
          {{ perChi(r) }}<template v-if="r.luogo"> · {{ r.luogo }}</template>
        </div>
        <div v-for="t in (r.turni ?? []).filter((x) => x.mio)" :key="t.turno" class="small">
          Turno di {{ t.gruppo }}: <strong>{{ t.turno }}</strong>
        </div>
      </li>
    </ul>

    <section v-if="serie.length && !passate">
      <h2 class="h5">Riunioni di ogni settimana</h2>
      <ul class="list-group mb-5">
        <li v-for="s in serie" :key="s.id" class="list-group-item">
          <div>
            <strong>{{ s.titolo }}</strong>
            <span class="small fg-2">
              · ogni {{ GIORNI[s.giorno_settimana] }}, {{ s.ora_inizio.slice(0, 5) }}–{{
                s.ora_fine.slice(0, 5)
              }}<template v-if="s.luogo"> · {{ s.luogo }}</template> · dal {{ data(s.dal) }} al
              {{ data(s.al) }} · {{ s.riunioni }} riunioni
            </span>
          </div>
          <div v-if="s.puo_gestire" class="d-flex flex-wrap align-items-center gap-3 mt-1">
            <div class="form-field mb-0">
              <div class="switch">
                <input
                  :id="`serie-uniforme-${s.id}`"
                  type="checkbox"
                  role="switch"
                  :checked="s.uniforme"
                  :disabled="inCorso"
                  @change="cambiaUniforme(s, ($event.target as HTMLInputElement).checked)"
                />
              </div>
              <label :for="`serie-uniforme-${s.id}`" class="small">Con l'uniforme</label>
            </div>
            <button
              v-if="daTogliere !== s.id"
              type="button"
              class="btn btn-sm btn-link"
              @click="daTogliere = s.id"
            >
              Togli le prossime
            </button>
            <template v-else>
              <span class="small">Annullare tutte le prossime riunioni?</span>
              <button
                type="button"
                class="btn btn-sm btn-solid theme-danger"
                :disabled="inCorso"
                @click="togli(s)"
              >
                Togli le prossime
              </button>
              <button type="button" class="btn btn-sm btn-link" @click="daTogliere = null">
                No
              </button>
            </template>
          </div>
        </li>
      </ul>
      <p class="form-text">
        Una singola riunione (con l'uniforme o no, informazioni, spostarla o annullarla) si cambia
        dalla riunione stessa. Le riunioni passate restano con le loro presenze.
      </p>
    </section>
  </section>
</template>
