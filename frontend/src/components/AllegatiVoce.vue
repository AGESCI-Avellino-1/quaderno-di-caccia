<script setup lang="ts">
import { reactive, ref } from 'vue'

import { allegatoVoceLibro, api, type VoceLibro } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The attachments of an entry of the book (DEC-437): read by who reads the entry, added and
// taken off by who writes it. PDF and images, online only: never kept on the device.
const props = defineProps<{ voce: VoceLibro }>()
const emit = defineEmits<{ aggiornata: [VoceLibro] }>()
const { errore, inCorso, esegui } = useErrore()

const aperto = ref(false)
const nuovo = reactive({ titolo: '', file: null as File | null })

function scegliFile(evento: Event) {
  nuovo.file = (evento.target as HTMLInputElement).files?.[0] ?? null
}

async function carica() {
  if (!nuovo.file) return
  const file = nuovo.file
  const voce = await esegui(() => api.caricaAllegatoVoce(props.voce.id, nuovo.titolo, file))
  if (!voce) return
  emit('aggiornata', voce)
  Object.assign(nuovo, { titolo: '', file: null })
  aperto.value = false
}

async function togli(id: number) {
  const voce = await esegui(() => api.togliAllegatoVoce(id))
  if (voce) emit('aggiornata', voce)
}
</script>

<template>
  <section v-if="voce.allegati.length || voce.puo_modificare" class="mb-7" data-allegati>
    <h2 class="h5">Allegati</h2>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <p v-if="!voce.allegati.length" class="small fg-2">Nessun allegato.</p>
    <ul v-else class="list-unstyled mb-3">
      <li v-for="a in voce.allegati" :key="a.id" class="d-flex flex-wrap gap-3 align-items-center">
        <a :href="allegatoVoceLibro(a.id)" target="_blank" rel="noopener">
          {{ a.titolo }}
        </a>
        <button
          v-if="voce.puo_modificare"
          type="button"
          class="btn btn-sm btn-link py-0"
          :aria-label="`Togli l'allegato ${a.titolo}`"
          :disabled="inCorso"
          @click="togli(a.id)"
        >
          Togli
        </button>
      </li>
    </ul>
    <p v-if="voce.allegati.length" class="small fg-2">Gli allegati si aprono solo con la rete.</p>
    <template v-if="voce.puo_modificare">
      <button
        v-if="!aperto"
        type="button"
        class="btn btn-sm btn-outline theme-primary"
        @click="aperto = true"
      >
        Aggiungi un allegato
      </button>
      <form v-else class="d-flex flex-wrap align-items-end gap-3" @submit.prevent="carica">
        <div>
          <label class="form-label small mb-0" for="allegato-titolo">Che cos'è</label>
          <input
            id="allegato-titolo"
            v-model="nuovo.titolo"
            class="form-control form-control-sm"
            maxlength="120"
            placeholder="Es. Testo del canto"
            required
          />
        </div>
        <div>
          <label class="form-label small mb-0" for="allegato-file">
            PDF o immagine, fino a 10 MB
          </label>
          <input
            id="allegato-file"
            type="file"
            accept="application/pdf,image/jpeg,image/png"
            class="form-control form-control-sm"
            required
            @change="scegliFile"
          />
        </div>
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Carica
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="aperto = false">Annulla</button>
      </form>
    </template>
  </section>
</template>
