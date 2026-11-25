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
- Un nom neuf à chaque livraison (le prochain : `vtx-0.835.zip`, `essai-0.835.bat` ; le `.bat` pose `set PYTHONUTF8=1`). Les `.bat` en CRLF et ASCII, sans
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

## 0.818 (23 novembre)
- Blocs creusés (FCREUX=110, un mot 64 bits par brique 8³ : sauts de 4 et de 2 dans tracer, et dans cubes_ref.c) :
  38 → 11 pas de voxel par rayon ; C 535 → 257 ms, vtx 600 → 346 ms ici. Empreinte échelle 1 : 4430286082495688754.
- Rôles du créateur (filmer_roles) : ARN de 3 étages, rayons+clarté (E_RAYONS / E_RAYONS_CARTE), Divona pour l'eau
  (E_EAU), le cache compose vers l'écran (E_ECRAN, qui appelle aussi etage_cache).
- Piège : deux appels consécutifs dans une branche du tapis = un accord = pas de bandes (un cœur). Les lier par une
  valeur (`soit fait = etage_cache(..); etage_ecran(y, s + fait * 0);`). À corriger dans la forge.
- Noyau Taranis : types_de remet `_corps_vus` autour des locales ; verifier_type rend PasPourLaCarte.
- Prochaine livraison : vtx-0.821.zip / essai-0.821.bat (après la 0.820).
- À discuter : une nouvelle répartition (carte et processeur ensemble sur des rangées) ; l'écart par fil vtx/C.

## 0.819 (24 novembre) : la partie graphique renaît
- Décidé : reprendre la partie graphique seule, à partir du modèle classique des moteurs pour la carte, puis la
  changer pas à pas vers un modèle tout vtx (le document du projet `belenos-renouveau.md`, §105).
- L'épreuve de Gergovie (le juge) : `cubes_ref.c` avec `GERGOVIE=1` (C et C++), `belenos/gergovie.rs` (Rust à la main),
  `belenos/gergovie.vtx` ; le vol (240 images) et le jour (120) ; moyenne, 1 % bas, pire image, empreinte (les mêmes
  pour les quatre : 8987854166678181011 et 1907865044188733942).
