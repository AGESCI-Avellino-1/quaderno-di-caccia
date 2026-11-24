<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import {
  api,
  type AvvisoScambio,
  type BabboNatale,
  type CandidatoScambio,
  type ScambioRegali,
} from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'
import { useNomePagina } from '@/composables/useNomePagina'

// One exchange of Babbo Natale segreto (DEC-422), for the staff of its unit and the
// capigruppo. Before the draw the participants are chosen all together (a whole unit or patrol,
// then one by one); after it one is added or withdrawn at a time, and only who is touched is told
// again. Never who gives a gift to whom: only how each participant is told. Online only.
const props = defineProps<{ id: number }>()
const router = useRouter()
const { errore, inCorso, esegui } = useErrore()

const scambio = ref<ScambioRegali | null>(null)
const candidati = ref<CandidatoScambio[]>([])
const contesto = ref<BabboNatale | null>(null)
const scelti = ref<Set<number>>(new Set())
const cerca = ref('')
const messaggio = ref('')
const conferma = ref<'estrai' | 'elimina' | `ritira-${number}` | null>(null)
const daAggiungere = ref<number | null>(null)
const modifica = ref({ nome: '', unita_id: null as number | null, consegna_il: '', luogo: '' })

useNomePagina(() => scambio.value?.nome)

const data = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString('it-IT')
const AVVISI: Record<AvvisoScambio, string> = {
  app: 'Notifica e app',
  email: "Email con invito ad attivare l'account",
  genitori: 'Email ai genitori',
  nessuno: 'Nessuno da avvisare',
}

function mostra(s: ScambioRegali) {
  scambio.value = s
  scelti.value = s.estratto ? new Set() : new Set(s.elenco.map((p) => p.id))
  modifica.value = {
    nome: s.nome,
    unita_id: s.unita_id,
    consegna_il: s.consegna_il,
    luogo: s.luogo,
  }
}

onMounted(async () => {
  const [s, c, ctx] = await Promise.all([
    esegui(() => api.scambio(props.id)),
    esegui(() => api.candidatiScambio(props.id)),
    esegui(() => api.babboNatale()),
  ])
  if (s) mostra(s)
  candidati.value = c ?? []
  contesto.value = ctx ?? null
})

// The units and patrols among the candidates: a whole one is added with one click.
const gruppiCandidati = computed(() => {
  const gruppi = new Map<string, { nome: string; persone: number[] }>()
  for (const c of candidati.value) {
    const chiavi = [
      ...c.unita.map((u) => [`u${u.id}`, u.nome] as const),
      ...(c.squadriglia ? [[`s${c.squadriglia.id}`, `Sq. ${c.squadriglia.nome}`] as const] : []),
    ]
    for (const [chiave, nome] of chiavi) {
      const g = gruppi.get(chiave) ?? { nome, persone: [] }
      g.persone.push(c.id)
      gruppi.set(chiave, g)
    }
  }
  return [...gruppi.values()]
})

const filtrati = computed(() => {
  const testo = cerca.value.trim().toLocaleLowerCase('it')
  return candidati.value.filter(
    (c) => !testo || `${c.nome} ${c.cognome}`.toLocaleLowerCase('it').includes(testo),
  )
})

const nonPartecipanti = computed(() => {
  const dentro = new Set(scambio.value?.elenco.map((p) => p.id) ?? [])
  return candidati.value.filter((c) => !dentro.has(c.id))
})

function aggiungiGruppo(persone: number[]) {
  scelti.value = new Set([...scelti.value, ...persone])
}

function alterna(id: number) {
  const nuovi = new Set(scelti.value)
  if (nuovi.has(id)) nuovi.delete(id)
  else nuovi.add(id)
  scelti.value = nuovi
}

async function agisci(azione: () => Promise<ScambioRegali | undefined>, testo = '') {
  messaggio.value = ''
  conferma.value = null
  const s = await esegui(azione)
  if (s) {
    mostra(s)
    messaggio.value = testo
  }
}

const salvaDati = () =>
  agisci(() => api.modificaScambio(props.id, modifica.value), 'Dati dello scambio salvati.')
const salvaPartecipanti = () =>
  agisci(() => api.partecipantiScambio(props.id, [...scelti.value]), 'Partecipanti salvati.')

async function estrai() {
  messaggio.value = ''
  conferma.value = null
  const esito = await esegui(() => api.estraiScambio(props.id))
  if (!esito) return
  mostra(esito)
  const a = esito.avvisati ?? {}
  const parti = (Object.keys(a) as AvvisoScambio[]).map((k) => `${AVVISI[k]}: ${a[k]}`)
  // After the draw the selection is for resending: start empty.
  scelti.value = new Set()
  messaggio.value = `Estrazione fatta. ${parti.join(' · ')}`
}

async function aggiungi() {
  const persona = daAggiungere.value
  if (persona === null) return
  await agisci(
    () => api.aggiungiAlloScambio(props.id, persona),
    'Aggiunto: sono stati avvisati solo lui/lei e chi ora gli fa il regalo.',
  )
  daAggiungere.value = null
}

