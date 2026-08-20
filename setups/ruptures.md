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

---

# Septième passe — le test croisé sur BTC réfute l'hypothèse de régime (20/08)

311 017 bougies BTC/USD M5, mêmes trois ans, même découpage calibrage/test,
mêmes prédictions pré-enregistrées.

## W. Deux adaptations obligatoires — et un piège évité de peu

**Le harnais supposait un marché qui ferme.** Trois mécanismes en dépendaient, et
les appliquer à BTC aurait produit un résultat faux sans lever d'erreur : le
filtre calendrier aurait jeté ~29 % de vraies bougies, la journée forex bornée à
17h New York n'a pas de sens en continu, et l'assertion de fuseau cherche une
clôture hebdomadaire inexistante — remplacée par un contrôle de continuité
(couverture 100 %, 2 trous, le plus grand de 55 minutes).

**Le seuil de dégénérescence dépend du marché.** Le filtre d'amplitude, calibré
pour attraper le remplissage synthétique du forex, rejetait **11 562 bougies BTC
d'amplitude médiane 8 $** sur un actif à ~68 000 $ — des bougies *calmes mais
réelles*, concentrées entre 4h et 7h UTC. On aurait supprimé la nuit asiatique,
c'est-à-dire **précisément le régime calme qu'on cherchait à mesurer**. En
continu, seule une bougie strictement plate compte comme défaut de flux : 52 sur
311 017.

C'est le piège le plus vicieux rencontré dans ce projet : un filtre légitime sur
un marché, qui détruit la mesure sur un autre, en biaisant exactement la variable
étudiée.

## X. Une validation inattendue au passage

La bande d'amplitude de S1, calibrée indépendamment sur chaque instrument :

| | médiane du ratio | bande | éligibilité |
|---|---|---|---|
| XAU/USD | 0,317 | [0,25 ; 0,60] | 65 % |
| BTC/USD | 0,313 | [0,22 ; 0,67] | 65 % |

Le range asiatique vaut ~0,31 × ATR journalier sur deux marchés sans rapport.
**C'est une propriété structurelle des marchés**, pas une particularité de l'or —
et la seule régularité solide que ce projet ait établie.

## Y. Le verdict : les deux prédictions s'inversent

| | XAU/USD | BTC/USD |
|---|---|---|
| **S1** — corrélation volatilité/R | **+0,150** (t = 1,50) | **−0,058** (t = −0,60) |
| **S3** — corrélation volatilité/R | **−0,141** (t = −1,31) | **+0,089** (t = +1,04) |

**Les deux signes s'inversent.** Aucun n'est significatif nulle part : quatre
mesures, tous les |t| sous 1,5, signes dispersés. C'est le portrait du bruit.

### Pourquoi la défense « effet spécifique aux marchés à séances » ne tient pas

C'était la lecture alternative annoncée avant le test : l'effet pourrait être réel
mais propre aux marchés à séances, BTC n'ayant pas de session asiatique au sens
où l'or en a une.

Elle ne résiste pas à S3. **La mécanique de S3 ne dépend d'aucune séance** — un
niveau H4 établi, une divergence MACD M15, un filtre ADX. Rien là-dedans n'a
besoin de Londres ou de Tokyo. Si son effet de régime était structurel, il
devrait survivre au changement d'instrument. Il s'inverse.

L'explication la plus économique est donc la bonne : **le résultat sur l'or était
du bruit.**

## Z. Ce que ce test a fait gagner

L'hypothèse de régime demandait 5 à 6 ans de données supplémentaires pour être
tranchée sur l'or seul. Le test croisé l'a réfutée pour **un téléchargement et
deux minutes de calcul**.

C'est la leçon méthodologique de tout le projet : face à un effet non
significatif, **changer de terrain coûte infiniment moins cher qu'attendre plus
de données**. Et un effet qui ne survit pas au changement d'instrument n'aurait
de toute façon pas survécu au marché.

---

# Huitième passe — recherche systématique de setups (20/08)

63 spécifications testées sur XAU : 51 proposées par huit familles d'agents
indépendants, 12 de référence. Objectif : 2R, 1 à 2 trades/jour, 3 indicateurs
maximum, et l'exigence de pouvoir accumuler 200+ trades pour faire ses preuves.

## AA. Le spread est le coût dominant, et il dépend du stop

60 setups à entrée **pseudo-aléatoire**, même structure, donnent la distribution
empirique du « aucun edge ». Ils sont tous négatifs :

| stop | R moyen (hasard) | spread / risque |
|---|---|---|
| 0,8 × ATR | −0,265 | 21,6 % |
| 1,5 × ATR | −0,157 | 11,5 % |
| 3,0 × ATR | −0,076 | 5,8 % |

Un stop à 1,5 × ATR M15 **offre 11,5 % du risque au spread à chaque trade**.
Pour dégager +0,20 R net, un setup doit produire +0,36 R bruts. Cette marche
compte davantage que le choix des indicateurs.

Piège associé : la réussite qui monte à 39-41 % sur les stops larges vient des
**sorties forcées à 12 h**, qui se répartissent près de l'entrée. Le taux de
réussite n'est pas comparable d'une largeur de stop à l'autre.

