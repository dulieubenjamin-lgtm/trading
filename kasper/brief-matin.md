# Gabarit du brief du matin (8 h, heure de Paris)

Objectif : trois actifs, les zones proches, un plan par actif, et surtout le
**pourquoi** de chaque décision, pour apprendre en même temps qu'on trade.
Rien n'est exécuté : analyse, dessins sur le graphique, alertes.

## 0. État du montage
- tv_health_check : OK / KO (symbole affiché, port 9222)
- obscanner : OK / KO (heure de la dernière mise à jour)
- Alertes de la veille : expirées à 23 h 59, liste à renouveler

## 1. Tableau des plans (une ligne par actif ; week-end : BTCUSD seul)

| Actif | Sens | Zone OB (UT) | Prix / distance | Statut | Confirmation attendue | Entrée | SL | TP1 | TP2 | TP3 | R:R |
|---|---|---|---|---|---|---|---|---|---|---|---|
| XAUUSD | Achat | 4 160 – 4 171 (4h) | 4 190 / 0,5 % | À surveiller | Cassure de structure haussière M5 | après confirmation | 4 155 | 1:2 | 1:3 | zone 4 230 | 1:3,5 |

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
