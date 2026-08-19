# Twelve Data — validation de la source (19/08/2026)

Connecteur activé et testé. **Le plan gratuit suffit.** Mais la source a deux
pièges qu'il faut traiter dans le harnais, sinon le backtest produit des
résultats plausibles et faux.

## Ce qui fonctionne

| Test | Résultat |
|---|---|
| Quota | 800 appels/jour, plan gratuit |
| XAU/USD | Couvert — « Gold Spot / US Dollar », Forex |
| OHLC 15min | Oui |
| Indicateurs 15min | Oui — ATR(14) M15 relevé à 13,37 $ |
| Historique intraday | **≥ 7 mois** — bougies M15 récupérées au 17/01/2026 |

L'historique gratuit dépasse ce qu'offre TradingView Essential en 1-minute
(6 mois). Pour un walk-forward en M15, c'est largement suffisant.

## Piège n°1 — les horodatages sont en heure de Sydney, avec DST

**Les `datetime` renvoyés ne sont ni en UTC, ni en heure de marché.**

Méthode de vérification : le forex ferme le vendredi à 17h00 New York. On
localise la fermeture hebdomadaire dans la série et on compare à l'heure UTC
réelle de cet instant.

| Échantillon | Dernière vraie bougie | Fermeture réelle (UTC) | Décalage |
|---|---|---|---|
| Samedi 15/08/2026 | 07:00 | vendredi 21:00 (EDT, UTC−4) | **+10 h** |
| Samedi 17/01/2026 | 09:00 | vendredi 22:00 (EST, UTC−5) | **+11 h** |

Recoupement indépendant : au moment du test (14:17 UTC le 19/08), la dernière
bougie était étiquetée `2026-08-20 00:15` — soit +10 h également.

+10 h en août, +11 h en janvier : **le fuseau suit l'heure d'été de l'hémisphère
sud. C'est `Australia/Sydney`** (AEST UTC+10 d'avril à octobre, AEDT UTC+11
d'octobre à avril).

### Pourquoi c'est dangereux

Trois fuseaux changent d'heure à des **dates différentes** :

| | Bascule |
|---|---|
| Étiquettes du flux (Sydney) | début octobre / début avril |
| Nos règles (Paris) | fin mars / fin octobre |
| Sessions de marché (New York, Londres) | dates encore différentes |

Un décalage codé en dur serait juste la plupart de l'année et **faux plusieurs
semaines par an**, sans rien casser visiblement. Avec un offset erroné de 10 h,
le « range asiatique 00:00–06:00 UTC » de S1 serait calculé sur 14:00–20:00 UTC,
c'est-à-dire la session de New York. Le backtest tournerait, produirait une
courbe d'équité, et ne voudrait rien dire.

### Traitement dans le harnais

1. Interpréter chaque étiquette dans `Australia/Sydney` via la base tz, puis
   convertir en UTC. Le DST est géré par la bibliothèque, jamais à la main.
2. **Assertion à chaque exécution** : localiser la fermeture hebdomadaire dans
   les données et vérifier qu'elle tombe où le calendrier forex le dit.
   Échec bruyant en cas d'écart. Si Twelve Data change son fuseau par défaut
   un jour, l'assertion le détecte au lieu de produire du plausible faux.

## Piège n°2 — le marché fermé est comblé par des bougies synthétiques

Le flux ne saute pas les périodes de fermeture : il les remplit avec un prix figé.

```
2026-08-15 07:00  4376.019  4376.942  4375.536  4375.684   <- dernière vraie
2026-08-15 07:15  4375.600  4375.985  4375.537  4375.675   <- figée
2026-08-15 07:30  4375.598  4375.896  4375.538  4375.585   <- figée
2026-08-15 07:45  4375.598  4375.799  4375.534  4375.589   <- figée
```

Signature : amplitude ≈ **0,26 $** quand l'ATR réel est à **13 $**, et OHLC
quasi identiques d'une bougie à l'autre. Même motif confirmé sur les deux
échantillons (août et janvier).

### Ce que ça casserait

- **ATR écrasé vers zéro** sur le week-end. Le calcul de taille étant
  `risque / distance au stop`, une position dimensionnée sur un ATR de 0,3 $ au
  lieu de 13 $ serait **40 fois trop grosse**.
- **S1 déclencherait un faux signal chaque lundi** : le range asiatique calculé
  sur des bougies figées est minuscule, donc la réouverture ressemble toujours
  à une cassure massive.
- MACD et ADX s'aplatissent puis fouettent à la réouverture.

### Traitement dans le harnais

1. **Filtre principal** : calendrier forex. Marché fermé du vendredi 17h00 NY au
   dimanche 17h00 NY, en tenant compte du DST américain.
2. **Garde-fou secondaire** : rejeter toute bougie dont l'amplitude est
   inférieure à 5 % de l'ATR courant. Attrape les fériés et les coupures de flux
   que le calendrier ne prévoit pas.

Les deux, pas l'un ou l'autre : le calendrier rate les fériés, le garde-fou seul
rejetterait de vraies bougies très calmes.

## Contexte de marché relevé au test

- XAU/USD : 4 473 $, **+3,17 % sur la journée** (+137 $)
- Amplitude 52 semaines : 3 301 – 5 597 $
- ATR(14) M15 : 13,37 $

L'or est dans une phase très volatile. Avec 1 % de risque (100 $) et un stop à
1,2 × ATR ≈ 16 $, la taille ressort à ~6 oz. Les ordres de grandeur du modèle de
risque tiennent, mais l'amplitude annuelle de 70 % justifie de vérifier
régulièrement que l'ATR n'a pas changé de régime.
