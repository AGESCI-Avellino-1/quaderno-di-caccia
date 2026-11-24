import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { api, type ModelloEmailBreve } from '@/api/qdc'
import ModelliEmailView from '@/views/ModelliEmailView.vue'

const stubs = { RouterLink: { props: ['to'], template: '<a><slot /></a>' } }

const modello = (chiave: string, gruppo: string, extra = {}): ModelloEmailBreve => ({
  chiave,
  nome: chiave,
  descrizione: '',
  personalizzato: false,
  da_correggere: false,
  gruppo,
  ...extra,
})

describe('Modelli delle email', () => {
  afterEach(() => vi.restoreAllMocks())

  it('groups the templates in closed sections, one open at a time', async () => {
    vi.spyOn(api, 'modelliEmail').mockResolvedValue([
      modello('invito', 'Account e accesso', { personalizzato: true }),
      modello('codice_accesso', 'Account e accesso'),
      modello('ricevuta', 'Quote e spese', { personalizzato: true, da_correggere: true }),
    ])
    const pagina = mount(ModelliEmailView, { global: { stubs } })
    await flushPromises()
    const gruppi = pagina.findAll('details')
    expect(gruppi.map((g) => g.findAll('summary span span').map((x) => x.text()))).toEqual([
      ['2 modelli', '1 personalizzato'],
      ['1 modello', '1 da correggere', '1 personalizzato'],
    ])
    // All closed, and the same name: the browser keeps only one open.
    expect(gruppi.every((g) => !g.attributes('open'))).toBe(true)
    expect(new Set(gruppi.map((g) => g.attributes('name')))).toEqual(new Set(['modelli-email']))
    expect(gruppi[0]!.findAll('.list-group-item')).toHaveLength(2)
  })
})
