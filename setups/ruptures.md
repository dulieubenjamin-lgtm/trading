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


---

# Deuxième passe — ce que le backtest a révélé (20/08)

Premier walk-forward sur 7 mois réels : **3 trades**, tous S1. S2 et S3 : zéro
signal. L'entonnoir (`outils/entonnoir.py`) a localisé chaque blocage.

## D. Défauts corrigés, avec la mesure avant/après

**R6 — S2, l'impulsion était géométriquement impossible.**
La détection cherchait l'impulsion la plus ample sur une fenêtre *incluant la
bougie courante*. Maximiser l'ampleur place l'extrême **sur** cette bougie, donc
un retracement toujours nul : 53 impulsions détectées, **0** avec le prix dans la
zone 0,618–0,705. Détection et mesure du pullback sont désormais séparées —
l'impulsion doit s'être achevée au moins une bougie avant, et son extrême ne doit
pas avoir été dépassé depuis.
→ **53 → 127 impulsions, zone 0 → 4.**

**R11 (nouveau) — S3, deux conditions posées sur des bougies différentes.**
Le toucher du niveau se lisait sur la bougie courante, la divergence sur des
pivots vieux d'au moins 2 bougies (décalage anti-look-ahead). Les deux voulaient
décrire le **même** extrême de prix. C'est le pivot qui doit toucher le niveau ;
la bougie courante ne sert qu'à confirmer le retour.
→ **divergences de prix 0 → 41.**

**S1 — un seuil inventé, remplacé par un seuil mesuré.**
La bande exigeait 0,50–1,50 × ATR journalier. Mesure : le range asiatique vaut
**0,39 × ATR journalier en médiane**. La bande était posée presque entièrement
au-dessus de la distribution réelle, rejetait 72 % des jours comme « trop
étroits » et ne retenait que le quartile le plus large — l'inverse de l'intention.
Recalibrée sur janvier–avril **uniquement** : **[0,24 ; 0,69]**.

## E. Deux blocages restants, qui ne sont pas des bugs

Ce sont des **erreurs de spécification**. Les corriger, c'est réécrire le setup.

**R12 — S2 : la « confluence obligatoire » est un filtre d'impossibilité.**
La zone 0,618–0,705 ne mesure que **0,38 × ATR** de large. Exiger que le prix
*et* l'EMA50 M15 s'y trouvent simultanément, c'est demander à deux grandeurs
largement indépendantes de coïncider dans une fenêtre étroite.
→ 4 candidats atteignent la zone, **0** passent la confluence.

**R13 — S3 : « divergence à un extrême 5 jours » est auto-contradictoire.**
Un nouvel extrême sur 5 séances signifie **par construction** que le prix vient
de balayer tout ce que la semaine contenait : le momentum y est maximal. Y
chercher un affaiblissement du momentum, c'est chercher l'inverse de ce que
l'extrême signifie.

Vérifié plutôt qu'affirmé — en retirant la seule exigence de niveau :

| | avec le niveau 5j | sans |
|---|---|---|
| divergences de prix | 41 | 1 013 |
| dont divergence MACD | **0** | **236 (23 %)** |

Les divergences existent, en proportion normale. Testé aussi sur la ligne MACD
et non l'histogramme : 0/41 également. Ce n'est donc ni un bug de signe ni un
choix d'indicateur — c'est la spécification.

## F. Résultat hors échantillon

Calibrage sur janvier–avril, test sur **mai–août, jamais utilisé pour régler
quoi que ce soit**.

| | trades | réussite | R total |
|---|---|---|---|
| Calibrage (jan–avr) | 5 | 40 % | −2,12 |
| **Test (mai–août)** | **5** | **20 %** | **−3,65** |

**Aucune conclusion n'est permise sur 5 trades.** Le seuil fixé d'avance était de
20 trades minimum par setup (`config.yml`). On en a un quart, sur un seul setup.
Ce chiffre ne dit pas que S1 perd : il dit qu'on n'a rien mesuré.

## G. Le piège à éviter maintenant

La tentation évidente est d'assouplir R12 et R13 jusqu'à ce que des trades
apparaissent. Ce serait régler les seuils pour obtenir des signaux, puis
constater qu'il y a des signaux. La bande de S1 a été recalibrée **d'après une
distribution mesurée et une règle de centiles fixée à l'avance**, jamais d'après
les résultats — c'est la seule forme de réglage admissible, et elle reste à
valider hors échantillon sur davantage de données.

Pour S2 et S3, le problème n'est pas un seuil mais l'idée du setup. Il faut le
réécrire, pas le desserrer.

---

# Troisième passe — lecture D1 / H4 / M15 / M5 (20/08)

