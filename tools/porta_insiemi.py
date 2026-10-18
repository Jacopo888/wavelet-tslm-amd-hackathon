#!/usr/bin/env python3
"""Aggiunge alla porta ``conferma.py`` della copia ``code_metropt3`` (estesa con metropt3_p15/a7/fumo) altri insiemi,
ciascuno con righe e sha: ``python porta_insiemi.py <code_metropt3> nome:righe:sha [nome:righe:sha ...]``.
Variabile d'ambiente del percorso ``WR_<NOME>_PARQUET``, costante ``SHA_<NOME>``.  Conserva i CRLF; rifiuta se un
insieme c'è già o se un ancoraggio non è unico."""
import re
import sys
from pathlib import Path


def sost(x: str, a: str, b: str) -> str:
    if x.count(a) != 1:
        raise SystemExit(f"ancoraggio non unico ({x.count(a)}): {a[:70]!r}")
    return x.replace(a, b)


def main() -> int:
    code = Path(sys.argv[1])
    insiemi = []
    for arg in sys.argv[2:]:
        nome, righe, sha = arg.split(":")
        if not re.fullmatch(r"metropt3_[a-z0-9]+", nome) or not re.fullmatch(r"[0-9a-f]{64}", sha) or not righe.isdigit():
            raise SystemExit(f"argomento non valido: {arg!r}")
        insiemi.append((nome, int(righe), sha))
    p = code / "src/wavelet_rope/conferma.py"
    x = p.read_bytes().decode("utf-8")
    if x.count("\n") != x.count("\r\n"):
        raise SystemExit("conferma.py non è tutto CRLF")
    for nome, _, _ in insiemi:
        if f'"{nome}"' in x:
            raise SystemExit(f"la porta contiene già {nome}")
    n = "\r\n"
    i = x.index('SHA_METROPT3_FUMO = "')
    riga = x[i: x.index(n, i)]
    x = sost(x, riga + n, riga + n + "".join(
        f'SHA_{nome.upper()} = "{sha}"   # hackathon, 15/10 notte: indicatori e adattamento' + n for nome, _, sha in insiemi))
    x = sost(x, '"metropt3_p15": 23, "metropt3_a7": 23, "metropt3_fumo": 2}',
             '"metropt3_p15": 23, "metropt3_a7": 23, "metropt3_fumo": 2,' + n
             + "         " + ", ".join(f'"{nome}": {r}' for nome, r, _ in insiemi) + "}")
    x = sost(x, '"metropt3_fumo": ("WR_METROPT3_FUMO_PARQUET", "SHA_METROPT3_FUMO")}',
             '"metropt3_fumo": ("WR_METROPT3_FUMO_PARQUET", "SHA_METROPT3_FUMO"),' + n
             + ("," + n).join(f'                       "{nome}": ("WR_{nome.upper()}_PARQUET", "SHA_{nome.upper()}")'
                               for nome, _, _ in insiemi) + "}")
    if x.count("\n") != x.count("\r\n"):
        raise SystemExit("patch difettosa")
    p.write_bytes(x.encode("utf-8"))
    print("porta estesa con", ", ".join(nome for nome, _, _ in insiemi))
    return 0


if __name__ == "__main__":
    sys.exit(main())
