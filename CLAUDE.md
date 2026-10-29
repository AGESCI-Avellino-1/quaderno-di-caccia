# CLAUDE.md — Quaderno di Caccia (QdC)

Design reference for anyone (human or Claude Code) working on this repository. Read it
before changing code; `backend/CLAUDE.md` and `frontend/CLAUDE.md` add the details of
each half.

## What this is

QdC is the app of the AGESCI Avellino 1 scout group (installable by other groups):
registry of members and families, personal file, Progressione Personale (PP), events and
attendance, fees and cash book. Capi use it heavily, also offline; ragazzi and parents
see only their own part.

**The requirements are in [`docs/analisi/analisi-requisiti.md`](docs/analisi/analisi-requisiti.md).**
Every decision has a code `DEC-nn`; code and comments cite them (`# DEC-31`). The
original document, with discussion, is
<https://claude.ai/artifact/Y8hDa3xkQ1cXVSToLTa7H7>.

## Rules that are not negotiable

### No guessing (anti-confabulation)

- **Never invent a requirement.** If the analysis does not cover a case, stop and ask
  the user (Andrea Bruno). Do not create `DEC-nn` codes: only the analysis assigns them.
  When you must proceed on an assumption, write it in the code/PR as
  `[da verificare]` and tell the user.
- **Never guess an API.** Check the installed version before using a library feature:
  `backend/.venv/lib/python3.14/site-packages/<pkg>`, `frontend/node_modules/<pkg>`.
  Versions in use are recent (Django 6.1, allauth 65.20, ninja 1.7, Vue 3.5,
  vue-router 5, Pinia 4, Vite 8, TypeScript 6): patterns from older tutorials are often
  wrong (e.g. Django 6.1 uses `MAILERS`, not `EMAIL_BACKEND`; ninja wants
  `Status(201, …)`, not tuples; allauth headless signup takes `password`, not
  `password1/password2`).
- **allauth endpoints:** with `mise run backend`, the full contract is at
  <http://localhost:8000/_allauth/openapi.html>. Check there before adding a call.
- **Never claim something works without running it.** "Tests pass" means you ran the
  commands in *Quality gate* below and they passed.
- **AGESCI terms** (branche, unità, Co.Ca., CSQ, Pista/Sentiero/Strada…) have precise
  meanings: use the glossary at the end of the analysis, do not paraphrase them.

### Personal data of minors

- **Never commit real data.** No BuonaStrada exports, dumps, screenshots with real
  names. Tests use the synthetic export in `backend/tests/export_sintetico.py`
  (fictional people, fake codici fiscali, group `T9999`). `.gitignore` blocks
  `RicercaSoci*.csv`, `*.sql*`, `*.sqlite3`, `backups/`.
- **Never log personal data** (names, CF, health data, contacts) at INFO or above.
- **Who sees what is decided only in `backend/apps/permessi/policy.py`** (DEC-09…DEC-20,
  DEC-39, DEC-40). Every endpoint asks the policy; the frontend only hides menu items,
  it never protects data. A new kind of data = a new policy function + tests in
  `tests/test_policy.py` and `tests/test_api.py` covering capo, capogruppo, CSQ,
  ragazzo, genitore and an unrelated person (`estraneo`).
- **Everything kept on a device is encrypted** (DEC-97, see "Protezione sul telefono"
  below). Offline data goes only through `leggiConCache`/`salvaInCache` and `scrivi`/
  `accoda`, never directly into IndexedDB or `localStorage`.
- **Health data** lives only in `apps/sanitaria`. It is not registered in the Django
  admin (the admin would bypass the access log, and the technical administrator must not
  see it, DEC-12). Every read, offline download and change goes through
  `apps.permessi.models.registra_accessi` (DEC-101). Offline, capi get only medicines,
  allergies and intolerances, not the whole medical form (DEC-55, DEC-95).

### Language

- Code, comments, docstrings, commit messages: **English**.
- Domain identifiers stay **Italian** and match the analysis: `Persona`, `Unita`,
  `Appartenenza`, `Incarico`, `squadriglia`, `anno_associativo`, `puo_importare`…
  Do not translate them.
- Everything the user reads (UI, API error messages, emails): **Italian**, plain words,
  no unexplained acronyms (the users are capi and parents, not developers).
