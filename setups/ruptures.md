# Ce que l'écriture en code a cassé dans le rulebook

Le rulebook en prose se lisait comme objectif. Il ne l'était pas. Sur environ 35
clauses, **10 se sont dérobées** au moment de les écrire en règles mécaniques.

C'est exactement ce que cette étape devait révéler — et la raison de la faire
avant de payer un abonnement TradingView.

## A. Règles abandonnées faute de source de données

Aucune n'est contournée : elles sont **retirées du système**, et leur absence
change ce que le backtest mesure.

| | Règle | Manque |
|---|---|---|
| **R1** | S1 « hors férié majeur US/UK » | Pas de calendrier des fériés |
| **R2** | S1 « aucune publication US avant 10h » | Pas de calendrier économique |
| **R3** | S3 « aucune publication US sous 60 min » | Idem |
| **R4** | S1 « entrée sur la première M5 » | On n'a que du M15 |

**Conséquence à garder en tête** : R1–R3 étaient des filtres de *protection*. Sans
eux, le backtest prendra des trades les jours de NFP et de CPI — précisément ceux
où l'or fait des mouvements de 40 $ en trois minutes. Les résultats seront donc
**plus bruyants et plus mauvais** que ce que donnerait le système complet. C'est
le bon sens du biais : on préfère sous-estimer.

R4 dégrade le prix d'entrée. Entrer à la clôture M15 au lieu d'une M5 de
confirmation coûte en moyenne une fraction de bougie.

## B. Formulations ambiguës — un choix a été fait, il est arbitraire

Ce sont les candidats prioritaires au réglage une fois qu'on aura des données.

| | Règle | Ce qui manquait | Choix retenu |
|---|---|---|---|
| **R5** | S1 « le prix revient dans la zone » | mèche ou clôture ? | **Mèche**. La clôture donnerait moins d'entrées et de meilleurs prix |
| **R6** | S2 « impulsion de N bougies » | quel point de départ ? | Extrême de fenêtre → extrême opposé, dans l'ordre chronologique, retracement max 38,2 % |
| **R7** | S2 « EMA50 H1 orientée » | orientée sur quelle durée ? | Pente mesurée sur 3 heures (12 bougies M15) |
| **R8** | S2 « mèche ≥ 50 % du corps » | indéfini si le corps est nul | Corps minimal exigé à 0,10 × ATR |
| **R9** | S3 « zone testée ≥ 2 fois » | aucune définition opérationnelle | **Abandonnée.** Seul subsiste le plus haut / bas des 5 séances |

R6 est le plus lourd de conséquences : une définition par swing points
identifierait d'autres impulsions, et donc d'autres trades. Le résultat de S2
dépend d'un choix que rien ne justifie encore.

## C. Le piège caché

**R10 — S3 « deux sommets ».** Un sommet ne se confirme qu'**après coup** : il
faut voir les bougies suivantes pour savoir que c'en était un. Détecter une
divergence sur les dernières bougies revient donc à lire le futur — et ce genre
d'erreur ne se voit pas dans les résultats, elle les rend simplement excellents.

Corrigé par `DECALAGE_PIVOT = 2` : les deux dernières bougies ne peuvent pas
héberger de pivot confirmé. S3 réagit donc avec 30 minutes de retard sur ce que
l'œil croit voir sur un graphique. C'est la réalité du signal, pas une limite du
harnais.

## Ce que ça dit du rulebook

Un ensemble de règles dont 10 clauses sur 35 se dérobent à l'écriture n'était pas
un rulebook — c'était une intention. La version en prose *donnait le sentiment*
d'être objective parce que chaque clause est plausible lue isolément. C'est
précisément le mécanisme qui rend un journal de trading inutile : on croit
appliquer un système, on applique un jugement.

Ordre de traitement quand les données seront là :
1. Faire tourner le backtest **tel quel** — il mesure ce qui est réellement codé
2. Tester la sensibilité de R5 et R6 : si les résultats basculent selon le choix,
   c'est que le setup n'a pas d'edge, seulement un réglage
3. Ne chercher un calendrier économique (R2, R3) que si le bruit des jours de
   publication domine les statistiques
