<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

// A PDF read inside the page, the same on every device: phones do not show one reliably in an
// iframe, and the app's pages may not be framed anyway. Loaded only when opened (DEC-335).
const props = defineProps<{ url: string }>()
const contenitore = ref<HTMLElement | null>(null)
const errore = ref('')
const caricamento = ref(true)
let chiuso = false

onMounted(async () => {
  try {
    const risposta = await fetch(props.url, { credentials: 'same-origin' })
    if (!risposta.ok) throw new Error(String(risposta.status))
    const dati = new Uint8Array(await risposta.arrayBuffer())
    const pdfjs = await import('pdfjs-dist')
    const worker = await import('pdfjs-dist/build/pdf.worker.min.mjs?url')
    pdfjs.GlobalWorkerOptions.workerSrc = worker.default
    const caricato = pdfjs.getDocument({ data: dati })
    const documento = await caricato.promise
    for (let n = 1; n <= documento.numPages && !chiuso; n++) {
      const pagina = await documento.getPage(n)
      const larghezza = contenitore.value?.clientWidth || 600
      const base = pagina.getViewport({ scale: 1 })
      const scala = (larghezza / base.width) * (window.devicePixelRatio || 1)
      const viewport = pagina.getViewport({ scale: scala })
      const tela = document.createElement('canvas')
      tela.width = viewport.width
      tela.height = viewport.height
      tela.style.width = '100%'
      tela.className = 'd-block mb-3 border'
      tela.setAttribute('aria-label', `Pagina ${n} di ${documento.numPages}`)
      contenitore.value?.appendChild(tela)
      await pagina.render({ canvas: tela, viewport }).promise
    }
    await caricato.destroy()
  } catch {
    errore.value = 'Non riesco a mostrare il PDF qui: scaricalo per leggerlo.'
  } finally {
    caricamento.value = false
  }
})

onBeforeUnmount(() => {
  chiuso = true
})
</script>

<template>
  <div>
    <p v-if="caricamento" class="small fg-2 mb-1" role="status">Carico il PDF…</p>
    <div v-if="errore" class="alert theme-warning small" role="alert">
      <div>{{ errore }}</div>
    </div>
    <div ref="contenitore"></div>
  </div>
</template>
