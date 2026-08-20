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

---

## Amendement, écrit avant réception de toute donnée EUR/USD

**Motif : une erreur de modélisation possible, sans rapport avec le résultat.**

La friction dépend de la volatilité *relative* de l'instrument. Le spread est
modélisé à 1 point de base du prix ; ce qu'il coûte en fraction du risque dépend
donc de la largeur de l'ATR rapportée au prix.

- Or : ATR M15 ≈ 13 $ sur 4 400 $, soit ~30 points de base. Stop à 1,5 × ATR
  → le spread pèse **~11 %** du risque.
- EUR/USD : la volatilité relative est bien plus faible. Le même spread pourrait
  peser **trois fois plus** du risque.

Si c'est le cas, **aucun** setup ne peut atteindre un R moyen positif sur
EUR/USD, quelle que soit sa qualité — la friction mangerait tout. La règle
« R moyen > 0 » deviendrait alors un test de la structure de coût de
l'instrument, pas de la figure.

### Ce qui est ajouté, et pourquoi maintenant

À la réception des données, **avant** d'examiner le moindre résultat de la
figure, je mesurerai le ratio spread/risque de l'instrument et le R moyen du
témoin aléatoire. Deux cas, tranchés d'avance :

1. **Témoin achat > −0,25 R** → la profitabilité absolue reste atteignable.
   La règle de décision d'origine s'applique **inchangée**.
2. **Témoin achat ≤ −0,25 R** → la friction domine. Le critère devient
   `z > 2,5` contre le témoin apparié, et le rapport mentionnera explicitement
   que la profitabilité absolue est hors de portée avec ce modèle de coût.

Ce seuil de −0,25 R est fixé maintenant, sans connaître la valeur réelle.

### Ce que cet amendement ne fait pas

Il n'assouplit rien sur l'or : le résultat XAU a été obtenu et jugé avec la règle
d'origine. Il ne change pas non plus le nombre d'instruments requis, ni la
pondération déclarée (XAG reste le test faible). Il traite un seul point : ne pas
confondre « la figure ne marche pas » avec « le coût modélisé rend tout
instrument peu volatil intradable ».
