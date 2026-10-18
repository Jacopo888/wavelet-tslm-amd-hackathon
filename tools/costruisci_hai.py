#!/usr/bin/env python3
"""HAI 21.03 nelle righe di AnomalyXL (``diagnostics/20261016/DISEGNO-ZEROSHOT-HAI2103.md`` §2-§3).

Scrive in ``--out-dir``:
- ``hai_mc.parquet``: una riga di ``localize_all_channels`` per finestra, L = 32.768 campioni a 1 Hz, i 16 canali scelti
  (``ch_00``…``ch_15``);
- ``hai_loc.parquet``: le stesse finestre, una riga di ``localize`` per finestra e canale (canale rinominato ``ch_00``);
- ``hai_fumo.parquet``: 2 righe di passeggiata casuale (una multicanale, una a un canale), seme 20261016;
- ``GOLD_HAI.json``: gli attacchi (dalla colonna ``attack`` dei file di test) e, per finestra, attacchi e pulizia;
- ``COMPOSIZIONE_HAI.json``: canali scelti con le loro statistiche, finestre, sha.

Finestre: nei file di test passo 16.384 più una allineata alla fine; nei file di training passo 65.536 più una allineata
alla fine, sui tratti che NON condividono istanti con i file di test (le ultime 12 ore di train1 sono le prime 12 di
test3).  Canali: per ciascun processo P1-P4, fra i canali con MAD non nulla in ogni finestra, i 4 con la quota più bassa di
passi piatti sui tratti di training (parità: più valori distinti).  Nessuna uscita del modello è coinvolta; le etichette
servono solo al gold.  Le righe portano la risposta cieca (nessuna anomalia).  Non sovrascrive.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

L = 32768
PASSO_TEST = 16384
PASSO_TRAIN = 65536
MARGINE_S = 600
PER_PROCESSO = 4
PROCESSI = ("P1", "P2", "P3", "P4")
SEME_FUMO = 20261016
SHA_CSV = {
    "test1": "532de41bed372206941609d05b763958f59abecfd63c8c123649f823452e445e",
    "test2": "c5572e0ed19906107ceb56c4b4f40e165153fc7ba87b3506230d53d2478c29bb",
    "test3": "bff835894baff0c73871bc01ece4f5cf759d455a049e808b012128767420caaf",
    "test4": "51380fd28fd985b94a10cae3d8b80926becb3af9f233f2d3a38ab8be9482a482",
    "test5": "f0d59308b167ed95d0e81fb3e27c906682c9b21d3dba0ab4c4d696565df35179",
    "train1": "fdd0162315b32817ba665e2cc8990eb09c47c4edc29683a86b11dc9df062b3a9",
    "train2": "c330af06a24f5fe3df864dddc0e9cbbbfd27db2e005bd32dc8ab3eb2ab356337",
    "train3": "de09120c617bad5f4f3cab86705137fe7ced4b1123fb67ffdf67fd645f3d1b8f",
}
TEST = ("test1", "test2", "test3", "test4", "test5")
TRAIN = ("train1", "train2", "train3")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def inizi(n: int, passo: int) -> list[int]:
    if n < L:
        return []
    x = list(range(0, n - L + 1, passo))
    if x[-1] + L < n:
        x.append(n - L)
    return x


def tratti(maschera: np.ndarray) -> list[tuple[int, int]]:
    e = np.diff(np.r_[0, maschera.astype(np.int8), 0])
    return list(zip(np.where(e == 1)[0].tolist(), np.where(e == -1)[0].tolist()))


def mad(v: np.ndarray) -> float:
    return float(np.median(np.abs(v - np.median(v))))


def sovrapp(a0: int, a1: int, b0: int, b1: int) -> int:
    return max(0, min(a1, b1) - max(a0, b0))


def leggi_csv(p: Path):
    import pyarrow.csv as pc
    t = pc.read_csv(p)
    tm = np.array(t.column("time").to_pylist(), dtype="datetime64[s]")
    if not np.all(np.diff(tm).astype(np.int64) == 1):
        raise SystemExit(f"{p.name}: passo non sempre di 1 s")
    canali = [c for c in t.column_names if c != "time" and not c.startswith("attack")]
    X = {c: np.asarray(t.column(c).to_numpy(), dtype=np.float32) for c in canali}  # float32: i valori che il modello vede
    for c, v in X.items():
        if not np.all(np.isfinite(v)):
            raise SystemExit(f"{p.name}: {c} con valori non finiti")
    lab = {c: np.asarray(t.column(c).to_numpy()) for c in t.column_names if c.startswith("attack")}
    return tm, canali, X, lab


def finestre_e_gold(dati: dict) -> tuple[list[dict], list[dict]]:
    """Finestre (file, inizio) e attacchi con le loro posizioni; pulizia con margine dopo la fine dell'attacco."""
    istanti_test = np.concatenate([dati[f][0] for f in TEST])
    attacchi = []
    for f in TEST:
        tm, _, _, lab = dati[f]
        for s, e in tratti(lab["attack"] > 0):
            proc = [p for p in ("P1", "P2", "P3") if lab[f"attack_{p}"][s:e].any()]
            attacchi.append({"attacco": f"{f}-a{len([x for x in attacchi if x['file'] == f]):02d}", "file": f,
                             "start": s, "end": e, "durata_s": e - s, "inizio": str(tm[s]), "fine": str(tm[e - 1]),
                             "processi": proc})
    finestre = []
    for f in TEST + TRAIN:
        tm = dati[f][0]
        if f in TEST:
            pezzi = [(0, len(tm))]
            passo = PASSO_TEST
        else:
            pezzi = tratti(~np.isin(tm, istanti_test))
            passo = PASSO_TRAIN
        k = 0
        for p0, p1 in pezzi:
            for i in inizi(p1 - p0, passo):
                a = p0 + i
                b = a + L
                dentro = []
                for g in attacchi:
                    if g["file"] != f:
                        continue
                    ov = sovrapp(a, b, g["start"], g["end"])
                    if ov:
                        dentro.append({"attacco": g["attacco"], "intero": a <= g["start"] and g["end"] <= b,
                                       "start": max(a, g["start"]) - a, "end": min(b, g["end"]) - a, "campioni": ov,
                                       "processi": g["processi"]})
                vicino = any(g["file"] == f and sovrapp(a, b, g["start"], g["end"] + MARGINE_S) for g in attacchi)
                finestre.append({"finestra": f"{f}-w{k:02d}", "file": f, "tipo": "test" if f in TEST else "training",
                                 "inizio_indice": a, "fine_indice": b, "primo": str(tm[a]), "ultimo": str(tm[b - 1]),
                                 "attacchi": dentro, "pulita": not vicino})
                k += 1
    return finestre, attacchi


