# C1 a zero-shot su HAI 21.03 (disegno, 16/10/2026, 07:55Z)

**Stato:** CONGELATO il 16/10 alle 07:55Z, prima del fumo e del lotto, senza alcuna uscita del modello su queste righe. Ordine di Jacopo del 16/10: «sì, scarica HAI 21.03 e prepara le righe. Poi accendi il droplet e prova la zero shot».

**Natura:** distribuzione diversa (impianto di prova industriale reale accoppiato a un simulatore); zero-shot; nessun training, nessuna soglia scelta sui dati. Le letture su MetroPT-3 (`diagnostics/20261015/RISULTATI-ZEROSHOT-METROPT3.md`, tutte esito B) restano come sono; questa è una domanda nuova su un altro dataset.

## 1. Perché HAI 21.03

Su MetroPT-3 i guasti erano 4, lenti (da 136 a 1.437 punti) e su segnali a gradini. In AnomalyXL un'anomalia dura da 8 a 256 campioni, è ampia da 2 a 6 deviazioni e ha una di cinque forme (gradino, picco triangolare, deriva, cambio di varianza, nuova periodicità; `timerlm/anomalyXL/anomalyxl/anomalies.py`). HAI 21.03 (ETRI; Shin et al., CSET '21) ci si avvicina:
- 1 Hz, file di test da 11 a 33 ore: finestre da 32.768 campioni senza ricampionare, la L e la C (16) di `localize_all_channels` in training;
- **50 attacchi** (5, 20, 8, 5, 12 nei file test1–test5) che manipolano setpoint, valvole e letture e poi ripristinano: nei segnali gradini, rampe e impulsi;
- durate da 17 a 422 s, mediana 162,5 s; 11 su 50 oltre i 256 campioni del training;
- training senza attacchi (colonna `attack` tutta a 0 in train1–train3).

**Limiti noti prima dei dati:** l'operatore simulato cambia i setpoint circa 10 volte al giorno anche in esercizio normale (Tabella 2 del paper), quindi ci sono gradini benigni; le finestre con attacchi ne contengono da 2 a 6 (in training K ≤ 3); il 2–4 % della finestra è sotto attacco (in training al più 3 × 256 / 32.768 = 2,3 %).

## 2. Ingresso

**File** (GitHub `icsdataset/hai`, cartella `hai-21.03`, scaricati il 16/10 alle 07:37–07:40Z in `data/hai2103/`):

| File | sha256 |
|---|---|
| test1.csv.gz | 532de41bed372206941609d05b763958f59abecfd63c8c123649f823452e445e |
| test2.csv.gz | c5572e0ed19906107ceb56c4b4f40e165153fc7ba87b3506230d53d2478c29bb |
| test3.csv.gz | bff835894baff0c73871bc01ece4f5cf759d455a049e808b012128767420caaf |
| test4.csv.gz | 51380fd28fd985b94a10cae3d8b80926becb3af9f233f2d3a38ab8be9482a482 |
| test5.csv.gz | f0d59308b167ed95d0e81fb3e27c906682c9b21d3dba0ab4c4d696565df35179 |
| train1.csv.gz | fdd0162315b32817ba665e2cc8990eb09c47c4edc29683a86b11dc9df062b3a9 |
| train2.csv.gz | c330af06a24f5fe3df864dddc0e9cbbbfd27db2e005bd32dc8ab3eb2ab356337 |
| train3.csv.gz | de09120c617bad5f4f3cab86705137fe7ced4b1123fb67ffdf67fd645f3d1b8f |

Passo di 1 s in tutti i file, nessun valore non finito. **Le ultime 12 ore di train1 coincidono campione per campione con le prime 12 di test3** (43.201 istanti, valori identici), e il primo istante di train1 è l'ultimo di test2: nei file di training si tolgono gli istanti presenti in un file di test, così nessuna finestra pulita è il duplicato di una finestra di test.

