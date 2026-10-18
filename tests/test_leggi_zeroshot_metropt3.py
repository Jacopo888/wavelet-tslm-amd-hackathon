import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "tools"))
import leggi_zeroshot_metropt3 as lz  # noqa: E402

GOLD = json.loads((BASE / "datasets_cluster" / "GOLD.json").read_text(encoding="utf-8"))


def pred(anomalie):
    return " localize_all_channels:" + json.dumps({"_L": lz.L, "anomalies": anomalie})


def dump(fun, insieme="p15"):
    return {"records": [{"id": f"metropt3-{insieme}-w{f['finestra']:02d}", "category": "localize_all_channels",
                         "pred": fun(f)} for f in GOLD["finestre"]], "summary": {}}


def test_gold_vero_ha_23_finestre_e_15_pulite():
    assert len(GOLD["finestre"]) == 23
    assert sum(f["pulita"] for f in GOLD["finestre"]) == 15


def test_tutto_vuoto_esito_C():
    out = lz.leggi(dump(lambda f: pred([])), GOLD, "p15")
    assert out["M1_guasti_rilevati"]["rilevati"] == 0
    assert out["M2_falsi_allarmi"]["finestre_pulite_con_segnalazioni"] == 0
    assert out["esito_regola"] == "C"
    assert out["formato"]["valide"] == 23 and out["formato"]["liste_vuote"] == 23


def test_colpi_giusti_solo_dove_ci_sono_guasti_esito_A():
    def f(fin):
        return pred([{"channel": "ch_02", "start": x["start"] + 10, "end": x["start"] + 200} for x in fin["guasti"]])
    out = lz.leggi(dump(f), GOLD, "p15")
    assert out["M1_guasti_rilevati"]["rilevati"] == 4
    assert out["M1_guasti_rilevati"]["col_centro"] == 4
    assert out["M2_falsi_allarmi"]["finestre_pulite_con_segnalazioni"] == 0
    assert out["esito_regola"] == "A"
    assert out["M1_guasti_rilevati"]["attesi_a_caso"] < 1
    assert out["M3_precisione"]["emessi_che_toccano_una_zona_sospetta"] == out["M3_precisione"]["emessi"]


def test_segnala_ovunque_esito_B():
    out = lz.leggi(dump(lambda f: pred([{"channel": "ch_00", "start": 100, "end": 300}])), GOLD, "p15")
    assert out["M2_falsi_allarmi"]["finestre_pulite_con_segnalazioni"] == 15
    assert out["esito_regola"] == "B"


def test_risposta_rotta_conta_come_non_valida():
    def f(fin):
        return "localize_all_channels:{non json" if fin["finestra"] == 3 else pred([])
    out = lz.leggi(dump(f), GOLD, "p15")
    assert out["formato"]["valide"] == 22


def test_fermo_se_manca_una_riga_o_un_campo():
    d = dump(lambda f: pred([]))
    d["records"].pop()
    with pytest.raises(lz.Fermo):
        lz.leggi(d, GOLD, "p15")
    d = dump(lambda f: pred([]))
    del d["records"][0]["pred"]
    with pytest.raises(lz.Fermo):
        lz.leggi(d, GOLD, "p15")
    with pytest.raises(lz.Fermo):
        lz.leggi(dump(lambda f: pred([]), insieme="a7"), GOLD, "p15")


def test_caso_e_unione():
    assert lz.p_caso([{"start": 0, "end": 1}], 1) == pytest.approx(1 / lz.L)
    assert lz.p_caso([{"start": 0, "end": lz.L}], 10) == 1.0
    assert lz.iou([(0, 10), (5, 20)], [(0, 20)]) == 1.0
    assert lz.iou([(0, 10)], [(10, 20)]) == 0.0
    assert lz.wilson(0, 15)[0] == 0.0
