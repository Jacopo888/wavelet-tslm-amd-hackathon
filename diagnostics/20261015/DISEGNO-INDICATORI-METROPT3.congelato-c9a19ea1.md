# C1 su MetroPT-3 dopo un pre-processing: indicatori di salute (A) e canali «alla AnomalyXL» (B) (disegno, 15/10/2026, 21:00Z)

**Stato:** CONGELATO il 15/10 alle 21:08Z, prima del fumo e del lotto, senza alcuna uscita del modello su queste righe. Scritto alle 21:00Z; aggiunti, prima del congelamento, la variante C e il §6 coi fatti delle righe costruite. Ordine di Jacopo del 15/10: «preparala con gli indicatori di salute (A), poi un'altra normalizzazione che preservi il senso ma adattando alla distribuzione di AnomalyXL, a tua scelta (B)».

**Natura:** come le due letture precedenti (`RISULTATI-ZEROSHOT-METROPT3.md`): distribuzione diversa; segnali industriali reali; zero-shot; quattro guasti, caso di studio, non conferma. **Le letture già fatte restano come sono** (esito B, multicanale e a un canale); queste sono domande nuove su un ingresso trasformato.

## 1. Perché

Sui segnali grezzi a 10 s C1 risponde «presente» quasi sempre. Il confronto delle statistiche d'ingresso (15/10, sera) dice che la differenza da AnomalyXL è nella forma, non nella scala:
- MetroPT-3 ha l'11,8 % di passi con un salto, contro lo 0 % di AnomalyXL;
- il 16,6 % di passi piatti contro lo 0,07 %;
- l'1 % di valori distinti contro il 23 %.

La causa sono i cicli del compressore: carica in media ogni 16,5 minuti (mediana su 15.584 cicli; il 90 % entro 30 minuti) e resta sotto carico il 16 % del tempo. Questi numeri vengono da tutta la serie, senza il gold.

**La scala non c'entra:** il modello normalizza ogni canale per mediana e MAD, una trasformazione che non cambia se si sposta o si ri-scala il canale. Nel prompt (layout `eth`) non c'è nessuna statistica, e l'unico dato di scala nei token è il rapporto fra scala locale e globale. Portare i canali a media 0 e deviazione 1 come il generatore di AnomalyXL darebbe lo stesso ingresso.

## 2. Ingresso

**Griglia:** un punto ogni 2 minuti. Ogni punto si calcola sui campioni grezzi dei 60 minuti precedenti, che coprono almeno due cicli nel 90 % dei casi. Un punto è valido con almeno 180 campioni grezzi (metà dei 360 attesi); si tengono solo i punti validi, serie per indice come nelle letture precedenti.

**A, indicatori di salute** (6 canali, valori come calcolati):

| Indicatore | Calcolo sui 60 minuti | Perché |
|---|---|---|
| `quota_carico` | media di DV_eletric (1 = compressore sotto carico) | una perdita d'aria fa lavorare di più il compressore |
| `cicli_ora` | fronti di salita di DV_eletric, per ora | idem, più cicli |
| `calo_TP3` | mediana della pendenza di TP3 (bar/min) fra campioni consecutivi a compressore scarico | con una perdita la pressione cala più in fretta quando il compressore non carica |
| `TP3_medio` | media di TP3 | livello di pressione |
| `olio_medio` | media di Oil_temperature | carico termico |
| `corrente_media` | media di Motor_current | carico elettrico |

Se in un punto ci sono meno di 10 coppie a compressore scarico, `calo_TP3` tiene l'ultimo valore valido (dichiarato ora).

**B, i 7 canali analogici «alla AnomalyXL»** (TP2, TP3, H1, DV_pressure, Reservoirs, Oil_temperature, Motor_current):
1. mediana mobile a 60 minuti di ciascun canale sulla griglia: toglie i cicli e conserva l'andamento lento del canale;
2. in ogni finestra, trasformazione per ranghi verso una normale standard (media 0, deviazione 1, come i canali del generatore): conserva l'ordine nel tempo e ogni salto o deriva, toglie le code pesanti;
3. rumore gaussiano di deviazione 0,1, seme 20261015: rompe i valori uguali, così il segnale è continuo come quelli di AnomalyXL.

**C, gli indicatori di A con l'adattamento di B** (aggiunta prima del congelamento, vedi §6): gli stessi 6 indicatori, in ogni finestra portati per ranghi verso una normale standard, con rumore gaussiano di deviazione 0,1 (seme 20261017).

