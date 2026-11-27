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
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { chromium, type Browser, type BrowserContext, type Locator, type Page } from 'playwright'

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
/** The invented BuonaStrada export of the test data, for the import preview. */
const EXPORT_DI_PROVA = join(tmpdir(), 'qdc-manuale-export.csv')

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

/** The personal link generated in «capo/link-personale», opened by «ragazzo/attiva». */
let linkPersonale = ''

/** Opens a card of the home page, e.g. a child's page. */
const apri = (testo: string) => async (pagina: Page) => {
  // On the Home the entry may be in a closed group (DEC-285): open it first.
  const gruppo = pagina
    .locator('details.accordion-item:not([open])')
    .filter({ has: pagina.getByRole('link', { name: testo, includeHidden: true }) })
  if (!(await pagina.getByRole('link', { name: testo }).first().isVisible())) {
    if (await gruppo.count()) await gruppo.first().locator('summary').click()
  }
  const prima = pagina.url()
  await pagina.getByRole('link', { name: testo }).first().click()
  // The app changes page without loading one: wait for the address, then for its data, so the
  // next step does not act on the page left behind.
  await pagina.waitForURL((url) => url.href !== prima, { timeout: 5_000 }).catch(() => {})
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
  /** Scroll so that this text (a heading) is at the top of the screen; its group opens. */
  mostra?: string
  /** Keep the cookie notice, closed in every other scene. */
  cookie?: boolean
  /** On the server before the page opens (a reload would lock the app). */
  prima?: () => Promise<void>
  /** Put back what `prepara` changed on the server, after the screenshot. */
  dopo?: () => Promise<void>
  /** A scene of the totem names: every other one hides them (below). */
  totem?: boolean
}

// The totem names (DEC-416) are described only in the generic manual: the screenshots are
// the same for both, so every other scene hides them (the menu entry, the person's card,
// the settings).
const NASCONDI_TOTEM = `
  li:has(> a[href="/tribu"]), .col-12:has(> a[href="/tribu"]), a[href="/tribu"], [data-totem] {
    display: none !important;
  }`

// Giulia's totem image waiting for a capo: only during the totem scenes, as it counts in the
// capi's menu, which every other scene shows.
const IMMAGINE_TOTEM = `
from apps.tribu.models import Totem
t = Totem.objects.get(persona__nome="Giulia", persona__cognome="Rossi")
`
const immagineInAttesa = () =>
  django(`${IMMAGINE_TOTEM}
if not t.immagine_in_attesa:
    import io
    from PIL import Image
    from django.core.files.uploadedfile import SimpleUploadedFile
    from apps.tribu import servizi
    b = io.BytesIO()
    Image.new("RGB", (600, 600), "#a0522d").save(b, "JPEG")
    servizi.carica_immagine(t, SimpleUploadedFile("t.jpg", b.getvalue(), "image/jpeg"), True)
`)
const senzaImmagineInAttesa = () =>
  django(`${IMMAGINE_TOTEM}
if t.immagine_in_attesa:
    t.immagine_in_attesa.delete(save=True)
`)

/** Scroll so that the element is at the top of the screen, as `mostra` does. */
const scorriA = (selettore: string) => async (pagina: Page) => {
  await pagina.locator(selettore).evaluate((el) => {
    el.scrollIntoView({ block: 'start' })
    el.closest('.qdc-scorrevole')?.scrollBy(0, -24)
    window.scrollBy(0, -80)
  })
}

/** The side menu with the profile menu open: on the phone it opens from the top button. */
async function apriMenu(pagina: Page): Promise<void> {
  const pulsante = pagina.getByRole('button', { name: 'Apri il menu' })
  if (await pulsante.isVisible()) await pulsante.click()
  await pagina.locator('.ag-sidebar__user-toggle').click()
  await pagina.locator('#menu-profilo').waitFor()
}

/** Python run by Django on the manual's database, for a state no page can create. */
function django(codice: string): Promise<void> {
  return esegui('uv', ['run', 'python', 'manage.py', 'shell', '-c', codice], 'backend', ENV_DJANGO)
}

const CARLA_GENITRICE = `
from apps.anagrafica.models import Persona
from apps.iscrizioni.servizi import annulla_passaggio_in_coca, passaggio_annullabile
carla = Persona.objects.get(nome="Carla", cognome="Verdi")
if passaggio_annullabile(carla):
    annulla_passaggio_in_coca(carla)
`
const MANUTENZIONE = (attiva: boolean) => `
from apps.impostazioni.models import Impostazioni
imp = Impostazioni.carica()
imp.manutenzione = ${attiva ? 'True' : 'False'}
imp.messaggio_manutenzione = "Stiamo aggiornando l'app: torna dopo le 18."
imp.save()
`

