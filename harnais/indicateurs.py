"""Indicateurs, en stdlib pur et strictement causaux.

Chaque serie renvoyee a la meme longueur que l'entree, avec None pendant la
periode de chauffe. Aucune valeur a l'indice i n'utilise de donnee posterieure
a i : c'est la condition sine qua non d'un walk-forward honnete.

Lissage de Wilder pour ATR et ADX (et non une moyenne simple) : c'est la
definition d'origine, et celle qu'utilise TradingView. Un ecart ici rendrait
incomparables les resultats du harnais et ceux d'une future validation en replay.
"""
from __future__ import annotations


def _wilder(valeurs, periode: int):
    """Lissage de Wilder : RMA[i] = (RMA[i-1]*(n-1) + x[i]) / n."""
    sortie = [None] * len(valeurs)
    tampon, courant = [], None
    for i, v in enumerate(valeurs):
        if v is None:
            continue
        if courant is None:
            tampon.append(v)
            if len(tampon) == periode:
                courant = sum(tampon) / periode
                sortie[i] = courant
        else:
            courant = (courant * (periode - 1) + v) / periode
            sortie[i] = courant
    return sortie


def ema(valeurs, periode: int):
    """Moyenne exponentielle, amorcee sur la moyenne simple des `periode` premieres."""
    alpha = 2 / (periode + 1)
    sortie = [None] * len(valeurs)
    courant = None
    for i, v in enumerate(valeurs):
        if courant is None:
            if i + 1 >= periode:
                courant = sum(valeurs[i + 1 - periode: i + 1]) / periode
                sortie[i] = courant
        else:
            courant = alpha * v + (1 - alpha) * courant
            sortie[i] = courant
    return sortie


def _true_range(bougies):
    tr = [None]
    for prec, b in zip(bougies, bougies[1:]):
        tr.append(max(b.haut - b.bas,
                      abs(b.haut - prec.cloture),
                      abs(b.bas - prec.cloture)))
    return tr


def atr(bougies, periode: int = 14):
    return _wilder(_true_range(bougies), periode)


def macd(bougies, rapide: int = 12, lent: int = 26, signal: int = 9):
    """Renvoie (ligne_macd, ligne_signal, histogramme)."""
    clotures = [b.cloture for b in bougies]
    er, el = ema(clotures, rapide), ema(clotures, lent)
    ligne = [None if (a is None or b is None) else a - b for a, b in zip(er, el)]

    # La ligne signal est une EMA de la ligne MACD : on l'amorce sur la premiere
    # valeur definie, pas sur l'indice 0, sinon la chauffe est faussee.
    debut = next((i for i, v in enumerate(ligne) if v is not None), None)
    sig = [None] * len(ligne)
    if debut is not None:
        sig[debut:] = ema(ligne[debut:], signal)
    hist = [None if (m is None or s is None) else m - s for m, s in zip(ligne, sig)]
    return ligne, sig, hist


def adx(bougies, periode: int = 14):
    """ADX de Wilder. Renvoie (adx, plus_di, moins_di)."""
    n = len(bougies)
    plus_dm, moins_dm = [None], [None]
    for prec, b in zip(bougies, bougies[1:]):
        haut_delta = b.haut - prec.haut
        bas_delta = prec.bas - b.bas
        plus_dm.append(haut_delta if (haut_delta > bas_delta and haut_delta > 0) else 0.0)
        moins_dm.append(bas_delta if (bas_delta > haut_delta and bas_delta > 0) else 0.0)

    tr_liss = _wilder(_true_range(bougies), periode)
    plus_liss = _wilder(plus_dm, periode)
    moins_liss = _wilder(moins_dm, periode)

    plus_di, moins_di, dx = [None] * n, [None] * n, [None] * n
    for i in range(n):
        if not tr_liss[i] or plus_liss[i] is None or moins_liss[i] is None:
            continue
        plus_di[i] = 100 * plus_liss[i] / tr_liss[i]
        moins_di[i] = 100 * moins_liss[i] / tr_liss[i]
        somme = plus_di[i] + moins_di[i]
        dx[i] = 0.0 if somme == 0 else 100 * abs(plus_di[i] - moins_di[i]) / somme

    return _wilder(dx, periode), plus_di, moins_di