## H. Les deux blocages du §E sont levés, par restructuration et non par desserrage

**R12 — S2.** La « confluence obligatoire » exigeait que le prix *et* l'EMA50 M15
se trouvent dans une zone large de 0,38 × ATR : deux grandeurs indépendantes
dans une fenêtre étroite, soit un filtre d'impossibilité (4 candidats, 0 passant).
Le biais est désormais porté par l'unité qui a vocation à le porter, la **H4**.
Ce n'est pas un seuil desserré, c'est une condition déplacée sur la bonne unité.

**R13 — S3.** « Divergence à un extrême 5 jours » demandait un essoufflement du
momentum exactement là où le momentum est maximal par construction. Le niveau est
désormais un **pivot H4 confirmé et déjà ancien** (≥ 3 bougies H4) — un niveau
travaillé, où un momentum a le droit de faiblir.
→ **S3 passe de 0 à 17 signaux.** Le diagnostic était juste.

## I. R14 — un bug introduit par la réécriture, attrapé par le test

La reconstruction de l'état de cassure de S1 parcourait la vue **à l'envers du
temps** et traitait toute clôture du mauvais côté comme une invalidation — y
compris celles *antérieures* à la cassure, qui ne sont que l'état d'avant.
Conséquence : aucune cassure ne survivait à sa propre bougie précédente.

Le scénario construit de `test_setups.py` l'a signalé immédiatement. C'est
précisément pourquoi il existe : un setup qui ne se déclenche jamais est
indiscernable d'un setup sans signal.

## J. Résultats après restructuration

Calibrage jan–avr, test mai–août jamais utilisé pour régler quoi que ce soit.

| | trades | réussite | R moyen | R total |
|---|---|---|---|---|
| **S1** (test) | **19** | 36,8 % | **−0,391** | −7,42 |
| **S3** (test) | 9 | 55,6 % | −0,063 | −0,57 |
| S2 (test) | 0 | — | — | — |
| **Total test** | **28** | | | **−7,99** |

**S1 atteint 19 trades** — au seuil des 20 fixé d'avance. C'est le premier
chiffre qui approche une portée statistique, et il est franchement négatif :
−0,39 R par trade sur 19 trades. Un trade de plus ne renverserait pas ce signe.

**S3 est à l'équilibre moins les frais** : 55,6 % de réussite pour −0,06 R par
trade. La signature d'un setup sans edge qui paie le spread — pas d'un setup
dangereux, mais pas d'un setup utile non plus.

**S2 reste mort** : 1 signal sur le calibrage, 0 sur le test. Le déplacement du
biais sur H4 ne l'a pas ranimé. À ce stade, l'hypothèse la plus économique est
que la conjonction « impulsion de 1,5 × ATR en ≤ 6 bougies » et « retracement
exactement entre 0,618 et 0,705 » est trop étroite pour l'or en M15.

## K. Ce que ces chiffres NE disent pas

Ils portent sur une base **M15**, pas M5 : le déclencheur d'entrée reste une
clôture M15 (R4 non résolu) et l'ambiguïté intra-bougie porte toujours sur 15
minutes. Les prix d'entrée sont donc dégradés par rapport à ce que le rulebook
spécifie, ce qui pénalise mécaniquement les résultats sans qu'on sache de combien.

---

# Quatrième passe — base M5 (20/08)

Le cache M5 est arrivé : 60 461 bougies, 41 263 après filtrage. R4 est résolu —
le déclencheur d'entrée est enfin une M5, comme le rulebook le spécifiait depuis
le début. L'ambiguïté intra-bougie porte désormais sur 5 minutes au lieu de 15.

## L. L'unité d'exécution portait l'essentiel de la perte mesurée

Hors échantillon (mai–août), à règles **rigoureusement identiques** :

| | base M15 | base M5 |
|---|---|---|
| S1 — trades | 19 | 13 |
| S1 — R moyen | **−0,391** | **−0,178** |
| S3 — trades | 9 | 12 |
| S3 — R moyen | −0,063 | −0,050 |
| **R total** | **−7,99** | **−2,92** |

**La perte diminue de 63 % sans qu'une seule règle change.** Seul le moment de
l'entrée diffère : clôture M15 contre clôture M5. Ce que le backtest M15
mesurait, c'était pour l'essentiel le coût d'entrer trop tard.

C'est la justification rétrospective de R4. Une règle abandonnée « faute de
données » n'est pas neutre : elle a coûté ici 0,21 R par trade sur S1, soit plus
de la moitié de la perte apparente.

**Corollaire de méthode.** Tout backtest exécuté sur une unité plus grossière que
celle du rulebook mesure la stratégie *plus* le coût de l'écart d'exécution, sans
séparer les deux. C'est un biais silencieux et systématiquement défavorable.

