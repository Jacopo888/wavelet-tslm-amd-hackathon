#!/usr/bin/env python3
"""Aggiunge alla porta ``conferma.py`` della COPIA ``code_metropt3`` i tre insiemi di MetroPT-3 col loro pin, e scrive il
config ``configs/metropt3_c1.toml`` (= ``va1s4locr2e_polimi.toml`` col solo ``run_root`` nella cartella dell'hackathon).
Conserva i fine riga CRLF di ``conferma.py``.  Rifiuta se trova la porta già estesa o un ancoraggio non unico.

    python porta_metropt3.py <code_metropt3> <sha_p15> <sha_a7> <sha_fumo>
"""
import re
import sys
from pathlib import Path

RUN_ROOT_VECCHIO = 'run_root = "/work/u10970284/wavelet-tslm-rope-ablation/runs"'
RUN_ROOT_NUOVO = 'run_root = "/work/u10970284/hackathon-amd-act3/runs"'


def sost(x: str, a: str, b: str) -> str:
    if x.count(a) != 1:
        raise SystemExit(f"ancoraggio non unico ({x.count(a)}): {a[:70]!r}")
    return x.replace(a, b)


def main() -> int:
    code, p15, a7, fumo = Path(sys.argv[1]), *sys.argv[2:5]
    for s in (p15, a7, fumo):
        if not re.fullmatch(r"[0-9a-f]{64}", s):
            raise SystemExit(f"sha non valido: {s!r}")
    p = code / "src/wavelet_rope/conferma.py"
    x = p.read_bytes().decode("utf-8")
    if "metropt3" in x:
        raise SystemExit("la porta contiene già metropt3")
    if "\r\n" not in x or x.count("\n") != x.count("\r\n"):
        raise SystemExit("conferma.py non è tutto CRLF")
    n = "\r\n"
    i = x.index('SHA_OOD_A = "62a9769e0bfde10fc01767629181980f6e4792a3dd5c4b7507a8e4b226c589d7"')
    riga_a = x[i: x.index(n, i)]
    x = sost(x, riga_a + n, riga_a + n
             + f'SHA_METROPT3_P15 = "{p15}"   # hackathon AMD ACT III, 15/10: zero-shot su MetroPT-3, 15 segnali' + n
             + f'SHA_METROPT3_A7 = "{a7}"    # hackathon AMD ACT III, 15/10: i 7 segnali analogici' + n
             + f'SHA_METROPT3_FUMO = "{fumo}"  # hackathon AMD ACT III, 15/10: fumo, rumore con la stessa struttura' + n)
    x = sost(x, '"ood_b": 394, "ood_a": 394}', '"ood_b": 394, "ood_a": 394,' + n
             + '         "metropt3_p15": 23, "metropt3_a7": 23, "metropt3_fumo": 2}')
    x = sost(x, '"ood_a": ("WR_OOD_A_PARQUET", "SHA_OOD_A")}', '"ood_a": ("WR_OOD_A_PARQUET", "SHA_OOD_A"),' + n
             + '                       "metropt3_p15": ("WR_METROPT3_P15_PARQUET", "SHA_METROPT3_P15"),' + n
             + '                       "metropt3_a7": ("WR_METROPT3_A7_PARQUET", "SHA_METROPT3_A7"),' + n
             + '                       "metropt3_fumo": ("WR_METROPT3_FUMO_PARQUET", "SHA_METROPT3_FUMO")}')
    if x.count("\n") != x.count("\r\n"):
        raise SystemExit("patch difettosa")
    p.write_bytes(x.encode("utf-8"))
    c = code / "configs/va1s4locr2e_polimi.toml"
    t = c.read_bytes().decode("utf-8")
    nuovo = code / "configs/metropt3_c1.toml"
    if nuovo.exists():
        raise SystemExit(f"{nuovo} esiste già")
    nuovo.write_bytes(sost(t, RUN_ROOT_VECCHIO, RUN_ROOT_NUOVO).encode("utf-8"))
    print("porta estesa e config scritto")
    return 0


if __name__ == "__main__":
    sys.exit(main())
