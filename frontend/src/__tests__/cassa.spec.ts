import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Cassa, Movimento } from '@/api/qdc'
import CassaView from '@/views/CassaView.vue'

import { risposta } from './aiuti'

const contanti: Cassa = {
  id: 3,
  nome: 'Contanti reparto',
  tipo: 'CONTANTI',
  unita_id: 1,
  saldo_iniziale: '50.00',
  data_saldo_iniziale: '2025-10-01',
  attiva: true,
  saldo: '30.00',
  puo_registrare: true,
  senza_giustificativo: 1,
}

const uscita: Movimento = {
  id: 9,
  cassa_id: 3,
  cassa: 'Contanti reparto',
  tipo: 'USCITA',
  tipo_nome: 'Uscita',
  data: '2026-01-15',
  importo: '20.00',
  effetto: '-20.00',
  descrizione: 'Cancelleria',
  voce_riga: 'A.1',
  voce_nome: 'Uscite per acquisto materiale vario',
  unita_id: 1,
  cassa_destinazione: null,
  ha_giustificativo: false,
  senza_giustificativo: true,
  storno_di: null,
  stornato: false,
  motivo_storno: '',
  da_quote: false,
  registrato_da: 'Anna Capo',
  creato_il: '2026-01-15T10:00:00Z',
}

beforeEach(() => setActivePinia(createPinia()))
afterEach(() => vi.unstubAllGlobals())

describe('CassaView', () => {
  it('shows balances, flags missing receipts and records an outflow', async () => {
    const corpi: unknown[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, opzioni?: RequestInit) => {
        if (opzioni?.method === 'POST') {
          corpi.push(JSON.parse(opzioni.body as string))
          return risposta(201, uscita)
        }
        if (url.startsWith('/api/v1/casse/')) return risposta(200, [])
        if (url.startsWith('/api/v1/casse')) return risposta(200, [contanti])
        if (url.startsWith('/api/v1/voci-modello-d'))
          return risposta(200, [
            { id: 'U:A.1:0', lato: 'U', riga: 'A.1', titolo_riga: 'Materie', nome: 'Materiale' },
            { id: 'E:A.1:0', lato: 'E', riga: 'A.1', titolo_riga: 'Quote', nome: 'Quota' },
          ])
        if (url.startsWith('/api/v1/movimenti')) return risposta(200, [uscita])
        if (url.startsWith('/api/v1/modello-d')) return risposta(403, {})
        return risposta(200, [])
      }),
    )
    const pagina = mount(CassaView)
    await flushPromises()
    expect(pagina.text()).toContain('Saldo 30,00 €')
    expect(pagina.text()).toContain('1 uscita senza giustificativo')
    expect(pagina.text()).toContain('Senza giustificativo')
    expect(pagina.text()).not.toContain('Rendiconto') // the Co.Ca. only

    const pulsante = pagina.findAll('button').find((b) => b.text() === 'Registra un movimento')!
    await pulsante.trigger('click')
    const voci = pagina
      .get('#mov-voce')
      .findAll('option')
      .map((o) => o.text())
    expect(voci).toEqual(['Scegli…', 'A.1 · Materiale']) // outflow categories only
    await pagina.get('#mov-importo').setValue('12.5')
    await pagina.get('#mov-descrizione').setValue('Nastro')
    await pagina.get('#mov-voce').setValue('U:A.1:0')
    await pagina.get('form').trigger('submit')
    await flushPromises()
    expect(corpi).toEqual([
      expect.objectContaining({
        cassa_id: 3,
        tipo: 'USCITA',
        importo: '12.50',
        voce_id: 'U:A.1:0',
        giustificativo: '',
      }),
    ])
    expect(pagina.text()).toContain('Movimento registrato.')
  })
})