## BB. Le piège de la dérive — deux faux gagnants évités

Premier passage avec un témoin mélangeant achats et ventes : deux candidats
ressortaient à **+3,70 et +3,17 écarts-types**. De quoi conclure à une trouvaille.

Mesure de contrôle : l'écart entre entrées longues et courtes **purement
aléatoires** vaut **+0,107 R** (année 1) et **+0,128 R** (année 2). C'est la
hausse de l'or, +29 % puis +38 %.

Un témoin mixte **crédite donc à tout setup acheteur la tendance du marché comme
si c'était son edge** — environ 1,2 écart-type offert. Recalculés contre un
témoin du même sens et de la même fenêtre, les deux « gagnants » retombent à
+1,2 et +0,9, et ne passent plus la fenêtre de recherche.

**Zéro survivant sur 63 spécifications et 79 tests.**

## CC. Les candidats font PIRE que le hasard

Avec un témoin stabilisé (320 tirages, moyenne −0,071, écart-type 0,107) :

| | observé | attendu par pur hasard |
|---|---|---|
| candidats avec z > 0 | **29 %** | 50 % |
| candidats avec z > 1 | **4 %** | 16 % |
| z médian | **−0,62** | 0,00 |

Ce n'est pas une absence d'edge, c'est un edge négatif.

## DD. Le mécanisme : ils voient juste, ils entrent trop tôt

Excursion sur les 12 h suivant le signal, en multiples d'ATR :

| origine des entrées | favorable | adverse | ratio |
|---|---|---|---|
| hasard | 3,38 | 2,88 | **1,17** |
| Rejet de Keltner | 4,00 | 3,09 | **1,29** |
| RSI survente | 3,28 | 2,58 | **1,27** |
| Cassure Donchian | 3,78 | 2,97 | **1,27** |

**Les setups lisent la direction MIEUX que le hasard.** Mais le backtest compte
la *première* touche : le contre-mouvement arrive avant le mouvement favorable et
prend le stop. L'échec est dans le **timing d'entrée**, pas dans la lecture.

## EE. Corriger le timing n'y change rien — et la façon dont ça échoue compte

Entrée différée jusqu'à un repli de X × ATR contre le signal :

| repli | z médian | z > 1 | meilleur z |
|---|---|---|---|
| 0 | −0,60 | 2 % | +1,34 |
| 0,3 × ATR | −0,72 | 20 % | +2,66 |
| 1,0 × ATR | −0,77 | 26 % | +2,66 |

Le **meilleur** résultat double, la **médiane** ne bouge pas. Signature de la
variance ajoutée, pas de l'edge : moins de trades par candidat, queues plus
grasses des deux côtés. **Un réglage qui améliore le maximum sans déplacer la
médiane n'a rien amélioré du tout** — c'est exactement ainsi qu'on fabrique un
système surajusté en croyant l'optimiser.

## FF. Ce qu'il faut retenir de cette recherche

Le contre-mouvement adverse n'est pas un défaut d'exécution à corriger : c'est
**le prix du signal**. L'information portée par un indicateur est déjà dans le
prix au moment où il la donne ; ce qui reste à parcourir ne couvre ni le spread
ni le risque assumé.

Trois protections ont chacune renversé une conclusion :
- le **témoin aléatoire** a déplacé le point de comparaison de 0 à −0,157 R
- l'**appariement par sens** a supprimé deux faux gagnants à +3,7 et +3,2
- le **suivi de la médiane** plutôt que du maximum a démasqué la fausse
  amélioration de l'entrée en repli

Aucune n'est optionnelle. Sans elles, cette recherche aurait produit un système
d'apparence excellente, et faux.

## GG. L'objectif : 1R est PIRE que 2R, et le taux de réussite est un piège

Test de six objectifs sur la population entière, témoin apparié par sens **et**
par objectif.

| objectif | R moyen du témoin | réussite du témoin | z médian des candidats | candidats z > 0 |
|---|---|---|---|---|
| 0,50 R | −0,113 | **62,6 %** | **−1,31** | 11 % |
| 0,75 R | −0,121 | 53,2 % | −1,04 | 17 % |
| 1,00 R | −0,121 | 46,7 % | **−0,79** | 16 % |
| 1,50 R | −0,120 | 38,6 % | −0,71 | 23 % |
| 2,00 R | −0,125 | 33,6 % | **−0,65** | 26 % |
| 3,00 R | −0,086 | 29,9 % | −0,67 | **29 %** |

**Resserrer l'objectif dégrade la performance relative, de façon monotone.**
Passer de 2R à 1R fait tomber le z médian de −0,65 à −0,79, et la proportion de
candidats battant le hasard de 26 % à 16 %.

### Pourquoi

L'information portée par les indicateurs vit dans **la queue du mouvement**, pas
près de l'entrée. La mesure d'excursion (§DD) le montrait déjà : excursion
favorable de 4,0 ATR contre 3,1 adverse. Resserrer l'objectif monétise la partie
de la distribution où ils n'ont aucun avantage, tout en continuant d'encaisser
des stops entiers. On coupe les gains et on garde les pertes.

