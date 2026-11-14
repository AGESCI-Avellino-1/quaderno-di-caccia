<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import {
  api,
  bozzaSquadrigliePdf,
  nomeUnita,
  temaDellaBranca,
  type AnimaleSquadriglia,
  type PersonaBreve,
  type Squadriglia,
  type Unita,
  type UnitaDettaglio,
  type UnitaIn,
} from '@/api/qdc'
import Avatar from '@/components/Avatar.vue'
import CodiciIscrizione from '@/components/CodiciIscrizione.vue'
import AltaSquadriglia from '@/components/AltaSquadriglia.vue'
import CopiaLocale from '@/components/CopiaLocale.vue'
import EtaUnita from '@/components/EtaUnita.vue'
import DelegaSquadriglia from '@/components/DelegaSquadriglia.vue'
import ElencoIncarichi from '@/components/ElencoIncarichi.vue'
import ImmagineAnimale from '@/components/ImmagineAnimale.vue'
import ModuloUnita from '@/components/ModuloUnita.vue'
import SestiglieUnita from '@/components/SestiglieUnita.vue'
import TurniUnita from '@/components/TurniUnita.vue'
import { useErrore } from '@/composables/useErrore'
import { useNomePagina } from '@/composables/useNomePagina'
import { useRubrica } from '@/composables/useRubrica'
import { leggiConCache } from '@/offline/cache'
import { useSessioneStore } from '@/stores/sessione'

// Staff, roles and patrols of a unit. Reading works offline (cached copy); changes need
// the network. What each user may change comes from the backend (`nomina`, `puo_*`).
const props = defineProps<{ id: number }>()
const router = useRouter()
const { errore, inCorso, esegui } = useErrore()
const dettaglio = ref<UnitaDettaglio | null>(null)
const copiaDel = ref<string | null>(null)
const altre = ref<Unita[]>([])
const modifica = ref(false)
const sessione = useSessioneStore()
const rubrica = useRubrica()
const nuovaSquadriglia = reactive({
  aperta: false,
  animale: null as number | null,
  sesso: 'F',
  reparto: 0,
})

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
useNomePagina(() => unita.value && nomeUnita(unita.value))
const rs = computed(() => unita.value?.branca === 'RS')
const LC = ['BRANCO', 'CERCHIO', 'BRANCO_CERCHIO']
const CON_TURNI = ['REPARTO', ...LC]
const turniCollegata = computed(
  () =>
    !!unita.value?.collegata_a &&
    CON_TURNI.includes(unita.value.tipo) &&
    CON_TURNI.includes(unita.value.collegata_tipo ?? ''),
)
const linkataLC = computed(
  () =>
    !!unita.value && LC.includes(unita.value.collegata_tipo ?? '') && LC.includes(unita.value.tipo),
)

const breve = (p: PersonaBreve): PersonaBreve => ({ id: p.id, nome: p.nome, cognome: p.cognome })
const ragazziDi = async (unitaId: number) => (await api.persone(unitaId)).map(breve)

// Unit roles go to capi; in R/S the treasurer may also be a rover or scolta (DEC-11);
// the Consiglio degli Anziani is made of the lupetti and coccinelle (DEC-182).
async function candidatiUnita(ruolo: string) {
  if (ruolo === 'CONSIGLIO_ANZIANI') return ragazziDi(props.id)
  // Only a presbitero may be assistente ecclesiastico (DEC-296).
  const capi = await api.capi(ruolo === 'AE_UNITA')
  if (ruolo !== 'TESORIERE_UNITA' || !rs.value) return capi
  return [...capi, ...(await ragazziDi(props.id))]
}
// Patrol roles: members of their own patrol (DEC-13, DEC-14, DEC-321).
const candidatiDi = (s: Squadriglia) => async () => s.membri.map((m) => m.persona)
// The ragazzi of a reparto: patrol members and who is in no patrol yet.
const ragazziDelReparto = computed(() => [
  ...squadriglieDi(props.id).flatMap((s) => s.membri.map((m) => m.persona)),
  ...(dettaglio.value?.senza_squadriglia.filter((p) => p.reparto_id === props.id) ?? []),
])

// With two linked reparti both are here (DEC-405): a ragazzo moves only among the patrols
// of their own reparto.
const squadriglieDi = (reparto: number) =>
  dettaglio.value?.squadriglie.filter((s) => s.unita_id === reparto) ?? []
const insieme = computed(() => (dettaglio.value?.reparti?.length ?? 0) > 1)
const nomeReparto = (id: number) => dettaglio.value?.reparti?.find((r) => r.id === id)?.nome ?? ''

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

