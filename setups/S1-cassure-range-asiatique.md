# S1 — Cassure du range asiatique

**Statut : hypothèse non validée.** Aucun de ces trois setups n'est un edge
prouvé. Ce sont des règles falsifiables que le journal confirmera ou tuera.

Le comportement le plus documenté de l'or : le range se construit pendant Tokyo
(faible volume), et Londres décide de la direction. C'est aussi celui qui colle
le mieux à ta fenêtre parisienne — le range se forme pendant que tu dors, tu
n'as qu'à trader sa résolution.

## Éligibilité (toutes obligatoires)

- Jour de semaine, hors férié majeur US/UK
- Range Tokyo = plus haut / plus bas entre **02h00 et 08h00 Paris** (00:00–06:00 UTC)
- Amplitude du range entre **0,5× et 1,5× l'ATR(14) D1**
  - Trop étroit → c'est du bruit, la cassure ne porte pas
  - Trop large → le mouvement a déjà eu lieu, on arriverait après
- Aucune publication US majeure avant 10h00 Paris

## Déclencheur (achat — symétrique en vente)

1. Une bougie **M15 clôture** au-dessus du plus haut du range, entre **09h00 et 11h30 Paris**
2. **Retest** : le prix revient dans la zone `[high_range ; high_range − 0,25×ATR M15]`
   sans qu'aucune M15 ne clôture sous le high du range
3. **Entrée** sur la première M5 qui clôture haussière dans la zone de retest

### Pourquoi exiger un retest

Les fausses cassures du range asiatique sont fréquentes sur l'or. Le retest
sacrifie les cassures les plus violentes — celles qui partent sans revenir — mais
élimine l'essentiel des faux signaux. **C'est un arbitrage assumé, pas une vérité.**
Le journal le mesure : chaque cassure partie sans nous est notée dans le champ
`manque` du résultat. Si après 30 trades les manqués valent plus que les faux
signaux évités, on supprime la condition de retest.

## Niveaux

- **SL** : sous le plus bas de la bougie de retest, minimum 1,2 × ATR(14) M15
  depuis l'entrée. Si la distance dépasse **2,5 × ATR M15 → trade refusé**.
- **TP1** : 1R → on sort la moitié, stop à break-even
- **TP2** : `high_range + amplitude_range`, ou 2R si plus proche
- **Flat** : 20h00 Paris, sans exception

## Invalidation avant entrée

- Pas de retest avant **12h30 Paris** → le plan meurt, on ne le repêche pas l'après-midi
- Une M15 clôture sous le high du range → fausse cassure confirmée, plan mort

## Régime Bali

**Inutilisable tel quel.** À Bali le range asiatique se forme pendant ta session
de trading, pas avant. Il faudra une variante — probablement sur le range de
la clôture NY de la veille. À écrire le moment venu, pas maintenant.
