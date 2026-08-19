# Harnais walk-forward

Backtest barre par barre du rulebook, sur données XAU/USD M15 réelles.

## Principe

Le harnais ne parle jamais à l'API pendant un backtest : il lit un **cache figé
sur disque**. Un backtest doit être reproductible à l'identique, et le quota
gratuit (800 appels/jour) ne doit pas être brûlé à chaque essai.

## Modules

| Module | Rôle |
|---|---|
| `bougie.py` | Structure OHLC. Refuse tout horodatage naïf ou non-UTC |
| `fuseau.py` | Sydney → UTC, calendrier forex, **assertion de décalage** |
| `nettoyage.py` | Rejet des bougies synthétiques (calendrier + amplitude) |
| `cache.py` | Lecture du cache, tri chronologique, détection de doublons |
| `indicateurs.py` | ATR, EMA, MACD, ADX — Wilder, strictement causaux |
| `agregation.py` | M15 → H1 et M15 → journalier forex (bornes 17h NY) |
| `vue.py` | `VueMarche` — rend le look-ahead impossible |

## Les deux garanties

**1. Le fuseau est vérifié, pas supposé.** `verifier_decalage()` localise la
fermeture hebdomadaire du forex dans les données et la compare au calendrier
(vendredi 17h New York). Écart > 30 min → exception. Si Twelve Data change son
fuseau par défaut, on obtient un échec bruyant, pas un backtest plausible et faux.

**2. Le look-ahead est impossible, pas déconseillé.** Une règle ne reçoit jamais
la liste des bougies, seulement une `VueMarche` bornée à l'indice courant. Tout
accès au futur lève `RegardVersLeFutur`. C'est l'équivalent structurel de ce que
le mode replay de TradingView garantit par construction.

## Tests

```bash
cd trading-ia && python3 harnais/tests/test_donnees.py
```

Les fixtures sont de **vraies bougies Twelve Data**, choisies de part et d'autre
d'une bascule d'heure d'été australe : août (Sydney +10) et janvier (Sydney +11).
Un décalage codé en dur ferait échouer l'une des deux.
