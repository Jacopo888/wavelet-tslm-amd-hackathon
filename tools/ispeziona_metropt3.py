"""Ispezione di MetroPT-3: colonne, righe, passo di campionamento, buchi, intervalli per colonna.

Solo libreria standard. Il file è un download non fidato: si esegue con `python -I` e il percorso arriva come argomento.
"""
import csv
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

FORMATO = "%Y-%m-%d %H:%M:%S"


def ispeziona(percorso: Path) -> dict:
    passi = Counter()
    buchi = []
    stat = {}
    righe = 0
    primo = ultimo = precedente = None
    fuori_ordine = 0
    with percorso.open(newline="", encoding="utf-8") as f:
        lettore = csv.reader(f)
        intestazione = next(lettore)
        i_tempo = intestazione.index("timestamp")
        colonne = [(i, n) for i, n in enumerate(intestazione) if i != i_tempo and n]
        for _, n in colonne:
            stat[n] = {"min": float("inf"), "max": float("-inf"), "somma": 0.0, "n": 0, "non_numerici": 0, "valori": set()}
        for riga in lettore:
            righe += 1
            t = datetime.strptime(riga[i_tempo], FORMATO)
            if primo is None:
                primo = t
            if precedente is not None:
                d = (t - precedente).total_seconds()
                if d <= 0:
                    fuori_ordine += 1
                passi[d] += 1
                if d > 600:
                    buchi.append((precedente.strftime(FORMATO), t.strftime(FORMATO), d))
            precedente = ultimo = t
            for i, n in colonne:
                s = stat[n]
                try:
                    v = float(riga[i])
                except ValueError:
                    s["non_numerici"] += 1
                    continue
                s["n"] += 1
                s["somma"] += v
                if v < s["min"]:
                    s["min"] = v
                if v > s["max"]:
                    s["max"] = v
                if len(s["valori"]) <= 12:
                    s["valori"].add(v)
    for n, s in stat.items():
        s["media"] = s["somma"] / s["n"] if s["n"] else None
        distinti = s.pop("valori")
        s["distinti"] = sorted(distinti) if len(distinti) <= 12 else "più di 12"
        del s["somma"]
    return {
        "file": percorso.name,
        "intestazione": intestazione,
        "righe": righe,
        "primo": primo.strftime(FORMATO),
        "ultimo": ultimo.strftime(FORMATO),
        "durata_giorni": (ultimo - primo).total_seconds() / 86400,
        "passi_piu_frequenti_s": passi.most_common(12),
        "passi_non_positivi": fuori_ordine,
        "buchi_oltre_10_min": len(buchi),
        "buchi_piu_lunghi": sorted(buchi, key=lambda b: -b[2])[:15],
        "colonne": stat,
    }


if __name__ == "__main__":
    esito = ispeziona(Path(sys.argv[1]))
    uscita = Path(sys.argv[2])
    if uscita.exists():
        sys.exit(f"rifiuto: {uscita} esiste già")
    uscita.write_text(json.dumps(esito, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in esito.items() if k != "colonne"}, indent=1, ensure_ascii=False))
    for n, s in esito["colonne"].items():
        print(f"{n:18s} n={s['n']:8d} min={s['min']:.4g} max={s['max']:.4g} media={s['media']:.4g} distinti={s['distinti']}")
