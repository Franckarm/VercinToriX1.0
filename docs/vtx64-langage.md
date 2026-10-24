# Vercintorix sur le SPU-64 (vtx64)

Principe gravé : **cube chromatique, quaternaire, ADN / ARN.** Le mot du SPU-64 est un point profond `#RRRRGGGGBBBBAAAA`
(64 bits, 32 quits) ; tous les nombres sont quaternaires ; chaque mot porte un brin (libre, ADN, ARN).

`vtx64.py` est le compilateur de référence pour le SPU-64 (`docs/specification-spu64.md`). Le compilateur du SPU-32
(`vtx.py`) et vtxc restent tels quels et toujours vérifiés : les deux mondes vivent côte à côte. **vtxc64**
(`vtxc/vtxc64.vtx`), le compilateur écrit en vtx pour le SPU-64, donne exactement les mêmes mots que vtx64.py et se
compile lui-même (voir la section 8).

```
python3 vtx64.py mots prog.vtx          puis   vtx64 lancer prog.mots      (la machine Rust, rapide)
python3 vtx64.py run prog.vtx                                               (la machine de référence en Python, lente)
python3 vtx64.py compile prog.vtx | asm prog.vtx | partition prog.vtx | test
```

## 1. Les types

| Type | Mots | Littéraux | Remarques |
|---|---|---|---|
| `entier` (aussi `entier_64`, `long`) | 1 | `42`, `0x2A`, `0q222`, `42L`, `#0123456789ABCDEF` | 64 bits, sans signe pour `/ % < >` ; signé pour `./ .% .>> .< .<= .> .>=` |
| `entier_32` | 1 | `42S` | rangé sans signe dans 64 bits ; `+ - * << /` reviennent dans 32 bits ; affiché signé |
| `flottant` (aussi `flottant_64`) | 1 | `1.5`, `2e-300`, `1.5D` | quaternaire : état Belnap (2 bits), exposant en base 4 (10 bits, biais 537), mantisse de 26 quits |
| `flottant_32` | 1 | `1.5S` | quaternaire : état, exposant de 8 bits (biais 138), 11 quits |
| `entier_petuar` (aussi `entier_128`, `petuar`) | 2 | `5LL`, `#…16 chiffres…_…16 chiffres…`, `adn"…"` de plus de 32 bases | 128 bits, mot bas d'abord (registres R1:R4) |
| `flottant_petuar` (aussi `flottant_128`) | 2 | `1.5Q` | quaternaire : état, 7 quits d'exposant (biais 8247), 56 quits de mantisse |
| `logique` | 1 | `vrai faux inconnu variable` | Belnap : inconnu 0, faux 1, vrai 2, variable 3 |
| `texte`, références | 1 | `"…"` | l'adresse longue d'un bloc |

Mélanges permis sans conversion : l'entier_32 s'élargit en entier ; un entier en flottant ; le flottant_32 en flottant ;
les types de 128 bits accueillent ceux qui tiennent en eux. Un entier écrit qui tient dans 32 bits va dans un
`entier_32` ; un flottant écrit pour un `flottant_32` porte le suffixe S (`0.1S`) : `0.1` est un flottant de 64 bits, et
le ranger dans un flottant_32 arrondirait deux fois (décimal vers 64 bits, puis vers 32), en silence — c'est refusé. Une
autre valeur de 64 bits demande `entier_32()` ou `flottant_32()` : pas de troncature silencieuse.

