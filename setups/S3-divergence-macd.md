# S3 — Divergence MACD sur niveau H1

**Statut : hypothèse non validée. Le plus risqué des trois.**

Ta demande MACD. C'est un setup **contre-tendance**, donc celui qui a le plus
de chances d'être désactivé après 30 trades — et le plus bordé pour cette
raison. Une divergence MACD prise en tendance est une machine à perdre : le
filtre ADX ci-dessous n'est pas décoratif, il est la condition d'existence du setup.

## Éligibilité (toutes obligatoires)

- **ADX(14) H1 < 20** → jour de range. C'est le filtre vital.
- Le prix touche un **niveau H1 identifié à l'avance** : plus haut / plus bas des
  5 derniers jours, ou zone testée ≥ 2 fois
- Fenêtre : **09h00–18h00 Paris**
- Aucune publication US dans les 60 minutes

## Déclencheur

1. **Divergence régulière** MACD(12,26,9) sur M15 : deux sommets de prix
   croissants contre deux sommets d'histogramme décroissants (inverse en achat)
2. Les deux sommets séparés d'au moins **5** et au plus **20** bougies M15
3. **Confirmation** : clôture M15 qui repasse du bon côté du niveau

## Niveaux

- **SL** : au-delà de l'extrême de la divergence, minimum 1,0 × ATR M15
- **TP1** : **1R strict** — en contre-tendance on encaisse vite
- **TP2** : milieu du range du jour
- **Flat** : 20h00 Paris
- **Maximum 1 trade S3 par jour**

## Invalidation avant entrée

- ADX(14) H1 repasse ≥ 20 pendant la formation → plan annulé immédiatement
- Une publication US tombe dans la fenêtre → plan annulé

## Régime Bali

Transposable, mais les jours de range sont plus fréquents sur Tokyo+Londres que
sur Londres+NY. Ce setup sera probablement **plus** utilisable à Bali qu'à Paris.
