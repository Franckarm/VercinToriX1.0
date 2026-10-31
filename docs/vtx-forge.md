# La forge : Vercintorix en code natif

*vtx 0.5i. La forge est un prototype en Python (`forge/forge.py`) ; son portage dans vtxc, pour que vtx écrive lui-même
son code natif, est la prochaine étape.*

## L'idée

Trois façons de faire tourner un programme vtx existaient :

1. **le SPU émulé** (`vtx programme.vtx`) : une instruction après l'autre ;
2. **la traduction des mots** (`vtx traduire`, dossier `natif/`) : chaque instruction du SPU devient une ligne de
   Rust. La boucle d'interprétation disparaît, mais le programme garde la convention du SPU : chaque variable vit
   dans le cadre de sa fonction, en mémoire, chaque appel empile ses arguments ;
3. **la forge** (nouvelle) : on ne part plus des mots, mais de **l'arbre du programme**, tel que vtx.py le lit et le
   type. Chaque fonction vtx devient une fonction Rust, chaque variable une variable Rust. rustc (LLVM) range alors
   les variables dans les registres de la machine, déroule et vectorise les boucles, met en ligne les petites
   fonctions.

La forge garde **le sens exact du SPU** : entiers de 32 bits sans signe, division par zéro définie (le plus grand nombre,
le reste vaut le dividende), décalages pris modulo 32, flottants IEEE au NaN unique (0x7FC00000), longs signés,
flottant_64, entier_128, petuar (par le prélude, comme sur le SPU), logique de Belnap, quits. Les fonctions du
prélude sont forgées comme les autres.

## Autour du programme : la même machine

Le programme forgé emporte la machine (`forge/noyau_forge.rs`), faite des fichiers mêmes de la machine émulée :

| Fichier de vtx-rs | Rôle dans le programme forgé |
|---|---|
| `memoire.rs` | les quatre étages, les cubes (fréquences), les cubes sur disque |
| `miroir.rs` | chaque cube écrit avec son anti-cube et son ombre ; `etat_disque()` |
| `sortie.rs`, `gif.rs`, `hote.rs` | Gobatix : la fenêtre (Windows), l'animation GIF, les images PNG, la souris, le clavier, l'horloge, les scénarios |

L'image du programme compilé par vtx.py est chargée telle quelle dans l'étage 0 : les textes et les données sont aux
mêmes adresses que sur le SPU. Un programme forgé se lance comme `vtx programme.vtx` (les entrées sur la ligne de
commande), et un programme Gobatix comme `vtx gobatix programme.vtx` : la première image ouvre la fenêtre, ou
`--gif FICHIER`, `--images DOSSIER`, `--max N`, `--pas K`, `--scenario FICHIER`.

## Deux points délicats

**Le ramasse-miettes.** Celui du prélude cherche les références vivantes dans la pile du SPU, de `pile()` au haut de
la pile. Dans un programme forgé, les variables sont dans les registres de la machine : il ne les verrait pas. Une
fonction forgée qui appelle, de près ou de loin, le ramasse-miettes garde donc un cadre dans la pile du SPU, et y
recopie ses variables juste avant chaque appel qui peut ramasser ; une valeur déjà calculée au milieu d'une expression
(un argument, l'adresse d'une structure en construction) y est posée aussi, comme le SPU l'empile. Les autres
fonctions (les boucles de calcul) n'ont aucun cadre. Le ramasse-miettes étant conservateur, il garde tout ce qu'un mot
de la pile semble désigner ; la pile du SPU porte d'autres mots périmés que celle d'un programme forgé : après une
purge, la taille du tas peut différer de quelques blocs (`purge.vtx` : 5 670 238 mots au lieu de 5 691 343). Les
valeurs gardées sont les mêmes.

