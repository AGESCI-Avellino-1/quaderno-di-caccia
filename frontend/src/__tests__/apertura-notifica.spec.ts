import { describe, expect, it } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { apri, percorsoInterno } from '@/pwa/aperturaNotifica'

// The page of a tapped notification with the app open (#74).
const Vuota = { template: '<div />' }

function router(bloccata: boolean) {
  const r = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: Vuota },
      { path: '/sblocco', name: 'sblocco', component: Vuota },
      { path: '/eventi/:id', name: 'evento', component: Vuota },
      { path: '/persone/:id', name: 'persona', component: Vuota },
    ],
  })
  // As the real guard: locked, every page waits for the unlock.
  r.beforeEach((verso) => {
    if (bloccata && verso.name !== 'sblocco') {
      return { name: 'sblocco', query: { prossima: verso.fullPath } }
    }
    return true
  })
  return r
}

describe('notification page', () => {
  it('accepts only the paths of the app', () => {
    expect(percorsoInterno('/eventi/3')).toBe('/eventi/3')
    expect(percorsoInterno('https://altro.example/')).toBeNull()
    expect(percorsoInterno('//altro.example/x')).toBeNull()
    expect(percorsoInterno('/\\altro.example')).toBeNull()
    expect(percorsoInterno(42)).toBeNull()
  })

  it('unlocked, goes straight to the page', async () => {
    const r = router(false)
    await r.push('/persone/5')
    await apri(r, '/eventi/3')
    expect(r.currentRoute.value.fullPath).toBe('/eventi/3')
  })

  it('locked, the page becomes the one after unlocking', async () => {
    const r = router(true)
    await r.push('/persone/5') // the guard already sent it to the unlock, with the last page
    expect(r.currentRoute.value.query.prossima).toBe('/persone/5')
    await apri(r, '/eventi/3')
    expect(r.currentRoute.value.name).toBe('sblocco')
    expect(r.currentRoute.value.query.prossima).toBe('/eventi/3')
  })
})
