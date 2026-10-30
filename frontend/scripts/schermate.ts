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
} as const

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
  { nome: 'genitore/home', chi: 'genitore', percorso: '/', intera: true },
  { nome: 'comune/sblocco', chi: 'genitore', percorso: '/sblocco' },
  { nome: 'comune/dispositivi', chi: 'genitore', percorso: '/dispositivi' },
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
      if (scena.chi) await entra(await contesto.newPage(), scena.chi, !scena.senzaProtezione)
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
    await scena.prepara?.(pagina)
    await pagina.waitForTimeout(300)
    let immagine = await pagina.screenshot({ fullPage: scena.intera ?? false })
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
  for (const figlio of processi) figlio.kill()
}