**Le flottant quaternaire.** Sa mantisse commence par un quit non nul : selon ce quit, 51 ou 52 bits de précision (le
binary64 de l'IEEE en a 53). Ses valeurs spéciales sont celles de Belnap : *inconnu* (le mot tout à zéro), *variable*
(la contradiction : 0/0, racine(−1), ∞ − ∞) et les infinis ; il n'y a pas de NaN. Un flottant sert de condition s'il est
un nombre non nul (zéro, inconnu et variable sont faux). `afficher` écrit les chiffres les plus courts qui redonnent
exactement le nombre (0,1 + 0,2 s'affiche 0.3 : en quaternaire, c'est exactement le flottant le plus proche de 0,3).
L'échange avec le binary64 se fait par `vers_ieee64(x)` et `de_ieee64(n)` (instructions FVIEEE et FDIEEE), avec le
binary128 par `vers_ieee128` et `de_ieee128`.

## 2. Littéraux

* `#RRGGBB` et `#RRGGBBAA` **s'approfondissent** : chaque octet c devient c × 257 sur 16 bits (`#FF8000` vaut
  `#FFFF808000000000`) ; le champ `x.r`, `x.v`, `x.b`, `x.a` lit un canal de 16 bits. C'est un changement par rapport
  au SPU-32 : pour un nombre brut, écrivez `0x…` ou les 16 chiffres `#…`.
* `#RRRRGGGGBBBBAAAA` : un point profond tel quel ; `#…16…_…16…` : deux points profonds (un entier_petuar).
* `adn"…"` : jusqu'à 32 bases dans un entier, jusqu'à 64 dans un entier_petuar (A 0, C 1, G 2, T/U 3).
* `S` : 32 bits ; `LL`, `Q` : 128 bits ; `L` et `D` restent acceptés (64 bits).

## 3. La mémoire : le cube chromatique en adresses longues

Une adresse longue porte l'étage (bits 63-62), la fréquence du cube (bits 47-24) et `#RRGGBB` (bits 23-0) :
4 étages × 16 777 216 cubes × 16 777 216 mots.

* `@e[a]` place `a` à l'étage `e` (sa fréquence est gardée) ; `@(x)[a]` un étage calculé ; **`@[a]`** l'adresse longue
  telle quelle.
* `cube_adresse(etage, frequence, rgb)` compose une adresse longue.
* `ranger_cube(etage, f)` écrit un cube sur disque (avec le brin de chaque mot) ; un autre lancement le retrouve page
  par page, au premier accès, sans rien demander.
* **Le cube de transfert jetable** : un cube entier sert de brouillon ; `jeter_cube(etage, f)` le vide d'un coup (ses
  pages quittent la mémoire, sans être relues du disque).
* Le tas (`nouveau`, textes, tableaux, structures) est à l'étage 3, cube 0 ; ses adresses sont longues (étage dedans).

## 4. Le brin : ADN et ARN

Chaque mot a un brin : 0 libre, 1 **ADN** (T : le résultat fixé, en lecture seule), 2 **ARN** (U : le travail).

* Automatique : au départ, le code, les textes écrits et les données du programme deviennent de l'ADN. Une écriture
  dessus arrête la machine (« écriture dans un mot ADN (fixé) ») au lieu de corrompre le programme.
* `fixer(h)` : le bloc `h` (texte, structure, poignée) devient de l'ADN ; il ne sera jamais libéré.
  `fixer_tableau(t)` : la poignée et les données.
* `copier_arn(h)` : une copie de travail (ARN), modifiable (un texte écrit dans le programme aussi) ;
  `copier_arn_tableau(t)`.
* `est_fixe(h)`, `est_arn(h)`, `brin(adresse)` ; au plus bas : `marquer_adn(a, n)`, `marquer_arn(a, n)`,
  `liberer_brin(a, n)` (l'instruction MARQUE).

## 5. Intégrés nouveaux ou changés

`entier_32`, `flottant_32`, `comme_flottant_32`, `flottant_64` (= `flottant`), `mul_haut(a, b)` et
`mul_haut_signe(a, b)` (les 64 bits hauts du produit), `vers_ieee64`, `de_ieee64`, `entier_petuar_de(haut, bas)`,
`entier_petuar_signe`, `bas`, `haut`, `brin`, `marquer_adn`, `marquer_arn`, `liberer_brin`. `gemv` place ses adresses à
l'étage 2, comme avant ; `gdot` multiplie quatre canaux de 16 bits (avec des couleurs approfondies, le résultat est celui
du SPU-32 multiplié par 257², exactement).

