import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Impostazioni } from '@/api/qdc'
import ServerPosta from '@/components/ServerPosta.vue'

import { risposta } from './aiuti'

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ replace: vi.fn() }),
}))

afterEach(() => vi.unstubAllGlobals())

async function provaNotifica(esiti: unknown) {
  const chiamate: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, opzioni?: RequestInit) => {
      chiamate.push(`${opzioni?.method ?? 'GET'} ${url}`)
      return risposta(200, esiti)
    }),
  )
  const pagina = mount(ServerPosta, { props: { impostazioni: {} as Impostazioni } })
  await pagina
    .findAll('button')
    .find((b) => b.text() === 'Manda una notifica di prova a me')!
    .trigger('click')
  await flushPromises()
  return { pagina, chiamate }
}

describe('ServerPosta: notifica di prova', () => {
  it('mostra l esito di ogni dispositivo', async () => {
    const { pagina, chiamate } = await provaNotifica([
      { servizio: 'Apple', accettata: true, codice: 201 },
      { servizio: 'Google', accettata: false, codice: 403 },
      { servizio: 'Mozilla', accettata: false, codice: null },
    ])
    expect(chiamate).toContain('POST /api/v1/push/prova')
    expect(pagina.text()).toContain('Apple: accettata.')
    expect(pagina.text()).toContain('Google: rifiutata (codice 403).')
    expect(pagina.text()).toContain('Mozilla: servizio non raggiungibile.')
  })

  it('dice se nessun dispositivo ha le notifiche attive', async () => {
    const { pagina } = await provaNotifica([])
    expect(pagina.text()).toContain('Nessun tuo dispositivo ha le notifiche attive')
  })
})
