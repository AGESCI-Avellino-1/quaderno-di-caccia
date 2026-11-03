import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Profilo } from '@/api/qdc'
import CondividiLink from '@/components/CondividiLink.vue'
import QrCode from '@/components/QrCode.vue'
import { indirizzoListaAttesa, moduliQr, percorsoQr } from '@/navigazione/condividi'
import { useSessioneStore } from '@/stores/sessione'
import InvitaView from '@/views/InvitaView.vue'

describe('lista d’attesa da condividere', () => {
  it('links the public waiting list, the same for everybody', () => {
    expect(indirizzoListaAttesa('https://qdc.example.org')).toBe(
      'https://qdc.example.org/lista-attesa',
    )
    expect(indirizzoListaAttesa()).toBe(`${window.location.origin}/lista-attesa`)
  })

  it('draws the QR code with its finder patterns and a border', () => {
    const moduli = moduliQr('https://qdc.example.org/lista-attesa')
    // Square, version 2 or more (25 modules) plus a border of 2 on each side.
    expect(moduli.length).toBeGreaterThanOrEqual(29)
    expect(moduli.every((r) => r.length === moduli.length)).toBe(true)
    expect(moduli[0]!.some(Boolean)).toBe(false)
    // The top-left finder pattern: a dark row of 7 modules, inside the border.
    expect(moduli[2]!.slice(2, 9).every(Boolean)).toBe(true)
    expect(percorsoQr([[true, false]])).toBe('M0 0h1v1h-1z')
  })

  it('shows the QR as an image with a name', () => {
    const qr = mount(QrCode, {
      props: { valore: 'https://x.invalid', etichetta: 'QR della lista' },
    })
    expect(qr.attributes('role')).toBe('img')
    expect(qr.attributes('aria-label')).toBe('QR della lista')
    expect(qr.find('path').attributes('d')).toMatch(/^M\d/)
  })
})

describe('CondividiLink', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('copies the link', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { ...navigator, clipboard: { writeText } })
    const campo = mount(CondividiLink, { props: { url: 'https://x.invalid/l', titolo: 'L' } })
    expect(campo.text()).not.toContain('Condividi')
    await campo.find('button').trigger('click')
    await flushPromises()
    expect(writeText).toHaveBeenCalledWith('https://x.invalid/l')
    expect(campo.text()).toContain('Link copiato.')
  })

  it("uses the phone's share sheet where there is one; closing it is no error", async () => {
    const share = vi.fn().mockRejectedValue(new DOMException('chiuso', 'AbortError'))
    vi.stubGlobal('navigator', { ...navigator, share })
    const campo = mount(CondividiLink, {
      props: { url: 'https://x.invalid/l', titolo: 'Lista', testo: 'Vieni' },
    })
    await campo.find('button').trigger('click')
    await flushPromises()
    expect(share).toHaveBeenCalledWith({
      title: 'Lista',
      text: 'Vieni',
      url: 'https://x.invalid/l',
    })
    expect(campo.find('[role="alert"]').exists()).toBe(false)
  })
})

describe('InvitaView', () => {
  beforeEach(() => setActivePinia(createPinia()))

  const monta = () =>
    mount(InvitaView, { global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } } })

  it('gives link, QR and flyer to anyone; the capigruppo also the way to its text', () => {
    useSessioneStore().profilo = { capogruppo: false } as Profilo
    const pagina = monta()
    expect((pagina.find('input').element as HTMLInputElement).value).toBe(
      `${window.location.origin}/lista-attesa`,
    )
    expect(pagina.find('svg[role="img"]').exists()).toBe(true)
    expect(pagina.find('a[download]').attributes('href')).toBe('/api/v1/volantino-lista-attesa.pdf')
    expect(pagina.text()).not.toContain('Impostazioni')
    useSessioneStore().profilo = { capogruppo: true } as Profilo
    expect(monta().text()).toContain('Impostazioni')
  })
})
