# Gabarit du brief du matin (8 h, heure de Paris)

Objectif : trois actifs, les zones proches, un plan par actif, et surtout le
**pourquoi** de chaque décision, pour apprendre en même temps qu'on trade.
Rien n'est exécuté : analyse, dessins sur le graphique, alertes.

## 0. État du montage
- tv_health_check : OK / KO (symbole affiché, port 9222)
- obscanner : OK / KO (heure de la dernière mise à jour)
- Alertes de la veille : expirées à 23 h 59, liste à renouveler

## 1. Pour chaque actif (XAUUSD, BTCUSD, EURUSD ; week-end : BTCUSD seul)

### Contexte (la lecture d'ensemble)
- Tendance daily et 4h : haussière / baissière / en range, et ce qui le montre
  (derniers hauts et bas, dernière cassure de structure).
- Momentum (KTA Momentum) : accélère, ralentit, diverge.
- Où est la liquidité (Zones Liquidités) : au-dessus de quel haut, sous quel bas.

### Les 3 zones les plus proches du prix (obscanner 4h / 1h / daily)
| Zone | Sens | Haut | Bas | Distance au prix | Touchée ? |
|---|---|---|---|---|---|

Règles d'écartement :
- plus de 1 % du prix : « trop loin, on attend »
- déjà touchée : « consommée, pas de plan dessus »

### Confirmation petites unités (OB Kasper, M1 / M5 / M10)
- Y a-t-il une structure, une imbalance ou une prise de liquidité qui va dans le
  sens de la zone ? Si rien : pas de trade, on note pourquoi.

### Le plan (si une zone passe les filtres)
- Entrée : bord proche de la zone
- SL : au-delà du bord lointain + 0,1 %
- TP1 : 1:2 · TP2 : 1:3 · TP3 : prochaine zone opposée si elle arrive avant
- Taille : 1 % du capital ÷ distance au stop

### Le pourquoi (obligatoire, c'est la partie pédagogique)
1. Pourquoi cette zone : quel mouvement l'a créée, pourquoi le marché peut y revenir.
2. Pourquoi ce sens : ce que disent la structure et le momentum.
3. Pourquoi ce stop : le scénario précis qui invalide l'idée.
4. Pourquoi ces TP : ratio ou zone opposée, et laquelle est la plus réaliste.
5. Ce qui ferait renoncer : news, bougie de rejet, zone cassée avant l'entrée.

## 2. Dessins posés sur TradingView
- Rectangles : rouge (zone vendeuse), vert (zone acheteuse)
- Lignes horizontales étiquetées : Entrée, SL, TP1, TP2, TP3
- Jamais de draw_clear.

## 3. Alertes
- Une par actif, sur l'entrée, vérifiée par alert_list.
- Avec chaque alerte, rappeler SL, TP1, TP2, TP3.

## 4. Limites du jour
- 3 trades max, stop journalier -2 %, dernière entrée 18 h, flat 22 h.