## M. Le calibrage passe positif, le test reste négatif

| | trades | réussite | R total |
|---|---|---|---|
| Calibrage (jan–avr) | 21 | 52 % | **+0,22** |
| **Test (mai–août)** | **25** | 48 % | **−2,92** |

Manuel de cas d'école. Si on avait regardé la seule période de calibrage, on
aurait conclu à un système à l'équilibre — et on aurait eu tort. C'est
exactement ce contre quoi la séparation des échantillons protège, et la raison
de ne jamais publier un chiffre in-sample.

## N. Ce qu'on peut dire, et ce qu'on ne peut pas

**On peut dire** que l'unité d'exécution comptait davantage que n'importe lequel
des réglages débattus jusqu'ici.

**On ne peut pas dire** si S1 ou S3 ont un edge. 13 et 12 trades hors
échantillon, contre un seuil de 20 fixé d'avance. Les deux restent négatifs, mais
à −0,18 et −0,05 R par trade sur si peu de tirages, l'intervalle de confiance
couvre largement zéro dans les deux sens.

Le facteur limitant n'est plus la qualité du code ni celle des règles : **c'est
la quantité de données.** 7 mois donnent 25 trades hors échantillon. Il en
faudrait 3 à 4 fois plus.

---

# Cinquième passe — 3 ans de M5, et le verdict (20/08)

239 493 bougies M5, septembre 2023 à août 2026. **Calibrage sur la première
année, test sur les deux suivantes.** La bande de S1 avait été calibrée sur
janvier–avril 2026, devenus période de test une fois l'historique étendu : elle a
donc été recalculée sur la première année. Elle bouge peu — [0,24 ; 0,69] →
[0,25 ; 0,60] — ce qui est en soi rassurant sur sa stabilité.

## O. Deux corrections du détecteur de fermeture, imposées par l'échelle

**Une fermeture se définit par sa durée, pas par une bougie plate.** Le détecteur
retenait toute transition bougie réelle → bougie figée. En M15 cela suffisait ;
en M5 l'amplitude de référence est plus basse, si bien que la moindre accalmie de
milieu de séance produisait une fausse fermeture — un vendredi 05h45 New York,
par exemple. La médiane des écarts passait de 15 minutes à deux heures et
l'assertion refusait des données saines. Seules comptent désormais les plages
figées d'au moins quatre heures : un week-end en dure quarante-huit.

**Un marché fermé se manifeste de deux façons selon le lot.** Le lot sur 7 mois
*comblait* les week-ends avec un prix figé ; celui sur 36 mois les *omet*
purement. Ne chercher que les plages figées ne trouvait que 9 fermetures sur
trois ans. Le détecteur cherche maintenant aussi les trous temporels : 93
fermetures, **écart médian 0:00**.

**Une anomalie réelle localisée au passage.** Entre octobre 2023 et février 2024,
les vendredis s'arrêtent une à deux heures trop tôt. Ailleurs, 57 fermetures sur
58 tombent à 0:00 exactement. Un fuseau erroné décalerait *toutes* les
fermetures : c'est donc une couverture dégradée du fournisseur sur cette
fenêtre-là, pas une erreur d'horodatage.

## P. Le verdict

Hors échantillon, septembre 2024 → août 2026, **188 trades** :

| setup | n | réussite | R moyen | écart-type | t | intervalle 95 % |
|---|---|---|---|---|---|---|
| **S1** | **97** | 52,6 % | **+0,000** | 1,083 | 0,00 | [−0,215 ; +0,216] |
| **S3** | **87** | 57,5 % | **+0,059** | 0,956 | 0,57 | [−0,142 ; +0,260] |
| S2 | 4 | 25 % | −0,545 | 1,061 | −1,03 | [−1,585 ; +0,494] |

Drawdown maximal : **−13,10 R**. Résultat total : **+2,95 R en deux ans**, soit
+1,99 % de capital.

**S1 et S3 dépassent largement le seuil de 20 trades fixé d'avance. On peut donc
enfin conclure — et la conclusion est qu'aucun des trois n'a d'edge démontrable.**

- **S1 est exactement à zéro** sur 97 trades. Ni gagnant ni perdant : il paie ses
  frais et rien de plus.
- **S3 est à +0,059 R, avec t = 0,57.** Il en faudrait 1,96 pour parler d'un
  effet. L'intervalle couvre zéro des deux côtés.
- **S2 n'a jamais produit d'échantillon**, en trois ans.

## Q. Pourquoi l'edge de S3 ne sera jamais prouvable

