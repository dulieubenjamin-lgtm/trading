# Papier live sur XAU — protocole

**Pré-enregistré le 25/08/2026, à zéro trade compté.**
Empreinte de la spécification testée : `11d8e566a7b5baad`
(`specs/papier-live.json` — le script de veille la vérifie à chaque passage).

---

## 1. Ce que « papier live » veut dire, et pourquoi c'est la seule option

Un backtest mesure une figure sur des bougies que la recherche a **déjà vues**.
Cette session a comparé environ 137 objets. Le meilleur d'entre eux est flatteur
par construction : sur 137 tirages sous l'hypothèse nulle, le maximum attendu se
situe vers |z| ≈ 3,1 — et notre meilleur résultat est à +2,45. **Il est
exactement là où le pur hasard le mettrait.**

Ce n'est pas un jugement sur la figure. C'est une limite arithmétique : aucune
manipulation des 274 trades existants ne peut trancher, parce que ce sont eux qui
ont servi à choisir la figure. Découper autrement, changer d'angle, ajouter un
témoin — tout cela remesure le même échantillon et donne des résultats cohérents
entre eux, ce qui ressemble à de l'accumulation de preuve et n'en est pas (§KK).

**Papier live = mesurer la figure sur des bougies qui n'existaient pas au moment
du choix.** Aucune sélection ne peut les contaminer, puisqu'elles n'étaient pas
là. C'est la définition la plus stricte de « données neuves », et la seule qui
vaille ici.

« Papier » : aucune position réelle, aucun argent. Ce qui est testé n'est pas ta
capacité d'exécution mais une spécification gelée.

---

## 2. La routine, deux commandes

```bash
python3 outils/telecharger.py --symbole XAU/USD --intervalle 5min --incremental
python3 outils/veille.py
```

La première ne tire que les bougies postérieures au cache : une requête au lieu
de soixante-dix-huit. La seconde vérifie l'empreinte, cherche un signal sur les
36 dernières bougies (3 h), et journalise le passage **qu'il y ait signal ou
non**.

Deux à trois passages par jour suffisent — la fenêtre de 3 h les couvre sans
trou. Un passage manqué n'est pas grave ; un passage manqué **non journalisé**
l'est, parce qu'alors rien ne distingue « pas de signal » de « pas regardé ».

### Le registre, et pourquoi il a trois statuts

`veilles.csv` enregistre chaque passage avec l'empreinte de la spécification
surveillée ce jour-là. La colonne `statut` vaut :

| statut | sens | code de sortie |
|---|---|---|
| `ok` | le cache atteint le présent, le passage couvre les 3 dernières heures | 0 |
| `ferme` | marché fermé, le cache s'arrête normalement à la clôture | 0 |
| `perime` | le cache est plus vieux que la fenêtre d'examen : **le passage ne couvre rien** | 3 |

Un passage `perime` n'a pas de compte de signaux — la case reste vide. C'est
délibéré : si un cache périmé produisait « 0 signal », le registre se remplirait
de lignes qui ressemblent à de la surveillance et sont en fait de l'aveuglement,
et la journalisation ne protègerait plus de rien. **Rafraîchir puis relancer.**

**Le comptage démarre au premier passage `ok`.** Les passages `perime` sont
conservés — ils font partie de l'historique honnête du protocole — mais ne
comptent ni comme couverture ni comme absence de signal.

### Une seule machine écrit dans le registre

`veilles.csv` n'est alimenté que par **la machine d'exploitation**, celle depuis
laquelle tu surveilles réellement. Un lancement de `veille.py` ailleurs — dans un
conteneur de développement, pour vérifier que l'outil marche — est un test
d'outil, pas une veille : il ne s'inscrit pas au registre.

Deux raisons, et la seconde est la vraie. La première est mécanique : un CSV en
ajout écrit depuis deux endroits produit un conflit git à chaque `pull`, et
résoudre un conflit à la main dans le registre d'un protocole anti-biais est
précisément ce qu'on ne veut jamais avoir à faire. La seconde est de fond : le
registre existe pour prouver que les jours sans signal ont été **surveillés**.
Une ligne écrite par une machine qui ne surveille rien ne prouve rien, et
affaiblit toutes les autres en diluant ce que « veille » veut dire.

Pour tester l'outil sans toucher au registre : `python3 outils/veille.py --essai`.

### Quand il y a un signal

Le script écrit `journal/papier-live/AAAA-MM-JJTHHMM.plan.md` avec entrée, stop,
objectif 2R et taille. **Ce fichier se commite immédiatement, avant de connaître
l'issue.** C'est le verrou anti-biais posé au premier jour du projet : un plan
écrit après coup n'est pas un plan, c'est un souvenir.

```bash
git add journal/papier-live/*.plan.md && git commit -m "plan: <horodatage>" && git push
```

### Quand le trade est terminé

Ajouter un fichier `<horodatage>.issue.md` séparé — stop touché, objectif touché,
ou sortie de séance — et le commiter. Deux fichiers, deux commits, deux dates :
l'historique git prouve que le plan précède l'issue.

### Voir où on en est

```bash
python3 outils/journal.py           # au terminal
python3 outils/journal.py --html    # page à ouvrir dans le navigateur
```

Le journal montre **tout** : chaque trade, le R moyen courant, la discipline de
veille, et un audit git vérifiant que chaque plan a bien été commité avant la
sortie de son trade.

Rien n'est masqué, délibérément. Cacher le résultat jusqu'à l'échéance serait à
la fois condescendant et inefficace — additionner dix nombres visibles ne demande
aucun effort. Ce qui protège réellement d'une lecture prématurée est le
**contexte** : à n = 12 l'intervalle de confiance couvre à peu près tout ce qui
est concevable, et affiché à côté de la moyenne il rend la sur-interprétation
difficile plutôt qu'interdite. La discipline vient de la règle d'arrêt écrite
d'avance, pas d'une donnée dissimulée.

