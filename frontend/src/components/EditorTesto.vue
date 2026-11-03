<script setup lang="ts">
import Image from '@tiptap/extension-image'
import { TableKit } from '@tiptap/extension-table'
import TextAlign from '@tiptap/extension-text-align'
import StarterKit from '@tiptap/starter-kit'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import { onBeforeUnmount, ref, watch } from 'vue'

import { api } from '@/api/qdc'
import Icona from '@/components/Icona.vue'
import { useErrore } from '@/composables/useErrore'
import { nonPermessi } from '@/sito/html'

// Formatted text for the email templates and the public pages (DEC-250, DEC-266): only
// what an email needs (bold, italic, underline, lists, links, two heading levels,
// tables, images uploaded to the app, alignment). Images are resized by dragging their
// corner or with a few sizes; the HTML can be written by hand (DEC-305). The server cleans
// the HTML again before saving it, so this is a convenience, not a protection.
const html = defineModel<string>({ required: true })
const props = defineProps<{ etichetta: string; immagini?: boolean }>()
const { errore: erroreImmagine, inCorso: caricaInCorso, esegui: eseguiCaricamento } = useErrore()

// Tiptap's resizable image applies the width only when drawn and while dragging: a size
// chosen with the buttons must show at once too (DEC-305).
const Immagine = Image.extend({
  addNodeView() {
    const originale = this.parent?.()
    if (!originale) return null
    return (props) => {
      const vista = originale(props)
      const applica = (nodo: typeof props.node) => {
        const img = vista.dom instanceof HTMLElement ? vista.dom.querySelector('img') : null
        if (!img) return
        img.style.width = nodo.attrs.width ? `${nodo.attrs.width}px` : ''
        img.style.height = ''
      }
      const aggiorna = vista.update?.bind(vista)
      vista.update = (nodo, ...resto) => {
        const fatto = aggiorna ? aggiorna(nodo, ...resto) : false
        if (fatto) applica(nodo)
        return fatto
      }
      return vista
    }
  },
})

const editor = useEditor({
  content: html.value,
  extensions: [
    StarterKit.configure({
      heading: { levels: [2, 3] },
      code: false,
      codeBlock: false,
      blockquote: false,
      horizontalRule: false,
      link: { openOnClick: false, autolink: true, protocols: ['mailto'] },
    }),
    TableKit.configure({ table: { resizable: false } }),
    TextAlign.configure({
      types: ['heading', 'paragraph'],
      alignments: ['left', 'center', 'right'],
    }),
    // Inline, so that the paragraph's alignment moves it too (DEC-305).
    Immagine.configure({
      inline: true,
      resize: {
        enabled: true,
        directions: ['bottom-right', 'bottom-left'],
        minWidth: 40,
        minHeight: 20,
        alwaysPreserveAspectRatio: true,
      },
    }),
  ],
  editorProps: { attributes: { class: 'form-control qdc-editor-testo' } },
  onUpdate: ({ editor: e }) => {
    html.value = e.getHTML()
  },
})

// Replaced from outside (back to the default): show the new text.
watch(html, (nuovo) => {
  if (editor.value && nuovo !== editor.value.getHTML()) {
    editor.value.commands.setContent(nuovo, { emitUpdate: false })
  }
})

onBeforeUnmount(() => editor.value?.destroy())

// The HTML written by hand (DEC-305): back to the editor, what the server would drop is
// named, and the editor keeps only what it knows.
const modoHtml = ref(false)
const codice = ref('')
const tolti = ref<string[]>([])

// What is typed is the text: saving while the HTML is open keeps it.
watch(codice, (nuovo) => {
  if (!modoHtml.value) return
  html.value = nuovo
  tolti.value = nonPermessi(nuovo)
})
watch(html, (nuovo) => {
  if (modoHtml.value && nuovo !== codice.value) codice.value = nuovo
})

function alternaHtml() {
  if (!editor.value) return
  if (!modoHtml.value) {
    codice.value = editor.value.getHTML()
    tolti.value = []
    modoHtml.value = true
    return
  }
  tolti.value = nonPermessi(codice.value)
  editor.value.commands.setContent(codice.value, { emitUpdate: false })
  html.value = editor.value.getHTML()
  modoHtml.value = false
}

