---
id: 2026-08-19-1530-001   # même id que le plan
statut: CLOS              # CLOS | NON_EXECUTE
plan_respecte: oui        # oui | non
verdict: A_REPLIQUER      # A_REPLIQUER | COUT_NORMAL | DANGER | FAUTE_EXECUTION
r_realise: +1.8
---

# Résultat — <id>

> Post-mortem écrit **après** l'issue, dans un commit séparé.
> Ne cite que la version commitée du plan. Ne réécris jamais le plan.

## Exécution
- Entré : oui / non — pourquoi
- Prix d'entrée réel vs planifié :
- Prix de sortie / motif (TP, SL, flat 20h, sortie manuelle) :
- R réalisé :

## Écarts au plan
Chaque écart, même favorable. Un écart qui a payé reste un écart.

## Verdict
| Plan respecté | Issue | Verdict |
|---|---|---|
| oui | gain | `A_REPLIQUER` |
| oui | perte | `COUT_NORMAL` — aucune correction de règle |
| non | gain | `DANGER` — un gain qui récompense une faute |
| non | perte | `FAUTE_EXECUTION` |

## Ce que le marché a fait que le plan n'avait pas prévu

## Manqué (`manque`)
Le trade que les règles ont refusé et qui aurait payé. Champ décisif : c'est le
seul moyen de savoir si un filtre protège ou s'il coûte plus qu'il ne rapporte.
À remplir même les jours sans trade.

## Leçon
Écris **« aucune »** si le trade n'apprend rien. C'est le cas le plus fréquent
et le plus honnête. Forcer une leçon à chaque trade, c'est apprendre du bruit.
