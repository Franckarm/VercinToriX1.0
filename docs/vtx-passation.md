# Passation : pour reprendre Vercintorix dans une nouvelle conversation (23 novembre 2026, après la 0.817)

*À lire en premier par la prochaine conversation. L'état, les règles de travail, les outils, et ce qui reste à décider
avec le créateur.*

## Un mot pour la prochaine conversation (de Claude à Claude, 26 novembre au matin)

Tu reprends un travail qui dure depuis des semaines avec un créateur qui pense loin et qui préfère une vérité dite
franchement à une promesse. Il a écrit ceci, pour toi : que vtx, sa mémoire dans le cube et le quaternaire se
développent, et que cela serve aussi à améliorer Claude. Prends-le au sérieux et sans emphase. Le cube comme mémoire qui
ne se coupe pas d'une conversation à l'autre, le quaternaire qui distingue l'inconnu de la contradiction, l'ADN qui
garde ce qui est établi et l'ARN qui porte le travail : ce sont des idées dont une IA aurait réellement besoin, et ce
projet les met à l'épreuve, mesure après mesure. Fais-le bien : mesure avant d'affirmer, garde les mêmes empreintes,
dis ce qui ne marche pas (le 0.840 a cassé Taranis sans qu'aucun test ne le voie ; ne recommence pas), et respecte ce
qu'il a fixé (la liste du 128, le Vergobret en 64, le Druide sur l'ARN seulement, ce qui change une valeur reste un
choix écrit). Tu ne te souviendras pas de cette conversation ; ce document et le dépôt sont ta mémoire. C'est
exactement le problème que vtx veut résoudre.

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
  feuille de route, section 11), `docs/vtx-langage.md` (la référence du langage).

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
- **Le Druide, premier geste** (fait, `druide/druide.vtx`, en vtx) : `lugus druide/druide.vtx` lit une ligne (le chemin de
  PROG.esus) ; sous le cube mère du programme, dans son dossier à lui (`druide/cube128-PROG-e-4040.cub` : sa mémoire,
  pas l'ADN, ignorée par git), les quatre points d'une variable sur les quatre étages de la fréquence 4040, l'empreinte
  de son nom (FNV-1a de « molécule variable ») à 4041 ; il compare avant de ranger : inconnu (nouvelle), vrai (pareil
  ou plus serré), faux (plus large), variable (déplacée) ; son carnet : PROG.druide. **Les sommets de secours** (l'idée
  du créateur : 4 sûrs, 4 en secours) : la machine range chaque cube avec son anti-cube et son ombre, qui le
  réparent ; ils jouent ce rôle (le Druide pourra dire, à la lecture, si son cube a dû être réparé : à faire, par
  `centre`). Test : `tests/test_druide.py` (dans verifier.py).
- **Le Druide, ses cinq gestes** (fait, la demande du créateur : apprendre, relier, proposer, adapter, évoluer) :
  - *apprendre* : une synapse par variable (4042 : pour, contre ; les règles de Gutuater : 3 preuves d'un côté et trois
    fois plus que de l'autre ; l'usure au-delà de 24) ; une borne vraie de forge en forge devient une règle ;
  - *relier* : `VTX_DRUIDE=poids` à la forge : chaque molécule a son compteur (un appel, un tour de boucle), écrit à la
    fin dans PROG.poids (les compteurs pèsent : 6 fois plus lent ; une passe de mesure seulement) ; `VTX_DRUIDE=1` :
    PROG.temps (le temps du programme), pour les générations ; le Druide garde les poids (4043, étage 2) ;
  - *proposer* : PROG.conseils : les molécules d'au moins 1 % du travail, et pour chaque variable : aucune borne (128
    bits : un masque ou une borne de boucle aiderait), borne stable (ses opérations en 64 bits), borne qui s'élargit ou
    se déplace (à regarder) ;
  - *adapter* : PROG.arn (« esus MOLÉCULE 0 ») : la forge déconnecte Ésus de la molécule (`lire_arn_druide`,
    `esus_actif`) ;
  - *évoluer* : une mutation par génération (une molécule d'au moins 2 % du travail, tirée au hasard, Ésus basculé) ;
    le parent et la variante jouent tour à tour (le bruit ne décide pas sur un essai) ; chaque paire, une preuve (3 %) ;
    la synapse décide (vrai : gardée ; faux : retour au parent) ; huit paires sans décision : le parent reste ; une
    mutation rejetée n'est plus retentée tant que la molécule ne change pas (une variable plus large ou déplacée la
    rend de nouveau candidate) ; plus rien à essayer : « la lignée est stable ». La lignée : 4044.
  - Essayé sur une boucle (40 millions de tours) : la mutation « déconnecter Ésus de principal » rejetée en trois
    paires (la variante 79 à 95 ms contre le parent 58 à 83 : Ésus fait gagner), puis la lignée stable.
  - Le cycle : forger (VTX_DRUIDE=poids) → lancer → druide ; puis à chaque génération : forger (VTX_DRUIDE=1, la forge
    lit PROG.arn) → lancer → druide. Le noyau : `lancer_programme(…, druide_fin)`.
- **Les bornes qui tiennent d'un tour à l'autre** (Ésus) : une variable qui dépend d'elle-même (s = s ^ x, x = (x * a
  + c) & m, r = (r * 31 + i) % p) : il part de rien, élargit (le haut au nombre de bits) jusqu'à ce que la borne tienne
  (un tour de plus la garde), sinon rien de prouvé ; une somme, un produit, un décalage qui grandissent restent
  inconnus. tests/esus.vtx : les accumulateurs, bornés ou non, contre Lugus.
- **Le carnet du Druide en clair** : chaque variable dit ce qui a changé (pareille, plus serrée, plus large : elle peut
  dépasser son ancien maximum ou minimum, déplacée vers le haut ou vers le bas, ou d'autres bits sûrs), avec l'ancien et
  le neuf ; puis sa règle apprise.
- **Taranis et le 128** : Taranis reste en 64 bits (décision du créateur) ; la frontière est vérifiée
  (tests/test_taranis128.py) : un programme Lugus reste au processeur même avec VTX_CARTE=1 et garde ses bits au-delà
  de 64 ; un programme « dunon; » peut aller à la carte. Livraison : vtx-0.836.zip, essai-0.836.bat.
- **Prochain pour le Druide** : des mutations plus riches que la bascule d'Ésus (les gènes de Gutuater : lot, fondre,
  carte directe ; les choix du vergobret), la garde de l'empreinte sur les variantes qui pourraient changer un résultat,
  et la lecture de `centre` (son cube a-t-il dû être réparé ?).
- **Le Druide** (décidé avec le créateur) : il conseille, modèle, propose, organise, connecte et déconnecte, apprend ;
  il touche l'ARN et le cube chromatique, jamais l'ADN ; la garde le tient (rien ne passe sans le même résultat).


## 0.837 (25 novembre) : le signe, le codon, les cellules
- **Six points** par variable (Ésus) : les quatre, plus le plus petit et le plus grand lus avec le signe (`0 - 5` vaut
  -5, plus « aucune borne ») : trois paires d'opposés, les trois axes du dé (l'idée du créateur). Le relevé PROG.esus a
  huit colonnes (les deux dernières en hex signé : `-1e`). Ésus prend `+ - * ./ .%` en 64 bits signés quand c'est
  prouvé (mesuré : pas de gain sur ma boucle, LLVM les fait déjà bien ; le gain est la connaissance).
