"""Moteur de recherche : execute des setups DECLARATIFS et les evalue.

Un setup est une specification de donnees, pas du code :

    {"nom": "...", "sens": "achat", "unite_signal": "M15",
     "conditions": [{"gauche": {"ind":"rsi","ut":"M15","params":[14]},
                     "op": "<", "droite": {"const": 30}}, ...],
     "declencheur_m5": "cloture_directionnelle",
     "stop": {"type":"atr","ut":"M15","mult":1.5}, "tp_r": 2.0}

Deux raisons a ce choix. D'abord, des agents peuvent proposer des setups sans
ecrire de code, donc sans introduire de biais de look-ahead. Ensuite, l'espace de
recherche devient DENOMBRABLE — indispensable pour corriger les comparaisons
multiples : sans savoir combien d'hypotheses ont ete testees, le meilleur
resultat d'une recherche n'a aucune interpretation statistique.

PERFORMANCE : chaque condition devient un tableau de booleens calcule une fois
pour toutes, puis les conditions se combinent par ET. Evaluer bougie par bougie
serait cent fois plus lent sur 300 000 barres.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from . import agregation, alignement, formes, indicateurs, indicateurs_etendus as ie
from .marche import resoudre

# Valeur neutre de chaque indicateur borne, pour le miroir achat <-> vente.
NEUTRE = {"rsi": 50.0, "stoch_k": 50.0, "stoch_d": 50.0, "cci": 0.0,
          "zscore": 0.0, "roc": 0.0, "position_range": 0.5, "asymetrie": 0.0,
          "macd_hist": 0.0, "macd": 0.0}

# Bandes qui se refletent l'une dans l'autre.
MIROIR_SERIE = {"bb_haut": "bb_bas", "bb_bas": "bb_haut",
                "donchian_haut": "donchian_bas", "donchian_bas": "donchian_haut",
                "keltner_haut": "keltner_bas", "keltner_bas": "keltner_haut",
                "plus_haut": "plus_bas", "plus_bas": "plus_haut"}

MIROIR_OP = {"<": ">", ">": "<", "<=": ">=", ">=": "<=",
             "croise_haut": "croise_bas", "croise_bas": "croise_haut"}


class SpecInvalide(ValueError):
    """La specification n'est pas executable telle quelle."""


