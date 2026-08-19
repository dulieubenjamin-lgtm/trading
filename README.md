# IA de trading + journal intégré — cahier des charges v0

**Statut : brouillon de conception. Aucun trade, aucun argent réel.**
Support de la discussion en cours. Rien ici n'est figé.

---

## 1. La contrainte dure : je n'ai pas de flux de prix

Testé depuis cette session, résultats vérifiés :

| Source tentée | Résultat |
|---|---|
| `api.binance.com` | `403` — bloqué par la politique réseau de l'environnement |
| `stooq.com` (CSV XAUUSD) | `403` — bloqué |
| `query1.finance.yahoo.com` | `403` — bloqué |
| WebFetch sur ces mêmes hôtes | `EGRESS_BLOCKED` |
| Recherche web | Fonctionne, mais renvoie ~4 380 $ / 4 348 $ / 4 397 $ selon la source |

Trois sources, 50 $ d'écart. Pour un stop de 10 $ sur du M15, c'est inutilisable.

**Et TradingView ne se « donne » pas.** Il n'y a pas d'API publique de données
TradingView : le site est protégé, et même sans blocage réseau je ne pourrais
pas m'y connecter avec tes identifiants. Donc « je te donne accès à TradingView »
ne peut pas se traduire techniquement par un accès direct. Il faut choisir un
autre chemin — voir §2.

Ce que ça implique : **je ne peux pas, aujourd'hui, regarder le marché tout seul.**
Tout le reste du système (analyse, plan de trade, journal, statistiques) est
faisable immédiatement. C'est la seule brique manquante, et elle est bloquante
pour l'autonomie, pas pour démarrer.

## 2. Les trois façons de me brancher au marché

**A — Tu es le flux.** Tu me copies les bougies OHLC depuis TradingView (export
CSV, ou copier-coller de la fenêtre de données), ou tu m'envoies une capture.
Je produis le plan, tu exécutes en démo, tu me donnes le résultat.
→ 0 setup, opérationnel dès aujourd'hui. Je ne vois que ce que tu me montres.

**B — Un petit script chez toi.** Sur ta machine, un script tire les bougies
XAUUSD depuis une API gratuite et les écrit dans ce dépôt. Je lis le dépôt.
→ Vraies données, vraie précision. Demande ~1h de setup et que ta machine tourne.

**C — Ouvrir le réseau de l'environnement.** L'environnement d'exécution a une
politique réseau choisie à sa création. Si tu en crées un qui autorise un hôte
de données, je tire les prix moi-même, en direct, sans toi.
→ Le seul chemin vers une vraie autonomie. Doc : https://code.claude.com/docs/en/claude-code-on-the-web

Mon avis : **A pour commencer cette semaine, C comme cible.** B seulement si C
est refusé, parce que B dépend de ta machine allumée — donc pas quand tu dors,
donc pas de session Tokyo.

## 3. XAUUSDT ou XAUUSD ? (ce n'est pas un détail)

Tu as écrit XAUUSDT. Ce sont deux instruments différents :

- **XAUUSD** — l'or spot du Forex. Ouvert dimanche 23h → vendredi 22h (Paris),
  **fermé le week-end**, rythmé par les sessions. Spread serré. C'est ce que
  suivent London Fix et le COMEX.
- **XAUUSDT** — de l'or synthétique coté en Tether, sur des exchanges crypto
  (MEXC, Bitget, Gate). Tourne **24/7, week-end compris**, spread plus large,
  liquidité plus fine, et il peut décrocher du spot quand l'USDT bouge.

Ton plan — sessions Tokyo → New York, pas de trade la nuit — est un plan
**XAUUSD**. Sur XAUUSDT, la notion de « session » est beaucoup plus floue et tu
ajoutes un risque de contrepartie crypto qui n'a rien à voir avec ta thèse sur
l'or. À trancher avant d'écrire la moindre règle.

## 4. Le cœur du système : le verrou anti-biais

C'est le seul point sur lequel je ne transigerai pas, parce que c'est ce qui
sépare un journal utile d'une machine à se raconter des histoires.

