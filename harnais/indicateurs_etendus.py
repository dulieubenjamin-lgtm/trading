"""Indicateurs supplementaires, tous causaux et en stdlib pur.

Chaque serie a la longueur de l'entree, avec None pendant la chauffe. Aucune
valeur a l'indice i n'utilise de donnee posterieure a i.

CONTRAINTE DE DONNEES : le flux ne fournit que l'OHLC, jamais le volume. Tout
indicateur volumetrique — OBV, VWAP au sens strict, profil de volume, delta —
est donc hors de portee, et aucune approximation ne le remplace honnetement.
"""
from __future__ import annotations

from statistics import pstdev

from .indicateurs import _wilder, atr, ema


def sma(valeurs, periode: int):
    sortie, somme = [None] * len(valeurs), 0.0
    for i, v in enumerate(valeurs):
        somme += v
        if i >= periode:
            somme -= valeurs[i - periode]
        if i + 1 >= periode:
            sortie[i] = somme / periode
    return sortie


def ecart_type(valeurs, periode: int):
    """Ecart-type glissant, par sommes courantes.

    La version naive recalculait pstdev sur toute la fenetre a chaque barre :
    O(n x periode). Sur 300 000 bougies et plusieurs indicateurs qui en
    dependent, cela dominait le temps de calcul. Les sommes courantes ramenent
    a O(n).
    """
    sortie = [None] * len(valeurs)
    somme = somme_carres = 0.0
    for i, v in enumerate(valeurs):
        somme += v
        somme_carres += v * v
        if i >= periode:
            sortant = valeurs[i - periode]
            somme -= sortant
            somme_carres -= sortant * sortant
        if i + 1 >= periode:
            variance = somme_carres / periode - (somme / periode) ** 2
            sortie[i] = variance ** 0.5 if variance > 0 else 0.0
    return sortie


def rsi(bougies, periode: int = 14):
    """RSI de Wilder."""
    clot = [b.cloture for b in bougies]
    hausses, baisses = [None], [None]
    for a, b in zip(clot, clot[1:]):
        d = b - a
        hausses.append(max(d, 0.0))
        baisses.append(max(-d, 0.0))
    mh, mb = _wilder(hausses, periode), _wilder(baisses, periode)
    sortie = [None] * len(bougies)
    for i in range(len(bougies)):
        if mh[i] is None or mb[i] is None:
            continue
        sortie[i] = 100.0 if mb[i] == 0 else 100 - 100 / (1 + mh[i] / mb[i])
    return sortie


def bollinger(bougies, periode: int = 20, k: float = 2.0):
    """Renvoie (haut, bas, largeur_relative). La largeur sert aux setups de compression."""
    clot = [b.cloture for b in bougies]
    moy, sd = sma(clot, periode), ecart_type(clot, periode)
    haut = [None if (m is None or s is None) else m + k * s for m, s in zip(moy, sd)]
    bas = [None if (m is None or s is None) else m - k * s for m, s in zip(moy, sd)]
    largeur = [None if (h is None or b is None or not m) else (h - b) / m
               for h, b, m in zip(haut, bas, moy)]
    return haut, bas, largeur


def stochastique(bougies, k: int = 14, d: int = 3):
    pk = [None] * len(bougies)
    for i in range(k - 1, len(bougies)):
        fen = bougies[i + 1 - k: i + 1]
        hh, bb = max(x.haut for x in fen), min(x.bas for x in fen)
        pk[i] = 50.0 if hh == bb else 100 * (bougies[i].cloture - bb) / (hh - bb)
    valides = [v for v in pk if v is not None]
    pd_ = [None] * len(bougies)
    if valides:
        debut = pk.index(valides[0])
        pd_[debut:] = sma(pk[debut:], d)
    return pk, pd_


def donchian(bougies, periode: int = 20):
    """Canal calcule sur les `periode` bougies PRECEDENTES, courante EXCLUE.

    Inclure la bougie courante rendrait toute cassure vraie par construction :
    le plus haut du canal serait le plus haut de la bougie qui le casse.
    """
    haut, bas = [None] * len(bougies), [None] * len(bougies)
    for i in range(periode, len(bougies)):
        fen = bougies[i - periode: i]
        haut[i] = max(x.haut for x in fen)
        bas[i] = min(x.bas for x in fen)
    return haut, bas


