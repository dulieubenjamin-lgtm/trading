"""Figures chartistes, definies mecaniquement.

POURQUOI UNE FAMILLE A PART
===========================
Un indicateur compresse une fenetre de prix en un nombre : deux trajectoires
tres differentes peuvent donner le meme RSI. Une figure est une relation
GEOMETRIQUE entre des pivots precis — c'est exactement l'information que les
indicateurs jettent. Aucun test mene jusqu'ici ne couvre cette classe.

LE PIEGE DES FIGURES
====================
« Double creux » n'a pas de definition unique : a quelle distance les deux creux
doivent-ils etre ? sur quelle portee ? quelle profondeur pour le sommet
intermediaire ? Chaque praticien repond autrement. C'est le probleme des
ruptures R5 a R9 de ce projet — de la prose qui parait objective et ne l'est pas.

Ici chaque tolerance est un PARAMETRE EXPLICITE, jamais une valeur enfouie. Deux
consequences : les definitions sont discutables mais executables, et le nombre de
variantes testees reste denombrable, donc corrigeable.

CAUSALITE
=========
Un pivot exige `largeur` bougies de chaque cote : il n'est donc confirme que
`largeur` bougies APRES son sommet. Toute figure est signalee au plus tot a la
confirmation de son dernier pivot, jamais au moment ou l'oeil la voit sur un
graphique fini. C'est la rupture R10, deja rencontree sur les divergences.
"""
from __future__ import annotations

from .indicateurs import atr


def pivots(bougies, largeur: int = 3):
    """Pivots confirmes. Renvoie deux listes (indice, prix) : hauts, bas.

    L'indice rendu est celui du SOMMET, mais la figure ne peut etre exploitee
    qu'a partir de indice + largeur.
    """
    hauts, bas = [], []
    n = len(bougies)
    for j in range(largeur, n - largeur):
        c = bougies[j]
        gauche = bougies[j - largeur:j]
        droite = bougies[j + 1:j + 1 + largeur]
        if all(c.haut > x.haut for x in gauche + droite):
            hauts.append((j, c.haut))
        if all(c.bas < x.bas for x in gauche + droite):
            bas.append((j, c.bas))
    return hauts, bas


def _serie_vide(n):
    return [0.0] * n


def double_extreme(bougies, sens="creux", largeur=3, tolerance=0.5,
                   ecart_min=8, ecart_max=60, profondeur_min=1.5):
    """Double creux / double sommet, signale a la cassure de la ligne de cou.

    Definition retenue :
      - deux pivots de meme type separes de `ecart_min` a `ecart_max` bougies
      - ecart de prix entre eux <= `tolerance` x ATR
      - un pivot oppose entre les deux, distant d'au moins
        `profondeur_min` x ATR du plus proche des deux extremes
      - signal a la premiere cloture au-dela de ce pivot oppose (ligne de cou),
        et seulement apres confirmation du second pivot
    """
    n = len(bougies)
    sortie = _serie_vide(n)
    a = atr(bougies, 14)
    hauts, bas = pivots(bougies, largeur)
    memes = bas if sens == "creux" else hauts
    opposes = hauts if sens == "creux" else bas
    s = 1 if sens == "creux" else -1     # sens de la cassure attendue

    for k in range(1, len(memes)):
        j1, p1 = memes[k - 1]
        j2, p2 = memes[k]
        ecart = j2 - j1
        if not (ecart_min <= ecart <= ecart_max):
            continue
        ref = a[j2]
        if not ref or abs(p2 - p1) > tolerance * ref:
            continue
        entre = [(j, p) for j, p in opposes if j1 < j < j2]
        if not entre:
            continue
        jc, cou = max(entre, key=lambda x: s * x[1])
        if s * (cou - max(p1, p2) if s > 0 else cou - min(p1, p2)) < profondeur_min * ref:
            continue
        depart = j2 + largeur              # confirmation du second pivot
        for i in range(depart, min(depart + ecart_max, n)):
            if s * (bougies[i].cloture - cou) > 0:
                sortie[i] = 1.0
                break
    return sortie


