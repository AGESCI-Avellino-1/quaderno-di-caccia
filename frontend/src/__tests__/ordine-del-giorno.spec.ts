import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ErroreApi } from '@/api/http'
import { api } from '@/api/qdc'
import OrdineDelGiorno from '@/components/OrdineDelGiorno.vue'

afterEach(() => vi.restoreAllMocks())

async function monta() {
  const pagina = mount(OrdineDelGiorno, { props: { evento: 7 } })
  await flushPromises()
  return pagina
}

describe('OrdineDelGiorno', () => {
  it('mostra il testo a chi legge, senza il pulsante per cambiarlo', async () => {
    vi.spyOn(api, 'ordineDelGiorno').mockResolvedValue({
      testo: '<p>Programma</p>',
      puo_scrivere: false,
    })
    const pagina = await monta()
    expect(pagina.text()).toContain('Programma')
    expect(pagina.find('button').exists()).toBe(false)
  })

  it('chi gestisce la riunione può scriverlo', async () => {
    vi.spyOn(api, 'ordineDelGiorno').mockResolvedValue({ testo: '', puo_scrivere: true })
    const pagina = await monta()
    expect(pagina.text()).toContain('Non è ancora stato scritto')
    expect(pagina.find('button').text()).toBe('Scrivilo')
  })

  it('senza la rete dice che serve', async () => {
    vi.spyOn(api, 'ordineDelGiorno').mockRejectedValue(new TypeError('Failed to fetch'))
    const pagina = await monta()
    expect(pagina.text()).toContain('Per leggerlo serve la rete')
  })

  it('a chi non può leggerlo non mostra nulla', async () => {
    vi.spyOn(api, 'ordineDelGiorno').mockRejectedValue(new ErroreApi(404, null))
    const pagina = await monta()
    expect(pagina.text()).toBe('')
  })
})
