"""Rejet des bougies synthetiques que le flux insere quand le marche est ferme.

Twelve Data ne saute pas les periodes de fermeture : il les comble avec un prix
fige. Ingerees telles quelles, elles ecrasent l'ATR vers zero — donc gonflent
les tailles de position — et rendent chaque reouverture du lundi semblable a une
cassure massive.

Deux filtres, dans cet ordre :

1. CALENDRIER (principal, deterministe) — le forex est ferme du vendredi 17h NY
   au dimanche 17h NY. Ce filtre traite tout le week-end hebdomadaire, sans
   dependre d'un seuil.
2. AMPLITUDE (secondaire) — attrape les feries et les coupures de flux, que le
   calendrier ignore.

Le seuil du filtre 2 est delicat, et une premiere version etait fausse : elle
calculait l'amplitude de reference sur TOUTES les bougies, y compris les figees.
Sur un echantillon contenant beaucoup de marche ferme, la mediane etait tiree
vers le bas et les figees passaient sous le radar. La reference se calcule
desormais sur les seules bougies que le calendrier declare ouvertes.
"""
from __future__ import annotations

from statistics import median

# Fraction de l'amplitude mediane sous laquelle une bougie est tenue pour figee.
# Calibre sur les donnees reelles : en periode de marche ferme l'amplitude
# observee est de ~0,26 $ pour une mediane d'ouverture de ~5 $, soit 5 %. Une
# vraie bougie calme de session asiatique descend a ~1 $, soit 20 %. Le seuil a
# 15 % separe les deux avec de la marge des deux cotes.
SEUIL_DEGENERESCENCE = 0.15


def amplitude_reference(bougies) -> float:
    """Amplitude mediane des bougies que le CALENDRIER declare ouvertes.

    Exclure les bougies de marche ferme evite que la reference soit tiree vers
    le bas par les figees qu'on cherche justement a detecter.
    """
    from .fuseau import marche_ferme

    ouvertes = [b.amplitude for b in bougies if not marche_ferme(b.ts)]
    if not ouvertes:
        raise ValueError(
            "aucune bougie en marche ouvert : impossible de calibrer le filtre"
        )
    return median(ouvertes)


def est_degeneree(bougie, reference: float) -> bool:
    return bougie.amplitude < SEUIL_DEGENERESCENCE * reference


def filtrer(bougies):
    """Retire les bougies de marche ferme. Renvoie (bougies_propres, rapport)."""
    from .fuseau import marche_ferme

    reference = amplitude_reference(bougies)
    propres, rejet_calendrier, rejet_amplitude = [], 0, 0

    for b in bougies:
        if marche_ferme(b.ts):
            rejet_calendrier += 1
            continue
        if est_degeneree(b, reference):
            rejet_amplitude += 1
            continue
        propres.append(b)

    return propres, {
        "entrantes": len(bougies),
        "conservees": len(propres),
        "rejet_calendrier": rejet_calendrier,
        "rejet_amplitude": rejet_amplitude,
        "amplitude_reference": round(reference, 4),
    }
