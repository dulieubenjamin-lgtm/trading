"""Les trois setups, en lecture D1 / H4 / M15 / M5.

REPARTITION DES ROLES
=====================
    D1    biais et ATR de reference       filtre la direction, pas le nombre
    H4    structure, niveaux qui comptent  remplace, ne s'ajoute pas
    M15   identification du setup          inchange
    M5    declencheur et stop fin          augmente legerement le nombre

Les unites hautes servent de CONTEXTE, pas de barrieres. Empiler quatre
conditions ET diviserait par trois un nombre de signaux deja insuffisant.

HISTORIQUE DES RUPTURES : voir setups/ruptures.md. Les references Rn ci-dessous
y renvoient.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from . import seances
from .vue import UniteIndisponible

DECALAGE_PIVOT = 2      # R10 : un pivot n'est confirme qu'apres 2 bougies
RECUL_PENTE = 6         # pente EMA mesuree sur 6 bougies de l'unite consideree
CORPS_MINIMAL = 0.10    # R8 : sous ce corps, le ratio meche/corps n'a pas de sens

# S1 — bande d'amplitude du range asiatique en multiples d'ATR journalier.
# CALIBREE sur 22/01 -> 30/04/2026 uniquement (outils/calibrer.py), regle de
# centiles 25e-90e fixee avant tout resultat. Ne jamais recalculer sur la
# periode de test.
S1_RATIO_MIN = 0.24
S1_RATIO_MAX = 0.69

# S3 — anciennete minimale d'un niveau H4 pour etre tenu pour "etabli".
# R13 : exiger un extreme FRAIS etait auto-contradictoire — un nouvel extreme
# signifie par construction que le momentum vient de tout balayer. Un niveau
# ancien, deja travaille, est l'endroit ou le momentum a le droit de s'essouffler.
AGE_MINIMAL_NIVEAU_H4 = 3


@dataclass(frozen=True)
class Plan:
    setup: str
    sens: str
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


def _tendance(vue_ht, sens: str, cloture: float) -> bool:
    """Biais d'une unite superieure : EMA50 orientee et prix du bon cote."""
    s = _signe(sens)
    ema = vue_ht.indicateur("ema50")
    if ema is None:
        return False
    try:
        avant = vue_ht.indicateur("ema50", -RECUL_PENTE)
    except IndexError:
        return False
    if avant is None:
        return False
    return s * (ema - avant) > 0 and s * (cloture - ema) > 0


# --------------------------------------------------------------------------
# S1 — cassure du range asiatique.  M15 confirme, M5 declenche.
# --------------------------------------------------------------------------

def s1(vue, regime="paris"):
    reg = seances.REGIMES[regime]
    if reg["cassure"] is None:
        return None
    b = vue.courante
    if not seances.dans_fenetre(b.ts, reg["cassure"], regime):
        return None

    haut_r, bas_r = vue.indicateur("range_haut"), vue.indicateur("range_bas")
    atr = vue.indicateur("atr_m15")
    atr_d1 = vue.indicateur("atr_d1")
    if None in (haut_r, bas_r, atr, atr_d1) or atr <= 0 or not atr_d1:
        return None

    amplitude = haut_r - bas_r
    if not (S1_RATIO_MIN * atr_d1 <= amplitude <= S1_RATIO_MAX * atr_d1):
        return None
    try:
        m15 = vue.ut("M15")
    except (UniteIndisponible, KeyError):
        return None

    jour = seances.date_locale(b.ts, regime)
    for sens in ("achat", "vente"):
        s = _signe(sens)
        borne = haut_r if sens == "achat" else bas_r

        # Cassure : une M15 CLOSE au-dela de la borne, dans la fenetre du jour.
        #
        # L'ETAT SE RECONSTRUIT DANS LE SENS DU TEMPS. Une premiere version
        # parcourait la vue a l'envers et traitait toute cloture du mauvais cote
        # comme une invalidation — y compris celles ANTERIEURES a la cassure,
        # qui ne sont que l'etat d'avant. Resultat : aucune cassure ne survivait
        # jamais a sa propre bougie precedente.
        fenetre_jour = []
        for d in range(0, -40, -1):
            try:
                x = m15[d]
            except IndexError:
                break
            if seances.date_locale(x.ts, regime) != jour:
                break
            if seances.dans_fenetre(x.ts, reg["cassure"], regime):
                fenetre_jour.append(x)
        fenetre_jour.reverse()

        casse = False
        for x in fenetre_jour:
            if not casse and s * (x.cloture - borne) > 0:
                casse = True
            elif casse and s * (x.cloture - borne) < 0:
                casse = False       # fausse cassure confirmee : on abandonne
                break
        if not casse:
            continue

        # R5 : le retest est lu comme la MECHE de la M5 entrant dans la zone.
        zone_loin = borne - s * 0.25 * atr
        touche = (b.bas <= borne and b.haut >= zone_loin) if sens == "achat" \
            else (b.haut >= borne and b.bas <= zone_loin)
        if not touche:
            continue
        # R4 (resolu) : le declencheur est bien une M5, comme le rulebook l'exigeait.
        if (sens == "achat") != b.haussiere:
            continue

        entree = b.cloture
        stop = b.bas if sens == "achat" else b.haut
        if abs(entree - stop) < 1.2 * atr:
            stop = entree - s * 1.2 * atr
        distance = abs(entree - stop)
        if distance <= 0 or distance > 2.5 * atr:
            continue

        tp2_projete = borne + s * amplitude
        tp2_2r = entree + s * 2 * distance
        tp2 = min(tp2_projete, tp2_2r) if sens == "achat" else max(tp2_projete, tp2_2r)
        return Plan("S1", sens, b.ts, entree, stop, entree + s * distance, tp2,
                    f"retest M5 de la cassure du range asiatique ({amplitude:.2f} $)",
                    {"haut_range": haut_r, "bas_range": bas_r,
                     "amplitude_range": amplitude, "atr_m15": atr, "atr_d1": atr_d1})
    return None


