/**
 * Screenshots of the user manual (DEC-235, DEC-239): `mise run docs:schermate`.
 *
 * Starts its own Django (port 8001) on a separate database filled with invented people
 * (`manage.py dati_di_prova --azzera`) and its own Vite (port 5174), so the usual dev
 * database is never touched; then logs in as every profile and saves each scene twice,
 * phone (inside a phone frame) and computer, in `docs/manuale/img/`.
 *
 * Only some scenes: `node scripts/schermate.ts genitore/accesso genitore/protezione`.
 */
import { spawn, type ChildProcess } from 'node:child_process'
import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { chromium, type Browser, type BrowserContext, type Page } from 'playwright'

const RADICE = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const IMMAGINI = join(RADICE, 'docs', 'manuale', 'img')
const DATABASE =
  process.env.QDC_MANUALE_DATABASE_URL ?? 'postgres://qdc:qdc@localhost:5432/qdc_manuale'
const PORTA_DJANGO = 8001
const PORTA_VITE = 5174
const APP = `http://localhost:${PORTA_VITE}`

// Same as backend/apps/core/management/commands/dati_di_prova.py.
const PASSWORD = 'manuale-di-prova'
const PIN = '246813'
/** Tallest phone screenshot, in CSS pixels: about one and a half screens. */
const ALTEZZA_TELEFONO = 1300
/** Tallest computer screenshot, in CSS pixels. */
const ALTEZZA_COMPUTER = 2400
const DOMINIO = 'example.invalid'

/** Who appears in the manual, by profile (DEC-236): the people of `dati_di_prova`. */
export const PERSONE = {
  genitore: 'mario.rossi',
  genitoreLc: 'giovanni.esposito',
  coccinella: 'sofia.esposito',
  esploratore: 'luca.rossi',
  capoSquadriglia: 'giulia.rossi',
  scolta: 'chiara.russo',
  capogruppo: 'laura.bianchi',
  capoReparto: 'marco.ferri',
  capoCerchio: 'elena.conti',
  tesoriera: 'francesca.gallo',
  amministratore: 'davide.ricci',
  genitoreMaggiorenne: 'antonio.russo',
} as const

/** Opens a card of the home page, e.g. a child's page. */
const apri = (testo: string) => async (pagina: Page) => {
  await pagina.getByRole('link', { name: testo }).first().click()
  await pagina.waitForLoadState('networkidle')
}

interface Scena {
  /** File name under img/, without the format suffix: `genitore/accesso`. */
  nome: string
  /** Who is logged in; none for the pages before login. */
  chi?: keyof typeof PERSONE
  /** Stop on the device protection page right after login. */
  senzaProtezione?: boolean
  percorso: string
  /** Steps to reach the state to show, after opening `percorso`. */
  prepara?: (pagina: Page) => Promise<void>
  /** The whole page, not only what fits on the screen. */
  intera?: boolean
  /** Scroll so that this text (a heading) is at the top of the screen. */
  mostra?: string
  /** Keep the cookie notice, closed in every other scene. */
  cookie?: boolean
}

/** The side menu with the profile menu open: on the phone it opens from the top button. */
async function apriMenu(pagina: Page): Promise<void> {
  const pulsante = pagina.getByRole('button', { name: 'Apri il menu' })
  if (await pulsante.isVisible()) await pulsante.click()
  await pagina.locator('.ag-sidebar__user-toggle').click()
  await pagina.locator('#menu-profilo').waitFor()
}

