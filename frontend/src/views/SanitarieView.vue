<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import {
  ANAMNESI,
  api,
  percorsoSanitarie,
  TIPI_ALLERGIA,
  type Allergia,
  type Farmaco,
  type GenitoreScheda,
  type Sanitarie,
  type SanitarieIn,
  type TipoAllergia,
} from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'
import { useNomePersona } from '@/composables/useNomePagina'
import { leggiConCache, salvaInCache } from '@/offline/cache'
import { scrivi } from '@/offline/outbox'

// Parents, the adult member, or a capo transcribing the signed paper form (DEC-50, DEC-55):
// the group's form (DEC-289), section by section as on paper, and the other data
// (DEC-48, DEC-49).
const props = defineProps<{ id: number }>()
const router = useRouter()
const { errore, inCorso, esegui } = useErrore()

const nome = ref('')
useNomePersona(() => props.id, nome)
const caricata = ref(false)
const esito = ref<string | null>(null)
const modulo = reactive<SanitarieIn>({
  nessuna_allergia: false,
  nessun_farmaco: false,
  esigenze_alimentari: '',
  allergie: [],
  farmaci: [],
  tessera_sanitaria: '',
  reperibilita_nome: '',
  reperibilita_telefono: '',
  antitetanica: null,
  note_sanitarie: '',
  gruppo_sanguigno: '',
  medico_curante: '',
  altre_vaccinazioni: '',
  medico_telefono: '',
  patologie: null,
  patologie_dettaglio: '',
  interventi: null,
  interventi_dettaglio: '',
  disturbi_sonno: null,
  disturbi_sonno_dettaglio: '',
  occhiali: null,
  occhiali_dettaglio: '',
  allergie_farmaci: null,
  allergie_alimentari: null,
  intolleranze_alimentari: null,
  allergie_insetti: null,
  allergie_ambientali: null,
  farmaco_salvavita: null,
  farmaci_da_banco: null,
  antitetanica_data: null,
})
const CAMPI_TESTO = [
  'tessera_sanitaria',
  'reperibilita_nome',
  'reperibilita_telefono',
  'note_sanitarie',
  'gruppo_sanguigno',
  'medico_curante',
  'altre_vaccinazioni',
  'medico_telefono',
  'patologie_dettaglio',
  'interventi_dettaglio',
  'disturbi_sonno_dettaglio',
  'occhiali_dettaglio',
] as const
const CAMPI_SI_NO = [
  'patologie',
  'interventi',
  'disturbi_sonno',
  'occhiali',
  'allergie_farmaci',
  'allergie_alimentari',
  'intolleranze_alimentari',
  'allergie_insetti',
  'allergie_ambientali',
  'farmaco_salvavita',
  'farmaci_da_banco',
] as const
// The parents' phones: the landline is saved on the parent, apart (DEC-289).
const genitori = ref<GenitoreScheda[]>([])
const fissi = reactive<Record<number, string>>({})

onMounted(async () => {
  const [persona, sanitarie] = await Promise.all([
    esegui(() => leggiConCache(`persona:${props.id}`, () => api.persona(props.id))),
    esegui(() => leggiConCache(`sanitarie:${props.id}`, () => api.sanitarie(props.id))),
  ])
  if (persona) nome.value = `${persona.dati.nome} ${persona.dati.cognome}`
  if (sanitarie) {
    if (!sanitarie.dati.puo_modificare) {
      errore.value = 'Puoi leggere queste informazioni ma non modificarle.'
      return
    }
    modulo.nessuna_allergia = sanitarie.dati.nessuna_allergia
    modulo.nessun_farmaco = sanitarie.dati.nessun_farmaco
    // Copies saved before this field existed do not have it.
    modulo.esigenze_alimentari = sanitarie.dati.esigenze_alimentari ?? ''
    modulo.allergie = sanitarie.dati.allergie.map((a) => ({ ...a }))
    modulo.farmaci = sanitarie.dati.farmaci.map((f) => ({ ...f }))
    for (const campo of CAMPI_TESTO) modulo[campo] = sanitarie.dati[campo] ?? ''
    modulo.antitetanica = sanitarie.dati.antitetanica ?? null
    for (const campo of CAMPI_SI_NO) modulo[campo] = sanitarie.dati[campo] ?? null
    modulo.antitetanica_data = sanitarie.dati.antitetanica_data ?? null
    genitori.value = sanitarie.dati.genitori ?? []
    for (const g of genitori.value) fissi[g.id] = g.telefono_fisso
    caricata.value = true
  }
})