# --------------------------------------------------------------------------
# S2 — pullback Fibonacci.  Impulsion M15, biais H4, declencheur M5.
# --------------------------------------------------------------------------

def _impulsion(vue_m15, sens: str, atr: float, maxi: int = 6, recul: int = 20):
    """Impulsion ACHEVEE sur M15.

    R6 : la detection cherchait autrefois la plus ample sur une fenetre incluant
    la bougie courante, ce qui placait l'extreme SUR cette bougie et rendait le
    retracement toujours nul (53 impulsions, zero dans la zone Fibo). Detection
    et mesure du pullback sont desormais separees.
    """
    s = _signe(sens)
    for k in range(-1, -recul - 1, -1):
        try:
            fin = vue_m15[k]
        except IndexError:
            break
        arrivee = fin.haut if sens == "achat" else fin.bas
        if any(s * ((vue_m15[d].haut if sens == "achat" else vue_m15[d].bas) - arrivee) > 0
               for d in range(k + 1, 1)):
            continue

        meilleure = None
        for longueur in range(2, maxi + 1):
            try:
                bg = [vue_m15[d] for d in range(k - longueur + 1, k + 1)]
            except IndexError:
                break
            depart = (min(x.bas for x in bg) if sens == "achat"
                      else max(x.haut for x in bg))
            ampleur = s * (arrivee - depart)
            if ampleur < 1.5 * atr:
                continue
            pire, extreme = 0.0, depart
            for x in bg:
                extreme = (max(extreme, x.haut) if sens == "achat"
                           else min(extreme, x.bas))
                contre = x.bas if sens == "achat" else x.haut
                pire = max(pire, s * (extreme - contre))
            if pire / ampleur > 0.382:
                continue
            if meilleure is None or ampleur > meilleure[2]:
                meilleure = (depart, arrivee, ampleur)
        if meilleure is not None:
            return meilleure
    return None


def s2(vue, regime="paris"):
    reg = seances.REGIMES[regime]
    b = vue.courante
    fenetres = [f for f in (reg["fenetre_londres"], reg["fenetre_ny"]) if f]
    if not any(seances.dans_fenetre(b.ts, f, regime) for f in fenetres):
        return None
    atr = vue.indicateur("atr_m15")
    if atr is None or atr <= 0:
        return None
    try:
        m15, h4 = vue.ut("M15"), vue.ut("H4")
    except (UniteIndisponible, KeyError):
        return None

    for sens in ("achat", "vente"):
        s = _signe(sens)
        # R12 (resolu). L'ancienne version exigeait que le prix ET l'EMA50 M15 se
        # trouvent dans la zone 0,618-0,705, large de 0,38 x ATR : demander a deux
        # grandeurs independantes de coincider dans une fenetre aussi etroite est
        # un filtre d'impossibilite (4 candidats, zero passaient). Le biais est
        # desormais porte par l'unite qui a vocation a le porter, la H4.
        if not _tendance(h4, sens, b.cloture):
            continue

        imp = _impulsion(m15, sens, atr)
        if imp is None:
            continue
        depart, arrivee, ampleur = imp
        zone = sorted((arrivee - s * 0.618 * ampleur, arrivee - s * 0.705 * ampleur))
        if not (zone[0] <= b.cloture <= zone[1]):
            continue

        if b.corps < CORPS_MINIMAL * atr:
            continue
        meche = b.meche_basse if sens == "achat" else b.meche_haute
        if meche < 0.5 * b.corps or (sens == "achat") != b.haussiere:
            continue

        entree = b.cloture
        stop = arrivee - s * 0.786 * ampleur
        if abs(entree - stop) < 1.0 * atr:
            stop = entree - s * 1.0 * atr
        distance = abs(entree - stop)
        if distance <= 0:
            continue
        return Plan("S2", sens, b.ts, entree, stop, arrivee,
                    depart + s * 1.272 * ampleur,
                    f"pullback 0,618-0,705 sur impulsion M15 de {ampleur:.2f} $, "
                    f"biais H4, declencheur M5",
                    {"impulsion_depart": depart, "impulsion_arrivee": arrivee,
                     "ampleur": ampleur, "atr_m15": atr})
    return None


