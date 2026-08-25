"""Telecharge des bougies M5 depuis Dukascopy, sans compte ni cle.

    python3 outils/dukascopy.py --symbole XAGUSD --mois 36
    python3 outils/dukascopy.py --symbole XAUUSD --mois 36   # temoin de fournisseur

POURQUOI UNE SECONDE SOURCE
===========================
Twelve Data ne sert pas XAG/USD spot hors plan payant, et ne sert aucun indice.
Dukascopy publie l'historique tick de plus de 800 instruments, XAG/USD compris,
depuis 1997, gratuitement. C'est du SPOT, donc un instrument forex-like : le
harnais le traite deja, aucune extension necessaire.

CE QUE CETTE SOURCE COUTE, ET COMMENT ON LE MESURE
--------------------------------------------------
Changer de fournisseur en cours de protocole introduit un confondant : bougies
construites autrement, horodatage conventionne autrement, spread different. Si
XAG venait de Dukascopy et XAU de Twelve Data, un ecart entre les deux pourrait
venir de l'argent OU du fournisseur, et rien ne les departagerait.

D'ou la regle : **tirer AUSSI XAU/USD chez Dukascopy et verifier qu'il reproduit
le resultat mesure sur les donnees Twelve Data.** Si oui, le fournisseur n'est
pas un confondant et la comparaison XAG tient. Si non, on a appris quelque chose
qui vaut d'etre ecrit — la sensibilite au fournisseur — et le test de transfert
attendra.

FORMAT DUKASCOPY
----------------
Un fichier par heure, compresse en LZMA brut :
    datafeed.dukascopy.com/datafeed/{SYM}/{AAAA}/{MM}/{JJ}/{HH}h_ticks.bi5
Le MOIS EST INDEXE A PARTIR DE ZERO — janvier s'ecrit 00. C'est le piege
classique de cette API, et il produit un decalage d'un mois parfaitement
silencieux : les donnees existent, elles sont juste celles du mois d'avant.

Chaque tick fait 20 octets gros-boutiens : millisecondes depuis le debut de
l'heure, ask, bid (entiers a mettre a l'echelle), puis les volumes en flottants.
"""
from __future__ import annotations

import argparse
import lzma
import struct
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BASE = "https://datafeed.dukascopy.com/datafeed"
EN_TETE = "datetime;open;high;low;close"
TICK = struct.Struct(">IIIff")

# Facteur d'echelle des prix entiers. Dukascopy encode en unites de la derniere
# decimale cotee : trois pour les metaux, cinq pour la plupart des paires.
ECHELLES = {"XAGUSD": 1e-3, "XAUUSD": 1e-3, "EURUSD": 1e-5, "GBPUSD": 1e-5,
            "USDJPY": 1e-3}


def decoder(brut: bytes, heure: datetime, echelle: float):
    """Un fichier .bi5 -> liste de (horodatage, prix milieu)."""
    if not brut:
        return []
    try:
        donnees = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(brut)
    except lzma.LZMAError:
        donnees = lzma.decompress(brut)          # certains fichiers sont en .xz
    ticks = []
    for i in range(0, len(donnees) - len(donnees) % TICK.size, TICK.size):
        ms, ask, bid, _, _ = TICK.unpack_from(donnees, i)
        # Le MILIEU, pas le bid : le harnais modelise le spread separement, en
        # points de base. Prendre le bid le compterait deux fois.
        ticks.append((heure + timedelta(milliseconds=ms),
                      (ask + bid) / 2 * echelle))
    return ticks


def agreger(ticks, minutes=5):
    """Ticks -> bougies OHLC. Une bougie sans tick n'existe pas : on ne la
    fabrique pas. Le harnais lit les trous comme des fermetures, ce qui est
    exact, et inventer une bougie plate serait de la donnee synthetique (§B)."""
    seaux = {}
    pas = minutes * 60
    for ts, prix in ticks:
        cle = int(ts.timestamp()) // pas * pas
        s = seaux.get(cle)
        if s is None:
            seaux[cle] = [prix, prix, prix, prix]
        else:
            s[1] = max(s[1], prix)
            s[2] = min(s[2], prix)
            s[3] = prix
    return [(datetime.fromtimestamp(k, timezone.utc), *v)
            for k, v in sorted(seaux.items())]