// Two linked units with one cash box (DEC-288): united any day, split only at the start
// of a year, before its first movement.
const confermaCasse = ref(false)
async function unisciCasse() {
  confermaCasse.value = false
  if (await esegui(() => api.unisciCasse(props.id))) await carica()
}
async function dividiCasse() {
  if (await esegui(() => api.dividiCasse(props.id))) await carica()
}

// Only a closed unit nobody was ever in: created by mistake (DEC-273).
const eliminando = ref(false)
async function elimina() {
  await esegui(() => api.eliminaUnita(props.id))
  if (!errore.value) await router.push({ name: 'unita' })
}

// A single-sex reparto has patrols of its own sex only (DEC-280): no choice to make.
const repartoNuova = computed(
  () =>
    dettaglio.value?.reparti?.find((r) => r.id === nuovaSquadriglia.reparto) ?? unita.value ?? null,
)
const sessoDelReparto = computed(() =>
  repartoNuova.value && repartoNuova.value.composizione !== 'X'
    ? repartoNuova.value.composizione
    : null,
)

// The animals to choose from (DEC-351): not the switched off ones, nor those of this reparto.
const animali = ref<AnimaleSquadriglia[]>([])
const nomiPresi = computed(
  () => new Set(squadriglieDi(nuovaSquadriglia.reparto || props.id).map((s) => s.nome)),
)
const liberi = computed(() =>
  animali.value.filter((a) => a.attivo && !nomiPresi.value.has(a.plurale)),
)
const generali = computed(() => liberi.value.filter((a) => a.tipo === 'GENERALE'))
const nautici = computed(() => liberi.value.filter((a) => a.tipo === 'NAUTICO'))
const animaleScelto = computed(() => animali.value.find((a) => a.id === nuovaSquadriglia.animale))
// Read once, when the staff first needs them.
async function caricaAnimali() {
  if (animali.value.length) return
  animali.value = (await esegui(() => api.animali()))?.animali ?? []
}

async function apriNuovaSquadriglia() {
  nuovaSquadriglia.aperta = true
  nuovaSquadriglia.reparto = props.id
  await caricaAnimali()
}

async function creaSquadriglia() {
  // Without an animal: "Nuova Squadriglia N" until its CSQ chooses one (DEC-409).
  const animale_id = nuovaSquadriglia.animale ?? undefined
  const sesso = sessoDelReparto.value ?? nuovaSquadriglia.sesso
  const reparto = nuovaSquadriglia.reparto || props.id
  if (await esegui(() => api.creaSquadriglia(reparto, { animale_id, sesso }))) {
    Object.assign(nuovaSquadriglia, { aperta: false, animale: null })
    await carica()
  }
}

// A patrol from before the animals (DEC-351), one still waiting for its CSQ, or the CSQ's
// choice corrected within a month (DEC-409).
const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
async function scegliAnimale(evento: Event, s: Squadriglia) {
  const scelta = evento.target as HTMLSelectElement
  const animale_id = Number(scelta.value)
  if (!animale_id) return
  const dati = { animale_id, sesso: s.sesso }
  if (await esegui(() => api.modificaSquadriglia(s.id, dati))) await carica()
}