**Les flottants.** Le SPU rend tout NaN sous une forme unique. Le faire à chaque opération coûte une comparaison ; or
cela ne change rien tant que les bits ne sont pas regardés. La forge repère les variables flottantes dont les bits ne
sont jamais lus (elles ne servent qu'au calcul, aux comparaisons, à `entier()`, `racine()`…) : elles vivent comme des
flottants de la machine, et le NaN unique n'est imposé que là où les bits se voient. Dans `mandel`, la boucle
intérieure devient celle qu'écrirait un programmeur C.

## Vérification

- `forge/test_forge.py N` : les exemples du paquet qui se terminent seuls, et N programmes tirés au hasard (le
  générateur du test différentiel) ; sorties, texte et mémoire finale (étages 1 à 3) comparés au SPU émulé.
  **3 267 programmes en tout, aucun écart** (seule la mesure du tas de `purge.vtx` et `ramasser.vtx` diffère, voir plus haut).
- `--recolte FICHIER` ajoute les programmes des tests de types (flottants, longs, flottant_64, entier_128, petuar),
  avec leurs entrées, récoltés par `forge/recolte.py`.
- Gobatix : `peindre.vtx` (avec son scénario de gestes), `cube_tournant.vtx`, `cube_chromatique.vtx` et
  `jeu3/labyrinthe.vtx` (avec `labyrinthe.scenario`) donnent **la même animation GIF, octet pour octet**, émulés et
  forgés.

## Mesures

Médiane de 5 lancements, lancement du processus compris ; machine de mesure : Xeon 2,1 GHz (VM). La fiche complète
(C, Rust, Go, Java, JavaScript, Python) est dans `mesures/`.

| Programme | C (gcc -O2) | Rust | vtx forgé | rapport au C | vtx traduit | vtx émulé |
|---|---|---|---|---|---|---|
| fib(32) | 0,004 s | 0,008 s | 0,008 s | 2,0 | 0,047 s | 0,62 s |
| crible | 0,033 s | 0,032 s | 0,047 s | 1,4 | 0,093 s | 0,93 s |
| mandel | 0,020 s | 0,019 s | 0,022 s | 1,1 | 0,072 s | 0,90 s |
| tri | 0,049 s | 0,049 s | 0,067 s | 1,4 | 0,12 s | 0,72 s |
| adn | 0,023 s | 0,022 s | 0,010 s | **0,43** | 0,013 s | 0,22 s |

Le labyrinthe (300 images de la vue 3D, `jeu3/labyrinthe.vtx 1`) : **13,3 ms par image émulé, 0,45 ms traduit,
0,15 ms forgé** ; la même empreinte de l'image dans les trois cas.

Pour fib, gcc transforme lui-même la récursion ; Rust écrit à la main fait comme la forge (0,009 s). Pour adn, le
mot ADN de vtx range 16 bases et l'instruction QEGAL les compare d'un coup : le C écrit simplement compare base par
base.

## La forge de Lugus (le SPU-128)

`python forge/forge128.py PROG.vtx [-o EXE] [--natif]` : la même idée sur Lugus. Chaque valeur est un u128 ; les
opérations suivent la largeur des instructions de Lugus (l'entier par défaut à 64 bits, l'entier_petuar à 128, le
flottant quaternaire de 128 bits par défaut, 64 et 32 au choix, le point de matière et ses voies). Autour du programme,
la machine Rust de Lugus elle-même (`spu128.rs`, `qflot128.rs`, `miroir.rs`, `hote.rs`, recopiés dans le noyau
`noyau_forge128.rs`) : mémoire, brin ADN, cubes sur disque, services. Un petit cache de 16 pages évite la table de
pages à chaque accès.

Vérification : `forge/test_forge128.py N` forge la suite de vtx128.py dans les deux langages (celui de Lugus et celui du
SPU-64) et N programmes au hasard, tous dans un seul programme Rust, et compare sorties, texte et mémoire finale à Lugus
émulé : aucun écart.

| Programme | C (gcc -O2) | Rust | Lugus forgé | rapport au C | Lugus émulé | Dunon émulé |
|---|---|---|---|---|---|---|
| fib(32) | 0,004 s | 0,007 s | 0,012 s | 3,0 | 1,17 s | 0,75 s |
| crible | 0,031 s | 0,031 s | 0,056 s | 1,8 | 2,12 s | 1,30 s |
| mandel | 0,019 s | 0,019 s | 1,00 s | 53 | 3,76 s | 2,68 s |
| tri | 0,045 s | 0,047 s | 0,064 s | 1,4 | 1,37 s | 0,88 s |
| adn | 0,019 s | 0,015 s | 0,019 s | **1,0** | 0,39 s | 0,22 s |

(31 octobre, avec l'adaptation automatique ci-dessous ; avant elle : crible 4,2 fois le C, tri 2,0.)

**L'adaptation automatique** : un tableau que seul son nom touche (aucun accès par `@` dans son étage, aucune
référence, aucun service qui lit la mémoire, aucun brin posé) est rangé hors du cube, dans un tableau Rust serré, du plus
petit type qui tient ce qu'on y écrit : des nombres écrits jusqu'à 255 dans des octets (le crible : 5 Mo au lieu de
80), des entiers de 64 bits dans des u64 (tri, adn), le reste en u128. Un indice hors du tableau passe par le cube. À la
fin, ou à une erreur, le tableau est recopié dans le cube : la mémoire finale reste exactement celle de Lugus émulé
(`forge/test_forge128.py` le vérifie, avec neuf programmes écrits pour cela). S'il existe un cube sur disque pour
l'étage du tableau, il reste dans le cube.

Ce qui est comparable : Mandelbrot en C sur `__float128` (113 bits, logiciel) prend 0,88 s, Lugus forgé 1,00 s en
flottant quaternaire de 128 bits (0,85 s en flottant de 64 bits, logiciel aussi). Le C en float ou en double calcule en
matériel, avec une autre précision. Mesures : `mesures/mesurer128.py`, fiche `mesures/mesures-lugus.json`.

## Le labyrinthe, tout en vtx

`jeu3/labyrinthe.vtx` est le jeu complet sans la page web : la boucle (pas de simulation de 1/60 s, tours des
ennemis, animation), le clavier (`appuyee`, `touche`), la souris (`souris_glisse`), l'horloge, et l'affichage. L'image
montrée vit **dans un cube à elle** : l'étage 1 porte la carte, les textures et les tables du jeu (cube 0) ; pour
présenter, l'étage 1 s'accorde sur le cube 12, la vue et le tableau de bord y sont peints, puis l'étage revient au
cube du jeu. Deux cubes, un seul étage : rien n'est déplacé.

`vtx gobatix jeu3/labyrinthe.vtx` le joue sur la machine émulée ; `python forge/forge.py jeu3/labyrinthe.vtx` en
fait un exécutable seul.

## L'horloge des images

Une animation (`--gif`, `--images`) ou un scénario n'a pas de temps réel à suivre : `horloge()` y compte désormais le
temps des images déjà présentées (la cadence de chacune). Un programme qui mesure le temps, comme le labyrinthe, se
rejoue ainsi à l'identique, sur toutes les machines et à toutes les vitesses ; c'est ce qui permet de comparer les
animations octet pour octet.

## La suite

- **vtxc écrit le Rust** : porter la forge dans le compilateur écrit en vtx (même texte que forge.py), pour que
  `vtx forger programme.vtx` n'ait besoin que de rustc ;
- **le SPU-64** forgé de même (vtxc64) ;
- **le générateur x86-64 propre**, plus tard, comparé à la forge.
