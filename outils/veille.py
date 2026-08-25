"""Veille papier live : la figure s'est-elle confirmee depuis la derniere fois ?

    python3 outils/telecharger.py --symbole XAU/USD --intervalle 5min --incremental
    python3 outils/veille.py

CE QUE FAIT CE SCRIPT, ET POURQUOI
==================================
Le backtest mesure une figure sur des donnees que la recherche a deja vues. Sur
137 tests, le meilleur resultat est flatteur par construction : le z observe de
2,65 correspond exactement a ce que produirait le pur hasard avec ce nombre
d'essais. Seules des bougies qui N'EXISTAIENT PAS au moment de la recherche
peuvent trancher.

D'ou trois regles, appliquees par le script et non par la bonne volonte :

1. LA SPECIFICATION EST GELEE. Son empreinte est verifiee a chaque execution.
   La modifier invalide le comptage en cours — le script le dit et refuse de
   compter la suite avec ce qui precede.
2. LE PLAN EST ECRIT AVANT L'ISSUE, dans un fichier commite separement du
   resultat. C'est le verrou anti-biais pose au premier jour de ce projet.
3. CHAQUE PASSAGE EST JOURNALISE, signal ou non. Sans cela, rien ne distingue
   « aucun signal » de « veille pas lancee », et les trades manques
   disparaitraient silencieusement de l'echantillon.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harnais import cache, contexte, fuseau, nettoyage, recherche
from harnais.marche import deduire_du_symbole

CACHE = "donnees/cache/XAUUSD-M5.csv"
GEL = "specs/papier-live.json"
JOURNAL = Path("journal/papier-live")
CAPITAL = 10_000.0
RISQUE_PCT = 1.0
BARRES_RECENTES = 36          # 3 heures de M5 : couvre un ecart entre deux veilles


EMPREINTE = ""


def verifier_gel():
    global EMPREINTE
    g = json.loads(Path(GEL).read_text(encoding="utf-8"))
    calcule = hashlib.sha256(
        json.dumps(g["spec"], sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:16]
    if calcule != g["empreinte"]:
        print("!" * 68)
        print("SPECIFICATION MODIFIEE depuis le gel.")
        print(f"   attendue {g['empreinte']}   calculee {calcule}")
        print("Le comptage en cours est invalide : les trades deja enregistres")
        print("ne testent plus la meme hypothese que les suivants. Soit on")
        print("restaure la specification, soit on repart de zero trade.")
        print("!" * 68)
        sys.exit(2)
    EMPREINTE = g["empreinte"]
    return g["spec"]


def statut_couverture(age_min: float, ferme: bool, portee_min: float) -> str:
    """`ok`, `ferme` ou `perime` — isole pour etre verifiable dans les trois cas.

    L'ordre compte : marche ferme d'abord. Un cache qui s'arrete a la cloture du
    vendredi n'est pas perime le dimanche, il est complet.
    """
    if ferme:
        return "ferme"
    return "perime" if age_min > portee_min else "ok"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--essai", action="store_true",
                    help="rejoue le dernier signal historique pour verifier que "
                         "le script produit bien un plan ; n'ecrit pas au journal")
    args = ap.parse_args()

    spec = verifier_gel()
    JOURNAL.mkdir(parents=True, exist_ok=True)

    brutes = cache.charger(CACHE)
    marche = deduire_du_symbole(Path(CACHE).stem)
    base, _ = nettoyage.filtrer(brutes, marche)
    biblio = recherche.Bibliotheque(base, marche)
    maintenant = datetime.now(timezone.utc)
    derniere = base[-1].ts
    age = (maintenant - derniere).total_seconds() / 60

    print(f"veille du {maintenant:%Y-%m-%d %H:%M} UTC")
    print(f"   cache : {len(base)} bougies, derniere {derniere:%Y-%m-%d %H:%M} UTC "
          f"({age:.0f} min)")
    # COUVERTURE. Le passage n'examine que les BARRES_RECENTES dernieres bougies
    # du cache. Si la derniere est plus vieille que cette fenetre, l'examen ne
    # touche pas le present : il ne couvre rien. Journaliser un tel passage comme
    # « aucun signal » remplirait le registre de lignes qui ressemblent a de la
    # surveillance et sont en fait de l'aveuglement — exactement ce que la
    # journalisation est censee rendre impossible.
    #
    # Marche ferme : le retard est normal, le cache s'arrete a la cloture.
    portee_min = BARRES_RECENTES * 5
    statut = statut_couverture(age, fuseau.marche_ferme(maintenant), portee_min)

    sens = spec["sens"]
    idx = [i for i in recherche.indices_signal(spec, base, biblio, sens)
           if recherche.dans_fenetre(spec, base[i].ts)]
    fenetre = len(base) if args.essai else BARRES_RECENTES
    recents = [i for i in idx if i >= len(base) - fenetre]

    if args.essai:
        print(f"   MODE ESSAI : {len(idx)} signaux dans tout l'historique, "
              f"rejeu du dernier. Rien n'est journalise.")
    else:
        registre = JOURNAL / "veilles.csv"
        nouveau = not registre.exists()
        with registre.open("a", encoding="utf-8") as f:
            if nouveau:
                f.write("veille_utc;derniere_bougie_utc;statut;signaux;empreinte\n")
            # Un passage sans couverture n'a pas de compte de signaux a declarer.
            compte = "" if statut == "perime" else str(len(recents))
            f.write(f"{maintenant:%Y-%m-%dT%H:%M}Z;{derniere:%Y-%m-%dT%H:%M}Z;"
                    f"{statut};{compte};{EMPREINTE}\n")

        if statut == "perime":
            print(f"   PASSAGE SANS COUVERTURE : le cache s'arrete il y a "
                  f"{age / 60:.0f} h, la fenetre d'examen n'en couvre que "
                  f"{portee_min / 60:.0f}.")
            print("   Rafraichir puis relancer :")
            print("   python3 outils/telecharger.py --symbole XAU/USD "
                  "--intervalle 5min --incremental")
            print("   (journalise comme « perime » : ce passage ne compte pas)")
            return 3
        if statut == "ferme":
            print("   marche ferme : le cache s'arrete normalement a la cloture.")

    if not recents:
        print(f"   aucun signal sur les {BARRES_RECENTES} dernieres bougies "
              f"({BARRES_RECENTES * 5 / 60:.0f} h)")
        print("   (passage journalise : c'est ce qui distingue « pas de signal »")
        print("    de « veille pas lancee »)")
        return 0

    i = recents[-1]
    b = base[i]
    s = 1 if sens == "achat" else -1
    stop = recherche._stop_initial(spec, i, base, biblio, sens)
    if stop is None:
        print("   signal detecte mais stop incalculable — a examiner a la main")
        return 1
    entree = b.cloture
    risque = abs(entree - stop)
    objectif = entree + s * float(spec.get("tp_r", 2.0)) * risque
    taille = (CAPITAL * RISQUE_PCT / 100) / risque
    horodatage = f"{b.ts:%Y-%m-%dT%H%M}"
    fen = spec.get("fenetre_horaire") or [0, 24]
    fin_seance = int(fen[1])
    ville = spec.get("fuseau", "UTC").split("/")[-1]
    zone = ZoneInfo(spec["fuseau"]) if spec.get("fuseau") else timezone.utc
    locale = b.ts.astimezone(zone)

    print(f"\n   *** SIGNAL — {spec['nom']} ({sens}) sur la bougie "
          f"{b.ts:%H:%M} UTC / {locale:%H:%M} {ville} ***")
    plan = f"""---
