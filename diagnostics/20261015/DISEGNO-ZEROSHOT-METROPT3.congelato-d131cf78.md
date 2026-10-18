# Zero-shot del lettore C1 su MetroPT-3 (disegno e lettura dichiarata, 15/10/2026, 16:16Z)

**Stato:** CONGELATO il 15/10 alle 16:21Z, prima del fumo e del lotto, senza alcuna uscita del modello su MetroPT-3. Scritto alle 16:16Z; aggiunto solo il §8 con i fatti delle righe costruite (job 34396, nessun modello). Ordine di Jacopo del 15/10: «procediamo allo zero-shot del nostro modello migliore sui dati industriali. Usiamo le gpu del poli»; prima senza zoom (12/10).

**Natura:** distribuzione diversa; segnali industriali reali; zero-shot (nessun adattamento); **quattro guasti documentati: è un caso di studio, non una conferma.** Nessun numero di qui si confronta con un CI appaiato.

## 1. La domanda

Il lettore della linea Rope, **C1 DIRECT** (una chiamata, senza zoom), trova i guasti documentati di MetroPT-3 quando riceve la registrazione del compressore così com'è, e tace dove non ci sono guasti?

## 2. Sistema

- **C1 = R2E-42, step 4.488**, `runs/r2e/checkpoints/step_000000004488/model.safetensors`, sha256 che comincia con `c38547ae07e75072` (lo stesso controllo del lotto OOD).
- Lettura diretta, una chiamata, nessuna finestra, nessun correttore.
- Codice: copia di `code_ood2`, l'albero del lotto OOD (a). I tre file `model.py`, `testa_loc.py`, `training/validate.py` hanno lo stesso sha di `code_r2e`: e550d6df, 59115a71, 03c16485. Unici cambi nella copia: due insiemi nuovi nella porta `conferma.py` e `run_root` del config, che punta alla cartella dell'hackathon. Nessun file della linea Rope viene scritto.
- Config: `configs/va1s4locr2e_polimi.toml`, identico salvo `run_root`.

## 3. Dati

**Fonte:** `MetroPT3(AirCompressor).csv` (UCI 791, CC BY 4.0), sha256 `db30ccb4…`, 1.516.948 righe, 15 segnali, passo tipico 10 s.

**Serie per indice di campione.** I buchi non si riempiono: un buco diventa un salto fra due campioni consecutivi. Nessun ricampionamento, nessuna decimazione, nessuna normalizzazione oltre quella del modello. Valori come nel CSV.

**Finestre:** L = 131.072 campioni consecutivi (circa 15 giorni a 10 s), la L più lunga vista in training. Inizi a 0, 65.536, 131.072, …, 21 × 65.536 = 1.376.256, più una finestra allineata alla fine (inizio 1.385.876): **23 finestre**. Con passo pari a metà finestra ogni guasto (al più 52,5 h, cioè circa 19.000 campioni) sta per intero in almeno una finestra.

**Due insiemi, stesse finestre:**

| Insieme | Canali | Ruolo |
|---|---|---|
| **P15** | tutti i 15 segnali, nell'ordine del CSV, rinominati `ch_00`…`ch_14` come in training | **PRIMARIO**: il benchmark così come è rilasciato, nessuna scelta di canali |
| A7 | i 7 analogici (TP2, TP3, H1, DV_pressure, Reservoirs, Oil_temperature, Motor_current), rinominati `ch_00`…`ch_06` | accanto. Motivo dichiarato ora: gli 8 digitali sono stati 0/1 di valvole; con la normalizzazione MAD del modello un canale quasi costante degenera |

**Domanda:** quella di `localize_all_channels` di AnomalyXL, verbatim, con la L e la C della riga («(Here L = 131072, C = 15.)»). È l'unico compito multicanale visto in training (sempre 16 canali, L 32.768 o 131.072).

**Cecità:** le righe portano la risposta vuota (`"anomalies": []`) e liste `injection_*` vuote; il lotto non vede il gold. **Il campo `primary` del dump non è una misura e non si legge.** Il gold sta in un file a parte (`GOLD.json`) e lo apre solo il lettore.

**Gold:** i quattro guasti del PDF del dataset (tutti «Air leak», «High stress»):

| # | Inizio | Fine |
|---|---|---|
| 1 | 18/4/2020 00:00 | 18/4/2020 23:59 |
| 2 | 29/5/2020 23:30 | 30/5/2020 06:00 |
| 3 | 5/6/2020 10:00 | 7/6/2020 14:30 |
| 4 | 15/7/2020 14:30 | 15/7/2020 19:00 |

- Orari presi nello stesso orologio dei timestamp del CSV. Indice d'inizio = primo campione con timestamp ≥ inizio; fine esclusiva = primo campione con timestamp > fine.
- **Zone sospette** (per le finestre pulite): dall'inizio di ogni guasto alla manutenzione successiva elencata nel PDF. #1 → 30/4 12:00; #2 → 8/6 16:00; #3 → 8/6 16:00; #4 → 16/7 00:00. **Interpretazione dichiarata:** il PDF stampa «Maintenance on 30Apr» nella riga del guasto del 29/5, che però viene dopo; la si attribuisce al guasto del 18/4.

