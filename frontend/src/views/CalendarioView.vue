<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import {
  api,
  calendarioIcs,
  type Calendario,
  type Compleanno,
  type EventoCalendario,
} from '@/api/qdc'
import Icona from '@/components/Icona.vue'
import MioCalendario from '@/components/MioCalendario.vue'
import { useErrore } from '@/composables/useErrore'
import {
  chiaveGiorno,
  compleanniDelGiorno,
  eventiDelGiorno,
  leggiModo,
  leggiVista,
  salvaModo,
  salvaVista,
  settimaneDelMese,
  type ModoCalendario,
} from '@/eventi/calendario'
import { puoCreareEventi, puoCreareRiunioni } from '@/eventi/creazione'
import { quandoEvento } from '@/eventi/orario'
import { useSessioneStore } from '@/stores/sessione'

// The user's and their children's events as a month or as a list of the next ones; a
// capo chooses among the views, «Tutti i miei eventi» first (DEC-143, DEC-286, DEC-334). Files to download and the
// personal link to subscribe. Online only for now. Ragazzi/e and capi also see the birthdays:
// the next ones as a list, and a sign on the days of the month (DEC-417).
const { errore, esegui } = useErrore()
const modo = ref<ModoCalendario>(leggiModo())
const viste = ref<Calendario['viste']>([])
const vista = ref(leggiVista())
const eventi = ref<EventoCalendario[]>([])
const caricato = ref(false)
const conCompleanni = ref(false)
const compleanni = ref<Compleanno[]>([])

const oggi = new Date()
const mese = ref(new Date(oggi.getFullYear(), oggi.getMonth(), 1))
const scelto = ref(chiaveGiorno(oggi))

const settimane = computed(() => settimaneDelMese(mese.value.getFullYear(), mese.value.getMonth()))
const titoloMese = computed(() =>
  mese.value.toLocaleDateString('it-IT', { month: 'long', year: 'numeric' }),
)
const giorniSettimana = ['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom']

// A «+» on every day from today, to create a meeting or an event on it (DEC-412): a small
// menu with what the user may create, straight to the form when only one.
const router = useRouter()
const route = useRoute()
const sessione = useSessioneStore()
const creabili = computed(() =>
  [
    puoCreareRiunioni(sessione.profilo) && { nome: 'Nuova riunione', percorso: '/riunioni' },
    puoCreareEventi(sessione.profilo) && { nome: 'Nuovo evento', percorso: '/eventi' },
  ].filter((v): v is { nome: string; percorso: string } => !!v),
)
const menuDi = ref<string | null>(null)
const conPiu = (giorno: Date) =>
  creabili.value.length > 0 &&
  giorno.getMonth() === mese.value.getMonth() &&
  chiaveGiorno(giorno) >= chiaveGiorno(oggi)
function piu(giorno: Date) {
  const chiave = chiaveGiorno(giorno)
  if (creabili.value.length === 1) {
    void router.push({ path: creabili.value[0]!.percorso, query: { giorno: chiave } })
    return
  }
  menuDi.value = menuDi.value === chiave ? null : chiave
}
const chiudiMenu = (evento: Event) => {
  if (!(evento.target as HTMLElement).closest?.('.qdc-piu, .qdc-menu-piu')) menuDi.value = null
}
onMounted(() => document.addEventListener('click', chiudiMenu))
onBeforeUnmount(() => document.removeEventListener('click', chiudiMenu))

async function carica() {
  if (modo.value === 'compleanni') {
    compleanni.value = (await esegui(() => api.compleanniDelCalendario())) ?? []
    caricato.value = true
    return
  }
  let dal: string, al: string | undefined
  if (modo.value === 'mese') {
    const giorni = settimane.value.flat()
    dal = chiaveGiorno(giorni[0]!)
    al = chiaveGiorno(giorni[giorni.length - 1]!)
  } else {
    dal = chiaveGiorno(new Date())
  }
  const [trovati, delMese] = await Promise.all([
    esegui(() => api.eventiDelCalendario(vista.value, dal, al)),
    modo.value === 'mese' && conCompleanni.value
      ? esegui(() => api.compleanniDelCalendario(dal, al))
      : null,
  ])
  eventi.value = trovati ?? []
  compleanni.value = delMese ?? []
  caricato.value = true
}

onMounted(async () => {
  const calendario = await esegui(() => api.calendario())
  viste.value = calendario?.viste ?? []
  // A remembered view that no longer applies (no longer a capo): the default.
  if (!viste.value.some((v) => v.vista === vista.value)) vista.value = viste.value[0]?.vista ?? ''
  conCompleanni.value = calendario?.compleanni ?? false
  // From the morning notification; a remembered mode that no longer applies: the month.
  let iniziale = modo.value
  if (route.query.mostra === 'compleanni') iniziale = 'compleanni'
  if (iniziale === 'compleanni' && !conCompleanni.value) iniziale = 'mese'
  if (iniziale !== modo.value) {
    modo.value = iniziale // the watcher loads
    return
  }
  await carica()
})