Prélude : `binaire32` et `quaternaire32` (32 logiques par mot) remplacent `binaire16` et `quaternaire16` ; `rgb` donne
une couleur profonde (8 bits par canal, approfondis), `rgb16` prend 16 bits par canal ; `hasard` est un xorshift de 64
bits ; le hachage des dictionnaires est FNV-1a de 64 bits ; `accorder` et `frequence` disparaissent (l'adresse longue porte
la fréquence) ; `cube_adresse`, `jeter_cube`, `fixer`, `copier_arn` et leurs voisins apparaissent ; les fonctions
mathématiques (`sinus`, `exponentielle`, `logarithme`, `puissance`, `arctangente`…) travaillent en flottant de 64 bits
(les noms en `_64` de la version 0.4 restent, ils appellent les mêmes) ; mesurées contre la bibliothèque de Python, elles
restent à moins de 2 ulps (51 bits).

## 6. Ce qui est vérifié (tests/test_vtx64.py)

La suite du compilateur (87 tests, dont les 37 de vtx.py adaptés au 64 bits), puis contre une référence exacte en Python :
entier et entier_32 (300 cas, opérations signées comprises), flottant et flottant_32 (300 cas : opérations, conversions,
échange IEEE), écriture décimale la plus courte (64 et 32 bits), flottant_petuar sur deux mots (254 cas), entier_petuar
(150 cas), la bibliothèque mathématique en ulps, et l'accord exact de la machine de référence et de la machine Rust sur
les programmes compilés.

## 7. Notes honnêtes

* Le flottant quaternaire a 1 à 2 bits de moins que le binary64 : c'est le prix d'un exposant en base 4 (un quit
  d'exposant et un quit de mantisse en moins pour le même mot). Les constantes des fonctions mathématiques viennent de
  fdlibm (écrites pour 53 bits) : la réduction des grands angles perd un peu au-delà de 2^19.
* `entier_32(x)` d'un flottant tronque vers 64 bits puis garde les 32 bits bas (modulo 2^32).
* `flottant_32(e)` d'un entier de plus de 2^52 subit deux arrondis.
* La machine Rust SPU-64 fait 150 à 190 millions d'instructions par seconde ; la page du code a son propre cache, la pile ne
  la chasse plus.

## 8. vtxc64 : le compilateur écrit en vtx

`vtxc/vtxc64.vtx` (7 900 lignes de vtx) lit `source.vtx` et écrit `code.mots`, exactement comme vtx64.py (mêmes mots,
même table des accords) : lexique 64 bits et suffixes S, L, LL, D, Q, couleurs approfondies, flottants quaternaires lus
exactement (un seul calcul `bits_q` pour Q32, Q64 et Q128, en grands entiers), adresses longues `@[a]`, 32 quits par mot,
générateur du SPU-64 (CMPI, LDIS/LDIU/LDI, ETG/ETGX, MARQUE au départ), épissage sur les champs du mot de 64 bits,
variables en registres, partition des tâches, prélude de vtx64.py embarqué et lu à la demande.

```
vtx64 lancer m.mots  0 1 1 0        (entrées : dossier des imports, 0, prélude, optimisations, partition)
```

`vtxc/test_vtxc64.py` vérifie : le point fixe (vtx64.py compile vtxc64 en M0 ; M0 compile vtxc64 en M1, M1 en M2 :
M0 = M1 = M2, 159 000 mots, une dizaine de secondes sur la machine Rust), vtxc64 optimisé, la suite de vtx64.py, les
programmes de test_vtx64 et d'exemples64, et des programmes aléatoires (tous les types, tous les littéraux, structures,
tableaux rangés, hypothèses, segments, accords) avec et sans optimisation et partition.

