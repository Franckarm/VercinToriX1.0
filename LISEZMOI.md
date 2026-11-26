# Vercintorix (vtx) 0.845

**Pour commencer : lisez `COMMENCER.md`** (construire la machine, Ogmios, premiers programmes) ; **la référence du
langage : `docs/vtx-langage.md`** ; les fondements gravés : `docs/vtx-carnet.md`, section 1 bis.

Tous droits réservés : voir `AUTEUR.md`.

## Où en est vtx (26 novembre 2026, 0.845)

- **Lugus compte en 128 bits** : l'entier et le flottant par défaut ont la largeur du mot (le hex, l'ADN, l'ARN, le cube
  chromatique), dans les deux compilateurs (les mêmes mots), le prélude, la forge et Gobannos.
- **Les cubes nommés** (0.845) : `cube relief @2;`, `@relief[i]` ; le compilateur choisit les fréquences et refuse deux
  cubes qui se recouvrent, sur Lugus et sur Dunon. `exemples128/cubes_nommes.vtx`.
- **Dunon pour le graphique** : `dunon;` en tête d'un programme le fait compter en 64 bits, comme la carte (Taranis) et le
  C++ de référence ; Gergovie, l'épreuve du graphique, y est, avec les mêmes empreintes au processeur et sur la carte.
