#!/usr/bin/env python3
"""Lettura del zero-shot di C1 su HAI 21.03 (``diagnostics/20261016/DISEGNO-ZEROSHOT-HAI2103.md`` §4-§5).

Due modi, stesse misure:
- ``mc``: le risposte di ``localize_all_channels`` (righe ``hai-mc-<finestra>``), canali ``ch_00``…``ch_15`` riportati
  ai nomi di HAI con l'ordine di ``COMPOSIZIONE_HAI.json``;
- ``scan``: le risposte di ``localize`` a un canale (righe ``hai-loc-<finestra>-<canale>``), riunite per finestra: gli
  intervalli di tutti i canali che rispondono «presente».

Misure: M1 (attacchi toccati, su 50), M1-centro, M1-caso con la stessa formula di MetroPT-3 e il p-valore esatto
(Poisson-binomiale, una coda); M2 (finestre pulite con segnalazioni); M3 (intervalli che toccano un attacco, contro
l'atteso a caso); M4 (IoU per finestra con attacchi); finestre con attacchi segnalate; per processo, descrittivo.  Si
ferma se mancano righe o campi; non sovrascrive.

    python leggi_hai.py --modo mc --dump c1_direct.json --gold GOLD_HAI.json --composizione COMPOSIZIONE_HAI.json --out x.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import leggi_localize_canale as llc  # noqa: E402
import leggi_zeroshot_metropt3 as lz  # noqa: E402

L = 32768
SOGLIA_P = 0.05
Fermo = lz.Fermo


def p_coda(p: list[float], k: int) -> float:
    """P(X >= k) per X somma di Bernoulli indipendenti di probabilità p (Poisson-binomiale esatta)."""
    d = [1.0]
    for q in p:
        n = [0.0] * (len(d) + 1)
        for i, x in enumerate(d):
            n[i] += x * (1 - q)
            n[i + 1] += x * q
        d = n
    return float(min(1.0, sum(d[k:])))


def indicizza(dump: dict, categoria: str) -> dict:
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
        if r["category"] != categoria:
            raise Fermo(f"{r['id']}: categoria {r['category']!r}")
        per_id[r["id"]] = r
    return per_id


def emessi_mc(dump: dict, gold: dict, canali: list[str]) -> dict:
    per_id = indicizza(dump, "localize_all_channels")
    attesi = {f"hai-mc-{w['finestra']}" for w in gold["finestre"]}
    if set(per_id) != attesi:
        raise Fermo(f"righe attese {len(attesi)}, trovate {len(per_id)}; differenza {sorted(attesi ^ set(per_id))[:5]}")
    mappa = {f"ch_{i:02d}": c for i, c in enumerate(canali)}
    out = {}
    for w in gold["finestre"]:
        valida, em = lz.intervalli(per_id[f"hai-mc-{w['finestra']}"]["pred"])
        out[w["finestra"]] = {"valida": valida, "emessi": [dict(e, channel=mappa.get(str(e["channel"]), f"?{e['channel']}"))
                                                           for e in em]}
    return out


def emessi_scan(dump: dict, gold: dict, canali: list[str]) -> tuple[dict, dict]:
    per_id = indicizza(dump, "localize")
    attesi = {f"hai-loc-{w['finestra']}-{c}" for w in gold["finestre"] for c in canali}
    if set(per_id) != attesi:
        raise Fermo(f"righe attese {len(attesi)}, trovate {len(per_id)}; differenza {sorted(attesi ^ set(per_id))[:5]}")
    out, stati = {}, {"righe": len(per_id), "valide": 0, "assente": 0, "presente": 0, "non_valide": 0}
    for w in gold["finestre"]:
        em, tutte_valide = [], True
        for c in canali:
            s, iv = llc.risposta(per_id[f"hai-loc-{w['finestra']}-{c}"]["pred"])
            stati["valide" if s == "valida" else "non_valide"] += 1
            if s == "valida":
                stati["presente" if iv else "assente"] += 1
            tutte_valide &= s == "valida"
            if iv:
                em.append({"channel": c, "start": iv[0], "end": iv[1]})
        out[w["finestra"]] = {"valida": tutte_valide, "emessi": em}
    return out, stati


def misura(em: dict, gold: dict) -> dict:
    finestre = gold["finestre"]
    attacchi = {a["attacco"]: a for a in gold["attacchi"]}
    m1 = []
    for nome, a in attacchi.items():
        lg = a["end"] - a["start"]
        per_f = []
        for w in finestre:
            x = next((x for x in w["attacchi"] if x["attacco"] == nome and x["intero"]), None)
            if x is None:
                continue
            e = em[w["finestra"]]["emessi"]
            tocca = [i for i in e if lz.sovrapp(i["start"], i["end"], x["start"], x["end"])]
            per_f.append({"finestra": w["finestra"], "tocca": bool(tocca),
                          "centro_dentro": any(x["start"] <= (i["start"] + i["end"]) / 2 < x["end"] for i in e),
                          "canali_che_toccano": sorted({str(i["channel"]) for i in tocca}),
                          "p_caso": min(1.0, sum((i["end"] - i["start"] + lg - 1) / (L - (i["end"] - i["start"]) + 1) for i in e))})
        if not per_f:
            raise Fermo(f"{nome}: nessuna finestra che lo contenga per intero")
        q = 1.0
        for x in per_f:
            q *= 1 - x["p_caso"]
        canali_tocco = sorted({c for x in per_f for c in x["canali_che_toccano"]})
        m1.append({"attacco": nome, "durata_s": lg, "processi": a["processi"], "rilevato": any(x["tocca"] for x in per_f),
                   "rilevato_col_centro": any(x["centro_dentro"] for x in per_f), "p_caso": 1 - q,
                   "toccato_da_un_canale_del_suo_processo": any(c.split("_")[0] in a["processi"] for c in canali_tocco),
                   "finestre": per_f})
    ril = sum(x["rilevato"] for x in m1)
    p_val = p_coda([x["p_caso"] for x in m1], ril)
    pulite = [w for w in finestre if w["pulita"]]
    allarmi = [w for w in pulite if em[w["finestra"]]["emessi"]]
    con_att = [w for w in finestre if w["attacchi"]]
    toccano = n_int = 0
    atteso = 0.0
    for w in con_att:
        for i in em[w["finestra"]]["emessi"]:
            n_int += 1
            li = i["end"] - i["start"]
            toccano += any(lz.sovrapp(i["start"], i["end"], x["start"], x["end"]) for x in w["attacchi"])
            atteso += min(1.0, sum((li + x["end"] - x["start"] - 1) / (L - li + 1) for x in w["attacchi"]))
    m4 = [{"finestra": w["finestra"], "iou": lz.iou([(i["start"], i["end"]) for i in em[w["finestra"]]["emessi"]],
                                                   [(x["start"], x["end"]) for x in w["attacchi"]])} for w in con_att]
    canali = {}
    lunghezze = []
    for w in finestre:
        for i in em[w["finestra"]]["emessi"]:
            canali[str(i["channel"])] = canali.get(str(i["channel"]), 0) + 1
            lunghezze.append(i["end"] - i["start"])
    lunghezze.sort()
    per_processo = {}
    for p in ("P1", "P2", "P3"):
        xs = [x for x in m1 if p in x["processi"]]
        per_processo[p] = {"attacchi": len(xs), "rilevati": sum(x["rilevato"] for x in xs),
                           "attesi_a_caso": sum(x["p_caso"] for x in xs),
                           "toccati_da_un_canale_del_processo": sum(x["toccato_da_un_canale_del_suo_processo"] for x in xs)}
    met = len(pulite) / 2
    sopra = p_val < SOGLIA_P
    if len(allarmi) > met:
        esito, frase = "B", "segnala quasi ovunque: le rilevazioni non si leggono come prova"
    elif sopra:
        esito, frase = "A", "tace nella maggior parte delle finestre pulite e tocca gli attacchi più che a caso"
    else:
        esito, frase = "C", "tace nella maggior parte delle finestre pulite ma non tocca gli attacchi più che a caso"
    return {
        "M1_attacchi_rilevati": {"rilevati": ril, "su": len(m1), "col_centro": sum(x["rilevato_col_centro"] for x in m1),
                                 "attesi_a_caso": sum(x["p_caso"] for x in m1), "p_valore_una_coda": p_val,
                                 "per_attacco": m1},
        "concentrazione": {"sopra_il_caso": sopra, "soglia": SOGLIA_P,
                           "frase": ("gli intervalli cadono sugli attacchi più spesso che a caso" if sopra
                                     else "gli intervalli non cadono sugli attacchi più spesso che a caso")},
        "M2_falsi_allarmi": {"finestre_pulite_con_segnalazioni": len(allarmi), "finestre_pulite": len(pulite),
                             "di_cui_test": [len([w for w in allarmi if w["tipo"] == "test"]),
                                             len([w for w in pulite if w["tipo"] == "test"])],
                             "di_cui_training": [len([w for w in allarmi if w["tipo"] == "training"]),
                                                 len([w for w in pulite if w["tipo"] == "training"])],
                             "wilson95": lz.wilson(len(allarmi), len(pulite))},
        "finestre_con_attacchi_segnalate": [sum(bool(em[w["finestra"]]["emessi"]) for w in con_att), len(con_att)],
        "M3_precisione": {"intervalli_che_toccano_un_attacco": toccano, "intervalli_nelle_finestre_con_attacchi": n_int,
                          "attesi_a_caso": atteso},
        "M4_iou": m4,
        "per_processo": per_processo,
        "formato": {"finestre_valide": sum(em[w["finestra"]]["valida"] for w in finestre),
                    "finestre_senza_intervalli": sum(not em[w["finestra"]]["emessi"] for w in finestre),
                    "intervalli_emessi": len(lunghezze), "canali_citati": dict(sorted(canali.items())),
                    "lunghezza_intervalli": ({"min": lunghezze[0], "mediana": lunghezze[len(lunghezze) // 2],
                                              "max": lunghezze[-1]} if lunghezze else None)},
        "regola": "B: M2 > meta' delle pulite; A: M2 <= meta' e p(M1) < 0,05; C: altrimenti. M1-caso: per attacco "
                  "1 - prod_finestre(1 - min(1, sum_intervalli (l_i + l_g - 1)/(L - l_i + 1))); p esatto Poisson-binomiale",
        "esito_regola": esito, "frase": frase,
        "per_finestra": [{"finestra": w["finestra"], "pulita": w["pulita"], "attacchi": [x["attacco"] for x in w["attacchi"]],
                          "valida": em[w["finestra"]]["valida"], "emessi": em[w["finestra"]]["emessi"]} for w in finestre],
    }


def leggi(modo: str, dump: dict, gold: dict, canali: list[str]) -> dict:
    prima = lz.L  # le funzioni di lz leggono la L del modulo: la si mette a 32.768 e poi si rimette com'era
    lz.L = L
    try:
        return _leggi(modo, dump, gold, canali)
    finally:
        lz.L = prima


def _leggi(modo: str, dump: dict, gold: dict, canali: list[str]) -> dict:
    if gold.get("L") != L:
        raise Fermo(f"gold con L {gold.get('L')}")
    if modo == "mc":
        out = misura(emessi_mc(dump, gold, canali), gold)
        out["ruolo"] = "PRIMARIO: localize_all_channels, 16 canali"
    elif modo == "scan":
        em, stati = emessi_scan(dump, gold, canali)
        out = misura(em, gold)
        out["ruolo"] = "SECONDARIO: scansione dei 16 canali con localize a un canale"
        out["risposte_a_un_canale"] = stati
        out["per_canale"] = {}
        for c in canali:
            solo = {k: {"valida": v["valida"], "emessi": [e for e in v["emessi"] if e["channel"] == c]} for k, v in em.items()}
            x = misura(solo, gold)
            out["per_canale"][c] = {"M1": x["M1_attacchi_rilevati"]["rilevati"], "M1_caso": x["M1_attacchi_rilevati"]["attesi_a_caso"],
                                    "M2": x["M2_falsi_allarmi"]["finestre_pulite_con_segnalazioni"],
                                    "presente": sum(bool(v["emessi"]) for v in solo.values())}
    else:
        raise Fermo(f"modo {modo!r}")
    out["modo"] = modo
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modo", required=True, choices=("mc", "scan"))
    ap.add_argument("--dump", required=True, type=Path)
    ap.add_argument("--gold", required=True, type=Path)
    ap.add_argument("--composizione", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f"RIFIUTO: {a.out} esiste già")
    canali = json.loads(a.composizione.read_text(encoding="utf-8"))["canali"]
    try:
        out = leggi(a.modo, json.loads(a.dump.read_text(encoding="utf-8")), json.loads(a.gold.read_text(encoding="utf-8")), canali)
    except Fermo as e:
        raise SystemExit(f"FERMO: {e}")
    a.out.write_bytes((json.dumps(out, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    m1, m2, m3 = out["M1_attacchi_rilevati"], out["M2_falsi_allarmi"], out["M3_precisione"]
    print(f"{out['ruolo']}: esito {out['esito_regola']}: {out['frase']}")
    print(f"M1 {m1['rilevati']}/{m1['su']} (a caso {m1['attesi_a_caso']:.1f}, p {m1['p_valore_una_coda']:.3g}; col centro "
          f"{m1['col_centro']}); concentrazione: {out['concentrazione']['frase']}")
    print(f"M2 {m2['finestre_pulite_con_segnalazioni']}/{m2['finestre_pulite']} (test {m2['di_cui_test']}, training "
          f"{m2['di_cui_training']}); finestre con attacchi segnalate {out['finestre_con_attacchi_segnalate']}")
    print(f"M3 {m3['intervalli_che_toccano_un_attacco']}/{m3['intervalli_nelle_finestre_con_attacchi']} (a caso {m3['attesi_a_caso']:.1f})")
    print("formato", out["formato"])
    print("per processo", out["per_processo"])
    if "risposte_a_un_canale" in out:
        print("risposte a un canale", out["risposte_a_un_canale"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
