import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import AccountPersona from '@/components/AccountPersona.vue'

const json = (dati: unknown, stato = 200) =>
  new Response(JSON.stringify(dati), {
    status: stato,
    headers: { 'Content-Type': 'application/json' },
  })

const scheda = (id: number, nome: string, altro: object = {}) => ({
  id,
  nome,
  cognome: 'Prova',
  ha_account: false,
  puo_invitare: true,
  richiede_consenso_genitore: false,
  email: null,
  inviti: [],
  ...altro,
})

const stato = {
  persona: scheda(1, 'Luca', {
    richiede_consenso_genitore: true,
    email: 'luca@example.invalid',
  }),
  genitori: [scheda(2, 'Lucia', { ha_account: true })],
  metodi_consenso: [{ valore: 'IN_PRESENZA', etichetta: 'In presenza, davanti a un capo' }],
}

afterEach(() => vi.unstubAllGlobals())

describe('AccountPersona', () => {
  it('stays hidden when the server says the user may not invite', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => json({ detail: 'Persona non trovata.' }, 404)),
    )
    const pannello = mount(AccountPersona, { props: { id: 1 } })
    await flushPromises()
    expect(pannello.html()).not.toContain('Accesso')
  })

  it('invites a child under 14 with their own email and parental consent', async () => {
    const chiamate: { url: string; corpo: unknown }[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, opzioni?: RequestInit) => {
        if (opzioni?.method === 'POST') {
          chiamate.push({ url, corpo: JSON.parse(opzioni.body as string) })
          return json({ id: 9 }, 201)
        }
        return json(stato)
      }),
    )
    const pannello = mount(AccountPersona, { props: { id: 1 } })
    await flushPromises()

    expect(pannello.text()).toContain('Nessun account')
    expect(pannello.text()).toContain('Ha un account')
    await pannello.get('button.btn-outline.theme-primary').trigger('click')
    // Their own address is proposed and the only parent preselected (DEC-24).
    expect((pannello.get('input[type=email]').element as HTMLInputElement).value).toBe(
      'luca@example.invalid',
    )
    expect(pannello.text()).toContain('serve il consenso di un genitore')
    await pannello.get('select[aria-label="Come è stato verificato"]').setValue('IN_PRESENZA')
    await pannello.get('form').trigger('submit')
    await flushPromises()

    expect(chiamate).toEqual([
      {
        url: '/api/v1/inviti',
        corpo: {
          persona_id: 1,
          email: 'luca@example.invalid',
          consenso_genitore_da_id: 2,
          consenso_genitore_metodo: 'IN_PRESENZA',
        },
      },
    ])
    expect(pannello.text()).toContain('Invito inviato a luca@example.invalid')
  })

  it("offers consent through the parent's account only if the parent has one", async () => {
    const conDueMetodi = {
      ...stato,
      genitori: [scheda(2, 'Lucia', { ha_account: true }), scheda(3, 'Mario')],
      metodi_consenso: [
        { valore: 'ACCOUNT_GENITORE', etichetta: "Dall'account del genitore collegato" },
        { valore: 'IN_PRESENZA', etichetta: 'In presenza, davanti a un capo' },
      ],
    }
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => json(conDueMetodi)),
    )
    const pannello = mount(AccountPersona, { props: { id: 1 } })
    await flushPromises()
    await pannello
      .findAll('button')
      .find((b) => b.text() === 'Invita')!
      .trigger('click')
    const metodi = () =>
      pannello.findAll('select[aria-label="Come è stato verificato"] option').map((o) => o.text())

    await pannello.get('select[aria-label="Genitore che dà il consenso"]').setValue(2)
    expect(metodi()).toContain("Dall'account del genitore collegato")
    await pannello.get('select[aria-label="Genitore che dà il consenso"]').setValue(3)
    expect(metodi()).not.toContain("Dall'account del genitore collegato")
  })
})
