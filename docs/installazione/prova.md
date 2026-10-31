# Server di prova

Per provare l'app (o un aggiornamento) senza disturbare nessuno, su un server **di prova**
le email si possono trattenere in **Mailpit** invece di spedirle.

1. In `.env`: `QDC_MAILPIT_CONSENTITO=true`.
2. Avvia anche Mailpit:

   ```bash
   COMPOSE_PROFILES=mailpit docker compose up -d
   ```

3. Nell'app l'amministratore tecnico accende la modalità di prova in **Impostazioni › Email
   di prova** e legge le email dal menu **Amministrazione › Mailpit**. Mailpit non pubblica
   porte: si raggiunge solo attraverso l'app, e solo dall'amministratore tecnico.

Finché la modalità è accesa, tutti vedono in alto un avviso.

:::{danger}
Non usarla sul server con i dati veri: in Mailpit finiscono anche i codici di accesso e gli
inviti, che fanno entrare come chiunque. Lì lascia `QDC_MAILPIT_CONSENTITO=false`.
:::
