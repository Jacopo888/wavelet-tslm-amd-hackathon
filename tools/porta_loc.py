#!/usr/bin/env python3
"""Aggiunge alla porta ``conferma.py`` della copia ``code_metropt3`` (già estesa con metropt3_p15/a7/fumo) i due
insiemi a un canale, ``metropt3_loc`` (161 righe) e ``metropt3_locfumo`` (2), col loro pin.  Conserva i CRLF.
Rifiuta se la porta li contiene già o se un ancoraggio non è unico.

    python porta_loc.py <code_metropt3> <sha_loc> <sha_locfumo>
"""
import re
import sys
from pathlib import Path


def sost(x: str, a: str, b: str) -> str:
    if x.count(a) != 1:
        raise SystemExit(f"ancoraggio non unico ({x.count(a)}): {a[:70]!r}")
    return x.replace(a, b)


def main() -> int:
    code, loc, fumo = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    for s in (loc, fumo):
        if not re.fullmatch(r"[0-9a-f]{64}", s):
            raise SystemExit(f"sha non valido: {s!r}")
    p = code / "src/wavelet_rope/conferma.py"
    x = p.read_bytes().decode("utf-8")
    if "metropt3_loc" in x:
        raise SystemExit("la porta contiene già metropt3_loc")
    if x.count("\n") != x.count("\r\n"):
        raise SystemExit("conferma.py non è tutto CRLF")
    n = "\r\n"
    i = x.index('SHA_METROPT3_FUMO = "')
    riga = x[i: x.index(n, i)]
    x = sost(x, riga + n, riga + n
             + f'SHA_METROPT3_LOC = "{loc}"   # hackathon, 15/10 sera: localize a un canale, 23 finestre x 7 analogici' + n
             + f'SHA_METROPT3_LOCFUMO = "{fumo}"  # hackathon, 15/10 sera: fumo a un canale' + n)
    x = sost(x, '"metropt3_p15": 23, "metropt3_a7": 23, "metropt3_fumo": 2}',
             '"metropt3_p15": 23, "metropt3_a7": 23, "metropt3_fumo": 2,' + n
             + '         "metropt3_loc": 161, "metropt3_locfumo": 2}')
    x = sost(x, '"metropt3_fumo": ("WR_METROPT3_FUMO_PARQUET", "SHA_METROPT3_FUMO")}',
             '"metropt3_fumo": ("WR_METROPT3_FUMO_PARQUET", "SHA_METROPT3_FUMO"),' + n
             + '                       "metropt3_loc": ("WR_METROPT3_LOC_PARQUET", "SHA_METROPT3_LOC"),' + n
             + '                       "metropt3_locfumo": ("WR_METROPT3_LOCFUMO_PARQUET", "SHA_METROPT3_LOCFUMO")}')
    if x.count("\n") != x.count("\r\n"):
        raise SystemExit("patch difettosa")
    p.write_bytes(x.encode("utf-8"))
    print("porta estesa con metropt3_loc e metropt3_locfumo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
