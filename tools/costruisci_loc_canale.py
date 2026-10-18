#!/usr/bin/env python3
"""MetroPT-3 a un canale alla volta (``diagnostics/20261015/DISEGNO-LOCALIZE-CANALE-METROPT3.md`` §3).

Dalle 23 righe di ``metropt3_a7.parquet`` (7 canali analogici, ``ch_00``…``ch_06``) scrive 161 righe di ``localize``,
una per finestra e canale, col canale rinominato ``ch_00`` e la domanda di localize presa dal val di AnomalyXL.
Risposta cieca (``present: false``), liste ``injection_*`` vuote.  In più 2 righe di fumo (rumore, seme 20261015).
Non sovrascrive.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

L = 131072
CANALI = ("TP2", "TP3", "H1", "DV_pressure", "Reservoirs", "Oil_temperature", "Motor_current")
SEME_FUMO = 20261015


def domanda_localize(val_righe: list[dict]) -> tuple[str, dict]:
    loc = [r for r in val_righe if r["category"] == "localize"]
    if not loc:
        raise SystemExit("nessuna riga di localize nel val")
    r = loc[0]
    coda = f"(Here L = {r['length']}.)"
    if not r["question"].endswith(coda):
        raise SystemExit(f"la domanda di localize non finisce con {coda!r}")
    modello = r["question"][: -len(coda)] + "(Here L = {L}.)"
    for x in loc:
        if x["question"] != modello.replace("{L}", str(x["length"])):
            raise SystemExit(f"{x['id']}: domanda di localize diversa dal modello")
    return modello, r


def riga(idr: str, valori, modello: str, tipo: dict) -> dict:
    return {"id": idr, "tier": tipo["tier"], "category": "localize", "length": L, "n_channels": 1,
            "n_channels_a": tipo["n_channels_a"], "n_channels_b": tipo["n_channels_b"],
            "question": modello.replace("{L}", str(L)), "options": [],
            "answer": "localize:" + json.dumps({"_L": L, "present": False}),
            "semantic_class": f"localize_absent_L{L}", "coupling_kind": tipo["coupling_kind"],
            "coupling_lag": tipo["coupling_lag"], "injection_kinds": [], "injection_channels": [],
            "injection_starts": [], "injection_ends": [], "channel_names": ["ch_00"],
            "channel_values": [list(np.asarray(valori, dtype=np.float32).tolist())], "seed": 0}


def main(argv=None) -> int:
    import pyarrow as pa
    import pyarrow.parquet as pq
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a7", required=True, type=Path)
    ap.add_argument("--sha-a7", required=True)
    ap.add_argument("--val", required=True, type=Path, help="val.parquet di AnomalyXL (domanda e schema)")
    ap.add_argument("--out-dir", required=True, type=Path)
    a = ap.parse_args(argv)
    if hashlib.sha256(a.a7.read_bytes()).hexdigest() != a.sha_a7:
        raise SystemExit("RIFIUTO: sha del parquet A7")
    a.out_dir.mkdir(parents=True, exist_ok=True)
    nomi = ("metropt3_loc.parquet", "metropt3_locfumo.parquet", "COMPOSIZIONE_LOC.json")
    for f in nomi:
        if (a.out_dir / f).exists():
            raise SystemExit(f"RIFIUTO: {a.out_dir / f} esiste già")
    schema = pq.read_schema(a.val).remove_metadata()
    modello, tipo = domanda_localize(pq.read_table(a.val, columns=[
        "id", "tier", "category", "length", "question", "n_channels_a", "n_channels_b", "coupling_kind", "coupling_lag"]).to_pylist())
    a7 = pq.read_table(a.a7).to_pylist()
    if len(a7) != 23 or any(r["n_channels"] != 7 or r["length"] != L for r in a7):
        raise SystemExit("A7 inattesa")
    righe, mappa = [], {}
    for r in a7:
        w = r["id"].rsplit("-w", 1)[1]
        for k, nome in enumerate(CANALI):
            idr = f"metropt3-loc-w{w}-{nome}"
            righe.append(riga(idr, r["channel_values"][k], modello, tipo))
            mappa[idr] = {"finestra": int(w), "canale": nome, "indice_in_a7": k}
    rng = np.random.default_rng(SEME_FUMO)
    fumo = [riga(f"metropt3-locfumo-{k}", np.cumsum(rng.standard_normal(L)), modello, tipo) for k in range(2)]
    out = {"natura": "localize a un canale da metropt3_a7; risposte cieche", "domanda_modello": modello, "canali": list(CANALI)}
    for nome, rr in (("metropt3_loc.parquet", righe), ("metropt3_locfumo.parquet", fumo)):
        p = a.out_dir / nome
        pq.write_table(pa.Table.from_pylist(rr, schema=schema), p)
        p.chmod(0o444)
        out[nome] = {"righe": len(rr), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    out["mappa"] = mappa
    (a.out_dir / "COMPOSIZIONE_LOC.json").write_bytes((json.dumps(out, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    print(json.dumps({k: v for k, v in out.items() if k not in ("mappa", "domanda_modello")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