// Image sizes, handier than dragging on a phone (DEC-305): widths in pixels.
const MISURE = [
  { nome: 'Piccola', larghezza: 120 },
  { nome: 'Media', larghezza: 240 },
  { nome: 'Grande', larghezza: 480 },
  { nome: 'Originale', larghezza: null },
] as const

function misura(larghezza: number | null) {
  const e = editor.value
  if (!e) return
  // The image stays selected, to try another size.
  const posizione = e.state.selection.from
  e.chain()
    .focus()
    .updateAttributes('image', { width: larghezza, height: null })
    .setNodeSelection(posizione)
    .run()
}

const ALLINEAMENTI = [
  { valore: 'left', nome: 'Allinea a sinistra', icona: 'text-left' },
  { valore: 'center', nome: 'Allinea al centro', icona: 'text-center' },
  { valore: 'right', nome: 'Allinea a destra', icona: 'text-right' },
] as const

function allinea(valore: (typeof ALLINEAMENTI)[number]['valore']) {
  editor.value?.chain().focus().setTextAlign(valore).run()
}

const indirizzo = ref('')
const chiediLink = ref(false)

function apriLink() {
  indirizzo.value = editor.value?.getAttributes('link').href ?? ''
  chiediLink.value = true
}

function applicaLink() {
  const href = indirizzo.value.trim()
  const catena = editor.value?.chain().focus().extendMarkRange('link')
  if (!catena) return
  if (href) catena.setLink({ href }).run()
  else catena.unsetLink().run()
  chiediLink.value = false
}

function tabella(
  azione: 'inserisci' | 'riga' | 'colonna' | 'togliRiga' | 'togliColonna' | 'elimina',
) {
  const catena = editor.value?.chain().focus()
  if (!catena) return
  if (azione === 'inserisci') catena.insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()
  else if (azione === 'riga') catena.addRowAfter().run()
  else if (azione === 'colonna') catena.addColumnAfter().run()
  else if (azione === 'togliRiga') catena.deleteRow().run()
  else if (azione === 'togliColonna') catena.deleteColumn().run()
  else catena.deleteTable().run()
}

async function caricaImmagine(evento: Event) {
  const input = evento.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !props.immagini) return
  const caricata = await eseguiCaricamento(() => api.caricaImmagine(file))
  if (caricata) editor.value?.chain().focus().setImage({ src: caricata.url, alt: '' }).run()
}

/** Put a placeholder where the cursor is (the settings page calls it). */
function inserisci(testo: string) {
  editor.value?.chain().focus().insertContent(testo).run()
}

defineExpose({ inserisci })

const PULSANTI = [
  { nome: 'Grassetto', icona: 'type-bold', comando: 'toggleBold', attivo: 'bold' },
  { nome: 'Corsivo', icona: 'type-italic', comando: 'toggleItalic', attivo: 'italic' },
  {
    nome: 'Sottolineato',
    icona: 'type-underline',
    comando: 'toggleUnderline',
    attivo: 'underline',
  },
  { nome: 'Elenco puntato', icona: 'list-ul', comando: 'toggleBulletList', attivo: 'bulletList' },
  {
    nome: 'Elenco numerato',
    icona: 'list-ol',
    comando: 'toggleOrderedList',
    attivo: 'orderedList',
  },
] as const

function esegui(comando: (typeof PULSANTI)[number]['comando']) {
  const catena = editor.value?.chain().focus()
  if (catena) catena[comando]().run()
}
</script>

