import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import SceltaDaElenco from '@/components/SceltaDaElenco.vue'
import { coincide, opzioniDa } from '@/components/sceltaDaElenco'

const PERSONE = opzioniDa([
  { id: 1, nome: 'Giulia', cognome: 'Rossi', unita: 'Reparto Antares (N1)' },
  { id: 2, nome: 'Luca', cognome: 'Rossi', unita: 'Branco Seeonee (L1)' },
  { id: 3, nome: 'Nicolò', cognome: "D'Amato", unita: 'Co.Ca.' },
])

describe('scelta di una persona', () => {
  it('finds by name or surname, in any order, ignoring case and accents', () => {
    const trovate = (testo: string) => PERSONE.filter((o) => coincide(o, testo)).map((o) => o.id)
    expect(trovate('rossi')).toEqual([1, 2])
    expect(trovate('giu ROS')).toEqual([1])
    expect(trovate('nicolo')).toEqual([3])
    expect(trovate('')).toEqual([1, 2, 3])
  })

  it('shows the unit next to the name', async () => {
    const w = mount(SceltaDaElenco, {
      props: { id: 'p', opzioni: PERSONE, modelValue: null },
      attachTo: document.body,
    })
    await w.find('input').trigger('focus')
    expect(w.text()).toContain('Rossi Giulia · Reparto Antares (N1)')
    w.unmount()
  })

  it('chooses with arrows and Enter, and only from the list', async () => {
    const w = mount(SceltaDaElenco, {
      props: {
        id: 'p',
        opzioni: PERSONE,
        modelValue: null,
        richiesto: true,
        'onUpdate:modelValue': (v: unknown) => w.setProps({ modelValue: v as number }),
      },
      attachTo: document.body,
    })
    const campo = w.find('input')
    await campo.setValue('luca')
    await campo.trigger('input')
    await campo.trigger('keydown', { key: 'Enter' })
    expect(w.props('modelValue')).toBe(2)
    expect((campo.element as HTMLInputElement).value).toBe('Rossi Luca')
    // Writing something else undoes the choice: nothing free is accepted.
    await campo.setValue('Rossi Lu')
    await campo.trigger('input')
    expect(w.props('modelValue')).toBeNull()
    expect((campo.element as HTMLInputElement).validationMessage).toContain('Scegli')
    w.unmount()
  })

  it('with several, the chosen ones line up and leave the list', async () => {
    const w = mount(SceltaDaElenco, {
      props: {
        id: 'p',
        opzioni: PERSONE,
        modelValue: [],
        multipla: true,
        'onUpdate:modelValue': (v: unknown) => w.setProps({ modelValue: v as number[] }),
      },
      attachTo: document.body,
    })
    const campo = w.find('input')
    await campo.trigger('focus')
    await w.findAll('[role=option]')[0]!.trigger('mousedown')
    expect(w.props('modelValue')).toEqual([1])
    expect(w.findAll('[role=option]').map((o) => o.text())).not.toContain(
      'Rossi Giulia · Reparto Antares (N1)',
    )
    await w.find('[aria-label="Togli Rossi Giulia"]').trigger('click')
    expect(w.props('modelValue')).toEqual([])
    w.unmount()
  })
})

describe('scelta di una persona, cambiando idea', () => {
  it('writing over a choice keeps the text and finds the new one', async () => {
    const w = mount(SceltaDaElenco, {
      props: {
        id: 'p',
        opzioni: PERSONE,
        modelValue: 1,
        'onUpdate:modelValue': (v: unknown) => w.setProps({ modelValue: v as number }),
      },
      attachTo: document.body,
    })
    const campo = w.find('input')
    await campo.setValue('luca')
    await campo.trigger('input')
    expect((campo.element as HTMLInputElement).value).toBe('luca')
    await campo.trigger('keydown', { key: 'Enter' })
    expect(w.props('modelValue')).toBe(2)
    // Emptied from outside, as a form does after saving.
    await w.setProps({ modelValue: null })
    expect((campo.element as HTMLInputElement).value).toBe('')
    w.unmount()
  })

  it('chooses from a catalog by its code, with its own messages', async () => {
    const w = mount(SceltaDaElenco<string>, {
      props: {
        id: 's',
        opzioni: [
          { id: 'EGSP001', nome: 'Allevatore' },
          { id: 'EGSP002', nome: 'Alpinista' },
        ],
        modelValue: null,
        richiesto: true,
        avviso: "Scegli dall'elenco.",
        nessuno: 'Nessuna voce con questo nome.',
        'onUpdate:modelValue': (v: unknown) => w.setProps({ modelValue: v as string }),
      },
      attachTo: document.body,
    })
    const campo = w.find('input')
    await w.vm.$nextTick()
    // Untouched, the form does not go.
    expect((campo.element as HTMLInputElement).validationMessage).toBe("Scegli dall'elenco.")
    await campo.setValue('zzz')
    await campo.trigger('input')
    expect(w.text()).toContain('Nessuna voce con questo nome.')
    await campo.setValue('alp')
    await campo.trigger('input')
    await campo.trigger('keydown', { key: 'Enter' })
    expect(w.props('modelValue')).toBe('EGSP002')
    w.unmount()
  })

  it('keeps what is written when the list arrives late', async () => {
    const w = mount(SceltaDaElenco, {
      props: { id: 'p', opzioni: [] as typeof PERSONE, modelValue: null },
      attachTo: document.body,
    })
    const campo = w.find('input')
    await campo.setValue('luca')
    await campo.trigger('input')
    await w.setProps({ opzioni: PERSONE })
    expect((campo.element as HTMLInputElement).value).toBe('luca')
    expect(w.findAll('li[role=option]').map((o) => o.text())).toEqual([
      'Rossi Luca · Branco Seeonee (L1)',
    ])
    await campo.trigger('keydown', { key: 'Enter' })
    expect(w.emitted('update:modelValue')?.at(-1)).toEqual([2])
    w.unmount()
  })
})