**Les tables dans les cubes.** vtxc64 range ses noms dans des cubes chromatiques de l'étage 3, comme les rayons
d'un magasin : la fréquence du cube dit le rôle et la durée de vie (le permanent : mots-clés, intégrés, sorte des
instructions ; la compilation : fonctions, constantes, textes, fonctions du prélude ; le frais : les variables de la
fonction en cours, rayon vidé d'un coup par `jeter_cube`, service 13, à chaque fonction), le #RRGGBB de la case vient du
hachage du nom (FNV-1a de 64 bits). Les collisions se règlent en **hachage Robin Hood**, comme l'eau qui se met de
niveau : le nom le plus loin de sa case d'origine garde la place, et une recherche s'arrête dès qu'elle croise un nom
plus proche de chez lui. Les tables ne servent qu'à trouver : l'ordre reste celui des listes, les mots ne changent pas.
Avec le tas qui ne remet plus à zéro la mémoire neuve et des accès directs (`@[a]`) dans les fonctions de base, vtxc64
se compile en 550 à 625 millions d'instructions au lieu de 1,2 milliard ; un petit programme avec le prélude : 90
millions au lieu de 179. `vtx64 profil prog.mots` compte les instructions par adresse
(`profil.txt`). Ce qui reste est surtout le coût des appels des petites fonctions (`ajouter`, `elem`…) : l'étape
suivante est l'expansion en ligne des fonctions courtes, dans vtx64.py et vtxc64 ensemble (faite : section 10).

## 9. vtxc64 dans la machine Rust, l'atelier sur le SPU-64

vtxc64 optimisé (`vtx-rs/vtxc64.mots`, copie de `vtxc/vtxc64.mots`) est embarqué dans les exécutables : plus besoin de
Python pour compiler un programme du SPU-64.

| Commande | Effet |
|---|---|
| `vtx64 PROG.vtx [ENTRÉES…]` | vtxc64 compile (prélude, optimisations, partition), la SPU-64 exécute ; la console du programme est le terminal (`lire_ligne` lit le clavier), le canal `voix:` parle ; une erreur de compilation donne le fichier et la ligne |
| `vtx64 compiler PROG.vtx [SORTIE.mots]` | écrit seulement « mots;table » |
| `vtx64 renouveler vtxc64.vtx` | l'ancien vtxc64 compile le nouveau (m1), m1 le recompile (m2), m2 se recompile (m3) : `vtxc64.mots` n'est écrit que si m2 = m3 ; puis `cargo build --release` l'embarque |
| `vtx-spu essai-pas64 PROG.vtx` | ce que fait l'atelier sur la SPU-64, sans fenêtre (vérification) |

**L'atelier** travaille par défaut sur la SPU-64 : le titre et le bouton de la barre nomment la machine, *Exécuter ›
Machine 64 bits* (Ctrl+M, ou `machine 32` / `machine 64` dans le terminal) change de machine. Un fichier du dossier
`exemples` (les programmes de 32 bits) s'ouvre sur la SPU-32, tout le reste sur la SPU-64.

* **F5** : vtxc64 compile, la SPU-64 exécute dans un fil à part ; la console passe par le terminal de l'atelier, Maj+F5
  arrête le programme (vu toutes les 2^20 instructions).
* **Le cube** dessine des points de 32 bits : un point profond `#RRRRGGGGBBBBAAAA` y paraît par l'octet fort de chaque
  voie (`#RRGGBBAA`), un petit nombre (moins de 2^32) reste tel quel. Chaque étage regarde son cube 0 (ou, s'il est vide,
  le premier cube écrit) ; `cube ÉTAGE FRÉQUENCE` en montre un autre, `cubes` liste les cubes écrits ; l'arbre les liste
  aussi. Un clic dans le cube, ou `mot ADRESSE`, rend la vraie valeur de 64 bits : décimal, point profond, adresse longue
  (étage, cube, #RRGGBB), instruction (à l'étage 0), flottant, 32 quits de Belnap.
* **Le pas à pas** (F7 ligne, F8 par-dessus les fonctions, F9 point d'arrêt, F5 continuer) : vtxc64 donne la table des
  lignes ; le panneau montre les registres sur 64 bits (décimal, quatre voies en hexadécimal, 32 quits), R13 et R14, le
  cadre de la fonction (variables locales et paramètres), les sorties et ce que le programme a écrit.
* Ce qui reste propre à la SPU-32 : l'image d'un programme qui dessine (`ecran`) et l'arbre des objets du tas
  (tableaux, dictionnaires, textes), dont la disposition est celle des mots de 32 bits. L'atelier en console
  (`vtx atelier`, hors Windows) reste sur la SPU-32.

`vtxc/test_vtxc64.py` vérifie aussi que le compilateur embarqué est à jour, que `vtx64 PROG.vtx` donne sur exemples64
ce que donnent vtx64.py puis la machine, et que le pas à pas de l'atelier (ligne par ligne, par-dessus, d'un coup) finit
avec la même console et les mêmes sorties que F5, la vue du cube montrant chaque mot. Il annonce chaque étape avant de
la commencer.

## 10. L'expansion en ligne des petites fonctions

Un appel coûte cher pour une petite fonction : `elem(l, i)` faisait 18 instructions (les arguments poussés sur la pile,
CALL, le cadre, le saut vers la fin, RET) pour 3 instructions utiles. Avec les optimisations, vtx64.py et vtxc64
**recopient à la place de l'appel** une fonction dont le corps est une seule instruction : `retour E` (dans une
expression), ou une écriture `@[a] = v`, `x.champ = v`, ou un appel (écrits comme instruction) ; ses paramètres sont
remplacés par les arguments. `elem(l, i)` devient 4 instructions.