def tirer_heure(symbole, quand: datetime, essais=3):
    # Mois indexe a zero. Voir l'avertissement en tete de fichier.
    url = (f"{BASE}/{symbole}/{quand.year}/{quand.month - 1:02d}/"
           f"{quand.day:02d}/{quand.hour:02d}h_ticks.bi5")
    for tentative in range(essais):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return b""            # marche ferme : absence normale
            if tentative == essais - 1:
                raise
        except Exception:
            if tentative == essais - 1:
                raise
        time.sleep(2 ** tentative)
    return b""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbole", default="XAGUSD", help="XAGUSD, XAUUSD, ...")
    ap.add_argument("--mois", type=int, default=36)
    ap.add_argument("--sortie", default=None)
    ap.add_argument("--echelle", type=float, default=None,
                    help="forcer le facteur d'echelle si le symbole est inconnu")
    args = ap.parse_args()

    echelle = args.echelle or ECHELLES.get(args.symbole)
    if echelle is None:
        print(f"echelle inconnue pour {args.symbole} : la preciser avec --echelle")
        print(f"connus : {', '.join(sorted(ECHELLES))}")
        return 2

    cible = Path(args.sortie or f"donnees/cache/{args.symbole}-M5.csv")
    cible.parent.mkdir(parents=True, exist_ok=True)

    fin = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    debut = fin - timedelta(days=int(args.mois * 30.44))
    total_h = int((fin - debut).total_seconds() // 3600)
    print(f"{args.symbole} : {debut:%Y-%m-%d} -> {fin:%Y-%m-%d}  "
          f"({total_h} fichiers horaires, echelle {echelle})")
    print("Dukascopy sert un fichier par heure : compter une a deux heures.\n")

    # PARALLELE. Vingt-six mille requetes en serie prennent deux heures ; huit
    # de front les ramenent a une vingtaine de minutes. Huit et pas trente :
    # ce sont des fichiers statiques sur le serveur public d'une banque, et
    # rien ne justifie de le marteler.
    heures = [debut + timedelta(hours=k) for k in range(total_h)]
    fait = [0]

    def une(quand):
        try:
            brut = tirer_heure(args.symbole, quand)
        except Exception as e:
            return quand, None, e
        finally:
            fait[0] += 1
            if fait[0] % 2000 == 0:
                print(f"  {fait[0]}/{total_h} heures")
        return quand, brut, None

    with ThreadPoolExecutor(max_workers=8) as pool:
        resultats = list(pool.map(une, heures))

    # UN ECHEC ISOLE N'ARRETE PAS TOUT, mais un taux d'echec eleve si. Quelques
    # heures perdues sur vingt-six mille laissent un trou que verifier_cache.py
    # attrapera ; une panne systematique produirait un historique amputé qui,
    # lui, se lirait comme un marche calme.
    ticks, vides, echecs = [], 0, []
    for quand, brut, err in resultats:
        if err is not None:
            echecs.append((quand, err))
        elif brut:
            ticks += decoder(brut, quand, echelle)
        else:
            vides += 1
    ticks.sort()

    if echecs:
        taux = len(echecs) / total_h
        print(f"\n{len(echecs)} heures en echec sur {total_h} ({100 * taux:.2f} %)")
        print(f"   premiere : {echecs[0][0]:%Y-%m-%d %Hh} — {echecs[0][1]}")
        if taux > 0.02:
            print("   TAUX TROP ELEVE : rien n'est ecrit. Verifier le reseau,")
            print("   puis relancer.")
            return 4

    if not ticks:
        print("\nAUCUN TICK. Symbole inconnu de Dukascopy, ou echelle erronee.")
        return 5

    bougies = agreger(ticks)
    lignes = [f"{ts:%Y-%m-%d %H:%M:%S};{o:.5f};{h:.5f};{b:.5f};{c:.5f}"
              for ts, o, h, b, c in bougies]
    cible.write_text("\n".join(["# timezone: UTC", EN_TETE] + lignes) + "\n",
                     encoding="utf-8")
    print(f"\n{cible} : {len(bougies)} bougies M5 depuis {len(ticks)} ticks")
    print(f"couverture : {bougies[0][0]:%Y-%m-%d %H:%M} -> "
          f"{bougies[-1][0]:%Y-%m-%d %H:%M} UTC")
    print(f"\nVerifier AVANT de mesurer quoi que ce soit :")
    print(f"   python3 outils/verifier_cache.py {cible}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