<template>
  <div>
    <span class="form-label small mb-1 d-block">{{ etichetta }}</span>
    <div class="d-flex flex-wrap gap-1 mb-1" role="toolbar" :aria-label="`Formato: ${etichetta}`">
      <button
        v-for="p in PULSANTI"
        :key="p.nome"
        type="button"
        class="btn btn-sm btn-outline theme-primary"
        :class="{ active: editor?.isActive(p.attivo) }"
        :title="p.nome"
        :aria-label="p.nome"
        :aria-pressed="!!editor?.isActive(p.attivo)"
        :disabled="modoHtml"
        @click="esegui(p.comando)"
      >
        <Icona :nome="p.icona" />
      </button>
      <button
        v-for="a in ALLINEAMENTI"
        :key="a.valore"
        type="button"
        class="btn btn-sm btn-outline theme-primary"
        :class="{ active: editor?.isActive({ textAlign: a.valore }) }"
        :title="a.nome"
        :aria-label="a.nome"
        :aria-pressed="!!editor?.isActive({ textAlign: a.valore })"
        :disabled="modoHtml"
        @click="allinea(a.valore)"
      >
        <Icona :nome="a.icona" />
      </button>
      <button
        type="button"
        class="btn btn-sm btn-outline theme-primary"
        :class="{ active: editor?.isActive('link') }"
        title="Link"
        aria-label="Link"
        :disabled="modoHtml"
        @click="apriLink"
      >
        <Icona nome="link-45deg" />
      </button>
      <button
        type="button"
        class="btn btn-sm btn-outline theme-primary"
        title="Inserisci una tabella"
        aria-label="Inserisci una tabella"
        :disabled="modoHtml"
        @click="tabella('inserisci')"
      >
        <Icona nome="table" />
      </button>
      <template v-if="!modoHtml && editor?.isActive('table')">
        <button type="button" class="btn btn-sm btn-outline theme-primary" @click="tabella('riga')">
          + riga
        </button>
        <button
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          @click="tabella('colonna')"
        >
          + colonna
        </button>
        <button
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          @click="tabella('togliRiga')"
        >
          − riga
        </button>
        <button
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          @click="tabella('togliColonna')"
        >
          − colonna
        </button>
        <button
          type="button"
          class="btn btn-sm btn-outline theme-danger"
          title="Elimina la tabella"
          aria-label="Elimina la tabella"
          @click="tabella('elimina')"
        >
          <Icona nome="trash3" />
        </button>
      </template>
      <label
        v-if="immagini"
        class="btn btn-sm btn-outline theme-primary mb-0"
        title="Inserisci un'immagine (PNG o JPEG)"
        :class="{ disabled: caricaInCorso || modoHtml }"
      >
        <Icona nome="image" />
        <span class="visually-hidden">Inserisci un'immagine</span>
        <input type="file" accept="image/png,image/jpeg" class="d-none" @change="caricaImmagine" />
      </label>
      <button
        type="button"
        class="btn btn-sm btn-outline theme-primary"
        :class="{ active: modoHtml }"
        :aria-pressed="modoHtml"
        title="Modifica l'HTML"
        @click="alternaHtml"
      >
        <Icona nome="code-slash" /> HTML
      </button>
    </div>
    <div
      v-if="!modoHtml && editor?.isActive('image')"
      class="d-flex flex-wrap align-items-center gap-1 mb-1"
      role="group"
      aria-label="Dimensione dell'immagine"
    >
      <span class="small fg-2 me-1">Immagine:</span>
      <button
        v-for="m in MISURE"
        :key="m.nome"
        type="button"
        class="btn btn-sm btn-outline theme-primary"
        :class="{ active: (editor?.getAttributes('image').width ?? null) === m.larghezza }"
        @click="misura(m.larghezza)"
      >
        {{ m.nome }}
      </button>
    </div>
    <div v-if="tolti.length" class="alert theme-warning small" role="status">
      <div>
        Alcune parti dell'HTML non sono permesse e sono state tolte: {{ tolti.join(', ') }}.
      </div>
    </div>
    <form v-if="chiediLink" class="d-flex gap-3 mb-1" @submit.prevent="applicaLink">
      <input
        v-model="indirizzo"
        type="url"
        class="form-control form-control-sm"
        placeholder="https://… (vuoto per togliere il link)"
        aria-label="Indirizzo del link"
      />
      <button type="submit" class="btn btn-sm btn-solid theme-primary">Applica</button>
      <button type="button" class="btn btn-sm btn-link" @click="chiediLink = false">Annulla</button>
    </form>
    <div v-if="erroreImmagine" class="alert theme-danger small" role="alert">
      {{ erroreImmagine }}
    </div>
    <textarea
      v-if="modoHtml"
      v-model="codice"
      class="form-control font-monospace small qdc-editor-testo"
      rows="12"
      spellcheck="false"
      :aria-label="`HTML: ${etichetta}`"
    />
    <EditorContent v-show="!modoHtml" :editor="editor" />
  </div>
</template>
