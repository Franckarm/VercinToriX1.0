# vtx 0.5 : le langage figé pour l'autonomie

**But** : Vercintorix totalement autonome. Son compilateur est écrit en vtx, tourne sur le SPU et se compile lui-même. vtx reste un langage **spécifique** : le cube, les quits, la logique à quatre valeurs, les segments et la partition en sont le cœur ; ce qu'on ajoute ici ne sert qu'à lui permettre de s'écrire lui-même et, plus tard, d'écrire Coatvtx.

## 0. Le noyau immuable

Ces éléments définissent vtx et ne seront ni retirés ni remplacés, dans aucune version : le mot du cube `#RRGGBBAA` et ses quits ; **la logique à quatre valeurs** (`vrai`, `faux`, `inconnu`, `variable`, avec `non4`, `anti`, `fusion`, `consensus`, `selon`) ; les segments et la partition par fréquences. Toute nouvelle partie du langage, compilateur en vtx compris, s'appuie dessus.

## 1. Ce qui ne change pas (acquis de la 0.4)

Entiers 32 bits, flottants, longs, `logique` ; quits, voies du mot `#RRGGBBAA`, couche ADN ; tableaux, structures, tableaux de quits et de logiques ; fonctions et récursion ; `si`, `selon`, `tantque`, `pour`, segments, `cumulant` ; hypothèses ; partition par fréquences ; réécriture en 16 éléments d'un coup ; débogueur. Le code machine des programmes 0.4 ne change pas.

## 2. Ce qui entre dans la 0.5

### 2.1 Caractères et texte
- Littéral caractère : `'a'`, `'é'`, avec `'\n'`, `'\t'`, `'\\'`, `'\''` : c'est un entier, le numéro Unicode.
- Littéral texte : `"bonjour"`. Il est rangé dans les données sous la forme **longueur, puis un caractère par mot**. Sa valeur est l'adresse de ce bloc.
- Fonctions du prélude : `longueur(t)`, `car(t, i)`, `texte_egal(a, b)`, `ecrire_texte(canal, t)`.
- Choix retenu : **un caractère par mot**. C'est simple et sans piège d'encodage, et la mémoire ne manque pas (64 millions de mots). Le rangement en quits viendra plus tard, si un besoin de place le justifie.

### 2.2 Mémoire allouée à la demande : le tas
- Un compilateur ne connaît pas d'avance la taille de ses listes (jetons, arbre du programme). Le **tas** occupe une zone réservée de l'étage 3.
- `nouveau(n)` rend l'adresse de `n` mots neufs (mis à zéro). `tas_marque()` et `tas_retour(m)` libèrent d'un coup tout ce qui a été pris depuis une marque.
- Pas de libération mot à mot : c'est la méthode habituelle des compilateurs (allocation par zones), simple et rapide.

### 2.3 Références à des structures
```
structure Noeud { valeur, gauche: Noeud, droite: Noeud }
soit n = Noeud { valeur: 7 };                       // les champs non nommés valent nul
soit arbre = Noeud { valeur: 1, gauche: Noeud { valeur: 2 } };
fonction profondeur(n: Noeud) { … }
```
- Une variable ou un paramètre déclaré avec le nom d'une structure est une **référence** : l'adresse d'un bloc du tas. `n.champ` lit ou écrit le champ.
- `nul` vaut 0 et désigne l'absence de bloc.

### 2.4 Listes qui grandissent
- `soit l = liste();`, `ajouter(l, x)`, `l[i]`, `taille(l)` : un bloc du tas qui double sa place quand il est plein.

### 2.5 Entrées et sorties par canaux (trois instructions nouvelles du SPU)

| Code | Nom | Effet |
|---|---|---|
| 51 | ENTC rd, rc | lit un mot sur le canal rc |
| 52 | SORC rs, rc | écrit le mot rs sur le canal rc |
| 53 | SYS rd, ra, rb | service de la machine hôte : ouvrir un fichier (nom en texte, mode), le fermer, savoir si la fin est atteinte |

- Canal 0 : les entrées et sorties actuelles (`entrée()`, `sortie()`), inchangées.
- Canal 1 : la console en texte, un caractère par mot.
- Canaux 2 et suivants : des fichiers. Langage : `soit c = ouvrir("prog.vtx", lecture);`, `lire_car(c)`, `ecrire_car(c, x)`, `fin(c)`, `fermer(c)`.
- Ce sont les premiers **périphériques** du SPU. L'écran, le clavier et la souris de Coatvtx viendront ensuite par le même mécanisme.

### 2.6 La logique à quatre valeurs dans le compilateur
Les analyses du compilateur écrit en vtx répondent par un `logique` : `vrai` (prouvé), `faux` (réfuté), `inconnu` (impossible à décider), `variable` (vrai sur un chemin, faux sur un autre). Exemple : la preuve d'indépendance des segments répond `inconnu` au lieu d'un « non » trompeur.

## 3. Le démarrage, et la preuve de l'autonomie

1. **Étape 0** : le compilateur écrit en vtx (`vtxc.vtx`) est compilé une dernière fois par `vtx.py`, ce qui donne le code M0.
2. **Étape 1** : M0, exécuté sur la machine Rust, compile `vtxc.vtx`, ce qui donne M1.
3. **Étape 2** : M1 compile `vtxc.vtx`, ce qui donne M2.
4. **Point fixe** : M1 et M2 doivent être identiques, mot pour mot. À partir de là, vtx n'a plus besoin de Python : il se compile lui-même.
5. **Juge** : pour chaque programme du corpus de conformité et pour des milliers de programmes aléatoires, le compilateur en vtx doit produire le même code machine que `vtx.py`.

## 4. Par étapes, sans perdre la vérification

- **Noyau d'abord** : le premier compilateur en vtx couvre ce dont il a besoin pour se compiler lui-même (entiers, texte, tas, structures, fonctions, contrôle). Le reste (flottants, longs, quits, logique, segments, partition, réécriture en 16, hypothèses) entre ensuite, une partie à la fois, chaque fois vérifiée contre `vtx.py`.
- **Machines** : les instructions 51 à 53 sont ajoutées à Python, Rust et aux deux JavaScript, et le corpus est enrichi.
- **Ordre général** : 1. figer la 0.5 (ce document) ; 2. la machine Rust : canaux de fichiers, multicœur ; 3. le compilateur en vtx et son point fixe ; 4. `vtx.exe` = la machine Rust qui embarque le compilateur vtx déjà compilé : plus besoin de Python ; 5. la traduction en code natif ; 6. Coatvtx.
- **Pourquoi pas un compilateur en Rust** : ce serait écrire le compilateur deux fois (en Rust, puis en vtx). Puisque le but est que vtx se compile lui-même, Rust ne fait que la machine ; c'est le compilateur en vtx, embarqué dans `vtx.exe`, qui remplace `vtx.py`.

