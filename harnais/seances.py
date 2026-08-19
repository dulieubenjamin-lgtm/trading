"""Fenetres de seance, exprimees dans le fuseau de l'utilisateur.

Les regles sont ecrites en heure de Paris ("range 02h-08h", "flat a 22h"). On les
evalue via la base tz : une regle ecrite en heure locale se decale d'une heure au
changement d'heure si on la traduit en UTC une fois pour toutes.
"""
from __future__ import annotations

from datetime import time
from zoneinfo import ZoneInfo

REGIMES = {
    "paris": {
        "tz": ZoneInfo("Europe/Paris"),
        "range_asiatique": (time(2, 0), time(8, 0)),
        "cassure": (time(9, 0), time(11, 30)),
        "retest_limite": time(12, 30),
        "fenetre_londres": (time(9, 0), time(11, 0)),
        "fenetre_ny": (time(15, 30), time(17, 30)),
        "fenetre_s3": (time(9, 0), time(18, 0)),
        "derniere_entree": time(18, 0),
        "flat": time(22, 0),
    },
    "bali": {
        "tz": ZoneInfo("Asia/Makassar"),
        "range_asiatique": None,   # S1 inutilisable : le range se forme pendant la seance
        "cassure": None,
        "retest_limite": None,
        "fenetre_londres": (time(15, 0), time(17, 0)),
        "fenetre_ny": None,        # NY ouvre a 21h30 WITA, apres la derniere entree
        "fenetre_s3": (time(8, 0), time(17, 0)),
        "derniere_entree": time(17, 0),
        "flat": time(20, 0),
    },
}


def locale(instant, regime="paris"):
    return instant.astimezone(REGIMES[regime]["tz"])


def date_locale(instant, regime="paris") -> str:
    return locale(instant, regime).date().isoformat()


def dans_fenetre(instant, fenetre, regime="paris") -> bool:
    if fenetre is None:
        return False
    h = locale(instant, regime).time()
    return fenetre[0] <= h < fenetre[1]


def apres(instant, borne, regime="paris") -> bool:
    return locale(instant, regime).time() >= borne