class Bibliotheque:
    """Series d'indicateurs, calculees une fois et alignees sur l'index de base."""

    DUREES = {"M5": timedelta(minutes=5), "M15": timedelta(minutes=15),
              "H4": timedelta(hours=4), "D1": timedelta(days=1)}

    def __init__(self, base, marche="forex"):
        self.base = base
        self.marche = resoudre(marche)
        self._bougies = {"M5": base,
                         "M15": agregation.en_m15(base),
                         "H4": agregation.en_h4(base, marche),
                         "D1": agregation.en_journalier(base, marche)}
        self._cache = {}
        self._idx = {}

    def bougies(self, ut):
        if ut not in self._bougies:
            raise SpecInvalide(f"unite inconnue : {ut!r}")
        return self._bougies[ut]

    def _aligner(self, ut, serie):
        if ut == "M5":
            return serie
        return alignement.aligner(self.base, self._bougies[ut], serie, self.DUREES[ut])

    def serie(self, nom: str, ut: str = "M15", params=()):
        cle = (nom, ut, tuple(params))
        if cle in self._cache:
            return self._cache[cle]
        brute = self._calculer(nom, ut, list(params))
        self._cache[cle] = self._aligner(ut, brute)
        return self._cache[cle]

    def _calculer(self, nom, ut, p):
        b = self.bougies(ut)
        clot = [x.cloture for x in b]
        if nom == "ema":       return indicateurs.ema(clot, p[0] if p else 50)
        if nom == "sma":       return ie.sma(clot, p[0] if p else 50)
        if nom == "atr":       return indicateurs.atr(b, p[0] if p else 14)
        if nom == "rsi":       return ie.rsi(b, p[0] if p else 14)
        if nom == "cci":       return ie.cci(b, p[0] if p else 20)
        if nom == "roc":       return ie.roc(b, p[0] if p else 10)
        if nom == "zscore":    return ie.zscore(b, p[0] if p else 20)
        if nom == "ecart_type": return ie.ecart_type(clot, p[0] if p else 20)
        if nom == "atr_relatif":     return ie.atr_relatif(b, *(p or [14, 100]))
        if nom == "taille_relative": return ie.taille_relative(b, p[0] if p else 14)
        if nom == "asymetrie":       return ie.asymetrie_meches(b)
        if nom == "position_range":  return ie.position_dans_range(b, p[0] if p else 20)
        if nom == "adx":       return indicateurs.adx(b, p[0] if p else 14)[0]
        if nom in ("macd", "macd_signal", "macd_hist"):
            l, s, h = indicateurs.macd(b, *(p or [12, 26, 9]))
            return {"macd": l, "macd_signal": s, "macd_hist": h}[nom]
        if nom in ("bb_haut", "bb_bas", "bb_largeur"):
            h, bs, lg = ie.bollinger(b, *(p or [20, 2.0]))
            return {"bb_haut": h, "bb_bas": bs, "bb_largeur": lg}[nom]
        if nom in ("stoch_k", "stoch_d"):
            k, d = ie.stochastique(b, *(p or [14, 3]))
            return k if nom == "stoch_k" else d
        if nom in ("donchian_haut", "donchian_bas"):
            h, bs = ie.donchian(b, p[0] if p else 20)
            return h if nom == "donchian_haut" else bs
        if nom in ("keltner_haut", "keltner_bas"):
            h, bs = ie.keltner(b, *(p or [20, 1.5]))
            return h if nom == "keltner_haut" else bs
        if nom in ("plus_haut", "plus_bas"):
            n = p[0] if p else 20
            h, bs = ie.donchian(b, n)
            return h if nom == "plus_haut" else bs
        if nom in ("range_horaire_haut", "range_horaire_bas"):
            h, bs = ie.range_horaire(b, *(p or [0.0, 7.0]))
            return h if nom == "range_horaire_haut" else bs
        if nom in ("double_creux", "double_sommet"):
            return formes.double_extreme(
                b, "creux" if nom.endswith("creux") else "sommet", *(p or []))
        if nom in ("drapeau_haussier", "drapeau_baissier"):
            return formes.drapeau(
                b, "haussier" if nom.endswith("haussier") else "baissier", *(p or []))
        if nom == "triangle":
            return formes.triangle(b, *(p or []))
        if nom in ("tete_epaules", "tete_epaules_inverse"):
            return formes.tete_epaules(
                b, "sommet" if nom == "tete_epaules" else "creux", *(p or []))
        if nom == "heure_utc":
            return [x.ts.hour + x.ts.minute / 60 for x in b]
        raise SpecInvalide(f"indicateur inconnu : {nom!r}")


def _terme(t, biblio):
    """Resout un terme en serie alignee sur l'index de base."""
    n = len(biblio.base)
    if "const" in t:
        return [float(t["const"])] * n
    if "prix" in t:
        champ = {"cloture": "cloture", "haut": "haut", "bas": "bas",
                 "ouverture": "ouverture"}[t["prix"]]
        ut = t.get("ut", "M5")
        b = biblio.bougies(ut)
        return biblio._aligner(ut, [getattr(x, champ) for x in b])
    if "ind" not in t:
        raise SpecInvalide(f"terme sans 'ind', 'prix' ni 'const' : {t!r}")
    s = biblio.serie(t["ind"], t.get("ut", "M15"), t.get("params", []))
    mult, decal = t.get("mult"), t.get("decalage")
    if mult is not None:
        s = [None if v is None else v * mult for v in s]
    if decal:
        s = [None] * decal + s[:-decal]
    return s


def evaluer_condition(cond, biblio):
    """Renvoie un tableau de booleens de la longueur de l'index de base."""
    g, d = _terme(cond["gauche"], biblio), _terme(cond["droite"], biblio)
    op = cond["op"]
    n = len(biblio.base)
    out = [False] * n
    if op in ("croise_haut", "croise_bas"):
        for i in range(1, n):
            a, b, pa, pb = g[i], d[i], g[i - 1], d[i - 1]
            if None in (a, b, pa, pb):
                continue
            out[i] = (pa <= pb and a > b) if op == "croise_haut" else (pa >= pb and a < b)
        return out
    test = {"<": lambda a, b: a < b, ">": lambda a, b: a > b,
            "<=": lambda a, b: a <= b, ">=": lambda a, b: a >= b}.get(op)
    if test is None:
        raise SpecInvalide(f"operateur inconnu : {op!r}")
    for i in range(n):
        if g[i] is not None and d[i] is not None:
            out[i] = test(g[i], d[i])
    return out


