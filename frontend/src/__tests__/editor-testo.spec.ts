import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import EditorTesto from '@/components/EditorTesto.vue'
import { nonPermessi } from '@/sito/html'

describe('nonPermessi', () => {
  it('names what the server will drop', () => {
    expect(
      nonPermessi(
        '<p style="text-align: center">ok</p><div>x</div><p style="color:red" class="a">y</p>' +
          '<img src="https://x.it/a.png"><img src="/api/v1/immagini/a.png" width="120">',
      ),
    ).toEqual([
      '<div>',
      'style="color:red"',
      'class="…" in <p>',
      "un'immagine non caricata nell'app",
    ])
    expect(nonPermessi('<h2 style="text-align:right">t</h2><p><strong>b</strong></p>')).toEqual([])
  })
})

describe('EditorTesto', () => {
  const monta = (testo: string) => {
    const stato = { html: testo }
    const editor = mount(EditorTesto, {
      props: {
        etichetta: 'Piè di pagina',
        modelValue: testo,
        'onUpdate:modelValue': (v: string) => {
          stato.html = v
          void editor.setProps({ modelValue: v })
        },
      },
      attachTo: document.body,
    })
    return { editor, stato }
  }

  it('aligns the text and keeps it in the HTML', async () => {
    const { editor, stato } = monta('<p>Ciao</p>')
    await flushPromises()
    await editor.get('button[aria-label="Allinea al centro"]').trigger('click')
    expect(stato.html).toBe('<p style="text-align: center;">Ciao</p>')
    editor.unmount()
  })

  it('opens the HTML, keeps what is typed and says what will be dropped', async () => {
    const { editor, stato } = monta('<p>Ciao</p>')
    await flushPromises()
    const pulsante = editor.get('button[title="Modifica l\'HTML"]')
    await pulsante.trigger('click')
    const codice = editor.get('textarea')
    expect((codice.element as HTMLTextAreaElement).value).toBe('<p>Ciao</p>')
    await codice.setValue('<p>Nuovo</p><div style="color:red">x</div>')
    // Saving now keeps what was typed.
    expect(stato.html).toBe('<p>Nuovo</p><div style="color:red">x</div>')
    expect(editor.text()).toContain('<div>')
    await pulsante.trigger('click')
    expect(editor.find('textarea').exists()).toBe(false)
    expect(stato.html).toBe('<p>Nuovo</p><p>x</p>')
    expect(editor.get('[role="status"]').text()).toContain('<div>')
    editor.unmount()
  })
})
