"""Protocole de recherche de setups, avec toutes les protections anti-illusion.

    python3 outils/rechercher.py --specs specs/candidats.json

POURQUOI CE PROTOCOLE EST AUSSI LOURD
=====================================
Chercher le meilleur setup dans un jeu de donnees GARANTIT d'en trouver un. Avec
N hypotheses testees sur du bruit pur, le meilleur t observe vaut environ
sqrt(2 ln N) : 3,0 pour N=100, 3,7 pour N=1000. Un t de 3 en recherche ne prouve
donc rien du tout. Quatre protections :

1. QUATRE FENETRES SUCCESSIVES, chacune franchie avant d'acceder a la suivante :
      recherche    XAU annee 1   on y explore librement
      validation   XAU annee 2   premier filtre reel
      holdout      XAU annee 3   touche UNE fois, a la toute fin
      croise       BTC 3 ans     touche UNE fois — l'epreuve la plus severe
2. TEMOIN ALEATOIRE : des setups a entree pseudo-aleatoire, meme frequence et
   meme structure stop/TP, donnent la distribution empirique du "aucun edge".
   Un candidat doit battre cette distribution, pas seulement zero.
3. SEUIL DE FREQUENCE : tout setup incapable de produire 200 trades sur une
   annee est ecarte AVANT d'etre juge sur sa performance. Une combinaison rare
   ne peut rien prouver, aussi belle soit-elle.
4. CORRECTION DE BONFERRONI sur le nombre exact d'hypotheses testees.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harnais import cache, nettoyage, recherche
from harnais.marche import deduire_du_symbole

FENETRES = {
    "recherche":  ("XAUUSD", "2023-09-05", "2024-08-31"),
    "validation": ("XAUUSD", "2024-09-01", "2025-08-31"),
    "holdout":    ("XAUUSD", "2025-09-01", "2026-12-31"),
    "croise":     ("BTCUSD", "2023-09-05", "2026-12-31"),
}
TRADES_MINIMUM = 200        # exigence de l'utilisateur : faire ses preuves
MAX_TRADES_JOUR = 2


def charger(instrument, debut, fin):
    b = cache.charger(f"donnees/cache/{instrument}-M5.csv")
    b = [x for x in b if debut <= str(x.ts.date()) <= fin]
    m = deduire_du_symbole(instrument)
    p, _ = nettoyage.filtrer(b, m)
    return p, recherche.Bibliotheque(p, m)


def specs_temoin(n=60, graine=12345):
    """Setups a entree pseudo-aleatoire, meme structure stop/TP.

    Le declencheur est une condition sur l'heure decimale, deterministe mais sans
    rapport avec le prix : elle produit des entrees regulieres et arbitraires.
    C'est le "aucun edge" incarne, mesure par la meme machinerie.
    """
    out, etat = [], graine
    for k in range(n):
        etat = (etat * 1103515245 + 12345) % (2 ** 31)
        minute = etat % 12 * 5
        etat = (etat * 1103515245 + 12345) % (2 ** 31)
        h_debut = 6 + etat % 12
        out.append({
            "nom": f"temoin-{k:02d}", "sens": "achat" if k % 2 else "vente",
            "tp_r": 2.0,
            "conditions": [
                {"gauche": {"ind": "heure_utc", "ut": "M5"}, "op": ">=",
                 "droite": {"const": h_debut}},
                {"gauche": {"ind": "heure_utc", "ut": "M5"}, "op": "<",
                 "droite": {"const": h_debut + 0.1 + minute / 600}},
            ],
            "stop": {"type": "atr", "ut": "M15", "mult": 1.5},
        })
    return out


def stats_temoin(instrument, debut, fin, n=120):
    """Distribution du « aucun edge », SEPAREE PAR SENS.

    Un temoin melangeant achats et ventes est un piege. Sur XAU l'ecart entre
    entrees longues et courtes purement aleatoires vaut +0,107 R sur l'annee 1 et
    +0,128 R sur l'annee 2 : c'est la derive haussiere, et elle gonfle
    mecaniquement tout setup acheteur d'environ un ecart-type. Comparer un setup
    long a un temoin mixte, c'est lui crediter la tendance du marche comme si
    c'etait son edge.

    Chaque candidat est donc mesure contre le hasard DE SON PROPRE SENS, sur la
    MEME fenetre — la derive n'etant pas la meme d'une annee a l'autre.
    """
    base, biblio = charger(instrument, debut, fin)
    par_sens = {"achat": [], "vente": []}
    for spec in specs_temoin(n):
        for sens in ("achat", "vente"):
            s = dict(spec)
            s["sens"] = sens
            for nom_sens, res in recherche.executer_spec(
                    s, base, biblio, MAX_TRADES_JOUR).items():
                st = res.stats()
                if st and st["n"] >= 50:
                    par_sens[nom_sens].append(st["r_moyen"])
    sortie = {}
    for sens, v in par_sens.items():
        if len(v) < 5:
            continue
        m = sum(v) / len(v)
        sd = (sum((x - m) ** 2 for x in v) / (len(v) - 1)) ** 0.5
        sortie[sens] = {"moyenne": m, "ecart_type": sd, "n": len(v),
                        "derive": None}
    if "achat" in sortie and "vente" in sortie:
        ecart = sortie["achat"]["moyenne"] - sortie["vente"]["moyenne"]
        sortie["achat"]["derive"] = ecart
        sortie["vente"]["derive"] = -ecart
    return sortie


def evaluer(specs, instrument, debut, fin, etiquette):
    base, biblio = charger(instrument, debut, fin)
    print(f"   {etiquette:<11} {instrument} {debut} -> {fin}  "
          f"({len(base)} bougies)")
    sorties = {}
    for spec in specs:
        try:
            for sens, res in recherche.executer_spec(
                    spec, base, biblio, MAX_TRADES_JOUR).items():
                st = res.stats()
                if st:
                    sorties[(spec["nom"], sens)] = st
        except recherche.SpecInvalide:
            continue
    return sorties


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--specs", required=True)
    ap.add_argument("--etapes", default="recherche,validation")
    a = ap.parse_args()

    specs = json.loads(Path(a.specs).read_text(encoding="utf-8"))
    etapes = [e.strip() for e in a.etapes.split(",")]
    print(f"{len(specs)} specifications chargees depuis {a.specs}\n")

    print("TEMOIN ALEATOIRE, SEPARE PAR SENS")
    print("   Un temoin mixte crediterait a tout setup long la derive du marche")
    print("   comme si c'etait son edge. Chaque candidat est mesure contre le")
    print("   hasard DE SON PROPRE SENS, sur la MEME fenetre.\n")
    temoins = {}
    for etape in etapes:
        instrument, d, f = FENETRES[etape]
        temoins[etape] = stats_temoin(instrument, d, f)
        t = temoins[etape]
        b0, b1 = charger(instrument, d, f)[0][0], charger(instrument, d, f)[0][-1]
        derive_prix = 100 * (b1.cloture / b0.cloture - 1)
        print(f"   {etape:<11} {instrument}  prix {derive_prix:+.0f} %")
        for sens in ("achat", "vente"):
            if sens in t:
                print(f"      {sens:<7} R moyen {t[sens]['moyenne']:+.3f}  "
                      f"ecart-type {t[sens]['ecart_type']:.3f}  "
                      f"({t[sens]['n']} temoins)")
        if "achat" in t and "vente" in t:
            print(f"      ecart achat-vente : {t['achat']['derive']:+.3f} R "
                  f"<- valeur de la derive, a ne PAS crediter au setup")
    print()

    survivants = specs
    resultats = {}
    for etape in etapes:
        instrument, debut, fin = FENETRES[etape]
        print(f"ETAPE « {etape} »")
        r = evaluer(survivants, instrument, debut, fin, etape)
        resultats[etape] = r

        assez_frequents = {k: v for k, v in r.items()
                           if v["n"] >= TRADES_MINIMUM * (1 if etape != "croise" else 3)}
        print(f"   {len(r)} variantes evaluees, "
              f"{len(assez_frequents)} atteignent le seuil de frequence "
              f"({TRADES_MINIMUM} trades)")

        tem = temoins.get(etape, {})
        for (nom, sens), v in assez_frequents.items():
            ref = tem.get(sens)
            v["z_temoin"] = ((v["r_moyen"] - ref["moyenne"]) / ref["ecart_type"]
                             if ref and ref["ecart_type"] else 0.0)
        positifs = {k: v for k, v in assez_frequents.items() if v["z_temoin"] > 1.0}
        print(f"   {len(positifs)} depassent le temoin d'au moins 1 ecart-type\n")

        noms = {k[0] for k in positifs}
        survivants = [s for s in specs if s["nom"] in noms]
        if not survivants:
            print("   Aucun survivant : la recherche s'arrete ici.")
            break

    n_tests = sum(len(v) for v in resultats.values())
    if n_tests:
        seuil = 1.96
        seuil_bonf = abs(_quantile_normal(1 - 0.05 / (2 * n_tests)))
        attendu_max = math.sqrt(2 * math.log(max(n_tests, 2)))
        print(f"COMPTABILITE DES HYPOTHESES")
        print(f"   {n_tests} tests effectues au total")
        print(f"   seuil de Bonferroni : |t| >= {seuil_bonf:.2f}")
        print(f"   t maximal attendu sous l'hypothese nulle : {attendu_max:.2f}")
        print(f"   (tout t inferieur a {attendu_max:.2f} est compatible avec l'absence "
              f"totale d'edge)")

    derniere = etapes[-1] if etapes[-1] in resultats else list(resultats)[-1]
    classement = sorted(resultats[derniere].items(),
                        key=lambda kv: -kv[1].get("z_temoin", 0.0))[:15]
    print(f"\nMEILLEURS a l'etape « {derniere} » (attention : classement = selection)")
    print(f"   {'setup':<32}{'sens':<7}{'n':>5}{'reuss.':>8}{'R moy':>9}"
          f"{'z/temoin':>10}{'/jour':>7}")
    for (nom, sens), v in classement:
        z = v.get("z_temoin", 0.0)
        print(f"   {nom[:31]:<32}{sens:<7}{v['n']:>5}{v['reussite']:>7.1f}%"
              f"{v['r_moyen']:>+9.3f}{z:>+10.2f}{v['trades_par_jour']:>7.2f}")

    Path("resultats").mkdir(exist_ok=True)
    Path("resultats/recherche.json").write_text(
        json.dumps({e: {f"{k[0]}|{k[1]}": v for k, v in r.items()}
                    for e, r in resultats.items()}, indent=1), encoding="utf-8")
    print("\n   detail complet dans resultats/recherche.json")
    return 0


def _quantile_normal(p):
    """Inverse de la loi normale centree reduite (approximation d'Acklam)."""
    a = [-39.69683028665376, 220.9460984245205, -275.9285104469687,
         138.3577518672690, -30.66479806614716, 2.506628277459239]
    b = [-54.47609879822406, 161.5858368580409, -155.6989798598866,
         66.80131188771972, -13.28068155288572]
    c = [-0.007784894002430293, -0.3223964580411365, -2.400758277161838,
         -2.549732539343734, 4.374664141464968, 2.938163982698783]
    d = [0.007784695709041462, 0.3224671290700398, 2.445134137142996,
         3.754408661907416]
    pb = 0.02425
    if p < pb:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > 1 - pb:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q, r = p - 0.5, (p - 0.5) ** 2
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


if __name__ == "__main__":
    raise SystemExit(main())