def miroir(cond):
    """Version « vente » d'une condition ecrite pour l'achat.

    Un setup n'est pas symetrique par simple inversion d'operateur : « RSI < 30 »
    a pour miroir « RSI > 70 », pas « RSI > 30 ». On reflete donc les constantes
    autour de la valeur neutre de l'indicateur, et on echange les bandes haute et
    basse. Ce qui ne peut pas etre reflete de facon sure leve une exception
    plutot que de produire un miroir faux et silencieux.
    """
    g, d, op = dict(cond["gauche"]), dict(cond["droite"]), cond["op"]

    for terme in (g, d):
        if terme.get("ind") in MIROIR_SERIE:
            terme["ind"] = MIROIR_SERIE[terme["ind"]]

    autre = d if "const" in d else (g if "const" in g else None)
    if autre is not None:
        ref = g if autre is d else d
        nom = ref.get("ind")
        if nom in NEUTRE:
            autre["const"] = 2 * NEUTRE[nom] - float(autre["const"])
        elif nom is not None and ref.get("ind") not in MIROIR_SERIE:
            raise SpecInvalide(
                f"miroir impossible : pas de valeur neutre connue pour {nom!r}")
    return {"gauche": g, "op": MIROIR_OP[op], "droite": d}


# --------------------------------------------------------------------------
# Simulation
# --------------------------------------------------------------------------

SPREAD_BP = 1.0          # cout aller simple, en points de base du prix
DUREE_MAX = timedelta(hours=12)
"""Duree de detention maximale.

Le cahier des charges demande de l'intraday. Plutot qu'une heure de cloture
propre au forex, on borne la duree : la regle vaut alors telle quelle sur un
marche continu, et les resultats des deux instruments restent comparables.
"""


@dataclass
class Resultat:
    nom: str = ""
    r: list = field(default_factory=list)
    dates: list = field(default_factory=list)
    signaux: int = 0            # declenchements avant plafond journalier
    jours: int = 0

    @property
    def n(self):
        return len(self.r)

    def stats(self):
        if self.n < 3:
            return None
        m = sum(self.r) / self.n
        var = sum((x - m) ** 2 for x in self.r) / (self.n - 1)
        sd = var ** 0.5
        se = sd / self.n ** 0.5
        gagnants = sum(1 for x in self.r if x > 0)
        return {"n": self.n, "r_moyen": m, "ecart_type": sd, "err_type": se,
                "t": (m / se if se else 0.0),
                "reussite": 100 * gagnants / self.n,
                "r_total": sum(self.r),
                "trades_par_jour": self.n / self.jours if self.jours else 0.0}


def _stop_initial(spec, i, base, biblio, sens):
    s = 1 if sens == "achat" else -1
    b = base[i]
    st = spec.get("stop", {"type": "atr", "ut": "M15", "mult": 1.5})
    if st.get("type") == "extreme_recent":
        n = int(st.get("n", 10))
        fen = base[max(0, i - n + 1): i + 1]
        return min(x.bas for x in fen) if sens == "achat" else max(x.haut for x in fen)
    serie = biblio.serie("atr", st.get("ut", "M15"), [int(st.get("periode", 14))])
    a = serie[i]
    if not a:
        return None
    return b.cloture - s * float(st.get("mult", 1.5)) * a


