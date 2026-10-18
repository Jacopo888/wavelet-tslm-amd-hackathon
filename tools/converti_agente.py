#!/usr/bin/env python3
"""Uscita di ``scripts/eval_v1_rlm.py`` (TimeRLM, una riga jsonl per rollout) -> dump nel formato che legge
``tools/leggi_zeroshot_metropt3.py`` (``records`` con ``id``, ``category``, ``pred``).

- ``example_id`` è l'indice nella cornice di valutazione del loro loader, che rimescola le righe (seme 42): l'id della
  finestra si prende da ``ORDINE.json``, scritto prima di qualunque uscita.
- La risposta si estrae col LORO parser (``parse_structured_pred`` di ``ts_datasets.anomalyxl``, chiave ``anomalies``):
  se il loro parser non la legge, la riga resta senza risposta valida (``pred`` vuoto), come nel loro punteggio.
- Si ferma se mancano righe o se un ``example_id`` si ripete.  Non sovrascrive.

Da eseguire col venv dell'agente, dalla radice del repository TimeRLM:
    python converti_agente.py --jsonl out.jsonl --ordine ORDINE.json --insieme p15 --timerlm <repo> --out agente_direct.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def converti(righe: list[dict], ordine: list[str], parser) -> dict:
    visti: dict[int, dict] = {}
    for r in righe:
        i = r["example_id"]
        if i in visti:
            raise SystemExit(f"FERMO: example_id {i} ripetuto")
        visti[i] = r
    if sorted(visti) != list(range(len(ordine))):
        raise SystemExit(f"FERMO: attesi gli example_id 0..{len(ordine) - 1}, trovati {sorted(visti)}")
    records = []
    for i, idr in enumerate(ordine):
        r = visti[i]
        risposta = r.get("model_answer") or ""
        letta = parser(risposta, frozenset({"anomalies"})) if risposta else None
        pred = ("localize_all_channels:" + json.dumps(letta, sort_keys=True)) if isinstance(letta, dict) else ""
        records.append({"id": idr, "category": "localize_all_channels", "pred": pred, "example_id": i,
                        "num_turns": r.get("num_turns"), "seconds": r.get("seconds"), "error": r.get("error"),
                        "model_answer_coda": risposta[-500:]})
    return {"natura": "agente TimeRLM (eval_v1_rlm.py) convertito; risposta estratta col loro parser", "records": records}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jsonl", required=True, type=Path)
    ap.add_argument("--ordine", required=True, type=Path)
    ap.add_argument("--insieme", required=True, choices=("p15", "a7", "fumo"))
    ap.add_argument("--timerlm", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f"RIFIUTO: {a.out} esiste già")
    sys.path.insert(0, str(a.timerlm / "environments/timeseries_qa"))
    from ts_datasets.anomalyxl import parse_structured_pred  # noqa: E402
    ordine = json.loads(a.ordine.read_text(encoding="utf-8"))[a.insieme]["ordine_example_id"]
    righe = [json.loads(x) for x in a.jsonl.read_text(encoding="utf-8").splitlines() if x.strip()]
    out = converti(righe, ordine, parse_structured_pred)
    a.out.write_bytes((json.dumps(out, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    n_valide = sum(bool(r["pred"]) for r in out["records"])
    print(f"{len(out['records'])} righe, {n_valide} con una risposta letta dal loro parser")
    return 0


if __name__ == "__main__":
    sys.exit(main())
