# Zero-shot su MetroPT-3: C1 e l'agente TimeRLM di Nico (risultati, 15/10/2026)

**Dicitura obbligatoria: distribuzione diversa; segnali industriali reali; zero-shot; quattro guasti, caso di studio, non conferma.**

**Letture dichiarate prima dei dati:** C1 `DISEGNO-ZEROSHOT-METROPT3.congelato-6c61e315.md` (prima versione d131cf78, aggiunto il §9 sulla piattaforma AMD); agente `DISEGNO-AGENTE-TIMERLM-METROPT3.congelato-41abe9af.md` (prima versione 27b1fe39, aggiunto il §7). Una sola lettura per insieme, il 15/10 alle 19:46:58Z, con `tools/leggi_zeroshot_metropt3.py` (2dfa6a76, provato su dump sintetici).

## 1. Esito in tre righe

1. **Esito B per tutti e due, sulla primaria (15 segnali): «segnalano quasi ovunque: le rilevazioni non si leggono come prova».** C1 segnala qualcosa in 15 finestre pulite su 15, l'agente in 12 su 15.
2. **Le rilevazioni sono al livello del caso.** C1 tocca 2 guasti su 4 dove a caso ne toccherebbe 2,31; l'agente 2 su 4 contro 2,33.
3. **Nessuno dei due, a zero-shot, trova le perdite d'aria documentate di MetroPT-3.** Lo fanno in modi diversi: C1 emette molti intervalli corti, l'agente pochi intervalli lunghi giorni.

## 2. Popolazione

