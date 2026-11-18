# Passation : pour reprendre Vercintorix dans une nouvelle conversation (18 novembre 2026, après la 0.62b)

*À lire en premier par la prochaine conversation. L'état, les règles de travail, les outils, et ce qui reste à décider
avec le créateur.*

## 1. Où en est le projet

- Le dépôt : `github.com/Franckarm/vercintorix1.0`, branche **`vtx-0.6`** (dernier état : la 0.62b, vérifiée
  « Tout est conforme » ; `essai-0.62b.bat` déposé chez le créateur, son essai à lire dans `essai-0.62b.log`). Œuvre protégée (`AUTEUR.md`) : rien hors de ses
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
- Les journaux : `docs/vtx-reactions.md` (sections 1 à 66), `docs/vtx-carnet.md` (les fondements, section 1 bis ; la
  feuille de route, section 11), `docs/vtx-syntaxe-v0-4.md` (la référence du langage).

## 2. Les règles de travail (à garder)

- Répondre en français, honnêtement, avec des arguments ; dire ce qui ne marche pas.
- **Les deux compilateurs de chaque machine donnent les mêmes mots** (vtx128.py et vtxc128 pour Lugus, vtx64.py et vtxc64
  pour Dunon). Tout ajout dans les deux ; les programmes déjà écrits gardent leurs mots (`outils/avant_apres.py`).
- Le créateur lance lui-même les `.bat` : les déposer dans `G:\Boulot\Code\Vercintorix1.0 rust\Claude outputs\` (envoi
  du fichier, puis dépôt sur son PC). Ne jamais lancer le `.bat`, ne jamais prendre le contrôle de son écran.
- Un nom neuf à chaque livraison (le prochain : `vtx-0.63.zip`, `essai-0.63.bat`). Les `.bat` en CRLF et ASCII, sans
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
- `bibliotheque/catalogue.vtxcat` est gardé dans le dépôt : le refaire (`lugus cataloguer bibliotheque`) après toute
  retouche d'un module de la bibliothèque (sinon `importer empreinte` le refuse, l'empreinte ayant changé).
- `outils/tests_du_paquet.txt` : les tests mis dans le paquet ; la commande du paquet : `git archive --format=zip
  --prefix=vtx-0.6/ -o vtx-0.63.zip HEAD AUTEUR.md COMMENCER.md LISEZMOI.md vtx.py vtx64.py vtx128.py vtx-rs vtxc spu64
  spu128 chimie natif gobannos exemples exemples128 exemples64 bibliotheque docs` suivi de ces tests et de
  `tests/test_supposons.py tests/supposons_alors.vtx tests/test_gobannos.py tests/gobannos tests/test_valeurs.py
  tests/valeurs_mele.vtx tests/test_types_fonction.py tests/test_gobannos_flottants.py tests/test_nombres.py
  tests/nombres tests/test_vocabulaire_etendu.py tests/vocabulaire tests/test_modules.py tests/modules
  tests/test_reste.py tests/test_catalogue.py` et des nouveaux.
- La vérification complète : `python3 verifier.py` (environ deux heures ; elle doit finir par « Tout est conforme ») ;
  la lancer en arrière-plan et la suivre.
- La machine : `cd vtx-rs && cargo build --release` (binaires `lugus`, `vtx64`, `vtx`, `atelier`).

## 4. Ce qui reste, à décider avec le créateur (après la 0.62b)

La 0.62 a fait le chantier du 17 (`vtx-reactions.md` §66) ; la 0.62b a corrigé `sortie(f)` dans vtxc128 et renommé
`melanger` de `bibliotheque/cube.vtx` en `brasser` (le choix du créateur).

**Rectifié par le créateur le 18** : les empreintes des modules se gardent **dans un cube, pas dans l'ADN**. Le chemin,
pour toute chose (`vtx-carnet.md`, « Le chemin, pour toute chose ») : cube (une place et un contenu) → hex (l'écriture,
sans coût) → ADN (ce qui dure : les mots, les cubes sur disque avec anti-cube et ombre) → ARN (ce qui agit) → programme,
et retour. Le catalogue d'aujourd'hui (`catalogue.vtxcat`) n'est que l'écriture hex, sans cube derrière : à proposer, le
cube du catalogue (chaque module et chaque molécule un point, rangés selon Fischer dans les colonnes couleur-matière,
sur disque avec anti-cube et ombre), dont `catalogue.vtxcat` devient la lecture hex.

Puis : l'accroche (deux codes qui partagent des vibrations) ; un catalogue écrit aussi par Dunon (il lui faut les
fonctions passées en valeur).

Ce qui reste ouvert ailleurs, à ne pas oublier : `multiplier_ajouter` en un seul arrondi ; Dunon sans fonctions passées en
valeur ; les broches d'Arduino (un vrai port) ; Gobannos qui se traduit lui-même, puis les cylindres dedans.
