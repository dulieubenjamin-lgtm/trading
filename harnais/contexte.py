"""Construction des series exposees aux setups, toutes causales et alignees."""
from __future__ import annotations

from datetime import timedelta

from . import agregation, alignement, indicateurs, seances


def construire(bougies, regime="paris") -> dict:
    reg = seances.REGIMES[regime]
    series: dict[str, list] = {}

    series["atr_m15"] = indicateurs.atr(bougies, 14)
    series["ema50_m15"] = indicateurs.ema([b.cloture for b in bougies], 50)
    _, _, series["macd_hist"] = indicateurs.macd(bougies)

    h1 = agregation.en_h1(bougies)
    adx_h1, _, _ = indicateurs.adx(h1, 14)
    series["adx_h1"] = alignement.aligner(bougies, h1, adx_h1)
    series["ema50_h1"] = alignement.aligner(
        bougies, h1, indicateurs.ema([b.cloture for b in h1], 50))

    jours = agregation.en_journalier(bougies)
    series["atr_d1"] = alignement.aligner(
        bougies, jours, indicateurs.atr(jours, 14), timedelta(days=1))

    series["range_haut"], series["range_bas"] = _range_asiatique(bougies, reg, regime)
    series["plus_haut_5j"], series["plus_bas_5j"] = _extremes_5_seances(bougies, jours)
    return series


def _range_asiatique(bougies, reg, regime):
    """Plus haut / plus bas de la fenetre asiatique, disponible une fois close.

    Causalite : la valeur n'est exposee qu'a partir de la fin de la fenetre. Avant,
    elle est None — un setup ne peut donc pas connaitre le range en cours de
    formation.
    """
    fenetre = reg["range_asiatique"]
    hauts, bas = [None] * len(bougies), [None] * len(bougies)
    if fenetre is None:
        return hauts, bas

    accumule: dict[str, list] = {}
    for i, b in enumerate(bougies):
        jour = seances.date_locale(b.ts, regime)
        if seances.dans_fenetre(b.ts, fenetre, regime):
            h, l = accumule.get(jour, (None, None))
            accumule[jour] = (b.haut if h is None else max(h, b.haut),
                              b.bas if l is None else min(l, b.bas))
        elif seances.locale(b.ts, regime).time() >= fenetre[1]:
            h, l = accumule.get(jour, (None, None))
            hauts[i], bas[i] = h, l
    return hauts, bas


def _extremes_5_seances(bougies, jours):
    """Plus haut / plus bas des 5 seances forex PRECEDENTES (jamais celle en cours)."""
    hauts, bas = [None] * len(bougies), [None] * len(bougies)
    cles = [agregation.seance_forex(j.ts) for j in jours]
    index = {c: k for k, c in enumerate(cles)}

    for i, b in enumerate(bougies):
        k = index.get(agregation.seance_forex(b.ts))
        if k is None or k < 5:
            continue
        precedentes = jours[k - 5:k]
        hauts[i] = max(j.haut for j in precedentes)
        bas[i] = min(j.bas for j in precedentes)
    return hauts, bas
