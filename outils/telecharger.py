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
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = "https://api.twelvedata.com/time_series"
SYMBOLE = "XAU/USD"
INTERVALLE = "15min"
MAX_POINTS = 5000          # plafond par requete, plan gratuit
PAUSE = 8.0                # 8 requetes/min sur le plan gratuit -> 1 toutes les 8 s
EN_TETE = "datetime;open;high;low;close"


def fenetres(mois: int):
    """Decoupe la periode en tranches sous le plafond de points par requete."""
    fin = datetime.now(timezone.utc)
    debut = fin - timedelta(days=30 * mois)
    # 5000 bougies de 15 min = ~52 jours. On prend 45 pour garder de la marge.
    pas = timedelta(days=45)
    curseur = debut
    while curseur < fin:
        yield curseur, min(curseur + pas, fin)
        curseur += pas


def tirer(cle: str, debut: datetime, fin: datetime) -> list[str]:
    params = urllib.parse.urlencode({
        "symbol": SYMBOLE,
        "interval": INTERVALLE,
        "start_date": debut.strftime("%Y-%m-%d %H:%M:%S"),
        "end_date": fin.strftime("%Y-%m-%d %H:%M:%S"),
        "outputsize": MAX_POINTS,
        "timezone": "UTC",
        "format": "CSV",
        "delimiter": ";",
        "apikey": cle,
    })
    with urllib.request.urlopen(f"{BASE}?{params}", timeout=60) as r:
        corps = r.read().decode("utf-8")

    if corps.lstrip().startswith("{"):        # l'API renvoie du JSON en cas d'erreur
        detail = json.loads(corps)
        raise RuntimeError(f"API : {detail.get('message', corps[:200])}")

    lignes = [l.strip() for l in corps.splitlines() if l.strip()]
    return [l for l in lignes if not l.startswith("datetime")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mois", type=int, default=7, help="profondeur en mois (defaut 7)")
    ap.add_argument("--sortie", default="donnees/cache/XAUUSD-M15.csv")
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

    cible = Path(args.sortie)
    cible.parent.mkdir(parents=True, exist_ok=True)

    lignes: dict[str, str] = {}
    if cible.exists():
        for l in cible.read_text(encoding="utf-8").splitlines():
            if l.strip() and not l.startswith(("datetime", "#")):
                lignes[l.split(";")[0]] = l
    avant = len(lignes)

    tranches = list(fenetres(args.mois))
    for n, (debut, fin) in enumerate(tranches, 1):
        print(f"[{n}/{len(tranches)}] {debut:%Y-%m-%d} -> {fin:%Y-%m-%d} ...", end=" ", flush=True)
        try:
            recues = tirer(cle, debut, fin)
        except Exception as e:
            print(f"ECHEC : {e}")
            continue
        for l in recues:
            lignes[l.split(";")[0]] = l
        print(f"{len(recues)} bougies")
        if n < len(tranches):
            time.sleep(PAUSE)

    ordonnees = [lignes[k] for k in sorted(lignes)]
    cible.write_text(
        "\n".join(["# timezone: UTC", EN_TETE] + ordonnees) + "\n", encoding="utf-8")

    print(f"\n{cible} : {avant} -> {len(lignes)} bougies (+{len(lignes) - avant})")
    if ordonnees:
        print(f"couverture : {ordonnees[0].split(';')[0]} -> {ordonnees[-1].split(';')[0]} UTC")
    print("\nCommiter ce fichier : c'est la seule source du harnais.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
