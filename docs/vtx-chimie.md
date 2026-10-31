# La chimie de Vercintorix (conception, à valider avant tout code)

Document de conception du 30 octobre 2026, à partir des idées de l'utilisateur (la structure de Lewis, le carbone, les
quatre atomes C H O N, la surface façon Blueprint, la projection de Fischer, l'épissage) et des réflexions de Claude.
Rien n'est codé : ce document sépare ce qui est une image de ce qui se mesure, et liste les décisions à prendre.

## 0. Ce qui reste gravé

- Le cube chromatique, le quaternaire, l'ADN et l'ARN.
- Le chemin : **Cube → Hex → ADN → ARN**. La chimie ne le change pas : elle range et lie ce qui passe dessus.
- Belnap : inconnu 0, faux 1, vrai 2, variable 3.
- Le point de matière de Lugus (trois couleurs de 32 bits, la voie de matière : l'état et cinq codons de 6 bits) reste
  la donnée du cube.

## 1. La leçon de la mesure : la vitesse vient de la densité

Lugus forgé prend de 0,7 à 4,2 fois le temps du C sur les programmes entiers. La cause n'est pas le langage : chaque
valeur occupe 16 octets, même un 0 ou un 1. Le crible range 5 millions de « 0 ou 1 » : 80 Mo sur Lugus, 20 Mo en C.

Mesure du 26 octobre, une ligne changée (`tableau p[N] de quits`) :

| crible | place | temps |
|---|---|---|
| C (int) | 20 Mo | 0,038 s |
| Lugus forgé, mots de 128 bits | 80 Mo | 0,165 s |
| Lugus forgé, quits | 1,25 Mo | 0,045 s |

Et là où vtx tasse déjà l'information (le mot ADN, plusieurs bases comparées d'un coup), il va plus vite que le C.
**Règle** : une valeur occupe la place de l'information qu'elle porte, pas celle du mot de la machine. La chimie qui
suit sert cette règle : lier, ranger serré, contrôler peu mais au bon endroit.

## 2. Deux étages de chimie

| Étage | Éléments | Pourquoi |
|---|---|---|
| Le cube (la machine) | **C, H, O, N** seulement | les quatre éléments du vivant (environ 96 % de sa masse) ; les bases de l'ADN ne sont faites que d'eux ; quatre éléments tiennent dans un quit |
| Le langage et la forge | **toute la chimie** | les éléments plus rares pour les capacités plus rares, les composés pour les constructions du programme |

## 3. Les quatre atomes du cube

Un atome est l'unité du programme lié : une case de la surface (section 8), ce qui agit ; les données sont ses liaisons
(section 4 et décision 1 de la section 11). **Il occupe autant
d'hex que son nombre de masse** : ses protons (l'identité, ce qu'il est) et ses neutrons (le contrôle, ce qui le
stabilise). Ses électrons de valence font les liaisons, rangées à part (section 4).

| Atome | Protons : identité | Neutrons : contrôle | Taille | Liaisons | Doublets libres | Rôle |
|---|---|---|---|---|---|---|
| H-1 | 1 hex | 0 | 1 hex | 1 | 0 | constante, afficher, fin d'une chaîne |
| C-12 | 6 hex (un `#RRGGBB`) | 6 hex | 12 hex | 4 | 0 | calcul : ce qui transforme |
| N-14 | 7 hex | 7 hex | 14 hex | 3 | 1 | condition, attente (le doublet est la voie en réserve) |
| O-16 | 8 hex (32 bits : une voie entière, une adresse) | 8 hex | 16 hex | 2 | 2 | pont : importer, passage entre cubes ou fichiers |

Chaque atome porte une **tête d'un hex** : son élément (un quit : C, H, O ou N) et son état de Belnap (un quit :
inconnu tant que sa valeur n'est pas arrivée).

**Les isotopes** règlent le contrôle sans changer le sens :
- le deutérium (H-2, un neutron) : une constante qu'on veut quand même surveiller ;
- le carbone 13 (7 neutrons) : une donnée critique ;
- par défaut, l'isotope léger.

Le contrôle est donc là où il compte : rien sur les constantes (H, le plus fréquent, vérifié une fois à la
compilation), le plus aux frontières (O, là où les erreurs entrent).

## 4. Les liaisons

- Une liaison est une paire d'électrons **partagée** : la donnée qui passe d'un atome à l'autre. Elle n'appartient à aucun
  des deux atomes. Elle est rangée une
  seule fois, entre eux : les deux atomes et son type.
