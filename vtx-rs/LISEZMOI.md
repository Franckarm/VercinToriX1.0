# Émulateur du SPU en Rust (vtx-spu)

Même sémantique que `vtx.py` et les machines JavaScript. Aucune bibliothèque externe : il se compile sans connexion au registre crates.io.

## Installer Rust pas à pas (Windows)

1. **Outils de compilation C++ de Microsoft** (Rust s'en sert pour assembler le programme final). Téléchargez « Build Tools for Visual Studio » sur le site de Microsoft (visualstudio.microsoft.com, rubrique Téléchargements, « Outils pour Visual Studio »). Dans l'installateur, cochez **« Développement Desktop en C++ »**, puis installez. Si Visual Studio (pas VS Code) est déjà installé avec cette charge de travail, sautez cette étape.
2. **Rust** : sur https://rustup.rs, téléchargez `rustup-init.exe`, lancez-le, et acceptez l'installation par défaut (touche Entrée).
3. **Fermez et rouvrez** tous les terminaux (et VS Code), pour qu'ils trouvent `cargo`.
4. Vérifiez dans un terminal : `cargo --version` doit afficher un numéro de version.
5. **VS Code** : onglet Extensions (Ctrl+Maj+X), cherchez et installez **rust-analyzer** (éditeur : rust-lang). C'est facultatif pour compiler, mais il colore et vérifie le code.
6. Dans VS Code : Fichier > Ouvrir le dossier… > le dossier `vtx-0.5`. Terminal > Nouveau terminal.

Sous macOS ou Linux, l'étape 1 n'existe pas : `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`, puis rouvrir le terminal.

## Compiler et vérifier

Dans le terminal, depuis le dossier `vtx-0.5` :

```
cd vtx-rs
cargo build --release
```

La première compilation prend une minute environ. Elle produit `target\release\vtx.exe` et `target\release\atelier.exe`. (Les tests de conformité ne sont plus dans le paquet allégé ; ils sont passés avant chaque livraison.)

## En cas de problème

- « linker `link.exe` not found » : l'étape 1 manque (outils C++).
- « cargo n'est pas reconnu » : rouvrir le terminal (étape 3), ou redémarrer l'ordinateur.
- Un antivirus peut ralentir la première compilation ; c'est sans conséquence.
- rust-analyzer dit « failed to find any projects » : il cherche `Cargo.toml` dans le dossier ouvert. Ouvrez le dossier `vtx-0.5` (le fichier `.vscode/settings.json` lui indique `vtx-rs/Cargo.toml`) ou directement `vtx-rs`. Cela ne gêne pas la compilation.

## vtx.exe : compiler et exécuter sans Python

La compilation produit deux exécutables identiques : `vtx-spu` et son nom court `vtx` (`vtx.exe` sous Windows, dans `target\release`). Ils embarquent **vtxc**, le compilateur de vtx écrit en vtx (`vtxc/vtxc.vtx`), déjà compilé par lui-même (`vtxc.mots`).

```
vtx programme.vtx 3 4          compile programme.vtx avec vtxc, puis l'exécute avec les entrées 3 et 4
vtx ..\logique\initialisation.vtx 9 3 0 0 0 2 1 0 4 1 1 1 0 0 1 1 0 5 2 2 3 0 8 2 4 6 8 0 1 5 0 16 1 5 0 1 0
                               l'analyse d'initialisation à quatre valeurs, sans Python
vtx compiler programme.vtx     écrit seulement le code machine dans programme.prog
vtx traduire programme.vtx     traduit en code natif : un exécutable programme (programme.exe sous Windows),
                               qu'on lance avec ses entrées : programme 3 4 ; il faut rustc (installé avec Rust)
vtx renouveler vtxc.vtx        après une modification de vtxc : il se recompile lui-même, vérifie le point fixe
                               (le nouveau compilateur se reproduit à l'identique), puis écrit vtxc.mots ;
                               refaire cargo build --release pour l'embarquer
```

Ce que vtxc compile : **tout le langage**, avec le prélude, les fichiers importés, **les optimisations de vtx.py** et **la partition des tâches en accords** : le code et la table des accords sont identiques à ceux de `python vtx.py exporter`. `vtx programme.vtx` joue donc les accords sur les cœurs de la machine moins un (la variable d'environnement `VTX_ROTOS` fixe un autre nombre : *rotos*, la roue en gaulois). Python ne sert plus qu'aux tests, au débogueur et au rapport lisible de la partition.

## Commandes

| Commande | Effet |
|---|---|
| `vtx PROG.vtx [ENTRÉES…]` | compile avec vtxc embarqué, puis exécute ; les fichiers du programme sont ouverts dans le dossier courant |
| `vtx compiler PROG.vtx [SORTIE]` | compile seulement ; écrit « mots; » dans SORTIE (par défaut PROG.prog), lisible par `lancer` |
| `atelier.exe [PROG.vtx]` | sous Windows, la fenêtre de l'atelier (menus, boutons, éditeur, cube en perspective ou à plat, sortie) ; ailleurs, l'atelier en console |
| `vtx image PROG.vtx SORTIE.ppm [étage] [plan\|iso] [entrées…]` | lance le programme et écrit l'image du cube (perspective ou à plat) |
| `vtx atelier PROG.vtx` | l'atelier en console : éditeur, compilation et exécution (F5), et le cube : un étage de la mémoire dessiné en couleurs, un mot `#RRGGBBAA` par pixel (voir COMMENCER.md) |
| `vtx traduire PROG.vtx [SORTIE]` | traduit en code natif : vtxc compile, le code du SPU devient du Rust, rustc (LLVM) en fait un exécutable ; même résultat, environ 12 fois plus vite sur un cœur ; les accords sont joués sur les cœurs de la machine moins un (`VTX_ROTOS` pour en fixer le nombre : *rotos*, la roue en gaulois) |
| `vtx renouveler VTXC.vtx` | recompile vtxc par lui-même et remplace `vtxc.mots` si le point fixe est atteint |
| `vtx64 PROG.vtx [ENTRÉES…]` | la machine 64 bits : vtxc64 (embarqué) compile, la SPU-64 exécute ; aussi `vtx64 compiler PROG.vtx`, `vtx64 renouveler vtxc64.vtx` (voir docs/vtx64-langage.md, section 9). L'atelier travaille par défaut sur la SPU-64 (Ctrl+M : SPU-32) |
| `vtx-spu corpus FICHIER` | rejoue un corpus (une ligne « mots;entrées » par programme), mémoire neuve à chaque programme |
| `vtx-spu session FICHIER [N]` | première ligne : les mots ; lignes suivantes : entrées d'appels successifs qui partagent la mémoire ; la dernière est rejouée N fois et chronométrée |
| `vtx-spu lancer FICHIER [MAX_PAS] [CYLINDRES]` | un programme « mots;entrées;table » : instructions, durée, sorties, puis le texte de la console. Avec la table des accords (produite par `python vtx.py exporter prog.vtx [entrées] > prog.txt`), les tâches d'une mesure sont jouées sur plusieurs cœurs : par défaut les cœurs de la machine moins un |

## Mesures (même ordinateur, une image du jeu, 1 372 871 instructions)

| Machine | Temps par image | Instructions par seconde |
|---|---|---|
| Rust, interprète | 3,6 ms | 378 millions |
| JavaScript, interprète | 6,4 ms | 213 millions |
| JavaScript, traduit en fonctions | 2,0 ms | 675 millions |

Les prochaines étapes : jouer les cylindres (segments) sur plusieurs cœurs, puis un traducteur vers le code machine de l'ordinateur (Cranelift), qui devrait dépasser la traduction JavaScript ; ce sont des estimations à mesurer.
