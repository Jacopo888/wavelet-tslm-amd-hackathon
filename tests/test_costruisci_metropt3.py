import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import costruisci_metropt3 as c  # noqa: E402


def test_finestre_sulla_lunghezza_vera():
    inizi = c.inizi_finestre(1_516_948)
    assert len(inizi) == 23
    assert inizi[:3] == [0, 65536, 131072]
    assert inizi[21] == 21 * 65536
    assert inizi[-1] == 1_516_948 - c.L
    assert all(b - a <= c.PASSO for a, b in zip(inizi, inizi[1:]))


def test_finestre_senza_coda():
    assert c.inizi_finestre(c.L + c.PASSO) == [0, c.PASSO]
    with pytest.raises(ValueError):
        c.inizi_finestre(c.L - 1)


def test_ogni_evento_corto_sta_intero_in_una_finestra():
    n = 1_516_948
    inizi = c.inizi_finestre(n)
    for s in range(0, n - 19000, 7919):
        e = s + 19000
        assert any(a <= s and e <= a + c.L for a in inizi)


def test_gold_su_tempi_sintetici():
    tempi = np.datetime64("2020-04-01T00:00:00") + np.arange(0, 1_200_000, dtype="int64").astype("timedelta64[s]") * 10
    inizi = c.inizi_finestre(len(tempi))
    g = c.gold(tempi, inizi)
    g1 = g["guasti"][0]
    assert str(tempi[g1["start"]]) == "2020-04-18T00:00:00"
    assert tempi[g1["end"] - 1] <= np.datetime64("2020-04-18T23:59:00") < tempi[g1["end"]]
    assert g1["zona_sospetta"][0] == g1["start"]
    for f in g["finestre"]:
        for x in f["guasti"]:
            assert 0 <= x["start"] < x["end"] <= c.L
        assert f["pulita"] == (not any(c.sovrapposti(f["inizio_indice"], f["fine_indice"], *x["zona_sospetta"]) for x in g["guasti"]))
    assert any(any(x["intero"] for x in f["guasti"]) for f in g["finestre"])


def test_riga_ha_risposta_vuota_e_domanda_con_L_e_C():
    modello = "Find every anomaly. (Here L = {L}, C = {C}.)"
    tipo = {"tier": 3, "n_channels_a": 0, "n_channels_b": 0, "coupling_kind": None, "coupling_lag": None}
    r = c.riga("x", [np.zeros(c.L), np.ones(c.L)], modello, tipo)
    assert r["question"].endswith("(Here L = 131072, C = 2.)")
    assert r["answer"] == 'localize_all_channels:{"_L": 131072, "anomalies": []}'
    assert r["channel_names"] == ["ch_00", "ch_01"]
    assert r["injection_starts"] == [] and r["n_channels"] == 2 and len(r["channel_values"][1]) == c.L