## 5. État : le point fixe est atteint (étape 3)

`vtxc/vtxc.vtx` (environ 1 300 lignes de vtx) est le compilateur de vtx écrit en vtx. Il lit `source.vtx` sur le canal des fichiers et écrit `code.mots`.

- **Point fixe** : M0 = vtx.py(vtxc) fait 15 444 mots. M0, lancé sur la machine Rust, compile vtxc et donne M1 ; M1 compile vtxc et donne M2. **M0 = M1 = M2, mot pour mot.** Une compilation de vtxc par lui-même prend 110 millions d'instructions, soit environ un tiers de seconde sur la machine Rust.
- **Juge** : 1 000 programmes aléatoires du noyau (opérateurs, accès @étage et @(étage calculé), voies .r .v .b .a, fonctions, si, pour, tantque, retours anticipés, caractères, textes) : vtxc produit exactement les mots de `vtx.py` sans optimisation, 1000/1000.
- **Erreurs** : variable ou fonction inconnue, double déclaration, symbole manquant, `principal` absent, flottant : refusés avec la ligne, sans code écrit.
- Test : `vtxc/test_vtxc.py`, lancé par `verifier.py` quand cargo est présent.

**Ce que vtxc ne fait pas encore** (vtx.py reste nécessaire pour ces programmes) : flottants, longs, `<<q`/`>>q` et `.q()`, `logique` et `selon`, quits et tableaux de quits, segments et partition, hypothèses, `donnees`, imports, prélude, optimisations, vérification des types (vtxc accepte certains programmes que vtx.py refuse). Ils entreront un par un, chacun vérifié contre vtx.py ; la logique à quatre valeurs passe en premier, puisqu'elle est le cœur.

## 6. État : vtx.exe (étape 4)

La machine Rust se compile en deux exécutables identiques, `vtx-spu` et `vtx` (`vtx.exe` sous Windows). Ils embarquent vtxc déjà compilé (`vtx-rs/vtxc.mots`, 15 503 mots).

- `vtx programme.vtx [entrées]` compile avec vtxc, puis exécute. Python n'intervient pas.
- `vtx compiler programme.vtx` écrit seulement le code machine.
- `vtx renouveler vtxc.vtx` : après une modification du compilateur, vtxc se recompile lui-même. Le nouveau compilateur doit se reproduire à l'identique (point fixe) avant de remplacer `vtxc.mots`. Les messages d'erreur actuels (« variable inconnue : « x » ») ont été ajoutés ainsi, sans Python.
- Le test `vtxc/test_vtxc.py` vérifie aussi que le compilateur embarqué est bien `vtxc.vtx` compilé, et que `vtx essai.vtx` donne les mêmes sorties que vtx.py.

**Dépendance à Python, honnêtement** : pour le noyau du langage et pour faire évoluer le compilateur lui-même, il n'y en a plus. Elle reste pour tout ce que vtxc ne sait pas encore compiler (flottants, longs, quits, logique à quatre valeurs, segments, hypothèses, prélude, optimisations), et pour les tests, qui comparent à vtx.py. Chaque partie portée dans vtxc retire un morceau de cette dépendance.

## 7. La logique à quatre valeurs dans vtxc

