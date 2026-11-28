<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { api, type AltaSquadriglia, type MembroAlta } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The Alta Squadriglia of a reparto, one for two linked reparti (DEC-439): who is in, since
// when; the antechamber, about to enter; who was in. The reparto staff puts ragazzi/e in the
// antechamber and lets them in, from the antechamber or directly, also with a day of past
// years; taking someone off closes their period, which stays. Its events invite who is in,
// the antechamber only when chosen. It has a name the staff corrects; closed, it stays for the
// history and a new one starts empty, with copies of the old one's entries of the book
// (DEC-440). Online only.
const props = defineProps<{ reparto: number }>()
const { errore, inCorso, esegui } = useErrore()
const alta = ref<AltaSquadriglia | null>(null)
const scelti = ref<number[]>([])
const oggi = () => new Date().toLocaleDateString('sv-SE')
const giorno = ref(oggi())
const aperto = ref(false)
// The name being corrected, the closing to confirm, the new one being created.
const nuovoNome = ref<string | null>(null)
const chiusura = ref(false)
const nuova = ref({ nome: '', copia: [] as number[] })

watch(
  () => props.reparto,
  async (id) => {
    try {
      alta.value = await api.altaSquadriglia(id)
    } catch {
      alta.value = null
    }
  },
  { immediate: true },
)

const data = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString('it-IT')
const nome = (m: MembroAlta) => `${m.cognome} ${m.nome}`
// Who may be chosen: not in yet (in the antechamber or not at all).
const sceglibili = computed(() =>
  alta.value ? [...alta.value.anticamera, ...alta.value.candidati] : [],
)
const daCandidati = computed(() => new Set(alta.value?.candidati.map((m) => m.persona_id) ?? []))

async function aggiorna(azione: () => Promise<AltaSquadriglia>) {
  const dati = await esegui(azione)
  if (!dati) return
  alta.value = dati
  scelti.value = []
  aperto.value = false
  nuovoNome.value = null
  chiusura.value = false
  nuova.value = { nome: '', copia: [] }
}

const rinomina = () => aggiorna(() => api.rinominaAlta(props.reparto, nuovoNome.value ?? ''))
const chiudi = () => aggiorna(() => api.chiudiAlta(props.reparto))
const crea = () => aggiorna(() => api.creaAlta(props.reparto, nuova.value.nome, nuova.value.copia))

const inAnticamera = () =>
  aggiorna(() =>
    api.mettiInAnticamera(
      props.reparto,
      scelti.value.filter((id) => daCandidati.value.has(id)),
    ),
  )
const entrano = () =>
  aggiorna(() => api.faiEntrareInAlta(props.reparto, scelti.value, giorno.value))
const entraOggi = (m: MembroAlta) =>
  aggiorna(() => api.faiEntrareInAlta(props.reparto, [m.persona_id], oggi()))
const rimetti = (m: MembroAlta) => aggiorna(() => api.rimettiInAnticamera(props.reparto, m.id))
const togli = (m: MembroAlta) => aggiorna(() => api.togliDallAlta(props.reparto, m.id))
</script>

