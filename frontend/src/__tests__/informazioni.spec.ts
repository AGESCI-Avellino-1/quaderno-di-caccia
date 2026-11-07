import { describe, expect, it } from 'vitest'

import type { Profilo } from '@/api/qdc'
import {
  browserDa,
  linkEmail,
  linkSegnalazione,
  LINK_PROGETTO,
  testo,
  voci,
  type Ambiente,
} from '@/pwa/informazioni'

const IPHONE =
  'Mozilla/5.0 (iPhone; CPU iPhone OS 18_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Mobile/15E148 Safari/604.1'
const MAC =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15'
const ANDROID =
  'Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36'

const BASE: Ambiente = {
  versioneApp: '1.22.0',
  versioneServer: '1.23.0',
  installata: true,
  agente: IPHONE,
  puntiTocco: 5,
  schermo: { larghezza: 393, altezza: 852, densita: 3 },
  lingua: 'it-IT',
  fuso: 'Europe/Rome',
  adesso: new Date(2026, 10, 7, 8, 30),
  online: true,
  aggiornamento: 'sul_server',
  stato: 'sbloccata',
  biometria: 'supportato',
  notifiche: 'negate',
  inCoda: 1,
  conErrori: 1,
  profilo: null,
}
const valore = (a: Ambiente, voce: string) => voci(a).find((v) => v.voce === voce)?.valore

describe('informazioni', () => {
  it('reads browser and system', () => {
    expect(browserDa(IPHONE)).toBe('Safari 18.4')
    expect(browserDa(ANDROID)).toBe('Chrome 130.0.0.0')
    expect(valore(BASE, 'Dispositivo')).toBe('iPhone, iOS 18.4, schermo 393×852 (×3)')
    expect(valore({ ...BASE, agente: ANDROID }, 'Dispositivo')).toContain('Android 14')
  })

  it('tells an iPad, which says it is a Mac, from a Mac', () => {
    expect(valore({ ...BASE, agente: MAC, puntiTocco: 5 }, 'Dispositivo')).toContain('iPad')
    expect(valore({ ...BASE, agente: MAC, puntiTocco: 0 }, 'Dispositivo')).toContain('Mac')
  })

  it('an installed app on iPhone has no browser version: it is still recognised', () => {
    const installata = IPHONE.replace(' Version/18.4', '').replace(' Safari/604.1', '')
    expect(browserDa(installata)).toBe('Safari')
  })

  it('shows the state of the device', () => {
    expect(valore(BASE, 'Versione del server')).toBe('v1.23.0')
    expect(valore({ ...BASE, versioneServer: '' }, 'Versione del server')).toBe('Non nota')
    expect(valore(BASE, 'Modalità')).toBe('App installata')
    expect(valore(BASE, 'Modifiche in sospeso')).toBe('2, di cui 1 con errore')
    expect(valore({ ...BASE, inCoda: 0, conErrori: 0 }, 'Modifiche in sospeso')).toBe('0')
    expect(valore(BASE, 'Sblocco con impronta o volto')).toBe('Supportato, non attivo')
  })

  it('never carries personal data: a report is public', () => {
    const profilo = {
      persona: { id: 77, nome: 'Giulia', cognome: 'Rossi' },
      tutelati: [{ id: 78, nome: 'Marco', cognome: 'Verdi' }],
      email: 'giulia.rossi@example.invalid',
      capo: false,
      capogruppo: false,
      amministratore_tecnico: false,
    } as unknown as Profilo
    const copiato = testo(voci({ ...BASE, profilo }))
    for (const dato of ['Giulia', 'Rossi', 'Marco', 'Verdi', 'example.invalid', '77', '78']) {
      expect(copiato).not.toContain(dato)
    }
    expect(valore({ ...BASE, profilo }, 'Profilo')).toBe('Genitore')
  })

  it('the kind of profile is not known while the app is locked', () => {
    expect(valore({ ...BASE, stato: 'bloccata' }, 'Profilo')).toBe('Non noto, app bloccata')
    expect(valore(BASE, 'Profilo')).toBe('Non collegato')
  })

  it('the report carries the data, where the site can take them', () => {
    const github = new URL(linkSegnalazione('', 'Versione: v1'))
    expect(github.origin + github.pathname).toBe(LINK_PROGETTO)
    expect(github.searchParams.get('body')).toContain('Versione: v1')
    expect(linkSegnalazione('https://esempio.it/segnala', 'dati')).toBe(
      'https://esempio.it/segnala',
    )
    const email = linkEmail('gruppo@example.invalid', 'Versione: v1')
    expect(email.startsWith('mailto:gruppo@example.invalid?')).toBe(true)
    expect(decodeURIComponent(email)).toContain('Versione: v1')
  })
})
