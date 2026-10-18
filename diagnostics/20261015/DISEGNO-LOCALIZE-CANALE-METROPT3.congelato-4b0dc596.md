# C1 su MetroPT-3, un canale alla volta (disegno e lettura dichiarata, 15/10/2026, 20:03Z)

**Stato:** CONGELATO il 15/10 alle 20:19Z, prima del fumo e del lotto, senza alcuna uscita del modello su queste righe. Scritto alle 20:03Z; aggiunto solo il §6-bis con i fatti delle righe costruite. Ordine di Jacopo del 15/10, dopo i risultati dello zero-shot multicanale: «si procedi così su cluster AMD».

**Natura:** come lo zero-shot multicanale (`RISULTATI-ZEROSHOT-METROPT3.md`): distribuzione diversa; segnali industriali reali; zero-shot; quattro guasti, caso di studio, non conferma. **È una domanda nuova sulle stesse finestre, non una rilettura:** il multicanale resta letto com'è, con esito B.

## 1. La domanda

Se a C1 si fa la domanda su cui è stato allenato per rispondere anche «assente», cioè `localize` su un solo canale, segnala meno nelle finestre senza guasti e trova i guasti oltre il caso?

## 2. Sistema

Lo stesso dello zero-shot multicanale sulla MI300X (`DISEGNO-ZEROSHOT-METROPT3.congelato-6c61e315.md`, §2 e §9): C1 DIRECT, checkpoint R2E-42 4.488 (sha `c38547ae07e75072`), stesso codice e stesso config `metropt3_c1_mi300x.toml`, attenzione `FLEX_PAD512`, macchina AMD Developer Cloud MI300X ricreata con la stessa immagine. Cambiano solo le righe e la porta: due insiemi nuovi, `metropt3_loc` e `metropt3_locfumo`.

## 3. Righe

- **Le stesse 23 finestre** (L = 131.072, passo 65.536 più quella allineata alla fine), prese da `metropt3_a7.parquet` (13bc0666…).
- **Una riga per finestra e per canale analogico:** TP2, TP3, H1, DV_pressure, Reservoirs, Oil_temperature, Motor_current. Sono **161 righe**. Il canale si rinomina `ch_00` come in tutte le righe di localize del training; i valori sono quelli del canale.
- **Domanda:** quella di `localize` di AnomalyXL, verbatim, con L = 131.072. Si prende da una riga di localize del val e si controlla che sia identica in tutte.
- **Cecità:** risposta `localize:{"_L": 131072, "present": false}` in tutte le righe e liste `injection_*` vuote. Il campo `primary` del dump non si legge. Il gold è il `GOLD.json` di prima (25317206).
- **Gli 8 canali digitali restano fuori:** sono stati 0/1 di valvole, e con la normalizzazione del modello un canale quasi costante degenera (stesso motivo dell'insieme A7).
- **Fumo:** 2 righe di rumore casuale con la stessa struttura (1 canale, L = 131.072, stessa domanda), seme 20261015.

## 4. Misure

**Sistema primario, «scansione dei canali»:** in una finestra c'è una segnalazione se almeno uno dei 7 canali risponde «presente». Gli intervalli della finestra sono quelli di tutti i canali che rispondono «presente».

| Sigla | Misura | Popolazione |
|---|---|---|
| **M1** | guasti toccati: in almeno una finestra che contiene il guasto per intero, almeno un intervallo emesso (di qualunque canale) si sovrappone al guasto | 4 guasti |
| **M2** | finestre pulite con almeno una segnalazione | 15 finestre pulite |
| M1-centro, M1-caso, M3, M4, formato | come nel disegno multicanale (§4), sugli intervalli dei 7 canali | come lì |
| Per canale | M1 e M2 di ciascun canale da solo, e quante risposte «assente» dà su 23 | descrittivo |

## 5. Letture (dichiarate prima dei dati)

Le stesse regole del multicanale, applicate al sistema primario:

| Esito | Condizione | Si scrive |
|---|---|---|
| A | M1 ≥ 3 su 4 e M2 ≤ metà delle finestre pulite | «a un canale alla volta segnala i guasti documentati e tace nella maggior parte delle finestre senza guasti» (con la nota «non oltre il caso» se M1 non supera M1-caso di almeno 1) |
| B | M2 > metà delle finestre pulite | «segnala quasi ovunque: le rilevazioni non si leggono come prova» |
| C | M1 ≤ 1 e M2 ≤ metà | «a un canale alla volta non trova questi guasti» |
| D | altrimenti | «indeterminato su quattro eventi» |

- **Il confronto col multicanale si scrive solo come conteggi** (M1 e M2 fianco a fianco), senza CI.
- **Il dettaglio per canale è descrittivo:** non si sceglie a posteriori il canale «migliore».

## 6. Esecuzione

1. Righe costruite sulla MI300X da `tools/costruisci_loc_canale.py`, dal parquet A7 e dalla domanda del val; sha nella porta.
2. Lettore `tools/leggi_localize_canale.py`, provato su dump sintetici da 161 righe prima della lettura.
3. Fumo (2 righe), poi le 161 righe; una sola lettura.
4. Macchina distrutta appena copiati e verificati i risultati.

## 6-bis. Righe costruite e porta (15/10, 20:18Z, sulla MI300X 609474246; nessun modello)

`tools/costruisci_loc_canale.py`, nel container `wrope`, da `metropt3_a7.parquet` (13bc0666…) e dal val di AnomalyXL (90b805b8…): la domanda di localize è identica in tutte le righe di localize del val.

| File | Righe | sha256 |
|---|---:|---|
| `metropt3_loc.parquet` | 161 | 11b1b314c06391f050850533397c04c24d90e45dd741b529929012ea703ab3da |
| `metropt3_locfumo.parquet` | 2 | 6352a85cb5c604df477eeaac7c299420cbd00d93e8a357f18213dbf7997eb3fb |
| `COMPOSIZIONE_LOC.json` | | 131c61077336eecf… |

- **Porta:** `tools/porta_loc.py` aggiunge `metropt3_loc` (161) e `metropt3_locfumo` (2) a `conferma.py` della copia, con questi sha.
- **Esecuzione:** `tools/esegui_loc_amd.sh`, che controlla che gli sha delle righe siano quelli scritti qui.
- **La macchina è la seconda MI300X** (609474246, creata alle 20:07Z), con la stessa immagine e la stessa preparazione della prima: AnomalyXL e Qwen agli stessi pin verificati, config `metropt3_c1_mi300x.toml` identico (9b4a621a).
