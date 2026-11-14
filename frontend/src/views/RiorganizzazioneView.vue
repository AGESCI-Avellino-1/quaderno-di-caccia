<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

import { api, type AnimaleSquadriglia, type BozzaSquadriglie } from '@/api/qdc'
import ImmagineAnimale from '@/components/ImmagineAnimale.vue'
import { useErrore } from '@/composables/useErrore'

// The future patrols of a reparto, or of two linked ones (DEC-410): the staff prepares them
// while the current ones stay in force, and applies them by hand from their first day; a
// mistake is undone while nobody changed patrols since. The future CSQ and VCSQ read it when
// the staff shows it to them. Online only.
const props = defineProps<{ unita?: number; bozza?: number }>()
const { errore, inCorso, esegui } = useErrore()
const aperta = ref<BozzaSquadriglie | null>(null)
const applicata = ref<BozzaSquadriglie | null>(null)
const caricata = ref(false)
const esito = ref('')
const oggi = () => new Date().toLocaleDateString('sv')
const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')

async function carica() {
  if (props.bozza) {
    aperta.value = (await esegui(() => api.bozzaSquadriglie(props.bozza!))) ?? null
  } else if (props.unita) {
    const lette = await esegui(() => api.bozzeSquadriglie(props.unita!))
    aperta.value = lette?.aperta ?? null
    applicata.value = lette?.applicata ?? null
  }
  caricata.value = true
}
watch(() => [props.unita, props.bozza], carica, { immediate: true })

const gestisce = computed(() => !!aperta.value?.puo_gestire)
const insieme = computed(() => (aperta.value?.reparti.length ?? 0) > 1)
const nomi = computed(() => {
  const tutti = new Map<number, string>()
  for (const s of aperta.value?.squadriglie ?? []) {
    for (const m of s.membri) tutti.set(m.id, `${m.nome} ${m.cognome}`)
  }
  return tutti
})

function aggiorna(fatta: BozzaSquadriglie | undefined) {
  if (fatta) aperta.value = fatta
}

// --- A new draft ----------------------------------------------------------------------
const dataNuova = ref(oggi())
async function prepara() {
  aggiorna(await esegui(() => api.creaBozzaSquadriglie(props.unita!, dataNuova.value)))
}

// --- Settings ----------------------------------------------------------------------------
const impostazioni = reactive({ data_inizio: '', visibile_ai_capi_squadriglia: false })
watch(
  aperta,
  (b) => {
    if (b) {
      impostazioni.data_inizio = b.data_inizio
      impostazioni.visibile_ai_capi_squadriglia = b.visibile_ai_capi_squadriglia
    }
  },
  { immediate: true },
)
async function salvaImpostazioni() {
  aggiorna(await esegui(() => api.impostaBozza(aperta.value!.id, { ...impostazioni })))
}

// --- Patrols and moves -----------------------------------------------------------------
async function sposta(persona: number, evento: Event) {
  const scelta = evento.target as HTMLSelectElement
  const valore = scelta.value
  scelta.value = ''
  if (!valore) return
  const posto = valore === 'nessuna' ? null : Number(valore)
  aggiorna(await esegui(() => api.spostaInBozza(aperta.value!.id, persona, posto)))
}

// Without a patrol: who stays in the reparto and who goes to R/S, shown apart and nothing
// more: the passage itself is in the Passaggi (DEC-411).
const senzaSquadriglia = computed(() => {
  const senza = aperta.value?.senza_squadriglia ?? []
  return [
    {
      titolo: 'Senza squadriglia, restano nel reparto',
      persone: senza.filter((p) => !p.passa_in_rs),
    },
    { titolo: 'Passano in R/S', persone: senza.filter((p) => p.passa_in_rs) },
  ].filter((g) => g.persone.length)
})
async function segnaRs(persona: number, passa: boolean) {
  aggiorna(await esegui(() => api.segnaRsInBozza(aperta.value!.id, persona, passa)))
}

// A ragazzo/a stays among the reparti of the draft; the server checks the sexes.
const posti = computed(() => aperta.value?.squadriglie ?? [])

async function guide(
  posto: BozzaSquadriglie['squadriglie'][number],
  ruolo: 'capo' | 'vice',
  evento: Event,
) {
  const valore = (evento.target as HTMLSelectElement).value
  const dati = { capo_id: posto.capo_id, vice_id: posto.vice_id }
  dati[ruolo === 'capo' ? 'capo_id' : 'vice_id'] = valore ? Number(valore) : null
  aggiorna(await esegui(() => api.guideInBozza(aperta.value!.id, posto.id, dati)))
}