def simuler(spec, base, candidats, biblio, sens="achat",
            max_trades_jour=2, spread_bp=SPREAD_BP, duree_max=DUREE_MAX) -> Resultat:
    """Simule un setup a partir de son tableau de bougies candidates.

    Conventions, identiques a celles du moteur principal et toutes defavorables :
      - le spread est preleve a l'entree ET a la sortie
      - quand une bougie contient a la fois le stop et l'objectif, l'ordre reel
        est indeterminable a partir d'un OHLC : on tranche TOUJOURS pour le stop
      - une seule position a la fois
    """
    s = 1 if sens == "achat" else -1
    tp_r = float(spec.get("tp_r", 2.0))
    res = Resultat(nom=spec.get("nom", "?"))

    fenetre = spec.get("fenetre_horaire")
    h_min = h_max = None
    if fenetre and len(fenetre) == 2:
        h_min, h_max = float(fenetre[0]), float(fenetre[1])

    jour_courant, pris_ce_jour = None, 0
    jours = set()
    i, n = 0, len(base)
    while i < n:
        b = base[i]
        jours.add(b.ts.date())
        if b.ts.date() != jour_courant:
            jour_courant, pris_ce_jour = b.ts.date(), 0
        if not candidats[i] or pris_ce_jour >= max_trades_jour:
            i += 1
            continue
        if h_min is not None:
            h = b.ts.hour + b.ts.minute / 60
            if not (h_min <= h < h_max):
                i += 1
                continue
        res.signaux += 1

        # ENTREE EN REPLI. La mesure des excursions montre que les setups a
        # indicateurs lisent la direction MIEUX que le hasard sur douze heures
        # (ratio favorable/adverse 1,27-1,29 contre 1,17), mais que le
        # contre-mouvement arrive AVANT le mouvement favorable et prend le stop.
        # Entrer apres avoir laisse ce contre-mouvement se produire teste
        # directement ce diagnostic.
        repli = float(spec.get("repli_atr", 0) or 0)
        i_entree = i
        if repli > 0:
            serie_atr = biblio.serie("atr", "M15", [14])
            a = serie_atr[i]
            if not a:
                i += 1
                continue
            cible = base[i].cloture - s * repli * a
            i_entree = None
            for k in range(i + 1, min(i + 1 + int(spec.get("repli_bougies", 36)), n)):
                x = base[k]
                atteint = (x.bas <= cible) if s > 0 else (x.haut >= cible)
                if atteint:
                    i_entree = k
                    break
            if i_entree is None:
                i += 1
                continue

        stop = _stop_initial(spec, i_entree, base, biblio, sens)
        if stop is None:
            i += 1
            continue
        be = base[i_entree]
        cout = be.cloture * spread_bp / 10000
        entree = be.cloture + s * cout
        risque = abs(entree - stop)
        if risque <= 0:
            i += 1
            continue
        objectif = entree + s * tp_r * risque
        limite = be.ts + duree_max

        j, sortie = i_entree + 1, None
        while j < n:
            x = base[j]
            touche_stop = (x.bas <= stop) if s > 0 else (x.haut >= stop)
            touche_tp = (x.haut >= objectif) if s > 0 else (x.bas <= objectif)
            if touche_stop:                      # le stop l'emporte en cas d'ambiguite
                sortie = stop
                break
            if touche_tp:
                sortie = objectif
                break
            if x.ts >= limite:
                sortie = x.cloture
                break
            j += 1
        if sortie is None:
            break
        sortie -= s * cout
        res.r.append(s * (sortie - entree) / risque)
        res.dates.append(b.ts)
        pris_ce_jour += 1
        i = j + 1

    res.jours = len(jours)
    return res


def executer_spec(spec, base, biblio, max_trades_jour=2) -> dict:
    """Evalue une spec dans les deux sens si demande. Renvoie {sens: Resultat}."""
    conditions = spec.get("conditions") or []
    if not conditions:
        raise SpecInvalide("aucune condition")
    if len(conditions) > 3:
        raise SpecInvalide(f"{len(conditions)} conditions : le cahier des charges "
                           f"en autorise trois au maximum")

    sens_demande = spec.get("sens", "achat")
    sorties = {}
    for sens in (("achat", "vente") if sens_demande == "les_deux" else (sens_demande,)):
        if sens == "vente" and sens_demande == "les_deux":
            try:
                conds = [miroir(c) for c in conditions]
            except SpecInvalide:
                continue          # miroir impossible : on ne trade que le sens ecrit
        else:
            conds = conditions
        tableaux = [evaluer_condition(c, biblio) for c in conds]
        combine = [all(t[i] for t in tableaux) for i in range(len(base))]
        sorties[sens] = simuler(spec, base, combine, biblio, sens, max_trades_jour)
    return sorties