- Prochain : le modèle classique sur la carte (la scène résidente, en 64 bits, l'image gardée par la carte), mesuré
  dans Gergovie ; puis l'ombre quaternaire (prioritaire).
- Prochaine livraison : vtx-0.821.zip / essai-0.821.bat (après la 0.820).

## 0.820 (24 novembre) : le modèle classique sur la carte
- `belenos/gergovie_carte.vtx` (un fil par point, `regarder_1`/`regarder_0` sans récursion, `FIMAGE = 120`) ;
  `VTX_EPISSAGE=rapide` : `SALES` (les pages changées marquées, plus de comparaison), le noyau sans auteurs
  (`NoyauI64(..., rapide=True)`, troisième SPIR-V : `taranis_boucle_pages(c, spv, spv64, spv64r, ...)`) ;
  `VTX_CARTE_VERIF=1` : le filet. La mise en place (une image) n'est plus comptée dans Gergovie.
- Le C et le C++ ne sont plus joués (le créateur) ; Rust reste la référence.
- Prochain : lire la mesure de la RTX ; la clepsydre sur la carte (le jour) ; l'image montrée par la carte ;
  l'ombre quaternaire (prioritaire).

## 0.821 (24 novembre) : Taranis, le noyau de la carte
- Avant (0.816–0.820), la carte jouait Lugus imité (pages, table, marques, demandes) : 58–121 ms par image sur la RTX.
- `NoyauTaranis` (le monde d'un seul tenant par fréquence, base[f] + i ; les divisions épissées en 64 bits exacts) et
  `taranis_direct` (EtatTaranis : le rangement, SALES, les fréquences écrites qui redescendent) ; `VTX_EPISSAGE=rapide`.
  Test : `tests/test_taranis_direct.py`. Lavapipe : 128 Mo par tampon, tester à demi-échelle (RD = 2).
- Décidé : Taranis est le noyau, Belenos le moteur ; le 64 bits reste ; les étages reviendront après.
- Prochain : lire la RTX ; les vagues en 8 × 8 ; la clepsydre sur la carte ; l'image montrée par la carte ; l'ombre
  quaternaire. Prochaine livraison : vtx-0.822.zip / essai-0.822.bat.

## 0.822 (24 novembre) : la nouvelle Gergovie
- `belenos/gergovie_scene.vtx` : la plaine auvergnate, le grand puy et son cratère (deux petits), le lac, le camp romain,
  les armées romaine et gauloise (mannequins) ; `point_vu` (le regard du point i, pour le processeur et la carte),
  `inverse_longueur` (une division par direction), `epreuve(vol, jour, sur_carte)`. Mains : `gergovie.vtx`,
  `gergovie_carte.vtx`. Tester à demi-échelle sur lavapipe (RD = 2, W = 320, H = 180).
- Chez le créateur, la 0.821 : Taranis 53,8 images par seconde (la carte 4 ms ; le reste : redescendre et poser).
- Prochain (décidé) : les étages sur la carte (matériaux, ombre, lumière, reflet ; le cache compose ; le tapis des
  images en vol, le vergobret en logistique) ; puis le cache qui montre l'image (Vulkan, la fenêtre) ; l'ombre
  quaternaire (un mot de 64 bits par vague de 32 points) ; le vergobret qui apprend pendant la mise en place.
  Prochaine livraison : vtx-0.823.zip / essai-0.823.bat.

## 0.823 (24 novembre) : les étages sur la carte, la référence C++
- `belenos/gergovie_ref.cpp` (la nouvelle scène en C++, même empreinte) ; `image_etages` (matériaux, ombre, lumière,
  reflet, cache : cinq noyaux), `gergovie_etages.vtx` ; `epreuve(vol, jour, sur_carte)` : 0 processeur, 1 un noyau,
  2 les étages ; la clepsydre sur la carte (`ranger_lumiere_carte`, `ranger_mot`, `FINV`).
- Noyau de la forge : `FREQ_CARTE = 200` (les fréquences de la carte ne redescendent pas ; `taranis_rapatrier` avant une
  boucle jouée au processeur et avant un nouveau rangement) ; préparer sans relire quand rien n'a changé.
- Prochain : lire la RTX (les étages paient-ils ?) ; le cache qui montre l'image (Vulkan, la fenêtre) ; l'ombre à
  résolution réduite (l'indicateur du créateur) ; le tapis des images en vol ; l'ombre quaternaire en un mot par vague.
  Prochaine livraison : vtx-0.824.zip / essai-0.824.bat.

## 0.824 (24 novembre) : le tapis vers le cache, le lot
- Le lot de la carte : `lancer_lot` (taranis_vk), `taranis_vider`, `taranis_envoyer`, la région des paramètres de chaque
  noyau ; la forge groupe les boucles en segments qui se suivent (`lot_pos`, `lot_suite`, `accord_carte`) ;
  `carte_voulue_lot` ; `VTX_LOT=0`. La mise en place : trois images, trois clepsydres.
- À venir (décidé) : les deux groupes avec un cycle d'avance (les images en vol) ; le cache qui montre l'image ; le duel
  au processeur (l'épissage rapide du processeur, contre le C++) ; le duel sur la carte (GLSL, avec le Vulkan SDK, plus
  tard). Prochaine livraison : vtx-0.825.zip / essai-0.825.bat.

## 0.825 (24 novembre) : Gutuater, le socle
- Chez le créateur, la 0.824 : le lot fait passer les étages de 26,1 à 42,6 images par seconde ; la mise en place
  supprime l'accroc du jour (noyau unique : le jour 32,4, pire 37 ms) ; mais les étages restent derrière le noyau
  unique (55,2) : la carte 8,2 ms pour les cinq étages (contre 4 à 5 en un noyau), redescendre 6 ms, le reste au
  processeur 8 ms.
- Décidé : trois agents, tous écrits en vtx à terme. **Vergobret** à l'exécution (carte ou processeur, les fils, et
  aussi les 32 ou 64 bits sur la carte) ; **Gutuater** côté code machine : la forge (les gènes) et la garde (les mêmes
  mots, les variantes fidèles), d'autres tâches hors du graphique à trouver ; **le Druide** : les conseils, les potions
  (il les prépare et surtout les corrige), la bibliothèque. Conception : `docs/gutuater-druide-conception.md`.
- Fait : `gutuater/gutuater.vtx` et `gutuater/synapse.vtx` (en vtx) : le carnet (synapses de Belnap, pour/contre,
  seuil 5 %, usure au-delà de 8 preuves, un côté l'emporte à trois contre un), l'ARN. Le premier gène : `lot`. Le
  vergobret (noyau_forge128.rs : `gene_lot_debut`, `gene_lot_fin`, `arn_gutuater`) lit l'ARN ; inconnu ou variable :
  il mesure le lot avec et sans (chauffer, sans, avec, sans, avec), garde le meilleur, écrit `gutuater.mesures`. La forge
  passe le lieu du lot (la ligne de sa première boucle, `lot_tete`). `VTX_GUTUATER=0` : comme en 0.824.
  Test : `tests/test_gutuater.py`. Sur lavapipe le lot ne gagne que 4 % (le bruit) : Gutuater reste « inconnu ».
- Prochain : le gène `fondre` (deux boucles sur le même intervalle en un noyau ; le gain mesurable : les étages contre
  le noyau unique) ; la garde des mêmes mots, automatique ; le Druide. En attente : le cache qui montre l'image
  (swapchain), les duels. Prochaine livraison : vtx-0.826.zip / essai-0.826.bat.

## 0.826 (24 novembre) : le gène « fondre », la garde, le seuil qui tremble
- Chez le créateur, la 0.825 : le cercle marche (le lot mesuré 18,2 contre 29,7 ms, vrai dès la première preuve ; au
  passage suivant, sans essai) ; la vitesse est celle de la 0.824 (le lot y était déjà).
- `fondre` : la forge (`groupes_du_lot`, `fondre`, `appels_dans`) écrit, à côté du lot séparé, le même lot fondu en un
  noyau (les corps à la suite, le même intervalle, chaque écriture à une fréquence connue) ; le vergobret
  (`gene_fondre_debut`, `gene_fondre_fin`, `taranis_fondre`) suit l'ARN ou mesure (chauffer l'un et l'autre, puis
  l'un et l'autre en alternance, dans un ordre tiré au hasard). `VTX_FONDRE=0` (à la forge) : pas de forme fondue.
- La garde du noyau fondu (`NoyauTaranis(..., garde=...)`, `garder`) : dans les fréquences que le lot écrit, un fil ne
  touche que sa case ((f << 24) + son tour) ; sinon le drapeau 2 : la machine s'arrête, note « infidele fondre LIEU » ;
  Gutuater tait le gène pour toujours (64 preuves contre, que l'usure ne touche pas). Test : `tests/test_fondre.py`
  (`tests/fondre/fidele.vtx`, `infidele.vtx`).
- Le seuil qui tremble (`preuve_pour`, synapse.vtx) : le seuil d'une petite preuve tiré entre 0,1 et 10 % (la
  résonance stochastique, l'arrondi stochastique) ; au-delà de 10 %, une preuve forte (poids 3, qui suffit) ; croire
  demande un poids de 3 d'un côté (`SUR`) ; l'usure au-delà de 24. La graine vient des mesures (la même entrée, la même
  décision).
- Prochain : lire la RTX (fondre gagne-t-il ? sur lavapipe il perd 14 %) ; selon : fondre par morceaux (1+2, 4+5),
  le tableau mort (les intermédiaires dans les registres) ; la garde des mêmes mots ; le Druide. En attente : le cache
  qui montre l'image, les duels.

## 0.827 (24 novembre) : l'ordre des fils par blocs
- Chez le créateur, la 0.826 : fondre perd 7 à 11 % sur la RTX (19,5 contre 17,5 ms) ; Gutuater a deux petites preuves
  contre (il en faut 3) : il le taira au prochain passage. Le noyau unique écrit à la main reste devant (55,5).
- `BLOCS` (dans le programme principal ; 0 dans les anciens) : `pixel_de(q)`, `rang_de(x, y)` dans gergovie_scene.vtx ;
  une vague de 32 fils fait un bloc de 8 × 4 pixels. Mains : `gergovie_carte_blocs.vtx`, `gergovie_etages_blocs.vtx`.
  La même empreinte (vérifié à demi-échelle). Attention : le lieu d'un gène est sa ligne ; toucher la scène change les
  lignes (le carnet repart à inconnu).
- Décidé avec le créateur (à faire) : le filtrage stochastique des calques (ombre, ciel : une lecture qui tremble, Pharr
  et al., I3D 2024), en option à côté de l'image témoin, avec le même bruit dans le C++ ; puis le calque de lumière à
  résolution réduite (le jour) ; puis son idée des étages en cube qui se fondent d'une image à l'autre (la fusion
  temporelle : rien ne se déplace, l'image suivante reprend ce que la précédente a fait) ; le bruit aux passages ADN →
  ARN → ADN (la vérification au hasard des transferts, à la manière de Freivalds).

## 0.828 (24 novembre) : la clepsydre progressive (option)
- Chez le créateur, la 0.827 : les blocs de 8 × 4 perdent environ 5 % (un noyau 52 contre 55) : la carte n'est pas le
  goulot, et le processeur relit l'image dans un ordre haché. `BLOCS = 0` reste la règle.
- `PROGRESSIF` (dans le programme principal ; 0 dans les anciens) : `ranger_lumiere_progressive(jeu, image)`,
  `ranger_mot_tire`, `tirage(t, n, g, image)`, `ranger_mot_tnw(t, n, w, avec_ciel, jeu, refs)` : au jour, un mot sur
  quatre par image (tiré par son lieu : tuile, bloc, groupe de quatre), et les références du créateur (la ligne de huit
  points : les bouts et le centre ; s'ils voient le même soleil, les autres le reçoivent). Main :
  `gergovie_carte_progressif.vtx` ; le C++ : `gergovie_ref.cpp -DPROGRESSIF` (`ranger_lumiere_p`). Le vol : la même
  empreinte ; le jour : une autre, la même pour vtx et le C++ (vérifié à demi-échelle : -7787085414147578818 pour 12 et
  8 images ; le témoin : 8984151156866620437).
- Le créateur a écrit à Anthropic (le blocage du 18).
- À discuter : autre chose qu'un rayon (le créateur : « une fréquence, une couleur, une intensité ») : la projection des
  points vers l'écran (le point émet, l'écran reçoit ; le plus proche gagne : atomicMin de 64 bits, Schütz, Kerbl,
  Wimmer, 2021 et 2022) ; un pixel où rien ne tombe reste inconnu, et lui seul lance un rayon.

## 0.829 (24 novembre) : à armes égales, l'empreinte du film
- Chez le créateur, la 0.828 : la clepsydre progressive : le C++ au jour 19,8 → 27,0 (+36 %) ; Taranis 32,4 → 35,8
  (+10 % : sur la carte, la clepsydre n'est pas le plus lourd). La dernière image du jour progressif a la même empreinte
  que le témoin (le nombre de points du soleil vus change peu en trois images) : la dernière image ne suffit pas.
- L'empreinte du film entier (chaque image, hors du chronomètre ; vtx `epreuve`, C++ `main`) : vérifiée à demi-échelle,
  la même pour le C++, vtx au processeur et Taranis, forme par forme (le témoin et la progressive).
- vtx au processeur avec la clepsydre progressive : `ranger_lumiere_progressive_processeur` (en bandes),
  `gergovie_progressif.vtx`. L'essai : le C++ contre vtx au processeur (à armes égales), Taranis à part.
- Prochain (proposé) : le duel au processeur (l'épissage rapide du processeur : le monde d'un seul tenant, comme
  Taranis, pour la forge au processeur) ; les points qui émettent vers l'écran (atomicMin de 64 bits).

## 0.830 (24 novembre) : l'épissage rapide du processeur, géré par Gutuater
- Le gène `carte_directe` (choisi à la forge : `carte_directe()` dans forge128.py ; `VTX_CARTE_DIRECTE=1/0` l'impose,
  sinon l'ARN de Gutuater à côté du programme forgé) : la carte du vergobret à 65 536 places, une par page des 256
  premières fréquences, sans mêler ni chasser (`CARTE_DIRECTE`, `place_carte`). La carte s'oublie par génération
  (`gen`, `etiquette`) : plus de remise à zéro.
- Un gène de la forge se mesure par le temps du programme entier : `VTX_GUTUATER_TEMPS=1` fait écrire « temps
  carte_directe 0 VARIANTE µs » ; Gutuater met en face la variante exprimée et la tue (une moitié attend sa paire).
  Test : `tests/test_gutuater.py` (5).
- Attention : avec la carte directe, une machine neuve pèse 2,6 Mo ; dans `tests/test_cylindres.py`, la boucle
  « mauvais » (100 000 tours) peut finir sur un seul cœur avant que les autres ne commencent : rien n'est rompu (la sortie
  est juste), et la promesse est bien vue sur une boucle plus longue (vérifié sur 20 millions de tours).
- Prochain (demandé) : les points qui émettent vers l'écran (Schütz, Kerbl, Wimmer) : il faut d'abord au langage un
  minimum atomique sur un mot de l'étage 2 (les deux compilateurs, Lugus, la forge, Taranis : OpAtomicUMin 64 bits).

## 0.831 (24 novembre) : la projection des points hex, garder le minimum
- Chez le créateur, la 0.830 : la carte directe gagne environ 3 % (vol 19,3 contre 18,7 ; jour 11,7 contre 11,2) ;
  Gutuater reste « inconnu » (de petites preuves, au hasard : il lui faut plusieurs essais). L'empreinte du film de vtx
  au processeur est celle du C++, image par image.
- Garder le minimum : la forme « si x < @2[a] { @2[a] = x; } » (aucun mot nouveau : les deux compilateurs donnent les
  mêmes mots ; Lugus la joue telle quelle) devient sur la carte un seul geste atomique (OpAtomicUMin de 64 bits,
  `minimum_garde`, `NoyauTaranis.garder_minimum`, Capability Int64Atomics) ; taranis_vk demande
  VK_KHR_shader_atomic_int64 (`atomique64` ; `VTX_ATOMIQUE64=0` l'éteint) ; un noyau qui en a besoin ne va pas à une
  carte qui ne le sait pas. Test : `tests/test_minimum.py`.
- La projection (`image_projection`, `projeter_mot`, `projeter_point`, `resoudre` ; `FPROJ = 205` ; mode 3 ;
  `gergovie_projection.vtx`) : chaque point de surface (la terre au calque du soleil, le dessus de l'eau), poussé d'un
  demi-point le long de sa normale, se projette ; un carré à sa taille à l'écran (sa hauteur suit le cosinus avec le
  regard) ; la clé : profondeur << 32 | le point (hex) ; un pixel inconnu, ou d'eau, lance le rayon. Vérifié : l'image
  est très proche de celle du rayon (640 × 360 : décalage d'au plus un pixel, quelques fentes claires) ; la
  projection exacte d'un point touché tombe sur son pixel.
- Piège trouvé : `constante VIDE` existait déjà (un bloc vide) ; une seconde `constante VIDE` a été acceptée sans un
  mot et a cassé le monde (le pixel vide s'appelle `PIXEL_VIDE`). À donner au Druide : une constante définie deux fois.
- Fondre : refusé à la forge pour une écriture à une case calculée (la projection écrit où tombe le point).

## 0.832 (24 novembre) : la projection ne coule plus ; les trois à chaque essai
- Chez le créateur, la 0.831 : la projection 24 à 25 images par seconde au vol (le rayon 55), et l'image « coule » : les
  pixels n'étaient pas vidés sur la carte. La cause : une boucle simple (vider FPROJ) prenait le vieux chemin de la
  fenêtre, qui écrit la copie du processeur ; FPROJ (205) ne vit que sur la carte. Corrigé dans la forge : avec
  l'épissage rapide, une boucle simple va aussi à Taranis (`vers_la_carte` : `rapide_ok`). Vérifié : le film de la
  projection est le même sur la carte et au processeur (là où le minimum se garde point après point).
- Règle du créateur : chaque essai joue les trois : le C++ (processeur), vtx au processeur, Taranis (la carte).
- La chaîne du créateur pour la suite : Lugus (le code, 128 bits) → Gutuater (traduit les boucles du graphique en Dunon,
  64 bits) → Vergobret (la carte ou le processeur, les fils) → Taranis (la carte). Les fréquences 200 et plus sont l'ARN
  (des données de passage, refaites à chaque image) ; le monde est l'ADN.
- Prochain : le gène « Dunon » de Gutuater (les boucles du graphique forgées en 64 bits au processeur, avec la garde des
  mêmes mots sur les premières images).

## Décision du 24 novembre (soir) : Lugus en 128 bits, le graphique en Dunon
- **Décidé par le créateur** : l'entier par défaut de Lugus passe à 128 bits (« le hex, l'ADN, l'ARN, le cube chromatique
  lui-même : je le voulais en 128 ») ; plus lent : « on trouvera une méthode ». La traduction en 64 bits se fait au
  passage du graphique, par Dunon (Gutuater) ; Taranis reste en 64 bits. Et tout ce qui peut l'être est traduit en vtx.
- **Ce qui existe** : la machine Lugus est déjà de 128 bits (mots, registres, mémoire ; le flottant par défaut, l'entier_128,
  le point natifs) ; l'entier par défaut était de 64 bits par choix (« l'adresse courte », 25 octobre). L'adresse courte
  reste valable : une adresse reste sous 2^64 (ses 64 bits hauts nuls).
- **Essai fait** (vtx128.py : les opérations entières à toute la largeur au lieu de .64) : sur les 34 exemples de
  exemples128, 26 donnent la même sortie ; 8 changent : 6 tournent sans fin (le prélude compte sur 64 bits : l'affichage
  des flottants, les sentinelles 18446744073709551615 = -1 en 64 bits, 57 fois dans le prélude), `cylindres` donne un
  autre hachage (voulu : il déborde maintenant à 128 bits), `chute` (ses exemples).
- **Le chemin, par étapes** :
  1. le prélude propre en 128 (les sentinelles, l'affichage, les nombres), les deux compilateurs (vtx128.py et vtxc128 :
     la même table de largeur), la forge (u128 au lieu de u64 pour l'entier), la vérification complète ;
  2. le passage Dunon : un module (ou une fonction) calculé en 64 bits (`importer "…" en dunon` ou équivalent, à
     choisir) ; Gergovie y passe et garde ses empreintes (celles du C++) ; Taranis inchangé ;
  3. le compilateur des noyaux de Taranis en vtx (les mêmes mots SPIR-V que noyau_vtx.py) ;
  4. les décisions du vergobret en vtx ; 5. la forge en vtx ;
  6. puis le cache qui montre l'image, et le monde d'un seul tenant au processeur.

## 0.833 (24 novembre) : Lugus en 128
- **L'entier par défaut de Lugus a 128 bits**, dans les deux compilateurs (vtx128.py et vtxc128 : les mêmes mots, point
  fixe), le prélude et la forge. À toute la largeur : l'arithmétique, les comparaisons, LDIS / LDIU / LDI + LDIH, COMPTE,
  MULHU, MULHS, et (0.833) QEGAL, ET4, OU4, NON4, ANTI. Restent à 64 bits : ETG, ETGX (l'adresse courte : une adresse
  reste sous 2^64), EXQ, LDQ, STQ (le quit d'un mot rangé), GDOT, GEMV, SYS (un service rend 2^64 - 1 en cas d'échec :
  les sentinelles 18446744073709551615 du prélude restent justes), les flottants de 64 bits. Conversions : `flottant(e)`
  lit les 128 bits (ITOF.L #0), `flottant_64(e)` aussi (ITOF.64 #0), `entier(x)` sature à 128 bits.
- **Le prélude ne dépend plus de la largeur** : `nb_bits(0 - 1)` (128 sur Lugus, 64 sur Dunon ou en `dunon;`) dans
  zeros_en_tete, zeros_en_queue, compter_zeros, tourner_gauche, tourner_droite, inverser_bits, echanger_octets,
  log2_entier ; les saturations rendent `0 - 1`. Le texte vient de `vtxc/vocabulaire.py` (ne pas retoucher vtx128.py à
  la main : il est réécrit). Les hachages de 64 bits (les dictionnaires, le catalogue, les tables de vtxc, les empreintes
  de modules) sont masqués à 64 bits : les mêmes valeurs qu'avant. `hasard` garde le même xorshift de 64 bits.
  `ecrire_hexa` : 16 chiffres si le nombre tient en 64 bits, 32 sinon.
- **Dunon : `dunon;`** en tête d'un programme (avant ses fonctions) : tout le programme, prélude compris, compte en 64
  bits (comme avant la 0.833). C'est le passage au graphique : Gergovie (ses huit programmes principaux) et les tests de
  la carte le portent ; leurs empreintes sont celles de la 0.832 (vérifié à demi-échelle : vol -2747819110214049570,
  jour 1331348773709531791, au processeur et sur la carte). vtx128.py : `regler_largeur`, la marque « ; dunon » lue par
  `lugus_asm` ; vtxc128 : `c.dunon`, `masque(c, v)`.
- **Taranis reste en 64 bits** : la forge n'envoie à la carte que les boucles d'un programme `dunon;` (une boucle d'un
  programme à 128 bits y donnerait d'autres nombres) ; ailleurs elle reste au processeur.
- **La forge** : l'entier en u128 (divu128, divs128l, sar128, quits_128, mulhu128…), u64 en `dunon;` ; ses tableaux
  serrés d'entiers en u128. `forge/test_forge128.py` : 94 programmes conformes à Lugus émulé.
- **Défauts trouvés et corrigés en chemin** : `charger_l` de vtxc (des moitiés de plus de 64 bits) ; les masques
  internes BITS_V / BITS_F (répétés sur 128 bits pour un mot de 64 logiques) ; le pliage `<<q` / `>>q` (64 quits) ;
  la réduction `min` part de 2^128 - 1 ; ma première table des conversions (un flottant de 128 bits depuis un entier de
  64 : faux, corrigé).
- **À savoir** : `0 - 1` vaut maintenant 2^128 - 1 ; un programme qui compare son propre -1 à 18446744073709551615 doit
  écrire `0 - 1`. `1 << 100` est juste en 128 ; en `dunon;`, le décalage se prend modulo 64 (comme Rust et le C).
  Exemples : `exemples128/entier128.vtx` et `entier128_dunon.vtx`.
- **Passent aussi en Dunon** (ils comptent sur 64 bits par nature) : le langage du SPU-64 sur Lugus (`COMPAT_64`,
  les suites de vtx64), le lecteur d'ADN (`chimie/adn.vtx` : ses signatures et neutrons sont ceux de adn.rs),
  tout Belenos (le fluide : par `belenos/fabriquer_fluide.py`, le tableau, les cubes), la bibliothèque des flottants de
  Gobannos (ses règles : ni / ni % sur 128 bits). En `dunon;`, un nombre écrit de plus de 64 bits est refusé.
- **Corrigés au second tour** : la place d'un souvenir (l'épigénome) se calculait sur les bits forts d'un mot de 64
  bits ; `__empreinte` (vers_logique) à 64 bits ; l'ADN d'un entier a 64 bases sur Lugus, 32 sur Dunon
  (compter_base, ecart_bases, inverser_bases) ; le duel (le plan d'expert de 64 portes) ; le lecteur d'ADN embarqué
  (`lugus compiler ../chimie/adn.vtx lecteur_adn.mots` après chaque changement de vtxc128).
- **Gobannos** traduit les programmes en Dunon (ADDI, SUBI, CMPI à 128 bits ajoutés) ; la division et le modulo de 128
  bits (#0C, #0D, et ce qui en dépend) ne sont pas encore traduits : un programme à 128 bits s'arrête en le disant
  (code 3), rien de faux. À faire : une division longue de 128 bits en x86.
- **Les sentinelles** : un service de la machine rend ses codes sur 64 bits (`SYS`) : -1 vaut 18446744073709551615,
  -2 vaut 18446744073709551614 (affichés ainsi sur Lugus) ; « absent » (rang_si, chercher…) reste 18446744073709551615.
  Question au créateur : les étendre par le signe (-1 sur toute la largeur), ce qui change ces comparaisons partout.
- **Le coût** (forgé, une boucle de hachage avec multiplications, divisions, modulos) : 0,21 s en 128 bits contre 0,07
  s en Dunon (×3 : la division de 128 bits est une routine) ; sur l'émulateur Lugus, presque rien.
- Branche `lugus-128`, fusionnée dans vtx-0.6 à la livraison.
- **Prochain (décidé)** : traduire en vtx ce qui peut l'être : le compilateur des noyaux de Taranis (les mêmes mots SPIR-V
  que taranis/noyau_vtx.py), les décisions du vergobret, la forge ; puis le cache qui montre l'image, et le monde d'un
  seul tenant au processeur.

## 0.834 (25 novembre) : finir Lugus en 128
- **-1 vaut -1 sur tout le mot** (décidé par le créateur : les services de Lugus et de Dunon sont indépendants, ceux de
  Lugus passent en 128). SYS et ENTC sont à toute la largeur sur Lugus (64 bits en `dunon;`) : la machine rendait déjà
  `u128::MAX` (inconnu : absent, illisible, la fin de l'entrée) et `u128::MAX - 1` (faux : pas un cube, pas un
  dossier) ; c'est SYS.64 qui les tronquait. Le prélude écrit ses sentinelles `0 - 1` (justes sur Lugus et sur Dunon ;
  « absent » s'affiche -1) ; les masques de 64 bits des hachages restent. La forge ne masque plus un service (sauf en
  `dunon;`). Corrigés : vtxc128 (`lire_fichier`), Gobannos, Gutuater, Ogmios (leurs comparaisons à 0 - 1).
- **Le piège du `0 - 1`** est fermé avec : un -1 rendu par un service est le -1 du programme. Exemple :
  `exemples128/sentinelles.vtx`.
- **Gobannos traduit la division de 128 bits** : les routines `R_DIV128` (sans signe : deux DIV si le diviseur tient en
  64 bits, sinon 128 tours décaler-soustraire, la retenue du reste gardée) et `R_DIVS128` (les valeurs absolues, puis
  les signes ; par zéro et le plus petit par -1 comme la machine) ; DIV, MOD, DIVS, MODS à 128 bits les appellent ;
  `CC_GE`. Les programmes à 128 bits deviennent des .exe (les tests de Gobannos ne passent plus par Dunon ; sa
  bibliothèque des flottants reste en `dunon;`, ses règles le veulent). Restent non traduits, comme avant : IN, les
  voies (#8A), la matière (#92), et les fichiers (le travail en attente depuis le 18, que le créateur écrit lui-même).
  Exemple : `exemples128/division128.vtx`.
- Vérifié : `verifier.py` « Tout est conforme » ; l'épreuve d'Alésia 60/60.
- **Ensuite (décidé)** : le Druide pour la vitesse du 128 (prouver qu'une valeur tient en 64 bits et prendre l'opération
  de 64 bits ; la division par une constante changée en multiplication, Granlund et Montgomery) ; il aidera la forge et
  Gobannos. Puis la traduction en vtx : le compilateur des noyaux de Taranis, le vergobret, la forge.
- Idée du créateur à creuser : que les services répondent aussi par les quatre valeurs (un quit d'état en haut du mot,
  comme les flottants), au lieu d'un nombre à comparer.

## 0.835 (25 novembre, en cours) : Ésus dans la forge
- **Ésus** (le bûcheron qui taille l'arbre) : l'optimisation du cœur, dans la forge (le natif), pas dans les mots de
  Lugus (sur l'émulateur, une division est une seule instruction : la changer l'allongerait ; les deux compilateurs ne
  changent pas). `esus_diviser` : la division et le reste par une constante (puissance de deux : un décalage ; sinon
  Granlund et Montgomery, fig. 4.1 : `divk128`, `modk128`, `mulhu128v` dans noyau_forge128.rs) ; `borne(e)` : la plus
  grande valeur prouvée d'une expression ; quand les deux opérandes et le résultat tiennent en 64 bits, l'opération de
  64 bits (+, *, / et % par une constante). `VTX_ESUS=0` l'éteint. Test : `tests/test_esus.py` (avec et sans, contre
  Lugus) ; la forge : 98 programmes conformes.
- **Mesuré** (une boucle de hachage de 30 millions de tours) : le reste d'une valeur de 121 bits par 1000003 : −25 à
  −30 % ; `/ 7` d'une valeur de 16 bits : rien (LLVM le faisait déjà) ; la boucle entière : à égalité, parce que ses
  valeurs sont vraiment grandes (le coût du 128 y est réel et ne se réduit pas sans changer le résultat).
- **Les bornes des variables** (fait) : `esus_definitions` lit toutes les affectations d'une variable dans la fonction
  (`soit`, `affecter`, `pour`) et prend la plus grande borne ; le compteur de `pour i dans a..b` va jusqu'à b + le pas ;
  un paramètre, une écriture qu'Ésus ne lit pas, ou une variable qui dépend d'elle-même : 128 bits (prudent : au pire,
  rien n'est optimisé). Mesuré : une boucle à petites valeurs (40 millions de tours) : 0,088 s → 0,062 s (−30 %),
  autant que la même en Dunon (0,063 s), la même sortie.
- **Ésus est un épisseur** (le créateur) : il retire de l'ARN ce qui ne sert pas au travail, comme l'épissage sûr de la
  0.69c retirait la vérification des bornes dans `0..longueur(t)` ; avec les bornes prouvées, le même geste partout.
- **Les quatre points d'une molécule** (l'idée du créateur) : pour chaque variable, la plus petite et la plus grande
  valeur, les bits sûrement à 0 et sûrement à 1 (ce que LLVM garde : intervalles et bits connus) ; bit à bit, c'est
  Belnap (inconnu, faux = 0 sûr, vrai = 1 sûr, variable = un chemin qui se contredit, du code jamais atteint). À
  ranger dans le cube (le côté du travail, pas l'ADN) : le Druide les relira d'une forge à l'autre.
- **Les quatre points calculés** (fait) : `points(e)` dans forge128.py (le plus bas, le plus haut, les bits sûrement à 0,
  à 1 : &, |, ^, les décalages, %, /, +, * ; les variables par `esus_definitions`) ; la borne d'Ésus en est le deuxième
  point. **Le relevé d'Ésus** : `PROG.esus` à côté de l'exécutable forgé (une ligne par variable entière de chaque
  molécule : molécule, variable, bas, haut, zéros, uns, en hex ; rien pour un programme en `dunon;`).
- **Les faces ne suffisent pas** (six faces de 64 bits par molécule, déjà prises) ; le rangement proposé : les quatre
  points d'une variable à la même adresse sur les quatre étages d'une fréquence réservée (étage 0 le plus bas, 1 le
  plus haut, 2 les zéros sûrs, 3 les uns sûrs). Ce sera le premier geste du Druide (en vtx).
- **Retirer `__borne`** quand l'indice est prouvé : laissé ; il faut prouver i < longueur(t) (une relation entre deux
  valeurs, que des bornes ne donnent pas) ; le cas courant (`0..longueur(t)`) est déjà fait par l'épissage sûr.
- **Le Druide** (décidé avec le créateur) : il conseille, modèle, propose, organise, connecte et déconnecte, apprend ;
  il touche l'ARN et le cube chromatique, jamais l'ADN ; la garde le tient (rien ne passe sans le même résultat).

