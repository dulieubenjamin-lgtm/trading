# Gabarit du brief du matin (8 h, heure de Paris)

Objectif : trois actifs, les zones proches, un plan par actif, et surtout le
**pourquoi** de chaque décision, pour apprendre en même temps qu'on trade.
Rien n'est exécuté : analyse, dessins sur le graphique, alertes.

## Principe : ne lire que ce qui sert à décider

Chaque donnée lue répond à une de ces quatre questions, sinon on ne la lit pas :

| Question | Donnée lue | À quoi elle sert |
|---|---|---|
| Où sont les zones ? | Zones OB obscanner 4h, 1h, daily + prix | Distance, zone intacte ou touchée |
| Dans quel sens ? | Structure daily et 4h (hauts, bas, dernière cassure) | Garder les zones dans le sens de la structure |
| La confirmation est-elle là ? | OB Kasper M1/M5/M10, Imbalance, Liquidité | Déclencher l'entrée. Lu seulement si le prix est dans la zone ou à moins de 0,3 % |
| Jusqu'où ? | Prochaine zone OB opposée, liquidité visible | TP3 et réalisme des cibles |

Les autres indicateurs ne sont lus que s'ils changent la décision.

## 0. État du montage
- tv_health_check : OK / KO (symbole affiché, port 9222)
- obscanner : OK / KO (heure de la dernière mise à jour)
- Alertes de la veille : expirées à 23 h 59, liste à renouveler

## 1. Tableau des plans (une ligne par actif ; week-end : BTCUSD seul)

| Actif | Sens | Zone OB (UT) | Prix / distance | Statut | Confirmation attendue | Entrée | SL | TP1 | TP2 | TP3 | R:R max | Taille (risque 100 $) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EURUSD | Vente | 1,13250 – 1,13404 (4h) | 1,12423 / +0,7 % | À surveiller | Cassure baissière M5/M10 | à la confirmation | 1,13517 | ≈ 1,12716 | ≈ 1,12449 | 1,11620 | 1:6 (provisoire) | ≈ 0,37 lot (provisoire) |

R:R et taille sont **provisoires** avant la confirmation (entrée supposée au bord proche de la zone), puis recalculés avec la vraie entrée. Taille = 100 $ ÷ distance entrée-SL ; en BTC pour BTCUSD, en lots pour EURUSD (1 lot = 100 000 unités) et XAUUSD (1 lot = 100 onces).

Statuts possibles :
- **En attente** : zone à plus de 1 % du prix, on ne fait rien.
- **À surveiller** : zone proche, l'alerte est posée sur son bord.
- **Zone touchée, attente confirmation** : le prix est dans la zone, on regarde M1/M5/M10.
- **Confirmé, entrée possible** : la confirmation est là, l'entrée se fait au retour dans le petit OB ou l'imbalance.
- **Annulé** : zone traversée sans confirmation, ou déjà consommée.

**Règle d'or : le contact avec la zone ne déclenche rien. Seule la confirmation dans le sens du trade déclenche l'entrée.**

L'entrée et la taille ne sont chiffrées qu'une fois la confirmation apparue, parce que c'est elle qui donne le point d'entrée exact. Avant, le tableau donne la zone, le SL prévu et les cibles.

## Sous le tableau : l'explication de chaque trade

Pour chaque actif, en quelques phrases simples :
1. **Pourquoi cette zone** : quel mouvement l'a créée, pourquoi le prix peut y réagir.
2. **Pourquoi ce sens** : ce que disent la tendance daily/4h, le momentum (KTA) et la liquidité.
3. **Quelle confirmation attendre** : ce qu'on veut voir sur M1/M5/M10, et à quoi ça ressemble.
4. **Pourquoi ce stop** : le scénario précis qui invalide l'idée.
5. **Pourquoi ces TP** : ratio ou zone opposée, et laquelle est la plus réaliste.
6. **Ce qui ferait renoncer** : news, zone traversée d'un coup, bougie de rejet dans le mauvais sens.

## 2. Dessins posés sur TradingView
- Rectangles : rouge (zone vendeuse), vert (zone acheteuse)
- Lignes horizontales étiquetées : Entrée, SL, TP1, TP2, TP3
- Jamais de draw_clear.

## 3. Alertes
- Une par actif, sur le bord proche de la zone OB : elle veut dire « zone atteinte, va chercher la confirmation », pas « entre ».
- Vérifiée par alert_list.
- Avec chaque alerte, rappeler SL, TP1, TP2, TP3.

## 4. Limites du jour
- 3 trades max, stop journalier -2 %, dernière entrée 18 h, flat 22 h.