def scegli_canali(dati: dict, finestre: list[dict], canali: list[str]) -> tuple[list[str], dict]:
    istanti_test = np.concatenate([dati[f][0] for f in TEST])
    stat = {}
    for c in canali:
        piatti = passi = 0
        distinti = []
        for f in TRAIN:
            tm, _, X, _ = dati[f]
            for p0, p1 in tratti(~np.isin(tm, istanti_test)):
                v = X[c][p0:p1]
                d = np.diff(v)
                piatti += int((d == 0).sum())
                passi += len(d)
                distinti.append(len(np.unique(v)) / len(v))
        mad0 = sum(mad(dati[w["file"]][2][c][w["inizio_indice"]:w["fine_indice"]]) == 0 for w in finestre)
        stat[c] = {"piatti": piatti / passi, "distinti": float(np.mean(distinti)), "mad_nulla_finestre": int(mad0)}
    scelti = []
    for p in PROCESSI:
        cand = [c for c in canali if c.startswith(p + "_") and stat[c]["mad_nulla_finestre"] == 0]
        cand.sort(key=lambda c: (stat[c]["piatti"], -stat[c]["distinti"], c))
        if len(cand) < PER_PROCESSO:
            raise SystemExit(f"{p}: solo {len(cand)} canali con MAD non nulla ovunque")
        scelti += cand[:PER_PROCESSO]
    return scelti, stat


