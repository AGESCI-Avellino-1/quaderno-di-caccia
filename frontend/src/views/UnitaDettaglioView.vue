<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import {
  api,
  nomeUnita,
  temaDellaBranca,
  type PersonaBreve,
  type Squadriglia,
  type Unita,
  type UnitaDettaglio,
  type UnitaIn,
} from '@/api/qdc'
import CodiciIscrizione from '@/components/CodiciIscrizione.vue'
import CopiaLocale from '@/components/CopiaLocale.vue'
import ElencoIncarichi from '@/components/ElencoIncarichi.vue'
import ModuloUnita from '@/components/ModuloUnita.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'

// Staff, roles and patrols of a unit. Reading works offline (cached copy); changes need
// the network. What each user may change comes from the backend (`nomina`, `puo_*`).
const props = defineProps<{ id: number }>()
const { errore, inCorso, esegui } = useErrore()
const dettaglio = ref<UnitaDettaglio | null>(null)
const copiaDel = ref<string | null>(null)
const altre = ref<Unita[]>([])
const modifica = ref(false)
const nuovaSquadriglia = reactive({ aperta: false, nome: '', sesso: 'F' })

async function carica(id = props.id) {
  const letto = await esegui(() => leggiConCache(`unita:${id}`, () => api.dettaglioUnita(id)))
  dettaglio.value = letto?.dati ?? null
  copiaDel.value = letto?.copiaDel ?? null
}
watch(
  () => props.id,
  (id) => carica(id),
  { immediate: true },
)

const unita = computed(() => dettaglio.value?.unita)
const rs = computed(() => unita.value?.branca === 'RS')

const breve = (p: PersonaBreve): PersonaBreve => ({ id: p.id, nome: p.nome, cognome: p.cognome })
const ragazziDi = async (unitaId: number) => (await api.persone(unitaId)).map(breve)

// Unit roles go to capi; in R/S the treasurer may also be a rover or scolta (DEC-11).
async function candidatiUnita(ruolo: string) {
  const capi = await api.capi()
  if (ruolo !== 'TESORIERE_UNITA' || !rs.value) return capi
  return [...capi, ...(await ragazziDi(props.id))]
}
// CSQ and VCSQ: members of their own patrol (DEC-13, DEC-14).
const candidatiDi = (s: Squadriglia) => async () => s.membri.map((m) => m.persona)

const squadriglieAttive = computed(() => dettaglio.value?.squadriglie.filter((s) => s.attiva) ?? [])

// Patrol composition (DEC-65): moving a ragazzo closes the previous membership from today.
// `verso` is a patrol id, or "fuori" to take them out of their patrol.
async function sposta(evento: Event, persona: number, membro?: number) {
  const scelta = evento.target as HTMLSelectElement
  const verso = scelta.value
  scelta.value = ''
  if (!verso) return
  const fatto = await esegui<unknown>(() =>
    verso === 'fuori' ? api.togliMembro(membro!) : api.aggiungiMembro(Number(verso), persona),
  )
  if (fatto) await carica()
}

async function apriModifica() {
  altre.value = ((await esegui(() => api.unita(true))) ?? []).filter((u) => u.id !== props.id)
  modifica.value = true
}

async function salva(dati: UnitaIn) {
  if (await esegui(() => api.modificaUnita(props.id, dati))) {
    modifica.value = false
    await carica()
  }
}

async function creaSquadriglia() {
  const dati = { nome: nuovaSquadriglia.nome.trim(), sesso: nuovaSquadriglia.sesso }
  if (await esegui(() => api.creaSquadriglia(props.id, dati))) {
    Object.assign(nuovaSquadriglia, { aperta: false, nome: '' })
    await carica()
  }
}

async function attivaSquadriglia(s: Squadriglia, attiva: boolean) {
  const dati = { nome: s.nome, sesso: s.sesso, attiva }
  if (await esegui(() => api.modificaSquadriglia(s.id, dati))) await carica()
}

const iniziale = (u: Unita): UnitaIn => ({
  nome: u.nome,
  tipo: u.tipo,
  composizione: u.composizione,
  ambiente: u.ambiente,
  collegata_a: u.collegata_a,
  nota_collegamento: u.nota_collegamento,
  attiva: u.attiva,
})
</script>

