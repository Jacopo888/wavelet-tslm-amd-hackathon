#!/usr/bin/env python3
"""MetroPT-3 in due forme nuove per C1 (``diagnostics/20261015/DISEGNO-INDICATORI-METROPT3.md``):

- **A, indicatori di salute:** su una griglia ogni 2 minuti, ciascun punto calcolato sui campioni grezzi dei 60 minuti
  precedenti: quota del tempo sotto carico (DV_eletric), cicli di carico all'ora, calo di TP3 a compressore scarico
  (bar/min), TP3 medio, temperatura media dell'olio, corrente media.
- **C, gli indicatori di A con l'adattamento di B** (ranghi verso la normale e rumore 0,1, seme 20261017).
- **B, i 7 canali analogici «alla AnomalyXL»:** sulla stessa griglia la mediana mobile a 60 minuti di ciascun canale;
  poi, in ogni finestra, trasformazione per ranghi verso una normale (media 0, deviazione 1) e un rumore gaussiano di
  deviazione 0,1 (seme fisso), così il segnale è continuo e senza gradini come quelli del generatore.

Un punto della griglia è valido se nei 60 minuti ci sono almeno 180 campioni grezzi (metà dei 360 attesi a 10 s); si
tengono solo i punti validi (serie per indice, come nello zero-shot).  Finestre di 16.384 punti, passo 8.192, più una
allineata alla fine.  Righe di ``localize`` a un canale (rinominato ``ch_00``), risposta cieca; gold in GOLD_HI.json.
Nessuna uscita del modello è coinvolta.  Non sovrascrive.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

PASSO_S = 120
FINESTRA_S = 3600
MIN_CAMPIONI = 180
L = 16384
PASSO_FIN = 8192
ANALOGICI = ("TP2", "TP3", "H1", "DV_pressure", "Reservoirs", "Oil_temperature", "Motor_current")
INDICATORI = ("quota_carico", "cicli_ora", "calo_TP3", "TP3_medio", "olio_medio", "corrente_media")
SEME_B, SEME_FUMO, SEME_C = 20261015, 20261016, 20261017
SIGMA_B = 0.1
GUASTI = (
    ("1", "2020-04-18 00:00:00", "2020-04-18 23:59:00", "2020-04-30 12:00:00"),
    ("2", "2020-05-29 23:30:00", "2020-05-30 06:00:00", "2020-06-08 16:00:00"),
    ("3", "2020-06-05 10:00:00", "2020-06-07 14:30:00", "2020-06-08 16:00:00"),
    ("4", "2020-07-15 14:30:00", "2020-07-15 19:00:00", "2020-07-16 00:00:00"),
)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def griglia(ts: np.ndarray, col: dict[str, np.ndarray]) -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Punti validi della griglia (tempi), indicatori A e mediane B, ciascuno sui 60 minuti precedenti il punto."""
    t0 = (ts[0] // PASSO_S + 1) * PASSO_S + FINESTRA_S
    tg = np.arange(t0, ts[-1] + 1, PASSO_S, dtype=np.int64)
    lo = np.searchsorted(ts, tg - FINESTRA_S, side="right")
    hi = np.searchsorted(ts, tg, side="right")
    n = hi - lo
    ok = n >= MIN_CAMPIONI
    dv = col["DV_eletric"].astype(np.int8)
    tp3 = col["TP3"]
    cons = np.diff(ts) <= 20                      # coppie consecutive senza buco
    salita = np.concatenate([[0], (cons & (dv[1:] == 1) & (dv[:-1] == 0)).astype(np.int64)])
    scarico = cons & (dv[1:] == 0) & (dv[:-1] == 0)
    pend = np.where(scarico, np.diff(tp3) / np.maximum(np.diff(ts), 1) * 60.0, np.nan)   # bar/min fra i e i+1
    c_salita = np.concatenate([[0], np.cumsum(salita)])
    def media(x):
        c = np.concatenate([[0.0], np.cumsum(x.astype(np.float64))])
        return (c[hi] - c[lo]) / np.maximum(n, 1)
    A = {"quota_carico": media(dv), "cicli_ora": (c_salita[hi] - c_salita[lo]) * (3600.0 / FINESTRA_S),
         "TP3_medio": media(tp3), "olio_medio": media(col["Oil_temperature"]), "corrente_media": media(col["Motor_current"])}
    calo = np.full(len(tg), np.nan)
    B = {c: np.full(len(tg), np.nan) for c in ANALOGICI}
    for g in np.where(ok)[0]:
        a, b = lo[g], hi[g]
        seg = pend[a:max(a, b - 1)]
        seg = seg[np.isfinite(seg)]
        if len(seg) >= 10:
            calo[g] = np.median(seg)
        for c in ANALOGICI:
            B[c][g] = np.median(col[c][a:b])
    # calo di TP3 senza abbastanza coppie a compressore scarico: si tiene l'ultimo valore valido (dichiarato)
    ultimo = np.nan
    for g in range(len(tg)):
        if np.isfinite(calo[g]):
            ultimo = calo[g]
        elif ok[g]:
            calo[g] = ultimo
    primo = calo[ok][np.isfinite(calo[ok])][0]
    calo[ok & ~np.isfinite(calo)] = primo
    A["calo_TP3"] = calo
    A = {k: A[k][ok] for k in INDICATORI}
    B = {c: B[c][ok] for c in ANALOGICI}
    return tg[ok], A, B, int(ok.sum()), int(len(tg))


def inizi_finestre(n: int) -> list[int]:
    inizi = list(range(0, n - L + 1, PASSO_FIN))
    if inizi[-1] + L < n:
        inizi.append(n - L)
    return inizi


def gold(tempi: np.ndarray, inizi: list[int]) -> dict:
    def idx(t, dopo):
        return int(np.searchsorted(tempi, np.datetime64(t).astype("datetime64[s]").astype(np.int64), side="right" if dopo else "left"))
    guasti = []
    for nome, t0, t1, man in GUASTI:
        s, e, z = idx(t0, False), idx(t1, True), idx(man, True)
        if not 0 <= s < e <= len(tempi):
            raise ValueError(f"guasto {nome}: [{s}, {e}) fuori dalla serie")
        guasti.append({"guasto": nome, "inizio": t0, "fine": t1, "manutenzione_successiva": man, "start": s, "end": e,
                       "campioni": e - s, "zona_sospetta": [s, z]})
    finestre = []
    for k, a in enumerate(inizi):
        b = a + L
        dentro = [{"guasto": g["guasto"], "intero": a <= g["start"] and g["end"] <= b, "start": max(a, g["start"]) - a,
                   "end": min(b, g["end"]) - a, "campioni": min(b, g["end"]) - max(a, g["start"])}
                  for g in guasti if min(b, g["end"]) > max(a, g["start"])]
        pulita = not any(min(b, g["zona_sospetta"][1]) > max(a, g["zona_sospetta"][0]) for g in guasti)
        finestre.append({"finestra": k, "inizio_indice": a, "fine_indice": b,
                         "primo_timestamp": str(tempi[a].astype("datetime64[s]")), "ultimo_timestamp": str(tempi[b - 1].astype("datetime64[s]")),
                         "guasti": dentro, "pulita": pulita})
    return {"guasti": guasti, "finestre": finestre}


def rango_normale(x: np.ndarray) -> np.ndarray:
    """Ranghi (medi in caso di pari) -> quantili della normale standard."""
    from statistics import NormalDist
    ordine = np.argsort(x, kind="mergesort")
    r = np.empty(len(x))
    r[ordine] = np.arange(len(x))
    xs = x[ordine]
    i = 0
    while i < len(xs):                                # ranghi medi sui valori uguali
        j = i
        while j + 1 < len(xs) and xs[j + 1] == xs[i]:
            j += 1
        if j > i:
            r[ordine[i:j + 1]] = (i + j) / 2
        i = j + 1
    q = (r + 0.5) / len(x)
    nd = NormalDist()
    return np.array([nd.inv_cdf(v) for v in q])


def riga(idr: str, valori: np.ndarray, modello: str, tipo: dict) -> dict:
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
    import pyarrow.csv as pcsv
    import pyarrow.parquet as pq
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True, type=Path)
    ap.add_argument("--sha-csv", required=True)
    ap.add_argument("--schema-di", required=True, type=Path, help="un parquet con lo schema di AnomalyXL (metropt3_a7)")
    ap.add_argument("--domanda-da", required=True, type=Path, help="COMPOSIZIONE_LOC.json: domanda di localize dal val")
    ap.add_argument("--metadati-da", required=True, type=Path, help="parquet di AnomalyXL con righe di localize")
    ap.add_argument("--out-dir", required=True, type=Path)
    a = ap.parse_args(argv)
    if sha(a.csv) != a.sha_csv:
        raise SystemExit("RIFIUTO: sha del CSV")
    a.out_dir.mkdir(parents=True, exist_ok=True)
    nomi = ("metropt3_hia.parquet", "metropt3_hib.parquet", "metropt3_hic.parquet", "metropt3_hifumo.parquet", "GOLD_HI.json",
            "COMPOSIZIONE_HI.json")
    for f in nomi:
        if (a.out_dir / f).exists():
            raise SystemExit(f"RIFIUTO: {a.out_dir / f} esiste già")
    modello = json.loads(a.domanda_da.read_text(encoding="utf-8"))["domanda_modello"]
    if not modello.endswith("(Here L = {L}.)") or not modello.startswith("Does the time series contain an anomaly"):
        raise SystemExit("domanda di localize inattesa")
    m = pq.read_table(a.metadati_da, columns=["category", "tier", "n_channels_a", "n_channels_b", "coupling_kind", "coupling_lag"])
    righe_m = [r for r in m.slice(0, 400).to_pylist() if r["category"] == "localize"]
    tipo = {k: righe_m[0][k] for k in ("tier", "n_channels_a", "n_channels_b", "coupling_kind", "coupling_lag")}
    t = pcsv.read_csv(a.csv)
    ts = np.array(t.column("timestamp").to_pylist(), dtype="datetime64[s]").astype(np.int64)
    col = {c: np.asarray(t.column(c).to_numpy(), dtype=np.float64) for c in ANALOGICI + ("DV_eletric",)}
    tempi, A, B, n_validi, n_griglia = griglia(ts, col)
    inizi = inizi_finestre(n_validi)
    g = gold(tempi, inizi)
    schema = pq.read_schema(a.schema_di).remove_metadata()
    rng_b = np.random.default_rng(SEME_B)
    rng_c = np.random.default_rng(SEME_C)
    righe_a, righe_b, righe_c = [], [], []
    for k, s in enumerate(inizi):
        for nome in INDICATORI:
            righe_a.append(riga(f"metropt3-hia-w{k:02d}-{nome}", A[nome][s:s + L], modello, tipo))
            zc = rango_normale(A[nome][s:s + L]) + rng_c.normal(0.0, SIGMA_B, L)
            righe_c.append(riga(f"metropt3-hic-w{k:02d}-{nome}", zc, modello, tipo))
        for nome in ANALOGICI:
            z = rango_normale(B[nome][s:s + L]) + rng_b.normal(0.0, SIGMA_B, L)
            righe_b.append(riga(f"metropt3-hib-w{k:02d}-{nome}", z, modello, tipo))
    rng_f = np.random.default_rng(SEME_FUMO)
    fumo = [riga(f"metropt3-hifumo-{k}", np.cumsum(rng_f.standard_normal(L)) / np.sqrt(L), modello, tipo) for k in range(2)]
    out = {"natura": "MetroPT-3: A indicatori di salute, B analogici alla AnomalyXL; localize a un canale; risposte cieche",
           "csv_sha256": a.sha_csv, "passo_s": PASSO_S, "finestra_mobile_s": FINESTRA_S, "min_campioni": MIN_CAMPIONI,
           "punti_griglia": n_griglia, "punti_validi": n_validi, "L": L, "passo_finestre": PASSO_FIN, "inizi": inizi,
           "indicatori_A": list(INDICATORI), "canali_B": list(ANALOGICI), "sigma_B": SIGMA_B, "seme_B": SEME_B,
           "finestre_con_un_guasto_intero": sum(any(x["intero"] for x in f["guasti"]) for f in g["finestre"]),
           "finestre_pulite": sum(f["pulita"] for f in g["finestre"]), "domanda_modello": modello, "tipo_righe": tipo}
    out["seme_C"] = SEME_C
    for nome, rr in (("metropt3_hia.parquet", righe_a), ("metropt3_hib.parquet", righe_b), ("metropt3_hic.parquet", righe_c),
                     ("metropt3_hifumo.parquet", fumo)):
        p = a.out_dir / nome
        pq.write_table(pa.Table.from_pylist(rr, schema=schema), p)
        p.chmod(0o444)
        out[nome] = {"righe": len(rr), "sha256": sha(p)}
    for f, x in (("GOLD_HI.json", g), ("COMPOSIZIONE_HI.json", out)):
        (a.out_dir / f).write_bytes((json.dumps(x, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    print(json.dumps({k: v for k, v in out.items() if k not in ("domanda_modello", "inizi")}, indent=1))
    for f in g["finestre"]:
        print(f["finestra"], f["primo_timestamp"][:10], f["ultimo_timestamp"][:10], [(x["guasto"], x["intero"]) for x in f["guasti"]], "pulita" if f["pulita"] else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
