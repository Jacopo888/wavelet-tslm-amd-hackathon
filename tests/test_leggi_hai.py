import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "tools"))
import leggi_hai as lh  # noqa: E402

GOLD = json.loads((BASE / "datasets_hai" / "GOLD_HAI.json").read_text(encoding="utf-8"))
CANALI = json.loads((BASE / "datasets_hai" / "COMPOSIZIONE_HAI.json").read_text(encoding="utf-8"))["canali"]
FIN = {w["finestra"]: w for w in GOLD["finestre"]}


def dump_mc(fun):
    return {"records": [{"id": f"hai-mc-{w}", "category": "localize_all_channels",
                         "pred": " localize_all_channels:" + json.dumps({"_L": 32768, "anomalies": fun(w)})} for w in FIN]}


def dump_scan(fun):
    return {"records": [{"id": f"hai-loc-{w}-{c}", "category": "localize", "pred": "localize:" + json.dumps(fun(w, c))}
                        for w in FIN for c in CANALI]}


def test_composizione_attesa():
    assert len(FIN) == 38 and len(GOLD["attacchi"]) == 50 and len(CANALI) == 16
    assert sum(w["pulita"] for w in FIN.values()) == 18


def test_p_coda():
    assert lh.p_coda([0.5, 0.5], 1) == pytest.approx(0.75)
    assert lh.p_coda([0.1] * 3, 0) == pytest.approx(1.0)
    assert lh.p_coda([0.2, 0.3], 2) == pytest.approx(0.06)


def test_mc_vuoto_e_C():
    out = lh.leggi("mc", dump_mc(lambda w: []), GOLD, CANALI)
    assert out["esito_regola"] == "C"
    assert out["M1_attacchi_rilevati"]["rilevati"] == 0 and out["M2_falsi_allarmi"]["finestre_pulite_con_segnalazioni"] == 0
    assert out["formato"]["finestre_valide"] == 38


def test_mc_perfetto_e_A():
    out = lh.leggi("mc", dump_mc(lambda w: [{"channel": "ch_00", "start": x["start"], "end": x["end"]}
                                            for x in FIN[w]["attacchi"]]), GOLD, CANALI)
    m1 = out["M1_attacchi_rilevati"]
    assert m1["rilevati"] == 50 and m1["col_centro"] == 50 and m1["p_valore_una_coda"] < 1e-10
    assert out["esito_regola"] == "A" and out["concentrazione"]["sopra_il_caso"]
    assert out["M3_precisione"]["intervalli_che_toccano_un_attacco"] == out["M3_precisione"]["intervalli_nelle_finestre_con_attacchi"]
    assert out["formato"]["canali_citati"] == {CANALI[0]: out["formato"]["intervalli_emessi"]}


def test_mc_ovunque_e_B():
    out = lh.leggi("mc", dump_mc(lambda w: [{"channel": "ch_03", "start": 100, "end": 250}]), GOLD, CANALI)
    assert out["esito_regola"] == "B"
    assert out["M2_falsi_allarmi"]["finestre_pulite_con_segnalazioni"] == 18


def test_mc_riga_mancante_si_ferma():
    d = dump_mc(lambda w: [])
    d["records"].pop()
    with pytest.raises(lh.Fermo):
        lh.leggi("mc", d, GOLD, CANALI)


def test_mc_risposta_non_valida_conta_come_nessun_intervallo():
    d = dump_mc(lambda w: [])
    d["records"][0]["pred"] = "boh"
    out = lh.leggi("mc", d, GOLD, CANALI)
    assert out["formato"]["finestre_valide"] == 37


def test_scan_perfetto_su_un_canale():
    def f(w, c):
        a = FIN[w]["attacchi"]
        if c == CANALI[1] and a:
            return {"_L": 32768, "present": True, "start": a[0]["start"], "end": a[0]["end"]}
        return {"_L": 32768, "present": False}
    out = lh.leggi("scan", dump_scan(f), GOLD, CANALI)
    assert out["risposte_a_un_canale"]["righe"] == 608 and out["risposte_a_un_canale"]["presente"] == 20
    assert out["M2_falsi_allarmi"]["finestre_pulite_con_segnalazioni"] == 0
    assert out["M1_attacchi_rilevati"]["rilevati"] >= 15
    assert out["per_canale"][CANALI[1]]["presente"] == 20 and out["per_canale"][CANALI[0]]["presente"] == 0


def test_scan_tutto_presente_e_B():
    out = lh.leggi("scan", dump_scan(lambda w, c: {"_L": 32768, "present": True, "start": 0, "end": 200}), GOLD, CANALI)
    assert out["esito_regola"] == "B" and out["risposte_a_un_canale"]["presente"] == 608
