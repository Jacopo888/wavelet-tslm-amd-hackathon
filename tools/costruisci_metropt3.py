#!/usr/bin/env python3
"""MetroPT-3 nelle righe di AnomalyXL (``diagnostics/20261015/DISEGNO-ZEROSHOT-METROPT3.md`` §3).

Scrive in ``--out-dir``:
- ``metropt3_p15.parquet``: 23 finestre da 131.072 campioni, tutti i 15 segnali rinominati ``ch_00``…``ch_14``;
- ``metropt3_a7.parquet``: le stesse finestre, i 7 segnali analogici rinominati ``ch_00``…``ch_06``;
- ``metropt3_fumo.parquet``: 2 righe con la stessa struttura di P15 e valori di rumore casuale (seme 20261015);
- ``GOLD.json``: i quattro guasti del PDF, le zone sospette e, per finestra, sovrapposizioni e pulizia (lo apre solo il
  lettore: le righe portano la risposta vuota);
- ``COMPOSIZIONE.json``: conteggi e sha.

Serie per indice di campione: i buchi non si riempiono.  Domanda: quella di ``localize_all_channels`` presa da una riga
del val di AnomalyXL, con la L e la C della riga.  Nessuna uscita del modello è coinvolta.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

L = 131072
PASSO = 65536
ANALOGICI = ("TP2", "TP3", "H1", "DV_pressure", "Reservoirs", "Oil_temperature", "Motor_current")
TUTTI = ANALOGICI + ("COMP", "DV_eletric", "Towers", "MPG", "LPS", "Pressure_switch", "Oil_level", "Caudal_impulses")
# PDF del dataset, «Failure Information»: inizio, fine (inclusa al minuto), manutenzione successiva elencata (§3 del disegno)
GUASTI = (
    ("1", "2020-04-18 00:00:00", "2020-04-18 23:59:00", "2020-04-30 12:00:00"),
    ("2", "2020-05-29 23:30:00", "2020-05-30 06:00:00", "2020-06-08 16:00:00"),
    ("3", "2020-06-05 10:00:00", "2020-06-07 14:30:00", "2020-06-08 16:00:00"),
    ("4", "2020-07-15 14:30:00", "2020-07-15 19:00:00", "2020-07-16 00:00:00"),
)
SEME_FUMO = 20261015


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def inizi_finestre(n: int) -> list[int]:
    """Passo PASSO da 0 finché la finestra sta nella serie, più una finestra allineata alla fine se ne resta fuori una coda."""
    if n < L:
        raise ValueError(f"serie di {n} campioni, più corta di una finestra")
    inizi = list(range(0, n - L + 1, PASSO))
    if inizi[-1] + L < n:
        inizi.append(n - L)
    return inizi


def indice(tempi: np.ndarray, t: str, dopo: bool) -> int:
    """Primo campione con timestamp >= t (dopo=False) o > t (dopo=True)."""
    x = np.datetime64(t)
    return int(np.searchsorted(tempi, x, side="right" if dopo else "left"))


def sovrapposti(a0: int, a1: int, b0: int, b1: int) -> int:
    return max(0, min(a1, b1) - max(a0, b0))


def gold(tempi: np.ndarray, inizi: list[int]) -> dict:
    guasti = []
    for nome, t0, t1, man in GUASTI:
        s, e = indice(tempi, t0, False), indice(tempi, t1, True)
        z = indice(tempi, man, True)
        if not 0 <= s < e <= len(tempi):
            raise ValueError(f"guasto {nome}: indici [{s}, {e}) fuori dalla serie")
        guasti.append({"guasto": nome, "inizio": t0, "fine": t1, "manutenzione_successiva": man, "start": s, "end": e,
                       "campioni": e - s, "zona_sospetta": [s, z],
                       "primo_campione": str(tempi[s]), "ultimo_campione": str(tempi[e - 1])})
    finestre = []
    for k, a in enumerate(inizi):
        b = a + L
        dentro = []
        for g in guasti:
            ov = sovrapposti(a, b, g["start"], g["end"])
            if ov:
                dentro.append({"guasto": g["guasto"], "intero": a <= g["start"] and g["end"] <= b, "start": max(a, g["start"]) - a,
                               "end": min(b, g["end"]) - a, "campioni": ov})
        tocca_zona = any(sovrapposti(a, b, *g["zona_sospetta"]) for g in guasti)
        finestre.append({"finestra": k, "inizio_indice": a, "fine_indice": b, "primo_timestamp": str(tempi[a]),
                         "ultimo_timestamp": str(tempi[b - 1]), "guasti": dentro, "pulita": not tocca_zona})
    return {"guasti": guasti, "finestre": finestre}


def domanda_lac(val: Path) -> tuple[str, dict]:
    import pyarrow.parquet as pq
    righe = pq.read_table(val, columns=["id", "tier", "category", "length", "n_channels", "question", "semantic_class",
                                        "n_channels_a", "n_channels_b", "coupling_kind", "coupling_lag"]).to_pylist()
    lac = [r for r in righe if r["category"] == "localize_all_channels"]
    if not lac:
        raise SystemExit("nessuna riga localize_all_channels nel val")
    r = lac[0]
    coda = f"(Here L = {r['length']}, C = {r['n_channels']}.)"
    if not r["question"].endswith(coda) or r["question"].count(coda) != 1:
        raise SystemExit(f"la domanda non finisce con {coda!r}")
    modello = r["question"][: -len(coda)] + "(Here L = {L}, C = {C}.)"
    for x in lac:  # la stessa domanda in tutte le righe, a parte L e C
        if x["question"] != modello.replace("{L}", str(x["length"])).replace("{C}", str(x["n_channels"])):
            raise SystemExit(f"{x['id']}: domanda diversa dal modello")
    return modello, r


def riga(idr: str, valori: list[np.ndarray], modello: str, tipo: dict) -> dict:
    C = len(valori)
    return {"id": idr, "tier": tipo["tier"], "category": "localize_all_channels", "length": L, "n_channels": C,
            "n_channels_a": tipo["n_channels_a"], "n_channels_b": tipo["n_channels_b"],
            "question": modello.replace("{L}", str(L)).replace("{C}", str(C)), "options": [],
            "answer": "localize_all_channels:" + json.dumps({"_L": L, "anomalies": []}, sort_keys=True),
            "semantic_class": f"localize_all_channels_K0_L{L}", "coupling_kind": tipo["coupling_kind"],
            "coupling_lag": tipo["coupling_lag"], "injection_kinds": [], "injection_channels": [], "injection_starts": [],
            "injection_ends": [], "channel_names": [f"ch_{i:02d}" for i in range(C)],
            "channel_values": [v.astype(np.float32).tolist() for v in valori], "seed": 0}


def scrivi(righe: list[dict], schema, p: Path) -> str:
    import pyarrow as pa
    import pyarrow.parquet as pq
    if p.exists():
        raise SystemExit(f"RIFIUTO: {p} esiste già")
    pq.write_table(pa.Table.from_pylist(righe, schema=schema), p)
    p.chmod(0o444)
    return sha(p)


def main(argv=None) -> int:
    import pyarrow.csv as pcsv
    import pyarrow.parquet as pq
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True, type=Path)
    ap.add_argument("--sha-csv", required=True)
    ap.add_argument("--schema-di", required=True, type=Path, help="val.parquet di AnomalyXL")
    ap.add_argument("--out-dir", required=True, type=Path)
    a = ap.parse_args(argv)
    if sha(a.csv) != a.sha_csv:
        raise SystemExit("RIFIUTO: sha del CSV diverso da quello dichiarato")
    a.out_dir.mkdir(parents=True, exist_ok=True)
    for f in ("GOLD.json", "COMPOSIZIONE.json"):
        if (a.out_dir / f).exists():
            raise SystemExit(f"RIFIUTO: {a.out_dir / f} esiste già")
    t = pcsv.read_csv(a.csv)
    nomi = t.column_names
    if tuple(nomi[2:]) != TUTTI or nomi[1] != "timestamp":
        raise SystemExit(f"colonne inattese: {nomi}")
    tempi = np.array(t.column("timestamp").to_pylist(), dtype="datetime64[s]")
    if not np.all(np.diff(tempi) > np.timedelta64(0, "s")):
        raise SystemExit("timestamp non strettamente crescenti")
    serie = {c: np.asarray(t.column(c).to_numpy(), dtype=np.float64) for c in TUTTI}
    for c, v in serie.items():
        if not np.all(np.isfinite(v)):
            raise SystemExit(f"{c}: valori non finiti")
    n = len(tempi)
    inizi = inizi_finestre(n)
    modello, tipo = domanda_lac(a.schema_di)
    schema = pq.read_schema(a.schema_di).remove_metadata()
    p15 = [riga(f"metropt3-p15-w{k:02d}", [serie[c][i:i + L] for c in TUTTI], modello, tipo) for k, i in enumerate(inizi)]
    a7 = [riga(f"metropt3-a7-w{k:02d}", [serie[c][i:i + L] for c in ANALOGICI], modello, tipo) for k, i in enumerate(inizi)]
    rng = np.random.default_rng(SEME_FUMO)
    fumo = [riga(f"metropt3-fumo-{k}", [np.cumsum(rng.standard_normal(L)) for _ in TUTTI], modello, tipo) for k in range(2)]
    g = gold(tempi, inizi)
    out = {"natura": "MetroPT-3 nelle righe di localize_all_channels; risposte vuote; gold in GOLD.json", "csv_sha256": a.sha_csv,
           "campioni": n, "L": L, "passo": PASSO, "inizi": inizi, "finestre": len(inizi),
           "canali_p15": list(TUTTI), "canali_a7": list(ANALOGICI),
           "metropt3_p15": {"righe": len(p15), "sha256": scrivi(p15, schema, a.out_dir / "metropt3_p15.parquet")},
           "metropt3_a7": {"righe": len(a7), "sha256": scrivi(a7, schema, a.out_dir / "metropt3_a7.parquet")},
           "metropt3_fumo": {"righe": len(fumo), "sha256": scrivi(fumo, schema, a.out_dir / "metropt3_fumo.parquet"),
                             "seme": SEME_FUMO},
           "finestre_con_un_guasto_intero": sum(any(x["intero"] for x in f["guasti"]) for f in g["finestre"]),
           "finestre_che_toccano_un_guasto": sum(bool(f["guasti"]) for f in g["finestre"]),
           "finestre_pulite": sum(f["pulita"] for f in g["finestre"]),
           "domanda_modello": modello}
    for f, x in (("GOLD.json", g), ("COMPOSIZIONE.json", out)):
        (a.out_dir / f).write_bytes((json.dumps(x, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        (a.out_dir / f).chmod(0o444)
    print(json.dumps({k: v for k, v in out.items() if k != "domanda_modello"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
