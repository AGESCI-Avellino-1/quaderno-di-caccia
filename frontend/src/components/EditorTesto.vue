<script setup lang="ts">
import StarterKit from '@tiptap/starter-kit'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import { onBeforeUnmount, ref, watch } from 'vue'

import Icona from '@/components/Icona.vue'

// Formatted text for the email templates (DEC-250): only what an email needs (bold,
// italic, underline, lists, links, two heading levels). The server cleans the HTML
// again before saving it, so this is a convenience, not a protection.
const html = defineModel<string>({ required: true })
defineProps<{ etichetta: string }>()

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
        @click="esegui(p.comando)"
      >
        <Icona :nome="p.icona" />
      </button>
      <button
        type="button"
        class="btn btn-sm btn-outline theme-primary"
        :class="{ active: editor?.isActive('link') }"
        title="Link"
        aria-label="Link"
        @click="apriLink"
      >
        <Icona nome="link-45deg" />
      </button>
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
    <EditorContent :editor="editor" />
  </div>
</template>
