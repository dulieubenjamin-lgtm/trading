"""Le cache est-il sain ? A lancer apres toute mise a jour incrementale.

    python3 outils/verifier_cache.py

POURQUOI CET OUTIL EXISTE
=========================
`test_donnees.py` valide le harnais sur des fixtures figees. Rien ne validait le
cache REEL — celui dans lequel `--incremental` ecrit deux fois par jour, et dont
depend un protocole prevu pour durer des annees.

Une soudure ratee ne leve aucune erreur : elle produit des bougies. Un decalage
de fuseau introduit un lundi, des doublons a la jonction, un trou pris pour un
mouvement de prix — tout cela se lit comme du prix et fausse le comptage en
silence. C'est exactement la classe de defaut que ce projet documente depuis §A.

Cinq controles, chacun capable de dire non.
"""
from __future__ import annotations

import sys
from collections import Counter
from datetime import timedelta
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harnais import cache, fuseau, nettoyage
from harnais.marche import deduire_du_symbole

CACHE = "donnees/cache/XAUUSD-M5.csv"
echecs = 0


def controle(intitule, ok, detail=""):
    global echecs
    marque = " ok " if ok else "ECHEC"
    if not ok:
        echecs += 1
    print(f"  {marque}  {intitule}" + (f"\n         {detail}" if detail else ""))