def riga_lac(idr: str, valori: list[np.ndarray], modello: str, tipo: dict) -> dict:
    C = len(valori)
    return {"id": idr, "tier": tipo["tier"], "category": "localize_all_channels", "length": L, "n_channels": C,
            "n_channels_a": tipo["n_channels_a"], "n_channels_b": tipo["n_channels_b"],
            "question": modello.replace("{L}", str(L)).replace("{C}", str(C)), "options": [],
            "answer": "localize_all_channels:" + json.dumps({"_L": L, "anomalies": []}, sort_keys=True),
            "semantic_class": f"localize_all_channels_K0_L{L}", "coupling_kind": tipo["coupling_kind"],
            "coupling_lag": tipo["coupling_lag"], "injection_kinds": [], "injection_channels": [], "injection_starts": [],
            "injection_ends": [], "channel_names": [f"ch_{i:02d}" for i in range(C)],
            "channel_values": [np.asarray(v, dtype=np.float32).tolist() for v in valori], "seed": 0}


def riga_loc(idr: str, valori: np.ndarray, modello: str, tipo: dict) -> dict:
    return {"id": idr, "tier": tipo["tier"], "category": "localize", "length": L, "n_channels": 1,
            "n_channels_a": tipo["n_channels_a"], "n_channels_b": tipo["n_channels_b"],
            "question": modello.replace("{L}", str(L)), "options": [],
            "answer": "localize:" + json.dumps({"_L": L, "present": False}),
            "semantic_class": f"localize_absent_L{L}", "coupling_kind": tipo["coupling_kind"],
            "coupling_lag": tipo["coupling_lag"], "injection_kinds": [], "injection_channels": [],
            "injection_starts": [], "injection_ends": [], "channel_names": ["ch_00"],
            "channel_values": [np.asarray(valori, dtype=np.float32).tolist()], "seed": 0}


