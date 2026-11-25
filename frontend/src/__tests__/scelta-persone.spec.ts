import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import SceltaPersone from '@/components/SceltaPersone.vue'

const opzioni = [
  { id: 1, nome: 'Bianchi Anna', dettaglio: 'Co.Ca.' },
  { id: 2, nome: 'Verdi Luca', dettaglio: 'Reparto' },
  { id: 3, nome: 'Neri Sara', dettaglio: 'Reparto' },
  { id: 4, nome: 'Rossi Ugo' },
]

function monta(scelti: number[], voci = opzioni) {
  const campo = mount(SceltaPersone, {
    props: {
      id: 'p',
      opzioni: voci,
      modelValue: scelti,
      'onUpdate:modelValue': (v: number[]) => campo.setProps({ modelValue: v }),
    },
  })
  return campo
}

describe('people chosen one by one, by unit', () => {
  it('shows one unit and takes or leaves only who is shown', async () => {
    const campo = monta([1])
    const pulsante = (testo: string) => campo.findAll('button').find((b) => b.text() === testo)!
    expect(campo.findAll('option').map((o) => o.text())).toEqual([
      'Tutte le unità',
      'Co.Ca.',
      'Reparto',
    ])
    expect(pulsante('Scegli tutti')).toBeUndefined()
    await campo.get('#p-unita').setValue('Reparto')
    expect(campo.findAll('.qdc-scelta-persone input')).toHaveLength(2)
    await pulsante('Scegli tutti').trigger('click')
    expect(campo.props('modelValue')).toEqual([1, 2, 3])
    await campo.get('#p-cerca').setValue('neri')
    await pulsante('Togli tutti').trigger('click')
    expect(campo.props('modelValue')).toEqual([1, 2])
  })

  it('has no filter where there is one unit only', () => {
    expect(monta([], opzioni.slice(0, 1)).find('#p-unita').exists()).toBe(false)
  })
})