- **Les agents** : le Vergobret (l'exécution : la carte ou le processeur, les fils), Gutuater (la forge et la garde),
  le Druide (la mémoire des bornes, les cellules, l'évolution) ; leur mémoire vit dans le **nemeton**
  (`~/.vercintorix/nemeton/PROG`), qui survit aux paquets. Ésus, dans la forge : les opérations de 64 bits prouvées.
- L'ombre de Belenos est revenue au calcul exact (la décision du créateur, le 26 novembre) ; les essais approchés
  (la clepsydre progressive, l'éventail, les deux faces) sont gardés dans la branche `ombre-approchee`.
- Le journal de passation : `docs/vtx-passation.md` ; les décisions et leurs raisons : `docs/vtx-reactions.md`.

Langage, compilateurs, machines et atelier du SPU à cube chromatique.

## Les machines : Lugus est la machine de vtx

| Machine | Mot | Rôle | Compilateurs |
|---|---|---|---|
| **Lugus** (SPU-128) | 128 bits, le point de matière | **la machine de vtx** : tout ce qui est nouveau y vient d'abord (les réactions, l'ADN protégé, la provenance) | `vtx128.py`, `vtxc128` (écrit en vtx, embarqué dans `lugus`) |
| **Dunon** (SPU-64) | 64 bits, le point profond | la référence et la compatibilité : son langage tourne aussi sur Lugus (le mode compatible) | `vtx64.py`, `vtxc64` |
| **Senos** (SPU-32) | 32 bits | la référence d'origine | `vtx.py`, `vtxc` |

Senos et Dunon gardent le langage d'avant les réactions ; ils y viendront pour la rétrocompatibilité. Chaque machine a
deux compilateurs qui donnent exactement les mêmes mots, et ses programmes peuvent être forgés en code natif.

## Ce que Lugus réunit

- **Les réactions** (`docs/vtx-reactions.md`) : chaque ligne est un atome, chaque `->` une liaison. Les atomes sont
  rangés par vagues, donc l'ordre des lignes ne compte pas ; les atomes d'une même vague réagissent ensemble, sur
  plusieurs cœurs une fois forgés.
  - **La sûreté** : les contrats (`exige`, `garantit`), les exemples vérifiés à chaque compilation (`exemple f(2) ==
    4`, rejoués aussi par Lugus sans Python), les unités physiques vérifiées par le compilateur (`= 9.81 m/s² -> g`),
    qui ne coûtent rien à l'exécution ; une liaison qui peut porter faux se rend en logique (faux) ou en flottant
    (inconnu) ; une division par zéro donne une liaison variable avec sa cause (`erreur(x)`, `reparer x par v`).
  - **Les tableaux** (`pour chaque` sans réduction, `pour chaque x dans t`, `garder x dans t si …`), **plusieurs
    résultats** (`-> q, r`) et **`selon`** dans les réactions.
  - **Le calcul incrémental** : chaque atome lourd garde ses souvenirs dans une colonne de seize places, rangée comme
    Fischer. Rappelé avec des entrées déjà vues, il ne réagit pas (10 fois moins d'instructions sur une scène
    d'animation).
  - **La provenance** : `lugus pourquoi PROG.vtx [liaison]`, ou Ctrl+P dans l'atelier, remonte une valeur jusqu'à ses
    constantes et à ses entrées.
- **Le chemin Cube → Hex → ADN → ARN** :
  - l'ADN, c'est le programme rangé avec ses trois témoins (signature, ombre, neutrons) : `lugus ranger PROG.vtx` ;
  - `lugus PROG.adn` le vérifie, le répare si besoin, puis l'épissage retire les témoins et l'ARN (les mots seuls) est
    lancé ;
  - mesuré : 6 % de place, réparé jusqu'à huit mots abîmés de suite, jamais réparé de travers ;
  - **l'ADN vivant** : il garde aussi le texte (recompilé, il doit redonner les mots), les isotopes lourds
    (`-> a lourd`) et l'épigénome (`lugus apprendre` : les souvenirs appris, repris au lancement suivant) ; sur demande
    (`--veille`) ou pour les isotopes lourds, la patrouille relit le code pendant l'exécution et le répare ; un isotope
    lourd abîmé pendant qu'il sert arrête la machine (l'apoptose) ; `lugus transcrire PROG.adn PROG.arn` tire de
    l'ADN son ARN, l'ARNc, qui porte tout, avec une coiffe vérifiée (0.66 : il se lance aussi rapide, `--rapide`) ; `lugus relire PROG.adn` fait la
    même lecture avec le lecteur écrit en vtx (`chimie/adn.vtx`), forgeable en exécutable (docs/vtx-reactions.md,
    section 9).
  - **dans les deux sens** (0.6n bis) : `lugus retrotranscrire PROG.arn` refait l'ADN d'un ARN (l'ADNc, réparé par ses
    témoins s'il en a) ; `lugus hex PROG.adn` écrit les mots en hex, chacun à sa place du cube ; `lugus cube PROG.adn`
    les range dans le cube (`cube128-1-440.cub`, avec son anti-cube et son ombre) ; `lugus ranger` reprend un hex ou un
    cube en ADN, et `lugus PROG.hex`, `lugus cube128-1-440.cub` se lancent (docs/vtx-reactions.md, section 49).
- **L'atelier Ogmios** (`atelier.exe`) : le texte à gauche, **la paillasse au centre** (les réactions dessinées en
  atomes et liaisons, rangées en vagues, dans les deux sens avec le texte : tirer une liaison, ajouter ou retirer un
  atome réécrit la ligne), le cube à droite ; en bas, Sortie, Terminal, Pas à pas, Arbre et la fenêtre des explications.
  Sur Lugus, F5 range aussi l'ADN, et Ctrl+P fait réagir : chaque liaison montre sa valeur. Les trois machines (Ctrl+M).
- **Ogmios écrit en vtx** (`ogmios/ogmios.vtx`, premier temps) : l'atelier dans le langage, qui tourne sur Lugus.
  `vtx toile128 ogmios/ogmios.vtx --fichier PROG.vtx` : édition en couleurs, Ctrl+S, F5 (le programme compilé par vtxc128
  et lancé sur une machine fille), Ctrl+Q.
- **La forge** : un programme devient un exécutable natif, par Rust (`python forge/forge128.py PROG.vtx`), avec les
  mêmes sorties que la machine émulée.
- **La toile** : le service d'image de la machine (la souris, le clavier, l'horloge, les GIF). Le nom Gobatix est
  réservé au futur logiciel de modélisation et d'animation (`docs/gobatix-vision.md`).

L'histoire complète, les choix et les mesures : `docs/vtx-carnet.md` et `docs/archives/vtx-0-5-autonomie.md`.

## Ce qu'il faut

- **Python 3.9 ou plus récent** : c'est tout pour écrire, compiler, exécuter et déboguer des programmes vtx. `vtx.py` n'utilise que la bibliothèque standard.
- Facultatif : **numpy** (`pip install numpy`) pour le test des flottants et des longs ; **Node.js** pour les machines JavaScript ; **Rust** (`cargo`) pour la machine Rust : installation pas à pas dans `vtx-rs/LISEZMOI.md`.

Pour commencer simplement : `COMMENCER.md` (vtx.exe et Ogmios, sans Python). Les tests de développement (vérificateur,
corpus de conformité, tests de chaque partie) sont passés avant chaque livraison et restent dans le dépôt ; le paquet
emporte à leur place **l'épreuve d'Alésia** : `python epreuve/epreuve.py` montre et vérifie en une quinzaine de
secondes ce que fait Vercintorix (créer, programmer, compter, douter, réagir, se souvenir, se défendre), et dit les
brèches connues. Les `.bat` d'essai livrés à côté du paquet, eux, ne mesurent que la nouveauté.

## Premiers pas

Avec Lugus (`vtx-rs/target/release/lugus`, construit par `cargo build --release` dans `vtx-rs`), sans Python :

```
lugus exemples128/panel.vtx                         # une réaction : 42
lugus pourquoi exemples128/panel.vtx r2             # d'où vient ce 42
lugus ranger exemples128/chute.vtx                  # l'ADN : chute.adn
lugus exemples128/chute.adn                         # vérifié, réparé si besoin, lancé sous la patrouille
lugus apprendre exemples128/alternance.adn          # (après lugus ranger) ses souvenirs gardés dans l'ADN
lugus transcrire exemples128/chute.adn chute.arn   # l'ARNc : il garde ses témoins, son texte, ses souvenirs
lugus carte exemples128/chute.vtx                   # la carte : ce qu'est chaque fonction, ce qu'elle touche, ses racines, ses promesses
lugus exemples128/supposons.vtx                    # supposons x parmi [ … ] { ecarter; noter n; } retenir r; : essayer, garder le meilleur
lugus exemples128/valeurs.vtx                     # les fonctions passées en valeur : pour_chacun(t, carre), plier(t, plus, 0)
lugus exemples128/types_fonction.vtx              # le type d'une fonction : fonction(entier): entier, vérifié
lugus exemples128/promesse_type.vtx              # la promesse dans le type : fonction(entier): entier touche rien
lugus exemples128/nombres.vtx                    # le vocabulaire des nombres : un mot pour tous les types, le doute gardé
lugus exemples128/vocabulaire.vtx                # 0.61 : le vocabulaire étendu (Rust, Arduino, UE5, Blender), en français
vtx64 exemples128/vocabulaire.vtx                # le même sur Dunon
lugus exemples128/modules.vtx                    # un module promis par son empreinte (lugus empreinte FICHIER la donne)
lugus gobannos/gobannos.vtx                       # Gobannos (en vtx) : PROG.mots, PROG.exe, windows -> l'exécutable, sans Rust
lugus arnc exemples128/chute.vtx                    # le programme né en ARN (l'ARNc), sans fichier d'ADN
lugus retrotranscrire exemples128/chute.arn         # l'ARN fixé en ADN : chute-c.adn (entier, depuis un ARNc)
lugus hex exemples128/chute.adn                     # les mots en hex : chute.hex
lugus cube exemples128/chute.hex                    # dans le cube : cube128-1-440.cub, puis : lugus cube128-1-440.cub
vtx paillasse exemples128/chute.vtx --valeurs --png chute.png   # la paillasse sans écran, avec les valeurs
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

La référence complète du langage est dans `docs/vtx-langage.md`. Le jeu d'instructions du SPU est dans `docs/archives/specification-spu-v0-5.md`, section 5. Les limites connues sont à la fin de la référence et dans le carnet.