# --------------------------------------------------------------------------
# S3 — divergence MACD M15 sur niveau H4 etabli.  Declencheur M5.
# --------------------------------------------------------------------------

def _pivots(vue, sens: str, largeur: int = 2, profondeur: int = 40):
    """Sommets CONFIRMES, du plus recent au plus ancien.

    R10 : un pivot exige `largeur` bougies de chaque cote. Les dernieres bougies
    ne peuvent donc pas en heberger un — l'ignorer reviendrait a lire le futur.
    """
    trouves = []
    for d in range(-DECALAGE_PIVOT, -profondeur, -1):
        try:
            centre = vue[d]
            voisins = [vue[d - k] for k in range(1, largeur + 1)] + \
                      [vue[d + k] for k in range(1, largeur + 1)]
        except IndexError:
            break
        if sens == "vente":
            if all(centre.haut > x.haut for x in voisins):
                trouves.append((d, centre.haut))
        elif all(centre.bas < x.bas for x in voisins):
            trouves.append((d, centre.bas))
    return trouves


def _niveaux_h4(vue_h4, age_minimal: int = AGE_MINIMAL_NIVEAU_H4):
    """Niveaux structurels : pivots H4 confirmes et deja anciens.

    R13 : c'est ici que le setup change de nature. Un niveau H4 vieux de
    plusieurs bougies est un niveau DEJA TRAVAILLE — l'endroit ou un momentum
    peut legitimement s'essouffler. Un extreme frais est l'inverse.
    """
    hauts = [(d, v) for d, v in _pivots(vue_h4, "vente", profondeur=30)
             if -d >= age_minimal]
    bas = [(d, v) for d, v in _pivots(vue_h4, "achat", profondeur=30)
           if -d >= age_minimal]
    return hauts, bas


def s3(vue, regime="paris"):
    reg = seances.REGIMES[regime]
    b = vue.courante
    if not seances.dans_fenetre(b.ts, reg["fenetre_s3"], regime):
        return None
    atr = vue.indicateur("atr_m15")
    if atr is None or atr <= 0:
        return None
    try:
        m15, h4 = vue.ut("M15"), vue.ut("H4")
    except (UniteIndisponible, KeyError):
        return None

    adx = h4.indicateur("adx")
    if adx is None or adx >= 20:      # filtre vital : hors range, on ne joue pas
        return None
    hauts, bas = _niveaux_h4(h4)

    for sens in ("achat", "vente"):
        s = _signe(sens)
        candidats = bas if sens == "achat" else hauts
        niveau = next((v for _, v in candidats
                       if abs(b.bas - v if sens == "achat" else b.haut - v) <= 0.5 * atr),
                      None)
        if niveau is None:
            continue

        pivots = _pivots(m15, sens)
        if len(pivots) < 2:
            continue
        (d1, p1), (d2, p2) = pivots[0], pivots[1]
        if not (5 <= abs(d1 - d2) <= 20):
            continue
        if s * (p1 - p2) >= 0:
            continue
        h_1, h_2 = m15.indicateur("macd_hist", d1), m15.indicateur("macd_hist", d2)
        if h_1 is None or h_2 is None or s * (h_1 - h_2) <= 0:
            continue
        if s * (b.cloture - niveau) <= 0:
            continue

        entree = b.cloture
        stop = min(p1, p2) if sens == "achat" else max(p1, p2)
        if abs(entree - stop) < 1.0 * atr:
            stop = entree - s * 1.0 * atr
        distance = abs(entree - stop)
        if distance <= 0:
            continue
        milieu = (hauts[0][1] + bas[0][1]) / 2 if hauts and bas else entree + s * 2 * distance
        return Plan("S3", sens, b.ts, entree, stop, entree + s * distance, milieu,
                    f"divergence MACD M15 sur niveau H4 etabli ({niveau:.2f} $), "
                    f"ADX H4 {adx:.1f}",
                    {"niveau_h4": niveau, "adx_h4": adx, "pivots": [p1, p2],
                     "atr_m15": atr})
    return None


SETUPS = {"S1": s1, "S2": s2, "S3": s3}
