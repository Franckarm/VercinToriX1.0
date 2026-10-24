# Vercintorix (vtx) 0.5

**Pour commencer : lisez `COMMENCER.md`** (construire vtx.exe, installer l'éditeur, premiers programmes).

Tous droits réservés : voir `AUTEUR.md`.

Langage, compilateur, assembleur et émulateur du SPU à cube chromatique.

## Ce que la 0.5 réunit

- **Le SPU-64** : mots de 64 bits, points profonds `#RRRRGGGGBBBBAAAA`, adresses longues (étage, cube, `#RRGGBB`), brin
  ADN et ARN de chaque mot, flottant quaternaire de 64 bits par défaut (32 et 128 au choix). Machines Python et Rust
  identiques (`spu64/`, `docs/specification-spu64.md`).
- **vtx64.py** (le compilateur de référence du SPU-64) et **vtxc64** (le compilateur écrit en vtx, qui se compile lui-même
  au point fixe), qui donnent toujours les mêmes mots (`docs/vtx64-langage.md`).
- **vtx64.exe sans Python** : `vtx64 programme.vtx` compile avec vtxc64 embarqué et exécute ; l'**atelier** travaille par
  défaut sur la SPU-64 (Ctrl+M : SPU-32).
- **Les optimisations** : variables en registres, épissage (dont la règle échange, comme l'auto-épissage des introns),
  expansion en ligne des petites fonctions, tables de noms dans les cubes.
- **Gobatix interactif** : la souris, le clavier, la molette, l'horloge et la cadence des images pour les programmes
  qui dessinent, sur les deux machines ; l'atelier montre l'animation pendant qu'elle tourne et l'enregistre en GIF
  (Ctrl+G), écrit par différence d'une image à l'autre ; l'anti-cube des couleurs pour les curseurs et les objets
  animés (`exemples/gobatix/peindre.vtx`).
- Le SPU-32 (vtx.py, vtxc, `vtx.exe`) reste là ; il reçoit les mêmes fonctions de Gobatix.

L'histoire complète, les choix et les mesures : `docs/vtx-carnet.md` et `docs/vtx-0-5-autonomie.md`.

## Ce qu'il faut

- **Python 3.9 ou plus récent** : c'est tout pour écrire, compiler, exécuter et déboguer des programmes vtx. `vtx.py` n'utilise que la bibliothèque standard.
- Facultatif : **numpy** (`pip install numpy`) pour le test des flottants et des longs ; **Node.js** pour les machines JavaScript ; **Rust** (`cargo`) pour la machine Rust : installation pas à pas dans `vtx-rs/LISEZMOI.md`.

Pour commencer simplement : `COMMENCER.md` (vtx.exe et atelier.exe, sans Python). Les tests de développement
(vérificateur, corpus de conformité, tests de chaque partie) ne sont plus dans ce paquet, pour l'alléger : ils sont
gardés à part et passés avant chaque livraison.

## Premiers pas

Ouvrez un terminal dans ce dossier, puis :

```
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
| `jeu3/`, `jeu2/` | le jeu « Labyrinthe du cube » en vtx |
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