Le piège d'un « journal analysé par IA » : après coup, je peux justifier
n'importe quel résultat. Trade gagnant → « le MACD confirmait ». Trade perdant
→ « la Fibo n'était pas assez nette ». Les deux sont plausibles, aucune n'est
falsifiable, et tu apprends du bruit pendant six mois.

**Le verrou : la thèse est commitée avant l'issue.**

1. Avant l'entrée, j'écris `<horodatage>.plan.md` : contexte, déclencheur exact,
   entrée, SL, TP, et surtout **« ce qui prouverait que j'ai tort »**.
2. Ce fichier est commité dans git. Horodatage et empreinte figés.
3. Le résultat arrive dans un fichier **séparé**, commité plus tard.
4. Le post-mortem n'a le droit de citer que la version commitée du plan.

Git rend la triche visible. Si je réécris un plan après coup, ça se voit dans
l'historique.

**Et on note le processus, pas le résultat.** Quatre cases :

| | Plan respecté | Plan violé |
|---|---|---|
| **Gagnant** | À répliquer | ⚠️ Le cas le plus dangereux — un gain qui récompense une faute |
| **Perdant** | Coût normal du business. Aucune correction. | Faute d'exécution |

Un perdant qui a suivi le plan ne déclenche **aucun** changement de règle. C'est
contre-intuitif et c'est exactement ce qui empêche de sur-ajuster.

**Le journal n'aura rien à dire avant un mois.** À ~2 trades/jour, il faut 30 à
50 trades par setup pour distinguer un edge du hasard, soit 4 à 6 semaines. Toute
conclusion tirée sur 8 trades sera du bruit, et je te le dirai plutôt que de te
fabriquer un rapport qui a l'air sérieux.

## 5. Paris puis Bali : ce ne sera pas la même stratégie

Tu prévois Bali « pareil ». Ce ne sera pas pareil, et c'est structurel.

Heures d'août (Paris = UTC+2, Bali = UTC+8, sans changement d'heure) :

| Événement | UTC | Paris | Bali |
|---|---|---|---|
| Ouverture Tokyo | 00:00 | 02:00 | 08:00 |
| Clôture Tokyo | 06:00 | 08:00 | 14:00 |
| Ouverture Londres | 07:00 | 09:00 | 15:00 |
| Chiffres US (NFP/CPI) | 12:30 | 14:30 | 20:30 |
| **Ouverture NY / COMEX** | 13:30 | 15:30 | 21:30 |
| Fixing Londres PM | 14:00 | 16:00 | 22:00 |
| Ton flat obligatoire | 18:00 | **20:00** | **02:00 — en pleine nuit** |

À Paris, ta journée 08h–20h te donne **Londres + l'ouverture de New York**.
À Bali, la même journée 08h–20h te donne **Tokyo + Londres**, et tu te couches
juste avant l'ouverture de New York.

Autrement dit : la contrainte « pas de trade la nuit » produit **deux stratégies
différentes** selon où tu dors. Les setups qui marchent à Paris (impulsion NY,
réaction aux chiffres US) sont précisément ceux que tu n'auras plus à Bali.

Conséquences pour la construction :
- La fenêtre de trading est un **paramètre de config**, jamais une valeur en dur.
- Tout est stocké en **UTC**, converti à l'affichage. Sinon le passage
  heure d'été/hiver décale silencieusement ta règle des 20h.
- Chaque trade est tagué `regime: paris` ou `regime: bali`. **Les statistiques
  ne se mélangent pas** — ce sont deux échantillons distincts.

## 6. Trois setups, pas trente

Tu proposes que j'aie accès à « l'ensemble des méthodes » — Fibonacci, MACD, etc.
C'est le piège classique. Un système qui peut invoquer 30 indicateurs trouvera
toujours de quoi justifier l'envie du moment. L'edge vient d'un rulebook court,
déclaré à l'avance, et falsifiable.

Proposition de départ, adaptée à ta fenêtre parisienne :

