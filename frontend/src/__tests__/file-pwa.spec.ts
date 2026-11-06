import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import FileDaSalvare from '@/components/FileDaSalvare.vue'
import { fileInArrivo, linkAFile, nomeDelFile, salvaFile, scaricaFile } from '@/pwa/file'

function suIphone(installata: boolean) {
  Object.defineProperty(navigator, 'standalone', { value: installata, configurable: true })
  Object.defineProperty(navigator, 'maxTouchPoints', { value: 5, configurable: true })
}

function suMac() {
  Object.defineProperty(navigator, 'standalone', { value: true, configurable: true })
  Object.defineProperty(navigator, 'maxTouchPoints', { value: 0, configurable: true })
}

function clic(href: string, opzioni: MouseEventInit = {}): MouseEvent {
  const link = document.createElement('a')
  link.href = href
  const evento = new MouseEvent('click', { bubbles: true, cancelable: true, ...opzioni })
  Object.defineProperty(evento, 'target', { value: link })
  return evento
}

beforeEach(() => {
  // jsdom has no modal dialogs.
  HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) {
    this.open = true
  })
  HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) {
    this.open = false
  })
})

afterEach(() => {
  fileInArrivo.value = null
  Reflect.deleteProperty(navigator, 'standalone')
  Reflect.deleteProperty(navigator, 'maxTouchPoints')
  Reflect.deleteProperty(navigator, 'share')
  Reflect.deleteProperty(navigator, 'canShare')
  vi.unstubAllGlobals()
  document.body.innerHTML = ''
})

describe('i link ai file', () => {
  it('riconosce solo i link ai file dell app', () => {
    expect(linkAFile(clic('/api/v1/pagamenti/1/ricevuta.pdf'))).not.toBeNull()
    expect(linkAFile(clic('/eventi'))).toBeNull()
    expect(linkAFile(clic('https://www.paypal.com/api/v1/x'))).toBeNull()
    expect(linkAFile(clic('/api/v1/x.pdf', { metaKey: true }))).toBeNull()
  })

  it('ricava il nome del file', () => {
    const risposta = (intestazioni: Record<string, string>) =>
      new Response('', { headers: intestazioni })
    expect(
      nomeDelFile(
        risposta({ 'Content-Disposition': 'attachment; filename="presenze-3.pdf"' }),
        '/api/v1/x',
      ),
    ).toBe('presenze-3.pdf')
    expect(
      nomeDelFile(
        risposta({ 'Content-Disposition': "attachment; filename*=UTF-8''modulo%20uno.pdf" }),
        '/api/v1/x',
      ),
    ).toBe('modulo uno.pdf')
    expect(
      nomeDelFile(
        risposta({ 'Content-Type': 'application/pdf' }),
        '/api/v1/segnalazioni/4/ricevuta',
      ),
    ).toBe('ricevuta.pdf')
  })
})