## 4. Misure

| Sigla | Misura | Popolazione |
|---|---|---|
| **M1** | **guasti rilevati**: un guasto è rilevato se, in almeno una finestra che lo contiene per intero, almeno un intervallo emesso (di qualunque canale) si sovrappone al guasto di almeno un campione | i 4 guasti |
| **M2** | **falsi allarmi**: finestre pulite con almeno un intervallo emesso | finestre senza sovrapposizione con le zone sospette |
| M1-centro | come M1, ma col centro dell'intervallo emesso dentro il guasto | i 4 guasti |
| M1-caso | rilevazioni attese se gli stessi intervalli emessi cadessero a caso nella finestra (somma, per intervallo, di (lunghezza emessa + lunghezza del guasto − 1) / (L − lunghezza emessa + 1), troncata a 1) | i 4 guasti |
| M3 | precisione delle segnalazioni: intervalli emessi che toccano una zona sospetta, sul totale degli emessi | tutte le finestre |
| M4 | IoU fra l'unione degli intervalli emessi e l'unione dei guasti nella finestra, descrittiva | finestre che contengono un guasto per intero |
| Formato | emissioni valide, liste vuote, canali citati | tutte |

**Limite dichiarato ora:** in training un'anomalia occupava al più l'1,5 % della finestra (localize) o lo 0,74 % (multicanale). Qui i guasti occupano dall'1,2 % (4,5 h) al 14,4 % (52,5 h) di una finestra da 15 giorni. L'IoU (M4) è attesa bassa per costruzione anche con il posto giusto; per questo la misura principale è la sovrapposizione.

## 5. Letture (dichiarate prima dei dati)

Per P15, la primaria:

| Esito | Condizione | Si scrive |
|---|---|---|
| **A** | M1 ≥ 3 su 4 e M2 ≤ metà delle finestre pulite | «a zero-shot il lettore segnala i guasti documentati e tace nella maggior parte delle finestre senza guasti» |
| **B** | M2 > metà delle finestre pulite | «segnala quasi ovunque: le rilevazioni non si leggono come prova», qualunque sia M1 |
| **C** | M1 ≤ 1 su 4 e M2 ≤ metà | «a zero-shot non trova questi guasti» |
| **D** | ogni altro caso | «indeterminato su quattro eventi» |

- M1 si scrive sempre accanto a M1-caso: se le rilevazioni osservate non superano quelle attese a caso di almeno 1, l'esito A si scrive con la nota «non oltre il caso».
- A7 si legge con le stesse regole, accanto, senza esito proprio.
- Una sola lettura per insieme, sulle copie verificate dei dump.

## 6. Prima del lotto

1. **Righe:** costruite sul cluster da `tools/costruisci_metropt3.py` (job CPU), schema preso dal val di AnomalyXL; sha dei due parquet nella porta.
2. **Fumo:** due righe con la stessa struttura (L = 131.072, C = 15, stessa domanda) e valori di rumore casuale, lungo lo stesso percorso. Serve solo a vedere che la generazione arrivi in fondo e che il dump si legga; le sue uscite non dicono nulla su MetroPT-3.
3. **Lettore:** `tools/leggi_zeroshot_metropt3.py`, provato su dump sintetici con 23 righe prima della lettura.

## 7. Che cosa non si rivendica

- Generalità ad altri impianti o ad altri guasti: è un compressore, quattro perdite d'aria.
- Che un fallimento dipenda dal modello e non dal gold: il PDF dà intervalli di sistema, non canali; i guasti potrebbero durare più o meno di quanto scritto.
- Un confronto con altri modelli: viene dopo, con le stesse righe.
- Lo zoom: per ordine di Jacopo si parte senza.

## 8. Le righe costruite (job 34396, 15/10 16:19Z; nessun modello)

`tools/costruisci_metropt3.py` sha 86661982, `pbs/costruisci_metropt3.pbs` ef166f8b. Cartella sul cluster: `/work/u10970284/hackathon-amd-act3/datasets/metropt3/righe/`.

| File | Righe | sha256 |
|---|---:|---|
| `metropt3_p15.parquet` | 23 | 0d26c3f27574fbe4… |
| `metropt3_a7.parquet` | 23 | 13bc066618de948e… |
| `metropt3_fumo.parquet` | 2 | 186f348e5d1e852a… |
| `GOLD.json` | | 25317206… |
| `COMPOSIZIONE.json` | | 03553040… |

| Guasto | Campioni | Finestre che lo contengono per intero |
|---|---:|---|
| 1 | 8.657 | 7, 8 |
| 2 | 2.360 | 11, 12 |
| 3 | 17.315 | 12, 13 |
| 4 | 1.622 | 16, 17 |

- **Finestre pulite: 15** (0–6, 10, 14, 15, 18–22). La finestra 9 tocca la zona sospetta del guasto 1 senza toccare il guasto: non entra né in M1 né in M2.
- Porta: `code_metropt3/src/wavelet_rope/conferma.py` con gli insiemi `metropt3_p15`, `metropt3_a7`, `metropt3_fumo` e i tre sha qui sopra; config `configs/metropt3_c1.toml` (solo `run_root` cambiato).
