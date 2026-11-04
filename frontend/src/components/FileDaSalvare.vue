<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { fileInArrivo, linkAFile, pwaSuIos, scaricaFile } from '@/pwa/file'

// The app installed on an iPhone (issue #12): links to files come here instead of opening
// a page with no way back. The share needs its own tap: Safari may refuse it when it
// follows the wait for the download.
const MASSIMO_IN_MEMORIA = 200 * 1024 * 1024
const TROPPO_GRANDE =
  'Il file è troppo grande per aprirlo dall\u2019app sull\u2019iPhone: aprilo da Safari o dal computer.'
const finestra = ref<HTMLDialogElement | null>(null)
const errore = ref('')

function suClic(evento: MouseEvent) {
  const link = linkAFile(evento)
  if (!link) return
  evento.preventDefault()
  // A file this big would not fit in the phone's memory.
  if (Number(link.dataset.dimensione ?? 0) > MASSIMO_IN_MEMORIA) {
    fileInArrivo.value = { stato: 'errore', messaggio: TROPPO_GRANDE }
    return
  }
  void scaricaFile(link.href)
}

onMounted(() => {
  if (pwaSuIos()) document.addEventListener('click', suClic, true)
})
onBeforeUnmount(() => document.removeEventListener('click', suClic, true))

watch(fileInArrivo, (file) => {
  errore.value = ''
  if (file && !finestra.value?.open) finestra.value?.showModal()
  if (!file && finestra.value?.open) finestra.value.close()
})

function chiudi() {
  fileInArrivo.value = null
}

async function condividi(file: File) {
  errore.value = ''
  const dati = { files: [file] }
  if (!navigator.canShare?.(dati)) {
    errore.value = 'Questo telefono non può condividere questo tipo di file dall’app.'
    return
  }
  try {
    await navigator.share(dati)
    chiudi()
  } catch (e) {
    // Closing the share sheet is not an error.
    if ((e as DOMException)?.name !== 'AbortError')
      errore.value = 'Non sono riuscito a condividere il file: riprova.'
  }
}
</script>

<template>
  <dialog ref="finestra" class="dialog" aria-labelledby="file-da-salvare" @close="chiudi">
    <div class="dialog-body">
      <h2 id="file-da-salvare" class="h5">
        {{ fileInArrivo?.stato === 'attesa' ? 'Sto scaricando il file…' : 'Il file' }}
      </h2>
      <template v-if="fileInArrivo?.stato === 'pronto'">
        <p class="text-break">{{ fileInArrivo.file.name }}</p>
        <button
          type="button"
          class="btn btn-solid theme-primary me-3"
          @click="condividi(fileInArrivo.file)"
        >
          Condividi o salva
        </button>
      </template>
      <div v-if="fileInArrivo?.stato === 'errore'" class="alert theme-danger" role="alert">
        {{ fileInArrivo.messaggio }}
      </div>
      <div v-if="errore" class="alert theme-danger mt-3" role="alert">{{ errore }}</div>
      <button type="button" class="btn btn-outline" @click="chiudi">Chiudi</button>
    </div>
  </dialog>
</template>
