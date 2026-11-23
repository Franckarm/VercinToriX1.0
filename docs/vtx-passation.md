# Passation : pour reprendre Vercintorix dans une nouvelle conversation (23 novembre 2026, après la 0.817)

*À lire en premier par la prochaine conversation. L'état, les règles de travail, les outils, et ce qui reste à décider
avec le créateur.*

## 1. Où en est le projet

- Le dépôt : `github.com/Franckarm/VercinToriX1.0`, branche **`vtx-0.6`** (dernier état : la 0.65, vérifiée
  « Tout est conforme » ; `essai-0.65.bat` déposé chez le créateur, son essai à lire dans `essai-0.65.log`). Œuvre protégée (`AUTEUR.md`) : rien hors de ses
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
- Les journaux : `docs/vtx-reactions.md` (sections 1 à 77), `docs/vtx-carnet.md` (les fondements, section 1 bis ; la
  feuille de route, section 11), `docs/vtx-syntaxe-v0-4.md` (la référence du langage).

## 2. Les règles de travail (à garder)

- Répondre en français, honnêtement, avec des arguments ; dire ce qui ne marche pas.
- **Les deux compilateurs de chaque machine donnent les mêmes mots** (vtx128.py et vtxc128 pour Lugus, vtx64.py et vtxc64
  pour Dunon). Tout ajout dans les deux ; les programmes déjà écrits gardent leurs mots (`outils/avant_apres.py`).
- Le créateur lance lui-même les `.bat` : les déposer dans `G:\Boulot\Code\Vercintorix1.0 rust\Claude outputs\` (envoi
  du fichier, puis dépôt sur son PC). Ne jamais lancer le `.bat`, ne jamais prendre le contrôle de son écran.
- Un nom neuf à chaque livraison (le prochain : `vtx-0.818.zip`, `essai-0.818.bat` ; le `.bat` pose `set PYTHONUTF8=1`). Les `.bat` en CRLF et ASCII, sans
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
  --prefix=vtx-0.6/ -o vtx-0.79.zip HEAD AUTEUR.md COMMENCER.md LISEZMOI.md vtx.py vtx64.py vtx128.py vtx-rs vtxc spu64
  spu128 chimie natif gobannos exemples exemples128 exemples64 bibliotheque docs` suivi de ces tests et de
  `tests/test_supposons.py tests/supposons_alors.vtx tests/test_gobannos.py tests/gobannos tests/test_valeurs.py
  tests/valeurs_mele.vtx tests/test_types_fonction.py tests/test_gobannos_flottants.py tests/test_nombres.py
  tests/nombres tests/test_vocabulaire_etendu.py tests/vocabulaire tests/test_modules.py tests/modules
  tests/test_reste.py tests/test_catalogue.py tests/test_cube_mere.py tests/test_faces_cube.py tests/test_valeurs64.py tests/test_fma.py tests/test_glossaire.py` et des nouveaux.
- La vérification complète : `python3 verifier.py` (environ deux heures ; elle doit finir par « Tout est conforme ») ;
  la lancer en arrière-plan et la suivre.
- La machine : `cd vtx-rs && cargo build --release` (binaires `lugus`, `vtx64`, `vtx`, `atelier`, `ogmios`).
- L'épreuve d'Alésia : `python3 epreuve/epreuve.py` (une quinzaine de secondes, 41 vérifications) ; la jouer avant chaque livraison.

## 4. Ce qui reste, décidé avec le créateur (après la 0.64)

Fait le 21 : la 0.64 (**les faces dans le cube**, §69) : à la même fréquence, le code à l'étage Đ (le tau gallicum,
l'étage 0, le choix du créateur : 440/Đ), les trois axes du dé aux étages 1, 2, 3, chaque molécule à la place de son
début ; `face(f, k)`, `centre(f)` (le service 31) ; le cube mère sur ses quatre étages, 64 bits par étage (0.64b, la demande du créateur).