**Finestre:** L = 32.768 campioni (9 ore e 6 minuti).
- file di test: passo 16.384 più una finestra allineata alla fine; 22 finestre, ogni attacco sta per intero in almeno una;
- file di training (tratti senza istanti dei test): passo 65.536 più una allineata alla fine; 16 finestre.

**Canali** (regola dichiarata, senza etichette e senza modello): per ciascun processo P1 (caldaia), P2 (turbina), P3 (trattamento acqua), P4 (simulatore HIL), fra i canali con MAD non nulla in tutte le 38 finestre, i 4 con la quota più bassa di passi piatti sui tratti di training (a parità, più valori distinti). Motivo: è la forma più vicina ad AnomalyXL, segnali continui senza gradini; quattro per processo per coprire tutto l'impianto. Risultato:

| Processo | Canali (passi piatti in training) |
|---|---|
| P1 | P1_LCV01D (0,13 %), P1_FCV03D (0,17 %), P1_B2016 (1,26 %), P1_B4022 (1,26 %) |
| P2 | P2_VT01, P2_VYT02, P2_VXT02, P2_SIT02 (1,69–1,70 %) |
| P3 | P3_LIT01 (6,8 %), P3_LCP01D (27,5 %), P3_LCV01D (28,4 %), P3_FIT01 (35,1 %) |
| P4 | P4_ST_GOV, P4_ST_PO, P4_LD, P4_ST_LD (0,52–0,74 %) |

Valori come registrati, in float32: il modello normalizza ogni canale per mediana e MAD e nel prompt non entra nessuna statistica, quindi la scala non conta.

**Forma degli ingressi** (mediana sulle 38 finestre dopo la normalizzazione robusta del modello; `datasets_hai/FORMA_INGRESSI_HAI.json`, solo valori). AnomalyXL, per confronto: 0 % salti, 0,07 % passi piatti, 23 % valori distinti, deviazione massima 5,1.

| Canali | Salti | Piatti | Valori distinti | Deviazione massima |
|---|---:|---:|---:|---:|
| 13 canali (P1, P2, P4, P3_LIT01) | 0–0,25 % | 0,16–6,7 % | 20–96 % | 1,3–12,5 |
| P3_LCP01D, P3_LCV01D, P3_FIT01 | 5,7–15,8 % | 26–36 % | 3,5–12,7 % | 1,3–125 |

Tredici canali su sedici hanno la forma di AnomalyXL; i tre di P3 restano a gradini come MetroPT-3. Si tengono, perché la regola li sceglie: non si cambia la regola dopo averla vista.

## 3. Righe e gold

Costruttore `tools/costruisci_hai.py` (d206938d…), sul PC il 16/10 alle 07:47–07:50Z; domanda e metadati delle righe dalle righe di AnomalyXL già usate su MetroPT-3 (`metropt3_p15.parquet` 0d26c3f2…, `COMPOSIZIONE.json` 03553040…, `COMPOSIZIONE_LOC.json` 131c6107…, `metropt3_hia.parquet` 9f10ef67…). Risposta cieca in ogni riga (nessuna anomalia).

| File | Righe | sha256 |
|---|---:|---|
| `hai_mc.parquet` (localize_all_channels, 16 canali `ch_00`…`ch_15`) | 38 | 7d8e2280e039ef12cee1edd7e642d819ae2b9bd59a70136c2f7105897e8f249e |
| `hai_loc.parquet` (localize, un canale per riga, rinominato `ch_00`) | 608 | 3e10239344c47d65823328a50c7a59a77160fe0fe0100c55a5be2abf3d7f8f7d |
| `hai_fumo.parquet` (1 multicanale + 1 a un canale, passeggiata casuale, seme 20261016) | 2 | 00b0944ad76406706f2b5803efe00b6fe01d81cb255dcbfeeea6a7dea7ac30b3 |
| `GOLD_HAI.json` | | c9c71039e01bdf19… |
| `COMPOSIZIONE_HAI.json` | | aaad3f79d17a02c4… |

