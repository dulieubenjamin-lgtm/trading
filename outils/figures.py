"""Le test pre-enregistre des figures chartistes, sur un instrument quelconque.

    python3 outils/figures.py XAGUSD-M5
    python3 outils/figures.py EURUSD-M5 BTCUSD-M5 XAUUSD-M5

CE QUE CE SCRIPT EXECUTE, ET CE QU'IL N'A PAS LE DROIT DE CHANGER
=================================================================
Le protocole est fixe par `preenregistrement/2026-08-20-tete-epaules.md`, ecrit
avant d'avoir vu la moindre donnee hors de l'or. Ce fichier ne fait que
l'appliquer. Il n'expose AUCUN parametre de figure en ligne de commande : un
reglage par instrument transformerait un test de confirmation en nouvelle
recherche, et c'est nommement ce que le pre-enregistrement interdit.

Trois mesures, dans cet ordre impose par l'amendement :

1. LA FRICTION D'ABORD, avant de regarder la moindre figure. Le spread est
   modelise en points de base du PRIX ; ce qu'il coute en fraction du RISQUE
   depend de la volatilite relative de l'instrument. Sur EUR/USD il mange 23 %
   du risque et le temoin aleatoire y perd -0,46 R : aucun setup, si bon soit-il,
   n'y atteint un R moyen positif. Confondre « la figure ne marche pas » avec
   « cet instrument est intradable sous ce modele de cout » serait une erreur de
   lecture, pas de mesure.

2. LE TEMOIN ALEATOIRE, qui tranche le seuil declare d'avance : au-dessus de
   -0,25 R la regle d'origine s'applique (R moyen > 0 et t > 2) ; en dessous le
   critere devient z > 2,5 contre le temoin apparie, profitabilite absolue hors
   de portee.

3. LES FIGURES, avec STOP SYMETRIQUE. Le stop structurel place le stop loin a
   l'achat et colle au prix a la vente quand le prix vient de casser vers le
   haut : comparer les deux sens sous ce stop revient a comparer un bon stop a
   un stop absurde. Le stop ATR porte le meme risque dans les deux sens, et
   c'est la seule construction qui isole la prediction.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harnais import cache, nettoyage, recherche
from harnais.marche import deduire_du_symbole

# STOP SYMETRIQUE, impose. Ce n'est pas un reglage : c'est le seul stop sous
# lequel achat et vente au meme instant portent le meme risque.
STOP = {"type": "atr", "ut": "M15", "mult": 1.5}

# PAS DE FENETRE DE SEANCE ICI, VOLONTAIREMENT. La contrainte horaire appartient
# a la specification PAPIER LIVE, decidee plus tard et pour des raisons
# d'exploitation. L'ajouter au test pre-enregistre rendrait XAG incomparable a
# EUR/USD et BTC, deja mesures sans elle. Deux objets distincts, deux specs.

# Les parametres de la tete-epaules sont ceux d'XAU, a l'identique -- c'est ce
# que le pre-enregistrement gele nommement. Les autres figures tournent sur les
# valeurs par DEFAUT de `formes.py` : elles servent de contexte, et choisir des
# valeurs pour elles instrument par instrument serait exactement le reglage
# interdit. Une liste vide veut dire « les defauts ».
#
# Un premier jet passait [3, 0.5, 60] a double_extreme, dont la signature est
# (largeur, tolerance, ecart_min, ecart_max) : cela fixait ecart_min a 60 contre
# un ecart_max par defaut de 60, soit une fenetre vide. Zero signal. Le script
# l'affichait « < 50 signaux — ne compte ni pour ni contre », c'est-a-dire
# exactement comme une figure qui ne se declenche pas sur cet instrument.
# UNE FIGURE MAL CONFIGUREE SE LIT COMME UNE FIGURE QUI NE MARCHE PAS.
FIGURES = [
    ("tete-epaules inversee", "tete_epaules_inverse", [3, 0.9, 80, 0.5], False),
    ("  + filtre H4", "tete_epaules_inverse", [3, 0.9, 80, 0.5], True),
    ("double creux", "double_creux", [], False),
    ("double sommet", "double_sommet", [], False),
    ("drapeau haussier", "drapeau_haussier", [], False),
]


def spec_figure(nom, ind, params, filtre):
    conditions = [{"gauche": {"ind": ind, "ut": "M15", "params": params},
                   "op": "croise_haut", "droite": {"const": 0.5}}]
    if filtre:
        conditions.append({"gauche": {"prix": "cloture"}, "op": ">",
                           "droite": {"ind": "ema", "ut": "H4", "params": [50]}})
    sens = "vente" if ind == "double_sommet" else "achat"
    return {"nom": nom, "sens": sens, "tp_r": 2.0, "conditions": conditions,
            "stop": STOP}


def friction(base, biblio):
    """Ce que le spread coute en fraction du risque, et ce que perd le hasard."""
    atr = biblio.serie("atr", "M15", [14])
    paires = [(a, b.cloture) for a, b in zip(atr, base) if a]
    atr_med = sorted(x for x, _ in paires)[len(paires) // 2]
    prix_med = sorted(p for _, p in paires)[len(paires) // 2]
    # Le spread est preleve aux deux bouts ; le risque vaut 1,5 x ATR.
    part = 2 * (prix_med * recherche.SPREAD_BP / 10000) / (1.5 * atr_med)
    return {"atr_bp": 10000 * atr_med / prix_med, "part_risque": part}


def temoin_hasard(base, biblio, tirages=12, graine=20260820):
    """R moyen d'entrees a l'achat tirees au hasard, memes regles de sortie."""
    modele = spec_figure("hasard", "tete_epaules_inverse", [3, 0.9, 80, 0.5], False)
    utilisables = [i for i, a in enumerate(biblio.serie("atr", "M15", [14])) if a]
    etat, moyennes = graine, []
    for _ in range(tirages):
        c = [False] * len(base)
        for _ in range(300):
            etat = (etat * 1103515245 + 12345) % (2 ** 31)
            c[utilisables[etat % len(utilisables)]] = True
        r = recherche.simuler(modele, base, c, biblio, "achat")
        if len(r.r) >= 50:
            moyennes.append(sum(r.r) / len(r.r))
    return sum(moyennes) / len(moyennes) if moyennes else None


def instrument(nom_cache: str):
    chemin = f"donnees/cache/{nom_cache}.csv"
    if not Path(chemin).exists():
        print(f"\n{nom_cache} : cache absent ({chemin})")
        print("  telecharger d'abord, par exemple :")
        sym = nom_cache.split("-")[0]
        sym = f"{sym[:3]}/{sym[3:]}"
        print(f"  python3 outils/telecharger.py --symbole {sym} "
              f"--intervalle 5min --mois 36")
        return

    brutes = cache.charger(chemin)
    marche = deduire_du_symbole(nom_cache)
    base, _ = nettoyage.filtrer(brutes, marche)
    biblio = recherche.Bibliotheque(base, marche)

    print(f"\n{'=' * 70}\n{nom_cache}   {len(base)} bougies   "
          f"{base[0].ts:%Y-%m-%d} -> {base[-1].ts:%Y-%m-%d}\n{'=' * 70}")

    f = friction(base, biblio)
    h = temoin_hasard(base, biblio)
    print(f"\n1. FRICTION")
    print(f"   ATR M15 median : {f['atr_bp']:.1f} points de base du prix")
    print(f"   le spread mange {100 * f['part_risque']:.0f} % du risque "
          f"a 1,5 x ATR")
    print(f"\n2. TEMOIN ALEATOIRE (achat, memes regles de sortie)")
    if h is None:
        print("   echantillon insuffisant")
        regle = "origine"
    else:
        print(f"   R moyen : {h:+.3f}")
        regle = "origine" if h > -0.25 else "amendee"
        if regle == "origine":
            print("   > -0,25 : la profitabilite absolue reste atteignable.")
            print("   REGLE D'ORIGINE : R moyen > 0 et t > 2.")
        else:
            print("   <= -0,25 : la friction domine cet instrument.")
            print("   REGLE AMENDEE : critere z > 2,5 contre le temoin apparie ;")
            print("   la profitabilite absolue est hors de portee sous ce cout.")

    print(f"\n3. FIGURES (stop symetrique, temoin apparie par sens, derive "
          f"soustraite)")
    print(f"   {'figure':24s} {'n':>5s} {'R moyen':>8s} {'ecart':>8s} "
          f"{'z':>7s}   verdict")
    resultats = []
    for nom, ind, params, filtre in FIGURES:
        spec = spec_figure(nom, ind, params, filtre)
        try:
            d = recherche.test_directionnel(spec, base, biblio, spec["sens"])
        except Exception as e:
            print(f"   {nom:24s} erreur : {e}")
            continue
        if d is None:
            # Le compte EXACT, jamais « < 50 » : zero signal signale une figure
            # mal configuree, trente une figure qui se declenche peu. Les
            # confondre a failli faire passer un bug de parametres pour un
            # resultat negatif.
            brut = len(recherche.indices_signal(spec, base, biblio, spec["sens"]))
            note = ("AUCUN SIGNAL — verifier les parametres de la figure"
                    if brut == 0
                    else "trop peu de signaux : ne compte ni pour ni contre")
            print(f"   {nom:24s} {brut:5d}   {note}")
            continue
        # `ecart` est la double difference (achat moins vente, derive
        # soustraite) : c'est la colonne du tableau publie. `r_sens` est le
        # R moyen brut du setup, ce que la regle d'origine nomme « R moyen ».
        ecart = d["delta_setup"] - d["delta_hasard"]
        z = ecart / d["ecart_type"]
        exces = d["r_sens"]
        if d["n"] < 100:
            v = "n < 100 : ne compte pas"
        elif regle == "origine":
            v = "PASSE" if (exces > 0 and z > 2) else "echoue"
        else:
            v = "PASSE" if z > 2.5 else "echoue"
        print(f"   {nom:24s} {d['n']:5d} {exces:+8.3f} {ecart:+8.3f} "
              f"{z:+7.2f}   {v}")
        resultats.append((nom, d["n"], exces, ecart, z, v))
    return resultats


def main() -> int:
    caches = sys.argv[1:] or ["XAUUSD-M5"]
    for c in caches:
        instrument(c)
    print("\nRappel de la regle pre-enregistree : l'hypothese demande R moyen > 0")
    print("et t > 2 sur AU MOINS DEUX des trois instruments (EUR/USD, XAG, indice),")
    print("avec n >= 100 chacun. EUR/USD a deja echoue. XAG etait declare d'avance")
    print("comme le test le PLUS FAIBLE : meme classe d'actif que l'or, memes")
    print("acteurs. Il peut donc REFUTER -- si sa figure ressort <= 0, deux")
    print("instruments sur trois sont negatifs -- mais il ne peut pas CONFIRMER.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
