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


def charger(chemin: str | Path) -> list[Bougie]:
    """Lit un CSV de cache et renvoie les bougies TRIEES par temps croissant.

    Twelve Data renvoie du plus recent au plus ancien. Tout le harnais suppose
    l'ordre chronologique : le tri est fait ici pour que personne d'autre n'ait
    a y penser.
    """
    lignes = Path(chemin).read_text(encoding="utf-8").strip().splitlines()
    if not lignes:
        raise ValueError(f"cache vide : {chemin}")
    if lignes[0].strip() != EN_TETE:
        raise ValueError(f"en-tete inattendu dans {chemin} : {lignes[0]!r}")

    bougies, ambigues = [], []
    for ligne in lignes[1:]:
        if not ligne.strip():
            continue
        etiquette, o, h, b, c = ligne.split(";")
        if heure_ambigue(etiquette):
            ambigues.append(etiquette)
        bougies.append(
            Bougie(etiquette_vers_utc(etiquette), float(o), float(h), float(b), float(c))
        )

    if ambigues:
        print(
            f"  note : {len(ambigues)} etiquette(s) sur une transition d'heure "
            f"d'ete a Sydney, lue(s) comme la premiere occurrence "
            f"(ex. {ambigues[0]})"
        )

    bougies.sort(key=lambda x: x.ts)
    doublons = len(bougies) - len({x.ts for x in bougies})
    if doublons:
        raise ValueError(f"{doublons} horodatage(s) en double dans {chemin}")
    return bougies
