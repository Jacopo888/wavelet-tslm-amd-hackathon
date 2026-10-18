import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "tools"))
import leggi_localize_canale as lc  # noqa: E402

GOLD = json.loads((BASE / "datasets_cluster" / "GOLD.json").read_text(encoding="utf-8"))
FIN = {f["finestra"]: f for f in GOLD["finestre"]}


def dump(fun):
    return {"records": [{"id": f"metropt3-loc-w{w:02d}-{c}", "category": "localize", "pred": fun(w, c)}
                        for w in FIN for c in lc.CANALI]}


def assente(w, c):
    return " localize:" + json.dumps({"_L": 131072, "present": False})


def test_righe_e_tutto_assente():
    out = lc.leggi(dump(assente), GOLD)
    assert out["risposte_a_un_canale"] == {"righe": 161, "valide": 161, "assente": 161, "presente": 0}
    assert out["esito_regola"] == "C"
    assert all(v["assente"] == 23 for v in out["per_canale"].values())


def test_un_canale_che_vede_i_guasti():
    def f(w, c):
        g = FIN[w]["guasti"]
        if c == "TP3" and g:
            return "localize:" + json.dumps({"_L": 131072, "present": True, "start": g[0]["start"] + 5, "end": g[0]["start"] + 300})
        return assente(w, c)
    out = lc.leggi(dump(f), GOLD)
    assert out["M1_guasti_rilevati"]["rilevati"] >= 3
    assert out["M2_falsi_allarmi"]["finestre_pulite_con_segnalazioni"] == 0
    assert out["esito_regola"] == "A"
    assert out["per_canale"]["TP3"]["M1"] >= 3 and out["per_canale"]["TP2"]["M1"] == 0


def test_un_canale_che_segnala_sempre_basta_per_B():
    def f(w, c):
        if c == "Motor_current":
            return "localize:" + json.dumps({"_L": 131072, "present": True, "start": 10, "end": 50})
        return assente(w, c)
    out = lc.leggi(dump(f), GOLD)
    assert out["esito_regola"] == "B"
    assert out["per_canale"]["Motor_current"]["M2"] == 15 and out["per_canale"]["TP2"]["M2"] == 0


def test_non_valide_e_fermo():
    out = lc.leggi(dump(lambda w, c: "boh" if c == "H1" else assente(w, c)), GOLD)
    assert out["per_canale"]["H1"]["non_valide"] == 23
    d = dump(assente)
    d["records"].pop()
    with pytest.raises(lc.lz.Fermo):
        lc.leggi(d, GOLD)


def test_indicatori_su_L_16384():
    import leggi_zeroshot_metropt3 as lz
    gold = json.loads((BASE / "datasets_hi_v2" / "GOLD_HI.json").read_text(encoding="utf-8"))
    can = ("quota_carico", "cicli_ora", "calo_TP3", "TP3_medio", "olio_medio", "corrente_media")
    vecchio = lz.L
    lz.L = 16384
    try:
        fin = {f["finestra"]: f for f in gold["finestre"]}
        def pred(w, c):
            g = fin[w]["guasti"]
            if c == "TP3_medio" and g:
                return "localize:" + json.dumps({"_L": 16384, "present": True, "start": g[0]["start"], "end": g[0]["start"] + 50})
            return "localize:" + json.dumps({"_L": 16384, "present": False})
        d = {"records": [{"id": f"metropt3-hia-w{w:02d}-{c}", "category": "localize", "pred": pred(w, c)} for w in fin for c in can]}
        out = lc.leggi(d, gold, can, "hia")
        assert out["risposte_a_un_canale"]["righe"] == 90
        assert out["M2_falsi_allarmi"]["finestre_pulite"] == 7
        assert out["M1_guasti_rilevati"]["rilevati"] >= 3 and out["esito_regola"] == "A"
    finally:
        lz.L = vecchio
