"""Normalise et valide des specifications de setups avant execution.

Les specifications viennent de sources diverses et n'emploient pas toutes le
meme vocabulaire : bollinger_haut pour bb_haut, macd_ligne pour macd,
position_dans_range pour position_range. Plutot que d'exiger une convention
parfaite en amont, on traduit ici — et surtout, on REJETTE BRUYAMMENT ce qui
n'est pas executable, au lieu de l'ignorer en silence.

Une specification muette qui ne se declenche jamais serait indiscernable d'une
specification sans signal. C'est le piege rencontre plus tot dans ce projet avec
S2 et S3, et il ne doit pas se reproduire par une simple faute de nom.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harnais import cache, nettoyage, recherche

ALIAS = {
    "bollinger_haut": "bb_haut", "bollinger_bas": "bb_bas",
    "bollinger_largeur": "bb_largeur", "bb_width": "bb_largeur",
    "macd_ligne": "macd", "macd_line": "macd", "ligne_macd": "macd",
    "signal_macd": "macd_signal", "histogramme_macd": "macd_hist",
    "position_dans_range": "position_range", "position_range_n": "position_range",
    "stochastique_k": "stoch_k", "stochastique_d": "stoch_d",
    "stoch_rapide": "stoch_k", "stoch_lent": "stoch_d",
    "keltner_superieur": "keltner_haut", "keltner_inferieur": "keltner_bas",
    "donchian_superieur": "donchian_haut", "donchian_inferieur": "donchian_bas",
    "plus_haut_n": "plus_haut", "plus_bas_n": "plus_bas",
    "atr_ratio": "atr_relatif", "ratio_atr": "atr_relatif",
    "taille_bougie": "taille_relative", "asymetrie_meches": "asymetrie",
    "heure": "heure_utc", "ecart_type_prix": "ecart_type",
    "moyenne_mobile": "sma", "ema_rapide": "ema", "ema_lente": "ema",
}
ALIAS_OP = {"<": "<", ">": ">", "<=": "<=", ">=": ">=",
            "inferieur": "<", "superieur": ">",
            "croise_au_dessus": "croise_haut", "croise_en_dessous": "croise_bas",
            "cross_up": "croise_haut", "cross_down": "croise_bas"}


def _normaliser_terme(t):
    if not isinstance(t, dict):
        raise recherche.SpecInvalide(f"terme non structure : {t!r}")
    t = dict(t)
    if "ind" in t:
        t["ind"] = ALIAS.get(t["ind"], t["ind"])
    if "ut" in t and t["ut"] in ("M1", "M30", "H1", "D"):
        # Unites non derivees du cache : on remonte a la plus proche disponible.
        t["ut"] = {"M1": "M5", "M30": "M15", "H1": "H4", "D": "D1"}[t["ut"]]
    if "params" in t and t["params"] is None:
        t.pop("params")
    return t


def normaliser(spec):
    s = dict(spec)
    conds = []
    for c in s.get("conditions", []):
        conds.append({"gauche": _normaliser_terme(c["gauche"]),
                      "op": ALIAS_OP.get(c.get("op"), c.get("op")),
                      "droite": _normaliser_terme(c["droite"])})
    s["conditions"] = conds
    s.setdefault("tp_r", 2.0)
    s.setdefault("stop", {"type": "atr", "ut": "M15", "mult": 1.5})
    return s


def valider(specs, echantillon=None):
    """Renvoie (acceptees, rejets). Chaque rejet porte sa raison."""
    if echantillon is None:
        b = cache.charger("donnees/cache/XAUUSD-M5.csv")
        b = [x for x in b if str(x.ts.date()) <= "2023-12-31"]
        echantillon, _ = nettoyage.filtrer(b)
    biblio = recherche.Bibliotheque(echantillon)

    acceptees, rejets = [], []
    vus = set()
    for brut in specs:
        try:
            s = normaliser(brut)
        except Exception as e:
            rejets.append((brut.get("nom", "?"), f"normalisation : {e}"))
            continue
        if s.get("nom") in vus:
            rejets.append((s.get("nom"), "nom en double"))
            continue
        try:
            sorties = recherche.executer_spec(s, echantillon, biblio, 2)
        except recherche.SpecInvalide as e:
            rejets.append((s.get("nom", "?"), str(e)))
            continue
        except Exception as e:
            rejets.append((s.get("nom", "?"), f"{type(e).__name__}: {e}"))
            continue
        total = sum(r.n for r in sorties.values())
        if total == 0:
            rejets.append((s.get("nom", "?"),
                           "aucun declenchement sur l'echantillon de controle"))
            continue
        vus.add(s.get("nom"))
        acceptees.append(s)
    return acceptees, rejets


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: ingerer.py <entree.json> <sortie.json>")
        return 2
    brut = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if isinstance(brut, dict):
        brut = brut.get("setups", [])
    acceptees, rejets = valider(brut)
    print(f"{len(brut)} specifications lues")
    print(f"   {len(acceptees)} executables")
    print(f"   {len(rejets)} rejetees :")
    for nom, raison in rejets:
        print(f"      {str(nom)[:40]:<42}{raison[:70]}")
    Path(sys.argv[2]).write_text(json.dumps(acceptees, indent=1, ensure_ascii=False),
                                 encoding="utf-8")
    print(f"\n   ecrit dans {sys.argv[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
