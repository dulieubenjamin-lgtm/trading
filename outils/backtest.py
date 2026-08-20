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
    ap.add_argument("--cache", default=None,
                    help="par defaut le M5 s'il existe, sinon le M15")
    ap.add_argument("--regime", default="paris")
    ap.add_argument("--setups", default="S1,S2,S3")
    ap.add_argument("--debut", default=None, help="premiere date incluse (AAAA-MM-JJ)")
    ap.add_argument("--fin", default=None, help="derniere date incluse (AAAA-MM-JJ)")
    a = ap.parse_args()
    setups = tuple(s.strip() for s in a.setups.split(",") if s.strip())

    chemin = a.cache
    if chemin is None:
        m5 = Path("donnees/cache/XAUUSD-M5.csv")
        chemin = str(m5) if m5.exists() else "donnees/cache/XAUUSD-M15.csv"

    print("=" * 68)
    print("1. CHARGEMENT")
    print(f"   unite de base : {Path(chemin).stem.split('-')[-1]}")
    brutes = cache.charger(chemin)
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
        print("   (feries US, ou couverture degradee du fournisseur — "
              "voir setups/ruptures.md)")

    print("\n3. FILTRAGE DES BOUGIES SYNTHETIQUES")
    propres, rap = nettoyage.filtrer(brutes)
    print(f"   conservees        {rap['conservees']:>6}")
    print(f"   rejet calendrier  {rap['rejet_calendrier']:>6}  (week-ends)")
    print(f"   rejet amplitude   {rap['rejet_amplitude']:>6}  (feries, coupures)")
    print(f"   amplitude mediane {rap['amplitude_reference']:>6} $")

    print("\n4. WALK-FORWARD")
    ctx = contexte.construire(propres, a.regime)
    print(f"   unites derivees : " + "  ".join(
        f"{n} {len(ctx.unites[n][0])}" for n in ("M15", "H4", "D1")))
    res = moteur.executer(propres, ctx, a.regime, setups)
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

    print("\n   INCERTITUDE — une moyenne sans son intervalle ne dit rien")
    print(f"   {'setup':<6}{'n':>5}{'R moyen':>10}{'ecart-type':>12}"
          f"{'err. type':>11}{'t':>7}   intervalle 95 %")
    from statistics import mean, stdev
    for nom in sorted(stats):
        rs = [t.r_realise for t in res.trades if t.plan.setup == nom]
        if len(rs) < 3:
            print(f"   {nom:<6}{len(rs):>5}   echantillon trop court")
            continue
        m, sd = mean(rs), stdev(rs)
        se = sd / (len(rs) ** 0.5)
        t_stat = m / se if se else 0.0
        print(f"   {nom:<6}{len(rs):>5}{m:>+10.3f}{sd:>12.3f}{se:>11.3f}"
              f"{t_stat:>7.2f}   [{m - 1.96 * se:+.3f} ; {m + 1.96 * se:+.3f}]"
              + ("" if abs(t_stat) >= 1.96 else "  <- couvre zero"))

    # Drawdown maximal sur la courbe des R cumules, dans l'ordre chronologique.
    cumul, sommet, pire = 0.0, 0.0, 0.0
    for t in sorted(res.trades, key=lambda x: x.plan.ts):
        cumul += t.r_realise
        sommet = max(sommet, cumul)
        pire = min(pire, cumul - sommet)
    print(f"\n   drawdown maximal : {pire:.2f} R")

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
