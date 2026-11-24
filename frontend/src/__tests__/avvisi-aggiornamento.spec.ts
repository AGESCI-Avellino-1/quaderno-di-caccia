import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

const pronta = vi.hoisted(() => ({ valore: null as null | { value: boolean } }))

vi.mock('virtual:pwa-register/vue', () => {
  const needRefresh = ref(false)
  pronta.valore = needRefresh
  return {
    useRegisterSW: () => ({
      needRefresh,
      offlineReady: ref(false),
      updateServiceWorker: vi.fn(),
    }),
  }
})

vi.mock('vue-router', () => ({
  RouterLink: { props: ['to'], template: '<a><slot /></a>' },
}))

import AggiornamentoApp from '@/components/AggiornamentoApp.vue'
import PiePagina from '@/components/PiePagina.vue'
import { useSitoStore } from '@/stores/sito'

// DEC-424: one notice of a new version at a time.
describe('Avvisi di aggiornamento', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useSitoStore().versioneServer = '999.0.0'
    pronta.valore!.value = false
  })

  it('only the footer line while the browser has nothing ready', () => {
    const piede = mount(PiePagina)
    const riquadro = mount(AggiornamentoApp)
    expect(piede.text()).toContain('È disponibile la versione v999.0.0')
    expect(riquadro.text()).toBe('')
  })

  it('only the browser’s notice when it is ready, the line again after «Più tardi»', async () => {
    pronta.valore!.value = true
    const piede = mount(PiePagina)
    const riquadro = mount(AggiornamentoApp)
    expect(riquadro.text()).toContain('È disponibile una nuova versione')
    expect(piede.text()).not.toContain('È disponibile la versione')
    await riquadro
      .findAll('button')
      .find((b) => b.text() === 'Più tardi')!
      .trigger('click')
    expect(riquadro.text()).toBe('')
    expect(piede.text()).toContain('È disponibile la versione v999.0.0')
  })
})