### Le taux de réussite est achetable, et il ne vaut rien

Le témoin **purement aléatoire** affiche **62,6 % de réussite à 0,5R** — pour
−0,113 R par trade. Un système à 62 % de réussite qui perd de l'argent, produit
par des entrées au hasard.

C'est la réponse définitive à l'objectif « 55-60 % de réussite » : ce taux
s'obtient à volonté en resserrant l'objectif, et c'est précisément le réglage où
l'espérance est la pire. **Le taux de réussite ne mesure rien** tant qu'on ne
donne pas le ratio gain/perte avec — et une fois qu'on le donne, il n'apporte
plus d'information que l'espérance ne contienne déjà.

Si une direction existe, c'est donc vers des objectifs **plus larges**, pas plus
serrés. La tendance est monotone jusqu'à 3R (29 % de candidats au-dessus du
hasard) — mais elle n'atteint jamais la parité de 50 %.

---

# Neuvième passe — les figures chartistes (20/08)

## HH. Une classe d'hypothèses entièrement absente des tests précédents

Tout ce qui avait été testé jusqu'ici était **indicateur** : une fonction qui
compresse une fenêtre de prix en un nombre. Deux trajectoires très différentes
donnent le même RSI. Une **figure** est une relation géométrique entre des pivots
précis — exactement l'information que les indicateurs jettent.

Huit figures implémentées mécaniquement, chaque tolérance étant un paramètre
explicite : double creux/sommet, drapeaux, triangles, épaule-tête-épaule et son
inverse. Signalées à la confirmation du dernier pivot, jamais au moment où l'œil
les voit sur un graphique fini.

**Réglage des paramètres sur la fréquence seule**, en ne regardant que les
comptages de signaux et jamais les résultats. C'est la seule forme d'ajustement
admissible : elle porte sur une contrainte déclarée d'avance.

## II. Le premier résultat qui franchit le seuil

Cumul sur les trois fenêtres XAU, témoin apparié par sens et par type de stop :

| figure | n | réussite | R moyen | t | concentration |
|---|---|---|---|---|---|
| **tête-épaules inversé + filtre H4** | 191 | 53,9 % | **+0,384** | **+4,00** | 24 % |
| tête-épaules inversé | 277 | 50,2 % | +0,275 | +3,44 | 34 % |
| double creux | 381 | 41,7 % | +0,068 | +1,04 | **145 %** |
| double sommet | 345 | 35,7 % | −0,081 | −1,21 | — |

Seuil de Bonferroni sur les ~121 tests de la session : **|t| ≥ 3,53**. La
tête-épaules inversée filtrée le franchit — la seule chose de toute cette
recherche à y parvenir.

**La concentration est le contrôle décisif.** Elle mesure la part du résultat
portée par les 5 % de meilleurs trades. À 24 %, la tête-épaules inversée est
portée par l'ensemble de sa distribution. Le double creux affiche **145 %** :
sans ses meilleurs trades il est négatif, donc son +0,068 R n'est qu'une poignée
de coups déguisée en système. Sans cette mesure, les deux se seraient ressemblés.

Positif dans les **trois** fenêtres XAU indépendamment : +0,296 (recherche),
+0,203 (validation), +0,334 (holdout, jamais vu avant cet instant).

## JJ. Mais BTC contredit

| figure | XAU (3 ans) | BTC (3 ans) |
|---|---|---|
| tête-épaules inversé | **+0,275** (n=277) | **−0,077** (n=448) |
| tête-épaules inv. + filtre | **+0,384** (n=191) | **−0,112** (n=262) |
| double creux | +0,068 | −0,087 |
| double sommet | −0,081 | −0,042 |

Sur BTC, les cinq figures battent leur témoin (z > 0) mais restent **absolument
négatives**. Battre un témoin qui perd −0,14 R en perdant −0,08 R n'est pas
gagner de l'argent.

C'est exactement le test qui a tué l'hypothèse de régime (§Y), et il refuse de
valider celle-ci.

## KK. Deux lectures, et comment les départager

**Lecture 1 — spécifique à l'or.** Les figures chartistes sont massivement
suivies sur les marchés à forte présence technique. Si beaucoup d'acteurs tradent
la même figure au même endroit, elle devient partiellement auto-réalisatrice. La
base de participants de BTC est différente. Cette lecture est **testable** : la
figure devrait alors marcher aussi sur d'autres instruments très chartés —
EUR/USD, indices, argent — et échouer sur les marchés jeunes ou peu techniques.

**Lecture 2 — l'or a eu de la chance.** 191 trades restent peu, la sélection des
cinq figures s'est faite après avoir vu deux fenêtres, et sur ~121 tests un t de
4,00 reste atteignable par sélection.

**Rien dans les données actuelles ne départage ces deux lectures.** Un seul test
le ferait : la même figure, sans aucun réglage, sur trois ou quatre instruments
supplémentaires. Coût : un téléchargement et un run. C'est exactement le protocole
qui a réfuté l'hypothèse de régime en deux minutes après cinq ans d'attente
annoncés.