<template>
  <section v-if="unita && dettaglio" :data-branca="temaDellaBranca(unita.branca)">
    <div class="d-flex align-items-center flex-wrap gap-3 mb-1">
      <h1 class="h4 mb-0">{{ nomeUnita(unita) }}</h1>
      <span v-if="!unita.attiva" class="badge theme-secondary">Chiusa</span>
      <button
        v-if="dettaglio.puo_modificare && !modifica"
        type="button"
        class="btn btn-sm btn-outline theme-primary ms-auto"
        @click="apriModifica"
      >
        Modifica
      </button>
    </div>
    <p class="small">
      <RouterLink :to="{ name: 'persone', query: { unita: unita.id } }">Chi ne fa parte</RouterLink>
      <span v-if="unita.nota_collegamento" class="fg-2"> · {{ unita.nota_collegamento }}</span>
    </p>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <CopiaLocale :del="copiaDel" />
    <div v-if="dettaglio?.avvisi.length" class="alert theme-warning small" role="status">
      <div>
        <strong>Da controllare</strong>
        <ul class="mb-0 ps-5">
          <li v-for="(a, i) in dettaglio.avvisi" :key="i">{{ a }}</li>
        </ul>
      </div>
    </div>

    <div v-if="modifica" class="card card-body mb-5">
      <ModuloUnita
        :iniziale="iniziale(unita)"
        :altre="altre"
        :in-corso="inCorso"
        etichetta="Salva"
        @salva="salva"
        @annulla="modifica = false"
      />
    </div>

    <section class="card card-body mb-5">
      <h2 class="h5">Staff e incarichi</h2>
      <ElencoIncarichi
        :incarichi="dettaglio.incarichi"
        :nomina="dettaglio.nomina"
        :dove="{ unita_id: unita.id }"
        :candidati="candidatiUnita"
        vuoto="Nessuno staff registrato."
        @cambiato="carica()"
      />
    </section>

    <CodiciIscrizione :unita="unita.id" />

    <section v-if="unita.tipo === 'REPARTO'" class="card card-body mb-5">
      <div class="d-flex align-items-center mb-3">
        <h2 class="h5 mb-0">Squadriglie</h2>
        <button
          v-if="dettaglio.puo_gestire_squadriglie && !nuovaSquadriglia.aperta"
          type="button"
          class="btn btn-sm btn-outline theme-primary ms-auto"
          @click="nuovaSquadriglia.aperta = true"
        >
          Nuova squadriglia
        </button>
      </div>
      <form v-if="nuovaSquadriglia.aperta" class="row g-3 mb-5" @submit.prevent="creaSquadriglia">
        <div class="col-12 sm:col-6">
          <input
            v-model="nuovaSquadriglia.nome"
            class="form-control form-control-sm"
            placeholder="Nome (es. Aquile)"
            aria-label="Nome della squadriglia"
            required
          />
        </div>
        <div class="col-6 sm:col-3">
          <select
            v-model="nuovaSquadriglia.sesso"
            class="form-control form-control-sm"
            aria-label="Maschile o femminile"
          >
            <option value="F">Femminile</option>
            <option value="M">Maschile</option>
          </select>
        </div>
        <div class="col-6 sm:col-3 d-flex gap-1">
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Crea
          </button>
          <button
            type="button"
            class="btn btn-sm btn-link"
            @click="nuovaSquadriglia.aperta = false"
          >
            Annulla
          </button>
        </div>
      </form>
      <p v-if="!dettaglio.squadriglie.length" class="fg-2 small mb-0">Nessuna squadriglia.</p>
      <div
        v-for="s in dettaglio.squadriglie"
        :key="s.id"
        class="border-top pt-3 mt-3"
        :class="{ 'opacity-75': !s.attiva }"
      >
        <div class="d-flex align-items-center gap-3 mb-1">
          <strong>Sq. {{ s.nome }}</strong>
          <span class="fg-2 small">{{ s.sesso === 'F' ? 'femminile' : 'maschile' }}</span>
          <span v-if="!s.attiva" class="badge theme-secondary">Chiusa</span>
          <button
            v-if="dettaglio.puo_gestire_squadriglie"
            type="button"
            class="btn btn-link btn-sm p-0 ms-auto"
            :disabled="inCorso"
            @click="attivaSquadriglia(s, !s.attiva)"
          >
            {{ s.attiva ? 'chiudi' : 'riapri' }}
          </button>
        </div>
        <ul v-if="s.attiva" class="list-unstyled small mb-3">
          <li
            v-for="m in s.membri"
            :key="m.id"
            class="d-flex align-items-center flex-wrap gap-3 py-1"
          >
            <RouterLink :to="{ name: 'persona', params: { id: m.persona.id } }">
              {{ m.persona.nome }} {{ m.persona.cognome }}
            </RouterLink>
            <select
              v-if="dettaglio.puo_gestire_squadriglie"
              class="form-control form-control-sm w-auto ms-auto"
              :aria-label="`Sposta ${m.persona.nome} ${m.persona.cognome}`"
              :disabled="inCorso"
              @change="sposta($event, m.persona.id, m.id)"
            >
              <option value="">Sposta in…</option>
              <option
                v-for="altra in squadriglieAttive.filter((a) => a.id !== s.id)"
                :key="altra.id"
                :value="altra.id"
              >
                Sq. {{ altra.nome }}
              </option>
              <option value="fuori">Nessuna squadriglia</option>
            </select>
          </li>
          <li v-if="!s.membri.length" class="fg-2">Nessun membro.</li>
        </ul>
        <ElencoIncarichi
          v-if="s.attiva"
          :incarichi="s.incarichi"
          :nomina="s.nomina"
          :dove="{ squadriglia_id: s.id }"
          :candidati="candidatiDi(s)"
          vuoto="Nessun capo squadriglia."
          @cambiato="carica()"
        />
      </div>
      <div v-if="dettaglio.senza_squadriglia.length" class="border-top pt-3 mt-3">
        <strong>Senza squadriglia</strong>
        <ul class="list-unstyled small mb-0">
          <li
            v-for="p in dettaglio.senza_squadriglia"
            :key="p.id"
            class="d-flex align-items-center flex-wrap gap-3 py-1"
          >
            <RouterLink :to="{ name: 'persona', params: { id: p.id } }">
              {{ p.nome }} {{ p.cognome }}
            </RouterLink>
            <select
              v-if="dettaglio.puo_gestire_squadriglie && squadriglieAttive.length"
              class="form-control form-control-sm w-auto ms-auto"
              :aria-label="`Metti ${p.nome} ${p.cognome} in una squadriglia`"
              :disabled="inCorso"
              @change="sposta($event, p.id)"
            >
              <option value="">Metti in…</option>
              <option v-for="a in squadriglieAttive" :key="a.id" :value="a.id">
                Sq. {{ a.nome }}
              </option>
            </select>
          </li>
        </ul>
      </div>
    </section>
  </section>
  <div v-else-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
</template>