async function togli(posto: number) {
  aggiorna(await esegui(() => api.togliSquadrigliaDaBozza(aperta.value!.id, posto)))
}

const nuova = reactive({ aperta: false, unita: 0, animale: null as number | null, sesso: 'F' })
const animali = ref<AnimaleSquadriglia[]>([])
async function apriNuova() {
  nuova.aperta = true
  nuova.unita = aperta.value!.reparti[0]!.id
  if (!animali.value.length) {
    animali.value = ((await esegui(() => api.animali()))?.animali ?? []).filter((a) => a.attivo)
  }
}
const sessoFisso = computed(() => {
  const reparto = aperta.value?.reparti.find((r) => r.id === nuova.unita)
  return reparto && reparto.composizione !== 'X' ? reparto.composizione : null
})
async function aggiungi() {
  const fatta = await esegui(() =>
    api.nuovaSquadrigliaInBozza(aperta.value!.id, {
      unita_id: nuova.unita,
      animale_id: nuova.animale,
      sesso: sessoFisso.value ?? nuova.sesso,
    }),
  )
  if (fatta) {
    aggiorna(fatta)
    Object.assign(nuova, { aperta: false, animale: null })
  }
}

// --- Applying, discarding, undoing ---------------------------------------------------
const conferma = ref<'applica' | 'scarta' | 'annulla' | null>(null)
async function applica() {
  conferma.value = null
  const fatta = await esegui(() => api.applicaBozza(aperta.value!.id))
  if (fatta) {
    esito.value = 'Bozza applicata: le squadriglie sono cambiate.'
    await carica()
  }
}
async function scarta() {
  conferma.value = null
  if ((await esegui(() => api.scartaBozza(aperta.value!.id))) !== undefined) {
    esito.value = 'Bozza scartata.'
    await carica()
  }
}
async function annulla() {
  conferma.value = null
  const fatta = await esegui(() => api.annullaBozza(applicata.value!.id))
  if (fatta) {
    esito.value =
      'Applicazione annullata: le squadriglie sono tornate come prima, la bozza è di nuovo da applicare.'
    await carica()
  }
}
</script>

