"""Lance le walk-forward sur le cache et rend compte.

    python3 outils/backtest.py [--regime paris] [--setups S1,S2,S3]

Aucun appel reseau : tout vient du cache disque, donc deux executions donnent
exactement le meme resultat.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harnais import cache, contexte, moteur, nettoyage, seances
from harnais.fuseau import verifier_decalage


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="donnees/cache/XAUUSD-M15.csv")
    ap.add_argument("--regime", default="paris")
    ap.add_argument("--setups", default="S1,S2,S3")
    ap.add_argument("--debut", default=None, help="premiere date incluse (AAAA-MM-JJ)")
    ap.add_argument("--fin", default=None, help="derniere date incluse (AAAA-MM-JJ)")
    a = ap.parse_args()
    setups = tuple(s.strip() for s in a.setups.split(",") if s.strip())

    print("=" * 68)
    print("1. CHARGEMENT")
    brutes = cache.charger(a.cache)
    if a.debut or a.fin:
        brutes = [x for x in brutes
                  if (a.debut is None or str(x.ts.date()) >= a.debut)
                  and (a.fin is None or str(x.ts.date()) <= a.fin)]
    print(f"   {len(brutes)} bougies  |  {brutes[0].ts:%Y-%m-%d %H:%M} -> "
          f"{brutes[-1].ts:%Y-%m-%d %H:%M} UTC")

    print("\n2. VERIFICATION DU FUSEAU (assertion contre le calendrier forex)")
    r = verifier_decalage(brutes)
    print(f"   {r['controles']} fermetures hebdomadaires localisees")
    print(f"   ecart median au vendredi 17h New York : {r['ecart_median']}  (teste le fuseau)")
    if r['seances_ecourtees']:
        print(f"   seances ecourtees detectees : " +
              ", ".join(str(d) for d in r['seances_ecourtees']))
        print(f"   (feries US — le rulebook n'a pas de calendrier, voir setups/ruptures.md)")

    print("\n3. FILTRAGE DES BOUGIES SYNTHETIQUES")
    propres, rap = nettoyage.filtrer(brutes)
    print(f"   conservees        {rap['conservees']:>6}")
    print(f"   rejet calendrier  {rap['rejet_calendrier']:>6}  (week-ends)")
    print(f"   rejet amplitude   {rap['rejet_amplitude']:>6}  (feries, coupures)")
    print(f"   amplitude mediane {rap['amplitude_reference']:>6} $")

    print("\n4. WALK-FORWARD")
    series = contexte.construire(propres, a.regime)
    res = moteur.executer(propres, series, a.regime, setups)
    print(f"   {res.barres_parcourues} barres parcourues, {len(res.trades)} trades")

    if not res.trades:
        print("\n   AUCUN TRADE. Ce n'est pas un verdict sur les setups :")
        print("   verifier d'abord que les conditions d'eligibilite sont atteignables.")
        return 0

    print("\n5. RESULTATS PAR SETUP")
    print(f"   {'setup':<6}{'n':>5}{'reussite':>11}{'R total':>10}{'R moyen':>10}")
    stats = res.par_setup()
    for nom in sorted(stats):
        s = stats[nom]
        print(f"   {nom:<6}{s['n']:>5}{s['taux_reussite']:>10.1f}%"
              f"{s['r']:>+10.2f}{s['r_moyen']:>+10.3f}")
    total_r = sum(s["r"] for s in stats.values())
    print(f"   {'TOTAL':<6}{len(res.trades):>5}{'':>11}{total_r:>+10.2f}")

    print(f"\n   capital  10 000,00 $ -> {res.capital:>10,.2f} $  "
          f"({100 * (res.capital - 10000) / 10000:+.2f} %)")

    print("\n6. MOTIFS DE SORTIE")
    for motif, n in Counter(t.motif_sortie for t in res.trades).most_common():
        print(f"   {motif:<16}{n:>5}  ({100 * n / len(res.trades):.0f} %)")

    print("\n7. REPARTITION MENSUELLE")
    par_mois = {}
    for t in res.trades:
        k = f"{t.plan.ts:%Y-%m}"
        e = par_mois.setdefault(k, [0, 0.0])
        e[0] += 1
        e[1] += t.r_realise
    for k in sorted(par_mois):
        n, r = par_mois[k]
        print(f"   {k}   {n:>3} trades   {r:>+7.2f} R")

    print("\n8. REFUS DU MOTEUR")
    print(f"   {res.refus or 'aucun'}")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