const delTipo = (tipo: TipoAllergia) => modulo.allergie.filter((a) => a.tipo === tipo)

function rispondi(campo: (typeof TIPI_ALLERGIA)[number]['campo'], tipo: TipoAllergia, si: boolean) {
  modulo[campo] = si
  if (!si) modulo.allergie = modulo.allergie.filter((a) => a.tipo !== tipo)
  else if (!delTipo(tipo).length) aggiungiAllergia(tipo)
  modulo.nessuna_allergia = TIPI_ALLERGIA.every((t) => modulo[t.campo] === false)
}

function aggiungiAllergia(tipo: TipoAllergia) {
  modulo.nessuna_allergia = false
  modulo.allergie.push({
    tipo,
    sostanza: '',
    gravita: 'MODERATA',
    reazione: '',
    cosa_fare: '',
  } satisfies Allergia)
}

function aggiungiFarmaco() {
  modulo.nessun_farmaco = false
  modulo.farmaci.push({
    nome: '',
    posologia: '',
    orari: '',
    autonomo: false,
    note: '',
  } satisfies Farmaco)
}

function nessuna(campo: 'allergie' | 'farmaci', valore: boolean) {
  if (valore) modulo[campo] = []
}

async function salva() {
  esito.value = null
  // The landlines first, online only: they are on the parents' records.
  for (const g of genitori.value) {
    if (g.puo_modificare && (fissi[g.id] ?? '') !== g.telefono_fisso) {
      const salvato = await esegui(() => api.telefonoFisso(g.id, fissi[g.id] ?? ''))
      if (!salvato) return
      g.telefono_fisso = salvato.telefono
    }
  }
  const dati: SanitarieIn = JSON.parse(JSON.stringify(modulo))
  const risultato = await esegui(() =>
    scrivi({
      metodo: 'PUT',
      percorso: percorsoSanitarie(props.id),
      corpo: dati,
      // Stored in clear in the queue: no names, no health data.
      descrizione: `Scheda sanitaria (n. ${props.id})`,
    }),
  )
  if (!risultato) return
  // Keep the device copy in step, so the change is visible offline too.
  const copia: Sanitarie = {
    ...dati,
    genitori: genitori.value,
    compilate: true,
    puo_modificare: true,
    inserite_da: null,
    aggiornate_il: new Date().toISOString(),
  }
  await salvaInCache(`sanitarie:${props.id}`, copia)
  if (risultato.inCoda) {
    esito.value = 'Salvato sul telefono: verrà inviato appena c’è la rete.'
    return
  }
  await router.push({ name: 'persona', params: { id: props.id } })
}
</script>

