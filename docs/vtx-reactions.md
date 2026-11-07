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
