"""Conversion des etiquettes Twelve Data vers UTC, et verification du decalage.

Twelve Data etiquette les series XAU/USD en heure de Sydney, heure d'ete de
l'hemisphere sud comprise : +10h en aout, +11h en janvier (constat verifie, voir
donnees/twelve-data-constat.md).

On ne code JAMAIS le decalage en dur. On interprete l'etiquette dans
Australia/Sydney via la base tz, et on verifie le resultat contre un fait de
marche independant : le forex ferme le vendredi a 17h00 New York.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

SYDNEY = ZoneInfo("Australia/Sydney")
NEW_YORK = ZoneInfo("America/New_York")

# Heure de fermeture et de reouverture hebdomadaire, en heure de New York.
FERMETURE_NY = 17  # vendredi 17h00
OUVERTURE_NY = 17  # dimanche 17h00


class FuseauIncoherent(RuntimeError):
    """Le decalage observe ne correspond pas au calendrier forex."""


def etiquette_vers_utc(etiquette: str, fuseau: str = "Australia/Sydney") -> datetime:
    """'2026-08-15 07:00:00' dans `fuseau` -> datetime UTC aware.

    Le fuseau est un PARAMETRE, jamais une constante enfouie : les caches
    produits par outils/telecharger.py demandent explicitement UTC a l'API,
    ceux constitues via le connecteur MCP heritent du defaut Sydney.
    """
    naif = datetime.fromisoformat(etiquette.strip())
    if naif.tzinfo is not None:
        raise ValueError(f"etiquette deja localisee, inattendu : {etiquette!r}")
    # fold=0 : lors du recul d'heure d'avril a Sydney, l'heure ambigue est lue
    # comme la premiere occurrence. Ces creneaux tombent un dimanche matin
    # heure locale, donc marche ferme — ils seront filtres comme synthetiques.
    return naif.replace(tzinfo=ZoneInfo(fuseau), fold=0).astimezone(ZoneInfo("UTC"))


def heure_ambigue(etiquette: str) -> bool:
    """Vrai si l'etiquette tombe sur une transition d'heure d'ete a Sydney.

    Une heure ambigue (recul) donne deux instants UTC ; une heure inexistante
    (avance) n'en donne aucun. zoneinfo ne leve pas d'erreur, il choisit
    silencieusement — on veut le savoir plutot que de le subir.
    """
    naif = datetime.fromisoformat(etiquette.strip())
    tot = naif.replace(tzinfo=SYDNEY, fold=0)
    tard = naif.replace(tzinfo=SYDNEY, fold=1)
    return tot.utcoffset() != tard.utcoffset()


def fermeture_hebdo_attendue(instant_utc: datetime) -> datetime:
    """Fermeture forex (vendredi 17h NY) de la semaine contenant instant_utc."""
    local = instant_utc.astimezone(NEW_YORK)
    # weekday() : lundi=0 ... vendredi=4
    delta = (4 - local.weekday()) % 7
    vendredi = (local + timedelta(days=delta)).replace(
        hour=FERMETURE_NY, minute=0, second=0, microsecond=0
    )
    if vendredi < local:
        vendredi += timedelta(days=7)
    return vendredi.astimezone(ZoneInfo("UTC"))


def marche_ferme(instant_utc: datetime) -> bool:
    """Vrai si le forex est ferme a cet instant (week-end hebdomadaire)."""
    local = instant_utc.astimezone(NEW_YORK)
    jour, heure = local.weekday(), local.hour
    if jour == 4 and heure >= FERMETURE_NY:      # vendredi apres 17h
        return True
    if jour == 5:                                 # samedi entier
        return True
    if jour == 6 and heure < OUVERTURE_NY:        # dimanche avant 17h
        return True
    return False


DUREE_MINIMALE_FERMETURE = timedelta(hours=4)


def _pas_median(bougies) -> timedelta:
    from statistics import median
    ecarts = [(b.ts - a.ts).total_seconds()
              for a, b in zip(bougies[:200], bougies[1:200])]
    return timedelta(seconds=median(ecarts))


def verifier_decalage(bougies, tolerance=timedelta(minutes=30), minimum=100,
                      duree_minimale=None) -> dict:
    """Assertion : la fermeture hebdomadaire observee tombe-t-elle ou il faut ?

    Localise les plages de marche fige et compare leur debut a la fermeture
    theorique (vendredi 17h New York).

    UNE FERMETURE SE DEFINIT PAR SA DUREE, PAS PAR UNE SEULE BOUGIE PLATE. Une
    premiere version retenait toute transition bougie reelle -> bougie figee. En
    base M15 cela suffisait ; en base M5 l'amplitude de reference est plus basse,
    si bien que la moindre accalmie de milieu de seance produisait une fausse
    fermeture — un vendredi 05h45 New York, par exemple. La mediane des ecarts
    passait de 15 minutes a deux heures, et l'assertion refusait des donnees
    saines.

    On ne retient donc que les plages figees durant au moins
    DUREE_MINIMALE_FERMETURE : un week-end en dure quarante-huit, aucune
    accalmie n'en approche.

    ON TESTE LA MEDIANE, PAS LE MAXIMUM : un fuseau errone decale TOUTES les
    fermetures du meme montant, un ferie n'en decale qu'une, vers l'avant.
    """
    from statistics import median

    from .nettoyage import amplitude_reference, est_degeneree

    if len(bougies) < minimum:
        raise ValueError("echantillon trop court pour verifier le decalage")

    # Duree au-dela de laquelle une interruption est tenue pour une fermeture
    # hebdomadaire. Ajustable pour les echantillons courts des tests, ou une
    # plage de quatre heures ne tient pas.
    duree_minimale = duree_minimale or DUREE_MINIMALE_FERMETURE

    reference = amplitude_reference(bougies)
    plats = [est_degeneree(b, reference) for b in bougies]

    # Un marche ferme se manifeste de DEUX facons selon le lot de donnees, et il
    # faut chercher les deux : le flux comble parfois la fermeture avec un prix
    # fige, parfois il omet simplement les bougies. Le lot sur 7 mois comblait ;
    # celui sur 36 mois omet (131 trous de plus de 4 h pour ~154 week-ends). Ne
    # detecter que les plages figees ne trouvait donc que 9 fermetures sur trois
    # ans, echantillon trop maigre pour que la mediane veuille dire quelque chose.
    candidats = []                       # (fin de la derniere vraie bougie, sa date)
    pas = _pas_median(bougies)

    for k in range(len(bougies) - 1):
        trou = bougies[k + 1].ts - bougies[k].ts
        if trou >= duree_minimale:
            candidats.append((bougies[k].ts + pas, bougies[k].ts.date()))

    i = 0
    while i < len(bougies):
        if not plats[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(bougies) and plats[j + 1]:
            j += 1
        if i > 0 and bougies[j].ts - bougies[i].ts >= duree_minimale:
            candidats.append((bougies[i].ts, bougies[i - 1].ts.date()))
        i = j + 1

    controles, ecarts, dates = 0, [], []
    for instant, date in candidats:
        attendue = fermeture_hebdo_attendue(instant - pas)
        ecart = abs(attendue - instant)
        if ecart <= timedelta(hours=12):
            controles += 1
            ecarts.append(ecart)
            dates.append(date)

    if controles == 0:
        raise FuseauIncoherent(
            "aucune fermeture hebdomadaire identifiee : impossible de verifier "
            "le decalage. L'echantillon couvre-t-il au moins un week-end ?"
        )

    mediane = median(ecarts)
    if mediane > tolerance:
        raise FuseauIncoherent(
            f"fermeture hebdomadaire decalee de {mediane} EN MEDIANE par rapport "
            f"au calendrier forex (tolerance {tolerance}). Un decalage systematique "
            f"signale un changement de fuseau des etiquettes — verifier avant tout "
            f"backtest."
        )
    return {
        "controles": controles,
        "ecart_median": mediane,
        "ecart_max": max(ecarts),
        # Dedoublonne : en base M5 le figement est graduel et produit plusieurs
        # transitions detectees pour une meme fermeture. Ce sont des dates, pas
        # des evenements distincts.
        "seances_ecourtees": sorted(
            {d for d, e in zip(dates, ecarts) if e > tolerance}
        ),
    }