watch(modo, (nuovo) => {
  salvaModo(nuovo)
  void carica()
})
watch(vista, (nuova) => {
  salvaVista(nuova)
  void carica()
})

function cambiaMese(di: number) {
  mese.value = new Date(mese.value.getFullYear(), mese.value.getMonth() + di, 1)
  void carica()
}

function vaiAOggi() {
  mese.value = new Date(oggi.getFullYear(), oggi.getMonth(), 1)
  scelto.value = chiaveGiorno(oggi)
  void carica()
}

const delGiornoScelto = computed(() =>
  eventiDelGiorno(eventi.value, new Date(`${scelto.value}T12:00:00`)),
)

const quando = (e: EventoCalendario) => quandoEvento(e, true)

const compleanniDelGiornoScelto = computed(() =>
  compleanniDelGiorno(compleanni.value, new Date(`${scelto.value}T12:00:00`)),
)

function giornoCompleanno(c: Compleanno): string {
  const giorno = new Date(`${c.giorno}T12:00:00`)
  const domani = new Date(oggi.getFullYear(), oggi.getMonth(), oggi.getDate() + 1)
  if (c.giorno === chiaveGiorno(oggi)) return 'oggi'
  if (c.giorno === chiaveGiorno(domani)) return 'domani'
  return giorno.toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long' })
}

function descriviGiorno(giorno: Date): string {
  const nEventi = eventiDelGiorno(eventi.value, giorno).length
  const nCompleanni = compleanniDelGiorno(compleanni.value, giorno).length
  return (
    giorno.toLocaleDateString('it-IT', { day: 'numeric', month: 'long' }) +
    (nEventi ? `, ${nEventi} eventi` : '') +
    (nCompleanni ? `, ${nCompleanni === 1 ? 'un compleanno' : `${nCompleanni} compleanni`}` : '')
  )
}
</script>

