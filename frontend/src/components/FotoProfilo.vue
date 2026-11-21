<script setup lang="ts">
import { ref } from 'vue'

import { api, fotoProfilo, type FotoStorica, type PersonaDettaglio } from '@/api/qdc'
import RitaglioFoto from '@/components/RitaglioFoto.vue'
import { useErrore } from '@/composables/useErrore'
import { useSessioneStore } from '@/stores/sessione'

// The profile photo, to recognise the ragazzi (DEC-42, DEC-201). The photo is cropped
// on the device to a square around the person (DEC-205): only that square leaves the
// phone, so the other people in a group photo are never uploaded. The server reduces it
// to a JPEG of at most 1 MB without metadata; the earlier photos stay for the capi, who
// open them on request (online only, like the current one).
const props = defineProps<{ persona: PersonaDettaglio }>()
const emit = defineEmits<{ cambiata: [persona: PersonaDettaglio] }>()
const sessione = useSessioneStore()
const { errore, inCorso, esegui } = useErrore()

const versione = ref(Date.now())
// The earlier photos, newest first; null until asked for.
const precedenti = ref<FotoStorica[] | null>(null)
const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')

async function mostraPrecedenti() {
  if (precedenti.value) {
    precedenti.value = null
    return
  }
  const tutte = await esegui(() => api.storicoFoto(props.persona.id))
  // The first one is the current photo, already shown.
  if (tutte) precedenti.value = tutte.slice(1)
}
// The photo chosen, being cropped.
const scelta = ref<File | null>(null)

function scegli(evento: Event) {
  const input = evento.target as HTMLInputElement
  scelta.value = input.files?.[0] ?? null
  input.value = ''
}

function annulla() {
  scelta.value = null
}

async function salva(blob: Blob) {
  const nuova = await esegui(() => api.caricaFotoProfilo(props.persona.id, blob))
  if (!nuova) return
  annulla()
  versione.value = Date.now()
  emit('cambiata', nuova)
  // One's own photo: the avatar of the side menu changes too (DEC-297).
  if (props.persona.id === sessione.profilo?.persona?.id) await sessione.carica()
}
</script>

<template>
  <div class="d-flex flex-wrap align-items-start gap-3 mb-3">
    <img
      v-if="persona.foto && !scelta"
      :src="`${fotoProfilo(persona.id)}?v=${versione}`"
      :alt="`Foto di ${persona.nome} ${persona.cognome}`"
      width="96"
      height="96"
      class="rounded"
    />
    <div v-if="persona.puo_caricare_foto && !scelta">
      <label class="btn btn-sm btn-outline theme-primary mb-0" :for="`foto-${persona.id}`">
        {{ persona.foto ? 'Cambia la foto' : 'Aggiungi una foto' }}
      </label>
      <input
        :id="`foto-${persona.id}`"
        type="file"
        accept="image/*"
        class="d-none"
        @change="scegli"
      />
      <p class="small fg-2 mb-0 mt-1">
        Serve ai capi per riconoscere {{ persona.nome }}; non viene pubblicata.
      </p>
    </div>
    <div v-if="persona.vede_storico_foto && persona.foto && !scelta" class="w-100">
      <button type="button" class="btn btn-sm btn-link px-0" @click="mostraPrecedenti">
        {{ precedenti ? 'Nascondi le foto precedenti' : 'Foto precedenti' }}
      </button>
      <template v-if="precedenti">
        <p v-if="!precedenti.length" class="small fg-2 mb-0">Nessuna foto precedente.</p>
        <ul v-else class="list-unstyled d-flex flex-wrap gap-3 mb-0">
          <li v-for="f in precedenti" :key="f.id" class="small fg-2 text-center">
            <img
              :src="`${fotoProfilo(persona.id)}?foto_id=${f.id}`"
              :alt="`Foto di ${persona.nome} del ${data(f.creata_il)}`"
              width="72"
              height="72"
              class="rounded d-block mb-1"
            />
            {{ data(f.creata_il) }}
          </li>
        </ul>
      </template>
    </div>

    <div v-if="scelta" class="w-100">
      <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
      <RitaglioFoto
        :id="`foto-${persona.id}`"
        :file="scelta"
        :in-corso="inCorso"
        @pronta="salva"
        @annulla="annulla"
        @errore="(m) => (errore = m)"
      >
        <p class="small mb-1">
          Sposta la foto e ingrandiscila finché nel riquadro c'è solo
          {{ persona.nome }}: le altre persone non vengono caricate.
        </p>
      </RitaglioFoto>
    </div>
  </div>
</template>
