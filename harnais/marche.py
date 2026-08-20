"""Type de marche : le forex ferme le week-end, la crypto non.

Trois mecanismes du harnais dependent de cette difference, et les appliquer a
tort produirait un resultat FAUX plutot qu'une erreur visible :

    filtrage       le calendrier forex jetterait ~29 % de vraies bougies BTC
    journee        la seance forex court de 17h a 17h New York ; en continu la
                   journee est celle d'UTC
    bloc H4        ancre sur la seance forex, sinon sur minuit UTC
    verification   un marche continu n'a pas de fermeture hebdomadaire : on
                   verifie sa continuite au lieu de sa fermeture
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Marche:
    nom: str
    continu: bool          # True : ouvert 24/7, aucune fermeture hebdomadaire
    heure_ancre: int       # heure de New York ou demarre la journee (forex)


FOREX = Marche("forex", continu=False, heure_ancre=17)
CONTINU = Marche("continu", continu=True, heure_ancre=0)

MARCHES = {"forex": FOREX, "continu": CONTINU, "24/7": CONTINU}


def resoudre(nom) -> Marche:
    if isinstance(nom, Marche):
        return nom
    if nom not in MARCHES:
        raise KeyError(f"marche inconnu : {nom!r} (connus : {sorted(MARCHES)})")
    return MARCHES[nom]


def deduire_du_symbole(symbole: str) -> Marche:
    """Devine le type de marche a partir du nom du fichier ou du symbole."""
    s = symbole.upper()
    if any(c in s for c in ("BTC", "ETH", "USDT", "SOL", "XRP", "DOGE")):
        return CONTINU
    return FOREX