- **Codes from the analysis** (`DEC-31`, and the question codes such as `V-02`, `N-19`,
  `O-05`, `R-08`, `PP-D`) go only in comments and docstrings. Never in anything a user
  can see or receive: UI, API messages, emails, labels, choices, command output, test
  names. `scripts/controlla-codici.py` (run by `mise run lint` and CI) enforces it.
- Conversation with the maintainer (explanations, questions, summaries): **Italian**.
  Only code and comments are in English.

## Architecture in one page

```
frontend/  Vue 3 PWA (TypeScript, Vite, Pinia, Dexie)  ──┐ same origin:
backend/   Django 6.1 + django-ninja API + allauth      ──┤ session cookie + CSRF,
           PostgreSQL 18                                   │ no CORS, no tokens
deploy/, compose.*.yml, scripts/   Docker, reverse proxy  ─┘
```

- **One origin.** In dev Vite proxies the Django paths; in production nginx (the `app`
  container) does. The list of Django paths exists in two places that must stay equal:
  `DJANGO_PATHS` in `frontend/vite.config.ts` and the `location ~ ^/(…)/` regex in
  `frontend/docker/qdc-locations.conf`.
- **Authentication:** django-allauth *headless* (`/_allauth/browser/v1/…`): email +
  password, login by emailed code, passkeys, Google, Apple (DEC-21, DEC-22). Sign-up is
  possible only through an invitation (`apps/accounts/adapters.py`). Session 30 days
  (DEC-23). django-axes limits login attempts.
- **API:** `/api/v1/` (django-ninja, `backend/config/api.py`). OpenAPI docs at
  `/api/v1/docs` in dev.
- **BuonaStrada is the source of truth for the registry** (DEC-02, DEC-27…DEC-35).
  Import = preview first, then apply. Corrections made in the app are never silently
  overwritten (DEC-31): the import reports a *differenza* instead.
- **Offline writes** (DEC-94…DEC-96) go through the outbox in `frontend/src/offline/`:
  stored in IndexedDB, replayed in order with an `Idempotency-Key` header; the server
  (`apps/core/idempotenza.py`) answers a replay from storage instead of executing it
  twice. Attendance and cash movements must be *append-only records* (no conflicts);
  for texts the last write wins.
- **Associative year** 1 Oct – 30 Sep, labelled by its end year (2025/26 = `2026`, as
  BuonaStrada does); ages computed at 30 April (DEC-37): `apps/core/anno.py`.
- **Audit:** django-auditlog records changes to every domain model; register new models
  in the app's `apps.py`. Reads of sensitive data are logged separately
  (`AccessoDatoSensibile`, DEC-101): health data and exceptions to single-sex patrols;
  extend it to every new sensitive category (notes reserved to the Co.Ca., DEC-43).

### Protezione sul telefono (DEC-97)

| Piece | Where |
| --- | --- |
| AES-GCM 256 data key; JSON payloads encrypted with the record key as authenticated data | `frontend/src/sicurezza/cripto.ts` |
| Key wrapped by the PIN (PBKDF2-SHA256, 600,000 iterations, ≥ 6 digits) and optionally by a passkey PRF secret (fingerprint/face, works offline) | `cassaforte.ts`, `biometria.ts` |
| States `da_configurare` / `solo_online` / `bloccata` / `sbloccata`; key only in memory | `cassaforte.ts` |
| 5 wrong PINs → everything wiped; lock after 5 minutes of inactivity | `cassaforte.ts`, `composables/useBloccoAutomatico.ts` |
| Device registered on the server, its id in the server-side session | `backend/apps/dispositivi` |
| Revocation by the owner or a capogruppo (DEC-23): the session is deleted; at start-up the app asks `/dispositivi/{id}/stato` (no login needed) and wipes itself | `dispositivi/api.py`, `sicurezza/dispositivo.ts` |
| Offline window: every answer carries `X-QdC-Offline-Fino-Al` (last contact + `QDC_OFFLINE_GIORNI`, default 14); past it the data is wiped at start-up | `dispositivi/middleware.py`, `sicurezza/collegamenti.ts` |
| Another account logging in on the same device wipes the previous one's data | `stores/sessione.ts` |

**Threat model, stated honestly:** this protects against a lost, stolen or borrowed
phone and against anyone opening the app or its storage without the PIN. A 6-digit PIN
does **not** resist an offline brute force on a dump of the browser storage taken from
an unlocked or rooted phone (minutes on a GPU): there the defences are the phone's own
lock, remote revocation and the offline window. Do not weaken any of the three, and do
not lower the PBKDF2 iterations (tests pass a lower value explicitly).

