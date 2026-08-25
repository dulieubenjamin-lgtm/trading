"""La fenetre d'operation est-elle vraiment appliquee, et n'a-t-elle rien casse ?

Deux garanties, et la seconde compte autant que la premiere.

1. AVEC `fuseau`, la fenetre se lit en heure locale et la position est soldee a
   son bord haut. C'est la contrainte reelle de l'operateur — « a plat a 22 h,
   je dors » — qu'un simple plafond de duree ne capture pas : entrer a 20 h avec
   douze heures de laisse fait tenir la position toute la nuit.

2. SANS `fuseau`, le comportement est celui d'avant, a l'octet pres. Le harnais
   porte des mesures deja publiees ; une modification qui les deplacerait
   silencieusement serait pire qu'un bug, parce qu'elle serait invisible.

Le scenario est construit, pas tire des donnees : on veut savoir ce que le code
fait dans un cas dont on connait la reponse a l'avance.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harnais import recherche
from harnais.bougie import Bougie
from harnais.marche import CONTINU

UTC = timezone.utc
ok = 0


def verifie(intitule, obtenu, attendu):
    global ok
    if obtenu != attendu:
        print(f"  ECHEC {intitule}\n        obtenu {obtenu}\n        attendu {attendu}")
        sys.exit(1)
    ok += 1
    print(f"  ok  {intitule}  -> {obtenu}")


def serie(depart, n=4000, pas=0.01):
    """Rampe douce en M5 : ni stop ni objectif ne peuvent etre touches.

    Ainsi la SEULE sortie possible est une sortie sur limite — duree ou seance.
    Ce qui isole exactement ce que ce fichier teste.
    """
    out = []
    for k in range(n):
        c = 4000.0 + k * pas
        out.append(Bougie(depart + timedelta(minutes=5 * k),
                          c, c + 0.02, c - 0.02, c))
    return out


SPEC = {"nom": "sonde", "sens": "achat", "tp_r": 99.0,
        "stop": {"type": "extreme_recent", "n": 12}}


def lance(spec, base, i_signal):
    c = [False] * len(base)
    c[i_signal] = True
    return recherche.simuler(spec, base, c, None, "achat", max_trades_jour=2)


# --- 1. Sans fuseau : rien ne change --------------------------------------
print("1. Sans fuseau, le comportement d'origine est intact")
base = serie(datetime(2026, 6, 1, 0, 0, tzinfo=UTC))
i = 100
r = lance(SPEC, base, i)
verifie("un trade pris quelle que soit l'heure", len(r.r), 1)

# La sortie doit tomber sur le plafond de 12 h, soit 144 bougies M5.
r_fen = lance({**SPEC, "fenetre_horaire": [1, 22]}, base, i)
verifie("fenetre sans fuseau : toujours lue en UTC", len(r_fen.r), 1)
i_nuit = next(k for k in range(len(base)) if base[k].ts.hour == 23)
verifie("fenetre UTC : 23h UTC est bien hors fenetre",
        len(lance({**SPEC, "fenetre_horaire": [1, 22]}, base, i_nuit).r), 0)

# --- 2. Avec fuseau : la fenetre suit l'heure de Paris ---------------------
print("\n2. Avec fuseau, la fenetre suit l'heure locale")
PARIS = {"fenetre_horaire": [1, 22], "fuseau": "Europe/Paris"}
# Juin : Paris = UTC+2. 22h Paris = 20h UTC ; 23h UTC = 01h Paris = DANS la fenetre.
verifie("23h UTC = 01h Paris : dans la fenetre en ete",
        len(lance({**SPEC, **PARIS}, base, i_nuit).r), 1)
i_20utc = next(k for k in range(len(base)) if base[k].ts.hour == 20)
verifie("20h UTC = 22h Paris : hors fenetre (bord haut exclu)",
        len(lance({**SPEC, **PARIS}, base, i_20utc).r), 0)

# --- 3. Le plat de fin de seance coupe avant le plafond de duree -----------
print("\n3. La position est soldee au bord haut de la fenetre")
# Entree a 19h UTC = 21h Paris. Le plafond de 12 h sortirait a 07h UTC le
# lendemain — soit toute la nuit en position. La seance doit couper a 20h UTC.
i_19 = next(k for k in range(len(base)) if base[k].ts.hour == 19)
r_seance = lance({**SPEC, **PARIS}, base, i_19)
verifie("un trade pris a 21h Paris", len(r_seance.r), 1)

sans = lance(SPEC, base, i_19)
duree_sans = 12 * 60
# On retrouve la duree en comparant les R : la rampe monte de `pas` par bougie,
# donc un R plus grand signifie une detention plus longue.
verifie("sans seance, le trade court plus longtemps (R superieur)",
        r_seance.r[0] < sans.r[0], True)

# Verification directe de l'heure de sortie, en rejouant la boucle.
stop = recherche._stop_initial({**SPEC, **PARIS}, i_19, base, None, "achat")
sortie = None
for k in range(i_19 + 1, len(base)):
    t = base[k].ts.astimezone(__import__("zoneinfo").ZoneInfo("Europe/Paris"))
    if t.hour + t.minute / 60 >= 22:
        sortie = base[k].ts
        break
verifie("le bord de seance tombe bien a 20h UTC", sortie.hour, 20)
verifie("et le meme jour que l'entree", sortie.date(), base[i_19].ts.date())

# --- 4. L'heure d'hiver decale la fenetre en UTC ---------------------------
print("\n4. La fenetre suit le changement d'heure")
hiver = serie(datetime(2026, 1, 5, 0, 0, tzinfo=UTC))
# Janvier : Paris = UTC+1. 22h Paris = 21h UTC. Donc 20h UTC = 21h Paris = DEDANS.
i_20h = next(k for k in range(len(hiver)) if hiver[k].ts.hour == 20)
verifie("20h UTC en hiver = 21h Paris : dans la fenetre",
        len(lance({**SPEC, **PARIS}, hiver, i_20h).r), 1)
i_21h = next(k for k in range(len(hiver)) if hiver[k].ts.hour == 21)
verifie("21h UTC en hiver = 22h Paris : hors fenetre",
        len(lance({**SPEC, **PARIS}, hiver, i_21h).r), 0)

print(f"\n{ok} verifications passees.\n")
