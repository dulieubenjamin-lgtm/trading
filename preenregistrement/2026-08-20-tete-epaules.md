# Pré-enregistrement — la tête-épaules inversée tient-elle hors de l'or ?

**Écrit AVANT d'avoir vu la moindre donnée EUR/USD, XAG/USD ou indice.**
Daté du 20/08/2026. Toute lecture du résultat qui s'écarte des règles ci-dessous
est une réinterprétation après coup, pas une conclusion.

## Ce qu'on a observé

Sur XAU/USD, trois fenêtres indépendantes (recherche, validation, holdout) :

| | n | réussite | R moyen | t |
|---|---|---|---|---|
| tête-épaules inversée + filtre H4 | 191 | 53,9 % | +0,384 | **+4,00** |
| tête-épaules inversée | 277 | 50,2 % | +0,275 | +3,44 |

Concentration à 24 % — le résultat n'est pas porté par quelques trades.
Seuil de Bonferroni sur ~121 tests de la session : |t| ≥ 3,53. Franchi.

**Sur BTC/USD la même figure donne −0,077 R sur 448 trades.** Négative.

## L'hypothèse testée

> Les figures chartistes fonctionnent sur les marchés à forte présence
> technique, où beaucoup d'acteurs tradent la même figure au même endroit et la
> rendent partiellement auto-réalisatrice. Elles échouent là où la base de
> participants est différente.

Cette hypothèse **prédit** :
- EUR/USD → positif (le marché le plus charté du monde)
- XAG/USD → positif (mêmes acteurs que l'or, mêmes outils)
- Indice → positif (fortement technique)
- BTC/USD → négatif — **déjà observé, ce qui a inspiré l'hypothèse et ne
  compte donc PAS comme confirmation**

L'hypothèse concurrente est simplement : *l'or a eu de la chance sur 191 trades
parmi 121 tests.* Elle prédit des résultats nuls ou négatifs partout ailleurs.

## Ce qui est gelé

La spécification exacte, **sans aucun réglage** :

```
figure    tete_epaules_inverse, largeur 3, tolerance 0,9, ecart_max 80,
          saillie_min 0,5   — paramètres identiques à ceux d'XAU
filtre    cloture > EMA50 H4
entree    croisement du signal, cloture M5
stop      extreme_recent n=12
objectif  2R
plafond   2 trades/jour
```

**Aucun paramètre ne sera ajusté par instrument.** Un réglage par marché
transformerait ce test de confirmation en nouvelle recherche.

## Règle de décision, fixée maintenant

Le témoin reste apparié par sens, par type de stop et par fenêtre.

| résultat | verdict |
|---|---|
| R moyen > 0 **et** t > 2 sur **≥ 2** des 3 instruments (n ≥ 100 chacun) | **hypothèse confirmée** |
| R moyen ≤ 0 sur **≥ 2** des 3 | **hypothèse réfutée** — l'or était de la chance |
| tout autre cas | **non concluant** — ne pas trancher, ne pas rejouer |

Si n < 100 sur un instrument, il ne compte ni pour ni contre : l'échantillon
est trop mince, et l'exclure après coup serait de la sélection.

## Nuance déclarée d'avance

XAG/USD est le test le **plus faible** : même classe d'actif que l'or, mêmes
acteurs, corrélation élevée. Un succès sur l'argent seul ne prouverait presque
rien. **EUR/USD et l'indice sont les tests qui comptent** — classes d'actifs
distinctes, participants distincts.

Si seul XAG passe, le verdict est « non concluant », pas « confirmé ».