def drapeau(bougies, sens="haussier", impulsion_atr=2.5, impulsion_max=12,
            consolidation_max=10, largeur_consolidation=1.0):
    """Drapeau : impulsion nette suivie d'une consolidation etroite, puis cassure.

    Definition retenue :
      - une impulsion d'au moins `impulsion_atr` x ATR en <= `impulsion_max` bougies
      - suivie de <= `consolidation_max` bougies dont l'amplitude totale reste
        sous `largeur_consolidation` x ATR
      - signal a la cloture au-dela de l'extreme de la consolidation, dans le
        sens de l'impulsion
    """
    n = len(bougies)
    sortie = _serie_vide(n)
    a = atr(bougies, 14)
    s = 1 if sens == "haussier" else -1

    i = impulsion_max
    while i < n - 1:
        ref = a[i]
        if not ref:
            i += 1
            continue
        fen = bougies[i - impulsion_max:i + 1]
        depart = min(x.bas for x in fen) if s > 0 else max(x.haut for x in fen)
        arrivee = bougies[i].cloture
        if s * (arrivee - depart) < impulsion_atr * ref:
            i += 1
            continue
        # Consolidation : on avance tant que le prix reste dans un couloir etroit.
        haut = bas = None
        for k in range(i + 1, min(i + 1 + consolidation_max, n)):
            x = bougies[k]
            haut = x.haut if haut is None else max(haut, x.haut)
            bas = x.bas if bas is None else min(bas, x.bas)
            if haut - bas > largeur_consolidation * ref:
                break
            if k > i + 2 and s * (x.cloture - (haut if s > 0 else bas)) >= 0:
                sortie[k] = 1.0
                break
        i += 1
    return sortie


def triangle(bougies, largeur=3, portee=60, pivots_min=2, convergence=0.6):
    """Triangle : sommets decroissants ET creux croissants, puis cassure.

    Definition retenue : sur les `portee` dernieres bougies, au moins
    `pivots_min` sommets strictement decroissants et autant de creux strictement
    croissants, avec un resserrement d'au moins `convergence` (l'ecart final
    vaut au plus `convergence` fois l'ecart initial). Signal a la cloture
    au-dela du dernier sommet ou sous le dernier creux.
    """
    n = len(bougies)
    sortie = _serie_vide(n)
    hauts, bas = pivots(bougies, largeur)
    if len(hauts) < pivots_min or len(bas) < pivots_min:
        return sortie

    # Index par position pour eviter de rebalayer toute la liste a chaque barre :
    # la version naive etait en O(n x pivots) et prenait plus d'une minute.
    ih = ib = 0
    dh = db = 0
    for i in range(portee, n):
        while ih < len(hauts) and hauts[ih][0] <= i - largeur:
            ih += 1
        while dh < len(hauts) and hauts[dh][0] < i - portee:
            dh += 1
        while ib < len(bas) and bas[ib][0] <= i - largeur:
            ib += 1
        while db < len(bas) and bas[db][0] < i - portee:
            db += 1
        hs, bs = hauts[dh:ih], bas[db:ib]
        if len(hs) < pivots_min or len(bs) < pivots_min:
            continue
        hs, bs = hs[-pivots_min:], bs[-pivots_min:]
        if not all(hs[k][1] > hs[k + 1][1] for k in range(len(hs) - 1)):
            continue
        if not all(bs[k][1] < bs[k + 1][1] for k in range(len(bs) - 1)):
            continue
        ecart_debut = hs[0][1] - bs[0][1]
        ecart_fin = hs[-1][1] - bs[-1][1]
        if ecart_debut <= 0 or ecart_fin > convergence * ecart_debut:
            continue
        c = bougies[i].cloture
        if c > hs[-1][1] or c < bs[-1][1]:
            sortie[i] = 1.0
    return sortie


def tete_epaules(bougies, sens="sommet", largeur=3, tolerance=0.6,
                 ecart_max=80, saillie_min=0.8):
    """Epaule-tete-epaule et sa version inversee, signale a la cassure du cou.

    Definition retenue : trois pivots de meme type, celui du milieu depassant les
    deux autres d'au moins `saillie_min` x ATR, les deux epaules distantes de
    moins de `tolerance` x ATR l'une de l'autre. La ligne de cou est le pivot
    oppose le plus marque entre les epaules ; signal a sa cassure.
    """
    n = len(bougies)
    sortie = _serie_vide(n)
    a = atr(bougies, 14)
    hauts, bas = pivots(bougies, largeur)
    memes = hauts if sens == "sommet" else bas
    opposes = bas if sens == "sommet" else hauts
    s = 1 if sens == "sommet" else -1     # tete au-dessus (sommet) ou en dessous

    for k in range(2, len(memes)):
        (j1, e1), (j2, tete), (j3, e3) = memes[k - 2], memes[k - 1], memes[k]
        if j3 - j1 > ecart_max:
            continue
        ref = a[j3]
        if not ref:
            continue
        if s * (tete - e1) < saillie_min * ref or s * (tete - e3) < saillie_min * ref:
            continue
        if abs(e1 - e3) > tolerance * ref:
            continue
        entre = [(j, p) for j, p in opposes if j1 < j < j3]
        if not entre:
            continue
        jc, cou = min(entre, key=lambda x: s * x[1])
        depart = j3 + largeur
        for i in range(depart, min(depart + ecart_max, n)):
            if -s * (bougies[i].cloture - cou) > 0:      # cassure a l'oppose de la tete
                sortie[i] = 1.0
                break
    return sortie