- **Simple** : une valeur passe. **Double** : deux valeurs à la fois. **Triple** : trois. Les voies de Lugus portent
  directement les liaisons multiples.
- La **valence** limite le nombre de fils d'une case : H un, O deux, N trois, C quatre. Une règle simple, lisible, et
  qui interdit les nœuds illisibles.
- Une liaison est une **dépendance** : deux atomes liés ne réagissent pas en même temps (l'un attend l'autre). Tout ce
  qui n'est pas lié peut réagir en même temps, sans que la machine ait à le deviner.

## 5. Les molécules : reconnues vite, suivies jusqu'à leur source

- **Signature** d'une molécule, calculée d'un passage : sa **formule** (combien de C, H, N, O) et sa **masse** (sa taille
  en hex). H₂O : 18 hex ; CH₄ : 16 ; l'éthanol C₂H₆O : 46. Comparer deux signatures dit si une molécule a changé, sans la
  relire.
- **Source** : chaque molécule garde la case (ou la ligne du texte) qui l'a créée. Une erreur ramène à l'endroit dans
  l'atelier.
- **Contrôle local** : quand un atome change, on revérifie cet atome et ses liaisons, pas le programme. Le travail de
  contrôle suit la taille du changement, pas celle du programme.
- **Triangulation**, trois témoins indépendants : la formule (ce que la molécule contient), les liaisons (comment elle
  est assemblée), les neutrons (le contrôle de chaque atome). Une formule juste aux liaisons fausses est un isomère :
  une molécule mal assemblée. Deux témoins d'accord désignent l'atome fautif, le troisième confirme, ses neutrons le
  réparent.
- Une molécule se **replie** en une seule case : c'est une fonction.

## 6. L'écriture sur le cube : la projection de Fischer

La projection de Fischer écrit une molécule à trois dimensions sur un plan sans perdre sa forme : la chaîne principale
de carbones à la verticale, chaque carbone au croisement d'une croix. Par convention, **les bras horizontaux viennent
vers le lecteur, les bras verticaux s'en éloignent**. C'est ainsi qu'on écrit les sucres, dont le ribose et le
désoxyribose de l'ARN et de l'ADN.

Écrire une molécule dans le cube :
- **la chaîne** (les bras verticaux : l'atome précédent et le suivant) suit une **colonne** du cube, celle de la couleur et
  de la matière (la règle du 24 octobre : la matière entre deux couleurs, toujours dans le même ordre). La chaîne se lit
  à la suite, en descendant : c'est la lecture la plus rapide (le processeur devine la suite et la charge d'avance) ;
- **les substituants** (les bras horizontaux : H, O, N ou une branche) s'écrivent dans les cases voisines de la colonne,
  dans la même couche ;
- la convention de Fischer garde l'information de profondeur : un carbone à quatre substituants différents a deux formes,
  lui et son image dans le miroir.

**La chiralité est l'anti-cube.** Un tétraèdre régulier (le carbone sp3) se loge dans le cube en prenant un coin sur deux ;
les quatre autres coins forment son reflet. Dans le cube chromatique :

