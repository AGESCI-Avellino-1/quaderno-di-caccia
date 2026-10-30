import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { IscrizioneBC, VersioneScheda } from '@/api/qdc'
import RisposteSchedaBC from '@/components/RisposteSchedaBC.vue'

import { risposta } from './aiuti'

const scheda: VersioneScheda = {
  id: 1,
  modello_id: 1,
  nome: 'Piccole Orme',
  numero: 1,
  chiede_foto: true,
  domande: [
    { id: 'a', tipo: 'SCELTA_SINGOLA', testo: 'Taglia', opzioni: ['S', 'M'], obbligatoria: true },
    {
      id: 'b',
      tipo: 'SCELTA_MULTIPLA',
      testo: 'Cosa sai fare',
      opzioni: ['Nodi', 'Fuoco'],
      obbligatoria: false,
    },
    { id: 'c', tipo: 'SI_NO', testo: 'Sai nuotare?', opzioni: [], obbligatoria: false },
    { id: 'd', tipo: 'BREVE', testo: 'Soprannome', opzioni: [], obbligatoria: false },
    { id: 'e', tipo: 'FOTO', testo: 'Una tua foto', opzioni: [], obbligatoria: true },
  ],
}

function iscrizione(altro: Partial<IscrizioneBC> = {}): IscrizioneBC {
  return {
    id: 7,
    evento_id: 3,
    evento: 'Piccole Orme',
    inizio: '2026-12-01T09:00:00+01:00',
    persona_id: 5,
    persona: 'Giulia Esploratrice',
    stato: 'AMMESSO',
    stato_nome: 'Ammesso',
    attiva: true,
    iscritto_il: '2026-10-29',
    scadenza: '2026-11-07',
    limite_cancellazione: '2026-11-24',
    cancellata_il: null,
    link_gestione: null,
    modo_liberatoria: 'APP',
    scadenza_liberatoria: '2026-11-05',
    scadenza_liberatoria_fissata: false,
    liberatoria_da_firmare: false,
    liberatoria_firmata: false,
    liberatoria_ricevuta_il: null,
    liberatoria_caricata_il: null,
    esito_liberatoria: '',
    motivo_rigetto: '',
    risposte: { a: 'S' },
    risposte_il: null,
    risposte_mancanti: ['Una tua foto'],
    foto: false,
    presentazione: null,
    scheda_inviata_il: null,
    pagata_il: null,
    quota: null,
    puo_gestire: false,
    puo_rispondere: true,
    puo_togliere_quota: false,
    ...altro,
  }
}

afterEach(() => vi.unstubAllGlobals())

describe('RisposteSchedaBC', () => {
  it('sends the answers with their types', async () => {
    const corpi: unknown[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, opzioni?: RequestInit) => {
        corpi.push(JSON.parse(String(opzioni?.body)))
        return risposta(200, iscrizione())
      }),
    )
    const pagina = mount(RisposteSchedaBC, {
      props: { iscrizione: iscrizione(), scheda, modifica: true },
    })
    await pagina.find('#d-7-a-1').setValue(true)
    await pagina.find('#d-7-b-0').setValue(true)
    await pagina.find('#d-7-c').setValue('si')
    await pagina.find('#d-7-d').setValue('Volpe')
    await pagina.find('form').trigger('submit')
    await flushPromises()
    expect(corpi).toEqual([{ risposte: { a: 'M', b: ['Nodi'], c: true, d: 'Volpe' } }])
    expect(pagina.emitted('cambiata')).toHaveLength(1)
  })

  it('is read only once the staff filled the form on BuonaCaccia', () => {
    const pagina = mount(RisposteSchedaBC, {
      props: {
        iscrizione: iscrizione({ scheda_inviata_il: '2026-11-03' }),
        scheda,
        modifica: true,
      },
    })
    expect(pagina.find('form').exists()).toBe(false)
    expect(pagina.text()).toContain('le risposte non si cambiano più')
    expect(pagina.text()).toContain('Taglia')
  })
})
