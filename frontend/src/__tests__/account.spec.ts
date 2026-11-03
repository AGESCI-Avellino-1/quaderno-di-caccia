import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import AccountView from '@/views/AccountView.vue'

const json = (dati: unknown, stato = 200) =>
  new Response(JSON.stringify(dati), {
    status: stato,
    headers: { 'Content-Type': 'application/json' },
  })

const ACCOUNT = {
  id: 5,
  email: 'mario@example.invalid',
  attivo: true,
  persona: { id: 9, nome: 'Mario', cognome: 'Rossi' },
  creato_il: '2026-10-01T10:00:00Z',
  ultimo_accesso: null,
  password: true,
  passkey: 0,
  secondo_fattore: false,
  accessi_esterni: ['google'],
  dispositivi: 0,
  bloccato: false,
  amministratore_tecnico: false,
}

afterEach(() => vi.unstubAllGlobals())

describe('AccountView', () => {
  it('offers only what applies, and sends the action with its reason', async () => {
    const chiamate: { url: string; corpo: unknown }[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, opzioni?: RequestInit) => {
        chiamate.push({ url, corpo: opzioni?.body ? JSON.parse(opzioni.body as string) : null })
        return json(url.includes('account-azioni') ? [] : [ACCOUNT])
      }),
    )
    const vista = mount(AccountView)
    await flushPromises()
    expect(vista.text()).toContain('entra con: password, Google')
    expect(vista.text()).toContain('ultimo accesso mai')

    await vista.get('button[aria-expanded]').trigger('click')
    const voci = vista.findAll('select option').map((o) => o.text())
    expect(voci).toContain('Disattiva l’account')
    expect(voci).not.toContain('Riattiva l’account')
    expect(voci).not.toContain('Togli le passkey')

    await vista.get('select').setValue('CAMBIA_EMAIL')
    const conferma = vista.get('button[type="submit"].btn-solid')
    expect(conferma.attributes('disabled')).toBeDefined()
    await vista.get('input[type="email"]').setValue('nuovo@example.invalid')
    await vista.get('input[maxlength="500"]').setValue('Ha cambiato casella')
    await vista.get('form.mt-3').trigger('submit')
    await flushPromises()
    expect(chiamate.find((c) => c.url === '/api/v1/amministrazione/account/5')?.corpo).toEqual({
      tipo: 'CAMBIA_EMAIL',
      motivo: 'Ha cambiato casella',
      email: 'nuovo@example.invalid',
    })
    expect(vista.text()).toContain('Cambia l’email: fatto per mario@example.invalid.')
  })
})
