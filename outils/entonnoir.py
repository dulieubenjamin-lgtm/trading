"""Entonnoir de declenchement : ou chaque setup perd ses candidats.

    python3 outils/entonnoir.py

Un backtest qui rend "3 trades" ne dit pas si les setups sont mauvais ou si une
condition d'eligibilite est mal calibree. L'entonnoir compte les barres
survivant a chaque condition successive, et localise la marche qui tue tout.
"""
from __future__ import annotations

import sys
from pathlib import Path
from statistics import median, quantiles

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harnais import cache, contexte, nettoyage, seances
from harnais.setups import _impulsion, _pivots
from harnais.vue import VueMarche

CACHE = "donnees/cache/XAUUSD-M15.csv"


def sgn(sens): return 1 if sens == "achat" else -1


def main() -> int:
    p, _ = nettoyage.filtrer(cache.charger(CACHE))
    s = contexte.construire(p)
    reg = seances.REGIMES["paris"]

    print("S1 — amplitude du range asiatique rapportee a l'ATR journalier")
    ratios, vus = [], set()
    for i, bg in enumerate(p):
        if s["range_haut"][i] is None or not s["atr_d1"][i]:
            continue
        j = seances.date_locale(bg.ts)
        if j in vus:
            continue
        vus.add(j)
        ratios.append((s["range_haut"][i] - s["range_bas"][i]) / s["atr_d1"][i])
    q = quantiles(ratios, n=20)
    print(f"   {len(ratios)} jours | min {min(ratios):.2f} | mediane {median(ratios):.2f} "
          f"| max {max(ratios):.2f}")
    print(f"   centiles  5e {q[0]:.2f}   25e {q[4]:.2f}   75e {q[14]:.2f}   95e {q[18]:.2f}")
    dans = sum(1 for r in ratios if 0.5 <= r <= 1.5)
    print(f"   regle actuelle [0,50 ; 1,50] -> {dans}/{len(ratios)} jours "
          f"({100 * dans / len(ratios):.0f} %)")

    etapes2 = dict.fromkeys(
        ["fenetre", "pente EMA H1", "prix du bon cote", "impulsion",
         "zone 0,618-0,705", "confluence EMA50", "bougie de rejet"], 0)
    for i, bg in enumerate(p):
        if not any(seances.dans_fenetre(bg.ts, f)
                   for f in (reg["fenetre_londres"], reg["fenetre_ny"])):
            continue
        etapes2["fenetre"] += 1
        atr, eh, em = s["atr_m15"][i], s["ema50_h1"][i], s["ema50_m15"][i]
        if None in (atr, eh, em) or i < 12 or s["ema50_h1"][i - 12] is None:
            continue
        v = VueMarche(p, i, s)
        for sens in ("achat", "vente"):
            k = sgn(sens)
            if k * (eh - s["ema50_h1"][i - 12]) <= 0:
                continue
            etapes2["pente EMA H1"] += 1
            if k * (bg.cloture - eh) <= 0:
                continue
            etapes2["prix du bon cote"] += 1
            imp = _impulsion(v, sens, atr)
            if imp is None:
                continue
            etapes2["impulsion"] += 1
            dep, arr, amp = imp
            z = sorted((arr - k * 0.618 * amp, arr - k * 0.705 * amp))
            if not (z[0] <= bg.cloture <= z[1]):
                continue
            etapes2["zone 0,618-0,705"] += 1
            if not (z[0] - 0.3 * atr <= em <= z[1] + 0.3 * atr):
                continue
            etapes2["confluence EMA50"] += 1
            if bg.corps < 0.10 * atr:
                continue
            meche = bg.meche_basse if sens == "achat" else bg.meche_haute
            if meche < 0.5 * bg.corps or (sens == "achat") != bg.haussiere:
                continue
            etapes2["bougie de rejet"] += 1
            break

    etapes3 = dict.fromkeys(
        ["fenetre", "ADX H1 < 20", "touche niveau 5j", "2 pivots confirmes",
         "ecart 5-20 bougies", "divergence MACD", "cloture confirmee"], 0)
    for i, bg in enumerate(p):
        if not seances.dans_fenetre(bg.ts, reg["fenetre_s3"]):
            continue
        etapes3["fenetre"] += 1
        adx, nh, nb = s["adx_h1"][i], s["plus_haut_5j"][i], s["plus_bas_5j"][i]
        if None in (adx, nh, nb) or adx >= 20:
            continue
        etapes3["ADX H1 < 20"] += 1
        v = VueMarche(p, i, s)
        for sens in ("achat", "vente"):
            k = sgn(sens)
            niv = nb if sens == "achat" else nh
            if not (bg.bas <= niv if sens == "achat" else bg.haut >= niv):
                continue
            etapes3["touche niveau 5j"] += 1
            piv = _pivots(v, sens)
            if len(piv) < 2:
                continue
            etapes3["2 pivots confirmes"] += 1
            (d1, p1), (d2, p2) = piv[0], piv[1]
            if not (5 <= abs(d1 - d2) <= 20):
                continue
            etapes3["ecart 5-20 bougies"] += 1
            if k * (p1 - p2) >= 0:
                continue
            h1, h2 = s["macd_hist"][i + d1], s["macd_hist"][i + d2]
            if h1 is None or h2 is None or k * (h1 - h2) <= 0:
                continue
            etapes3["divergence MACD"] += 1
            if k * (bg.cloture - niv) <= 0:
                continue
            etapes3["cloture confirmee"] += 1
            break

    for titre, etapes in (("S2", etapes2), ("S3", etapes3)):
        print(f"\n{titre} — entonnoir")
        for k, n in etapes.items():
            print(f"   {k:<22}{n:>7}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
