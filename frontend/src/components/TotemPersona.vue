<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { ErroreApi } from '@/api/http'
import { api, immagineTotem, type TotemPersona } from '@/api/qdc'
import RitaglioFoto from '@/components/RitaglioFoto.vue'
import { useErrore } from '@/composables/useErrore'
import { useSessioneStore } from '@/stores/sessione'

// The totem name on the person's page (DEC-416): the capi see it for whoever may have one
// (from the reparto up), the person themself once they have one; never the parents. The
// staff of the unit and the capigruppo assign it. The image is cropped on the device like
// the profile photo; a ragazzo's waits for a capo. Online only.
// «Modifica totem» (DEC-418): a capo with a totem name lets the person write their own,
// once; any change turns it off. Only who may turn it on or off sees the switch.
const props = defineProps<{ persona: number; nome: string }>()
const sessione = useSessioneStore()
const { errore, inCorso, esegui } = useErrore()
const totem = ref<TotemPersona | null>(null)
const modifica = ref(false)
const nuovoNome = ref('')
const scelta = ref<File | null>(null)
// Taking away an inappropriate image: the reason, shown to the owner.
const togliendo = ref(false)
const motivo = ref('')
// Writing one's own name through «Modifica totem», not assigning it.
const proprio = computed(() => !!totem.value?.puo_scrivere && !totem.value.puo_assegnare)

onMounted(async () => {
  try {
    totem.value = await api.totemPersona(props.persona)
  } catch (e) {
    // Not one to see: nothing to show.
    if (!(e instanceof ErroreApi && e.stato === 404)) throw e
  }
})

function apri() {
  nuovoNome.value = totem.value?.nome ?? ''
  modifica.value = true
}

async function salvaNome(nome: string) {
  const esito = await esegui(() => api.assegnaTotem(props.persona, nome))
  if (!esito) return
  totem.value = esito
  modifica.value = false
}

function scegli(evento: Event) {
  const input = evento.target as HTMLInputElement
  scelta.value = input.files?.[0] ?? null
  input.value = ''
}

async function carica(blob: Blob) {
  const esito = await esegui(() => api.caricaImmagineTotem(props.persona, blob))
  if (!esito) return
  totem.value = esito
  scelta.value = null
  await sessione.carica()
}

async function cambiaModifica(evento: Event) {
  const attiva = (evento.target as HTMLInputElement).checked
  const esito = await esegui(() => api.modificaTotem(props.persona, attiva))
  if (esito) totem.value = esito
  else (evento.target as HTMLInputElement).checked = !attiva
}

async function togli() {
  const id = totem.value?.id
  if (!id) return
  const esito = await esegui(() => api.togliImmagineTotem(id, motivo.value))
  if (!esito) return
  totem.value = await api.totemPersona(props.persona)
  togliendo.value = false
  motivo.value = ''
}
</script>

