import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { nextTick } from 'vue'

import Avatar from '@/components/Avatar.vue'
import CampoOtp from '@/components/CampoOtp.vue'
import CampoPassword from '@/components/CampoPassword.vue'

/** What the phone does when it fills in a code it suggested: one input event. */
async function riempi(input: HTMLInputElement, valore: string) {
  input.value = valore
  input.dispatchEvent(new Event('input', { bubbles: true }))
  await nextTick()
}

describe('CampoOtp', () => {
  it('draws one box per digit and goes on by itself when complete', async () => {
    const campo = mount(CampoOtp, {
      props: { modelValue: '', lunghezza: 6, maschera: true },
      attrs: { id: 'pin', 'aria-label': 'PIN', class: 'justify-content-center' },
      attachTo: document.body,
    })
    expect(campo.findAll('.otp-slot')).toHaveLength(6)
    // The class goes to the boxes, the rest to the input.
    expect(campo.classes()).toContain('justify-content-center')
    const input = campo.find('input').element
    expect(input.id).toBe('pin')
    expect(input.getAttribute('inputmode')).toBe('numeric')

    await riempi(input, '12a3')
    expect(campo.emitted('update:modelValue')!.at(-1)).toEqual(['123'])
    expect(campo.emitted('completo')).toBeUndefined()

    await riempi(input, '123456')
    expect(campo.emitted('completo')).toEqual([['123456']])
    // Masked: the boxes never show the digits.
    expect(campo.text()).not.toContain('1')
    campo.unmount()
  })

  it('takes the email code with or without the dash', async () => {
    const campo = mount(CampoOtp, {
      props: { modelValue: '', lunghezza: 8, tipo: 'alphanumeric', gruppi: [4, 4] },
      attachTo: document.body,
    })
    expect(campo.findAll('.otp-separator')).toHaveLength(1)
    await riempi(campo.find('input').element, 'AB3D-EF7H')
    expect(campo.emitted('completo')).toEqual([['AB3DEF7H']])
    campo.unmount()
  })

  it('empties the boxes when the page clears the code', async () => {
    // As with v-model: the page holds the value.
    const campo = mount(CampoOtp, {
      props: {
        modelValue: '',
        lunghezza: 6,
        'onUpdate:modelValue': (v: string) => campo.setProps({ modelValue: v }),
      },
      attachTo: document.body,
    })
    const input = campo.find('input').element
    await riempi(input, '000000')
    await campo.setProps({ modelValue: '' })
    expect(input.value).toBe('')
    expect(campo.findAll('.otp-slot-filled')).toHaveLength(0)
    campo.unmount()
  })
})

describe('CampoPassword', () => {
  it('shows the password in clear and hides it again', async () => {
    const campo = mount(CampoPassword, {
      props: { modelValue: 'segreta', id: 'pw' },
      attrs: { autocomplete: 'current-password' },
    })
    const input = campo.find('input')
    expect(input.attributes('type')).toBe('password')
    expect(input.attributes('autocomplete')).toBe('current-password')
    const pulsante = campo.find('button')
    expect(pulsante.attributes('aria-label')).toBe('Mostra password')
    await pulsante.trigger('click')
    expect(input.attributes('type')).toBe('text')
    expect(pulsante.attributes('aria-pressed')).toBe('true')
    await pulsante.trigger('click')
    expect(input.attributes('type')).toBe('password')
    // No strength meter for a password that is not new.
    expect(campo.find('.strength').exists()).toBe(false)
  })

  it('says how strong a new password is', async () => {
    const campo = mount(CampoPassword, {
      props: { modelValue: '', id: 'nuova', robustezza: true },
      attachTo: document.body,
    })
    const input = campo.find('input')
    await input.setValue('abc')
    expect(campo.find('.strength-text').text()).toBe('Debole')
    await input.setValue('Lupetti-Avellino-2026!')
    expect(campo.find('.strength-text').text()).toBe('Robusta')
    expect(campo.findAll('.strength-segment.active')).toHaveLength(4)
    campo.unmount()
  })
})

describe('Avatar', () => {
  it('shows the initials of the first two words', () => {
    const avatar = mount(Avatar, { props: { nome: 'Giulia Maria Esposito' } })
    expect(avatar.find('[aria-hidden="true"]').text()).toBe('GM')
    expect(avatar.find('.visually-hidden').text()).toBe('Giulia Maria Esposito')
    expect(avatar.classes()).toContain('theme-primary')
  })

  it('shows the photo, and the initials when it does not load', async () => {
    const avatar = mount(Avatar, {
      props: { nome: 'Luca Bianchi', foto: '/api/v1/persone/1/foto', dimensione: 'sm' },
    })
    expect(avatar.classes()).toContain('avatar-sm')
    await avatar.find('img').trigger('error')
    expect(avatar.find('img').exists()).toBe(false)
    expect(avatar.text()).toContain('LB')
    expect(avatar.emitted('errore')).toHaveLength(1)
  })
})