<template>
  <section style="max-width: 44rem">
    <h1 class="h4 mb-1">Scheda sanitaria</h1>
    <p class="fg-2">{{ nome }}</p>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-info" role="status">{{ esito }}</div>

    <form v-if="caricata" class="vstack gap-5" @submit.prevent="salva">
      <fieldset class="card card-body">
        <legend class="h6">Contatti per le emergenze</legend>
        <div class="row g-3">
          <template v-for="g in genitori" :key="g.id">
            <div class="col-12 small fw-bold">{{ g.nome }}</div>
            <div class="col-12 md:col-6 small">
              Cellulare: {{ g.cellulare || 'non indicato in BuonaStrada' }}
            </div>
            <div class="col-12 md:col-6">
              <label class="form-label small mb-0" :for="`fisso-${g.id}`">Fisso o lavoro</label>
              <input
                :id="`fisso-${g.id}`"
                v-model="fissi[g.id]"
                class="form-control form-control-sm"
                type="tel"
                maxlength="30"
                :disabled="!g.puo_modificare"
              />
            </div>
          </template>
          <div class="col-12 md:col-7">
            <label class="form-label small mb-0" for="rep-nome">
              Contatto di fiducia (nome e cognome)
            </label>
            <input
              id="rep-nome"
              v-model="modulo.reperibilita_nome"
              class="form-control form-control-sm"
              maxlength="120"
            />
          </div>
          <div class="col-12 md:col-5">
            <label class="form-label small mb-0" for="rep-tel">Telefono</label>
            <input
              id="rep-tel"
              v-model="modulo.reperibilita_telefono"
              class="form-control form-control-sm"
              type="tel"
              maxlength="30"
            />
          </div>
          <div class="col-12">
            <p class="form-text mb-0">
              Vale tutto l'anno; per un singolo campo o uscita puoi indicarne un altro nella pagina
              dell'evento.
            </p>
          </div>
          <div class="col-12 md:col-7">
            <label class="form-label small mb-0" for="medico">
              Medico di base o pediatra (nome e cognome)
            </label>
            <input
              id="medico"
              v-model="modulo.medico_curante"
              class="form-control form-control-sm"
              maxlength="200"
            />
          </div>
          <div class="col-12 md:col-5">
            <label class="form-label small mb-0" for="medico-tel">Telefono del medico</label>
            <input
              id="medico-tel"
              v-model="modulo.medico_telefono"
              class="form-control form-control-sm"
              type="tel"
              maxlength="30"
            />
          </div>
        </div>
      </fieldset>

      <fieldset class="card card-body">
        <legend class="h6">Stato di salute</legend>
        <div v-for="d in ANAMNESI" :key="d.campo" class="mb-3">
          <p class="small fw-bold mb-1">
            {{ d.domanda }} <span v-if="d.esempio" class="fw-normal fg-2">({{ d.esempio }})</span>
          </p>
          <div class="d-flex flex-wrap gap-5">
            <div class="form-field mb-0">
              <input
                :id="`${d.campo}-no`"
                v-model="modulo[d.campo]"
                class="radio"
                type="radio"
                :value="false"
              />
              <label :for="`${d.campo}-no`">No</label>
            </div>
            <div class="form-field mb-0">
              <input
                :id="`${d.campo}-si`"
                v-model="modulo[d.campo]"
                class="radio"
                type="radio"
                :value="true"
              />
              <label :for="`${d.campo}-si`">Sì</label>
            </div>
          </div>
          <input
            v-if="modulo[d.campo]"
            v-model="modulo[`${d.campo}_dettaglio`]"
            class="form-control form-control-sm mt-1"
            maxlength="300"
            :aria-label="`${d.domanda} Spiega in breve`"
            placeholder="Spiega in breve"
            required
          />
        </div>
      </fieldset>

      <fieldset class="card card-body">
        <legend class="h6">Allergie e intolleranze</legend>
        <div v-for="t in TIPI_ALLERGIA" :key="t.tipo" class="mb-5">
          <p class="small fw-bold mb-1">
            {{ t.nome }} <span v-if="t.esempio" class="fw-normal fg-2">({{ t.esempio }})</span>
          </p>
          <div class="d-flex flex-wrap gap-5 mb-1">
            <div class="form-field mb-0">
              <input
                :id="`${t.campo}-no`"
                :checked="modulo[t.campo] === false"
                class="radio"
                type="radio"
                :name="t.campo"
                @change="rispondi(t.campo, t.tipo, false)"
              />
              <label :for="`${t.campo}-no`">No</label>
            </div>
            <div class="form-field mb-0">
              <input
                :id="`${t.campo}-si`"
                :checked="modulo[t.campo] === true"
                class="radio"
                type="radio"
                :name="t.campo"
                @change="rispondi(t.campo, t.tipo, true)"
              />
              <label :for="`${t.campo}-si`">Sì</label>
            </div>
          </div>
          <template v-if="modulo[t.campo]">
            <div
              v-for="a in delTipo(t.tipo)"
              :key="modulo.allergie.indexOf(a)"
              class="border rounded p-3 mb-3"
            >
              <div class="row g-3">
                <div class="col-12 md:col-7">
                  <label
                    class="form-label small mb-0"
                    :for="`sostanza-${modulo.allergie.indexOf(a)}`"
                    >A cosa</label
                  >
                  <input
                    :id="`sostanza-${modulo.allergie.indexOf(a)}`"
                    v-model="a.sostanza"
                    class="form-control form-control-sm"
                    required
                  />
                </div>
                <div class="col-12 md:col-5">
                  <label
                    class="form-label small mb-0"
                    :for="`gravita-${modulo.allergie.indexOf(a)}`"
                    >Gravità</label
                  >
                  <select
                    :id="`gravita-${modulo.allergie.indexOf(a)}`"
                    v-model="a.gravita"
                    class="form-control form-control-sm"
                  >
                    <option value="LIEVE">Lieve</option>
                    <option value="MODERATA">Moderata</option>
                    <option value="GRAVE">Grave: rischio per la vita</option>
                  </select>
                </div>
                <div class="col-12 md:col-6">
                  <label
                    class="form-label small mb-0"
                    :for="`reazione-${modulo.allergie.indexOf(a)}`"
                    >Cosa succede</label
                  >
                  <input
                    :id="`reazione-${modulo.allergie.indexOf(a)}`"
                    v-model="a.reazione"
                    class="form-control form-control-sm"
                  />
                </div>
                <div class="col-12 md:col-6">
                  <label
                    class="form-label small mb-0"
                    :for="`cosa-fare-${modulo.allergie.indexOf(a)}`"
                    >Cosa fare</label
                  >
                  <input
                    :id="`cosa-fare-${modulo.allergie.indexOf(a)}`"
                    v-model="a.cosa_fare"
                    class="form-control form-control-sm"
                  />
                </div>
              </div>
              <button
                type="button"
                class="btn btn-sm btn-link fg-danger px-0"
                @click="modulo.allergie.splice(modulo.allergie.indexOf(a), 1)"
              >
                Togli
              </button>
            </div>
            <button
              type="button"
              class="btn btn-sm btn-outline theme-primary"
              @click="aggiungiAllergia(t.tipo)"
            >
              Aggiungi un'altra
            </button>
          </template>
        </div>
        <p class="small fw-bold mb-1">
          In caso di allergia grave serve un farmaco salvavita (es. adrenalina autoiniettabile)?
        </p>
        <div class="d-flex flex-wrap gap-5">
          <div class="form-field mb-0">
            <input
              id="salvavita-no"
              v-model="modulo.farmaco_salvavita"
              class="radio"
              type="radio"
              :value="false"
            />
            <label for="salvavita-no">No</label>
          </div>
          <div class="form-field mb-0">
            <input
              id="salvavita-si"
              v-model="modulo.farmaco_salvavita"
              class="radio"
              type="radio"
              :value="true"
            />
            <label for="salvavita-si">Sì</label>
          </div>
        </div>
        <p v-if="modulo.farmaco_salvavita" class="form-text mb-0">
          Il farmaco va consegnato ai capi prima della partenza, con istruzioni scritte.
        </p>
      </fieldset>

      <fieldset class="card card-body">
        <legend class="h6">Terapie in corso</legend>
        <div class="form-field mb-3">
          <input
            id="nessun-farmaco"
            v-model="modulo.nessun_farmaco"
            class="check"
            type="checkbox"
            @change="nessuna('farmaci', modulo.nessun_farmaco)"
          />
          <label for="nessun-farmaco"
            >Non deve prendere farmaci durante le attività o il campo</label
          >
        </div>
        <div v-for="(f, i) in modulo.farmaci" :key="i" class="border rounded p-3 mb-3">
          <div class="row g-3">
            <div class="col-12 md:col-6">
              <label class="form-label small mb-0" :for="`farmaco-${i}`">Farmaco</label>
              <input
                :id="`farmaco-${i}`"
                v-model="f.nome"
                class="form-control form-control-sm"
                required
              />
            </div>
            <div class="col-12 md:col-6">
              <label class="form-label small mb-0" :for="`posologia-${i}`">Quanto</label>
              <input
                :id="`posologia-${i}`"
                v-model="f.posologia"
                class="form-control form-control-sm"
                placeholder="Es. 1 compressa"
                required
              />
            </div>
            <div class="col-12 md:col-6">
              <label class="form-label small mb-0" :for="`orari-${i}`">Quando</label>
              <input
                :id="`orari-${i}`"
                v-model="f.orari"
                class="form-control form-control-sm"
                placeholder="Es. a colazione e a cena"
              />
            </div>
            <div class="col-12 md:col-6">
              <label class="form-label small mb-0" :for="`note-${i}`">Note</label>
              <input :id="`note-${i}`" v-model="f.note" class="form-control form-control-sm" />
            </div>
            <div class="col-12">
              <div class="form-field">
                <input :id="`autonomo-${i}`" v-model="f.autonomo" class="check" type="checkbox" />
                <label class="small" :for="`autonomo-${i}`">Lo prende da solo, senza un capo</label>
              </div>
            </div>
          </div>
          <button
            type="button"
            class="btn btn-sm btn-link fg-danger px-0"
            @click="modulo.farmaci.splice(i, 1)"
          >
            Togli
          </button>
        </div>
        <button
          type="button"
          class="btn btn-sm btn-outline theme-primary align-self-start"
          @click="aggiungiFarmaco"
        >
          Aggiungi farmaco
        </button>
      </fieldset>

      <fieldset class="card card-body">
        <legend class="h6">Esigenze alimentari</legend>
        <label class="form-label small" for="esigenze-alimentari">
          Altre esigenze a tavola, non mediche
        </label>
        <input
          id="esigenze-alimentari"
          v-model="modulo.esigenze_alimentari"
          class="form-control"
          maxlength="300"
          placeholder="Es. vegetariano, niente carne di maiale"
        />
        <p class="form-text mb-0">
          Scrivi solo cosa non mangia: non serve spiegare il motivo. Lo vedono i capi, come allergie
          e farmaci.
        </p>
      </fieldset>

      <fieldset class="card card-body">
        <legend class="h6">Antitetanica e farmaci da banco</legend>
        <label class="form-label small mb-0" for="antitetanica-data">
          Data dell'ultima vaccinazione o richiamo contro il tetano
        </label>
        <input
          id="antitetanica-data"
          v-model="modulo.antitetanica_data"
          class="form-control form-control-sm mb-3"
          type="date"
        />
        <p class="small fw-bold mb-1">
          Per piccoli malesseri (mal di testa, febbre leggera, mal di pancia, punture d'insetto) i
          capi possono dare farmaci da banco (es. paracetamolo, ibuprofene, antistaminici in crema),
          dopo una telefonata quando possibile?
        </p>
        <div class="d-flex flex-wrap gap-5">
          <div class="form-field mb-0">
            <input
              id="banco-si"
              v-model="modulo.farmaci_da_banco"
              class="radio"
              type="radio"
              :value="true"
            />
            <label for="banco-si">Sì, autorizzo</label>
          </div>
          <div class="form-field mb-0">
            <input
              id="banco-no"
              v-model="modulo.farmaci_da_banco"
              class="radio"
              type="radio"
              :value="false"
            />
            <label for="banco-no">No, non autorizzo</label>
          </div>
        </div>
      </fieldset>

      <fieldset class="card card-body">
        <legend class="h6">Altre informazioni</legend>
        <div class="row g-3">
          <div class="col-12">
            <label class="form-label small mb-0" for="tessera">Numero di tessera sanitaria</label>
            <input
              id="tessera"
              v-model="modulo.tessera_sanitaria"
              class="form-control form-control-sm"
              maxlength="30"
            />
          </div>
          <div class="col-12 md:col-4">
            <label class="form-label small mb-0" for="gruppo-sanguigno">Gruppo sanguigno</label>
            <input
              id="gruppo-sanguigno"
              v-model="modulo.gruppo_sanguigno"
              class="form-control form-control-sm"
              maxlength="10"
              placeholder="Es. 0+"
            />
          </div>
          <div class="col-12 md:col-8">
            <label class="form-label small mb-0" for="vaccinazioni">Altre vaccinazioni</label>
            <input
              id="vaccinazioni"
              v-model="modulo.altre_vaccinazioni"
              class="form-control form-control-sm"
              maxlength="300"
            />
          </div>
          <div class="col-12">
            <label class="form-label small mb-0" for="note-sanitarie">Altre note sanitarie</label>
            <textarea
              id="note-sanitarie"
              v-model="modulo.note_sanitarie"
              class="form-control form-control-sm"
              rows="2"
            />
          </div>
        </div>
      </fieldset>

      <p class="small fg-2 mb-0">
        Dopo aver salvato, stampa il modulo dalla scheda della persona, firmalo e consegnalo ai capi
        con l'eventuale prescrizione del medico. Se cambi qualcosa, va firmato di nuovo.
      </p>
      <button class="btn btn-solid theme-primary align-self-start" :disabled="inCorso">
        Salva
      </button>
    </form>
  </section>
</template>