const SCENE: Scena[] = [
  { nome: 'comune/accesso', percorso: '/accesso' },
  {
    nome: 'comune/accesso-password',
    percorso: '/accesso',
    prepara: async (pagina) => {
      await pagina.getByRole('button', { name: 'Password', exact: true }).click()
      await pagina.getByPlaceholder('Email').fill(`${PERSONE.genitore}@${DOMINIO}`)
    },
  },
  {
    nome: 'comune/accesso-codice',
    percorso: '/accesso',
    prepara: async (pagina) => {
      await pagina.getByPlaceholder('Email').fill(`${PERSONE.genitore}@${DOMINIO}`)
      await pagina.getByRole('button', { name: 'Inviami il codice' }).click()
      await pagina.getByPlaceholder('Codice').waitFor()
    },
  },
  { nome: 'comune/invito', percorso: '/invito/invito-di-prova' },
  {
    nome: 'comune/protezione',
    chi: 'genitore',
    senzaProtezione: true,
    percorso: '/protezione',
    intera: true,
  },
  { nome: 'comune/privacy', percorso: '/privacy', cookie: true },
  { nome: 'genitore/home', chi: 'genitore', percorso: '/', intera: true },
  { nome: 'genitore/menu', chi: 'genitore', percorso: '/', prepara: apriMenu },
  {
    nome: 'genitore/figlio',
    chi: 'genitore',
    percorso: '/',
    prepara: apri('Giulia Rossi'),
    intera: true,
  },
  {
    nome: 'genitore/sentiero',
    chi: 'genitore',
    percorso: '/',
    prepara: async (pagina) => {
      await apri('Giulia Rossi')(pagina)
      await apri('Sentiero (Progressione Personale)')(pagina)
    },
    intera: true,
  },
  {
    nome: 'genitore/fascicolo-anno',
    chi: 'genitore',
    percorso: '/',
    prepara: async (pagina) => {
      await apri('Giulia Rossi')(pagina)
      await apri("Fascicolo dell'anno")(pagina)
    },
    intera: true,
  },
  {
    nome: 'genitore/correzione',
    chi: 'genitore',
    percorso: '/',
    prepara: async (pagina) => {
      await apri('Giulia Rossi')(pagina)
      await pagina.getByRole('button', { name: 'Correggi un dato' }).click()
      await pagina.getByLabel('Dato').selectOption({ label: 'Cellulare' })
      await pagina.getByLabel('Valore giusto').fill('3331234567')
    },
    mostra: 'Dati di BuonaStrada',
  },
  {
    nome: 'genitore/telefono-squadriglia',
    chi: 'genitore',
    percorso: '/',
    prepara: apri('Giulia Rossi'),
    mostra: 'Telefono in squadriglia',
  },
  {
    nome: 'genitore/sanitaria',
    chi: 'genitore',
    percorso: '/',
    prepara: apri('Giulia Rossi'),
    mostra: 'Scheda sanitaria',
  },
  {
    nome: 'genitore/sanitaria-modifica',
    chi: 'genitore',
    percorso: '/',
    prepara: async (pagina) => {
      await apri('Giulia Rossi')(pagina)
      await apri('Modifica')(pagina)
    },
    intera: true,
  },
  { nome: 'genitore/eventi', chi: 'genitore', percorso: '/eventi', intera: true },
  {
    nome: 'genitore/calendario',
    chi: 'genitore',
    percorso: '/eventi',
    prepara: async (pagina) => {
      await pagina.getByRole('button', { name: 'Mostra il link' }).click()
      await pagina.getByRole('button', { name: 'Copia' }).first().waitFor()
    },
    mostra: 'Il mio calendario',
  },
  {
    nome: 'genitore/evento-recapito',
    chi: 'genitore',
    percorso: '/eventi',
    prepara: async (pagina) => {
      await apri('Uscita di reparto')(pagina)
      await pagina.getByText('Un altro recapito per le emergenze').first().click()
      await pagina.getByLabel('Chi chiamare').fill('Nonna Rosa')
      await pagina.getByLabel('Telefono').fill('3339876543')
    },
    mostra: 'Partecipazione',
  },
  {
    nome: 'genitore/evento',
    chi: 'genitore',
    percorso: '/eventi',
    prepara: apri('Uscita di reparto'),
    intera: true,
  },
  {
    nome: 'genitore/buonacaccia',
    chi: 'genitore',
    percorso: '/eventi',
    prepara: apri('Campo di specialità di Zona'),
    intera: true,
  },
  {
    nome: 'genitore/buonacaccia-scheda',
    chi: 'genitore',
    percorso: '/eventi',
    prepara: async (pagina) => {
      await apri('Campo di specialità di Zona')(pagina)
      await pagina.getByLabel('Taglia della maglietta').fill('M')
      await pagina.getByLabel('Topografo').check()
      await pagina.getByLabel('Sai nuotare?').selectOption({ label: 'Sì' })
      await pagina.getByRole('button', { name: 'Salva le risposte' }).click()
      await pagina.getByText('Salvate.').waitFor()
    },
    // After saving, only the photo is missing (the answers stay in the database).
    mostra: 'Mancano: Una tua foto per il cartellino.',
  },
  { nome: 'genitore/quote', chi: 'genitore', percorso: '/mie-quote', intera: true },
  {
    nome: 'genitore/quote-bonifico',
    chi: 'genitore',
    percorso: '/mie-quote',
    prepara: async (pagina) => {
      await pagina.getByRole('button', { name: 'Ho fatto il bonifico' }).click()
      await pagina.getByText('Quali quote hai pagato con il bonifico?').waitFor()
      await pagina.locator('form input.check').first().check()
    },
    mostra: 'Quali quote hai pagato con il bonifico?',
  },
  { nome: 'genitore/bacheca', chi: 'genitore', percorso: '/bacheca', intera: true },
  { nome: 'genitore/email', chi: 'genitore', percorso: '/email', intera: true },
  { nome: 'genitore/iscrizione', percorso: '/iscrizione/CERCHIO2027', intera: true },
  { nome: 'genitore/lista-attesa', percorso: '/lista-attesa', intera: true },
  // The link of the confirmation email (fixed in dati_di_prova).
  { nome: 'genitore/mia-attesa', percorso: '/lista-attesa/attesa-di-prova', intera: true },
  {
    nome: 'genitore/maggiorenne',
    chi: 'genitoreMaggiorenne',
    percorso: '/',
    prepara: apri('Chiara Russo'),
    intera: true,
  },
  // The ragazzi (DEC-237): Giulia is a guida and the capo squadriglia of the Pantere.
  { nome: 'ragazzo/home', chi: 'capoSquadriglia', percorso: '/', intera: true },
  {
    nome: 'ragazzo/scheda',
    chi: 'capoSquadriglia',
    percorso: '/',
    prepara: apri('Il mio profilo'),
    intera: true,
  },
  {
    nome: 'ragazzo/sentiero',
    chi: 'capoSquadriglia',
    percorso: '/',
    prepara: apri('Il mio Sentiero'),
    intera: true,
  },
  {
    nome: 'ragazzo/nuova-meta',
    chi: 'capoSquadriglia',
    percorso: '/',
    prepara: async (pagina) => {
      await apri('Il mio Sentiero')(pagina)
      await pagina.getByRole('button', { name: 'Nuova meta' }).click()
      await pagina
        .getByLabel('Il cambiamento che vuoi raggiungere')
        .fill('Parlare davanti al reparto senza agitarmi')
    },
    mostra: 'Nuova meta',
  },
  {
    nome: 'ragazzo/verifica',
    chi: 'capoSquadriglia',
    percorso: '/',
    prepara: apri('Il mio Sentiero'),
    mostra: 'Impegni',
  },
  { nome: 'ragazzo/squadriglia', chi: 'capoSquadriglia', percorso: '/squadriglia', intera: true },
  {
    nome: 'ragazzo/nota-csq',
    chi: 'capoSquadriglia',
    percorso: '/squadriglia',
    prepara: async (pagina) => {
      await apri('Alice Marino')(pagina)
      await pagina.getByRole('button', { name: 'Nuova nota' }).click()
      await pagina
        .getByLabel('Nota', { exact: true })
        .fill("Ha preparato da sola il fuoco per la cena dell'uscita: brava!")
    },
    mostra: 'Note',
  },
  // Chiara is a scolta of the clan Hirpinia, of age.
  {
    nome: 'ragazzo/strada',
    chi: 'scolta',
    percorso: '/',
    prepara: apri('La mia Strada'),
    intera: true,
  },
  {
    nome: 'ragazzo/rilettura',
    chi: 'scolta',
    percorso: '/',
    prepara: async (pagina) => {
      await apri('La mia Strada')(pagina)
      await pagina.getByRole('button', { name: 'Aggiungi la mia rilettura' }).click()
      await pagina
        .getByLabel('La mia rilettura')
        .fill('Alla mensa ho capito che ascoltare conta quanto servire il pranzo.')
    },
    mostra: 'Punti della Strada',
  },
  {
    nome: 'ragazzo/carta-clan',
    chi: 'scolta',
    percorso: '/',
    prepara: async (pagina) => {
      await apri('La mia Strada')(pagina)
      await apri('Leggi la Carta di clan')(pagina)
    },
    intera: true,
  },
  // Sofia is a coccinella of the cerchio Fiordaliso (setting: bosco).
  { nome: 'ragazzo/lc-home', chi: 'coccinella', percorso: '/', intera: true },
  {
    nome: 'ragazzo/lc-sentiero',
    chi: 'coccinella',
    percorso: '/',
    prepara: apri('Il mio Sentiero'),
    intera: true,
  },
  { nome: 'comune/sblocco', chi: 'genitore', percorso: '/sblocco' },
  { nome: 'comune/dispositivi', chi: 'genitore', percorso: '/dispositivi' },
  {
    // Last of the parent's scenes: the passkey stays in the database.
    nome: 'comune/passkey',
    chi: 'genitore',
    percorso: '/dispositivi',
    intera: true,
    prepara: async (pagina) => {
      const telefono = (pagina.viewportSize()?.width ?? 0) < 600
      await pagina
        .getByLabel('Nome della nuova passkey')
        .fill(telefono ? 'Telefono di Mario' : 'Computer di Mario')
      await pagina.getByRole('button', { name: 'Crea una passkey su questo dispositivo' }).click()
      await pagina.getByLabel('La tua password').fill(PASSWORD)
      await pagina.getByRole('button', { name: 'Conferma', exact: true }).click()
      await pagina.getByText('Passkey creata').waitFor()
    },
  },
]

