# Controllare l'installazione

Quando qualcosa non va, o subito dopo aver installato, questi controlli dicono dove si è
fermata la richiesta: dal browser al reverse proxy, poi ai container e all'app. Falli in
ordine; i comandi vanno dati nella cartella dell'installazione (`/srv/qdc` negli esempi),
con l'utente che gestisce i container.

## 1. La porta dei container è libera

Con `nginx-host`, `apache-host` e `apache-vhost` i container ascoltano su `127.0.0.1`, sulla
porta di `QDC_HTTP_PORT` in `.env` (di base `8080`). Prima di avviarli nessun altro programma
deve usarla:

```bash
sudo ss -ltnp | grep ':8080 '
```

Nessuna riga: è libera. Una riga con un altro programma (un pannello, un altro sito): scegli
un'altra porta con `scripts/configure-prod.sh --port …`, che controlla da solo e propone la
prima libera, e rimetti il virtual host generato. Dopo l'avvio, la riga giusta è quella di
`docker-proxy` (o di `rootlessport` con Podman).

## 2. I moduli di Apache

Solo con Apache. Devono comparire `proxy_module`, `proxy_http_module` e `headers_module`
(con `apache-host` anche `ssl_module`, `rewrite_module` e `http2_module`):

```bash
apachectl -M | grep -E 'proxy|headers|ssl|rewrite|http2'
```

Se ne manca uno: `sudo a2enmod …` e `sudo systemctl reload apache2`.

## 3. La pagina di errore è leggibile

Quando l'app non risponde, il reverse proxy mostra una pagina presa dalla cartella
dell'installazione. L'utente del server web deve poterla leggere (`www-data` su Debian e
Ubuntu, `apache` o `nginx` su Rocky, Alma e RHEL):

```bash
sudo -u www-data test -r /srv/qdc/frontend/public/errori/50x.html && echo leggibile
```

Se non stampa «leggibile», una delle cartelle del percorso non è attraversabile da
quell'utente: di solito basta `chmod o+x` sulla cartella che lo blocca.

## 4. I container sono in salute

```bash
docker compose ps
```

`db` e `web` devono essere `healthy` (in salute), `app` avviato. Se `web` non parte, il
motivo è in `docker compose logs web` (di solito una voce sbagliata in `.env` o il database
non raggiungibile).

## 5. L'app risponde in locale

Dal server, direttamente ai container, senza passare dal reverse proxy:

```bash
curl -sI http://127.0.0.1:8080/
```

Deve rispondere `HTTP/1.1 200 OK`. Se qui risponde e dal dominio no, il problema è nel
reverse proxy (passi 1–3 e il virtual host).

## 6. L'app risponde dal dominio

```bash
curl -s https://qdc.esempio.org/api/v1/salute
```

Deve rispondere `{"stato": "ok"}`. Usa una richiesta normale (GET), come qui: con
`curl -I`, che chiede solo le intestazioni (HEAD), l'API risponde `405` anche quando tutto
funziona.

## 7. La posta parte

Il primo accesso dell'amministratore tecnico passa da un codice mandato per email, e a quel
punto nessuno può ancora impostare la posta dall'app. Quindi, **prima** di
`createsuperuser`, completa le voci SMTP in `.env` (vedi [La posta](installazione.md#la-posta))
e riavvia con `docker compose up -d`. Se il codice non arriva, l'errore del server di posta è
in `docker compose logs web`.