id: {horodatage}
specification: {spec['nom']}
empreinte: {EMPREINTE}
bougie_signal: {b.ts:%Y-%m-%d %H:%M}Z ({locale:%H:%M} {ville})
statut: PLANIFIE
---

# Plan papier live — {horodatage}

**Écrit AVANT l'issue. Le résultat ira dans un fichier séparé, commité plus tard.**

| | prix |
|---|---|
| Entrée ({sens}) | {entree:.2f} |
| Stop | {stop:.2f} |
| Objectif 2R | {objectif:.2f} |

- Risque par once : {risque:.2f} $
- Taille pour {RISQUE_PCT} % de {CAPITAL:.0f} $ : **{taille:.2f} onces**
- Sortie forcée : à plat à {fin_seance} h {ville}, ou 12 h après l'entrée si
  cette limite arrive avant — selon ce qui vient en premier

## Ce qui prouverait que la figure a tort

Une clôture M15 sous {stop:.2f} avant tout progrès vers l'objectif : la ligne de
cou n'a pas tenu, la figure était fausse.

## Rappel de discipline

Aucun ajustement de stop, d'objectif ou de taille. Ce trade ne teste pas un
jugement, il teste une spécification gelée. Un écart le rend inutilisable pour
le comptage.
"""
    chemin = JOURNAL / (f"{horodatage}.essai.md" if args.essai
                        else f"{horodatage}.plan.md")
    chemin.write_text(plan, encoding="utf-8")
    print(f"   entree {entree:.2f} | stop {stop:.2f} | objectif {objectif:.2f}")
    print(f"   taille {taille:.2f} onces pour {RISQUE_PCT} % de risque")
    print(f"\n   plan ecrit dans {chemin}")
    if args.essai:
        print("   (essai : ce plan ne compte pas, supprimer le fichier)")
        return 0
    print("   COMMITER CE PLAN MAINTENANT, avant de connaitre l'issue :")
    print(f"      git add {chemin} && git commit -m \"plan: {horodatage}\" && git push")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
