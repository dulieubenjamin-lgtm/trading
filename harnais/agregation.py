"""Agregation M15 -> H1 et M15 -> journalier forex.

La bougie journaliere du forex ne va pas de minuit a minuit : elle court de
17h00 New York a 17h00 New York. Utiliser minuit UTC decalerait l'ATR journalier
— dont depend le filtre d'amplitude de S1 — d'environ un tiers de seance.
"""
from __future__ import annotations

from datetime import timedelta

from zoneinfo import ZoneInfo

from .bougie import Bougie
from .fuseau import NEW_YORK
from .marche import resoudre

UTC = ZoneInfo("UTC")


def _fusionner(groupe):
    return Bougie(
        ts=groupe[0].ts,
        ouverture=groupe[0].ouverture,
        haut=max(b.haut for b in groupe),
        bas=min(b.bas for b in groupe),
        cloture=groupe[-1].cloture,
    )


def _grouper(bougies, cle):
    groupes, courant, cle_courante = [], [], None
    for b in bougies:
        k = cle(b)
        if cle_courante is None or k == cle_courante:
            courant.append(b)
            cle_courante = k
        else:
            groupes.append(_fusionner(courant))
            courant, cle_courante = [b], k
    if courant:
        groupes.append(_fusionner(courant))
    return groupes


def en_m15(bougies):
    """M5 -> M15. Groupe par tranche de 15 minutes de l'heure."""
    return _grouper(bougies, lambda b: b.ts.replace(
        minute=(b.ts.minute // 15) * 15, second=0, microsecond=0))


def en_h1(bougies):
    return _grouper(bougies, lambda b: b.ts.replace(minute=0, second=0, microsecond=0))


def cle_h4(instant, marche="forex") -> str:
    """Bloc H4 ancre sur la seance forex, pas sur minuit UTC.

    La journee forex court de 17h00 New York a 17h00 New York : les six bougies
    H4 demarrent donc a 17h, 21h, 01h, 05h, 09h et 13h heure de New York.

    Decouper a minuit UTC — le reflexe naturel — placerait les frontieres H4 au
    milieu de l'ouverture de Londres et au milieu de celle de New York, cassant
    en deux les mouvements que ces bougies sont censees decrire.
    """
    m = resoudre(marche)
    if m.continu:
        # Aucune seance a respecter : on ancre sur minuit UTC.
        return f"{instant.date().isoformat()}#{instant.hour // 4}"
    local = instant.astimezone(NEW_YORK)
    bloc = ((local.hour - m.heure_ancre) % 24) // 4
    return f"{seance_forex(instant, marche)}#{bloc}"


def en_h4(bougies, marche="forex"):
    return _grouper(bougies, lambda b: cle_h4(b.ts, marche))


def seance_forex(instant, marche="forex") -> str:
    """Date de la seance contenant cet instant.

    Forex : bornes a 17h00 New York. Marche continu : journee UTC.
    """
    m = resoudre(marche)
    if m.continu:
        return instant.date().isoformat()
    local = instant.astimezone(NEW_YORK)
    if local.hour >= m.heure_ancre:
        local += timedelta(days=1)
    return local.date().isoformat()


def en_journalier(bougies, marche="forex"):
    return _grouper(bougies, lambda b: seance_forex(b.ts, marche))
