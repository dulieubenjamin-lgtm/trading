"""Construction du contexte multi-unites expose aux setups.

Repartition des roles, decidee pour ne PAS empiler quatre filtres :

    D1    biais et ATR de reference        filtre la direction, pas le nombre
    H4    structure, niveaux qui comptent   remplace, ne s'ajoute pas
    M15   identification du setup           inchange
    M5    declencheur et stop fin           augmente legerement le nombre

Empiler les quatre unites comme autant de conditions ET diviserait par trois un
nombre de signaux deja insuffisant. Les unites hautes servent de contexte, pas
de barrieres supplementaires.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from . import agregation, alignement, indicateurs, seances


@dataclass
class Contexte:
    series: dict = field(default_factory=dict)   # alignees sur l'index de base
    unites: dict = field(default_factory=dict)   # nom -> (bougies, indices, series)

    def unite(self, nom):
        return self.unites[nom]


def construire(base, regime="paris") -> Contexte:
    reg = seances.REGIMES[regime]
    ctx = Contexte()

    pas = alignement.duree_base(base)
    en_m5 = pas <= timedelta(minutes=5)

    m15 = agregation.en_m15(base) if en_m5 else base
    h4 = agregation.en_h4(base)
    d1 = agregation.en_journalier(base)

    series_m15 = {
        "atr": indicateurs.atr(m15, 14),
        "ema50": indicateurs.ema([b.cloture for b in m15], 50),
        "macd_hist": indicateurs.macd(m15)[2],
    }
    adx_h4, _, _ = indicateurs.adx(h4, 14)
    series_h4 = {
        "atr": indicateurs.atr(h4, 14),
        "ema50": indicateurs.ema([b.cloture for b in h4], 50),
        "adx": adx_h4,
    }
    atr_d1_court = indicateurs.atr(d1, 14)
    atr_d1_long = indicateurs.atr(d1, 100)
    series_d1 = {
        "atr": atr_d1_court,
        "atr_long": atr_d1_long,
        "ema20": indicateurs.ema([b.cloture for b in d1], 20),
        # Regime de volatilite : ATR journalier rapporte a sa propre moyenne
        # longue. Sans normalisation, un ATR de 30 $ ne veut pas dire la meme
        # chose sur un or a 1900 $ et sur un or a 4500 $.
        "ratio_vol": [None if (c is None or not l) else c / l
                      for c, l in zip(atr_d1_court, atr_d1_long)],
    }

    ctx.unites = {
        "M15": (m15, alignement.indices(base, m15, timedelta(minutes=15)), series_m15),
        "H4": (h4, alignement.indices(base, h4, timedelta(hours=4)), series_h4),
        "D1": (d1, alignement.indices(base, d1, timedelta(days=1)), series_d1),
    }

    # Series scalaires alignees sur la base, pour ce qui est consulte a chaque barre.
    ctx.series["atr_m15"] = alignement.aligner(base, m15, series_m15["atr"],
                                               timedelta(minutes=15))
    ctx.series["atr_d1"] = alignement.aligner(base, d1, series_d1["atr"],
                                              timedelta(days=1))
    ctx.series["atr_base"] = indicateurs.atr(base, 14)
    ctx.series["ratio_vol"] = alignement.aligner(
        base, d1, series_d1["ratio_vol"], timedelta(days=1))
    ctx.series["range_haut"], ctx.series["range_bas"] = _range_asiatique(base, reg, regime)
    return ctx


def _range_asiatique(base, reg, regime):
    """Plus haut / plus bas de la fenetre asiatique, expose une fois close.

    Causalite : la valeur reste None pendant la formation du range. Un setup ne
    peut donc pas connaitre un range en cours de constitution.
    """
    fenetre = reg["range_asiatique"]
    hauts, bas = [None] * len(base), [None] * len(base)
    if fenetre is None:
        return hauts, bas

    accumule = {}
    for i, b in enumerate(base):
        jour = seances.date_locale(b.ts, regime)
        if seances.dans_fenetre(b.ts, fenetre, regime):
            h, l = accumule.get(jour, (None, None))
            accumule[jour] = (b.haut if h is None else max(h, b.haut),
                              b.bas if l is None else min(l, b.bas))
        elif seances.locale(b.ts, regime).time() >= fenetre[1]:
            hauts[i], bas[i] = accumule.get(jour, (None, None))
    return hauts, bas
