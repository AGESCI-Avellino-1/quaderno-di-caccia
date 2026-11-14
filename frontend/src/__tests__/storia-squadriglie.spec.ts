import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import StoriaSquadriglieView from '@/views/StoriaSquadriglieView.vue'

import { risposta } from './aiuti'

// The patrols' history for esploratori and guide (DEC-407).
afterEach(() => vi.unstubAllGlobals())

describe('patrols history', () => {
  it('lists the patrols of today and of the past, the reparto named with two', async () => {
    const reparti = [
      {
        id: 5,
        nome: 'Reparto Prova',
        squadriglie: [
          { id: 1, nome: 'Aquile', sesso: 'F', attiva: true, dal: '2020-10-01', al: null },
          {
            id: 2,
            nome: 'Pantere',
            sesso: 'F',
            attiva: false,
            dal: '2015-10-01',
            al: '2026-11-14',
          },
        ],
      },
      { id: 6, nome: 'Reparto Parallelo', squadriglie: [] },
    ]
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => risposta(200, reparti)),
    )
    const pagina = mount(StoriaSquadriglieView)
    await flushPromises()
    const testo = pagina.text()
    expect(testo).toContain('Reparto Parallelo')
    expect(testo).toContain('Sq. Aquile')
    expect(testo).toContain('a oggi')
    expect(testo).toContain('Archiviata')
    expect(testo).toContain('al 14/11/2026')
  })
})
