import { describe, expect, it } from 'vitest'

import { briciole, type Anello } from '@/navigazione/briciole'
import type { Gruppo, Voce } from '@/navigazione/menu'

const voce = (nome: string, to: string): Voce => ({ nome, icona: 'compass', to })
const percorso = (v: Voce) => String(v.to)
const anello = (pagina: string, percorso: string, nome: string): Anello => ({
  pagina,
  percorso,
  nome,
})

describe('breadcrumb', () => {
  it("a ragazzo's own sentiero is the menu entry, without the person in between", () => {
    const gruppi: Gruppo[] = [
      {
        chiave: 'progressione',
        titolo: 'Il mio Sentiero',
        icona: 'compass',
        voci: [voce('Il mio Sentiero', '/persone/3/sentiero'), voce('Imprese', '/unita/2/imprese')],
      },
    ]
    const catena = [
      anello('persona', '/persone/3', 'Giulia Rossi'),
      anello('sentiero', '/persone/3/sentiero', 'Progressione personale'),
    ]
    expect(
      briciole(catena, gruppi, [voce('Il mio profilo', '/persone/3')], false, percorso),
    ).toEqual([{ nome: 'Il mio Sentiero', percorso: null }])
  })

  it("a parent on a child's sentiero goes through the family and the child", () => {
    const gruppi: Gruppo[] = [
      {
        chiave: 'famiglia',
        titolo: 'La mia famiglia',
        icona: 'people',
        voci: [voce('Giulia Rossi', '/persone/3'), voce('Luca Rossi', '/persone/4')],
      },
    ]
    const catena = [
      anello('persone', '/persone', 'Persone'),
      anello('persona', '/persone/3', 'Giulia Rossi'),
      anello('sentiero', '/persone/3/sentiero', 'Progressione personale'),
    ]
    expect(briciole(catena, gruppi, [], false, percorso)).toEqual([
      { nome: 'La mia famiglia', percorso: null },
      { nome: 'Giulia Rossi', percorso: '/persone/3' },
      { nome: 'Progressione personale', percorso: null },
    ])
  })

  it("a unit's sub-entry keeps the unit it hangs from", () => {
    const gruppi: Gruppo[] = [
      {
        chiave: 'progressione',
        titolo: 'Progressione personale',
        icona: 'compass',
        voci: [
          voce('Reparto Antares (N1)', '/unita/2/sentiero'),
          { ...voce('Passaggi', '/unita/2/passaggi'), sottovoce: true },
        ],
      },
    ]
    const catena = [
      anello('unita', '/unita', 'Unità'),
      anello('unita-dettaglio', '/unita/2', 'Reparto Antares (N1)'),
      anello('passaggi', '/unita/2/passaggi', 'Passaggi'),
    ]
    expect(briciole(catena, gruppi, [], true, percorso)).toEqual([
      { nome: 'Progressione personale', percorso: null },
      { nome: 'Reparto Antares (N1)', percorso: '/unita/2/sentiero' },
      { nome: 'Passaggi', percorso: null },
    ])
  })

  it('leaves out the pages only the capi open', () => {
    const catena = [
      anello('unita', '/unita', 'Unità'),
      anello('unita-dettaglio', '/unita/5', 'Clan/Fuoco Hirpinia (T1)'),
      anello('carta-clan', '/unita/5/carta-clan', 'Carta di clan'),
    ]
    expect(briciole(catena, [], [], false, percorso)).toEqual([
      { nome: 'Carta di clan', percorso: null },
    ])
    expect(briciole(catena, [], [], true, percorso)).toEqual([
      { nome: 'Clan/Fuoco Hirpinia (T1)', percorso: '/unita/5' },
      { nome: 'Carta di clan', percorso: null },
    ])
  })
})