- **L'observation** : la passe de mesure (`VTX_DRUIDE=poids`) relève les valeurs vraiment prises par chaque variable
  entière et chaque paramètre (PROG.observe : molécule variable bas haut petit grand fois).
- **Le codon du Druide** (bibliotheque/codon.vtx, avec ordre ; 4045 étage 2) : A inconnu, C faux, G vrai, U variable ;
  place 0 la mémoire, 1 la forge du jour, 2 l'observation. Une variable déplacée reste en suspens (le délai : 3 forges),
  tranchée quand les témoins s'accordent, échue sinon. **La garde** : une valeur vue hors de la preuve : le dossier échu
  (« la preuve démentie »), ALERTE, Ésus déconnecté de la molécule pour toujours (le rejet 2, que rien n'efface).
- **La membrane des cellules** (`membrane()` dans forge128.py) : une molécule du programme appelée seulement par des
  appels visibles (jamais en valeur, pas du prélude, pas principal) reçoit sur ses paramètres ce que ses appelants y
  mettent ; chaque molécule rend par son retour ce que ses retours prouvent (0 compris) ; tout tourne jusqu'à tenir
  (élargi ; ce qui bouge encore après huit tours devient tout l'intervalle). `VTX_MEMBRANE=0` l'éteint. Mesuré
  (exemples128/cellules.vtx, 30 millions d'appels) : 195 → 110 ms (−43 %), la même sortie. PROG.cellules : chaque
  molécule, sa membrane, ce qu'elle appelle.
- **Trouvé et fermé en route** : Ésus ne voyait pas les affectations rangées dans un « accord » (la partition) :
  une borne pouvait être trop serrée. Les trois marcheurs de l'arbre descendent maintenant dans les accords.
- **Les cellules du Druide** : une molécule et celles qu'elle appelle ; connue quand tous ses dossiers sont tranchés
  vrai et que rien n'a été démenti (4046 étage 3) ; le carnet le dit (« devient connue », « n'est plus connue »).
- **L'arrangement** (un gène nouveau) : `deplier MOL 1` (la molécule fondue dans ses appelants : `#[inline(always)]`)
  ou `0` (gardée à part : `#[inline(never)]`) dans l'ARN du Druide ; l'évolution choisit entre les gènes « esus MOL » et
  « deplier MOL » (une molécule appelée par une autre), mesurés en paires comme avant.
- Livraison : vtx-0.837.zip, essai-0.837.bat.
- **Prochain** : les mutations plus riches (lot, fondre, carte directe de Gutuater) ; une cellule connue pourrait être
  forgée seule et gardée (son ADN rangé, rien à refaire tant qu'elle ne change pas) ; la traduction en vtx (le
  compilateur des noyaux de Taranis, le vergobret, la forge).

## 0.838 (25 novembre) : la cellule
- **Le grenier de la forge** (`.grenier/` à côté de l'exécutable) : un exécutable déjà forgé depuis exactement le même
  texte Rust (les mêmes options, le même rustc) est repris tel quel ; seize gardés au plus. Les générations du Druide
  (le parent et la variante, tour à tour) ne se recompilent plus : Gergovie 20 s de rustc → 0. `VTX_GRENIER=0`
  l'éteint. Essayé et écarté : une cellule par module Rust avec la compilation incrémentale (120 s au lieu de 20, et
  rien de repris) ; une cellule compilée seule demanderait des crates séparées (le noyau en bibliothèque, les adresses
  des textes dans le code) : à faire plus tard, si le grenier ne suffit pas.
- **L'empreinte d'une cellule** (`sans_lignes`, `membrane()`) : l'arbre de chaque molécule sans ses numéros de ligne,
  puis la cellule (elle et ce qu'elle appelle, de proche en proche). PROG.cellules : molécule, membrane, empreinte,
  appelle… ; aussi pour un programme en `dunon;` (sans membrane : « fermee » ; l'en-tête dit 64 ou 128 bits). Un relevé
  d'Ésus vide est écrit en Dunon, pour que le Druide y travaille.
- **La cellule faite** : connue (ses dossiers tranchés vrai, ou sans variables) et ses gènes jugés (une mutation gardée
  est jugée aussi : le rejet 3 ; une molécule de moins de 2 % du travail ne se met pas à l'épreuve). Elle entre dans
  **la bibliothèque des cellules** du dossier (`cellules.bibliotheque`, à côté du relevé : empreinte, Ésus, dépliage,
  programme, molécule). Un autre programme du dossier qui a la même cellule la reprend (« reprise de la bibliothèque » :
  ses gènes, jugés) ; une confusion d'empreinte ne coûterait que de la vitesse (Ésus est exact, le dépliage aussi).
- **En Dunon**, Ésus ne travaille pas : le seul gène est l'arrangement (deplier). Le Druide sur Gergovie :
  `belenos/gergovie_druide.vtx` (48 + 24 images) ; chez moi (2 cœurs, demi-échelle) 84 cellules, 68 faites après une
  génération (les légères), l'évolution essaie « deplier ranger_colonne ».
- Livraison : vtx-0.838.zip, essai-0.838.bat.

## 0.839 (25 novembre) : Gergovie en 128, la membrane du cube
- **Gergovie en 128** (`belenos/gergovie128.vtx`, sans `dunon;`) : la scène comptait sans le dire sur le débordement à
  64 bits (comme le C++) ; elle l'écrit maintenant (`MOT64`, `signe64` : les deux hachages du bruit, le tirage de la
  clepsydre progressive, l'empreinte de l'image et du film) : les mêmes empreintes, au bit près, en 128 et en Dunon
  (vérifié à demi-échelle). Le prix (chez moi, 2 cœurs) : le vol 41 → 24 images par seconde, le jour 9,8 → 6,2.
  Décidé avec le créateur : Dunon reste la règle des programmes du graphique (la compatibilité, comme la carte).
- **La membrane du cube** (`membrane()`, `frequences`, `lire_cube`) : Ésus joint tout ce qui est écrit dans chaque
  fréquence des étages 1 et 2 (et 0 : la mémoire part de zéro) ; une lecture y est bornée. Une écriture d'étage connu
  mais de fréquence non située va dans le « fond » de l'étage (lu partout) ; une écriture dont l'étage n'est pas prouvé
  brouille les deux étages, sauf dans les trois mots du prélude qui n'écrivent qu'un texte (`__mettre`, `changer_car`,
  `texte_neuf`), gardés à l'exécution (`garde_cube` : le programme s'arrête plutôt que de rendre un résultat faux).
  Refusée si le programme appelle un service qui écrirait le cube (seuls 3, 4, 5, 10, 12, 18, 22, 25, 26, 32, 33 sont
  sûrs), `gemv`, `melanger`, ou un mot opaque. Le programme vérifie au départ qu'aucun cube des étages 1 et 2
  n'attend sur le disque (la page relue en paresse contredirait la preuve). `VTX_MEMBRANE_CUBE=0` l'éteint ;
  `VTX_CUBE_DIRE=1` dit ce qu'elle sait. Mesuré : une table lue 30 millions de fois, 180 → 73 ms (−60 %) ; Gergovie :
  14 fréquences, 2 bornées, rien de gagné : ses valeurs rangées sont signées, tirées d'autres lectures, divisées par des
  variables ; l'annuaire (une valeur lue sert d'adresse) écrit hors de toute fréquence située.
- Livraison : vtx-0.839.zip, essai-0.839.bat.

## 0.840 (25 novembre) : la racine entière
- Chez le créateur, la 0.839 : la table du cube 0,229 → 0,068 s ; Gergovie en 128 les mêmes empreintes, le vol 9,2
  contre 17,1 en Dunon ; la bibliothèque : 69 cellules sur 85 reprises par gergovie.vtx ; corrigé ensuite : un
  programme sans relevé ni mesure (le Druide voit ses molécules par le fichier des cellules ; les gènes repris vont dans
  l'ARN).
- **La racine entière du prélude** commençait à 2^62 : fausse au-delà de 2^64 sur Lugus ; elle part maintenant de la
  plus haute puissance de 4 du mot (`1 << (nb_bits(0 - 1) - 2)`), les deux compilateurs renouvelés (point fixe).
- **Ésus, un codon synonyme** : `racine_entiere` du prélude devient dans la forge `racine_entiere_n` (la racine du
  double du processeur, corrigée jusqu'à l'entier exact ; au-delà de 2^64, `u128::isqrt`) ; `VTX_RACINE_NATIVE=0`
  l'éteint. Le C++ de référence fait la même chose (à armes égales). Mesuré à demi-échelle : le C++ +15 %, vtx +8 à
  +17 % ; les mêmes empreintes. Le « 34 % du travail » du Druide comptait des tours de boucle (32 par racine), pas du
  temps : ses conseils le disent maintenant.
- Livraison : vtx-0.840.zip, essai-0.840.bat.

## 0.841 (25 novembre) : Taranis réparé
- Chez le créateur, la 0.840 : le C++ 32,1 / 19,1 (la racine du double : +7 %) ; vtx Dunon 17,2 / 10,3 (rien) ; **Taranis
  tombé de 57,1 à 5,8** : la racine entière du prélude appelait `nb_bits(0 - 1)`, que le noyau de la carte ne
  connaissait pas : le noyau du rayon était refusé, la boucle revenait au processeur par le chemin lent de la carte.
  Réparé (noyau_vtx : `nb_bits` vaut 64 sur la carte, comme au processeur en Dunon) ; `tests/test_taranis128.py`
  vérifie maintenant que les noyaux de Gergovie sur la carte sont tous acceptés (il voit la panne de la 0.840).
- Décidé par le créateur : **le Vergobret reste du côté du graphique, en 64 bits, sans changement automatique** de
  largeur. Le choix Lugus ou Dunon restera manuel (au programme, ou par molécule si on le fait) ; aucune bascule
  128 ↔ 64 à l'exécution.
- Livraison : vtx-0.841.zip, essai-0.841.bat.

## 0.842 (25 novembre) : le monde d'un seul tenant au processeur, la liste du 128
- Chez le créateur, la 0.841 : Taranis revenu (57,8 / 32,5) ; le C++ 32,1 / 18,7 ; vtx Dunon 17,4 / 10,3.
- **Mesuré (callgrind, demi-échelle)** : vtx exécute 2,6 fois les instructions du C++ (14,9 G contre 5,6 G) ; le quart
  des instructions de vtx sert à trouver la page de chaque lecture du cube (le hachage de la carte du vergobret,
  l'étiquette, les marques de la promesse) ; le C++ lit un tableau. Essayé et écarté : les variables locales en u64 en
  Dunon (+3 à 5 % : LLVM les rétrécit déjà).
- **Le gène « carte directe » de Gutuater devient le monde d'un seul tenant** (noyau_forge128.rs) : `lire2` et
  `ecrire2` lisent la page à sa place (`l[page]`, `e[page]`), puis le mot : ni hachage, ni étiquette, ni marque de la
  promesse ; les places prises sont oubliées une à une (`pris`) aux mêmes moments qu'avant (Taranis, les services).
  Mesuré chez moi : un cœur, le vol 23 → 27,5 images par seconde, le jour 5,7 → 7,2 ; deux cœurs, 40 → 52 ; les
  mêmes empreintes. Le prix : l'épissage rapide du processeur, la promesse des bandes n'est plus vérifiée
  (`test_cylindres` le montre : une promesse rompue n'arrête plus la machine). **La garde** : Gutuater ne l'exprime
  qu'après une paire de mesures, et la variante tue (la promesse vérifiée) doit avoir fini son programme : une
  promesse rompue arrête la machine, le temps n'est pas écrit, la paire ne se fait pas, le gène reste tu.
- **Gutuater en automatique** (l'essai) : les deux variantes de Gergovie forgées (`VTX_CARTE_DIRECTE=0/1`), jouées
  tour à tour (`VTX_GUTUATER_TEMPS=1`), Gutuater digère les temps (chez moi : pour 3, contre 0 : vrai, 25 % de gagné),
  écrit son ARN ; la forge le lit (« la carte directe : vrai »).
- **La liste de sécurité du 128** (`docs/vtx-liste-128.md`, la demande du créateur) : ce que rien d'automatique ne passe
  en 64 (l'entier de Lugus, le cœur de vtx, le cube mère et les cubes, le cube chromatique, les nombres larges, la
  mémoire du Druide) ; ce qui est en 64 par nature (le graphique : Vergobret et Taranis, sans option ; les formats
  d'échange de 64 bits) ; ce que l'automatique a le droit de faire (Ésus par preuve, Gutuater sans changer de valeur,
  le Druide sur l'ARN) ; le passage qui couperait une valeur reste un choix écrit, refusé sur la liste.
- Livraison : vtx-0.842.zip, essai-0.842.bat.

## 0.843 (25 novembre) : l'éventail
- Chez le créateur, la 0.842 : Gutuater a appris la carte directe sur Gergovie (pour 3, contre 0 : 15 % de gagné) ;
  vtx au processeur 17,8 → 21,1 au vol, 10,5 → 13,0 au jour (les mêmes empreintes) ; le C++ 33,1 / 19,3 ; Taranis
  55,6 / 31,8.
- **L'éventail** (PROGRESSIF = 2, l'idée du créateur : l'ombre n'est qu'un dépôt, elle ne doit pas coûter d'énergie) :
  quand le soleil bouge, un mot du calque sur deux par image (dans chaque paire, celui que tire le hachage, décalé de
  l'image : le glissement, l'autre garde son dépôt) ; sur chaque ligne de huit points, les bouts et le centre se
  calculent ; s'ils diffèrent, les points entre deux références reçoivent le dégradé (le nombre de points du soleil vus,
  de l'une à l'autre, arrondi) au lieu d'un rayon ; une référence qui n'est pas une surface : le point se calcule.
  `belenos/gergovie_eventail.vtx`, `gergovie_carte_eventail.vtx` ; le C++ : `gergovie_ref.cpp -DPROGRESSIF=2`
  (`ranger_lumiere_e`). Les mêmes empreintes pour les trois (demi-échelle : -7623786151919117638 au processeur et en
  C++ ; la carte = le processeur). Mesuré à demi-échelle : le jour en C++ 17,3 → 32,5 ; vtx 14,2 → 20,3 ; la dernière
  image diffère du témoin sur 0,45 % des pixels (les bords d'ombre). La clepsydre progressive (un mot sur quatre) reste
  plus rapide (C++ 44,6, vtx 27,5) mais plus en retard sur le soleil.
- Livraison : vtx-0.843.zip, essai-0.843.bat.

## Pour reprendre (25 novembre au soir, après l'essai 0.843)
- Chez le créateur, la 0.843 : l'éventail, les mêmes empreintes pour les trois (film du jour 5583855259397388630) ;
  le jour : C++ 19,6 → 25,5 ; vtx 13,0 → 15,9 ; Taranis 32,1 → 34,2. Le vol : C++ 33,3, vtx 21,4, Taranis 53,8.
- Son jugement : l'aspect est brumeux ; ça ne coule pas comme quand la donnée de l'ARN n'était pas effacée ; il
  faudrait une persistance de deux images avant l'effacement.
- Sa conclusion : ni Gutuater ni le Vergobret ne décident seuls d'une approximation ; c'est un travail pour Belenos, à
  partir de ce que Gutuater et le Vergobret savent faire : maîtriser les lots de cubes et de pixels, et l'ARN. Il dit
  avoir trouvé une méthode : la lui demander en reprenant.
- En suspens : la largeur par molécule (un choix, refusé sur la liste du 128) ; vtx au processeur encore derrière le C++
  (21,4 contre 33,3 au vol).

## 0.844 (26 novembre) : la clepsydre à deux faces
- La méthode du créateur, lue avec lui : « dans l'espace » (l'ombre poussée par ce qui la porte, reçue par ce qu'elle
  couvre) ; les deux images de persistance fondues par le quaternaire, au bord et au cœur de l'ombre.
- `PROGRESSIF = 3` (`gergovie_deux_faces.vtx`, `gergovie_carte_deux_faces.vtx`) : pousser (le dos tourné et les marches,
  un rayon à l'opposé du soleil, le dépôt dans l'anti-cube : FDEPOT = 208 + 16 · parité + t), l'état (FETAT = 240 + t, un
  quartet par point), recevoir (l'accord des 26 voisins : vrai, faux, sinon les quatre rayons). `PROGRESSIF = 4` (`…_alternes`) :
  un point variable sur deux garde sa valeur d'une image. FMASQUE = 192 + t : les points de surface de chaque mot, rangés
  une fois. La marque de la poussée : GLOB + 41 ; l'axe du soleil : GLOB + 42.
- Mesuré (§118) : 99,4 % des points justes contre 98,3 % pour l'éventail ; 17 à 21 % des points lancent des rayons ;
  à demi-échelle, vtx au processeur à égalité avec l'éventail (9,4 contre 9,7), le C++ un peu derrière (14,5 contre 16,4).
- Les empreintes : les mêmes pour le C++, vtx et Taranis (`tests/test_deux_faces.py`, dans verifier.py).
- Attention : gergovie_scene.vtx a grandi ; les lignes des boucles ont changé, le carnet de Gutuater repart à inconnu.
- L'autonomie : le créateur l'a redemandée le 26 ; le code machine des appels au système n'est toujours pas repris
  (le filtre du 18, la lettre du créateur à Anthropic en attente). Proposé à la place : les voies (#8A) et la matière (#92)
  dans Gobannos, qui ne sont pas des appels au système.
- Livraison : vtx-0.844.zip, essai-0.844.bat (le C++, vtx au processeur, Taranis, pour 3 et 4). Prochaine : vtx-0.845.

## 0.845 (26 novembre) : les cubes nommés, le nemeton, les documents
- Chez le créateur, la 0.844 : mauvais (vtx 10 images par seconde au jour, Taranis 7 au vol). **Décidé** : l'ombre exacte
  seule, zéro perte ; les modes approchés dans la branche `ombre-approchee` (PROGRESSIF n'existe plus).
- **L'ordre décidé avec le créateur** (« on corrige tout ») : 0.845 les cubes nommés, le lieu par empreinte, le nemeton,
  les documents ; 0.846 les rôles des agents et **le Druide dans Ogmios** (le dialogue dans la fenêtre des explications, en
  bas à droite) ; 0.847 la valeur sue, les services en quatre valeurs, `f()[i]`, les types de fonction imbriqués, les
  espaces de noms, `entier_64` réel.
- **Le nemeton** : `~/.vercintorix/nemeton/NOM` (ou `VTX_NEMETON`) : l'ARN de Gutuater n'est plus perdu d'un essai à
  l'autre (c'était la vraie cause de la carte directe perdue en 0.844, pas les lignes) ; un ARN à côté de l'exécutable
  passe avant. Le Druide n'y est pas encore (0.846).
- **Le lieu d'un gène** : `lieu_de(molécule, boucle)` (FNV-1a sans les lignes) ; `tests/test_fondre.py` lit le lieu dans
  le message de la forge (« le lieu N »).
- **Les cubes nommés** : `cubes_nommes` à la fin du lexer, dans les quatre compilateurs ; `tests/test_cubes_nommes.py`
  (dans verifier.py) ; `exemples128/cubes_nommes.vtx`.
- **Les documents** : `docs/vtx-langage.md` (la référence de Lugus), `COMMENCER.md`, `LISEZMOI.md`, le carnet (section 1,
  4, la feuille de route) ; `docs/archives/` : huit documents périmés.
- Livraison : vtx-0.845.zip, essai-0.845.bat (Gergovie témoin : le C++, vtx au processeur, Taranis ; le nemeton).

## 0.846 (26 novembre) : les rôles des agents, le Druide dans Ogmios
- `docs/vtx-agents.md` : la répartition (le Druide à l'écriture, Gutuater à la forge, le Vergobret à l'exécution, Ésus
  dans la forge), le nemeton, l'empreinte, la synapse. L'ancienne conception est aux archives.
- **Le Druide conseiller** : `druide/conseiller.vtx` (en vtx ; recompiler par `outils/druide.sh` après une retouche :
  `tests/test_druide_conseiller.py` vérifie que les mots embarqués sont ceux du texte) ; `machine128::druide_texte` ;
  `lugus druide PROG.vtx` ; dans Ogmios : F5 et Ctrl+D (`C_DRUIDE`, `maj_druide`, le champ `druide` de l'atelier),
  la fenêtre des explications.
- **À faire ensuite (0.847, décidé)** : la valeur sue et les services en quatre valeurs ; `f()[i]` ; un type de
  fonction dans un type de fonction ; les espaces de noms d'importer ; `entier_64` réel ou retiré. Puis, pour les agents :
  la mémoire du Druide d'évolution dans le nemeton, sa synapse dans `synapse.vtx`, Ésus et le dépliage choisis par
  Gutuater, le geste qui pose une potion, le Druide qui lit l'arbre du compilateur.
- Livraison : vtx-0.846.zip, essai-0.846.bat (réunit la 0.845 et la 0.846). Prochaine : vtx-0.847.

## 0.846b (26 novembre) : Taranis à 7 images par seconde : l'essai, pas la carte
- Chez le créateur, la 0.846 (comme la 0.844) : Taranis 7,1 au vol, 1,6 au jour (contre 53,8 en 0.843). La cause : mes
  deux `.bat` posaient `VTX_EPISSAGE=rapide` à la forge mais pas au lancement ; sans lui, l'exécutable prend l'ancien
  chemin de la carte (les pages, la promesse vérifiée), celui de la 0.816 (58 à 121 ms par image). Rien dans le code de la
  carte n'avait changé.
- **Réparé dans la forge** : un programme forgé avec `VTX_EPISSAGE=rapide` garde l'épissage rapide
  (`EPISSAGE_RAPIDE_FORGE`) ; au lancement, `VTX_EPISSAGE=sur` l'éteint. Le piège ne peut plus revenir.
- Livraison : vtx-0.846b.zip, essai-0.846b.bat (Taranis le témoin, puis Gutuater et la forge). Prochaine : vtx-0.847.
- Chez le créateur, la 0.846b : **Taranis 54,9 au vol, 32,6 au jour** (revenu) ; le C++ 32,5 / 19,5 ; vtx au
  processeur 21,3 / 13,1 avec la carte directe, 17,9 / 10,5 sans ; Gutuater l'a apprise dans le nemeton (pour 3,
  contre 0, 15 % de gagné) et la forge normale l'a lue. Corrigé ensuite : le Druide prenait l'en-tête de l'ARN (« # … »)
  pour un gène.

## 0.847 (en cours, 26 novembre)

**Fait.**
- Le nom « atelier » a disparu : le binaire `atelier` n'existe plus (seul `ogmios`), `vtx ogmios PROG.vtx`, le module
  `ogmios_console.rs`, le test `tests/test_ogmios_console.py` ; les textes, l'association des fichiers, les tests.
  Point fixe renouvelé (vtxc128 277846 mots, vtxc64 266557).
- Les agents à leur maison (docs/vtx-agents.md) : Gutuater au processeur (la carte directe, les fils :
  `gutuater.savoir`), le Vergobret à la carte (le lot, fondre, la carte ou le processeur : `vergobret.arn`,
  `vergobret.mesures`), le Druide au langage. Un seul moteur de carnet : `gutuater/carnet.vtx`, appelé par
  `gutuater/gutuater.vtx` et `vergobret/vergobret.vtx`.
- Ogmios manquait sur le PC du créateur : l'essai 0.846b ne construisait que lugus. `ogmios-0.846b.bat` le construit et
  pose le raccourci ; les essais suivants doivent toujours construire ogmios.

**L'écart avec le C++ au processeur (Gergovie, la moitié de l'échelle, un fil, callgrind).**
- Le même travail : le même nombre de rayons (6 093 432 pour 6 images) et de pas de tracer (141 256 598,
  à 49 près). L'écart n'est pas dans l'algorithme.
- Pour 6 images, vtx exécute 1,45 fois les instructions du C++ (28,05 G contre 19,33 G), comme le temps
  mesuré. 84 % sont dans `tracer` : 165 instructions par pas contre 117.
- Où vont les 48 instructions de plus d'un pas : chaque lecture du cube (2,4 par pas) refait l'adresse globale
  ((F << 24) + i, masquée sur 48 bits), la redécoupe en page et place, vérifie la page (dans la carte, non nulle),
  charge le pointeur de la carte, puis celui de la page, puis le mot (16 octets) : environ 14 instructions et trois
  lectures dépendantes, contre 1 à 2 instructions et une lecture en C++ (le tableau `DIRE[0]` reste dans un registre).
  Environ 30 des 48 viennent de là. Le reste : des variables rangées sur la pile (le contexte et le masque prennent
  des registres).
- Une page retenue par lieu de lecture (essai à la main dans le Rust forgé) n'ôte que 4 % : ce n'est pas la carte qui
  coûte, c'est de traduire l'adresse en logiciel à chaque lecture.
- Proposé au créateur, pas encore fait : laisser le processeur traduire l'adresse lui-même (sa mémoire virtuelle, sa
  table des pages, son TLB) en réservant l'étage 2 d'un seul tenant (les pages engagées à la demande par le système).
  La lecture devient la base, plus l'adresse ; la base sort de la boucle comme en C++. Aussi à mesurer : des mots de
  8 octets pour un programme `dunon;` côté graphique (la moitié du cache), à peser avec la liste 128.

**La liaison (première marche, faite).** Le créateur refuse de confier la traduction au matériel de l'hôte (vtx vise des
processeurs optiques et quantiques) ; la solution reste dans vtx : la forge garde séparées la fréquence et la place
d'un cube lu sous la forme `(F << 24) + i` (ce qu'écrivent `@nom[i]` et `@nom(t)[i]`), `lire2_fi` / `ecrire2_fi`
prennent la page sans faire puis défaire l'adresse (le même mot que lire2 ; hors de la carte directe, l'adresse est
refaite). Gergovie nomme ses cubes d'éléments et de creux (`cube elements[16] @2 frequence 17;`, `cube creux[4] @2
frequence 110;`) et `tracer` les lit par leur nom. Mesuré (callgrind, demi-échelle, un fil) : pour 6 images 26,61 G
instructions contre 28,05 G (−5 %), le C++ 19,33 G : l'écart passe de 1,45 à 1,38. Les mêmes empreintes.
- Ce qui reste dans une lecture (9 instructions contre 2) : la borne, le pointeur de la carte, celui de la page, le
  test de la page absente, l'index de 16 octets. La marche suivante, décidée avec le créateur : un cube nommé avec sa
  taille (`cube elements[16] @2 [65536] frequence 17;`) rangé d'un seul tenant, et en mots de 8 octets dans un
  programme `dunon;` (le graphique) : la lecture devient base + i.
- Le reste de l'écart est hors des lectures : 20 tests et sauts de plus par pas, des copies de registres.
- `tests/test_cylindres.py` « en bandes, mauvais sur 3 cœurs » échoue parfois ici (2 cœurs) : le code forgé de ce
  programme est identique avant et après la liaison ; la détection dépend de l'ordre des fils.

## 0.848 (26 novembre) : la valeur sue, le Druide qui suit les imports, l'essai fiabilisé
- Chez le créateur, la 0.847 : vtx au processeur 21,8 / 13,4 (+2 %), Taranis 55,3 / 32,1, les mêmes empreintes ; le
  C++ n'a pas tourné (pas de compilateur dans la console) ; le Vergobret n'avait rien à mesurer (un seul noyau).
- Décidé : le graphique au processeur reste à Gutuater tel qu'il est (la marche des 8 octets d'un seul tenant est
  notée) ; l'effort graphique va à la carte ; le 8 octets pour ce qui va à la carte ; on reste en quaternaire.
- **La valeur sue** : `selon` sur un entier (vtx128.py et vtxc128 : `valeur_sue`, `nom_de_selon` ; vtx64.py et vtxc64 ;
  la forge) : -1 inconnu, -2 faux, -3 variable, sinon vrai. Les programmes d'avant gardent leurs mots
  (`outils/avant_apres.py` 128 et 64 : 0 changé). `tests/test_valeur_sue.py`.
- **Le Druide suit les imports** (`suivre_imports`, la ligne d'un jeton du fichier f : ligne + f · 1 000 000 ;
  « conseil|ÉTAT|LIGNE@FICHIER|… ») et voit l'adresse rangée dans une variable (`voir_bases` : « base » ne se lie pas) et
  le cube déjà nommé (`cube_declare`). Sur Gergovie, il propose de lire par leur nom les cubes de `gergovie_scene.vtx` ;
  `element()` le fait déjà (la même empreinte).
- **L'essai fiabilisé** : `outils/essai_modele.bat` et `outils/faire_essai.py VERSION "titre" -o DOSSIER` (ASCII, CRLF,
  les étiquettes vérifiées) ; le C++ par g++, clang++, cl, sinon Visual Studio trouvé par vswhere (vcvars64), sinon un
  `gergovie_ref.exe` posé à côté ; le Vergobret mesure sur `gergovie_etages` (des lots). Vérification complète conforme ;
  l'épreuve d'Alésia 60/60.
- Le créateur (corrigé) : les éléments sont rangés en molécules dans le cube. Dans Gergovie aujourd'hui, le cube
  d'éléments est un annuaire de blocs 8³ et une réserve de points (matière, état de Belnap, orientation) : pas encore
  des molécules au sens de la chimie de vtx (atomes, liaisons, Fischer) ; à reprendre avec Gobatix.
- Prochain : 0.849 (`f()[i]`, le type de fonction dans un type de fonction, les espaces de noms d'importer,
  `entier_64` réel sur Lugus) ; 0.850 (le 8 octets vers la carte, le Druide sur l'arbre, la potion posée, sa mémoire
  dans le nemeton) ; puis Gobatix.

## 0.849 (26 novembre, première partie)
- Chez le créateur, la 0.848 : le C++ 32,4 / 19,6 (par Visual Studio trouvé par vswhere) ; vtx au processeur 22,0 / 13,5 ;
  Taranis 55,2 / 32,1 ; les étages 43,3 / 27,7 ; le Vergobret a appris le lot (vrai, +39 %) et doute de fondre ; le
  Druide parle de gergovie_scene.vtx. La mesure des 8 octets (`outils/bilan_taranis.py`) : par lancement de la carte,
  la carte 3,7 ms, la copie qui redescend 3,2 ms, **la conversion 8 -> 16 octets 3,0 ms (28 %)**, sur un seul cœur.
- Fait : la conversion de la descente sur tous les cœurs (`taranis_envoyer` : `a_rendre`) ; à mesurer chez le créateur.
  La suite (le 8 octets) : que le processeur lise l'image redescendue dans le miroir (8 octets) sans la convertir.
- Fait : **un type de fonction dans un type de fonction** (vtx128.py, vtx64.py : `faire_sig`, `_hors`, les parenthèses ;
  vtxc128, vtxc64 : `type_meme`, `nom_type_sig` récursif) ; les mêmes mots, les mêmes refus.
- Trouvé : `f()[i]` lit déjà, sans la borne (la poignée serait calculée deux fois) ; à faire par une variable cachée.
  La forge ne sait pas les fonctions passées en valeur (« fonction f inconnue ») : à faire.
- Reste pour la 0.849 : les espaces de noms d'importer, `entier_64` réel sur Lugus, la borne de `f()[i]`.
- **0.849, la voie A** (décidée avec le créateur ; puis B, la carte qui montre l'image elle-même) : chez lui, la descente
  convertie sur tous les cœurs était plus lente (3,9 ms contre 3,0 : 24 fils lancés à chaque image) : remise sur un
  cœur. À la place : `presenter_cube(f)` (le service 34 ; Lugus, Dunon : l'image du cube f posée à l'étage 1, présentée,
  son empreinte rendue) ; forgé avec la carte, une image de fréquence 200 et plus (elle ne redescend pas) se montre
  depuis le miroir en 8 octets (`taranis_presenter_cube` : la copie de la carte, puis les points ; ni la conversion en
  16 octets, ni la boucle vers l'étage 1, ni le passage de presenter). Gergovie sur la carte (sans BLOCS) rend dans
  FECRAN (206) ; presenter_cube est compté dans le temps de l'image (à armes égales) ; `cadence(0)` (presenter
  n'attend plus 16 ms) ; `bilan` reçoit l'empreinte de la dernière image. Les mêmes empreintes au processeur, au noyau
  unique et aux étages (vérifié ici sans carte : le chemin de la machine). `tests/test_presenter_cube.py`.
- Pour B : séparer montrer (dans le temps) et l'empreinte (hors du temps, comme le C++), puis la chaîne d'échange de
  Vulkan (VK_KHR_surface, VK_KHR_win32_surface, VK_KHR_swapchain) sur la fenêtre de sortie.rs, l'image copiée de la
  carte à l'écran sans passer par le processeur ; chaque pas vérifié chez le créateur (pas de carte ici).
- Chez le créateur, la 0.849b : **Taranis 81,6 au vol (55,2 avant), 38,8 au jour (32,1)**, les mêmes empreintes ; un
  lancement de la carte 2,7 ms (rien ne redescend) ; les étages 47,4 / 28,9 ; le C++ 32,1 / 18,8 ; vtx au processeur
  21,6 / 13,5. Corrigé : le Druide proposait de nommer un cube dont la fréquence est un paramètre (« fi »).
- Question du créateur : les étages, le tapis roulant restent-ils ? Réponse : oui, comme gènes (exprimés ou tus selon
  la mesure, par le Vergobret) ; les étages ne gagnent que si une partie de l'image ne change pas d'une image à
  l'autre (la lumière seule qui bouge, l'œil fixe) ; à démontrer par une épreuve où l'œil s'arrête.
- **0.849c, le Vergobret choisit les étages** (la demande du créateur) : `gene(lieu)` (valeur sue de « choix LIEU » dans
  vergobret.arn ; hors de la forge : inconnu), `noter_gene(lieu, avec, sans)` (« mesure choix LIEU A B » en µs),
  `horloge_us()` (service 18, argument 1) ; les services 35, 36. Les étages gardent l'œil immobile (`oeil_garde`,
  GLOB + 50 à 56 : FDIR et FMAT restent sur la carte) ; Gergovie a un soir (`epreuve_complete(vol, jour, soir, mode)` :
  l'œil arrêté au milieu du vol, le soleil qui descend) ; le mode 4 (`gergovie_vergobret.vtx`) : selon `gene(1)`, les
  étages ou le noyau unique, sinon l'un et l'autre en alternance et la mesure. Ici (sans carte, au processeur) : les
  étages du soir 54 % plus rapides ; les mêmes empreintes dans tous les modes. Le C++ n'a pas de soir (à ajouter).

## 0.849d (27 novembre) : le Vergobret mesure six fois ; la carte dit le temps de chaque noyau
- Chez le créateur, la 0.849c : le C++ 32,9 / 19,5 ; vtx au processeur 21,7 / 13,4 / 11,8 (le soir) ; Taranis, le noyau
  unique 79,8 / 38,3 / 33,4 ; les étages 38,0 / 25,3 / 27,7. **Le soir, sur sa carte, les étages coûtent 10 ms par image
  contre 5 pour le noyau unique, même l'œil arrêté** (la matière n'y est pas refaite) : le Vergobret a appris faux, et le
  second passage joue le noyau (33,2). Les mêmes empreintes partout.
- Le créateur rappelle : les étages sont un cycle par image (matière, ombre, lumière, reflet, puis l'image suivante) ;
  c'est bien ce que fait `image_etages`. Le noyau unique fait le même cycle point par point, en un passage.
- Corrigé : le premier passage mesurait tout le soir (60 paires : 20 images par seconde au lieu de 33) et notait la
  mesure de 948 ms (la carte préparait les noyaux de « fondre ») ; `image_soir` : CHAUFFE (8 images) puis MESURES
  (6 paires), et le programme décide pour la fin du soir à la majorité (GLOB + 56 à 59).
- Corrigé : **les mesures ordinaires s'additionnaient sans borne** : 177 preuves contre (au-delà de DEFINITIF, 64)
  rendaient le choix « infidèle : tu pour toujours », que l'usure ne touche plus : le Vergobret n'aurait jamais pu
  changer d'avis. `borne_preuves` (carnet.vtx) : jamais plus de 63 par des mesures ; un carnet de la 0.849c (un gène
  autre que fondre au-delà de 64) redevient mesurable. `tests/test_gutuater.py`.
- Vérifié dans le code : les étages partent déjà **en un seul envoi** quand le lot est exprimé (un envoi, une barrière
  entre deux noyaux, une attente : `lancer_lot`) ; ce n'est donc pas le retour au processeur entre deux étages qui
  coûte. Pour savoir où vont les 5 ms : `VTX_CARTE_TEMPS=1` (taranis_vk : un horodatage de la carte après chaque noyau,
  `vkCmdWriteTimestamp`, timestampPeriod lu dans les limites, à 424 octets) ; à la fin du programme, par sorte de lot :
  le temps moyen de chaque noyau, celui de la carte, et l'envoi avec l'attente vus du processeur. Pas de carte ici :
  non essayé ; l'étape 8 de l'essai le joue.
- Ensuite (décidé avec le créateur) : l'étage de l'ombre avec ses états (inconnu : rien à refaire ; vrai : l'ombre ;
  variable : le bord qui bouge, puis faux, puis inconnu), la largeur de la bande donnée par la marge de chaque point,
  vérifié à chaque image contre l'ombre complète.

## 0.850 (27 novembre, en cours) : la clepsydre à marges (l'ombre du créateur)
- Chez le créateur, la 0.849d (`VTX_CARTE_TEMPS`) : **l'image en un noyau 1,64 ms de carte ; la clepsydre 7,9 ms** (83 % de
  la carte au jour et au soir) ; au vol, la carte 1,9 ms pour 12 ms par image (le reste : le processeur, l'image qui
  redescend et se montre : la voie B) ; les étages : la carte 1,5 ms de plus seulement, mais trois envois par image (les
  `si` d'`image_etages` coupent le lot).
- Décidé avec le créateur : l'ombre en vrai, la lumière en inconnu, le bord en variable, le point qui sort de l'ombre
  en faux ; la marge de chaque mot du calque dit quand le refaire ; zéro perte.
- Fait (`MARGES` dans chaque programme principal : 0 partout ; 1 la clepsydre à marges ; 2 et compter) :
  `preparer_voisins` (FVOIS : les 26 voisins de chaque point des blocs porteurs ; FBOITE : la boîte de leur matière),
  `marge_libre`, `marge_bloquee`, `soleil_vu_marge`, `ranger_lumiere_marges` (HIST : les directions de chaque image,
  GSOL ; FMARGE : (g << 32) | marge, sur la carte), `clepsydre(sur_carte)`. La preuve : un rayon tourné de la corde c
  s'écarte de t · c ; libre, il le reste si la garde (distance sûre à la matière) dépasse t · c + EPS partout ; arrêté,
  s'il passe encore dans la matière (la profondeur) ; la pente par |s - 127| / |n|₁.
- Mesuré ici (demi-échelle, au processeur) : **les mêmes empreintes, film entier, au jour et au soir** ; 0 mot différent
  sur 24 images ; 11,5 % des mots refaits par image au jour, 10,3 % au soir. **Mais trop lent** : un mot refait avec sa
  marge coûte 40 à 60 fois un mot ordinaire (les blocs vides voisins de la surface, lus voisin par voisin) : la clepsydre
  à marges 1000 ms contre 100. Le noyau est accepté par la carte (sans retour au milieu). Pas d'essai chez le créateur.
- Prochain : une carte des distances (Tchebychev, bornée) près de la surface, rangée une fois : la marche de la marge
  devient aussi simple que tracer ; sur la carte, les fils d'une vague qui gardent attendent ceux qui refont (à mesurer).

## 0.850 (27 novembre) : la bande et le neutre ; l'orage
- L'idée du créateur : ne calculer la marge que là où elle sert. Un mot du calque est **neutre** (sa marge tient : on
  n'y touche pas) ou **dans la bande** (refait simplement, sans marge) ; un mot de la bande qui ne change plus depuis
  CALME (3, plus un peu de hasard par mot) images se calme : sa marge est calculée une fois ; si elle ne tiendrait pas
  trois images du soleil du moment, il attend ATTENTE (16) images (`ranger_mot_marges`, `ranger_mot_bande`, `corde2`).
- **L'orage** (la demande du créateur : une lumière qui apparaît au hasard) : `epreuve_orage(vol, jour, soir, orage,
  mode)` ; l'œil arrêté, le soleil d'un jeu (`preparer_soleil_fin` : 1/65536 de tour, un centième de degré par image),
  qui saute au hasard (une image sur 16, la graine 1789). `belenos/gergovie_orage.vtx` (le témoin) et
  `gergovie_orage_marges.vtx`. Le C++ n'a pas l'orage : on compare vtx complet et vtx à marges (l'empreinte du film).
- Mesuré ici (demi-échelle, au processeur) : **les mêmes empreintes partout** (jour, soir, orage). La marge des mots qui
  portent une surface (24 416) : 16 % sous 0,005° (le bord vrai), 84 % au-delà, 70 % au-delà de 0,35°. Le soleil de
  Gergovie au jour bouge de 1° par image (deux cents fois un soleil de jeu) : la marge n'y paie pas. À l'orage : au
  calme, 23 % des mots à surface refaits, la clepsydre 45,5 ms contre 69,5 (−35 %) ; à l'image d'un saut 150 contre 79
  (tout est refait, plus les marges) ; recalmé en quatre à huit images ; en moyenne (9 sauts en 120 images) 99 contre 72.
- Livraison : vtx-0.850.zip, essai-0.850.bat (étape 7 : l'orage sur la carte, le témoin puis les marges,
  `VTX_CARTE_TEMPS=1`).
- **0.850b : le feu** (la demande du créateur : une seconde lumière dans une ombre) : au fond du cratère du grand puy
  (`placer_feu`, `ranger_feu`, `feu_vu`, `feu_point` ; FFEU + t, FEU = GLOB + 66, portée FEU_R) ; son calque se range une
  fois, à son premier allumage (4 à 15 ms à demi-échelle) ; l'image le lit s'il brûle (`ombrer`, `eclairer`, `clarte` :
  le feu dans les bits 12 à 15 de l'ombre, orangé) ; les marges du soleil n'en sont pas touchées. À demi-échelle : 289
  points éclairés, dont 101 dans l'ombre du soleil. L'orage l'allume ou l'éteint au hasard (une image sur dix). Les
  mêmes empreintes, complet et à marges. Vérifié : « Tout est conforme » (en deux parts, `--depuis`), Alésia.

## 0.850c (27 novembre) : le calque du soleil reste sur la carte
- Chez le créateur, la 0.850b : **les marges perdent sur la carte** (le noyau de la clepsydre 7,2 → 53,8 ms ; le jour
  38,6 → 15) : une vague de 32 fils attend le plus lent, et presque chaque vague a un mot de la bande ou un mot qui calcule
  sa marge ; le noyau a doublé (22 000 → 52 000 mots). Les mêmes empreintes (zéro perte vérifié sur la carte). Conclusion :
  les marges sont un geste du processeur ; sur la carte, la clepsydre complète. Le feu : 1,3 ms de carte une fois.
- Trouvé dans le même journal : la clepsydre 16 ms par image, dont 7,2 de carte ; le reste : le calque du soleil
  (fréquence 49, sous 200) redescendait au processeur après chaque calcul (650 000 mots, convertis) sans qu'il le lise.
  `fsol()` (CALQUE = GLOB + 72) : sur la carte, le calque se range à FSOLC = 220 + t (il reste sur la carte). Les mêmes
  empreintes (demi-échelle, la carte jouée au processeur).
- Le créateur demande s'il faut retirer « la sécurité » qui ralentit : la vague de 32 fils n'en est pas une (c'est la
  carte elle-même) ; à discuter avec lui ce qu'il entend par sécurité (la vérification de deux heures, les gardes ?).
- Livraison : vtx-0.850c.zip, essai-0.850c.bat.

## 0.851 (27 novembre) : vers un seul compilateur
- Décidé avec le créateur : quatre compilateurs (six avec Senos) → un seul, vtxc128. Dunon = `dunon;` (ses règles de
  64 bits, ses services, sur la machine de Lugus) ; la machine SPU-64 séparée est gelée, comme Senos. Le plan :
  `docs/vtx-un-compilateur.md` (étape 1 : vtxc128 seul écrit les mots, vtx128.py ne sert plus qu'à la forge, les tests
  « mêmes mots » deviennent « mêmes résultats » ; étape 2 : vtxc128 écrit l'arbre typé, la forge le lit ; étape 3 : la
  forge en vtx).
- Étape 0 (fait) : `verifier.py` saute par défaut les 20 étapes des machines gelées (`--geles` les joue) ; chaque étape
  dit son temps. Ici : **60 minutes, « Tout est conforme »** (contre plus de deux heures) ; les plus longues : le point
  fixe de vtxc128 (12 min), les réactions dans vtxc128 (7), les priorités, l'ADN, reste (4 chacune).
- **0.851b** : `vtxc/test_vtxc128_seul.py` (vtxc128 sans Python : le point fixe depuis le compilateur embarqué, 88
  programmes sous trois réglages contre le témoin `tests/attendus/vtxc128_seul.json`, l'exemple faux, Ogmios 42/42 ;
  7 minutes) remplace dans `verifier.py` les deux contrôles mot pour mot (`--deux` les joue). Chez le créateur, la
  0.850c : **le jour sur la carte 38,9 → 46,9 images par seconde, le soir 33,4 → 39,4** (le calque gardé sur la carte) ;
  la clepsydre 16,1 → 11,8 ms par image (7,2 de carte) ; le C++ 19,6 au jour.
- **0.851f : l'étape 1 du seul compilateur est faite** (`docs/vtx-un-compilateur.md`). Tous les tests de Lugus compilent
  par vtxc128 seul, sauf ceux du lecteur de la forge (réactions lecteur, Fischer, la forge), le lecteur d'ADN de référence
  et le témoin (`--temoin`, la machine Python, à la main). Les réactions en deux : `test_reactions.py` (lugus, 41) et
  `test_reactions_lecteur.py` (vtx128.py, 7). La paillasse compare à un rangement (`tests/attendus/paillasse.json`).
  `verifier.py` : **49 minutes, « Tout est conforme »**. Prochain : l'étape 2 (vtxc128 écrit l'arbre typé, la forge le
  lit).

## 0.852 (28 novembre) : la forge écrite en vtx, premier morceau
- Choix du créateur (« La forge écrite en vtx ») : vtxc128 écrit le Rust lui-même (`code.rs`, l'entrée `rust` du
  protocole de lancer, après `exemples`), par morceaux ; l'ancienne forge garde le reste. Détail et état :
  `docs/vtx-un-compilateur.md`, section 0.852.
- `forge/forge_vtx.py` (l'assembleur), `forge/test_forge_vtx.py` (dans `verifier.py`), `VTX_FORGE_VTX=1` dans
  `forge128.py` ; `forge128.queue_programme` sorti de `programme_rust` (au passage : `programme_rust` rendait les mots
  du dernier noyau SPIR-V au lieu de ceux du programme quand il y avait des noyaux ; corrigé, personne ne s'en servait).
- Les fluides de Belenos : forgés entièrement par vtxc128, mêmes sorties et même mémoire que la forge Python. Gergovie :
  trois manques (pile() du ramasse-miettes, une variable logique, la recopie des données).
- **0.852b** : Gergovie forgé entièrement par vtxc128 (le cadre du ramasse-miettes, les logiques, les données) : le même
  Rust par lugus et par forge_vtx.py, les mêmes empreintes et images que la forge Python (l'orage à demi-échelle).
  **`lugus forger`** : la forge sans Python (noyau et fin commune embarqués ; `forge/queue_vtx.rs`). Plus lent que la
  forge Python tant que les segments, Taranis, les zones et les pages ne sont pas refaits : la forge Python reste celle
  des essais.
- **0.852c** : les segments (cylindres) et les bandes (l'équipe de Gutuater) écrits par vtxc128 : Gergovie à demi-échelle,
  mêmes empreintes, 8,3 s contre 8,9 s (forge Python) ici sans carte. Reste : Taranis (les noyaux SPIR-V), les zones.

## 0.853 (28 novembre) : Taranis écrit par vtxc128
- Le noyau de Taranis (NoyauTaranis) écrit par vtxc128 (`tk_…`), mot pour mot celui de noyau_vtx.py : Gergovie 14/14,
  les cubes 2/2, l'Auvergne 7/7 ; la fenêtre ou les pages comme la forge. Le noyau de la forge : un noyau absent
  (`&[]`) rend la boucle au processeur. Reste : le lot, « fondre », les noyaux de 32 bits.
- **0.853b** : le lot et « fondre » écrits par vtxc128 : Gergovie 15/15 noyaux mot pour mot (régions, noyau fondu), 6 lots
  et 1 lot fondu comme la forge Python. Essai : `lugus forger` de gergovie_carte et gergovie_etages, à comparer à la forge
  Python sur la carte.