interface Formato {
  suffisso: 'telefono' | 'computer'
  contesto: Parameters<Browser['newContext']>[0]
}

const FORMATI: Formato[] = [
  {
    suffisso: 'telefono',
    contesto: {
      viewport: { width: 390, height: 844 },
      deviceScaleFactor: 2,
      isMobile: true,
      hasTouch: true,
      userAgent:
        'Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) ' +
        'Chrome/156.0.0.0 Mobile Safari/537.36',
    },
  },
  { suffisso: 'computer', contesto: { viewport: { width: 1280, height: 800 } } },
]

// --- servers -------------------------------------------------------------------------

const processi: ChildProcess[] = []

function avvia(comando: string, argomenti: string[], cartella: string, env = {}): ChildProcess {
  const figlio = spawn(comando, argomenti, {
    cwd: join(RADICE, cartella),
    env: { ...process.env, ...env },
    stdio: ['ignore', 'ignore', 'inherit'],
    // Its own process group: stopping it stops what `uv` and `npx` started too.
    detached: true,
  })
  processi.push(figlio)
  return figlio
}

function esegui(comando: string, argomenti: string[], cartella: string, env = {}): Promise<void> {
  return new Promise((risolvi, rifiuta) => {
    avvia(comando, argomenti, cartella, env).on('exit', (codice) =>
      codice === 0 ? risolvi() : rifiuta(new Error(`${comando} ${argomenti.join(' ')}: ${codice}`)),
    )
  })
}