Data in the queue's `descrizione` field and in cache keys is stored in clear: never put
names or health data there.

### BuonaStrada "Ricerca Soci" CSV traps (DEC-29)

First line `sep=,`; UTF-8 BOM; values wrapped as `="…"`; dates `dd/mm/yyyy` unwrapped;
every row has one trailing comma more than the header (82 fields vs 81); the guardian
column `RESP.GENITORIALE DATI` is free text parsed by regex; surname/name of parents
are split using the codice fiscale. All handled in
`backend/apps/importazione/buonastrada.py`, with a test for each trap. If a new export
breaks the parser, add the case to `tests/export_sintetico.py` first.

### Theme

Colours come from **django-agesci-campania-theme 3.0.0a2**
(<https://github.com/AGESCI-Campania/django-agesci-campania-theme>), the line built on
**Bootstrap 6** (`bootstrap@6.0.0-alpha.1`, pinned): the maintainer chose the alpha on
purpose, to avoid a second migration later. `frontend/src/theme/_palette.scss` and
`_branche.scss` are copied **byte for byte** (excluded from Prettier). To update: copy
the two files from the new release, never edit them here. The branch colour is chosen
with `<html data-branca="lc|eg|rs|capi|generico">` (DEC-72); components use
`var(--ag-primary)` and friends, never hard-coded colours.

Bootstrap 6 is **not** Bootstrap 5: before writing markup read the theme's AI rules
(<https://django-agesci-campania-theme.readthedocs.io/it/latest/llms-full.txt>) and
check a class exists in `frontend/node_modules/bootstrap/dist/css/bootstrap.css`. In
short: colours via `theme-*` (`btn btn-solid theme-primary`, `btn-outline`,
`alert theme-danger`, `badge theme-success`); text `fg-*` (`fg-2` for secondary text);
responsive prefixes `md:col-6`; spacing scale 1, 3, 5, 7, 12 (= v5 1–5); `<select
class="form-control">`; checkboxes/switches are `input.check` / `input.switch` inside
`.form-field`; `.alert` is a flex box, so wrap mixed content in one `<div>`; the theme is
light only (`data-bs-theme="light"`). Minimum browsers: Chrome/Edge 130, Firefox 132,
Safari 18. Font: Titillium Web, bundled
(SIL OFL, `frontend/src/assets/fonts/OFL.txt`) so it works offline.

## Working on it

```bash
mise install && mise run setup   # tools, deps, dev database, migrations
mise run backend                 # Django  http://localhost:8000
mise run frontend                # PWA     http://localhost:5173  (use this one)
```

Dev emails (codes, invitations) are printed in the Django console.

Other `mise` tasks: `mise run dev` (database + backend + frontend together), `mise run
db` / `db:stop` (PostgreSQL via `$COMPOSE`), `mise run format` (autofix ruff/black/
prettier), `mise run importa -- file.csv [--applica]` (BuonaStrada import, preview by
default).

Single tests:

```bash
cd backend  && uv run pytest tests/test_policy.py::test_name   # or -k "expr"
cd frontend && npx vitest run src/path/file.test.ts            # npm run test:watch for watch mode
```

### Quality gate (run before every commit; CI runs the same)

```bash
mise run lint     # ruff, black, eslint, prettier, vue-tsc
mise run test     # pytest + vitest
cd backend && uv run python manage.py makemigrations --check --dry-run
cd frontend && npm run build
```

Backend tests use in-memory SQLite locally and PostgreSQL in CI; set
`DATABASE_URL=postgres://qdc:qdc@localhost:5432/qdc` to run them on the dev database.

### Adding a feature (checklist)

1. Find the `DEC-nn` it implements; if none, ask.
2. Model in the right app (`backend/CLAUDE.md`), registered with auditlog, migration.
3. Permission in `policy.py` + tests for every role.
4. Endpoint in the app's `api.py`, typed schemas, Italian error messages.
5. Types and client in `frontend/src/api/qdc.ts`; reads through `leggiConCache`
   if needed offline, writes through `accoda` if they must work offline.
6. View + route; tests; quality gate.

## Roadmap (phases from the analysis)

| Phase | Content | Status |
| --- | --- | --- |
| 1. Fondamenta | accounts, roles, units, BuonaStrada import, parents and families; anticipated: device protection (DEC-97) and health essentials (DEC-55) | **in progress** — done: models, policy, import (CLI + API + UI), invitations (API + email + `crea_invito` + panel on the person page), login (password, code, passkey, Google/Apple), PWA with encrypted offline data, PIN/biometrics, device revocation and expiry, medicines/allergies/intolerances with offline "Al campo" view, access log for health data, units/staff/roles/squadriglie and their members (API + UI). corrections to BuonaStrada data forwarded by the capigruppo (DEC-31). Missing: adult-consent alerts at 18 (DEC-26), GDPR rights (DEC-102), patrol contacts (DEC-13), non-medical dietary needs (DEC-49) |
| 2. Quote e cassa | fee types, sibling discount, agevolazioni, payments, receipts, cash book on Modello D | catalog ready in `backend/data/cataloghi/modello_d_2024_2025.json` |
| 3. Eventi e presenze | 4-level events, recurring meetings, offline attendance, iCal feed | — |
| 4. Progressione Personale | E/G first (pilot, imprese), then R/S and L/C | catalogs of specialità/brevetti ready in `backend/data/cataloghi/` |
| 5. Fascicolo completo | full medical form with print and signatures (extends `apps/sanitaria`), notes with visibility, archiving | — |
| 6. Dopo | notice board, bank statement matching, Carta di clan text | — |

Deferred: store app with Capacitor (DEC-105) comes last, after phase 6; the PWA has
priority and must stay the reference client;
check Apple guideline 4.2 with a prototype before investing (see "Punti ancora da
verificare" in the analysis).

## Open points to confirm with the maintainer

- "Staff dell'unità" (DEC-09) is an `Incarico` with role `STAFF`, not an `Appartenenza`:
  capi belong to the Co.Ca. from the import, and a second CAPO membership would look to
  the import like a change of unit. `policy.e_staff` counts the capo unità too.
- Who appoints CSQ/VCSQ (the reparto staff), group roles (capigruppo in office; the
  technical administrator only when there is none) and unit treasurers (capo unità and
  capigruppo) was decided with the maintainer on 2026-10-28 and is not yet in the
  analysis: see `TODO.md`, `policy.puo_nominare`.
- Squadriglie (maintainer, 2026-10-28): composed by the reparto staff and the
  capigruppo; one patrol at a time; CSQ/VCSQ are members and close their role before
  moving; single-sex, with exceptions (`DerogaSquadriglia`) decided by the Co.Ca.,
  recorded by a capogruppo, visible to capi only, valid while the person stays in the
  reparto; leaving the reparto ends patrol, CSQ role and exceptions
  (`organizzazione/servizi.esci_dal_reparto`, called by the import). Created and
  closed by the same people (`policy.puo_gestire_squadriglie`).
- Health data is written by the staff of the person's unit and by the capigruppo for
  every unit (`policy.puo_modificare_sanitarie`, confirmed 2026-10-28).
- django-auditlog's `LogEntry` is in the Django admin and stores changed values, health
  data included. Accepted by the maintainer (2026-10-28): the technical administrator is
  always a capo or has a delegation from the capigruppo for the data. Health data still
  stays out of the admin itself; `DerogaSquadriglia.motivazione` stays out of the audit
  log.
- Corrections (DEC-31, maintainer 2026-10-29): who corrects which field is
  `policy.campi_correggibili`; sex and place of birth count as identity (capigruppo
  only) because the codice fiscale derives from them `[da verificare]`. The daily
  summary to the capigruppo is `manage.py segnala_correzioni`, run by the host's cron.
- Every account has its own email: a child is not invited with a parent's address
  (maintainer, 2026-10-28, refines DEC-25; `accounts/api.crea_invito`).
- After 18 (DEC-26, maintainer 2026-10-29): until the R/S decides, parents keep seeing
  what they saw (`puo_vedere_dati_sensibili`) but no longer write it; the R/S and the
  parents get an alert. Not built yet.
- Decided on 2026-10-29, not built yet (details in `TODO.md`): patrol contacts (DEC-13:
  every member sees the others' phone, the CSQ also the parents'; VCSQ like a member;
  hideable by the parent); accounts from 14 by invitation without parental approval
  (DEC-24, as built); non-medical dietary needs in the personal file, treated like
  health data (DEC-49); capi training entered by hand (DEC-47); the
  capigruppo delegation covers the app (DEC-98, DEC-102).
- Device revocation and idempotency work with the browser session only; the store app
  (X-Session-Token, DEC-105) will need the same checks.
