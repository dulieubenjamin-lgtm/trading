"""Alignement d'une serie d'unite de temps superieure sur les bougies M15.

A la bougie M15 d'indice i, la valeur H1 (ou journaliere) exposee est celle de la
derniere bougie superieure **cloturee**. Utiliser celle en cours reviendrait a
lire un indicateur qui n'a pas sa valeur definitive : sur un graphique il
"repeint" jusqu'a la cloture de la periode. Un backtest qui l'ignore surestime
systematiquement ses resultats.

La fin d'une bougie superieure est deduite du debut de la suivante, et non d'une
duree fixe : les seances journalieres du forex ne durent pas 24 h autour du
week-end, et une duree fixe rendrait la derniere seance de la semaine
exploitable trop tot.
"""
from __future__ import annotations

from datetime import timedelta


def aligner(bougies_m15, bougies_ht, serie_ht, duree_derniere=timedelta(hours=1)):
    if len(bougies_ht) != len(serie_ht):
        raise ValueError("serie_ht et bougies_ht de longueurs differentes")
    if not bougies_ht:
        return [None] * len(bougies_m15)

    fins = [bougies_ht[j + 1].ts for j in range(len(bougies_ht) - 1)]
    fins.append(bougies_ht[-1].ts + duree_derniere)

    sortie, j = [None] * len(bougies_m15), -1
    for i, b in enumerate(bougies_m15):
        while j + 1 < len(fins) and fins[j + 1] <= b.ts:
            j += 1
        sortie[i] = serie_ht[j] if j >= 0 else None
    return sortie