Rien ne change à ce que fait le programme, par construction :

* le corps ne contient que des nombres, des textes écrits, ses paramètres, `@[a]`, des opérations, des champs, des
  quits et des appels ; aucun type de deux mots ; pas de tableau rangé (32 quits par mot) ;
* chaque argument a exactement le type du paramètre : aucune conversion ne change de place ;
* un argument qui n'est ni une variable, ni un nombre, ni un texte écrit prend la place de son paramètre, qui ne doit
  servir qu'une fois ; son calcul change donc de moment. Il le peut s'il ne fait que calculer : un **calcul**
  (variables, nombres, opérations sans division, quits, appels de fonctions pures qui ne lisent pas la mémoire) va
  partout ; un argument **pur** (qui lit aussi la mémoire : `@[a]`, champs) va seulement dans un corps qui n'écrit rien.
  Une **fonction pure** est une fonction recopiable `retour E` sans appel ni division. Une division reste à sa place :
  une division par zéro doit arriver au même moment ;
* au plus trois expansions l'une dans l'autre, jamais une fonction dans elle-même.

Aussi : un `retour` en dernière instruction d'une fonction n'a plus de saut vers la fin (il y arrive), et la fin ne
rend plus 0 dans ce cas.

Mesures (instructions exécutées) :

| Programme | Avant | Après |
|---|---|---|
| vtxc64 qui compile vtxc64 (le même travail, code produit avant / après) | 554 millions | 422 millions (−24 %) |
| bonjour64.vtx | 514 640 | 396 327 (−23 %) |
| quaternaire64.vtx | 37 185 | 29 021 (−22 %) |
| programmes aléatoires de test_vtxc64 | | −4,6 % |
| vtxc64 compile bonjour64.vtx (prélude, ce que fait F5) | 90 millions | 67 millions (−26 %) |

Le nouveau vtxc64 fait aussi plus de travail en compilant (il vérifie chaque appel, recopie, et il y a plus de code à
épisser) : il se compile lui-même en 497 millions d'instructions au lieu de 554 (−10 %). Le code produit grandit d'environ
5 % (vtxc64 : 133 932 → 140 525 mots). Les fonctions recopiées restent générées : les analyses (registres, partition)
voient toujours l'appel.

Vérifié : les deux compilateurs donnent les mêmes mots (point fixe, suites, programmes aléatoires qui appellent des
petites fonctions de toutes les sortes) ; vtx64.py avant et après donnent les mêmes sorties et la même mémoire sur 650
programmes aléatoires ; un test de vtx64.py porte sur l'expansion (structures, flottants, textes, récursion, appels
imbriqués, divisions). Le générateur de programmes aléatoires appelle maintenant des petites fonctions de toutes les
sortes ; il a trouvé deux écarts entre les compilateurs, corrigés : un argument `q[i]` (tableau de quits) que vtx64.py
voit déjà traduit en lecture de mot, et un écart plus ancien, sans rapport avec l'expansion : `x = q[i]` quand `x` est
dans un registre (vtxc64 prenait LDQ, vtx64.py le calcul direct).

