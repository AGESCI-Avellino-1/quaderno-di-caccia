/**
 * Minimal fetch wrapper for the Django API (same origin: session cookie + CSRF).
 */

export class ErroreApi extends Error {
  constructor(
    public readonly stato: number,
    public readonly dati: unknown,
  ) {
    super(`Errore API ${stato}`)
  }
}

export function leggiCookie(nome: string, cookie: string = document.cookie): string | null {
  for (const parte of cookie.split(';')) {
    const [chiave, ...valore] = parte.trim().split('=')
    if (chiave === nome) return decodeURIComponent(valore.join('='))
  }
  return null
}

/**
 * JSON when the server says so; otherwise the raw text (Django HTML error pages, a 502
 * from the proxy). Never throw here: a parse error would look like "offline".
 */
function leggiCorpo(testo: string, contentType: string | null): unknown {
  if (!testo) return null
  if (contentType?.includes('json')) {
    try {
      return JSON.parse(testo)
    } catch {
      return testo
    }
  }
  return testo
}

/** Observers of every server answer: the vault listens for the offline expiry header and
 * for device revocation (src/sicurezza/collegamenti.ts). Keeps this module dependency-free. */
export type OsservatoreRisposte = (risposta: Response, dati: unknown) => void | Promise<void>
const osservatori: OsservatoreRisposte[] = []

export function osservaRisposte(osservatore: OsservatoreRisposte): () => void {
  osservatori.push(osservatore)
  return () => {
    const i = osservatori.indexOf(osservatore)
    if (i >= 0) osservatori.splice(i, 1)
  }
}

const METODI_SICURI = new Set(['GET', 'HEAD', 'OPTIONS'])

export interface OpzioniRichiesta {
  metodo?: string
  corpo?: unknown
  intestazioni?: Record<string, string>
}

export async function richiesta<T>(percorso: string, opzioni: OpzioniRichiesta = {}): Promise<T> {
  const metodo = (opzioni.metodo ?? 'GET').toUpperCase()
  const intestazioni: Record<string, string> = {
    Accept: 'application/json',
    ...opzioni.intestazioni,
  }
  let body: BodyInit | undefined
  if (opzioni.corpo instanceof FormData) {
    body = opzioni.corpo
  } else if (opzioni.corpo !== undefined) {
    intestazioni['Content-Type'] = 'application/json'
    body = JSON.stringify(opzioni.corpo)
  }
  if (!METODI_SICURI.has(metodo)) {
    const csrf = leggiCookie('csrftoken')
    if (csrf) intestazioni['X-CSRFToken'] = csrf
  }
  const risposta = await fetch(percorso, {
    method: metodo,
    headers: intestazioni,
    body,
    credentials: 'same-origin',
  })
  const testo = await risposta.text()
  const dati = leggiCorpo(testo, risposta.headers.get('Content-Type'))
  for (const osservatore of osservatori) await osservatore(risposta, dati)
  if (!risposta.ok) throw new ErroreApi(risposta.status, dati)
  return dati as T
}
