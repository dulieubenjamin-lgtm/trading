"""Alignement des unites de temps superieures sur l'unite de base.

A la bougie de base d'indice i, une unite superieure n'expose que sa derniere
bougie CLOSE. Utiliser celle en cours reviendrait a lire un indicateur qui n'a
pas sa valeur definitive : sur un graphique il "repeint" jusqu'a la fin de sa
periode. Un backtest qui l'ignore surestime systematiquement ses resultats.

La fin d'une bougie superieure est deduite du debut de la suivante, jamais d'une
duree fixe : les seances journalieres du forex ne durent pas 24 h autour du
week-end, et les blocs H4 ancres sur la seance sont tronques aux bords.
"""
from __future__ import annotations

from datetime import timedelta
from statistics import median


def duree_base(bougies) -> timedelta:
    """Duree d'une bougie de base, deduite des donnees plutot que configuree."""
    if len(bougies) < 3:
        raise ValueError("echantillon trop court pour deduire la duree de bougie")
    ecarts = [(b.ts - a.ts).total_seconds()
              for a, b in zip(bougies[:200], bougies[1:200])]
    return timedelta(seconds=median(ecarts))


def _fins(bougies_ht, derniere: timedelta) -> list:
    fins = [bougies_ht[j + 1].ts for j in range(len(bougies_ht) - 1)]
    fins.append(bougies_ht[-1].ts + derniere)
    return fins


def indices(base, bougies_ht, derniere=timedelta(hours=1)) -> list[int]:
    """Pour chaque bougie de base, l'indice de la derniere bougie HT close.

    -1 tant qu'aucune bougie HT n'est close.

    La comparaison se fait sur la FIN de la bougie de base : une M15 qui se
    cloture en meme temps que la M5 courante est disponible des cet instant.
    Comparer sur le debut la rendrait indisponible pendant 5 minutes de plus,
    et decalerait chaque setup d'une bougie.
    """
    if not bougies_ht:
        return [-1] * len(base)
    pas = duree_base(base)
    fins = _fins(bougies_ht, derniere)
    sortie, j = [-1] * len(base), -1
    for i, b in enumerate(base):
        fin_base = b.ts + pas
        while j + 1 < len(fins) and fins[j + 1] <= fin_base:
            j += 1
        sortie[i] = j
    return sortie


def aligner(base, bougies_ht, serie_ht, derniere=timedelta(hours=1)):
    """Serie HT projetee sur l'index de base, valeur de la derniere HT close."""
    if len(bougies_ht) != len(serie_ht):
        raise ValueError("serie_ht et bougies_ht de longueurs differentes")
    idx = indices(base, bougies_ht, derniere)
    return [serie_ht[j] if j >= 0 else None for j in idx]
