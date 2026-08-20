"""Test de l'hypothese de regime : un setup n'a-t-il d'edge que par temps donne ?

    python3 outils/regimes.py

C'EST L'ANALYSE LA PLUS DANGEREUSE DU PROJET
============================================
Decouper 188 trades en trois regimes et retenir celui qui ressort positif, c'est
de l'exploration de donnees : sur trois tirages on trouve toujours un gagnant.
Trois garde-fous, poses AVANT la mesure.

1. LES SEUILS VIENNENT DU CALIBRAGE. Les bornes de regime sont les tercils du
   ratio de volatilite sur la periode de calibrage seule. La periode de test ne
   participe pas a leur definition.

2. LES PREDICTIONS SONT ECRITES D'ABORD. Voir PREDICTIONS ci-dessous. Elles
   decoulent de la nature des setups, pas des resultats. Un resultat positif dans
   un regime NON predit est du bruit, pas une decouverte — et sera traite comme
   tel.

3. CORRECTION POUR COMPARAISONS MULTIPLES. 2 setups x 3 regimes = 6 tests. Le
   seuil de significativite passe de |t| >= 1,96 a |t| >= 2,64 (Bonferroni sur
   alpha = 5 %). Sans cette correction, une chance sur quatre de trouver un
   "effet" alors qu'il n'y en a aucun.
"""
from __future__ import annotations

import sys
from pathlib import Path
from statistics import mean, quantiles, stdev

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harnais import cache, contexte, moteur, nettoyage
from harnais.marche import deduire_du_symbole, resoudre

CACHE = "donnees/cache/XAUUSD-M5.csv"
FIN_CALIBRAGE = "2024-08-31"
DEBUT_TEST = "2024-09-01"

# Predictions posees avant toute mesure, deduites de la nature des setups.
PREDICTIONS = {
    "S1": ("agite", "cassure de range : une cassure a besoin de repondant, "
                    "et les faux signaux dominent par temps calme"),
    "S3": ("calme", "retour a la moyenne sur divergence, deja filtre par "
                    "ADX H4 < 20 : c'est un setup de range"),
}
SEUIL_T = 2.64          # Bonferroni : alpha 5 % sur 6 comparaisons
NOMS = ("calme", "normal", "agite")