<template>
  <section>
    <h1 class="h4">
      {{ props.bozza ? 'Le squadriglie future' : 'Riorganizzazione delle squadriglie' }}
    </h1>
    <p v-if="!props.bozza" class="small fg-2">
      Prepara come saranno le squadriglie da una data, per esempio dall'apertura: squadriglie nuove,
      spostamenti, capi e vice. Fino a quando non la applichi valgono le squadriglie di oggi. Le
      squadriglie che restano vuote vengono archiviate.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>

    <!-- The last one applied, while it may be undone. -->
    <div v-if="applicata && !aperta" class="card card-body mb-5">
      <p class="mb-3">
        Bozza applicata dal {{ data(applicata.data_inizio)
        }}<template v-if="applicata.applicata_da"> da {{ applicata.applicata_da }}</template
        >. Se è stato un errore puoi annullarla: tornano le squadriglie, i membri e i capi di prima.
      </p>
      <div class="d-flex gap-3">
        <button
          v-if="conferma !== 'annulla'"
          type="button"
          class="btn btn-sm btn-outline theme-danger"
          @click="conferma = 'annulla'"
        >
          Annulla l'applicazione…
        </button>
        <template v-else>
          <button
            type="button"
            class="btn btn-sm btn-solid theme-danger"
            :disabled="inCorso"
            @click="annulla"
          >
            Sì, annulla
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="conferma = null">No</button>
        </template>
      </div>
    </div>

    <form
      v-if="caricata && !aperta && props.unita"
      class="card card-body mb-5 d-flex flex-row flex-wrap align-items-end gap-3"
      @submit.prevent="prepara"
    >
      <div>
        <label class="form-label small" for="bozza-dal">Le nuove squadriglie valgono dal</label>
        <input
          id="bozza-dal"
          v-model="dataNuova"
          type="date"
          class="form-control form-control-sm"
          required
        />
      </div>
      <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
        Prepara la bozza
      </button>
    </form>

    <template v-if="aperta">
      <p v-if="!gestisce" class="small fg-2">
        Le squadriglie decise dallo staff, dal {{ data(aperta.data_inizio) }}. Fino a quel giorno
        valgono quelle di oggi.
      </p>
      <form v-if="gestisce" class="card card-body mb-5" @submit.prevent="salvaImpostazioni">
        <div class="d-flex flex-wrap align-items-end gap-5">
          <div>
            <label class="form-label small" for="bozza-data">Valgono dal</label>
            <input
              id="bozza-data"
              v-model="impostazioni.data_inizio"
              type="date"
              class="form-control form-control-sm"
              required
            />
          </div>
          <div class="form-field mb-0 d-flex align-items-center gap-1">
            <div class="switch">
              <input
                id="bozza-visibile"
                v-model="impostazioni.visibile_ai_capi_squadriglia"
                type="checkbox"
                role="switch"
              />
            </div>
            <label for="bozza-visibile" class="small">Mostra ai futuri capi squadriglia</label>
          </div>
          <button type="submit" class="btn btn-sm btn-outline theme-primary" :disabled="inCorso">
            Salva
          </button>
        </div>
      </form>

      <div v-if="aperta.differenze.length" class="alert theme-warning small" role="status">
        <div>
          <strong>Da controllare</strong>
          <ul class="mb-0 ps-5">
            <li v-for="(d, i) in aperta.differenze" :key="i">{{ d }}</li>
          </ul>
        </div>
      </div>

      <section v-for="s in posti" :key="s.id" class="card card-body mb-5">
        <div class="d-flex align-items-center flex-wrap gap-3 mb-3">
          <ImmagineAnimale :animale="s.animale" />
          <h2 class="h6 mb-0">Sq. {{ s.nome }}</h2>
          <span class="fg-2 small">{{ s.sesso === 'F' ? 'femminile' : 'maschile' }}</span>
          <span v-if="s.nuova" class="badge theme-info">nuova</span>
          <span v-if="insieme" class="badge theme-secondary">{{ s.unita_nome }}</span>
          <span v-if="!s.membri.length && !s.nuova" class="badge theme-warning"
            >sarà archiviata</span
          >
          <button
            v-if="gestisce && s.nuova"
            type="button"
            class="btn btn-link btn-sm p-0 ms-auto"
            :disabled="inCorso"
            @click="togli(s.id)"
          >
            togli
          </button>
        </div>
        <ul class="list-unstyled small mb-3">
          <li
            v-for="m in s.membri"
            :key="m.id"
            class="d-flex align-items-center flex-wrap gap-3 py-1"
          >
            <span>{{ m.nome }} {{ m.cognome }}</span>
            <span v-if="s.capo_id === m.id" class="badge theme-primary">capo squadriglia</span>
            <span v-if="s.vice_id === m.id" class="badge theme-secondary">vice</span>
            <select
              v-if="gestisce"
              class="form-control form-control-sm w-auto ms-auto"
              :aria-label="`Sposta ${m.nome} ${m.cognome}`"
              :disabled="inCorso"
              @change="sposta(m.id, $event)"
            >
              <option value="">Sposta in…</option>
              <option v-for="a in posti.filter((p) => p.id !== s.id)" :key="a.id" :value="a.id">
                Sq. {{ a.nome }}<template v-if="insieme"> ({{ a.unita_nome }})</template>
              </option>
              <option value="nessuna">Nessuna squadriglia</option>
            </select>
          </li>
          <li v-if="!s.membri.length" class="fg-2">Nessun membro.</li>
        </ul>
        <div v-if="gestisce && s.membri.length" class="d-flex flex-wrap gap-3">
          <select
            class="form-control form-control-sm w-auto"
            :aria-label="`Capo squadriglia di Sq. ${s.nome}`"
            :value="s.capo_id ?? ''"
            :disabled="inCorso"
            @change="guide(s, 'capo', $event)"
          >
            <option value="">Capo squadriglia…</option>
            <option v-for="m in s.membri" :key="m.id" :value="m.id">
              {{ m.nome }} {{ m.cognome }}
            </option>
          </select>
          <select
            class="form-control form-control-sm w-auto"
            :aria-label="`Vice capo squadriglia di Sq. ${s.nome}`"
            :value="s.vice_id ?? ''"
            :disabled="inCorso"
            @change="guide(s, 'vice', $event)"
          >
            <option value="">Vice capo squadriglia…</option>
            <option v-for="m in s.membri" :key="m.id" :value="m.id">
              {{ m.nome }} {{ m.cognome }}
            </option>
          </select>
        </div>
        <p v-else-if="s.capo_id || s.vice_id" class="small mb-0">
          <template v-if="s.capo_id">Capo squadriglia: {{ nomi.get(s.capo_id) }}</template>
          <template v-if="s.vice_id"> · Vice: {{ nomi.get(s.vice_id) }}</template>
        </p>
      </section>

      <!-- Who stays in the reparto without a patrol, and who goes to R/S (DEC-411). -->
      <section v-for="gruppo in senzaSquadriglia" :key="gruppo.titolo" class="card card-body mb-5">
        <h2 class="h6">{{ gruppo.titolo }}</h2>
        <ul class="list-unstyled small mb-0">
          <li
            v-for="p in gruppo.persone"
            :key="p.id"
            class="d-flex align-items-center flex-wrap gap-3 py-1"
          >
            <span>{{ p.nome }} {{ p.cognome }}</span>
            <div v-if="gestisce" class="form-field mb-0 d-flex align-items-center gap-1">
              <input
                :id="`rs-${p.id}`"
                type="checkbox"
                class="check"
                :checked="p.passa_in_rs"
                :disabled="inCorso"
                @change="segnaRs(p.id, ($event.target as HTMLInputElement).checked)"
              />
              <label :for="`rs-${p.id}`">passa in R/S</label>
            </div>
            <select
              v-if="gestisce"
              class="form-control form-control-sm w-auto ms-auto"
              :aria-label="`Metti ${p.nome} ${p.cognome} in una squadriglia`"
              :disabled="inCorso"
              @change="sposta(p.id, $event)"
            >
              <option value="">Metti in…</option>
              <option v-for="a in posti" :key="a.id" :value="a.id">
                Sq. {{ a.nome }}<template v-if="insieme"> ({{ a.unita_nome }})</template>
              </option>
            </select>
          </li>
        </ul>
      </section>

      <template v-if="gestisce">
        <button
          v-if="!nuova.aperta"
          type="button"
          class="btn btn-sm btn-outline theme-primary mb-5"
          @click="apriNuova"
        >
          Nuova squadriglia nella bozza
        </button>
        <form v-else class="card card-body mb-5" @submit.prevent="aggiungi">
          <div class="d-flex flex-wrap gap-3">
            <select
              v-if="insieme"
              v-model="nuova.unita"
              class="form-control form-control-sm w-auto"
              aria-label="Reparto della squadriglia"
            >
              <option v-for="r in aperta.reparti" :key="r.id" :value="r.id">{{ r.nome }}</option>
            </select>
            <select
              v-model="nuova.animale"
              class="form-control form-control-sm w-auto"
              aria-label="Animale"
            >
              <option :value="null">Senza animale: lo sceglie il capo squadriglia</option>
              <option v-for="a in animali" :key="a.id" :value="a.id">{{ a.plurale }}</option>
            </select>
            <select
              v-if="!sessoFisso"
              v-model="nuova.sesso"
              class="form-control form-control-sm w-auto"
              aria-label="Maschile o femminile"
            >
              <option value="F">Femminile</option>
              <option value="M">Maschile</option>
            </select>
            <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
              Aggiungi
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="nuova.aperta = false">
              Annulla
            </button>
          </div>
        </form>

        <div class="card card-body mb-5">
          <p class="small mb-3">
            <template v-if="aperta.si_applica">
              Applicandola, gli spostamenti valgono dal {{ data(aperta.data_inizio) }}, i capi e
              vice di prima lasciano l'incarico e le squadriglie vuote vengono archiviate.
            </template>
            <template v-else>Si applica dal {{ data(aperta.data_inizio) }}.</template>
          </p>
          <div class="d-flex flex-wrap gap-3">
            <button
              v-if="conferma !== 'applica'"
              type="button"
              class="btn btn-sm btn-solid theme-primary"
              :disabled="inCorso || !aperta.si_applica"
              @click="conferma = 'applica'"
            >
              Applica la bozza…
            </button>
            <template v-else>
              <button
                type="button"
                class="btn btn-sm btn-solid theme-primary"
                :disabled="inCorso"
                @click="applica"
              >
                Sì, applica
              </button>
              <button type="button" class="btn btn-sm btn-link" @click="conferma = null">No</button>
            </template>
            <button
              v-if="conferma !== 'scarta'"
              type="button"
              class="btn btn-sm btn-outline theme-danger ms-auto"
              @click="conferma = 'scarta'"
            >
              Scarta la bozza…
            </button>
            <template v-else>
              <button
                type="button"
                class="btn btn-sm btn-solid theme-danger ms-auto"
                :disabled="inCorso"
                @click="scarta"
              >
                Sì, scarta
              </button>
              <button type="button" class="btn btn-sm btn-link" @click="conferma = null">No</button>
            </template>
          </div>
        </div>
      </template>
    </template>
  </section>
</template>
