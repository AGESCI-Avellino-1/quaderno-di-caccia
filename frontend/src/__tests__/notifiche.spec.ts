import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import InvitoNotifiche from '@/components/InvitoNotifiche.vue'
import NotifichePush from '@/components/NotifichePush.vue'
import { chiudiInvito, invitoChiuso, notificheSupportate } from '@/pwa/notifiche'

import { risposta } from './aiuti'

const stato = {
  disponibili: true,
  chiave_pubblica: 'BQ',
  questo_browser: false,
  preferenze: { eventi: true, promemoria_quote: false, riepiloghi: true, avvisi: true },
}

function stub(dati: unknown) {
  const chiamate: { url: string; metodo: string; corpo: unknown }[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, opzioni?: RequestInit) => {
      chiamate.push({ url, metodo: opzioni?.method ?? 'GET', corpo: opzioni?.body })
      return risposta(200, dati)
    }),
  )
  return chiamate
}

beforeEach(() => setActivePinia(createPinia()))
afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
})

describe('preferenze delle notifiche', () => {
  it('senza supporto spiega come fare su iPhone', async () => {
    stub(stato)
    expect(notificheSupportate()).toBe(false)
    const w = mount(NotifichePush)
    await flushPromises()
    expect(w.text()).toContain('Aggiungi alla schermata Home')
    expect(w.text()).not.toContain('Attiva su questo dispositivo')
  })

  it('mostra e salva le scelte per persona; niente voci dei capi a chi non lo è', async () => {
    const chiamate = stub(stato)
    const w = mount(NotifichePush)
    await flushPromises()
    expect((w.find('#push-promemoria_quote').element as HTMLInputElement).checked).toBe(false)
    expect(w.find('#push-riepiloghi').exists()).toBe(false)
    await w.find('#push-avvisi').setValue(false)
    await w.find('form').trigger('submit')
    await flushPromises()
    const salvata = chiamate.find((c) => c.metodo === 'PUT')!
    expect(salvata.url).toBe('/api/v1/push/preferenze')
    expect(JSON.parse(salvata.corpo as string).avvisi).toBe(false)
  })

  it('se l’installazione non le ha, non mostra nulla', async () => {
    stub({ ...stato, disponibili: false, chiave_pubblica: '' })
    const w = mount(NotifichePush)
    await flushPromises()
    expect(w.text()).toBe('')
  })
})

describe('invito', () => {
  it('fuori dall’app installata non compare e non chiede nulla', async () => {
    const chiamate = stub(stato)
    const w = mount(InvitoNotifiche)
    await flushPromises()
    expect(w.text()).toBe('')
    expect(chiamate).toHaveLength(0)
  })

  it('chiuso, torna solo dopo un mese', () => {
    const adesso = new Date('2026-11-04T10:00:00Z')
    expect(invitoChiuso(adesso.getTime())).toBe(false)
    chiudiInvito(adesso)
    expect(invitoChiuso(adesso.getTime() + 24 * 3600 * 1000)).toBe(true)
    expect(invitoChiuso(adesso.getTime() + 31 * 24 * 3600 * 1000)).toBe(false)
  })
})
