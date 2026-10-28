import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import DerogheSquadriglia from '@/components/DerogheSquadriglia.vue'

import { risposta } from './aiuti'

const deroga = {
  id: 4,
  reparto: 'Reparto Prova',
  sesso_squadriglia: 'F',
  squadriglie_ammesse: 'Femminili',
  data_decisione: '2026-10-20',
  motivazione: 'Decisione della Co.Ca.',
  registrata_da: 'cg@example.invalid',
  revocata_il: null,
  valida: true,
}

function stubFetch(
  lettura: unknown,
  stato = 200,
  chiamate: { url: string; corpo: unknown }[] = [],
) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, opzioni?: RequestInit) => {
      if (opzioni?.method === 'POST') {
        chiamate.push({ url, corpo: JSON.parse((opzioni.body as string) ?? 'null') })
        return risposta(201, deroga)
      }
      return risposta(stato, lettura)
    }),
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('DerogheSquadriglia', () => {
  it('stays hidden from whoever is not a capo', async () => {
    stubFetch({ detail: 'Persona non trovata.' }, 404)
    const pannello = mount(DerogheSquadriglia, { props: { id: 1 } })
    await flushPromises()
    expect(pannello.html()).not.toContain('Eccezioni')
  })

  it('stays hidden for a capo when there is nothing to show or record', async () => {
    stubFetch({ deroghe: [], puo_gestire: false, reparti: [{ valore: '5', etichetta: 'R' }] })
    const pannello = mount(DerogheSquadriglia, { props: { id: 1 } })
    await flushPromises()
    expect(pannello.html()).not.toContain('Eccezioni')
  })

  it('shows the exception to a capo, without revoking', async () => {
    stubFetch({ deroghe: [deroga], puo_gestire: false, reparti: [] })
    const pannello = mount(DerogheSquadriglia, { props: { id: 1 } })
    await flushPromises()
    expect(pannello.text()).toContain('Squadriglie femminili')
    expect(pannello.text()).toContain('In vigore')
    expect(pannello.text()).not.toContain('revoca')
    expect(pannello.text()).not.toContain('Registra')
  })

  it('lets a capogruppo record the Co.Ca. decision', async () => {
    const chiamate: { url: string; corpo: unknown }[] = []
    stubFetch(
      { deroghe: [], puo_gestire: true, reparti: [{ valore: '5', etichetta: 'Reparto Prova' }] },
      200,
      chiamate,
    )
    const pannello = mount(DerogheSquadriglia, { props: { id: 1 } })
    await flushPromises()
    await pannello.get('button.btn-outline-primary').trigger('click')
    await pannello.get('#deroga-sesso').setValue('M')
    await pannello.get('#deroga-data').setValue('2026-10-20')
    await pannello.get('#deroga-motivazione').setValue('Decisione della Co.Ca.')
    await pannello.get('form').trigger('submit')
    await flushPromises()
    expect(chiamate).toEqual([
      {
        url: '/api/v1/persone/1/deroghe-squadriglia',
        corpo: {
          reparto_id: 5,
          sesso_squadriglia: 'M',
          data_decisione: '2026-10-20',
          motivazione: 'Decisione della Co.Ca.',
        },
      },
    ])
  })
})
