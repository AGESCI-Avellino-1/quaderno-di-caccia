import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it, vi } from 'vitest'

// The tap on a notification in the service worker (public/push-sw.js), #74.
const codice = readFileSync(resolve(__dirname, '../../public/push-sw.js'), 'utf8')

function lavoratore(finestre: object[]) {
  const ascoltatori: Record<string, (evento: unknown) => void> = {}
  const self = {
    location: { origin: 'https://qdc.example' },
    addEventListener: (tipo: string, f: (evento: unknown) => void) => (ascoltatori[tipo] = f),
    clients: {
      matchAll: vi.fn(async () => finestre),
      openWindow: vi.fn(async () => null),
    },
    registration: { showNotification: vi.fn() },
  }
  new Function('self', codice)(self)
  async function tocca(percorso: string) {
    let attesa: Promise<unknown> = Promise.resolve()
    ascoltatori.notificationclick!({
      notification: { close: vi.fn(), data: { percorso } },
      waitUntil: (p: Promise<unknown>) => (attesa = p),
    })
    await attesa
  }
  return { self, tocca }
}

describe('notification tap', () => {
  it('sends the page to the open app instead of moving it', async () => {
    const finestra = { focus: vi.fn(async () => finestra), postMessage: vi.fn(), navigate: vi.fn() }
    const { tocca } = lavoratore([finestra])
    await tocca('/eventi/3?da=notifica')
    expect(finestra.postMessage).toHaveBeenCalledWith({
      tipo: 'qdc-apri',
      percorso: '/eventi/3?da=notifica',
    })
    expect(finestra.focus).toHaveBeenCalled()
    expect(finestra.navigate).not.toHaveBeenCalled()
  })

  it('opens the app on the page when it is closed', async () => {
    const { self, tocca } = lavoratore([])
    await tocca('/eventi/3')
    expect(self.clients.openWindow).toHaveBeenCalledWith('https://qdc.example/eventi/3')
  })

  it('never leaves the app', async () => {
    const finestra = { focus: vi.fn(async () => finestra), postMessage: vi.fn() }
    const { self, tocca } = lavoratore([finestra])
    await tocca('https://altro.example/x')
    expect(finestra.postMessage).not.toHaveBeenCalled()
    expect(self.clients.openWindow).not.toHaveBeenCalled()
  })
})