// Wrong passwords of the last minutes (they count for an hour): one account, one address.
// Run once per format: the same rows again.
const TENTATIVI_SBAGLIATI = `
from axes.models import AccessAttempt
for email, ip, browser, n in [
    ("${PERSONE.esploratore}@${DOMINIO}", "203.0.113.40", "Firefox", 5),
    ("${PERSONE.genitore}@${DOMINIO}", "198.51.100.23", "Safari", 3),
    ("${PERSONE.genitoreLc}@${DOMINIO}", "198.51.100.23", "Chrome", 2),
]:
    AccessAttempt.objects.update_or_create(
        username=email, ip_address=ip, user_agent=browser,
        defaults=dict(
            http_accept="*/*", path_info="/_allauth/browser/v1/auth/login", get_data="",
            post_data="", failures_since_start=n,
        ),
    )
`

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
      await pagina.getByLabel('Abbiamo inviato un codice').waitFor()
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
  // The calendar page (DEC-286): the month, then the subscription link.
  { nome: 'genitore/calendario-mese', chi: 'genitore', percorso: '/calendario' },
  {
    nome: 'genitore/calendario',
    chi: 'genitore',
    percorso: '/calendario',
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
  // «Invita nel gruppo»: link, QR code and flyer of the waiting list.
  { nome: 'genitore/invita', chi: 'genitore', percorso: '/invita', intera: true },
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
  {
    nome: 'capo/animali-squadriglia',
    chi: 'capoReparto',
    percorso: '/animali-squadriglia',
    prepara: async (pagina) => {
      await pagina.getByLabel('Cerca un animale').fill('pant')
      await pagina.getByText('Sq. Pantere').waitFor()
    },
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
  // The capi (DEC-233): Marco Ferri is capo of the reparto, Elena Conti of the cerchio.
  { nome: 'capo/home', chi: 'capoReparto', percorso: '/', intera: true },
  {
    nome: 'capo/unita',
    chi: 'capoReparto',
    percorso: '/unita',
    prepara: apri('Antares'),
    intera: true,
  },
  {
    // Delegated and revoked again (the data stay as they were), then the choice shown.
    nome: 'capo/delega',
    chi: 'capoReparto',
    percorso: '/unita',
    prepara: async (pagina) => {
      await apri('Antares')(pagina)
      // A field with search (DEC-395): write, then Enter on the first match.
      const delega = pagina.getByLabel('Delega a').last()
      const scegli = async () => {
        await delega.fill('Luca')
        await delega.press('Enter')
      }
      await scegli()
      await pagina.getByRole('button', { name: 'Delega', exact: true }).last().click()
      await pagina.getByText('Le può inserire anche Luca Rossi').waitFor()
      await pagina.getByRole('button', { name: 'Togli la delega' }).click()
      await pagina.getByText('Le inseriscono il capo squadriglia e lo staff.').last().waitFor()
      await scegli()
    },
    mostra: 'Sq. Volpi',
  },
  {
    nome: 'capo/persona',
    chi: 'capoReparto',
    percorso: '/soci',
    prepara: apri('Rossi Luca'),
    intera: true,
  },
  {
    nome: 'capo/percorso',
    chi: 'capoReparto',
    percorso: '/soci',
    prepara: apri('Rossi Luca'),
    mostra: 'Percorso scout',
  },
  {
    nome: 'capo/regole',
    chi: 'capoReparto',
    percorso: '/soci',
    prepara: apri('Rossi Luca'),
    mostra: 'Regole sul rapporto con il minore',
  },
  {
    nome: 'capo/note',
    chi: 'capoReparto',
    percorso: '/soci',
    prepara: apri('Rossi Luca'),
    mostra: 'Note',
  },
  {
    nome: 'capo/sanitaria',
    chi: 'capoReparto',
    percorso: '/soci',
    prepara: async (pagina) => {
      await apri('Rossi Giulia')(pagina)
      await pagina.getByText('Segna la consegna su carta…').click()
    },
    mostra: 'Scheda sanitaria',
  },
  {
    nome: 'capo/invito',
    chi: 'capoReparto',
    percorso: '/soci',
    prepara: async (pagina) => {
      await apri('Marino Alice')(pagina)
      await pagina.getByRole('button', { name: 'Invita' }).first().click()
      await pagina.getByLabel("Email a cui mandare l'invito").fill(`alice.marino@${DOMINIO}`)
    },
    mostra: "Accesso all'app",
  },
  {
    // The parents of the reparto who may get an invitation, one ticked; none sent.
    nome: 'capo/inviti-multipli',
    chi: 'capoReparto',
    percorso: '/genitori',
    prepara: async (pagina) => {
      await pagina.getByRole('button', { name: 'Invita chi non ha un account' }).click()
      const prima = pagina.locator('.card .list-group-item input.check').first()
      await prima.waitFor()
      await prima.check()
    },
  },
  {
    // A novice of 16 without an account: the capogruppo generates his personal link.
    nome: 'capo/link-personale',
    chi: 'capogruppo',
    percorso: '/soci',
    prepara: async (pagina) => {
      await apri('Verdi Paolo')(pagina)
      await pagina.getByRole('button', { name: /^Genera (il|un) link/ }).click()
      linkPersonale = (await pagina.locator('.text-break strong').first().textContent()) ?? ''
    },
    mostra: "Link personale per l'app",
  },
  {
    // The same link opened by the ragazzo, birth date and email written.
    nome: 'ragazzo/attiva',
    percorso: '/accesso',
    prepara: async (pagina) => {
      await pagina.goto(linkPersonale)
      await pagina.getByLabel('La tua data di nascita').fill('2010-09-20')
      await pagina.getByLabel('La tua email').fill(`paolo.verdi@${DOMINIO}`)
    },
  },
  {
    // The panel before the passage, with the confirmation open; nothing is changed.
    nome: 'capo/genitore-in-coca',
    chi: 'capogruppo',
    percorso: '/genitori',
    // On the computer, after the phone's «abilita-censito» brought her in: back a parent.
    prima: () => django(CARLA_GENITRICE),
    prepara: async (pagina) => {
      await apri('Verdi Carla')(pagina)
      await pagina.getByRole('button', { name: 'Porta in Comunità capi…' }).click()
    },
    mostra: 'Comunità capi',
  },
  {
    nome: 'capo/campo',
    chi: 'capoReparto',
    percorso: '/campo',
    prepara: async (pagina) => {
      await pagina.getByRole('combobox').first().selectOption({ label: 'Reparto Antares (N1)' })
      await pagina.getByRole('button', { name: 'Scarica sul dispositivo' }).click()
      await pagina
        .getByText('Cerca per nome')
        .or(pagina.getByPlaceholder('Cerca per nome'))
        .first()
        .waitFor()
    },
    intera: true,
  },
  {
    nome: 'capo/evento-nuovo',
    chi: 'capoReparto',
    percorso: '/eventi',
    prepara: async (pagina) => {
      await pagina.getByRole('button', { name: 'Nuovo evento' }).click()
      await pagina.getByLabel('Titolo').fill('Uscita di primavera')
    },
    intera: true,
  },
  {
    // Saved once unchanged (the form must round-trip), then opened again for the picture.
    nome: 'capo/evento-modifica',
    chi: 'capoReparto',
    percorso: '/eventi',
    prepara: async (pagina) => {
      await apri('Uscita di reparto')(pagina)
      await pagina.getByRole('button', { name: 'Modifica', exact: true }).click()
      await pagina.getByRole('button', { name: 'Salva', exact: true }).click()
      await pagina.getByText('Evento modificato.').waitFor()
      await pagina.getByRole('button', { name: 'Modifica', exact: true }).click()
    },
    mostra: 'Titolo',
  },
  { nome: 'capo/riunioni', chi: 'capoReparto', percorso: '/riunioni', intera: true },
  // The «+» of a day in the month (DEC-412): its menu open on the second day from today.
  {
    nome: 'capo/calendario-crea',
    chi: 'capoReparto',
    percorso: '/calendario',
    prepara: async (pagina) => {
      await pagina.getByRole('button', { name: 'Mese', exact: true }).click()
      await pagina.locator('.qdc-piu').nth(1).click()
      await pagina.getByRole('menuitem', { name: 'Nuova riunione' }).waitFor()
    },
  },
  // One's own events apart from the others (DEC-432).
  {
    nome: 'capo/calendario-miei',
    chi: 'capogruppo',
    percorso: '/calendario',
    prepara: async (pagina) => {
      await pagina.getByLabel('Quali eventi vedere').selectOption({ label: 'Tutto il gruppo' })
      await pagina.getByText('gli altri').first().waitFor()
    },
  },
  // The next birthdays of the whole group, the Co.Ca. marked (DEC-417).
  {
    nome: 'capo/calendario-compleanni',
    chi: 'capoReparto',
    percorso: '/calendario?mostra=compleanni',
    prepara: async (pagina) => {
      await pagina.getByRole('button', { name: 'Prossimi compleanni' }).waitFor()
    },
  },
  {
    nome: 'gruppo/assemblea',
    chi: 'capogruppo',
    percorso: '/riunioni',
    prepara: async (pagina) => {
      await pagina
        .getByRole('link', { name: /Assemblea dei soci/ })
        .first()
        .click()
      await pagina.getByRole('heading', { name: 'Convocazione' }).waitFor()
    },
    mostra: 'Convocazione',
  },
  {
    nome: 'capo/convocazione',
    chi: 'capoReparto',
    percorso: '/riunioni',
    prepara: async (pagina) => {
      await pagina
        .getByRole('link', { name: /Riunione dei genitori/ })
        .first()
        .click()
      await pagina.getByRole('heading', { name: 'Convocazione' }).waitFor()
    },
    mostra: 'Convocazione',
  },
  {
    nome: 'capo/verbale',
    chi: 'capogruppo',
    percorso: '/riunioni',
    prepara: async (pagina) => {
      // Last week's meeting of the Co.Ca.: the list shows the ones to come.
      await pagina.evaluate(async () => {
        const riunioni: { id: number; titolo: string }[] = await (
          await fetch('/api/v1/eventi?riunioni=true')
        ).json()
        const coca = riunioni.find((r) => r.titolo === 'Comunità capi')!
        history.pushState({}, '', `/eventi/${coca.id}`)
        dispatchEvent(new PopStateEvent('popstate'))
      })
      await pagina.getByRole('button', { name: 'Leggi il verbale' }).click()
      await pagina.getByText('Campo di reparto').waitFor()
    },
    mostra: 'Verbale',
  },
  {
    nome: 'capo/verbale-anteprima',
    chi: 'capogruppo',
    percorso: '/riunioni',
    prepara: async (pagina) => {
      // A meeting whose minutes are still to write: the assembly's follow the template.
      await pagina.evaluate(async () => {
        const riunioni: { id: number }[] = await (
          await fetch('/api/v1/eventi?riunioni=true')
        ).json()
        for (const { id } of riunioni) {
          const risposta = await fetch(`/api/v1/eventi/${id}/verbale`)
          if (!risposta.ok) continue
          const verbale = await risposta.json()
          if (verbale.stato === 'BOZZA' && verbale.puo_scrivere && !verbale.da_modello) {
            history.pushState({}, '', `/eventi/${id}`)
            dispatchEvent(new PopStateEvent('popstate'))
            return
          }
        }
        throw new Error('Nessun verbale da scrivere nei dati di prova')
      })
      await pagina.getByRole('button', { name: 'Scrivi il verbale' }).click()
      await pagina.locator('.ProseMirror').click()
      // As who writes: the button gives the cursor back to the text a moment later.
      const scrivi = async (testo: string, dato: string) => {
        await pagina.keyboard.type(testo)
        await pagina.getByRole('button', { name: dato, exact: true }).click()
        await pagina.locator('.ProseMirror:focus').waitFor()
      }
      await scrivi('Riunione del ', '[Data]')
      await scrivi(', dalle ', '[Ora di inizio]')
      await scrivi(' alle ', '[Ora di fine]')
      await scrivi(', a ', '[Luogo]')
      await pagina.getByRole('button', { name: 'Anteprima', exact: true }).click()
      await pagina.getByRole('dialog').getByText('Riunione del ').waitFor()
    },
  },
  {
    nome: 'capo/turni',
    chi: 'capoReparto',
    percorso: '/unita',
    prepara: apri('Antares'),
    mostra: 'Turni',
  },
  {
    // The meetings of Giulia and Luca, with their patrols' turns.
    nome: 'genitore/riunioni',
    chi: 'genitore',
    percorso: '/riunioni',
    prepara: async (pagina) => {
      await pagina.getByText('Turno di').first().waitFor()
    },
  },
  {
    // A weekly series of the reparto at the seat, not created.
    nome: 'capo/riunioni-nuove',
    chi: 'capoReparto',
    percorso: '/riunioni',
    prepara: async (pagina) => {
      await pagina.getByRole('button', { name: 'Nuove riunioni' }).click()
      await pagina.getByLabel('Unità').selectOption({ label: 'Reparto Antares (N1)' })
      await pagina.getByLabel('Chi è invitato').selectOption('ALTA_SQ')
      await pagina.getByLabel('Al', { exact: true }).fill(`${new Date().getFullYear() + 1}-05-31`)
      await pagina.getByLabel('Località').selectOption({ label: 'Sede del gruppo' })
    },
    intera: true,
  },
  {
    // People chosen one by one, not created (DEC-430).
    nome: 'capo/riunioni-selezionati',
    chi: 'capoReparto',
    percorso: '/riunioni',
    prepara: async (pagina) => {
      await pagina.getByRole('button', { name: 'Nuove riunioni' }).click()
      await pagina.getByLabel('Di chi').selectOption('scelti')
      await pagina.locator('.qdc-scelta-persone input').first().waitFor()
      await pagina.locator('.qdc-scelta-persone input').nth(2).check()
      await pagina.locator('.qdc-scelta-persone input').nth(4).check()
      await pagina.getByLabel('Filtra per unità').selectOption({ index: 1 })
      await pagina.getByLabel('Una volta').check()
      await pagina.getByLabel('Dalle').fill('20:30')
      await pagina.getByLabel('Titolo').fill('Preparazione della festa di apertura')
    },
    mostra: 'Di chi',
    intera: true,
  },
  {
    // A joint staff meeting of the reparto and the cerchio, online, not created (DEC-401, DEC-402).
    nome: 'capo/riunioni-staff',
    chi: 'capoReparto',
    percorso: '/riunioni',
    prepara: async (pagina) => {
      await pagina.getByRole('button', { name: 'Nuove riunioni' }).click()
      await pagina.getByLabel('Di chi').selectOption('staff')
      await pagina.getByLabel(/Antares/).check()
      await pagina.getByLabel(/Fiordaliso/).check()
      await pagina.getByLabel('Una volta').check()
      await pagina.getByLabel('Dalle').fill('21:00')
      await pagina.getByLabel('Alle', { exact: true }).fill('22:30')
      await pagina.getByLabel('Come').selectOption('ONLINE')
      await pagina.getByLabel('Link della riunione').fill('https://meet.google.com/abc-defg-hij')
    },
    intera: true,
  },
  {
    // The next meeting being changed: its notes in the editor.
    nome: 'capo/riunione-modifica',
    chi: 'capoReparto',
    percorso: '/riunioni',
    prepara: async (pagina) => {
      await apri('Riunione di Reparto Antares')(pagina)
      await pagina.getByRole('button', { name: 'Modifica la riunione' }).click()
      await pagina.locator('.ProseMirror').first().waitFor()
    },
    mostra: 'Giorno',
  },
  {
    nome: 'capo/presenze',
    chi: 'capoReparto',
    percorso: '/riunioni',
    prepara: async (pagina) => {
      await apri('Riunione di Reparto Antares')(pagina)
      await pagina.getByRole('button', { name: 'Presente', exact: true }).first().click()
    },
    mostra: 'Partecipanti',
  },
  {
    nome: 'capo/quota-evento',
    chi: 'capoReparto',
    percorso: '/eventi',
    prepara: apri('Uscita di reparto'),
    mostra: 'Quota',
  },
  { nome: 'capo/buonacaccia', chi: 'capoReparto', percorso: '/buonacaccia', intera: true },
  {
    // A new event: its type brings the constraints (DEC-398); nothing is saved.
    nome: 'capo/evento-bc-tipo',
    chi: 'capoReparto',
    percorso: '/buonacaccia',
    prepara: async (pagina) => {
      await pagina.getByLabel("Nome o luogo dell'evento").fill('Capi Squadriglia di Zona')
      await pagina.getByRole('button', { name: "Non c'è: aggiungilo" }).click()
      const tipo = pagina.locator('#bc-tipologia')
      await tipo.click()
      await tipo.fill('capi sq')
      await pagina.locator('li[role=option]').first().waitFor()
      await tipo.press('Enter')
      await pagina.getByLabel(/Età minima/).fill('14')
      await pagina.getByLabel(/Età massima/).fill('16')
    },
    mostra: 'Tipo di evento',
  },
  {
    nome: 'capo/tipologie-bc',
    chi: 'capoReparto',
    percorso: '/buonacaccia/tipologie',
    prepara: async (pagina) => {
      await pagina.getByLabel('Cerca un tipo').fill('squadriglia')
    },
  },
  {
    nome: 'capo/iscrizione-bc',
    chi: 'capoReparto',
    percorso: '/eventi',
    prepara: apri('Campo di specialità di Zona'),
    mostra: 'Iscrizioni su BuonaCaccia',
  },
  {
    nome: 'capo/sentiero-unita',
    chi: 'capoReparto',
    percorso: '/unita',
    prepara: async (pagina) => {
      await apri('Antares')(pagina)
      await apri('Progressione Personale')(pagina)
    },
    intera: true,
  },
  {
    nome: 'capo/sentiero-eg',
    chi: 'capoReparto',
    percorso: '/soci',
    prepara: async (pagina) => {
      await apri('Rossi Giulia')(pagina)
      await apri('Sentiero (Progressione Personale)')(pagina)
    },
    intera: true,
  },
  {
    nome: 'capo/correggi-tappa',
    chi: 'capoReparto',
    percorso: '/soci',
    prepara: async (pagina) => {
      await apri('Rossi Giulia')(pagina)
      await apri('Sentiero (Progressione Personale)')(pagina)
      await pagina.getByRole('button', { name: 'correggi una data…' }).first().click()
      await pagina
        .getByLabel('Quale data di Scoperta')
        .selectOption({ label: 'Riconoscimento (Consiglio della Legge)' })
      await pagina
        .getByLabel('Perché la correggi')
        .fill('Il Consiglio della Legge era il giorno prima')
    },
    mostra: 'Tappe',
  },
  {
    nome: 'capo/stagioni',
    chi: 'capoCerchio',
    percorso: '/unita',
    prepara: async (pagina) => {
      await apri('Fiordaliso')(pagina)
      await apri('Progressione Personale')(pagina)
    },
    mostra: 'Stagioni di caccia o di volo',
  },
  {
    // Davide Ricci is the capo of the clan (and the technical administrator).
    nome: 'capo/punto-strada',
    chi: 'amministratore',
    percorso: '/soci',
    prepara: async (pagina) => {
      await apri('Russo Chiara')(pagina)
      await apri('Sentiero (Progressione Personale)')(pagina)
      await pagina.getByRole('button', { name: 'Nuovo Punto della Strada' }).click()
    },
    mostra: 'Punti della Strada',
  },
  {
    nome: 'capo/passaggi',
    chi: 'capoReparto',
    percorso: '/unita',
    prepara: async (pagina) => {
      await apri('Antares')(pagina)
      await apri('Passaggi')(pagina)
      await pagina.getByRole('button', { name: 'Prepara un passaggio' }).click()
    },
    intera: true,
  },
  {
    nome: 'capo/fascicolo-anno',
    chi: 'capoReparto',
    percorso: '/soci',
    prepara: async (pagina) => {
      await apri('Rossi Luca')(pagina)
      await apri("Fascicolo dell'anno")(pagina)
    },
    intera: true,
  },
  {
    nome: 'capo/fascicolo-capo',
    chi: 'capoReparto',
    percorso: '/',
    prepara: async (pagina) => {
      await apri('Il mio profilo')(pagina)
      await apri('Servizio e formazione')(pagina)
    },
    intera: true,
  },
  {
    nome: 'capo/avviso',
    chi: 'capoReparto',
    percorso: '/bacheca',
    prepara: async (pagina) => {
      await pagina.getByRole('button', { name: 'Nuovo avviso' }).click()
      await pagina.getByLabel('Titolo').fill('Riunione dei genitori del reparto')
      await pagina
        .getByLabel('Testo')
        .fill('Sabato dopo la riunione presentiamo il campo invernale.')
      await pagina
        .getByLabel('Per', { exact: true })
        .selectOption({ label: 'Reparto Antares (N1)' })
      await pagina.getByRole('radio', { name: 'Solo i genitori' }).click()
    },
    intera: true,
  },
  { nome: 'capo/spese', chi: 'capoReparto', percorso: '/spese', intera: true },
  {
    nome: 'capo/impersona',
    chi: 'capoReparto',
    percorso: '/impersonazioni',
    prepara: async (pagina) => {
      // The results appear while one writes (DEC-397).
      await pagina.getByLabel('Nome, cognome o email').fill('Rossi')
      await pagina
        .getByRole('button', { name: /^Impersona / })
        .first()
        .waitFor()
    },
    intera: true,
  },
  {
    // After the camp download and the year's file: their reads are in the log.
    nome: 'capo/registro-accessi',
    chi: 'capoReparto',
    percorso: '/soci',
    prepara: async (pagina) => {
      await apri('Rossi Giulia')(pagina)
      await pagina.getByRole('button', { name: 'Mostra il registro' }).click()
      await pagina.locator('.list-group-item').first().waitFor()
    },
    mostra: 'Chi ha visto i dati delicati',
  },
  {
    nome: 'capo/foto-precedenti',
    chi: 'capoReparto',
    percorso: '/soci',
    prepara: async (pagina) => {
      await apri('Rossi Giulia')(pagina)
      await pagina.getByRole('button', { name: 'Foto precedenti' }).click()
      await pagina.getByText('Nascondi le foto precedenti').waitFor()
    },
  },
  { nome: 'capo/attesa', chi: 'capoCerchio', percorso: '/attesa', intera: true },
  { nome: 'capo/richieste', chi: 'capoCerchio', percorso: '/iscrizioni', intera: true },
  // Francesca Gallo is the group treasurer; Laura Bianchi the capogruppo.
  { nome: 'gruppo/home', chi: 'capogruppo', percorso: '/', intera: true },
  {
    nome: 'gruppo/importazione',
    chi: 'capogruppo',
    percorso: '/importazione',
    prepara: async (pagina) => {
      await pagina.locator('input[type=file]').setInputFiles(EXPORT_DI_PROVA)
      await pagina.getByRole('button', { name: 'Anteprima' }).click()
      await pagina.getByRole('button', { name: "Applica l'importazione" }).waitFor()
    },
    intera: true,
  },
  { nome: 'gruppo/incarichi', chi: 'capogruppo', percorso: '/gruppo', intera: true },
  {
    nome: 'gruppo/criteri-ammissione',
    chi: 'capogruppo',
    percorso: '/criteri-ammissione',
    prepara: async (pagina) => {
      await pagina.getByRole('button', { name: 'Nuova versione' }).click()
      await pagina.getByLabel('Valida dal').waitFor()
    },
    intera: true,
  },
  {
    nome: 'gruppo/scheda-incarichi',
    chi: 'capogruppo',
    percorso: '/gruppo/scheda-incarichi',
    intera: true,
  },
  {
    // The menu of the kinds of role open, one of them unticked.
    nome: 'gruppo/elenco-incarichi',
    chi: 'capogruppo',
    percorso: '/gruppo',
    mostra: 'Elenco degli incarichi',
    prepara: async (pagina) => {
      await pagina.locator('#elenco-ruoli').click()
      await pagina.locator('#elenco-ruoli + .menu [role=option]').last().click()
      await pagina.locator('#elenco-ruoli + .menu').evaluate((m) => (m.scrollTop = 0))
    },
  },
  { nome: 'gruppo/impostazioni', chi: 'capogruppo', percorso: '/impostazioni', intera: true },
  {
    // The editor with the group's logo, centred and made small; nothing is saved.
    nome: 'gruppo/editor-testo',
    chi: 'capogruppo',
    percorso: '/impostazioni/email-piede',
    prepara: async (pagina) => {
      const editor = pagina.locator('.ProseMirror').first()
      await editor.click()
      await pagina
        .locator('input[type=file][accept="image/png,image/jpeg"]')
        .first()
        .setInputFiles(join(RADICE, 'resources', 'logo-avellino1.png'))
      const logo = editor.locator('img[src^="/api/v1/immagini/"]').first()
      await logo.waitFor()
      await pagina.getByRole('button', { name: 'Allinea al centro' }).first().click()
      await logo.click()
      await pagina.getByRole('button', { name: 'Piccola' }).click()
      await pagina.getByRole('group', { name: "Dimensione dell'immagine" }).waitFor()
    },
  },
  {
    nome: 'gruppo/volantino',
    chi: 'capogruppo',
    percorso: '/impostazioni',
    mostra: "Volantino della lista d'attesa",
  },
  {
    // Switched on from the page itself; the bar says only administrators get in.
    nome: 'gruppo/manutenzione',
    chi: 'amministratore',
    percorso: '/impostazioni',
    prepara: async (pagina) => {
      await pagina.getByLabel('Messaggio').fill("Stiamo aggiornando l'app: torna dopo le 18.")
      await pagina.getByRole('button', { name: 'Metti in manutenzione' }).click()
      await pagina.getByRole('button', { name: 'Termina la manutenzione' }).waitFor()
      await pagina.getByText('Manutenzione in corso:').waitFor()
    },
    mostra: 'Manutenzione',
    dopo: () => django(MANUTENZIONE(false)),
  },
  {
    nome: 'gruppo/coda-email',
    chi: 'amministratore',
    percorso: '/impostazioni',
    mostra: "Invio un po' alla volta",
  },
  {
    // One account opened, the action chosen, nothing confirmed.
    nome: 'gruppo/account',
    chi: 'amministratore',
    percorso: '/amministrazione/account',
    prepara: async (pagina) => {
      await pagina.getByRole('button', { name: 'Gestisci' }).first().click()
      await pagina.getByLabel('Cosa fare').selectOption('DISATTIVA')
      await pagina.getByLabel('Motivo').fill('Ha perso il telefono')
    },
  },
  {
    nome: 'gruppo/accessi-bloccati',
    chi: 'amministratore',
    percorso: '/impostazioni',
    prepara: async (pagina) => {
      await django(TENTATIVI_SBAGLIATI)
      await pagina.getByRole('button', { name: "Aggiorna l'elenco" }).click()
      await pagina.getByRole('button', { name: 'Sblocca' }).first().waitFor()
    },
    mostra: 'Accessi bloccati',
  },
  {
    // A parent already in the app when the maintenance starts.
    nome: 'comune/manutenzione',
    chi: 'genitore',
    percorso: '/',
    prepara: async (pagina) => {
      await django(MANUTENZIONE(true))
      await pagina.reload()
      await pagina.waitForLoadState('networkidle')
      if (new URL(pagina.url()).pathname === '/sblocco') {
        // Six boxes: the app unlocks at the sixth digit.
        await pagina.getByLabel('PIN', { exact: true }).fill(PIN)
      }
      await pagina.getByRole('heading', { name: "L'app è in manutenzione" }).waitFor()
    },
    dopo: () => django(MANUTENZIONE(false)),
  },
  {
    nome: 'gruppo/impostazioni-pagamenti',
    chi: 'tesoriera',
    percorso: '/impostazioni',
    mostra: 'Pagamenti',
  },
  { nome: 'gruppo/quote', chi: 'tesoriera', percorso: '/quote', intera: true },
  {
    nome: 'gruppo/pagamento',
    chi: 'tesoriera',
    percorso: '/soci',
    prepara: async (pagina) => {
      await apri('Rossi Giulia')(pagina)
      await pagina.getByRole('button', { name: 'Registra un pagamento' }).click()
    },
    mostra: 'Pagamento ricevuto',
  },
  {
    nome: 'gruppo/da-verificare',
    chi: 'tesoriera',
    percorso: '/pagamenti-da-verificare',
    intera: true,
  },
  { nome: 'gruppo/prima-nota', chi: 'tesoriera', percorso: '/cassa', intera: true },
  { nome: 'gruppo/estratto-conto', chi: 'tesoriera', percorso: '/banca', intera: true },
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
  {
    // Last: it brings a parent into the Co.Ca. (DEC-307) and lets her in as registered
    // (DEC-400). Run once per format, so each step only if still to do.
    nome: 'capo/abilita-censito',
    chi: 'capogruppo',
    percorso: '/genitori',
    prepara: async (pagina) => {
      await apri('Verdi Carla')(pagina)
      const porta = pagina.getByRole('button', { name: 'Porta in Comunità capi…' })
      const abilitata = pagina.getByText('abilitato come censito dal')
      await porta.or(abilitata).waitFor()
      if (await porta.isVisible()) {
        await porta.click()
        await pagina.getByRole('button', { name: 'Porta in Comunità capi', exact: true }).click()
      }
      const abilita = pagina.getByRole('button', { name: 'Abilita come censito…' })
      await abilita.or(pagina.getByRole('button', { name: "Togli l'abilitazione…" })).waitFor()
      if (await abilita.isVisible()) {
        await abilita.click()
        await pagina.getByRole('button', { name: 'Abilita come censito', exact: true }).click()
      }
      await abilitata.waitFor()
    },
    mostra: 'Codice socio',
  },
  // The book of ceremonies (DEC-437): the capo reads everything, Giulia the reparto's entry
  // she was added to; the capo unità changes it.
  { nome: 'cerimonie/elenco', chi: 'capoReparto', percorso: '/cerimonie', intera: true },
  {
    nome: 'cerimonie/ragazzo',
    chi: 'capoSquadriglia',
    percorso: '/cerimonie',
    prepara: apri("Notte dell'Alta Squadriglia"),
    intera: true,
  },
  {
    nome: 'cerimonie/modifica',
    chi: 'capoReparto',
    percorso: '/cerimonie',
    prepara: async (pagina) => {
      await apri("Notte dell'Alta Squadriglia")(pagina)
      await pagina.getByRole('button', { name: 'Modifica' }).click()
      await pagina.locator('#voce-aggiunti-cerca').waitFor()
    },
    intera: true,
  },
  // Totem names (DEC-416): only in the generic manual. Giulia's image waits for a capo.
  {
    nome: 'tribu/ragazzo',
    chi: 'capoSquadriglia',
    percorso: '/tribu',
    prima: immagineInAttesa,
    dopo: senzaImmagineInAttesa,
    intera: true,
    totem: true,
  },
  {
    nome: 'tribu/profilo',
    chi: 'capoSquadriglia',
    percorso: '/',
    prima: immagineInAttesa,
    prepara: async (pagina) => {
      await apri('Il mio profilo')(pagina)
      await scorriA('[data-totem]')(pagina)
    },
    dopo: senzaImmagineInAttesa,
    totem: true,
  },
  {
    nome: 'tribu/capo',
    chi: 'capoReparto',
    percorso: '/tribu',
    prima: immagineInAttesa,
    dopo: senzaImmagineInAttesa,
    intera: true,
    totem: true,
  },
  {
    nome: 'tribu/assegna',
    chi: 'capoReparto',
    percorso: '/soci',
    prepara: async (pagina) => {
      await apri('Rossi Luca')(pagina)
      await scorriA('[data-totem]')(pagina)
    },
    totem: true,
  },
  {
    nome: 'tribu/impostazioni',
    chi: 'capogruppo',
    percorso: '/impostazioni',
    prepara: scorriA('#tribu'),
    totem: true,
  },
]

// Long pages in groups (DEC-426): a scene touches what a person would see after opening its
// group. Before each action on an element in a closed group, that group opens with a tap on its
// title, so the scenes read as before.
const AZIONI = new Set([
  'click',
  'fill',
  'check',
  'uncheck',
  'selectOption',
  'setInputFiles',
  'press',
  'waitFor',
])
const LOCATORI = new Set([
  'first',
  'last',
  'nth',
  'filter',
  'locator',
  'getByRole',
  'getByText',
  'getByLabel',
  'getByPlaceholder',
  'getByTitle',
  'getByTestId',
  'or',
  'and',
])

async function apriGruppoDi(locatore: Locator): Promise<void> {
  const primo = locatore.first()
  // Visible, or about to be (after a save, a message appears): nothing to open.
  try {
    await primo.waitFor({ state: 'visible', timeout: 2_000 })
    return
  } catch {
    // Hidden, maybe in a closed group.
  }
  const pagina = locatore.page()
  await pagina.waitForLoadState('networkidle')
  const chiusi = await pagina
    .locator('details[data-gruppo]')
    .evaluateAll((gruppi) =>
      (gruppi as HTMLDetailsElement[])
        .filter((g) => !g.open && getComputedStyle(g).display !== 'none')
        .map((g) => g.dataset.gruppo!),
    )
  for (const chiave of chiusi) {
    await pagina.locator(`details[data-gruppo="${chiave}"] > summary`).click()
    await pagina.waitForTimeout(300)
    if (await primo.isVisible()) return
  }
}

function conGruppiLocatore(locatore: Locator): Locator {
  return new Proxy(locatore, {
    get(bersaglio, nome, ricevente) {
      const valore = Reflect.get(bersaglio, nome, ricevente)
      if (typeof valore !== 'function' || typeof nome !== 'string') return valore
      if (AZIONI.has(nome))
        return async (...argomenti: unknown[]) => {
          await apriGruppoDi(bersaglio)
          return valore.apply(bersaglio, argomenti)
        }
      if (LOCATORI.has(nome))
        return (...argomenti: unknown[]) => conGruppiLocatore(valore.apply(bersaglio, argomenti))
      return valore.bind(bersaglio)
    },
  })
}

function conGruppi(pagina: Page): Page {
  return new Proxy(pagina, {
    get(bersaglio, nome, ricevente) {
      const valore = Reflect.get(bersaglio, nome, ricevente)
      if (typeof valore !== 'function' || typeof nome !== 'string') return valore
      if (LOCATORI.has(nome))
        return (...argomenti: unknown[]) => conGruppiLocatore(valore.apply(bersaglio, argomenti))
      return valore.bind(bersaglio)
    },
  })
}

/** Opens a group of a long page (DEC-426) the way a person does: a tap on its title. */
async function apriGruppo(pagina: Page, chiave: string) {
  const gruppo = pagina.locator(`details[data-gruppo="${chiave}"]`)
  if (!(await gruppo.evaluate((d) => (d as HTMLDetailsElement).open))) {
    await gruppo.locator('> summary').click()
  }
  await pagina.waitForTimeout(300)
}

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
  // As in production (DEC-311): the emails to many wait; nobody sends them here.
  QDC_EMAIL_IN_CODA: 'true',
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
    ['run', 'python', 'manage.py', 'dati_di_prova', '--azzera', '--csv', EXPORT_DI_PROVA],
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
    // The manual is Avellino 1's: its logo, not the AGESCI one of a new installation
    // (DEC-294).
    QDC_LOGO: 'resources/logo-avellino1.png',
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
  await pagina.getByLabel('PIN di 6 cifre').fill(PIN)
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
          // The secret that unlocks the data with the login passkey (DEC-295).
          hasPrf: true,
        },
      })
      if (scena.chi) await entra(contesto.pages()[0]!, scena.chi, !scena.senzaProtezione)
    }
    const pagina = contesto.pages()[0] ?? (await contesto.newPage())
    await scena.prima?.()
    await pagina.goto(`${APP}${scena.percorso}`)
    await pagina.waitForLoadState('networkidle')
    // A reload locks the app (the key lives only in memory): unlock, back to the page.
    if (new URL(pagina.url()).pathname === '/sblocco' && scena.percorso !== '/sblocco') {
      await pagina.getByLabel('PIN', { exact: true }).fill(PIN)
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
    if (!scena.totem) await pagina.addStyleTag({ content: NASCONDI_TOTEM })
    try {
      await scena.prepara?.(conGruppi(pagina))
    } catch (errore) {
      // What the page looked like when a step failed, to see why.
      const file = join(tmpdir(), `schermate-errore-${scena.nome.replace('/', '-')}.png`)
      await pagina.screenshot({ path: file, fullPage: true })
      console.error(`Schermata del passo fallito: ${file}`)
      throw errore
    }
    if (scena.mostra) {
      // A heading inside a closed group of a long page (DEC-426): open that group first.
      const chiave = await pagina
        .getByText(scena.mostra, { exact: true })
        .first()
        .evaluate((el) => {
          const gruppo = el.closest('details[data-gruppo]') as HTMLDetailsElement | null
          return gruppo && !gruppo.open ? gruppo.dataset.gruppo! : null
        })
      if (chiave) await apriGruppo(pagina, chiave)
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
    await scena.dopo?.()
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
