import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import TurniUnita from '@/components/TurniUnita.vue'

const json = (dati: unknown, stato = 200) =>
  new Response(JSON.stringify(dati), {
    status: stato,
    headers: { 'Content-Type': 'application/json' },
  })

const TURNI = {
  nomi: ['Pulizia'],
  rotazione: 'SETTIMANALE',
  dal: '2026-10-01',
  con_collegata: false,
  collegata: null,
  gruppi: ['Sq. Leoni', 'Sq. Volpi'],
  prossime: [
    {
      id: 9,
      inizio: '2026-11-07T16:30:00+01:00',
      turni: [{ turno: 'Pulizia', gruppo: 'Sq. Volpi' }],
    },
  ],
}

afterEach(() => vi.unstubAllGlobals())

const monta = () =>
  mount(TurniUnita, {
    props: { unita: 3 },
    global: { stubs: { RouterLink: RouterLinkStub } },
  })

describe('TurniUnita', () => {
  it('is hidden to who may not manage the turns', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => json({ detail: 'No' }, 403)),
    )
    const turni = monta()
    await flushPromises()
    expect(turni.find('section').exists()).toBe(false)
  })

  it('saves the turns one per line and shows the next meetings', async () => {
    const corpi: unknown[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, opzioni?: RequestInit) => {
        if (opzioni?.method === 'PUT') corpi.push(JSON.parse(opzioni.body as string))
        return json(TURNI)
      }),
    )
    const turni = monta()
    await flushPromises()
    expect(turni.text()).toContain('Pulizia Sq. Volpi')
    await turni.get('textarea').setValue('Pulizia\n \nPreghiera')
    await turni.get('form').trigger('submit')
    await flushPromises()
    expect(corpi[0]).toEqual({
      nomi: ['Pulizia', 'Preghiera'],
      rotazione: 'SETTIMANALE',
      dal: '2026-10-01',
      con_collegata: false,
    })
  })
})
