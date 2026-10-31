# Dati personali e sicurezza

Il titolare del trattamento dei dati è l'AGESCI nazionale; i capigruppo sono delegati. Chi
installa l'app tiene un server con dati di minori, anche sanitari: le regole qui sotto non
sono facoltative.

- **Chi vede cosa** lo decide l'app, ruolo per ruolo: non servono configurazioni.
- L'**amministratore tecnico** non vede schede sanitarie, note e regole sul rapporto con i
  minori; il registro delle modifiche però conserva i valori cambiati, anche sanitari: per
  questo deve essere un capo, o avere una delega dei capigruppo.
- I dati sul telefono sono **cifrati** con un PIN; un telefono che non si collega per
  `QDC_OFFLINE_GIORNI` giorni (di base 14) cancella i suoi dati. Non allungare troppo questo
  periodo.
- Gli export di BuonaStrada, i dump del database e i backup non vanno mai lasciati sul server
  più del necessario, né messi nel repository; si spostano solo cifrati.
- La modalità di prova delle email (Mailpit) resta **spenta** sul server con i dati veri.
- Il server va tenuto aggiornato (sistema, Docker) e raggiungibile solo in HTTPS.

Per segnalare un problema di sicurezza scrivi al responsabile del progetto, non aprire una
segnalazione pubblica.
