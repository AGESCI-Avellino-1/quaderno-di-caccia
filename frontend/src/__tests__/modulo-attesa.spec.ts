import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { nextTick } from 'vue'

import type { DatiAttesa } from '@/api/qdc'
import ModuloAttesa from '@/components/ModuloAttesa.vue'

const nato = (anni: number) => {
  const data = new Date()
  data.setFullYear(data.getFullYear() - anni)
  return data.toISOString().slice(0, 10)
}

const vuoti = (altro: Partial<DatiAttesa> = {}): DatiAttesa => ({
  nome: 'Marta',
  cognome: 'Verdi',
  sesso: 'F',
  data_nascita: '',
  luogo_nascita: 'Avellino',
  da_se: false,
  contatto_nome: '',
  contatto_cognome: '',
  telefono: '',
  email: '',
  indirizzo: '',
  comune: '',
  provincia: '',
  cap: '',
  ...altro,
})

const monta = (dati: DatiAttesa, esistente = false) =>
  mount(ModuloAttesa, { props: { modelValue: dati, prefisso: 'p', esistente } })

describe('ModuloAttesa', () => {
  it('lets the age decide: an adult has no parent to fill in, without ticking anything', async () => {
    const dati = vuoti()
    const modulo = monta(dati)
    expect(modulo.text()).toContain('Il genitore da contattare')
    dati.data_nascita = nato(19)
    await modulo.setProps({ modelValue: { ...dati } })
    await nextTick()
    expect(modulo.find('input[type="checkbox"]').exists()).toBe(false)
    expect(modulo.text()).toContain('I tuoi contatti')
    expect(modulo.find('#p-g-nome').exists()).toBe(false)
  })

  it('keeps the parent of an adult already on the list through a parent', () => {
    const modulo = monta(vuoti({ data_nascita: nato(19), contatto_nome: 'Carla' }), true)
    expect(modulo.text()).toContain('Il genitore da contattare')
    expect(modulo.find('#p-g-nome').exists()).toBe(true)
  })

  it('asks a parent for a minor', () => {
    const modulo = monta(vuoti({ data_nascita: nato(15), da_se: true }), true)
    expect(modulo.text()).toContain('Il genitore da contattare')
  })
})
