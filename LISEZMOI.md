# Vercintorix (vtx) 0.5

**Pour commencer : lisez `COMMENCER.md`** (construire vtx.exe, installer l'éditeur, premiers programmes).

Tous droits réservés : voir `AUTEUR.md`.

Langage, compilateurs, machines et atelier du SPU à cube chromatique.

## Les machines : Lugus est la machine de vtx

| Machine | Mot | Rôle | Compilateurs |
|---|---|---|---|
| **Lugus** (SPU-128) | 128 bits, le point de matière | **la machine de vtx** : tout ce qui est nouveau y vient d'abord (les réactions, l'ADN protégé, la provenance) | `vtx128.py`, `vtxc128` (écrit en vtx, embarqué dans `lugus`) |
| **Dunon** (SPU-64) | 64 bits, le point profond | la référence et la compatibilité : son langage tourne aussi sur Lugus (le mode compatible) | `vtx64.py`, `vtxc64` |
| **Senos** (SPU-32) | 32 bits | la référence d'origine | `vtx.py`, `vtxc` |

Senos et Dunon gardent le langage d'avant les réactions ; ils y viendront pour la rétrocompatibilité. Chaque machine a
deux compilateurs qui donnent exactement les mêmes mots, et ses programmes peuvent être forgés en code natif.

## Ce que la 0.5 réunit sur Lugus

- **Les réactions** (`docs/vtx-reactions.md`) : chaque ligne est un atome, chaque `->` une liaison. Les atomes sont
  rangés par vagues, donc l'ordre des lignes ne compte pas ; les atomes d'une même vague réagissent ensemble, sur
  plusieurs cœurs une fois forgés.
  - **La sûreté** : les contrats (`exige`, `garantit`), les exemples vérifiés à chaque compilation (`exemple f(2) ==
    4`, rejoués aussi par Lugus sans Python), les unités physiques vérifiées par le compilateur (`= 9.81 m/s² -> g`),
    qui ne coûtent rien à l'exécution ; une liaison qui peut porter faux se rend en logique (faux) ou en flottant
    (inconnu).
  - **Le calcul incrémental** : chaque atome lourd garde ses souvenirs dans une colonne de seize places, rangée comme
    Fischer. Rappelé avec des entrées déjà vues, il ne réagit pas (10 fois moins d'instructions sur une scène
    d'animation).
  - **La provenance** : `lugus pourquoi PROG.vtx [liaison]`, ou Ctrl+P dans l'atelier, remonte une valeur jusqu'à ses
    constantes et à ses entrées.
- **Le chemin Cube → Hex → ADN → ARN** :
  - l'ADN, c'est le programme rangé avec ses trois témoins (signature, ombre, neutrons) : `lugus ranger PROG.vtx` ;
  - `lugus PROG.adn` le vérifie, le répare si besoin, puis l'épissage retire les témoins et l'ARN (les mots seuls) est
    lancé ;
  - mesuré : 6 % de place, réparé jusqu'à huit mots abîmés de suite, jamais réparé de travers.
- **L'atelier Ogmios** (`atelier.exe`) sur les trois machines (Ctrl+M) : édition, F5, pas à pas, vue du cube, la toile.
  Sur Lugus, F5 range aussi l'ADN, et Ctrl+P donne la provenance.
- **Ogmios écrit en vtx** (`ogmios/ogmios.vtx`, premier temps) : l'atelier dans le langage, qui tourne sur Lugus.
  `vtx toile128 ogmios/ogmios.vtx --fichier PROG.vtx` : édition en couleurs, Ctrl+S, F5 (le programme compilé par vtxc128
  et lancé sur une machine fille), Ctrl+Q.
- **La forge** : un programme devient un exécutable natif, par Rust (`python forge/forge128.py PROG.vtx`), avec les
  mêmes sorties que la machine émulée.
- **La toile** : le service d'image de la machine (la souris, le clavier, l'horloge, les GIF). Le nom Gobatix est
  réservé au futur logiciel de modélisation et d'animation (`docs/gobatix-vision.md`).

L'histoire complète, les choix et les mesures : `docs/vtx-carnet.md` et `docs/vtx-0-5-autonomie.md`.

## Ce qu'il faut

- **Python 3.9 ou plus récent** : c'est tout pour écrire, compiler, exécuter et déboguer des programmes vtx. `vtx.py` n'utilise que la bibliothèque standard.
- Facultatif : **numpy** (`pip install numpy`) pour le test des flottants et des longs ; **Node.js** pour les machines JavaScript ; **Rust** (`cargo`) pour la machine Rust : installation pas à pas dans `vtx-rs/LISEZMOI.md`.

Pour commencer simplement : `COMMENCER.md` (vtx.exe et atelier.exe, sans Python). Les tests de développement
(vérificateur, corpus de conformité, tests de chaque partie) ne sont plus dans ce paquet, pour l'alléger : ils sont
gardés à part et passés avant chaque livraison.

## Premiers pas

Avec Lugus (`vtx-rs/target/release/lugus`, construit par `cargo build --release` dans `vtx-rs`), sans Python :

```
lugus exemples128/panel.vtx                         # une réaction : 42
lugus pourquoi exemples128/panel.vtx r2             # d'où vient ce 42
lugus ranger exemples128/chute.vtx                  # l'ADN : chute.adn
lugus exemples128/chute.adn                         # vérifié, réparé si besoin, lancé
vtx toile128 ogmios/ogmios.vtx --fichier exemples128/chute.vtx   # Ogmios écrit en vtx (F5, Ctrl+S, Ctrl+Q)
```

