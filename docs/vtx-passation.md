# Passation : pour reprendre Vercintorix dans une nouvelle conversation (17 novembre 2026, après la 0.61c)

*À lire en premier par la prochaine conversation. L'état, les règles de travail, les outils, et le prochain chantier,
décidé avec le créateur.*

## 1. Où en est le projet

- Le dépôt : `github.com/Franckarm/vercintorix1.0`, branche **`vtx-0.6`** (dernier état : la 0.61c, vérifiée
  « Tout est conforme », essayée chez le créateur, tout conforme). Œuvre protégée (`AUTEUR.md`) : rien hors de ses
  dossiers et des artefacts privés.
- Les machines : **Lugus** (SPU-128, la machine de vtx), **Dunon** (SPU-64, le même travail à 64 bits), Senos (SPU-32,
  gelé). Ogmios l'atelier, Belenos le moteur graphique, Taranis la carte graphique, Gobannos le forgeron (les .exe, écrit
  en vtx).
- Fait récemment : 0.61, le vocabulaire étendu (203 mots, `docs/vtx-vocabulaire.md`) ; 0.61b, les modules promis par leur
  empreinte (`importer "x.vtx" empreinte "16hex";`, `lugus empreinte`, `vtx-reactions.md` §64) ; 0.61c, `reste` exact sur
  les flottants (§65).
- Les journaux : `docs/vtx-reactions.md` (sections 1 à 65), `docs/vtx-carnet.md` (les fondements, section 1 bis ; la
  feuille de route, section 11), `docs/vtx-syntaxe-v0-4.md` (la référence du langage).

## 2. Les règles de travail (à garder)

- Répondre en français, honnêtement, avec des arguments ; dire ce qui ne marche pas.
- **Les deux compilateurs de chaque machine donnent les mêmes mots** (vtx128.py et vtxc128 pour Lugus, vtx64.py et vtxc64
  pour Dunon). Tout ajout dans les deux ; les programmes déjà écrits gardent leurs mots (`outils/avant_apres.py`).
- Le créateur lance lui-même les `.bat` : les déposer dans `G:\Boulot\Code\Vercintorix1.0 rust\Claude outputs\` (envoi
  du fichier, puis dépôt sur son PC). Ne jamais lancer le `.bat`, ne jamais prendre le contrôle de son écran.
- Un nom neuf à chaque livraison (le prochain : `vtx-0.62.zip`, `essai-0.62.bat`). Les `.bat` en CRLF et ASCII, sans
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
- `outils/tests_du_paquet.txt` : les tests mis dans le paquet ; la commande du paquet : `git archive --format=zip
  --prefix=vtx-0.6/ -o vtx-0.62.zip HEAD AUTEUR.md COMMENCER.md LISEZMOI.md vtx.py vtx64.py vtx128.py vtx-rs vtxc spu64
  spu128 chimie natif gobannos exemples exemples128 exemples64 bibliotheque docs` suivi de ces tests et de
  `tests/test_supposons.py tests/supposons_alors.vtx tests/test_gobannos.py tests/gobannos tests/test_valeurs.py
  tests/valeurs_mele.vtx tests/test_types_fonction.py tests/test_gobannos_flottants.py tests/test_nombres.py
  tests/nombres tests/test_vocabulaire_etendu.py tests/vocabulaire tests/test_modules.py tests/modules
  tests/test_reste.py` et des nouveaux.
- La vérification complète : `python3 verifier.py` (environ deux heures ; elle doit finir par « Tout est conforme ») ;
  la lancer en arrière-plan et la suivre.
- La machine : `cd vtx-rs && cargo build --release` (binaires `lugus`, `vtx64`, `vtx`, `atelier`).

## 4. Le prochain chantier (0.62, décidé le 17 novembre au soir)

Le créateur a dit oui au **catalogue des modules** et à la **reconnaissance des molécules par leur fréquence de
vibration**. Dans l'ordre :

1. **Lister un dossier** : un service de la machine (le 28 ; 22, 24 à 27 sont pris), sur Lugus (`vtx-rs/src/spu128.rs`
   et sa référence `spu128/spu128.py`) et sur Dunon ; il rend les noms des fichiers d'un dossier (le dossier absent :
   inconnu ; pas un dossier : faux). C'est aussi ce qui manque à `fichier_present` (absent ou « pas de dossier » ?).
2. **Le catalogue** : `lugus cataloguer DOSSIER` écrit `DOSSIER/catalogue.vtxcat` : pour chaque module (.vtx), son nom,
   son empreinte (FNV-1a, celle de `importer … empreinte`), et ses molécules (nom, masse, signature de vibration). Écrit
   en vtx de préférence (le lecteur d'ADN, `chimie/adn.vtx`, sait déjà faire la carte), avec une référence en Python.
3. **Importer par l'empreinte seule** : `importer empreinte "16hex";` (sans chemin) cherche dans le catalogue du dossier
   du programme, puis de `bibliotheque/` ; introuvable, ou deux modules différents : refusé et dit. Les deux compilateurs
   de chaque machine.
4. **La fréquence de vibration d'une molécule** (`vtx-reactions.md` §11 et `chimie/essai_vibrations.py` : les chemins
   fermés de longueur 1 à n de chaque atome, l'élément, trois tours de propagation ; 0 collision sur 3 756 molécules ; la
   limite : les graphes fortement réguliers). À porter dans le lecteur d'ADN (en vtx, et `chimie/adn.py` octet pour
   octet) sur le graphe d'une molécule compilée (ses instructions et leurs liaisons de registres, ou ses appels : à
   décider en mesurant), et à ranger dans la face « sa mémoire » de la carte.
5. **La carte dit d'où vient chaque molécule** : une molécule dont la vibration est dans le catalogue d'un module importé
   reçoit « vient du module X (empreinte …) » ; une molécule d'un module retouchée se voit (la vibration a changé).
6. Les tests (`tests/test_catalogue.py`), la doc (§66 de `vtx-reactions.md`, la syntaxe, le carnet), la vérification
   complète, le paquet `vtx-0.62.zip` et `essai-0.62.bat`.

Ce qui reste ouvert ailleurs, à ne pas oublier : `multiplier_ajouter` en un seul arrondi ; Dunon sans fonctions passées en
valeur ; les broches d'Arduino (un vrai port) ; Gobannos qui se traduit lui-même, puis les cylindres dedans.
