# L'agente TimeRLM di Nico su MetroPT-3 (confronto dichiarato, 15/10/2026)

**Stato:** CONGELATO il 15/10 alle 17:48Z, prima di qualunque uscita dell'agente. Scritto alle 17:40Z; aggiunto solo il §6 con le versioni fissate dal job 34408 (nessun modello eseguito). Ordine di Jacopo del 15/10: «sì, parti dall'agente di Nico».

**Natura:** accanto allo zero-shot di C1 (`DISEGNO-ZEROSHOT-METROPT3.congelato-d131cf78.md`): **stesse righe, stesse misure, stesso lettore, stesse regole di lettura.** Distribuzione diversa per tutti e due; quattro guasti: caso di studio, non conferma.

## 1. La domanda

L'agente di TimeRLM dopo RL, con lo stesso backbone di C1 (Qwen3.5-4B), che legge la serie intera col codice in una sandbox, trova i guasti documentati di MetroPT-3 e tace nelle finestre senza guasti? Con quanti turni e quanto tempo per finestra, contro una chiamata di C1?

## 2. Sistema, così come è rilasciato

- **Pesi:** `nz00shuuuu/TimeRLM-RL-Qwen-3.5-4B`, alla revisione scritta nel §6 (letta dall'API di Hugging Face prima del download), con gli sha256 dei file.
- **Protocollo:** `scripts/eval_v1_rlm.py` del repository ufficiale `OpenTSLM/TimeRLM` al commit `31fcd847`, senza modifiche (il job rifiuta un albero modificato): prompt v1, al più 15 turni, `RLM_MAX_OUTPUT` 8.192, riassunto a 45.000 token, timeout di esecuzione 300 s, nessuna ricorsione.
- **Servizio:** vLLM con i parametri del loro `REPRODUCE.md` (`--enable-auto-tool-choice --tool-call-parser qwen3_coder --max-model-len 65536 --gpu-memory-utilization 0.85`), su una L4.
- **Caricatore:** la loro classe `anomalyxl` in modalità `rlm`: la serie intera va nel file `context.json` della sandbox, senza decimazione.
- **Domanda:** quella delle righe, identica a quella data a C1. La loro nota di sistema dice «Multi-channel questions present 16 channels named `ch_00..ch_15`»; qui i canali sono 15 (o 7). La si lascia com'è: la stessa nota chiede di leggere i nomi veri dei canali dai dati.

## 3. Righe e risposta

- Le stesse di C1: `metropt3_p15` (primaria) e `metropt3_a7` (accanto), 23 finestre ciascuna, risposta vuota, gold in `GOLD.json`.
- Il loro caricatore rimescola le righe col seme 42: l'ordine è in `datasets/metropt3/agente/ORDINE.json` (sha 96e38b8a), scritto prima di qualunque uscita.
- **La risposta si estrae col loro parser** (`parse_structured_pred`, chiave `anomalies`), poi passa al nostro lettore (`tools/converti_agente.py`). Una risposta che il loro parser non legge resta senza intervalli e si conta come non valida.

## 4. Misure e letture

- **Le stesse del documento di C1** (§4 e §5): M1, M1-centro, M1-caso, M2, M3, M4, formato, esiti A–D per P15, A7 accanto.
- **In più, il costo:** turni per finestra, secondi per finestra, rollout chiusi per limite di turni o per timeout.
- **Confronto con C1:** si scrivono fianco a fianco i conteggi (guasti rilevati su 4, finestre pulite con segnalazioni su 15) e il costo. Nessun CI appaiato: quattro eventi non lo reggono. Si può scrivere «X ne trova più di Y» solo come conteggio, non come differenza dimostrata.

## 5. Prima del lotto

1. **Fumo:** un rollout su una riga di rumore con la stessa struttura (`metropt3_fumo`, C = 15, L = 131.072). Controllo meccanico: rollout chiuso, nessun errore. Se non passa, gli insiemi veri non partono.
2. **Convertitore** provato su un jsonl sintetico prima della lettura.

## 6. Versioni fissate prima del fumo (job 34408, 15/10 17:24–17:44Z, solo CPU)

| Che cosa | Valore |
|---|---|
| Pesi | `nz00shuuuu/TimeRLM-RL-Qwen-3.5-4B`, revisione `2b9760d62140647dbff02899a4aad99c13dfce07`, 13 file, 8,5 GB; architettura `Qwen3_5ForConditionalGeneration` |
| Manifest degli sha256 | `hf/TimeRLM-RL-Qwen-3.5-4B.SHA256SUMS`, sha 97acfb4b…; il job li ricontrolla tutti prima di servire |
| vLLM | 0.31.0 (torch 2.13.0+cu130, CUDA 13.0, transformers 5.17.0), in `venv_vllm` |
| Ambiente dell'agente | `venv_agente`: `rlm-harness` del commit 31fcd847 più pandas, datasets, huggingface-hub; `mcp` fissato a 1.23.3 perché la 2.3.0 ha rinominato `streamablehttp_client` e il pacchetto `rlm` non si importa |
| TimeRLM | `OpenTSLM/TimeRLM` al commit `31fcd847b7cb37a1f1e6859b1dca7973ed0eae74`, senza modifiche |
| Job | `pbs/agente_metropt3.pbs`: una L4 con almeno 20.000 MiB liberi, vLLM sulla porta 18000 + (numero del job mod 1000), concorrenza 4 |

**Se gira sull'AMD Developer Cloud** invece che sulla L4, prima del fumo si aggiunge qui l'immagine, la versione di vLLM per ROCm e lo sha dei pesi scaricati; il resto non cambia.