**S1 — Cassure du range asiatique** (le plus adapté à ton créneau)
Le range Tokyo (02h–08h Paris) se casse à l'ouverture de Londres. Objectif,
mécanique, historiquement le comportement le plus documenté de l'or.
Entrée sur retest du bord cassé. SL = 1,2 × ATR(14, M15) de l'autre côté.

**S2 — Pullback Fibonacci sur impulsion de session** (ta demande Fibo, rendue objective)
Impulsion ≥ 1,5 × ATR après ouverture Londres/NY. Entrée en zone 0,618–0,705
**uniquement** en confluence avec l'EMA50 M15. Sans confluence : pas de trade.

**S3 — Divergence MACD sur niveau H1** (ta demande MACD, bornée)
Contre-tendance, autorisé **seulement les jours de range** (ADX H1 < 20).
Sans ce filtre, une divergence MACD en tendance est une machine à perdre.

Chaque setup a : conditions d'éligibilité, déclencheur, règle de SL, règle de TP
en multiples de R, et invalidation. Après 30 trades, le journal en tue au moins un.

## 7. Modèle de risque (compte papier)

Proposition, à ajuster :

- Capital virtuel : 10 000 $
- Risque par trade : 1 % (100 $) — la taille se déduit du SL, jamais l'inverse
- Maximum 3 trades / jour
- Stop journalier : −2 % → on arrête, on ne « se refait » pas
- Flat à 20h00 Paris, sans exception, y compris sur un trade gagnant
- Objectifs en R, pas en dollars

## 8. Décisions prises (19/08)

| Question | Décision |
|---|---|
| Instrument | **XAUUSD** — or spot forex |
| Périmètre de départ | **Assistant-analyste** (choix délégué, voir ci-dessous) |
| Risque | **Standard** — 10 000 $, 1 %/trade, 3 trades/jour max, stop journalier −2 % |
| Données | **Claude in Chrome** — à confirmer, voir §9 |

Sur le périmètre, tu m'as laissé choisir. Je prends l'assistant-analyste, pour
une raison précise : **on ne code pas des règles qu'on n'a pas encore testées.**
Écrire les 3 setups en code aujourd'hui, c'est figer dans un backtest des seuils
sortis de nulle part (pourquoi 0,618–0,705 ? pourquoi ADX < 20 ?). Le manuel
d'abord sert à découvrir lesquels de ces seuils sont arbitraires. Après ~30
trades, on saura quoi coder, et le backtest voudra dire quelque chose.

Chemin prévu : **manuel (4–6 semaines) → moteur codé → dashboard**. Le
dashboard en dernier — il donne l'impression d'un système sérieux bien avant
qu'il y en ait un.

## 9. Le point Claude in Chrome

Tu proposes de me donner accès par Chrome. **C'est la bonne idée — mais pas
depuis cette session.**

- Cette session tourne dans un conteneur isolé, dans le cloud. Elle ne peut pas
  atteindre le Chrome de ta machine. Vérifié : les outils `claude-in-chrome` ne
  sont pas exposés ici.
- Même le Chromium installé dans le conteneur ne sert à rien : `tradingview.com`
  est bloqué par la politique réseau, comme les autres.

En revanche, ton `.claude/settings.json` autorise déjà `claude-in-chrome`
(`read_page`, `get_page_text`, `find`…). Donc tu l'utilises quand **Claude Code
tourne en local sur ton Mac** — et là, ça marche : je lis l'onglet TradingView,
la fenêtre de données, les valeurs d'indicateurs, le prix courant.

**Le bon montage :**

| Où | Quoi |
|---|---|
| Claude Code **en local** (dossier Quete-Vefa) | Lecture TradingView via Chrome, plans de trade, post-mortems en séance |
| Cette session **distante** | Conception, rulebook, statistiques, code — tout ce qui ne demande pas le marché en direct |
| **git** | Le lien entre les deux : le journal est versionné, les deux côtés le voient |

Limite honnête : lire l'onglet donne le prix courant et la fenêtre de données,
pas un historique complet. Pour backtester il faudra l'export CSV de TradingView
(plans payants) ou l'option C. Pour des plans en séance, lire l'onglet suffit.
