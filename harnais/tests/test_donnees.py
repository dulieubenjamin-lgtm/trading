"""Validation de la couche donnees contre de VRAIES bougies Twelve Data.

Les deux fixtures encadrent une bascule d'heure d'ete de l'hemisphere sud :
aout (Sydney +10) et janvier (Sydney +11). Si la conversion etait codee avec un
decalage fixe, l'une des deux echouerait — c'est tout l'interet du jeu.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harnais import cache, nettoyage
from harnais.fuseau import etiquette_vers_utc, marche_ferme, verifier_decalage

ICI = Path(__file__).parent
UTC = timezone.utc
ok = 0


def verifie(intitule, obtenu, attendu):
    global ok
    if obtenu != attendu:
        print(f"  ECHEC {intitule}\n        obtenu  {obtenu}\n        attendu {attendu}")
        sys.exit(1)
    ok += 1
    print(f"  ok  {intitule}  -> {obtenu}")


print("\n1. Conversion Sydney -> UTC, de part et d'autre du DST austral")
verifie("aout, +10 attendu   : 2026-08-15 07:00 Sydney",
        etiquette_vers_utc("2026-08-15 07:00:00"),
        datetime(2026, 8, 14, 21, 0, tzinfo=UTC))
verifie("janvier, +11 attendu: 2026-01-17 09:00 Sydney",
        etiquette_vers_utc("2026-01-17 09:00:00"),
        datetime(2026, 1, 16, 22, 0, tzinfo=UTC))

print("\n2. Ces deux instants sont bien la fermeture forex du vendredi 17h NY")
for etiquette in ("2026-08-15 07:00:00", "2026-01-17 09:00:00"):
    instant = etiquette_vers_utc(etiquette)
    ny = instant.astimezone(__import__("zoneinfo").ZoneInfo("America/New_York"))
    verifie(f"{etiquette} -> New York", ny.strftime("%A %H:%M"), "Friday 17:00")

print("\n3. Chargement, tri chronologique, detection de doublons")
aout = cache.charger(ICI / "fixture-2026-08-15.csv")
janvier = cache.charger(ICI / "fixture-2026-01-17.csv")
verifie("aout : nombre de bougies", len(aout), 49)
verifie("aout : trie par temps croissant",
        all(a.ts < b.ts for a, b in zip(aout, aout[1:])), True)
verifie("janvier : nombre de bougies", len(janvier), 21)

print("\n4. Assertion de decalage (le filet de securite)")
for nom, jeu in (("aout", aout), ("janvier", janvier)):
    # Fixtures de 21 a 49 bougies : la plage figee n'y atteint pas les quatre
    # heures exigees sur un jeu reel. On abaisse le seuil pour ces echantillons.
    rapport = verifier_decalage(jeu, minimum=20, duree_minimale=timedelta(hours=1))
    verifie(f"{nom} : fermeture hebdo trouvee", rapport["controles"] >= 1, True)
    verifie(f"{nom} : ecart au calendrier forex",
            rapport["ecart_max"] <= timedelta(minutes=30), True)
    print(f"      ecart mesure : {rapport['ecart_max']}")

print("\n5. Filtrage des bougies synthetiques")
for nom, jeu, attendu_conserve in (("aout", aout, 28), ("janvier", janvier, 12)):
    propres, r = nettoyage.filtrer(jeu)
    verifie(f"{nom} : bougies conservees", r["conservees"], attendu_conserve)
    verifie(f"{nom} : aucune figee ne passe",
            all(b.amplitude > 1.0 for b in propres), True)
    print(f"      calendrier {r['rejet_calendrier']}, amplitude "
          f"{r['rejet_amplitude']}, reference {r['amplitude_reference']} $")

print("\n6. Le decalage fixe naif aurait-il ete detecte ?")
# On simule l'erreur : lire les etiquettes d'aout comme si elles etaient UTC.
faux = [type(b)(b.ts + timedelta(hours=10), b.ouverture, b.haut, b.bas, b.cloture)
        for b in aout]
try:
    verifier_decalage(faux, minimum=20)
    print("  ECHEC : l'assertion a laisse passer un decalage de 10 h")
    sys.exit(1)
except Exception as e:
    ok += 1
    print(f"  ok  l'assertion rejette un decalage de 10 h")
    print(f"      {type(e).__name__}: {str(e)[:90]}...")

print(f"\n{ok} verifications passees.\n")
