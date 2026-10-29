<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import {
  api,
  percorsoSanitarie,
  type Allergia,
  type Farmaco,
  type Sanitarie,
  type SanitarieIn,
} from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache, salvaInCache } from '@/offline/cache'
import { scrivi } from '@/offline/outbox'

// Parents, the adult member, or a capo transcribing the signed paper form (DEC-50, DEC-55).
const props = defineProps<{ id: number }>()
const router = useRouter()
const { errore, inCorso, esegui } = useErrore()

const nome = ref('')
const caricata = ref(false)
const esito = ref<string | null>(null)
const modulo = reactive<SanitarieIn>({
  nessuna_allergia: false,
  nessun_farmaco: false,
  allergie: [],
  farmaci: [],
})

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
    modulo.allergie = sanitarie.dati.allergie.map((a) => ({ ...a }))
    modulo.farmaci = sanitarie.dati.farmaci.map((f) => ({ ...f }))
    caricata.value = true
  }
})

function aggiungiAllergia() {
  modulo.nessuna_allergia = false
  modulo.allergie.push({
    tipo: 'ALLERGIA',
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
  const dati: SanitarieIn = JSON.parse(JSON.stringify(modulo))
  const risultato = await esegui(() =>
    scrivi({
      metodo: 'PUT',
      percorso: percorsoSanitarie(props.id),
      corpo: dati,
      // Stored in clear in the queue: no names, no health data.
      descrizione: `Farmaci e allergie (scheda n. ${props.id})`,
    }),
  )
  if (!risultato) return
  // Keep the device copy in step, so the change is visible offline too.
  const copia: Sanitarie = {
    ...dati,
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
    <h1 class="h4 mb-1">Farmaci, allergie e intolleranze</h1>
    <p class="fg-2">{{ nome }}</p>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-info" role="status">{{ esito }}</div>

    <form v-if="caricata" class="vstack gap-5" @submit.prevent="salva">
      <fieldset class="card card-body">
        <legend class="h6">Allergie e intolleranze</legend>
        <div class="form-field mb-3">
          <input
            id="nessuna-allergia"
            v-model="modulo.nessuna_allergia"
            class="check"
            type="checkbox"
            @change="nessuna('allergie', modulo.nessuna_allergia)"
          />
          <label for="nessuna-allergia">Nessuna allergia o intolleranza</label>
        </div>
        <div v-for="(a, i) in modulo.allergie" :key="i" class="border rounded p-3 mb-3">
          <div class="row g-3">
            <div class="col-6 md:col-3">
              <label class="form-label small mb-0" :for="`tipo-${i}`">Tipo</label>
              <select :id="`tipo-${i}`" v-model="a.tipo" class="form-control form-control-sm">
                <option value="ALLERGIA">Allergia</option>
                <option value="INTOLLERANZA">Intolleranza</option>
              </select>
            </div>
            <div class="col-6 md:col-4">
              <label class="form-label small mb-0" :for="`gravita-${i}`">Gravità</label>
              <select :id="`gravita-${i}`" v-model="a.gravita" class="form-control form-control-sm">
                <option value="LIEVE">Lieve</option>
                <option value="MODERATA">Moderata</option>
                <option value="GRAVE">Grave: rischio per la vita</option>
              </select>
            </div>
            <div class="col-12 md:col-5">
              <label class="form-label small mb-0" :for="`sostanza-${i}`">A cosa</label>
              <input
                :id="`sostanza-${i}`"
                v-model="a.sostanza"
                class="form-control form-control-sm"
                placeholder="Es. arachidi, lattosio, punture di vespa"
                required
              />
            </div>
            <div class="col-12 md:col-6">
              <label class="form-label small mb-0" :for="`reazione-${i}`">Cosa succede</label>
              <input
                :id="`reazione-${i}`"
                v-model="a.reazione"
                class="form-control form-control-sm"
              />
            </div>
            <div class="col-12 md:col-6">
              <label class="form-label small mb-0" :for="`cosa-fare-${i}`">Cosa fare</label>
              <input
                :id="`cosa-fare-${i}`"
                v-model="a.cosa_fare"
                class="form-control form-control-sm"
                placeholder="Es. adrenalina autoiniettabile nello zaino"
              />
            </div>
          </div>
          <button
            type="button"
            class="btn btn-sm btn-link fg-danger px-0"
            @click="modulo.allergie.splice(i, 1)"
          >
            Togli
          </button>
        </div>
        <button
          type="button"
          class="btn btn-sm btn-outline theme-primary align-self-start"
          @click="aggiungiAllergia"
        >
          Aggiungi allergia o intolleranza
        </button>
      </fieldset>

      <fieldset class="card card-body">
        <legend class="h6">Farmaci</legend>
        <div class="form-field mb-3">
          <input
            id="nessun-farmaco"
            v-model="modulo.nessun_farmaco"
            class="check"
            type="checkbox"
            @change="nessuna('farmaci', modulo.nessun_farmaco)"
          />
          <label for="nessun-farmaco">Nessun farmaco</label>
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

      <p class="small fg-2 mb-0">
        Le prescrizioni del medico restano sulla scheda cartacea firmata, da consegnare ai capi.
      </p>
      <button class="btn btn-solid theme-primary align-self-start" :disabled="inCorso">
        Salva
      </button>
    </form>
  </section>
</template>
