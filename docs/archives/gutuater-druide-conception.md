# Gutuater et le Druide : conception

Décidé le 24/11/2026, et corrigé par le créateur le même jour. Vercintorix reçoit deux agents en plus du vergobret. **Les trois peuvent s'écrire en vtx** ; Gutuater l'est déjà depuis la 0.825.

| Agent | Quand il agit | Son rôle |
|---|---|---|
| **Vergobret** (existe) | à l'exécution | mesurer et choisir : la carte ou le processeur, combien de fils, les lots, **et taire les bits** (32 ou 64 sur la carte, le 64 d'abord) |
| **Gutuater** (nouveau) | à la forge, du côté du code machine | **la forge** (quelles variantes s'expriment) et **la garde** (les deux compilateurs, les variantes fidèles) ; d'autres tâches, hors du graphique, viendront |
| **Le Druide** (nouveau) | à l'écriture, dans l'atelier | **les conseils** au programmeur, **les potions** (il les prépare et surtout les corrige) et **la bibliothèque** |

Ces agents sont des programmes déterministes et lisibles, pas une IA. Toutes leurs décisions se retrouvent dans leurs carnets.

Gutuater n'écrit pas lui-même de code machine : il choisit entre des variantes que la forge sait déjà produire. Le travail d'autonomie bloqué (Gobannos, les appels au système) reste hors de son périmètre.

---

## 1. Les principes communs

### L'ADN, l'ARN et l'épigénétique
- **L'ADN, c'est le programme.** Il ne change jamais. La règle des mêmes mots reste absolue : `vtx.py` et `vtxc` produisent des mots identiques, avec ou sans agents.
- **L'épigénétique, c'est le carnet de Gutuater.** Ses marques ne modifient pas l'ADN, elles choisissent quels gènes s'expriment, c'est-à-dire quelle variante produit la forge native : fondu ou séparé, en lot ou non, quel épissage.
- **La méthylation, c'est taire un gène.** Un gène réduit au silence n'est plus exprimé. Taire les bits (32 ou 64 sur la carte) revient au vergobret.
- **L'ARN, c'est la transcription pour une machine et une scène.** Il y en a deux : le plan de forge, écrit par Gutuater, et le plan par image, lu par le vergobret (quels étages, lesquels sauter).
- **Les codons sont quaternaires.** Les plans s'écrivent avec les quatre valeurs du noyau (inconnu, faux, vrai, variable). C'est une notation compacte et naturelle pour le cube, pas une source de vitesse en soi.

### La synapse quaternaire (logique de Belnap)
Chaque connaissance porte deux compteurs : les preuves pour et les preuves contre.

| État | Quand | Action |
|---|---|---|
| **inconnu** | moins de 3 (en poids) de chaque côté | il demande une mesure |
| **vrai** | pour ≥ 3 (en poids) et pour ≥ 3 × contre | il exprime le gène |
| **faux** | contre ≥ 3 (en poids) et contre ≥ 3 × pour ; ou une infidélité (64 contre, pour toujours) | il tait le gène |
| **variable** | des preuves des deux côtés, sans que l'un l'emporte | les preuves se contredisent : le vergobret mesure et choisit à l'exécution |

- **Le seuil qui tremble (0.826).** Un seuil fixe (5 % en 0.825) jetait pour toujours un vrai petit gain. Le seuil d'une petite preuve est maintenant tiré au hasard entre 0,1 et 10 % : c'est la résonance stochastique (Gammaitoni et al., *Rev. Mod. Phys.* 70, 223, 1998) et l'arrondi stochastique (Croci et al., *R. Soc. Open Sci.* 9, 211631, 2022). Une petite preuve pèse 1, une preuve forte (plus de 10 %) pèse 3 ; il faut un poids de 3 d'un côté pour croire. La graine vient des mesures elles-mêmes : la même entrée donne la même décision.
- **L'usure.** Au-delà d'un poids de 24, les deux compteurs sont divisés par 2 (jamais une infidélité), pour qu'une machine ou une scène nouvelle puisse renverser une vieille croyance.
- **Une contradiction ne se moyenne pas** : elle devient variable, et cette contradiction est elle-même une information.
- **Plus tard, un apprentissage hebbien.** Un trait du code (une division par une constante, une boucle pure, un étage court, un accès au même indice…) qui revient avec un gain renforcera la synapse « trait → gène ».

---

## 2. Gutuater

### 2.1 La forge
Il lit le programme forgé et repère les traits du code : les boucles pures, les itérations indépendantes, les accès au même indice, les divisions par une constante, les fréquences réservées à la carte, les boucles qui peuvent former un lot.

**Les gènes** sont les variantes que la forge sait produire. Leurs conditions de légalité sont vérifiées par le code, elles ne s'apprennent pas :

| Gène | Variante | Légal si |
|---|---|---|
| `lot` | les boucles de la carte en un seul envoi | (0.824 ; gène de Gutuater depuis la 0.825) |
| `fondre` | les boucles d'un lot, sur le même intervalle → un seul noyau (0.826) | chaque écriture à une fréquence connue (forge) ; dans ces fréquences, un fil ne touche que sa case (la garde, sur la carte) |
| `tableau_mort` | un intermédiaire qui n'est plus lu ailleurs reste dans les registres | `fondre` est exprimé, et la fréquence n'est lue nulle part ailleurs |
| `epissage` | rapide ou par pages | (existe) |

**Le premier test mesurable** : sur Gergovie, les étages séparés perdent contre le noyau unique (0.824 : 42,6 contre 55,2 images par seconde). Gutuater doit apprendre `fondre` sur les étages qui s'y prêtent ; le gain se vérifie avec la même empreinte.

### 2.2 La garde
- **Les mêmes mots.** Il compare automatiquement `vtx.py` et `vtxc` (ce que fait aujourd'hui `outils/memes_mots128.py`) et signale toute divergence, avec la fonction et le mot concernés.
- **Des variantes fidèles.** Avant d'exprimer un gène, il vérifie, sur un essai réduit, que la variante donne la même empreinte que la forme de référence. Une variante infidèle reçoit une preuve contre définitive, et son gène est tu.
- **Une forge universelle.** Sans carnet, ou avec `VTX_GUTUATER=0`, la forge redevient identique sur toutes les machines.

### 2.3 Le dialogue avec le vergobret (0.825)
Ils se parlent par trois fichiers texte lisibles, posés à côté du programme forgé, propres à la machine :

| Fichier | Écrit par | Contenu |
|---|---|---|
| `gutuater.mesures` | le vergobret | `mesure GENE LIEU A B` : deux temps en microsecondes, la variante exprimée puis la variante tue |
| `gutuater.carnet` | Gutuater | `gene GENE LIEU POUR CONTRE ETAT` : ses synapses |
| `gutuater.arn` | Gutuater | `GENE LIEU ETAT` : le plan que lit le vergobret |

- **Gutuater → Vergobret** : l'ARN. Vrai, le vergobret exprime le gène sans le mesurer ; faux, il le tait sans le mesurer ; inconnu ou variable, il mesure.
- **Vergobret → Gutuater** : les mesures. Pour le lot, il fait un passage pour chauffer, puis sans, avec, sans, avec, et garde le meilleur temps de chaque variante. Chaque mesure renforce ou contredit une synapse, puis elle est effacée : elle ne compte qu'une fois.
- **Le lieu** d'un lot est la ligne de sa première boucle, que la forge transmet.
- **Plus tard, des garanties** de Gutuater : « cette boucle a un travail inégal selon la scène » (le vergobret cesse alors de la juger au temps), « ces deux étages peuvent fondre ».

---

## 3. Le Druide

Il est **écrit en vtx** et réutilise l'analyseur de `vtxc`, qui existe déjà en vtx : le langage s'outille lui-même.

### 3.1 Les conseils (dans l'atelier)
Chaque conseil porte son état quaternaire : sûr (vrai), à vérifier (inconnu), ou dépendant du cas (variable). Par exemple :
- « ce `selon` n'a pas de branche `inconnu` » ;
- « cette division serait plus rapide par une constante » ;
- « cette boucle ne peut pas aller sur la carte : `&&` autour d'un appel » ;
- « la variable `ou` est un mot-clé ».

Quand Gutuater a appris quelque chose qui concerne le programmeur, le Druide le lui dit en citant le carnet.

### 3.2 Les potions
Le Druide **prépare les potions et surtout les corrige**. Il propose le code corrigé, ou une fonction prête à l'emploi, montré à côté de l'original, avec sa raison et son état quaternaire. Le programmeur l'accepte d'un geste, ou non : rien ne change dans son programme sans lui. Une potion passe d'abord la garde de Gutuater : les mêmes mots, et la même empreinte quand elle ne doit rien changer d'autre.

### 3.3 La bibliothèque
- le code mort, les fonctions en double, les imports inutiles ;
- l'index de la bibliothèque : qui définit quoi, qui l'utilise.

---

## 4. L'ordre de travail

1. **Gutuater, le socle (fait, 0.825).** `gutuater/gutuater.vtx` et `gutuater/synapse.vtx`, en vtx : le carnet, les synapses, l'ARN. Le premier gène est `lot`, déjà connu, pour vérifier la machinerie sur ce qu'on sait. Le vergobret lit l'ARN, mesure ce qui est inconnu ou variable, et écrit ses mesures. Se coupe avec `VTX_GUTUATER=0`. Test : `tests/test_gutuater.py`.
2. **Gutuater, le gène `fondre` (fait, 0.826)**, avec sa garde : dans ce que le lot écrit, un fil ne touche que sa case, vérifié sur la carte à chaque accès ; une trahison arrête la machine et tait le gène pour toujours. Test : `tests/test_fondre.py`. Reste à lire la RTX : les étages fondus rattrapent-ils le noyau unique ?
3. **La garde des mêmes mots**, automatique.
4. **Le Druide, conseils et potions**, d'abord dans la console, puis dans l'atelier.
5. **Le Druide, la bibliothèque.**
6. **Le vergobret en vtx.**

Restent en attente : le cache qui affiche directement (swapchain Vulkan, par `fenetre.rs`) et les duels à armes égales.

## 5. Les garde-fous
- Les mêmes mots, toujours : les agents ne touchent pas au sens du programme.
- Déterministes et lisibles : chaque décision se retrouve dans le carnet.
- Le carnet est local et peut être coupé : sans lui, la forge reste universelle.
- Chaque étape a sa mesure : pas de biologie sans preuve.