Pour établir un effet de +0,059 R avec un écart-type de 0,956, il faudrait
**environ 1 000 trades**. S3 en produit 87 en deux ans : cela demanderait
**23 ans de données**.

Un edge trop petit pour être démontré est aussi trop petit pour être tradé — il
disparaît sous le premier écart de slippage réel. Ce n'est pas un problème
d'échantillon insuffisant : c'est la réponse.

## R. Ce que le processus a établi, lui

La démarche a fonctionné, même si les setups ne fonctionnent pas :

- 14 ruptures du rulebook identifiées et corrigées, dont trois qui rendaient un
  setup mathématiquement incapable de se déclencher
- l'unité d'exécution portait 63 % de la perte apparente (§L)
- deux bugs attrapés par les tests, dont un qui vidait le verrou anti-biais
- la période de calibrage ressortait positive quand le test ne l'était pas (§M) :
  sans séparation des échantillons, on aurait conclu à un système viable

**Le rulebook a été réfuté proprement.** C'est ce qu'on lui demandait.

---

# Sixième passe — l'hypothèse de régime (20/08)

Analyse menée sous trois garde-fous posés **avant** toute mesure, parce que
découper 188 trades en trois régimes et retenir le meilleur, c'est de
l'exploration de données déguisée en découverte.

1. **Bornes issues du calibrage seul** — tercils du ratio de volatilité
   (ATR 14 j / ATR 100 j) sur septembre 2023 – août 2024. La période de test ne
   participe pas à leur définition.
2. **Prédictions écrites d'abord, dans le code** (`outils/regimes.py`) : S1
   meilleur en régime agité (une cassure a besoin de répondant), S3 meilleur en
   régime calme (retour à la moyenne, déjà filtré ADX H4 < 20).
3. **Correction de Bonferroni** — 6 comparaisons portent le seuil de |t| ≥ 1,96
   à **|t| ≥ 2,64**. Sans elle, une chance sur quatre de « trouver » un effet
   inexistant.

## S. Un artefact de méthode qui coûtait 27 % de l'échantillon

Découper les données *avant* de construire le contexte fait redémarrer la chauffe
des indicateurs. L'ATR(100) journalier demande cent séances : les cinq premiers
mois de la période de test sortaient donc sans régime, et 26 des 97 trades de S1
disparaissaient de l'analyse — sur un détail d'implémentation, pas sur une
propriété du marché.

Le contexte se construit désormais sur l'historique complet, les trades sont
filtrés ensuite. **Ce n'est pas un regard vers le futur** : chaque valeur reste
calculée à partir des seules bougies qui la précèdent. On élargit la chauffe, on
ne remonte pas le temps.

## T. Résultat par régime — rien de significatif, mais un ordre cohérent

| setup | calme | normal | agité |
|---|---|---|---|
| **S1** | −0,098 | −0,112 | **+0,264** |
| **S3** | **+0,103** | +0,064 | −0,015 |

Aucune cellule n'atteint |t| ≥ 2,64 (maximum observé : 1,12). **Mais les deux
prédictions sont vérifiées dans leur direction** : S1 croît avec la volatilité,
S3 décroît. Ce n'est pas du bruit dispersé, c'est un ordre monotone conforme à
la nature de chaque setup.

## U. Test de tendance — la bonne statistique pour une hypothèse d'ordre

Découper en trois jette l'information de rang et divise l'échantillon. Une
hypothèse d'**ordre** se teste par une pente sur tous les trades : deux tests
seulement, donc seuil à |t| ≥ 2,24.

| setup | n | corrélation | t | sens attendu | verdict |
|---|---|---|---|---|---|
| **S1** | 99 | **+0,150** | 1,50 | croissante | bon sens, non significatif |
| **S3** | 87 | **−0,141** | −1,31 | décroissante | bon sens, non significatif |

## V. Pourquoi ce résultat vaut mieux que le précédent

L'edge global de S3 demandait **~1 000 trades, soit 23 ans** pour être prouvé —
autant dire jamais.

L'effet de régime demande **~224 trades pour S1 (≈ 5 ans)** et **~255 pour S3
(≈ 6 ans)**. C'est le premier résultat du projet à la fois **soutenu
directionnellement** et **testable dans un horizon atteignable**.

Ce qu'on ne peut pas faire : conclure. Deux setups pointant du bon côté, c'est
deux tirages — le pile ou face a une chance sur quatre d'en faire autant. Ce qui
plaide au-delà du hasard, c'est que les effets ont la taille et le sens que la
théorie prédisait, pas seulement le bon signe.

Ce qu'on peut faire : **poser cette hypothèse comme la prochaine à tester**, sur
des données neuves. Pas la retoucher, pas l'affiner sur ces 188 trades — la
tester ailleurs.