### Seuls les signaux détectés en direct comptent

Un signal retrouvé en rejouant l'historique **n'entre pas** dans l'échantillon,
même s'il tombe après la date de gel et qu'il est donc formellement hors
échantillon.

La raison n'est pas statistique, elle est procédurale. Autoriser le rejeu rend la
frontière entre « live » et « reconstitué » négociable, et c'est dans cette
négociation que le biais entre : rien n'empêcherait plus, dans deux ans, de
rattraper les quinze jours où la veille n'a pas tourné — en ayant vu entre-temps
comment le marché s'est comporté. Une règle qu'on peut assouplir au cas par cas
n'est pas une règle.

`--essai` sert à vérifier l'outil sur un signal historique. Ce qu'il produit
porte l'extension `.essai.md` et n'est jamais compté.

---

## 3. Ce qui est gelé, et ce que « gelé » interdit

```
figure     tête-épaules inversée M15, largeur 3, tolérance 0,9,
           écart_max 80, saillie_min 0,5
filtre     clôture > EMA50 H4
entrée     croisement du signal, clôture M5
stop       extrême récent, n = 12
objectif   2R
séance     01h–22h Europe/Paris, à plat à 22 h
plafond    2 trades par jour
```

**Aucun ajustement. Aucun.** Ni le stop, ni l'objectif, ni la taille, ni
« celui-là je le sens pas ». Tout écart rend le trade inutilisable pour le
comptage, et un échantillon où l'on a retiré les perdants ne mesure plus rien.

Si tu veux changer quelque chose : c'est légitime, mais ça repart de zéro trade.
Le script le fait respecter — il vérifie l'empreinte et refuse de compter la
suite avec ce qui précède.

**Les signaux non pris comptent quand même.** Un signal survenu pendant que tu
étais en réunion entre dans l'échantillon avec l'issue qu'il a eue. C'est le
point de discipline le plus facile à laisser filer et le plus destructeur : ne
garder que les trades observés, c'est ne garder que ceux dont on se souvient.

---

## 4. Combien de temps — le chiffre honnête

Sur les 36 mois d'historique, la spécification gelée déclenche **61,6 trades par
an** avec la contrainte de séance.

| trades | durée | puissance à t > 2 | à t > 2,5 |
|---|---|---|---|
| 50 | 10 mois | 24 % | 11 % |
| 100 | 1,6 an | 43 % | 25 % |
| 200 | 3,2 ans | 72 % | 53 % |
| 250 | 4,1 ans | 81 % | 65 % |
| 300 | 4,9 ans | 88 % | 75 % |

La puissance est la probabilité de **détecter l'effet s'il est réel à la taille
mesurée** (+0,232 R, écart-type 1,27).

Il faut le dire franchement : **200 trades ne suffisent pas à démontrer un effet
de cette taille.** Même s'il est parfaitement réel, il y a plus d'une chance sur
quatre de ne pas le voir. Pour 80 % de puissance il faut ~242 trades (3,9 ans) à
t > 2, et ~335 (5,4 ans) à t > 2,5.

Ton intuition de départ — « 200 ou 300 trades » — était bien calibrée. C'est le
bon ordre de grandeur. Ce que les chiffres ajoutent, c'est que la borne haute de
ton intervalle est la vraie borne, pas la basse.

---

## 5. Règles d'arrêt, fixées maintenant

Sans elles, on regarde la courbe monter et descendre pendant quatre ans en
décidant après coup quand s'arrêter — ce qui annule tout le bénéfice du
pré-enregistrement.

| palier | condition | décision | risque de tuer un effet réel |
|---|---|---|---|
| n = 50 | R moyen ≤ −0,20 | **arrêt, hypothèse morte** | 0,8 % |
| n = 100 | R moyen ≤ 0 | **arrêt, hypothèse morte** | 3,4 % |
| n = 250 | t > 2 | **hypothèse soutenue** | — |
| n = 250 | t ≤ 2 | **non concluant**, arrêt quand même | — |

Aucune lecture intermédiaire ne déclenche autre chose. En particulier : un
résultat *bon* à n = 50 ou n = 100 **ne conclut rien** et n'autorise ni à
augmenter la taille, ni à passer en réel, ni à s'arrêter là. Les bornes précoces
ne servent qu'à abandonner tôt, jamais à valider tôt.

« Non concluant » à n = 250 est un vrai verdict, et le plus probable. Il signifie :
l'effet est trop petit pour être établi avec cet instrument, il faut autre chose
(le carnet d'ordres, mentionné en fin de pré-enregistrement) ou rien.

---

## 6. Le pronostic, écrit d'avance

**Le résultat attendu est négatif.**

z = +2,45 après ~137 tests est exactement ce que produit la sélection pure. La
figure ne transfère ni à EUR/USD, ni à XAG, ni à BTC. Toutes ses mesures portent
sur les mêmes 274 trades et se répètent au lieu de se confirmer.

Un protocole dont on attend une confirmation n'est pas un test, c'est une
cérémonie. Celui-ci a une utilité précise et suffisante : **fermer la question**.
Dans dix mois, une moyenne à −0,20 R sur 50 trades classe l'affaire pour de bon,
et c'est un bon retour sur dix mois de deux commandes par jour.

Si la figure survit à 250 trades neufs, ce sera le premier résultat de ce projet
qu'aucune objection méthodologique connue n'atteint. C'est peu probable. C'est
précisément pour ça que ça vaudrait quelque chose.