<template>
  <section v-if="alta" class="card card-body mb-5" data-alta>
    <h2 class="h5 mb-1">{{ alta.alta?.titolo ?? 'Alta Squadriglia' }}</h2>
    <p v-if="alta.insieme_a" class="small mb-1" data-insieme>
      Una sola con il {{ alta.insieme_a }}, collegato.
    </p>
    <p class="form-text">
      Gli eventi e le riunioni di Alta Squadriglia invitano chi è entrato; l'anticamera solo se lo
      scegli. Chi è in anticamera non legge le cerimonie dell'Alta Squadriglia finché non entra.
      <RouterLink
        v-if="alta.cerimonia"
        :to="{ name: 'voce-libro', params: { id: alta.cerimonia } }"
      >
        La cerimonia d'ingresso
      </RouterLink>
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>

    <template v-if="!alta.alta">
      <p class="small fg-2" data-senza-alta>Il reparto non ha un'Alta Squadriglia aperta.</p>
      <form v-if="alta.puo_scegliere" class="card card-body" data-nuova-alta @submit.prevent="crea">
        <div class="mb-3">
          <label class="form-label small mb-0" for="alta-nuova-nome">Nome</label>
          <input
            id="alta-nuova-nome"
            v-model="nuova.nome"
            class="form-control"
            maxlength="120"
            required
          />
        </div>
        <fieldset v-if="alta.da_copiare?.length" class="mb-3">
          <legend class="form-label small mb-0">
            Copia dalla vecchia le voci del libro (testo, condizioni e allegati, senza chi le ha
            vissute)
          </legend>
          <div class="d-flex flex-wrap gap-5">
            <div v-for="v in alta.da_copiare" :key="v.id" class="form-field mb-0">
              <input
                :id="`alta-copia-${v.id}`"
                v-model="nuova.copia"
                type="checkbox"
                class="check"
                :value="v.id"
              />
              <label :for="`alta-copia-${v.id}`">{{ v.titolo }}</label>
            </div>
          </div>
        </fieldset>
        <div>
          <button class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Crea l'Alta Squadriglia
          </button>
        </div>
      </form>
    </template>

    <template v-else>
      <div v-if="alta.puo_scegliere" class="d-flex flex-wrap gap-3 align-items-center mb-3">
        <form
          v-if="nuovoNome !== null"
          class="d-flex flex-wrap gap-3 align-items-center"
          data-rinomina
          @submit.prevent="rinomina"
        >
          <label class="visually-hidden" for="alta-nome">Nome</label>
          <input
            id="alta-nome"
            v-model="nuovoNome"
            class="form-control form-control-sm w-auto"
            maxlength="120"
            required
          />
          <button class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">Salva</button>
          <button type="button" class="btn btn-sm btn-link" @click="nuovoNome = null">
            Annulla
          </button>
        </form>
        <button
          v-else
          type="button"
          class="btn btn-sm btn-link"
          @click="nuovoNome = alta.alta.nome"
        >
          Cambia nome
        </button>
        <button v-if="!chiusura" type="button" class="btn btn-sm btn-link" @click="chiusura = true">
          Chiudi l'Alta Squadriglia
        </button>
        <span v-else class="d-flex flex-wrap gap-3 align-items-center" data-chiusura>
          <span class="small"
            >Chi è dentro esce e resta nello storico; l'anticamera si svuota.</span
          >
          <button
            type="button"
            class="btn btn-sm btn-solid theme-danger"
            :disabled="inCorso"
            @click="chiudi"
          >
            Chiudila
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="chiusura = false">
            Annulla
          </button>
        </span>
      </div>

      <h3 class="h6 mt-3">Dentro</h3>
      <p v-if="!alta.entrati.length" class="small fg-2">Nessuno, per ora.</p>
      <ul v-else class="list-group mb-3" data-entrati>
        <li
          v-for="m in alta.entrati"
          :key="m.id"
          class="list-group-item d-flex flex-wrap gap-3 align-items-center"
        >
          <span class="flex-grow-1">
            {{ nome(m) }} <span class="small fg-2">{{ m.unita }}</span>
          </span>
          <span class="small">dal {{ data(m.dal!) }}</span>
          <template v-if="alta.puo_scegliere">
            <button
              type="button"
              class="btn btn-sm btn-link"
              :disabled="inCorso"
              :aria-label="`Rimetti ${nome(m)} in anticamera`"
              @click="rimetti(m)"
            >
              In anticamera
            </button>
            <button
              type="button"
              class="btn btn-sm btn-link"
              :disabled="inCorso"
              :aria-label="`Togli ${nome(m)} dall'Alta Squadriglia`"
              @click="togli(m)"
            >
              Togli
            </button>
          </template>
        </li>
      </ul>

      <h3 class="h6 mt-3">Anticamera</h3>
      <p v-if="!alta.anticamera.length" class="small fg-2">Nessuno, per ora.</p>
      <ul v-else class="list-group mb-3" data-anticamera>
        <li
          v-for="m in alta.anticamera"
          :key="m.id"
          class="list-group-item d-flex flex-wrap gap-3 align-items-center"
        >
          <span class="flex-grow-1">
            {{ nome(m) }} <span class="small fg-2">{{ m.unita }}</span>
          </span>
          <span v-if="m.in_anticamera_dal" class="small">dal {{ data(m.in_anticamera_dal) }}</span>
          <template v-if="alta.puo_scegliere">
            <button
              type="button"
              class="btn btn-sm btn-link"
              :disabled="inCorso"
              :aria-label="`Fai entrare oggi ${nome(m)}`"
              @click="entraOggi(m)"
            >
              Entra oggi
            </button>
            <button
              type="button"
              class="btn btn-sm btn-link"
              :disabled="inCorso"
              :aria-label="`Togli ${nome(m)} dall'anticamera`"
              @click="togli(m)"
            >
              Togli
            </button>
          </template>
        </li>
      </ul>

      <template v-if="alta.puo_scegliere && sceglibili.length">
        <button
          v-if="!aperto"
          type="button"
          class="btn btn-sm btn-outline theme-primary align-self-start"
          @click="aperto = true"
        >
          Aggiungi
        </button>
        <form v-else class="card card-body" data-aggiungi @submit.prevent="entrano">
          <p class="small fg-2">
            Metti in anticamera chi sta per entrare, oppure fallo entrare con il suo giorno, anche
            degli anni passati se c'era già prima dell'app.
          </p>
          <div class="d-flex flex-wrap gap-5 mb-3">
            <div v-for="m in sceglibili" :key="m.persona_id" class="form-field mb-0">
              <input
                :id="`alta-${m.persona_id}`"
                v-model="scelti"
                type="checkbox"
                class="check"
                :value="m.persona_id"
              />
              <label :for="`alta-${m.persona_id}`">
                {{ nome(m) }}
                <span v-if="!daCandidati.has(m.persona_id)" class="small fg-2"
                  >(in anticamera)</span
                >
              </label>
            </div>
          </div>
          <div class="mb-3">
            <label class="form-label small mb-0" for="alta-giorno">Entra il giorno</label>
            <input
              id="alta-giorno"
              v-model="giorno"
              type="date"
              class="form-control w-auto"
              :max="oggi()"
              required
            />
          </div>
          <div class="d-flex flex-wrap gap-3">
            <button
              class="btn btn-sm btn-solid theme-primary"
              :disabled="inCorso || !scelti.length"
            >
              Fai entrare
            </button>
            <button
              type="button"
              class="btn btn-sm btn-outline theme-primary"
              :disabled="inCorso || !scelti.some((id) => daCandidati.has(id))"
              @click="inAnticamera"
            >
              Metti in anticamera
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="aperto = false">
              Annulla
            </button>
          </div>
        </form>
      </template>

      <details v-if="alta.usciti.length" class="mt-5" data-usciti>
        <summary class="small">Usciti ({{ alta.usciti.length }})</summary>
        <ul class="small mt-3 mb-0">
          <li v-for="m in alta.usciti" :key="m.id">
            {{ nome(m) }}: dal {{ data(m.dal!) }} al {{ data(m.al!) }}
          </li>
        </ul>
      </details>
    </template>

    <details v-if="alta.chiuse?.length" class="mt-5" data-chiuse>
      <summary class="small">Alte Squadriglie chiuse ({{ alta.chiuse.length }})</summary>
      <div v-for="c in alta.chiuse" :key="c.id" class="small mt-3">
        <strong>{{ c.titolo }}</strong>, dal {{ data(c.aperta_il) }} al {{ data(c.chiusa_il) }}
        <ul class="mb-0">
          <li v-for="m in c.membri" :key="m.id">
            {{ nome(m) }}: dal {{ data(m.dal!) }} al {{ data(m.al!) }}
          </li>
        </ul>
      </div>
    </details>
  </section>
</template>
