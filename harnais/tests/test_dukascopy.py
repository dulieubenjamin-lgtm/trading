"""Le decodage Dukascopy sur un fichier fabrique dont on connait la reponse.

Le telechargement lui-meme n'est pas testable ici : l'egress de cette session
refuse datafeed.dukascopy.com. Tout le reste l'est, et c'est la ou sont les
erreurs qui ne se voient pas -- un facteur d'echelle faux donne des prix
plausibles, un mois mal indexe donne des bougies parfaitement valides mais
decalees d'un mois.
"""
import lzma
import struct
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "outils"))

import importlib.util
_s = importlib.util.spec_from_file_location(
    "duka", Path(__file__).resolve().parents[2] / "outils" / "dukascopy.py")
duka = importlib.util.module_from_spec(_s); _s.loader.exec_module(duka)

UTC = timezone.utc
ok = 0


def verifie(intitule, obtenu, attendu):
    global ok
    if obtenu != attendu:
        print(f"  ECHEC {intitule}\n        obtenu {obtenu}\n        attendu {attendu}")
        sys.exit(1)
    ok += 1
    print(f"  ok  {intitule}  -> {obtenu}")


def fabriquer(ticks):
    """(ms, ask_entier, bid_entier) -> fichier .bi5 tel que Dukascopy le sert."""
    brut = b"".join(duka.TICK.pack(ms, a, b, 1.0, 1.0) for ms, a, b in ticks)
    c = lzma.LZMACompressor(format=lzma.FORMAT_ALONE)
    return c.compress(brut) + c.flush()


heure = datetime(2026, 6, 10, 10, 0, tzinfo=UTC)

print("1. Decodage : echelle, milieu bid-ask, horodatage")
# Argent vers 36,500 $ : Dukascopy encode au millieme, donc 36500 -> 36,500.
fichier = fabriquer([(0, 36510, 36490), (60_000, 36600, 36580),
                     (299_999, 36400, 36380), (300_000, 36700, 36680)])
ticks = duka.decoder(fichier, heure, 1e-3)
verifie("quatre ticks decodes", len(ticks), 4)
verifie("prix milieu du premier tick", round(ticks[0][1], 3), 36.5)
verifie("le premier tick est a l'heure pile", ticks[0][0], heure)
verifie("le deuxieme est une minute plus tard", ticks[1][0],
        heure + timedelta(minutes=1))

print("\n2. Agregation en bougies de cinq minutes")
bougies = duka.agreger(ticks)
verifie("deux bougies : trois ticks puis un", len(bougies), 2)
ts, o, h, b, c = bougies[0]
verifie("la bougie s'ouvre a l'heure pile", ts, heure)
verifie("ouverture = premier tick", round(o, 3), 36.5)
verifie("plus haut = tick le plus haut", round(h, 3), 36.59)
verifie("plus bas = tick le plus bas", round(b, 3), 36.39)
verifie("cloture = dernier tick de la bougie", round(c, 3), 36.39)
verifie("la seconde bougie demarre a 10h05", bougies[1][0],
        heure + timedelta(minutes=5))

print("\n3. Un fichier vide n'invente pas de bougie")
verifie("aucun tick", duka.decoder(b"", heure, 1e-3), [])
verifie("aucune bougie", duka.agreger([]), [])

print("\n4. Le mois est indexe a ZERO dans l'URL")
# Ce test ne verifie pas un calcul mais une convention : s'il casse, quelqu'un
# a « corrige » le -1 en le prenant pour un bug, et tout l'historique glisse
# d'un mois sans qu'aucune donnee paraisse anormale.
import unittest.mock as mock
vus = []
with mock.patch.object(duka.urllib.request, "urlopen",
                       side_effect=duka.urllib.error.HTTPError(
                           "u", 404, "nf", None, None)):
    with mock.patch.object(duka, "BASE", "X") as _:
        pass
def faux_urlopen(url, timeout=None):
    vus.append(url)
    raise duka.urllib.error.HTTPError(url, 404, "nf", None, None)
duka.urllib.request.urlopen = faux_urlopen
duka.tirer_heure("XAGUSD", datetime(2026, 1, 15, 9, tzinfo=UTC))
verifie("janvier s'ecrit 00", "/2026/00/15/09h_ticks.bi5" in vus[-1], True)
duka.tirer_heure("XAGUSD", datetime(2026, 12, 3, 0, tzinfo=UTC))
verifie("decembre s'ecrit 11", "/2026/11/03/00h_ticks.bi5" in vus[-1], True)

print(f"\n{ok} verifications passees.\n")