Ce que le profil montre ensuite : les appels de fonctions plus longues (`ajouter`, `texte_egal`), les copies de
registres (MOV, 12 % des instructions : `MOV R1,R10 ; LD R1,R1,#2` pourrait être `LD R1,R10,#2`), et, dans vtxc64, le
coût de typ() (recalculé à chaque usage) et de l'épissage.

## 11. L'épissage par échange (l'auto-épissage des introns de groupe I et II)

Les introns de groupe I et II s'excisent seuls, en deux transestérifications : un OH attaque le site 5' (une guanosine
venue d'ailleurs pour le groupe I, l'adénosine du point de branchement, dans l'intron même, pour le groupe II), puis
l'extrémité libérée de l'exon 1 attaque le site 3' ; les exons sont soudés, l'intron part (en lasso pour le groupe II).
Une transestérification **échange** des liaisons sans en créer ni en perdre : rien ne change hors du site.

La cinquième règle de l'épissage fait la même chose avec un MOV :

```
MOV Ra,Rb ; … lit Ra …        ->        … lit Rb …        (le MOV s'en va)
MOV R1,R10 ; LD R1,R1,#2      ->        LD R1,R10,#2
```

Premier temps : le MOV (l'intron) se détache, « Ra vaut Rb ». Second temps : chaque lecture de Ra qui suit se soude
directement à Rb, jusqu'à l'instruction où l'ancienne valeur de Ra cesse de servir (Ra y est réécrit, ou mort après) ; si
Rb change avant, ou si un saut, un appel, une étiquette visée, un PUSH (la règle pile s'en charge mieux) ou une
instruction inconnue vient avant, rien n'est fait. Au plus 8 instructions (ECHANGE_PORTEE).

Comme pour la transestérification, les registres vivants à l'entrée et à la sortie du site restent les mêmes (ou moins
nombreux, ce qui reste prudent) : la vie des registres n'est refaite que sur le site, pas sur toute la fonction.

Dans vtxc64, l'analyse de vie décode aussi chaque instruction une seule fois (ce qu'elle lit, ce qu'elle écrit, où elle
peut aller) au lieu d'une fois à chaque passe ; le code produit n'en change pas.

| Mesure | Avant | Après |
|---|---|---|
| vtxc64 compile vtxc64 (le même source) | 497 millions | 473 millions (−5 %) |
| F5 sur bonjour64 (compilation avec le prélude) | 67 millions | 61 millions (−9 %) |
| code produit par vtxc64, à travail égal | 483 millions | 453 millions (−6 %) |
| programmes aléatoires (exécution, depuis avant l'expansion en ligne ; elle seule : −5 à −7 %) | | −10 % |
| vtxc64 | 140 555 mots | 138 827 mots |

Honnêtement : la propagation des copies et la mise à jour locale de l'analyse de vie sont des techniques connues des
compilateurs ; ce qui est propre à Vercintorix, c'est de les penser comme l'auto-épissage, et la condition de conservation
qui permet de ne refaire la vie que sur le site.

**Trouvé en chemin : le tas de vtxc64.** vtxc64 range ses objets de #800000 à 14 680 056 dans le cube 0 de l'étage 3, et
son pointeur de tas était à 14 680 056 : sans contrôle, un tas de plus de 6,3 millions de mots écrasait ce pointeur et
ce qui suivait. vtxc64 qui se compile lui-même en était tout près ; un peu plus de code l'a fait déborder (la compilation
tournait sans fin). Le tas de vtxc64 continue maintenant dans les cubes suivants, d'un seul tenant (l'adresse longue
porte le cube), et son pointeur est rangé dans le cube 2999 : plus de plafond. Le tas des programmes (le prélude) avait
déjà son contrôle (purge, puis nul quand il est plein) ; sa taille, environ 5,7 millions de mots, pourrait s'étendre de
la même façon.


## 12. Gobatix interactif : la souris, le clavier, l'animation, l'anti-cube

