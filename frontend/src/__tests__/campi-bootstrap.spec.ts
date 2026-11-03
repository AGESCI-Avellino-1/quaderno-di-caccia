import { mount, RouterLinkStub } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { nextTick } from 'vue'

import Avatar from '@/components/Avatar.vue'
import CampoImporto from '@/components/CampoImporto.vue'
import CampoOtp from '@/components/CampoOtp.vue'
import CampoPassword from '@/components/CampoPassword.vue'
import Passi from '@/components/Passi.vue'
import SceltaChip from '@/components/SceltaChip.vue'
import VociHome from '@/components/VociHome.vue'

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

  it('opens the file only when given the person, and only from the avatar', () => {
    const conLink = mount(Avatar, {
      props: { nome: 'Luca Bianchi', scheda: 7 },
      attrs: { 'aria-hidden': 'true' },
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    const link = conLink.getComponent(RouterLinkStub)
    expect(link.props('to')).toEqual({ name: 'persona', params: { id: 7 } })
    expect(link.attributes('aria-label')).toBe('Apri la scheda di Luca Bianchi')
    expect(link.attributes('aria-hidden')).toBeUndefined()

    const senza = mount(Avatar, {
      props: { nome: 'Luca Bianchi', scheda: null },
      attrs: { 'aria-hidden': 'true' },
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    expect(senza.findComponent(RouterLinkStub).exists()).toBe(false)
    expect(senza.attributes('aria-hidden')).toBe('true')
  })
})

describe('CampoImporto', () => {
  it('puts the € inside the field and gives back a number', async () => {
    const campo = mount(CampoImporto, {
      props: { modelValue: 10 },
      attrs: { id: 'importo', min: '0.01', required: true, class: 'w-auto' },
    })
    expect(campo.find('.form-adorn-text').text()).toBe('€')
    expect(campo.classes()).toContain('w-auto')
    const input = campo.find('input')
    expect(input.attributes('id')).toBe('importo')
    expect(input.attributes('step')).toBe('0.01')
    expect(input.element.value).toBe('10')
    await input.setValue('12.50')
    expect(campo.emitted('update:modelValue')!.at(-1)).toEqual([12.5])
  })
})

describe('Passi', () => {
  it('colours the steps done and marks the current one', () => {
    const passi = mount(Passi, {
      props: {
        orizzontale: true,
        passi: [
          { etichetta: 'Richiesta inviata', fatto: true },
          { etichetta: 'Accolta dai capi', corrente: true },
          { etichetta: 'Completata' },
        ],
      },
    })
    const voci = passi.findAll('li')
    expect(voci.map((v) => v.text())).toEqual([
      'Richiesta inviata',
      'Accolta dai capi',
      'Completata',
    ])
    expect(voci.map((v) => v.classes('active'))).toEqual([true, false, false])
    expect(voci[1]!.attributes('aria-current')).toBe('step')
    expect(passi.find('.stepper-horizontal').exists()).toBe(true)
  })
})

describe('SceltaChip', () => {
  it('chooses with one tap, as a group of radio buttons', async () => {
    const scelta = mount(SceltaChip, {
      props: {
        modelValue: 'FAMIGLIE',
        etichetta: 'A chi',
        scelte: [
          { valore: 'FAMIGLIE', nome: 'Le famiglie' },
          { valore: 'GENITORI', nome: 'Solo i genitori' },
        ],
      },
    })
    const chip = scelta.findAll('[role="radio"]')
    expect(chip[0]!.attributes('aria-checked')).toBe('true')
    await chip[1]!.trigger('click')
    expect(scelta.emitted('update:modelValue')).toEqual([['GENITORI']])
  })
})

describe('VociHome', () => {
  it('puts the entries of one unit in one card titled with the unit', () => {
    const voci = mount(VociHome, {
      props: {
        voci: [
          { nome: 'Imprese', icona: 'flag', to: '/unita/9/imprese' },
          ...[1, 2].flatMap((n) => [
            {
              nome: `Reparto Millenium (${n === 1 ? 'M1' : 'N1'})`,
              nomeInSezione: 'Progressione',
              icona: 'compass' as const,
              to: `/unita/${n}/sentiero`,
              sezione: `Reparto Millenium (${n === 1 ? 'M1' : 'N1'})`,
            },
            {
              nome: 'Passaggi',
              icona: 'signpost-split' as const,
              to: `/unita/${n}/passaggi`,
              sezione: `Reparto Millenium (${n === 1 ? 'M1' : 'N1'})`,
            },
          ]),
        ],
      },
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    const schede = voci.findAll('.card')
    expect(schede).toHaveLength(3)
    expect(schede[1]!.find('strong').text()).toBe('Reparto Millenium (M1)')
    expect(schede[1]!.findAll('nav a').map((a) => a.text())).toEqual(['Progressione', 'Passaggi'])
    expect(schede[2]!.find('strong').text()).toBe('Reparto Millenium (N1)')
  })
})