async function attendi(url: string): Promise<void> {
  for (let tentativo = 0; tentativo < 120; tentativo++) {
    try {
      await fetch(url)
      return
    } catch {
      await new Promise((risolvi) => setTimeout(risolvi, 500))
    }
  }
  throw new Error(`${url} non risponde`)
}

const ENV_DJANGO = {
  DATABASE_URL: DATABASE,
  // runserver opens one connection per request: kept for a minute they would exceed
  // PostgreSQL's limit during a full run.
  DJANGO_CONN_MAX_AGE: '0',
  DJANGO_CSRF_TRUSTED_ORIGINS: APP,
  QDC_FRONTEND_URL: APP,
}

async function avviaServer(): Promise<void> {
  const creaDatabase = `
import sys, psycopg
from urllib.parse import urlsplit
url = urlsplit(sys.argv[1])
with psycopg.connect(url._replace(path="/postgres").geturl(), autocommit=True) as c:
    nome = url.path.lstrip("/")
    if not c.execute("select 1 from pg_database where datname = %s", [nome]).fetchone():
        c.execute(f'create database "{nome}"')
`
  await esegui('uv', ['run', 'python', '-c', creaDatabase, DATABASE], 'backend')
  await esegui('uv', ['run', 'python', 'manage.py', 'migrate', '-v0'], 'backend', ENV_DJANGO)
  await esegui(
    'uv',
    ['run', 'python', 'manage.py', 'dati_di_prova', '--azzera'],
    'backend',
    ENV_DJANGO,
  )
  avvia(
    'uv',
    ['run', 'python', 'manage.py', 'runserver', String(PORTA_DJANGO), '--noreload'],
    'backend',
    ENV_DJANGO,
  )
  avvia('npx', ['vite', '--port', String(PORTA_VITE), '--strictPort'], 'frontend', {
    QDC_DJANGO_URL: `http://localhost:${PORTA_DJANGO}`,
  })
  await attendi(`http://localhost:${PORTA_DJANGO}/api/v1/docs`)
  await attendi(APP)
}

