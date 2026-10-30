# backend/CLAUDE.md

Django 6.1 · Python 3.14 · uv · django-ninja · django-allauth (headless) · PostgreSQL.
Read the root `CLAUDE.md` first.

## Layout

| Path | What |
| --- | --- |
| `config/settings/{base,dev,test,prod}.py` | Split settings; secrets only from env (`.env` at repo root) |
| `config/api.py` | NinjaAPI: mounts each app's `router` under `/api/v1/` |
| `apps/core` | `anno.py` (associative year, ages, DEC-37), `date_parziali.py` (partial dates, DEC-70), `stampa.py` (the group's letterhead on every PDF, DEC-192), `ModelloTracciato`, `FonteDato`, idempotency middleware (DEC-96) |
| `apps/accounts` | `User` (email login, `amministratore_tecnico`), the Django admin site and permissions for the technical administrators (`amministrazione.py`, DEC-166), `Invito` (DEC-21, DEC-24), allauth adapters, `/io`, `/inviti`, `crea_invito` command |
| `apps/organizzazione` | `Gruppo`, `Unita`, `Squadriglia`, `Incarico` (roles with diarchy, DEC-18; `STAFF` = the capi serving a unit, no holder limit; `A_DISPOSIZIONE` = a capo serving in no unit, excludes unit service; `AMMINISTRATORE` = technical administrator appointed by the capigruppo; service roles and additional roles add up; `clean()` checks who may hold each role); API for units, patrols, roles, `/capi` |
| `apps/anagrafica` | `Persona` (one identity for life, DEC-57), `RelazioneTutela`, `Appartenenza`, `AppartenenzaSquadriglia`, `CorrezioneAnagrafica` (DEC-31: open = IN_ATTESA/INOLTRATA; `servizi.correggi_campo`, `scarta_correzione`), `fratelli()` (DEC-33) |
| `apps/importazione` | BuonaStrada parser (`buonastrada.py`, pure, no DB), import service (`servizi.py`: `anteprima`/`applica`), `importa_buonastrada` command |
| `apps/permessi/policy.py` | **The only place that decides visibility and actions** |
| `apps/permessi/models.py` | `AccessoDatoSensibile` + `registra_accessi()`: log of reads/downloads/changes of sensitive data (DEC-101) |
| `apps/dispositivi` | `Dispositivo`, revocation, middleware that logs out revoked devices and sends `X-QdC-Offline-Fino-Al` (DEC-23, DEC-97) |
| `apps/iscrizioni` | Joining from the app: `CodiceIscrizione` (unit/personal, QR via segno), `RichiestaIscrizione` (waiting → approved with provisional codice socio → completed / suspended / rejected), `ModuloVuoto`, `AllegatoIscrizione` (scans: API only, never the admin) |
| `apps/quote` | Fees (phase 2): `TipoQuota` (set by the group, who owes it, monthly = one fee per month; `EVENTO` = an event's fee in instalments `rate`, issued to its participants by `servizi.emetti_evento`, kept in step by `allinea_quote_evento`), `Quota` (amount and family discount copied at issue), `Agevolazione` (Co.Ca. only, the family sees the amount), `LegameConiugale`, `Pagamento` + `RipartizionePagamento` (one payment over fees of one family, deposits allowed; receipt numbered per year, PDF by reportlab, never stored; cancelled, never edited). `servizi.famiglia` = guardianship and spouse links |
| `apps/cassa` | Cash book (phase 2): `Cassa` (one bank account, cash per unit), `Movimento` (never edited: `servizi.storna`; `effetto` = signed change on the box; Modello D category copied; receipt photo as base64 in the JSON so it can wait in the offline queue), `VerificaCassa` (difference → adjustment), `SpesaAnticipata` (refund → outflow). Fee payments enter by themselves (`servizi.registra_pagamento`). `catalogo.py` reads `data/cataloghi/modello_d_*.json` |
| `apps/eventi` | Events (phase 3): `Evento` (level group/branch/unit/patrol, `cerchia` for the reparto councils, `note_genitori` of a patrol's mission), `RiunioneRicorrente` (one event per date), `Partecipazione` (invited / not taking part / not invited with a reason), `Presenza` (one per member and event, last mark wins, offline), `PresenzeAnnue` (after two years), `DelegaSquadriglia`, `MembroAltaSquadriglia`, `CalendarioPersonale` (secret token, public `/calendario/{token}.ics`, `calendario.py` writes RFC 5545 by hand), `avvisi.py` (emails, one message per address). Budget and accounts of an event: `servizi.budget` (DEC-91, staff contribution apart), `servizi.rendiconto` (movements with `Movimento.evento`; an event's fee payments are linked by `cassa.servizi.registra_pagamento`). Optional emails ask `anagrafica.preferenze.accetta(persona, categoria)` and end with `nota_a_piede()`; a new optional kind = a new field on `PreferenzeEmail`. `servizi.previsti` = who is invited by default |
| `apps/buonacaccia` | Events on BuonaCaccia (DEC-158…DEC-164): `EventoBuonaCaccia` (1:1 with an `Evento` of level `ESTERNO`: capi training and type of camp, the event form), `ModelloScheda` + `VersioneScheda` (questions as JSON with stable ids; a change = a new version), `IscrizioneBuonaCaccia` (a minor's registration: deadlines, management link, release form files and ticks, answers, photo, presentation, fee), `QuotaFormazione` (fee a capo paid). `avvisi.py` (emails to family and staff, reminders), files API only |
| `apps/impersonazione` | Using the app as another user: `Impersonazione` (who, as whom, why, until when), `ImpersonazioneMiddleware` (swaps `request.user`, sets `request.impersonatore`, blocks the account and personal choices: `BLOCCATE`). Must stay after auditlog's and the device middleware |
| `apps/progressione` | Progressione Personale (DEC-56…DEC-74, DEC-171…DEC-190; spec in `docs/analisi/specifica-pp.md`), E/G first: `PeriodoBranca` (one open per person, separate from memberships), `Tappa` (phase period; `completata_il` = recognised in the Consiglio della Legge, `data_fine` = next one started; `collocamento` for late entrants), `Promessa`, `ConsegnaDistintivo`, `Obiettivo` (meta E/G or obiettivo R/S, "mete" in the API; `riservata`: not for the CSQ) and `Impegno` (six states, `Revisione` keeps old wordings), dates with precision (DEC-70). `PercorsoCompetenza` (specialità, brevetto or specialità di squadriglia: one holder, a person's period or a patrol; catalog code, name and version kept; `collegati`), catalogs read from `data/cataloghi/` by `catalogo.py` (`ritirata` items only in history), `Impresa` and `PostoAzione`, `Passaggio` + `PassaggioPersona` (prepared, executed atomically: periods close and open with the Scoperta, unit assigned in the app, DEC-174…DEC-177; `chiusure` records what it closed so `annulla_esecuzione` / `correggi_data` undo exactly that, DEC-178). R/S (DEC-67, DEC-179…DEC-181): `FirmaCarta` opens the passi di competenza (`firma_carta`), `avvia_responsabilita`, `PuntoStrada` (repeatable; `riservato` only for the R/S and the capi, `policy.vede_riservato_punto_strada`, kept out of auditlog), `Conclusione` (closes the period only, never automatic). L/C (DEC-66, DEC-182…DEC-185): `Stagione` (planned, launched, closed, cancelled; closing conquers nothing, `da_rileggere`), prede/voli are `Impegno` with `stagione`, a momento is recognised only after a conquest unless `storico` (`riconosci_tappa`), badge after recognition, `SPECIALITA_LC` from `specialita_lc.json`, names giungla/bosco from `api.ambiente`; `RuoloIncarico.CONSIGLIO_ANZIANI` (a unit role held by a child, closed by `esci_dal_reparto`); Piccole Orme are a flag on `EventoBuonaCaccia` with warnings (`buonacaccia.servizi.avvisi_piccole_orme`). Imprese (DEC-187): `Impresa.consiglio`, `policy.puo_creare_impresa` / `puo_modificare_impresa` / `puo_gestire_posti` / `imprese_visibili` / `reparto_imprese` (CSQ for their patrol, Consiglio d'impresa until `finita`). `PuntoStrada.voce` written only by the R/S (DEC-188); a new R/S period after an interruption, never after a Partenza (DEC-189). Commands in `servizi.py`: a step already applied returns as done (offline replays, DEC-96); never an automatic advancement (DEC-71) |
| `apps/diritti` | Requests from data subjects (DEC-102): register, `/persone/{id}/fascicolo` (full export), erasure/anonymisation (`servizi.cancella`); the Progressione Personale is in both (`_progressione`, `_cancella_progressione`: private mete included, patrol specialità and imprese stay with the patrol). Capigruppo only |
| `apps/sanitaria` | The medical form: medicines, allergies, intolerances (DEC-48 core, DEC-55, the only part offline), non-medical dietary needs (DEC-49, same rules and log), the rest of the AGESCI form and the optional fields (fields set to `None` in a PUT stay unchanged, for older queued requests), paper dates (`/sanitarie/carta`, staff and capigruppo, `da_rifirmare` from `dati_modificati_il`), `ReperibilitaEvento` (DEC-53), the AGESCI form printed by `stampa.py` (reportlab, never stored; prints logged as `Azione.STAMPA`), one PDF per event (`/eventi/{id}/schede-sanitarie.pdf`, `policy.puo_stampare_schede_evento`). `/campo/{unita}` for the offline download. **Not in the admin** |
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
uv run python manage.py riassumi_presenze  # daily: attendance older than two years becomes yearly totals (cron)
uv run python manage.py promemoria_quote  # daily: reminders of unpaid fees due within a week (cron)
uv run python manage.py promemoria_buonacaccia  # daily: BuonaCaccia deadlines to staff and families (cron)
uv run python manage.py createsuperuser   # technical admin (DEC-12): sees no educational data
```
