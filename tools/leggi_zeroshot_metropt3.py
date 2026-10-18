#!/usr/bin/env python3
"""Lettura del zero-shot su MetroPT-3 (``diagnostics/20261015/DISEGNO-ZEROSHOT-METROPT3.md`` §4-§5, CONGELATO d131cf78).

Legge il dump di ``validate.py`` (campo ``pred``: la risposta con le coordinate risolte) e ``GOLD.json``; scrive le misure
M1, M1-centro, M1-caso, M2, M3, M4, il formato e l'esito secondo la regola dichiarata.  Si ferma se il dump non ha
esattamente le righe attese o se manca un campo: non risponde «nessuno».  Non sovrascrive l'uscita.

    python leggi_zeroshot_metropt3.py --dump c1_direct.json --gold GOLD.json --insieme p15 --out lettura_p15.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

L = 131072
CATEGORIA = "localize_all_channels"
RUOLO = {"p15": "PRIMARIO", "a7": "accanto (stesse regole, senza esito proprio)", "fumo": "fumo: nessuna lettura"}


class Fermo(RuntimeError):
    """Il dump non permette la lettura dichiarata."""


def intervalli(pred: str) -> tuple[bool, list[dict]]:
    """(valida, [{channel, start, end}]) dalla risposta; non valida = nessun intervallo, si conta a parte."""
    testo = (pred or "").strip()
    cat, sep, corpo = testo.partition(":")
    if not sep or cat.strip() != CATEGORIA:
        return False, []
    try:
        x = json.loads(corpo)
    except json.JSONDecodeError:
        return False, []
    lista = x.get("anomalies") if isinstance(x, dict) else None
    if not isinstance(lista, list):
        return False, []
    out = []
    for e in lista:
        if not (isinstance(e, dict) and isinstance(e.get("start"), int) and isinstance(e.get("end"), int)):
            return False, []
        s, f = max(0, e["start"]), min(L, e["end"])
        if f > s:
            out.append({"channel": e.get("channel"), "start": s, "end": f})
    return True, out


def sovrapp(a0: int, a1: int, b0: int, b1: int) -> int:
    return max(0, min(a1, b1) - max(a0, b0))


def unione(segmenti: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out: list[list[int]] = []
    for s, e in sorted(segmenti):
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [(s, e) for s, e in out]


def iou(a: list[tuple[int, int]], b: list[tuple[int, int]]) -> float:
    ua, ub = unione(a), unione(b)
    inter = sum(sovrapp(x0, x1, y0, y1) for x0, x1 in ua for y0, y1 in ub)
    tot = sum(e - s for s, e in ua) + sum(e - s for s, e in ub) - inter
    return inter / tot if tot else 0.0


def p_caso(emessi: list[dict], lg: int) -> float:
    """Probabilità, troncata a 1, che gli stessi intervalli messi a caso nella finestra tocchino un guasto lungo lg."""
    return min(1.0, sum((e["end"] - e["start"] + lg - 1) / (L - (e["end"] - e["start"]) + 1) for e in emessi))


def wilson(k: int, n: int, z: float = 1.959964) -> list[float] | None:
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0.0, c - m), min(1.0, c + m)]


def leggi(dump: dict, gold: dict, insieme: str) -> dict:
    finestre = gold["finestre"]
    attesi = [f"metropt3-{insieme}-w{f['finestra']:02d}" for f in finestre]
    recs = dump.get("records")
    if not isinstance(recs, list):
        raise Fermo("il dump non ha 'records'")
    per_id = {}
    for r in recs:
        for k in ("id", "category", "pred"):
            if k not in r:
                raise Fermo(f"riga senza il campo {k!r}")
        if r["id"] in per_id:
            raise Fermo(f"id ripetuto {r['id']}")
        per_id[r["id"]] = r
    if sorted(per_id) != sorted(attesi):
        raise Fermo(f"righe attese {len(attesi)}, trovate {len(per_id)}; differenza {sorted(set(attesi) ^ set(per_id))[:5]}")
    righe = []
    for f in finestre:
        r = per_id[f"metropt3-{insieme}-w{f['finestra']:02d}"]
        if r["category"] != CATEGORIA:
            raise Fermo(f"{r['id']}: categoria {r['category']!r}")
        valida, em = intervalli(r["pred"])
        righe.append({"finestra": f["finestra"], "valida": valida, "emessi": em, "pulita": f["pulita"], "guasti": f["guasti"],
                      "inizio_indice": f["inizio_indice"]})
    # M1, M1-centro, M1-caso
    m1 = []
    for g in gold["guasti"]:
        lg = g["end"] - g["start"]
        piene = [(r, next(x for x in r["guasti"] if x["guasto"] == g["guasto"])) for r in righe
                 if any(x["guasto"] == g["guasto"] and x["intero"] for x in r["guasti"])]
        if not piene:
            raise Fermo(f"guasto {g['guasto']}: nessuna finestra che lo contenga per intero")
        per_f = []
        for r, x in piene:
            tocca = any(sovrapp(e["start"], e["end"], x["start"], x["end"]) for e in r["emessi"])
            centro = any(x["start"] <= (e["start"] + e["end"]) / 2 < x["end"] for e in r["emessi"])
            per_f.append({"finestra": r["finestra"], "tocca": tocca, "centro_dentro": centro, "p_caso": p_caso(r["emessi"], lg),
                          "emessi": len(r["emessi"])})
        q = 1.0
        for x in per_f:
            q *= 1 - x["p_caso"]
        m1.append({"guasto": g["guasto"], "campioni": lg, "rilevato": any(x["tocca"] for x in per_f),
                   "rilevato_col_centro": any(x["centro_dentro"] for x in per_f), "p_caso": 1 - q, "finestre": per_f})
    rilevati = sum(x["rilevato"] for x in m1)
    attesi_caso = sum(x["p_caso"] for x in m1)
    # M2
    pulite = [r for r in righe if r["pulita"]]
    allarmi = sum(bool(r["emessi"]) for r in pulite)
    # M3
    zone = [g["zona_sospetta"] for g in gold["guasti"]]
    emessi_tot = toccano = 0
    for r in righe:
        a = r["inizio_indice"]
        for e in r["emessi"]:
            emessi_tot += 1
            toccano += any(sovrapp(a + e["start"], a + e["end"], z0, z1) for z0, z1 in zone)
    # M4
    m4 = [{"finestra": r["finestra"], "iou": iou([(e["start"], e["end"]) for e in r["emessi"]],
                                                 [(x["start"], x["end"]) for x in r["guasti"]])}
          for r in righe if any(x["intero"] for x in r["guasti"])]
    canali = {}
    for r in righe:
        for e in r["emessi"]:
            canali[str(e["channel"])] = canali.get(str(e["channel"]), 0) + 1
    met = len(pulite) / 2
    if allarmi > met:
        esito, frase = "B", "segnala quasi ovunque: le rilevazioni non si leggono come prova"
    elif rilevati >= 3:
        esito, frase = "A", "a zero-shot il lettore segnala i guasti documentati e tace nella maggior parte delle finestre senza guasti"
        if rilevati - attesi_caso < 1:
            frase += " (non oltre il caso)"
    elif rilevati <= 1:
        esito, frase = "C", "a zero-shot non trova questi guasti"
    else:
        esito, frase = "D", "indeterminato su quattro eventi"
    return {
        "insieme": insieme, "ruolo": RUOLO.get(insieme, "?"), "righe": len(righe),
        "M1_guasti_rilevati": {"rilevati": rilevati, "su": len(m1), "col_centro": sum(x["rilevato_col_centro"] for x in m1),
                               "attesi_a_caso": attesi_caso, "per_guasto": m1},
        "M2_falsi_allarmi": {"finestre_pulite_con_segnalazioni": allarmi, "finestre_pulite": len(pulite),
                             "wilson95": wilson(allarmi, len(pulite)),
                             "per_finestra": [{"finestra": r["finestra"], "emessi": len(r["emessi"])} for r in pulite]},
        "M3_precisione": {"emessi_che_toccano_una_zona_sospetta": toccano, "emessi": emessi_tot},
        "M4_iou": m4,
        "formato": {"valide": sum(r["valida"] for r in righe), "liste_vuote": sum(r["valida"] and not r["emessi"] for r in righe),
                    "intervalli_emessi": emessi_tot, "canali_citati": dict(sorted(canali.items()))},
        "regola": "A: M1 >= 3 e M2 <= meta' delle pulite; B: M2 > meta'; C: M1 <= 1 e M2 <= meta'; D: altrimenti. "
                  "M1-caso: per guasto 1 - prod_finestre(1 - min(1, sum_intervalli (l_i + l_g - 1)/(L - l_i + 1)))",
        "esito_regola": esito, "frase": frase,
        "per_finestra": [{"finestra": r["finestra"], "valida": r["valida"], "pulita": r["pulita"],
                          "guasti": [x["guasto"] for x in r["guasti"]], "emessi": r["emessi"]} for r in righe],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dump", required=True, type=Path)
    ap.add_argument("--gold", required=True, type=Path)
    ap.add_argument("--insieme", required=True, choices=("p15", "a7", "fumo"))
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f"RIFIUTO: {a.out} esiste già")
    if a.insieme == "fumo":
        raise SystemExit("RIFIUTO: il fumo non si legge con le misure di MetroPT-3")
    try:
        out = leggi(json.loads(a.dump.read_text(encoding="utf-8")), json.loads(a.gold.read_text(encoding="utf-8")), a.insieme)
    except Fermo as e:
        raise SystemExit(f"FERMO: {e}")
    a.out.write_bytes((json.dumps(out, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    print(json.dumps({k: out[k] for k in ("insieme", "ruolo", "esito_regola", "frase", "formato")}, indent=1, ensure_ascii=False))
    print("M1", out["M1_guasti_rilevati"]["rilevati"], "/", out["M1_guasti_rilevati"]["su"],
          "(a caso %.2f)" % out["M1_guasti_rilevati"]["attesi_a_caso"],
          "M2", out["M2_falsi_allarmi"]["finestre_pulite_con_segnalazioni"], "/", out["M2_falsi_allarmi"]["finestre_pulite"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