**Finestre:** L = 16.384 punti (circa 23 giorni se senza buchi), la L più corta vista in training; passo 8.192, più una finestra allineata alla fine. A questa scala i guasti occupano circa dallo 0,8 % al 9,6 % della finestra (in training al più l'1,5 %).

**Righe:** `localize` a un canale, come nell'ultima lettura: canale rinominato `ch_00`, domanda di localize di AnomalyXL presa dal val (da `COMPOSIZIONE_LOC.json`), L = 16.384, risposta cieca `present: false`. **A** e **C:** finestre × 6 righe; **B:** finestre × 7 righe. Fumo: 2 righe di passeggiata casuale con la stessa struttura.

**Gold:** gli stessi 4 guasti e le stesse zone sospette del PDF, riportati sugli indici della griglia (`GOLD_HI.json`): inizio = primo punto con tempo ≥ inizio, fine esclusiva = primo punto con tempo > fine.

## 3. Sistema

C1 DIRECT sulla MI300X, come nelle letture precedenti (`DISEGNO-ZEROSHOT-METROPT3.congelato-6c61e315.md`, §2 e §9): checkpoint `c38547ae07e75072`, config `metropt3_c1_mi300x.toml` (9b4a621a), attenzione `FLEX_PAD512`. Porta estesa con `metropt3_hia`, `metropt3_hib`, `metropt3_hifumo`.

## 4. Misure e letture

Le stesse dell'ultima lettura (`DISEGNO-LOCALIZE-CANALE-METROPT3.congelato-4b0dc596.md`, §4–§5), separatamente per A, B e C; **nessuna delle tre si sceglie a posteriori come «il» risultato**, si riportano tutte:
- **sistema primario «scansione dei canali»:** una finestra segnala se almeno un canale risponde «presente»;
- M1, M1-centro, M1-caso, M2, M3, M4 e formato come lì; per canale, descrittivo;
- **esiti A–D con le stesse soglie:** A se M1 ≥ 3 e M2 ≤ metà delle finestre pulite; B se M2 > metà; C se M1 ≤ 1 e M2 ≤ metà; D altrimenti.
- **Se le finestre pulite sono meno di 3**, M2 si scrive come conteggio e l'esito si scrive «non determinabile su M2».

Lettore: `tools/leggi_localize_canale.py` con i nomi dei canali e la L di questa domanda, provato prima su dump sintetici con il numero vero di righe.

## 5. Che cosa non si rivendica

- Che un esito A dimostri che il modello «legge» i guasti: quattro eventi, finestre sovrapposte.
- Che il pre-processing sia il migliore: è uno, scelto dal dominio prima dei dati.
- Che A o B diventino il prodotto: lo decide Jacopo dopo.

## 6. Righe costruite (15/10, fra le 21:00 e le 21:08Z, sul PC; nessun modello)

`tools/costruisci_indicatori.py` dal CSV (db30ccb4…): 153.449 punti di griglia, **126.333 validi**. 15 finestre (inizi 0, 8.192, …, 106.496, più 109.949 allineata alla fine): **7 contengono per intero un guasto, 7 sono pulite** (0–3, 12–14). I guasti occupano 720, 196, 1.437 e 136 punti, cioè il 4,4 %, l'1,2 %, l'8,8 % e lo 0,8 % di una finestra.

| File | Righe | sha256 |
|---|---:|---|
| `metropt3_hia.parquet` (A) | 90 | 9f10ef678b5499b3bcae22b32619c54c8161dfbadb12e17330b35d44809c91a1 |
| `metropt3_hib.parquet` (B) | 105 | 0bcd59d16156c4d57c66b78f2d834acabd7601c29b36d318c99e9a10c6d4a85c |
| `metropt3_hic.parquet` (C) | 90 | 0722b42ec2db0b68f1f0e0f1bd43fa6ada2c5d773cbf3086a867f43926cf3e96 |
| `metropt3_hifumo.parquet` | 2 | 2e5f7e68e63b7812307ad28770591b62cdf22f74a53a68f8cd8f6b5e9fe99a75 |
| `GOLD_HI.json` | | ca20d2a8664eae59… |
| `COMPOSIZIONE_HI.json` | | b1eb08692ba4147d… |

**Controllo della forma degli ingressi** (solo valori, senza risposte né gold; mediana sulle 15 finestre dopo la normalizzazione robusta del modello). AnomalyXL, per confronto: 0 % salti, 0,07 % passi piatti, 23 % valori distinti, deviazione massima 5,1.

| Canale | Salti | Piatti | Valori distinti | Deviazione massima | MAD nulla |
|---|---:|---:|---:|---:|---:|
| A `quota_carico` | 42 % | 55 % | 6 % | 24 | 0 / 15 |
| A `cicli_ora` | 15 % | 85 % | 0,15 % | 36 | **7 / 15** |
| A `calo_TP3` | 9 % | 91 % | 0,24 % | 6,1 | 0 / 15 |
| A `TP3_medio`, `olio_medio`, `corrente_media` | 0,06–0,11 % | 2–4 % | 86–94 % | 6,7–40 | 0 / 15 |
| B, i 7 canali | 0,02–0,24 % | 0 % | 100 % | 3,4–15 | 0 / 15 |
| C, i 6 indicatori | 0,02–0,06 % | 0 % | 100 % | 3,6–4,1 | 0 / 15 |

**Perché C:** tre indicatori di A sono a gradini o piatti. `cicli_ora` ha MAD nulla in 7 finestre su 15, e lì la normalizzazione del modello degenera come per i canali digitali. A resta com'è, come chiesto. C dà agli stessi indicatori la forma di B; A e B sono identici byte per byte alla prima costruzione.