vtxc compile maintenant le cœur quaternaire, avec exactement le code de vtx.py :
- **Logique** : le type `logique` (variables, paramètres, valeurs rendues, champs de structure) ; `vrai`, `faux` (qui restent 1 et 0 hors d'un contexte logique), `inconnu`, `variable` ; `et4`, `ou4`, `non4`, `anti`, `fusion`, `consensus`, sur un logique ou sur 16 logiques rangés dans un entier ; `logique(x)`, `comme_logique(x)`, `entier(l)` ; `selon … { vrai { } faux, inconnu { } autre { } }` ; comparaison `x == vrai`.
- **Quits** : `<<q`, `>>q`, `x.q(i)`, `min4`, `max4`, `addm4`, `gdot`, `cmp3`, `qegal`, `nb_bits` ; comparaisons signées `.<`, `.<=`, `.>`, `.>=`.
- **Refus**, comme vtx.py : un logique comme condition de `si` (il faut `selon`, ou `x == vrai`), `~`, `!` ou l'arithmétique sur un logique, une comparaison logique contre entier, une valeur nommée deux fois dans un `selon`, une branche inconnue.
- **Vérifié** : 2 000 programmes aléatoires de logique et de quits, 1 000 du noyau, et la démonstration `logique/capteurs.vtx` : code identique mot pour mot. Le point fixe tient (19 886 mots).
- **Sans Python** : le nouveau compilateur a été embarqué par `vtx renouveler vtxc.vtx`. L'ancien vtxc, qui ne connaissait pas la logique, a compilé le nouveau, puis le nouveau s'est recompilé lui-même à l'identique.

Reste à porter : tableaux de quits et de logiques, flottants, longs, segments et partition, hypothèses, `donnees`, imports, prélude, optimisations, et la vérification complète des types.

## 8. Tableaux, réécriture en 16, et inconnu / variable à l'épreuve

**Tableaux dans vtxc** : tableaux d'entiers, de structures (`t[i].champ`), de quits et de logiques (16 par mot). La réécriture automatique des boucles « 16 éléments d'un coup » est portée à l'identique : mêmes boucles reconnues (opérations quit par quit, comptages `si t[i] == … { n = n + 1; }`, sommes), même code. Vérifié sur 1 000 programmes aléatoires de tableaux (518 réécrits par vtx.py) : identiques mot pour mot. `genomique/motif.vtx` aussi. Le point fixe tient (26 598 mots), et le nouveau compilateur a de nouveau été installé sans Python.

**Démonstration** : `logique/initialisation.vtx`, l'analyse qu'un compilateur fait pour chaque variable lue : « a-t-elle reçu une valeur ici ? »
- `vrai` : sur tous les chemins ; `faux` : sur aucun ; `variable` : sur certains chemins seulement (le bogue caché) ; `inconnu` : aucun chemin n'y mène (code mort), et l'analyse n'invente rien.
- Les 16 variables d'un bloc tiennent dans un mot : une seule instruction `fusion` réunit ce que disent deux chemins pour les 16. Le bilan final est compté 16 à la fois (22 599 instructions au lieu de 36 008 sur l'exemple).
- Vérifié : l'exemple (une branche qui initialise, une boucle, une variable oubliée, un bloc mort) donne exactement vrai, variable, faux et inconnu là où il faut. Sur 300 graphes aléatoires, le résultat est identique à une référence Python, par vtx.py comme par vtxc sur la machine Rust sans Python. Un booléen aurait confondu 15 847 lectures : 3 843 erreurs certaines, 3 929 bogues dépendant du chemin, 8 075 dans du code mort.
- Honnêtement : Python ou Rust peuvent faire ce calcul (deux ensembles de bits, « peut-être initialisée » et « peut-être pas », c'est ce que font les compilateurs). Ce qui est propre à vtx : c'est un type du langage, deux bits par valeur, 16 valeurs par mot traitées par une instruction, et le compilateur refuse d'utiliser un logique comme un booléen. On est obligé de traiter `inconnu` et `variable` (`selon`, ou `x == vrai`).

## 9. Tout le langage dans vtxc

vtxc compile maintenant tout le langage, comme `vtx.py` sans optimisation, et `vtx.exe` le fait sans Python :
- **Flottants** : les nombres écrits en décimal sont lus au bit près comme Python (arrondi correct vers un double, puis vers binary32, au plus proche pair), avec de grands entiers écrits en vtx. Vérifié sur des milliers de valeurs : sous-normaux, bords, milieux exacts entre deux flottants.
- **Longs** (64 bits) ; conversions `flottant`, `entier`, `arrondi`, `racine`, `long`, `long_de`, `bas`, `haut`… ; `abs`, `min`, `max` en ligne pour les flottants et les longs.
- **Le prélude** (abs, min, max, divs, division des longs, exp2, textes, tas…), mot pour mot celui de vtx.py.
- **`donnees`**, **`importer`** (chemins relatifs, un fichier importé deux fois n'est lu qu'une fois, erreurs situées dans le bon fichier), **`adn"ACGT"`**, les noms d'étages `CPU`, `GPU`, `PARTAGE`, `DISQUE`.
- **Boucles `par`**, **boucles en segments** (`cumulant` compris, avec les règles d'indépendance), **hypothèses** (`annuler`, `valider`, journal des écritures).
- **Vérifié** : les 36 tests de vtx.py, ses 32 erreurs, les 20 programmes du paquet (feu de camp, ombre, jeu, orchestres…), le test différentiel complet, les programmes typés, les programmes aléatoires en segments : code identique mot pour mot. Le point fixe tient (54 260 mots).
- **Correction dans vtx.py** : un champ flottant d'une structure ne pouvait pas être lu dans un calcul flottant (« expression flottante inattendue »). C'est corrigé.

**Ce qui reste à porter** : les optimisations de vtx.py (sans elles, le code demande 1,45 à 1,75 fois plus d'instructions : 1,45 sur capteurs.vtx, 1,51 sur motif.vtx, 1,75 sur rayons.vtx) et la partition des tâches sur plusieurs cœurs. Après cela, vtx.py ne servira plus qu'aux tests.

## 10. Autonomie : vtx.exe fait tout ce que fait vtx.py pour compiler

vtxc porte maintenant aussi les optimisations et la partition :
- **Optimisations** (comme `vtx.py` par défaut) : élagage des fonctions jamais appelées (celles qu'on appelle quand même, comme la division des longs, sont produites à la demande, après les autres) ; sauts directs sur les conditions, sans fabriquer de booléen ; feuilles chargées directement sans passer par la pile.
- **Partition des tâches** : effets de chaque fonction (zones de mémoire lues et écrites, entrées et sorties, point fixe sur les appels) ; suites d'appels rangées en accords, mesure par mesure ; boucles en segments découpées (bornes, indépendance des segments, copies des tableaux cumulés puis leur somme) ; table des accords pour la machine Rust.
- **Vérifié** : code **et table des accords** identiques à `python vtx.py exporter` sur les programmes aléatoires du test de partition (suites d'appels, segments, cumulants), les tests de vtx.py et tous les programmes du paquet. `vtx programme.vtx` donne les mêmes sorties que vtx.py sur 1 et sur 2 cœurs (ombre, capteurs, génomique, orchestres, initialisation).
- **Le compilateur embarqué est lui-même optimisé** (53 803 mots au lieu de 65 671). `vtx renouveler` fait désormais trois tours : l'ancien compilateur compile le nouveau, qui se recompile, puis se recompile encore. Les deux derniers résultats doivent être identiques. Une amélioration du générateur de code peut ainsi passer sans Python.

**Ce que Python fait encore** : les tests (ils comparent vtxc à vtx.py), le débogueur pas à pas et le rapport lisible de la partition (notes, mesures). La compilation et l'exécution, elles, n'en ont plus besoin. Prochaine étape : la traduction en code natif (Cranelift).

## 11. Traduction en code natif (étape 5)

`vtx traduire programme.vtx` produit un exécutable natif, `programme` (ou `programme.exe` sous Windows), qu'on lance avec ses entrées.

- **Comment** : vtxc compile le programme. La traduction suit les sauts depuis l'adresse 0 et ne décode que les instructions : les données et les textes rangés après le code restent des données. Chaque bloc d'instructions devient une branche en Rust, les registres du SPU deviennent des variables, et rustc (LLVM) les met dans les registres du processeur. Un RET retrouve son point de retour parmi les instructions qui suivent les CALL.
- **Pourquoi rustc et pas Cranelift** : Cranelift aurait demandé de télécharger des bibliothèques, et l'accès aux bibliothèques Rust est bloqué dans mon environnement de travail : je n'aurais pas pu la vérifier. rustc est déjà installé avec Rust, chez toi comme ici. Son optimiseur, LLVM, va plus loin que Cranelift ; en contrepartie, la traduction prend quelques secondes (4 s pour l'ombre, 8 s pour le feu de camp) au lieu d'être immédiate.
- **Vérifié** : les 470 programmes du corpus de conformité, traduits et compilés, donnent les mêmes nombres d'instructions, les mêmes sorties et la même mémoire que toutes les autres machines. Les programmes du paquet (capteurs, génomique, initialisation, ombre, feu de camp) donnent les mêmes sorties que la machine interprétée.
- **Vitesse** (même machine, un cœur) : ombre 256³, 5,74 s interprétée contre 0,46 s native (×12,4) ; image complète du feu de camp, 3,94 s contre 0,33 s (×12,1). Le feu de camp entier se calcule en un tiers de seconde.
- **Accords sur plusieurs cœurs** : le code natif joue les accords comme la machine interprétée. Une adresse où commence un accord confie ses mesures à `jouer_accord`, qui lance les tâches d'une mesure sur plusieurs fils. Chaque tâche est la même fonction native, lancée à son adresse de début et arrêtée à son adresse de fin, avec une copie du cadre courant dans sa propre zone de pile. Les adresses de la table des accords commencent toujours un bloc, et le test d'arrêt n'est fait qu'à ces adresses : il ne coûte rien ailleurs.
- **Vérifié** : sur 15 programmes aléatoires à accords (suites d'appels, segments, cumulants), sorties identiques à la machine interprétée sur 1, 2 et 3 cylindres.
- **Mesuré** (2 cœurs) : ombre 256³, 0,52 s natif sur 1 cylindre, 0,31 s sur 2 (× 1,65), contre 5,74 s pour la machine interprétée sur un cœur, soit 18 fois plus vite en tout. Le feu de camp ne gagne rien à un second cœur : son analyse à la demande écrit pendant le rendu, et le compilateur ne peut donc pas le découper en tâches indépendantes (cela pourra venir avec des écritures à quatre valeurs).

## 12. L'atelier en console

`vtx atelier programme.vtx` : un éditeur, la compilation et l'exécution (F5, avec vtxc embarqué), et le cube, c'est-à-dire un étage de la mémoire dessiné en couleurs vraies, un mot `#RRGGBBAA` par pixel, deux pixels par caractère grâce au demi-carré « ▀ ». Aucune bibliothèque : le terminal est piloté par les séquences ANSI ; le mode brut passe par `stty` sous Linux et macOS, par `SetConsoleMode` et `ReadConsoleW` (kernel32) sous Windows. La lecture directe par `ReadConsoleW` évite la lecture de Rust, qui prend Ctrl+Z pour une fin de fichier.

Vérifié ici dans un pseudo-terminal (`atelier/test_atelier.py`, 10 vérifications : sorties, image de `rayons.vtx` dans l'étage 2, retrait automatique, ligne d'erreur en rouge, annulation, sortie sans enregistrer). La partie Windows a été vérifiée par le compilateur seulement : elle reste à essayer sur une vraie console Windows.

Pas encore : le pas à pas (il faut que vtxc produise la correspondance entre adresses et lignes du source), les registres et la pile pendant l'exécution, et la vue des accords. Ensuite viendra la fenêtre graphique indépendante (Win32), puis l'écran, le clavier et la souris du SPU, pour que coatvtx soit lui-même un programme vtx.

## 13. Afficher, mathématiques, hasard

`sortie(x)` écrit le mot brut, sans signe : c'est voulu (canal des tests), mais illisible pour un humain. Le prélude gagne `afficher(x)`, qui choisit sa version selon le type de x (entier signé, flottant, long, logique, texte littéral), les fonctions `ecrire_entier`, `ecrire_flottant`, `ecrire_long`, `ecrire_logique`, `ecrire_hexa`, les mathématiques en flottant (`pi`, `plancher`, `plafond`, `sinus`, `cosinus`, `tangente`, `exponentielle`, `logarithme`, `puissance`, `arctangente`, `arctangente2`, `arcsinus`, `arccosinus`), et le hasard reproductible (`graine`, `hasard`, `hasard_entre`, `hasard_flottant`, `hasard_mot`, xorshift de 32 bits dont l'état est en `@3[14680057]`). Tout est écrit en vtx ; vtx.py et vtxc donnent les mêmes mots (`maths/test_maths.py`).

En chemin, un défaut ancien de vtxc est apparu et a été corrigé : une fonction écartée par l'élagage puis demandée pendant la génération était produite deux fois, et une fonction qu'elle demandait à son tour était perdue. Les longs ne le montraient pas, parce que la fonction en double masquait la perte.

## 14. bruit, hypothèses, pas à pas, atelier.exe

- `bruit()` : nouveau service SYS 5 sur les quatre machines (Python : `os.urandom` ; Rust et code natif : l'aléa de la bibliothèque standard, l'horloge et un compteur ; JavaScript : `Math.random`). `graine_bruit()` et `bruit_logique()` dans le prélude. `hasard()` reste reproductible.
- `exemples/hasard/reines.vtx` : hasard, logique à quatre valeurs (`fusion(faux, vrai) = variable` signale la contradiction) et hypothèses (`annuler` défait les cases écrites) ensemble. Il a montré un défaut de vtx.py (la reconnaissance d'un compteur dans une boucle échouait sur `si … { x = 1; }`), corrigé ; vtxc n'avait pas ce défaut.
- Pas à pas : vtxc écrit, sur demande (4ᵉ drapeau d'entrée), la table adresse → ligne du fichier (sans le prélude ni les fichiers importés), en troisième partie de code.mots. L'atelier exécute instruction par instruction (la boucle de la machine garde maintenant son état quand elle s'arrête sur la limite d'instructions) : F7, F8, F9, F5.
- `atelier.exe` : le même programme que `vtx.exe`, qui reconnaît son nom et ouvre l'atelier ; sans fichier, la liste des fichiers du paquet. Double-clic ou « Ouvrir avec » sous Windows.
- L'atelier a une barre des menus (Fichier, Édition, Exécuter, Cube, Aide ; F10, Alt+lettre ou la souris), la sélection (Maj+flèches, souris), couper/copier/coller avec le presse-papiers de Windows, annuler/rétablir, rechercher, enregistrer sous.
- Le paquet livré est allégé : les tests de développement (vérificateur, corpus de conformité, test_*.py) sont gardés à part et passés avant chaque livraison.

## 15. La fenêtre de l'atelier (Windows)

`atelier.exe` est, sous Windows, une fenêtre Win32 écrite directement (user32, gdi32, comdlg32, sans bibliothèque) : menus, boutons, le contrôle d'édition de Windows (souris, presse-papiers, annulation), le cube dessiné par GDI, la sortie. Le cube en perspective isométrique voit un étage comme 256 × 256 × 256 mots (adresse = x + 256 y + 65 536 z) et dessine chaque mot non nul en petit cube ombré ; les petits nombres prennent une palette selon leur grandeur. Le rendu est dans `cube.rs`, commun à la fenêtre et à `vtx image` (qui l'écrit en PPM, ce qui permet de le vérifier hors de Windows). Le code Windows est vérifié par le compilateur ; son essai réel se fait sur la machine de l'utilisateur.

## 16. Type texte et afficher à plusieurs valeurs

- Type `texte` : reconnu par une passe (`typer_textes`, dans vtx.py et dans vtxc) avant l'élagage et la partition, qui réécrit `+`, `==`, `!=`, `afficher`, `ecrire`, `texte()` et `afficher(a, b, c)` en appels du prélude ; le type redevient entier pour la génération du code. La partition voit donc les appels qui écrivent dans le tas. Écrire dans un texte passe par `__mettre` : les fonctions d'écriture du prélude écrivent sur un canal ou dans un texte en construction.
- Une écriture simplifiée (point-virgule facultatif, sections de déclarations, bibliothèques par leur nom) a été essayée puis retirée à la demande de l'utilisateur : elle sera repensée autrement.

## 17. Correction d'erreur diamant

Bibliothèque `bibliotheque/diamant.vtx`. Damier (détection : 30 bits, parité) et diamant (correction : 26 bits ; 3 quits de contrôle aux poids 1, 4 et 16, signature pondérée modulo 33 : +1 sur le quit k donne k + 1, −1 donne 33 − (k + 1)). L'état est un logique : vrai, faux (corrigé), variable (contradiction), inconnu (mot nul). Vérifié contre une référence Python : 4 361 lectures identiques, toutes les erreurs simples corrigées. Canal à 1 % d'erreur par quit : 12 % de mots faux sans code, 0,8 % avec. Deux erreurs : 23 % signalées, la plupart mal corrigées.

## 18. Tableaux dynamiques, vocabulaire, fenêtre d'exécution, association des fichiers

- Tableau dynamique : poignée dans le tas, trois mots `[n, capacité, adresse des données]` ; `t[i]` devient deux lectures d'étage 3. Littéral `[a, b]`, `tableau t[n]` local, `pour x dans t`. Mêmes mots par vtx.py et vtxc (`vtxc/test_tableaux.py`).
- Vocabulaire du prélude : listes (ajouter, retirer, inserer, enlever, indice, contient, trier…), dictionnaire à hachage FNV (dico, ranger, trouver, existe, cles), textes (decouper, assembler, remplacer, majuscules…), `lire_ligne`.
- Console de la machine Rust : canal 1 vers stdin (question affichée avant la lecture) ou vers la fenêtre d'exécution de l'atelier (canaux entre fils, arrêt vérifié toutes les 2^20 instructions).
- `vtx installer` : association `.vtx`, icône du cube écrite par la machine elle-même (ICO et PNG sans bibliothèque).
- Testé sur Windows (21 octobre 2026) : construction propre, fenêtre d'exécution, question au clavier, Arrêter. Corrigé après l'essai : collage multi-lignes (fins de ligne), F5 sur un fichier sans nom, ligne du compilateur dans la fenêtre du programme, temps d'attente du clavier compté comme calcul.

## 19. Tableaux de flottants et savoir à quatre valeurs

- `flottant[]` : la passe `typer_textes` (vtx.py et vtxc) reconnaît les tableaux de flottants (déclaration, paramètre, retour, littéral avec un flottant écrit, `copie`) ; `t[i]` devient `comme_flottant(t[i])`, une écriture range `bits(...)` (un nombre écrit est converti dès la compilation), `somme`/`trier` deviennent `__somme_f`/`__trier_f` (clé de tri : bits inversés pour les négatifs). La variable d'un `pour x dans t` prend le type de ses valeurs.
- Dictionnaire à états (poignée de 6 mots : n, capacité, clés, valeurs, états, ouvert) : `affirmer`, `nier`, `savoir` (logique de Belnap : inconnu = ni l'un ni l'autre, variable = les deux), `dico_ouvert`, `nommer`. Mêmes mots par les deux compilateurs (`vtxc/test_tableaux.py`).

## 20. Atelier : terminal, arbre des liaisons, dessin ; ScoR v0

- Sous le cube : un terminal (sortie du programme en direct, la ligne du dessous répond à `lire_ligne()`, commandes de l'atelier entre deux exécutions) et l'arbre des liaisons (`arbre.rs`, indépendant de Windows : objets du tas reconnus par leur forme, racines = objets que rien dans le tas ne désigne, dicos avec leurs quatre états, journal des hypothèses). `vtx arbre` l'écrit en texte. Numéros de ligne, image des programmes qui dessinent (`ecran`, `pixel`, `trait`, `rectangle`, `disque`, `rgb` : prélude en vtx, donc identique pour les deux compilateurs ; `vtx dessin` en PNG). Testé sur Windows : terminal, réponse au clavier, arbre et ses couleurs, étage 3 choisi seul.
- ScoR v0 (`scor/`) : graine hex, quatre points par mot, mémoire courte et sommeil (consolidation à deux occurrences), rêve en ressorts (rapport liés/hasard 0,99 → 0,14), ombre (seuls les mots consolidés sortent au cube), spirale à énergie d'activation (≈ 4 % du cube), épissage de Belnap et recherche contraire (anti-cube). 25 réponses sur 56 appuyées par des phrases ; limite : trois dimensions restent étroites.

## 21. ScoR v1 : le raisonnement ; atelier : onglets Sortie et Terminal

- Relations « X est Y » / « X n'est pas Y » lues dans les phrases ; déduction en chaînes sur le réseau orienté, en logique de Belnap : chaîne affirmée → vrai ; chaîne jusqu'à un « N n'est pas Y » → faux ; les deux sans fait direct → variable (diamant de Nixon) ; un fait direct contraire à une règle héritée → exception, le plus précis l'emporte ; rien → inconnu. Chaque conclusion donne sa preuve (phrases par lien). `qu'est-ce que X`, `lien X Y` (chemin dans l'ADN). Faits d'essai `scor/faits.md` : 8 conclusions attendues sur 8 (`scor/test_scor.py`).
- Atelier : onglets Sortie (compte rendu de l'exécution) et Terminal (interactif), comme VS Code ; Nouveau et Ouvrir effacent les résultats de toutes les vues.
- La voix : `parler(t)` (prélude, canal `voix:`, System.Speech sous Windows, espeak ailleurs) ; le ScoR répond à voix haute aux questions tapées. Corrigé dans vtx.py : un texte écrit dans une fonction du prélude prenait l'étiquette du premier texte du programme (le prélude a maintenant la même numérotation que le programme) ; vtxc était juste.

## 22. La mémoire qui se libère et qui dure ; le ScoR se souvient et apprend en parlant

- Tas à en-têtes (taille avant chaque bloc), listes de blocs libres par taille, `liberer`, ramasse-miettes prudent `ramasser()` (racines : la pile depuis `pile()`, les poignées protégées ; marquage par tableaux de bits posés au-dessus du tas ; balayage par la chaîne des en-têtes), `__texte_fin` qui ne rétrécit que le dernier bloc. Services 6 et 7 (blocs binaires) dans les trois machines ; `sauver_tas` / `charger_tas`. Mesuré (`vtxc/test_memoire.py`) : 101 867 mots libérés sur 105 079 ; 900 tableaux neufs sans faire grandir le tas ; souvenirs sur trois lancements.
- La voix passe aussi par la machine principale (vtx.exe, l'atelier) : elle n'était que dans la traduction en code natif.
- ScoR : recharge sa mémoire (1,3 s au lieu de 7 s), apprend ce qu'on lui affirme (« le chat est noir ») et dit ce qu'il en pensait avant (il le savait, il l'ignorait, ou il avait compris le contraire), « dors » consolide, la mémoire est ramassée puis enregistrée en partant.

## 23. Mémoire à la demande et cubes additionnés par fréquence

- La machine Rust réservait 256 Mo par exécution (jusqu'à trois à la fois dans l'atelier), comptés par Windows même inutilisés. Désormais : l'étage 0 (code et pile, lu à chaque instruction) d'un seul bloc de 64 Mo, les étages 1 à 3 en pages de 65 536 mots créées à la première écriture non nulle ; une page jamais écrite désigne une page nulle partagée (aucun test à la lecture). Même vitesse qu'avant (1,02 s contre 1,07 à 1,14 s sur 20 millions de tours). L'atelier rend la mémoire du programme précédent avant chaque exécution.
- Cubes par fréquence : chaque étage 1 à 3 regarde le cube de sa fréquence ; `accorder(étage, f)` range les 256 pages de l'étage sous l'ancienne fréquence et sort celles du cube f (services 8 et 9, dans les trois machines). Mesuré (`vtxc/test_memoire.py`, `exemples/premiers/cubes.vtx`) : trois cubes sur un étage retrouvés intacts, deux cubes pleins sur un autre, mêmes résultats en Rust et en Python, mêmes mots par les deux compilateurs.
- Les cœurs : la machine utilise (nombre de cœurs − 1) cylindres, mais seulement pour les accords (tâches prouvées indépendantes par le compilateur) ; un programme sans accord tourne sur un cœur.

## 24. Purge automatique, cœurs limités, fichiers « voix: »

- Bogue trouvé par un essai à deux fois la taille du tas : quand le tas était plein de petits blocs libres, une demande plus grande rendait `nul` sans que personne ne le voie ; `ajouter` écrivait alors à l'adresse 0, et le ramassage suivant libérait ce qui était encore tenu. Corrigé : balayage qui refait les listes en fondant les blocs libres voisins (et fait redescendre le tas), grands blocs découpés à la demande, purge automatique quand le tas est plein (sans acharnement), arrêt clair « mémoire pleine » (service 10) au lieu d'une écriture à l'adresse 0. Mesuré : 120 000 tableaux (deux fois le tas) gardés justes ; 8 lancements de suite qui rechargent, allouent 40 000 tableaux de 5 à 300 cases, ramassent et sauvent, tous justes. Les fichiers de mémoire portent un numéro de format : un fichier d'un autre format est ignoré.
- Cylindres : 2 par défaut, 8 au plus (et jamais plus que de cœurs) ; VTX_ROTOS les change dans ces limites.
- Deux fichiers nommés « voix: » s'étaient glissés dans le paquet (écrits par la machine avant qu'elle ne reconnaisse ce canal) : le « : » est interdit dans un nom Windows, d'où l'erreur 0x80070057 à la copie. Retirés, et exclus des paquets.
- À corriger : `soit faux = 0;` est accepté mais `faux` reste la constante ; une variable ne devrait pas pouvoir porter le nom d'une constante.


## 25. Variables en registres (R9 à R12)

- Les registres ne sont pas des cubes : R0 à R15 sont seize mots de 32 bits dans le processeur (R0 vaut toujours 0, R13 le cadre, R14 la pile). Jusqu'ici chaque variable vivait dans une case du cadre, en mémoire : chaque lecture était un LDF, chaque écriture un STF. R9 à R12 ne servaient à rien.
- Choix des variables : on compte les usages de chacune, pondérés par la profondeur de boucle (×8 par niveau, jusqu'à trois) ; la variable d'un `pour` compte en plus quatre usages par tour. Seules celles qui atteignent 16 (donc utilisées dans une boucle) ont droit à un registre ; les quatre meilleures prennent R9, R10, R11, R12 (à égalité, la plus haute dans le cadre). Pas pour les longs, ni pour les variables cachées des tableaux rangés, ni dans une fonction qui a des accords, des segments ou une hypothèse, ni au pas à pas (le débogueur lit les variables dans le cadre).
- Convention : la fonction range ces registres dans des cases cachées de son cadre à l'entrée et les remet à la sortie (registres « gardés par l'appelé »). Un paramètre en registre est chargé une fois à l'entrée.
- Les opérations lisent leurs opérandes directement dans les registres (`ADD R1,R9,R10`, `CMP R9,R2`), et `x = a op b` calcule directement dans le registre de x (`ADDI R9,R9,#1` pour `i = i + 1`).
- Ramasse-miettes : il trouve les adresses vivantes en lisant la pile. Une adresse tenue seulement dans R9 à R12 lui échapperait ; une fonction qui lit la pile (`pile()`) range donc toujours les quatre registres dans son cadre, où la lecture les trouve.
- vtx.py et vtxc font exactement le même choix et produisent les mêmes mots (vérifié sur les exemples, le prélude, le ScoR et vtxc lui-même, qui atteint son point fixe en se compilant avec registres). Bogue évité au passage : dans vtxc les décalages du cadre sont des entiers de 32 bits non signés, la comparaison « plus haute dans le cadre » se fait donc en signé.
- Mesures : boucle serrée (20 millions de tours) sur la machine Rust 1,02 s → 0,63 s ; instructions exécutées : tableaux −9,8 %, flottants −6,8 %, questions −5,5 %, savoir −4,9 %. Le reste du coût est dans les PUSH/POP et les copies (`MUL R1,…` puis `MOV R2,R1`) : c'est le travail de la représentation intermédiaire, étape suivante.

## 26. Sauts sur 20 bits, prélude à la demande, noms de variables

- **Bogue trouvé : le code ne pouvait pas dépasser 65 536 mots.** L'adresse d'un saut (JMP, JZ, JNZ, JC, JNC, CALL) tenait dans 16 bits (octets g et b du mot). Au-delà, les bits de trop débordaient sur le code d'opération : un JMP pouvait devenir un JZ. vtxc compilé sans optimisation (le compilateur de référence M0 du test) venait de passer 65 536 mots avec les variables en registres : il ne compilait plus rien, et le test du point fixe échouait. Le vérificateur l'avait signalé (« 1 étape en échec ») mais je ne l'avais pas vu, et la version déposée sur GitHub le 22 octobre avait ce défaut (le vtxc embarqué, optimisé, restait sous la limite : `vtx` et l'atelier marchaient).
- Correction : l'adresse d'un saut a maintenant 20 bits ; les 4 bits de plus vont dans les 4 bits bas du dernier octet du mot, toujours à 0 jusqu'ici (un programme ancien reste valable). Le code peut atteindre 1 048 576 mots. Changé partout où un saut est écrit ou lu : l'assembleur et la machine de vtx.py, vtxc, la machine Rust, la traduction en code natif, les deux machines JavaScript, le désassembleur. Un saut plus loin est refusé par l'assembleur avec un message clair.
- Le vérificateur nomme maintenant les étapes en échec, et le test du débogueur rend un code d'erreur quand une vérification échoue (avant, il l'écrivait sans échouer).
- **Prélude à la demande.** vtxc lisait tout le prélude (148 fonctions, 36 000 caractères) à chaque compilation : c'était l'essentiel du temps. Avec les optimisations, il ne lit plus que les fonctions dont le nom paraît dans le programme, celles qu'appelle le compilateur lui-même (`nouveau`, `divs`, `__texte_plus`, les versions typées d'`afficher`…), celles qui écrivent un texte (vtx.py garde tous les textes du prélude), et de proche en proche celles qu'elles appellent. Le code produit est identique (la génération ne gardait de toute façon que les fonctions appelées). Sans optimisation, rien n'est élagué et tout le prélude est lu, comme vtx.py. Mesure : un programme d'une ligne passe de 197 ms à 100 ms (compilation et exécution).
- **Variables au nom d'une constante.** `soit K = 5;` après `constante K = 3;` était accepté, mais chaque lecture de K rendait 3. vtx.py refusait déjà `soit faux = 0` (nom de la logique à quatre valeurs), vtxc l'acceptait. Les deux refusent maintenant, pour une variable, un paramètre ou une variable de boucle, les noms de la logique à quatre valeurs (vrai, faux, inconnu, variable, et4…) et ceux des constantes (`constante`, `nul`, CPU, GPU, PARTAGE, DISQUE). Quatre cas ajoutés aux erreurs testées.
- Registres et tableaux rangés : vtx.py écrit l'indice d'une lecture de tableau de logiques ou de quits deux fois (le mot, puis la place dans le mot) ; vtxc le compte maintenant deux fois aussi, sinon les deux compilateurs ne choisissaient pas les mêmes variables pour les registres.

## 27. La représentation intermédiaire : l'épissage

- Après la génération d'une fonction, ses instructions sont relues comme une suite d'opérations simples, chacune avec les registres qu'elle lit et ceux qu'elle écrit : c'est la représentation intermédiaire. Elle est ensuite « épissée », comme un ARN messager dont on retire les introns : les instructions qui ne font que déplacer une valeur.
- Quatre règles, essayées dans cet ordre à chaque instruction, tour après tour jusqu'à ce que rien ne change :
  - **pile** : `PUSH R1 ; S ; MOV R2,R1 ; POP R1` devient `S` (où R1 est remplacé par un registre libre Rf) puis `MOV R2,Rf` : la pile devient un registre ;
  - **constante** : `ADDI Rk,R0,#c ; ADD Rd,Ra,Rk` devient `ADDI Rd,Ra,#c` (de même pour SUB) ;
  - **relecture** : `STF Ra,#o ; LDF Rb,#o` garde seulement l'écriture (et `MOV Rb,Ra` si les registres diffèrent) ;
  - **copie** : `OP Rx,… ; MOV Ry,Rx` devient `OP Ry,…`.
- Chaque règle exige qu'un registre soit mort (sa valeur ne sera plus lue, sur aucun chemin). On le sait par l'analyse de vie des registres R1 à R8 sur le graphe de la fonction, sauts compris : un appel détruit R1 à R8, un retour lit R1 et R4, une instruction mal connue les lit tous (prudence). L'analyse est refaite au début de chaque tour ; une règle appliquée la laisse juste ou prudente pour le reste du tour. Seules les étiquettes visées par un saut séparent deux instructions.
- Pas d'épissage au pas à pas (le débogueur suit les instructions d'origine), ni dans `__init`, ni dans les fonctions à accords, segments ou hypothèses.
- vtx.py l'applique sur ses lignes d'assembleur, vtxc sur ses mots (en déplaçant ensuite étiquettes et renvois de sauts) : les deux produisent exactement les mêmes mots, vtxc compris quand il se compile lui-même (97 183 mots identiques).
- Mesures (instructions exécutées, en plus des registres) : tableaux −16 %, questions −20 %, savoir −16 %, flottants −10 %, calcul −9 % ; code 9 à 12 % plus court. La boucle serrée perd une instruction sur huit. Sur la machine Rust : vitesse 0,52 s (1,02 s avant les registres). Le test différentiel (oracle Python) ne voit aucun écart ; le code optimisé fait 38 % d'instructions de moins que le code simple.
- Coût : vtxc compile un peu plus lentement (tableaux 261 → 306 ms) ; l'analyse de vie est la prochaine chose à accélérer.

## 28. Instructions quaternaires LDQ et STQ (quits rangés)

- Mesure d'abord : suivre les constantes en vrai / faux / inconnu / variable dans l'épissage (l'idée proposée à la section 27) ne trouvait que 32 calculs connus sur 34 750 instructions (0,1 %) dans tous les exemples et le ScoR. Abandonnée.
- Le vrai coût quaternaire était ailleurs : un tableau de quits ou de logiques range 16 éléments par mot, et lire un élément demandait 5 à 6 instructions binaires (adresse du mot, décalage, masque), en écrire un une dizaine. Le génome rangé en quits coûtait 2,5 fois le génome « une base par mot ».
- Deux instructions nouvelles du SPU : **LDQ Rd, Rs, Rt, @e** (0x54) lit le quit `(e:[Rs + (Rt >> 4)] >> ((Rt & 15) × 2)) & 3` ; **STQ Rd, Rs, Rt, @e** (0x55) y écrit `Rd & 3` sans toucher aux 15 autres quits du mot. Ajoutées partout : assembleur et machine de vtx.py, machine Rust, traduction en code natif, les deux machines JavaScript, désassembleur, spécification (section des instructions).
- Les compilateurs reconnaissent la forme qu'ils fabriquent pour `t[i]` et `t[i] = v` et émettent LDQ / STQ, quand l'indice est simple (un nombre, une variable, ou a + b, a − b, a × b de ceux-là, le même aux deux places) ; vtx.py et vtxc font le même test et produisent les mêmes mots. Sans optimisation, rien ne change.
- Mesures (instructions, vtx.py) : génome de 16 384 bases lu base par base 8,67 M → 3,70 M (le tableau de quits coûte maintenant 1,08 fois le tableau ordinaire, avec 16 fois moins de mémoire) ; préparation du génome 1,45 M → 0,94 M.
- Le corpus de conformité gagne 5 programmes qui emploient LDQ et STQ (assembleur, tableaux de quits et de logiques sur les étages 1 à 3, génome) : Python, Rust, code natif et les deux machines JavaScript donnent les mêmes résultats.
- Bogue trouvé au passage : le code natif lisait le vrai clavier dans le corpus de conformité (programmes avec `lire_ligne`), alors que l'interprète n'y lit rien ; en vérification complète, la sortie se décalait. Corrigé : le corpus natif ne lit plus le clavier.

## 29. La mémoire qui dure, vraiment ; la logique de Belnap en instructions

- **Bogue de la mémoire qui dure** (vu dans le build.log du 22 octobre : « je suis  lancé 5 fois ; premier ami :  ») : un texte écrit entre guillemets reste dans le code (étage 0). Rangé dans un objet du tas, il n'y était qu'une adresse dans le code ; une fois le programme recompilé, le code bouge et l'adresse ne montre plus le bon texte. Les tests ne le voyaient pas : ils relançaient la même version.
- Correction : quand un texte est rangé dans le tas (champ d'une structure, construction, case d'un tableau dynamique, `ajouter`, `inserer`, `ranger`, `affirmer`, `nier`, tableaux écrits `[…]`), le compilateur l'enveloppe dans `__texte_tas` (prélude), qui le recopie dans le tas s'il vient du code (étage 0) et le laisse tel quel sinon. vtx.py et vtxc le font aux mêmes endroits (mêmes mots). Nouveau test : la mémoire est rechargée par une autre version du programme, les textes restent justes. Une mémoire déjà abîmée ne se répare pas : il faut la recommencer.
- **Instructions de Belnap** : ET4 (0x56), OU4 (0x57), NON4 (0x58), ANTI (0x59) traitent les 16 quits d'un mot en une instruction (il en fallait 7 à 10) ; EXQ (0x5A) lit un quit d'un registre (`x.q(i)`, il en fallait 4). Dans les quatre machines, la traduction native, l'assembleur, les deux compilateurs et l'épissage ; 3 programmes de plus au corpus de conformité (toutes les machines identiques).
- Pourquoi si tard : le socle a été construit sur les opérations binaires de la machine hôte pour avoir vite des compilateurs et des machines identiques ; le quaternaire est venu par couches (quits, logique à quatre valeurs, QEGAL, COMPTE, tableaux de quits, LDQ/STQ, Belnap). Ce n'était pas une impossibilité. Les entiers, eux, sont déjà quaternaires : un mot de 32 bits est exactement 16 chiffres en base 4, et l'addition binaire est l'addition quaternaire chiffre par chiffre.

## 30. L'atelier : pas à pas dans la fenêtre, vue quaternaire

- Fini le doublon : le pas à pas ne lance plus l'atelier en console dans une seconde fenêtre. Dans la fenêtre même : F7 ligne suivante (en entrant dans les fonctions), F8 sans y entrer, F9 point d'arrêt (●) sur la ligne du curseur, F5 continuer, Échap ou Maj+F5 arrêter ; la ligne courante est marquée ▶ en jaune dans la gouttière (le curseur s'y place sans rien choisir : une touche n'efface pas la ligne). Modifier le texte arrête le pas à pas ; un programme fini passe sa mémoire au cube et à l'arbre.
- Onglet « Pas à pas » : R1 à R12, puis R13, R14, Z, C, pc, puis le cadre de la fonction (−1 à −8, +2 à +5), chacun en décimal signé, en quaternaire (16 quits, du quit 15 au quit 0, par groupes de 4) et en logique de Belnap (un logique seul par son nom ; un mot par ses 16 quits : · inconnu, f faux, v vrai, ± variable).
- Vue « en quits » du cube (F6 : perspective → à plat → en quits) : chaque mot en 4 × 4 cases de couleur de Belnap ; le clic sur un mot donne aussi ses quits et sa logique. Le décodage d'un mot (terminal `mot`, arbre) gagne une ligne « logique ». Nouvelle commande `vtx quits PROG.vtx image.png [ÉTAGE] [BASE] [LARGEUR]`.
- Vérification : la fenêtre (Win32) ne se construit pas ici (Linux, sans la cible Windows) ; elle est vérifiée par le compilateur Rust avec l'option `verif_fenetre` (`cargo check --features verif_fenetre`), puis construite sur le PC.
