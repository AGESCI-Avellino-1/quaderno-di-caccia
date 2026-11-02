<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { api, calendarioIcs, type Calendario, type EventoCalendario } from '@/api/qdc'
import Icona from '@/components/Icona.vue'
import MioCalendario from '@/components/MioCalendario.vue'
import { useErrore } from '@/composables/useErrore'
import {
  chiaveGiorno,
  eventiDelGiorno,
  leggiModo,
  leggiVista,
  salvaModo,
  salvaVista,
  settimaneDelMese,
  type ModoCalendario,
} from '@/eventi/calendario'

// The user's and their children's events as a month or as a list of the next ones; a
// capo chooses among the three views (DEC-143, DEC-286). Files to download and the
// personal link to subscribe. Online only for now.
const { errore, esegui } = useErrore()
const modo = ref<ModoCalendario>(leggiModo())
const viste = ref<Calendario['viste']>([])
const vista = ref(leggiVista())
const eventi = ref<EventoCalendario[]>([])
const caricato = ref(false)

const oggi = new Date()
const mese = ref(new Date(oggi.getFullYear(), oggi.getMonth(), 1))
const scelto = ref(chiaveGiorno(oggi))

const settimane = computed(() => settimaneDelMese(mese.value.getFullYear(), mese.value.getMonth()))
const titoloMese = computed(() =>
  mese.value.toLocaleDateString('it-IT', { month: 'long', year: 'numeric' }),
)
const giorniSettimana = ['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom']

async function carica() {
  let dal: string, al: string | undefined
  if (modo.value === 'mese') {
    const giorni = settimane.value.flat()
    dal = chiaveGiorno(giorni[0]!)
    al = chiaveGiorno(giorni[giorni.length - 1]!)
  } else {
    dal = chiaveGiorno(new Date())
  }
  eventi.value = (await esegui(() => api.eventiDelCalendario(vista.value, dal, al))) ?? []
  caricato.value = true
}

onMounted(async () => {
  const calendario = await esegui(() => api.calendario())
  viste.value = calendario?.viste ?? []
  // A remembered view that no longer applies (no longer a capo): the default.
  if (!viste.value.some((v) => v.vista === vista.value)) vista.value = viste.value[0]?.vista ?? ''
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

const quando = (e: EventoCalendario) => {
  const inizio = new Date(e.inizio)
  const fine = new Date(e.fine)
  const giorno = (d: Date) =>
    d.toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'short' })
  const ora = (d: Date) => d.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
  return chiaveGiorno(inizio) === chiaveGiorno(fine)
    ? `${giorno(inizio)}, ${ora(inizio)}–${ora(fine)}`
    : `${giorno(inizio)} ${ora(inizio)} – ${giorno(fine)} ${ora(fine)}`
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
      </div>
      <select
        v-if="viste.length"
        v-model="vista"
        class="form-control w-auto"
        aria-label="Quali eventi vedere"
      >
        <option v-for="v in viste" :key="v.vista" :value="v.vista">{{ v.nome }}</option>
      </select>
      <a :href="calendarioIcs(vista)" class="small" download>Scarica il calendario</a>
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
                :aria-label="
                  giorno.toLocaleDateString('it-IT', { day: 'numeric', month: 'long' }) +
                  (eventiDelGiorno(eventi, giorno).length
                    ? `, ${eventiDelGiorno(eventi, giorno).length} eventi`
                    : '')
                "
                @click="scelto = chiaveGiorno(giorno)"
              >
                <span class="small">{{ giorno.getDate() }}</span>
                <span
                  v-for="e in eventiDelGiorno(eventi, giorno)"
                  :key="e.id"
                  class="qdc-evento-giorno"
                  :class="{ 'text-decoration-line-through': e.annullato }"
                  >{{ e.titolo }}</span
                >
              </button>
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
      <p v-if="!delGiornoScelto.length" class="small fg-2">Nessun evento in questo giorno.</p>
    </template>

    <ul
      v-if="modo === 'elenco' || delGiornoScelto.length"
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
