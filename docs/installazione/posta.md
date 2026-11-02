# La posta

L'app manda email per i codici di accesso, gli inviti, le ricevute e gli avvisi. Da dove
partono lo sceglie l'**amministratore tecnico** nell'app, in **Impostazioni › Server di
posta**, e lo prova con **Manda un'email di prova a me**. Password, segreti e token si
salvano cifrati con la chiave `QDC_CHIAVE_SEGRETI` di `.env`, che lo script di
configurazione genera da solo: conservala con i backup (se cambia, vanno inseriti di nuovo).

Finché nell'app non imposti niente, valgono le voci `DJANGO_EMAIL_*` di `.env` (vedi
[Installazione](installazione)).

Le strade possibili:

| Strada | Per chi | Serve |
| --- | --- | --- |
| [Gmail con accesso Google](#gmail-con-accesso-google) | Google Workspace e indirizzi @gmail.com | un client OAuth in Google Cloud; nessuna password |
| [Relay SMTP di Google](#relay-smtp-di-google) | Google Workspace | l'amministratore del Workspace e un IP pubblico fisso del server; nessuna password |
| SMTP con password per le app | Google Workspace e @gmail.com | la verifica in due passaggi sull'account; nel Workspace, password per le app permesse |
| SMTP di un altro fornitore | chiunque | i dati SMTP del fornitore |
| SMTP di Microsoft 365 | caselle Microsoft 365 | che il tenant accetti ancora utente e password per l'SMTP |

Negli esempi il dominio dell'installazione è `qdc.esempio.org` e quello della posta
`esempio.org`: usa i tuoi.

:::{note}
**Microsoft 365.** Microsoft sta togliendo l'invio SMTP con utente e password: nei tenant
esistenti è previsto spento di base da fine 2026 (l'amministratore del tenant può
riattivarlo), con una data definitiva annunciata per il 2027. La posta istituzionale AGESCI
è nel tenant nazionale: chiedi a chi lo amministra. L'invio con OAuth per Microsoft 365 non
c'è ancora.
:::

## Gmail con accesso Google

L'amministratore tecnico accede **una volta** con l'account Google da cui partono le email;
l'app chiede solo il permesso di **inviare** (non legge la posta) e conserva un token che si
rinnova da solo. Funziona con le caselle di un Google Workspace (anche for Nonprofits) e con
gli indirizzi @gmail.com.

### 1. Il client OAuth in Google Cloud

In [Google Cloud Console](https://console.cloud.google.com/), con l'account del gruppo:

1. Crea un progetto, per esempio «QdC posta». Usa un progetto **a parte** da quello per
   l'[accesso con Google](google-apple): il permesso di inviare email cambia le regole della
   schermata di consenso di tutto il progetto. Va bene invece il progetto dell'[archivio sul
   Drive](archivio): il suo account di servizio non usa la schermata di consenso.
2. In **API e servizi › Libreria** cerca **Gmail API** e tocca **Abilita**.
3. Configura la schermata di consenso (**Google Auth Platform**, o **API e servizi ›
   Schermata consenso OAuth**): nome dell'app, email di assistenza e contatto dello
   sviluppatore. Come **pubblico** (tipo di utenti):
   - **Interno**, se la casella da cui mandi è del Workspace del gruppo: l'app la usano solo
     gli account del Workspace e Google non chiede verifiche. È la scelta consigliata.
   - **Esterno**, se la casella è un indirizzo @gmail.com. Poi **pubblica** l'app («In
     produzione»): finché resta «In test» il collegamento scade dopo 7 giorni. Senza la
     verifica di Google, all'accesso compare l'avviso «Google non ha verificato questa app»:
     va bene, perché accede solo l'amministratore tecnico; tocca **Avanzate** e prosegui.
4. Negli **ambiti** (accesso ai dati) aggiungi `openid`, `.../auth/userinfo.email` e
   `https://www.googleapis.com/auth/gmail.send` (Gmail: «invia email per tuo conto»).
5. In **Client** (o **API e servizi › Credenziali › Crea credenziali › ID client OAuth**)
   crea un client di tipo **Applicazione web** e in **URI di reindirizzamento autorizzati**
   scrivi l'indirizzo che l'app mostra nelle Impostazioni:

   ```text
   https://qdc.esempio.org/api/v1/impostazioni/gmail/ritorno
   ```

6. Copia l'**ID client** e il **client secret**.

### 2. Il collegamento nell'app

1. In **Impostazioni › Server di posta** scegli **Gmail con accesso Google**, incolla ID e
   segreto e tocca **Salva**.
2. Tocca **Collega Gmail**: si apre Google. Entra con l'account da cui partono le email e
   consenti l'invio. Torni nelle Impostazioni con «Collegato a …».
3. Tocca **Manda un'email di prova a me**.

Il **mittente** è l'indirizzo collegato, con il nome di `DJANGO_DEFAULT_FROM_EMAIL`; se ne
scrivi un altro, deve essere un alias che quell'account può usare («Invia messaggio come»
nelle impostazioni di Gmail), altrimenti Gmail lo sostituisce.

Per togliere il collegamento tocca **Scollega**; si può anche revocare dall'account Google
(**Sicurezza › Le tue connessioni a app e servizi di terze parti**). Se Google smette di
accettarlo (revocato, password dell'account cambiata, app rimasta «In test»), l'email di
prova lo dice: collega di nuovo.

## Relay SMTP di Google

Con un Google Workspace il server può mandare attraverso Google **senza utente né
password**: Google accetta le email che arrivano dall'indirizzo IP del server e hanno come
mittente un indirizzo del tuo dominio. Serve un **IP pubblico fisso**: se il server cambia
indirizzo, scegli un'altra strada.

1. Trova l'IP pubblico del server:

   ```bash
   curl -4 https://ifconfig.me   # e, se il server ha IPv6: curl -6 https://ifconfig.me
   ```

2. Nella [console di amministrazione Google](https://admin.google.com/), con un account di
   amministratore (con il privilegio sulle impostazioni di Gmail), apri **App › Google
   Workspace › Gmail › Routing** e, in **Servizio di inoltro SMTP**, tocca **Configura**:
   - una descrizione, per esempio «Quaderno di Caccia»;
   - **Mittenti consentiti**: **Solo indirizzi nei miei domini**;
   - **Autenticazione**: spunta **Accetta email solo dagli indirizzi IP specificati** e
     aggiungi l'IP del server (IPv4 e, se c'è, IPv6). Se spunti anche **Richiedi
     l'autenticazione SMTP**, servono utente e password per le app di un account del
     Workspace, e devono valere entrambe le condizioni;
   - **Crittografia**: spunta **Richiedi la crittografia TLS**;
   - **Salva**. Le modifiche possono metterci un po' a diventare attive.
3. Nell'app, in **Impostazioni › Server di posta**, scegli **Server SMTP**:

   | Campo | Valore |
   | --- | --- |
   | Server | `smtp-relay.gmail.com` |
   | Porta | `587` |
   | Sicurezza | STARTTLS |
   | Utente e password | vuoti (o quelli dell'account, se hai chiesto l'autenticazione) |
   | Mittente | `Quaderno di Caccia <noreply@esempio.org>`, con un indirizzo del tuo dominio |

4. Tocca **Manda un'email di prova a me**. Se Google la rifiuta, controlla l'IP autorizzato e
   che il mittente sia del tuo dominio.