def stats(rs):
    if len(rs) < 3:
        return None
    m, sd = mean(rs), stdev(rs)
    se = sd / len(rs) ** 0.5
    return m, sd, se, (m / se if se else 0.0)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=CACHE)
    ap.add_argument("--marche", default=None)
    ap.add_argument("--fin-calibrage", default=FIN_CALIBRAGE)
    ap.add_argument("--debut-test", default=DEBUT_TEST)
    a = ap.parse_args()
    global FIN_CALIBRAGE, DEBUT_TEST
    FIN_CALIBRAGE, DEBUT_TEST = a.fin_calibrage, a.debut_test

    marche = resoudre(a.marche) if a.marche else deduire_du_symbole(Path(a.cache).stem)
    print(f"INSTRUMENT  {Path(a.cache).stem}   marche : {marche.nom}\n")
    brutes = cache.charger(a.cache)

    calib = [b for b in brutes if str(b.ts.date()) <= FIN_CALIBRAGE]
    p_cal, _ = nettoyage.filtrer(calib, marche)
    ratios = [v for v in contexte.construire(p_cal, "paris", marche).series["ratio_vol"] if v]
    t1, t2 = quantiles(ratios, n=3)
    print("BORNES DE REGIME — issues du CALIBRAGE seul "
          f"({p_cal[0].ts:%Y-%m-%d} -> {p_cal[-1].ts:%Y-%m-%d})")
    print(f"   calme   ratio < {t1:.3f}")
    print(f"   normal  {t1:.3f} a {t2:.3f}")
    print(f"   agite   ratio > {t2:.3f}\n")

    print("PREDICTIONS, posees avant mesure")
    for nom, (regime, motif) in PREDICTIONS.items():
        print(f"   {nom} -> meilleur en regime « {regime} »")
        print(f"        {motif}")

    # Le contexte se construit sur l'HISTORIQUE COMPLET, et les trades sont
    # filtres ensuite sur la periode de test. Decouper les donnees d'abord fait
    # redemarrer la chauffe des indicateurs : l'ATR(100) journalier demande cent
    # seances, si bien que les cinq premiers mois du test sortaient sans regime
    # — 26 des 97 trades de S1 perdus sur un detail de methode, pas sur une
    # propriete du marche.
    #
    # Ce n'est PAS un regard vers le futur : chaque valeur reste calculee
    # uniquement a partir des bougies qui la precedent. On elargit la chauffe,
    # on ne remonte pas le temps.
    p_tout, _ = nettoyage.filtrer(brutes, marche)
    ctx = contexte.construire(p_tout, "paris", marche)
    res_tout = moteur.executer(p_tout, ctx)
    p_test = [b for b in p_tout if str(b.ts.date()) >= DEBUT_TEST]

    class _Res:
        pass
    res = _Res()
    res.trades = [t for t in res_tout.trades if str(t.plan.ts.date()) >= DEBUT_TEST]

    def classe(r):
        if r is None:
            return None
        return "calme" if r < t1 else ("normal" if r <= t2 else "agite")

    print(f"\nTEST HORS ECHANTILLON  {p_test[0].ts:%Y-%m-%d} -> "
          f"{p_test[-1].ts:%Y-%m-%d}  |  {len(res.trades)} trades")
    print(f"seuil de significativite corrige : |t| >= {SEUIL_T}\n")
    print(f"   {'setup':<6}{'regime':<9}{'n':>5}{'R moyen':>10}{'err.type':>10}"
          f"{'t':>7}   verdict")

    conclusions = {}
    for setup in ("S1", "S3"):
        for regime in NOMS:
            rs = [t.r_realise for t in res.trades
                  if t.plan.setup == setup and classe(t.ratio_vol) == regime]
            st = stats(rs)
            if st is None:
                print(f"   {setup:<6}{regime:<9}{len(rs):>5}   "
                      f"echantillon trop court")
                continue
            m, sd, se, tt = st
            significatif = abs(tt) >= SEUIL_T
            verdict = "SIGNIFICATIF" if significatif else "indiscernable de zero"
            print(f"   {setup:<6}{regime:<9}{len(rs):>5}{m:>+10.3f}{se:>10.3f}"
                  f"{tt:>7.2f}   {verdict}")
            conclusions[(setup, regime)] = (m, tt, significatif, len(rs))
        print()

    print("CONFRONTATION AUX PREDICTIONS")
    for setup, (attendu, _) in PREDICTIONS.items():
        cle = (setup, attendu)
        if cle not in conclusions:
            print(f"   {setup} : regime « {attendu} » sans echantillon exploitable")
            continue
        m, tt, sig, n = conclusions[cle]
        etat = "CONFIRMEE" if (sig and m > 0) else "NON confirmee"
        print(f"   {setup} en « {attendu} » : {m:+.3f} R sur {n} trades, "
              f"t = {tt:.2f} -> prediction {etat}")

    # ---- Test de TENDANCE, statistiquement plus puissant ------------------
    # Une hypothese d'ORDRE ("le R croit avec la volatilite") se teste par une
    # correlation sur tous les trades, pas par trois cellules separees : le
    # decoupage jette l'information de rang et divise l'echantillon par trois.
    # Deux tests seulement (un par setup), donc seuil de Bonferroni a |t| >= 2,24.
    print("\nTEST DE TENDANCE — correlation entre volatilite et R, tous trades")
    print("   (une hypothese d'ordre se teste par une pente, pas par des cases)")
    print(f"   {'setup':<6}{'n':>5}{'correlation':>13}{'t':>8}   {'attendu':<14}verdict")
    SEUIL_TENDANCE = 2.24
    for setup, (attendu, _) in PREDICTIONS.items():
        paires = [(t.ratio_vol, t.r_realise) for t in res.trades
                  if t.plan.setup == setup and t.ratio_vol is not None]
        if len(paires) < 10:
            print(f"   {setup:<6}{len(paires):>5}   echantillon trop court")
            continue
        xs, ys = zip(*paires)
        n = len(xs)
        mx, my = mean(xs), mean(ys)
        num = sum((x - mx) * (y - my) for x, y in paires)
        den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
        r = num / den if den else 0.0
        tt = r * ((n - 2) ** 0.5) / ((1 - r ** 2) ** 0.5) if abs(r) < 1 else 0.0
        sens = "croissante" if attendu == "agite" else "decroissante"
        conforme = (r > 0) == (attendu == "agite")
        if abs(tt) >= SEUIL_TENDANCE and conforme:
            verdict = "SIGNIFICATIF, conforme"
        elif conforme:
            verdict = "bon sens, non significatif"
        else:
            verdict = "sens contraire"
        print(f"   {setup:<6}{n:>5}{r:>+13.3f}{tt:>8.2f}   {sens:<14}{verdict}")

        # Combien de trades faudrait-il pour trancher a ce niveau d'effet ?
        if abs(r) > 0.01:
            besoin = (SEUIL_TENDANCE / abs(r)) ** 2 + 2
            print(f"          il faudrait ~{besoin:.0f} trades pour conclure "
                  f"(soit ~{besoin / n * 2:.0f} ans au rythme observe)")

    autres = [(k, v) for k, v in conclusions.items()
              if v[2] and v[0] > 0 and k[1] != PREDICTIONS.get(k[0], (None,))[0]]
    if autres:
        print("\n   Effets significatifs dans un regime NON predit :")
        for (setup, regime), (m, tt, _, n) in autres:
            print(f"      {setup} en « {regime} » : {m:+.3f} R, t = {tt:.2f}, n = {n}")
        print("   A traiter comme du bruit jusqu'a validation sur donnees neuves :")
        print("   une prediction faite apres coup n'est pas une prediction.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
