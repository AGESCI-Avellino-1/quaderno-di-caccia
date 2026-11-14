import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import RiorganizzazioneView from '@/views/RiorganizzazioneView.vue'

import { risposta } from './aiuti'

// The draft of the future patrols (DEC-410).
const persona = (id: number, nome: string) => ({ id, nome, cognome: 'Prova' })
const bozza = (puo_gestire: boolean, si_applica = true) => ({
  id: 9,
  data_inizio: '2026-11-14',
  stato: 'APERTA',
  visibile_ai_capi_squadriglia: false,
  si_applica,
  annullabile: false,
  applicata_il: null,
  applicata_da: '',
  reparti: [{ id: 5, nome: 'Reparto Millenium (M1)', composizione: 'F' }],
  squadriglie: [
    {
      id: 1,
      nome: 'Civette',
      nuova: false,
      unita_id: 5,
      unita_nome: 'Reparto Millenium (M1)',
      sesso: 'F',
      capo_id: 100,
      vice_id: null,
      membri: [persona(100, 'Anna')],
    },
    {
      id: 2,
      nome: 'Volpi',
      nuova: false,
      unita_id: 5,
      unita_nome: 'Reparto Millenium (M1)',
      sesso: 'F',
      capo_id: null,
      vice_id: null,
      membri: [],
    },
  ],
  senza_squadriglia: [],
  differenze: puo_gestire ? ["Bea Prova è arrivato/a dopo la bozza: resta dov'è."] : [],
  puo_gestire,
})

type Chiamata = { metodo: string; url: string; corpo: unknown }

async function monta(dati: object, props: object, chiamate: Chiamata[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, opzioni?: RequestInit) => {
      const metodo = opzioni?.method ?? 'GET'
      if (metodo !== 'GET') {
        chiamate.push({ metodo, url, corpo: JSON.parse((opzioni?.body as string) || 'null') })
        return risposta(200, bozza(true)) // a write answers with the draft
      }
      return risposta(200, dati)
    }),
  )
  const pagina = mount(RiorganizzazioneView, { props })
  await flushPromises()
  return pagina
}

afterEach(() => vi.unstubAllGlobals())

describe('draft of the patrols', () => {
  it('the staff moves a ragazza, sees what will be archived, applies after asking', async () => {
    const chiamate: Chiamata[] = []
    const pagina = await monta({ aperta: bozza(true), applicata: null }, { unita: 5 }, chiamate)
    expect(pagina.text()).toContain('sarà archiviata')
    expect(pagina.text()).toContain('Da controllare')
    await pagina.get('select[aria-label="Sposta Anna Prova"]').setValue('2')
    await flushPromises()
    await pagina
      .findAll('button')
      .find((b) => b.text() === 'Applica la bozza…')!
      .trigger('click')
    await pagina
      .findAll('button')
      .find((b) => b.text() === 'Sì, applica')!
      .trigger('click')
    await flushPromises()
    expect(chiamate.slice(0, 2)).toEqual([
      {
        metodo: 'PUT',
        url: '/api/v1/bozze-squadriglie/9/membri/100',
        corpo: { squadriglia_id: 2 },
      },
      { metodo: 'POST', url: '/api/v1/bozze-squadriglie/9/applica', corpo: null },
    ])
  })

  it('shows apart who goes to R/S, and the staff marks it', async () => {
    // DEC-411
    const chiamate: Chiamata[] = []
    const dati = {
      ...bozza(true),
      senza_squadriglia: [
        { ...persona(200, 'Dora'), reparto_id: 5, passa_in_rs: false },
        { ...persona(300, 'Cloe'), reparto_id: 5, passa_in_rs: true },
      ],
    }
    const pagina = await monta({ aperta: dati, applicata: null }, { unita: 5 }, chiamate)
    const titoli = pagina.findAll('h2').map((h) => h.text())
    expect(titoli).toContain('Senza squadriglia, restano nel reparto')
    expect(titoli).toContain('Passano in R/S')
    await pagina.get('#rs-200').setValue(true)
    await flushPromises()
    expect(chiamate[0]).toEqual({
      metodo: 'PUT',
      url: '/api/v1/bozze-squadriglie/9/membri/200/rs',
      corpo: { passa: true },
    })
  })

  it('cannot be applied before its first day', async () => {
    const pagina = await monta({ aperta: bozza(true, false), applicata: null }, { unita: 5 })
    const applica = pagina.findAll('button').find((b) => b.text() === 'Applica la bozza…')!
    expect(applica.attributes('disabled')).toBeDefined()
    expect(pagina.text()).toContain('Si applica dal')
  })

  it('a future capo squadriglia only reads it', async () => {
    const pagina = await monta(bozza(false), { bozza: 9 })
    expect(pagina.text()).toContain('Le squadriglie future')
    expect(pagina.text()).toContain('Anna Prova')
    expect(pagina.find('select').exists()).toBe(false)
    expect(pagina.text()).not.toContain('Applica la bozza')
  })
})
