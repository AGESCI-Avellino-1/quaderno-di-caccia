# backend/CLAUDE.md

Django 6.1 · Python 3.14 · uv · django-ninja · django-allauth (headless) · PostgreSQL.
Read the root `CLAUDE.md` first.

## Layout

| Path | What |
| --- | --- |
| `config/settings/{base,dev,test,prod}.py` | Split settings; secrets only from env (`.env` at repo root) |
| `config/api.py` | NinjaAPI: mounts each app's `router` under `/api/v1/` |
| `apps/core` | `anno.py` (associative year, ages, DEC-37), `date_parziali.py` (partial dates, DEC-70), `ModelloTracciato`, `FonteDato`, idempotency middleware (DEC-96) |
| `apps/accounts` | `User` (email login, `amministratore_tecnico`), `Invito` (DEC-21, DEC-24), allauth adapters, `/io`, `/inviti`, `crea_invito` command |
| `apps/organizzazione` | `Gruppo`, `Unita`, `Squadriglia`, `Incarico` (roles with diarchy, DEC-18; `STAFF` = the capi serving a unit, no holder limit; `clean()` checks who may hold each role); API for units, patrols, roles, `/capi` |
| `apps/anagrafica` | `Persona` (one identity for life, DEC-57), `RelazioneTutela`, `Appartenenza`, `AppartenenzaSquadriglia`, `CorrezioneAnagrafica` (DEC-31: open = IN_ATTESA/INOLTRATA; `servizi.correggi_campo`, `scarta_correzione`), `fratelli()` (DEC-33) |
| `apps/importazione` | BuonaStrada parser (`buonastrada.py`, pure, no DB), import service (`servizi.py`: `anteprima`/`applica`), `importa_buonastrada` command |
| `apps/permessi/policy.py` | **The only place that decides visibility and actions** |
| `apps/permessi/models.py` | `AccessoDatoSensibile` + `registra_accessi()`: log of reads/downloads/changes of sensitive data (DEC-101) |
| `apps/dispositivi` | `Dispositivo`, revocation, middleware that logs out revoked devices and sends `X-QdC-Offline-Fino-Al` (DEC-23, DEC-97) |
| `apps/iscrizioni` | Joining from the app: `CodiceIscrizione` (unit/personal, QR via segno), `RichiestaIscrizione` (waiting → approved with provisional codice socio → completed / suspended / rejected), `ModuloVuoto`, `AllegatoIscrizione` (scans: API only, never the admin) |
| `apps/quote` | Fees (phase 2): `TipoQuota` (set by the group, who owes it, monthly = one fee per month), `Quota` (amount and family discount copied at issue), `Agevolazione` (Co.Ca. only, the family sees the amount), `LegameConiugale`, `Pagamento` + `RipartizionePagamento` (one payment over fees of one family, deposits allowed; receipt numbered per year, PDF by reportlab, never stored; cancelled, never edited). `servizi.famiglia` = guardianship and spouse links |
| `apps/cassa` | Cash book (phase 2): `Cassa` (one bank account, cash per unit), `Movimento` (never edited: `servizi.storna`; `effetto` = signed change on the box; Modello D category copied; receipt photo as base64 in the JSON so it can wait in the offline queue), `VerificaCassa` (difference → adjustment), `SpesaAnticipata` (refund → outflow). Fee payments enter by themselves (`servizi.registra_pagamento`). `catalogo.py` reads `data/cataloghi/modello_d_*.json` |
| `apps/diritti` | Requests from data subjects (DEC-102): register, `/persone/{id}/fascicolo` (full export), erasure/anonymisation (`servizi.cancella`). Capigruppo only |
| `apps/sanitaria` | Medicines, allergies, intolerances (DEC-48 core, DEC-55), non-medical dietary needs (DEC-49, same rules and log); `/persone/{id}/sanitarie`, `/campo/{unita}` for the offline download. **Not in the admin** |
| `data/cataloghi/` | Modello D, specialità, brevetti as JSON (not loaded into the DB yet; see its README) |
| `tests/` | pytest; `conftest.py` fixtures, `export_sintetico.py` fake BuonaStrada export |

## Conventions

- Domain models inherit `ModelloTracciato` (timestamps) and are registered with
  auditlog in their app's `apps.py` (exclude secrets: tokens, passwords).
- Data with an origin carries `fonte = FonteDato.BUONASTRADA | APP | RICOSTRUITO`.
- Periods use `data_inizio` inclusive and `data_fine` **exclusive** (`None` = open);
  querysets expose `.attive()` / `.attivi(al_giorno)`.
- Validation lives in `Model.clean()`; endpoints call `full_clean()` and turn
  `ValidationError` into `HttpError(400, …)` — never let it become a 500.
- Endpoints: typed `Schema` in/out; `Status(201, {...})` for creations; Italian
  `HttpError` messages; 404 (not 403) when the user may not even know the object exists.
- `request.auth` is the user (ninja `django_auth` / allauth `x_session_token_auth`).
- FKs to the user that are filled in by code get `blank=True` (otherwise `full_clean`
  fails).
- Keep `buonastrada.py` free of Django imports: it is tested on raw bytes.

## Settings notes

- Email: Django 6.1 `MAILERS` dict (dev: console; test: locmem; prod: SMTP from env).
  `EMAIL_BACKEND` is deprecated — do not reintroduce it.
- `dev.py` serves the allauth OpenAPI spec (needs the `headless-spec` extra, already in
  `pyproject.toml`) and allows WebAuthn on http://localhost.
- `prod.py` expects `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`,
  `DJANGO_CSRF_TRUSTED_ORIGINS`; `QDC_PROXY_COUNT` must equal the number of proxies in
  front of gunicorn (written by `scripts/configure-prod.sh`), or django-axes locks the
  wrong IP. `check --deploy --fail-level WARNING` must stay clean (CI enforces it).

## Tests

- `uv run pytest` (SQLite in memory); CI runs on PostgreSQL 18 via `DATABASE_URL`.
- Ages are relative: build birthdates with `nato_anni_fa(n)`; never hard-code a year
  (tests broke once when a "13-year-old" turned 14).
- `crea_persona(nome, cognome, login="x@…")` creates a Persona with a user; the
  parameter is `login`, not `email` (Persona has its own `email` field).
- Role fixtures: `capo` (also capo unità of `reparto`), `capogruppo`, `ragazza` (12, in
  squadriglia), `csq` (15), `genitore` (of `ragazza`), `estraneo`.
- Real exports may be used **locally** to check the parser (scratch DB outside the
  repo), never committed, never copied into tests.

- Sensitive endpoints call `registra_accessi(request, persone, categoria, azione)`;
  bulk offline downloads require `request.dispositivo` (a registered, revocable device).
- `request.dispositivo` is set by `DispositivoMiddleware` when the session is bound to a
  device; the middleware order in `base.py` matters (after auth, before idempotency).

## Common commands

```bash
uv run python manage.py importa_buonastrada RicercaSoci.csv            # preview
uv run python manage.py importa_buonastrada RicercaSoci.csv --applica  # write
uv run python manage.py crea_invito <codice_socio> <email> --capogruppo  # first start
uv run python manage.py segnala_correzioni   # daily email to the capigruppo (cron), DEC-31
uv run python manage.py avvisa_maggiore_eta  # daily alerts for members turning 18 (cron), DEC-26
uv run python manage.py promemoria_iscrizioni  # daily: new requests, reminders, suspension (cron)
uv run python manage.py emetti_quote  # daily: issue the fees whose period has started (cron)
uv run python manage.py createsuperuser   # technical admin (DEC-12): sees no educational data
```
