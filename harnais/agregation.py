"""Agregation M15 -> H1 et M15 -> journalier forex.

La bougie journaliere du forex ne va pas de minuit a minuit : elle court de
17h00 New York a 17h00 New York. Utiliser minuit UTC decalerait l'ATR journalier
— dont depend le filtre d'amplitude de S1 — d'environ un tiers de seance.
"""
from __future__ import annotations

from datetime import timedelta

from .bougie import Bougie
from .fuseau import NEW_YORK


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


def en_h1(bougies):
    return _grouper(bougies, lambda b: b.ts.replace(minute=0, second=0, microsecond=0))


def seance_forex(instant) -> str:
    """Date de la seance forex contenant cet instant (bornes 17h00 New York)."""
    local = instant.astimezone(NEW_YORK)
    if local.hour >= 17:
        local += timedelta(days=1)
    return local.date().isoformat()


def en_journalier(bougies):
    return _grouper(bougies, seance_forex_cle)


def seance_forex_cle(b):
    return seance_forex(b.ts)