def keltner(bougies, periode: int = 20, k: float = 1.5):
    milieu = ema([b.cloture for b in bougies], periode)
    a = atr(bougies, periode)
    haut = [None if (m is None or x is None) else m + k * x for m, x in zip(milieu, a)]
    bas = [None if (m is None or x is None) else m - k * x for m, x in zip(milieu, a)]
    return haut, bas


def cci(bougies, periode: int = 20):
    tp = [(b.haut + b.bas + b.cloture) / 3 for b in bougies]
    moy = sma(tp, periode)
    sortie = [None] * len(bougies)
    for i in range(periode - 1, len(bougies)):
        m = moy[i]
        dev = sum(abs(x - m) for x in tp[i + 1 - periode: i + 1]) / periode
        sortie[i] = 0.0 if dev == 0 else (tp[i] - m) / (0.015 * dev)
    return sortie


def roc(bougies, periode: int = 10):
    clot = [b.cloture for b in bougies]
    return [None if i < periode or not clot[i - periode]
            else 100 * (clot[i] / clot[i - periode] - 1)
            for i in range(len(clot))]


def zscore(bougies, periode: int = 20):
    clot = [b.cloture for b in bougies]
    moy, sd = sma(clot, periode), ecart_type(clot, periode)
    return [None if (m is None or not s) else (c - m) / s
            for c, m, s in zip(clot, moy, sd)]


def position_dans_range(bougies, periode: int = 20):
    """0 = au plus bas des N dernieres, 1 = au plus haut. Bougie courante incluse."""
    sortie = [None] * len(bougies)
    for i in range(periode - 1, len(bougies)):
        fen = bougies[i + 1 - periode: i + 1]
        hh, bb = max(x.haut for x in fen), min(x.bas for x in fen)
        sortie[i] = 0.5 if hh == bb else (bougies[i].cloture - bb) / (hh - bb)
    return sortie


def atr_relatif(bougies, court: int = 14, long: int = 100):
    """Compression / expansion : < 1 le marche se resserre, > 1 il s'ecarte."""
    c, l = atr(bougies, court), atr(bougies, long)
    return [None if (a is None or not b) else a / b for a, b in zip(c, l)]


def taille_relative(bougies, periode: int = 14):
    """Amplitude de la bougie rapportee a l'ATR : mesure de bougie exceptionnelle."""
    a = atr(bougies, periode)
    return [None if not x else b.amplitude / x for b, x in zip(bougies, a)]


def asymetrie_meches(bougies):
    """(meche basse - meche haute) / amplitude. Positif = rejet du bas.

    Faute de volume, la forme des bougies est le seul indice sur le rapport de
    force entre acheteurs et vendeurs a l'interieur d'une periode.
    """
    return [None if not b.amplitude else (b.meche_basse - b.meche_haute) / b.amplitude
            for b in bougies]


def range_horaire(bougies, heure_debut: float = 0.0, heure_fin: float = 7.0):
    """Plus haut / plus bas d'une plage horaire UTC du jour, expose une fois close.

    Generalisation du range asiatique : la plage est un parametre. La valeur reste
    None pendant la formation du range et jusqu'a sa cloture, de sorte qu'aucune
    regle ne peut connaitre un range en cours de constitution.

    Une fois la plage close, la valeur reste disponible jusqu'a la fin de la
    journee UTC — c'est ce qui permet aux setups de cassure de s'y referer toute
    la seance.
    """
    hauts, bas = [None] * len(bougies), [None] * len(bougies)
    accumule = {}
    for i, b in enumerate(bougies):
        jour = b.ts.date()
        h = b.ts.hour + b.ts.minute / 60
        if heure_debut <= h < heure_fin:
            hh, bb = accumule.get(jour, (None, None))
            accumule[jour] = (b.haut if hh is None else max(hh, b.haut),
                              b.bas if bb is None else min(bb, b.bas))
        elif h >= heure_fin:
            hauts[i], bas[i] = accumule.get(jour, (None, None))
    return hauts, bas
