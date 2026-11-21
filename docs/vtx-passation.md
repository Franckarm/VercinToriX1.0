# Passation : pour reprendre Vercintorix dans une nouvelle conversation (21 novembre 2026, après la 0.64)

*À lire en premier par la prochaine conversation. L'état, les règles de travail, les outils, et ce qui reste à décider
avec le créateur.*

## 1. Où en est le projet

- Le dépôt : `github.com/Franckarm/vercintorix1.0`, branche **`vtx-0.6`** (dernier état : la 0.64, vérifiée
  « Tout est conforme » ; `essai-0.64.bat` déposé chez le créateur, son essai à lire dans `essai-0.64.log`). Œuvre protégée (`AUTEUR.md`) : rien hors de ses
  dossiers et des artefacts privés.
- Les machines : **Lugus** (SPU-128, la machine de vtx), **Dunon** (SPU-64, le même travail à 64 bits), Senos (SPU-32,
  gelé). Ogmios l'atelier, Belenos le moteur graphique, Taranis la carte graphique, Gobannos le forgeron (les .exe, écrit
  en vtx).
- Fait récemment : 0.61, le vocabulaire étendu (203 mots, `docs/vtx-vocabulaire.md`) ; 0.61b, les modules promis par leur
  empreinte (`importer "x.vtx" empreinte "16hex";`, `lugus empreinte`, `vtx-reactions.md` §64) ; 0.61c, `reste` exact sur
  les flottants (§65) ; **0.62, le catalogue des modules et la vibration des molécules (§66)** : lister un dossier
  (service 28, `lister_dossier`, `dossier_present`), `lugus cataloguer DOSSIER` (écrit en vtx, dans le lecteur d'ADN),
  `importer empreinte "16hex";` sans chemin, la vibration de chaque molécule (`lugus morceaux`), et la carte qui dit
  d'où vient chaque molécule (et voit une retouche).
- Les journaux : `docs/vtx-reactions.md` (sections 1 à 69), `docs/vtx-carnet.md` (les fondements, section 1 bis ; la
  feuille de route, section 11), `docs/vtx-syntaxe-v0-4.md` (la référence du langage).

## 2. Les règles de travail (à garder)

- Répondre en français, honnêtement, avec des arguments ; dire ce qui ne marche pas.
- **Les deux compilateurs de chaque machine donnent les mêmes mots** (vtx128.py et vtxc128 pour Lugus, vtx64.py et vtxc64
  pour Dunon). Tout ajout dans les deux ; les programmes déjà écrits gardent leurs mots (`outils/avant_apres.py`).
- Le créateur lance lui-même les `.bat` : les déposer dans `G:\Boulot\Code\Vercintorix1.0 rust\Claude outputs\` (envoi
  du fichier, puis dépôt sur son PC). Ne jamais lancer le `.bat`, ne jamais prendre le contrôle de son écran.
- Un nom neuf à chaque livraison (le prochain : `vtx-0.65.zip`, `essai-0.65.bat` ; le `.bat` pose `set PYTHONUTF8=1`). Les `.bat` en CRLF et ASCII, sans
  accents ; le `.bat` écrit aussi dans le journal ce qu'il montre à l'écran ; il ne joue que la nouveauté.
- Commits sur `vtx-0.6`, jamais de force ; tuer un processus par son numéro, jamais `pkill -f`.
- L'adresse électronique du créateur ne part vers aucun service sans son accord.
- Le prélude : pas de texte entre guillemets ; dans le prélude, un mot à variantes n'est jamais appelé avec des flottants
  (appeler la variante) ; `v[i]` d'un tableau de flottants lit un entier (passer par `__vt_lire`, `__vt_ecrire`).

## 3. Les outils (dans `outils/`)

- `outils/renouveler.sh` : refait le vocabulaire et les préludes de vtxc, renouvelle vtxc128 et vtxc64 (point fixe),
  recompile la machine. À lancer après toute retouche d'un compilateur ou du prélude.
- `outils/memes_mots128.py PROG.vtx`, `outils/memes_mots64.py PROG.vtx` : MEMES ou DIFF entre les deux compilateurs.
- `outils/avant_apres.py 128 ANCIEN_vtx128.py` (ou 64) : tous les programmes, ancien contre nouveau compilateur.
- `outils/lecteur.sh` (0.62) : recompile le lecteur d'ADN en vtx (`chimie/adn.vtx`) et l'embarque dans Lugus
  (`vtx-rs/lecteur_adn.mots`) ; à lancer après toute retouche du lecteur.
- Le cube du catalogue de `bibliotheque/` (`cube128-1-392.cub`, son anti-cube, son ombre, et `catalogue.vtxcat`) est
  gardé dans le dépôt : le refaire (`lugus cataloguer bibliotheque`) après toute retouche d'un module de la
  bibliothèque (sinon `importer empreinte` le refuse, l'empreinte ayant changé).
- `outils/tests_du_paquet.txt` : les tests mis dans le paquet ; la commande du paquet : `git archive --format=zip
  --prefix=vtx-0.6/ -o vtx-0.65.zip HEAD AUTEUR.md COMMENCER.md LISEZMOI.md vtx.py vtx64.py vtx128.py vtx-rs vtxc spu64
  spu128 chimie natif gobannos exemples exemples128 exemples64 bibliotheque docs` suivi de ces tests et de
  `tests/test_supposons.py tests/supposons_alors.vtx tests/test_gobannos.py tests/gobannos tests/test_valeurs.py
  tests/valeurs_mele.vtx tests/test_types_fonction.py tests/test_gobannos_flottants.py tests/test_nombres.py
  tests/nombres tests/test_vocabulaire_etendu.py tests/vocabulaire tests/test_modules.py tests/modules
  tests/test_reste.py tests/test_catalogue.py tests/test_cube_mere.py tests/test_faces_cube.py tests/test_valeurs64.py tests/test_fma.py` et des nouveaux.
- La vérification complète : `python3 verifier.py` (environ deux heures ; elle doit finir par « Tout est conforme ») ;
  la lancer en arrière-plan et la suivre.
- La machine : `cd vtx-rs && cargo build --release` (binaires `lugus`, `vtx64`, `vtx`, `atelier`).

## 4. Ce qui reste, décidé avec le créateur (après la 0.64)

Fait le 21 : la 0.64 (**les faces dans le cube**, §69) : à la même fréquence, le code à l'étage Đ (le tau gallicum,
l'étage 0, le choix du créateur : 440/Đ), les trois axes du dé aux étages 1, 2, 3, chaque molécule à la place de son
début ; `face(f, k)`, `centre(f)` (le service 31) ; le cube mère sur ses quatre étages, 64 bits par étage (0.64b, la demande du créateur).

**Gobannos, les fichiers dans les .exe : en attente.** Le 18, un filtre de sécurité automatique a arrêté la réponse
qui écrivait le code machine des appels au système (les fichiers, le chemin du programme, la mémoire) ; ce travail ne
doit pas être repris sous une autre forme par l'IA. Le créateur l'a signalé à Anthropic, et peut l'écrire lui-même (les
routines du socle de Gobannos servent de modèle). Mesuré avant l'arrêt : Gobannos et vtxc128 ont besoin des services
1 à 4 (les fichiers) et 13 (jeter un cube), en plus du 26.

**L'ordre donné le 21** : les points du langage d'abord (les faces : fait ; les fonctions passées en valeur sur Dunon :
fait, 0.65, §70 ; `multiplier_ajouter` en un seul arrondi : fait, 0.65, §71 ; puis simplifier), puis Ogmios et la
paillasse.

(Ce qui suit date du 18.)

Fait le 18 : la 0.62c (le cube du catalogue, §67) ; la 0.63 (**les cubes mères**, §68) : un cube mère nommé comme un
fichier (`cube128-NOM.cub`, sans fréquence, le squelette du programme), ses sous-cubes `cube128-NOM-ÉTAGE-FRÉQUENCE.cub`
(le nom pour indicatif : chaque programme a toutes ses fréquences), `cube_mere(nom)` (le service 30), `lugus cube`
range sous le cube mère du programme. Pas d'anciennes versions gardées (le choix du créateur).

**Le chemin, et le rôle de chaque étape (à garder en tête)** : le cube est l'ensemble des adresses ; le hex est une
adresse, une case du cube ; on choisit le cube, puis on trouve l'information avec l'adresse ; l'ADN est ce qui dure,
l'ARN ce qui agit ; tout passe par le cube d'abord (`vtx-carnet.md`, « Le chemin, pour toute chose »).

**L'ordre décidé le 18 : finir vtx avant l'IA.**
1. ~~L'annuaire des cubes~~ : fait autrement, par les cubes mères (0.63).
2. **Gobannos complet** : les fichiers (lire, écrire), les services, les instructions à 32 bits qui manquent ; puis
   Gobannos qui se traduit lui-même ; puis vtxc128 en .exe (le premier compilateur sans Rust) ; le .exe qui embarque
   les cubes de son programme (le cube mère dit lesquels) ; puis les cylindres dedans.
3. **Ogmios** : la paillasse plus intuitive, puis la marche vers Ogmios écrit en vtx (les services de fenêtre).
4. **Belenos sur Taranis** (le tapis roulant dans chaque tuile, le fluide, la pénombre, la vidéo), puis **Gobatix**.
5. Le langage : les faces dans le cube, simplifier ; Dunon : les fonctions passées en valeur ; `multiplier_ajouter` en
   un seul arrondi ; un vrai port Arduino.

**Après** : la mémoire du cube pour l'IA (la direction du créateur : éviter la coupure entre deux conversations).