23 finestre da 131.072 campioni (circa 15 giorni a 10 s), passo metà finestra. 7 finestre contengono per intero uno dei 4 guasti; 15 sono pulite (nessuna sovrapposizione con le zone dall'inizio del guasto alla manutenzione). Gold in `GOLD.json` (25317206).

## 3. Misure dichiarate

| Misura | C1, 15 segnali | Agente, 15 segnali | C1, 7 analogici | Agente, 7 analogici |
|---|---|---|---|---|
| **Esito della regola** | **B** | **B** | B (accanto) | B (accanto) |
| M1, guasti toccati su 4 | 2 (1 e 4) | 2 (2 e 4) | 0 | 3 (1, 2 e 3) |
| M1 attesi a caso | 2,31 | 2,33 | 2,10 | 3,01 |
| M1-centro (centro dentro il guasto) | 2 | 0 | 0 | 0 |
| **M2, finestre pulite con segnalazioni** | **15 / 15** [0,80, 1,00] | **12 / 15** [0,55, 0,93] | 15 / 15 | 11 / 15 [0,48, 0,89] |
| M3, intervalli che toccano una zona sospetta | 22 / 235 | 4 / 23 | 15 / 143 | 4 / 24 |
| M4, IoU sulle 7 finestre col guasto | da 0 a 0,061 | da 0 a 0,018 | 0 ovunque | da 0 a 0,15 |
| Risposte valide | 23 / 23 | 20 / 23 | 23 / 23 | 21 / 23 |
| Intervalli per finestra (mediana) | 10 | 1 | 6 | 1 |
| Lunghezza di un intervallo (mediana) | 154 campioni (circa 26 min) | 30.393 campioni (circa 3,5 giorni) | 159 | 116 |
| Quota della finestra coperta (media) | 1,2 % | 49 % | 0,7 % | 34 % |

Tra parentesi quadre: intervallo di Wilson al 95 %.

- **M1 non dice nulla qui:** con M2 alto la regola dichiarata chiude a B, e le rilevazioni osservate coincidono con quelle attese a caso. Per l'agente sui 15 segnali la probabilità a caso dei guasti 2 e 4 è 1,0: i suoi intervalli coprono metà della finestra e toccano qualunque cosa.
- **C1 si comporta come sul multicanale di AnomalyXL:** elenca molti eventi brevi su quasi tutti i canali (tutti e 15 citati). Sui segnali reali le commutazioni del compressore somigliano alle anomalie sintetiche, e il lettore le segnala.
- **L'agente sui 7 analogici** tocca 3 guasti su 4, ma a caso ne toccherebbe 3,01, e segnala in 11 finestre pulite su 15.

## 4. Costo

| | C1 | Agente |
|---|---|---|
| Chiamate per finestra | 1 | mediana 7 turni (da 4 a 15; uno solo al tetto di 15) |
| Tempo per finestra | circa 32 s su P15 e 22 s su A7 (totali 736,7 s e 499,1 s), compilazione compresa | mediana 315 s su P15 e 235 s su A7, con 4 rollout in parallelo |
| Errori | 0 | 0 errori di esecuzione; 3 e 2 risposte che il loro parser non legge |

Le due esecuzioni hanno diviso la stessa MI300X: i tempi non sono una misura di latenza in produzione.

## 5. Si può dire / non si può dire

| Affermazione | Lettura |
|---|---|
| «A zero-shot C1 trova i guasti di MetroPT-3» | **no**: esito B, rilevazioni al caso, falsi allarmi in 15 finestre pulite su 15 |
| «A zero-shot l'agente di Nico trova i guasti di MetroPT-3» | **no**: esito B, rilevazioni al caso, falsi allarmi in 12 su 15 |
| «L'agente è meglio di C1» o il contrario | **non si può dire**: tutti e due al caso, su 4 eventi |
| «C1 costa una chiamata, l'agente circa 7 turni e qualche minuto per finestra» | **sì**, misurato qui, su GPU condivisa |
| «C1 risponde sempre nel formato richiesto» | **sì**: 23 su 23 in tutti e due gli insiemi |
| «Il modello non può servire su dati industriali» | **non si può dire**: è zero-shot. Un adattamento con etichette reali non è stato provato, e MetroPT-3 ha solo 4 guasti |
| «I guasti sono visibili nei segnali come annotati» | **non verificato**: il gold è un intervallo di sistema dai rapporti dell'azienda, senza canali |
| «Il risultato vale su L4» | **non letto**: le L4 del Polimi erano ferme; la piattaforma è la MI300X (§9 del disegno di C1) |

## 6. Esecuzione e artefatti

- **Macchina:** AMD Developer Cloud, MI300X ×1 on-demand (1,99 $/h), creata il 15/10 alle 18:23Z e distrutta alle 19:44Z circa, dopo aver copiato e verificato i risultati.
- **Fumo:** C1 sulle 2 righe di rumore, superato alle 18:45:22Z (un primo tentativo si era fermato prima di generare, per un config non scritto; corretto lo script e rifatto). Agente: un rollout, 7 turni, 102 s, superato alle 18:39:22Z.
- **Script:** `tools/esegui_c1_amd.sh` (ae2ea68f), `tools/esegui_agente_amd.sh` (a0472ceb), `tools/prepara_amd.sh`, `tools/prepara_c1_amd.sh`, `tools/converti_agente.py` (958a60c7).

| File | sha |
|---|---|
| `amd/c1/out/lotto_p15/c1_direct.json` | d0f40de0 |
| `amd/c1/out/lotto_a7/c1_direct.json` | c03709e2 |
| `amd/out/agente_p15/agente.jsonl` / `agente_direct.json` | 21c9ea0f / c40a7d23 |
| `amd/out/agente_a7/agente.jsonl` / `agente_direct.json` | 24c9bb5f / a0affdcf |
| `lettura/lettura_c1_p15.json`, `lettura_c1_a7.json` | 97ce9de8, 475f2d22 |
| `lettura/lettura_agente_p15.json`, `lettura_agente_a7.json` | 26644324, 0d2ccd69 |
| `amd/risultati.tgz` (tutto ciò che è uscito dalla macchina, senza le serie) | 0d63e559 |

## 7. Aggiunta del 15/10 sera: C1 a un canale alla volta

**Lettura dichiarata prima dei dati:** `DISEGNO-LOCALIZE-CANALE-METROPT3.congelato-4b0dc596.md`. Domanda nuova sulle stesse 23 finestre: `localize` su ciascuno dei 7 canali analogici, cioè il compito su cui C1 è allenato a rispondere anche «assente». 161 righe, una sola lettura il 15/10 alle 20:29:57Z con `tools/leggi_localize_canale.py` (3d8164cf, provato su dump sintetici). Seconda MI300X (609474246), accesa dalle 20:07Z a circa le 20:30Z; fumo superato (le 2 righe di rumore: «assente»).

| Misura | C1 multicanale (15 segnali, §3) | **C1 a un canale (7 analogici)** |
|---|---|---|
| **Esito della regola** | B | **B: «segnala quasi ovunque»** |
| Risposte «assente» | 0 liste vuote su 23 | **2 su 161** (entrambe su Motor_current) |
| M1, guasti toccati su 4 | 2 (a caso 2,31) | **1 (a caso 2,15)**: il guasto 3, nella finestra 13 |
| M1-centro | 2 | 0 |
| **M2, finestre pulite con segnalazioni** | 15 / 15 | **15 / 15**: in 13 lo segnalano tutti e 7 i canali |
| M3 | 22 / 235 | 18 / 159 |
| M4, IoU massima | 0,061 | 0,004 |
| Lunghezza di un intervallo | mediana 154 campioni | mediana 158 (da 102 a 174) |

Per canale, ciascuno da solo: M2 di 15 su 15 per sei canali e 13 su 15 per Motor_current; M1 di 0 su 4 per sei canali e 1 su 4 per Oil_temperature (a caso 0,44). Tutte le 161 risposte sono valide.

- **Si può dire:** anche a un canale alla volta, sul compito che prevede «assente», C1 risponde «presente» in 159 righe su 161, con un intervallo di circa 158 campioni, cioè della durata tipica di un'anomalia sintetica del training. I guasti non li tocca oltre il caso.
- **È lo stesso comportamento visto su ECG** (LTAF: 0 «assente» su 36 negativi, `PUNTO-DELLA-LINEA-20261008.md` §3.9): sui segnali reali la decisione di presenza non trasferisce.
- **Non si può dire** perché, né se un adattamento con etichette reali lo correggerebbe.

| File | sha |
|---|---|
| `amd2/c1/out/lotto_loc/c1_direct.json` | 60397b36 |
| `amd2/c1/out/lotto_locfumo/c1_direct.json` | d7a60bca |
| `lettura/lettura_c1_loc_canale.json` | 39b0bb59 |
| `amd2/risultati2.tgz` | a03429e6 |
| `tools/costruisci_loc_canale.py`, `porta_loc.py`, `esegui_loc_amd.sh` | 93d26a9d, 8de11c84, 619ef698 |

## 8. Aggiunta del 15/10 notte: pre-processing (A indicatori di salute, B canali alla AnomalyXL, C indicatori adattati)

**Lettura dichiarata prima dei dati:** `DISEGNO-INDICATORI-METROPT3.congelato-c9a19ea1.md`. Griglia ogni 2 minuti; ogni punto calcolato sui 60 minuti precedenti; 15 finestre da 16.384 punti, di cui 7 con un guasto intero e 7 pulite. `localize` a un canale. Una sola lettura per variante, il 15/10 alle 21:33:13Z. Terza MI300X (609488812), accesa dalle 21:10Z a circa le 21:33Z; fumo superato (le 2 righe di rumore: «assente»).

**Normalizzazione:** il modello normalizza ogni canale per mediana e MAD, una trasformazione che non cambia se si sposta o si ri-scala il canale, e nel prompt non entra nessuna statistica. Portare i canali a media 0 e deviazione 1 come il generatore di AnomalyXL avrebbe dato lo stesso ingresso. Per questo B e C cambiano la forma del segnale (ranghi verso una normale, rumore 0,1), non la scala.

| Misura | A, 6 indicatori grezzi | B, 7 analogici adattati | C, 6 indicatori adattati |
|---|---|---|---|
| **Esito della regola** | **B** | **B** | **B** |
| Risposte «assente» | 1 su 90 | 0 su 105 | 0 su 90 |
| M2, finestre pulite con segnalazioni | 7 / 7 | 7 / 7 | 7 / 7 |
| M1, guasti toccati su 4 (a caso) | 2 (1,82) | 3 (1,99) | **4 (1,78)** |
| M1-centro | 2 | 2 | **4** |
| M3, intervalli che toccano una zona sospetta | 17 / 89 | 16 / 105 | 12 / 90 |
| M4, IoU massima | 0,167 | 0,169 | 0,162 |
| Lunghezza di un intervallo (mediana) | 158 punti | 139 | 140,5 |
| Somma sui canali dei guasti toccati (attesi a caso) | 5 (2,22) | 5 (2,53) | 5 (2,16) |

- **Esito B in tutte e tre:** il modello risponde «presente» praticamente sempre (1 «assente» su 285 righe) e segnala in tutte le 7 finestre pulite. Il pre-processing ha tolto i cicli e i gradini (§6 del disegno: B e C hanno la forma di AnomalyXL), ma **non ha cambiato la decisione di presenza**.
- **Descrittivo, non una prova:** in C i centri degli intervalli cadono dentro tutti e 4 i guasti, e sommando i canali le rilevazioni sono circa il doppio di quelle attese a caso in tutte e tre le varianti. Con 4 eventi, canali correlati fra loro e un modello che segnala anche dove non c'è nulla, la regola dichiarata non permette di leggerlo come capacità; e non si sceglie C a posteriori.
- **Lunghezze:** come sui segnali grezzi, l'intervallo resta di circa 140–160 punti, la durata tipica di un'anomalia del training, qualunque sia il guasto (da 136 a 1.437 punti).
- **Si può dire:** a zero-shot, né il segnale grezzo, né gli indicatori di salute, né la forma «alla AnomalyXL» fanno dire «assente» a C1 su MetroPT-3. **Non si può dire:** che un adattamento con etichette reali non funzionerebbe, né che la localizzazione dentro le finestre col guasto sia al caso o oltre il caso (4 eventi).

| File | sha |
|---|---|
| `amd3/c1/out/lotto_hia/c1_direct.json`, `lotto_hib`, `lotto_hic` | 068710f2, 98dc4882, 5510f807 |
| `amd3/c1/out/lotto_hifumo/c1_direct.json` | ab9a4030 |
| `lettura/lettura_c1_hia.json`, `hib`, `hic` | ca71d67e, 465a90c1, d19dc114 |
| `amd3/risultati3.tgz` | 58360939 |
| `tools/costruisci_indicatori.py`, `porta_insiemi.py`, `esegui_hi_amd.sh`, `leggi_localize_canale.py` | 7dea8547, 04ca5ead, a3b10e96, c95b6f3c |
