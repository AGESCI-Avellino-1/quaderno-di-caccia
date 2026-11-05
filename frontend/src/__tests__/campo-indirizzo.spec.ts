import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '@/api/qdc'
import CampoIndirizzo from '@/components/CampoIndirizzo.vue'

const PROPOSTA = { nome: 'Scuola Dante', indirizzo: 'Via Verdi, 83100 Avellino' }

function monta() {
  return mount(CampoIndirizzo, {
    props: {
      idCampo: 'prova',
      modelValue: '',
      'onUpdate:modelValue': () => {},
    },
  })
}

async function scrivi(pagina: ReturnType<typeof monta>, testo: string) {
  await pagina.setProps({ modelValue: testo })
  await pagina.find('input').trigger('input')
  await vi.advanceTimersByTimeAsync(600)
  await flushPromises()
}

beforeEach(() => vi.useFakeTimers())
afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('CampoIndirizzo', () => {
  it('propone gli indirizzi e dice da dove vengono', async () => {
    const cerca = vi.spyOn(api, 'cercaIndirizzi').mockResolvedValue([PROPOSTA])
    const pagina = monta()
    await scrivi(pagina, 'via verdi')
    expect(cerca).toHaveBeenCalledWith('via verdi')
    expect(pagina.text()).toContain('Via Verdi, 83100 Avellino')
    expect(pagina.text()).toContain('© OpenStreetMap')
  })

  it('mentre aspetta la risposta dice che sta cercando', async () => {
    let rispondi: (proposte: (typeof PROPOSTA)[]) => void = () => {}
    vi.spyOn(api, 'cercaIndirizzi').mockReturnValue(
      new Promise((risolvi) => {
        rispondi = risolvi
      }),
    )
    const pagina = monta()
    await scrivi(pagina, 'via verdi')
    expect(pagina.text()).toContain('Cerco')
    rispondi([PROPOSTA])
    await flushPromises()
    expect(pagina.text()).not.toContain('Cerco')
    expect(pagina.text()).toContain('Via Verdi')
  })

  it('scegliendo una proposta la manda a chi usa il campo', async () => {
    vi.spyOn(api, 'cercaIndirizzi').mockResolvedValue([PROPOSTA])
    const pagina = monta()
    await scrivi(pagina, 'via verdi')
    await pagina.find('button').trigger('click')
    expect(pagina.emitted('scelta')).toEqual([[PROPOSTA]])
    expect(pagina.emitted('update:modelValue')?.at(-1)).toEqual([PROPOSTA.indirizzo])
    expect(pagina.find('button').exists()).toBe(false)
  })

  it('non cerca finché il testo è troppo corto', async () => {
    const cerca = vi.spyOn(api, 'cercaIndirizzi').mockResolvedValue([])
    await scrivi(monta(), 'vi')
    expect(cerca).not.toHaveBeenCalled()
  })

  it('se il servizio non risponde resta un campo normale', async () => {
    vi.spyOn(api, 'cercaIndirizzi').mockRejectedValue(new TypeError('Failed to fetch'))
    const pagina = monta()
    await scrivi(pagina, 'via verdi')
    expect(pagina.find('input').exists()).toBe(true)
    expect(pagina.find('button').exists()).toBe(false)
    expect(pagina.find('.alert').exists()).toBe(false)
  })
})
