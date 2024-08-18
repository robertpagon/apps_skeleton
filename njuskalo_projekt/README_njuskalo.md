### Nadzor
-   Nadzorni mail
    Izvještaj o izvršenoj obradi
    -   sadržaj
        -   Upozorenja
        -   Greške
            -   Sve očekivane i neočekivana greška se dojavljuju u mailu bez stacktracea.
        -   Broj datoteka po izvoru
            -   Prilikom skidanja s sftp servera, broje se svi fajlovi pronađeni na serveru, grupirano po sorsovima.
            -   To se na kraju obrade šalje kao dio izvještaja o izvršenoj obradi.
        -   Broj redaka po datoteci
        -   Ukupno trajanje cijele obrade
    -   definirati logiku za slanje nadzornih mailova:
        -   a) statusni mail koji će slati sažetak nakon završene obrade
            -   koliko je fileova učitano po pojedinom sustavu
            -   koliko je recorda po pojedinom fileu učitano
            -   koliko je trajala obrada
        -   b) alarm mail koji se šalje u situacijama kada
            -   dođe do neke greške, u situacijama ukoliko neki file nije stigao
            -   alarm kada je broj zapisa po file-u veći od 700 000
        -   c) ukoliko je broj recorda jednak 1 milion file se ne smije učitati i treba se dići alarm
-   Log datoteka
    -   Stacktrace se zapisuje u log datoteku.
    -   U folderu `log` je log datoteka.
-   Nadzorna tablica
    -   start_time
    -   duration_s
    -   filename
    -   csv_rows_count
    -   tablename
    -   loaded_count
    -   status
    -   status_msg
-   Kontrole
    -   Broj redaka u csv = 1 000 000
        -   greška
        -   takva se ne loada
    -   Broj redaka veći od 70%
        -   warning
    -   Očekivani broj datoteka pojedinog tipa
        -   Ako ne stigne očekivani broj datoteka pojedinog tipa, to se javlja kao upozorenje
    -   Već učitane datoteke se ne učitavaju ponovno
        -   Nego se premještaju u direktorij DUPLICATE
    -   Neuspjele datoteke u ERROR

# Njuškalo - Piano
Programi za:
1. Download CSV datoteka sa sFTP servera i loadanje u bazu
1. Kreiranje izvještaja i slanje klijentima




- Podizanje servera
  - `docker compose up --build -d` - svi serveri
  - `docker compose up --build -d app_server` - samo server `app_server`

- Upisivanje lozinki
    - Naredbom
      - `docker exec -it app_server bash`
        - `echo 'TABLEAU_USERNAME="user"' >> /root/secrets/secrets_njuskalo.py`
        - `echo 'TABCMD_PASSWORD="lozinka"' >> /root/secrets/secrets_njuskalo.py`
- Upute za korištenje programa
  - `docker exec -it app_server /shared_folder/bin/sftp_to_db.py -h`

