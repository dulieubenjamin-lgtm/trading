"""Telecharge l'historique XAU/USD M15 depuis l'API Twelve Data vers le cache.

A LANCER SUR TA MACHINE, pas depuis une session Claude distante : le conteneur
distant n'a pas d'acces reseau vers api.twelvedata.com (politique d'egress).

    python3 outils/telecharger.py --mois 7

Le script demande la cle si elle n'est pas dans l'environnement. Elle n'est
jamais ecrite dans un fichier du depot.

Puis commiter le cache produit : c'est lui, et lui seul, que lit le harnais.

POURQUOI timezone=UTC EST PASSE EXPLICITEMENT
---------------------------------------------
Par defaut, l'API etiquette les series XAU/USD en heure de Sydney, heure d'ete
australe comprise (+10 h en aout, +11 h en janvier — constat verifie, voir
donnees/twelve-data-constat.md). En demandant UTC explicitement, on supprime a
la source toute une classe de bugs silencieux.

L'assertion de coherence du harnais reste active malgre tout : elle verifie que
la fermeture hebdomadaire du forex tombe la ou le calendrier la place. Demander
UTC ne dispense pas de verifier qu'on l'a bien recu.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = "https://api.twelvedata.com/time_series"
SYMBOLE = "XAU/USD"
MAX_POINTS = 5000          # plafond par requete, plan gratuit
MINUTES = {"5min": 5, "15min": 15, "1h": 60}
# 8 requetes/min sur le plan gratuit. A 8,0 s pile on frole la limite : la
# moindre latence reseau fait passer la 8e requete dans la meme minute que la
# premiere, et l'API refuse. 9,5 s laisse de la marge sans allonger notablement.
PAUSE = 9.5
ATTENTE_APRES_ECHEC = 65.0     # une minute pleine : laisse le compteur se vider
EN_TETE = "datetime;open;high;low;close"


def contexte_ssl() -> ssl.SSLContext:
    """Contexte TLS avec une autorite de certification utilisable.

    Sur macOS, le Python de python.org et celui des Command Line Tools
    n'utilisent PAS le trousseau systeme : sans intervention, toute requete
    HTTPS echoue en CERTIFICATE_VERIFY_FAILED. On s'appuie donc sur le paquet
    `certifi` quand il est present, sur le magasin par defaut sinon.

    On ne desactive JAMAIS la verification : ce serait accepter n'importe quel
    certificat, donc n'importe quel intermediaire, sur une connexion qui
    transporte une cle API.
    """
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def pas_jours(intervalle: str) -> int:
    """Largeur de tranche tenant sous le plafond de points, avec 15 % de marge.

    Elle DEPEND de l'intervalle : 5000 bougies valent ~52 jours en M15 mais
    seulement ~17 en M5. Une largeur ecrite en dur tronquerait silencieusement
    les tranches M5 — l'API renverrait ses 5000 derniers points de la fenetre et
    le debut de chaque tranche manquerait, sans erreur.
    """
    return max(1, int(MAX_POINTS * MINUTES[intervalle] / 1440 * 0.85))


def fenetres(mois: int, intervalle: str):
    fin = datetime.now(timezone.utc)
    debut = fin - timedelta(days=30 * mois)
    pas = timedelta(days=pas_jours(intervalle))
    curseur = debut
    while curseur < fin:
        yield curseur, min(curseur + pas, fin)
        curseur += pas


def tirer(cle: str, debut: datetime, fin: datetime, intervalle: str) -> list[str]:
    params = urllib.parse.urlencode({
        "symbol": SYMBOLE,
        "interval": intervalle,
        "start_date": debut.strftime("%Y-%m-%d %H:%M:%S"),
        "end_date": fin.strftime("%Y-%m-%d %H:%M:%S"),
        "outputsize": MAX_POINTS,
        "timezone": "UTC",
        "format": "CSV",
        "delimiter": ";",
        "apikey": cle,
    })
    with urllib.request.urlopen(f"{BASE}?{params}", timeout=60,
                                context=contexte_ssl()) as r:
        corps = r.read().decode("utf-8")

    if corps.lstrip().startswith("{"):        # l'API renvoie du JSON en cas d'erreur
        detail = json.loads(corps)
        raise RuntimeError(f"API : {detail.get('message', corps[:200])}")

    lignes = [l.strip() for l in corps.splitlines() if l.strip()]
    return [l for l in lignes if not l.startswith("datetime")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mois", type=int, default=7, help="profondeur en mois (defaut 7)")
    ap.add_argument("--intervalle", default="15min", choices=sorted(MINUTES),
                    help="unite de temps (defaut 15min)")
    ap.add_argument("--sortie", default=None,
                    help="par defaut donnees/cache/XAUUSD-<UT>.csv")
    args = ap.parse_args()

    # La cle peut venir de l'environnement ; sinon on la demande ICI, au moment
    # ou on en a besoin. Une premiere version exigeait un `read -s` prealable :
    # colle dans un bloc multi-ligne, ce read avale la ligne suivante du bloc au
    # lieu d'attendre une saisie, et l'echec arrive plus loin, ailleurs, sans
    # rapport visible avec sa cause.
    cle = (os.environ.get("TWELVEDATA_API_KEY") or "").strip()
    if not cle and sys.stdin.isatty():
        print("Cle API Twelve Data (la saisie reste invisible, c'est normal).")
        print("Elle se trouve sur https://twelvedata.com/ -> Log in -> section API Key.")
        try:
            cle = getpass.getpass("Cle : ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 2
    if not cle:
        print("Aucune cle fournie.", file=sys.stderr)
        print("Recupere-la sur https://twelvedata.com/ (plan Basic, gratuit),",
              file=sys.stderr)
        print("puis relance : python3 outils/telecharger.py --mois 7", file=sys.stderr)
        print("La cle n'est jamais ecrite dans un fichier du depot.", file=sys.stderr)
        return 2

    nom = {"5min": "M5", "15min": "M15", "1h": "H1"}[args.intervalle]
    cible = Path(args.sortie or f"donnees/cache/XAUUSD-{nom}.csv")
    cible.parent.mkdir(parents=True, exist_ok=True)
    print(f"{SYMBOLE} {args.intervalle} sur {args.mois} mois -> {cible}")

    lignes: dict[str, str] = {}
    if cible.exists():
        for l in cible.read_text(encoding="utf-8").splitlines():
            if l.strip() and not l.startswith(("datetime", "#")):
                lignes[l.split(";")[0]] = l
    avant = len(lignes)

    reussies = 0
    tranches = list(fenetres(args.mois, args.intervalle))
    print(f"{len(tranches)} requetes de {pas_jours(args.intervalle)} jours, "
          f"~{PAUSE * (len(tranches) - 1):.0f} s")
    echecs_ssl = 0
    for n, (debut, fin) in enumerate(tranches, 1):
        print(f"[{n}/{len(tranches)}] {debut:%Y-%m-%d} -> {fin:%Y-%m-%d} ...", end=" ", flush=True)
        recues = None
        for tentative in (1, 2):
            try:
                recues = tirer(cle, debut, fin, args.intervalle)
                break
            except Exception as e:
                if "CERTIFICATE_VERIFY_FAILED" in str(e):
                    print(f"ECHEC : {e}")
                    echecs_ssl += 1
                    break
                if tentative == 1:
                    # Une seule reprise, et seulement apres une minute pleine :
                    # la cause de loin la plus frequente est le plafond de
                    # requetes par minute, qui se vide tout seul.
                    print(f"echec ({str(e)[:60]}) — reprise dans "
                          f"{ATTENTE_APRES_ECHEC:.0f} s", end=" ", flush=True)
                    time.sleep(ATTENTE_APRES_ECHEC)
                else:
                    print(f"ECHEC DEFINITIF : {e}")
        if recues is None:
            continue
        for l in recues:
            lignes[l.split(";")[0]] = l
        reussies += 1
        print(f"{len(recues)} bougies")
        if n < len(tranches):
            time.sleep(PAUSE)

    if echecs_ssl:
        print("\nAucun certificat racine utilisable pour ce Python.")
        print("Sur macOS, Python n'utilise pas le trousseau systeme. Corrige avec :")
        print("\n    pip3 install --upgrade certifi\n")
        print("puis relance. Si pip3 est introuvable : python3 -m pip install --upgrade certifi")
        return 3

    if not lignes:
        # Ne rien ecrire plutot que de produire un cache vide : un fichier a
        # zero bougie ferait echouer le harnais bien plus loin, sur un message
        # sans rapport avec la vraie cause.
        print("\nAucune bougie recuperee — le cache n'est pas ecrit.")
        return 1

    ordonnees = [lignes[k] for k in sorted(lignes)]
    cible.write_text(
        "\n".join(["# timezone: UTC", EN_TETE] + ordonnees) + "\n", encoding="utf-8")

    print(f"\n{cible} : {avant} -> {len(lignes)} bougies (+{len(lignes) - avant})")
    print(f"couverture : {ordonnees[0].split(';')[0]} -> {ordonnees[-1].split(';')[0]} UTC")
    manquantes = len(tranches) - reussies
    if manquantes:
        print(f"\nATTENTION : {manquantes} tranche(s) sur {len(tranches)} ont echoue.")
        print("Le cache est incomplet. Relance la meme commande : elle reprend")
        print("les tranches manquantes et fusionne sans doublon.")
    else:
        print("\nToutes les tranches sont passees. Etape suivante :")
        print(f"\n    git add {cible.parent} && \\")
        print(f"    git commit -m \"chore: cache XAUUSD {nom}\" && git push\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
