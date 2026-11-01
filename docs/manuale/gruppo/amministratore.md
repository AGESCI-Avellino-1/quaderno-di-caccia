# Amministratore tecnico

L'amministratore tecnico cura la parte tecnica dell'app. Il primo lo crea chi installa l'app;
gli altri li nominano i capigruppo in **Incarichi di gruppo**, e devono essere capi.
L'incarico non dà accesso ai dati educativi dei ragazzi.

Può:

- cambiare le **Impostazioni** del sito, i modelli delle email e le pagine legali (vedi
  [Impostazioni](impostazioni));
- importare da BuonaStrada e gestire le correzioni (vedi [BuonaStrada](buonastrada));
- nominare il **primo capogruppo**, quando il gruppo non ne ha (in **Incarichi di gruppo**);
- aprire il **Pannello di amministrazione** e la **modalità di prova delle email**;
- mettere l'app in **manutenzione** e **sbloccare gli accessi** di chi ha sbagliato la
  password troppe volte.

## Il pannello di amministrazione

Nel menu, in **Amministrazione**, tocca **Pannello di amministrazione**: è il pannello
tecnico, per correggere a mano un account, un invito, un'unità, un incarico. Usalo solo
quando l'app non offre un'altra strada.

:::{warning}
Le schede sanitarie, le note e le regole sul rapporto con i minori non sono nel pannello.
Il **registro delle modifiche** però conserva i valori cambiati, anche dei dati sanitari: per
questo l'amministratore tecnico è sempre un capo, o ha una delega dei capigruppo per i dati.
:::

## La modalità di prova delle email

Per provare l'app senza disturbare nessuno: in **Impostazioni**, **Email di prova**, accendi
**Trattieni le email in Mailpit**. Le email non partono: restano in **Mailpit**, che apri dal
menu **Amministrazione** e vedi solo tu. Finché è accesa, tutti vedono in alto un avviso.

:::{warning}
In Mailpit trovi anche i codici di accesso e gli inviti degli altri. La modalità di prova si
può accendere solo se chi ha installato il server l'ha permessa: è pensata per un server di
prova, non per quello con i dati veri.
:::

## La manutenzione

Quando devi aggiornare l'app o sistemare qualcosa senza che nessuno ci lavori nel frattempo,
in **Impostazioni**, **Manutenzione**, scrivi un messaggio (per esempio fino a quando dura) e
tocca **Metti in manutenzione**.

Da quel momento entrano solo gli amministratori tecnici: tu vedi in alto un avviso giallo,
tutti gli altri vedono il tuo messaggio al posto delle pagine, anche chi era già dentro. Si
fermano anche la richiesta di iscrizione, la lista d'attesa e il calendario sul telefono;
restano aperte solo la pagina di accesso, la privacy policy e i termini.

:::{container} schermate
![La manutenzione attiva sul telefono](../img/gruppo/manutenzione-telefono.png){.telefono width="30%"}
![La manutenzione attiva sul computer](../img/gruppo/manutenzione-computer.png){.computer width="65%"}
:::

Ecco cosa vede un genitore che stava usando l'app:

:::{container} schermate
![L'app in manutenzione sul telefono](../img/comune/manutenzione-telefono.png){.telefono width="30%"}
![L'app in manutenzione sul computer](../img/comune/manutenzione-computer.png){.computer width="65%"}
:::

Nessuno perde niente: i dati salvati sul telefono restano, e le modifiche fatte senza rete
(per esempio le presenze al campo) aspettano e partono da sole quando la manutenzione finisce.
La pagina si aggiorna da sola ogni minuto.

Per cambiare il messaggio tocca **Aggiorna il messaggio**; quando hai finito, **Termina la
manutenzione**.

## Gli accessi bloccati

Dopo 5 tentativi sbagliati l'app smette di accettare la password per un'ora: per quell'account
dallo stesso browser, oppure per tutti da quell'indirizzo internet, per esempio la rete di
casa o della sede. In **Impostazioni**, **Accessi bloccati**, vedi i blocchi in corso: l'email
o l'indirizzo, quanti tentativi e fino a quando dura al massimo.

:::{container} schermate
![Gli accessi bloccati sul telefono](../img/gruppo/accessi-bloccati-telefono.png){.telefono width="30%"}
![Gli accessi bloccati sul computer](../img/gruppo/accessi-bloccati-computer.png){.computer width="65%"}
:::

Tocca **Sblocca** accanto a quello da togliere. L'elenco non si aggiorna da solo: tocca
**Aggiorna l'elenco** per vedere i blocchi nuovi.

:::{warning}
Sblocca quando la persona ti conferma di aver sbagliato lei. Se nessuno ha sbagliato, può
essere qualcuno che prova a entrare al posto suo: in quel caso lascia il blocco e avvisa i
capigruppo.
:::
