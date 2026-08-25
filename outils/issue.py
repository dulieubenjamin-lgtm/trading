"""Denoue les plans en attente a partir des bougies. Aucune saisie a la main.

    python3 outils/issue.py

POURQUOI LA MACHINE, ET PAS TOI
===============================
L'issue d'un trade n'est pas une opinion : le plan fixe l'entree, le stop et
l'objectif, et les bougies determinent le reste. La saisir a la main
n'ajouterait aucune information et ouvrirait deux failles.

La premiere est l'erreur ordinaire -- un chiffre mal recopie six mois plus tard.
La seconde est plus grave : un echantillon live denoue a la main ne serait plus
comparable au backtest denoue par machine. Or c'est exactement cette comparaison
qui justifie le protocole. Les deux passent donc par `recherche.denouer`, une
seule implementation, memes conventions defavorables : le stop l'emporte en cas
d'ambiguite, le spread est preleve aux deux bouts.

LE PLAN N'EST JAMAIS MODIFIE. L'issue s'ecrit a cote, dans un fichier distinct.
Un plan qu'on amende n'est plus un plan.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harnais import cache, nettoyage, recherche
from harnais.marche import deduire_du_symbole

CACHE = "donnees/cache/XAUUSD-M5.csv"
GEL = "specs/papier-live.json"
JOURNAL = Path("journal/papier-live")


def lire_entete(chemin: Path) -> dict:
    """Lit l'en-tete YAML minimal d'un plan. Volontairement naif : le format est
    produit par ce depot, pas recu de l'exterieur."""
    lignes = chemin.read_text(encoding="utf-8").splitlines()
    if not lignes or lignes[0].strip() != "---":
        raise ValueError(f"{chemin} : en-tete absent")
    entete = {}
    for ligne in lignes[1:]:
        if ligne.strip() == "---":
            break
        if ":" in ligne:
            cle, val = ligne.split(":", 1)
            entete[cle.strip()] = val.strip()
    return entete


def main() -> int:
    spec = json.loads(Path(GEL).read_text(encoding="utf-8"))["spec"]
    brutes = cache.charger(CACHE)
    marche = deduire_du_symbole(Path(CACHE).stem)
    base, _ = nettoyage.filtrer(brutes, marche)
    par_ts = {b.ts: i for i, b in enumerate(base)}

    zone = ZoneInfo(spec["fuseau"]) if spec.get("fuseau") else None
    fen = spec.get("fenetre_horaire")
    h_max = float(fen[1]) if fen and len(fen) == 2 else None

    plans = sorted(JOURNAL.glob("*.plan.md"))
    if not plans:
        print("aucun plan a denouer.")
        return 0

    ouverts = clos = 0
    for chemin in plans:
        cible = chemin.with_name(chemin.name.replace(".plan.md", ".issue.md"))
        if cible.exists():
            continue

        e = lire_entete(chemin)
        ts = datetime.strptime(e["bougie_signal"], "%Y-%m-%d %H:%MZ").replace(
            tzinfo=timezone.utc)
        i = par_ts.get(ts)
        if i is None:
            print(f"  {chemin.name} : bougie {ts:%Y-%m-%d %H:%M}Z absente du "
                  f"cache — rafraichir puis relancer")
            continue

        sens = e["sens"]
        s = 1 if sens == "achat" else -1
        entree = float(e["entree"])
        stop = float(e["stop"])
        objectif = float(e["objectif"])
        risque = float(e["risque_unitaire"])

        j, prix, motif = recherche.denouer(
            base, i, stop, objectif, sens,
            ts + recherche.DUREE_MAX, zone, h_max)

        if prix is None:
            ouverts += 1
            print(f"  {chemin.name} : EN COURS depuis {ts:%d/%m %H:%M}Z")
            continue

        # Meme modele de cout que le backtest : le spread est preleve aux deux
        # bouts. L'entree du plan le porte deja, il reste celui de la sortie.
        cout = base[j].cloture * recherche.SPREAD_BP / 10000
        nette = prix - s * cout
        r = s * (nette - entree) / risque

        cible.write_text(f"""---
id: {e['id']}
plan: {chemin.name}
issue: {motif.upper()}
sortie_le: {base[j].ts:%Y-%m-%d %H:%M}Z
prix_sortie: {nette:.2f}
r: {r:+.3f}
duree_h: {(base[j].ts - ts).total_seconds() / 3600:.1f}
---

# Issue — {e['id']}

Denoue mecaniquement par `outils/issue.py` a partir des bougies du cache, avec
les memes conventions que le backtest. Le plan n'a pas ete modifie.

| | |
|---|---|
| Sortie | **{motif}** a {nette:.2f} |
| Horodatage | {base[j].ts:%Y-%m-%d %H:%M} UTC |
| Duree | {(base[j].ts - ts).total_seconds() / 3600:.1f} h |
| Résultat | **{r:+.3f} R** |
""", encoding="utf-8")
        clos += 1
        print(f"  {chemin.name} : {motif.upper()} a {nette:.2f} — {r:+.3f} R")

    if not clos and not ouverts:
        print("rien de nouveau : tous les plans sont deja denoues.")
    else:
        print(f"\n{clos} denoue(s), {ouverts} en cours.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