Avec Python, les compilateurs de référence et les outils :

```
python3 vtx128.py run exemples128/chute.vtx           # Lugus émulé
python3 vtx128.py molecule exemples128/panel.vtx      # la molécule : vagues, formule, souvenirs, place selon Fischer
python3 chimie/adn.py essai                           # les avaries de l'ADN, mesurées
# Senos (SPU-32), la référence d'origine :
python3 vtx.py test                                   # les tests intégrés du langage
python3 vtx.py run exemples/chariot.vtx 0xE03020FA 14 1
python3 vtx.py deboguer debogueur/demo.vtx            # tapez « aide » ; « q » pour quitter
python3 vtx.py partition partition/orchestre.vtx      # partition automatique des tâches
python3 vtx.py partition partition/orchestre_segments.vtx   # la même, avec des boucles en segments
python3 vtx.py partition partition/orchestre_cumul.vtx --cylindres 4   # histogramme cumulé, temps sur 4 cœurs
```

Sous Windows, remplacez `python3` par `py` ou `python`.

## Commandes de vtx.py

| Commande | Effet |
|---|---|
| `run prog.vtx [entrées]` | compile et exécute ; les entrées sont des nombres (décimal ou `0x…`) |
| `profil prog.vtx [entrées]` | exécute et compte les instructions par sorte et les accès par étage |
| `compile prog.vtx` | affiche l'assembleur produit |
| `asm prog.vtx` | affiche le code machine en mots `#RRGGBBAA` |
| `trace prog.vtx [entrées] [--max N] [--regs]` | une ligne par instruction machine |
| `deboguer prog.vtx [entrées]` | débogueur interactif au niveau du source |
| `partition prog.vtx [entrées]` | affiche les accords, mesures et notes, et le temps gagné |
| `exporter prog.vtx [entrées]` | écrit « mots;entrées;table des accords » pour la machine Rust multicœur (`vtx-spu lancer`) |
| `test` | tests du langage |

## Contenu

| Dossier ou fichier | Rôle |
|---|---|
| `vtx.py` | la chaîne complète : langage, compilateur, assembleur, émulateur de référence, débogueur, partition |
| `vtx-rs/` | émulateur en Rust (sans dépendance), 1,8 fois plus rapide que l'interprète JavaScript ; voir son LISEZMOI |
| `machines/` | émulateurs JavaScript (`vm_rapide.js` interprète, `vm_traduite.js` traduction en JavaScript, environ 3,5 fois plus rapide), utilisés par le jeu dans le navigateur ; `conformite.js` les vérifie. La machine Java a été retirée : Rust la remplace |
| `bibliotheque/` | `cube.vtx` (voies du mot RGBA, gris, distance, mélange, centrage), `adn.vtx` (couche ADN et ARN), `fixe.vtx` (64 bits et virgule fixe 16.16), avec leurs tests |
| `exemples/` | chariot d'usine, appariement spectral, mémoire associative, canal caché T/U, lancer de rayons, démonstration |
| `jeu3/`, `jeu2/` | le jeu « Labyrinthe du cube » en vtx ; `jeu3/labyrinthe.vtx` : le jeu complet sur la toile |
| `forge/` | la forge : vtx en code natif par Rust (`forge.py`, `noyau_forge.rs`), et son test contre la machine émulée |
| `debogueur/` | programme de démonstration du débogueur et son test |
| `partition/` | démonstrations de la partition des tâches (sans segments, en segments, avec tableaux cumulés) et leur test |
| `ombre/` | ombre binaire du cube : volume en voxels, ombre fine et grossière, rayons qui sautent le vide ; test contre une référence numpy |
| `compression/` | compression du cube par blocs et palettes (1 quit par voxel), forme ADN rangée et transcription en ARN ; test contre une référence Python |
| `logique/` | logique à quatre valeurs (vrai, faux, inconnu, variable ; `selon`, `fusion`, `anti`) et capteurs bruités, 16 logiques par mot |
| `genomique/` | recherche d'un motif d'ADN avec erreurs : tableaux de quits, instructions QEGAL et COMPTE (×6 sur la méthode classique) |
| `vectorise/` | réécriture automatique des boucles sur les tableaux de quits et de logiques, 16 éléments d'un coup ; test différentiel |
| `feu/` | feu de camp en voxels : ombre quaternaire (vide, brume, plein, inconnu), rendu PBR en vtx, animation par la mémoire du cube (`feu-anime.gif`) |
| `multicoeur/` | la machine Rust qui joue les tâches d'une mesure sur plusieurs cœurs : test d'équivalence avec la séquence |
| `conformite/` | corpus de 470 programmes et résultats attendus : toute nouvelle machine doit les reproduire |
| `tests/` | test différentiel, priorités des opérateurs, flottants et longs |
| `docs/` | référence du langage 0.4, spécification du SPU v0.5, carnet de bord |
| `labyrinthe-du-cube.html` | le jeu jouable, à ouvrir dans un navigateur |

## Pour aller plus loin

La référence complète du langage est dans `docs/vtx-syntaxe-v0-4.md`. Le jeu d'instructions du SPU est dans `docs/specification-spu-v0-5.md`, section 5. Les limites connues sont à la fin de la référence et dans le carnet.
