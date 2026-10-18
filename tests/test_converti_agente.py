import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import converti_agente as ca  # noqa: E402


def parser_finto(testo, richieste):
    try:
        x = json.loads(testo)
    except json.JSONDecodeError:
        return None
    return x if isinstance(x, dict) and richieste <= set(x) else None


def test_ordine_e_risposte():
    ordine = ["w02", "w00", "w01"]
    righe = [
        {"example_id": 1, "model_answer": '{"anomalies": []}', "num_turns": 3, "seconds": 10.0, "error": None},
        {"example_id": 0, "model_answer": '{"anomalies": [{"channel": "ch_01", "start": 5, "end": 9}]}', "num_turns": 4},
        {"example_id": 2, "model_answer": "non lo so", "num_turns": 15, "error": None},
    ]
    out = ca.converti(righe, ordine, parser_finto)
    r = {x["id"]: x for x in out["records"]}
    assert r["w02"]["pred"] == 'localize_all_channels:{"anomalies": [{"channel": "ch_01", "end": 9, "start": 5}]}'
    assert r["w00"]["pred"] == 'localize_all_channels:{"anomalies": []}'
    assert r["w01"]["pred"] == ""
    assert [x["id"] for x in out["records"]] == ordine


def test_fermo_se_manca_o_si_ripete():
    with pytest.raises(SystemExit):
        ca.converti([{"example_id": 0, "model_answer": ""}], ["a", "b"], parser_finto)
    with pytest.raises(SystemExit):
        ca.converti([{"example_id": 0}, {"example_id": 0}], ["a", "b"], parser_finto)
