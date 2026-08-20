"""Lecture du cache disque des bougies.

Le harnais ne parle JAMAIS a l'API pendant un backtest : il lit un cache fige
sur disque. Deux raisons — un backtest doit etre reproductible a l'identique,
et le quota gratuit (800 appels/jour) ne doit pas etre brule a chaque essai.

Format du cache : CSV point-virgule, tel que renvoye par Twelve Data, etiquettes
en heure de Sydney. La conversion vers UTC se fait ici, une seule fois.
"""
from __future__ import annotations

from pathlib import Path

from .bougie import Bougie
from .fuseau import etiquette_vers_utc, heure_ambigue

EN_TETE = "datetime;open;high;low;close"

# Fuseau par defaut si le cache ne le declare pas : c'est ce que l'API renvoie
# quand on ne lui demande rien (constate, pas suppose). Les caches produits par
# outils/telecharger.py declarent "# timezone: UTC" en premiere ligne.
FUSEAU_PAR_DEFAUT = "Australia/Sydney"


def charger(chemin: str | Path) -> list[Bougie]:
    """Lit un CSV de cache et renvoie les bougies TRIEES par temps croissant.

    Twelve Data renvoie du plus recent au plus ancien. Tout le harnais suppose
    l'ordre chronologique : le tri est fait ici pour que personne d'autre n'ait
    a y penser.
    """
    lignes = Path(chemin).read_text(encoding="utf-8").strip().splitlines()
    if not lignes:
        raise ValueError(f"cache vide : {chemin}")

    fuseau = FUSEAU_PAR_DEFAUT
    if lignes[0].startswith("#"):
        marqueur = lignes[0].lstrip("# ").strip()
        if marqueur.startswith("timezone:"):
            fuseau = marqueur.split(":", 1)[1].strip()
        lignes = lignes[1:]

    if lignes[0].strip() != EN_TETE:
        raise ValueError(f"en-tete inattendu dans {chemin} : {lignes[0]!r}")

    bougies, ambigues, incoherentes = [], [], []
    for ligne in lignes[1:]:
        if not ligne.strip():
            continue
        etiquette, o, h, b, c = ligne.split(";")
        if fuseau != "UTC" and heure_ambigue(etiquette):
            ambigues.append(etiquette)
        vo, vh, vb, vc = float(o), float(h), float(b), float(c)
        # Le flux EUR/USD contient 0,14 % de bougies ou la cloture depasse le
        # plus haut, ecart median de 2 points de base et maximum a 461. Ni XAU ni
        # BTC n'en presentent une seule : c'est un defaut propre a ce flux.
        #
        # On les ECARTE plutot que de les reparer. Ramener le plus haut a la
        # cloture fabriquerait, pour la bougie a 461 bp, un mouvement de cent ATR
        # qui n'a jamais eu lieu — et le harnais le lirait comme un signal.
        # Ignorer une bougie dont on ne connait pas le vrai prix est honnete ;
        # en inventer un ne l'est pas.
        if not (vb <= vo <= vh and vb <= vc <= vh):
            incoherentes.append(etiquette)
            continue
        bougies.append(
            Bougie(etiquette_vers_utc(etiquette, fuseau), vo, vh, vb, vc)
        )

    if ambigues:
        print(
            f"  note : {len(ambigues)} etiquette(s) sur une transition d'heure "
            f"d'ete a Sydney, lue(s) comme la premiere occurrence "
            f"(ex. {ambigues[0]})"
        )

    if incoherentes:
        print(f"  note : {len(incoherentes)} bougie(s) a OHLC incoherent ecartee(s) "
              f"({100 * len(incoherentes) / (len(bougies) + len(incoherentes)):.2f} %), "
              f"ex. {incoherentes[0]}")

    bougies.sort(key=lambda x: x.ts)
    doublons = len(bougies) - len({x.ts for x in bougies})
    if doublons:
        raise ValueError(f"{doublons} horodatage(s) en double dans {chemin}")
    return bougies
