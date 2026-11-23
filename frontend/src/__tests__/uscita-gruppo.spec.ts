import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ErroreApi } from '@/api/http'
import { api, type UscitaGruppo } from '@/api/qdc'
import UscitaGruppoCard from '@/components/UscitaGruppo.vue'

// DEC-420
const PRIMA: UscitaGruppo = {
  puo_registrare: true,
  quote: [
    { id: 7, descrizione: 'Censimento', importo: '40.00' },
    { id: 8, descrizione: 'Campo', importo: '150.00' },
  ],
  uscita: null,
}
const DOPO: UscitaGruppo = {
  puo_registrare: false,
  quote: [],
  uscita: {
    data: '2026-11-20',
    registrata_il: '2026-11-23T10:00:00Z',
    registrata_da: 'Anna Capo',
    stato: 'Da inoltrare alla segreteria',
    puo_annullare: true,
  },
}

afterEach(() => vi.restoreAllMocks())

describe('leaving the group', () => {
  it('records the exit with the fees left ticked', async () => {
    vi.spyOn(api, 'uscita').mockResolvedValue(PRIMA)
    const registra = vi.spyOn(api, 'registraUscita').mockResolvedValue(DOPO)
    const scheda = mount(UscitaGruppoCard, { props: { persona: 10, nome: 'Giulia' } })
    await flushPromises()
    await scheda.find('button').trigger('click')
    // Both fees ticked: untick the camp, it stays to pay.
    await scheda.find('#uscita-quota-8').setValue(false)
    await scheda.find('input[type="date"]').setValue('2026-11-20')
    await scheda.find('form').trigger('submit')
    await flushPromises()
    expect(registra).toHaveBeenCalledWith(10, '2026-11-20', [7])
    expect(scheda.text()).toContain('ha lasciato il gruppo il 20/11/2026')
    expect(scheda.emitted('cambiato')).toHaveLength(1)
  })

  it('undoes it after asking', async () => {
    vi.spyOn(api, 'uscita').mockResolvedValue(DOPO)
    const annulla = vi.spyOn(api, 'annullaUscita').mockResolvedValue(PRIMA)
    const scheda = mount(UscitaGruppoCard, { props: { persona: 10, nome: 'Giulia' } })
    await flushPromises()
    expect(scheda.text()).toContain('da inoltrare alla segreteria')
    await scheda.find('button').trigger('click')
    await scheda
      .findAll('button')
      .find((b) => b.text() === "Annulla l'uscita")!
      .trigger('click')
    await flushPromises()
    expect(annulla).toHaveBeenCalledWith(10)
  })

  it('shows nothing to who may not', async () => {
    vi.spyOn(api, 'uscita').mockRejectedValue(new ErroreApi(404, 'Non trovato.'))
    const scheda = mount(UscitaGruppoCard, { props: { persona: 10, nome: 'Giulia' } })
    await flushPromises()
    expect(scheda.html()).toBe('<!--v-if-->')
  })
})