describe('il file sull iPhone', () => {
  it('con l app installata resta nell app e si condivide con un secondo tocco', async () => {
    suIphone(true)
    const fetch = vi.fn(
      async () =>
        new Response(new Blob(['%PDF'], { type: 'application/pdf' }), {
          headers: { 'Content-Disposition': 'attachment; filename="incarichi.pdf"' },
        }),
    )
    vi.stubGlobal('fetch', fetch)
    const share = vi.fn(async () => undefined)
    Object.defineProperty(navigator, 'share', { value: share, configurable: true })
    Object.defineProperty(navigator, 'canShare', { value: () => true, configurable: true })
    const pagina = mount(FileDaSalvare, { attachTo: document.body })

    const link = document.createElement('a')
    link.href = '/api/v1/gruppo/incarichi/elenco.pdf'
    document.body.append(link)
    const evento = new MouseEvent('click', { bubbles: true, cancelable: true })
    link.dispatchEvent(evento)
    expect(evento.defaultPrevented).toBe(true)
    await flushPromises()

    expect(fetch).toHaveBeenCalledTimes(1)
    expect(share).not.toHaveBeenCalled()
    expect(pagina.text()).toContain('incarichi.pdf')
    await pagina.find('button.theme-primary').trigger('click')
    await flushPromises()
    const dati = (share.mock.calls as unknown as [{ files: File[] }][])[0]![0]
    expect(dati.files[0]!.name).toBe('incarichi.pdf')
    expect(fileInArrivo.value).toBeNull()
    pagina.unmount()
  })

  it('un file molto grande non si scarica in memoria', async () => {
    suIphone(true)
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    const pagina = mount(FileDaSalvare, { attachTo: document.body })
    const link = document.createElement('a')
    link.href = '/api/v1/allegati-verbale/1'
    link.dataset.dimensione = String(1024 ** 3)
    document.body.append(link)
    const evento = new MouseEvent('click', { bubbles: true, cancelable: true })
    link.dispatchEvent(evento)
    await nextTick()
    expect(evento.defaultPrevented).toBe(true)
    expect(fetch).not.toHaveBeenCalled()
    expect(pagina.text()).toContain('troppo grande')
    pagina.unmount()
  })

  it('nel browser e sugli altri dispositivi il link funziona come sempre', async () => {
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    const pagina = mount(FileDaSalvare, { attachTo: document.body })
    const link = document.createElement('a')
    link.href = '/api/v1/gruppo/incarichi/elenco.pdf'
    link.addEventListener('click', (e) => {
      expect(e.defaultPrevented).toBe(false)
      e.preventDefault() // jsdom cannot navigate.
    })
    document.body.append(link)
    link.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))
    await nextTick()
    expect(fetch).not.toHaveBeenCalled()
    pagina.unmount()
  })

  it('nell app installata su un Mac il file si scarica come sempre', async () => {
    suMac()
    const pagina = mount(FileDaSalvare, { attachTo: document.body })
    const link = document.createElement('a')
    link.href = '/api/v1/documenti/1/file'
    link.addEventListener('click', (e) => {
      expect(e.defaultPrevented).toBe(false)
      e.preventDefault() // jsdom cannot navigate.
    })
    document.body.append(link)
    link.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))
    await nextTick()
    expect(fileInArrivo.value).toBeNull()

    const clicSulLink = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    URL.createObjectURL = vi.fn(() => 'blob:prova')
    URL.revokeObjectURL = vi.fn()
    salvaFile(new Blob(['BEGIN:VCARD']), 'contatti.vcf')
    expect(fileInArrivo.value).toBeNull()
    expect(clicSulLink).toHaveBeenCalled()

    clicSulLink.mockRestore()
    link.remove()
    pagina.unmount()
  })

  it('spiega perché il file non arriva', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('', { status: 403 })),
    )
    const pagina = mount(FileDaSalvare, { attachTo: document.body })
    await scaricaFile('/api/v1/segreto.pdf')
    await nextTick()
    expect(pagina.text()).toContain('Non hai i permessi')
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('rete')
      }),
    )
    await scaricaFile('/api/v1/x.pdf')
    await nextTick()
    expect(pagina.text()).toContain('Connessione assente')
    pagina.unmount()
  })

  it('chiudere durante lo scaricamento non riapre la finestra', async () => {
    let arriva: (r: Response) => void = () => undefined
    vi.stubGlobal(
      'fetch',
      vi.fn(() => new Promise<Response>((r) => (arriva = r))),
    )
    const corso = scaricaFile('/api/v1/x.pdf')
    fileInArrivo.value = null
    arriva(new Response('x'))
    await corso
    expect(fileInArrivo.value).toBeNull()
  })

  it('avvisa se il telefono non può condividere quel tipo di file', async () => {
    Object.defineProperty(navigator, 'canShare', { value: () => false, configurable: true })
    const pagina = mount(FileDaSalvare, { attachTo: document.body })
    fileInArrivo.value = { stato: 'pronto', file: new File(['x'], 'a.xlsx') }
    await nextTick()
    await pagina.find('button.theme-primary').trigger('click')
    expect(pagina.text()).toContain('non può condividere')
    pagina.unmount()
  })

  it('i file creati dalla pagina passano dalla stessa finestra', () => {
    suIphone(true)
    salvaFile(new Blob(['BEGIN:VCARD'], { type: 'text/vcard' }), 'contatti.vcf')
    const arrivo = fileInArrivo.value
    expect(arrivo?.stato === 'pronto' && arrivo.file.name).toBe('contatti.vcf')
  })
})