def main() -> int:
    chemin = Path(sys.argv[1] if len(sys.argv) > 1 else CACHE)
    print(f"verification de {chemin}\n")

    # 1. Le marqueur de fuseau. Sans lui, le chargeur suppose une valeur par
    #    defaut : une mise a jour qui l'effacerait decalerait tout l'historique.
    tete = chemin.read_text(encoding="utf-8").split("\n", 1)[0]
    controle("marqueur de fuseau present", tete.startswith("# timezone:"),
             f"premiere ligne : {tete!r}")

    brutes = cache.charger(chemin)
    marche = deduire_du_symbole(chemin.stem)
    base, rejet = nettoyage.filtrer(brutes, marche)
    print(f"\n  {len(brutes)} bougies lues, {len(base)} retenues apres filtrage")
    print(f"  couverture : {brutes[0].ts:%Y-%m-%d %H:%M} -> "
          f"{brutes[-1].ts:%Y-%m-%d %H:%M} UTC\n")

    # 2. Pas de doublon d'horodatage. La mise a jour incrementale reecrit le
    #    fichier depuis un dictionnaire cle par horodatage, donc un doublon
    #    signalerait une corruption d'un tout autre ordre.
    compte = Counter(b.ts for b in brutes)
    doubles = [ts for ts, n in compte.items() if n > 1]
    controle("aucun horodatage en double", not doubles,
             f"{len(doubles)} doublons, ex. {doubles[:3]}" if doubles else "")

    # 3. Ordre strictement croissant.
    desordre = [a.ts for a, b in zip(brutes, brutes[1:]) if b.ts <= a.ts]
    controle("horodatages strictement croissants", not desordre,
             f"{len(desordre)} inversions, ex. {desordre[:3]}" if desordre else "")

    # 4. Le pas median est bien celui annonce par le nom du fichier.
    pas = median([(b.ts - a.ts).total_seconds()
                  for a, b in zip(brutes, brutes[1:])])
    attendu = 300 if "M5" in chemin.stem else None
    controle(f"pas median de {pas:.0f} s",
             attendu is None or pas == attendu,
             f"attendu {attendu} s" if attendu and pas != attendu else "")

    # 5. L'assertion de fuseau : la fermeture hebdomadaire observee tombe-t-elle
    #    ou le calendrier la place ? C'est le controle qui attrape un decalage
    #    d'heure introduit par une mise a jour.
    if marche.continu:
        info = fuseau.verifier_continuite(brutes)
        controle(f"continuite {info['couverture']:.1%}", True,
                 f"plus grand trou : {info['plus_grand_trou']}")
    else:
        try:
            info = fuseau.verifier_decalage(brutes)
            controle("fermeture hebdomadaire a l'heure attendue", True,
                     f"ecart median {info['ecart_median']} sur "
                     f"{info['controles']} fermetures, max {info['ecart_max']} "
                     f"({len(info['seances_ecourtees'])} seances ecourtees)")
        except Exception as e:
            controle("fermeture hebdomadaire a l'heure attendue", False, str(e))

    # 6. Les trous — mesures sur les bougies BRUTES, pas sur les retenues.
    #    Le filtrage ecarte les bougies figees ; sur `base` une accalmie filtree
    #    ressemble a un trou et le controle ne voudrait rien dire. Ce qui est
    #    teste ici est autre chose : le flux a-t-il livre toutes les bougies.
    #
    #    Une interruption ne se juge pas a son bord mais a ce qu'elle contient.
    #    Trois causes legitimes, et il faut les nommer pour que ce qui reste
    #    signifie quelque chose :
    #      - week-end       le marche est ferme au milieu du trou
    #      - bascule        la coupure quotidienne de 17 h New York, ~1 h
    #      - ferie          Noel, Jour de l'an, Presidents' Day, Vendredi saint
    #    Le calendrier du harnais ne connait que les week-ends. Les feries
    #    ressortent donc ici, et c'est voulu : mieux vaut les voir listes que
    #    codes en dur dans un calendrier a maintenir.
    pas_td = timedelta(seconds=pas)
    trous = [(b.ts - a.ts, a.ts) for a, b in zip(brutes, brutes[1:])
             if b.ts - a.ts > pas_td * 3]

    def classe(d, ts):
        if fuseau.marche_ferme(ts + d / 2):
            return "week-end"
        if d < timedelta(hours=2) and 20 <= (ts + d / 2).hour < 23:
            return "bascule 17h NY"
        return "inexplique"

    par_classe = Counter(classe(d, ts) for d, ts in trous)
    print()
    for nom, n in par_classe.most_common():
        print(f"         {n:4d}  {nom}")

    restes = [(d, ts) for d, ts in trous if classe(d, ts) == "inexplique"]
    perdu = sum(d.total_seconds() for d, ts in restes) / 3600
    total = (brutes[-1].ts - brutes[0].ts).total_seconds() / 3600
    controle(f"temps inexplique sous 1 % de l'historique "
             f"({perdu:.0f} h sur {total:.0f} h, {100 * perdu / total:.2f} %)",
             perdu / total < 0.01)

    longs = sorted((x for x in restes if x[0] > timedelta(hours=12)), reverse=True)
    if longs:
        print(f"\n  {len(longs)} interruption(s) inexpliquee(s) de plus de 12 h :")
        for d, ts in longs:
            print(f"         {ts:%Y-%m-%d %a %H:%M} -> {ts + d:%Y-%m-%d %a %H:%M} "
                  f"UTC   ({d})")
        print("         (feries pour la plupart ; un trou en pleine semaine "
              "ordinaire\n          est un vrai defaut de flux)")

    # 7. LE CONTROLE QUI COMPTE AU QUOTIDIEN. Les six precedents portent sur
    #    trois ans d'historique, ou une anomalie recente se noie. Une mise a
    #    jour incrementale ratee n'abime que la fin du fichier : on la regarde
    #    donc separement.
    print()
    recent = [b for b in brutes if b.ts > brutes[-1].ts - timedelta(days=7)]
    trous_r = [(b.ts - a.ts, a.ts) for a, b in zip(recent, recent[1:])
               if b.ts - a.ts > pas_td * 3
               and classe(b.ts - a.ts, a.ts) == "inexplique"]
    controle(f"7 derniers jours sans trou inexplique ({len(recent)} bougies)",
             not trous_r,
             ", ".join(f"{ts:%m-%d %H:%M} ({d})" for d, ts in trous_r[:3])
             if trous_r else "")

    print(f"\n{'CACHE SAIN' if not echecs else f'{echecs} CONTROLE(S) EN ECHEC'}\n")
    return 1 if echecs else 0


if __name__ == "__main__":
    raise SystemExit(main())
