# Accesso con Google e Apple

Oltre alla password, al codice via email e alle passkey, le persone possono entrare con un
account Google o Apple che abbia la stessa email del loro account. È facoltativo: se le voci
in `.env` restano vuote, con Google e Apple non si entra e restano gli altri modi.

Negli esempi il dominio dell'installazione è `qdc.esempio.org`: usa il tuo.

## Google

In [Google Cloud Console](https://console.cloud.google.com/), con l'account del gruppo:

1. Crea un progetto (per esempio «Quaderno di Caccia»).
2. Apri **Google Auth Platform** e, se è la prima volta, configura l'app: nome, email di
   assistenza, tipo di utenti **Esterni** ed email di contatto. Poi completa le voci del menu a
   sinistra:

   - **Branding**: scorri la pagina. In **Dominio app** scrivi la home page, il link alle norme
     sulla privacy e quello ai termini di servizio dell'installazione
     (`https://qdc.esempio.org/`, `https://qdc.esempio.org/privacy`,
     `https://qdc.esempio.org/termini`). In **Domini autorizzati** tocca **Aggiungi dominio** e
     scrivi il dominio principale, `esempio.org`, senza `https://` e senza `qdc.`. Tocca **Salva**
     in fondo alla pagina.
   - **Accesso ai dati**: tocca **Aggiungi o rimuovi ambiti**, spunta `.../auth/userinfo.email` e
     `.../auth/userinfo.profile`, tocca **Aggiorna** e poi **Salva** in fondo alla pagina.
   - **Pubblico**: tocca **Pubblica app** e conferma (finché è in prova, entrano solo gli utenti
     di prova che indichi).

3. In **Client** scegli **Crea client**, tipo **Applicazione web**, e in **URI di reindirizzamento
   autorizzati** scrivi:

   ```text
   https://qdc.esempio.org/accounts/google/login/callback/
   ```

4. Copia l'**ID client** e il **client secret** in `.env`:

   ```bash
   QDC_GOOGLE_CLIENT_ID=<ID client>
   QDC_GOOGLE_SECRET=<client secret>
   ```

## Apple

Serve un account dell'[Apple Developer Program](https://developer.apple.com/programs/). In
**Certificates, Identifiers & Profiles**:

1. **Identifiers › App IDs**: crea un App ID (per esempio `org.esempio.qdc`) e abilita
   **Sign in with Apple**.
2. **Identifiers › Services IDs**: crea un Services ID (per esempio `org.esempio.qdc.web`),
   abilita **Sign in with Apple** e, in **Configure**, scegli l'App ID del punto 1 come
   principale, scrivi il dominio `qdc.esempio.org` in **Domains and Subdomains** e in **Return
   URLs**:

   ```text
   https://qdc.esempio.org/accounts/apple/login/callback/
   ```

3. **Keys**: crea una chiave con **Sign in with Apple**, collegata all'App ID del punto 1, e
   scarica il file `.p8` (si può scaricare **una volta sola**: conservalo con i segreti).
   Annota il **Key ID**.
4. Il **Team ID** è in alto a destra nella pagina dell'account sviluppatore.

In `.env`:

```bash
QDC_APPLE_CLIENT_ID=org.esempio.qdc.web   # il Services ID
QDC_APPLE_KEY_ID=<Key ID>
QDC_APPLE_TEAM_ID=<Team ID>
# Il contenuto del file .p8, su una riga, tra virgolette doppie e con \n al posto degli a capo
QDC_APPLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIGT…\n-----END PRIVATE KEY-----"
```

## Attivare

```bash
docker compose up -d
```

Nella pagina di accesso, **Accedi con Google** e **Accedi con Apple** portano alla pagina del
fornitore e poi di nuovo nell'app. Entra chi ha già un account nel Quaderno di Caccia con la
stessa email; chi ha ricevuto un invito può anche creare l'account con **Continua con Google**
o **Continua con Apple**, dalla pagina dell'invito. Senza invito non ci si registra.