const ritira = (persona: number) =>
  agisci(
    () => api.ritiraDalloScambio(props.id, persona),
    'Ritirato: è stato avvisato solo chi gli faceva il regalo.',
  )

async function reinvia() {
  messaggio.value = ''
  const esito = await esegui(() => api.reinviaScambio(props.id, [...scelti.value]))
  if (esito) messaggio.value = `Avviso rimandato a ${esito.reinviati}.`
}

async function elimina() {
  if ((await esegui(() => api.eliminaScambio(props.id))) !== undefined) {
    await router.push({ name: 'babbo-natale' })
  }
}
</script>

<template>
  <section>
    <h1 class="h4">{{ scambio?.nome ?? 'Scambio di regali' }}</h1>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <div v-if="messaggio" class="alert theme-success small" role="status">{{ messaggio }}</div>

    <template v-if="scambio">
      <p class="small fg-2">
        {{ scambio.unita }} · consegna {{ data(scambio.consegna_il) }}
        <template v-if="scambio.luogo">, {{ scambio.luogo }}</template>
        <span v-if="scambio.chiuso" class="badge theme-secondary ms-3">Concluso</span>
        <span v-else-if="scambio.estratto" class="badge theme-success ms-3">Estratto</span>
      </p>

      <form v-if="!scambio.chiuso" class="card card-body mb-5" @submit.prevent="salvaDati">
        <div class="form-field mb-3">
          <label class="form-label small" for="scambio-nome">Nome</label>
          <input
            id="scambio-nome"
            v-model="modifica.nome"
            class="form-control"
            required
            maxlength="120"
          />
        </div>
        <div v-if="!scambio.estratto && contesto" class="form-field mb-3">
          <label class="form-label small" for="scambio-unita">Unità</label>
          <select id="scambio-unita" v-model="modifica.unita_id" class="form-control">
            <option v-if="contesto.puo_tutto_il_gruppo" :value="null">Tutto il gruppo</option>
            <option v-for="u in contesto.unita" :key="u.id" :value="u.id">{{ u.nome }}</option>
          </select>
        </div>
        <div class="form-field mb-3">
          <label class="form-label small" for="scambio-consegna">Giorno della consegna</label>
          <input
            id="scambio-consegna"
            v-model="modifica.consegna_il"
            type="date"
            class="form-control"
            required
          />
        </div>
        <div class="form-field mb-3">
          <label class="form-label small" for="scambio-luogo">Luogo (facoltativo)</label>
          <input id="scambio-luogo" v-model="modifica.luogo" class="form-control" maxlength="200" />
        </div>
        <div>
          <button type="submit" class="btn btn-outline theme-primary btn-sm" :disabled="inCorso">
            Salva
          </button>
        </div>
      </form>

      <!-- Before the draw: the participants, all together. -->
      <template v-if="!scambio.estratto">
        <h2 class="h5">Partecipanti ({{ scelti.size }})</h2>
        <p class="small fg-2">
          Aggiungi un'unità o una squadriglia intera, poi togli o aggiungi le singole persone. Ne
          servono almeno {{ scambio.minimo }}.
        </p>
        <div class="d-flex flex-wrap gap-3 mb-3">
          <button
            v-for="g in gruppiCandidati"
            :key="g.nome"
            type="button"
            class="btn btn-outline theme-secondary btn-sm"
            @click="aggiungiGruppo(g.persone)"
          >
            + {{ g.nome }}
          </button>
          <button
            v-if="scelti.size"
            type="button"
            class="btn btn-outline theme-danger btn-sm"
            @click="scelti = new Set()"
          >
            Togli tutti
          </button>
        </div>
        <input
          v-model="cerca"
          class="form-control mb-3"
          type="search"
          placeholder="Cerca per nome"
          aria-label="Cerca per nome"
        />
        <ul class="list-unstyled mb-3" data-candidati>
          <li v-for="c in filtrati" :key="c.id" class="form-field border-top py-2">
            <input
              :id="`candidato-${c.id}`"
              class="check"
              type="checkbox"
              :checked="scelti.has(c.id)"
              @change="alterna(c.id)"
            />
            <label :for="`candidato-${c.id}`">
              {{ c.cognome }} {{ c.nome }}
              <span class="small fg-2">
                {{ c.unita.map((u) => u.nome).join(', ')
                }}<template v-if="c.squadriglia"> · Sq. {{ c.squadriglia.nome }}</template>
              </span>
            </label>
          </li>
        </ul>
        <div class="d-flex flex-wrap gap-3 mb-5">
          <button
            type="button"
            class="btn btn-outline theme-primary"
            :disabled="inCorso"
            @click="salvaPartecipanti"
          >
            Salva partecipanti
          </button>
        </div>

        <h3 class="h6">Come verranno avvisati</h3>
        <ul class="list-unstyled small mb-5">
          <li v-for="p in scambio.elenco" :key="p.id" class="border-top py-2">
            {{ p.cognome }} {{ p.nome }}
            <span class="fg-2">· {{ AVVISI[p.avviso] }}</span>
            <span v-if="p.avviso === 'nessuno'" class="badge theme-warning ms-3">
              senza account né email
            </span>
          </li>
        </ul>

        <div class="card card-body mb-5">
          <p class="small mb-3">
            L'estrazione forma un unico giro: ognuno fa il regalo a un altro, nessuno a chi lo fa a
            lui, e se possibile fratelli e sorelle non si estraggono tra loro. Ognuno viene avvisato
            subito. Gli abbinamenti non li vedrà nessuno, neanche tu.
          </p>
          <div class="d-flex flex-wrap gap-3">
            <button
              v-if="conferma !== 'estrai'"
              type="button"
              class="btn btn-solid theme-primary"
              :disabled="inCorso || scambio.elenco.length < scambio.minimo"
              @click="conferma = 'estrai'"
            >
              Estrai
            </button>
            <template v-else>
              <button
                type="button"
                class="btn btn-solid theme-primary"
                :disabled="inCorso"
                @click="estrai"
              >
                Conferma l'estrazione
              </button>
              <button
                type="button"
                class="btn btn-outline theme-secondary"
                @click="conferma = null"
              >
                Annulla
              </button>
            </template>
            <button
              v-if="conferma !== 'elimina'"
              type="button"
              class="btn btn-outline theme-danger ms-auto"
              @click="conferma = 'elimina'"
            >
              Elimina lo scambio
            </button>
            <button
              v-else
              type="button"
              class="btn btn-solid theme-danger ms-auto"
              :disabled="inCorso"
              @click="elimina"
            >
              Conferma l'eliminazione
            </button>
          </div>
        </div>
      </template>

      <!-- After the draw: one change at a time, and resending. -->
      <template v-else>
        <h2 class="h5">Partecipanti ({{ scambio.elenco.length }})</h2>
        <p v-if="!scambio.chiuso" class="small fg-2">
          Seleziona chi deve ricevere di nuovo l'avviso. Se qualcuno si ritira, chi gli faceva il
          regalo lo farà a chi lo riceveva da lui; gli altri non cambiano.
        </p>
        <ul class="list-unstyled mb-3" data-partecipanti>
          <li
            v-for="p in scambio.elenco"
            :key="p.id"
            class="d-flex align-items-center flex-wrap gap-3 border-top py-2"
          >
            <div v-if="!scambio.chiuso" class="form-field mb-0">
              <input
                :id="`reinvia-${p.id}`"
                class="check"
                type="checkbox"
                :checked="scelti.has(p.id)"
                @change="alterna(p.id)"
              />
              <label :for="`reinvia-${p.id}`">{{ p.cognome }} {{ p.nome }}</label>
            </div>
            <span v-else>{{ p.cognome }} {{ p.nome }}</span>
            <span class="small fg-2">{{ AVVISI[p.avviso] }}</span>
            <template v-if="!scambio.chiuso">
              <button
                v-if="conferma !== `ritira-${p.id}`"
                type="button"
                class="btn btn-outline theme-danger btn-sm ms-auto"
                :disabled="scambio.elenco.length <= scambio.minimo"
                @click="conferma = `ritira-${p.id}`"
              >
                Ritira
              </button>
              <button
                v-else
                type="button"
                class="btn btn-solid theme-danger btn-sm ms-auto"
                :disabled="inCorso"
                @click="ritira(p.id)"
              >
                Conferma il ritiro
              </button>
            </template>
          </li>
        </ul>
        <template v-if="!scambio.chiuso">
          <div class="d-flex flex-wrap gap-3 mb-5">
            <button
              type="button"
              class="btn btn-solid theme-primary btn-sm"
              :disabled="inCorso || !scelti.size"
              @click="reinvia"
            >
              Rimanda l'avviso ({{ scelti.size }})
            </button>
            <button
              v-if="scelti.size"
              type="button"
              class="btn btn-outline theme-secondary btn-sm"
              @click="scelti = new Set()"
            >
              Deseleziona
            </button>
          </div>
          <h3 class="h6">Aggiungi un partecipante</h3>
          <form class="d-flex flex-wrap gap-3 mb-5" @submit.prevent="aggiungi">
            <select v-model="daAggiungere" class="form-control" aria-label="Chi aggiungere">
              <option :value="null" disabled>Scegli chi aggiungere</option>
              <option v-for="c in nonPartecipanti" :key="c.id" :value="c.id">
                {{ c.cognome }} {{ c.nome }}
              </option>
            </select>
            <button
              type="submit"
              class="btn btn-outline theme-primary"
              :disabled="inCorso || daAggiungere === null"
            >
              Aggiungi
            </button>
          </form>
        </template>
      </template>
    </template>
  </section>
</template>
