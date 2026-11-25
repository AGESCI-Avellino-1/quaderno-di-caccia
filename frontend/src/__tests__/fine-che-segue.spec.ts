import { flushPromises } from '@vue/test-utils'
import { effectScope, reactive } from 'vue'
import { describe, expect, it } from 'vitest'

import { GIORNI, MOMENTI, ORE, useFineCheSegue } from '@/composables/useFineCheSegue'

// DEC-429: the end follows the start.
function campi(inizio: string | undefined, fine: string | undefined, regole: object) {
  const m = reactive({ inizio, fine })
  effectScope().run(() =>
    useFineCheSegue({
      inizio: () => m.inizio,
      fine: () => m.fine,
      imposta: (f) => (m.fine = f),
      ...(regole as typeof ORE),
    }),
  )
  return m
}

describe('the end follows the start', () => {
  it('keeps the duration, also while the hour is being typed', async () => {
    const m = campi('16:30', '18:30', ORE)
    for (const [inizio, fine] of [
      ['02:30', '04:30'],
      ['20:30', '22:30'],
      ['23:30', '23:59'],
      ['', '23:59'],
      ['20:00', '22:00'],
    ]) {
      m.inizio = inizio!
      await flushPromises()
      expect(m.fine).toBe(fine)
    }
    m.fine = '21:00'
    await flushPromises()
    expect(m.fine).toBe('21:00')
    m.inizio = '17:00'
    await flushPromises()
    expect(m.fine).toBe('18:00')
  })

  it('proposes two hours for a new event, also past midnight', async () => {
    const m = campi('', '', MOMENTI)
    m.inizio = '2026-11-28T23:00'
    await flushPromises()
    expect(m.fine).toBe('2026-11-29T01:00')
    m.inizio = '2026-12-05T09:00'
    await flushPromises()
    expect(m.fine).toBe('2026-12-05T11:00')
  })

  it('leaves an event opened for editing as it is, then follows', async () => {
    const m = campi(undefined, undefined, MOMENTI)
    Object.assign(m, { inizio: '2027-03-27T09:00', fine: '2027-03-28T17:00' })
    await flushPromises()
    expect(m.fine).toBe('2027-03-28T17:00')
    m.inizio = '2027-04-03T09:00'
    await flushPromises()
    expect(m.fine).toBe('2027-04-04T17:00')
  })

  it('corrects an end written before the start', async () => {
    const m = campi('20:30', '18:30', ORE)
    m.inizio = '20:45'
    await flushPromises()
    expect(m.fine).toBe('22:45')
  })

  it('keeps an end written first, when it is after the start', async () => {
    const m = campi('', '', MOMENTI)
    m.fine = '2026-11-29T17:00'
    await flushPromises()
    m.inizio = '2026-11-28T09:00'
    await flushPromises()
    expect(m.fine).toBe('2026-11-29T17:00')
  })

  it('days: the same day; hours not known stay empty', async () => {
    const giorni = campi('', '', GIORNI)
    giorni.inizio = '2026-12-05'
    await flushPromises()
    expect(giorni.fine).toBe('2026-12-05')
    const ore = campi('', '', { ...ORE, proponi: false })
    ore.inizio = '09:00'
    await flushPromises()
    expect(ore.fine).toBe('')
  })
})