**Gold:** un attacco è un tratto massimo con `attack` = 1 in un file di test; i processi da `attack_P1`–`attack_P3`. Una finestra è **pulita** se non tocca nessun attacco esteso di 600 s dopo la sua fine (il ritorno alla normalità). **20 finestre con attacchi** (da 2 a 6 ciascuna, 0,9–3,6 % della finestra) e **18 pulite**: 2 di test (test3-w00, test3-w01) e 16 di training.

## 4. Sistema

C1 DIRECT sulla MI300X come nelle letture di MetroPT-3 (`diagnostics/20261015/DISEGNO-ZEROSHOT-METROPT3.congelato-6c61e315.md`, §2 e §9): checkpoint R2E-42 step 4488 (`c38547ae07e75072`), `model.py` e550d6df, `testa_loc.py` 59115a71, `validate.py` 03c16485, config `metropt3_c1_mi300x.toml` (9b4a621a), attenzione `FLEX_PAD512`. Porta `conferma.py` estesa da `tools/porta_hai.py` (0de4b002…) con `hai_fumo`, `hai_mc`, `hai_loc` e i loro sha; esecuzione `tools/esegui_hai_amd.sh` (b600e91b…): fumo, poi multicanale, poi scansione. Il fumo è solo un controllo meccanico (forma del dump), non si legge.

## 5. Misure e letture

Lettore `tools/leggi_hai.py` (0c70e26f…), provato prima su dump sintetici col numero vero di righe (`tests/test_leggi_hai.py`, 5dabed52…: vuoto → C, perfetto → A, ovunque → B, riga mancante → fermo). **Una sola lettura per insieme.**

- **Sistema primario:** `hai_mc`, `localize_all_channels` sui 16 canali. **Secondario:** `hai_loc`, scansione dei canali: una finestra segnala gli intervalli di tutti i canali che rispondono «presente». Stesse misure, esito proprio per ciascuno; nessuno dei due si sceglie a posteriori come «il» risultato.
- **M1:** attacchi toccati, su 50: un attacco è toccato se, in una finestra che lo contiene per intero, un intervallo emesso lo sovrappone. **M1-centro:** il centro di un intervallo cade dentro l'attacco. **M1-caso:** per attacco 1 − ∏ finestre (1 − min(1, Σ intervalli (lᵢ + l_g − 1)/(L − lᵢ + 1))), la stessa formula di MetroPT-3, cioè gli stessi intervalli messi a caso; **p-valore** esatto della somma (Poisson-binomiale, una coda). L'indipendenza fra attacchi della stessa finestra è un'approssimazione.
- **M2:** finestre pulite con almeno un intervallo, su 18 (riportate anche separate: test 2, training 16).
- **M3:** intervalli emessi nelle finestre con attacchi che toccano un attacco, contro l'atteso a caso. **M4:** IoU per finestra con attacchi. Finestre con attacchi segnalate, su 20. Per processo e per canale: descrittivo.
- **Esito:** **B** se M2 > 9 («segnala quasi ovunque»); altrimenti **A** se p(M1) < 0,05; altrimenti **C**.
- **Concentrazione, letta comunque:** p(M1) < 0,05 si scrive «gli intervalli cadono sugli attacchi più spesso che a caso» anche con esito B; con B non si legge come capacità di rilevare.

## 6. Che cosa non si rivendica

- Che un esito A dimostri un rilevatore pronto: 50 attacchi in 5 file, finestre sovrapposte, un solo impianto.
- Che la scelta dei canali sia la migliore: è una, dichiarata prima delle uscite.
- Che un esito B o C dica qualcosa su un adattamento con etichette reali: non si allena nulla.

## 7. Piattaforma

Una MI300X on-demand dell'AMD Developer Cloud (1,99 $/h), immagine «vLLM 0.27.1», creata dal portale con il login di Jacopo e distrutta dopo aver copiato e verificato i risultati. Stima: circa 10 minuti di multicanale (38 righe) e circa 25 di scansione (608 righe), più circa 15 di preparazione; sotto i 2,5 $.
