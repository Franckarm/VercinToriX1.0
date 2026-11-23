# Les réactions : la syntaxe complète des liaisons (proposition du 31 octobre 2026, à valider)

Décisions de l'utilisateur : le bloc s'appelle `reaction` ; l'élément d'un atome (H, C, N, O) est **déduit** par le
compilateur ; une liaison lue par plusieurs atomes reçoit une copie implicite. Demande : poser l'ensemble de la syntaxe
qu'on trouve dans un langage de programmation, et plus encore. Ce document le fait, puis donne les propositions de
Claude pour rendre vtx plus autonome et plus puissant (section 4).

Rappel du modèle (`docs/vtx-chimie.md`) : **les atomes sont le code, les liaisons sont les données**, le cube est le
support, Fischer l'indexation, Belnap la synchronisation. L'ordre des lignes ne compte pas : le compilateur range les
atomes par vagues ; tout ce qui n'est pas lié réagit ensemble.

## 1. La forme d'une ligne

```
nom = ce_que_fait_l_atome                  -> liaison, liaison…
```

- `nom` : le nom de l'atome (pour le pas à pas, les messages, la paillasse) ; facultatif : `= 6 -> a` suffit.
- À droite de `=` : une valeur, une opération, un appel.
- `->` : les liaisons que l'atome donne. Une ligne sans `->` est un bout de chaîne (afficher, ranger).
- L'élément est déduit de la valence (le nombre de liaisons reçues et données) : 1 → H, 2 → O, 3 → N, 4 → C ; au-delà
  de quatre, le compilateur découpe en plusieurs C liés (comme une chaîne carbonée) et le dit.

## 2. Tout ce qu'un langage sait faire, en réactions

### 2.1 Valeurs et types

| Besoin | Écriture | Remarque |
|---|---|---|
| constante | `= 6 -> a` | H |
| texte | `= "bonjour" -> t` | |
| couleur, point de matière | `= #FF8000 -> c` | le point de Lugus |
| flottant, entier long, logique | `= 1.5 -> x`, `= 3LL -> n`, `= vrai -> v` | les types de vtx |
| type écrit (facultatif) | `= 0 -> a: entier_32` | sinon déduit |
| unités (nouveau, section 4) | `= 9.81 m/s² -> g` | vérifiées par le compilateur |

### 2.2 Calculs

| Besoin | Écriture |
|---|---|
| opération | `= a × b -> p` (aussi `*`, `+`, `-`, `÷`, `/`, `%`, `<<`, `&`, `\|`…) |
| expression | `= (a + b) × c -> r` : le compilateur la découpe en atomes C liés |
| comparaison | `= a < b -> v` (une logique de Belnap) |
| quaternaire | `= et4(p, q) -> r`, `= anti(c) -> c2` |
| appel d'une fonction | `= racine(x) -> y` ; une fonction est une molécule |

### 2.3 Conditions (N)

| Besoin | Écriture | Belnap |
|---|---|---|
| garder une valeur si | `= si t alors x -> r` | faux : `r` porte faux, la suite de la branche ne réagit pas |
| choisir entre deux | `= si t alors x sinon y -> r` | |
| plusieurs cas | `= selon c { 1: x ; 2: y ; autre: z } -> r` | |
| les quatre valeurs | `= selon q { vrai: … ; faux: … ; inconnu: … ; variable: … } -> r` | toutes traitées, ou le compilateur prévient |

### 2.4 Répétitions : vagues, cycles et réductions

Une boucle classique fait une chose après l'autre ; une réaction préfère dire ce qui est indépendant.

| Besoin | Écriture | Ce que fait la machine |
|---|---|---|
| appliquer à chaque élément | `= pour chaque x dans t : x × 2 -> t2` | une seule vague : tous les éléments ensemble, sur plusieurs cœurs |
| réduire (somme, max…) | `= somme de t2 -> s`, `= reduire t2 par + -> s` | un arbre de rendez-vous : log₂(n) vagues |
| filtrer | `= garder x dans t si x > 0 -> t3` | |
| répéter jusqu'à | `= cycle (x = 1) tant que x < 100 : x × 2 -> fin` | un cycle catalytique : l'état passe d'un tour à l'autre par une liaison qui revient |
| intervalle | `= 0..100 -> i` | une liaison qui porte une suite |

Le cycle est l'exception, écrite : une liaison qui revient (comme le catalyseur qui ressort de la réaction). Tout le
reste est parallèle par défaut.

### 2.5 Données composées

| Besoin | Écriture |
|---|---|
| tableau | `= [1, 2, 3] -> t` ; `= t[i] -> x` |
| structure | `= Point { x: 1, y: 2 } -> p` ; `= p.x -> px` |
| dictionnaire | `= { "a": 1 } -> d` |
| tranche, longueur | `= t[2..5] -> u`, `= longueur(t) -> n` |
| cube | `= cube(2, f) -> k` ; `= k[#FF8000] -> v` (l'adresse est une couleur) |

### 2.6 Fonctions et molécules

```
reaction moyenne(a, b) -> m {
    s = a + b      -> s
    = s ÷ 2        -> m
}
```

- Les paramètres et les résultats sont des liaisons ; une réaction se replie en une case sur la paillasse.
- Plusieurs résultats : `-> m, e`.
- Récursion : permise (une molécule qui contient sa propre case).
- Une fonction ordinaire de vtx peut contenir une réaction, et une réaction peut appeler une fonction ordinaire.

### 2.7 Le monde extérieur : les ponts (O)

Tout ce qui sort de la réaction passe par un pont : c'est là que le temps et l'ordre comptent.

| Besoin | Écriture |
|---|---|
| afficher | `= afficher(r)` |
| lire l'entrée | `= entree() -> x` |
| fichier | `= pont lire "donnees.txt" -> texte` ; `= pont ecrire "sortie.txt" (texte)` |
| ranger dans le cube | `= pont r vers @2[0]` |
| importer un module | `= importer "maths" -> m` ; `= m.sinus(x) -> y` |
| la toile (image) | `= pont image vers la toile` |

Deux ponts sur la même chose (deux écritures dans le même fichier) sont **ordonnés** dans l'ordre des lignes, et le
compilateur le dit : c'est le seul endroit où l'ordre du texte compte.

### 2.8 Erreurs : Belnap, pas d'exceptions

- Une division par zéro, un indice hors du tableau, un fichier absent donnent une liaison **variable** (avec sa cause).
- Elle se propage ; on la traite là où on veut : `= si erreur(r) alors 0 sinon r -> r2`, ou `= reparer r par 0 -> r2`.
- Une liaison jamais arrivée reste **inconnue** : à la fin, le compilateur ou la machine dit laquelle et pourquoi (quelle
  entrée manquait).

### 2.9 Le temps : les flux

Pour l'animation (Gobatix, la toile) et le son : une liaison peut porter un **flux**, une valeur par image.

```
reaction anime() {
    t = horloge(1/60 s)                       -> t
    = rotation(t × 30 °/s)                    -> angle
    = dessiner(cube, angle)                   -> image
    = pont image vers la toile
}
```

À chaque image, seuls les atomes dont une entrée a changé réagissent de nouveau.

### 2.10 Ce qui accompagne le code

| Besoin | Écriture |
|---|---|
| commentaire | `// …` |
| documentation | `/// …` au-dessus d'une réaction : reprise par l'atelier et la paillasse |
| exemple vérifié (nouveau) | `exemple moyenne(4, 6) == 5` : exécuté à chaque compilation |
| contrat (nouveau) | `exige b != 0`, `garantit m >= 0` |
| isotope (contrôle) | `= 6 -> a lourd` : la liaison garde son contrôle (les neutrons) jusque dans l'ARN |

## 3. L'exemple du panel d'atomes, avec l'élément déduit

```
reaction principal() {
    six       = 6                         -> a
    sept      = 7                         -> b
    dix       = 10                        -> d
    produit   = a × b                     -> p
    somme     = a + b                     -> s
    ecart     = s - d                     -> e
    rdv       = rendez-vous(p, e)         -> p2, e2
    garde     = si e2 > 0 alors p2        -> r
    rangement = pont r vers @2[0]         -> r2
    montre    = afficher(r2)
}
```

Le compilateur en déduit les éléments d'après la valence (le nombre de liaisons de chaque atome) : six, sept, dix et
montre en ont une : H ; rangement deux : O ; produit, somme, ecart, garde et les deux copies implicites (de `a` et de
`b`, une entrée et deux sorties) en ont trois : N ; le rendez-vous quatre : C. Formule CH₄N₆O, masse 116 hex. Sept
vagues ; à la vague 2, le produit et la somme réagissent ensemble.

Remarque : une opération à deux entrées et une sortie a trois liaisons, c'est donc un N, avec son doublet libre (la
place d'une seconde sortie) ; elle devient un C quand on lui donne deux sorties. L'élément suit la valence, toujours :
le tableau des rôles de `vtx-chimie.md` (C pour le calcul…) n'était qu'une représentation, comme l'a décidé
l'utilisateur.

## 4. Les propositions de Claude : ce que je voudrais dans mon propre langage

L'utilisateur m'a demandé d'imaginer que Vercintorix est mon langage de conception. Voici ce que j'y ajouterais, avec la
raison de chaque chose. Ce sont des propositions : à trier ensemble.

### 4.1 Pour la sûreté : vérifier plutôt que croire

1. **Les exemples vérifiés** (`exemple f(2) == 4`) : un programme porte ses propres preuves de bon fonctionnement, rejouées
   à chaque compilation. Pour une IA qui écrit du code, c'est essentiel : je me trompe parfois, et un exemple faux se voit
   tout de suite.
2. **Les contrats** (`exige`, `garantit`) : ce qu'une réaction attend et promet, vérifié à l'exécution (et, plus tard,
   prouvé quand c'est possible).
3. **Les unités physiques dans les types** (m, s, kg, °) : additionner des mètres et des secondes devient une erreur de
   compilation. Une sonde martienne a été perdue pour une confusion d'unités (Mars Climate Orbiter, 1999).
4. **La conservation** : une valeur appartient à une seule molécule à la fois (comme la possession en Rust) ; pas de
   copie cachée, pas de fuite, pas de donnée partagée sans le dire.

### 4.2 Pour comprendre : la provenance

5. **Chaque valeur sait d'où elle vient.** Les liaisons forment déjà la chaîne : la machine peut répondre à « pourquoi
   cette valeur vaut 42 ? » en remontant les atomes jusqu'aux constantes. Pour le débogage, c'est le pas à pas à
   l'envers ; pour une IA, c'est une explication vérifiable.
6. **Les effets marqués** : seuls les ponts (O) touchent le monde extérieur. Tout le reste est pur, donc on peut le
   rejouer, le mettre en cache, le paralléliser sans risque. Le compilateur le sait sans analyse : c'est écrit dans la
   molécule.

### 4.3 Pour la puissance

7. **Le calcul incrémental** : quand une entrée change, seuls les atomes qui en dépendent réagissent de nouveau, comme un
   tableur. Pour l'atelier (on modifie, on voit aussitôt), pour Gobatix (on bouge un objet, seule sa partie de l'image
   est refaite) et pour l'animation.
8. **La signature comme identité** : une molécule est identifiée par sa formule et ses liaisons, hachées. Deux molécules
   identiques ne sont compilées et rangées qu'une fois ; un résultat déjà calculé pour les mêmes entrées est retrouvé
   (le cache par contenu).
9. **Le programme comme donnée** : une réaction peut lire, construire et modifier une molécule (avec la vérification de
   la valence). vtxc le fait déjà pour compiler ; l'ouvrir à tous permet les programmes qui écrivent des programmes, et
   une IA qui modifie Gobatix ou ses propres outils en toute sûreté.
10. **Les flux** (section 2.9) : le temps devient une liaison comme une autre, ce qui rend l'animation et le son
    naturels.

### 4.4 Pour l'autonomie (ce qui reste à faire, dans l'ordre)

11. **Gobannos, la forge écrite en vtx** : porter `forge.py` et `forge128.py` dans vtxc. Après, vtx n'a plus besoin de
    Python du tout : vtx se compile, se forge et se vérifie lui-même.
12. **La forge vers la carte graphique** : écrire, en plus du Rust, des programmes de calcul pour le GPU. Les vagues
    s'y prêtent exactement : des milliers d'atomes indépendants qui réagissent ensemble.
13. **Ogmios écrit en vtx** : l'atelier lui-même dans le langage, comme vtxc. Le langage s'améliore alors avec ses propres
    outils.
14. **Les modules par contenu** : un module se désigne par sa signature (empreinte), pas seulement par son nom ; une
    version exacte, vérifiable, partageable.

### 4.5 Ce que je déconseille

- **Tout rendre parallèle par magie** : les ponts (O) doivent rester ordonnés, sinon les fichiers et les affichages se
  mélangent. Le modèle ci-dessus le garde.
- **Ajouter une fonctionnalité sans mesure** : chaque ajout vient avec son essai chiffré (la méthode du crible).

## 5. Ordre proposé

1. Valider ce document (la syntaxe des sections 1 à 3 ; les propositions de la section 4 à trier).
2. Les réactions dans vtx128 (le compilateur de référence) : sections 1, 2.1 à 2.3, 2.6, 2.7 ; l'exemple du panel, compilé
   et exécuté sur Lugus, émulé et forgé.
3. Les vagues sur plusieurs cœurs, mesurées.
4. Fischer : les liaisons rangées dans le cube.
5. Puis les répétitions (2.4), les erreurs (2.8), les exemples et contrats, la provenance ; vtxc128 ; la paillasse dans
   Ogmios.

## 6. Décisions du 31 octobre (fin de matinée)

| Proposition | Décision |
|---|---|
| exemples vérifiés | gardés (dans l'esprit de ce qui est fait : tout vérifier) |
| contrats (`exige`, `garantit`) | **ajoutés** |
| unités physiques dans les types | **ajoutées** |
| calcul incrémental | **oui, évidemment** |
| signature d'une molécule comme identité | **oui, appuyée sur l'organisation de Fischer** : la place d'une molécule dans le cube et sa signature disent la même chose |
| le programme comme donnée | d'accord |
| la forge écrite en vtx (Gobannos) | à faire |
| la forge vers la carte graphique | à faire |
| Ogmios écrit en vtx | à faire **avant** les deux précédentes |
| modules désignés par leur empreinte | oui, par l'ADN et l'ARN : un module est un ADN signé, chaque usage une transcription |

**Les ponts : parallèles, avec des conditions quand c'est nécessaire** (idée de l'utilisateur). Les ponts réagissent en
même temps par défaut ; le compilateur ajoute lui-même une condition d'ordre quand deux ponts touchent la même chose
(le même fichier, la même case du cube, la toile), et le programmeur peut en écrire une (`apres pont1`). Deux ponts vers
des fichiers différents partent ensemble ; deux écritures dans le même fichier passent l'une après l'autre.

**La provenance et la fiabilité de l'ADN** : la provenance (d'où vient chaque valeur) est rangée dans l'ADN, avec la
signature et le contrôle (les neutrons) de chaque molécule. Le chantier qui suit les réactions : la fiabilité de l'ADN
par son code chimique (signatures, isotopes, triangulation, miroir segmenté).

### L'ordre de travail qui en découle

1. Les réactions dans vtx128 : l'exemple du panel, compilé et exécuté sur Lugus, émulé et forgé.
2. Les vagues sur plusieurs cœurs ; les ponts parallèles avec leurs conditions ; mesurés.
3. Fischer : les liaisons et les molécules rangées dans le cube, la signature comme identité.
4. Les contrats, les unités, les exemples vérifiés ; le calcul incrémental.
5. La fiabilité de l'ADN par son code chimique, avec la provenance.
6. Ogmios écrit en vtx ; puis Gobannos (la forge en vtx) ; puis la forge vers la carte graphique.

## 7. Ce qui est fait (31 octobre, fin de matinée)

- **Étape 1** (vtx128.py) : les atomes et les liaisons, les vagues (l'ordre des lignes sans effet), `si … alors …
  [sinon …]` avec la branche qui ne réagit pas, le rendez-vous, le pont vers le cube, une réaction qui rend un résultat,
  l'élément déduit de la valence et la formule (`python vtx128.py molecule PROG.vtx`), `×` et `÷`. Exemple :
  `exemples128/panel.vtx`.
- **Étape 2** :
  - **les ponts** : ensemble, sauf ceux qui touchent la même chose (la même case du cube, l'écran, la sortie) : ceux-là
    gardent l'ordre des lignes ; une lecture du cube vient après le pont qui écrit la même case ; `apres nom` écrit un
    ordre à la main (il l'emporte sur l'ordre des lignes) ;
  - **`somme` (`min`, `max`) `pour chaque i dans a..b : f(i) -> s`** : une vague de b − a atomes réduite en une liaison ;
    forgée, elle est partagée entre les cœurs quand chaque atome est pur (ni mémoire, ni effet) et rend un entier
    (la réduction est alors la même dans n'importe quel ordre) ;
  - **les atomes lourds d'une même vague** (des calculs qui appellent une fonction du programme) : forgés, chacun sur son
    cœur.
  - Mesure (forgé pour Lugus, 2 cœurs sur la machine de travail) : Mandelbrot en réaction
    (`exemples128/mandel_reaction.vtx`) 1,05 s sur un cœur, 0,56 s sur deux (1,9 fois) ; deux moitiés lourdes dans une
    vague : 1,08 → 0,58 s. Sur un PC à 8 cœurs, le gain attendu est plus grand (à mesurer chez l'utilisateur).
  - Limites : la machine émulée joue les vagues l'une après l'autre (mêmes sorties) ; vtxc128 ne connaît pas encore les
    réactions (étape 4) ; « pour chaque » sans réduction (qui donnera un tableau) n'est pas encore là.
- **Étape 3, Fischer** (`chimie/fischer.py`) :
  - **le cube des molécules** : l'étage 0 (avec le code : c'est l'ADN), le cube de fréquence 12 (la masse du carbone) ; ses
    256³ cases parcourues par le fil de Hilbert (une case ne mène qu'à sa voisine), coupé en 4096 colonnes ;
  - **la signature** : l'empreinte de ce qu'est la molécule (ses atomes vague après vague, la forme de leurs expressions et
    leurs valeurs écrites, d'où vient chaque liaison), sans les noms ni l'ordre des lignes ;
  - **la place** : la formule (la masse) choisit la colonne, la signature la place dans la colonne ; la molécule occupe une
    suite de cases (une tête, puis un atome par case, la chaîne à la suite) ; si la place est prise, elle avance le long du
    fil, comme une brique qui cherche son trou ;
  - **le puzzle** (idée de l'utilisateur) : une pièce qui ne rentre pas essaie l'autre sens, la colonne miroir (celle de
    l'anti-cube) ; on prend la moins pleine des deux ;
  - **la répartition** : les colonnes partagées selon la fréquence des masses (comme on égalise un histogramme), l'ordre
    gardé ; sans elle, les masses courantes saturent quelques colonnes pendant que le reste du cube reste vide.
  - `python vtx128.py molecule PROG.vtx` donne la signature et la place de chaque réaction.

  La saturation, mesurée (`python chimie/fischer.py essai N` ; molécules de 3 à 40 atomes ; cases regardées en moyenne) :

  | Molécules | Part du cube occupée | Ranger | Retrouver |
  |---|---|---|---|
  | 5 000 | 0,7 % | 1,1 | 1,5 |
  | 60 000 | 8 % | 3,0 | 5,8 |
  | 200 000 | 27 % | 32 | 62 |
  | 400 000 | 54 % | 507 | 866 |
  | 40 000, une colonne par masse, sans miroir ni répartition | 5 % | 188 | 217 |

  La formule de la saturation : pour un rangement « le long du fil » (le sondage linéaire de Knuth), il faut regarder en
  moyenne ½ (1 + 1/(1 − α)²) places pour ranger et ½ (1 + 1/(1 − α)) pour retrouver, α étant la part occupée ; avec des
  briques de plusieurs cases, les trous trop courts comptent comme pleins, et la saturation vient plus tôt : au-delà
  d'un quart du cube, elle se fait sentir. La règle qui en découle : ouvrir un deuxième cube de molécules (fréquence
  13…) quand le premier passe le quart, comme on ajoute une étagère.

- **Étape 4, la sûreté, premier temps** (vtx128.py ; l'exemple `exemples128/chute.vtx`) :
  - **les contrats**, ce sont les conditions de la réaction :
    - `exige` parle des entrées et est vérifié avant toute réaction ;
    - `garantit` parle de ce que la réaction donne et est vérifié à la fin ; une liaison qui porte faux (sa branche n'a
      pas réagi) ne promet rien.
    - Quand un contrat est rompu, la machine écrit `contrat rompu : chute exige h >= 0.0 (ligne 6)` et s'arrête (l'intégré
      `__rompre`, l'instruction HALT ; la forge fait de même). C'est un choix : une condition rompue est une erreur du
      programme, pas une valeur à propager ; les erreurs de calcul (division par zéro…) resteront des liaisons
      variables (2.8).
  - **les exemples vérifiés** : `exemple trajet() == 2500`, écrit hors des fonctions, est rejoué à chaque compilation (sur
    Lugus émulé). S'il est faux, la compilation s'arrête : `ligne 7 : l'exemple « moyenne(10, 20) == 16 » est faux : le
    côté gauche vaut 15`. `vtx128.EXEMPLES = False` les saute.
  - **les unités physiques** :
    - `= 9.81 m/s² -> g`, `= 2 km -> d`, `h: flottant m` pour une entrée, `-> t: flottant s` pour le résultat,
      `-> v: m/s` pour une liaison ;
    - le compilateur les suit le long des liaisons : `+`, `-`, les comparaisons et `min`/`max` veulent la même unité ;
      `×` et `÷` les combinent ; `racine` divise les exposants ;
    - les unités disponibles : les sept unités de base (m, kg, s, A, K, mol, cd), le degré `°`, les unités dérivées N,
      J, W, Pa, Hz, C, V, Ω, et km, cm, mm, g, ms, min, h ;
    - une valeur est rangée dans l'unité de base (2 km devient 2000, en mètres) ; un entier qui ne tombe pas juste
      (500 g = 0,5 kg) doit s'écrire à virgule ;
    - le zéro va avec toutes les unités ; une valeur venue d'une fonction ordinaire a une unité inconnue, qui n'est
      pas vérifiée ;
    - après un nombre, `/` suivi d'une unité fait partie de l'unité ; pour diviser par une liaison qui porte un nom
      d'unité, on écrit `(2 m) / h` ;
    - à l'exécution, il ne reste rien des unités : un programme avec unités donne les mêmes mots que sans.
  - `python vtx128.py molecule` montre aussi les contrats et l'unité de chaque liaison.
  - Ce qui reste :
    - ~~une réaction qui rend une liaison portant faux rend sa valeur brute~~ : réglé, voir « les trois restes » plus bas ;
    - ~~les unités et les contrats n'entrent pas encore dans la signature de Fischer~~ : réglé, idem ;
    - vtxc128 ne connaissait ni les réactions ni ces ajouts : fait au troisième temps, plus bas.
- **Étape 4, deuxième temps : le calcul incrémental, les souvenirs** (vtx128.py ; l'exemple
  `exemples128/scene_incrementale.vtx`) :
  - **Le principe.** Un atome lourd garde le souvenir de sa dernière réaction : ses entrées et ce qu'il a donné. Quand la
    réaction est rappelée et que ses entrées sont les mêmes, il ne réagit pas : il redonne son souvenir. Ce qui dépend de
    lui voit alors les mêmes entrées, et redonne aussi le sien : seuls les atomes dont une entrée a changé réagissent de
    nouveau.
  - **Qui a un souvenir** : rien n'est à écrire, le compilateur choisit seul.
    - L'atome appelle une fonction du programme qui est **pure** : elle ne lit ni n'écrit la mémoire, ne touche pas le
      monde, et n'appelle que des fonctions pures. Pour les mêmes entrées, elle donne toujours la même chose.
    - La fonction est **lourde** : elle fait une boucle, ou s'appelle elle-même. Une fonction sans boucle coûte moins que
      son souvenir.
    - L'atome est hors de `principal`, qui ne réagit qu'une fois.
    - Ses entrées et son résultat sont rangés en un mot : entier, entier_32, entier_petuar, les flottants, le point.
  - **Où** : dans le cube 1 de l'étage 3, `@3[#1000000..#1FFFFFF]` (le cube 0 garde le tas, les copies et le journal des
    hypothèses, qui commence à #F00000 : la première place choisie le heurtait, vu en portant les réactions dans vtxc128). Chaque souvenir prend sa validité, une case par entrée et une pour le
    résultat. Les flottants sont comparés bit à bit : -0 n'est pas +0.
  - **Les vagues sur plusieurs cœurs (étape 2).** Hors de principal, un atome lourd qui peut garder un souvenir le garde
    plutôt que d'aller sur un autre cœur : rappelé, il ne coûte plus rien. Dans principal, rien ne change.
  - **La mesure** : la scène rappelée 60 fois, avec un décor qui change toutes les dix images et une lumière toutes les vingt.

    | | Sans souvenirs (`VTX_SOUVENIRS=0`) | Avec |
    |---|---|---|
    | Lugus émulé | 1 919 875 instructions | 186 915 (10 fois moins) |
    | forgé (3000 images) | 0,89 s | 0,093 s |

    Le résultat est le même. La forge et Lugus en Rust rendent les mêmes sorties que l'émulateur.
  - `python vtx128.py molecule` montre les souvenirs et leur place.
  - Ce qui reste : ~~un souvenir ne garde que la dernière réaction~~ (fait plus bas : seize places, rangées comme
    Fischer) ; ~~le souvenir et les cœurs ne se combinent pas encore~~ (fait, section 9).
- **Étape 4, troisième temps : les réactions dans vtxc128**, le compilateur écrit en vtx (`vtxc/vtxc128.vtx`, la section
  « les réactions », environ 1 300 lignes de vtx) :
  - **Ce qu'il lit**, comme vtx128.py :
    - les atomes de chaque genre : calcul, si … alors [sinon], rendez-vous, pont, pour chaque ;
    - les noms, `apres`, l'ordre des effets ;
    - les vagues et les drapeaux des branches qui ne réagissent pas ;
    - les atomes lourds d'une même vague ;
    - les contrats ;
    - les unités, ramenées à l'unité de base ;
    - les souvenirs : est_pure et est_lourde sont refaits en vtx ;
    - ×, ÷, `->`, ° et ·.
  - **Le même résultat** : vtxc128 donne exactement les mêmes mots que vtx128.py (`vtxc/test_reactions_vtxc128.py`). C'est
    vérifié sous trois réglages (prélude, optimisations, partition) :
    - sur les exemples de Lugus en réactions ;
    - sur les programmes des tests des réactions ;
    - sur des réactions tirées au hasard (`vtxc/hasard_reactions.py` : chaque genre d'atome, les lignes mélangées).
  - **Deux corrections trouvées en route** :
    - les souvenirs heurtaient le journal des hypothèses (`@3[#F00000..]`) ; ils vont dans le cube 1 de l'étage 3 ;
    - vtx128.py comptait deux fois les variables d'une vague ou d'un « pour chaque » pour choisir ses registres (il
      lisait aussi ce que le bloc dit de lui-même, pour la forge) ; il ne compte plus que les instructions.
  - **Ce que vtxc128 ne fait pas encore** :
    - il ne vérifie pas les unités : il les lit et les ramène à la base, mais ne refuse pas des mètres plus des
      secondes ;
    - ~~il ne rejoue pas les exemples : il les lit seulement~~ : Lugus les rejoue, voir « les trois restes » ;
    - un flottant avec une unité à facteur (`2.0 km`) lui est refusé.
  - **Pour Lugus et Ogmios** : vtxc128 est embarqué dans lugus ; les réactions se compilent donc sans Python, dans
    l'atelier comme en ligne de commande.
- **Étape 5, premier temps : la provenance** (`python vtx128.py pourquoi PROG.vtx [réaction.liaison] [ENTRÉES…]`) :
  - « Pourquoi cette valeur vaut 42 ? » : le programme est compilé avec la provenance et lancé. Chaque réaction range,
    avant de rendre, la dernière valeur de chacune de ses liaisons et de ses entrées dans le cube 2 de l'étage 3, avec le
    nombre de réactions et la présence (0 quand sa branche n'a pas réagi).
  - Puis la commande remonte les atomes, de liaison en liaison, jusqu'aux constantes et aux entrées. Chaque ligne donne
    la valeur avec son unité, l'atome qui l'a donnée (son nom, ce qu'il fait, sa ligne, son élément) et le nombre de
    réactions. Pour un atome à souvenir, elle dit combien de fois il a vraiment réagi : 6 fois sur 60 appels pour le décor
    de la scène.
  - Exemple, le panel :

    ```
    r2 = 42   ← rangement : pont r vers @2[0]   (ligne 7, O)
        r = 42   ← garde : si e2 > 0 alors p2   (ligne 8, N)
            e2 = 3   ← rdv : rendez-vous(p, e)   (ligne 9, C)
                p = 42   ← produit : a × b   (ligne 12, N)
                    a = 6   ← six : 6   (ligne 15, H)
    ```

  - Sans la provenance, une réaction garde exactement ses mots (vtxc128 n'a rien à suivre).
  - Les valeurs sont celles de la dernière réaction complète : un contrat rompu arrête la machine avant la trace.
  - Ce qui reste :
    - la provenance d'une réaction à l'autre (descendre dans la réaction appelée) ;
    - ~~la ranger dans l'ADN du programme, pour que Lugus et Ogmios répondent sans Python~~ : fait, voir plus bas ;
    - la fiabilité de l'ADN par son code chimique : le deuxième temps, ci-dessous.
- **Étape 5, deuxième temps : la fiabilité de l'ADN** (`chimie/adn.py`, `chimie/rs.py` ; choix de l'utilisateur : les
  trois témoins par molécule).
  - **L'ADN d'un programme**, ce sont ses mots compilés, rangés pour durer (`python chimie/adn.py ranger PROG.vtx` écrit
    `PROG.adn`). Il est découpé en molécules : chaque fonction ou réaction, la tête, les textes et les données.
  - **Les trois témoins**, indépendants, se recoupent :
    1. **la signature** de chaque molécule (64 bits). Elle voit tout changement et confirme chaque réparation ;
    2. **l'ombre**. L'ADN est lu en colonnes entrelacées : la colonne k prend un mot sur C, et une rafale de mots
       voisins se répartit donc entre les colonnes. Chaque colonne a quatre mots d'ombre, un code de Reed-Solomon sur
       les seize octets de chaque mot. Elle répare deux mots abîmés n'importe où dans la colonne, ou quatre si l'on sait
       lesquels ;
    3. **les neutrons** : 8 bits de contrôle par mot, aux frontières seulement (O : les molécules dont le code écrit en
       mémoire ou sort quelque chose). Ils disent quels mots sont abîmés, et l'ombre en répare alors deux fois plus.
  - **La triangulation.** Une réparation n'est gardée que si deux témoins l'appuient : la signature, ou bien les neutrons
    avec l'ombre. Si la signature seule contredit les deux autres, c'est elle qui est refaite. Au-delà, la molécule est
    gardée telle qu'elle a été lue, pour la preuve.
  - **L'état de la lecture**, en logique de Belnap : vrai (intact), faux (réparé, ou un témoin refait), variable (vu, non
    réparé).
  - **La transcription** (`python chimie/adn.py transcrire PROG.adn`) vérifie et répare, puis l'épissage retire les
    témoins. L'ARN, ce sont les mots seuls, exactement ceux du programme d'origine. Un ADN réparé est réécrit.
  - **Mesuré** sur de vraies avaries (`python chimie/adn.py essai`, `tests/test_adn.py`) :

    | Programme | Mots | Témoins | Réparé |
    |---|---|---|---|
    | chute.vtx | 1 929 | 5,6 % | 100 % : un bit, un mot, un mot effacé, deux mots échangés, deux mots d'une molécule, des rafales de quatre et de huit mots, un témoin abîmé, un mot et sa signature |
    | bonjour128.vtx | 1 907 | 5,8 % | la même chose, 100 % |
    | vtxc128 lui-même | 169 983 | 2,6 % | 100 % : un mot, une rafale de huit, seize mots au hasard, un mot et sa signature |
    | panel.vtx (une seule colonne) | 89 | 13,5 % | 100 % pour un ou deux mots ; les rafales seulement en partie |

    - Au-delà de ce que l'ombre peut réparer (trois mots dans une même colonne, seize mots au hasard dans un petit
      programme), l'avarie est **vue**.
    - Erreurs muettes, c'est-à-dire réparées de travers ou passées sans être vues : **0** dans tous les essais.
  - **Les comparaisons** :
    - le miroir inversé double la place (100 %) ;
    - l'ombre des cubes sur disque (3,5 %) répare un mot par colonne.
  - **Lugus et Ogmios lisent l'ADN** (`vtx-rs/src/adn.rs`) :
    - le découpage se fait d'après les mots seuls : la tête, puis une molécule par fonction, de la cible d'un CALL à la
      suivante. La signature est un mélange de 64 bits refait à l'identique des deux côtés. Rust et Python font donc le
      même ADN, octet pour octet ;
    - Rust lit chaque avarie comme Python : 132 avaries sur 132, même état, mêmes mots, même ADN réparé
      (`tests/test_adn.py`) ;
    - `lugus ranger PROG.vtx` range l'ADN ; `lugus transcrire PROG.adn` vérifie, répare et rend les mots ;
      `lugus PROG.adn` vérifie, répare, puis lance (rien n'est lancé d'un ADN variable) ;
    - dans Ogmios, F5 sur Lugus range l'ADN à côté du programme (`PROG.adn`) et le lit avant de lancer ; le résumé dit
      son état et la place des témoins. « Exécuter > Lancer un ADN rangé » vérifie un `.adn`, le répare (et le réécrit),
      puis le lance ;
    - `python chimie/adn.py abimer PROG.adn N` abîme N mots, pour essayer la réparation.
  - **Ce qui reste** :
    - ~~les isotopes (`lourd`), pour des neutrons sur une molécule choisie~~ : fait, section 9 ;
    - la lecture de l'ADN dans vtxc128 (en vtx), pour Ogmios écrit en vtx ;
    - ~~la provenance rangée dans l'ADN~~ : l'ADN garde le texte, vérifié par la rétrotranscription ; `lugus pourquoi
      PROG.adn` repart de lui (section 9) ;
    - ~~la patrouille : relire l'ADN pendant que la machine attend~~ : fait, section 9.
- **La provenance sans Python** (Lugus et Ogmios) :
  - vtxc128 sait compiler avec la trace : c'est un sixième drapeau d'entrée. Il donne les mêmes mots que vtx128.py avec
    `PROVENANCE`, vérifié sur les exemples et sur des réactions au hasard (`vtxc/test_reactions_vtxc128.py`). La place
    de la trace repart du début à chaque compilation, dans les deux compilateurs.
  - Il écrit `code.prov`, lu par `vtx-rs/src/provenance.rs`. Le fichier donne, pour chaque réaction, la place de chaque
    nom dans la trace et son type, et pour chaque atome son nom, sa ligne, ses liaisons, son texte et s'il a un souvenir.
  - `lugus pourquoi PROG.vtx [liaison | réaction.liaison] [ENTRÉES…]` écrit le même arbre que `vtx128.py pourquoi`, au
    caractère près (`tests/test_provenance.py`), sauf les unités : vtxc128 ne les suit pas encore.
  - Dans Ogmios, « Exécuter › Pourquoi ? » (Ctrl+P) prend le nom sous le curseur. Le programme est compilé avec la
    provenance et lancé sur Lugus, puis l'arbre s'écrit dans le journal. Sans nom, ou sur un nom qui n'est pas une
    liaison, il montre ce que rendent les réactions.
  - `lugus PROG.adn` : l'épissage retire les témoins, et c'est l'ARN, les mots seuls, qui est lancé. Le chemin Cube → Hex →
    ADN → ARN est donc complet dans Lugus.
- **Les souvenirs rangés comme Fischer** (le point 3 de la route droite : Fischer prend sa fonction). Chaque atome lourd
  a maintenant une **colonne de seize places** :
  - la colonne, c'est l'atome ; la place, c'est l'empreinte de ses entrées (FNV, puis mélangée par le nombre d'or) ;
  - **deux choix**, comme la pièce du puzzle qui essaie l'autre sens. La première place, ce sont les quatre bits forts du
    mélange ; la seconde, les quatre suivants, une seconde pièce indépendante de la première, ou le miroir quand les
    deux tombent au même endroit ;
  - quand ni l'une ni l'autre ne garde ces entrées, l'atome réagit. Son souvenir est rangé à la première place libre
    des deux, sinon il remplace celui de la première.
  - Un premier essai prenait le miroir de la première place comme seconde place : trois valeurs se disputaient alors deux
    places et se chassaient l'une l'autre (41 calculs sur 60). La seconde pièce indépendante règle ce cas.
  - **Mesuré** (`exemples128/alternance.vtx`, le décor qui alterne entre k valeurs, 60 appels ; calculs du lourd) :

    | k valeurs | 2 | 3 | 5 | 8 | 12 | 16 | 20 |
    |---|---|---|---|---|---|---|---|
    | une seule place (avant) | 60 | 60 | 60 | 60 | 60 | 60 | 60 |
    | seize places, deux choix | 2 | 3 | 5 | 10 | 14 | 23 | 35 |

    Le coût, là où une seule place suffisait (la scène) : 3,6 % d'instructions de plus (195 135 au lieu de 186 915),
    toujours 10 fois moins que sans souvenirs.
  - vtxc128 range les souvenirs de la même façon : les mêmes mots. `lugus pourquoi` le montre aussi : « souvenir :
    réagi 5 fois sur 60 appels ».
- **Le ménage (point 4 de la route droite)** :
  - **Les unités dans vtxc128.** Elles sont vérifiées comme dans vtx128.py, avec les mêmes messages ; chaque unité tient
    dans un nombre (huit exposants de quatre bits). Les flottants à facteur sont acceptés (`2.0 km`, `5.0 mm`). La
    provenance de Lugus et d'Ogmios écrit les unités (`t = 2.0193 s`), et `lugus pourquoi` donne le même arbre que
    vtx128.py, unités comprises.
  - **Le facteur d'une unité est une fraction exacte**, dans les deux compilateurs (il était un flottant dans vtx128.py).
    Un facteur sans écriture décimale finie, comme km/h (5/18), est refusé sur un flottant plutôt qu'arrondi en silence.
  - **Les rôles des machines**, écrits dans `LISEZMOI.md` : Lugus est la machine de vtx. Senos et Dunon restent la
    référence et la compatibilité ; ils recevront les réactions plus tard, pour la rétrocompatibilité. L'atelier le dit
    quand on change de machine.
  - **Le nom Gobatix** n'apparaît plus dans le prélude de Lugus (c'est « la toile ») ; le code qui ne servait plus dans
    vtxc128 est retiré.
  - **Les trois restes** (1er novembre) :
    - **Une réaction dont le résultat porte faux** (sa branche n'a pas réagi) le dit avec son type : une logique rend
      faux, un flottant rend inconnu (la valeur n'est jamais arrivée, comme en 2.8). Un entier n'a aucune valeur libre
      pour le dire : le compilateur le refuse et demande un sinon (« un entier ne sait pas le dire : écrivez un sinon, ou
      rendez une logique (faux) ou un flottant (inconnu) »). Avant, la valeur calculée sortait comme si de rien n'était.
      Les deux compilateurs, les mêmes mots ; le générateur de réactions au hasard ne rend plus que des liaisons
      toujours là.
    - **La signature de Fischer** compte les contrats (exige, garantit, sans les noms ni l'ordre des lignes) et les
      unités (des entrées, des liaisons, du résultat). Une molécule qui promet autre chose, ou qui compte en secondes au
      lieu de mètres, n'est plus la même. `2 km` et `2000 m` restent la même molécule. Sans contrat ni unité, la
      signature ne change pas : les places déjà rangées restent (vérifié sur une valeur gardée).
    - **Les exemples rejoués par Lugus**, sans Python. vtxc128 écrit `code.ex` (la ligne, l'égalité, le texte de chaque
      exemple) ; avec un sixième drapeau, il compile le programme des exemples, mot pour mot comme vtx128.py (le
      principal remplacé par le calcul de chaque exemple). Lugus le fait tourner sur une machine neuve ; un exemple faux
      arrête la compilation avec le message de vtx128.py : `erreur ligne 6 : l'exemple « moyenne(10, 20) == 16 » est
      faux : le côté gauche vaut 15`. C'est fait dans la compilation elle-même : `lugus PROG.vtx`, `lugus ranger`, F5
      dans l'atelier et Ogmios en vtx en profitent.

- **Étape 6, premier temps : Ogmios écrit en vtx** (`ogmios/ogmios.vtx`, environ 650 lignes) :

  ```
  vtx toile128 ogmios/ogmios.vtx --fichier exemples128/chute.vtx
  ```

  - **L'atelier tourne sur Lugus**, comme n'importe quel programme : il dessine dans la toile (480 × 300 points,
    80 colonnes, 30 lignes, la police 5 × 7 du prélude ; la fenêtre l'agrandit) et lit le clavier et la souris.
  - **Ce qu'il sait faire** :
    - montrer le programme en couleurs (les mots du langage en bronze, les types en vert-de-gris, les nombres et les
      points, les textes, les commentaires, les liaisons `->` en braise), avec les numéros de ligne ;
    - éditer : les caractères (accents compris), Entrée qui garde le retrait, Retour arrière, Suppr, Tab, les flèches,
      Début, Fin, les pages, le clic de la souris, la molette ;
    - Ctrl+S enregistre, en gardant les fins de ligne du fichier (\r\n sous Windows) ; Ctrl+Q ferme ;
    - **F5** enregistre, puis une **machine fille** compile le programme avec vtxc128 (les exemples rejoués) et le
      lance sur un Lugus neuf. Son compte rendu (ce qu'il écrit, ses sorties, le nombre d'instructions, ou l'erreur)
      vient en bas de l'écran, et aussi dans la console.
  - **Ce que la machine a reçu pour lui** :
    - `vtx toile128` : la toile de Lugus (fenêtre, images PNG, GIF, scénario de gestes), comme `vtx toile64` ;
      `--fichier` donne un chemin au programme par ses entrées ;
    - le service 24, la machine fille : un programme vtx nommé, compilé et lancé à côté. Son compte rendu se lit comme
      un fichier (`lire_car`). C'est l'équivalent d'un processus : Ogmios reste un programme vtx, le compilateur aussi
      (vtxc128) ; la machine hôte ne fait que prêter un Lugus neuf ;
    - Ctrl+lettre arrive au programme (Ctrl+S donne 19).
  - **Vérifié** (`tests/test_ogmios.py`) : les deux compilateurs donnent les mêmes mots pour Ogmios (2 998) ; une édition
    rejouée par scénario (flèches, Fin, « été », Entrée, retour arrière, Début, Tab, Suppr, un clic) puis Ctrl+S donne
    exactement le fichier attendu, en \r\n ; F5 donne « bonjour » et 15 ; un exemple faux y est dit.
  - **Mesuré** : une touche (l'écran redessiné en entier) coûte 27 ms sur Lugus émulé ; F5 complet, 2,9 s (la
    compilation d'Ogmios, puis celle du programme et de ses exemples).
  - **Ce qui manque** (les temps suivants) : la sélection, copier et coller, annuler ; chercher ; plusieurs fichiers ;
    le pas à pas, la vue du cube, la provenance (Ctrl+P) et l'ADN dans Ogmios en vtx ; ne redessiner que ce qui
    change ; prévenir avant de fermer un fichier modifié.

- **La paillasse au centre d'Ogmios** (1er novembre, décision de l'utilisateur : Ogmios, c'est `atelier.exe`, un programme
  fiable et facile ; la version écrite en vtx passe au second plan ; la paillasse vient au centre, dans les deux sens
  avec le texte) :
  - **La fenêtre** : le texte à gauche, la paillasse au centre (la plus grande), le cube à droite ; en bas, les onglets
    Sortie, Terminal, Pas à pas et Arbre (l'arbre des liaisons) et, plus petite à droite, la fenêtre des explications.
    Un programme neuf s'ouvre sur Lugus, avec une réaction.
  - **Ce qu'elle montre** : la réaction du curseur (un onglet par réaction) ; chaque atome est une case avec son élément
    (H blanc, O rouge, N bleu, C gris, d'après la valence), son nom, ce qu'il fait, ses entrées à gauche et ses sorties à
    droite ; les liaisons sont des courbes d'une sortie vers les entrées qui la lisent ; les cases sont rangées en
    vagues, de gauche à droite ; les entrées de la réaction à gauche, ce qu'elle rend à droite ; les contrats et les
    erreurs en bas.
  - **Dans les deux sens** :
    - le texte change : la paillasse est relue (sans compiler, d'après les lignes de la réaction ; ce qui n'est pas encore
      juste reste visible : une entrée libre `_`, un cycle) ; le curseur dans le texte choisit la réaction et l'atome de
      sa ligne ;
    - sur la paillasse : tirer une sortie sur une case remplit son entrée libre `_` (ou remplace l'entrée visée) ; tirer
      une entrée vers le vide la rend libre ; double clic dans le vide : `= _ -> l1` s'écrit dans la réaction ; Suppr
      retire l'atome choisi ; glisser une case la déplace (sa place est gardée dans `PROG.paillasse`) ; un clic sur une
      case montre sa ligne dans le texte. Chaque geste réécrit seulement la ligne touchée : Ctrl+Z dans le texte le
      défait.
    - **Ctrl+P** (Faire réagir) : le programme est compilé avec la provenance et lancé ; chaque liaison porte alors sa
      valeur et son état de Belnap (vert : arrivée, rouge : sa branche n'a pas réagi, gris pointillé : jamais calculée).
      Depuis la paillasse, Ctrl+P remonte la liaison de l'atome choisi.
  - **La fenêtre des explications** dit ce qu'est l'atome choisi (élément, valence, ce qu'il lit et donne, sa vague, ce
    que fait son genre, sa valeur), ou, sans choix, comment se servir de la paillasse ; puis ce qu'il faut corriger.
  - **Fiable** : le module (`vtx-rs/src/paillasse.rs`) ne dépend pas de Windows ; il dessine dans une image et rend les
    textes, que l'atelier écrit avec sa police. `vtx paillasse PROG.vtx [--png F] [--gestes F] [--valeurs] [--ecrire]`
    fait la même chose sans écran ; `tests/test_paillasse.py` vérifie que la paillasse lit les réactions comme le
    compilateur (les exemples de Lugus et 30 réactions au hasard : mêmes vagues, mêmes entrées, mêmes sorties, l'ordre
    des ponts et des effets compris), rejoue les gestes à la souris et lance le texte réécrit (r(3) = 12).
  - **Ce qui manque** : le zoom ; plusieurs atomes choisis à la fois ; renommer une liaison depuis la paillasse ; les
    valeurs pendant le pas à pas.

## 8. Le langage avant la carte graphique (2 novembre)

Décidé avec l'utilisateur : d'abord le langage (pour un Ogmios propre), puis les dettes de l'ADN et des souvenirs, puis
la carte graphique. La comparaison signée par défaut est mise de côté (elle change le sens des programmes écrits).

- **Les erreurs en Belnap** (2.8) :
  - une division ou un reste par zéro donne une liaison *variable*, avec sa cause ; elle se propage le long des
    liaisons (chaque liaison qui peut errer a son drapeau, comme `__ok` pour faux) ;
  - `erreur(x)` la regarde (vrai si x porte une erreur) : l'atome qui la regarde la traite, elle ne passe pas plus loin ;
    `= reparer a / b par 0 -> q` donne la valeur, ou la valeur de secours ;
  - une erreur non réparée qui arrive à un atome qui touche le monde (un effet, un pont) ou au résultat entier d'une
    réaction arrête la machine avec sa cause : `erreur non réparée dans moyenne : division par zéro, ligne 3 (t / n)` ;
    un flottant ou une logique rendus portent *variable* (leur état de Belnap le dit) ; un contrat ne parle pas d'une
    liaison en erreur ;
  - diviser par une valeur écrite non nulle ne coûte rien (aucun drapeau) ; la provenance écrit « variable (une erreur,
    une division par zéro, non réparée) » ; la paillasse colore la liaison en violet ;
  - en route, un écart entre les deux compilateurs trouvé et corrigé : le texte d'un atome avec `÷` ou `×` (vtxc128
    collait la parenthèse qui suit, parce qu'il prenait ces signes pour des lettres).
- **Les tableaux dans les réactions** :
  - `= pour chaque i dans 0..n : i × i -> t` donne un tableau (une case par élément) ;
  - `= pour chaque x dans t : x + 1 -> t2`, `= somme pour chaque x dans t : x -> s` (min, max aussi) ;
  - `= garder x dans t si x % 2 == 0 -> pairs` (une copie de t : des flottants restent des flottants) ;
  - des flottants : `-> m: flottant[]` sur la liaison (le prélude a reçu `tableau_flottants(n)`) ; sans type écrit,
    des entiers ;
  - une réaction qui fait ou lit un tableau n'est pas pure (pas de souvenir : le tableau peut changer sous la même
    poignée).
- **Plusieurs résultats et `selon`** :
  - `reaction divmod(a, b) -> q, r { … }` ; dans une autre réaction, `= divmod(n, 7) -> q, r` ; une fonction ordinaire
    reçoit le premier. Les résultats après le premier passent par `@3[#3000000…]`, lus juste après l'appel ; chacun
    suit la même règle que le premier (une logique rend faux, un flottant inconnu ; une erreur : variable, ou l'arrêt
    pour un entier) ;
  - `= selon c { 1: 10 ; 2, 3: 20 ; autre: 99 } -> t`, et sur une logique `selon q { vrai: 1.0 ; faux: 0.0 }` ; la
    première branche qui convient ; sans `autre`, quand aucune ne convient, la liaison porte faux.
- **Les deux compilateurs donnent les mêmes mots** pour tout cela (`vtxc/test_reactions_vtxc128.py`, le générateur de
  réactions au hasard a reçu les divisions, `reparer`, `erreur()`, les tableaux, `garder`, `selon`) ; le compilateur
  embarqué dans Lugus est renouvelé (point fixe).

## 9. L'ADN vivant (2 novembre, soir)

Les dettes de l'ADN, de l'ARN et des souvenirs, prises comme la biologie les règle : une cellule garde son ADN, en tire
des ARN différents selon le besoin, apprend, se répare, et meurt plutôt que de se dérégler.

- **L'ADN version 3 : des introns signalés** (`chimie/adn.py`, `vtx-rs/src/adn.rs`, octet pour octet) :
  - le fichier est une suite de sections, chacune entre ses bornes : `GU nom N`, N lignes, puis `AG` (comme les bornes
    GU…AG d'un intron). La lecture saute une section qu'elle ne connaît pas sans rien analyser, et la garde telle
    quelle : un ADN d'une version future reste lisible. Un ADN de la version 2 se lit encore ;
  - sections : `mots`, `molecules`, `ombres`, `neutrons`, puis les introns : `isotopes`, `source`, `epigenome`.
- **Les isotopes lourds** : `= v * v / (2.0 * d) -> a lourd` marque une liaison critique.
  - Le code ne change pas (les mêmes mots avec ou sans `lourd`, dans les deux compilateurs) ;
  - la réaction qui la porte est un isotope lourd : ses mots gardent leurs neutrons dans l'ADN, même hors des
    frontières ; vtxc128 écrit `code.iso` (la place de chaque réaction lourde), vtx128.py la tire de ses étiquettes ;
  - à l'exécution, la patrouille la relit **à chaque entrée et à chaque sortie** (voir plus bas) ;
  - `python vtx128.py molecule` le dit ; la paillasse lit `lourd` sans le prendre pour une liaison.
- **Le texte gardé et la rétrotranscription** :
  - l'ADN garde le texte du programme (l'intron `source`) ;
  - `lugus transcrire PROG.adn` et `python chimie/adn.py transcrire PROG.adn` le recompilent : il doit redonner les
    mots, un pour un (« le texte : vrai »). Un texte retouché ne les redonne pas (« le texte : faux ») ; les mots de l'ADN
    restent alors seuls juges : les mots protègent le texte ;
  - `lugus pourquoi PROG.adn [liaison]` repart du texte gardé, s'il redonne bien les mots, et écrit le même arbre que
    depuis le `.vtx`. C'est la dette « provenance dans l'ADN », réglée sans ranger une seconde copie du code.
- **Les souvenirs et les cœurs ensemble** (`forge/forge128.py`) :
  - quand plusieurs atomes lourds d'une même vague gardent un souvenir, la forge fait d'abord regarder chacun le sien,
    puis fait réagir **ensemble, chacun sur son cœur**, ceux qui l'ont oublié ; un seul oublié réagit sur le fil
    principal ; puis chacun range son souvenir ;
  - le code émis pour la machine émulée ne change pas (les mêmes mots ; vtxc128 n'a rien eu à apprendre) ;
  - le même total que la machine émulée, sur un cœur (`VTX_COEURS=1`) comme sur plusieurs (`tests/test_reactions.py`).
    Le gain se mesure sur une machine qui a des cœurs libres : le conteneur où ce travail est fait n'en a qu'un, `essai-0.5u.bat`
    mesure les deux sur le PC.
- **L'épigénome : ce que le programme a appris, gardé dans l'ADN** :
  - les souvenirs sont ceux de fonctions pures : pour les mêmes entrées, toujours le même résultat. Ils restent donc
    justes d'une exécution à l'autre ;
  - `lugus apprendre PROG.adn [ENTRÉES…]` lance le programme, puis range ses souvenirs (`@3[#1000000..#1FFFFFF]`) dans
    l'intron `epigenome` ; `lugus PROG.adn` les reprend avant de lancer ; `lugus oublier PROG.adn` les retire ;
  - l'épigénome est lié à la signature des mots (un autre programme, même d'une lettre, ne le reprend pas) et porte la
    sienne : un souvenir abîmé fait oublier tout l'épigénome, il n'est jamais lu de travers ; une avarie de l'ADN
    réparée à la lecture le laisse en place ;
  - mesuré sur `alternance.vtx` : **995 389 instructions, puis 5 181** une fois appris (192 fois moins), le même
    résultat.
- **L'épissage alternatif : un ADN, plusieurs ARN** (`lugus transcrire PROG.adn PROG.arn --isoforme …`) :
  - *rapide* : les mots seuls ; *sur* : les mots et leurs témoins (la patrouille veille) ; *memoire* : les mots et
    l'épigénome ; *complet* : les deux ;
  - l'ARN porte une **coiffe**, la signature de ses mots, vérifiée avant de lancer : un ARN dont la coiffe ne reconnaît
    pas les mots est dégradé, jamais lancé ;
  - la **queue** des premiers ARN (un compte de lancements, usée : refaite depuis l'ADN) est retirée le soir même : la
    coiffe, vérifiée à chaque lancement, faisait déjà son travail. Un ARN ancien qui la porte encore se lit (la
    section est sautée).
- **La patrouille et l'apoptose** (`lugus PROG.adn`, `lugus PROG.arn` sûr ; **éteinte par défaut**, voir plus bas) :
  - pendant l'exécution, une colonne du code est relue toutes les 65 536 instructions (une colonne des isotopes lourds,
    puis une de l'ensemble, tour à tour), et une ronde entière quand le programme présente une image (la machine attend
    l'écran). Une empreinte de 64 bits par colonne, prise au lancement, dit vite si elle a changé ; alors seulement la
    lecture complète (ombre, neutrons, signatures) répare, et la triangulation confirme ;
  - une molécule ordinaire réparée par la patrouille a pu servir abîmée entre sa dernière relecture propre et sa
    réparation : la patrouille le dit (« elle a pu servir abîmée depuis le pas … ») ;
  - un **isotope lourd** est relu à son entrée : abîmé entre deux appels, il est réparé **avant de servir** ; il est
    relu à sa sortie : abîmé pendant qu'il servait, son résultat n'est pas sûr, et la machine s'arrête (l'**apoptose**)
    plutôt que de le rendre. Un isotope lourd ne rend donc jamais un résultat faux sans le dire ;
  - au-delà des témoins (neuf mots voisins abîmés), l'apoptose aussi ;
  - la patrouille n'ajoute aucune instruction au programme (les mêmes comptes, avec ou sans elle) ; sur une réaction
    lourde appelée 40 000 fois, elle coûte environ 40 % du temps (deux relectures par appel) : `lourd` se réserve au
    code critique ;
  - mesuré (`tests/test_patrouille.py`, avaries posées en pleine exécution par `LUGUS_AVARIE=PAS:MOT:BIT`) : sans
    patrouille, le résultat dérive (`inconnu`, ou un autre nombre) ; avec, il reste juste, ou la machine s'arrête en le
    disant. Aucun résultat faux rendu en silence.
- **Trois couches, pas vingt** (le même soir, après la question « est-elle utile au moins ? ») :
  - la patrouille protège contre une seule chose : un mot du code qui s'abîme en mémoire pendant que le programme
    tourne. Sur un PC, c'est presque impossible ; dans les essais, elle ne servait que parce que les avaries étaient
    posées exprès. Elle a un sens pour une machine qui tourne des jours sans surveillance, pour un programme qui peut
    écrire sur son code, et surtout pour la machine quaternaire à signal spectrométrique, où le bruit est la règle ;
  - elle est donc **éteinte par défaut**. Elle veille avec `--veille` (ou `LUGUS_PATROUILLE=1`), ou quand le programme
    a des isotopes lourds : écrire `lourd`, c'est dire « ce calcul doit être sûr », et l'on ne paie que là.
    `LUGUS_PATROUILLE=0` l'éteint toujours ;
  - mesuré : **la ronde seule ne coûte rien de visible** (mandel_reaction, 185 millions d'instructions, 2 820
    relectures : 4,81 s contre 4,75 s, dans le bruit). Le coût est celui des relectures à l'entrée et à la sortie
    d'une fonction lourde très appelée (les 40 % plus haut) ;
  - ce qui reste, chacun à sa place :

    | Quand | Contre quoi | Qui |
    |---|---|---|
    | au repos | un fichier abîmé sur le disque | les témoins : signature, ombre, neutrons (réparer) |
    | au lancement | un autre programme, un ARN dégradé | la signature des mots, la coiffe de l'ARN (refuser) |
    | en marche, sur demande | un mot abîmé pendant qu'il sert | la patrouille ; l'apoptose est son verdict |

  - les contrats, `exige`, les unités, les erreurs en Belnap et la rétrotranscription ne sont pas des sécurités de
    plus contre les bits abîmés : ils attrapent des fautes de raisonnement, et restent.
- **Le lecteur d'ADN écrit en vtx** (`chimie/adn.vtx`, embarqué dans lugus : `lugus relire PROG.adn [RELU.adn]`) :
  - la même lecture que `chimie/adn.py` et `vtx-rs/src/adn.rs`, dans le langage lui-même : les sections et leurs
    bornes, les signatures (le mélange de splitmix64 en entiers de 64 bits), les neutrons (le CRC-8, par une table),
    l'ombre (Reed-Solomon sur GF(256) : syndromes, Berlekamp-Massey, Chien, Forney, environ 450 lignes de vtx), la
    triangulation, le compte rendu de Lugus ligne pour ligne ; les introns qu'il ne connaît pas (isotopes, texte,
    épigénome) sont recopiés tels quels ; il écrit l'ADN relu comme Python l'écrit, octet pour octet ;
  - les deux compilateurs donnent ses mêmes mots (3 455) ; `tests/test_adn_vtx.py` le compare à Python sur les
    avaries de tous les genres : le même état, le même compte rendu, le même ADN relu (495 sur 495) ;
  - il ne dépend ni de Python ni de Rust : un Ogmios écrit en vtx pourra le lancer sur une machine fille, comme il
    lance vtxc128 ; la forge en fait un exécutable (`forge128.py chimie/adn.vtx`, les chemins en entrées) ;
  - **la vitesse, mesurée** (l'ADN de vtxc128, 173 166 mots, 3,7 Mo) : 11 s au début, 2,7 s aujourd'hui en vtx sur
    Lugus, **0,51 s forgé**, contre 0,14 s pour Lugus en Rust ; un programme ordinaire en 0,1 s. Ce qui a été fait,
    une idée à la fois, chacune mesurée (instructions de Lugus, puis instructions de la machine hôte) :
    - le lecteur, de 844 à 314 millions d'instructions :
      - l'ombre n'est plus recodée voie par voie : les quatre syndromes des seize voies sont calculés huit octets à la
        fois par moitié de mot (α fois huit octets en une fois : `((x << 1) & 0xFEFE…) ^ (((x >> 7) & 0x0101…) * 29)`) ;
        une colonne est intacte si et seulement s'ils sont nuls (le code est systématique : une seule ombre par
        données) ; le recodage ne sert plus qu'aux colonnes abîmées (−30 %) ;
      - les nombres sont lus dans la boucle même, le caractère courant dans un registre, sans appel par caractère ni
        `fin_de` (`lire_car` rend « tout à un » au bout du fichier), dans un `entier_128` (une multiplication, une
        addition) ;
      - ils sont écrits du chiffre fort au faible par une table des puissances de 10, un mot de 128 bits coupé en
        morceaux de 19 chiffres par la division de l'`entier_128` (signé : ⌊x / 10^19⌋ = ⌊⌊x / 2⌋ / (5·10^18)⌋) ;
      - le CRC-8 lit deux octets à la fois (une table de 65 536 : `CRC2[x | y << 8] = CRC[CRC[x] ^ y]`) ;
      - une faute corrigée en passant : le second chemin était rangé en `CHEMIN + 2000`, hors de la carte, là où la
        table est venue se mettre ; il a sa place (`CHEMIN2`), et un chemin trop long est coupé, pas débordé ;
    - Lugus, deux fois moins d'instructions de l'hôte par instruction (callgrind : 194 → 94), pour tout programme :
      - la demi-instruction est lue en ligne quand sa page est en cache ;
      - seize pages en cache par étage au lieu d'une (le lecteur passe sans cesse d'une zone à l'autre) ;
      - l'écriture sans le contrôle des brins sur une page qui n'en a pas (le code, marqué ADN au lancement, reste
        vérifié) ;
      - les sauts, LD, ST, LDF, STF, PUSH, POP, MOV et ETG ont leur chemin court ; le grand `match` est à part, il
        ne fait plus payer sa préparation aux autres ;
      - la boucle va d'un contrôle au suivant (la limite, l'arrêt, une avarie, la ronde) sans les refaire à chaque pas ;
      - essayé et rendu : la boucle serrée avec l'ancien grand pas (plus lente), forcer l'inlining de la mémoire dans
        le `match` (plus lent) ;
    - ce qui reste : le compilateur met des PUSH/POP autour de chaque opération, même quand l'opérande est une
      constante, et ne donne un registre qu'aux premières variables ; un regard à la lunette dans les deux
      compilateurs (les mêmes mots) en ôterait une bonne part, pour tous les programmes (à mesurer) ;
  - il lit la version 3 seulement, un million de mots au plus.
- **Essai : des neutrons quaternaires ?** (`chimie/essai_neutrons.py`, expérimental, rien n'est changé dans l'ADN) :
  - la question de l'utilisateur : lire par 4, en quaternaire, plutôt que deux octets à la fois ; une table qui
    avale quatre octets aurait 4,3 milliards d'entrées, et « par tranches de 4 » (quatre tables) demande quatre
    lectures pour quatre octets, contre deux aujourd'hui : plus lent ; la vraie question est donc le neutron lui-même ;
  - quatre candidats de 8 bits (4 quits, la taille du format ne change pas) : le CRC-8 d'aujourd'hui ; le même,
    les bits lus dans le sens des octets ; un **CRC sur GF(4)** (le mot vu comme 64 quits, divisé par le meilleur des
    192 générateurs de degré 4 : x⁴ + x² + ωx + 1) ; le **pli ℤ/4** (les 64 quits sommés en 4 par `addm4`) ;
  - ce qu'ils voient (un mot au hasard par erreur ; 20 000 tirages par genre au hasard) :

    | erreur | CRC-8 | CRC-8 ordonné | CRC GF(4) | pli ℤ/4 |
    |---|---|---|---|---|
    | un bit, un quit, un octet remplacé | 100 % | 100 % | 100 % | 100 % |
    | deux bits | 99,988 % | 99,988 % | **100 %** | 91,1 % |
    | deux quits | 99,99 % | 99,98 % | **100 %** | 92,0 % |
    | rafale de 3 à 8 bits | 99,805 % | **100 %** | **100 %** | 100 % |
    | trois bits | **100 %** | **100 %** | 99,66 % | 98,7 % |
    | quatre bits | 99,22 % | 99,25 % | **99,62 %** | 97,8 % |
    | huit bits épars | 99,20 % | 99,19 % | **99,64 %** | 99,4 % |
    | le mot remplacé | 99,63 % | 99,66 % | 99,58 % | 99,59 % |

    (au hasard, l'idéal pour 8 bits est 99,61 %) ;
  - ce qu'ils coûtent sur Lugus, par mot : le CRC-8 par la table de deux octets, 81 instructions (et 950 000 une fois
    pour la table) ; le CRC GF(4) est linéaire sur GF(2), il se calcule par la même table, **pour le même prix** ; le
    pli ℤ/4, 30 instructions sans table ; la valeur de `addm4` sur Lugus est celle du modèle en Python ;
  - lecture honnête : les rafales manquées venaient de l'ordre des bits, pas du binaire (le CRC-8 ordonné les voit
    toutes) ; ce que le quaternaire apporte en propre : toutes les erreurs de deux bits et de deux quits (le bruit
    d'un canal quaternaire touche des quits), et une détection au niveau de l'idéal au-delà de trois bits ; ce qu'il
    perd : le CRC-8 voit tout nombre impair de bits faux (son facteur x + 1), pas lui ; le pli ℤ/4, quatre fois moins
    cher, laisse passer une erreur double sur onze : trop faible seul ;
  - **décidé (3 novembre) : l'ADN version 4, aux neutrons quaternaires** (`VTXADN04`) :
    - le neutron d'un mot : le reste de ses 64 quits (le plus fort d'abord) divisé par g(x) = x⁴ + x² + ωx + 1 sur
      GF(4) ; par une table d'un octet en Python et en Rust (`crc_gf4`), de deux octets dans le lecteur en vtx
      (`CRC2[x << 8 | y] = T[T[x] ^ y]`, construite après l'en-tête, selon la version) ;
    - tout ADN nouveau est en version 4 ; un ADN lu garde sa version (un ADN de la version 3 est relu, réparé et
      réécrit en version 3, octet pour octet, ses neutrons CRC-8 gardés) ; la version 2 se lit toujours ;
    - l'ARN sûr porte ses neutrons : `VTXARN02` (quaternaires) ; `VTXARN01` (CRC-8) se lit toujours ;
    - vérifié : Python et Lugus rangent le même ADN version 4, octet pour octet ; un ADN version 3 lu vrai, réécrit
      à l'identique, un mot abîmé désigné et réparé ; le lecteur en vtx lit les deux versions comme Python (132 avaries,
      dont une copie en version 3), les deux compilateurs donnent ses mêmes mots (3 638).
- **Ce qui reste** : Ogmios lance l'ADN sans la patrouille (elle est dans `lugus`) ; la patrouille relit le code, pas
  les données (un tableau abîmé n'est pas vu) ; le lecteur en vtx prend tout l'étage 2 (il tourne seul, sur sa machine)
  et la rétrotranscription reste faite par Lugus.


## 10. Le code produit (3 novembre)

Décidé avec l'utilisateur, dans l'ordre : le code produit, les réactions incomplètes, les flux, puis Gobannos et la
paillasse améliorée.

- **Les registres des variables** : mesuré avant de changer. Les quatre variables les plus utilisées d'une fonction
  (pondérées par la profondeur des boucles, l'`entier_128` compris) vivent déjà dans R9 à R12 ; un cinquième (R15,
  libre) ne gagne que 0 à 1 % (lecteur d'ADN −0,1 %, chute −1 %, mandel 0). Rien n'est changé.
- **Deux règles d'épissage de plus** (vtx128.py et vtxc128, les mêmes mots) :
  - *garde* : `PUSH Ra ; S ; POP Ra` → `S`, quand S (des instructions simples, huit au plus) n'écrit pas Ra et ne
    touche ni la pile ni le cadre : Ra garde sa valeur sans passer par la pile ;
  - *const128* : `LDI Rx,a ; LDIH Rx,b ; MOV Ry,Rx` → `LDI Ry,a ; LDIH Ry,b` (Rx mort après) ; pour cela `LDIH` n'est
    plus une barrière : il lit et écrit son registre (vtxc128 : une sorte à lui, la 13), sauf pour la règle échange,
    qui ne saurait renommer sa lecture ;
  - mesuré (instructions de Lugus) : mandel_reaction −22,6 % (185 → 143 millions), freinage −7 %, lecteur d'ADN
    −3,3 % ; les autres exemples inchangés ; vtxc128 lui-même passe de 173 166 à 172 395 mots ;
  - vérifié : la suite de vtx128.py (138 compilations), les programmes au hasard, le point fixe (M0 = M1 = M2), le
    compilateur embarqué renouvelé, les réactions (avec la provenance).
- **Ce qui reste du code produit** : les constantes flottantes rechargées à chaque tour de boucle ; la comparaison qui
  fabrique une logique avant d'être testée (`FLE` puis `CMP` puis `JZ`) ; les PUSH/POP qui entourent un calcul qui
  écrit le registre gardé (il faudrait un autre registre libre, ce que fait déjà la règle pile dans un cas).
- **Un trou de la patrouille, trouvé et fermé** (en route) :
  - le test de la patrouille posait ses avaries à des places et des pas réglés à la main ; avec le code plus court,
    elles tombaient ailleurs. Réécrit sans dépendre de la disposition : une avarie est choisie parce qu'elle fausse
    l'ARN rapide (sans témoins, critère indépendant de la patrouille), et pour l'isotope lourd on exige, à chaque pas
    d'une fenêtre, que la machine ne rende **jamais** un résultat faux ;
  - il a trouvé un vrai trou : un isotope relu sain à son entrée, abîmé au pas suivant pendant qu'il sert, sur une
    instruction qui fait sortir l'exécution **sans passer par son RET** : le contrôle de sortie ne venait jamais, la
    valeur fausse sortait (« 48 »), et l'entrée suivante réparait en disant « il n'a pas servi abîmé » ;
  - fermé en deux temps : la patrouille compte, pour chaque isotope lourd, les entrées dont la sortie n'a pas été vue ;
    un isotope trouvé abîmé alors qu'il sert (à une entrée, à un tic) n'est plus réparé mais arrête la machine ; et
    une nouvelle ronde, **avant chaque effet** (`sortie`, une écriture sur un canal), relit les isotopes qui servent :
    rien d'incertain ne touche le monde (la règle des erreurs en Belnap, section 8) ;
  - balayé : chaque mot de l'isotope, trois bits, 120 pas de suite (7 560 avaries) : 3 150 fois le résultat juste,
    4 410 fois l'apoptose, **aucune fois un résultat faux** ; sans avarie, le même nombre d'instructions avec ou sans
    patrouille.
- **La fiche comparée** (`mesures/mesurer128.py 3`, médiane de trois lancements, lancement du processus compris ;
  `mesures/mesures-lugus-4.json`) ; Python 3 ajouté, et les instructions de Lugus :

  | programme | C -O2 | Rust -O | Python 3 | vtx forgé (Lugus) | vtx sur Lugus | instructions de Lugus |
  |---|---|---|---|---|---|---|
  | fib (appels) | 0,005 s | 0,011 s | 0,35 s | 0,017 s | 1,09 s | 112,8 M |
  | crible (mémoire) | 0,037 s | 0,033 s | 1,44 s | 0,063 s | 1,34 s | 158,4 M |
  | mandel (flottants) | 0,022 s (32 b) ; 1,07 s (`__float128`) | 0,021 s | 1,69 s (64 b) | 1,24 s (128 b) ; 0,86 s (64 b) | 3,91 s | 139,4 M |
  | tri rapide | 0,053 s | 0,052 s | 1,33 s | 0,078 s | 1,04 s | 135,0 M |
  | ADN, deux brins | 0,026 s | 0,020 s | 7,97 s | 0,026 s | 0,38 s | 45,1 M |
  | neutrons, CRC-8 | 0,009 s | 0,013 s | 1,95 s | 0,069 s | 0,50 s | 78,0 M |
  | neutrons, GF(4) | 0,009 s | 0,018 s | 1,76 s | 0,050 s | 0,64 s | 80,3 M |

  - forgé, vtx est au niveau du C sur l'ADN, à 1,5 à 1,7 fois sur le tri et le crible, 3 fois sur fib ; mandel en
    128 bits forgé (1,24 s) est proche du C en `__float128` (1,07 s) ;
  - sur Lugus (émulé), vtx bat Python sur l'ADN (21 fois), les neutrons (3 à 4 fois), le tri ; à égalité sur le
    crible ; derrière sur fib (3 fois) et mandel (2,3 fois, mais en 128 bits contre 64) ;
  - les temps sous 0,05 s sont surtout le lancement du processus.
- **Le CRC quaternaire : vitesse, instructions, puissance** :
  - Lugus n'a pas de décalage par une valeur écrite : la table du CRC GF(4) est rangée **décalée de 8 bits**
    (`T2[x << 8 | y] = T[T[x] ^ y] << 8`), chaque pas est un OU exclusif et une lecture, comme le CRC-8 (fait aussi
    dans le lecteur d'ADN en vtx) ; sans cela, 25 instructions de plus par mot ;
  - en passant : l'attribution des registres se fait pour toute la fonction, pondérée par la profondeur des boucles ;
    la construction des tables (deux boucles imbriquées de 256) prenait les registres de la boucle chaude (un million
    de tours) ; les tables mises dans une fonction à part, 93 → 77 instructions par mot. À reprendre dans le
    compilateur (les registres par boucle, ou pondérés par le nombre de tours quand il est connu) ;
  - **vitesse** : égale (C, Rust, forgé, Lugus : dans le bruit de la mesure) ; **instructions** : +3 % sur Lugus
    (80,3 M contre 78,0 M : le premier pas et le décalage final) ;
  - **puissance** sur les avaries de l'ADN (`chimie/essai_neutrons_adn.py`, 150 par genre et par programme, quatre
    programmes) : égale ; les deux désignent 99,3 à 100 % des mots abîmés (un mot entier changé : le hasard, une chance
    sur 256), les mêmes réparations (rafale de quatre mots : 89,5 % contre 89,3 % ; seize mots : 2,2 % contre 2,3 %),
    jamais de travers ; l'avantage du quaternaire est sur les petites erreurs (deux bits, deux quits : 100 % contre
    99,99 % ; quatre bits : 99,62 % contre 99,22 %), le bruit d'un canal quaternaire, que les genres d'avaries de
    l'ADN (des mots entiers) ne contiennent pas encore.

## 11. Les vibrations (4 novembre)

Idée de l'utilisateur : les atomes et leurs liaisons vibrent (les vibrations des réseaux d'atomes, les phonons : chaînes
monoatomiques et diatomiques, modes acoustiques et optiques, une fréquence, un sens) ; une bibliothèque par atome ; une
fréquence, un sens, une signature ; dans le cube, les chaînes nommées dans ce sens ; et, contre les molécules
isospectrales, l'accroche : un atome se retrouve d'un code à l'autre, une vibration commune fait une accroche, la
vibration totale garde l'intégrité de chaque groupe de blocs.

- **Les registres en graphe de liaisons** (vtx128.py et vtxc128, les mêmes mots) :
  - chaque variable est un atome ; elle vibre de la première à la dernière instruction de premier niveau du corps où
    elle apparaît (var, la cible d'un soit ou d'une affectation, la variable d'un pour : les seules places où le
    générateur touche une variable) ; une boucle de premier niveau est un seul bloc, ce qui couvre d'office ce qui passe
    d'un tour à l'autre ; les deux compilateurs comptent ces instructions de la même façon, quelle que soit la forme de
    leurs arbres (essayé d'abord au nœud près : même gain, mais une parité fragile) ;
  - deux atomes qui vibrent en même temps sont liés : deux registres différents (le mode optique) ; les atomes passent
    par fréquence décroissante (les usages pondérés par les boucles), chacun prend le premier registre libre de ses
    voisins, ou reste dans le cadre ; quatre registres portent plus de quatre variables ;
  - mesuré (instructions de Lugus, mêmes sorties) : −4,8 % sur la fiche et les exemples ; neutrons aux tables dans
    principal −17 % et −25 % (le défaut d'hier : réglé par le graphe seul) ; crible −6,3 % ; relevés −8,3 % ; chute
    −2,9 % ; lecteur d'ADN −1,9 % ; fib, mandel, tri inchangés (toutes leurs variables vivent ensemble) ;
  - essayé et rendu : la vraie fréquence d'une boucle (son nombre de tours quand ses bornes sont écrites) : −0,0 % de
    plus, le graphe fait déjà tout ;
  - en route, dans vtxc128 : « pas encore vue » marquée −1, et `vfin < k` est sans signe : la période ne s'ouvrait pas
    et deux variables vivantes partageaient un registre ; vu par un petit programme comparé dans les deux compilateurs.
- **La signature par les vibrations, la parade** (`chimie/essai_vibrations.py`, expérimental) :
  - la vibration locale d'un atome : ses chemins fermés de longueur 1 à n, (Aᵏ)ᵢᵢ (sa part dans chaque mode, pondérée
    par la fréquence) ; son élément (sa masse) ; propagée trois tours le long des liaisons ; la signature : l'ensemble
    trié des vibrations finales et leur total ; tout en entiers (les mêmes dans tous les compilateurs) ;
  - mesuré sur tous les graphes de 1 à 7 sommets (1 252), puis 3 756 molécules aux éléments C, H, O, N : paires de
    molécules différentes à la même signature : spectre ordinaire 64, spectre des vibrations 76, avec les masses 22 ;
    **la parade : 0, sans et avec les éléments** ;
  - l'intégrité : une liaison ajoutée ou retirée est vue 2 140 fois sur 2 140 ;
  - l'accroche : deux codes qui partagent un groupe de cinq atomes ont 2,5 vibrations en commun en moyenne, 0 sans lui ;
  - la limite, honnêtement : deux graphes fortement réguliers de mêmes paramètres (la tour 4×4 et le graphe de
    Shrikhande, 16 sommets) vibrent exactement de la même façon, atome par atome : même signature. Ce qui les sépare :
    les groupes de quatre atomes tous liés (8 contre 0). Suite possible : des harmoniques (les petits cycles et les
    groupes autour de chaque atome) ; dans du code, les éléments brisent presque toujours cette symétrie ;
  - la signature de l'ADN (splitmix sur les mots) reste la garantie ; la signature par les vibrations sert à
    l'accroche (retrouver une partie commune, un module, une molécule déjà vue) et à l'intégrité de la structure ;
  - à venir : la bibliothèque par atome, le sens (longitudinal, transversal) et les chaînes nommées dans le cube.

## 12. Essai : l'entier de 128 bits par défaut (5 novembre)

Mesuré sans rien changer au langage : les mêmes programmes de la fiche, compilés normalement, puis avec leurs
opérations entières à toute la largeur (128 bits ; ETG reste à 64 : l'étage est dans les bits hauts d'une adresse de
64 bits) ; forgés normalement, puis avec l'entier en `u128` (une copie de la forge, le temps de l'essai). Médiane de
cinq lancements.

| programme | Lugus 64 | Lugus 128 | écart | forgé 64 | forgé 128 | écart | sorties |
|---|---|---|---|---|---|---|---|
| fib | 1,01 s | 1,18 s | +17 % | 0,021 s | 0,011 s | (bruit) | mêmes |
| crible | 1,06 s | 2,06 s | +95 % | 0,079 s | 0,070 s | −11 % | mêmes |
| tri | 0,95 s | 1,19 s | +26 % | 0,080 s | 0,083 s | +4 % | mêmes |
| adn | 0,36 s | 0,56 s | +56 % | 0,027 s | 0,019 s | (bruit) | mêmes |
| mandel (flottants) | 3,74 s | 3,78 s | +1 % | 1,16 s | 1,19 s | +2 % | mêmes |
| neutrons (xorshift) | 0,50 s | 17,2 s | ×34 | 0,04 s | 3,9 s | ×90 | **autres** |

- les instructions de Lugus ne changent pas (une instruction de 128 bits reste une instruction) ;
- **forgé, le 128 bits ne coûte presque rien** (addition, comparaison : le même prix sur le processeur hôte ; la
  division coûterait plus, il n'y en a pas ici) ;
- **sur Lugus, +17 à +95 %** : le chemin court de la machine (`court64`) ne sert qu'à la largeur 64 ; les opérations
  de 128 bits passent par le grand `match` et l'arithmétique `u128` de l'hôte ; un chemin court de 128 bits le
  réduirait (à mesurer) ;
- **le vrai coût est le sens** : tout ce qui compte sur le débordement à 64 bits (le hasard xorshift et splitmix, les
  hachages, le CRC, la signature de l'ADN, le lecteur d'ADN en vtx) donne d'autres nombres ; les neutrons ci-dessus
  sortent de leur table (des valeurs plus grandes que 2⁶⁴ comme indices), d'où la lenteur et le résultat faux ;
- à décider : garder 64 par défaut (le 128 sur demande, `entier_128`), passer à 128 (en écrivant `entier_64` partout où
  le débordement compte, et un chemin court de 128 bits dans Lugus), ou le choix par programme.

## 13. Belenos, premier pas : le fluide et le tapis roulant (7 novembre)

Décidé avec l'utilisateur : Belenos d'abord (l'autonomie, Gobannos, n'ajoute pas de capacité) ; la démonstration est un
fluide (la méthode de Boltzmann sur réseau) : une grille de cellules, chacune porte neuf populations qui partent vers
ses voisines ; un pas = la collision (chaque cellule seule : une vague) puis la propagation (vers la voisine : un pont).

- **Le tapis roulant** (idée de l'utilisateur : les Hex qui descendent vers l'ombre, en boucle sans fin) : au lieu de
  déplacer les données, on déplace le repère ; chaque direction a son origine, qui recule d'un cran à chaque pas ; la
  propagation ne déplace aucune donnée (un seul tampon). Les codes rapides des cartes graphiques font de même.
- `belenos/fabriquer_fluide.py` fabrique les deux versions (la collision écrite une fois) : `fluide_copie.vtx` (A : les
  populations poussées dans la voisine, deux tampons) et `fluide_tapis.vtx` (B : le tapis roulant) ; 128 × 64 cellules,
  bouclé, en entiers à virgule fixe de 24 bits (les mêmes nombres sur Lugus, forgé, et plus tard sur la carte : les
  flottants des cartes diffèrent au dernier bit) ; `belenos/fluide_ref.py` : la même arithmétique en Python, et une
  image de la vorticité.
- **Mesuré, 50 pas** (les mêmes nombres partout, la masse gardée au bit près) :

  | | A, la copie | B, le tapis roulant |
  |---|---|---|
  | instructions de Lugus | 224,1 M | 228,4 M (+1,9 %) |
  | sur Lugus | 1,37 s | 1,21 à 1,49 s (dans le bruit) |
  | forgé | 33 ms | **15 à 20 ms (deux fois plus vite)** |
  | mémoire | deux tampons | **un seul** |

- **La précision, trouvée en route** : en 16 bits, les arrondis vers le bas retiraient de la quantité de mouvement à
  chaque pas (−13 % de vitesse en 200 pas, contre 0 % pour la physique) : le fluide s'éteignait en bruit. En 24 bits :
  0,0 %. Et la viscosité réglée (ω = 31/16, un nombre de Reynolds d'environ 240) : au bout de 2 500 pas, les deux
  couches de cisaillement s'enroulent en tourbillons (Kelvin-Helmholtz), de sens contraires
  (`belenos/tourbillons_2500.png`).
- `tests/test_fluide.py` (dans `verifier.py`) : les deux versions et la référence, les mêmes nombres, sur Lugus et forgées.
- **La suite** : l'ombre comme cache (les cellules fantômes au bord des blocs : le pas suivant préparé pendant que le
  pas courant est projeté) et les repères brillants par étage (des Hex de valeur connue, relus à chaque tour : le
  tapis est-il calé ?) ; le fluide affiché dans la toile, aux couleurs du cube ; puis le même programme en SPIR-V sur
  la carte (Vulkan), comparé à Lugus.

## 14. L'ombre comme cache, en nuances (7 novembre)

Question de l'utilisateur : faut-il plusieurs caches ? et l'ombre peut aller du plus noir au plus blanc, seulement si
le nombre de caches l'exige.

- **Oui, d'ordinaire il y en a plusieurs**, du plus proche (petit, immédiat) au plus loin (grand, lent) : dans un
  processeur, les registres, puis L1 (48 Ko par cœur ici), L2 (2 Mo), L3 (260 Mo sur la machine d'essai), puis la
  mémoire ; dans une carte graphique, les registres, la mémoire partagée d'un bloc (48 à 100 Ko), L2, puis la mémoire
  de la carte. Ceux du processeur se remplissent seuls ; ceux que Vercintorix tient lui-même : les registres (les
  vibrations, § 11) et les pages de Lugus.
- **Mesuré d'abord** (`belenos/mesurer_ombre.py`, le fluide forgé, environ quatre millions de cellules par mesure) : le
  temps par cellule restait le même jusqu'à 256 × 256, puis était multiplié par 35 à 512 × 512. Ce n'était pas le
  processeur (les 144 Mo du tapis 1024 × 1024 tiennent dans son L3) mais **l'ombre de Lugus elle-même** : seize cases de
  pages ; à 512 × 512, chaque direction occupe quatre pages, neuf directions espacées de quatre pages tombaient sur
  quatre cases seulement et se chassaient ; chaque page manquée était cherchée dans une table hachée (une centaine de
  nanosecondes).
- **Trois nuances, dans `vtx-rs/src/spu128.rs`** (et la forge, `forge/noyau_forge128.rs`) :
  - **noire** : les seize cases ; la case d'une page est son numéro plié par quatre bits, `(k ^ k>>4 ^ k>>8) & 15` : des
    pages qui se suivent gardent des cases différentes, comme avant, et des pages espacées de 16, 64 ou 256 ne tombent
    plus dans la même ;
  - **grise** : l'annuaire, une table par étage rangée par le numéro de page (les 65 536 premières : 2³² mots) ; une
    page sortie des seize cases s'y retrouve en une lecture ; vidé quand un cube est jeté ;
  - **blanche** : la table hachée, et les fichiers du cube sur le disque (la première lecture d'une page).
- **Mesuré, forgé, en nanosecondes par cellule et par pas** (le départ et le compte inclus : sensibles à 1024 × 1024,
  trois pas seulement) :

  | grille (pages du tapis) | tapis avant | + annuaire | + pli | copie avant | copie après |
  |---|---|---|---|---|---|
  | 128 × 64 (1) | 31,0 | 30,1 | 31,6 | 50,3 | 54,5 |
  | 256 × 256 (9) | 39,6 | 35,6 | 38,0 | 47,9 | 50,0 |
  | 512 × 512 (36) | 1 395,6 | 237,6 | **54,6** | 1 526,2 | **65,7** |
  | 1024 × 1024 (144) | 1 816,8 | 267,1 | **82,2** | 1 974,0 | **104,1** |

  Les petites grilles ne changent pas (à quelques pour cent près : le bruit de la machine d'essai) ; les grandes vont 22
  à 25 fois plus vite. Sur Lugus (l'émulateur, où le décodage domine), 512 × 512, deux pas : la copie 3,25 → 2,79 s, le
  tapis 3,49 → 3,13 s (−11 à −14 %). Les mêmes nombres partout.
- **Essayé et écarté** : soixante-quatre cases au lieu de seize (512 × 512 réglé, mais 1024 × 1024 toujours 1 820 ns :
  la grille dépasse tout nombre fixe de cases, d'où l'annuaire) ; la case par le nombre d'or (bon sur les grandes
  grilles, mais des pages qui se suivent se chassaient : la copie 256 × 256 passait de 45 à 75 ns).
- **La quatrième nuance n'est pas nécessaire sur le processeur** : une ombre logicielle (le fluide découpé en blocs, des
  cellules fantômes au bord) n'apporterait plus rien ici. Elle le sera sur la carte : la mémoire partagée d'un bloc est
  une ombre qu'on remplit à la main ; elle viendra avec SPIR-V.
- `tests/test_fluide.py` : un grand fluide (512 × 512, 36 pages, donc par l'annuaire), les mêmes nombres sur Lugus et
  forgé, la masse gardée.

## 15. Les tuiles : une ombre par étage, côte à côte (7 novembre)

Idée de l'utilisateur : le cache se fait déjà par les étages du cube ; l'ombre est un cache de diffusion. Au lieu de
multiplier les ombres en profondeur (§ 14), les multiplier en surface : la première ombre porte les valeurs du premier
étage de Hex, la deuxième celles du deuxième, et ainsi de suite ; les ombres collées en grille forment l'image ; on
calcule par groupes d'étages, en cycles, sans viser le 4K.

- **Cohérent, et connu sous un autre nom** : c'est le rendu par tuiles des cartes graphiques des téléphones (Apple,
  Mali, PowerVR) : l'écran en tuiles, chaque tuile calculée en entier dans une petite mémoire rapide, écrite une fois.
  La méthode la plus économe en énergie et en bande passante.
- **Trois justesses** : la résolution est le nombre de tuiles fois la taille d'une tuile (64 étages de 64 × 64 points
  = 512 × 512), et la taille d'une tuile est celle que tient la mémoire rapide (48 à 100 Ko sur une carte) ; une tuile a
  besoin d'une marge prise chez ses voisines (le fluide passe la frontière) ; les étages de Lugus sont des espaces
  d'adresses, l'idée vaut pour les étages de Hex du cube.
- **Ce que l'idée ajoute** : les vagues de tuiles permettent de ne recalculer que les tuiles qui changent, et de
  calculer finement là où l'œil regarde ; les repères brillants d'un étage serviraient aux coutures.
- **L'essai, `belenos/fluide_tuiles.vtx`** (C, fabriqué par `fabriquer_fluide.py`) : 128 × 64 cellules en tuiles ;
  chaque tuile a son ombre (la tuile et une marge d'une cellule, bouclée comme les autres versions), les ombres rangées
  côte à côte ; la collision est faite dans l'ombre, puis chaque cellule tire ses populations de l'ombre vers le tampon
  d'arrivée ; les tuiles calculées par vagues de quatre, **dans le désordre** (la tuile n° 9k mod 16) : les mêmes nombres
  que A, B et la référence, sur Lugus et forgé (`tests/test_fluide.py`). L'ordre ne compte pas : chaque tuile ne lit que
  le tampon de départ ; c'est ce qui permet de les donner à des cœurs ou à une carte, en parallèle.
- **Mesuré** (`belenos/mesurer_tuiles.py` ; Lugus, 50 pas ; forgé, 488 pas) :

  | version | calcul par cellule rendue | instructions de Lugus | forgé |
  |---|---|---|---|
  | A, la copie | 1,00 | 224,1 M | 187 ms |
  | B, le tapis roulant | 1,00 | 228,4 M | **121 ms** |
  | C, tuiles 8 × 8 | 1,56 | 390,6 M | 521 ms |
  | C, tuiles 16 × 16 | 1,27 | 323,6 M | 421 ms |
  | C, tuiles 32 × 16 | 1,20 | 307,6 M | 381 ms |
  | C, tuiles 64 × 32 | 1,10 | 285,3 M | 357 ms |

- **Lecture honnête** : sur le processeur, les tuiles coûtent plus (la marge recalculée, et chaque population passe par
  l'ombre : écrite puis relue) ; le tapis roulant reste le plus rapide. Les instructions suivent la marge, le temps
  forgé un peu plus. Le gain des tuiles n'est pas sur le processeur (son cache se remplit seul, § 14) : il est sur la
  carte, où l'ombre d'une tuile tient dans la mémoire partagée d'un bloc et où les tuiles tournent ensemble, et dans
  les tuiles qu'on ne recalcule pas. Prochaine étape : le tapis roulant à l'intérieur de chaque tuile (les deux idées
  réunies), puis l'affichage tuile par tuile dans la toile.

## 16. Décision et une autre stratégie : l'accordéon (7 novembre)

- **Décidé** : on garde le tapis roulant (le plus rapide, la moitié de la mémoire) et on avance dans cette direction ;
  les tuiles restent un outil pour la carte, pas la voie principale.
- **L'accordéon** (idée de l'utilisateur, d'après les meurtrières des bunkers et leurs gradins qui font ricocher les
  balles : l'ouverture s'élargit marche après marche) : une tuile pour le centre de l'image, la suivante pour la partie
  étendue autour, la suivante plus loin encore ; le centre toujours net, chaque étage de tuile une extension de l'image.
  Cohérent, et connu ailleurs : le rendu fovéal (net là où l'œil regarde), les clipmaps des terrains et les cascades des
  ombres portées. Ce qui le rend propre au cube : chaque étage a **le même nombre de cases** et couvre deux fois plus
  large (le pas de ses cases double) ; le coût est le même à chaque étage, le champ double. Six étages de 64 × 64 : un
  centre à pleine finesse, un champ 32 fois plus large, pour le prix d'une image de 157 × 157.
  À essayer plus tard : l'affichage du fluide en accordéon (le centre net, les étages lointains moyennés), et un
  fluide en accordéon (des grilles emboîtées, plus fines au centre : le raffinement de maillage).

## 17. Belenos peint : « Les puys au soir » (7 novembre)

Demandé : une image de démonstration faite avec Belenos seul, en 2K, un paysage de l'Auvergne ; pourquoi pas le 4K.

- **`belenos/auvergne.vtx`** (vtx seul : ni bibliothèque, ni carte, ni Python) :
  - **un vrai relief** : une grille de 1024 × 1024 hauteurs (en 1/256 de case) : la plaine vallonnée, treize puys (le
    puy de Dôme en dôme de lave, arrondi ; les cônes de scories aux flancs droits et à cratère ; le puy de la Vache
    égueulé, son cratère ouvert vers nous), un lac de cratère, les prés qui descendent vers lui ; la lumière du soleil
    par la normale de chaque case (une racine carrée entière, Newton) ;
  - **le rendu par colonnes** : chaque colonne de l'image lance un rayon qui avance du plus près au plus loin et peint de
    bas en haut ce qu'il découvre (un tampon de hauteur par colonne : rien n'est peint deux fois ; la méthode de
    Comanche, 1992) ; la brume selon la distance ;
  - le ciel du soir (le dégradé, la lueur et le disque du soleil, des bancs de nuages éclairés dessus, ombrés dessous :
    des nappes de bruit en entiers), les monts Dore au loin et la neige sur leurs crêtes ;
  - **le reflet** : un point d'eau prend la couleur du point symétrique par rapport à l'horizon (le rayon renvoyé par
    l'eau monte autant qu'il descendait), troublée de rides, plus fort au loin ;
  - posés dans la scène **avec leur profondeur** (chaque point de l'image garde la sienne) : des arbres (couronne en
    touffes, éclairée du côté du soleil, quelques feuilles rousses), un buron (pierre sèche, toit de lauzes) et des
    vaches Salers (robe acajou, cornes en lyre), du plus loin au plus près ;
  - **le PNG écrit par le programme** : la signature, IHDR, IDAT (zlib, blocs « stockés », Adler-32), IEND, chaque
    morceau avec son CRC-32 (une table) ; dans un **fichier d'octets** : `ouvrir_ecriture("octets:nom")` (nouveau, dans
    `vtx-rs/src/spu128.rs` et `spu128/spu128.py` : chaque mot écrit donne un octet ; les fichiers de texte ne savaient
    porter que des caractères).
- **Mesuré** (2048 × 1080) : **Lugus 7,5 milliards d'instructions, 57 s ; forgé 0,6 s ; la même image, octet pour
  octet** (`tests/test_tableau.py --lugus`). Le PNG fait 6,6 Mo (sans compression).
- **Le 4K** : rien ne l'empêche ; `constante K = 2` (toutes les mesures de l'image en dépendent) donne 4096 × 2160,
  forgé en 2,4 s. Ce qui se voit alors : la grille du relief (1024 × 1024) devient trop grossière de près (les
  champs en marches) ; il faudra une grille de 2048 × 2048, ou l'accordéon (§ 16 : fine au centre, plus grossière au
  bord) ; et le PNG sans compression fait 26 Mo : une vraie compression (deflate) est à écrire.
- `tests/test_tableau.py` (dans `verifier.py`) : forgé, le programme écrit un PNG juste (relu par Python : les CRC, le
  zlib, l'Adler-32), de 2048 × 1080 points, dont l'empreinte est celle qu'il a sortie ; `--lugus` : Lugus peint la même.

## 18. Pour que Belenos dépasse DirectX : les propositions (7 novembre)

DirectX, c'est une interface de Microsoft, ses pilotes (fournis par AMD, Nvidia, Intel) et son langage de nuanceurs
(HLSL, compilé en DXIL). On ne le remplace pas en réécrivant les pilotes ; on le dépasse sur ce qu'il ne sait pas faire,
en passant par la porte commune à toutes les cartes.

1. **Belenos écrit du SPIR-V** (le langage intermédiaire des cartes, celui de Vulkan), directement depuis vtx, sans
   HLSL ni GLSL : une sortie de plus du compilateur, comme la forge. SPIR-V tourne sur Vulkan partout (Windows, Linux,
   Android), et Microsoft a annoncé (septembre 2024) que DirectX l'adopterait comme format d'échange à partir du
   Shader Model 7 : les nuanceurs de Belenos deviendraient aussi des nuanceurs DirectX.
2. **Les mêmes nombres partout** : DirectX ne garantit pas que deux cartes donnent la même image (les flottants
   diffèrent au dernier bit selon le fabricant). Belenos calcule en entiers et en flottants arrondis exactement (comme
   Lugus et la forge aujourd'hui) : la même image au bit près sur toutes les cartes, et vérifiable par son empreinte.
   C'est la démonstration la plus forte, et DirectX ne peut pas la faire.
3. **Les vagues, l'ombre et le tapis roulant dans le langage** : en DirectX, le programmeur pose à la main les
   barrières, les tas de descripteurs, la mémoire partagée. vtx connaît déjà les dépendances (la partition des
   tâches, les vibrations) : il peut déduire ces barrières, et ranger l'ombre d'une tuile dans la mémoire partagée.
   Moins de code, moins d'erreurs.
4. **L'ADN sur la carte** : les neutrons (le CRC quaternaire) et la patrouille appliqués à la mémoire de la carte : une
   donnée abîmée vue et réparée. Aucune interface graphique ne le propose.
5. **La démonstration mesurée** : le fluide et ce tableau, faits quatre fois : Lugus, forgé, Belenos sur Vulkan, et la
   même chose écrite en HLSL pour Direct3D 12 ; on compare le temps, le nombre de lignes, et les images (au bit près
   pour Belenos, pas pour l'autre).
6. **Le chemin, pas à pas** : (a) le noyau du fluide en SPIR-V, validé par l'outil de Khronos ; (b) un hôte Vulkan
   minimal en Rust pur (comme la fenêtre Win32 pure de l'atelier) ; (c) le tableau calculé sur la carte (un nuanceur de
   calcul par colonne) et affiché ; (d) DirectX par SPIR-V quand le Shader Model 7 sera là.
   Honnêtement : battre DirectX en vitesse brute dès le début est peu probable ; ce qui est à portée : la même image
   partout, moins de code, l'intégrité, et la même source pour Vulkan et DirectX.

## 19. L'accordéon du relief (7 novembre, après-midi)

**Idée de l'utilisateur** : le même nombre de cases par étage, chaque étage deux fois plus étendu ; le centre net.
**Décisions de l'utilisateur** : on suit le plan ; vtx pourrait un jour passer au-dessus de SPIR-V (réponse honnête :
une carte n'accepte que le format de son pilote, SPIR-V, DXIL ou Metal ; la voie réaliste est que les mots de vtx
soient le format portable et SPIR-V une traduction au chargement) ; les reflets et les ombres par l'anticube (un
masque à quatre valeurs : inconnu, rien à calculer ; vrai, l'eau ; variable, un bord ; faux, une surface qui absorbe ;
les ombres par la position du soleil, rangées dans l'anticube, recalculées segment par segment) : pour le moteur
graphique, dans cet ordre : accordéon, masque des reflets, ombres, puis SPIR-V.

**Réalisé dans le tableau** (`belenos/auvergne.vtx`) : trois étages de 1024 × 1024 cases, centrés sur l'œil : 1/4 de
case sur 256 cases, 1/2 case sur 512, puis la grille d'une case sur tout le pays. Chaque étage fin garde la hauteur de
l'étage d'une case et ajoute le détail qu'il est seul à pouvoir porter (la nappe d'une case pour l'étage 1, la demi et
le quart de case pour l'étage 0 : les touffes de l'estive, les blocs des flancs). Chaque détail s'efface sur les
dernières cases de son étage : aucune marche entre étages.

**Mesuré, une idée à la fois** (forgé, en secondes ; Lugus 2K : environ 115 s au lieu de 57, mêmes octets) :

| version | 2K | 4K | ce qu'on voit |
|---|---|---|---|
| avant | 0,61 | 1,98 | le premier plan lisse : un pas du rayon (1 case) peignait une bande de ~140 lignes |
| le pas en accordéon (une ligne par pas) | 0,64 | 2,82 | presque rien : le relief d'une case est lisse, le pas seul ne suffit pas |
| + les trois étages | 1,04 | 3,03 | du relief au premier plan, mais trop fort, et du moiré en colonnes sur le puy |
| + le rayon ne saute pas une case de l'étage, le détail filtré | 1,03 | 3,13 | les touffes éclairées au premier plan, le puy net, aucune couture |

**Ce que la mesure a appris** (honnêtement) : sur un sol vu en rasant, ce qu'une ligne d'image couvre en profondeur
croît comme z², pas comme z : un détail d'une case n'est plus visible au-delà de ~170 cases (2K) ou ~235 (4K). La
moitié lointaine de l'étage 1 ne porte donc que la grille d'une case : pour un sol rasant, chaque étage devrait être
√2 fois plus profond seulement (et non deux fois). La règle « deux fois plus étendu » reste juste pour ce qui est vu de
face (les flancs raides des puys) : le filtre actuel mesure le sol à plat, il efface donc aussi le détail des flancs.
À faire : un filtre qui tient compte de la pente, ou des étages en √2 pour le sol.

## 20. L'anticube de l'image : les vrais reflets, seulement où il faut (7 novembre)

**Idée de l'utilisateur** : superposer à l'image son anticube, qui ne garde que les parties nécessaires pour renvoyer
le reflet (et plus tard étaler les ombres, avec la position du soleil) ; à mettre dans le moteur graphique.

**D'abord la mesure** (instructions comptées par Lugus, 2K, sur la version à l'accordéon : 13,23 G) : les colonnes
7,3 G (55 %), l'accordéon 3,9 G (30 %), le relief d'une case, les objets et le PNG 1,9 G, les reflets 0,06 G (0,5 %).
Les reflets ne coûtaient presque rien parce qu'ils trichaient : le miroir de l'écran par rapport à l'horizon, exact
pour l'infini seulement.

**Réalisé** (`belenos/auvergne.vtx`) :
- l'anticube, un état de Belnap par point, écrit par les colonnes sans coût de plus : **inconnu** le ciel et le
  lointain (rien à renvoyer), **faux** la terre (elle absorbe), **vrai** l'eau (elle renvoie), **variable** la rive
  (terre et eau à la fois) ; et pour chaque ligne, de quel x à quel x elle a de l'eau ;
- les **vrais reflets** : le rayon touche l'eau, repart dans le paysage symétrique ; un point de hauteur h à la
  distance z s'y voit à la ligne HORIZON + (CAMH − 2·EAU + h)·F/z, symétrique de sa vraie ligne par rapport à la
  ligne de l'eau à cette distance ; au-delà de tout relief, le ciel, à l'infini, où l'ancien miroir est exact. Le lac
  reflète maintenant les puys qui sont derrière lui, renversés, à leur place ;
- la rive variable mêle l'eau et la terre voisine : le bord n'est plus en escalier.

**Mesuré** : les vrais reflets avec l'anticube : 1,37 G ; les mêmes calculés sur tout le bas de l'image, sans masque :
4,68 G ; **le masque économise 70 % des reflets, 18 % de l'image** (17,9 G → 14,6 G). Forgé : 2K 1,1 s, 4K 3,3 s.
Lugus et forgé : mêmes octets.

**Honnêtement** : sans masque, chaque point de terre s'arrête dès le premier pas (la plaine est au-dessus de l'eau) ;
le gain grandit avec le prix de l'effet par point (les ombres, plusieurs rebonds) et baisse si l'eau couvre l'image.
Les vaches et les arbres ne se reflètent pas encore (ils sont posés après).

**La vitesse, honnêtement** : Lugus interprète environ 146 millions d'instructions vtx par seconde ; forgé, le même
tableau en fait environ 13 milliards par seconde, soit l'ordre d'un code natif sur un cœur. La limite n'est donc plus
vtx mais le cœur unique : il faut 16,7 ms par image pour 60 images par seconde, et le 2K en demande 1,1 s (65 fois
trop). Les colonnes sont indépendantes : c'est le travail exact d'une carte graphique (des milliers de cœurs), d'où
SPIR-V dans le plan ; l'accordéon, lui, ne se recalcule que quand l'œil bouge (et par bandes, segment par segment).

## 21. Les ombres depuis le soleil peint ; les cylindres : un cube par cœur (7 novembre)

**Demandes de l'utilisateur** : les ombres ; « c'est trop lent : il faut plus de cœurs, plus de cubes ».

**Les ombres** (`belenos/auvergne.vtx`, `ombres()`) : rangées dans l'anticube du relief, une valeur par case :
**faux** éclairée, **vrai** à l'ombre, **variable** la pénombre (sur 1,5 case de hauteur), **inconnu** hors de la
grille. Un seul balayage, des lignes du fond (côté soleil) vers l'œil : chaque case reçoit la hauteur de l'ombre de sa
voisine côté soleil, abaissée de la pente du rayon ; plus haute que la case, la case est à l'ombre. Puis la lumière
(l'étage d'une case et les étages fins) en tient compte. Première version honnêtement ratée : le soleil qui éclairait
le relief (haut, 33 degrés) n'était pas celui peint dans le ciel (8 degrés, 17 à droite), et les ombres ne se voyaient
pas. Le soleil est maintenant le même partout : le tableau est à contre-jour ; les faces des puys tournées vers nous
s'assombrissent, leurs ombres viennent vers nous sur la plaine entre les puys et le lac, les sommets prennent un
liseré de lumière, et la lumière rasante modèle les touffes du premier plan.

**Les cylindres** (la forge, `forge/forge128.py` et `forge/noyau_forge128.rs` ; trois fonctions dans `spu128.rs`) :
`pour i dans a..b en segments { … }` existait (le V6 de vtx 0.4 : 12 segments, 6 cylindres × 2 temps) ; en 128 bits,
la forge le jouait en boucle ordinaire. Maintenant, quand le corps ne touche que le cube (ni sortie, ni fichier, ni
tas), chaque cylindre (un fil, un cœur) joue des segments qui se suivent, sur **son propre cube** :
- il lit les pages du cube commun sans les copier (l'instantané) ; il ne copie une page qu'au moment où il y écrit ;
- quand tous ont fini, les cubes sont fondus dans le cube commun, mot à mot, dans l'ordre des segments ; chaque mot a
  un état de Belnap : **inconnu** (personne n'y a touché), **vrai** (un seul l'a changé), **variable** (deux l'ont
  changé différemment : le dernier l'emporte, comme dans l'ordre, et le conflit est compté) ;
- si un cylindre a lu une page qu'un cylindre d'avant a écrite, ou écrit hors de la pile dans l'étage 0, ou touché un
  cube sur disque ou une page d'ADN, tout est oublié et les segments sont rejoués l'un après l'autre.

Le résultat est donc toujours celui de Lugus. La partition rangeait chaque segment dans sa propre mesure (elle ne
prouve pas l'indépendance d'écritures à une adresse calculée) : les cylindres la vérifient en jouant.
`VTX_COEURS=n` fixe le nombre de cylindres, `VTX_CYLINDRES=1` montre la fusion.

**Vérifié** (`tests/test_cylindres.py`) : `exemples128/cylindres.vtx` et `tests/cylindres_dependants.vtx` donnent la
sortie de Lugus sur 1, 2 et 3 cylindres ; la boucle dépendante (chaque case lit la précédente) est vue et rejouée ;
les segments qui écrivent les mêmes mots donnent 3 mots variables, résolus comme dans l'ordre.

**Le tableau en cylindres** : le relief, l'accordéon, la lumière à l'ombre, les colonnes et les reflets sont en
segments. Pour que chaque segment écrive sa part : les colonnes écrivent l'image colonne par colonne, puis
`remettre()` la remet en lignes ; les reflets sont calculés à part, puis posés ; la rive a sa couche à elle. Sur
2 cylindres : 105 pages fondues pour les colonnes, aucun mot variable, rien de rejoué. Lugus et forgé : mêmes octets.

**La mesure, honnêtement** : la machine de travail n'a qu'un vrai cœur (deux programmes côte à côte prennent deux
fois plus de temps ; le Mandelbrot parallèle passe de 0,67 à 0,60 s) : le gain ne se mesure pas ici. Sur un cœur, le
découpage coûte 6 % (2K : 1,33 → 1,42 s). Ce qui reste sur un seul cœur : le balayage des ombres (chaque ligne dépend
de la précédente), l'empreinte, les objets et surtout le PNG (le CRC et l'Adler-32 se suivent), environ 12 % du
travail : sur 8 cœurs, on attend environ 3 à 4 fois plus vite (12 segments sur 8 cœurs : 4 en jouent deux), pas 8.
Le .bat mesure sur 1 cœur puis sur tous.

## 22. La mesure sur 24 cœurs, et les deux murs (7 novembre, soir)

**Le paquet nettoyé (0.5zf)** : les sorties de test (casse-briques, feu de camp, ombre 256) et trois relevés de
mesures que rien ne lisait sont retirés (et ignorés par git) ; `forge/test_forge.py` (la forge du SPU-32), oublié par
le vérificateur mais toujours juste (343 programmes, 0 écart), y est rebranché ; `verifier.bat` lance la vérification
complète à la demande. Les `.bat` d'essai ne mesurent plus que la nouveauté, dans un dossier fixe `essai-vtx\` (les
sources remplacées, la compilation Rust gardée).

**La mesure de l'utilisateur** (24 cœurs) : 2K 1,60 → 1,03 s (×1,55), 4K 4,69 → 3,23 s (×1,45) ; la même image
octet pour octet. Bien moins que les ×3 à ×4 annoncés. Le chrono de chaque accord (`VTX_CYLINDRES=1` affiche
maintenant, pour chacun, quand il commence, le temps dans les fils et celui de la fusion) a montré deux murs :

1. **La fusion, sur un seul cœur : environ 0,38 s.** Un cylindre copie une page entière (65 536 mots de 128 bits :
   1 Mo) dès qu'il y écrit ; la fusion comparait puis recopiait chaque page mot à mot. Maintenant : la comparaison
   (la page a-t-elle vraiment changé ?) se fait dans le fil, sur son cœur ; une page écrite par un seul cylindre
   **devient** la page commune (`poser_page` dans `spu128.rs` : on échange les mots, rien n'est recopié) ; seules les
   pages écrites par plusieurs sont fondues mot à mot, une page par fil à la fois, sur tous les cœurs, en sautant
   d'un coup les blocs de 64 mots qu'un cylindre n'a pas touchés.
2. **La queue : environ 0,4 s.** Comptée en instructions sur Lugus (exactes, contrairement au chrono de la machine de
   travail, trop bruité) : PNG 644 millions, sprites et cadre 471 millions, empreinte 44 millions (sur 15,68 milliards).
   Mais en forgé le PNG coûtait bien plus que ses instructions : chaque octet écrit cherchait son canal dans deux
   tables de hachage (clés de 128 bits). `ecrire_canal` garde maintenant le dernier canal d'octets et son tampon (oubliés
   dès qu'un fichier s'ouvre ou se ferme).

**Mesuré sur un cœur** (la machine de travail) : 2K 1,30 → 1,02 s, le même PNG octet pour octet ; la fusion ne se
mesure pas ici (un seul cœur). **Attendu sur 24 cœurs** (calcul, pas mesure) : vers 0,5 à 0,6 s en 2K.

**Ce qui reste** : la boucle de la lumière à l'ombre est toujours rejouée (lecture et écriture de la même case : la page
du bord, partagée par deux segments, passe pour une dépendance ; environ 30 ms perdues) ; 12 segments pour 24 cœurs
(la moitié des cœurs attend) ; les sprites et le PNG restent séquentiels (le CRC et l'Adler-32 se combinent pourtant
par morceaux : un PNG en cylindres est possible).

## 23. Le rendu différé : les reflets et les ombres à la toute fin, pour tout le monde (7 novembre, soir)

**La mesure de la 0.5zg** (chez l'utilisateur, 24 cœurs) : 2K 1,35 s sur un cœur, **0,68 s** sur tous (1,03 s avant) ;
4K 3,66 s et **1,90 s** (3,23 s avant) ; la même image partout. La fusion ne pèse plus (7 à 30 ms par boucle). Restaient :
la boucle des reflets, déséquilibrée (130 ms : un seul segment portait presque toute l'eau), le balayage des ombres
(31 ms sur un cœur) et la queue (sprites et PNG, environ 0,2 s).

**L'idée de l'utilisateur** : l'anticube (reflets, ombres) doit venir à la toute fin de la composition de l'image, pour
que chaque élément en profite. C'est le rendu différé des moteurs : tout ce qui est dans l'image écrit d'abord dans un
tampon, puis une seule passe éclaire tout, sans savoir qui a peint quoi. Dans Belenos :

- **le tampon** : la couleur (`IMAGE`), la distance fine en 1/256 de case (`ZF`, nouvelle), l'état de Belnap
  (`ANTI` : le ciel inconnu, la terre et les objets faux, l'eau vraie), et pour les objets leur distance (`OBJ`) ; un
  objet posé (`poser`) y écrit tout cela, et ses bornes : de quelle ligne à quelle ligne chaque colonne a des objets,
  à quelles distances il y en a, et de quel x à quel x ;
- **la passe finale** (`passe_finale`), après le dernier objet : les rives (l'eau qui touche la terre ou un objet devient
  variable), puis pour chaque ligne les reflets et les ombres, rangés à part (`NOUV`), puis posés ;
- **les reflets des objets**, lus dans le tampon : un point posé à la distance o, à la ligne ys, se voit dans l'eau à la
  ligne 2·yw(o) − ys (yw(o) : la ligne de l'eau à cette distance ; exact pour une eau plate) ; l'eau doit être devant
  lui, le plus proche l'emporte, et le vrai rayon dans le relief s'arrête sur lui (une colline devant l'objet le cache
  encore) ;
- **les ombres des objets**, lues dans le tampon : du point du sol, le rayon remonte vers le soleil peint par
  demi-case ; s'il traverse un point de l'image où un objet est posé à sa distance (à 1,25 case près : l'épaisseur
  d'un objet), le point est à l'ombre. Le rayon saute les distances où il n'y a aucun objet, et ne lit pas l'image à
  côté des objets de cette distance (de 0,65 à 0,23 s sur un cœur, la même image) ;
- **les bandes entrelacées** : la ligne y va à la bande y mod 12 ; l'eau, qui tient en peu de lignes, se partage entre
  tous les cœurs ; aucune passe ne lit ce qu'elle écrit (rien n'est rejoué).

**Pour le montrer** : un bosquet et un buron sur la rive d'en face du lac (à 271 cases) ; sans une ligne pour eux, ils
ont leur reflet (à l'envers, troublé de rides, décalé : leur pied est au-dessus de l'eau). Les vaches et les arbres de
l'estive ont leur ombre longue du soir, vers nous (le soleil est bas, à contre-jour). Lugus et forgé : la même image,
octet pour octet.

**Ce qui manque encore** : les ombres ont des bords francs (pas de pénombre pour les objets) ; un objet ne fait pas
d'ombre sur un autre ; la passe ne voit que ce qui est dans l'image (un objet hors du cadre n'a ni reflet ni ombre).

**La carte graphique (RTX 3070)** : tout Belenos tourne aujourd'hui sur le processeur. La carte a 5 888 cœurs CUDA
(46 multiprocesseurs, qui vont par groupes de 32 au même pas) et sa propre mémoire : faite pour la passe finale et les
colonnes (un point, un fil), pas pour le PNG. Le chemin prévu : SPIR-V par Vulkan, la forge écrivant un nuanceur de
calcul pour une boucle en segments sans effet. Deux obstacles honnêtes : les mots de 128 bits (la carte calcule en 32
bits : chaque opération en coûte plusieurs) ; et la machine de travail n'a pas de carte graphique : chaque pas ne se
vérifie que sur le PC de l'utilisateur, par un .bat.

## 24. Taranis : la carte graphique, par Vulkan, sans bibliothèque (7 novembre, soir)

**La mesure de la 0.5zh** (24 cœurs) : 2K 1,67 s sur un cœur, **0,83 s** sur tous ; 4K 5,2 s et **2,43 s** ; la même
image partout. La passe finale coûte environ 130 ms sur 24 cœurs (fils et fusion) ; il reste environ 0,2 s après la
dernière boucle (objets, cadre, empreinte, PNG). **Le PNG n'est plus le frein** depuis que l'écriture d'octets ne
cherche plus son canal dans une table (0,28 s gagnées) : ses 644 millions d'instructions font environ 50 ms forgés.
Un format sans contrôle (PPM, BMP) en gagnerait une partie, pas l'essentiel. Pour la vidéo, la vraie voie est autre :
les images brutes, et le codeur matériel de la carte (NVENC sur une RTX), pas un PNG par image.

**Ce que vaut Belenos, comparé** : forgé, vtx est mesuré à 1 à 3 fois le temps du C (section des mesures) ; la même
scène en C sur le processeur irait donc au mieux 2 à 3 fois plus vite (estimation, pas mesure). Un moteur de jeu peint
un relief de ce genre en 4K en quelques millisecondes : 500 à 1 000 fois plus vite. L'écart n'est pas le langage, c'est
la carte. D'où le but de l'utilisateur : configurer la partie carte graphique, pas faire une belle image.

**Ce que la machine de travail permet** : ni crates.io, ni PyPI, ni paquets système ; mais le chargeur Vulkan est là,
et **SwiftShader** (le Vulkan logiciel de Google, livré avec Chromium) aussi : tout ce qui part sur la carte de
l'utilisateur peut d'abord être vérifié ici, sur le processeur, par une vraie implémentation de Vulkan.

**Taranis, étape zéro (la sonde)**, sans aucune dépendance, comme le reste de vtx-rs :
- `taranis/spirv.py` : l'écrivain de SPIR-V de vtx (les mots de 32 bits, l'en-tête, les instructions, une relecture qui
  vérifie longueurs et identifiants) ; il écrit le noyau de la sonde : chaque fil brasse son numéro en 64 tours de
  xorshift et de multiplication (384 opérations sur 32 bits) et le range ;
- `vtx-rs/src/taranis.rs` (le binaire `taranis`) : Vulkan chargé à l'exécution (`vulkan-1.dll` sous Windows, que le
  pilote installe ; `libvulkan.so.1` ailleurs), les structures de la spécification écrites à la main ; la carte choisie
  (la première dédiée), un tampon visible du processeur, le noyau, n / 64 groupes ; puis le même brassage sur un cœur et
  sur tous, et la comparaison mot à mot ;
- `tests/test_taranis.py` (dans le vérificateur) : le noyau embarqué est celui que spirv.py écrit, et la carte (ou
  SwiftShader) rend les mêmes mots que le processeur. Ici : 1 048 576 mots identiques sur SwiftShader.

**La suite** : la forge écrit le SPIR-V d'une boucle en segments (le corps traduit en opérations de la carte ; les
mots de 128 bits en quatre mots de 32, ou des boucles prouvées sur 32 bits), puis une passe de Belenos (les colonnes, la
passe finale) sur la carte, comparée au processeur point pour point.

**La sonde sur la RTX 3070** (0.5zi, chez l'utilisateur) : la carte trouvée par Vulkan 1.4, le SPIR-V de vtx accepté du
premier coup, 16 777 216 puis 67 108 864 mots identiques au processeur. Carte 25 ms (tout compris) contre 170 ms sur 24
cœurs et 5,2 s sur un : 7 fois les 24 cœurs. Mais le temps suivait exactement le nombre de fils, à 2,7 Go/s : la
sonde écrivait dans la mémoire du processeur, à travers le bus ; le calcul lui-même n'était pas mesuré.

**La sonde, deuxième version (0.5zj)** : le calcul dans la mémoire de la carte, puis une copie vers le processeur ; la
carte horodate elle-même le calcul et la copie (les requêtes d'horodatage de Vulkan ; la période du tic lue dans les
limites de la carte, à l'octet 296 + 424 des propriétés, avec le nombre de groupes et de fils par groupe : 65 535 et
256 sur SwiftShader, ce qui vérifie les décalages).

**La comparaison** (`taranis/comparer.py`) : le même calcul sur chaque système que la machine sait faire tourner, chaque
somme vérifiée : vtx sur la carte (le calcul seul, et tout compris), C (`taranis/brassage.c` : MSVC ou gcc, un cœur
puis OpenMP), vtx forgé (`taranis/brassage.vtx`, en segments), Rust, Lugus émulé et Python (sur une partie, ramenés à
n). Sur la machine de travail (un vrai cœur, SwiftShader pour carte) : vtx forgé à égalité avec le C et Rust (93 à
97 ms sur deux fils pour un million de nombres) ; Python 140 fois plus lent ; Lugus émulé 200 fois.

## 25. La forge écrit le SPIR-V : une boucle vtx sur la carte (7 novembre, nuit)

**La comparaison sur la RTX 3070** (0.5zj, 16 777 216 nombres brassés en 64 tours, toutes les sommes justes) :

| système | temps | × la carte |
|---|---|---|
| vtx sur la carte, le calcul (SPIR-V de la sonde) | 0,9 ms | 1 |
| vtx sur la carte, tout compris (lancement, copie de 64 Mo, attente) | 26,3 ms | 31 |
| C (MSVC /O2, OpenMP), tous les cœurs | 169,9 ms | 199 |
| vtx forgé, tous les cœurs (le programme entier) | 349,3 ms | 409 |
| C (MSVC /O2), 1 cœur | 2,67 s | 3 123 |
| vtx forgé, 1 cœur (le programme entier) | 3,00 s | 3 509 |
| Python 3 | 665 s | 778 558 |
| vtx sur Lugus émulé | 897 s | 1 050 524 |

Le calcul seul : 8,6 milliards d'opérations en 0,85 ms, environ 10 000 milliards par seconde (le chiffre « d'après
la fiche », 5 000, était trop bas). Le coût est ailleurs : redescendre 64 Mo prend 25 ms (2,6 Go/s) ; la règle en
découle : les données restent dans la carte, seul ce qui doit sortir redescend. vtx forgé est à 12 % du C sur un cœur
(en mots de 128 bits, en rangeant chaque mot dans le cube) ; deux fois sur tous les cœurs (12 segments seulement).

**Le noyau écrit par la forge** (`taranis/noyau_vtx.py`) : une boucle « en segments » dont le corps sait aller sur la
carte devient un noyau SPIR-V, un fil par tour. Le sens est celui de Lugus : un entier est un mot de 64 bits, calculé
en deux mots de 32 (les retenues ; le produit étendu, OpUMulExtended ; la division longue en 64 tours, avec les cas
de Lugus : la division par zéro rend le plus grand entier, le reste par zéro le dividende, la division signée par −1
rend l'opposé) ; ainsi tout se vérifie sur SwiftShader, qui n'a pas d'entiers de 64 bits, et va sur toute carte. Le
corps peut avoir des variables, soit, si / sinon, tantque, pour, des comparaisons signées ou non, && || non, des
appels de fonctions vtx (recopiées dans le noyau ; leur retour à la fin), et lire ou écrire @2[adresse] si l'adresse
ne dépend que de la variable de boucle et de variables d'avant la boucle.

**Le programme forgé** (`vers_la_carte` dans forge128.py, `taranis_boucle` dans noyau_forge128.rs, le module
`taranis_vk.rs` recopié dans chaque programme) : avant les cylindres, la boucle entière part sur la carte. La fenêtre de
l'étage 2 se calcule à l'exécution : chaque adresse est évaluée aux tours a, a + 1 et b − 1 et doit avancer d'un pas
constant ; une lecture qui croise l'écriture d'une autre expression, ou des écritures toutes sur le même mot, et la
boucle reste aux cylindres (l'ordre des tours compterait). La fenêtre monte (des mots de 64 bits ; un mot plus large :
non), le noyau calcule, la fenêtre redescend, seuls les mots changés sont écrits dans le cube. Un accès hors de la
fenêtre lève un drapeau : les cylindres rejouent la boucle. Sans carte, ou `VTX_CARTE=0` : les cylindres, comme avant.
`VTX_TARANIS=1` dit ce que fait la carte (et, à la forge, pourquoi une boucle reste au processeur).

**Vérifié** : `taranis/brassage.vtx` forgé sur la carte (SwiftShader) rend la somme de Lugus ;
`tests/test_taranis_noyaux.py` tire au hasard des boucles (toutes les opérations et leurs cas limites : 0, 1, 31, 32,
63, 64, 2^63, 2^64 − 1 ; si, tantque, pour, des appels) : 104 boucles sur trois graines, toutes sur la carte, les mêmes
mots que Lugus. Belenos n'y va pas encore : ses adresses dépendent de variables du corps, ses fonctions lisent la
mémoire (la suite : une fenêtre de pages entières, et les fonctions qui lisent).

**Sur la RTX 3070** (0.5zk) : 80 boucles tirées au hasard (graines 7 et 99), toutes sur la carte, les mêmes mots que
Lugus : le SPIR-V écrit par la forge est juste sur une vraie carte. Mais lent : brassage.vtx, la boucle sur la carte,
1,7 s (contre 0,9 ms pour le noyau de la sonde, 343 ms pour vtx forgé sur 24 cœurs). Le calcul n'y est pour rien
(environ 64 milliards d'opérations sur 32 bits : quelques millisecondes) : la fenêtre (128 Mo) était montée même vide,
redescendue par une mémoire visible du processeur mais non cachée (relue octet à octet à travers le bus), et lue puis
rangée dans le cube mot à mot. **Corrigé (0.5zl)** : une fenêtre vide (que des zéros : des pages absentes) est remplie
par la carte elle-même (vkCmdFillBuffer) ; la descente passe par une mémoire cachée (HOST_CACHED) ; le cube est lu et
écrit page par page (page_si, sans créer de page ; page_de pour ranger). `VTX_TARANIS=1` donne le temps de chaque
étape : lire le cube, monter, la carte, redescendre, ranger dans le cube.

## 26. L'autonomie : vtx en .exe Windows, sans Rust (8 novembre)

**La question de l'utilisateur** : à quoi sert la carte graphique aujourd'hui pour le langage, et pourquoi passer par
Rust à chaque fois ? Réponse honnête : Taranis a prouvé que vtx sait écrire lui-même le SPIR-V d'une carte, juste sur la
RTX 3070 (80 boucles au hasard, les mêmes mots que Lugus) ; il s'arrête là tant qu'un vrai besoin ne le demande pas. La
dépendance à Rust est ailleurs : la machine (Lugus, vtx-rs) est le support du processeur quaternaire qui n'existe pas
encore ; la forge (vtx -> Rust -> rustc) et l'atelier, eux, dépendent de Rust sans raison de fond. Décision : reprendre
`natif/` (mis de côté jusqu'ici) pour que vtx fasse ses exécutables lui-même, en perfectionnant l'atelier et la
paillasse.

**`natif/` tel qu'il était** : le programme du SPU-32 traduit directement en code machine x86-64 (l'assembleur maison
`natif/x86.py`, vérifié octet pour octet contre GNU as ; le socle `natif/socle.py` : démarrage, sorties, texte, canaux,
services), un exécutable Linux (ELF) sans Rust ni LLVM ; le corpus de conformité sans écart. Le socle était prévu pour
un portage (seules 14 primitives OS_* parlent au système ; `socle_windows` était appelé, jamais écrit).

**Windows (0.5zm)** : `natif/socle_windows.py` écrit les primitives par KERNEL32 (la seule bibliothèque, toujours là) :
l'appel de Windows x64 (rcx, rdx, r8, r9, 32 octets réservés, la pile alignée ; r8 à r11 gardés pour le socle) ; les
descripteurs 0, 1, 2 par GetStdHandle ; la console en UTF-8 ; les \r des lignes tapées retirés ; les noms de fichiers
en UTF-16 (MultiByteToWideChar : les accents passent) ; la mémoire du SPU par VirtualAlloc ; le bruit par rdtsc ; la
ligne de commande sans le nom du programme. Pas encore : la voix, les cubes rangés (erreur claire). `natif.py --windows`
écrit le .exe lui-même (PE32+ : en-têtes DOS, PE, optionnel, une section lisible, inscriptible et exécutable, la table
d'import dans le socle) : ni Rust, ni éditeur de liens. Vérifié ici : le code du socle Windows réassemblé par GNU as
(mêmes octets), les 487 programmes du corpus en .exe relus par objdump (PE32+, KERNEL32, ses 13 fonctions), le point
d'entrée. Pas lancés : la machine de travail n'est pas sous Windows (`natif/test_windows.py` les lance sous Windows).

**La suite** : le corpus lancé sous Windows ; le loto en .exe ; puis le traducteur écrit en vtx (les mêmes octets que
natif.py), dans vtx.exe, un bouton de l'atelier ; la voix et les cubes ; la paillasse.

**Sous Windows** (0.5zm, chez l'utilisateur) : 481 programmes du corpus sur 487 justes, bonjour.exe parle. Les 6 autres
échouaient aussi sous Linux : les flottants de 64 bits (0x5B à 0x6B), venus au SPU après la mise de côté de natif.
**0.5zn** : ils sont traduits (SSE2 : addsd, subsd, mulsd, divsd, sqrtsd, ucomisd, les conversions ; le NaN unique
0x7FF8000000000000 de la référence ; les conversions vers les entiers saturées, NaN : 0) ; le corpus entier : 487
programmes, 0 écart (Linux), et relus pour Windows. Le loto lu d'un fichier quittait : Windows rangeait le compte
d'octets lus dans la case même où le socle lit un caractère (OCTET) ; le compte a sa propre case. Un programme ouvert
d'un double clic (seul dans sa fenêtre : GetConsoleProcessList) attend Entrée avant de se fermer.

## 27. L'atelier : la carte du programme, la visionneuse, l'exécutable autonome (8 novembre, 0.5zo)

**La carte du programme sur la paillasse.** Ouvrir n'importe quel programme pose sa carte sur la paillasse : chaque
fonction est une case, chaque appel une liaison ; les vagues vont de `principal` vers les feuilles (la profondeur
d'appel ; la récursion est vue, pas suivie à l'infini). La carte se lit et ne se modifie pas : un clic sur une case
mène à sa ligne dans l'éditeur. Sur le loto : 14 fonctions, 4 vagues, `principal` appelle 5 fonctions
(tests/test_carte.py, sans ligne écrite en dur). `paillasse --analyse` ignore la carte (les réactions seules).

**La visionneuse.** Avant de lancer un programme, l'atelier relève le dossier du programme et le dossier courant ;
après, ce qui est apparu ou a changé s'ouvre dans une fenêtre à part : une image (BMP, PNG, JPG, GIF par GDI+,
agrandie à pixels entiers, sans flou), un son WAV (rejoué d'un clic, Échap l'arrête), un exécutable (lancé dans sa
propre console). Démonstration : exemples128/visionneuse.vtx (Lugus) écrit `la.wav` (un la 440 Hz en triangle) et
`belnap.bmp` (les quatre couleurs de Belnap) par le canal `octets:`.

**Ctrl+E : l'exécutable autonome.** Menu Lancer → « Faire l'exécutable autonome » : natif.py --windows traduit le
programme (machine 32, Senos) en .exe x86-64 qui ne demande que KERNEL32, puis l'ouvre dans la visionneuse.
Le code Windows de l'atelier est vérifié par le compilateur Rust (cargo check), pas encore lancé ici : c'est l'essai
0.5zo qui le dira.

**0.5zp : le dossier Ogmios, le clavier, le guetteur.** L'essai pose l'atelier à un endroit fixe,
`Vercintorix1.0 rust\Ogmios\Ogmios.exe` (avec vtx.exe, natif, les exemples et la bibliothèque ; un fichier déjà là et
plus récent n'est pas remplacé), un raccourci « Ogmios » sur le Bureau et dans le menu Démarrer, et les .vtx s'ouvrent
d'un double clic dans Ogmios (`vtx desinstaller` défait l'association). Un clic sur la paillasse lui donnait le clavier,
et elle ne garde que Suppr et Échap : les autres touches se perdaient (« les touches ne répondent plus »). Elles vont
maintenant au texte, et après un clic sur la carte le clavier revient au texte. Le guetteur : si un message tient la
boucle de l'atelier plus de deux secondes, un fil à part l'écrit dans ogmios.log (quel message, sur quelle partie de la
fenêtre), et une panique y laisse sa place dans le code. Le cube n'est pas dans loto.exe : l'exécutable autonome n'a
encore ni la vue du cube ni la voix ; c'est un chantier à venir, avec Lugus en .exe.

**0.5zq.** La carte se promène : glisser le vide à la souris (de gauche à droite comme de haut en bas), la molette
(haut, bas), Maj + molette ou la molette penchée du pavé tactile (gauche, droite). Le loto choisit seul : « 4 » la
machine tire une grille et un numéro chance et les joue contre un tirage ; « 5 » elle propose des grilles (5 par défaut,
jusqu'à 100) sans les jouer. Mêmes mots par vtx.py et vtxc, même sortie par le .exe autonome.

## 28. Le débogueur par les noms, et le vocabulaire (8 novembre, 0.5zr)

**Le débogueur de Lugus.** En pas à pas, vtxc128 écrit `code.sym` : pour chaque fonction gardée son nom, la place de
son premier mot (en demi-mots, le pc de Lugus) et sa ligne ; pour chaque variable son nom, sa place dans le cadre et sa
sorte (les textes, tableaux de textes et de flottants sont notés par typer_textes avant que la génération n'en fasse
des entiers). L'atelier (symboles.rs) remonte la pile des appels par le cadre R13 (l'ancien cadre en +0, l'adresse de
retour en +1) et écrit chaque variable comme le programme l'entend. Maj+F8 sort de la fonction en cours : l'arrêt se
fait dès le retour, au milieu de la ligne de l'appelante. Les mots du programme ne changent pas (code.sym est à part).
`vtx-spu regarder128` donne la même vue en console ; tests/test_debogueur128.py : variables d'une fonction, deuxième
passage dans une boucle, quatre étapes d'une récursion avec chacune son n, sortir d'une fonction.

**Le vocabulaire.** Vingt mots dans le prélude des trois machines (tableaux, hasard, textes, entiers ; la liste est
dans la référence du langage). Dans le prélude, `+` sur des textes ne se réécrit pas : il faut `__texte_plus`.

**Une erreur ancienne de vtxc128.** prelude_utile coupe le prélude en morceaux, d'une « fonction » en début de ligne à
la suivante ; la dernière fonction du prélude (borne) ne se compilait pas sur Lugus par vtxc128 (« caractère
inattendu »), alors que vtx128.py l'acceptait. Une fonction vide, jamais appelée, ferme maintenant le prélude
(`__fin_du_prelude`) : borne et puissance_entiere se compilent. La cause exacte reste à comprendre.

Le lecteur d'ADN embarqué dans Lugus (`vtx-rs/lecteur_adn.mots`) a été recompilé : le prélude ayant changé, ses mots
aussi (même nombre, 3 528).

## 29. Lugus fait les .exe, avec ses cubes (8 novembre, 0.5zs)

**Le choix.** Le créateur a choisi la traduction directe, sans Rust (comme le .exe de Senos, écrit en x86-64 par
natif.py). Pour Lugus elle se fait en deux temps. D'abord le **paquet** (cette version) : le .exe est la machine
elle-même, vtx.exe déjà construite, suivie du programme compilé par vtxc128 et des fichiers dont il a besoin. Le faire ne
demande ni Rust ni Python : une compilation et une copie, une fraction de seconde. Ensuite la **traduction** : les mots
deviendront du x86-64 dans le même paquet, et la machine embarquée gardera ce qui ne se traduit pas en quelques
instructions (les pages du cube, les flottants quaternaires de qflot128, les services, la fenêtre). Le paquet est le socle
sur lequel la traduction viendra se poser ; il est utile dès maintenant.

**Ce que le .exe emporte.** Les mots ; les cubes sur disque du dossier du programme (`cube128-É-F.cub`, avec son
anti-cube et son ombre) ; les fichiers que les textes de la source nomment, s'ils sont dans le dossier (`"notes.txt"`,
`"octets:image.png"`). Au lancement, il pose à côté de lui ceux qui n'y sont pas encore, jamais par-dessus ceux qui y
sont (le programme a pu les changer), puis joue. Sa console lit le clavier au fil de l'eau (le loto se joue au
clavier) ; la fenêtre de dessin s'ouvre à la première image présentée ; la voix et la machine fille sont là. Lancé d'un
double clic, il attend Entrée avant de fermer sa console.

**Le format.** La fin du fichier : `[paquet][longueur u64][VTXLUGUS]`. Au démarrage, vtx lit les 16 derniers octets de
son propre exécutable : sans la marque, il est la machine ordinaire. Le paquet : des entrées nom/données (`@nom`,
`@mots` en u128 petit-boutiste, puis les fichiers).

**Où.** `vtx exe128 PROG.vtx [SORTIE]` en console ; Ctrl+E dans Ogmios sur Lugus (la machine emportée est le vtx.exe du
dossier Ogmios), puis le .exe est lancé dans sa console. Dunon n'a pas encore d'exécutable. `tests/test_exe128.py` : même
texte et mêmes sorties que `lugus PROG.vtx`, le loto au clavier, un cube rangé par un programme puis relu par le .exe
lancé dans un autre dossier (état du disque : vrai), un fichier déjà là jamais écrasé, une erreur de compilation dite.

**Ce qui manque encore.** La vue du cube d'Ogmios (la mémoire en couleurs pendant que le programme tourne) n'est pas
dans le .exe ; la traduction en x86-64 ; Dunon.

## 30. La vitrine des .exe de Lugus (9 novembre, 0.5zt)

« Le loto en commande est un peu austère pour un exécutable. » Lancé d'un double clic sous Windows (ou par Ctrl+E
d'Ogmios), le .exe de Lugus n'a plus de console grise : il ouvre sa **vitrine** (vitrine.rs). À gauche le texte du
programme, ce qu'il écrit et ce qu'on lui tape (la saisie en ambre, Entrée l'envoie) ; à droite le **cube chromatique de
sa mémoire**, en perspective, qui se remplit pendant qu'il tourne ; en bas l'état : la machine tourne, attend une
réponse ou a fini, le nombre d'instructions, l'étage du cube et ses mots. Clic : l'étage suivant qui a quelque chose ;
clic droit : un quart de tour ; molette : zoom. La toile s'ouvre toujours à part, à la première image.

La machine tourne sur le fil principal par tranches de trois millions d'instructions ; entre deux tranches (au plus
toutes les 0,4 s) et chaque fois que le programme attend le clavier (un crochet nouveau de Spu128, `avant_lire`), elle
laisse une vue de sa mémoire, celle d'Ogmios (Vue64::depuis128), que la fenêtre dessine avec cube::rendre_iso. La
fenêtre vit sur son propre fil et ne tient que des statiques. Fermer la vitrine arrête le programme.

Lancé depuis un terminal (PowerShell, cmd) ou avec `--console` (ou la variable VTX_CONSOLE), le .exe reste en console,
comme en 0.5zs : les tests et les scripts le lisent ainsi. Sous Linux, la console seule.

## 31. Les cases au clic droit, la vitrine sans le cube (9 novembre, 0.5zu)

**La paillasse.** Le clic droit sur une case ouvre une petite boîte posée sur elle, pleine de sa ligne (« double = a ×
2 -> b »), tout choisi : on tape, Entrée récrit la ligne au même retrait, Échap renonce, un clic ailleurs écrit comme
Entrée. Le clic droit dans le vide pose une case neuve là où l'on a cliqué (« = _ -> l1 ») et ouvre aussitôt sa boîte.
Sur la carte du programme, le clic droit dit que la carte se lit (une fonction s'écrit dans le texte). Comme les autres
gestes, Ctrl+Z dans le texte défait. paillasse.rs reste sans Windows : `Souris::Droit` rend `Reponse::Editer`, et
`editer_ligne` récrit ; « vtx paillasse --gestes » rejoue `droit X Y` puis `ecrire TEXTE` (tests/test_paillasse.py :
x + 1 devient x + 2 et r(3) passe de 12 à 15 ; une case posée dans le vide et écrite).

**La vitrine.** Le créateur : inutile de montrer le cube dans les programmes (il pensait que le .exe gardait le cube
pour fonctionner : c'est le cas, les cubes sur disque sont emportés et posés à côté). La vitrine garde la fenêtre (le
texte, la saisie en ambre, l'état et le compteur d'instructions) et n'a plus le cube ; le crochet `avant_lire` de
Spu128, qui ne servait qu'à lui, est retiré.

## 32. Lugus traduit en x86-64 (9 novembre, 0.5zv)

**Le principe.** Au lancement d'un .exe de Lugus, ses mots sont traduits une fois en instructions du processeur du PC
(natif128.rs), dans une mémoire rendue exécutable (mmap sous Linux, VirtualAlloc sous Windows). Chaque
demi-instruction devient un morceau de x86-64 qui travaille sur la machine même : les registres r0 à r15, z, c et le
compte des instructions restent à leur place dans Spu128 (le code traduit les lit et les écrit là, `offset_of!`). La
mémoire de Lugus passe par deux portes, `natif_lire` et `natif_ecrire` : les pages, leur cache, les cubes sur disque
et la protection de l'ADN restent ceux de Lugus. Rien de Rust ni de Python n'est demandé à l'utilisateur : le
traducteur est dans vtx.exe.

**Ce qui est traduit.** À la largeur 64 : ADD, ADDI, SUB, SUBI, CMP, CMPI, MUL, AND, OR, XOR, les trois décalages,
les deux MOVI, ETG ; à la largeur 128 : MOV, les lectures et écritures (par registre, dans le cadre R13, la pile
R14), les sauts (direct et sur z, c), CALL, et RET par une table des adresses traduites. Tout le reste (flottants,
divisions, services, arrêt, ce qui sort du programme) est **rejoué par Lugus** une instruction, puis le code traduit
reprend : la traduction ne peut pas se tromper sur ce qu'elle ne sait pas faire. Une écriture refusée (un mot d'ADN)
revient à Lugus sans rien changer, et Lugus dit l'erreur.

**Mesuré.** tests/test_natif128.py : les 14 exemples de Lugus, le vocabulaire, le loto au clavier, quatre programmes
faits pour cela (les bords des entiers de 64 bits, Ackermann pour la pile, une lecture hors du tableau, les textes et
les flottants) : traduits et joués par Lugus seul (VTX_INTERPRETE), le même texte, les mêmes sorties, la même fin et
**le même nombre d'instructions** à l'unité. Le banc (exemples128/banc_traduction.vtx : un crible jusqu'à deux
millions, fib(27), trois millions de brassages ; 131 millions d'instructions) : 1,06 à 1,43 s par Lugus, 0,28 à
0,49 s traduit, **3 à 4 fois plus vite**. Les programmes de flottants gagnent peu (mandel_reaction : 1,1) : qflot128
n'est pas encore traduit.

**Les limites, dites.** Le code traduit ne regarde ni la limite d'instructions, ni la patrouille, ni l'arrêt demandé
d'Ogmios : c'est le mode des .exe (Ogmios garde Lugus). Un programme qui écrirait dans son propre code serait suivi par
Lugus, pas par la traduction faite au départ. VTX_INTERPRETE joue sans traduction ; VTX_COMPTE écrit le compte et la
part traduite. Hors d'un processeur x86-64 (un PC ARM), le .exe joue par Lugus.

**0.5zw, pour Windows.** Sous Windows, le test de la traduction s'est figé (le .bat arrêté par Ctrl+C), sans message.
Deux suspects, corrigés ensemble : le mot lu par `natif_lire` revenait comme un u128 dans rax:rdx, une convention que
Rust tient sous Linux mais dont rien ne garantit la forme sous Windows (il passe maintenant par `natif_tampon`, deux
u64 dans la machine : plus rien de 128 bits ne traverse un appel) ; et un plantage du .exe ouvrait la boîte de Windows
« a cessé de fonctionner », qui attend (SetErrorMode la retire ; SetUnhandledExceptionFilter écrit le code et
l'adresse de l'exception, puis le .exe s'arrête). Le test dit chaque programme avant de le jouer, sur l'écran et dans
le journal, et arrête au bout de deux minutes un programme figé : la prochaine fois, on saura lequel.

**Mesuré chez le créateur (0.5zw, Windows 10).** Tout conforme : les 20 programmes traduits et joués par Lugus seul
donnent le même texte et le même nombre d'instructions ; le banc : 0,42 s traduit contre 0,93 s, un gain de 2,2 sur
son processeur (3 à 4 ici). La cause du figement de 0.5zv était donc bien le mot de 128 bits rendu par la convention
d'appel.

## 33. Les quatre vérités (9 novembre, 0.5zx)

Le créateur : remplacer un test inutile (le banc, rejoué en double dans le .bat) par un test **visible**, qui montre
le quaternaire. `exemples128/quatre_verites.vtx` : les quatre valeurs et leurs deux preuves ; la table de `fusion`
(rassembler deux témoignages : vrai et faux donnent variable, inconnu ne change rien) et celle de `et4` ; le conseil
d'Alésia, trois éclaireurs par porte, une décision par `selon` (vrai : les remparts ; faux : on dort ; inconnu : on
envoie un éclaireur ; variable : on réunit le conseil) ; ce qu'un booléen aurait dit (l'absence de nouvelles devient
« non », la contradiction du gué disparaît) ; seize fusions en une seule instruction OU. `tests/test_quatre_verites.py`
recalcule les tables d'après les deux bits de preuve, vérifie chaque porte, les mêmes mots par vtx128.py et vtxc128,
et le .exe traduit contre Lugus seul ; le .bat joue le .exe à l'écran.

## 34. Le duel du binaire et du quaternaire (9 novembre, 0.5zy)

Le créateur : « 0 a plus d'intérêt à annoncer une inconnue ; 1, 2, 3 sont des réponses (non, oui, variable) ». C'est
la lecture de Belnap : 0 n'a aucune preuve (personne n'a répondu), les trois autres en ont au moins une. Et la
question : comment démontrer que le quaternaire fonctionne mieux que le binaire ?

`exemples128/duel.vtx` : 65 536 portes, trois éclaireurs chacune ; un quart voient les légions ; un éclaireur sur trois
se tait, et celui qui parle se trompe une fois sur vingt. Quatre méthodes sur les mêmes rapports, mesurées par
`instructions()` (nouveau, Lugus, service 25 : le compte des instructions jouées) :

| | erreurs | à vérifier | instructions |
|---|---|---|---|
| A. binaire naïf (le silence vaut non, le dernier a raison) | 7 762 (12 %) | 0 | 4 920 828 |
| B. binaire juste, une porte à la fois, deux booléens | 809 (1 %) | 8 016 | 5 789 605 |
| C. binaire d'expert, deux plans de bits, 64 portes par mot | 809 | 8 016 | 128 016 |
| D. quaternaire, écrit porte par porte, joué 32 à la fois | 809 | 8 016 | 284 984 |

**Ce que le duel dit, honnêtement.** Le binaire naïf se trompe dix fois plus et ne sait pas qu'il se trompe ; le
quaternaire prend les mêmes décisions que le binaire juste (les silences sont ses inconnus, les contradictions ses
variables) avec **20 fois moins d'instructions**. Mais le binaire d'expert, qui a réinventé à la main les deux bits de
preuve en deux plans de bits, va **2,2 fois plus vite** que notre quaternaire : sur une machine binaire, deux plans de
bits valent deux bits de preuve, il n'y a pas de bit magique. Deux raisons, qui sont deux chantiers :
- Lugus ne range que **32 logiques par mot**, la moitié de son mot de 128 bits (les tableaux de logiques suivent
  l'entier de 64 bits) ; à 64 par mot, le compte d'instructions des boucles réécrites tomberait de moitié ;
- le compilateur réécrit chaque boucle à part : sept passes sur la mémoire, là où l'expert n'en fait qu'une ; fondre
  les boucles voisines qui parcourent les mêmes tableaux rattraperait l'expert.
L'avantage qui reste au quaternaire, même à vitesse égale : il s'écrit comme on pense (porte par porte, fusion,
selon), et l'on ne peut pas oublier le silence ni la contradiction ; l'expert a dû inventer ses plans et ses masques.

`tests/test_duel.py` : mêmes mots par vtx128.py et vtxc128 ; B, C et D prennent exactement les mêmes décisions ; A se
trompe au moins cinq fois plus ; D joue au moins cinq fois moins que B ; le .exe traduit dit la même chose que Lugus.
Les quatre vérités font maintenant 32 fusions d'un coup (un entier de Lugus porte 32 logiques). Le pas à pas de
vtxc/test_vtxc128.py laisse de côté les programmes qui écrivent `instructions()` : en pas à pas leur code est plus
long, ils écrivent d'autres nombres, à juste titre.

## 35. Soixante-quatre logiques par mot, et les boucles fondues (9 novembre, 0.5zz)

Le duel l'avait montré : Lugus ne rangeait que 32 logiques par mot, la moitié de son mot de 128 bits, et son
quaternaire faisait sept passes là où l'expert n'en faisait qu'une. Les deux sont corrigés, dans vtx128.py et dans
vtxc128, avec les mêmes mots.

**64 par mot.** Les tableaux de quits et de logiques de Lugus rangent 64 éléments par mot (`t[i]` : le mot `i >> 6`, le
quit `i & 63`). Les calculs sur ces mots passent par `__large(e)`, une génération à part, simple et la même dans les
deux compilateurs : chaque opération à toute la largeur (AND.L, OR.L, ET4.L, QEGAL.L, COMPTE.L…, LDQ.L et STQ.L pour
un seul élément), la pile pour le second opérande, les adresses et les décalages à la largeur ordinaire ; une constante
d'un mot entier de quits (0x5555…, 0xAAAA…, 0xFFFF…) y vaut le motif répété sur 128 bits. Un entier ordinaire de Lugus
(64 bits) porte toujours 32 logiques : `fusion(a, b)` sur des entiers en fusionne 32.

**Les boucles fondues.** Deux boucles voisines `pour i dans a..b`, de même variable et mêmes bornes (un nombre, ou la
même variable), qui se réécrivent chacune mot par mot, sont fondues quand la boucle fondue se réécrit encore : chaque
élément ne dépend que des éléments de même indice, l'ordre des calculs d'un même indice est gardé. Une borne ne doit pas
être l'accumulateur d'une des boucles. Le test de réécriture ne change rien (les compteurs de noms sont remis).

**Le duel, refait.** Le quaternaire passe de 284 984 instructions à 144 696 (64 par mot), puis 80 941 (une seule
passe) : **1,6 fois moins que le binaire d'expert** (128 016), et 71 fois moins que le binaire juste, pour les mêmes
décisions. (L'expert pourrait encore affûter son code à la main ; le quaternaire, lui, s'écrit porte par porte.)

**Vérifié.** `tests/test_rangees128.py` : des programmes au hasard (tailles qui ne remplissent pas les mots, bornes au
milieu des mots, boucles voisines de mêmes bornes ou non, quits et logiques, toutes les opérations quit par quit,
comptes et sommes) : mêmes mots par les deux compilateurs, et Lugus écrit ce que Python calcule élément par élément.
`tests/test_vtx128_differentiel.py` laisse de côté `exemples64/quaternaire64.vtx`, qui compare les deux mots d'un
tableau de logiques (32 par mot sur le SPU-64, 64 sur Lugus : deux rangements, à juste titre).

**Trouvé en route par le test au hasard.** Dans une boucle réécrite, les écritures de mots passaient avant les comptes :
un compte qui lisait un tableau écrit plus loin dans la même boucle (`s = s + ta[i]` puis `ta[i] = …`) lisait le
nouveau mot au lieu de l'ancien. Rare dans une seule boucle, fréquent une fois les boucles fondues. Les écritures et les
comptes gardent maintenant l'ordre du corps, dans les deux compilateurs (200 programmes au hasard : conformes).

## 36. La traduction avance, et un écart sous Windows à comprendre (10 novembre, 0.5zza)

**L'écart.** Chez le créateur, 0.5zz : tout conforme sauf `test_rangees128.py`, qui dit « programme 137 : mêmes mots :
265 contre None », sans message, puis le .bat arrêté par Ctrl+C. Ici le même programme (même graine) se compile juste,
400 fois de suite, même avec une petite pile : la cause n'est pas trouvée. « None » veut dire que `lugus compiler` a
rendu un code d'erreur sans rien écrire sur sa sortie d'erreur : un plantage, ou un fichier tenu un instant par
l'antivirus. Pour le savoir : le test écrit maintenant le code de retour et les deux sorties, donne à chaque programme
son fichier de mots, réessaie une fois, dit où il en est tous les 20 programmes (à l'écran et dans le journal) ; et vtx
comme lugus disent un plantage (code et adresse de l'exception) au lieu d'ouvrir la boîte de Windows qui attend
(`spu128::garde_plantage`, au début de main).

**La traduction.** VTX_PROFIL compte les instructions que la traduction laisse à Lugus, par code et largeur. D'après
lui, traduits maintenant : la division et le reste sans signe à 64 bits (par zéro : tout à un, ou le dividende), LDI
et LDIH (la constante est la demi-instruction suivante, que l'on saute). Et ce qui n'est pas traduit n'oblige plus à
quitter le code traduit : il appelle `natif_rejouer`, qui fait jouer l'instruction par Lugus et revient à la suite
(sortie seulement si la machine est allée ailleurs, s'est arrêtée ou a rendu une erreur). Mesuré ici : le duel entier
0,14 s traduit contre 0,36 à 0,55 s ; le banc 0,29 s contre 0,81 s ; mandel_reaction 4,1 s contre 4,9 s : les flottants
quaternaires (codes #40 à #48, 63 millions d'instructions sur 143) restent le gros du travail, encore joués par Lugus.
Mêmes textes, mêmes sorties, même compte d'instructions partout (tests/test_natif128.py).

## 37. Vercintorix 0.6 : les flottants traduits (10 novembre)

La version passe à 0.6 (branche vtx-0.6, dossier vtx-0.6), à la demande du créateur ; la direction est écrite dans
docs/vtx-0-6-vision.md (le projet « Inv. » en a la copie).

**Les flottants quaternaires dans le code traduit.** L'addition, la soustraction, le produit, le quotient, la racine,
les comparaisons, la négation, l'état et les conversions depuis les entiers (codes #40 à #49, #5B à #5D, aux trois
largeurs) sont appelés directement depuis le x86-64 : `natif_flot::<OP, W>`, une fonction par code et par largeur,
dont le format (Q128, Q64, Q32) est une constante, comme dans l'atelier forgé. Plus de décodage par Lugus à chaque
flottant. Mesuré : mandel_reaction 3,3 s traduit contre 4,9 s par Lugus seul (il ne reste plus que 3 instructions sur
143 millions qui ne soient pas traduites) ; freinage 0,031 contre 0,054 s. La forge (Rust compilé) fait Mandelbrot en
1,4 s de calcul : l'écart qui reste est dans le calcul des flottants de 128 bits eux-mêmes et dans les registres
relus en mémoire à chaque instruction, les deux prochains morceaux. Même texte, mêmes sorties et même compte
d'instructions partout (tests/test_natif128.py).

## 37. Les quatre valeurs aux bords du monde (10 novembre, 0.6)

Le créateur : étendre les quatre valeurs pour les rendre exploitables. Le premier pas : là où un programme touche le
monde (le clavier, un texte lu, un fichier), la réponse dit si elle est sue, au lieu de devenir un zéro ou un « non »
en silence. Dans le prélude de Lugus (les mêmes mots par vtx128.py et vtxc128) : `de_preuves`, `vers_logique`,
`lire_logique`, `nombre_su`, `fichier_present`, `temoins` (le tableau de la syntaxe). La règle est celle de Belnap :
deux preuves, une du oui et une du non ; aucune, inconnu ; les deux, variable.

`exemples128/bords_du_monde.vtx` : trois guetteurs répondent au clavier (rien reste inconnu, oui puis non donne
variable, et le conseil décide par `selon`) ; un relevé de nombres où la ligne vide est inconnue et « beaucoup » est
faux, au lieu d'un zéro chacun ; un registre absent ; des témoignages rassemblés. `tests/test_bords128.py` : chaque
cas, les mêmes mots, et la démonstration au clavier traduite comme jouée par Lugus seul, pour quatre jeux de réponses.

Limite dite : `fichier_present` ne distingue pas encore « absent » de « pas de dossier où chercher » (les deux
rendent faux ; le second devrait être inconnu) : il faudra un service de la machine qui le dise. Senos et Dunon
n'ont pas encore ces fonctions.

Trouvé par le test du SPU-64 contre Lugus : les textes écrits dans une fonction du prélude vont dans **chaque**
programme, même quand la fonction n'y sert pas (un petit programme passait de 23 à 154 mots, et son `@0[100]` tombait
dans le code). `vers_logique` ne garde donc aucun texte : elle compare l'empreinte du mot (ses lettres en base 257,
`__empreinte`) à celles des mots compris, calculées d'avance. Règle pour le prélude : pas de texte littéral.

**Les livraisons allégées (0.6b).** Le créateur : alléger les tests et les dossiers envoyés. Le paquet d'essai ne
porte plus que ce qui sert à construire et à essayer (AUTEUR, COMMENCER, LISEZMOI, vtx.py, vtx64.py, vtx128.py, vtx-rs,
vtxc, spu64, spu128, chimie, natif, les exemples, bibliotheque, docs et les tests que joue le .bat) : 3,8 Mo au lieu de
5,7 ; il a été extrait, construit et testé seul avant l'envoi. Le dépôt GitHub garde tout (conformité, mesures,
vérification complète). Le .bat ne rejoue plus à chaque essai ce qui est stable (l'exécutable, les quatre vérités).

## 38. Les quatre valeurs partout : logique[] (11 novembre, 0.6c)

Le créateur : « le rôle du 0 et du 4, inconnu et variable, doivent être compris ». Le 0 n'est pas une réponse : c'est
l'absence de réponse ; 1, 2 et 3 en sont. Pour que ce rôle tienne dans les programmes, les quatre valeurs doivent
pouvoir vivre partout où vit un nombre : la première place qui manquait, c'est le tableau qui grandit et se passe à
une fonction.

`logique[]`, dans vtx128.py et vtxc128 (les mêmes mots) : le type se déclare ou se reconnaît à un littéral qui porte un
logique écrit ; la passe des textes et des tableaux (typer_textes) sait quelles variables, quels paramètres et quels
retours sont des tableaux de logiques, lit `t[i]` par `comme_logique`, range par le code (`vrai` et `faux` écrits : 2
et 1, pas les entiers 1 et 0), et fait de même pour ajouter, inserer, indice, contient, retirer, enlever. Dessous, c'est
le tableau dynamique ordinaire : une case, un mot. `exemples128/conseil.vtx` : la mémoire du conseil, cinq questions
d'abord inconnues, des témoignages qui s'ajoutent sans s'effacer (vrai puis faux : variable), les questions restées à
demander, les paroles rassemblées. `tests/test_logiques128.py` : huit cas, les mêmes mots, traduit comme joué.

Limites dites : un littéral fait de lectures (`[t[0], t[2]]`) n'est pas reconnu comme tableau de logiques (il faut un
logique écrit, ou le type) ; le tableau rangé (64 par mot) ne se passe toujours pas à une fonction ; Senos et Dunon
n'ont ni logique[] ni les fonctions des bords du monde : c'est la suite.

## 39. Lugus contre C, Rust, Java et Python (11 novembre)

Le créateur : la traduction va deux fois plus vite, mais comparée aux meilleurs langages ? Le même banc (un crible
jusqu'à deux millions, fib(27) en récursion, trois millions de brassages) écrit dans chaque langage, en entiers de 64
bits puis de 128 bits ; tous écrivent les mêmes trois résultats. Le meilleur temps de plusieurs lancements, programme
entier (démarrage compris), sur la machine de travail (Xeon 2,1 GHz). `mesures/banc_langages/`.

| | 64 bits | 128 bits |
|---|---|---|
| C (gcc -O2) | 0,029 s | 0,044 s |
| Rust (-O) | 0,030 s | 0,051 s |
| Java | 0,099 s | 1,129 s (BigInteger : pas d'entier de 128 bits) |
| **Lugus traduit** | 0,268 s | 0,457 s |
| Lugus seul | 0,706 s | 1,148 s |
| Python 3 | 1,206 s | 1,731 s |

**Dit sans fard.** Lugus traduit est 4,5 fois plus rapide que Python et 2,6 fois plus que Lugus seul ; il est **9 fois
plus lent que C et Rust** en 64 bits comme en 128, et 2,7 fois plus lent que Java en 64 bits. En 128 bits il bat Java
de 2,5 fois : le mot de 128 bits est natif chez Lugus, pas chez Java. L'écart avec C a des causes connues, toutes dans
la traduction et non dans le langage : chaque registre de Lugus vit en mémoire (une lecture et une écriture par
instruction, là où C garde tout dans les registres du processeur) ; chaque accès à la mémoire de Lugus passe par un
appel (les pages du cube) ; les drapeaux z et c sont écrits à chaque instruction ; aucune optimisation entre
instructions. Les prochains gains, dans l'ordre de ce qu'ils rapportent : les registres de Lugus dans ceux du
processeur, l'accès direct aux pages déjà ouvertes, les drapeaux calculés seulement quand ils sont lus.
(Le banc à 128 bits de Lugus garde des indices de 64 bits dans le crible ; C et Rust y sont tout en 128.)

## 40. T, U et la valeur variable (11 novembre) : la lecture proposée

La question du créateur : entre l'ADN et l'ARN, T (en mémoire) et U (en écriture) sont-ils la valeur variable ? U
est-il la valeur variable qui se fixe en T ? T est-il l'indicateur d'une valeur variable présentée en U à
l'exploitation ? Et cela peut-il accélérer le langage ?

**Ce qui est déjà gravé** (23 octobre) : A = 0, C = 1, G = 2, T = U = 3 ; T est le résultat fixé (ADN), U le travail
(ARN) ; le brin est un quit de marque à côté du mot (libre, ADN, ARN), pas dans sa valeur. Donc T et U sont la **même
valeur 3**, celle que Belnap appelle variable ; ce qui les distingue est le brin du mot qui la porte.

**Deux axes, à ne pas confondre.** La valeur dit ce qu'on sait (inconnu, faux, vrai, variable : rien, un non, un oui,
les deux). Le brin dit si le mot peut encore changer (ARN : oui ; ADN : non). « Variable » chez Belnap est une
contradiction, pas « une chose qui varie » : le mot français invite à mêler les deux axes, et c'est en les croisant
qu'on obtient la lecture utile, la deuxième du créateur, précisée :
- **U : la contradiction ouverte.** Deux témoignages contraires, dans un mot de travail : on a encore le droit de la
  trancher (un nouveau témoin, une vérification), ou de l'annuler (une hypothèse).
- **T : la contradiction constatée.** Fixée dans l'ADN : elle fait partie de ce qui a été établi, on ne la retouche
  plus ; qui la lit sait qu'elle a été vue et gardée telle.
- Et de même pour les trois autres valeurs : en ARN elles sont provisoires, en ADN acquises. T et U sont le seul endroit
  où l'alphabet le montre, parce que 3 est la seule valeur que de nouveaux témoignages ne peuvent plus changer.

**Ce que cela accélère, à mesurer.**
1. *La saturation.* Dans l'ordre du savoir, on ne fait que monter : inconnu, puis vrai ou faux, puis variable. Une
   fusion ne redescend jamais. Un mot tout à 3 est saturé (aucun témoignage ne le changera), un mot tout à 0 est neutre
   (il ne change rien à ce qu'on fusionne avec lui) : une boucle de fusion peut sauter les deux sans les calculer.
2. *L'ADN est une constante.* Un mot d'ADN ne change plus : la traduction peut le lire directement, sans passer par
   la porte des pages, le garder dans un registre, ne jamais le relire ; une réaction dont toutes les entrées sont de
   l'ADN a un résultat qu'on peut garder (le souvenir). C'est le deuxième des trois coûts mesurés contre C.
3. *L'ARN est privé.* Une copie de travail n'appartient qu'à celui qui travaille : pas de partage à surveiller entre
   les tâches du tapis roulant ; seul `fixer` la rend publique.

**Mesuré ce jour, et sans gain :** ne plus écrire z et c quand l'instruction suivante les pose sans les lire (la
troisième cause de l'écart avec C). Conforme partout, mais le temps ne bouge pas de façon mesurable (0,186 s contre
0,179 s de processeur sur le banc, dans le bruit). Gardé parce que juste et sans coût ; les gains sont ailleurs : les
registres et l'accès à la mémoire.

## 41. Le codon : la contradiction en suspens (11 novembre, 0.6d)

**L'idée du créateur**, devant le tableau du code génétique : une contradiction ne doit pas être un déchet ; qu'elle
garde de quoi être réétudiée, avec un délai, et que la lecture se fasse comme celle d'un codon, trois lettres qui
donnent une fonction parmi une vingtaine.

**Le compte.** Trois lectures à quatre valeurs font 64 codons écrits dans l'ordre. Si l'ordre ne compte pas (trois
témoins de même rang), il reste exactement **20 situations** : 4 unanimités, 12 « deux contre un », 4 « trois avis
différents ». Honnêteté sur la biologie : la cellule ne compte pas ainsi (chez elle l'ordre compte, et les 64 codons
donnent 20 acides aminés par redondance, surtout sur la troisième lettre) ; le compte sans ordre est le code de
combinaison de Gamow (années 1950), juste en mathématiques, faux pour le vivant. Les deux lectures servent : sans
ordre pour des témoins égaux (faite), avec ordre quand la place a un rôle (à faire).

**Ce qui est construit** (`bibliotheque/codon.vtx`, en vtx, sans toucher aux compilateurs ni au prélude) :
- un dossier est un entier : trois lettres (6 bits), l'état (en suspens : U ; tranché ; échu : fixé en T), l'âge ;
- `codon(a, b, c)`, `lettre(d, k)`, `situation(d)` (0 à 19, le même numéro dans tout ordre), `nom_situation(d)` ;
- `verdict(d)` : vrai si les oui francs dépassent tout le reste exprimé (les non et les témoins partagés), faux de
  même, inconnu si personne n'a parlé, variable sinon. Les 64 réponses tiennent en deux entiers, deux bits par codon :
  une seule lecture de table ; `penche(d)`, `absents(d)` ;
- `recouper(d, k, parole)` : la lecture nouvelle s'ajoute à ce que la place disait (un témoin qui se dédit devient un
  témoin partagé ; rien ne revient à inconnu) ; si le codon change, l'étude reprend, même sur un dossier fixé ;
- `consolider(d)` : le tri. Majorité franche : tranché. Sinon le dossier vieillit ; après `delai()` = 3 tris sans rien
  de neuf, il est échu. Le délai se compte en tris, pas en secondes : le même programme donne le même résultat ;
- la table du programmeur : un tableau de 20 cases indexé par `situation(d)` (dans l'exemple, un conseil prudent).

**Mesuré.** Sur les 64 codons, la fusion seule répond « variable » 49 fois. Le codon en tranche 26, en laisse 37 en
suspens (dont chacun dit de quel côté il penche et s'il lui reste un absent à entendre), 1 est le silence. Coût : un
tri de dossier 63 instructions, contre 35 pour la fusion de trois lectures (184 avant la table en deux entiers).
`tests/test_codon.py` vérifie les 64 codons contre une référence en Python, la vie d'un dossier, et les mêmes mots.

**Ce qui ne va pas encore, dit.**
- Le codon dit ce qui a été dit, pas par qui : la liste des sources reste à garder à part si on la veut.
- « La majorité l'emporte » est un choix, pas une vérité : deux menteurs battent un témoin juste. D'où la table du
  programmeur ; le verdict fourni n'est qu'une table par défaut.
- Trois lectures seulement : un quatrième témoin n'a pas de place. À voir : des codons en chaîne (un gène).
- Pas encore de `selon` sur une situation dans le langage : on passe par un tableau ou des `si`.
- Trouvé en route : sur Lugus, un tableau de textes rangé dans une variable ne s'affiche pas comme des textes
  (`soit t = ["a", "b"]; afficher(t[0]);` écrit un nombre) ; il faut le rendre par une fonction `: texte`. À corriger
  dans les deux compilateurs.

**Le codon avec ordre (0.6e).** Chaque place a son rôle : places 0 et 1, deux lectures de premier rang (la mémoire
et la lecture nouvelle, égales entre elles) ; place 2, le recoupement, de second rang. Règle : si les deux premières
donnent une réponse franche (un oui ou un non, sans contradiction), la troisième ne change rien ; si elles se
contredisent ou se taisent, la troisième tranche si elle est franche. `verdict_ordonne(d)` (table en deux entiers),
`case_pleine(d)`, `situation_ordonnee(d)` (40 numéros : 10 paires sans ordre pour les deux premières, fois 4),
`consolider_ordonne(d)`. L'exemple écrit le tableau comme celui du vivant (A inconnu, C faux, G vrai, U variable) :

           A      C      G      U
    A     ACGU   CCCC   GGGG   UCGU
    C     CCCC   CCCC   UCGU   UCGU
    G     GGGG   UCGU   GGGG   UCGU
    U     UCGU   UCGU   UCGU   UCGU

*Mesuré.* 6 cases pleines sur 16 (le code génétique : 8 sur 16) ; 44 codons tranchés sur 64 (sans ordre : 26 ; la
fusion seule : 14). Changer une lettre change le verdict, sur 192 essais par place : sans ordre 88, 88, 88 ; avec
ordre 82, 82, **102**.

*Une annonce fausse, corrigée.* Il avait été dit que la troisième lettre serait la moins sensible, comme dans le
code génétique. C'est l'inverse : elle est la plus sensible (102 contre 82). La raison est de fond : un recoupement
qui tranche est décisif partout où il est entendu (10 cases sur 16), alors que la troisième lettre du vivant est
surtout redondante. On ne peut pas avoir les deux rôles à la fois ; c'est le rôle de juge qui a été gardé, parce que
c'est lui qui fait sortir une contradiction du suspens. Ce qui reste vrai de l'analogie : dans une case pleine, une
erreur sur la troisième lettre ne change rien.

## 42. Le combat : quatre réactions pour quatre valeurs (11 novembre, 0.6f)

**La demande du créateur :** un test plus explicite, un combat avec un personnage dont l'IA a quatre réactions selon
ce qui arrive.

**`exemples128/combat.vtx`.** Brennos, garde gaulois, face à un légionnaire. À chaque tour : une charge, un recul,
une cachette ou une feinte. Le garde ne le sait que par ses sens : la vue et l'ouïe (premier rang), le flair (le
recoupement). Sa question : « est-ce qu'il me frappe ? ». vrai : parer et riposter ; faux : attaquer ; inconnu :
chercher ; variable : se garder. La réponse est `verdict_ordonne` du codon (vue, ouïe, flair) : une feinte (un sens
dit oui, l'autre non) laisse le garde en garde, sauf si le flair la perce, et alors il pare ou attaque.

**Le tournoi : les mêmes 500 combats pour quatre gardes** (20 points de vie contre 36, 60 tours au plus) :

| Garde | Gagnés | Perdus | Vie restante |
|---|---|---|---|
| Brennos, quatre valeurs et le codon | 499 | 1 | 15 |
| quatre valeurs, la fusion seule | 495 | 5 | 13 |
| binaire prudent (pas de preuve qu'il recule : je pare) | 418 | 82 | 7 |
| binaire hardi (pas d'alarme : j'attaque) | 200 | 300 | 2 |

**Ce que cela dit, et ce que cela ne dit pas.**
- L'écart vient surtout des quatre valeurs elles-mêmes : savoir qu'on ne sait pas (chercher au lieu de frapper le
  vide) et savoir qu'on est trompé (se garder au lieu de mordre à la feinte).
- Le codon ajoute peu ici : 499 contre 495, 15 points de vie contre 13. Il ne sert que dans une feinte sur quatre.
- Les règles du combat sont inventées pour l'exemple, et réglées pour que les gardes se départagent (avec un
  légionnaire à 20 points de vie, le binaire prudent gagnait lui aussi 500 fois sur 500). Ce qui se mesure est
  l'écart entre les gardes à règles égales, pas une vérité sur les jeux.
- Un programmeur binaire peut écrire le même garde avec deux bits et une table : c'est Belnap fait à la main. Le
  gain du langage est que ce soit natif, vérifié, et qu'on ne puisse pas oublier un des quatre cas (`selon`).

**Corrigé en route :** sur Lugus, un tableau de textes écrit et rangé dans une variable (`soit t = ["a", "b"];`)
voit maintenant ses cases comme des textes (affichage, `+`, `==`), dans vtx128.py et vtxc128, mêmes mots.
`tests/test_combat.py` : mêmes mots, traduit = Lugus seul, les quatre réactions, le tournoi, et la machine en Python.

**Le hasard de la valeur variable (0.6g), sur l'avis du créateur :** devant une contradiction, une réaction fixe
donne toujours le même résultat ; ne vaudrait-il pas mieux tirer au sort, et n'est-ce pas là que le codon gagne ?
Deux changements pour le mesurer : le légionnaire **apprend** (derrière une feinte, il fait ce qui a battu la
dernière réaction du garde à une feinte ; et parer une feinte vide coûte 2), et un garde peut, devant « variable »,
**tirer au sort** entre parer (5 fois sur 9) et attaquer (4 sur 9) au lieu de se garder.

| Garde (500 combats) | La garde tient (coût 1) | La garde est enfoncée (coût 3) |
|---|---|---|
| le codon et le hasard | 494 | 494 |
| le codon seul | 499 | 474 |
| la fusion et le hasard | 457 | 457 |
| la fusion seule | 479 | 199 |
| binaire prudent | 64 | 64 |
| binaire hardi | 23 | 23 |

- **Le hasard ne gagne que s'il n'existe pas de réponse sûre.** Tant que se garder ne coûte presque rien, la
  réaction fixe reste la meilleure (499 contre 494) ; dès que la garde peut être enfoncée, celui qui répond toujours
  pareil se fait lire et le tirage passe devant (494 contre 474 ; sans codon, 457 contre 199).
- **Le codon gagne nettement face à un adversaire qui apprend** (499 contre 479, et 474 contre 199) : chaque feinte
  percée par le flair est une feinte où il n'y a ni à se garder ni à tirer au sort.
- Le tirage ne dépend pas des règles : il fait 494 dans les deux cas. C'est sa qualité (on ne peut pas l'exploiter)
  et sa limite (il ne profite pas d'une réponse sûre quand il y en a une).
- Les binaires s'effondrent (64 et 23 sur 500) : le légionnaire apprend vite ce que fait un garde à deux réactions.
- Pas encore fait : des poids de tirage donnés par le codon (son penchant) ; ici une feinte non percée est toujours
  « un oui contre un non », sans penchant.

## 43. Dunon fait le travail de Lugus (11 novembre, 0.6h)

**La demande du créateur :** Senos et Dunon doivent faire le même travail que Lugus (seule la finesse en bits
change), en gardant la lecture des programmes déjà écrits.

**Fait sur Dunon (le SPU-64), dans vtx64.py et vtxc64, mêmes mots :**
- les quatre valeurs aux bords du monde : `de_preuves`, `vers_logique`, `lire_logique`, `nombre_su`,
  `fichier_present`, `temoins` (le même texte que dans le prélude de Lugus) ;
- `logique[]` : les tableaux dynamiques de logiques (déclarés, reconnus à leurs valeurs écrites, passés aux
  fonctions, allongés, copiés) ;
- un tableau de textes écrit et rangé dans une variable voit ses cases comme des textes (le défaut existait aussi
  sur Dunon).

**Vérifié.**
- *Le même travail :* `conseil.vtx` et `combat.vtx`, écrits pour Lugus, écrivent sur Dunon exactement la même
  sortie, à l'octet près (le tournoi compris) ; `bords_du_monde.vtx` aussi, pour quatre jeux de réponses au clavier.
- *La lecture de l'ancien :* les 47 programmes des dossiers d'exemples et de la bibliothèque que Dunon acceptait
  donnent, après ces ajouts, exactement les mêmes mots qu'avant (comparaison avec le compilateur d'avant).
- `tests/test_bords64.py`, `tests/test_logiques64.py`.

**Ce qui manque encore, dit.**
- `instructions()` n'existe pas sur Dunon : `exemples128/codon.vtx`, qui mesure son coût, n'y compile pas (la
  bibliothèque `codon.vtx` elle-même y marche : le combat s'en sert).
- La traduction en x86-64 et les exécutables autonomes restent propres à Lugus.
- Les tableaux rangés 64 par mot et les boucles fondues sont de Lugus (sur Dunon : 32 par mot, sans fusion).
- Senos (32 bits) n'a rien reçu : il était gelé ; à décider avec le créateur s'il faut le dégeler.
- Trouvé en route : `lugus PROG.vtx` ne lit pas le clavier (les réponses restent inconnues) ; l'exécutable de Lugus
  et `vtx64 PROG.vtx` le lisent. À corriger.

**Suite (0.6i) : deux manques comblés.**
- `instructions()` existe sur Dunon (service 25, machine Rust et machine de référence en Python, même compte) :
  `exemples128/codon.vtx` y compile et écrit ce que Lugus écrit, sauf le compte lui-même (un tri de dossier : 71
  instructions de Dunon, 63 de Lugus).
- `lugus PROG.vtx` lit le clavier, comme l'exécutable de Lugus et comme Dunon. Devant quelqu'un (un terminal), ce que
  le programme écrit paraît aussitôt ; sinon la sortie reste rendue à la fin, comme avant. `VTX_SANS_CLAVIER=1`
  retire le clavier ; `verifier.py` lance ses étapes sans clavier (une lecture y est la fin de l'entrée).

**Senos (le 32 bits) : l'avis donné au créateur, qui se demande s'il faut l'arrêter et donner son nom à autre chose.**
L'arrêter, oui : il reste lisible et vérifié (les anciens programmes tournent), mais ne reçoit plus rien de neuf ;
chaque ajout porté sur trois machines coûte trois fois, et c'est son compilateur, le plus ancien, qui risquerait le
plus de changer les mots d'un vieux programme. Changer le sens du nom, plutôt non : « senos » veut dire « l'ancien »
en gaulois, ce qui convient exactement à une machine gelée, et les documents, les dossiers et les tests disent
partout « Senos » pour le 32 bits ; le réemployer brouillerait la lecture de l'ancien. La décision revient au
créateur.

## 44. La vitesse de la traduction (11 novembre, 0.6j)

**La demande du créateur :** de la vitesse.

**Ce qui a été essayé, dans l'ordre, et ce que chaque pas a donné** (le banc `banc_traduction.vtx`, 130 millions
d'instructions de Lugus ; avant : 0,26 s) :
1. *Le compte des instructions dans un registre du processeur (r12) au lieu de la mémoire.* Attendu : un gros gain
   (chaque instruction attendait l'écriture de la précédente). Mesuré : **rien**. Le pas est gardé (il est juste, et
   il libère les drapeaux du processeur pour le pas 3), mais ce n'était pas le frein.
2. *Lire et écrire la mémoire de Lugus sans appel.* Le vrai frein : les variables d'un programme vivent dans le
   cadre, en mémoire, et chaque accès appelait une fonction de Lugus. Le code traduit garde maintenant seize pages
   (clé, adresse du premier mot) et y lit ou écrit lui-même ; il n'appelle Lugus que pour une page qu'il ne tient
   pas, ou qui porte un mot d'ADN (les brins : ces pages-là restent toujours vérifiées par Lugus). Une première
   version à deux pages laissait 12 millions d'accès à Lugus (la poignée d'un tableau et ses données se chassaient) ;
   à seize pages il en reste 0,4 million.
3. *Une comparaison suivie d'un saut saute tout de suite*, avec les drapeaux du processeur, sans relire z et c en
   mémoire. Le saut garde son propre morceau pour qui arrive sur lui d'ailleurs.
4. *Les opérations sur tout le mot de 128 bits sont traduites* (addition et soustraction avec la retenue du bas au
   haut, comparaison, produit, et, ou, ou exclusif, décalages de 0 à 127, constantes). Avant, chacune était rejouée
   par Lugus : 27 millions sur 167 dans le banc à 128 bits.

**Mesuré** (le meilleur de 12 lancements entrelacés, temps total du programme, lancement compris) :

| | 64 bits | 128 bits |
|---|---|---|
| C (gcc -O2) | 0,025 s | 0,044 s |
| Rust | 0,023 s | 0,038 s |
| Java | 0,087 s | 1,085 s |
| Lugus traduit, avant | 0,207 s | 0,541 s |
| **Lugus traduit, 0.6j** | **0,113 s** | **0,154 s** |
| Lugus seul | 0,710 s | 1,047 s |

L'écart avec C passe de 8 à 4,5 fois (64 bits) et de 12 à 3,5 fois (128 bits). À 128 bits, Lugus traduit est 7 fois
plus rapide que Java (qui n'a pas d'entier de 128 bits).

**Sur la puissance de Lugus face à C, dit honnêtement.** Un mot de 128 bits ne rend pas un calcul ordinaire plus
rapide : le processeur du PC travaille par 64 bits, et une opération de 128 bits lui coûte deux ou trois des
siennes. Là où la largeur gagne, c'est quand un mot porte beaucoup de petites choses à la fois (64 logiques par mot :
une instruction en traite 64), ou quand il faut des entiers plus grands que 64 bits. C sait aussi faire du 128 bits
(`__int128`), c'est ce que mesure la colonne de droite.

**Vérifié.** Mêmes texte, sorties, registres et compte d'instructions que Lugus seul, sur tous les exemples et les
cas de `tests/test_natif128.py`, dont un nouveau cas « large » (128 bits : retenues, zéro, décalages 0, 1, 63, 64,
65, 127, produit), identique aussi à la machine de référence en Python. `VTX_COMPTE=1` dit maintenant combien
d'accès à la mémoire sont passés par Lugus.

**Ce qui reste entre Lugus et C.** Les registres de Lugus vivent encore dans la mémoire de la machine (chaque
opération les lit et les écrit) ; chaque accès au cadre refait le calcul d'adresse et la vérification de page ; les
appels et retours passent par la mémoire de Lugus et une table. Le prochain pas serait de garder les registres les
plus utilisés dans ceux du processeur, à l'intérieur d'un bloc sans saut.

## 45. La vitesse, deuxième passe (14 novembre, 0.6k)

**Ce qui a été essayé, et ce que chaque pas a donné** (mesuré dans une même séance, le meilleur de 15 lancements) :
1. *Les registres de Lugus les plus utilisés gardés dans ceux du processeur* (r1, r2, r14 la pile, r13 le cadre,
   r9, r10 ; leur moitié basse, dans rbp, r10, r11, r13, r14, r15). Ils retournent dans la machine à chaque sortie
   et avant chaque appel à Lugus, et en reviennent après. Attendu : le grand pas. Mesuré : **presque rien**
   (0 % à 64 bits, 7 % à 128 bits). Le code machine d'une boucle chaude, regardé instruction par instruction
   (`VTX_VIDAGE=fichier` l'écrit), montre pourquoi : les valeurs qui comptaient passaient déjà par le cache du
   processeur ; ce n'était pas le frein. Gardé, parce qu'il est juste et ne coûte rien.
2. *La table des pages du code traduit passe de 16 à 64 pages.* Le tableau du crible en occupe 31 : elles se
   chassaient (433 000 accès repassaient par Lugus ; il en reste 81). Mesuré : **rien** non plus.
3. *Le vrai frein n'était pas dans la traduction mais dans le prélude* : `nouveau` remettait chaque bloc neuf à zéro
   case par case, neuf instructions par case. Créer le tableau du crible coûtait 18 millions d'instructions sur 90.
   C'est maintenant un service de la machine (26), qui fait exactement ce que faisait la boucle : chaque page
   touchée comme elle la touchait (chargée du disque ou créée, l'ADN vérifié), puis effacée d'un coup. Seul le
   nombre d'instructions change (dans les deux compilateurs, mêmes mots ; la machine en Python aussi).
4. *Les drapeaux morts ne sont plus écrits*, en regardant plus loin que l'instruction suivante : à travers MOV, ETG
   et les sauts sans condition, jusqu'à une instruction qui les pose sans les lire. Avant toute instruction qui
   peut sortir du code traduit ou appeler Lugus, ils restent écrits.

**Mesuré** (même séance ; la machine était plus lente ce jour-là qu'à la section 44, d'où d'autres chiffres absolus) :

| | 64 bits | 128 bits |
|---|---|---|
| C (gcc -O2) | 0,028 s | 0,046 s |
| Rust | 0,026 s | 0,040 s |
| Java | 0,094 s | 1,271 s |
| Lugus traduit, 0.6j | 0,158 s | 0,193 s |
| **Lugus traduit, 0.6k** | **0,112 s** | **0,133 s** |
| Lugus seul | 0,766 s | 1,270 s |

L'écart avec C passe de 5,6 à 4,0 fois à 64 bits, et de 4,2 à 2,9 fois à 128 bits. À 128 bits, Lugus traduit va
9 fois plus vite que Java.

**Où en est l'écart, dit honnêtement.** Le crible seul, sur un tableau qui tient dans le cache et sur un tableau
dix fois plus grand, est 3,3 fois plus lent que le même crible en C sur des cases de 128 bits : l'écart ne vient
plus de la mémoire mais du nombre d'instructions que la traduction produit (le compte des instructions, la moitié
haute de chaque registre, les drapeaux encore vivants, la vérification de page à chaque accès). Le gagner demande un
vrai compilateur, qui voit tout un morceau de programme à la fois (où va chaque valeur, quels drapeaux servent) ;
c'est le prochain grand chantier de la vitesse, et il ne se fera pas par petites touches.

## 46. Selon sur plusieurs lectures : la table du programmeur dans le langage (14 novembre, 0.6l)

**Décidé avec le créateur** (après la vitesse, qu'on arrête là : battre C sur un processeur binaire ne dit rien de ce
que vaut le quaternaire) : revenir au langage. D'abord le `selon` sur codon, puis les codons en chaîne (un gène), puis
un Ogmios plus intuitif.

**Ce qui est fait** (vtx128.py et vtxc128 pour Lugus, vtx64.py et vtxc64 pour Dunon, les mêmes mots) :
- `selon (a, b, c) { (vrai, faux|variable, _) { … } … }` : de 2 à 4 lectures dont la place compte ; `_` prend toute
  valeur, `|` donne le choix ; plusieurs motifs par branche, séparés par des virgules ;
- `selon {a, b, c} { {vrai, vrai, _} { … } … }` : des témoins de même rang, sans ordre ;
- la première branche qui convient est jouée ; `autre` prend le reste ;
- le compilateur **refuse une branche inatteignable** (il essaie les 4ⁿ lectures : une branche dont tous les cas sont
  déjà pris par les précédentes est une faute de raisonnement, dite à la compilation) ;
- `selon (x)` garde son sens ; tous les programmes déjà écrits donnent exactement les mêmes mots qu'avant (67 sur
  Lugus, 58 sur Dunon, comparés au compilateur d'avant).

**Dans les exemples.** Le conseil prudent de `exemples128/codon.vtx` n'est plus un tableau de 20 cases indexé par un
numéro de situation, mais un `selon {a, b, c}` qui se lit. En l'écrivant, le compilateur n'a rien dit mais le test a
vu une faute : `{variable, variable, _}` prenait aussi « deux partagés, un absent », que l'ancienne table envoyait
chercher un témoin de plus ; corrigée en nommant les trois cas. C'est la limite de `_` : il dit « n'importe quoi », y
compris l'absence.

**Vérifié** (`tests/test_selon.py`) : des `selon` tirés au hasard (2 à 4 lectures, avec et sans ordre, `_` et `|`,
plusieurs motifs, avec ou sans `autre`), sur Lugus et sur Dunon : mêmes mots par les deux compilateurs de chaque
machine, et sur toutes les combinaisons de lectures la branche jouée est celle d'une référence écrite à part ; les
branches inatteignables refusées par les deux ; des `selon` imbriqués ; les deux verdicts du codon écrits en `selon`
décident comme les tables en deux entiers (64 sur 64) ; le conseil prudent comme l'ancienne table (64 sur 64).

**Le coût.** Un `selon` se déplie en comparaisons : la table en deux entiers du codon reste plus rapide (une lecture)
pour un verdict appelé des millions de fois ; le `selon` est fait pour ce que le programmeur décide et doit pouvoir
relire.

**La suite** : les codons en chaîne (un gène : plus de trois témoins, lus par groupes de trois) ; puis un Ogmios plus
intuitif ; et, avant d'écrire des programmes durables, la version du prélude gardée dans l'ADN (sinon chaque changement
du prélude fait dire « le texte : faux » à la rétrotranscription des programmes rangés avant).

## 47. Le gène : plus de trois témoins (14 novembre, 0.6m)

**La question.** Le codon donne une place à trois témoins ; un quatrième n'en avait pas. Un **gène** est une chaîne de
témoins (un `logique[]`), lue par codons de trois dans l'ordre (le cadre de lecture), puis les verdicts des codons
relus trois par trois, jusqu'à un seul : 3, 9, 27, 81 témoins. Les trois témoins d'un codon sont une **famille** (les
trois éclaireurs d'une porte, les trois sens d'un même instant). Une place qui manque au bout de la chaîne est un témoin
absent : inconnu. Dans `bibliotheque/codon.vtx` : `gene_codon(g, k)`, `gene_codons(g)`, `gene_lire(g)`,
`gene_lire_ordonne(g)`, `gene_plat(g)`, `gene_suspens(g)`.

**Mesuré d'abord, et dit sans fard** (27 témoins en 9 familles ; en Python sur 20 000 questions, puis en vtx sur 400) :

| | décide juste | se trompe | reste en suspens |
|---|---|---|---|
| bruit épars : le compte de tous (`gene_plat`) | 98,5 % | 0,8 % | 0,7 % |
| bruit épars : le gène, première règle | 83,2 % | 0,6 % | 16,2 % |
| bruit épars : le gène, une famille partagée se tait au-dessus | 94,9 % | 1,3 % | 3,6 % |
| familles achetées (une sur quatre ment en bloc) : le compte de tous | 92,3 % | 5,8 % | 1,9 % |
| familles achetées : le gène | 91,2 % | 5,9 % | 2,9 % |

- **Pour décider, le compte de tous est le meilleur.** Regrouper les témoins avant de compter perd de l'information
  (c'est le théorème du jury de Condorcet : avec des témoins indépendants, la majorité de tous est la règle la plus
  sûre). Le gène ne décide pas mieux, et il ne faut pas le présenter ainsi.
- **La première règle était mauvaise** : une seule famille partagée remontait « variable » et bloquait tout le gène (en
  suspens trois fois sur vingt). Corrigée : au-dessus du premier étage, une famille en contradiction **se tait** (elle
  n'apporte ni oui ni non) ; sa contradiction reste marquée en bas.
- **Ce que le gène apporte** : savoir **quelle famille** se contredit (`gene_suspens`), et lire chaque famille avec
  ordre quand ses places ont un rôle (`gene_lire_ordonne`). La structure n'est pas un vote meilleur, c'est une carte.

**L'exemple** `exemples128/gene.vtx` : une question racontée (27 éclaireurs, 9 portes ; les portes 2 et 5 se
contredisent ; tous disent oui), puis la mesure sur 400 questions : bruit épars, le compte de tous 394 justes, le gène
384 ; familles achetées, 371 contre 361. **Vérifié** (`tests/test_gene.py`) : 84 chaînes tirées au hasard (0 à 30
témoins) contre une référence en Python, sur Lugus et sur Dunon, mêmes mots par les deux compilateurs de chacun ;
Dunon écrit ce que Lugus écrit ; le .exe traduit comme Lugus seul.

**Une remarque de biologie** : déplacer le cadre de lecture d'une place change toutes les familles, donc le verdict du
gène (comme une mutation par décalage du cadre dans le vivant) ; le compte de tous, lui, ne change pas. Ce n'est pas une
faute : le cadre fait partie du sens.

## 48. Le chemin de l'ADN, tout en vtx (14 novembre, 0.6n)

**La demande du créateur :** l'ADN et l'ARN doivent être compris en vtx ; le chemin Cube → Hex → ADN → ARN haché entre
Rust, Python et vtx, « ce n'est pas top ».

**Ce qui est fait.** Le lecteur d'ADN écrit en vtx (`chimie/adn.vtx`, embarqué dans lugus) range et transcrit, en plus
de relire. Ses entrées : deux chemins, puis un verbe :
- **ranger** : il lit les mots compilés (le fichier de `lugus compiler`), découpe les molécules (la tête, puis une par
  fonction, de la cible d'un CALL à la suivante ; une frontière O si son code écrit en mémoire ou sort quelque chose),
  marque les isotopes lourds, calcule les trois témoins (la signature de chaque molécule, l'ombre de Reed-Solomon des
  colonnes entrelacées, les neutrons quaternaires des frontières et des isotopes), garde le texte du programme et la
  signature du compilateur, et écrit l'ADN version 4 ;
- **transcrire** : il vérifie et répare, réécrit l'ADN réparé, puis écrit l'ARN : les mots seuls, ou l'ARN avec sa
  coiffe et son isoforme (rapide, sur, memoire, complet ; l'épigénome recopié dans « memoire » et « complet ») ;
- **relire** : comme avant.

`lugus ranger` et `lugus transcrire` passent maintenant par lui : Lugus ne fait que compiler (par vtxc128, lui aussi
écrit en vtx) et lui passer les fichiers. Ce qui reste à Lugus : la rétrotranscription (recompiler le texte gardé et
comparer les mots ; la compilation est vtxc128, la comparaison une ligne), et la lecture de l'ADN au lancement et par
la patrouille, qui sont du travail de machine (comme la mémoire à correction d'erreurs d'un ordinateur).

**L'intron « compilateur ».** Chaque ADN rangé garde la signature des mots du compilateur qui l'a fait. À la
rétrotranscription, si le texte gardé ne redonne plus les mots :
- même compilateur : le texte a été retouché, **faux** ;
- compilateur changé depuis le rangement : on ne peut pas savoir, **inconnu** (« le compilateur a changé depuis le
  rangement : le texte ne peut pas être vérifié ») ;
- ADN rangé avant cet intron : **faux**, avec la réserve « cet ADN ne note pas son compilateur : il a pu changer depuis ».
C'est la réponse au problème vu en 0.6k : chaque changement du prélude faisait dire « faux » à des textes intacts.

**Trouvé en route.** Lugus lisait les mots de son compilateur en prenant le dernier nombre (« 10; ») pour un 0. Sans
effet sur le compilateur, mais la signature différait de celle de Python ; elle est maintenant prise sur les mots avant
le « ; », des deux côtés.

**Vérifié** (`tests/test_adn_chemin.py`) : l'ADN rangé en vtx est celui de Python, octet pour octet, sur quatre
programmes (dont un isotope lourd, un texte en \r\n et accentué) ; trois mots abîmés, transcrits en vtx : les mots
d'origine, et l'ADN réparé réécrit comme Python le réécrit ; les quatre isoformes de l'ARN, au format de Lugus, leur
coiffe reconnue, lancées elles donnent la sortie du programme ; l'épigénome appris recopié dans l'ARN « memoire » ; la
rétrotranscription vrai, faux, inconnu et faux avec réserve. Les suites de l'ADN, du lecteur en vtx, de la patrouille et
de la provenance restent conformes.

**L'autonomie, mise à jour** (section donnée le même jour) : l'ADN passe d'environ 50 % à environ 85 % écrit en vtx ;
l'ensemble, d'environ 45 % à environ 48 %.

## 49. Le chemin dans les deux sens (14 novembre, 0.6n bis)

**La demande du créateur :** réfléchir à la rétrotranscription ; que le chemin ARN, ADN, hex, cube soit fonctionnel
dans les deux sens. Le carnet le disait déjà : « copier l'ADN en ARN pour travailler, refixer l'ARN en ADN pour
garder ».

**La rétrotranscription, au sens de la biologie.** Jusqu'ici, le mot nommait la vérification du texte gardé (recompilé,
redonne-t-il les mots ?). En biologie, c'est autre chose : la transcriptase inverse refait de l'ADN à partir d'un ARN
(l'ADN complémentaire, l'ADNc). Les deux existent maintenant, et les deux sont faites par le lecteur écrit en vtx :
- **ARN → ADN** : `lugus retrotranscrire PROG.arn [PROG-c.adn]`. Un ARN sûr ou complet garde ses témoins : il est
  vérifié et réparé comme un ADN, et si les trois témoins reconnaissent les mots mais pas la coiffe, c'est la coiffe qui
  est abîmée (deux contre un), elle est refaite. Un ARN rapide ou mémoire n'a que sa coiffe : si elle ne reconnaît pas
  les mots, rien ne tranche, l'ARN est **variable** et rien n'est écrit ; sinon ses témoins sont refaits. L'épigénome
  est gardé. Comme l'ADNc de la biologie, celui de vtx n'a pas d'introns : le texte du programme et le nom des
  isotopes ont été retirés à l'épissage (les drapeaux des isotopes restent dans les molécules d'un ARN sûr). Il prend
  le nom `PROG-c.adn`, pour ne jamais écraser l'ADN d'origine, qui a son texte.
- **Le texte gardé** : la vérification aussi est faite en vtx. Le lecteur donne le texte au compilateur de vtx
  (vtxc128, écrit en vtx, lancé sur une machine fille : le service 27, sur Lugus et sur la machine Python), relit ses
  mots et les compare un pour un ; vrai, faux, inconnu (compilateur changé) et faux avec réserve, comme avant.

**Le hex.** L'écriture des mots à la main de l'homme : `VTXHEX01 N SIGNATURE`, puis une ligne par mot, sa place dans
le cube et ses quatre voies :

```
VTXHEX01 107 5859642989249918019
#000000 #0018E001_7FFFFFFF_000A2000_00000000
#000001 #00000000_0000006B_005E0020_00000001
```

Les adresses voyagent avec les données. Le hex n'a pas de témoins : c'est l'écriture brute, celle qu'on peut lire et
retoucher. À la relecture, les lignes vides et `//` sont sautées, les `_` sont libres ; des places qui ne se suivent pas
sont refusées ; un hex retouché depuis qu'il a été écrit (sa signature ne reconnaît plus ses mots) est dit, puis pris
tel qu'il est écrit, parce qu'écrire un programme en hex à la main est un usage légitime.

**Le cube.** La mémoire elle-même : les mots rangés aux points du cube de l'étage 1, à une fréquence (440, le la du
diapason, si rien n'est dit) ; la queue, au point blanc `#FFFFFF`, dit combien il y en a, la coiffe, au point
`#FFFFFE`, les signe. La machine l'écrit (`cube128-1-440.cub`) avec son anti-cube et son ombre, le miroir inversé de
la 0.5, et le relit réparé s'il a été abîmé ou effacé.

**Les commandes.**
- `lugus hex PROG.adn [PROG.hex]` : ADN → hex (aussi depuis un ARN, des mots, un cube) ;
- `lugus cube PROG.adn [FRÉQUENCE]` : → `cube128-1-FRÉQUENCE.cub` (aussi depuis un hex, un ARN, des mots) ;
- `lugus ranger PROG.hex|cube128-1-F.cub|PROG.mots [PROG.adn]` : → ADN (ses témoins refaits) ;
- `lugus retrotranscrire PROG.arn` (ou `lugus ranger PROG.arn`) : ARN → ADNc ;
- `lugus PROG.hex`, `lugus cube128-1-440.cub` : lancés comme un ADN ou un ARN (lus par le lecteur en vtx).

**Vérifié** (`tests/test_adn_deux_sens.py`, 42 contrôles) : sur trois programmes (dont un isotope lourd et des
accents), le hex écrit en vtx est celui de la référence Python, octet pour octet, et redonne les mots ; l'ADN refait
depuis un hex ou un cube est celui de la référence ; l'ADNc de chacune des quatre isoformes est celui de la référence
et a les mots de l'ADN ; un hex et un cube lancés donnent la sortie du programme ; le tour entier, vtx → ADN → ARN →
ADNc → hex → cube → ADN → ARN, lancé, donne la même sortie ; les avaries : hex retouché (dit, pris tel quel), places en
désordre (refusé), un mot abîmé dans le cube et le cube effacé (réparés par l'anti-cube et l'ombre), un ARN sûr abîmé
de deux mots ou à la coiffe abîmée (réparé, le même ADNc que l'ARN intact), un ARN rapide abîmé (variable, rien
d'écrit) ; le texte d'un long programme qui importe une bibliothèque (codon.vtx), vérifié en vtx : vrai.
`test_adn_chemin`, `test_adn_vtx`, `test_adn`, `test_patrouille` et `test_provenance` restent conformes ; les deux compilateurs donnent les mêmes
8681 mots du lecteur.

**Trouvé en route.** La machine lit un texte en mémoire jusqu'à 4096 caractères (c'est fait pour un nom de fichier) :
le texte de codon.vtx (6902) arrivait coupé au compilateur, « erreur ligne 101 ». Le service 27 lit maintenant le texte
entier.

**Ce qui reste en Rust, honnêtement.** La lecture de l'ADN au lancement et par la patrouille (du travail de machine) ;
`lugus pourquoi`, qui vérifie encore le texte par Rust ; et l'orchestration de la machine fille du service 27 (le
compilateur lui-même est vtxc128, en vtx). L'ADN passe d'environ 85 % à environ 92 % écrit en vtx ; l'ensemble, d'environ
48 % à environ 49 %.

**Une question ouverte.** L'ADN écrit ses mots en décimal, pas en bases : le hex est maintenant une station à part.
Écrire les mots de l'ADN en bases (A, C, G, T, deux bits par base) serait plus fidèle au cap « ADN et ARN
hexadécimaux », au prix d'un changement de format (une version 5) : à trancher.

## 50. L'ARNc : le programme naît en ARN (14 novembre, 0.6o)

**La remarque du créateur :** le tour devrait être vtx → ARN → ADNc → hex → cube → hex → ADN → ARN ; « c'est assez
étrange que cet ordre ne soit pas retenu » ; peut-être par un ARNc, une passe de l'ARN sûr assurée par vtx.

**Il avait raison, et c'est ce qui est gravé** (section 40) : U est le travail, T ce qui est fixé. Écrire un programme,
c'est travailler : il naît en ARN ; on le fixe en ADN quand on veut le garder. L'objection faite d'abord (un ARN tiré
sans ADN perd le texte du programme) tombe si l'ARN le porte lui-même.

**L'ARNc**, une cinquième isoforme (`arnc`) : l'ARN sûr (la coiffe, les mots, les trois témoins) qui porte aussi tous
les introns : les isotopes, le texte du programme, la signature du compilateur, l'épigénome s'il y en a un.
- `lugus arnc PROG.vtx [PROG.arn]` : le programme compilé (vtxc128) devient un ARNc, par le lecteur en vtx ; **aucun
  fichier d'ADN n'est écrit** ;
- `lugus PROG.arn` le lance (sous la patrouille, comme un ARN sûr) ;
- `lugus retrotranscrire PROG.arn` rend **l'ADN entier** : celui que `lugus ranger PROG.vtx` aurait écrit, octet pour
  octet ;
- `lugus transcrire PROG.adn PROG.arn --isoforme arnc` : l'aller, sans perte ; ADN → ARNc → ADN redonne le même fichier.

Dit honnêtement : un ARNc contient tout ce que contient l'ADN ; ce qui les distingue est le brin (le travail, ou le
fixé), pas le contenu. Les isoformes rapide, sur, memoire et complet restent des ARN épissés (sans le texte).

**Le tour entier, dans l'ordre du créateur**, descend la chaîne jusqu'au cube puis la remonte station par station :
vtx → ARNc → ADNc → hex → cube → hex → ADN → ARN. Le test précédent sautait le hex au retour (cube → ADN, un raccourci
permis, gardé comme contrôle à part).

**Vérifié** (`tests/test_adn_deux_sens.py`, 51 contrôles) : sur trois programmes (dont un isotope lourd), vtx → ARNc
n'écrit aucun ADN et l'ARNc lancé donne la sortie du programme ; son ADNc est l'ADN de `ranger` et celui de la
référence Python, octet pour octet ; ADNc → ARNc redonne l'ARNc de départ, et le texte est vérifié vrai ; le tour entier
dans le nouvel ordre : la même sortie, les mêmes mots, le hex du retour identique à celui de l'aller. Les deux
compilateurs donnent les mêmes 8951 mots du lecteur ; les suites de l'ADN, du lecteur, de la patrouille et de la
provenance restent conformes.

**En passant** : les chemins ne s'affichent plus avec le préfixe `\\?\` de Windows (non essayé ici : pas de Windows).

## 51. La carte du programme : l'ARN de transfert (15 novembre, 0.6p)

**La direction donnée par le créateur :** Vercintorix doit se rapprocher du langage humain (le doute, les homophones,
l'interprétation, les figures de style) pour qu'une IA y explore plus facilement d'autres raisonnements ; vtx doit être
natif pour l'IA, plus simple, plus fonctionnel. Le contexte d'un programme, au moment de l'écrire, tient à la nature
de ses cases et à leurs racines (dans Ogmios, sur la paillasse). L'ARNc doit accentuer la compréhension du code, et dans
la nature l'ARN ne fait pas qu'un travail.

**Ce qui a été répondu.** L'ambiguïté vit dans le sens, pas dans la grammaire : un texte qui se lirait de deux façons ne
se vérifie plus, et les deux compilateurs ne donneraient plus les mêmes mots. U et T disent si une chose est ouverte ou
fixée, pas quelles lectures sont en jeu : il faudra un troisième axe, les lectures (`supposons … parmi`, puis
`retenir`), à venir. D'abord la carte : c'est elle qui donne le contexte qui tranchera entre deux lectures.

**L'ARN de transfert.** Dans la cellule, l'ARN messager porte le message, l'épissage en tire plusieurs, et l'ARN de
transfert est l'adaptateur : il fait le lien entre un codon et ce qu'il veut dire. vtx avait les deux premiers ; les
mots savaient ce qu'ils font, pas ce qu'ils veulent dire. La carte est cet adaptateur.

**La carte**, un intron de l'ADN et de l'ARNc (`GU carte N`), une ligne par molécule, ses quatre faces (le créateur :
« quatre valeurs, comme par hasard ») :
- **ce qu'elle est** : son nom, son genre (fonction, réaction, empruntée au prélude ou à une bibliothèque, la tête),
  ses lignes dans le texte, sa taille, son en-tête ;
- **ce qu'elle touche**, sur quatre degrés : rien, lit la mémoire, écrit la mémoire, le monde (sorties, fichiers,
  services) ; elle-même, puis avec ses appels. Tiré des mots : les instructions qui lisent, écrivent ou sortent ; pour un
  service (SYS), son numéro est retrouvé en suivant les constantes jusqu'à lui ; un numéro qu'on ne retrouve pas compte
  pour le monde (le doute va du côté prudent) ;
- **ses racines** : sa profondeur depuis la tête (principal est à un pas), les molécules qu'elle appelle ; celles qui
  l'appellent se lisent à l'envers ;
- **ses promesses** : exige, garantit, les exemples vérifiés qui l'appellent, l'isotope lourd.

```
m31|moyenne|reaction|29-33|16|0|3|2|535|1|1|1|0|reaction moyenne(a, b) -> m
```

Les noms viennent du compilateur (vtxc128 écrit `code.carte`, « nom|mot » pour chaque fonction gardée, sans changer
aucun mot ; vtx128.py les tire de ses étiquettes) ; le reste, des mots et du texte gardé. Le lecteur en vtx l'écrit ;
`chimie/adn.py` l'écrit de même, octet pour octet.

**Les commandes.**
- `lugus carte PROG.vtx|PROG.adn|PROG.arn [--tout]` : la carte, en clair. Exemple :

  ```
  moyenne : une réaction, lignes 29 à 33, 16 mots
      reaction moyenne(a, b) -> m
    ce qu'elle touche : rien elle-même ; le monde par ses appels
    ses racines       : appelée par principal ; à 2 pas de la tête ; appelle __afficher_t
    ses promesses     : exige 1, garantit 1, 1 exemple vérifié
  ```

  Elle nomme aussi les fonctions écrites qui n'ont pas de molécule à elles (recopiées en ligne là où elles servent).
  « Le monde par ses appels » d'une réaction pure vient du message d'un contrat rompu : c'est vrai, et c'est utile à
  savoir. D'un `.vtx`, l'ARNc est fait à part et rien n'est écrit à côté du programme.
- Un brin sans carte (un ARN rapide, des mots, un hex, un cube, un ADN d'avant) : ce que touchent les molécules et leurs
  racines viennent de ses mots seuls ; ses noms et ses promesses sont **inconnus**, et la carte le dit.
- `lugus transcrire` refait la carte (le compilateur rend les noms avec les mots, service 27) et la compare : « la carte
  : vrai » ; retouchée, « faux », avec la première molécule où elle ne dit plus ce que disent le texte et les mots ; un
  ADN d'avant la carte, « inconnu ».
- Ogmios (F5 sur Lugus) range maintenant l'ADN par le lecteur en vtx, avec sa carte.

**Vérifié** (`tests/test_carte_arn.py`) : sur six programmes (dont un qui importe une bibliothèque, un isotope lourd,
des noms accentués, des contrats et des exemples), l'ADN avec sa carte est celui de la référence, octet pour octet ;
l'ARNc la porte, et sa rétrotranscription rend l'ADN entier ; chaque face sur un programme fait pour elles (une somme
qui ne touche rien, un remplissage qui écrit la mémoire, principal qui touche le monde ; les profondeurs ; exige,
garantit, un exemple, l'isotope) ; `lugus carte` en clair, `--tout`, sur un `.vtx` ; un ARN rapide ; la carte vraie,
retouchée, absente. Les deux compilateurs donnent les mêmes mots du lecteur ; vtxc128 renouvelé (point fixe) ; les
suites de l'ADN, du lecteur, du chemin dans les deux sens, de la patrouille et de la provenance restent conformes.

**Limites, dites.** Ce qu'une molécule touche est lu dans ses instructions, pas suivi à l'exécution : une écriture
derrière une adresse calculée compte pour « écrit la mémoire » sans dire où. Les noms écrits dans un alphabet autre que
le latin pourraient être lus autrement par les deux compilateurs (les minuscules ne sont faites que pour le latin).

**Les étages, proposés pour la suite.** Les quatre faces vont aux quatre étages d'une même place du cube : l'étage 0 a
le code (ce qu'elle est), les étages 1, 2, 3 recevraient ce qu'elle touche, ses racines et ses promesses ; la même
couleur #RRGGBB, d'un étage à l'autre, lie les quatre faces d'une molécule. Et à la rétrotranscription, un verdict de
Belnap par face : quatre lettres par molécule, un codon de quatre, qui dirait laquelle a changé (« ses racines ont
changé, ses promesses tiennent »).

## 52. Six faces, comme un dé, et le centre (15 novembre, 0.6q)

**L'idée du créateur :** six faces comme un dé, en double ternaire ; « trois valeurs et un indicateur ». Étudiée avant de
continuer (la réponse donnée) :
- **ce qui vient de la structure** : deux bits de preuve donnent toujours trois valeurs qui ont une preuve (oui, non,
  variable) et une qui n'en a pas (inconnu, l'indicateur) ; dans GF(4), les trois éléments non nuls forment un cycle de
  trois, le zéro à part. Un cube a trois axes à deux sens : six faces opposées deux à deux, et le centre ; dans le cube
  chromatique, les trois primaires et leurs trois complémentaires. Les deux brins de l'ADN se lisent en sens contraires,
  et le complément de Watson et Crick est, dans notre codage, 3 − x : la négation de Belnap suivie de la conflation ;
- **ce qui est un hasard** : le 3 des valeurs (2² − 1) et le 3 des axes (l'espace) n'ont pas la même cause ;
- **décidé** : six faces et le centre, oui ; le miroir ternaire et T comme indicateur à côté de U, non : on reste
  quaternaire. **Les étages restent quatre** : dans Lugus, l'étage d'une adresse tient sur deux bits (`adr >> 62`), un
  quit ; six étages sortiraient du quaternaire.

**Les six faces**, en trois paires opposées, et le centre (la section `faces` de l'ADN et de l'ARNc, qui remplace la
`carte` à quatre faces de la 0.6p) :

| axe | une face | la face opposée |
|---|---|---|
| dedans, dehors | ce qu'elle est | ce qu'elle touche |
| d'où elle vient | ses racines (qui l'appelle, sa profondeur) | ses branches (ce qu'elle appelle) |
| le temps | ses promesses (exige, garantit, les exemples, l'isotope lourd) | sa mémoire (son empreinte, son histoire) |

- **le centre** n'est pas écrit dans le fichier : c'est l'état de la molécule **à chaque lecture** du brin (vrai :
  intacte, faux : réparée, variable : abîmée sans réparation, inconnu : le brin n'a pas de témoins). Le cube réagit
  ainsi à chaque valeur, comme le créateur le demandait ;
- **sa mémoire** : l'empreinte de son texte (FNV-1a sur ses lignes), et son histoire d'un rangement à l'autre : le
  rangement relit le brin d'avant et compare les empreintes : « ? » (rien n'était rangé avant), « n » (nouvelle),
  « c » (changée), « iK » (inchangée depuis K rangements). L'empreinte est celle du texte et non des mots : les mots
  d'une fonction changent quand une autre grandit (les adresses des appels), son texte non. Une fonction empruntée n'a
  pas de texte ici : son empreinte est sa taille ;
- à la rétrotranscription, la carte est refaite et comparée ; l'histoire, qui n'est ni dans le texte ni dans les mots, est
  recopiée, pas vérifiée (c'est dit).

```
chute : une réaction, lignes 5 à 12, 48 mots
    reaction chute(h: flottant m, g: flottant m/s²) -> t: flottant s
  au centre         : faux (réparée à cette lecture)
  ce qu'elle touche : rien elle-même ; le monde par ses appels
  ses racines       : appelée par impact, principal ; à 2 pas de la tête
  ses branches      : appelle __afficher_t
  ses promesses     : exige 2, garantit 1, 1 exemple vérifié
  sa mémoire        : inchangée depuis 2 rangements (l'empreinte de son texte)
```

**Dans Ogmios.** Après F5 sur Lugus (qui range l'ADN avec sa carte), la fenêtre des explications montre les six faces et
le centre : pour une fonction, en cliquant sa case sur la carte du programme ; pour une réaction, sur son onglet.
L'ADN est relu quand il change (sa date), et vérifié pour le centre. Si le texte a été retouché depuis le dernier F5,
l'explication le dit. `vtx paillasse PROG.vtx --faces PROG.adn --gestes F` (gestes `choisir NOM`, `explique`) fait la
même chose sans écran.

**Le registre tridimensionnel** (la question du créateur) : au sens d'un registre où l'on inscrit, oui : chaque
molécule a sa place (une couleur #RRGGBB, trois coordonnées), et à cette place six faces et un centre ; on y lit par la
place et la face. Au sens d'un registre du processeur, pas encore : il le deviendra quand la machine lira ces faces
pendant qu'elle tourne (la patrouille, les souvenirs). Le rangement des faces dans le cube est l'étape suivante.

**Vérifié** (`tests/test_carte_arn.py`, 32 contrôles) : la carte à six faces est celle de la référence, octet pour
octet, sur six programmes, au premier rangement et au second (avec le rangement d'avant) ; l'ARNc la porte ; chaque
face ; l'histoire (changée, inchangée depuis 1 puis 2 rangements, nouvelle) ; la carte vraie malgré l'histoire ; le centre
d'une molécule abîmée (réparée) ; la paillasse d'Ogmios (une fonction, une réaction, le texte retouché depuis) ; une carte
à quatre faces (inconnue). Les deux compilateurs donnent les mêmes mots du lecteur (14 328).

## 53. Les promesses : la carte constate, la promesse engage (15 novembre, 0.6r)

**Décidé avec le créateur**, après un avis demandé sur la nature du langage (une avancée : les quatre valeurs natives et
un programme qui se décrit et se prouve lui-même ; un risque : l'accumulation des couches et du vocabulaire, et un cœur
du langage en retard sur ce qui l'entoure) : suivre la piste, faire des faces des promesses vérifiées, et graver le
fonctionnement de vtx (le carnet, `docs/vtx-carnet.md`, section 1 bis).

**La promesse.** Après la dernière parenthèse de l'en-tête (et le type du résultat) :

```
fonction somme(n) touche rien { … }               // ni la mémoire, ni le monde
fonction lire_case(t, i): entier touche lecture { … }
fonction remplir(t, n) touche memoire { … }        // la mémoire, pas le monde
reaction moyenne(a, b) -> m touche rien { … }
fonction principal() touche monde { … }            // le dire
```

- C'est ce que la fonction touche au plus, **elle et ses appels**. Les deux compilateurs l'acceptent sans changer un mot
  du code ; une seule différence : une fonction qui promet **n'est plus recopiée en ligne** (elle garde sa molécule),
  sinon sa promesse ne pourrait pas se vérifier à part. Les programmes sans promesse donnent exactement les mêmes mots
  qu'avant.
- **Le juge est le lecteur d'ADN écrit en vtx** : il fait la carte (ce que les mots touchent vraiment), lit la promesse
  dans l'en-tête, et dit ce qui la rompt, d'appel en appel :

  ```
  promesse rompue : double (ligne 10) promet de ne rien toucher, mais elle touche le monde : par parler → afficher
  promesse rompue : remplir (ligne 14) promet de ne rien toucher, mais elle écrit la mémoire : elle-même
  ```

- **Une promesse rompue arrête la compilation** (toute compilation ordinaire de Lugus : `lugus PROG.vtx`, `lugus
  compiler`, F5 dans Ogmios, l'exécutable) **et le rangement** (aucun ADN, aucun ARNc n'est écrit). Le juge ne tourne
  que si le texte porte une promesse : les autres programmes ne paient rien.
- La face « ses promesses » de la carte la montre : « ne rien toucher (tenue) » ; dans `lugus carte` et dans Ogmios.
- `chimie/adn.py` (promesses) dit exactement les mêmes mots que le lecteur en vtx.

**Limites, dites.** La promesse est jugée sur les mots ordinaires (pas en pas à pas ni avec la provenance, qui ajoutent
des écritures). Ce qu'une fonction touche est lu dans ses instructions, pas suivi à l'exécution : c'est une borne sûre
(le doute compte du côté prudent), pas une mesure fine. vtx128.py accepte la promesse mais ne la juge pas lui-même :
Lugus, Ogmios et la référence `chimie/adn.py` la jugent.

**Vérifié** (`tests/test_promesses.py`, 15 contrôles) : les promesses tenues (les mêmes mots par les deux compilateurs, le
programme tourne) ; une fonction qui promet garde sa molécule ; trois promesses rompues (la compilation, le rangement et
l'ARNc refusés ; les mêmes messages que la référence ; le chemin, elle-même ou d'appel en appel) ; la carte et la
paillasse montrent la promesse tenue ; `touche partout` refusé par les deux compilateurs. vtxc128 renouvelé (point
fixe) ; les suites des compilateurs, de l'ADN, de la carte, du chemin, de la patrouille, de la provenance et de la
paillasse restent conformes.

## 54. Supposons : essayer, écarter, noter, retenir (15 novembre, 0.6s)

Le doute devient une instruction. Un humain qui cherche dit « supposons que ce soit celui-ci… non, il ne tient pas ;
celui-là, il vaut 8 ; je retiens le meilleur » : c'est une écriture faite pour explorer plusieurs raisonnements et garder
le résultat, avec **la façon dont il a été obtenu**.

```
supposons x parmi [3, 8, 5, 12] {
    @3[100] = x;                   // défait après chaque lecture
    si x > 10 { ecarter; }
    noter x;
} retenir r;                       // x = 8, r = vrai, @3[100] inchangé
```

- **Chaque candidat est calculé une fois**, puis lu à tour de rôle dans `x`. La lecture peut **écarter** le candidat
  (`ecarter;` ou `écarter;`) ou le **noter** (`noter E;`, un entier, comparé signé ; la plus grande note gagne).
- **Ce que la lecture écrit en mémoire est défait** après elle : elle est jouée dans une hypothèse (§ hypothèse), mais
  seulement si elle écrit. Une lecture qui ne fait que lire ne coûte pas de journal, et une fonction `touche rien` peut
  supposer : sa promesse tient (vérifié par le juge de la carte).
- **Le verdict est un logique de Belnap**, et c'est là le cœur : `retenir r` dit **faux** si aucun ne survit, **vrai** si
  un seul survit ou si une note est seule en tête, **inconnu** si plusieurs survivent sans que rien ne les départage (le
  manque d'information), **variable** si plusieurs sont ex aequo (l'excès : deux réponses aussi bonnes). Le choix lui-même
  est toujours défini (le premier candidat, le premier survivant ou le premier des meilleurs), mais le programme sait
  **s'il peut s'y fier** : `selon r { vrai { … } inconnu { … } variable { … } faux { … } }`.
- **Rendu en instructions ordinaires** par les deux compilateurs, exactement les mêmes : des variables cachées
  `__supN_…` (les candidats, le meilleur, la meilleure note, les ex aequo, les survivants), une boucle sur les candidats,
  une chaîne de `si` pour poser `x`, la lecture dans une boucle à un tour (écarter = noter l'écart, puis `arrêter`), et
  l'hypothèse si la lecture écrit. Aucune instruction nouvelle de la machine : Lugus et sa traduction x86-64 n'ont rien
  à apprendre.
- `supposons`, `parmi`, `ecarter`, `noter`, `retenir` ne sont pas réservés : ils ne comptent qu'à leur place (une
  fonction utilisateur peut s'appeler `noter`, hors d'une lecture).

**Limites, dites.** Les lectures sont jouées l'une après l'autre, pas en parallèle (les cylindres le pourraient : piste
ouverte, car une lecture qui n'écrit pas est indépendante des autres). Comme l'hypothèse, les variables locales et les
écritures faites par les fonctions appelées ne sont pas défaites ; ce qui est affiché reste affiché. La note est un
entier (pas un flottant). `retour`, `arrêter` et `continuer` ne sortent pas d'une lecture ; `ecarter` dans une boucle de
la lecture ne sort que de cette boucle (le candidat est quand même écarté). Au plus 64 candidats. Seulement sur Lugus
(vtx128.py et vtxc128) ; Dunon et Senos ne l'ont pas.

**Vérifié** (`tests/test_supposons.py`, 10 contrôles) : l'exemple `exemples128/supposons.vtx` et un mélange (textes,
flottants, boucles, supposons dans supposons, hypothèse dans la lecture, 12 candidats, une fonction nommée `noter`)
donnent les mêmes mots par les deux compilateurs et affichent ce qu'ils doivent ; les quatre verdicts ; la mémoire
défaite ; une fonction `touche rien` qui suppose tient sa promesse ; cinq refus, les mêmes des deux côtés. vtxc128
renouvelé (point fixe 184 211 mots).

## 55. Le contrat écarte, la carte parle comme le texte (15 novembre, 0.6t)

**Le contrat d'une lecture.** Dans une lecture de `supposons`, `exige CONDITION;` dit ce qu'un candidat doit tenir ;
s'il ne le tient pas, il est écarté, sans écrire `ecarter` : « ça ne peut pas être lui, il ne remplit pas la
condition ».

```
supposons n parmi [12, 7, 9, 15, 4] {
    exige n % 3 == 0;
    exige n > 5 && n < 14;
    noter n;
} retenir r;                       // n = 12, r = vrai (9 tient aussi, moins bien noté)
```

- Rendu par les deux compilateurs en `si CONDITION { } sinon { écarter }` : les mêmes mots. La condition suit les règles
  de `si` (un logique n'y sert pas : `selon`, ou `== vrai`).
- Hors d'une lecture, `exige` reste ce qu'il était : un contrat de réaction, ou un nom ordinaire dans une fonction
  (`soit exige = 3;`). Dans une lecture, `exige = …` reste une affectation.
- **La carte ne le compte pas comme une promesse de la fonction** : il parle d'un candidat, pas de ce que la fonction
  promet. Les contrats comptés dans la face « ses promesses » sont ceux des réactions (`chimie/adn.py` et le lecteur en
  vtx, les mêmes octets).

**La carte parle comme le texte.** Les molécules du journal des hypothèses (`__hyp_debut`, `__hyp_noter`,
`__hyp_annuler`, `__hyp_valider`) sont les rouages de `supposons` et `hypothèse`, pas ce que le programmeur a écrit :
la face « ses branches » ne les nomme plus, elle dit « suppose (supposons ou hypothèse : le journal qui défait les
écritures) », dans `lugus carte` comme dans Ogmios. La carte rangée ne change pas (les rouages y restent, avec ce qu'ils
touchent) : seul ce qu'on en lit change. `lugus carte --tout` les montre toujours.

**Ce qui n'est pas fait, dit.** L'écriture défaite par une supposition compte toujours dans « ce qu'elle touche » (le
journal écrit la mémoire) : une fonction `touche rien` qui suppose en écrivant reste refusée. Ne pas la compter demande
que le juge reconnaisse le journal ; c'est une décision de fond, laissée au créateur.

**Vérifié** (`tests/test_supposons.py`, 15 contrôles) : `exige` donne les mêmes mots, écarte ce qu'il doit, rend faux
quand aucun candidat ne le tient, reste un nom hors d'une lecture ; la carte et Ogmios disent « suppose » sans les
rouages, et ne comptent pas l'exige d'une lecture parmi les promesses. vtxc128 renouvelé (point fixe 184 270 mots) ; le
lecteur d'ADN, les mêmes 15 475 mots par les deux compilateurs.

## 56. Retenir, alors : l'action du choix (16 novembre, 0.6u)

**La question.** Après une supposition, faut-il garder ce que la lecture retenue a construit ? Le créateur : la valeur la
plus humaine. Un humain réfléchit à chaque possibilité, en choisit une, puis la fait ; il n'agit pas sur un doute.

```
supposons c parmi [3, 8, 5] {
    @3[101] = c;                 // la lecture : défaite
    exige c < 10;
    noter c;
} retenir rc alors {
    @3[101] = c * 10;            // l'action : gardée (80)
} sinon {
    afficher("pas de choix sûr :", rc);
}
```

- **Les lectures jugent, l'action est écrite à part.** Ce que les lectures écrivent est toujours défait (la règle reste
  simple) ; le bloc `alors` se joue une seule fois, pour le candidat retenu, et **seulement si le verdict est vrai**.
  Avec inconnu (rien ne départage), variable (des ex aequo) ou faux (aucun), c'est `sinon` qui se joue, s'il est écrit.
  Pour agir malgré des ex aequo sous condition, on l'écrit : `selon rc { variable { si … { … } } }`.
- Rien n'est rejoué : ce qui s'affiche dans une lecture ne s'affiche qu'une fois.
- `alors` va aussi sans `retenir` (`} alors { … }`). Ce n'est pas un mot réservé : il ne compte qu'après le bloc d'une
  supposition, suivi d'une accolade (`soit alors = 2;` marche toujours).
- Les mêmes mots par vtx128.py et vtxc128 : une variable cachée de plus (`__supN_ok`), posée dans les deux branches où le
  verdict est vrai, puis un `si`. Aucune instruction nouvelle : le .exe traduit en profite.

**Les cylindres, mis de côté pour la supposition** (le créateur ne s'en sert pas : ils ne vivent que dans la forge, et
la traduction en x86-64 de ses .exe n'en a pas). L'idée, gardée pour plus tard : le cube propre d'un cylindre (copié à
l'écriture) **est** une hypothèse ; une lecture jouée sur son cylindre n'aurait plus besoin du journal, son cube serait
jeté au lieu d'être fondu, chaque lecture ne rendrait que son verdict (écartée, notée, sa note) dans une case à elle, le
choix serait fait dans l'ordre des candidats (le même résultat que Lugus) ; autant de cylindres que de candidats, et un
seuil pour laisser les petites lectures en ordinaire. Pour que les .exe en profitent, il faudrait des fils dans la
traduction en x86-64.

**Vérifié** (`tests/test_supposons.py`, 17 contrôles ; `tests/supposons_alors.vtx`) : les mêmes mots ; `alors` joué une
fois pour le retenu, la lecture défaite et l'action gardée ; `sinon` pour des ex aequo ; sans `retenir` ; « alors » reste
un nom ailleurs. vtxc128 renouvelé (point fixe 184 404 mots).

## 57. Gobannos, le forgeron : vtx écrit ses exécutables lui-même (16 novembre, 0.6v)

**La décision du créateur :** Vercintorix doit être autonome à 100 %, sans Rust ni Python ; dans l'ordre : Gobannos
(le traducteur écrit en vtx), puis la traduction complète, puis les cylindres dedans ; et penser à finir le langage.

**Ce qui existait, et n'était pas en vtx.** La forge (vtx → texte Rust → rustc : il faut Rust), `natif/` (Senos → .exe,
écrit en Python), la traduction de Lugus en x86-64 au lancement des .exe (`natif128.rs`, en Rust). Gobannos n'était que
sur le papier.

**Gobannos, premier temps** (`gobannos/gobannos.vtx`, environ 2 400 lignes de vtx, joué par Lugus) :

```
lugus compiler PROG.vtx PROG.mots
lugus gobannos/gobannos.vtx            (trois lignes : PROG.mots, PROG.exe, windows | linux)
```

- **Il lit les mots** de Lugus (des nombres de 128 bits, lus en `entier_128`), **trouve le code** (de la demi-instruction
  0, en suivant les sauts, les appels et la suite : les textes et les données rangés après le code ne sont jamais pris
  pour des instructions), **traduit chaque demi-instruction en x86-64** (un assembleur écrit en vtx : les formes dont il
  a besoin, toujours de la même taille, les sauts toujours longs), et **écrit l'exécutable** octet par octet par le canal
  `octets:` : un ELF64 pour Linux (un segment), un PE32+ pour Windows (une section, KERNEL32 seul : GetStdHandle,
  WriteFile, ReadFile, VirtualAlloc, ExitProcess, SetConsoleOutputCP, SetConsoleCP ; la même disposition que `natif.py`,
  que Windows accepte déjà).
- **Le code produit :** rbx porte l'état (les seize registres de Lugus, 16 octets chacun, les drapeaux z et c, le compte
  des instructions, les tampons) ; la mémoire de Lugus en pages de 65 536 mots et leurs brins, prises au système au
  premier besoin, une table de 65 536 pages par étage (les indices jusqu'à 2^32) ; les mots du programme posés dans
  l'étage 0 et marqués ADN au départ ; RET par une table des retours (la place traduite de chaque demi-instruction).
- **Traduit :** toutes les opérations entières à 64 bits (avec la division par zéro et la division signée par −1 de
  Lugus), sur tout le mot l'addition, la soustraction, la comparaison, le produit, les décalages, ET, OU, OU exclusif, le
  complément ; les constantes ; les lectures et écritures de la mémoire, du cadre et de la pile ; les sauts, CALL, RET ;
  le quaternaire (ET4, OU4, NON4, ANTI, QEGAL, ADDM4, EXQ, LDQ, STQ) ; la console en UTF-8 (écrire, lire au clavier, les
  \r sautés), `sortie()` ; les brins (MARQUE, BRIN, l'écriture dans un mot ADN refusée) ; les services 25
  (`instructions()` : **le même compte que Lugus**, chaque demi-instruction comptée) et 26 (effacer) ; HALT.
- **Pas encore :** les flottants quaternaires, les fichiers, l'entrée de nombres (`entrée()`), les autres services, le
  point de matière, les voies. Une instruction qui n'est pas traduite **arrête l'exécutable en le disant** au moment où
  elle est atteinte (« Gobannos : cette instruction de Lugus n'est pas encore traduite… (son code : #48, largeur 0)
  (demi-instruction 22) », code 3) : rien n'est jamais fait de travers en silence.

**Vérifié** (`tests/test_gobannos.py`, 16 contrôles) : douze exemples de Lugus (alternance, banc_traduction, codon,
combat, conseil, cylindres, duel, gene, panel, quatre_verites, releves, supposons) donnent **la même sortie que Lugus,
au caractère près**, et le même compte d'instructions là où ils l'écrivent (duel, codon) ; un programme fait pour les
bords (la division par zéro, `./` par −1, les décalages de 63, les entiers de 128 bits, les tableaux de quits et de
logiques, la récursion d'Ackermann, les textes) ; le clavier (des accents, une réponse à quatre valeurs, un nombre, la fin
de l'entrée) ; un flottant (l'arrêt dit) ; l'exécutable Windows (PE32+, KERNEL32). Les deux compilateurs de Lugus donnent
les mêmes mots pour Gobannos lui-même (7 898 mots).

**La vitesse** (le banc : un crible, fib(27), trois millions de brassages ; machine de travail) : Lugus seul 2,0 s,
**Gobannos 0,52 s** (4 fois plus vite), la traduction en Rust 0,26 s (elle garde les registres de Lugus dans ceux du
processeur et les pages ouvertes : Gobannos les relit en mémoire à chaque instruction ; c'est la suite).

**Ce que cela change pour l'autonomie.** Le chemin vtx → .exe ne passe plus ni par Rust ni par Python : vtxc128 (en vtx)
compile, Gobannos (en vtx) traduit et écrit l'exécutable. Ce qui reste en Rust : la machine Lugus elle-même, qui joue
Gobannos et vtxc128 (pour s'en passer, il faudra que Gobannos se traduise lui-même : un Gobannos.exe, puis un vtxc128.exe,
et le point fixe des exécutables), et la traduction actuelle des .exe (`natif128.rs`), que Gobannos remplacera.

**Les étapes suivantes**, dans l'ordre : (2) les flottants quaternaires, les fichiers et les services, les registres
gardés dans le processeur, pour égaler puis remplacer la traduction en Rust ; Gobannos traduit lui-même (le point fixe des
exécutables) ; (3) les cylindres dans Gobannos (un fil par cylindre, son cube copié à l'écriture, la fusion en Belnap ;
pour `supposons`, le cube jeté) ; et, à côté, finir le langage (les fonctions passées en valeur, les modules désignés par
leur empreinte).

## 58. Finir le langage, premier pas : les fonctions passées en valeur (16 novembre, 0.6w)

**Décidé avec le créateur :** le langage en priorité, Gobannos à côté. Le premier manque du cœur du langage : une
fonction ne pouvait pas se passer à une autre. C'est ce qui permet d'écrire `pour_chacun(t, carre)`, `plier(t, plus, 0)`,
une table d'outils, un choix de méthode (et demain `supposons f parmi [methode_a, methode_b]`).

```
fonction plier(t, f, depart) {
    soit acc = depart;
    pour v dans t { acc = f(acc, v); }
    retour acc;
}
afficher(plier([1, 2, 3, 4, 5], plus, 0), plier([1, 2, 3, 4, 5], fois, 1));     // 15 120
```

- **L'écriture** : un nom de fonction sans parenthèses est sa valeur (si aucune variable ne porte ce nom) ; `f(…)` par
  une variable qui n'est pas le nom d'une fonction est un appel par valeur. Les programmes déjà écrits donnent les mêmes
  mots qu'avant (rien de ce qui compilait ne change de sens : un nom inconnu était une erreur).
- **La machine n'apprend rien.** Lugus n'a pas d'appel indirect ; il n'en faut pas : les arguments sont empilés comme
  pour un appel ordinaire, la cible va dans R1, puis `CALL __appeler`, et `__appeler` fait `PUSH R1 ; RET` : le RET saute
  à la cible, l'adresse de retour de l'appelant restant en place. La cible voit exactement la pile d'un appel ordinaire.
  Un mot de plus par appel ; la traduction en x86-64 et Gobannos le jouent comme le reste.
- **Derrière le trampoline, une table jamais jouée** : un `CALL` vers chaque fonction passée en valeur. Sans elle, une
  fonction jamais appelée directement n'avait pas de molécule dans l'ADN (le découpage suit les cibles des CALL) : la
  carte la fondait dans sa voisine. Avec elle, chaque fonction a sa molécule, « appelée par __appeler », et Gobannos la
  traduit (il parcourt la table derrière un PUSH-RET).
- **La promesse reste honnête.** Le lecteur d'ADN (et la référence Python) lit un PUSH suivi d'un RET comme un saut
  calculé : le monde. Une fonction `touche rien` qui appelle par valeur est refusée : « promesse rompue : appliquer
  (ligne 2) promet de ne rien toucher, mais elle touche le monde : par __appeler ».
- **Les analyses** : un appel par valeur est impur (pas de souvenir), et il touche tout pour la partition (rien n'est
  réordonné autour de lui) ; une fonction passée en valeur n'est jamais recopiée en ligne.

**Trouvé en route, corrigé :** sur une fonction écrite sur une seule ligne (`fonction f(x) touche rien { … f(x) … }`), la
promesse était cherchée après la dernière parenthèse de toute la ligne, celle du corps : le juge ne la voyait pas, et
une promesse rompue passait. L'en-tête s'arrête maintenant à la première accolade (le lecteur en vtx, la référence
Python, et le test de Lugus qui décide s'il y a des promesses à juger).

**Limites, dites.** Le nombre d'arguments d'un appel par valeur n'est pas vérifié (à la compilation, on ne sait pas
quelle fonction est portée) : un mauvais nombre défait la pile. Le résultat est un entier (une déclaration le convertit).
Une variable qui porte le nom d'une fonction ne s'appelle pas (le nom de la fonction l'emporte). Pas encore de type
« fonction(entier): entier » qui vérifierait tout cela : c'est la suite naturelle, avec les modules par empreinte.

**Vérifié** (`tests/test_valeurs.py`, 9 contrôles) : l'exemple `exemples128/valeurs.vtx` et un mélange (une fonction qui
rend une fonction, la récursion par valeur, une fonction du prélude passée, une structure qui porte une fonction, une
boucle en segments à côté) : les mêmes mots par les deux compilateurs, la sortie attendue ; la promesse refusée ; la
promesse d'une fonction en une ligne ; la carte ; Gobannos (la même sortie que Lugus). vtxc128 renouvelé (point fixe
184 695 mots) ; le lecteur d'ADN, les mêmes 15 486 mots par les deux compilateurs.

## 59. Le type d'une fonction : `fonction(entier): entier` (16 novembre, 0.6x)

**La suite annoncée en 0.6w.** Une fonction passée en valeur n'était qu'un entier : le compilateur ne savait ni combien
d'arguments lui donner, ni ce qu'elle rendait. Trois défauts en sortaient : un mauvais nombre d'arguments défaisait la
pile sans un mot ; un flottant passé à une fonction de flottants arrivait comme un entier ; un texte rendu s'affichait
comme un nombre. Le type écrit les règle tous les trois, à la compilation, sans un mot de plus à l'exécution.

```
fonction plier(t, f: fonction(entier, entier): entier, depart) { … }
fonction choisir(k): fonction(entier): entier { retour carre; }
soit g: fonction(flottant): flottant = moitie;     afficher(g(3));         // 1.5 : 3 est converti
soit c: fonction(texte): texte = crier;            afficher(c("Ho"));      // un texte, affiché comme tel
```

- **Vérifié où l'on peut l'être** : une fonction nommée là où l'on attend un type doit l'avoir (paramètres et résultat,
  les textes et les tableaux comptant comme des entiers pour la machine) ; un appel par une variable typée compte ses
  arguments et convertit chacun. Les deux compilateurs refusent avec les mêmes mots.
- **Une porte laissée ouverte, exprès** : un entier se range dans une variable typée fonction. C'est par là qu'une table
  de fonctions lue dans un tableau garde son type ; c'est aussi une promesse que le compilateur ne peut pas vérifier.
  Deux types de fonction différents, eux, ne se mélangent jamais.
- **Sans type écrit, rien ne change** : les programmes de 0.6w donnent les mêmes mots.
- **Dans vtxc128**, un type de fonction est un numéro (2 000 000 + sa place dans une table des signatures, les mêmes
  types écrits ayant le même numéro) ; dans vtx128.py, une chaîne `g:e,e>e`. La passe des textes suit les variables
  typées fonction pour savoir qu'un appel rend un texte.

**Limites, dites.** Pas de type de fonction dans un type de fonction (un message clair le dit). Le type ne porte pas ce
que la fonction touche : `fonction appliquer(f: fonction(entier): entier, x) touche rien` reste refusée (« elle touche le
monde : par __appeler »). La suite naturelle serait `fonction(entier): entier touche rien`, qui laisserait le juge croire
la promesse du type et vérifier chaque fonction qu'on y range ; puis les modules désignés par leur empreinte.

**Vérifié** (`tests/test_types_fonction.py`, 7 contrôles) : un programme qui mêle appliquer, plier, un flottant, une
fonction rendue, un texte et une structure, les mêmes mots par les deux compilateurs et la sortie attendue ; quatre refus,
le même message des deux côtés ; un appel sans type, inchangé. vtxc128 renouvelé (point fixe 185 590 mots).

## 60. La promesse dans le type, et les flottants dans Gobannos (16 novembre, 0.6y)

**La promesse dans le type.** `fonction(entier): entier touche rien` : le type d'une fonction passée en valeur dit aussi
ce qu'elle touche au plus. La 0.6x laissait une fonction `touche rien` incapable d'appeler une valeur (le juge comptait
l'appel pour le monde) ; c'est réglé, sans croire personne sur parole :
- **le compilateur garde l'entrée** : seule une fonction qui tient au moins la promesse du type y entre (sa propre
  promesse, jugée à part), ou une valeur d'un type qui promet autant ; un entier n'y entre pas. Les mêmes refus, mot pour
  mot, par les deux compilateurs (quatre messages, dans `tests/test_types_fonction.py`) ;
- **les mots portent la promesse** : chaque niveau a son trampoline, `__appeler_rien` (ou `_lecture`, `_memoire`), qui
  commence par `LDIS R15,#k`, puis `PUSH R1 ; RET` comme `__appeler`. Le juge (le lecteur d'ADN en vtx, et la référence
  Python) lit ce `k` juste avant le PUSH et compte l'appel pour ce niveau au lieu du monde. Rien n'est ajouté à la
  machine ; la carte nomme le trampoline (« par __appeler_lecture ») ;
- **le juge reste exact** : une fonction `touche rien` qui appelle une valeur promise `touche lecture` est refusée, « elle
  lit la mémoire : par __appeler_lecture ».

*Trouvé en route.* La découpe en molécules suit les cibles des CALL. Quand rien n'appelait `__appeler` lui-même (des appels
promis seulement, ou des fonctions passées sans aucun appel par valeur), `__appeler` et sa table se fondaient dans la
molécule voisine, qui passait pour toucher le monde. La table l'appelle alors lui-même (un mot de plus, seulement dans ce
cas) : chacun a sa molécule. Les programmes de 0.6w et 0.6x qui appellent par valeur gardent leurs mots.

**Les flottants dans Gobannos.** Ils étaient l'arrêt le plus fréquent (« cette instruction n'est pas encore traduite,
#48 »). Plutôt que d'écrire à la main l'arithmétique quaternaire en x86-64, elle est écrite en vtx :
- **`gobannos/flottants.vtx`**, environ 700 lignes, des entiers seulement : l'addition, la soustraction, le produit, le
  quotient, la racine, les comparaisons, l'opposé, l'état, les conversions depuis et vers les entiers (tronquées,
  arrondies, saturées) et d'un format à l'autre, aux trois largeurs (128, 64, 32 bits). Chaque opération donne le
  résultat exact arrondi une seule fois, par le même arrondi que la machine (`qflot128.rs`) : les mêmes bits. Le produit
  de deux mantisses de 112 bits se fait en morceaux de 56 bits ; le quotient, une division longue par morceaux de 14 bits
  dont chaque chiffre est estimé par la division de 64 bits ; la racine, chiffre par chiffre ;
- **Gobannos la traduit avec le programme** (4e ligne d'entrée : ses mots) : ses mots suivent ceux du programme, ses sauts
  relogés ; chaque instruction flottante devient un appel : les registres, z, c et le compte gardés, l'opération et ses
  deux valeurs empilées comme pour un appel ordinaire de Lugus, une place de retour à elle ; au retour tout est rendu, D
  reçoit le résultat. Le programme traduit garde **le même compte d'instructions que Lugus**. Sans la bibliothèque,
  l'instruction flottante arrête l'exécutable en le disant, comme avant.

**Vérifié** (`tests/test_gobannos_flottants.py`) : la bibliothèque, jouée par Lugus, contre la machine sur 6 000 calculs
tirés au hasard (cas limites, milieux d'arrondi, sous-normaux, infinis, inconnu et variable, les trois largeurs) : 0 écart
(et 60 000 de plus pendant la mise au point) ; un programme qui joue chaque instruction flottante aux trois largeurs et les
mathématiques du prélude (sinus, exponentielle, logarithme), et quatre exemples (types_fonction, freinage,
scene_incrementale, chute) : la sortie de Lugus, le même compte d'instructions. Les deux compilateurs donnent les mêmes
mots pour la bibliothèque (2 771) et pour Gobannos.

**La vitesse, dite sans fard.** Une instruction flottante de Lugus devient de 750 (comparaison) à 3 000 (quotient) et
6 300 (racine) instructions de la bibliothèque. Un calcul plein de flottants va donc **plus lentement traduit que joué par
Lugus** : 600 000 opérations, 3,1 s contre 0,8 s (le quotient seul, 9,8 µs par opération). Les programmes surtout entiers
gagnent toujours à la traduction. `mandel_reaction` (63 millions d'opérations flottantes) prend plusieurs minutes. Ce qui
le rattrapera : garder les registres de Lugus dans ceux du processeur (l'étape 2 de Gobannos, qui accélère aussi la
bibliothèque), puis une racine par Newton. Les flottants de l'IEEE (`vers_ieee128`, `de_ieee128`) et les voies de
flottants restent au piège.

## 61. Gobannos plus vite, la porte vers le processeur quaternaire, et la frontière du binaire (16 novembre, 0.6z)

**Mesurer d'abord** (Valgrind sur l'exécutable du banc, en instructions du processeur) : 55 % dans le code traduit des
instructions, 29 % dans la recherche de la page à chaque accès mémoire, 12 % dans les routines de lecture et
d'écriture. Trois changements, chacun mesuré (le banc : un crible, fib(27), trois millions de brassages ; le meilleur de
neuf lancements, sur une machine de travail bruitée) :

| | temps |
|---|---|
| avant (0.6y) | ~250 ms |
| + le compte des instructions dans un registre du processeur (R15) et les quatre registres de Lugus les plus employés dans RBP, R12, R13, R14 | ~185 ms |
| + un cache de huit pages, essayé sans appel dans les routines de lecture et d'écriture | ~150 ms |
| + les drapeaux morts : z et c ne sont plus écrits quand l'instruction suivante les repose sans les lire (la règle de la traduction en Rust) | **135 ms** |
| la traduction en Rust (`vtx exe128`), pour comparer | 127 ms |
| Lugus seul | 1 419 ms |

Sur les entiers, l'exécutable écrit par Gobannos (en vtx) va aussi vite que celui de la traduction en Rust. Sur les
flottants, deux fois plus vite qu'en 0.6y (600 000 opérations : 3,1 s → 1,43 s), mais toujours deux fois plus lent que
Lugus seul (0,67 s) et seize fois plus que la traduction en Rust (0,09 s), qui appelle l'arithmétique de Rust : chaque
opération reste un appel de 750 à 6 300 instructions de la bibliothèque écrite en vtx. Même texte, même compte
d'instructions que Lugus, partout.

*Trouvé en route* : la routine qui empile un argument pour la bibliothèque écrivait encore R14 en mémoire ; avec R14
gardé dans le processeur, la pile se décalait et un retour partait au mauvais endroit (« un retour vers une place qui
n'est pas du code traduit »). Le test des flottants l'a vu ; corrigé.

*Trouvé aussi, par les programmes tirés au hasard de la vérification complète* (un désaccord ancien, déjà là en 0.6x) :
vtxc128 recopiait en ligne `t3(q[28], 5)` (q, un tableau de quits rangé) alors que vtx128.py gardait l'appel. Sur Lugus,
vtx128.py change la lecture d'un tableau rangé (64 quits par mot) en un calcul à toute la largeur, qu'il ne déplace
jamais ; vtxc128 suivait encore la règle de Dunon, qui la disait pure. vtxc128 suit maintenant la référence : 360
compilations tirées au hasard sur quatre graines, mêmes mots.

**La porte vers le processeur quaternaire optique.** Le processeur reste celui du PC (le x86-64). Ce qui ne dépend pas de
lui est mis à part, pour qu'une autre cible n'ait qu'à donner les siennes :
- **ce qui reste à chaque cible** : `cible_places()` (les registres qu'elle prête : pour le x86-64, RBP, R12, R13, R14),
  ses façons d'écrire une instruction, son en-tête d'exécutable et son socle (les appels au système) ;
- **ce qui sert à toutes** : la lecture des mots, le parcours du code atteint, le choix des registres de Lugus les plus
  employés (`choisir_registres`), les drapeaux morts, la bibliothèque des flottants (écrite en vtx : elle se traduit
  comme le reste), le cache des pages ;
- et surtout **les mots de Lugus** eux-mêmes : c'est déjà un jeu d'instructions quaternaire (des quits, des étages en
  quit, les quatre valeurs en instructions). Sur une machine quaternaire, une bonne part n'aurait rien à traduire.
  Honnêtement : une cible quaternaire demandera son propre écrivain d'instructions ; la porte est la séparation, pas
  l'écrivain.

**La frontière du binaire** (`vers_ieee128`, `de_ieee128`, `vers_ieee64`…) : traduite par la bibliothèque, au bit près de
la machine (et vérifiée aussi sur des bits binaires quelconques : tous les NaN, les sous-normaux). Ce que le binaire
garde : le signe (un bit, 0 ou 1) et la grandeur, exacte du flottant de 128 bits au binary128 (113 bits). Ce qu'il ne
sait pas porter : inconnu et variable deviennent tous deux le NaN, qui revient **variable**. Un aller et retour perd
donc « inconnu ». Proposition, à décider : marquer inconnu par la charge du NaN (un NaN tranquille de charge 1,
toujours un NaN valide pour le binaire), pour qu'il revienne inconnu ; un changement de la machine, des deux
compilateurs et de la bibliothèque.

## 62. Le vocabulaire des nombres (17 novembre, 0.6za)

**Décision du créateur sur la frontière du binaire** : « laissons le binaire dans son monde » ; la traduction IEEE ne
sert qu'aux tests et aux programmes d'à côté, de façon temporaire si tout passe en quaternaire. Pas de charge de NaN :
les conversions restent telles quelles (inconnu revient variable après un aller et retour, et c'est dit).

**Le vocabulaire** (demandé : « un module complet de math. entier flottant réel, negatif, positif, decimale… ») :
treize mots, un pour tous les types — `signe`, `est_positif`, `est_negatif`, `est_nul`, `est_entier`, `est_infini`,
`est_su`, `partie_entiere`, `partie_decimale`, `entre`, `ecart`, `borne`, `arrondi(x, n)`. Comment : comme `afficher`
choisit `__afficher_x`, un mot du prélude devient `__mot_x`, `_f`, `_s`, `_w` ou `_i` selon le type le plus large de
ses arguments (`_i` seulement si tous sont des `entier_32`) ; le type rendu est celui de la variante. Les variantes
sont écrites en vtx dans le prélude et ne sont tirées que si le programme emploie le mot (rien ne change pour les
autres programmes : les mots de 35 exemples, de Gobannos, de la bibliothèque des flottants et de Belenos sont
identiques avant et après). Les deux compilateurs donnent les mêmes mots (`tests/test_nombres.py`).

**Le doute gardé** : sur un flottant inconnu, `est_positif` rend inconnu ; sur un variable, variable ; `est_su` dit
lequel. C'est la logique de Belnap appliquée aux nombres : une question sur une valeur qu'on ne connaît pas n'a pas de
réponse inventée.

**Vérifié par propriétés** (`tests/nombres/proprietes.vtx`) : 161 valeurs de −10 à 10 par huitièmes, les cinq types :
partie entière + partie décimale = x, signe × |x| = x, est_entier ⇔ partie décimale nulle, entre, ecart, borne,
arrondi à moins d'un demi. Zéro faute.

**Ce qui n'y est pas, honnêtement** : `reste` sur les flottants (un reste exact demande une division longue, pas faite) ;
`tronquer` (c'est `partie_entiere`) ; les cubes et les faces ne sont pas des nombres et restent dans leur bibliothèque
(`bibliotheque/cube.vtx`) ; et **Dunon** n'a pas encore ce vocabulaire (vtx64.py et vtxc64 : le même travail à refaire).


## 63. Le vocabulaire étendu, sur Lugus et sur Dunon (17 novembre, 0.61)

**La demande du créateur** : passer à la 0.61, enrichir le vocabulaire « en utilisant l'ensemble du vocabulaire de
Rust, celui d'Arduino, et celui des extensions » (précisé : les extensions officielles, et celles d'UE5 et de Blender ;
« pas recréer les extensions, mais un vocabulaire préparé et capable d'adapter les extensions à Vercintorix ») ; des
noms français, l'équivalent d'origine en note ; tout réparti en familles, sur Dunon et Lugus.

**Un seul texte pour les deux machines** (`vtxc/vocabulaire.py`). Les mots sont écrits une fois, pour Lugus ; l'outil
en tire le prélude de Dunon (le flottant principal y est de 64 bits, les mathématiques s'appellent `sinus_64`…), écrit
lui-même les variantes pour les autres flottants (convertir, appeler, reconvertir) et la table de
`docs/vtx-vocabulaire.md` à partir des commentaires des mots : la documentation ne peut pas dire autre chose que le code.
L'outil est en Python, comme `prelude128.py` qui recopie le prélude dans vtxc : ce qu'il écrit est du vtx.

**Ce qu'il y a : 202 mots publics**, en douze familles (nombres, flottants, interpolation, entiers et bits, textes,
tableaux, hasard, temps, vecteurs-quaternions-matrices, couleurs, cube, codes ADN) et une treizième sur Lugus seul (les
tableaux avec une fonction : `transformer`, `filtrer`, `plier`, `tous`, `trier_par`…). Dunon reçoit aussi le
vocabulaire des nombres de 0.6za, qu'il n'avait pas. Les familles « cube » (une place et ses coordonnées, le voisin, le
code de Morton) et « codes » (le complément, le brin d'en face, la teneur en G et C, les bases qui diffèrent) sont propres
à vtx. Les faces de la carte ne sont pas des mots : elles vivent dans l'ADN, lues par `lugus carte`.

**Le mécanisme, sans table** : en 0.6za, la liste des mots à variantes était écrite dans les deux compilateurs. Elle ne
l'est plus : un mot du prélude qui a des variantes `__mot_x`, `_f`, `_s`, `_w`, `_i` dans le prélude en est un, et prend
celle qui convient aux arguments (sinon le mot lui-même). Les mêmes règles dans vtx128.py, vtx64.py, vtxc128 et vtxc64 ;
vtx64.py et vtxc64 les reçoivent pour la première fois. vtxc garde pour chaque fonction du prélude s'il a des variantes
(une case de plus dans sa structure), pour ne pas chercher à chaque appel.

**Vérifié** (`tests/test_vocabulaire_etendu.py`, 13 contrôles) : un programme qui emploie chaque mot (113 lignes) donne
les mêmes mots par les deux compilateurs de chaque machine ; Lugus rend les valeurs gardées, Dunon les mêmes à 10⁻¹³ près
(son flottant a 52 bits) ; les flottants (racine cubique, hypoténuse, logarithmes, hyperboliques et leurs réciproques,
slerp, la courbe sRGB…) comme la bibliothèque `math` de Python ; les variantes de 64 et 32 bits, des entiers de 32 et 128
bits ; les mots qui prennent une fonction ; une fonction du programme qui s'appelle `carre`, `premier` ou `distance`
garde son sens. **Rien ne change pour les programmes déjà écrits** : 69 programmes de Lugus et 49 de Dunon, compilés par
l'ancien compilateur de référence et par le nouveau, donnent les mêmes mots. L'exemple : `exemples128/vocabulaire.vtx`
(un garde, son capteur, sa tête qui tourne par un quaternion, un message lu, l'ADN de son carnet), le même sur les deux
machines.

**Trouvé en route, corrigé** :
- le trampoline des fonctions passées en valeur s'écrivait dès qu'une fonction **du prélude** appelait par valeur,
  même si le programme ne l'employait pas : 65 programmes sur 69 changeaient de mots. Il ne s'écrit plus que si une
  fonction gardée en a besoin (vtx128.py et vtxc128, les mêmes mots qu'avant pour tous les programmes) ;
- Dunon : `hypotenuse(3.0S, 4.0S)` faisait diverger les deux compilateurs. vtxc64 renomme l'appel en `__hypotenuse_s`
  pendant la génération, puis décide s'il épisse la fonction : un nom qui commence par `__hyp` passait pour le journal des
  hypothèses (`__hyp_debut`…), et l'épissage était sauté. Le repère est maintenant `__hyp_`, dans les quatre
  compilateurs ;
- le paramètre qui porte la fonction, dans `transformer`, `plier`… s'appelait `f` : un programme qui a sa propre
  fonction `f` captait l'appel (une variable ne s'appelle pas quand une fonction porte son nom). Il s'appelle `__fv` ;
- `vers_degres(π)` sur Dunon : 179,99999999999994 avec deux arrondis ; 180,00000000000006 maintenant. Le π du
  flottant de 64 bits de Dunon (52 bits) est trop loin du vrai π pour que 180 tombe juste : c'est le bon arrondi, pas une
  faute.

**Ce qui n'y est pas, honnêtement** : les broches d'Arduino (pas de broches sur Lugus ni Dunon ; elles viendront avec un
service de la machine, un vrai port) ; les bibliothèques entières (le vocabulaire prépare leur branchement : vecteurs,
quaternions, matrices, couleurs, interpolations ; il ne les recopie pas) ; `reste` exact sur les flottants ;
`multiplier_ajouter` en un seul arrondi ; les itérateurs paresseux (vtx rend des tableaux) ; sur Dunon, les mots qui
prennent une fonction (Dunon n'a pas les fonctions passées en valeur) ; `premier`, `dernier`, `moyenne`, `mediane`…
lisent des tableaux d'entiers. Le prélude a presque doublé : vtxc128 se compile en 262 047 mots (195 558 avant),
vtxc64 en 246 187 ; un programme de taille moyenne (combat.vtx) se compile en moins d'une seconde.

## 64. Les modules promis par leur empreinte (17 novembre, 0.61)

**La suite de la feuille de route** : « les modules désignés par leur empreinte (un module est un ADN signé, chaque usage
une transcription) ». Premier pas, le plus utile tout de suite : qu'un programme sache **avec quel module** il a été
écrit, et qu'un module changé ne passe plus en silence.

- `importer "bibliotheque/codon.vtx" empreinte "…";` : 16 chiffres hexadécimaux, l'empreinte du texte du module (FNV-1a de
  64 bits sur ses caractères ; les retours chariot sont sautés, pour qu'un même fichier sous Windows et sous Linux ait la
  même). Les deux compilateurs de chaque machine la calculent ; s'il a changé, le module est refusé, avec ce qu'on
  attendait et ce qu'on a trouvé : « importer : le module n'est plus celui promis (empreinte attendue f62defeb8b893235,
  trouvée 0d7a…) ».
- `lugus empreinte FICHIER…` et `vtx64 empreinte FICHIER…` la donnent, pour l'écrire.
- **La chaîne** : un module peut promettre ses propres modules ; une lettre changée tout au fond est vue à la surface. C'est
  ce que font les sommes de contrôle de Cargo (Cargo.lock), de Go (go.sum) ou les empreintes de Nix, ici dans le langage.
- La promesse **ne change aucun mot** : un programme promis et le même sans promesse donnent les mêmes mots ; sans
  promesse, `importer` reste ce qu'il était (les programmes déjà écrits : les mêmes mots, sur les deux machines).
- Vérifié (`tests/test_modules.py`, 14 contrôles) : la même empreinte par vtx128.py, vtx64.py, `lugus empreinte` et `vtx64
  empreinte` ; \r\n et \n ; un module promis puis le module qu'il promet, les mêmes mots que sans promesse ; un module
  changé refusé par les deux compilateurs de chaque machine, l'empreinte trouvée dite ; sans promesse, pris tel quel ; un
  module promis absent : introuvable. L'exemple : `exemples128/modules.vtx` (le codon promis).

**Ce qui n'y est pas encore, dans l'ordre** : trouver un module **par son empreinte seule**, sans chemin (il faut que la
machine sache lister un dossier, un service à écrire) ; garder les empreintes des modules dans l'ADN du programme (un
intron « modules » ; la carte dirait alors de quel module vient chaque molécule) ; un module rangé en ADN, importé depuis
son ADN (le texte gardé et sa signature : « un module est un ADN signé »).

## 65. Le reste exact (17 novembre, 0.61b)

**Demandé par le créateur** : corriger `reste`, le manque laissé en 0.6za et en 0.61.

- `reste(a, b)` : le reste de a par b, **exact**, du signe du dividende : le `%` de Rust sur les flottants, `fmod` en C,
  `FMath::Fmod` d'UE. Un mot pour tous les types : sur les entiers, le reste signé (par zéro : x, comme la machine).
- **Pourquoi c'est exact, et pourquoi en entiers.** Le reste tient toujours dans le format de ses arguments (plus petit
  que b, et sur la grille de b) : rien à arrondir. Mais le calculer par `a - b * partie_entiere(a / b)` arrondit deux
  fois et se trompe dès que le quotient dépasse la mantisse. Il est donc fait sur les mantisses, en entiers : la division
  longue, quit par quit (sept à la fois sur Lugus, cinq sur Dunon), sur tout l'écart des exposants (jusqu'à 16 000 quits
  pour le flottant de 128 bits). Les variantes de 64 et 32 bits passent par le flottant le plus large et reviennent sans
  rien perdre (le résultat tient dans leur format).
- **Belnap** : un inconnu donne inconnu, un variable variable ; reste(∞, b) et reste(a, 0) donnent variable (l'IEEE dit
  NaN) ; reste(a, ∞) rend a ; reste(−6, 2) rend −0,0.
- **Vérifié** (`tests/test_reste.py`) : 2 100 restes sur Lugus (128, 64 et 32 bits) et 1 400 sur Dunon (64 et 32), tirés au
  hasard avec les bords (sous-normaux, exposants proches, très éloignés, multiples exacts, infinis, zéros, inconnu,
  variable) : **au bit près** d'une référence en fractions exactes ; les mêmes mots par les deux compilateurs de chaque
  machine ; une fonction du programme nommée `reste` garde la main ; les 71 programmes de Lugus et les 51 de Dunon
  gardent leurs mots.
- **Ce qui reste** : `multiplier_ajouter` en un seul arrondi (le même genre de travail, avec un arrondi à la fin) ; `%`
  sur les flottants n'est toujours pas permis dans le langage (on écrit `reste`).

## 66. Le catalogue des modules et la vibration des molécules (17 novembre, 0.62)

**Décidé par le créateur le 17 au soir** : le catalogue des modules, et la reconnaissance des molécules par leur
fréquence de vibration (l'idée de la section 11).

- **Lister un dossier** : le service 28, sur Lugus et sur Dunon (en Rust et dans leurs références en Python). Il rend
  les noms d'un dossier, triés (l'ordre des caractères), un par ligne, un sous-dossier terminé par « / » ; le dossier
  absent : inconnu ; le nom existe mais n'est pas un dossier : faux. Dans le langage : `lister_dossier(nom)` (un tableau
  de textes) et `dossier_present(nom): logique` (vrai, faux, inconnu : la différence qui manquait à `fichier_present`,
  gardé tel quel pour que les programmes écrits gardent leurs mots).
- **Le catalogue** : `lugus cataloguer DOSSIER` écrit `DOSSIER/catalogue.vtxcat`. Il est écrit **en vtx**, par le
  lecteur d'ADN (`chimie/adn.vtx`, le verbe « cataloguer ») : il liste le dossier (service 28), lit chaque module (un
  `.vtx` sans `principal`), calcule son empreinte (celle de `importer … empreinte`), le fait compiler par vtxc128 dans
  une sonde (service 27), et range chaque fonction : son nom, sa masse, ses atomes, sa vibration. La référence,
  `python3 chimie/adn.py cataloguer DOSSIER`, écrit le même fichier, octet pour octet. Un module qui ne se compile pas
  seul : « - ».
- **Importer par l'empreinte seule** : `importer empreinte "16 chiffres";`, dans les deux compilateurs de Lugus et de
  Dunon. Les catalogues lus : celui du dossier qui importe, puis `bibliotheque/` (dans ce dossier, ou à côté de lui).
  Trouvé : comme par son chemin (les mêmes mots), et son texte vérifié ; introuvable, ou deux modules différents de
  cette empreinte : refusé, et dit.
- **La vibration d'une molécule** (dans le lecteur en vtx, et `chimie/adn.py` au bit près) :
  - les atomes : les instructions d'un **morceau** ; le code est coupé au début, à la cible de chaque CALL et à chaque
    prologue (PUSH R13, MOV R13,R14), pour que deux fonctions posées à la suite sans appel entre elles restent deux ;
  - les liaisons : celles du code (l'instruction suivante, un saut vers l'intérieur) et **celles des registres** (une
    lecture liée à la dernière instruction qui a écrit le registre ; un CALL les écrit tous) ;
  - l'élément suit la valence, comme pour les réactions (une liaison H, deux O, trois N, quatre et plus C) ; la masse
    d'une molécule est la somme ;
  - chaque atome vibre de ses chemins fermés de longueur 1 à 6, de son élément et de sa clé : l'instruction, sans ce
    qui dépend du programme autour (la cible d'un appel, un saut vers l'extérieur, une constante qui est une adresse) ;
    trois tours de propagation ; la vibration de la molécule mêle ses atomes, ses liaisons, sa masse, la somme et le ou
    exclusif des vibrations finales ;
  - **ses appels** (la question laissée à la mesure) : les deux. Deux passes : à la seconde, un CALL porte la première
    vibration de sa cible. Sans elles, deux fonctions qui ne diffèrent que par la fonction qu'elles appellent vibraient
    pareil.
- **Mesuré** : sur 32 programmes (les exemples de Lugus, le lecteur, vtxc128, Ogmios), 1 743 morceaux, 1 085 suites
  d'instructions différentes, 1 153 vibrations différentes (les appels en séparent encore) : **aucune collision**. Les
  fonctions de `bibliotheque/` dans les programmes qui les importent : **36 sur 36** ont la vibration de leur catalogue.
  Il a fallu deux corrections pour y arriver, mesurées : garder les constantes d'un LDI qui ne sont pas des adresses
  (`verdict` et `verdict_ordonne` du codon ne diffèrent que par elles), et ne prendre en valeur dans la sonde que les
  fonctions que le module n'appelle pas lui-même (une fonction prise en valeur n'est plus recopiée en ligne : le corps
  de celles qui l'appellent changeait).
- **La carte dit d'où vient chaque molécule** (face « sa mémoire ») : sa vibration, puis « elle vient du module codon.vtx
  (empreinte …) », « elle porte aussi … du module … » (une fonction posée à la suite, sans molécule à elle), ou « son nom
  est celui d'une molécule du module …, mais pas sa vibration : retouchée, ou compilée autrement ». Ces molécules sont
  montrées sans `--tout`, et comptées en tête. La vibration est calculée à la lecture, des mots : **le format de l'ADN
  ne change pas** (tous ses tests passent tels quels) ; c'est le catalogue qui la garde.
- **Trouvé en route, et dit** :
  - vtxc128 ne finissait pas de compiler `sortie(f)` quand `f` est un nom de fonction écrit seul (la mémoire grandissait
    sans fin) ; vtx128.py le compilait. **Corrigé (0.62b)** : `est_sig` prenait « son propre type » (-1, ce que demande
    `sortie`) pour un type de fonction, et le message lisait une signature hors des bornes ; il est borné. La sonde du
    catalogue garde sa forme (`soit __vK = f; sortie(__vK);`).
  - vtx128.py et vtx64.py acceptaient une fonction du programme qui porte le nom d'une fonction intégrée tant qu'elle
    n'était pas appelée (l'élagage l'ôtait avant le contrôle), quand vtxc la refusait : ils la refusent maintenant
    avant l'élagage, comme vtxc (les 72 programmes de Lugus et les 52 de Dunon gardent leurs mots). Conséquence, à
    regarder : `bibliotheque/cube.vtx` définissait `melanger`, devenu une fonction intégrée. **Réglé (0.62b), choix du
    créateur** : sa fonction s'appelle **`brasser`** (le brassage de deux points, voie par voie). Elle cache, dans un
    programme qui importe cube.vtx, le `brasser` du prélude (le mélange d'un tableau) ; aucun de ces programmes ne s'en
    sert. Les programmes de Senos qui importent cube.vtx gardent leurs mots ; cube.vtx est catalogué (7 molécules).
- **Les limites, honnêtement** : une fonction recopiée en ligne partout n'a pas de molécule à elle (la carte ne peut pas
  la montrer) ; une constante de moins de 32 bits chargée par un LDI est prise pour une adresse ; les données après la
  dernière fonction forment un grand morceau ; la vibration reconnaît, elle ne prouve pas (la signature de l'ADN reste la
  garantie) ; Dunon lit les catalogues pour `importer` mais ne les écrit pas (il n'a pas les fonctions passées en valeur,
  dont la sonde a besoin).
- **Vérifié** (`tests/test_catalogue.py`, 25 contrôles) : la liste d'un dossier, la même sur les quatre machines et par
  les deux compilateurs de chacune ; les morceaux et leur vibration, le lecteur en vtx et chimie/adn.py, ligne pour ligne
  (jusqu'au lecteur lui-même, 187 morceaux) ; le catalogue, octet pour octet ; importer par l'empreinte, les mêmes mots
  que par le chemin, sur les deux machines ; introuvable, deux modules, un module retouché : refusés par les quatre
  compilateurs ; la carte : « vient du module », et la retouche vue.
- **La suite** (rectifiée par le créateur le 18) : les empreintes des modules ne vont pas dans un intron de l'ADN, elles
  se rangent **dans un cube**, et suivent le chemin : cube (la place et le contenu de chaque module et de chaque
  molécule) → hex (l'écriture : ce que `catalogue.vtxcat` montre aujourd'hui sans cube derrière) → ADN (le cube sur
  disque, avec son anti-cube et son ombre) → ARN (le compilateur qui importe). Puis l'accroche (deux codes qui partagent
  des vibrations).

## 67. Le cube du catalogue (18 novembre, 0.62c)

**Rectifié par le créateur le 18** : les empreintes des modules se gardent dans un cube, pas dans l'ADN ni dans un
texte, et suivent le chemin. Ses mots : « le Hex est une adresse, le cube est l'ensemble de plusieurs adresses ; le
compilateur doit choisir le cube pour ensuite trouver les informations à l'intérieur avec l'adresse ». Le catalogue de la
0.62 (`catalogue.vtxcat`) n'était qu'un texte, sans cube derrière : c'est corrigé.

- **Le cube du catalogue** : `cube128-1-392.cub` dans le dossier catalogué (la fréquence 392, le sol ; la 440 est celle du
  cube d'un programme), rangé avec son anti-cube et son ombre, comme tout cube sur disque. **La place dit ce qu'est le
  point** :
  - les modules dans la moitié basse (RR de 00 à 7F) : la colonne #RRGG d'un module vient de son empreinte (la première
    page d'abord, la colonne suivante si elle est prise : comme le cube des noms de vtxc64) ; sa chaîne descend la
    colonne, à la Fischer : la tête (l'empreinte, le nombre de molécules, la longueur du nom, les colonnes qu'elle prend),
    le nom (quatre caractères par point, un par voie de 32 bits), puis chaque molécule (sa vibration, sa masse, ses
    atomes, la longueur de son nom) suivie de son nom ; un grand module continue sur la colonne suivante ;
  - l'index des vibrations dans la moitié haute (#800000 à #FEFFFF, la page #80 d'abord) : la place vient de la
    vibration ; le point dit la vibration et où est la molécule (la colonne de son module, son rang dans la chaîne) ;
  - la coiffe en #FFFFFE (ce que portent tous les points), la queue en #FFFFFF (« VTXCAT », les modules, les molécules).
- **Le chemin** : `lugus cataloguer` (le lecteur d'ADN en vtx) range d'abord le cube (l'ADN, ce qui dure), puis le
  **lit** pour écrire `catalogue.vtxcat`, qui en est la lecture hex : chaque ligne donne la place de son point.
  `python3 chimie/adn.py cataloguer` fait le même cube, le même anti-cube, la même ombre et le même hex, octet pour octet
  (par l'écrivain de la machine Python).
- **Choisir un cube par son chemin : le service 29**, sur Lugus et sur Dunon (en Rust et en Python). Le cube nommé
  `cube128-ÉTAGE-FRÉQUENCE.cub` est relu avec son anti-cube et son ombre (réparé s'il le faut, l'état noté pour
  `etat_disque`), et accordé dans son étage à la première fréquence libre depuis la sienne ; il rend cette fréquence (pas
  un nom de cube : faux ; absent : inconnu). **Dunon lit le même cube en deux moitiés** (le choix du créateur) : chaque
  point de 128 bits devient deux mots de 64 bits, à la même adresse, la moitié basse à la fréquence rendue, la haute à la
  suivante. Un seul cube, un seul ADN.
- **`importer empreinte "…";`** : les quatre compilateurs **choisissent le cube** de chaque dossier (celui du dossier, puis
  de `bibliotheque/`), puis **lisent à l'adresse** que donne l'empreinte (sa colonne, la suivante si elle est à un
  autre) : la tête dit l'empreinte, le nom suit. vtxc128 et vtxc64 passent par le service 29 ; vtx128.py et vtx64.py
  lisent le même fichier avec le même miroir. Le texte `catalogue.vtxcat` n'est plus lu par les compilateurs.
- **La carte** choisit les mêmes cubes (service 29) et cherche chaque molécule **par l'index des vibrations** : une
  lecture à une place, pas un parcours. Un cube abîmé est réparé à la lecture, et la carte le dit.
- **Vérifié** (`tests/test_catalogue.py`, 31 contrôles) : le cube, son anti-cube, son ombre et son hex, octet pour octet
  entre le lecteur en vtx et la référence ; le service 29 sur les quatre machines ; importer par le cube, les mêmes mots
  par les quatre compilateurs ; un octet changé dans le cube : réparé, et tout se lit encore.
- **Les limites, honnêtement** : un catalogue de la 0.62 (le texte seul) n'est plus lu, il faut refaire `lugus
  cataloguer` ; le cube d'un petit catalogue prend trois pages de 65 536 points (3,2 Mo, et autant pour l'anti-cube) :
  c'est le prix d'un cube rangé par pages ; Dunon ne lit pas les brins d'un cube de Lugus (le catalogue n'en a pas).
- **Une direction donnée par le créateur** : que la mémoire du cube serve à l'IA, pour éviter la coupure entre deux
  conversations (ce qu'une IA a compris d'un projet se perd quand la conversation change). Le cube du catalogue en est
  le premier pas : une mémoire rangée par la place, durable, vérifiée par son anti-cube et son ombre, qu'on interroge
  par une adresse. La suite à concevoir : un cube de mémoire du projet (ses décisions, ses fondements, ce qui est fait),
  que le lecteur en vtx sait lire et qu'une IA interroge au début de son travail.

## 68. Les cubes mères (18 novembre, 0.63)

**Décidé par le créateur le 18** : les programmes vont bâtir leurs cubes, et les fréquences seules ne suffisent pas
(la 440, celle de `lugus cube`, était la même pour tous les programmes d'un dossier : le second écrasait le premier).
Pas d'anciennes versions gardées. Un cube pour archiver les autres, oui, mais sans fréquence à lui, « sinon on aura une
limite de nouveau programme » : **comme pour un fichier, un nom de cube mère, et les sous-cubes archivés avec une
fréquence et un indicatif lié au nom**.

- **Le cube mère** : `cube128-NOM.cub` (Dunon : `cube64-NOM.cub`), avec son anti-cube et son ombre, comme tout cube sur
  disque. Il n'a pas de fréquence. C'est le squelette du programme : **à l'adresse #F, la place même de la fréquence**, le
  descripteur du sous-cube de fréquence F (pour chaque étage de 1 à 3 : présent, ses pages, onze bits de coiffe, celle
  de son fichier). Sur Lugus, la moitié haute de chaque point porte l'indicatif (l'empreinte FNV-1a du nom). La queue
  (#FFFFFF) dit l'indicatif et le nombre de sous-cubes ; la coiffe (#FFFFFE) brasse tous les descripteurs.
- **Les sous-cubes** : `cube128-NOM-ÉTAGE-FRÉQUENCE.cub` : le nom est leur indicatif. Chaque programme a toutes les
  fréquences à lui, et le nombre de programmes n'a pas de limite. Un sous-cube rangé remplace le précédent.
- **Dans le langage** : `cube_mere("labyrinthe")` (le service 30, sur Lugus et Dunon, en Rust et en Python). Ensuite,
  `ranger_cube` écrit le sous-cube et met le cube mère à jour, et la machine relit les pages sous ce nom. Il rend
  l'indicatif ; un nom vide : plus de cube mère ; un nom refusé : faux. Un nom : de 1 à 64 caractères (lettres,
  chiffres, `_`, `-`, les lettres accentuées du latin), sans `-` au bord, et dont le dernier morceau après un `-` n'est
  pas un nombre (sinon `jeu-2` serait lu comme un sous-cube). Sans cube mère, rien ne change : les programmes écrits
  gardent leurs fichiers et leurs mots.
- **Le service 29** choisit aussi un sous-cube ou un cube mère par son chemin (un cube mère est accordé à la plus haute
  fréquence libre de l'étage 1, le temps de le lire). Sur Dunon, il accorde aussi ses propres cubes (`cube64-…`), tels
  quels.
- **Le chemin** : `lugus cube PROG.adn [FRÉQUENCE]` range le programme dans `cube128-PROG-1-FRÉQUENCE.cub`, sous le cube
  mère `cube128-PROG.cub` (le nom du fichier du programme, ses caractères refusés changés en `_`). Il se relance par son
  sous-cube (`lugus cube128-PROG-1-440.cub`) ou par son cube mère (`lugus cube128-PROG.cub` : son programme est dans le
  sous-cube 1-440). Les anciens cubes simples (`cube128-1-F.cub`) se lisent toujours.
- **Vérifié** (`tests/test_cube_mere.py`, 16 contrôles) : le cube mère et ses sous-cubes, les mêmes fichiers sur Lugus et
  Dunon, en Rust et en Python, octet pour octet ; les mêmes mots par les deux compilateurs ; le squelette lu par le
  service 29 ; les noms refusés ; deux programmes du même dossier, chacun sa fréquence 440, sans se gêner ; le chemin,
  rangé sous le cube mère et relancé par lui. `tests/test_adn_deux_sens.py` suit les nouveaux noms.
- **La suite** : le .exe qui embarque les cubes de son programme (le cube mère dit lesquels) ; Gobannos, les fichiers et
  les services.

## 69. Les faces dans le cube (21 novembre, 0.64)

**Décidé avec le créateur le 21** (point 5 du carnet, section 11) : les six faces de chaque molécule rangées dans le
cube, lues par la machine pendant qu'elle tourne. Ses choix : **la même fréquence sur les quatre étages**, et **le code
à l'étage 0, nommé par une lettre gauloise, le tau gallicum Đ** (440/Đ). Sa hiérarchie, notée : le cube mère, le cube
hex, la molécule, l'atome.

- **Le cube du programme** (`lugus cube PROG.adn [F]`) : à la fréquence F (440 par défaut), sous le cube mère du
  programme, les quatre étages :
  - **F/Đ, le code** : chaque mot à sa place, comme dans la machine qui tourne, la coiffe en #FFFFFE, la queue en
    #FFFFFF (`cube128-PROG-Đ-F.cub`) ;
  - **F/1, F/2, F/3, les trois axes du dé** : chaque molécule à la place de son début (l'adresse que donne une fonction
    passée en valeur), un axe par étage, **la face d'un côté dans la moitié basse du point, la face opposée dans la
    haute** : F/1 ce qu'elle est | ce qu'elle touche ; F/2 ses racines | ses branches ; F/3 ses promesses | sa mémoire.
    Les faces viennent de la carte rangée dans l'ADN (la section `faces`) ; un brin sans carte à six faces n'en a pas.
    La queue des cubes des faces dit « VTXFACES » et le nombre de molécules.
- **Ce que porte chaque face** (64 bits) : ce qu'elle est (le genre, ses mots, ses lignes) ; ce qu'elle touche (deux
  quits : elle-même, avec ses appels) ; ses racines (sa profondeur, combien l'appellent, la première) ; ses branches
  (combien elle en appelle, la première, la dernière) ; ses promesses (exige, garantit, les exemples, l'isotope) ; sa
  mémoire (l'empreinte de son texte). Les noms et les listes entières restent dans la carte de l'ADN.
- **Le centre n'est pas écrit** : il se lit à chaque lecture. `centre(f)` compare le code qui tourne, mot pour mot, à
  celui de l'étage Đ : vrai, il est celui du cube ; variable, il a changé (une avarie pendant qu'il tourne) ; faux, le
  cube a été réparé par son anti-cube et son ombre en le lisant ; inconnu, pas de faces.
- **Dans le langage** : `face(f, k)` (k de 0 à 5, dans l'ordre du dé) et `centre(f): logique`, le service 31, dans les
  quatre compilateurs (les mêmes mots deux à deux). Lugus en Rust lit les faces quand le programme est lancé depuis son
  cube (`lugus cube128-PROG.cub`, ou un sous-cube) ; lancé depuis son texte, ou sur Dunon (qui n'a pas de fonctions
  passées en valeur, ni de cube de programme), les faces sont à 0 et le centre inconnu.
- **Le cube mère, 0.64b (la demande du créateur : 32 ou 64 bits par étage)** : 64 bits par étage. Le cube mère porte
  maintenant ses quatre étages, comme ses sous-cubes : **le descripteur de l'étage e du sous-cube de fréquence F est à
  l'étage e du cube mère, à l'adresse #F** (présent, ses pages, puis 54 bits de coiffe : l'empreinte de son fichier) ;
  sur Lugus, la moitié haute du point garde l'indicatif. Un mot entier de Dunon, une moitié de point de Lugus. La
  dimension du cube ne change pas (trois axes, une adresse #RRGGBB de 24 bits) : c'est la profondeur du point qui
  grandit, et les étages du cube mère qui servent. À l'étage Đ : la marque du format (« VTXMERE2 ») en #FFFFFD, la
  coiffe en #FFFFFE, la queue en #FFFFFF. Une page du fichier dit son étage (bits 8 et 9 de son numéro) ; l'anti-cube
  garde ces bits (le miroir de Lugus et de Dunon, en Rust et en Python). Le service 29 relit un cube mère sur ses quatre
  étages, à une fréquence libre dans chacun. Un cube mère d'avant (sans la marque) est refait au prochain rangement.
  **Laissé ouvert pour des processeurs plus larges** (la demande du créateur) : la largeur d'un point est écrite dans
  l'en-tête du fichier (« VTXCUB64 », « VTXCU128 » ; un SPU-256, *Albios*, aurait le sien), et le format du cube mère
  porte sa marque (« VTXMERE2 », qui peut devenir « VTXMERE3 »). La règle pour aller plus haut : les 64 bits du
  descripteur restent au bas du point, tels quels ; une machine plus large ajoute ses champs au-dessus, sans rien
  déplacer. Un cube écrit aujourd'hui se lira donc demain sur une machine plus large, et celle-ci saura qu'elle lit un
  cube plus étroit par son en-tête.
- **Les anciens cubes** : un cube de la 0.63 (le programme à l'étage 1) se lance encore par son cube mère ; un cube des
  faces lancé seul est refusé, et dit pourquoi.
- **Vérifié** (`tests/test_faces_cube.py`, 13 contrôles) : les six faces lues pendant qu'il tourne, celles de la carte
  champ pour champ ; le centre vrai, variable (une avarie), faux (le cube des faces abîmé, réparé), inconnu (depuis son
  texte, sur Dunon) ; les mêmes mots par les deux compilateurs de Lugus et de Dunon ; le descripteur de chaque étage, à son étage du cube mère ;
  un cube de la 0.63 ; un cube des faces seul refusé. `tests/test_cube_mere.py` et `tests/test_adn_deux_sens.py` suivent
  les nouveaux noms.
- **Les limites, honnêtement** : une face tient sur 64 bits, alors les listes d'appels sont réduites à leur nombre, leur
  première et leur dernière ; une molécule recopiée en ligne n'a pas de place à elle ; un programme lancé depuis son
  cube qui range lui-même un cube à sa propre fréquence sous son propre nom écraserait ses faces ; `afficher` montre une
  face dont le bit 63 est posé comme un nombre négatif (l'empreinte, souvent), les bits restent justes.
- **Trouvé en route, et corrigé** : vtx128.py et vtxc128 ne donnaient pas les mêmes mots quand deux fonctions passées
  en valeur, sans être appelées par valeur, formaient un accord (deux appels à la suite) : la recherche de vtx128.py
  ne descendait pas dans les tâches d'un accord, et oubliait la table d'appels ; elle y descend (les programmes écrits
  gardent leurs mots). Et `tests/test_natif128.py` jouait `cube_mere.vtx` deux fois dans le même dossier (la seconde
  relisait les cubes de la première) : chaque jeu part sans cube.
- **La suite** : la paillasse et Ogmios montrent ces faces lues dans le cube ; puis les autres points du langage.

## 70. Les fonctions passées en valeur sur Dunon (21 novembre, 0.65)

**Le premier des points du langage**, dans l'ordre donné par le créateur. Dunon n'avait pas ce que Lugus a depuis la
0.6w et la 0.6x : une fonction qui se passe à une autre, et son type.

- **Comme sur Lugus** : un nom de fonction sans parenthèses est sa valeur ; `f(…)` par une variable qui n'est pas le nom
  d'une fonction est un appel par valeur ; les arguments empilés comme pour un appel ordinaire, la cible dans R1, puis
  `CALL __appeler`, qui fait `PUSH R1 ; RET`. Derrière, la table jamais jouée : un `CALL` vers chaque fonction passée,
  pour qu'elle ait sa molécule. Une fonction passée n'est jamais recopiée en ligne ; un appel par valeur touche tout
  pour la partition.
- **Le type** : `fonction(entier, entier): entier`, vérifié où l'on peut : une fonction nommée là où l'on attend un type
  doit l'avoir ; un appel par une variable typée compte ses arguments et convertit chacun (un flottant reste un
  flottant, un texte reste un texte). Un entier se range dans une variable typée fonction (la même porte ouverte que
  sur Lugus).
- **Ce qui diffère de Lugus, et pourquoi** : pas de promesse « touche » dans le type, puisque Dunon ne juge pas ce que
  touchent les fonctions ; une valeur de 128 bits (`entier_petuar`, `flottant_petuar`), qui tient sur deux mots de
  Dunon, ne passe pas par valeur, et c'est dit.
- **Dans les deux compilateurs de Dunon**, vtx64.py et vtxc64, les mêmes mots et les mêmes refus, mot pour mot. Les
  programmes déjà écrits gardent leurs mots (les 55 programmes de Dunon comparés à l'ancien compilateur : 0 changé).
- **Le vocabulaire qui prend une fonction** (`transformer`, `filtrer`, `plier`, `tous`, `au_moins_un`, `aucun`,
  `trouver_si`, `rang_si`, `compter_si`, `pour_chacun`, `garder_si`, `trier_par`) est maintenant aussi sur Dunon ; une
  fonction du programme qui porte l'un de ces noms garde la main (les programmes de Dunon gardent leurs mots).
- **`face` et `centre`** se lisent maintenant d'une fonction passée sur Dunon : 0 et inconnu, puisque Dunon n'est pas
  lancé depuis un cube de programme.
- **Vérifié** (`tests/test_valeurs64.py`, 14 contrôles) : `exemples128/valeurs.vtx` et `exemples128/types_fonction.vtx`
  sur Dunon, un mélange (un tableau de fonctions, la récursion par valeur, une composition), deux fonctions passées sans
  appel par valeur, face et centre, le vocabulaire qui prend une fonction ; six refus, le même message des deux côtés.
- **Les limites, honnêtement** : comme sur Lugus, pas de type de fonction dans un type de fonction ; sans type écrit, le
  nombre d'arguments n'est pas vérifié.

## 71. multiplier_ajouter en un seul arrondi (21 novembre, 0.65)

**Le deuxième point du langage.** `multiplier_ajouter(a, b, c)` (Rust `mul_add`, C `fma`, UE `FMath::FMA`) faisait deux
arrondis, le produit puis la somme, et le disait. Il est maintenant **exact, arrondi une seule fois**, sur les cinq
flottants : Lugus 128, 64 et 32 bits, Dunon 64 et 32 bits.

- **Comment** : comme `reste` (0.61b), en entiers. Les mantisses deviennent des grands entiers (les limbes de 16 bits
  qui servent déjà à écrire les flottants en décimal) ; le produit exact (jusqu'à 224 bits sur Lugus) ; c aligné sur
  lui ; la somme ou la différence exacte ; puis un seul arrondi au plus proche, pair au milieu, avec les sous-normaux et
  le débordement, comme la machine (`spu64/qflot.py`). Un terme bien plus petit que l'autre ne compte que par son signe :
  il devient une miette sous le dernier bit de l'autre, à la même place pour l'arrondi, et la somme reste courte (sans
  cela, un écart de 16 000 quits sur Lugus ferait un grand entier de 32 000 bits).
- **Chaque largeur a son propre calcul** (le même cœur, ses bornes à elle) : passer par le flottant le plus large puis
  revenir aurait fait deux arrondis, le double arrondi que l'on voulait justement ôter.
- **Belnap** : un inconnu, un variable, un infini ou un zéro parmi les trois : comme `a * b + c` (rien à arrondir de
  plus) ; sur les entiers, `a * b + c` (les entiers de 32 et 128 bits ont leur variante).
- **Vérifié** (`tests/test_fma.py`, 12 contrôles) : 138 cas par largeur, tirés au hasard avec les bords (sous-normaux,
  exposants extrêmes, annulations de a·b par c, milieux d'arrondi, débordements, les états et les infinis) : **au bit
  près** d'une référence en fractions exactes, sur les cinq flottants ; deux arrondis se seraient trompés de 20 à 38 fois
  sur 138. Les mêmes mots par les deux compilateurs de chaque machine. Les programmes déjà écrits gardent leurs mots
  (77 sur Lugus, 58 sur Dunon, comparés à l'ancien compilateur).
- **Le prix, dit sans fard** : environ 11 000 instructions par appel sur Dunon et 26 000 sur Lugus, contre une
  multiplication et une addition. C'est le prix de l'exactitude sans instruction de la machine ; une instruction FMA
  dans Lugus et Dunon (le processeur la fait en un cycle) le rendrait gratuit, et `multiplier_ajouter` l'emploierait
  sans changer de sens.

## 72. Simplifier : l'ADN, l'ARNc, le cube (21 novembre, 0.66)

**Décidé par le créateur le 21** : trois formes seulement. Un programme pouvait vivre en neuf : le texte, les mots, le
hex, le cube, l'ADN, et cinq ARN (rapide, sûr, mémoire, complet, l'ARNc). Il en reste trois qui comptent, et le
chemin du créateur les tient : **ARNc → ADN → hex → cube → hex → ADN → ARN**, où l'ARN du bout du chemin est l'ARNc
lui-même.

- **L'ADN** est ce qui dure, **l'ARNc** le travail (il porte tout : la coiffe, les mots, les trois témoins, le texte,
  la carte, les souvenirs, et se rétrotranscrit en ADN entier), **le cube** la mémoire (le code à l'étage Đ, les faces
  aux étages 1 à 3, sous le cube mère). Les mots et le hex restent des vues d'outil : ce que la machine joue, ce que
  l'homme lit.
- **`lugus transcrire PROG.adn PROG.arn`** écrit l'ARNc. Les isoformes épissées ne s'écrivent plus (`--isoforme rapide`,
  `sur`, `memoire`, `complet` : refusé, et dit pourquoi) ; ce sont des **façons de lancer l'ARNc** : `lugus PROG.arn`
  avec ses témoins et ses souvenirs (la patrouille veille sur les isotopes lourds, ou partout avec `--veille`), ou
  `lugus PROG.arn --rapide` : les mots seuls, ni témoins, ni patrouille, ni souvenirs, ce que faisait l'ARN rapide.
- **Les anciens ARN se lisent toujours** : un ARN rapide, sûr, mémoire ou complet de la 0.65 se lance, se
  rétrotranscrit et montre sa carte comme avant (`chimie/adn.py` garde leur écrivain, `ecrire_arn_ancien`, pour le
  vérifier).
- **Vérifié** : `tests/test_adn_chemin.py` (l'ARNc écrit en vtx, lancé et lancé rapide ; les quatre isoformes refusées,
  rien n'est écrit ; un ancien ARN de chacune se lance ; l'épigénome dans l'ARNc), `tests/test_adn_deux_sens.py` (le
  tour entier dans l'ordre du créateur, l'ADNc de l'ARNc et des quatre anciens ARN, octet pour octet de la référence),
  `tests/test_patrouille.py` (l'ARNc lancé rapide est l'ancien ARN rapide : sans témoins, une avarie fausse le résultat ;
  lancé tel quel, la patrouille répare ; ses souvenirs repris, et pas en rapide), `tests/test_carte_arn.py` (la carte
  d'un ancien ARN rapide).
- **Ce qui reste de « simplifier »** : un glossaire d'une ligne par mot dans les messages (que « molécule », « brin »,
  « coiffe » s'expliquent là où ils paraissent).

## 73. Le glossaire d'une ligne par mot (21 novembre, 0.67)

**Le dernier morceau de « simplifier ».** Les messages de Lugus parlent la langue de vtx : molécule, coiffe, brin,
cube, étage Đ, ADNc, patrouille… Ils s'expliquent maintenant eux-mêmes.

- **À la fin des messages**, les mots propres à vtx qui y ont paru, **une ligne chacun, une seule fois**, dans l'ordre
  du glossaire (40 mots, ceux du carnet, section 13). Rien n'est changé aux messages eux-mêmes.
- **Pour qui** : montré quand les messages vont à quelqu'un (la console), ou avec `VTX_GLOSSAIRE=1` ; `VTX_GLOSSAIRE=0`
  le tait. Lus par un tube (les tests, les outils), les messages restent tels quels, octet pour octet.
- **Où** : tous les messages de `lugus`, ceux du lecteur d'ADN en vtx compris. Dunon et l'atelier pas encore.
- **Vérifié** (`tests/test_glossaire.py`, 4 contrôles) : les mots parus, chacun une fois, et pas les autres ; rien par
  un tube ni avec `VTX_GLOSSAIRE=0` ; un message sans mot propre à vtx, pas de glossaire.

## 74. La fenêtre d'un programme (21 novembre, 0.68)

**Demandé par le créateur le 21** : pas d'image dans la vue du cube ; un programme qui dessine, joue un son ou se finit
ouvre sa propre fenêtre, comme dans un éditeur de code moderne.

- **Dans l'atelier** (`atelier.exe`, Ogmios) : F5 ouvre la fenêtre du programme dès qu'il appelle `presenter()` (la même
  que `vtx toile128` : l'image agrandie sans flou, la souris et le clavier de cette fenêtre vont au programme) ; la vue
  du cube reste au cube. Maj+F5 l'arrête toujours ; relancé, le programme ferme sa fenêtre d'avant et en ouvre une neuve.
  Les fichiers qu'il crée (images, sons, exécutables) s'ouvrent toujours dans la visionneuse.
- **Avec `lugus PROG.vtx`** (et un double-clic sur un programme) : la même fenêtre, qui reste ouverte à la fin jusqu'à
  ce qu'on la ferme. Elle s'ouvre pour quelqu'un : à la console, ou avec `VTX_FENETRE=1` ; lu par un tube (les tests),
  le programme n'en ouvre pas, ni avec `VTX_FENETRE=0`.
- **Sous Windows seulement** : ailleurs, `presenter()` rend 0 sans rien montrer, comme avant. Le code de Windows est
  vérifié ici à la compilation (`cargo check` sous la forme de Windows) ; il se voit sur le PC du créateur
  (`essai-0.68.bat`).
- **La suite** : Ogmios écrit en vtx (`ogmios/ogmios.vtx`) aura la même fenêtre pour le programme lancé par F5, et ne
  figera plus pendant qu'il tourne (la machine fille lancée à côté, son compte rendu lu au fil de l'eau, Échap pour
  l'arrêter) : il faut pour cela que la machine sache tenir deux fenêtres à la fois.

## 75. L'épreuve d'Alésia, Ogmios indépendant, la palette des cases (21 novembre, 0.69)

**Demandé par le créateur le 21** : un test complet et parlant de ce que fait vtx (création, programmation, calcul,
sécurité) à la place des nombreux tests du paquet ; Ogmios en programme indépendant avec son raccourci ; plus de cases
à la paillasse, avec les atomes existants, H, O, N et C gardés pour la molécule de registre.

- **L'épreuve** (`epreuve/epreuve.py`, `epreuve/alesia.vtx`, 41 vérifications en une quinzaine de secondes), sept
  chapitres qui disent ce qu'ils montrent puis le vérifient : I la forge (des cases posées depuis la palette, une
  réaction complétée qui réagit, les deux compilateurs d'accord sur les 4064 mots d'alesia.vtx) ; II programmer
  (structures, textes, tableaux, dictionnaires, fonctions en valeur) ; III compter (30!, fibonacci(150), 2^127 - 1,
  1/3 et racine de 2 sur 34 chiffres, vérifiés par Python ; le flottant quaternaire montré tel qu'il est) ; IV douter
  (fusion, le savoir ouvert, la contradiction gardée) ; V réagir (une vague de 10 000 carrés, 84 / 0 réparé, la machine
  Python qui redit les mêmes lignes) ; VI se souvenir (ARNc -> ADN -> hex -> cube -> hex -> ADN -> ARN, chaque forme
  relancée redit les mêmes lignes, le hex revenu du cube identique octet pour octet) ; VII se défendre (la promesse
  rompue, le type de fonction, la faute de frappe refusés ; une avarie qui fausse le résultat sans patrouille, réparée
  sous la patrouille ; neuf mots abîmés : l'apoptose ; l'ARN coiffé vérifié). VIII, montré sans être compté : les
  brèches que l'épreuve a trouvées.
- **Les brèches trouvées** (à fermer ensuite) : `t[i]` hors des bornes d'un tableau lit au-delà sans rien dire (0) ;
  `soit m: texte = n;` avec un entier est accepté par les deux compilateurs, et l'affichage prend l'entier pour
  l'adresse d'un texte (la machine s'emballe).
- **Le flottant quaternaire, pas une brèche** : `0.1` (64 bits, base 4) vaut 0.09999999999999998 ; il s'affiche « 0.1 »
  (le décimal le plus court qui redonne la même valeur) et `0.1 + 0.1` s'affiche 0.19999999999999996. La machine en Rust
  et la référence en Python sont d'accord : c'est la base 4, comme 0.1 + 0.2 en IEEE.
- **Ogmios indépendant** : `ogmios.exe` est construit sous son nom (`src/ogmios_exe.rs`, sans console sous Windows).
  `vtx installer` pose ses raccourcis « Ogmios » sur le Bureau et dans le menu Démarrer (`vtx desinstaller` les
  retire) ; l'essai le pose dans le dossier fixe `Vercintorix1.0 rust\Ogmios` (un exemple plus récent n'y est pas
  remplacé).
- **La palette des cases** (`paillasse::PALETTE`, 24 cases, 14 familles) : la structure reste à la valence (H 1, O 2,
  N 3, C 4 : la molécule de registre) ; la famille dit ce que fait la case : C calcul, S soufre la logique de Belnap,
  Si silicium les conditions, Fe fer la mémoire du cube, Mg magnésium les vagues, K potassium le rendez-vous, F fluor
  les conversions, P phosphore les mesures, Au or le calcul exact, Zn zinc la réparation (le zinc protège le fer),
  Ar argon le hasard, Ca calcium le temps, Na sodium les données, Cl chlore la sortie. La case porte le symbole et la
  couleur de sa famille, son élément de structure suit son titre ; les explications disent les deux. Dans Ogmios, le
  menu **Cases** : « Toutes les cases expliquées », puis une entrée par case, écrite dans la réaction montrée (une
  réaction neuve s'il n'y en a pas). Dans `vtx paillasse --gestes` : `palette`, `poser NOM`.
- **Le paquet allégé** : les tests de développement restent dans le dépôt (et `verifier.py`), le paquet n'emporte plus
  que l'épreuve (`outils/fichiers_du_paquet.txt` : 211 fichiers au lieu de 266).

### 75 bis. Le clic droit des cases, la fin, deux brèches fermées (21 novembre, 0.69b)

**Demandé par le créateur le 21, après l'essai 0.69** : le menu des cases sur le clic droit (plus ergonomique), une
case pour la fin ou le résultat, puis fermer les deux brèches trouvées par l'épreuve.

- **Le clic droit dans le vide** d'une réaction ouvre le menu des cases là où l'on a cliqué (« Case vide », puis la
  palette famille par famille) ; la case choisie se pose à cet endroit et s'ouvre à l'édition. Le clic droit sur une
  case l'édite, comme avant. Par les gestes : `droit X Y`, puis `case NOM` (ou `case vide`).
- **La fin** (Ne, le néon : l'enseigne qui dit que c'est fini) : `= _ -> r` où `r` est le résultat de la réaction, ou
  `= sortie(_)` si elle ne rend rien ; la case qui donne le résultat d'une réaction porte le néon.
- **t[i] hors des bornes, fermé sur Lugus** : l'analyseur écrit `t[__borne(i, t, ligne)]` (pour une variable ou
  `t[i][j]`, pas dans le prélude) ; `__borne` (prélude) compare l'indice à la longueur, et hors du tableau les
  services 32 (l'indice retenu) et 33 (l'arrêt, `longueur << 24 | ligne`) arrêtent la machine avec le message. Pour le
  juge et l'analyse des effets, `__borne` ne fait que lire l'étage 3 (une fonction « touche lecture » qui lit t[i] reste
  tenue ; les vagues se partagent toujours entre les cœurs). vtxc128 lit `__borne` dans le prélude d'office et la sait
  entière avant de lire le prélude. Coût mesuré : 3,6 millions d'instructions au lieu de 1,1 sur une boucle qui ne fait
  que lire un tableau de 1000 cases cent fois.
- **Un nombre pour un texte, fermé** (vtx128.py `nombre_pour_texte`, vtxc128 la même) : un nombre sûr (écrit, un
  calcul `- * / % << >> & | ^`, un `+` de deux nombres sûrs, une variable dont toutes les valeurs en sont : le plus
  grand point fixe) ne va ni dans un `soit x: texte`, ni dans un paramètre `texte` ; la plus petite ligne fautive est
  dite, la même par les deux compilateurs.
- **Vérifié** : les mêmes mots sur les 47 programmes de Lugus (vtxc128 compris, qui se compile lui-même) ; l'épreuve
  (47 vérifications) ; le juge en vtx et sa référence en Python (services 32 et 33 : une lecture).
- **Pas encore** : Dunon (vtx64, vtxc64) a toujours les deux brèches ; `s.champ[i]` n'est pas vérifié.

### 75 ter. L'épissage des vérifications, Dunon et les champs (21 novembre, 0.69c)

**Décidé avec le créateur le 21** : la vitesse compte ; l'épissage est le bon lieu pour retirer les vérifications de
`t[i]`, en deux niveaux.

- **L'épissage sûr, toujours fait** (vtx128.py et vtx64.py `epissage_sur`, vtxc128 et vtxc64 la même) : dans
  `pour i dans a..longueur(t)`, `t[i]` perd son `__borne` si rien dans la boucle ne peut rendre `i` trop grand : ni `i`
  ni `t` réaffectés ; aucune fonction qui raccourcit un tableau (`retirer`, `enlever`, `vider`, `liberer`,
  `tronquer_tableau`, `compter_si` et trois internes) ; aucun appel, sauf `longueur`, qui reçoive une variable nue autre
  que `i` ou un champ (ce pourrait être `t`) ; aucun appel par valeur ; aucune écriture directe à l'étage 3 hors d'une
  case de tableau. Mesuré : 1 216 315 instructions au lieu de 3 640 214 (1 115 214 sans aucune vérification).
- **L'épissage rapide, demandé, après l'épreuve** : `lugus eprouver PROG.adn [ENTRÉES…]` lance le programme avec ses
  vérifications ; s'il va au bout, l'ADN le note (l'intron « epreuve » : la signature de ses mots). `lugus PROG.adn
  --rapide` recompile alors le texte gardé dans l'ADN, précédé de `constante __SANS_BORNES = 1; ` (sur la première
  ligne : les numéros de ligne ne bougent pas), et lance ces mots-là. Sans épreuve (ou si les mots ont changé), le
  programme garde ses vérifications et Lugus dit pourquoi. L'épreuve vaut pour les entrées données. `--rapide` d'un ARN
  reste ce qu'il était (les mots seuls, sans témoins).
- **Dunon** : les deux brèches fermées de même (le service 32 et 33 dans spu64.rs et spu64.py, `__borne` dans son
  prélude, `nombre_pour_texte`, l'épissage).
- **Les champs** : `s.champ[i]` (le champ d'une variable) est vérifié aussi, sur les deux machines.
- **Pas encore** : une poignée calculée (`f()[i]`) ; le message nomme `t`, pas le vrai nom du tableau.

## 76. LDT et STT : la machine vérifie t[i] elle-même ; Ogmios, les vagues et les pages (22 novembre, 0.70)

**Décidé avec le créateur le 22** : une instruction vérifiée dans le SPU (« le 2 »), sur Lugus et sur Dunon ; puis deux
points d'Ogmios : la place d'une case dans les vagues décide de sa ligne, et des pages qu'on crée facilement, le néon
qui renvoie à la page suivante.

- **LDT et STT** (codes 2C et 2D, libres sur les deux machines, à côté de LDX, STX et LDIH) : `LDT d, s, t, #ligne`
  lit la case T du tableau de poignée S ; `STT d, s, t, #ligne` écrit S dans la case T du tableau de poignée D. À la
  largeur L de l'instruction : la longueur `M[étage3(P)]`, l'adresse des données `M[étage3(P + 2)]`, la case
  `M[étage3(données + T)]` (étage3 : les bits L-1 et L-2 à 3, comme ETG #3). T hors de 0..longueur (sans signe) : la
  machine s'arrête et dit la ligne (l'immédiat), l'indice et la longueur, le même message que le service 33. Partout :
  spu128.rs, spu128.py, spu64.rs, spu64.py ; vtx128.py, vtxc128, vtx64.py, vtxc64 (`case_bornee` : la case dont
  l'indice passe par `__borne` devient un LDT ou un STT, l'arbre et le juge ne changent pas) ; la traduction native
  (natif128 : trois lectures, l'indice comparé ; hors du tableau, Lugus rejoue l'instruction et dit l'erreur) ;
  Gobannos (le piège dit la ligne) ; le juge du lecteur (LDT lit, STT écrit), sa référence, les frontières et la
  vibration des molécules.
- **Mesuré** : la boucle de l'épreuve (cent tours d'un tableau de 1000 cases) prend 716 314 instructions, toutes
  vérifiées ; 1 115 214 sans aucune vérification (l'ancienne lecture, six instructions) ; 3 640 214 avec `__borne`.
  Le duel : 39,8 millions (45,2 sans vérification, 69,6 avec `__borne`). **La sûreté est plus rapide que son
  absence** : une instruction fait le travail de six.
- **L'épissage d'hier (§75 ter) n'a plus rien à retirer** : retirer la vérification ramènerait la lecture en six
  instructions. L'épissage sûr, `__SANS_BORNES` et l'épissage rapide sont éteints (`LDT_STT` dans les quatre
  compilateurs) ; `lugus PROG.adn --rapide` le dit et lance le programme ; `lugus eprouver` note toujours l'épreuve
  (pour d'autres introns à venir).
- **Ogmios, les vagues** : poser une case dans la colonne d'une vague écrit sa ligne à la place de cette vague (avant
  la première case d'une vague plus tardive) ; glisser une case vers une autre colonne y déplace sa ligne. Les
  liaisons décident toujours de la vague (une case réagit dès que ses entrées sont là) : la paillasse le dit quand
  la case ne peut pas suivre (« elle attend une liaison de la vague N »). L'ordre compte vraiment pour les ponts.
- **Ogmios, les pages** : « Nouvelle page » au clic droit (geste `page`) crée `reaction page_N(entree) -> fin` et la
  montre. La case **suite** (Ne) : la fin qui renvoie à la page suivante (créée s'il n'y en a pas) : `= page_2(_) ->
  r`, ou `= sortie(page_2(_))` ; toute case qui appelle une autre page porte le néon et le nom de la page (« vers
  page_2 ») ; un double clic sur elle ouvre la page.

### 76 bis. La paillasse fait l'ordre du texte ; appeler une page, le retour (22 novembre, 0.70b)

**Demandé par le créateur le 22** : la position verticale dans la paillasse définit la ligne, le passage d'une vague à
l'autre aussi ; la case ne doit pas « attendre une liaison » pour être placée ; la case retour (une page comme
sous-programme).

- Après chaque déplacement, les lignes des cases sont réécrites dans l'ordre de leurs places : colonne par colonne,
  de gauche à droite, puis de haut en bas (`ordonner_lignes`). La case reste où on l'a posée. Si elle reçoit une
  valeur d'une vague plus tardive, la paillasse le dit seulement (« elle calculera quand la valeur arrivera ») : une
  case ne peut pas calculer avant l'arrivée de sa valeur, comme un réactif.
- **appeler** (Ne) : `= page_2(_) -> lK` : la page suivante comme sous-programme, son résultat revient dans une liaison
  neuve. Dans la page appelée, la case qui donne le résultat porte « retour vers principal » ; un double clic y ramène.

## 77. Belenos : le val des neiges, la scène d'essai qu'on parcourt (22 novembre, 0.71)

**Demandé par le créateur le 22** : une scène de haute qualité, en 3D, dans l'esprit d'un grand jeu de montagne
nordique (un paysage original, pas une copie) : des collines de pentes variées, un plan d'eau ou une fontaine, des
flammes (la diffusion de la lumière), les ombres avec un soleil qu'on fait tourner, la neige (le dépôt de texture) ; et
surtout s'y déplacer pour vérifier le calcul en temps réel. Le cube comme tapis roulant (le temps), l'anti-cube pour
les reflets, l'ombre pour les ombres.

- **Premier pas** (`belenos/val.vtx`, `vtx toile128 belenos/val.vtx`) : un relief de 512 × 512 (cinq octaves de bruit,
  les vallées aplanies, les monts au carré), la roche sur les pentes fortes, la neige en haut et sur les replats déjà
  hauts, la lande, l'herbe ; un rayon par colonne d'image, du plus près au plus loin (le tampon de hauteur), la brume du
  loin ; les flèches pour marcher et tourner, a et q pour monter et descendre. Tout en entiers ; les mêmes mots par les
  deux compilateurs. Mesuré ici (un cœur) : 146 ms l'image en 480 × 270 (7 images par seconde), 3,4 s pour créer le
  relief.
- **La suite prévue** : le soleil qu'on fait tourner et les ombres (l'ombre du relief projetée depuis le soleil) ; le
  lac et ses reflets (l'anti-cube) ; l'eau et les nuages qui avancent (le tapis roulant) ; la neige qui tombe et se
  dépose ; un feu (la lumière diffusée, qui vacille) ; une fontaine ; puis la forge et les cylindres (plusieurs cœurs),
  puis Taranis (la carte) pour la haute définition en temps réel ; les objets fins viendront de Gobatix.

## 78. Le soleil, les ombres, et la scène face au C (22 novembre, 0.72)

**Demandé par le créateur le 22** : tester, ajuster, fiabiliser, et montrer toute la performance de Vercintorix face
à d'autres modèles graphiques.

- **Le soleil et les ombres** (`belenos/val.vtx`) : o / p tournent le soleil, i / k le montent et le descendent. La
  lumière suit la pente face au soleil (la normale du relief) ; l'ombre portée remonte vers le soleil sur 17 distances
  (serrées près, espacées loin), avec une pénombre (un soleil n'est pas un point) ; la lumière s'orange au ras de
  l'horizon, le ciel aussi ; le disque du soleil dans le champ. Quand le soleil bouge, la grille est éclairée de nouveau
  par bandes de 16 lignes, une bande par image : le tapis roulant, chaque image ne paie que sa part. Le compteur dans
  l'image (ms par image, la place du soleil). Les rayures claires sur la neige venaient d'un grain qui dépassait 255 :
  corrigé (borné).
- **La scène en trois fichiers** : `val_scene.vtx` (le relief, la lumière, le rendu, sans programme principal),
  `val.vtx` (la marche, au clavier), `val_banc.vtx` (le banc : sans fenêtre, toujours le même passage, 12 images, le
  soleil qui tourne, puis l'**empreinte** de la dernière image, FNV-1a sur ses 129 600 points). Le sinus est en entiers
  (Bhaskara, à 0,2 % près) : les mêmes nombres partout, aucun arrondi de flottant ne peut différer d'une machine ou
  d'un langage à l'autre.
- **La référence en C** (`val_ref.c`) : le même calcul, ligne pour ligne, en C (mots de 64 bits, les opérations signées
  par conversion). Elle donne **la même empreinte** que vtx (en -O2 comme en -O0) : la même image au point près. On
  compare donc des temps à travail identique.
- **Ce que la comparaison a trouvé** : en x86 traduit, l'éclairage coûtait 68 fois le C. Le profil (`VTX_PROFIL=1`) :
  12 millions de divisions signées (`./`, code #1A) n'étaient pas traduites ; chacune sortait du code x86, se faisait
  rejouer par Lugus, et vidait le cache des pages, d'où 29 millions de lectures lentes derrière elles. **Traduites**
  (division et reste signés, à la largeur 64 : par zéro, tout à un ou le dividende ; le plus petit par −1, lui-même et
  un reste nul, comme Lugus) ; vérifiées contre Lugus sur les cas de bord (`tests/test_natif128.py`, « signes »).
- **`toile128` traduit aussi en x86** (comme les .exe ; `VTX_INTERPRETE=1` garde Lugus seul) : les 46 images du
  scénario du soleil en 3,5 s au lieu de 16,4.
- **Mesuré ici (un cœur, 480 × 270, machine partagée : ±20 %)** :

  | | préparer (relief, 512 lignes éclairées) | une image complète | dont le rendu seul |
  |---|---|---|---|
  | C, gcc -O2 | 62 ms | 2,3 ms | 1,7 ms |
  | vtx traduit en x86 (0.72) | 0,65 s | 22 à 28 ms | 15 ms |
  | vtx traduit (0.71, avant #1A) | | ~50 ms | |
  | Lugus seul (l'interprète) | 5,8 s | ~105 ms (185 ms à l'horloge du banc) | |

  Vercintorix est donc à **environ 10 fois le C** sur cette scène, 35 à 45 images par seconde. L'écart vient surtout de
  la traduction : les registres de la machine restent en mémoire (pas dans ceux du processeur), chaque instruction
  compte son pas, et chaque petite fonction (sin1024, hauteur_en, embrume, rgb) est un vrai appel. Les trois pistes,
  par gain attendu : garder les registres dans ceux du processeur ; déplier les petites fonctions à la compilation (dans
  les deux compilateurs) ; puis les cylindres (une bande d'image par cœur).
- **L'épreuve d'Alésia** a un chapitre VIII, « Voir » : le banc traduit rend l'empreinte attendue, le C aussi (si un
  compilateur C est là), et `val.vtx` se parcourt sans fenêtre (9 images). 59 vérifications.

## 79. La paillasse en grille ; la fenêtre d'édition ; la scène face aux outils (22 novembre, 0.73)

**Demandé par le créateur le 22** : les cases, une fois posées, ne changeaient pas la ligne du code qu'elles écrivent,
et leur déplacement n'était « pas génial » ; éditer une case dans une petite fenêtre (et non dans son en-tête), pour
choisir entre autres le nombre de ses connexions ; « pratique et intuitif ».

- **Ce qui n'allait pas** : la case se posait au point près, par-dessus ses voisines, sans se ranger ; on ne voyait ni
  où elle tomberait ni quelle ligne elle prendrait.
- **La grille aimantée** : chaque vague est une colonne ; les cases s'y empilent dans l'ordre de leurs lignes. Pendant
  le glissement, les autres cases s'écartent, un cadre en pointillés montre la place, et une étiquette dit « ici :
  vague V, ligne L » ; une colonne libre attend au bout. Lâchée, la case tombe dans la place et le texte prend l'ordre
  des colonnes, puis des rangs. La colonne choisie est gardée (`PROG.paillasse`, « réaction|clé|V|-1 ») ; les anciennes
  places au point près sont oubliées. Une case posée plus tard que sa vague le dit (« elle pourrait réagir dès la vague
  1 ») ; posée plus tôt que ce qu'elle lit : « elle calculera quand la valeur arrivera ». Une case neuve (le menu du
  clic droit, le double clic) va dans la colonne où l'on a cliqué.
- **La fenêtre d'édition** (clic droit sur une case, ou double clic sur son en-tête ; aussi à chaque case posée) : le
  nom de la case, ce qu'elle fait, **le nombre de ses entrées et de ses sorties** (− et +) et leurs noms ; la ligne de
  code qui en sortira, en bas ; ce qui ne va pas (un nom qui n'en est pas un, une liaison donnée deux fois). Une entrée de
  plus : un argument `_` de plus à l'appel qui finit la case (`fusion(a, b, _)`), sinon la dernière opération écrite
  (`a + b + _`) ; une de moins : la dernière, avec ce qui la sépare. Une sortie renommée l'est aussi là où on la lisait.
  Tab passe au champ suivant, Entrée écrit, Échap renonce. Dans Ogmios, le clavier va à la fenêtre tant qu'elle est
  ouverte.
- **Vérifié** : `tests/test_paillasse.py` et `tests/test_ogmios.py` conformes (trois tests de l'ancienne boîte et des
  places au point près réécrits) ; l'épreuve d'Alésia, 60 vérifications (la fenêtre d'édition ajoutée au chapitre I) ;
  Ogmios compile (`cargo check --features verif_fenetre --bin ogmios`). L'exemple `exemples128/calcul_vagues.vtx`.

**La scène face aux outils (la question du créateur : « tout a été fait avec vtx ? les cubes ont servi ? »)** :
la scène est écrite en vtx, compilée par les deux compilateurs, jouée par Lugus, traduite, forgée ; mais elle ne range
rien dans un cube sur disque (ni anti-cube, ni ombre), ne reprend ni le fluide ni le tableau d'Auvergne de Belenos, et
son « tapis roulant » n'était qu'une lumière refaite par bandes. **La forge** (vtx → Rust → code machine) donne la même
image en 5,7 ms (2,5 × le C, au lieu de 10). **Les cylindres** : les colonnes du rendu et les lignes de la lumière sont
en segments (`val_scene.vtx`) ; l'image reste la même, mais **sur 2 cœurs c'est 3 fois plus lent** (15 ms) : chaque
cylindre recopie les pages qu'il écrit (l'écran : environ 2 Mo par image) et chaque lecture qui manque son petit cache
(16 cases pour une dizaine de pages vives) passe par une table de hachage. À réparer dans `forge/noyau_forge128.rs`.
`essai-0.73.bat` mesure la scène forgée sur 1, 2 et 4 cœurs chez le créateur.

**La suite décidée** : la lumière dans le rouleau (l'idée du créateur : la lumière entrelacée avec la matière dans le
tapis roulant, comme le fluide : la propagation gratuite, la collision par la matière du cube), d'abord en 2D (une coupe
du val, un feu, le soleil) ; l'ombre du cube pour le soleil direct ; le cube des matières ; la neige qui se dépose par
un tapis vertical ; l'eau par le fluide ; le reflet par un miroir segmenté ; puis Taranis.

### 79 bis. Les cylindres de la forge réparés (22 novembre, 0.74)

**Mesuré chez le créateur (0.73)** : la scène forgée, 5,75 ms par image sur 1 cœur, 16,66 sur 2, 13,33 sur 4. « Ce
n'est pas bon. »

- **Le profil** (callgrind) : près de 60 % du temps des cylindres dans le hachage. À chaque lecture qui manquait le
  petit cache des pages (16 cases, pour une dizaine de pages vives), le cylindre rangeait la page dans deux tables
  hachées par SipHash (le hachage de Rust fait contre les attaques). **Réparé** : un cache de 64 cases, mieux mêlé ; un
  hachage rapide pour les tables des cylindres ; chaque page n'est cherchée et notée qu'une fois (`vues`). Le cache
  plus grand profite aussi à un seul cœur : **3,7 ms par image au lieu de 5,7 (1,6 × le C)**.
- **Le déséquilibre** : les segments allaient par blocs contigus ; le premier cœur avait la moitié gauche de l'image
  (2,7 ms de travail), le second la droite (0,7 ms), et chacun attendait le plus lent. **Les segments vont maintenant en
  alternance** (0, n, 2n… au premier cylindre ; 1, n + 1… au second) : 1,7 ms chacun. L'ordre des cylindres n'étant plus
  celui des segments, la fusion devient stricte : un cylindre qui a lu une page qu'un autre écrivait, ou deux cylindres
  qui ont écrit le même mot de deux valeurs (un mot variable), et rien n'est posé : les segments sont rejoués dans
  l'ordre. Le résultat reste toujours celui de Lugus (`tests/test_cylindres.py`, la forge : 103 programmes conformes).
- **Moins de mémoire remuée** : la copie d'une page écrite est posée telle quelle (plus de page remise à zéro puis
  recopiée) ; plus de page de zéros pour comparer ; les pages fondues sont posées sans recopie.
- **Ce qui reste** : chaque cylindre recopie encore la page entière (1 Mo) qu'il écrit, et la fusion la compare ; sur
  une image de 480 × 270 en 3,7 ms, c'est une part sensible. La machine de travail n'a que deux cœurs partagés : la
  mesure qui compte est celle du créateur (`essai-0.74.bat`, 1, 2, 4 cœurs et tous).
- **La carte graphique n'a pas servi** : `VTX_TARANIS=1` dit pourquoi. Le noyau de Taranis n'accepte que des lectures
  dont l'adresse se calcule depuis l'indice de la boucle (la fenêtre de l'étage 2) ; le rendu lit le relief là où le
  rayon arrive (une adresse qui dépend du calcul), la lumière lit et écrit dans une fonction appelée, et l'image est à
  l'étage 1. À étendre (la suite).

### 79 ter. Les cylindres, la suite : la copie par blocs (22 novembre, 0.75)

**Mesuré chez le créateur (0.74)** : 3,58 ms par image sur 1 cœur ; 8,58 sur 2 ; 10,00 sur 4 ; 18,08 sur 24. Le
détail sur 4 cœurs : 2 à 4 ms dans les fils et 1,3 à 2,7 ms de fusion à chaque passage. La réparation de la 0.74
avait ôté le hachage et le déséquilibre, pas le vrai poids.

- **La copie par blocs** : un cylindre ne recopiait pas une page qu'il écrit (un mégaoctet : 65 536 mots de 16 octets),
  il la recopiait entière ; la fusion la comparait entière. Maintenant, une page écrite est une **feuille ouverte bloc
  par bloc** (64 mots) : au premier mot écrit dans un bloc, ce bloc seul est recopié du cube commun ; le cylindre rend
  ses blocs ouverts (ceux qui ont vraiment changé), et la fusion ne regarde qu'eux, répartie sur tous les cœurs par
  tranches. La fusion de la lumière passe de 1,3 ms à 0,1 ms.
- **Les réserves** : les machines des cylindres (2 Mo remis à zéro, le code et la pile, à chaque passage et dans
  chaque fil) et les pages des feuilles servent d'un passage à l'autre.
- **Les variables dans les registres** : capturées par le fil, les variables du programme vivaient dans la mémoire de
  la fermeture : cinq fois plus d'écritures en mémoire (cachegrind : 13 millions contre 2,4) ; un cylindre seul
  rendait l'image en 7,3 ms au lieu de 2,6. Elles sont recopiées en locales au début de chaque fil : 3,2 ms.
- **Où l'on en est (2 vrais cœurs ici)** : le rendu se partage (1,7 ms par fil au lieu de 3,2), mais l'écran entier
  (129 600 mots de 16 octets, 2 Mo) se fond encore en 1 ms environ à chaque image ; à deux cœurs, on ne gagne pas
  encore. Sur 4 cœurs et plus, chez le créateur, la mesure le dira. La forge reste exacte (103 programmes, les
  cylindres).
- **Ce que ça dit** : pour une image de 3,6 ms, l'isolement des cylindres (chacun son cube, puis la fusion) coûte autant
  que le travail. Les cylindres gagnent sur les gros calculs ; pour l'image en temps réel, la carte graphique est la
  vraie voie.

## 80. Le rouleau de lumière, en 2D (22 novembre, 0.76)

**L'idée du créateur** : la lumière entrelacée avec la matière dans le tapis roulant (le rouleau), comme le fluide.

- **`belenos/rouleau_scene.vtx`** : une coupe verticale du val, 256 × 128 cellules. Le rouleau a 25 plans : la matière
  (plan 0), et la lumière de chacune des huit directions en trois couleurs. La lumière qui va dans la direction d,
  pour la cellule c, est rangée en (c + o_d) mod N ; à chaque pas, o_d recule du pas de sa direction : **la propagation
  ne déplace aucune donnée** (le tapis roulant du fluide de Belenos). **La collision, c'est la matière** : la roche,
  l'herbe, la lande et la terre renvoient ce qu'elles reçoivent dans toutes les directions, selon leur couleur ; la
  neige renvoie presque tout (et la lumière s'y enfonce un peu) ; l'eau laisse passer en bleuissant, et sa surface
  renvoie vers le haut une part de ce qui descend ; l'air en diffuse un peu (la brume, plus bleue que rouge) ; le feu
  émet en vacillant ; les bords absorbent, et le ciel y entre (le soleil dans sa direction, le bleu de partout en haut).
  Tout en entiers.
- **`belenos/rouleau.vtx`** (`vtx toile128 belenos/rouleau.vtx`) : la coupe agrandie trois fois ; o / p : le soleil
  du levant au couchant (cinq places : les directions du réseau), i / k : sa force (jusqu'à la nuit), f : le feu. On voit
  la lumière couler du ciel puis se poser : les pentes face au soleil éclairées, l'ombre portée derrière le mont, la neige
  brillante, le lac bleu, et la nuit, le seul feu qui éclaire le sol autour de lui.
- **`belenos/rouleau_banc.vtx`** : 300 pas, puis l'empreinte de l'image : la même sur Lugus et forgé ; 38 ms par pas
  traduit en x86, 5,8 ms forgé (un cœur).
- **Les limites, honnêtement** : huit directions seulement ; une source ponctuelle (le feu) rayonne en étoile à huit
  branches (l'« effet de rayons » des méthodes sur réseau) ; le soleil n'a que cinq places. La suite : seize directions
  (ou plus) ; l'ombre du cube pour le soleil direct (net, à tout angle), le rouleau pour tout le reste.
- **Les cylindres sur le rouleau** : chaque cellule n'écrit que sa propre lumière (les cellules sont en segments). La
  fusion voyait un conflit dès qu'une page était lue par l'un et écrite par l'autre (« un cylindre a lu ce qu'un autre
  écrivait : rejoué »), même à des mots différents. **Le contrôle est maintenant au mot près** : chaque cylindre note
  les mots qu'il lit (un bit par mot), et il n'y a conflit que si un autre a vraiment changé l'un d'eux. Le rouleau passe
  sans être rejoué. Mais chaque pas remue 12,6 Mo de lumière (786 432 mots de 16 octets) : les cylindres recopient puis
  fondent autant, et sur deux cœurs le pas est 2,5 fois plus lent. Le rouleau est fait pour la carte graphique.

## 81. En bandes : un seul cube, chaque cœur sa part (22 novembre, 0.77)

**Mesuré chez le créateur (0.76)** : le val forgé, 4,41 ms par image sur 1 cœur, 9,66 sur 2, 9,75 sur 4, 12,91 sur 8,
27,41 sur 24 ; le rouleau, 1,82 s sur 1 cœur, 4,87 sur 2, 3,18 sur 4. Les cylindres ne gagnent pas : chaque cœur son
cube, puis la fusion, coûte autant que le travail. **L'idée du créateur** : ne pas recréer un cube entier sur chaque
cœur, mais partager le travail du cube : chaque cœur sa part d'un étage, et les étages qui coulent l'un dans l'autre
jusqu'à l'affichage ; un cœur, le vergobret, pour la cadence et le contrôle.

- **`pour … en bandes`** (les deux compilateurs : les mêmes mots qu'`en segments` ; la promesse est notée pour la
  forge) : chaque cœur reçoit une bande et écrit directement dans le cube commun. Chacun note les mots lus et écrits ;
  une promesse non tenue arrête la machine (`tests/bandes/` : deux cœurs qui écrivent le même mot, un cœur qui lit ce
  qu'un autre écrit). Le rouleau et le val sont en bandes.
- **Mesuré ici** (deux cœurs, mémoire partagée) : le rouleau, 300 pas en 1,7 s sur 1 cœur, 1,6 à 1,8 s sur 2 (avant :
  2,5 fois plus lent sur 2) ; plus de fusion. La mémoire de la machine de travail est le frein : chez le créateur, la
  mesure dira la pente.
- **L'équipe de cœurs gardés vivants** (`equipe_jouer`) est écrite dans le noyau, mais pas branchée : avec elle, le
  compilateur Rust alourdissait tout le code de la fonction du programme, même jouée sur un seul cœur (30 %
  d'instructions de plus, vu à callgrind) ; les fils restent créés à chaque passage, le temps de trouver pourquoi.
- **La lumière, une règle physique** (question du créateur) : l'approximation de diffusion. Une lumière qui a beaucoup
  rebondi se comporte comme la chaleur : une valeur par case et par couleur (8 fois moins de mémoire que le rouleau à
  huit directions), lisse (plus d'étoile autour du feu), résolue vite sur une pyramide de cubes (256³, 128³, …, la
  méthode multigrille). Les trois voix : l'ombre (le soleil direct, net), l'anti-cube (les reflets), la diffusion (le
  ciel, les rebonds, le feu, la brume). À essayer après la chaîne des étages.
- **La suite** : la chaîne des étages et le vergobret (la cadence, l'équilibre des cœurs entre les étages, le clavier
  et la patrouille) ; puis la carte graphique.

## 82. L'image en un bloc, et l'écran à la vitesse de la forge (22 novembre, 0.78)

**Mesuré chez le créateur (0.77)** : en bandes, le rouleau passe de 1,87 s (1 cœur) à 1,40 s (4 cœurs), le val ne
gagne pas. **Demandé** : commencer par l'image ; « il faut que l'étage envoie l'info en un bloc pour apparaître à
l'écran : si on gagne du temps ici, on gagnera du temps pour tout le reste ». **L'idée du créateur pour la lumière**
(à faire ensuite) : la lumière quaternaire, vrai (vu par la source), faux (caché), variable (les deux : la pénombre,
le halo, le reflet), inconnu (pas atteint), dégressive depuis la source et depuis le point occupé le plus proche de la
source ; tous les points hex à la fois (l'inondation par sauts) ; l'ordre : l'anti-cube, l'ombre, la lumière.

- **`presenter()` lisait l'écran point par point** : une recherche de page par point, 4,2 ms par image de 480 × 270 rien
  que pour la préparer (autant que tout le rendu du val). **L'étage de l'écran part maintenant en un bloc**, page par
  page (`page_vue`, Lugus et Dunon) : 0,18 ms (23 fois plus vite) ; les images sont les mêmes au point près.
- **La fenêtre faisait tourner la version traduite en x86** (28 à 35 ms par image du val), alors que la forge en fait 3
  à 4. **La forge présente maintenant elle-même ses images** : la fenêtre (`sortie.rs`, et `gif.rs`) est recopiée dans
  le programme forgé, `presenter()` y envoie l'étage de l'écran en un bloc ; `VTX_IMAGES=DOSSIER` écrit les images en
  PNG, `VTX_SCENARIO=FICHIER` rejoue des touches (comme `vtx toile128`). Le val forgé rend les mêmes 46 images que la
  fenêtre traduite ; 201 images en 0,93 s (préparation comprise) contre 7,7 s : **8 fois plus vite à l'écran**. La
  fenêtre limite à 60 images par seconde (la cadence).
- **Chaque point de l'écran écrit une fois** (`val_scene.vtx`) : chaque colonne peint son relief, puis son ciel
  au-dessus (une table des couleurs du ciel) et le soleil là où il se voit ; avant, tout le ciel d'abord, puis le relief
  par-dessus. La même empreinte.

## 83. L'ombre quaternaire (22 novembre, 0.79)

**Demandé par le créateur** : l'ombre en quaternaire aussi, avec l'ombre du cube : la densité de l'ombre projetée, et
une diffusion variable.

- **Par balayage** (`eclairer_lignes`, `val_scene.vtx` ; le même calcul en C dans `val_ref.c`) : la lumière parcourt le
  relief en lignes parallèles, dans la direction où elle va ; chaque ligne porte son horizon (le relief le plus haut
  déjà rencontré, qui descend de la pente du soleil à chaque pas) et la distance au point qui fait l'ombre. Chaque case
  reçoit son état : **vrai** (au-dessus de l'horizon), **faux** (sous l'horizon au-delà de la pénombre, ou tournée à
  l'opposé du soleil), **variable** (dans la pénombre, avec sa densité ; la pénombre s'élargit avec la distance au point
  qui fait l'ombre : nette au pied d'un rocher, floue loin derrière), **inconnu** (une ligne pas encore refaite depuis
  que le soleil a bougé). Chaque case est vue deux fois (un tour pour l'horizon, un tour pour l'écrire) ; les lignes ne
  se touchent pas : elles vont en bandes. L'état de chaque case est gardé (`ETAT`), et compté par ligne (`COMPTE`).
- **Plus juste** : l'ancienne recherche (dix-sept sondages vers le soleil, jusqu'à 200 cases) coupait les longues
  ombres des grands sommets ; le balayage les suit jusqu'au bout (vu de dessus : les mêmes ombres, et la longue ombre
  effilée d'un sommet au-delà de 200 cases).
- **La fenêtre** (`val.vtx`) dit, sous le compteur, la part de chaque état : au départ, vrai 34 %, faux 62 %, variable
  2 %, inconnu 0 % ; quand le soleil bouge, inconnu monte, puis redescend à mesure que le tapis refait les lignes.
- **Les pentes gardées** : la normale de chaque case est calculée une fois (le relief ne bouge pas) ; l'éclairage d'une
  case n'est plus qu'un produit et une division.
- **Honnêtement** : ni le balayage ni les pentes gardées n'accélèrent l'image forgée (l'ancienne recherche s'arrêtait
  vite dans l'ombre pleine) ; ce qui coûte, c'est le tracé des rayons de l'image. Le C : 2,2 ms par image ; la même
  empreinte (-2697648536993976745).

## 84. L'ombre et la lumière ensemble, et les sources diverses (22 novembre, 0.801)

**Demandé par le créateur** : que l'ombre et la lumière fonctionnent ensemble ; la variable se ferait naturellement,
comme les niveaux de gris du cube, mais dans l'ombre du cube : plutôt qu'un point qui va jusqu'au noir ou jusqu'à la
lumière, la lumière jusqu'au noir. Penser aux sources de lumière diverses, et faire le reste.

- **Une seule lumière par case, de 256 au noir** (`eclairer_lignes`, `val_scene.vtx` ; le même calcul en C), faite de
  plusieurs sources : le **soleil** direct (la pente face à lui, adoucie par la pénombre de 0.79) ; le **ciel**, selon
  l'heure (bleuté de jour, faible la nuit) et selon l'**ouverture** de la case (`preparer_ouverture`, une fois : dans
  huit directions, la plus haute pente vers le relief à 3, 6, 12 et 24 cases ; le ciel caché par une pente de tangente
  t est t² / (1 + t²)) ; le **renvoi** du sol éclairé (sa couleur sous le soleil, à moitié), porté le long de la ligne
  dans les deux sens et qui baisse à chaque pas (230 / 256) : l'ombre est claire près de son bord, sombre loin dedans ;
  les **feux** ; la nuit, la **lune**.
- **L'aller et le retour** : à l'aller, l'horizon, la lumière directe, ce que chaque case renvoie et le renvoi venu de
  l'avant sont notés dans le **carnet de la ligne** (576 cases : la ligne et 64 de marge, pour que le retour parte déjà
  chargé) ; au retour, le renvoi venu de l'arrière et la lumière de chaque case. Chaque ligne n'écrit que son carnet et
  ses cases : les lignes vont toujours en bandes, et la promesse tient (la forge sur 1 et 4 cœurs, la même empreinte).
- **L'état vient de la lumière reçue** : **vrai**, une source la touche en plein (le coin blanc du cube) ; **faux**,
  presque rien n'arrive, moins de 24 sur 256 en moyenne (le coin noir) ; **variable**, tout le gris entre les deux :
  l'ombre éclairée par le ciel et les renvois, à la fois dans l'ombre et dans la lumière (Belnap) ; **inconnu**, pas
  encore refait. De jour, au départ : vrai 35 %, faux 0 %, variable 64 % (en 0.79 : faux 62 %). La nuit, feux allumés,
  sous la lune : vrai 17 %, faux 76 %, variable 5 %. Faux n'est plus « dans l'ombre » mais « dans le noir ».
- **Les feux** (`preparer_feux`, `eclairer_feux`, une fois : le relief et les feux ne bougent pas) : huit feux dans
  les creux et les replats bas, loin les uns des autres, choisis par la hache ; trois sortes (le feu de camp, la forge,
  la lanterne). Pour chaque case à moins de 40 cases : la valeur dégressive depuis le feu (nulle à 40 cases), la ligne
  de vue depuis la flamme (sa plus grande marge sous le relief, en quaternaire : passe, coupée, ou la pénombre entre
  les deux : les feux ont leur ombre) et la pente face au feu. Le foyer lui-même est une flamme. `f` les allume et les
  éteint.
- **La lune** : sous l'horizon, le soleil passe la main à la lune, à l'opposé, aussi haute que le soleil est bas, faible
  et bleutée ; son ombre vient du même balayage. Le ciel et la brume s'assombrissent ; le disque de la lune se voit.
  `k` descend le soleil jusqu'à −24° ; `n` passe du jour à la nuit d'un coup.
- **Ce que ça coûte** : la préparation, une fois, de 73 à 130 ms (en C) ; par image, le C ne bouge pas (2,3 ms), la
  forge passe de 3,7 à 4,4 ms (les 16 lignes refaites par image font deux tours au lieu d'un). La même empreinte
  partout : 4817037499302952394.
- **Les limites, honnêtement** : le renvoi ne suit que la direction du soleil (la lumière qui entre dans l'ombre par le
  côté n'est pas vue, et on devine de légères traînées le long des lignes) : l'inondation par sauts le rendra égal dans
  toutes les directions, et ce sera le début de l'anti-cube (les reflets). Les feux ne renvoient pas de lumière, et ne
  vacillent pas encore. La trame en damier sur la roche et la neige vient des marches du relief (elle était là avant).

## 85. Le renvoi par la pyramide de cubes (22 novembre, 0.802)

**La suite demandée par le créateur.** En 0.801, le renvoi (la lumière que le sol éclairé renvoie dans l'ombre) suivait
les lignes du soleil, dans les deux sens : la lumière qui entre par le côté n'était pas vue, et on devinait des
traînées le long des lignes.

- **Pourquoi pas l'inondation par sauts** : elle trouve, pour chaque case, le point éclairé *le plus proche* ; or une
  case dans l'ombre reçoit la lumière renvoyée par *tout* ce qui l'entoure : une somme, pas un plus proche voisin. Le
  bon outil est la **pyramide de cubes** (la diffusion, l'idée déjà notée au §81). L'inondation par sauts est gardée
  pour les reflets de l'anti-cube, où c'est bien le point le plus proche qui compte.
- **La pyramide** (`construire_pyramide`, `val_scene.vtx` ; la même en C) : chaque case note ce qu'elle renvoie (sa
  couleur sous les sources : l'astre et les feux, sans le ciel ni le renvoi : un seul rebond) dans `SRC` ; quatre
  niveaux en sont tirés, des sommes de 2 × 2, 4 × 4, 8 × 8 et 16 × 16 cases. Les trois voies tiennent chacune dans 16
  bits d'un même mot (au plus 255 × 256) : chaque niveau n'est qu'une addition de quatre mots, sans rien défaire.
  Chaque niveau va en bandes.
- **La lecture** (`lire_niveau`) : chaque case lit les quatre niveaux autour d'elle, en mêlant les quatre blocs voisins
  (bilinéaire, sur le tore) ; les plus proches comptent plus (96, 80, 64, 64 sur 256). Le renvoi arrive par la part du
  ciel que le relief cache : `128 + 2 × (256 − ouverture)` sur 256 (une case à découvert n'en reçoit guère ; un creux ou
  le pied d'une paroi, beaucoup). Il vient de toutes les directions : plus de traînées dues au renvoi ; l'ombre reste
  claire près de son bord et sombre au fond, en plus doux.
- **Les feux renvoient** : leur lumière entre dans `SRC`, leurs halos s'élargissent sur le sol et les parois.
- **Le tapis à deux tours** (`val.vtx`) : chaque bande lit la pyramide faite avant elle. Quand la lumière saute (`n`,
  `f`), le tapis fait un premier tour (ce que chaque case renvoie), puis la pyramide, puis un second tour qui la lit
  (sans lui, la nuit gardait le renvoi du jour). Quand le soleil tourne, la pyramide est refaite toutes les quatre bandes.
- **Le balayage redevient un seul tour** (plus de carnet par ligne) : l'horizon, la lumière directe, et la composition
  de la case dans le même pas.
- **Ce que ça coûte** : en C, 2,6 ms par image (le banc refait la pyramide à chaque image) ; la forge, de 4,4 à environ
  6 ms par image quand le soleil bouge ; rien de plus quand il est immobile. La même empreinte partout :
  -3681145075876775514.
- **Les limites** : le renvoi ne regarde pas si le relief le coupe entre la source et la case (il passe les crêtes) ;
  les traînées en éventail qui restent dans les grandes ombres viennent de la pénombre du balayage (chaque ligne a son
  horizon), pas du renvoi.

## 86. La lumière instantanée : trois étages dans la même image (22 novembre, 0.803)

**Vu par le créateur** : un changement de lumière balaie encore l'écran, alors qu'il doit être instantané ; l'étage en
un bloc s'applique-t-il mal ?

- **L'étage en un bloc n'y était pour rien** : l'image part bien à l'écran d'un seul bloc. Ce qui balayait, c'était le
  **calcul** de la lumière, étalé exprès sur le tapis (16 lignes par image : un changement mettait 32 images, 64 avec
  les deux tours de la 0.802, à traverser l'écran). C'était un choix, pas une panne ; il ne convenait pas.
- **Toute la lumière dans l'image où elle change**, en trois étages qui se suivent, chacun en bandes sur les cœurs
  (`eclairer_tout`, `val_scene.vtx` ; la même chose en C) :
  1. **le balayage** (`eclairer_lignes`) : l'ombre du cube et la lumière des sources reçue par chaque case (l'astre, les
     feux), notée dans `LUM` (et deux drapeaux : une source en plein, un foyer). Il ne lit plus que trois mots par case
     (la hauteur ; la pente, **en un seul mot** `NORM` au lieu de trois ; les feux) et n'en écrit qu'un ;
  2. **la pyramide, montée puis redescendue** (`construire_pyramide`) : en montant, ce que chaque case renvoie
     (`renvoye`, calculé ici, dans l'ordre de la mémoire) sommé par blocs de 2, 4, 8, 16 ; en redescendant
     (`descendre`), chaque niveau reçoit celui d'au-dessus, mêlé, plus sa propre moyenne pondérée : `RV1` (256 × 256)
     dit le renvoi autour de chaque bloc de 2 × 2 cases ;
  3. **la composition** (`composer`), rangée par rangée, dans l'ordre de la mémoire : le ciel selon l'ouverture, les
     sources, le renvoi (`RV1` mêlé autour de la case), la couleur, l'état, le compte de chaque rangée.
- **Plus de tapis, plus de second tour** : tout est cohérent dans l'image même. L'image qui suit `n` est déjà toute de
  nuit ; celle qui suit `f`, déjà sans feux. Le compteur « inconnu » reste à 0 : rien n'attend plus d'être refait.
- **Ce que ça coûte** (toute la lumière refaite, plus l'image) : en C, sur un cœur, 13,9 ms (le balayage 9,7, la
  pyramide 1,7, la composition 3,1) ; forgé, 35 ms sur un cœur, **22 ms sur deux** (les trois étages se partagent bien
  entre les cœurs). Quand la lumière ne change pas, rien de plus (l'image seule, 3 à 4 ms). Le banc refait désormais
  toute la lumière à chaque image : il mesure ce que coûte un changement instantané. La même empreinte partout :
  7510702145557097999.
- **Une erreur trouvée en route** : l'adresse de `NORM` recouvrait la table des feux (en C, les tableaux sont séparés :
  l'empreinte du C est restée juste, celle de vtx a changé ; c'est l'accord des deux qui l'a montré).
- **Ce qui reste cher** : le balayage, quand le soleil vient du nord ou du sud, avance d'une rangée à chaque pas (un
  saut de 512 mots) ; et la moitié de ses pas ne sert qu'à porter l'horizon.

## 87. La lumière en calque (22 novembre, 0.804)

**Le créateur** (après son essai de la 0.803 : 31 ms par image sur un cœur, 42 ms sur tous) : avec l'ombre du cube, le
résultat devrait être bien meilleur ; tout est refait, alors que l'idée serait d'apposer un calque (la luminance et
l'ombre) sur la texture déjà établie à la conception du décor. Et le paysage fait par le cube donnerait une surface plus
simple pour les couleurs, l'ombre, la lumière et les reflets (décidé : plus tard, et seulement avec les points des
surfaces, voxels ou polygones).

- **Le calque** (`val_scene.vtx` ; la même chose en C) : le décor fixe se prépare une fois (la couleur propre,
  l'ouverture au ciel, la lumière des feux, et désormais ce que les feux renvoient : `FEUR`). Quand l'astre bouge, on
  ne refait que **le calque d'ombre** (`OMBRE` : pour chaque case, la lumière de l'astre qu'elle reçoit et son état
  quaternaire) et la pyramide du renvoi. La couleur finale est posée **au moment de peindre** (`teinte`), seulement sur
  les cases que l'œil voit ; il n'y a plus de composition de tout le relief.
- **Le balayage sans division** : la normale unitaire est gardée en un mot (`NUNIT`, sur 4096) : la pente face à
  l'astre n'est plus qu'un produit ; la pénombre se lit dans une table (`INVW`). Il lit au plus deux mots par case et
  en écrit un.
- **Moins de cœurs lancés** : sur la machine du créateur, lancer et rassembler les cœurs coûtait plus que le travail ;
  seuls le balayage et les colonnes de l'image restent en bandes ; la pyramide (petite) va sur un seul cœur.
- **Le compteur** dit désormais l'état du calque d'ombre (vrai : l'astre en plein ; variable : la pénombre ; faux : à
  l'ombre) ; le dégradé jusqu'au noir se fait en posant le calque.
- **Mesures** (toute la lumière refaite à chaque image, plus l'image) : en C, 10,4 ms (18,9 en 0.803) : le calque
  d'ombre 7,0 ms, la pyramide 2,4 ms ; l'image seule, calque posé, 2,25 ms (1,3 ms quand la couleur était gardée : le
  prix du calque à chaque image). Forgé, ici : 27,5 ms sur un cœur (35 en 0.803), 19 à 24 ms sur deux. La forge gagne
  moins que le C : ses mots ont 128 bits (deux fois plus de mémoire remuée) et chaque lecture passe par la recherche de
  sa page. Empreinte : 4981707699916968273.

## 88. Le vergobret, premier pas : la carte des pages (22 novembre, 0.805)

**Le créateur** (après la 0.804, chez lui : 20,4 ms par image sur un cœur, 17,6 sur tous) : c'est mieux, mais pas assez
quand la lumière change ; chercher la page, un cœur devait s'en charger : ne fait-il pas son travail ? Les mots de 128
bits restent (Lugus, et le plus de hex possible).

- **Le constat** : ce cœur, le vergobret, décidé en 0.77, n'avait jamais été construit. Mesuré (callgrind, le banc forgé
  sur un cœur) : **42 % des instructions** servaient à trouver la page du mot lu ou écrit (décoder l'adresse, son étage,
  hacher la page, comparer avec le petit cache de 64 pages, marquer le mot lu).
- **La carte du vergobret** (`forge/noyau_forge128.rs` : `Carte`, `lire2`, `ecrire2`) : pour chaque page de l'étage 2
  (là où vivent les données d'un programme), le pointeur sur son premier mot, pour lire et pour écrire ; en bandes, les
  mots lus et écrits (la promesse, toujours vérifiée au mot près). Lire un mot de l'étage 2 n'est plus que : numéro de
  page, pointeur, mot. Une page entre dans la carte à sa première lecture ou écriture ; la carte est oubliée avec le
  petit cache (après une fusion de cylindres, un brin posé, un service qui touche aux pages). Les cylindres en
  segments gardent leur chemin (leurs feuilles). La forge écrit `c.lire2` / `c.ecrire2` pour tout `@2[…]`.
- **Mesures** (le banc du val, toute la lumière refaite à chaque image) : sur un cœur, **de 27,5 à 19 ms** par image ;
  sur deux, de 19-24 à 14 ms. L'accès à la mémoire passe de 42 % à environ 18 % des instructions. La même empreinte ;
  la forge conforme (103 programmes : mêmes sorties, même mémoire que Lugus) ; les cylindres et les bandes conformes.
- **La promesse gardée** : sans marquer les mots lus, on gagnerait environ 1 ms (dans le bruit) : ce n'est pas assez
  pour renoncer à la vérification.
- **La suite du vergobret** : l'équipe de cœurs qui reste en place (les cœurs sont encore lancés à chaque boucle en
  bandes) ; les deux calques, posés d'un bloc.
- **Deux idées du créateur, notées pour la suite** :
  - *Un cœur entre deux étages* : puisqu'un cœur se charge d'un étage, un cœur placé entre deux étages ferait la
    lumière et l'ombre (le calque d'ombre calculé au passage, entre l'étage du décor et celui de l'affichage) ; les
    deux calques sont à penser avec les étages.
  - *La clepsydre* (plutôt qu'une pyramide) : autour d'un point de surface, quatre points au-dessus, vers la source de
    lumière, et quatre points en dessous, pour la projection de l'ombre : deux cônes opposés par la pointe, le point
    de surface au milieu.

## 89. Le vergobret : l'équipe de cœurs, le travail en morceaux (23 novembre, 0.806)

**Mesuré chez le créateur** (`mesure-0.805.bat`, le banc sur 1 à 16 cœurs) : 16,3 ms sur un cœur, 17,5 sur deux (plus
lent), 13,6 sur quatre, puis plus rien ; la boucle n'était coupée qu'en 12 morceaux, fixés à la compilation ; la
vérification de la promesse prenait 1,1 ms par boucle (les cœurs comparés deux à deux). **La règle du créateur** : le
langage doit marcher et s'optimiser sur toutes sortes de processeurs : rien n'est réglé pour une machine.

- **Le travail en morceaux, à l'exécution** (`forge128.py` : `equipe_en_morceaux`) : une boucle « en bandes » (les
  segments d'une même boucle) est coupée quand elle se joue, en quatre morceaux par cœur, alignés sur son pas ; un
  compteur partagé les distribue : chaque cœur libre prend le suivant. Le nombre de cœurs est celui que le système
  donne (`VTX_COEURS` pour le forcer) ; plus de limite à 12. Une colonne de ciel ne retarde plus une colonne de
  montagne.
- **L'équipe du vergobret** (`equipe_jouer`, écrite en 0.77) : les cœurs sont créés une fois et gardés vivants ; chaque
  boucle leur donne sa tâche et attend qu'ils l'aient finie. Le coût de lancer un cœur, qui change d'un système à
  l'autre, ne compte plus. L'alourdissement vu en 0.77 (30 % d'instructions en plus, même sur un cœur) venait des
  variables prises par la tâche sans être copiées : copiées dans la tâche, la fonction jouée sur un seul cœur garde les
  siennes dans les registres. Une boucle en bandes dans une tâche (un cœur de l'équipe) se joue sur ce cœur.
- **La promesse en un seul passage** (`bandes_touchees`) : pour chaque page, les mots écrits par au moins un cœur, par
  au moins deux, et lus par un cœur qui ne les a pas écrits ; la promesse est rompue là où un mot est écrit deux fois,
  ou écrit par l'un et lu par un autre. Le même verdict qu'avant, en un temps qui croît comme le nombre de cœurs, et
  non plus comme son carré.
- **La pyramide sur l'équipe** (`val_scene.vtx`) : son premier niveau et sa redescente vont en bandes.
- **Mesures, ici (deux cœurs)** : le banc de 14 à environ 11,5 ms par image ; la vérification, de 0,3 à 0,2 ms par
  boucle (à douze cœurs) ; un cœur seul, 15 à 16 ms. Les bandes vérifiées sur 1, 5, 7, 24 et 64 cœurs : la même sortie
  que Lugus quand la promesse tient, l'arrêt quand elle est rompue. La forge conforme ; l'épreuve conforme.

## 90. Le val en 720p, et ce qu'il montre (23 novembre, 0.807)

**Mesuré chez le créateur (0.806, 24 fils)** : 16,1 ms sur un cœur, 15,5 sur deux, 13,5 sur quatre, **10,1 sur huit**,
10,5 sur seize, 13,3 sur tous. Le détail : une image fait cinq ou six boucles en bandes ; chacune passe 0,3 à 2,6 ms dans
les cœurs, puis 0,7 à 1,7 ms à rassembler et vérifier. Au-delà de huit cœurs, c'est ce rassemblement qui coûte, pas le
calcul : le prochain travail du vergobret (rendre moins de cartes de bits, ne vérifier que les pages partagées), sans
rien régler pour une machine. Noté aussi : quand Taranis prendra l'image, le vergobret gardera des cœurs libres pour les
autres tâches d'un programme (la marche, le son, les entrées).

- **720p** (`val_scene.vtx`, `val_ref.c`) : 1280 × 720 (480 × 270 jusqu'ici), le même champ (`ECHELLE` 587, le disque
  du soleil à l'échelle : `DISQUE`). Toute la lumière refaite plus l'image : en C, 13,8 ms (10,4 en 480 × 270) ;
  forgé, ici, 25 ms sur un cœur, 20 sur deux. Empreinte : 1937855438348925206.
- **Ce que montre le 720p** : les cases du relief. La grille n'a que 512 × 512 cases, et le rendu prend chaque case
  telle quelle : de gros carrés de couleur et des marches sur les pentes. En 480 × 270 ça passait ; en 720p, la limite
  n'est plus l'écran mais le relief. C'est l'argument pour le paysage fait dans le cube (des points de surface plus
  fins, la couleur et la matière de chacun), plutôt que pour un relief mêlé entre les cases.
- **Les quatre valeurs de la fusion** (la question du créateur : deux cylindres ne devraient-ils pas avoir 3 ou 4
  valeurs ?) : après un passage en cylindres, chaque mot est inconnu (personne n'y a touché), faux (écrit puis rendu à
  sa valeur), vrai (une seule valeur nouvelle, d'un cylindre ou de plusieurs d'accord) ou variable (deux valeurs : la
  seule qui oblige à rejouer). Le rapport (`VTX_CYLINDRES`) compte désormais vrai et variable ; faux ne se distingue
  pas d'un mot jamais touché sans noter chaque écriture (ce qui coûterait) ; le compte ne se fait que sur demande.
- **La clepsydre, précisée par le créateur** : des points de référence pour l'ombre (le point de surface, ses quatre
  points vers la source, ses quatre points d'ombre), pas un éclairage général.
