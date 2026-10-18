#!/usr/bin/env python3
"""Ispezione di HAI 21.03 prima del disegno (nessun modello).

Per file: righe, passo, valori non finiti.  Per attacco (solo file di test): inizio, fine, durata e processi.
Per canale, SOLO sui file di training (nessuna etichetta): quota di passi piatti, quota di valori distinti, quota di
salti oltre 5 MAD dei passi; e, sulle finestre previste (test e training), in quante la MAD del canale è nulla.

    python ispeziona_hai.py --dir data/hai2103 --out ispezione_hai.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

L = 32768
PASSO_TEST = 16384
PASSO_TRAIN = 65536
TEST = ("test1", "test2", "test3", "test4", "test5")
TRAIN = ("train1", "train2", "train3")


def inizi(n: int, passo: int) -> list[int]:
    if n < L:
        raise ValueError(f"serie di {n} campioni, più corta di una finestra")
    x = list(range(0, n - L + 1, passo))
    if x[-1] + L < n:
        x.append(n - L)
    return x


def leggi(p: Path):
    import pyarrow.csv as pc
    t = pc.read_csv(p)
    tm = np.array(t.column("time").to_pylist(), dtype="datetime64[s]")
    canali = [c for c in t.column_names if c != "time" and not c.startswith("attack")]
    X = {c: np.asarray(t.column(c).to_numpy(), dtype=np.float64) for c in canali}
    lab = {c: np.asarray(t.column(c).to_numpy()) for c in t.column_names if c.startswith("attack")}
    return tm, canali, X, lab


def runs(a: np.ndarray) -> list[tuple[int, int]]:
    e = np.diff(np.r_[0, (a > 0).astype(np.int8), 0])
    return list(zip(np.where(e == 1)[0].tolist(), np.where(e == -1)[0].tolist()))


def mad(v: np.ndarray) -> float:
    return float(np.median(np.abs(v - np.median(v))))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)
    file_info, attacchi, canali_ref = {}, [], None
    forma = {}
    mad_nulla: dict[str, int] = {}
    n_finestre = 0
    for nome in TEST + TRAIN:
        tm, canali, X, lab = leggi(a.dir / f"{nome}.csv.gz")
        if canali_ref is None:
            canali_ref = canali
            forma = {c: {"piatti": 0, "distinti": [], "salti": 0, "passi": 0} for c in canali}
            mad_nulla = {c: 0 for c in canali}
        if canali != canali_ref:
            raise SystemExit(f"{nome}: colonne diverse")
        passi = np.unique(np.diff(tm).astype(np.int64), return_counts=True)
        nonfin = {c: int((~np.isfinite(v)).sum()) for c, v in X.items() if not np.all(np.isfinite(v))}
        ii = inizi(len(tm), PASSO_TEST if nome in TEST else PASSO_TRAIN)
        file_info[nome] = {"righe": len(tm), "primo": str(tm[0]), "ultimo": str(tm[-1]),
                           "passi_s": dict(zip(map(str, passi[0].tolist()), passi[1].tolist())), "non_finiti": nonfin,
                           "finestre": len(ii), "inizi": ii}
        for i in ii:
            n_finestre += 1
            for c in canali:
                if mad(X[c][i:i + L]) == 0:
                    mad_nulla[c] += 1
        if nome in TEST:
            for s, e in runs(lab["attack"]):
                proc = [p for p in ("P1", "P2", "P3") if lab[f"attack_{p}"][s:e].any()]
                attacchi.append({"file": nome, "start": s, "end": e, "durata_s": e - s, "inizio": str(tm[s]),
                                 "processi": proc})
        else:
            for c in canali:
                v = X[c]
                d = np.diff(v)
                f = forma[c]
                f["piatti"] += int((d == 0).sum())
                f["passi"] += len(d)
                f["distinti"].append(len(np.unique(v)) / len(v))
                md = mad(d)
                f["salti"] += int((np.abs(d) > 5 * md).sum()) if md > 0 else int((d != 0).sum())
    tab = {c: {"piatti": f["piatti"] / f["passi"], "distinti": float(np.mean(f["distinti"])),
               "salti": f["salti"] / f["passi"], "mad_nulla_finestre": mad_nulla[c]} for c, f in forma.items()}
    durate = np.array([x["durata_s"] for x in attacchi])
    out = {"file": file_info, "attacchi": attacchi, "n_attacchi": len(attacchi),
           "durate_s": {"min": int(durate.min()), "mediana": float(np.median(durate)), "max": int(durate.max()),
                        "oltre_256": int((durate > 256).sum())},
           "finestre_totali": n_finestre, "canali": tab}
    a.out.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("n_attacchi", "durate_s", "finestre_totali")}, indent=1))
    for nome, f in file_info.items():
        print(nome, f["righe"], f["primo"], f["ultimo"], f["passi_s"], "finestre", f["finestre"], "non finiti", f["non_finiti"])
    print(f"{'canale':12s} piatti distinti salti mad0")
    for c, v in sorted(tab.items(), key=lambda kv: (kv[1]["mad_nulla_finestre"], kv[1]["piatti"])):
        print(f"{c:12s} {v['piatti']:.3f} {v['distinti']:.4f} {v['salti']:.4f} {v['mad_nulla_finestre']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
