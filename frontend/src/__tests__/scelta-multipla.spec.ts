import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import SceltaMultipla from '@/components/SceltaMultipla.vue'

const SCELTE = [
  { valore: 'A', nome: 'Capogruppo' },
  { valore: 'B', nome: 'Staff' },
  { valore: 'C', nome: 'Tesoriere' },
]

const monta = (valori: string[]) =>
  mount(SceltaMultipla, {
    attachTo: document.body,
    props: {
      id: 'prova',
      scelte: SCELTE,
      modelValue: valori,
      'onUpdate:modelValue': (v: string[]) => monta.ultimo.push(v),
    },
  })
monta.ultimo = [] as string[][]

describe('SceltaMultipla', () => {
  it('sums up the choice in Italian', async () => {
    const scelta = monta(['A', 'B', 'C'])
    expect(scelta.get('.combobox-value').text()).toBe('Tutti')
    await scelta.setProps({ modelValue: ['B'] })
    expect(scelta.get('.combobox-value').text()).toBe('Staff')
    await scelta.setProps({ modelValue: ['A', 'C'] })
    expect(scelta.get('.combobox-value').text()).toBe('2 scelti su 3')
    await scelta.setProps({ modelValue: [] })
    expect(scelta.get('.combobox-value').text()).toBe('Nessuno')
    scelta.unmount()
  })

  it('ticks and unticks, keeping the order of the list', async () => {
    monta.ultimo = []
    const scelta = monta(['C'])
    const voci = scelta.findAll('[role="option"]')
    expect(voci[2]!.attributes('aria-selected')).toBe('true')
    await voci[0]!.trigger('click')
    expect(monta.ultimo.at(-1)).toEqual(['A', 'C'])
    await voci[2]!.trigger('click')
    expect(monta.ultimo.at(-1)).toEqual([])
    scelta.unmount()
  })

  it('chooses all or none at once', async () => {
    monta.ultimo = []
    const scelta = monta(['B'])
    const [tutti, nessuno] = scelta.findAll('.menu button.btn-link')
    await tutti!.trigger('click')
    expect(monta.ultimo.at(-1)).toEqual(['A', 'B', 'C'])
    await nessuno!.trigger('click')
    expect(monta.ultimo.at(-1)).toEqual([])
    scelta.unmount()
  })
})