| Tétraèdre | Ses quatre coins |
|---|---|
| le premier | noir, cyan, magenta, jaune (l'encre : CMJN) |
| son miroir | blanc, rouge, vert, bleu (la lumière : RVB) |

L'anti-cube envoie exactement l'un sur l'autre : la forme D et la forme L d'une molécule.

**Les règles de Fischer deviennent des contrôles d'ordre, presque gratuits :**
- échanger deux substituants donne le miroir ; en échanger deux fois redonne la molécule. La **parité** des échanges
  dit si l'ordre des mots a été respecté : deux mots échangés dans une même colonne, que l'ombre droite ne voit pas, se
  voient ici ;
- tourner la croix d'un demi-tour dans le plan garde la molécule, d'un quart de tour donne son miroir.

## 7. L'hybridation dit comment ranger

| Hybridation | Forme | Les données | Rangement |
|---|---|---|---|
| sp | linéaire | une chaîne, un tableau parcouru | à la suite (la colonne de Fischer) |
| sp2 | plan | une image, une couche du cube | par carreaux de 64 octets (4 × 4 points de 32 bits) |
| sp3 | tétraèdre | un arbre à quatre branches | un nœud et ses quatre liaisons dans une même ligne de cache |

La règle de l'octet a son pendant exact : un processeur charge toujours 64 octets d'un coup (une ligne de cache). Une
molécule « stable » est un bloc plein, sans case vide. Le diamant (un réseau cubique de carbones sp3) est le cube ; le
graphite (des feuillets sp2 empilés, faiblement liés) est l'empilement des étages : passer d'un étage à l'autre coûte plus
que rester dans un feuillet.

## 8. L'atelier : une surface façon Blueprint

- On **pose des cases** (constante, afficher, importer, calcul, condition, attente, rendez-vous…) et on les **relie**. La
  valence de chaque case (section 4) limite ses fils.
- **Synchronisation par Belnap** : une entrée encore vide est *inconnue*, la case attend ; dès que toutes ses entrées
  sont connues, elle réagit, en même temps que toutes les cases prêtes. Deux valeurs contradictoires sur une même entrée
  donnent *variable* : l'atelier la montre au lieu de choisir au hasard. C'est l'énergie d'activation : une réaction ne
  part que quand tout est réuni.
- **Le rendez-vous** : une case qui attend que plusieurs voies arrivent, puis les relâche ensemble (« attendre qu'une
  voie atteigne une valeur pour activer l'autre, et repartir ensemble »).
- **Le pas à pas** suit des vagues de réactions, plus des lignes : chaque vague montre ce qui part ensemble et ce qui
  attend.
- **Le texte reste la source** (le Hex) : la surface et le texte se traduisent l'un en l'autre, dans les deux sens. On
  enregistre, compare et relit du texte.
- « Dans la mesure du possible » : ce qui réagit vraiment en même temps dépend des liaisons et des cœurs du processeur.

Antériorité, à saluer et à dépasser : la programmation chimique de Banâtre et Le Métayer (Gamma, Rennes, 1986) et la
machine chimique abstraite de Berry et Boudol (1990). Aucune n'a été pensée pour un cube, Belnap et l'ADN.

## 9. L'épissage

En biologie, l'ARN transcrit garde d'abord tout ; l'épissage en retire les introns et raboute les exons. L'épissage
alternatif tire plusieurs protéines d'un même gène.

**Ce qui existe déjà** (docs/vtx-0-5-autonomie.md, sections 27 et 38) : un épissage des instructions à la compilation
(Hex → ADN) : cinq règles qui retirent les instructions qui ne font que déplacer une valeur. Instructions exécutées :
−9 à −20 %.

**Ce qui reste : l'épissage des atomes, à la transcription (ADN → ARN).**
- **L'ADN garde tout** : les neutrons (le contrôle), les sources des molécules, la table des lignes du pas à pas, les
  isotopes lourds. Rien ne se perd dans ce qui dure.
- **L'ARN n'en garde que ce que la lecture demande.** À la transcription, l'épissage retire les introns : les neutrons
  déjà vérifiés, les tables de l'atelier, les sources. C'est là que le contrôle allégé rend la vitesse.
- **L'épissage alternatif** tire plusieurs ARN d'un même ADN :
  - *rapide* : tout le contrôle retiré, sauf celui des frontières (O) ;
  - *sûr* : les isotopes lourds gardés ;
  - *pas à pas* : la table des lignes et les sources gardées.
- **Les signaux** : en biologie, les bornes d'un intron sont marquées (GU au début, AG à la fin). Dans l'ADN de vtx, une
  borne d'intron serait marquée de même, pour que la transcription le saute sans rien analyser.
- La lecture du Hex et de l'ADN n'épisse pas : elle doit pouvoir tout relire (la fiabilité, l'atelier). L'épissage est à
  la transcription.

Une coïncidence à noter : un codon biologique fait trois bases, soit 6 bits ; les codons de la voie de matière de Lugus
font aussi 6 bits.

## 10. Ce qui se mesure (les essais, dans l'ordre)

1. **La densité** : fait pour le crible (les quits). À généraliser : la forge range un tableau selon son type.
2. **Les gaz nobles** : une page fixée (l'ADN, inerte) n'a plus de vérification du brin dans la forge.
3. **L'hybridation** : une image de Gobatix rangée en carreaux sp2 ; un arbre sp3 en lignes de cache.
4. **Le tétraèdre et son miroir** : une palette de quatre couleurs, les quatre autres calculées (NON).
5. **L'épissage alternatif** : le même programme en ARN *rapide* et *sûr*, mesurés.
6. **La parité de Fischer** : deux mots échangés dans une colonne, détectés.

Chaque essai a sa mesure avant et après, comme le crible.

## 11. Décisions (30 octobre, soir)

1. **La liaison est la donnée** (rectification de l'utilisateur, 31 octobre). Les atomes sont le code : les cases, ce
   qui agit. Les liaisons sont les valeurs qui passent d'une case à l'autre, comme la paire d'électrons partagée entre
   deux atomes. Elles vivent dans le cube, rangées en points de matière : chaque liaison a donc son adresse du cube, et
   la suite du programme peut la relire. Liaison simple : une valeur ; double : deux ; triple : trois (les voies de
   Lugus). Les deux liaisons de la chaîne (en haut et en bas de la croix de Fischer) sont rangées l'une après l'autre
   dans la colonne : elles se lisent à la suite, sans adresse à ranger.

   | | Chimie | Vercintorix |
   |---|---|---|
   | atome | ce qui agit | une case : le code |
   | liaison | la paire d'électrons partagée | la valeur qui passe : la donnée, dans le cube |
   | molécule | des atomes liés | une fonction : des cases et leurs données |
   | le support | | le cube |
   | l'indexation | Fischer | l'ordre de lecture des colonnes couleur et matière |

2. **Le cube est le support, Fischer est l'indexation.** La croix de Fischer s'intègre aux colonnes couleur et matière :
   le cube dit *où*, Fischer dit *dans quel ordre on lit*, les liaisons (les données) disent *ce qui y est*, les atomes
   *ce qu'on en fait*.
3. **La syntaxe est la surface (Blueprint)** : on programme en posant des cases et en tirant des liaisons. Elle s'enregistre
   en texte (les cases, leurs valeurs, leurs liaisons), lisible et comparable : c'est le Hex. Une case peut garder des
   lignes de vtx classique, pour que rien de l'existant ne se perde.
4. **Les éléments de l'atelier sont une représentation**, pas une contrainte : on prend dans la chimie, la biologie ou la
   physique ce qui est le plus efficace pour chaque besoin (section 11 bis).
5. **Pas d'épissage entre le Hex et l'ADN** : l'épissage se fait à la transcription (ADN → ARN). L'épissage actuel des
   instructions, aujourd'hui fait à la compilation, est à déplacer ou à renommer (voir la question ouverte).

## 11 bis. Le plus efficace, besoin par besoin

| Besoin | Discipline | Ce qu'on prend | Pourquoi c'est efficace |
|---|---|---|---|
| la structure du programme | chimie | atomes, valence, liaisons | la valence borne les fils d'une case : un graphe toujours lisible |
| ranger et lire | chimie | Fischer, hybridation | la chaîne se lit à la suite : le processeur charge d'avance |
| garder et exécuter | biologie | ADN, ARN, épissage, codons | ce qui dure garde tout, ce qui s'exécute n'a que l'utile |
| le temps et l'ordre | physique | énergie d'activation, fronts d'onde | une case part quand ses entrées sont connues ; une vague à la fois, toutes les cases prêtes ensemble |
| la mémoire | physique | conservation | une valeur appartient à une seule molécule à la fois : pas de copie cachée, pas de fuite |
| la fiabilité | physique | triangulation, projections | trois témoins indépendants localisent et réparent |

## L'épissage, en deux temps (31 octobre, confirmé par l'utilisateur)

1. **À la lecture du Hex** (la compilation, Hex → ADN) : l'épissage du code, qui existe et est mesuré.
2. **De l'ADN à l'ARN** (la transcription) : l'épissage des atomes, conçu, fait seulement si un essai montre un gain.

### Détail

La mesure décide, pas le principe :
- **l'épissage des instructions** (sections 27 et 38 de vtx-0-5-autonomie.md) reste où il est : il est mesuré utile
  (de 9 à 20 % d'instructions exécutées en moins) ; il épisse le code, pas les données ;
- **l'épissage des atomes à la transcription** (ADN → ARN : les neutrons vérifiés, les sources, les tables de l'atelier)
  n'est fait que si un essai montre qu'il rend du temps. Essai 5 de la section 10 : le même programme en ARN *rapide* et
  en ARN *sûr*, mesurés ; s'il n'y a pas d'écart, pas d'épissage.

## 12. Ordre de travail

1. Valider ce document.
2. Les liaisons écrites dans le langage, avec un exemple qui réunit tout un panel d'atomes (H, C, N, O, plusieurs de
   chaque), compilé, exécuté et mesuré.
3. La maquette web de la surface (faite : la paillasse, `surface/paillasse.html`) (poser des cases, tirer des liaisons, voir les vagues et les attentes en Belnap, voir le
   texte vtx s'écrire).
3. Les essais mesurés de la section 10.
4. L'atelier, puis la chaîne Cube → Hex → ADN → ARN.
