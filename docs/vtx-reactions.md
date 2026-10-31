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
    - une réaction qui rend une liaison portant faux rend sa valeur brute (elle devrait rendre faux) ;
    - les unités et les contrats n'entrent pas encore dans la signature de Fischer ;
    - vtxc128 ne connaît encore ni les réactions ni ces ajouts ;
    - le calcul incrémental.
