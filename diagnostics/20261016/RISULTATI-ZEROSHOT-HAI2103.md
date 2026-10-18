# C1 a zero-shot su HAI 21.03: risultati (16/10/2026)

**Lettura dichiarata prima dei dati:** `DISEGNO-ZEROSHOT-HAI2103.congelato-e666e5f1.md` (congelato alle 07:55Z). Una sola lettura per insieme, alle 09:44:59Z, con `tools/leggi_hai.py` (0c70e26f…). Nessun training, nessuna soglia scelta sui dati.

**Esecuzione:** quarta MI300X dell'AMD Developer Cloud (609621907), creata verso le 08:09Z. Fumo superato alle 09:15Z (controllo solo meccanico: le 2 righe di passeggiata casuale rispondono «assente»). Multicanale: 38 righe in 422 s, fino alle 09:22Z. Scansione: 608 righe in 1.169 s, fino alle 09:42Z. Risultati copiati e verificati alle 09:43Z (`amd4/risultati4.tgz` fca50dee…, `SHA256SUMS` OK per fumo, multicanale e scansione). Dump: multicanale 2c6afb72…, scansione 46fe271d…, fumo deadc9d7…. Letture: `lettura/lettura_c1_hai_mc.json` (581301c4…), `lettura/lettura_c1_hai_scan.json` (403447e2…).

## 1. Esito della regola

| Misura | Multicanale (primario) | Scansione a un canale (secondario) |
|---|---|---|
| **Esito della regola** | **B** | **B** |
| M2, finestre pulite con segnalazioni | 18 / 18 | 18 / 18 |
| **M1, attacchi toccati su 50** (attesi a caso) | **34** (6,6) | **37** (11,8) |
| p-valore di M1 (una coda) | 1·10⁻¹⁹ | 2·10⁻¹⁴ |
| M1-centro, attacchi col centro di un intervallo dentro | 32 | 35 |
| Concentrazione (p < 0,05) | **sì** | **sì** |
| M3, intervalli nelle finestre con attacchi che toccano un attacco (atteso a caso) | **93 / 154** (7,0) | 112 / 295 (12,9) |
| Precisione per finestra con attacchi, mediana (min–max) | 0,71 (0,10–0,86) | 0,40 (0,07–0,64) |
| M4, IoU per finestra, mediana (max) | 0,23 (0,35) | 0,16 (0,32) |
| Intervalli per finestra: pulite / con attacchi | 7,5 / 7,7 | 13,8 / 14,8 |
| Lunghezza di un intervallo, mediana (min–max) | 152 s (80–186) | 136 s (67–182) |
| Risposte non valide | 0 / 38 | 0 / 608 (64 «assente») |

- **Esito B per la regola dichiarata:** C1 segnala in tutte le 18 finestre pulite, circa 7–8 intervalli per finestra, tanti quanti nelle finestre con attacchi. **Il numero di segnalazioni non distingue una finestra con attacchi da una pulita.**
- **La posizione sì:** nelle finestre con attacchi il 60 % degli intervalli del multicanale (93 su 154) cade su un attacco, contro il 4,5 % atteso mettendo gli stessi intervalli a caso; tocca 34 attacchi su 50 contro 6,6 attesi. È la domanda «concentrazione» dichiarata nel §5 del disegno, letta anche con esito B: **gli intervalli cadono sugli attacchi molto più spesso che a caso.**

## 2. Dettaglio descrittivo

- **Il canale giusto:** in entrambi i modi ogni attacco toccato è toccato da almeno un canale del proprio processo (multicanale: P1 23 su 34, P2 16 su 22, P3 5 su 8, con 4,6, 2,9 e 1,1 attesi a caso).
- **Per canale (scansione):** i più informativi sono P1_FCV03D (16 attacchi toccati, 0,9 attesi), P2_SIT02 (13), P1_LCV01D (12) e i tre di vibrazione di P2 (9 ciascuno). I quattro canali del simulatore P4 non toccano quasi nulla (0–1 attacchi); P1_B2016 e P1_B4022 nessuno o quasi.
- **Durata:** toccati 24 attacchi su 39 fino a 256 s (4,7 attesi) e 10 su 11 oltre i 256 s (1,9 attesi) nel multicanale.
- **Per file (multicanale):** test1 2/5, test2 13/20, test3 5/8, test4 5/5, test5 9/12.
- **Accordo fra i due modi:** 33 attacchi toccati da entrambi, 1 solo dal multicanale, 4 solo dalla scansione, 12 da nessuno.
- **Lunghezze:** come su MetroPT-3 l'intervallo resta di circa 140–150 campioni, la durata tipica di un'anomalia del training, qualunque sia l'attacco (da 17 a 422 s). L'IoU resta quindi bassa anche quando la posizione è giusta.

## 3. Che cosa si può dire

- **Si può dire:** a zero-shot, su segnali industriali reali con anomalie della scala di AnomalyXL, C1 **mette i suoi intervalli sugli attacchi** molto più spesso che a caso, nel formato multicanale del training, con una sola chiamata per finestra di 9 ore e 16 canali. Su MetroPT-3, con guasti lenti e segnali a gradini, questo non si vedeva (4 eventi, nessuna concentrazione leggibile).
- **Non si può dire:** che C1 sia un rilevatore. Segnala sempre circa 8 intervalli per finestra, anche dove non c'è nessun attacco: senza una soglia o un punteggio, il «c'è o non c'è» non funziona (esito B). Si comporta come un indicatore dei tratti più anomali della finestra, non come un allarme.
- **Limiti:** un solo impianto e 50 attacchi in 5 file. Finestre sovrapposte. L'indipendenza fra attacchi della stessa finestra nel p-valore è un'approssimazione. La scelta dei canali è una, dichiarata prima. In esercizio normale ci sono cambi di setpoint, che spiegano almeno in parte le segnalazioni nelle finestre pulite (non verificato).

## 4. Piattaforma e spesa

Droplet creata verso le 08:09Z. È rimasta ferma circa 30 minuti per una caduta della connessione durante la creazione; poi un primo upload lento è stato ripreso e completato su un solo stream (tutti gli sha verificati alle 09:10Z).

Distrutta dal portale alle 09:57Z circa, dopo la copia e la verifica dei risultati (alle 09:44Z il portale aveva chiesto di nuovo il login a Jacopo). Pagina GPU Droplets vuota dopo la distruzione. Accesa circa 1 ora e 48 minuti: **circa 3,6 $** a 1,99 $/h, sopra la stima del disegno (2,5 $) per i 30 minuti persi alla creazione e l'attesa del login.
