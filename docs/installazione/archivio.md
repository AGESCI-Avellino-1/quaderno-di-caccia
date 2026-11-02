# Archivio sul Drive

Due anni dopo l'uscita dal gruppo, il fascicolo di una persona va, come file ZIP, in una
cartella del **Drive condiviso** del gruppo (Google Workspace); solo dopo aver verificato il
caricamento l'app cancella i dati, tenendo nome e anni nel gruppo. Finché il Drive non è
collegato, i capigruppo vedono l'avviso «L'archivio non è ancora configurato» e non si
archivia niente.

Per collegarlo, una volta:

1. In Google Cloud crea un progetto, abilita la **Google Drive API** e crea un **account di
   servizio**; scaricane la chiave JSON. Puoi usare lo stesso progetto della [posta con
   Gmail](posta): l'account di servizio non usa la schermata di consenso.
2. Nel Drive condiviso del gruppo aggiungi l'indirizzo email dell'account di servizio come
   **Gestore contenuti** e crea la cartella per gli archivi; copiane l'id (la parte finale
   dell'indirizzo della cartella).
3. Metti la chiave in `secrets/drive.json`, accanto a `compose.prod.yml` (la cartella
   `secrets/` non va mai nel repository), e in `.env`:

   ```bash
   QDC_DRIVE_CREDENZIALI=/run/qdc-secrets/drive.json
   QDC_DRIVE_CARTELLA=<id della cartella>
   ```

4. Controlla che in `.env` ci sia `QDC_IMPRONTA_CHIAVE`, la chiave che riconosce chi rientra
   dopo l'archiviazione: la genera lo script di configurazione. Se manca (installazioni fatte
   prima che lo script la generasse), creala **una volta**:

   ```bash
   openssl rand -hex 32   # QDC_IMPRONTA_CHIAVE=<il risultato>
   ```

5. Riavvia: `docker compose up -d`. Un capogruppo, nella pagina **Incarichi di gruppo**,
   riquadro **Archivio**, non vede più l'avviso (il riquadro lo vedono solo i capigruppo).
6. Controlla l'impostazione, senza scrivere niente sul Drive:

   ```bash
   docker compose exec web python manage.py controlla_drive
   ```

   Verifica un passo alla volta le voci in `.env`, la chiave dell'account di servizio, che
   Google la accetti, che la cartella esista e sia in un Drive condiviso, e che l'account
   possa scriverci. Si ferma al primo punto segnato `NO` e dice cosa correggere; alla fine
   stampa «Il Drive dell'archivio è pronto.».

:::{danger}
Conserva `QDC_IMPRONTA_CHIAVE` insieme ai backup e **non cambiarla mai**, nemmeno se rigeneri
gli altri segreti o sposti l'app su un altro server: con una chiave diversa chi è stato
archiviato non viene più riconosciuto in automatico quando torna (resta solo il caricamento a
mano dello ZIP).
:::

Il primo caricamento vero sul Drive va provato con un capogruppo, su una persona da
archiviare, controllando che il file arrivi nella cartella.
