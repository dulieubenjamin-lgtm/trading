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

---

# RÉSULTAT — 20/08/2026

## Verdict selon la règle pré-enregistrée : **hypothèse NON confirmée**

EUR/USD ne valide pas. La règle exigeait ≥ 2 instruments sur 3 ; le seul qui
montre quelque chose reste l'or, celui qui a produit l'hypothèse.

## Le chemin, parce qu'il compte autant que le résultat

**Trois témoins successifs, trois confonds, chacun démasqué par un test de
cohérence — pas par l'intuition.**

**Témoin 1 — moments quelconques.** Sur EUR/USD il validait les CINQ figures,
dont le double sommet, connu pour être négatif sur XAU *et* BTC. Un critère qui
valide ce qu'on sait faux est cassé. Diagnostic : le témoin entre aussi dans les
heures mortes, la figure jamais. Le z mesurait « entrer quand ça bouge ».

**Témoin 2 — apparié en volatilité.** Pire. L'ATR est rétrospectif : apparier
dessus tire des moments *après* un mouvement, où il reste peu à parcourir. Les
témoins ont empiré, tous les z ont monté. Nouveau biais, pas correction.

**Témoin 3 — mêmes bougies, sens opposé, dérive soustraite.** Le sens opposé
ressortait à −0,42 / −0,98, bien pire que le hasard. Diagnostic : le stop.
`extreme_recent` place le stop loin à l'achat et collé au prix à la vente quand
le prix vient de casser vers le haut. Je comparais un bon stop à un stop absurde.

**Témoin 4 — même chose, stop symétrique.** Long et court au même instant
portent le même risque. C'est le seul qui isole la prédiction.

## Ce qu'il reste après nettoyage

| | XAU | EUR/USD | BTC |
|---|---|---|---|
| tête-épaules inversée | **+0,348** (z +2,65) | −0,081 | −0,068 |
| + filtre H4 | +0,437 (z +2,45) | +0,022 | −0,049 |
| double creux | +0,073 | −0,130 | +0,031 |
| double sommet | −0,023 | −0,106 | +0,060 |

Seuil de Bonferroni sur les ~125 tests de la session : **|z| ≥ 3,53**. Aucun ne
le franchit. La tête-épaules inversée sur l'or reste **suggestive et non
démontrée**.

## Le chiffre que le nettoyage a coûté

Sur XAU, la tête-épaules inversée filtrée donnait **+0,356 R** avec le stop
structurel, et **+0,217 R** avec le stop symétrique. **Environ 0,14 R par trade
venait donc du placement du stop, pas de la prédiction.**

Ce n'est pas rien, et ce n'est pas non plus établi : un stop structurel est
peut-être simplement plus large, donc moins pénalisé par le spread (§AA). Placer
le stop derrière la structure plutôt qu'à distance fixe mérite un test dédié —
séparé, avec la largeur contrôlée.

## Ce que ce test a réellement établi

**EUR/USD n'est pas tradable en intraday sous ce modèle de coût**, indépendamment
de toute figure. ATR M15 de 5,9 points de base contre ~30 pour l'or : à 1,5 × ATR
le spread mange **23 %** du risque, et le témoin aléatoire y perd −0,46 R. Il
faudrait produire +0,46 R avant de gagner le premier centime.

C'est une propriété de l'instrument, pas un jugement sur la méthode — et c'est
la découverte la plus actionnable de ce test.

---

# Test de suivi — le placement du stop (20/08)

## Ce qui était annoncé

Le nettoyage avait révélé que la tête-épaules inversée passait de +0,356 R (stop
structurel) à +0,217 R (stop symétrique). J'en avais tiré une piste : **placer le
stop derrière la structure vaudrait ~0,14 R par trade**, applicable à n'importe
quel setup.

## Le test

Comparer un stop structurel à un stop ATR confond deux effets — la largeur (un
stop large paie moins de spread) et l'adaptativité (le stop est-il large
*précisément quand il faut* ?).

Pour isoler l'adaptativité seule : relever les distances réelles du stop
structurel trade par trade, puis les **réassigner au hasard entre les trades**.
Distribution de largeurs identique, mêmes bougies, même tout — seul l'appariement
change.

## Résultat

| setup | XAU | EUR/USD | BTC |
|---|---|---|---|
| **tête-épaules inversée** | **+0,144 (z +3,10)** | +0,019 | +0,001 |
| double creux | −0,007 | +0,009 | −0,048 |
| double sommet | +0,044 | +0,003 | −0,005 |
| drapeau haussier | −0,023 | −0,009 | +0,007 |

**Une cellule sur douze.** La même que d'habitude.

## Ce que ça change

La piste annoncée n'existe pas. **Les 0,14 R ne sont pas une propriété
transférable du placement structurel** — sinon ils apparaîtraient sur les autres
figures et les autres instruments. Ils n'apparaissent nulle part ailleurs.

C'est **la même anomalie**, vue sous un autre angle. Direction, placement du
stop : ces mesures portent toutes sur les mêmes 274 trades. Elles ne se
confirment pas l'une l'autre — elles se répètent.

C'est précisément le piège qui fait croire à un système : multiplier les angles
sur un même échantillon et prendre la cohérence des résultats pour de
l'accumulation de preuve.

## Où cela laisse la session

Un seul objet a résisté à tout : la tête-épaules inversée sur XAU, z entre 2,6 et
3,1 selon l'angle, sur 274 trades. Elle ne franchit aucun seuil corrigé, ne
transfère à aucun autre instrument, et toutes ses mesures sont redondantes entre
elles.

**Aucun redécoupage de ces 274 trades ne tranchera.** Seules des données neuves le
peuvent : du papier live sur XAU, à spécification gelée, jusqu'à 200 trades
inédits. Environ deux ans au rythme observé — ou une donnée que ce projet n'a
jamais eue, le carnet d'ordres.
