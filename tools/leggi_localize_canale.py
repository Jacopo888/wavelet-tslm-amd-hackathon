#!/usr/bin/env python3
"""Lettura di C1 su MetroPT-3 a un canale alla volta (``DISEGNO-LOCALIZE-CANALE-METROPT3.md`` §4-§5).

Le 161 risposte di ``localize`` si riuniscono per finestra (sistema primario «scansione dei canali»: gli intervalli di
tutti i canali che rispondono «presente») e si leggono con la STESSA funzione del multicanale
(``leggi_zeroshot_metropt3.leggi``), così misure e regole sono identiche.  Per canale si rifà la stessa lettura col
solo canale, descrittiva.  Si ferma se mancano righe o campi.  Non sovrascrive.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import leggi_zeroshot_metropt3 as lz  # noqa: E402

CANALI = ("TP2", "TP3", "H1", "DV_pressure", "Reservoirs", "Oil_temperature", "Motor_current")


def risposta(pred: str) -> tuple[str, tuple[int, int] | None]:
    """('valida'|'non_valida', intervallo o None).  «assente» è valida senza intervallo."""
    cat, sep, corpo = (pred or "").strip().partition(":")
    if not sep or cat.strip() != "localize":
        return "non_valida", None
    try:
        x = json.loads(corpo)
    except json.JSONDecodeError:
        return "non_valida", None
    if not isinstance(x, dict) or not isinstance(x.get("present"), bool):
        return "non_valida", None
    if not x["present"]:
        return "valida", None
    s, e = x.get("start"), x.get("end")
    if not (isinstance(s, int) and isinstance(e, int)):
        return "non_valida", None
    s, e = max(0, s), min(lz.L, e)
    return "valida", ((s, e) if e > s else None)


def dump_finestre(per_id: dict, finestre: list[int], canali, prefisso: str = "loc") -> dict:
    recs = []
    for w in finestre:
        anomalie = []
        for c in canali:
            _, iv = risposta(per_id[f"metropt3-{prefisso}-w{w:02d}-{c}"]["pred"])
            if iv:
                anomalie.append({"channel": c, "start": iv[0], "end": iv[1]})
        recs.append({"id": f"metropt3-{prefisso}-w{w:02d}", "category": "localize_all_channels",
                     "pred": "localize_all_channels:" + json.dumps({"_L": lz.L, "anomalies": anomalie})})
    return {"records": recs}


def leggi(dump: dict, gold: dict, canali=CANALI, prefisso: str = "loc") -> dict:
    recs = dump.get("records")
    if not isinstance(recs, list):
        raise lz.Fermo("il dump non ha 'records'")
    per_id = {}
    for r in recs:
        for k in ("id", "category", "pred"):
            if k not in r:
                raise lz.Fermo(f"riga senza il campo {k!r}")
        if r["id"] in per_id:
            raise lz.Fermo(f"id ripetuto {r['id']}")
        if r["category"] != "localize":
            raise lz.Fermo(f"{r['id']}: categoria {r['category']!r}")
        per_id[r["id"]] = r
    finestre = [f["finestra"] for f in gold["finestre"]]
    attesi = {f"metropt3-{prefisso}-w{w:02d}-{c}" for w in finestre for c in canali}
    if set(per_id) != attesi:
        raise lz.Fermo(f"righe attese {len(attesi)}, trovate {len(per_id)}")
    primario = lz.leggi(dump_finestre(per_id, finestre, canali, prefisso), gold, prefisso)
    per_canale = {}
    for c in canali:
        x = lz.leggi(dump_finestre(per_id, finestre, (c,), prefisso), gold, prefisso)
        stati = [risposta(per_id[f"metropt3-{prefisso}-w{w:02d}-{c}"]["pred"]) for w in finestre]
        per_canale[c] = {"M1": x["M1_guasti_rilevati"]["rilevati"], "M1_caso": x["M1_guasti_rilevati"]["attesi_a_caso"],
                         "M2": x["M2_falsi_allarmi"]["finestre_pulite_con_segnalazioni"],
                         "assente": sum(s == "valida" and iv is None for s, iv in stati),
                         "presente": sum(iv is not None for _, iv in stati),
                         "non_valide": sum(s == "non_valida" for s, _ in stati)}
    stati_tutti = [risposta(r["pred"]) for r in per_id.values()]
    primario["ruolo"] = f"PRIMARIO: scansione di {len(canali)} canali (almeno un canale «presente»)"
    primario["risposte_a_un_canale"] = {"righe": len(per_id), "valide": sum(s == "valida" for s, _ in stati_tutti),
                                        "assente": sum(s == "valida" and iv is None for s, iv in stati_tutti),
                                        "presente": sum(iv is not None for _, iv in stati_tutti)}
    primario["per_canale"] = per_canale
    return primario


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dump", required=True, type=Path)
    ap.add_argument("--gold", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--prefisso", default="loc")
    ap.add_argument("--canali", default=",".join(CANALI))
    ap.add_argument("--L", type=int, default=131072)
    a = ap.parse_args(argv)
    lz.L = a.L
    canali = tuple(a.canali.split(","))
    if a.out.exists():
        raise SystemExit(f"RIFIUTO: {a.out} esiste già")
    try:
        out = leggi(json.loads(a.dump.read_text(encoding="utf-8")), json.loads(a.gold.read_text(encoding="utf-8")), canali, a.prefisso)
    except lz.Fermo as e:
        raise SystemExit(f"FERMO: {e}")
    a.out.write_bytes((json.dumps(out, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    m1, m2 = out["M1_guasti_rilevati"], out["M2_falsi_allarmi"]
    print(f"esito {out['esito_regola']}: {out['frase']}")
    print(f"M1 {m1['rilevati']}/4 (a caso {m1['attesi_a_caso']:.2f}), M2 {m2['finestre_pulite_con_segnalazioni']}/{m2['finestre_pulite']}")
    print("risposte a un canale:", out["risposte_a_un_canale"])
    for c, v in out["per_canale"].items():
        print(f"  {c:16s} M1 {v['M1']}/4 (caso {v['M1_caso']:.2f})  M2 {v['M2']}/{m2['finestre_pulite']}  assente {v['assente']}/{len(gold_finestre := json.loads(a.gold.read_text(encoding='utf-8'))['finestre'])}  non valide {v['non_valide']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
