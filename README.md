# Wavelet-TSLM on AMD Instinct MI300X — AMD Developer Hackathon: ACT III

Track: **Intelligent Industry** · Team PoliMi · Jacopo D'Abundo

Wavelet-TSLM is a Time Series Language Model: a Qwen3.5-4B (LoRA) that reads long, multichannel time series through a
Haar-wavelet encoder and returns where each anomaly starts and ends, in a single call. It was trained only on synthetic
anomalies (the AnomalyXL benchmark from the ETH Zürich TimeRLM work). This repository holds what we measured during the
hackathon, the scripts to reproduce it, and the pitch material.

**What is not here:** the model checkpoint and training code (the research repositories are private), and the datasets
(download links below). There is **no live demo application**: the demo is the video and the reproducible reading scripts.

## Results (all numbers come from files in this repository or from the cited paper)

| What | Result |
|---|---|
| AnomalyXL test set, one call, no zoom | localize 0.61, classify 0.33, multichannel 0.75 (official scorer); baselines in Table 1 of the TimeRLM paper (arXiv 2608.03391): best TSLM 0.32 / 0.07 / 0.23. We do **not** win on magnitude (0.31 vs 0.82, Toto 32B) or lead-lag (0.25 vs 0.35–0.56). |
| vs the TimeRLM agent (Qwen3.5-4B after RL, published) | localize 0.61 vs 0.54, multichannel 0.75 vs 0.24; lower on classify, magnitude, lead-lag. Agents backed by GPT-5.5 score higher. |
| Zero-shot on HAI 21.03 (real industrial control testbed, 50 attacks, 38 windows of 9 h × 16 channels) | intervals touch **34 / 50** attacks vs 6.6 expected at random (p ≈ 1e-19); 60 % of the intervals land on an attack vs 4.5 % at random. **But** it flags all 18 attack-free windows: it ranks anomalous stretches, it is not an alarm. Regime "B" of our pre-declared rule. |
| Zero-shot on MetroPT-3 (4 slow air-leak failures) | did not transfer: five different readings, all regime "B" (flags every window). |
| Cost | 4 MI300X droplets on the AMD Developer Cloud, under $10 in total. |
| Attention memory | FlexAttention (Triton) padded to 512: 65.4 GiB → 3.5 GiB at L = 16,384, forward + backward (measured in our September backend gate on MI300X with ROCm 6.4; that report is not included here). |

## Layout

- `diagnostics/20261015/` — MetroPT-3: frozen designs (`*.congelato-<sha>.md`, written before any model output),
  results (`RISULTATI-ZEROSHOT-METROPT3.md`), readings (`lettura/`).
- `diagnostics/20261016/` — HAI 21.03: frozen design, results (`RISULTATI-ZEROSHOT-HAI2103.md`), readings.
- `tools/` — row builders, readers, gate patchers and the AMD run scripts. `tests/` — reader tests (`pytest`).
- `datasets_hai/` — gold labels and composition of the HAI windows (the parquet rows are rebuilt with `tools/costruisci_hai.py`).
- `deck/` — pitch deck (PPTX/PDF, `build.js`); `video/` — script to build the voiced video, slide texts, the video.

## Method in one paragraph

Each reading was declared and frozen (file name carries its sha256) before the model produced any output; one reading
per set; outcome rule fixed in advance (A: finds the events and stays quiet on clean windows; B: flags almost everywhere;
C: finds nothing). Chance level for "events touched" is computed analytically for the same intervals placed at random.

## Data

- HAI 21.03: https://github.com/icsdataset/hai (CC BY-SA 4.0), Shin et al., CSET '21.
- MetroPT-3: UCI Machine Learning Repository.
- AnomalyXL / TimeRLM: arXiv 2608.03391.

## Reproduce a reading

```
pip install pyarrow numpy pytest
python tools/costruisci_hai.py --dir <hai-21.03> ...   # see the docstring
python tools/leggi_hai.py --modo mc --dump <dump.json> --gold datasets_hai/GOLD_HAI.json --composizione datasets_hai/COMPOSIZIONE_HAI.json --out out.json
pytest tests
```

The model dumps themselves need the checkpoint, which is not published here.
