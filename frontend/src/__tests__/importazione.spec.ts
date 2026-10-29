import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import ImportazioneView from '@/views/ImportazioneView.vue'

import { risposta } from './aiuti'

const riepilogo = {
  persone_create: [],
  persone_aggiornate: [],
  genitori_creati: [],
  unita_create: [],
  appartenenze_aperte: [],
  appartenenze_chiuse: [],
  correzioni_recepite: [],
  avvisi: [],
  differenze: [
    {
      persona: 'Rossi Giulia',
      campo: 'Cellulare',
      valore_app: '3339999999',
      valore_buonastrada: '3330000000',
      motivo: '',
      chiave: '5:cellulare',
      data_app: '2026-10-20',
      proposta: 'BUONASTRADA',
      scelta: 'BUONASTRADA',
    },
    {
      persona: 'Bianchi Paolo',
      campo: 'Unità',
      valore_app: 'Noviziato',
      valore_buonastrada: 'Clan',
      motivo: '',
      chiave: '7:unita:RAGAZZO',
      data_app: '2026-10-25',
      proposta: 'APP',
      scelta: 'APP',
    },
  ],
}

afterEach(() => vi.unstubAllGlobals())

describe('ImportazioneView', () => {
  it('sends the update date, proposes the newer side and applies the choices', async () => {
    const chiamate: { url: string; corpo: BodyInit | null | undefined }[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, opzioni?: RequestInit) => {
        chiamate.push({ url, corpo: opzioni?.body })
        const stato = url.endsWith('/applica') ? 'APPLICATA' : 'ANTEPRIMA'
        return risposta(201, { id: 3, stato, dati_aggiornati_al: '2026-10-22', riepilogo })
      }),
    )
    const vista = mount(ImportazioneView)
    const input = vista.get('#file-export')
    Object.defineProperty(input.element, 'files', {
      value: [new File(['x'], 'RicercaSoci.csv')],
    })
    await input.trigger('change')
    await vista.get('#aggiornato-al').setValue('2026-10-22')
    await vista
      .findAll('button')
      .find((b) => b.text() === 'Anteprima')!
      .trigger('click')
    await flushPromises()

    const caricato = chiamate[0]!.corpo as FormData
    expect(caricato.get('aggiornato_al')).toBe('2026-10-22')
    const scelti = vista
      .findAll<HTMLInputElement>('input[type="radio"]')
      .filter((r) => r.element.checked)
      .map((r) => r.element.value)
    expect(scelti).toEqual(['BUONASTRADA', 'APP'])
    expect(vista.text()).toContain('più recente')

    await vista.get('#scelta-0-APP').setValue(true) // keep the app's phone instead
    await vista
      .findAll('button')
      .find((b) => b.text().startsWith('Applica'))!
      .trigger('click')
    await flushPromises()
    expect(JSON.parse(chiamate[1]!.corpo as string)).toEqual({
      scelte: { '5:cellulare': 'APP', '7:unita:RAGAZZO': 'APP' },
    })
    expect(vista.text()).toContain('Importazione applicata')
  })
})