<template>
  <section>
    <h1 class="h4 mb-5">Calendario</h1>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>

    <div class="d-flex flex-wrap align-items-center gap-3 mb-5">
      <div class="btn-group" role="group" aria-label="Come vedere gli eventi">
        <button
          type="button"
          class="btn btn-sm"
          :class="modo === 'mese' ? 'btn-solid theme-primary' : 'btn-outline theme-primary'"
          :aria-pressed="modo === 'mese'"
          @click="modo = 'mese'"
        >
          Mese
        </button>
        <button
          type="button"
          class="btn btn-sm"
          :class="modo === 'elenco' ? 'btn-solid theme-primary' : 'btn-outline theme-primary'"
          :aria-pressed="modo === 'elenco'"
          @click="modo = 'elenco'"
        >
          Prossimi eventi
        </button>
        <button
          v-if="conCompleanni"
          type="button"
          class="btn btn-sm"
          :class="modo === 'compleanni' ? 'btn-solid theme-primary' : 'btn-outline theme-primary'"
          :aria-pressed="modo === 'compleanni'"
          @click="modo = 'compleanni'"
        >
          Prossimi compleanni
        </button>
      </div>
      <select
        v-if="viste.length && modo !== 'compleanni'"
        v-model="vista"
        class="form-control w-auto"
        aria-label="Quali eventi vedere"
      >
        <option v-for="v in viste" :key="v.vista" :value="v.vista">{{ v.nome }}</option>
      </select>
      <a v-if="modo !== 'compleanni'" :href="calendarioIcs(vista)" class="small" download
        >Scarica il calendario</a
      >
    </div>

    <template v-if="modo === 'mese'">
      <div class="d-flex align-items-center gap-3 mb-3">
        <button
          type="button"
          class="btn btn-sm btn-outline"
          aria-label="Mese prima"
          @click="cambiaMese(-1)"
        >
          <Icona nome="chevron-left" />
        </button>
        <h2 class="h5 mb-0 qdc-mese">{{ titoloMese }}</h2>
        <button
          type="button"
          class="btn btn-sm btn-outline"
          aria-label="Mese dopo"
          @click="cambiaMese(1)"
        >
          <Icona nome="chevron-right" />
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="vaiAOggi">Oggi</button>
      </div>
      <table class="qdc-calendario mb-5">
        <thead>
          <tr>
            <th v-for="g in giorniSettimana" :key="g" scope="col" class="small fg-2">{{ g }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(settimana, n) in settimane" :key="n">
            <td
              v-for="giorno in settimana"
              :key="chiaveGiorno(giorno)"
              :class="{
                'qdc-fuori-mese': giorno.getMonth() !== mese.getMonth(),
                'qdc-oggi': chiaveGiorno(giorno) === chiaveGiorno(oggi),
                'qdc-scelto': chiaveGiorno(giorno) === scelto,
              }"
            >
              <button
                type="button"
                class="qdc-giorno"
                :aria-label="descriviGiorno(giorno)"
                @click="scelto = chiaveGiorno(giorno)"
              >
                <span class="small"
                  >{{ giorno.getDate() }}
                  <Icona
                    v-if="compleanniDelGiorno(compleanni, giorno).length"
                    nome="cake2"
                    class="qdc-compleanno-giorno"
                /></span>
                <span
                  v-for="e in eventiDelGiorno(eventi, giorno)"
                  :key="e.id"
                  class="qdc-evento-giorno"
                  :class="{ 'text-decoration-line-through': e.annullato }"
                  >{{ e.titolo }}</span
                >
              </button>
              <button
                v-if="conPiu(giorno)"
                type="button"
                class="qdc-piu"
                :aria-label="`Crea il ${giorno.toLocaleDateString('it-IT', { day: 'numeric', month: 'long' })}`"
                :aria-expanded="creabili.length > 1 ? menuDi === chiaveGiorno(giorno) : undefined"
                @click="piu(giorno)"
              >
                <Icona nome="plus-lg" />
              </button>
              <div
                v-if="menuDi === chiaveGiorno(giorno)"
                class="qdc-menu-piu"
                :class="{ 'qdc-menu-sinistra': [1, 2].includes(giorno.getDay()) }"
                role="menu"
              >
                <RouterLink
                  v-for="c in creabili"
                  :key="c.percorso"
                  :to="{ path: c.percorso, query: { giorno: chiaveGiorno(giorno) } }"
                  role="menuitem"
                  >{{ c.nome }}</RouterLink
                >
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <h2 class="h6">
        {{
          new Date(`${scelto}T12:00:00`).toLocaleDateString('it-IT', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
          })
        }}
      </h2>
      <ul
        v-if="compleanniDelGiornoScelto.length"
        class="list-unstyled mb-3"
        aria-label="Compleanni"
      >
        <li v-for="c in compleanniDelGiornoScelto" :key="c.persona_id" class="small">
          <Icona nome="cake2" class="qdc-compleanno-giorno" />
          <RouterLink v-if="c.scheda" :to="`/persone/${c.persona_id}`"
            >{{ c.nome }} {{ c.cognome }}</RouterLink
          ><template v-else>{{ c.nome }} {{ c.cognome }}</template> compie {{ c.anni }} anni
          <span v-if="c.coca" class="badge theme-primary ms-1">Co.Ca.</span>
        </li>
      </ul>
      <p v-if="!delGiornoScelto.length" class="small fg-2">Nessun evento in questo giorno.</p>
    </template>

    <template v-if="modo === 'compleanni'">
      <ul v-if="compleanni.length" class="list-group mb-5" aria-label="Prossimi compleanni">
        <li
          v-for="c in compleanni"
          :key="`${c.persona_id}-${c.giorno}`"
          class="list-group-item"
          :class="{ 'qdc-compleanno-coca': c.coca }"
        >
          <RouterLink v-if="c.scheda" :to="`/persone/${c.persona_id}`" class="fw-bold"
            >{{ c.nome }} {{ c.cognome }}</RouterLink
          >
          <span v-else class="fw-bold">{{ c.nome }} {{ c.cognome }}</span>
          <span v-if="c.coca" class="badge theme-primary ms-3">Co.Ca.</span>
          <div class="small fg-2">
            {{ giornoCompleanno(c) }} · compie {{ c.anni }} anni<template v-if="c.unita">
              · {{ c.unita }}</template
            >
          </div>
        </li>
      </ul>
      <p v-else-if="caricato" class="small fg-2">Nessun compleanno nei prossimi 30 giorni.</p>
    </template>

    <ul
      v-if="modo === 'elenco' || (modo === 'mese' && delGiornoScelto.length)"
      class="list-group mb-5"
      aria-label="Eventi"
    >
      <li
        v-for="e in modo === 'elenco' ? eventi : delGiornoScelto"
        :key="e.id"
        class="list-group-item"
      >
        <RouterLink :to="`/eventi/${e.id}`" class="fw-bold">
          <span :class="{ 'text-decoration-line-through': e.annullato }">{{ e.titolo }}</span>
        </RouterLink>
        <span v-if="e.annullato" class="badge theme-danger ms-3">Annullato</span>
        <div class="small fg-2">
          {{ e.tipo_nome }} · {{ quando(e) }}<template v-if="e.luogo"> · {{ e.luogo }}</template>
        </div>
      </li>
    </ul>
    <p v-if="modo === 'elenco' && caricato && !eventi.length" class="small fg-2">
      Nessun evento in programma.
    </p>

    <MioCalendario />
  </section>
</template>