def main(argv=None) -> int:
    import pyarrow as pa
    import pyarrow.parquet as pq
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", required=True, type=Path, help="cartella con gli 8 csv.gz di HAI 21.03")
    ap.add_argument("--schema-di", required=True, type=Path, help="metropt3_p15.parquet: schema e metadati lac")
    ap.add_argument("--domanda-lac", required=True, type=Path, help="COMPOSIZIONE.json di MetroPT-3 (domanda lac dal val)")
    ap.add_argument("--domanda-loc", required=True, type=Path, help="COMPOSIZIONE_LOC.json (domanda di localize dal val)")
    ap.add_argument("--metadati-loc", required=True, type=Path, help="metropt3_hia.parquet: metadati delle righe localize")
    ap.add_argument("--out-dir", required=True, type=Path)
    a = ap.parse_args(argv)
    for f, s in SHA_CSV.items():
        if sha(a.dir / f"{f}.csv.gz") != s:
            raise SystemExit(f"RIFIUTO: sha di {f}.csv.gz")
    nomi = ("hai_mc.parquet", "hai_loc.parquet", "hai_fumo.parquet", "GOLD_HAI.json", "COMPOSIZIONE_HAI.json")
    a.out_dir.mkdir(parents=True, exist_ok=True)
    for f in nomi:
        if (a.out_dir / f).exists():
            raise SystemExit(f"RIFIUTO: {a.out_dir / f} esiste già")
    lac = json.loads(a.domanda_lac.read_text(encoding="utf-8"))["domanda_modello"]
    loc = json.loads(a.domanda_loc.read_text(encoding="utf-8"))["domanda_modello"]
    if not lac.endswith("(Here L = {L}, C = {C}.)") or not lac.startswith("The time series has multiple channels."):
        raise SystemExit("domanda lac inattesa")
    if not loc.endswith("(Here L = {L}.)") or not loc.startswith("Does the time series contain an anomaly"):
        raise SystemExit("domanda di localize inattesa")
    campi = ["category", "tier", "n_channels_a", "n_channels_b", "coupling_kind", "coupling_lag"]
    t_lac = pq.read_table(a.schema_di, columns=campi).slice(0, 1).to_pylist()[0]
    t_loc = pq.read_table(a.metadati_loc, columns=campi).slice(0, 1).to_pylist()[0]
    if t_lac["category"] != "localize_all_channels" or t_loc["category"] != "localize":
        raise SystemExit("metadati inattesi")
    schema = pq.read_schema(a.schema_di).remove_metadata()
    dati = {f: leggi_csv(a.dir / f"{f}.csv.gz") for f in TEST + TRAIN}
    canali = dati["test1"][1]
    if any(dati[f][1] != canali for f in dati):
        raise SystemExit("colonne diverse fra i file")
    finestre, attacchi = finestre_e_gold(dati)
    scelti, stat = scegli_canali(dati, finestre, canali)
    def gen_mc():
        for w in finestre:
            X = dati[w["file"]][2]
            yield [riga_lac(f"hai-mc-{w['finestra']}", [X[c][w["inizio_indice"]:w["fine_indice"]] for c in scelti], lac, t_lac)]

    def gen_lc():
        for w in finestre:
            X = dati[w["file"]][2]
            yield [riga_loc(f"hai-loc-{w['finestra']}-{c}", X[c][w["inizio_indice"]:w["fine_indice"]], loc, t_loc)
                   for c in scelti]

    def gen_fumo():
        rng = np.random.default_rng(SEME_FUMO)
        yield [riga_lac("hai-fumo-mc", [np.cumsum(rng.standard_normal(L)) for _ in scelti], lac, t_lac),
               riga_loc("hai-fumo-loc", np.cumsum(rng.standard_normal(L)), loc, t_loc)]
    g = {"natura": "HAI 21.03: attacchi dalla colonna attack dei file di test; finestre da 32.768 s",
         "L": L, "margine_pulizia_s": MARGINE_S, "attacchi": attacchi, "finestre": finestre}
    interi = {x["attacco"] for w in finestre for x in w["attacchi"] if x["intero"]}
    out = {"natura": "HAI 21.03 nelle righe di AnomalyXL; risposte cieche; gold in GOLD_HAI.json", "csv_sha256": SHA_CSV,
           "L": L, "passo_test": PASSO_TEST, "passo_training": PASSO_TRAIN, "canali": scelti,
           "statistiche_canali": stat, "finestre": len(finestre),
           "finestre_test": sum(w["tipo"] == "test" for w in finestre),
           "finestre_training": sum(w["tipo"] == "training" for w in finestre),
           "finestre_pulite": sum(w["pulita"] for w in finestre),
           "finestre_pulite_test": sum(w["pulita"] and w["tipo"] == "test" for w in finestre),
           "finestre_con_attacchi": sum(bool(w["attacchi"]) for w in finestre),
           "attacchi": len(attacchi), "attacchi_interi_in_una_finestra": len(interi),
           "durate_s": sorted(x["durata_s"] for x in attacchi), "domanda_lac": lac, "domanda_loc": loc,
           "tipo_lac": t_lac, "tipo_loc": t_loc, "seme_fumo": SEME_FUMO}
    for nome, gen in (("hai_mc.parquet", gen_mc), ("hai_loc.parquet", gen_lc), ("hai_fumo.parquet", gen_fumo)):
        p = a.out_dir / nome
        n = 0
        with pq.ParquetWriter(p, schema) as wr:  # un gruppo di righe per finestra: niente liste giganti in memoria
            for rr in gen():
                wr.write_table(pa.Table.from_pylist(rr, schema=schema))
                n += len(rr)
        p.chmod(0o444)
        out[nome] = {"righe": n, "sha256": sha(p)}
    for f, x in (("GOLD_HAI.json", g), ("COMPOSIZIONE_HAI.json", out)):
        (a.out_dir / f).write_bytes((json.dumps(x, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        (a.out_dir / f).chmod(0o444)
    print(json.dumps({k: v for k, v in out.items() if k not in ("domanda_lac", "domanda_loc", "statistiche_canali")},
                     indent=1, ensure_ascii=False))
    for w in finestre:
        print(w["finestra"], w["primo"], w["ultimo"], len(w["attacchi"]), "pulita" if w["pulita"] else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
