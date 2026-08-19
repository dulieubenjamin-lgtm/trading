"""Validation des setups sur un scenario construit.

"Le code tourne" n'est pas "les regles marchent". On fabrique ici une journee
qui remplit exactement les conditions de S1, et on verifie que le plan produit
a les bons niveaux. Sans ce test, un setup qui ne se declenche JAMAIS passerait
pour un setup sans signal.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harnais import contexte, moteur, nettoyage
from harnais.bougie import Bougie
from harnais.setups import s1
from harnais.vue import VueMarche

UTC = timezone.utc
ok = 0


def verifie(intitule, obtenu, attendu, tol=None):
    global ok
    bon = abs(obtenu - attendu) <= tol if tol is not None else obtenu == attendu
    if not bon:
        print(f"  ECHEC {intitule}\n        obtenu {obtenu}\n        attendu {attendu}")
        sys.exit(1)
    ok += 1
    print(f"  ok  {intitule}  -> {obtenu}")


def barre(ts, o, h, b, c):
    return Bougie(ts, o, h, b, c)


def journee_neutre(depart, base=4000.0):
    """24 h de M15 oscillant d'environ +/-12 $ : fixe l'ATR journalier vers 24 $."""
    out = []
    for k in range(96):
        ts = depart + timedelta(minutes=15 * k)
        # Triangle deterministe : monte 48 barres, descend 48.
        phase = k if k < 48 else 96 - k
        centre = base - 12 + phase * 0.5
        out.append(barre(ts, centre, centre + 1.5, centre - 1.5, centre + 0.5))
    return out


# --- 18 journees de chauffe (ATR M15, ATR D1, EMA) ------------------------
bougies = []
jour = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)      # lundi
while len(bougies) < 18 * 96:
    if jour.weekday() < 5:
        bougies += journee_neutre(jour)
    jour += timedelta(days=1)

# --- la journee de test ---------------------------------------------------
# Juin : Paris = UTC+2. Range asiatique 02h-08h Paris = 00:00-06:00 UTC.
# Fenetre de cassure 09h-11h30 Paris = 07:00-09:30 UTC.
jour_test = jour if jour.weekday() < 5 else jour + timedelta(days=(7 - jour.weekday()))
HAUT_RANGE, BAS_RANGE = 4020.0, 4000.0

test = []
for k in range(24):                                 # 00:00 -> 06:00 UTC : le range
    ts = jour_test + timedelta(minutes=15 * k)
    monte = k % 2 == 0
    o, c = (4005, 4015) if monte else (4015, 4005)
    test.append(barre(ts, o, HAUT_RANGE if k == 6 else 4016,
                      BAS_RANGE if k == 9 else 4004, c))

for k in range(24, 28):                             # 06:00 -> 07:00 UTC : creux
    ts = jour_test + timedelta(minutes=15 * k)
    test.append(barre(ts, 4014, 4016, 4012, 4014))

test.append(barre(jour_test + timedelta(minutes=15 * 28), 4014, 4018, 4013, 4017))
# 07:15 UTC (09h15 Paris) : CASSURE, cloture au-dessus du haut du range
test.append(barre(jour_test + timedelta(minutes=15 * 29), 4017, 4026, 4016, 4025))
# 07:30 UTC : prolongation
test.append(barre(jour_test + timedelta(minutes=15 * 30), 4025, 4027, 4023, 4024))
# 07:45 UTC : RETEST — la meche redescend dans la zone, cloture haussiere
test.append(barre(jour_test + timedelta(minutes=15 * 31), 4021, 4024, 4019.5, 4023))
for k in range(32, 96):
    ts = jour_test + timedelta(minutes=15 * k)
    test.append(barre(ts, 4023, 4025, 4021, 4023))

bougies += test
propres, _ = nettoyage.filtrer(bougies)
series = contexte.construire(propres)

print("\n1. Le contexte expose bien le range asiatique")
i_retest = next(i for i, b in enumerate(propres)
                if b.ts == jour_test + timedelta(minutes=15 * 31))
verifie("haut du range vu au moment du retest", series["range_haut"][i_retest], HAUT_RANGE)
verifie("bas du range vu au moment du retest", series["range_bas"][i_retest], BAS_RANGE)
print(f"      ATR M15 {series['atr_m15'][i_retest]:.2f} $ | "
      f"ATR D1 {series['atr_d1'][i_retest]:.2f} $")

print("\n2. Causalite : le range n'existe pas AVANT la fin de sa fenetre")
i_dans_range = next(i for i, b in enumerate(propres)
                    if b.ts == jour_test + timedelta(minutes=15 * 10))
verifie("range inconnu pendant sa formation", series["range_haut"][i_dans_range], None)

print("\n3. S1 se declenche sur le retest")
plan = s1(VueMarche(propres, i_retest, series))
if plan is None:
    print("  ECHEC : S1 n'a produit aucun plan sur un scenario concu pour lui")
    sys.exit(1)
ok += 1
print(f"  ok  plan produit : {plan.setup} {plan.sens}")
verifie("entree = cloture de la bougie de retest", plan.entree, 4023.0)
verifie("stop sous l'entree", plan.stop < plan.entree, True)
verifie("distance au stop >= 1,2 x ATR",
        plan.risque_unitaire >= 1.2 * series["atr_m15"][i_retest] - 1e-9, True)
verifie("TP1 a exactement 1R", plan.tp1 - plan.entree, plan.risque_unitaire, tol=1e-9)
print(f"      entree {plan.entree} | stop {plan.stop:.2f} | "
      f"TP1 {plan.tp1:.2f} | TP2 {plan.tp2:.2f} | risque {plan.risque_unitaire:.2f} $")

print("\n4. S1 ne se declenche PAS avant la cassure")
i_avant = next(i for i, b in enumerate(propres)
               if b.ts == jour_test + timedelta(minutes=15 * 28))
verifie("aucun plan avant la cassure", s1(VueMarche(propres, i_avant, series)), None)

print("\n5. Le moteur execute le trade de bout en bout")
res = moteur.executer(propres, series)
# Les journees de chauffe sont des triangles deterministes : elles produisent
# elles aussi des cassures de range. On n'assert donc que sur le trade du jour
# de test, pas sur le total.
du_jour = [t for t in res.trades
           if t.plan.ts.date() == jour_test.date()]
verifie("un trade sur la journee de test", len(du_jour), 1)
t = du_jour[0]
verifie("le plan n'a PAS ete modifie par le moteur",
        t.plan.stop, plan.stop)
print(f"      {t.plan.setup} {t.plan.sens} | sortie {t.motif_sortie} | "
      f"R {t.r_realise:+.2f} | capital {res.capital:.2f} $")
verifie("cout du spread preleve a l'entree",
        t.entree_reelle > t.plan.entree, True)
verifie("taille deduite du stop, pas choisie",
        abs(t.taille - (t.capital_entree * 0.01) / t.plan.risque_unitaire) < 1e-9, True)
verifie("risque engage = 1 % du capital a l'entree",
        abs(t.taille * t.plan.risque_unitaire - t.capital_entree * 0.01) < 1e-9, True)

print("\n6. Le plan reste immuable meme apres passage a break-even")
avec_be = [t for t in res.trades if t.tp1_pris]
if avec_be:
    t2 = avec_be[0]
    verifie("stop du plan inchange", t2.plan.stop < t2.entree_reelle, True)
    verifie("stop courant remonte a l'entree", t2.stop_courant, t2.entree_reelle)
else:
    print("      (aucun trade n'a atteint TP1 dans ce scenario)")

print(f"\n{ok} verifications passees.\n")
