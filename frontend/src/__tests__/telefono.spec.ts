import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import type { Profilo } from '@/api/qdc'
import Telefono from '@/components/Telefono.vue'
import { indirizziTelefono, internazionale } from '@/navigazione/telefono'
import { useSessioneStore } from '@/stores/sessione'

describe('internazionale', () => {
  it('adds +39 to a number with no international prefix', () => {
    expect(internazionale('333 123 4567')).toBe('393331234567')
    expect(internazionale('0825-123456')).toBe('390825123456')
    expect(internazionale('+39 333 1234567')).toBe('393331234567')
    expect(internazionale('0041 79 123 45 67')).toBe('41791234567')
  })

  it('gives the address of each button', () => {
    expect(indirizziTelefono('333 123 4567')).toEqual({
      chiama: 'tel:+393331234567',
      whatsapp: 'https://wa.me/393331234567',
      sms: 'sms:+393331234567',
    })
  })
})

describe('Telefono', () => {
  beforeEach(() => setActivePinia(createPinia()))

  const pulsanti = (campo: ReturnType<typeof mount>) =>
    campo.findAll('a').map((a) => a.attributes('aria-label'))

  it('shows call and WhatsApp unless the person chose otherwise', () => {
    const campo = mount(Telefono, { props: { numero: '333 123 4567', di: 'Giulia Rossi' } })
    expect(campo.text()).toContain('333 123 4567')
    expect(pulsanti(campo)).toEqual(['Chiama Giulia Rossi', 'Scrivi su WhatsApp a Giulia Rossi'])
  })

  it('shows the buttons chosen in the preferences', () => {
    useSessioneStore().profilo = { pulsanti_telefono: ['chiama', 'sms'] } as Profilo
    const campo = mount(Telefono, { props: { numero: '333 123 4567' } })
    expect(pulsanti(campo)).toEqual(['Chiama', 'Manda un SMS'])
    expect(campo.findAll('a')[1]!.attributes('href')).toBe('sms:+393331234567')
  })
})
