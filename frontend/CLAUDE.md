# frontend/CLAUDE.md

Vue 3.5 · TypeScript 6 · Vite 8 · vue-router 5 · Pinia 4 · Dexie 4 · Bootstrap 5.3 ·
vite-plugin-pwa 2 · Vitest 5. Node 22. Read the root `CLAUDE.md` first.

## Layout

| Path | What |
| --- | --- |
| `src/api/http.ts` | `richiesta<T>()`: fetch, same-origin cookie, `X-CSRFToken` on writes, `ErroreApi` for non-2xx (body parsed as JSON only when the server says so) |
| `src/api/allauth.ts` | allauth headless *browser* client (session, login, code, passkey, providers, signup, email verify, password reset, TOTP) |
| `src/api/qdc.ts` | Typed QdC API (mirror of the ninja schemas) + `temaDellaBranca` |
| `src/offline/db.ts` | Dexie DB (schema v2): `coda`, `cache` (encrypted payloads), `protezione` (vault), `meta` (device id); `svuotaDatiLocali()` / `cancellaTutto()` |
| `src/offline/outbox.ts` | `scrivi()` (entry point), `accoda()` + `inviaCoda()` with `Idempotency-Key` (DEC-96) |
| `src/offline/cache.ts` | `leggiConCache()`: network first, encrypted device copy when offline; `salvaInCache()`, `leggiDallaCache()` |
| `src/sicurezza/` | Device protection (DEC-97): `cripto.ts` (Web Crypto), `cassaforte.ts` (vault states, PIN, wrong-PIN wipe, expiry), `biometria.ts` (passkey PRF), `dispositivo.ts` (registration, revocation check at start-up), `collegamenti.ts` (server headers → vault) |
| `src/stores/sessione.ts` | Profile (`/api/v1/io`), role flags for menus, branch theme |
| `src/composables/` | `useRete` (online state, queue counters, auto-send), `useErrore` (readable errors), `useBloccoAutomatico` (lock after inactivity) |
| `src/router/index.ts` | Routes; `meta.pubblica`, `meta.richiede` (menu guard only) |
| `src/theme/` | AGESCI palette (copied from the Django theme, do not edit) + `qdc.scss` |
| `docker/` | nginx config for the production `app` container |

## Rules

- **Permissions are not enforced here.** `sessione.capo`, `puoImportare`, route
  `meta.richiede` only hide UI. Every check that matters is in the backend policy.
- **Do not put data in `localStorage` or directly in Dexie.** Reads for offline use go
  through `leggiConCache` / `salvaInCache` (encrypted, nothing saved in "solo online"
  mode); the service worker caches only the app shell, never API responses.
- **Writes** go through `scrivi({metodo, percorso, corpo, descrizione})`: queued and
  encrypted when the vault is active, sent directly otherwise. `descrizione` is stored
  in clear and shown in *Modifiche in sospeso*: no names, no health data. A 4xx stays
  in the queue as `errore` for the user to fix or discard: never drop it silently.
- The router guard order is deliberate: vault initialisation and revocation check →
  unlock → session → protection setup on first login. Do not load data before the
  vault is unlocked.
- WebAuthn PRF has uneven support (see the header of `biometria.ts`): the PIN must
  always remain a working way in.
- **allauth:** 401 with `flows` is a state ("not logged in yet", "needs email
  verification", "needs TOTP"), not an error — see `flussoInSospeso()`. Verify
  payloads at `/_allauth/openapi.html` before adding calls.
- Prop names: `key` is reserved in Vue — route params are named `chiave`.
- UI text in Italian, short, no acronyms without explanation (users are capi and
  parents). Use Bootstrap classes and theme variables (`var(--ag-primary)`), no inline
  colours.
- The service worker is in **prompt** mode (`AggiornamentoApp.vue`): never switch to
  auto-update, a capo may be filling a form at camp.

## Tests

`npm test` (Vitest + jsdom + fake-indexeddb). When mocking `fetch`, return a **new**
`Response` for every call (`vi.fn(async () => new Response(...))`) and set
`Content-Type: application/json`: a Response body can be read once, and non-JSON
bodies are kept as text by design. Use `nuovoDatabase()` and `cassaforteSbloccata()`
from `src/__tests__/aiuti.ts` (fresh database, vault with fast PBKDF2) in every test that
touches offline data.

## Dev

`npm run dev` on http://localhost:5173; `/api`, `/_allauth`, `/accounts`, `/admin`,
`/static` are proxied to Django (`QDC_DJANGO_URL`, default `http://localhost:8000`).
Passkeys work on `localhost` only (WebAuthn needs a secure context).

## Not here yet

Capacitor (store app, DEC-105) was removed from the dependencies on purpose (its CLI
pulled vulnerable packages and it is not needed before the PWA is complete).
