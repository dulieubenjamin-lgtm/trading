"""Les trois setups, traduits en regles strictement mecaniques.

CE QUE LA TRADUCTION A CASSE
============================
Le rulebook en prose (setups/*.md) se lisait comme objectif. Il ne l'etait pas.
Dix points ont du etre tranches ou abandonnes. Ils sont marques RUPTURE dans le
code et recapitules dans setups/ruptures.md.

Manque une source de donnees (regle ABANDONNEE, pas contournee) :
  R1  S1 "hors ferie majeur US/UK"          -> pas de calendrier des feries
  R2  S1 "aucune publication US avant 10h"  -> pas de calendrier economique
  R3  S3 "aucune publication US sous 60 min"-> idem
  R4  S1 "entree sur la premiere M5"        -> on n'a que du M15

Formulation ambigue (un choix a ete fait, il est ARBITRAIRE) :
  R5  S1 "le prix revient dans la zone"     -> meche ou cloture ?
  R6  S2 "impulsion de N bougies"           -> quel point de depart exactement ?
  R7  S2 "EMA50 H1 orientee"                -> orientee sur quelle duree ?
  R8  S2 "meche >= 50 % du corps"           -> indefini si le corps est nul
  R9  S3 "zone testee >= 2 fois"            -> aucune definition operationnelle

Piege cache :
  R10 S3 "deux sommets"  -> un sommet ne se confirme qu'apres coup. Le detecter
      sans decalage, c'est lire le futur. Corrige par DECALAGE_PIVOT.

Un rulebook dont 10 clauses sur ~35 se derobent a l'ecriture n'etait pas un
rulebook, c'etait une intention. C'est precisement ce que cet exercice devait
reveler, et pourquoi il fallait le faire avant de payer un abonnement.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from . import seances

# R10 : un pivot a l'indice j n'est confirme qu'apres DECALAGE_PIVOT bougies.
# Toute detection de divergence doit donc ignorer les dernieres bougies.
DECALAGE_PIVOT = 2

# R7 : "EMA50 H1 orientee" -> pente mesuree sur 3 heures (12 bougies M15).
RECUL_PENTE = 12

# R8 : sous ce corps (en fraction d'ATR), le ratio meche/corps n'a pas de sens.
CORPS_MINIMAL = 0.10


@dataclass(frozen=True)
class Plan:
    setup: str
    sens: str                 # "achat" | "vente"
    ts: datetime
    entree: float
    stop: float
    tp1: float
    tp2: float
    motif: str
    contexte: dict = field(default_factory=dict)

    @property
    def risque_unitaire(self) -> float:
        return abs(self.entree - self.stop)


def _signe(sens: str) -> int:
    return 1 if sens == "achat" else -1


# --------------------------------------------------------------------------
# S1 — cassure du range asiatique
# --------------------------------------------------------------------------

def s1(vue, regime="paris"):
    reg = seances.REGIMES[regime]
    if reg["cassure"] is None:                     # regime bali : S1 desactive
        return None
    b = vue.courante
    if not seances.dans_fenetre(b.ts, reg["cassure"], regime):
        return None

    haut_r, bas_r = vue.indicateur("range_haut"), vue.indicateur("range_bas")
    atr = vue.indicateur("atr_m15")
    atr_d1 = vue.indicateur("atr_d1")
    if None in (haut_r, bas_r, atr, atr_d1) or atr <= 0:
        return None

    amplitude = haut_r - bas_r
    if not (0.5 * atr_d1 <= amplitude <= 1.5 * atr_d1):
        return None

    jour = seances.date_locale(b.ts, regime)
    for sens in ("achat", "vente"):
        s = _signe(sens)
        borne = haut_r if sens == "achat" else bas_r

        # Reconstruction de l'etat depuis la vue : on cherche, dans la fenetre de
        # cassure du jour, la premiere bougie ayant CLOTURE au-dela de la borne.
        i_cassure = None
        for d in range(-(len(vue) - 1), 1):
            x = vue[d]
            if seances.date_locale(x.ts, regime) != jour:
                continue
            if not seances.dans_fenetre(x.ts, reg["cassure"], regime):
                continue
            if s * (x.cloture - borne) > 0:
                i_cassure = d
                break
        if i_cassure is None or i_cassure == 0:
            continue    # pas de cassure, ou cassure a l'instant : le retest suit

        # Invalidation : une cloture repassee du mauvais cote depuis la cassure.
        depuis = [vue[d] for d in range(i_cassure, 1)]
        if any(s * (x.cloture - borne) < 0 for x in depuis[1:]):
            continue

        # R5 : "revient dans la zone" est lu comme la MECHE entrant dans la zone.
        # Choix arbitraire. Retenir la cloture donnerait moins d'entrees et de
        # meilleurs prix ; c'est un des premiers reglages a tester.
        zone_loin = borne - s * 0.25 * atr
        touche = (b.bas <= borne and b.haut >= zone_loin) if sens == "achat" \
            else (b.haut >= borne and b.bas <= zone_loin)
        if not touche:
            continue

        # R4 : l'entree devait se faire sur une M5 de confirmation. Faute de M5,
        # on entre a la cloture M15. Le prix de remplissage en est degrade.
        if sens == "achat" and not b.haussiere:
            continue
        if sens == "vente" and b.haussiere:
            continue

        entree = b.cloture
        extreme = b.bas if sens == "achat" else b.haut
        stop = extreme - s * 0.0
        if abs(entree - stop) < 1.2 * atr:
            stop = entree - s * 1.2 * atr
        distance = abs(entree - stop)
        if distance > 2.5 * atr or distance <= 0:
            continue

        tp2_projete = borne + s * amplitude
        tp2_2r = entree + s * 2 * distance
        tp2 = min(tp2_projete, tp2_2r) if sens == "achat" else max(tp2_projete, tp2_2r)

        return Plan(
            setup="S1", sens=sens, ts=b.ts, entree=entree, stop=stop,
            tp1=entree + s * distance, tp2=tp2,
            motif=f"retest de la cassure du range asiatique ({amplitude:.2f} $)",
            contexte={"haut_range": haut_r, "bas_range": bas_r,
                      "amplitude_range": amplitude, "atr_m15": atr, "atr_d1": atr_d1},
        )
    return None


# --------------------------------------------------------------------------
# S2 — pullback Fibonacci sur impulsion de session
# --------------------------------------------------------------------------

def _impulsion(vue, sens: str, atr: float, maxi: int = 6):
    """R6 : definition operationnelle d'une impulsion.

    Choix retenu : sur une fenetre de 2 a `maxi` bougies, l'extreme de depart
    doit PRECEDER l'extreme d'arrivee, l'ampleur doit valoir >= 1,5 x ATR, et le
    retracement maximal pendant la formation doit rester sous 38,2 %.
    On garde la fenetre la plus ample. C'est UN choix, pas LE choix : une
    definition par swing points donnerait d'autres impulsions.
    """
    s = _signe(sens)
    meilleure = None
    for longueur in range(2, maxi + 1):
        if len(vue) < longueur:
            break
        fen = vue.fenetre(longueur)
        if sens == "achat":
            j = min(range(len(fen)), key=lambda k: fen[k].bas)
            if j == len(fen) - 1:
                continue
            k = max(range(j, len(fen)), key=lambda k: fen[k].haut)
            depart, arrivee = fen[j].bas, fen[k].haut
        else:
            j = max(range(len(fen)), key=lambda k: fen[k].haut)
            if j == len(fen) - 1:
                continue
            k = min(range(j, len(fen)), key=lambda k: fen[k].bas)
            depart, arrivee = fen[j].haut, fen[k].bas
        ampleur = s * (arrivee - depart)
        if ampleur < 1.5 * atr:
            continue
        # Retracement maximal entre les deux extremes.
        pire = 0.0
        extreme_courant = depart
        for x in fen[j:k + 1]:
            extreme_courant = max(extreme_courant, x.haut) if sens == "achat" \
                else min(extreme_courant, x.bas)
            recul = s * (extreme_courant - (x.bas if sens == "achat" else x.haut))
            pire = max(pire, recul)
        if ampleur > 0 and pire / ampleur > 0.382:
            continue
        if meilleure is None or ampleur > meilleure[2]:
            meilleure = (depart, arrivee, ampleur)
    return meilleure


def s2(vue, regime="paris"):
    reg = seances.REGIMES[regime]
    b = vue.courante
    fenetres = [f for f in (reg["fenetre_londres"], reg["fenetre_ny"]) if f]
    if not any(seances.dans_fenetre(b.ts, f, regime) for f in fenetres):
        return None

    atr = vue.indicateur("atr_m15")
    ema_h1 = vue.indicateur("ema50_h1")
    ema_m15 = vue.indicateur("ema50_m15")
    if None in (atr, ema_h1, ema_m15) or atr <= 0:
        return None
    try:
        ema_h1_avant = vue.indicateur("ema50_h1", -RECUL_PENTE)
    except IndexError:
        return None
    if ema_h1_avant is None:
        return None

    for sens in ("achat", "vente"):
        s = _signe(sens)
        # R7 : "orientee" -> pente sur RECUL_PENTE bougies, et prix du bon cote.
        if s * (ema_h1 - ema_h1_avant) <= 0:
            continue
        if s * (b.cloture - ema_h1) <= 0:
            continue

        imp = _impulsion(vue, sens, atr)
        if imp is None:
            continue
        depart, arrivee, ampleur = imp

        zone_proche = arrivee - s * 0.618 * ampleur
        zone_loin = arrivee - s * 0.705 * ampleur
        bas_zone, haut_zone = sorted((zone_proche, zone_loin))
        if not (bas_zone <= b.cloture <= haut_zone):
            continue

        # Confluence EMA50 M15 OBLIGATOIRE.
        if not (bas_zone - 0.3 * atr <= ema_m15 <= haut_zone + 0.3 * atr):
            continue

        # R8 : ratio meche/corps indefini sur un corps quasi nul -> on exige un
        # corps minimal plutot que de laisser le ratio exploser.
        if b.corps < CORPS_MINIMAL * atr:
            continue
        meche = b.meche_basse if sens == "achat" else b.meche_haute
        if meche < 0.5 * b.corps:
            continue
        if (sens == "achat") != b.haussiere:
            continue

        entree = b.cloture
        stop = arrivee - s * 0.786 * ampleur
        if abs(entree - stop) < 1.0 * atr:
            stop = entree - s * 1.0 * atr
        distance = abs(entree - stop)
        if distance <= 0:
            continue

        return Plan(
            setup="S2", sens=sens, ts=b.ts, entree=entree, stop=stop,
            tp1=arrivee, tp2=depart + s * 1.272 * ampleur,
            motif=f"pullback 0,618-0,705 sur impulsion de {ampleur:.2f} $, "
                  f"confluence EMA50 M15",
            contexte={"impulsion_depart": depart, "impulsion_arrivee": arrivee,
                      "ampleur": ampleur, "atr_m15": atr, "ema50_m15": ema_m15},
        )
    return None


# --------------------------------------------------------------------------
# S3 — divergence MACD sur niveau H1
# --------------------------------------------------------------------------

def _pivots(vue, sens: str, largeur: int = 2, profondeur: int = 40):
    """Sommets confirmes, du plus recent au plus ancien.

    R10 : un pivot a l'indice j exige `largeur` bougies de chaque cote. Les
    `largeur` dernieres bougies ne peuvent donc PAS heberger de pivot confirme.
    Ignorer ce decalage reviendrait a lire le futur — et donnerait un backtest
    flatteur et faux.
    """
    trouves = []
    dernier = -DECALAGE_PIVOT
    for d in range(dernier, -profondeur, -1):
        try:
            centre = vue[d]
            gauche = [vue[d - k] for k in range(1, largeur + 1)]
            droite = [vue[d + k] for k in range(1, largeur + 1)]
        except (IndexError, Exception):
            break
        if any(x is None for x in gauche + droite):
            break
        if sens == "vente":
            if all(centre.haut > x.haut for x in gauche + droite):
                trouves.append((d, centre.haut))
        else:
            if all(centre.bas < x.bas for x in gauche + droite):
                trouves.append((d, centre.bas))
    return trouves


def s3(vue, regime="paris"):
    reg = seances.REGIMES[regime]
    b = vue.courante
    if not seances.dans_fenetre(b.ts, reg["fenetre_s3"], regime):
        return None

    adx_h1 = vue.indicateur("adx_h1")
    atr = vue.indicateur("atr_m15")
    if None in (adx_h1, atr) or atr <= 0:
        return None
    if adx_h1 >= 20:                       # filtre vital : hors range, on ne joue pas
        return None

    # R9 : "zone testee >= 2 fois" n'a pas de definition operationnelle.
    # Abandonne. Seul subsiste le plus haut / plus bas des 5 dernieres seances.
    niveau_haut, niveau_bas = vue.indicateur("plus_haut_5j"), vue.indicateur("plus_bas_5j")
    if None in (niveau_haut, niveau_bas):
        return None

    for sens in ("achat", "vente"):
        s = _signe(sens)
        niveau = niveau_bas if sens == "achat" else niveau_haut
        touche = b.bas <= niveau if sens == "achat" else b.haut >= niveau
        if not touche:
            continue

        pivots = _pivots(vue, sens)
        if len(pivots) < 2:
            continue
        (d1, p1), (d2, p2) = pivots[0], pivots[1]
        ecart = abs(d1 - d2)
        if not (5 <= ecart <= 20):
            continue
        # Divergence reguliere : prix fait un extreme plus marque, MACD non.
        if s * (p1 - p2) >= 0:
            continue
        h1, h2 = vue.indicateur("macd_hist", d1), vue.indicateur("macd_hist", d2)
        if h1 is None or h2 is None:
            continue
        if s * (h1 - h2) <= 0:
            continue

        # Confirmation : cloture repassee du bon cote du niveau.
        if s * (b.cloture - niveau) <= 0:
            continue

        entree = b.cloture
        extreme = min(p1, p2) if sens == "achat" else max(p1, p2)
        stop = extreme
        if abs(entree - stop) < 1.0 * atr:
            stop = entree - s * 1.0 * atr
        distance = abs(entree - stop)
        if distance <= 0:
            continue

        milieu = (niveau_haut + niveau_bas) / 2
        return Plan(
            setup="S3", sens=sens, ts=b.ts, entree=entree, stop=stop,
            tp1=entree + s * distance,          # 1R strict : contre-tendance
            tp2=milieu,
            motif=f"divergence MACD sur niveau 5j ({niveau:.2f} $), ADX H1 {adx_h1:.1f}",
            contexte={"niveau": niveau, "adx_h1": adx_h1, "pivots": [p1, p2],
                      "macd_hist": [h1, h2], "atr_m15": atr},
        )
    return None


SETUPS = {"S1": s1, "S2": s2, "S3": s3}
