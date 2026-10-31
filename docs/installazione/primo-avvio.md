# Primo avvio

Su un'installazione vuota nessuno può ancora invitare qualcuno dall'app. L'ordine è questo.

## 1. L'amministratore tecnico

```bash
docker compose exec web python manage.py createsuperuser
```

È l'**amministratore tecnico**: gestisce account, importazioni e impostazioni del sito, ma
**non vede i dati educativi e sanitari** dei ragazzi. Gli altri amministratori li nominano poi
i capigruppo dall'app, e devono essere capi.

## 2. I dati da BuonaStrada

Un capogruppo scarica da BuonaStrada l'export **Ricerca soci** in CSV. Copialo sul server e
importalo, prima in anteprima:

```bash
docker compose cp RicercaSoci.csv web:/tmp/RicercaSoci.csv
docker compose exec web python manage.py importa_buonastrada /tmp/RicercaSoci.csv            # anteprima
docker compose exec web python manage.py importa_buonastrada /tmp/RicercaSoci.csv --applica  # importa
```

La prima importazione crea il gruppo, le unità (senza nome: le nominano i capigruppo), le
persone e le famiglie. Da quel momento l'installazione accetta solo export dello stesso
gruppo.

:::{warning}
L'export contiene dati di minori: cancellalo dal server (e dal container) appena hai
importato, e non metterlo mai nel repository.
:::

```bash
docker compose exec web rm /tmp/RicercaSoci.csv && rm RicercaSoci.csv
```

Le importazioni successive le fanno i capigruppo dall'app.

## 3. Il primo capogruppo

```bash
docker compose exec web python manage.py crea_invito <codice socio> <email> --capogruppo
```

Al capogruppo arriva l'invito per email. In alternativa, l'amministratore tecnico può entrare
nell'app e nominare il primo capogruppo da **Incarichi di gruppo**. Da lì in poi gli inviti
partono dall'app.

## 4. Le prime impostazioni

Il capogruppo, dall'app, nel menu **Amministrazione › Impostazioni**:

- nome e titolo del sito, intestazione delle stampe con il logo del gruppo;
- i modi di pagamento delle quote (contanti, bonifico, PayPal);
- la privacy policy e i termini, partendo dal testo di base, da far controllare a chi segue
  la privacy per il gruppo.

Poi nomina lo staff delle unità, i tesorieri e gli eventuali altri amministratori: i passi
sono nel manuale d'uso.