// --- screenshots ---------------------------------------------------------------------

async function entra(pagina: Page, chi: keyof typeof PERSONE, proteggi: boolean): Promise<void> {
  await pagina.goto(`${APP}/accesso`)
  await pagina.getByRole('button', { name: 'Password', exact: true }).click()
  await pagina.getByPlaceholder('Email').fill(`${PERSONE[chi]}@${DOMINIO}`)
  await pagina.getByPlaceholder('Password').fill(PASSWORD)
  await pagina.getByRole('button', { name: 'Accedi', exact: true }).click()
  await pagina.waitForURL('**/protezione**')
  if (!proteggi) return
  await pagina.getByLabel('PIN (almeno').fill(PIN)
  await pagina.getByLabel('Ripeti il PIN').fill(PIN)
  // Fingerprint or face would open the browser's passkey dialog: PIN only.
  const biometria = pagina.getByLabel('Sblocca anche con impronta o volto')
  if (await biometria.isVisible()) await biometria.uncheck()
  await pagina.getByRole('button', { name: 'Attiva la protezione' }).click()
  await pagina.waitForURL((url) => !url.pathname.startsWith('/protezione'))
}

/** The phone screenshot inside a phone outline, transparent around it (DEC-239). */
async function incornicia(browser: Browser, immagine: Buffer): Promise<Buffer> {
  const pagina = await browser.newPage({ deviceScaleFactor: 1 })
  await pagina.setContent(`
    <style>
      body { margin: 0; background: transparent; }
      .telefono {
        display: inline-block; padding: 28px 18px; border-radius: 64px;
        background: #1d1d1f; box-shadow: inset 0 0 0 3px #3a3a3c;
      }
      .telefono img { display: block; width: 780px; border-radius: 44px; }
    </style>
    <div class="telefono"><img src="data:image/png;base64,${immagine.toString('base64')}"></div>`)
  const cornice = await pagina.locator('.telefono').screenshot({ omitBackground: true })
  await pagina.close()
  return cornice
}

