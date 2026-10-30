<script setup lang="ts">
import { ref } from 'vue'

import { allegatoPP, api, type AllegatoPP, type TipoVoceAllegato } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Images and PDFs on an item of the Progressione (DEC-42, DEC-202): uploaded by the
// staff or the ragazzo, read by who reads the item. Online only: files do not wait in
// the offline queue.
const props = defineProps<{
  tipo: TipoVoceAllegato
  voce: number
  allegati: AllegatoPP[]
  carica: boolean
  togli: boolean
}>()
const emit = defineEmits<{ cambiata: [inCoda: boolean] }>()
const { errore, inCorso, esegui } = useErrore()
const aperta = ref(false)
const titolo = ref('')
const file = ref<File | null>(null)

async function salva() {
  if (!file.value) return
  const fatto = await esegui(() =>
    api.caricaAllegatoPP(props.tipo, props.voce, titolo.value, file.value!),
  )
  if (!fatto) return
  aperta.value = false
  titolo.value = ''
  file.value = null
  emit('cambiata', false)
}

async function rimuovi(id: number) {
  if (await esegui(() => api.togliAllegatoPP(id))) emit('cambiata', false)
}
</script>

<template>
  <div v-if="allegati.length || carica" class="small mt-1">
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <ul v-if="allegati.length" class="list-unstyled mb-1">
      <li v-for="a in allegati" :key="a.id">
        <a :href="allegatoPP(a.id)" target="_blank" rel="noopener">{{ a.titolo }}</a>
        <span class="fg-2"> ({{ a.tipo_file === 'application/pdf' ? 'PDF' : 'immagine' }})</span>
        <button
          v-if="togli"
          type="button"
          class="btn btn-sm btn-link py-0"
          :disabled="inCorso"
          @click="rimuovi(a.id)"
        >
          Togli
        </button>
      </li>
    </ul>
    <button
      v-if="carica && !aperta"
      type="button"
      class="btn btn-sm btn-link px-0"
      @click="aperta = true"
    >
      Allega una foto o un PDF
    </button>
    <form v-if="aperta" class="d-flex flex-wrap align-items-end gap-3" @submit.prevent="salva">
      <div class="flex-grow-1">
        <label class="form-label small" :for="`all-t-${tipo}-${voce}`">Cos'è</label>
        <input
          :id="`all-t-${tipo}-${voce}`"
          v-model="titolo"
          class="form-control form-control-sm"
          maxlength="120"
          required
        />
      </div>
      <div>
        <label class="form-label small" :for="`all-f-${tipo}-${voce}`">
          File (PDF, JPEG o PNG, al massimo 10 MB)
        </label>
        <input
          :id="`all-f-${tipo}-${voce}`"
          type="file"
          accept="application/pdf,image/jpeg,image/png"
          class="form-control form-control-sm"
          required
          @change="file = ($event.target as HTMLInputElement).files?.[0] ?? null"
        />
      </div>
      <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
        Carica
      </button>
      <button type="button" class="btn btn-sm btn-link" @click="aperta = false">Annulla</button>
    </form>
  </div>
</template>