// Only an empty patrol, for good (DEC-403): the page of the archived ones keeps it.
const archiviando = ref<number | null>(null)
async function archiviaSquadriglia(s: Squadriglia) {
  archiviando.value = null
  if (await esegui(() => api.archiviaSquadriglia(s.id))) await carica()
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
      <span v-if="unita.archiviata_il" class="badge theme-secondary">Archiviata</span>
      <span v-else-if="!unita.attiva" class="badge theme-secondary">Chiusa</span>
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
      ·
      <RouterLink :to="{ name: 'passaggi', params: { id: unita.id } }">Passaggi</RouterLink>
      <template v-if="unita.tipo !== 'COMUNITA_CAPI'">
        ·
        <RouterLink :to="{ name: 'sentiero-unita', params: { id: unita.id } }">
          Progressione Personale
        </RouterLink>
      </template>
      <template v-if="unita.tipo === 'CLAN_FUOCO'">
        ·
        <RouterLink :to="{ name: 'carta-clan', params: { id: unita.id } }"
          >Carta di clan</RouterLink
        >
      </template>
      <template v-if="unita.tipo === 'REPARTO'">
        ·
        <RouterLink :to="{ name: 'imprese', params: { id: unita.id } }">
          Imprese e specialità di squadriglia
        </RouterLink>
      </template>
      <template v-if="unita.collegata_a">
        · Collegata a
        <RouterLink :to="{ name: 'unita-dettaglio', params: { id: unita.collegata_a } }">{{
          unita.collegata_nome
        }}</RouterLink>
        <span v-if="unita.nota_collegamento" class="fg-2"> ({{ unita.nota_collegamento }})</span>
        <template v-if="unita.cassa_comune_dal">
          · cassa in comune dal {{ new Date(unita.cassa_comune_dal).toLocaleDateString('it-IT') }}
        </template>
      </template>
    </p>
    <div
      v-if="dettaglio && (dettaglio.puo_unire_casse || dettaglio.puo_dividere_casse)"
      class="card card-body small mb-5"
    >
      <template v-if="dettaglio.puo_unire_casse">
        <p class="mb-3">
          Le due unità collegate possono avere una sola cassa contanti: da oggi i saldi si sommano,
          i tesorieri di ciascuna valgono per tutte e due e il rendiconto le mostra insieme. Si
          dividono di nuovo solo all'inizio di un anno associativo, prima di ogni movimento.
        </p>
        <div class="d-flex gap-3">
          <button
            v-if="!confermaCasse"
            type="button"
            class="btn btn-sm btn-outline theme-primary"
            @click="confermaCasse = true"
          >
            Unisci le casse
          </button>
          <template v-else>
            <button
              type="button"
              class="btn btn-sm btn-solid theme-primary"
              :disabled="inCorso"
              @click="unisciCasse"
            >
              Sì, unisci le casse da oggi
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="confermaCasse = false">
              Annulla
            </button>
          </template>
        </div>
      </template>
      <template v-else>
        <p class="mb-3">
          L'anno associativo è appena cominciato e non ci sono ancora movimenti: puoi dividere di
          nuovo le casse delle due unità.
        </p>
        <button
          type="button"
          class="btn btn-sm btn-outline theme-primary align-self-start"
          :disabled="inCorso"
          @click="dividiCasse"
        >
          Dividi le casse
        </button>
      </template>
    </div>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <EtaUnita
      v-if="unita && dettaglio"
      :unita="unita"
      :modificabile="!!dettaglio.puo_modificare_eta"
    />
    <CopiaLocale :del="copiaDel" />
    <div v-if="dettaglio?.avvisi.length" class="alert theme-warning small" role="status">
      <div>
        <strong>Da controllare</strong>
        <ul class="mb-0 ps-5">
          <li v-for="(a, i) in dettaglio.avvisi" :key="i">{{ a }}</li>
        </ul>
      </div>
    </div>

    <div v-if="dettaglio.puo_eliminare" class="alert theme-info small" role="status">
      <div class="d-flex flex-wrap align-items-center gap-3">
        <span
          >Nell'unità non c'è mai stato nessuno: se l'hai creata per errore puoi eliminarla.</span
        >
        <button
          v-if="!eliminando"
          type="button"
          class="btn btn-sm btn-outline theme-danger ms-auto"
          @click="eliminando = true"
        >
          Elimina…
        </button>
        <span v-else class="ms-auto d-flex align-items-center gap-1">
          Eliminarla per sempre?
          <button
            type="button"
            class="btn btn-sm btn-solid theme-danger"
            :disabled="inCorso"
            @click="elimina"
          >
            Confermo
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="eliminando = false">No</button>
        </span>
      </div>
    </div>

    <div v-if="modifica" class="card card-body mb-5">
      <ModuloUnita
        :iniziale="iniziale(unita)"
        :altre="altre"
        :unita-id="unita.id"
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

    <!-- The unit's numbers into the phone's contacts (DEC-302): the list, ready to choose. -->
    <section v-if="rubrica.disponibile.value && sessione.capo" class="card card-body mb-5">
      <h2 class="h5">Numeri nella rubrica del telefono</h2>
      <p class="small fg-2">
        Scegli chi aggiungere alla rubrica: il telefono ti propone di salvare i contatti, con nome e
        numeri.
      </p>
      <div class="d-flex flex-wrap gap-3">
        <RouterLink
          :to="{ name: 'persone', query: { unita: unita.id, rubrica: '1' } }"
          class="btn btn-sm btn-outline theme-primary"
          >Soci dell'unità</RouterLink
        >
        <RouterLink
          :to="{ name: 'genitori', query: { unita: unita.id, rubrica: '1' } }"
          class="btn btn-sm btn-outline theme-primary"
          >Genitori</RouterLink
        >
      </div>
    </section>

    <CodiciIscrizione :unita="unita.id" />

    <section v-if="unita.tipo === 'REPARTO'" class="card card-body mb-5">
      <div class="d-flex align-items-center mb-3">
        <h2 class="h5 mb-0">Squadriglie</h2>
        <button
          v-if="dettaglio.puo_gestire_squadriglie && !nuovaSquadriglia.aperta"
          type="button"
          class="btn btn-sm btn-outline theme-primary ms-auto"
          @click="apriNuovaSquadriglia"
        >
          Nuova squadriglia
        </button>
      </div>
      <form v-if="nuovaSquadriglia.aperta" class="row g-3 mb-5" @submit.prevent="creaSquadriglia">
        <div v-if="insieme" class="col-12">
          <select
            v-model="nuovaSquadriglia.reparto"
            class="form-control form-control-sm"
            aria-label="Reparto della squadriglia"
          >
            <option v-for="r in dettaglio.reparti" :key="r.id" :value="r.id">{{ r.nome }}</option>
          </select>
        </div>
        <div class="col-12 sm:col-6">
          <div class="d-flex align-items-center gap-3">
            <ImmagineAnimale :animale="animaleScelto" />
            <select
              v-model="nuovaSquadriglia.animale"
              class="form-control form-control-sm"
              aria-label="Animale della squadriglia"
            >
              <option :value="null">Senza animale: lo sceglie il capo squadriglia</option>
              <optgroup label="Generali">
                <option v-for="a in generali" :key="a.id" :value="a.id">{{ a.plurale }}</option>
              </optgroup>
              <optgroup label="Nautici">
                <option v-for="a in nautici" :key="a.id" :value="a.id">{{ a.plurale }}</option>
              </optgroup>
            </select>
          </div>
          <p class="form-text mb-0">
            Manca?
            <RouterLink :to="{ name: 'animali-squadriglia' }">Aggiungilo all'elenco</RouterLink>.
          </p>
        </div>
        <div v-if="!sessoDelReparto" class="col-6 sm:col-3">
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
      <div v-for="s in dettaglio.squadriglie" :key="s.id" class="border-top pt-3 mt-3">
        <div class="d-flex align-items-center flex-wrap gap-3 mb-1">
          <ImmagineAnimale :animale="s.animale" />
          <strong>Sq. {{ s.nome }}</strong>
          <span class="fg-2 small">{{ s.sesso === 'F' ? 'femminile' : 'maschile' }}</span>
          <span v-if="s.unita_nome" class="badge theme-secondary">{{ s.unita_nome }}</span>
          <template v-if="dettaglio.puo_gestire_squadriglie && !s.membri.length">
            <button
              v-if="archiviando !== s.id"
              type="button"
              class="btn btn-link btn-sm p-0 ms-auto"
              :disabled="inCorso"
              @click="archiviando = s.id"
            >
              archivia
            </button>
            <span v-else class="ms-auto d-flex align-items-center gap-1 small">
              Archiviarla per sempre?
              <button
                type="button"
                class="btn btn-sm btn-solid theme-danger"
                :disabled="inCorso"
                @click="archiviaSquadriglia(s)"
              >
                Archivia
              </button>
              <button type="button" class="btn btn-sm btn-link" @click="archiviando = null">
                No
              </button>
            </span>
          </template>
        </div>
        <p v-if="s.provvisoria" class="small fg-2 mb-1">
          Senza animale: lo sceglie il capo squadriglia.
        </p>
        <select
          v-if="dettaglio.puo_gestire_squadriglie && (!s.animale || s.correggibile_fino)"
          class="form-control form-control-sm mb-3"
          :aria-label="s.animale ? `Correggi l'animale di Sq. ${s.nome}` : 'Scegli l\'animale'"
          :disabled="inCorso"
          @focus="caricaAnimali"
          @change="scegliAnimale($event, s)"
        >
          <option value="">
            {{
              s.correggibile_fino
                ? `Correggi l'animale scelto dal capo squadriglia (fino al ${data(s.correggibile_fino)})…`
                : "Scegli l'animale…"
            }}
          </option>
          <optgroup label="Generali">
            <option v-for="a in generali" :key="a.id" :value="a.id">{{ a.plurale }}</option>
          </optgroup>
          <optgroup label="Nautici">
            <option v-for="a in nautici" :key="a.id" :value="a.id">{{ a.plurale }}</option>
          </optgroup>
        </select>
        <ul v-if="s.attiva" class="list-unstyled small mb-3">
          <li
            v-for="m in s.membri"
            :key="m.id"
            class="d-flex align-items-center flex-wrap gap-3 py-1"
          >
            <Avatar
              :nome="`${m.persona.nome} ${m.persona.cognome}`"
              :scheda="m.persona.scheda ? m.persona.id : null"
              dimensione="xs"
              tenue
              aria-hidden="true"
            />
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
                v-for="altra in squadriglieDi(s.unita_id).filter((a) => a.id !== s.id)"
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
          vuoto="Nessun incarico."
          @cambiato="carica()"
        />
        <!-- The reparto staff may delegate too (DEC-267); hidden to who may not. -->
        <DelegaSquadriglia
          v-if="s.attiva && s.membri.length"
          :squadriglia="s.id"
          :membri="s.membri.map((m) => m.persona)"
        />
      </div>
      <p
        v-if="dettaglio.puo_gestire_squadriglie && dettaglio.squadriglie.length"
        class="form-text mt-3 mb-0"
      >
        L'animale di una squadriglia non si cambia: per cambiarlo aprine una nuova, spostaci i
        membri e archivia la vecchia. Si archivia solo una squadriglia vuota.
      </p>
      <div v-if="dettaglio.senza_squadriglia.length" class="border-top pt-3 mt-3">
        <strong>Senza squadriglia</strong>
        <ul class="list-unstyled small mb-0">
          <li
            v-for="p in dettaglio.senza_squadriglia"
            :key="p.id"
            class="d-flex align-items-center flex-wrap gap-3 py-1"
          >
            <Avatar
              :nome="`${p.nome} ${p.cognome}`"
              :scheda="p.scheda ? p.id : null"
              dimensione="xs"
              tenue
              aria-hidden="true"
            />
            <RouterLink :to="{ name: 'persona', params: { id: p.id } }">
              {{ p.nome }} {{ p.cognome }}
            </RouterLink>
            <span v-if="insieme" class="fg-2">{{ nomeReparto(p.reparto_id) }}</span>
            <select
              v-if="dettaglio.puo_gestire_squadriglie && squadriglieDi(p.reparto_id).length"
              class="form-control form-control-sm w-auto ms-auto"
              :aria-label="`Metti ${p.nome} ${p.cognome} in una squadriglia`"
              :disabled="inCorso"
              @change="sposta($event, p.id)"
            >
              <option value="">Metti in…</option>
              <option v-for="a in squadriglieDi(p.reparto_id)" :key="a.id" :value="a.id">
                Sq. {{ a.nome }}
              </option>
            </select>
          </li>
        </ul>
      </div>
      <p v-if="dettaglio.puo_gestire_squadriglie" class="small mt-3 mb-0">
        <!-- DEC-410 -->
        <RouterLink :to="{ name: 'riorganizzazione', params: { id: unita.id } }">
          Riorganizza le squadriglie da una data
        </RouterLink>
      </p>
      <p v-if="dettaglio.bozza_squadriglie_pdf" class="small mt-3 mb-0">
        <!-- DEC-411 -->
        <a :href="bozzaSquadrigliePdf(dettaglio.bozza_squadriglie_pdf)" download
          >Bozza delle squadriglie future (PDF)</a
        >
      </p>
      <p v-if="dettaglio.squadriglie_archiviate" class="small mt-3 mb-0">
        <RouterLink :to="{ name: 'squadriglie-archiviate', params: { id: unita.id } }">
          Squadriglie archiviate ({{ dettaglio.squadriglie_archiviate }})
        </RouterLink>
      </p>
    </section>
    <AltaSquadriglia
      v-if="unita.tipo === 'REPARTO'"
      :reparto="unita.id"
      :ragazzi="ragazziDelReparto"
    />
    <!-- Turns and sestiglie (DEC-312): hidden to who may not manage them. -->
    <SestiglieUnita
      v-if="LC.includes(unita.tipo)"
      :key="`sestiglie-${unita.id}`"
      :unita="unita.id"
      :nome="linkataLC ? nomeUnita(unita) : undefined"
    />
    <!-- A linked branco or cerchio: its sestiglie here too, one staff for both (DEC-405). -->
    <SestiglieUnita
      v-if="linkataLC && unita.collegata_a"
      :key="`sestiglie-${unita.collegata_a}`"
      :unita="unita.collegata_a"
      :nome="unita.collegata_nome"
    />
    <TurniUnita
      v-if="CON_TURNI.includes(unita.tipo)"
      :key="`turni-${unita.id}`"
      :unita="unita.id"
      :nome="turniCollegata ? nomeUnita(unita) : undefined"
    />
    <!-- And the linked unit's turns, which may go round the groups of both (DEC-405). -->
    <TurniUnita
      v-if="turniCollegata && unita.collegata_a"
      :key="`turni-${unita.collegata_a}`"
      :unita="unita.collegata_a"
      :nome="unita.collegata_nome"
    />
  </section>
  <div v-else-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
</template>
