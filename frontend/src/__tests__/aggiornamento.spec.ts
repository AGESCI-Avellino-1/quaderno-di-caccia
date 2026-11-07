import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

const stato = vi.hoisted(() => ({
  registrazione: undefined as ServiceWorkerRegistration | undefined,
  aggiorna: vi.fn(async () => {}),
}))

vi.mock('virtual:pwa-register/vue', () => ({
  useRegisterSW: (opzioni: {
    onRegisteredSW: (indirizzo: string, r: ServiceWorkerRegistration) => void
  }) => {
    if (stato.registrazione) opzioni.onRegisteredSW('/sw.js', stato.registrazione)
    return {
      needRefresh: ref(false),
      offlineReady: ref(false),
      updateServiceWorker: stato.aggiorna,
    }
  },
}))

describe('versioneInferiore', () => {
  it('compares numbers, not text', async () => {
    const { versioneInferiore } = await import('@/pwa/aggiornamento')
    expect(versioneInferiore('1.9.0', '1.10.0')).toBe(true)
    expect(versioneInferiore('1.21.0', '1.21.1')).toBe(true)
    expect(versioneInferiore('1.21.0', '1.21.0')).toBe(false)
    expect(versioneInferiore('2.0.0', '1.99.0')).toBe(false)
  })

  it('an unknown version is no reason to update', async () => {
    const { versioneInferiore } = await import('@/pwa/aggiornamento')
    expect(versioneInferiore('1.21.0', '')).toBe(false)
    expect(versioneInferiore('', '1.21.0')).toBe(false)
  })
})

describe('aggiornaOra', () => {
  beforeEach(() => {
    vi.resetModules()
    stato.aggiorna.mockClear()
  })

  it('uses a version already waiting, even after «Più tardi», without checking', async () => {
    const update = vi.fn()
    stato.registrazione = { waiting: {}, update } as unknown as ServiceWorkerRegistration
    const { aggiornaOra } = await import('@/pwa/aggiornamento')
    await aggiornaOra()
    expect(update).not.toHaveBeenCalled()
    expect(stato.aggiorna).toHaveBeenCalledOnce()
  })

  it('asks the browser to check, then installs what it found', async () => {
    const registrazione = { waiting: null } as unknown as ServiceWorkerRegistration
    const { aggiornaOra, needRefresh } = await (async () => {
      stato.registrazione = registrazione
      return import('@/pwa/aggiornamento')
    })()
    registrazione.update = vi.fn(async () => {
      needRefresh.value = true
      return registrazione
    })
    await aggiornaOra()
    expect(registrazione.update).toHaveBeenCalledOnce()
    expect(stato.aggiorna).toHaveBeenCalledOnce()
  })
})