**Gobannos, les fichiers dans les .exe : en attente.** Le 18, un filtre de sécurité automatique a arrêté la réponse
qui écrivait le code machine des appels au système (les fichiers, le chemin du programme, la mémoire) ; ce travail ne
doit pas être repris sous une autre forme par l'IA. Le créateur l'a signalé à Anthropic, et peut l'écrire lui-même (les
routines du socle de Gobannos servent de modèle). Mesuré avant l'arrêt : Gobannos et vtxc128 ont besoin des services
1 à 4 (les fichiers) et 13 (jeter un cube), en plus du 26.

**Simplifier, décidé le 21 (fait, 0.66, §72)** : trois formes seulement, l'ADN (ce qui dure), l'ARNc (le travail), le cube (la mémoire) ;
les quatre ARN épissés (rapide, sûr, mémoire, complet) deviennent des façons de lancer l'ARNc (`--rapide`, `--veille`),
plus des fichiers ; les anciens se lisent toujours ; .mots et .hex restent des vues d'outil. La liste des fichiers du
paquet : `outils/fichiers_du_paquet.txt` (`git archive … HEAD $(cat outils/fichiers_du_paquet.txt)`).

**0.69 (§75)** : l'épreuve d'Alésia (`python epreuve/epreuve.py`, 41 vérifications : la demande du créateur, un test
complet et parlant à la place des nombreux tests du paquet) ; Ogmios indépendant (`ogmios.exe`, ses raccourcis Bureau
et menu Démarrer par `vtx installer`) ; la palette des cases (24 cases, 14 familles d'éléments, le menu Cases). **À
fermer ensuite, trouvé par l'épreuve** : `t[i]` hors des bornes lit sans rien dire ; `soit m: texte = n` (un entier)
accepté par les deux compilateurs. Le paquet n'emporte plus les tests (ils restent dans le dépôt). **0.69b (§75 bis)** : le menu des cases au clic droit, la case de
fin (Ne) ; les deux brèches fermées sur Lugus (`__borne`, services 32 et 33 ; `nombre_pour_texte`).  **0.69c (§75 ter)** : l'épissage sûr (les
boucles sur `0..longueur(t)` sans vérification, toujours) et l'épissage rapide (`lugus eprouver PROG.adn`, puis
`lugus PROG.adn --rapide`), décidés avec le créateur ; Dunon et `s.champ[i]` fermés. **0.70 (§76)** : LDT et STT (la machine vérifie t[i] en une instruction,
plus vite que sans vérification : 716 314 instructions contre 1 115 214), sur Lugus et Dunon, la traduction native,
Gobannos, le juge ; l'épissage d'hier éteint (`LDT_STT`) ; Ogmios : la place des vagues fait l'ordre des lignes, la
nouvelle page, la case suite (Ne) qui renvoie à la page suivante. **0.70b (§76 bis)** : la paillasse fait l'ordre du texte (colonne, puis hauteur), appeler une page et le
retour. **0.71 (§77)** : Belenos, le val des neiges (`belenos/val.vtx`, premier pas : le relief et la marche, 7 images
par seconde sur un cœur) ; la suite de la scène est au §77. **0.72 (§78)** : le soleil (o p i k) et les ombres portées
avec pénombre, éclairées par bandes (le tapis roulant) ; la scène en trois fichiers (`val_scene.vtx`, `val.vtx`,
`val_banc.vtx`) et sa référence en C (`val_ref.c`, la même empreinte au point près) ; la division signée traduite en x86
(elle faisait sortir du code traduit) ; `toile128` traduit ; vtx ≈ 10 × le C sur la scène ; l'épreuve a son chapitre
Voir (59). **Prochain pour Belenos** : les registres dans ceux du processeur (natif128), déplier les petites
fonctions, puis le lac et ses reflets. **0.73 (§79)** : la paillasse en grille aimantée (la place fait la vague et
la ligne, montrée pendant le glissement) et la fenêtre d'édition des cases (nombre et noms des entrées et des sorties) ;
la scène forgée (2,5 × le C) ; les cylindres de la forge plus lents que un cœur sur la scène (à réparer). **0.74 (§79 bis)** : les cylindres de la forge
réparés (cache de 64 pages, hachage rapide, segments en alternance, fusion stricte ; 1 cœur : 3,7 ms par image, 1,6 × le C).
**0.75 (§79 ter)** : les cylindres, copie par blocs, réserves, variables dans les registres. **0.76 (§80)** : le
rouleau de lumière en 2D (`belenos/rouleau.vtx`) ; le contrôle des cylindres au mot près. **0.77 (§81)** : `en bandes` (un seul cube, chaque cœur sa part,
la promesse vérifiée au mot près) ; décidé avec le créateur : ensuite la chaîne des étages (`chaine { etage … }`) et le
vergobret (un cœur pour la cadence et le contrôle), puis la carte ; la lumière par diffusion (pyramide de cubes) à
essayer. **0.78 (§82)** : l'image en un bloc (`presenter`, 23 fois plus vite) ; la forge ouvre sa fenêtre (le val à
l'écran 8 fois plus vite) ; ensuite, dans l'ordre du créateur : l'anti-cube, l'ombre, la lumière quaternaire (vrai /
faux / variable / inconnu, dégressive, l'inondation par sauts). **0.79 (§83)** : l'ombre quaternaire par balayage (vrai, faux, variable avec
sa densité, inconnu), juste au-delà de 200 cases ; ensuite : la lumière quaternaire (dégressive, l'inondation par sauts),
le tracé des rayons de l'image (ce qui coûte). **0.801 (§84)** : l'ombre et la lumière ensemble (l'idée du créateur :
une seule lumière par case, du blanc au noir ; vrai = une source en plein, faux = le noir, variable = tout le gris) ;
les sources diverses : le soleil, le ciel (selon l'heure et l'ouverture de la case), le renvoi du sol éclairé (porté
dans les deux sens le long des lignes, dégressif), huit feux (dégressifs, avec leur ombre quaternaire ; `f`), la lune
et son ombre la nuit (`k` jusqu'à −24°, `n`) ; empreinte 4817037499302952394. Ensuite : le renvoi égal dans toutes les
directions (l'inondation par sauts, le début de l'anti-cube et des reflets), les feux qui vacillent et renvoient, puis
le tracé des rayons. **0.802 (§85)** : le renvoi par la pyramide de cubes (sommes 2×2 à 16×16, trois voies de 16 bits
dans un mot, lecture bilinéaire des quatre niveaux, reçu par la part du ciel cachée) ; les feux renvoient ; le tapis à
deux tours après un saut de lumière ; empreinte -3681145075876775514. L'inondation par sauts est gardée pour les
reflets de l'anti-cube. **0.803 (§86)** : la lumière instantanée (la demande du créateur : le changement ne doit plus
balayer l'écran) : toute la lumière dans l'image où elle change, en trois étages en bandes (balayage → `LUM` ; pyramide
montée et redescendue → `RV1` ; composition rangée par rangée) ; plus de tapis ; forgé 22 ms sur deux cœurs ;
empreinte 7510702145557097999. **0.804 (§87)** : la lumière en calque (l'idée du créateur) : décor fixe préparé une
fois ; quand l'astre bouge, seulement le calque d'ombre (`OMBRE`, sans division) et la pyramide ; la couleur posée au
moment de peindre (`teinte`) ; la pyramide sur un seul cœur ; C 10,4 ms par image (toute la lumière refaite) ;
empreinte 4981707699916968273. Décidé : le paysage dans le cube viendra après, avec les seuls points des surfaces
(voxels ou polygones). **0.805 (§88)** : le vergobret, premier pas : la carte des pages de l'étage 2 dans la forge
(`Carte`, `lire2`, `ecrire2` : 42 % des instructions servaient à chercher les pages ; le banc de 27,5 à 19 ms sur un
cœur). Ensuite : l'équipe de cœurs qui reste en place, les deux calques posés d'un bloc (avec les étages : un cœur
entre deux étages pour la lumière et l'ombre, l'idée du créateur), puis la clepsydre et le tracé de rayons. **0.806 (§89)** : l'équipe du vergobret (cœurs gardés vivants,
`equipe_jouer`), les boucles en bandes coupées à l'exécution en quatre morceaux par cœur, la promesse vérifiée en un
passage ; règle du créateur : rien de réglé pour une machine, tout doit valoir sur tous les processeurs. Le dépôt
GitHub a changé de nom : `github.com/Franckarm/VercinToriX1.0` (remote mis à jour) ; pousser `vtx-0.6` à chaque
livraison. **0.807 (§90)** : le val en 720p (1280 × 720 ; il montre les cases du relief : l'argument pour le
paysage dans le cube) ; le rapport de fusion en quaternaire. Demandé ensuite : le paysage fait dans le cube (cube de
texture, cube d'élément, lumière, ombre par la clepsydre, reflets par l'anti-cube), en 720p ; le rassemblement des
cœurs moins cher au-delà de 8 cœurs. **0.808 (§91)** : le paysage fait dans le cube, en film GIF 720p
(`belenos/cubes_scene.vtx`, `cubes_gif.vtx`) : 2 × 2 tuiles, chacune un cube de texture et un cube d'élément à leurs
fréquences, seuls les blocs de surface ; rayons, clepsydre, occlusion, reflets de l'eau ; `VTX_GIF` dans la forge ;
la carte du vergobret sur toutes les fréquences (1024 places étiquetées). Ensuite : voir les cubes lointains par leurs
blocs (la transition fluide), le rassemblement des cœurs, Taranis. **0.809 (§92)** : les blocs vides savent leur distance (le film 30 % plus vite, identique), l'échelle
du cube (`RN / RD` : 1/2, 1, 2 ; `cubes_film.vtx` et quatre programmes courts), le changement de lumière sans coût,
`belenos/cubes_ref.c` : **vtx forgé égale le C** sur cette scène (un et deux cœurs, la même empreinte). **§93** : le reflet
s'appelle **Divona** (le rayon retourné ; un anti-cube rangé reste une option : il ne vaut que pour un reflet qui
diffère du monde, ou plus grossier) ; chez le créateur, la 0.809 en 315 ms par image sur 24 fils. **0.810 (§94)** : les
calques de lumière dans le cube (le ciel rangé une fois, la clepsydre refaite quand le soleil bouge : fréquences
`FCIEL + t`, `FSOL + t`, un octet par point de surface) : le film 2,3 fois plus vite ; et le vergobret qui mesure
(`Reglage` dans le noyau : chaque boucle en bandes essaie tous les fils, la moitié, le quart… et garde le meilleur ;
`VTX_REGLAGE=1`). Chez le créateur : 123 ms par image sur 24 fils, 226 ms sur 8 cœurs réels. **0.811 (§95)** : la
pente apprise (le tracé multiplie au lieu de diviser : 30 % plus vite, la même image) ; la promesse mesurée (6 à 16 % :
la promesse jugée passe après) ; le C compilable par MSVC. Chez le créateur : 73 ms par image. **0.812 (§96)** : le
tapis à cinq images (`belenos/cubes_tapis.vtx` : cache, image, ombre, lumière, Divona ; une boucle en bandes par tour ;
trois jeux de soleil), l'ARN du tapis lu par le vergobret (il choisit : déplié quand le soleil bouge, 28 % de moins ; un
seul étage sinon) ; le vergobret qui apprend (`vergobret.savoir` : il se souvient, devine par un voisin, doute en
quatre valeurs). Le langage, les compilateurs et Ogmios n'ont pas bougé (la demande du créateur). **0.813 (§97)** : l'ombre et la
lumière en un étage, la clarté (le tapis à quatre étages, 715 → 678 ms ; la même image) ; proposé : le génome du tapis
(l'ARN muté, l'empreinte pour juge, le savoir par machine). **0.814 (§98)** : la mesure de chaque étage
(`cubes_tapis_mesure0/1.vtx` : l'image 70 %, Divona 22 %, la clarté 4 %) ; le vergobret ne juge plus une boucle dont le
travail change d'un passage à l'autre ; le plan du tapis sur la carte (une passe par étage, 32 bits, la même empreinte).
**0.815 (§99)** : chez le créateur, **le C 44 ms, vtx 76 ms sur 24 fils** (vtx perd en montant en fils) ; le diagnostic
(`VTX_SANS_PROMESSE=1`, `cubes_ref.c -DMOT16`, l'essai sur 1, 6, 12, 24 fils) pour départager la promesse et les mots de
16 octets. Chez le créateur : ni la promesse ni les mots ; l'écart est sur un fil (892 contre 652 ms, §100). Le créateur s'est
dit perdu : décidé avec lui, la partie graphique sur la carte par la machine Rust ; l'autonomie complète attend (le
blocage du 18 n'est pas levé ; il ne saurait pas écrire les routines système). **0.816 (§101)** : le mode pages de
Taranis (la table des pages, les retours au milieu, la mémoire dans les fonctions, la promesse vérifiée sur la carte),
le rayon de l'œil sur la carte (`cubes_carte_gif.vtx`, `cubes_carte_mesure.vtx` ; la même empreinte sur SwiftShader),
le vergobret qui choisit la carte ou le processeur en mesurant (`Choix`). Chez le créateur (§102) : la carte plus lente que le processeur (165–280 ms contre 56), la même empreinte ; le vergobret a
choisi le processeur. **0.817 (§103)** : le 64 bits demandé à la carte (`NoyauI64`, `shaderInt64`), la marque une fois
par page, la résidence (le cube gardé sur la carte : seules les pages changées montent). **Prochain** : lire la mesure
sur la RTX ; l'idée du créateur (le cache qui part de l'œil, vers l'écran : recomposer cache et image) ; tout le tapis
sur la carte, l'image montrée par la carte ; l'écart d'un fil avec le C ; puis lire
la mesure du créateur ; le vergobret qui choisit l'ARN en mesurant (le génome du tapis, si le créateur le veut) ; puis
les paquets de rayons (un type « quatre voies » dans le mot de 128 bits : à décider) ; puis les coques (le trompe-l'œil du créateur : l'anti-cube à fréquence négative qui
montre de loin ce qui est dedans ; la transition fluide entre cubes ; Divona qui lit les coques) ; le calque du soleil
refait près de l'œil seulement. Ensuite : Taranis pour la scène (lectures à adresse calculée, mémoire dans
les fonctions appelées, l'image), puis la lumière dans le rouleau en 2D (l'idée du créateur), puis le val dans le cube. **Reste** : `f()[i]` ; un LDT sans vérification
pour le prélude (si jamais il en a besoin) ; Ogmios en vtx qui ne fige pas.

**Le glossaire** (fait, 0.67, §73). **La fenêtre d'un programme** (fait, 0.68, §74 : l'atelier et `lugus`, sous
Windows). **Ensuite** : Ogmios en vtx, F5 qui ne fige pas et sa fenêtre (deux fenêtres à la fois dans sortie.rs). **La suite donnée par le créateur le 21** : Ogmios, construit en vtx ; s'assurer
qu'une fenêtre paraît pour un programme qui dessine ; une paillasse plus pratique (un menu pour choisir les cases, avec
leur explication d'utilisation ; facile à utiliser et à éditer) ; vérifier qu'Ogmios ne fige pas.

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
