"""Boucle walk-forward : execution du rulebook, bougie par bougie.

DEUX CHOIX DE METHODE, tous deux defavorables au systeme
========================================================

1. AMBIGUITE INTRA-BOUGIE. Quand une bougie M15 contient a la fois le stop et
   l'objectif, l'ordre reel des touches est indeterminable a partir d'un OHLC.
   On tranche TOUJOURS pour le stop. Un backtest qui suppose l'inverse produit
   des courbes flatteuses et fausses ; celui-ci sous-estime plutot que de mentir.

2. COUT DE TRANSACTION. Le spread est preleve a l'entree ET a la sortie. Sur un
   stop de ~16 $, un aller-retour a 0,30 $ pese ~4 % du risque : negligeable a
   l'echelle d'un trade, pas a celle de 200.

Une seule position ouverte a la fois : un trader discretionnaire sur un seul
instrument ne suit pas trois trades en parallele, et l'autoriser dans le
backtest gonflerait le nombre d'occasions au-dela du realisable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from . import seances
from .setups import SETUPS
from .vue import VueMarche

SPREAD = 0.30              # $ par once, aller simple. Ordre de grandeur retail sur XAU.
RISQUE_PCT = 1.0
CAPITAL_INITIAL = 10_000.0
MAX_TRADES_JOUR = 3
STOP_JOURNALIER_PCT = -2.0


@dataclass
class Trade:
    """Le plan est IMMUABLE. Il n'est jamais modifie apres l'entree.

    Le stop evolue (passage a break-even apres TP1), mais il vit dans
    `stop_courant`, pas dans le plan. Une premiere version remplacait le plan par
    une copie au stop mis a jour : le journal aurait alors compare chaque
    post-mortem a un plan qui n'a jamais ete ecrit, ce qui vide de sa substance
    tout le verrou anti-biais du projet.
    """
    plan: object
    taille: float
    entree_reelle: float
    stop_courant: float = 0.0
    capital_entree: float = CAPITAL_INITIAL
    sortie: float | None = None
    ts_sortie: datetime | None = None
    motif_sortie: str = ""
    r_realise: float = 0.0
    tp1_pris: bool = False
    gain: float = 0.0


@dataclass
class Resultat:
    trades: list = field(default_factory=list)
    capital: float = CAPITAL_INITIAL
    refus: dict = field(default_factory=dict)
    barres_parcourues: int = 0

    def par_setup(self) -> dict:
        stats: dict[str, dict] = {}
        for t in self.trades:
            s = stats.setdefault(t.plan.setup, {"n": 0, "gagnants": 0, "r": 0.0})
            s["n"] += 1
            s["r"] += t.r_realise
            if t.r_realise > 0:
                s["gagnants"] += 1
        for s in stats.values():
            s["r_moyen"] = round(s["r"] / s["n"], 3) if s["n"] else 0.0
            s["taux_reussite"] = round(100 * s["gagnants"] / s["n"], 1) if s["n"] else 0.0
            s["r"] = round(s["r"], 2)
        return stats


def _signe(sens: str) -> int:
    return 1 if sens == "achat" else -1


def executer(bougies, series, regime="paris", setups=("S1", "S2", "S3")) -> Resultat:
    reg = seances.REGIMES[regime]
    res = Resultat()
    position: Trade | None = None
    jour_courant, trades_du_jour, capital_debut_jour = None, 0, CAPITAL_INITIAL

    for i, b in enumerate(bougies):
        res.barres_parcourues += 1
        jour = seances.date_locale(b.ts, regime)
        if jour != jour_courant:
            jour_courant, trades_du_jour = jour, 0
            capital_debut_jour = res.capital

        # ---- gestion d'une position ouverte -------------------------------
        if position is not None:
            s = _signe(position.plan.sens)
            touche_stop = (b.bas <= position.stop_courant) if s > 0 \
                else (b.haut >= position.stop_courant)
            touche_tp1 = (b.haut >= position.plan.tp1) if s > 0 else (b.bas <= position.plan.tp1)
            touche_tp2 = (b.haut >= position.plan.tp2) if s > 0 else (b.bas <= position.plan.tp2)

            # CHOIX 1 : le stop l'emporte toujours en cas d'ambiguite.
            if touche_stop:
                motif = "break-even" if position.tp1_pris else "stop"
                _fermer(res, position, position.stop_courant, b.ts, motif)
                position = None
            elif touche_tp2:
                _fermer(res, position, position.plan.tp2, b.ts, "tp2")
                position = None
            elif touche_tp1 and not position.tp1_pris:
                # Moitie sortie a 1R, stop ramene a l'entree.
                gain = s * (position.plan.tp1 - position.entree_reelle) * position.taille / 2
                res.capital += gain
                position.gain += gain
                position.tp1_pris = True
                position.taille /= 2
                position.stop_courant = position.entree_reelle
            elif seances.apres(b.ts, reg["flat"], regime):
                _fermer(res, position, b.cloture, b.ts, "flat 22h")
                position = None
            if position is not None:
                continue

        # ---- conditions d'ouverture ---------------------------------------
        if trades_du_jour >= MAX_TRADES_JOUR:
            res.refus["max_trades_jour"] = res.refus.get("max_trades_jour", 0) + 1
            continue
        perte_jour = 100 * (res.capital - capital_debut_jour) / capital_debut_jour
        if perte_jour <= STOP_JOURNALIER_PCT:
            res.refus["stop_journalier"] = res.refus.get("stop_journalier", 0) + 1
            continue
        if seances.apres(b.ts, reg["derniere_entree"], regime):
            continue

        vue = VueMarche(bougies, i, series)
        for nom in setups:
            plan = SETUPS[nom](vue, regime)
            if plan is None:
                continue
            risque_euros = res.capital * RISQUE_PCT / 100
            if plan.risque_unitaire <= 0:
                continue
            taille = risque_euros / plan.risque_unitaire
            s = _signe(plan.sens)
            entree_reelle = plan.entree + s * SPREAD / 2   # CHOIX 2 : cout a l'entree
            position = Trade(plan=plan, taille=taille, entree_reelle=entree_reelle,
                             stop_courant=plan.stop, capital_entree=res.capital)
            res.trades.append(position)
            trades_du_jour += 1
            break

    if position is not None:
        _fermer(res, position, bougies[-1].cloture, bougies[-1].ts, "fin des donnees")
    return res


def _fermer(res, trade, prix, ts, motif):
    s = _signe(trade.plan.sens)
    sortie = prix - s * SPREAD / 2                       # CHOIX 2 : cout a la sortie
    gain = s * (sortie - trade.entree_reelle) * trade.taille
    res.capital += gain
    trade.gain += gain
    trade.sortie, trade.ts_sortie, trade.motif_sortie = sortie, ts, motif
    # Le R se mesure contre le risque REELLEMENT engage sur ce trade — soit 1 %
    # du capital AU MOMENT DE L'ENTREE. L'ancrer sur le capital initial ferait
    # deriver l'echelle des R des que le compte s'ecarte de 10 000 $, et les
    # statistiques par setup deviendraient incomparables entre debut et fin de
    # periode.
    risque_euros = trade.capital_entree * RISQUE_PCT / 100
    trade.r_realise = round(trade.gain / risque_euros, 3)