<template>
  <section v-if="totem" class="card card-body mb-5" data-totem>
    <h2 class="h5">Nome di totem</h2>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>

    <div v-if="totem.puo_scrivere" class="alert theme-info small" role="status" data-una-volta>
      <div>
        Puoi {{ totem.id ? 'cambiare' : 'scrivere' }} il tuo nome di totem una volta sola: dopo, per
        cambiarlo ancora, dovrà permettertelo un capo.
      </div>
    </div>

    <form v-if="modifica" class="mb-3" @submit.prevent="salvaNome(nuovoNome)">
      <label class="form-label small" :for="`totem-${persona}`">
        Un animale o una pianta con un aggettivo
      </label>
      <input
        :id="`totem-${persona}`"
        v-model="nuovoNome"
        class="form-control mb-3"
        maxlength="80"
        autocomplete="off"
      />
      <div class="d-flex flex-wrap gap-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Salva
        </button>
        <button
          v-if="totem.id && !proprio"
          type="button"
          class="btn btn-sm btn-outline theme-danger"
          :disabled="inCorso"
          @click="salvaNome('')"
        >
          Togli il nome di totem
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="modifica = false">Annulla</button>
      </div>
    </form>

    <template v-else>
      <div class="d-flex flex-wrap align-items-center gap-3">
        <img
          v-if="totem.id && totem.immagine && !scelta"
          :src="immagineTotem(totem.id, totem.versione)"
          :alt="`Immagine di ${totem.nome}`"
          width="96"
          height="96"
          class="rounded"
        />
        <strong v-if="totem.id" class="h5 mb-0">{{ totem.nome }}</strong>
        <span v-else-if="!proprio" class="fg-2">{{ nome }} non ha ancora un nome di totem.</span>
        <button
          v-if="totem.puo_assegnare || totem.puo_scrivere"
          type="button"
          class="btn btn-sm btn-outline theme-primary ms-auto"
          @click="apri"
        >
          {{ totem.id ? 'Cambia' : proprio ? 'Scrivi il tuo nome di totem' : 'Assegna' }}
        </button>
      </div>

      <div v-if="totem.puo_attivare_modifica" class="form-field mt-3">
        <div class="switch">
          <input
            :id="`totem-modifica-${persona}`"
            type="checkbox"
            role="switch"
            :checked="totem.modifica_attiva"
            :disabled="inCorso"
            @change="cambiaModifica"
          />
        </div>
        <label :for="`totem-modifica-${persona}`">Modifica totem</label>
        <p class="small fg-2 mb-0">
          {{ nome }} può {{ totem.id ? 'cambiare' : 'scrivere' }} da sé il nome di totem, una volta
          sola: dopo ogni modifica si spegne.
        </p>
      </div>

      <div v-if="totem.avviso" class="alert theme-warning small mt-3" role="status">
        <div>{{ totem.avviso }}</div>
      </div>
      <div v-if="totem.id && totem.in_attesa && !scelta" class="d-flex gap-3 mt-3">
        <img
          :src="immagineTotem(totem.id, totem.versione, true)"
          alt="Immagine in attesa di approvazione"
          width="64"
          height="64"
          class="rounded"
        />
        <p class="small fg-2 mb-0">
          Immagine in attesa di approvazione: la vedranno gli altri quando un capo l'avrà approvata.
        </p>
      </div>

      <div v-if="totem.puo_caricare && !scelta" class="mt-3">
        <label class="btn btn-sm btn-outline theme-primary mb-0" :for="`totem-img-${persona}`">
          {{ totem.immagine ? "Cambia l'immagine" : "Aggiungi un'immagine" }}
        </label>
        <input
          :id="`totem-img-${persona}`"
          type="file"
          accept="image/*"
          class="d-none"
          @change="scegli"
        />
        <p class="small fg-2 mb-0 mt-1">
          Un'immagine che rappresenta il totem.
          <template v-if="totem.da_approvare"
            >La vedono gli altri dopo che un capo l'ha approvata.</template
          >
        </p>
      </div>
      <RitaglioFoto
        v-if="scelta"
        :id="`totem-${persona}`"
        class="mt-3"
        :file="scelta"
        :in-corso="inCorso"
        etichetta-salva="Salva l'immagine"
        @pronta="carica"
        @annulla="scelta = null"
        @errore="(m) => (errore = m)"
      >
        <p class="small mb-1">Sposta l'immagine e ingrandiscila: si carica solo il riquadro.</p>
      </RitaglioFoto>

      <template v-if="totem.puo_moderare && totem.immagine && !scelta">
        <button
          v-if="!togliendo"
          type="button"
          class="btn btn-sm btn-link px-0 mt-3"
          @click="togliendo = true"
        >
          Togli l'immagine perché non è adatta
        </button>
        <form v-else class="mt-3" @submit.prevent="togli">
          <label class="form-label small" :for="`totem-motivo-${persona}`">
            Perché la togli? Lo legge chi ha il totem.
          </label>
          <input
            :id="`totem-motivo-${persona}`"
            v-model="motivo"
            class="form-control mb-3"
            maxlength="200"
            required
          />
          <div class="d-flex gap-3">
            <button type="submit" class="btn btn-sm btn-solid theme-danger" :disabled="inCorso">
              Togli l'immagine
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="togliendo = false">
              Annulla
            </button>
          </div>
        </form>
      </template>
    </template>
  </section>
</template>
