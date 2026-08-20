"""Calibre la bande d'amplitude de S1 sur une periode DELIMITEE.

    python3 outils/calibrer.py --fin 2026-04-30

REGLE DE METHODE. Le calibrage se fait sur une periode, le backtest sur une
autre. Regler un seuil d'apres la distribution d'un jeu de donnees puis
backtester sur ce meme jeu, c'est de l'ajustement en echantillon : le resultat
mesure alors la qualite du reglage, pas celle du setup.

Le choix des centiles est fixe A L'AVANCE, a partir de l'intention declaree dans
setups/S1-cassure-range-asiatique.md — ecarter les ranges degeneres (bas) et
ceux dont le mouvement a deja eu lieu (haut) — et JAMAIS d'apres les resultats.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from statistics import median, quantiles

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harnais import cache, contexte, nettoyage, seances

CENTILE_BAS, CENTILE_HAUT = 25, 90


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=None,
                    help="par defaut le M5 s'il existe, sinon le M15")
    ap.add_argument("--debut", default=None)
    ap.add_argument("--fin", required=True, help="derniere date INCLUSE du calibrage")
    a = ap.parse_args()

    chemin = a.cache
    if chemin is None:
        m5 = Path("donnees/cache/XAUUSD-M5.csv")
        chemin = str(m5) if m5.exists() else "donnees/cache/XAUUSD-M15.csv"
    b = cache.charger(chemin)
    b = [x for x in b
         if (a.debut is None or str(x.ts.date()) >= a.debut) and str(x.ts.date()) <= a.fin]
    if len(b) < 500:
        print(f"Seulement {len(b)} bougies dans cette periode pour {chemin}.")
        print("Le cache couvre-t-il bien l'intervalle demande ?")
        return 1
    p, _ = nettoyage.filtrer(b)
    s = contexte.construire(p).series

    ratios, vus = [], set()
    for i, bg in enumerate(p):
        if s["range_haut"][i] is None or not s["atr_d1"][i]:
            continue
        j = seances.date_locale(bg.ts)
        if j in vus:
            continue
        vus.add(j)
        ratios.append((s["range_haut"][i] - s["range_bas"][i]) / s["atr_d1"][i])

    if len(ratios) < 30:
        print(f"Seulement {len(ratios)} jours : echantillon trop court pour calibrer.")
        return 1

    q = quantiles(ratios, n=100)
    bas, haut = q[CENTILE_BAS - 1], q[CENTILE_HAUT - 1]
    print(f"PERIODE DE CALIBRAGE   {p[0].ts:%Y-%m-%d} -> {p[-1].ts:%Y-%m-%d}")
    print(f"   {len(ratios)} jours exploitables")
    print(f"   mediane du ratio range asiatique / ATR journalier : {median(ratios):.3f}")
    print(f"\n   {CENTILE_BAS}e centile  {bas:.3f}   <- ecarte les ranges degeneres")
    print(f"   {CENTILE_HAUT}e centile  {haut:.3f}   <- ecarte ceux qui ont deja explose")
    dans = sum(1 for r in ratios if bas <= r <= haut)
    print(f"\n   bande retenue [{bas:.2f} ; {haut:.2f}] -> {dans}/{len(ratios)} jours "
          f"eligibles ({100 * dans / len(ratios):.0f} %)")
    print(f"\n   A reporter dans harnais/setups.py :")
    print(f"      S1_RATIO_MIN = {bas:.2f}")
    print(f"      S1_RATIO_MAX = {haut:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
