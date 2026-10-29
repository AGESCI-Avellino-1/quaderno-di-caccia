import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { Sanitarie } from '@/api/qdc'
import SchedaSanitaria from '@/components/SchedaSanitaria.vue'

const dati = (altro: Partial<Sanitarie> = {}): Sanitarie => ({
  compilate: true,
  nessuna_allergia: true,
  nessun_farmaco: true,
  esigenze_alimentari: 'Vegetariana',
  allergie: [],
  farmaci: [],
  inserite_da: 'Genitore',
  aggiornate_il: null,
  puo_modificare: false,
  ...altro,
})

describe('SchedaSanitaria', () => {
  it('shows the dietary needs, also in the compact camp card', () => {
    expect(mount(SchedaSanitaria, { props: { dati: dati() } }).text()).toContain(
      'Esigenze alimentari',
    )
    const compatta = mount(SchedaSanitaria, { props: { dati: dati(), compatta: true } })
    expect(compatta.text()).toContain('A tavola: Vegetariana')
  })

  it('says nothing when there are none', () => {
    const scheda = mount(SchedaSanitaria, { props: { dati: dati({ esigenze_alimentari: '' }) } })
    expect(scheda.text()).not.toContain('Esigenze alimentari')
  })
})
