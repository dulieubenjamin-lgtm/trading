"""Fusionne des blocs CSV Twelve Data dans le cache disque.

Usage :
    python3 outils/alimenter_cache.py donnees/cache/XAUUSD-M15.csv < bloc.csv

Le cache est la seule source du harnais. On l'alimente par lots au fil des
appels a l'API, en fusionnant sans doublon : le quota gratuit est de 800 appels
par jour et un backtest doit rester reproductible a l'identique.

Les etiquettes sont conservees TELLES QUELLES (heure de Sydney). La conversion
vers UTC est faite a la lecture, une seule fois, par harnais/cache.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

EN_TETE = "datetime;open;high;low;close"


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    cible = Path(sys.argv[1])
    cible.parent.mkdir(parents=True, exist_ok=True)

    lignes: dict[str, str] = {}
    if cible.exists():
        for ligne in cible.read_text(encoding="utf-8").splitlines():
            if ligne.strip() and not ligne.startswith("datetime"):
                lignes[ligne.split(";")[0]] = ligne
    avant = len(lignes)

    conflits = 0
    for ligne in sys.stdin.read().splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("datetime") or ligne.startswith("{"):
            continue
        cle = ligne.split(";")[0]
        if cle in lignes and lignes[cle] != ligne:
            conflits += 1
        lignes[cle] = ligne

    ordonnees = [lignes[k] for k in sorted(lignes)]
    cible.write_text("\n".join([EN_TETE] + ordonnees) + "\n", encoding="utf-8")

    print(f"{cible} : {avant} -> {len(lignes)} bougies "
          f"(+{len(lignes) - avant})")
    if ordonnees:
        print(f"  couverture : {ordonnees[0].split(';')[0]} -> "
              f"{ordonnees[-1].split(';')[0]} (heure Sydney)")
    if conflits:
        print(f"  ATTENTION : {conflits} bougie(s) redefinie(s) avec des valeurs "
              f"differentes — l'API a revise son historique")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
