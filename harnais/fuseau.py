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


def verifier_decalage(bougies, tolerance=timedelta(minutes=30), minimum=100) -> dict:
    """Assertion : la fermeture hebdomadaire observee tombe-t-elle ou il faut ?

    Localise dans les donnees la derniere bougie reelle avant chaque plage de
    marche ferme et compare a la fermeture theorique (vendredi 17h New York).

    ON TESTE LA MEDIANE, PAS LE MAXIMUM. Une premiere version prenait le pire
    ecart et bloquait le backtest sur les donnees reelles : deux semaines sur
    vingt-sept montraient une fermeture avancee de 3-4 h. Ce n'etait pas une
    erreur de fuseau mais deux jours feries americains (Juneteenth le 19/06,
    Independence Day observe le 03/07) sur lesquels les marches US ferment tot.

    Les deux defauts ne se ressemblent pas, et c'est ce qui permet de les
    distinguer :
      - un fuseau errone decale TOUTES les fermetures du MEME montant
      - un ferie n'en decale QU'UNE, et toujours vers l'avant

    D'ou : la mediane teste le fuseau, et les valeurs aberrantes sont remontees
    telles quelles — elles designent des seances ecourtees, information utile
    puisque le rulebook n'a pas de calendrier des feries (voir setups/ruptures.md).
    """
    from .nettoyage import est_degeneree, amplitude_reference

    if len(bougies) < minimum:
        raise ValueError("echantillon trop court pour verifier le decalage")

    reference = amplitude_reference(bougies)
    controles, ecarts, dates = 0, [], []

    for precedente, suivante in zip(bougies, bougies[1:]):
        # Transition reelle -> degeneree : candidate a une fermeture hebdo.
        if est_degeneree(precedente, reference) or not est_degeneree(suivante, reference):
            continue
        attendue = fermeture_hebdo_attendue(precedente.ts)
        ecart = abs(attendue - (precedente.ts + timedelta(minutes=15)))
        # On ne retient que les transitions proches d'un vendredi soir : les
        # accalmies de milieu de semaine ne sont pas des fermetures hebdo.
        if ecart > timedelta(hours=12):
            continue
        controles += 1
        ecarts.append(ecart)
        dates.append(precedente.ts.date())

    if controles == 0:
        raise FuseauIncoherent(
            "aucune fermeture hebdomadaire identifiee : impossible de verifier "
            "le decalage. L'echantillon couvre-t-il au moins un week-end ?"
        )

    from statistics import median

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
