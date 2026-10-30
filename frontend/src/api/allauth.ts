/**
 * django-allauth headless, "browser" client (session cookie).
 *
 * Endpoints verified on django-allauth 65.20 by resolving the Django URLconf.
 * The full contract is served in dev at /_allauth/openapi.html: check there before
 * adding calls, never guess paths or payloads.
 */
import { startAuthentication, startRegistration } from '@simplewebauthn/browser'

import { ErroreApi, leggiCookie, richiesta } from './http'

const BASE = '/_allauth/browser/v1'

export interface SessioneAllauth {
  status: number
  data: {
    user?: { email: string }
    flows?: { id: string; is_pending?: boolean; types?: string[] }[]
  }
  meta: { is_authenticated: boolean }
}

/** A login passkey (allauth "webauthn" authenticator); times in seconds. */
export interface Passkey {
  id: number
  name: string
  created_at: number
  last_used_at: number | null
}

/**
 * Adding or removing a passkey needs a recent login (allauth's reauthentication, 5
 * minutes): otherwise allauth answers 401 with the ways to confirm (`flows`).
 */
export class RiautenticazioneRichiesta extends Error {
  constructor(
    readonly conPassword: boolean,
    readonly conPasskey: boolean,
  ) {
    super('Conferma che sei tu.')
  }
}

async function oRiautentica<T>(chiamataProtetta: () => Promise<T>): Promise<T> {
  try {
    return await chiamataProtetta()
  } catch (errore) {
    if (errore instanceof ErroreApi && errore.stato === 401) {
      const flussi = (errore.dati as SessioneAllauth | null)?.data?.flows ?? []
      throw new RiautenticazioneRichiesta(
        flussi.some((f) => f.id === 'reauthenticate'),
        flussi.some((f) => f.id === 'mfa_reauthenticate' && f.types?.includes('webauthn')),
      )
    }
    throw errore
  }
}

/** allauth answers 401 for "not authenticated (yet)": that is a state, not an error. */
async function chiamata(percorso: string, metodo = 'GET', corpo?: unknown) {
  try {
    return await richiesta<SessioneAllauth>(`${BASE}${percorso}`, { metodo, corpo })
  } catch (errore) {
    if (errore instanceof ErroreApi && errore.stato === 401) {
      return errore.dati as SessioneAllauth
    }
    throw errore
  }
}

export const allauth = {
  sessione: () => chiamata('/auth/session'),
  accedi: (email: string, password: string) => chiamata('/auth/login', 'POST', { email, password }),
  richiediCodice: (email: string) => chiamata('/auth/code/request', 'POST', { email }),
  confermaCodice: (code: string) => chiamata('/auth/code/confirm', 'POST', { code }),
  esci: () => chiamata('/auth/session', 'DELETE'),
  /** Headless signup takes a single "password" field (allauth SignupInput). */
  registrati: (email: string, password: string) =>
    chiamata('/auth/signup', 'POST', { email, password }),
  verificaEmail: (key: string) => chiamata('/auth/email/verify', 'POST', { key }),
  richiediRecuperoPassword: (email: string) =>
    chiamata('/auth/password/request', 'POST', { email }),
  reimpostaPassword: (key: string, password: string) =>
    chiamata('/auth/password/reset', 'POST', { key, password }),
  /** Second step when the account has TOTP enabled (flow "mfa_authenticate"). */
  confermaSecondoFattore: (code: string) => chiamata('/auth/2fa/authenticate', 'POST', { code }),

  /**
   * Google / Apple (DEC-22). The browser flow is a full-page form POST: allauth redirects
   * to the provider and back to `callbackUrl` with the session already set.
   */
  accediConProvider(provider: 'google' | 'apple', callbackUrl: string) {
    const modulo = document.createElement('form')
    modulo.method = 'POST'
    modulo.action = `${BASE}/auth/provider/redirect`
    const campi = {
      provider,
      callback_url: callbackUrl,
      process: 'login',
      csrfmiddlewaretoken: leggiCookie('csrftoken') ?? '',
    }
    for (const [nome, valore] of Object.entries(campi)) {
      const input = document.createElement('input')
      input.type = 'hidden'
      input.name = nome
      input.value = valore
      modulo.appendChild(input)
    }
    document.body.appendChild(modulo)
    modulo.submit()
  },

  /** Passkey login (DEC-22). */
  async accediConPasskey() {
    const opzioni = await richiesta<{ data: { request_options: { publicKey: unknown } } }>(
      `${BASE}/auth/webauthn/login`,
    )
    const credenziale = await startAuthentication({
      // allauth returns WebAuthn options in JSON form; simplewebauthn expects the same.
      optionsJSON: opzioni.data.request_options.publicKey as never,
    })
    return chiamata('/auth/webauthn/login', 'POST', { credential: credenziale })
  },
}

/** Login passkeys of the account (DEC-22): created here, used on the login page. */
export const passkey = {
  async elenco(): Promise<Passkey[]> {
    const risposta = await richiesta<{ data: (Passkey & { type: string })[] }>(
      `${BASE}/account/authenticators`,
    )
    return risposta.data.filter((a) => a.type === 'webauthn')
  },

  /**
   * Creates a passkey on this device. Passwordless (a discoverable credential): the
   * login page asks for no email first.
   */
  async crea(nome: string): Promise<void> {
    const percorso = `${BASE}/account/authenticators/webauthn`
    const opzioni = await oRiautentica(() =>
      richiesta<{ data: { creation_options: { publicKey: unknown } } }>(`${percorso}?passwordless`),
    )
    const credenziale = await startRegistration({
      optionsJSON: opzioni.data.creation_options.publicKey as never,
    })
    await oRiautentica(() =>
      richiesta(percorso, {
        metodo: 'POST',
        corpo: { name: nome, credential: credenziale, passwordless: true },
      }),
    )
  },

  rimuovi: (id: number) =>
    oRiautentica(() =>
      richiesta(`${BASE}/account/authenticators/webauthn`, {
        metodo: 'DELETE',
        corpo: { authenticators: [id] },
      }),
    ),

  riautenticaConPassword: (password: string) =>
    richiesta(`${BASE}/auth/reauthenticate`, { metodo: 'POST', corpo: { password } }),

  async riautenticaConPasskey(): Promise<void> {
    const percorso = `${BASE}/auth/webauthn/reauthenticate`
    const opzioni = await richiesta<{ data: { request_options: { publicKey: unknown } } }>(percorso)
    const credenziale = await startAuthentication({
      optionsJSON: opzioni.data.request_options.publicKey as never,
    })
    await richiesta(percorso, { metodo: 'POST', corpo: { credential: credenziale } })
  },
}

/** Human-readable messages from an allauth 400 ({ errors: [{ message }] }). */
export function messaggiAllauth(dati: unknown): string[] {
  const errori = (dati as { errors?: { message: string }[] } | null)?.errors
  return errori?.map((e) => e.message) ?? []
}

/** Pending step of an unfinished login (e.g. "verify_email", "mfa_authenticate"). */
export function flussoInSospeso(sessione: SessioneAllauth): string | null {
  return sessione.data?.flows?.find((f) => f.is_pending)?.id ?? null
}