Les mêmes fonctions sur le SPU-32 et le SPU-64 (services 16 à 21 de la machine, `vtx-rs/src/hote.rs`), au prélude des
deux compilateurs de chaque machine, avec les mêmes mots (`tests/test_gobatix.py`) :

| Fonction | Rend | Service |
|---|---|---|
| `souris()` | x (bits 0-11), y (12-23) en points de l'image, boutons (24-26 : gauche 1, droit 2, milieu 4), dans l'image (27) | 16 |
| `touche()` | la prochaine touche appuyée, sans attendre : un caractère, ou 65536 + code ; 0 s'il n'y en a pas | 17 |
| `horloge()` | les millisecondes depuis le lancement | 18 |
| `cadence(ms)` | l'ancienne cadence ; presenter() attend au moins ms entre deux images (16 par défaut) | 19 |
| `molette()` | les crans depuis le dernier appel, signé | 20 |
| `appuyee(t)` | 1 si la touche t est enfoncée | 21 |

Sans fenêtre, 16, 17, 20 et 21 rendent 0 (sur les quatre machines : Python, Rust, et le code natif traduit) ; la
cadence est gardée sans effet ; l'horloge marche partout.

**L'image finie (double tampon).** `presenter()` copie l'image de l'étage 1 vers la sortie : la fenêtre de Gobatix, la
vue du cube de l'atelier, des PNG, un GIF. La sortie ne montre que des images finies ; le programme dessine la
suivante dans l'étage 1 sans être vu. Jusqu'ici l'atelier ne montrait l'image qu'à la fin du programme : il la montre
maintenant à chaque `presenter()`, sur les deux machines (le SPU-64 n'avait aucune sortie d'image : `presenter64`,
`vtx gobatix64`). Un point profond est vu par l'octet fort de chaque voie.

**L'anti-cube des couleurs.** `anti_couleur(c)` = 255 − c par voie (65 535 − c en 64 bits), l'alpha gardé : c'est le
« ou exclusif » de la couleur avec #FFFFFF00, la symétrie du cube par son centre gris. Involutive, elle donne les
curseurs, les sélections et les objets animés **sans sauvegarde du fond** : poser en anti, présenter, reposer en anti.
C'est la vieille astuce du curseur en XOR des premiers écrans ; dans le cube, elle a une géométrie (le triangle
rouge-vert-bleu devient cyan-magenta-jaune, et un gris moyen reste presque gris : c'est sa limite, un curseur sur un fond
gris #808080 se voit mal).

**Le GIF par l'anti-cube de Belnap.** Chaque image n'est écrite que par sa différence avec la précédente : un point
inchangé n'apporte aucune preuve nouvelle, il est *inconnu* et devient l'index transparent ; seul le rectangle des
changements est écrit, et une image identique allonge la précédente au lieu de s'ajouter. Le cube tournant (400 × 300,
120 images) tient en 190 Ko ; peindre (320 × 200, 200 images) en 42 Ko. La palette est le cube réduit à 6 niveaux par
voie, 216 couleurs, et 39 gris, avec une trame ordonnée de Bayer qui garde exactes les couleurs de la grille (0, 51…
255). Vérifié : chaque image décodée par Pillow est exactement l'image tramée attendue. Honnêtement : une palette fixe
trame les dégradés fins (le cube chromatique se voit légèrement grenu) ; une palette choisie pour l'animation ferait mieux.

**Les scénarios.** `--scenario FICHIER` rejoue des gestes image par image ; le même scénario donne le même GIF octet
pour octet sur le SPU-32 et le SPU-64 (`peindre.scenario`).

**L'atelier.** Pendant l'exécution, la vue du cube montre la dernière image ; un clic sur l'image lui donne la souris et
le clavier (Échap compris ; F5 et Maj+F5 restent à l'atelier). Ctrl+G commence et finit l'enregistrement d'un GIF
(`programme-1.gif` à côté du programme) ; Cube › Image en PNG. Le programme fini, la vue en perspective se tourne à la
souris (glisser à gauche : un quart de tour ; glisser à droite : déplacer ; double clic : revenir). La limite d'instructions
de F5 est levée : un programme interactif tourne tant qu'on veut, Maj+F5 l'arrête.
