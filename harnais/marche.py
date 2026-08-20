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
    seuil_degenerescence: float = 0.15
    """Fraction de l'amplitude mediane sous laquelle une bougie est tenue pour
    synthetique.

    LE SEUIL DEPEND DU MARCHE, et le confondre fausse l'analyse. Sur un marche a
    seances, le flux COMBLE les fermetures avec un prix fige : un seuil genereux
    les attrape. Sur un marche continu il n'y a rien a combler — verifie, la
    couverture BTC est de 100 %. Le meme seuil de 15 % y rejetait 11 562 bougies
    d'amplitude mediane 8 $ sur un actif a ~68 000 $ : des bougies CALMES mais
    REELLES, concentrees entre 4h et 7h UTC. On aurait supprime la nuit
    asiatique, c'est-a-dire precisement le regime calme qu'on cherche a mesurer.

    En continu, seule une bougie strictement plate est tenue pour un defaut de
    flux : 52 bougies sur 311 017.
    """


FOREX = Marche("forex", continu=False, heure_ancre=17, seuil_degenerescence=0.15)
CONTINU = Marche("continu", continu=True, heure_ancre=0, seuil_degenerescence=0.0)

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