async function fotografa(browser: Browser, formato: Formato, scene: Scena[]): Promise<void> {
  let contesto: BrowserContext | undefined
  let attuale: string | undefined
  for (const scena of scene) {
    const chi = `${scena.chi ?? ''}${scena.senzaProtezione ? ':senza' : ''}`
    if (!contesto || chi !== attuale) {
      await contesto?.close()
      contesto = await browser.newContext({
        ...formato.contesto,
        locale: 'it-IT',
        timezoneId: 'Europe/Rome',
        serviceWorkers: 'block',
      })
      attuale = chi
      // A virtual authenticator, as on a phone with a fingerprint: passkeys work.
      const cdp = await contesto.newCDPSession(await contesto.newPage())
      await cdp.send('WebAuthn.enable')
      await cdp.send('WebAuthn.addVirtualAuthenticator', {
        options: {
          protocol: 'ctap2',
          transport: 'internal',
          hasResidentKey: true,
          hasUserVerification: true,
          isUserVerified: true,
          automaticPresenceSimulation: true,
        },
      })
      if (scena.chi) await entra(contesto.pages()[0]!, scena.chi, !scena.senzaProtezione)
    }
    const pagina = contesto.pages()[0] ?? (await contesto.newPage())
    await pagina.goto(`${APP}${scena.percorso}`)
    await pagina.waitForLoadState('networkidle')
    // A reload locks the app (the key lives only in memory): unlock, back to the page.
    if (new URL(pagina.url()).pathname === '/sblocco' && scena.percorso !== '/sblocco') {
      await pagina.getByPlaceholder('PIN').fill(PIN)
      await pagina.getByRole('button', { name: 'Sblocca' }).click()
      await pagina.waitForURL((url) => url.pathname !== '/sblocco')
      await pagina.waitForLoadState('networkidle')
    }
    // The cookie notice covers the bottom of every page: the manual shows it once.
    if (scena.cookie) {
      await pagina.evaluate(() => localStorage.removeItem('qdc-cookie-informativa'))
      await pagina.reload()
      await pagina.waitForLoadState('networkidle')
    } else {
      const cookie = pagina.getByRole('button', { name: 'Ho capito' })
      if (await cookie.isVisible()) await cookie.click()
    }
    await scena.prepara?.(pagina)
    if (scena.mostra) {
      await pagina
        .getByText(scena.mostra, { exact: true })
        .first()
        .evaluate((el) => {
          el.scrollIntoView({ block: 'start' })
          // Only the content scrolls (DEC-241): leave a margin above the heading.
          el.closest('.qdc-scorrevole')?.scrollBy(0, -24)
          window.scrollBy(0, -80)
        })
    }
    await pagina.mouse.move(0, 0) // no hover highlight left on a button
    await pagina.waitForTimeout(300)
    // Only the content scrolls (DEC-241), so `fullPage` would stop at one screen: a
    // whole page grows the window to the content instead, then puts it back.
    const finestra = pagina.viewportSize()!
    if (scena.intera) {
      const contenuto = await pagina.evaluate(() => {
        const s = document.querySelector('.qdc-scorrevole')
        return window.innerHeight + (s ? s.scrollHeight - s.clientHeight : 0)
      })
      // On the phone up to ALTEZZA_TELEFONO: a taller image does not fit a PDF page and
      // rinohtype pushes it to the next page forever.
      const massima = formato.suffisso === 'telefono' ? ALTEZZA_TELEFONO : ALTEZZA_COMPUTER
      await pagina.setViewportSize({ ...finestra, height: Math.min(contenuto, massima) })
      await pagina.waitForTimeout(300)
    }
    let immagine = await pagina.screenshot()
    if (scena.intera) await pagina.setViewportSize(finestra)
    if (formato.suffisso === 'telefono') immagine = await incornicia(browser, immagine)
    const file = join(IMMAGINI, `${scena.nome}-${formato.suffisso}.png`)
    await mkdir(dirname(file), { recursive: true })
    await writeFile(file, immagine)
    console.log(`  ${scena.nome}-${formato.suffisso}.png`)
  }
  await contesto?.close()
}

async function principale(): Promise<void> {
  const scelte = process.argv.slice(2)
  const scene = scelte.length ? SCENE.filter((s) => scelte.includes(s.nome)) : SCENE
  await avviaServer()
  const browser = await chromium.launch()
  try {
    for (const formato of FORMATI) await fotografa(browser, formato, scene)
  } finally {
    await browser.close()
  }
}

try {
  await principale()
} finally {
  for (const figlio of processi) {
    try {
      if (figlio.pid && figlio.exitCode === null) process.kill(-figlio.pid)
    } catch {
      // already gone
    }
  }
}
