# Carnet de VercinToriX

*Carnet vivant de Vercintorix (vtx) : ce qu'est le projet, toutes les solutions et technologies imaginées depuis le
début, ce qui est fait et vérifié, ce qui est resté sur le papier, et les innovations nouvelles ou améliorées.
Refait le 23 octobre 2026, version 0.5 le 24 octobre (vtx 0.5 : le SPU-32 et le SPU-64, vtx64 et vtxc64). La première partie est la synthèse ;
le journal d'origine (versions 0.1 à 0.4) est gardé tel quel en annexe, et le journal de l'autonomie (0.5 à SPU-64)
est dans `vtx-0-5-autonomie.md`.*

> Vercintorix est l'œuvre de son créateur. « Pas touche, ou contactez le créateur, qui sera ravi de poser ses conditions
> pour faire avancer la science. » (`AUTEUR.md`)

---

## 1. Vercintorix en une page

**Vercintorix** (vtx, nom en hommage à Vercingétorix) est un système informatique complet pensé autour d'une idée :
**calculer en couleurs**. La mémoire est le **cube chromatique** (le cube RGB adressé en hexadécimal, `#RRGGBB`),
les nombres sont écrits en **base 4** (le *quit*, deux bits, un chiffre hex valant exactement deux quits), et chaque
valeur se lit aussi comme une **séquence d'ADN** (A C G T, U pour l'ARN). Le projet vise tout, matériel et logiciel :

- **Le matériel rêvé** : un processeur optique, le **SPU** (*spectral processing unit*), où un laser cadence le calcul,
  où la mémoire est une RAM spectrale étagée et le disque une surface d'impression spectrale (section 2).
- **Le logiciel réel** : le langage **vtx** (mots-clés en français, quelques alias gaulois), ses deux compilateurs
  qui produisent toujours les mêmes mots (l'un en Python, l'autre écrit en vtx et qui se compile lui-même), des
  machines qui exécutent le code du SPU (Rust surtout), un atelier de programmation, et des programmes écrits en vtx :
  jeux, rendu 3D, une IA (le ScoR), la génomique, la compression du cube.

Le matériel n'existe pas : tout tourne en émulation, fidèle au format des mots, des instructions et de la mémoire du
SPU. Le créateur l'a dit lui-même : il n'aura peut-être jamais le matériel ; le logiciel avance quand même.

**Trois piliers sont gravés** (décision du 23 octobre 2026) : le cube chromatique, le quaternaire, l'ADN et l'ARN.
Une nouveauté qui ne respecte pas ces trois lectures n'entre pas. S'y ajoutent, dans le **noyau immuable** du
langage, la **logique à quatre valeurs** de Belnap (inconnu, faux, vrai, variable) et la **partition par
fréquences** (accords, mesures, segments).

---

## 2. Le matériel imaginé : le SPU spectral

*Rien de cette section n'est construit ; c'est le but lointain, décrit par la spécification (`specification-spu`,
v0.5). Le logiciel lui reste fidèle par les formats.*

| Élément | Idée | Statut |
|---|---|---|
| **Horloge laser** | un laser cadence le signal, comme une horloge ; il n'est pas continu | idée |
| **MAR à 8 lasers** | le registre d'adresse mémoire est la seule source de lumière ; ses voies sont associées à des plages hex | retenu (idée) |
| **Prisme** | sépare la lumière vers la RAM côté CPU et la RAM côté GPU, chacun sa part de l'espace des couleurs | retenu (idée) |
| **SPRAM** | RAM spectrale étagée : 4 étages (0 CPU, 1 GPU, 2 partagée, 3 disque), une notation d'étage qui aiguille les données | retenu ; dans le logiciel |
| **Disque spectral** | surface d'impression spectrale (« un million de couleurs ») écrite par les lasers du MAR | idée |
| **Chipset** | seul traducteur : regroupe les quits en binaire/hex pour PCIe et USB ; tout le reste vit en optique | retenu |
| **Cache RGBA** | des LED RGBA maintenues à la couleur commandée (comme une WS2812) : la valeur reste lisible à tout instant | proposé (banc d'essai possible) |
| **Version 1 / version 2** | hybride (la lumière transporte et calcule l'algèbre linéaire, l'électronique décide), puis tout-optique à flux (des lignes à retard comme tampons, un programme = des routes) | feuille de route |
| **Tranches à 4 coins** | une région du cube décrite par 4 points, les points internes par interpolation (un produit scalaire sur 4 voies : naturel en optique) | proposé |
| **Code de Morton** | entrelacer les quits des trois axes pour que deux points proches aient des adresses proches | proposé |

**Mesure du canal** (simulation `canal_spectral.py`) : 1 quit par voie (4 niveaux) demande 26 dB de rapport
signal/bruit (avec correction d'erreur), 2 quits (16 niveaux) 40 dB, 4 quits (256 niveaux) 65 dB. D'où le choix
par défaut d'un quit par voie dans les liaisons, et 256 niveaux seulement aux frontières. Au-delà de 16 niveaux,
l'étalonnage de la diaphonie entre couleurs (matrice 3×3) est obligatoire.

**Canal caché T/U** : T et U valent tous deux 3 ; le choix entre eux peut porter un bit caché sur les quits à 3,
soit +12,5 % de capacité (au plus +16 % en déformant la statistique, ce qui le rend détectable). Étudié, **non
retenu en matériel** (une position à 5 symboles casserait l'arithmétique modulo 4) ; possible en logiciel, à la
frontière de sérialisation.

---

## 3. Les trois piliers et le noyau

### 3.1 Le cube chromatique

- **Un point** s'écrit `#RRGGBB` : 24 bits, 12 quits, 16 777 216 points ; x = RR, y = GG, z = BB.
- **Le mot du SPU-32** est `#RRGGBBAA` (32 bits, 16 quits, 4 voies R V B A).
- **Le mot du SPU-64**, le **point profond**, est `#RRRRGGGGBBBBAAAA` (64 bits, 32 quits, 16 bits par voie, couleur
  profonde HDR). Un `#RRGGBB` écrit dans un programme 64 bits « s'approfondit » : chaque octet c devient c × 257.
- **Un étage** est un cube de 256³ mots ; il y a 4 étages.
- **L'adresse longue** (SPU-64) : étage (bits 63-62), **fréquence** du cube (bits 47-24), `#RRGGBB` (bits 23-0). Un
  étage contient ainsi 16 millions de cubes de 16 millions de mots ; un pointeur porte son cube.
- **Les cubes s'additionnent par fréquences** : idée du créateur, d'abord comme un adressage sur des canaux de
  longueur d'onde (`accorder` sur le SPU-32), puis comme champ de l'adresse longue.
- **Cubes sur disque** (`ranger_cube`) : fichiers `cube64-ÉTAGE-FRÉQUENCE.cub`, relus **page par page au premier
  accès**, pour qu'un très gros modèle se parcoure sans être chargé entier.
- **Le cube de transfert jetable** : un cube sert de brouillon et `jeter_cube` le vide d'un coup (ses pages quittent
  la mémoire). Premier vrai usage : les variables de la fonction en cours dans vtxc64 (section 8.6).
- **L'ombre du cube** : sa projection 2D, là où le binaire trouve sa place (une ombre est une surface). Faite en
  bit par voxel (`ombre/`) et en quit par voxel (`feu/`).
- **La texture volumique** : un étage = 256³ couleurs, un volume entier ; quatre étages pour quatre attributs PBR
  (idée, et base de Gobatix).

### 3.2 Le quaternaire

- **Le quit** : 2 bits, un chiffre en base 4. Un chiffre hex = 2 quits, exactement : le hex n'est pas une base
  concurrente, c'est le groupement du quaternaire.
- **Les entiers sont quaternaires par nature** : un mot de 32, 64 ou 128 bits est exactement 16, 32 ou 64 chiffres en
  base 4, et l'addition binaire est l'addition en base 4 chiffre par chiffre. Le langage le montre (`0q…`, `<<q`,
  `>>q`, `.q(i)`).
- **Opérations quit par quit en instructions** : MIN4, MAX4, ADDM4, CMP3, QEGAL (égalité de chaque quit), COMPTE
  (bits à 1), LDQ et STQ (un quit d'un tableau rangé), EXQ (un quit d'un registre), ET4, OU4, NON4, ANTI (Belnap
  sur tous les quits d'un mot).
- **Les flottants quaternaires** (le cœur nouveau du SPU-64) : un quit d'**état de Belnap** (inconnu, négatif,
  positif, variable), un exposant **en base 4**, une mantisse en quits dont le premier n'est pas nul.

| Format | Taille | Exposant | Mantisse | Précision | Étendue |
|---|---|---|---|---|---|
| `flottant_32` | 32 bits | 8 bits (biais 138) | 11 quits | 21 à 22 bits | ≈ 10^±76 |
| `flottant` (64) | 64 bits | 10 bits (biais 537) | 26 quits | 51 à 52 bits | ≈ 10^±308 |
| `flottant_petuar` | 128 bits | 14 bits (biais 8 247) | 56 quits | 111 à 112 bits | ≈ 10^±4931 |

  Valeur : mantisse × 4^(max(E, 1) − biais). **Ce que le quaternaire apporte** : une mémoire nulle vaut *inconnu*,
  une contradiction (0/0, ∞ − ∞, racine d'un négatif) vaut *variable* ; l'IEEE confond les deux dans un NaN. **Le prix
  honnête** : sans bit caché en base 4, un ou deux bits de précision de moins que l'IEEE. L'IEEE reste pour l'échange
  (`vers_ieee64`, `de_ieee64`, `vers_ieee128`…).

### 3.3 La logique à quatre valeurs (Belnap)

- **Origine** : idée du créateur (vrai, faux, variable, et l'antimatière ; un essai précédent en Rust « avait tourné
  à l'enfer »). Forme retenue : la logique de **Belnap (1977)**, deux bits de preuve par valeur (v, f), rangés dans un
  quit : **inconnu 0** (aucune preuve), **faux 1**, **vrai 2**, **variable 3** (preuves dans les deux sens : le bruit,
  la contradiction).
- **L'antimatière** devient l'opération `anti`, qui échange inconnu et variable : le cube et l'**anti-cube**
  échangent les triangles rouge-vert-bleu et cyan-magenta-jaune.
- Toutes les opérations sont des ET, OU et échanges de bits : la même instruction traite un logique ou tous les
  logiques d'un mot (16 sur le SPU-32, 32 sur le SPU-64). `et4`, `ou4`, `non4`, `anti`, `fusion`, `consensus`,
  `selon` (qui oblige à traiter les quatre cas).
- **Un logique ne sert jamais de condition** : il faut `selon`, ou une comparaison (`x == vrai`).
- **La frontière binaire** : `binaire()` et `quaternaire()` passent au code d'échange 0 non, 1 oui, 2 inconnu,
  3 variable ; le cœur reste Belnap.
- Usages vérifiés : capteurs bruités, analyse d'initialisation des variables (vrai sur tous les chemins, faux sur
  aucun, variable sur certains : le bogue caché, inconnu : code mort), dictionnaire à états (`affirmer`, `nier`,
  `savoir`), correction d'erreur diamant, ScoR.

### 3.4 L'ADN et l'ARN

- **L'alphabet** : A = 0, C = 1, G = 2, T = U = 3 ; la première lettre est la plus forte. `adn"ACGT"` écrit un nombre
  (32 bases dans un entier de 64 bits, 64 dans un entier de 128).
- **T (ADN) est le résultat fixé, U (ARN) est le travail** (décision du 23 octobre).
- **Le brin de chaque mot** (SPU-64) : un quit de marque à côté de chaque mot (1/32 de mémoire en plus) : libre, ADN,
  ARN. **Une écriture dans un mot ADN arrête la machine** : le code, les textes et les données d'un programme sont
  ADN dès le départ, une protection native. `fixer(x)` (ARN → ADN), `copier_arn(x)` (une copie de travail),
  `est_fixe`, `est_arn`, `brin(adresse)`, `marquer_adn`, `marquer_arn`, `liberer_brin` (instruction MARQUE).
- **Transcription et rétrotranscription** : copier l'ADN en ARN pour travailler, refixer l'ARN en ADN pour garder.
- **Les hypothèses** (`hypothèse { … annuler; … valider; }`) : les écritures d'un bloc sont journalisées ; annuler les
  défait. C'est la place naturelle de U.
- **Le double brin** (jeu des ennemis) : l'ADN porte l'état validé, l'ARN le déplacement hypothétique ; le résultat ne
  dépend plus de l'ordre des mises à jour (0 % de scénarios dépendants contre 48,5 % sur place).
- **L'épissage** : le compilateur retire les « introns » (les instructions qui ne font que déplacer une valeur),
  comme un ARN messager mûrit (section 8.4).
- **La compression ADN/ARN du cube** : la forme comprimée est l'ADN (passive), un bloc transcrit en clair est l'ARN ;
  on peut aussi lire un voxel directement dans l'ADN, ce que zip ne permet pas.
- **La complémentarité** (idée, 23 octobre) : avec A, C, G, T codés 0 à 3, les paires A–T et C–G donnent 3 − q, c'est
  le complément bit à bit du mot (`~x`, une instruction) ; le brin anti-sens des biologistes, c'est `~x` puis les quits
  lus à l'envers. En Belnap, le complément échange inconnu et variable, vrai et faux.
- **La signature de l'auteur** (idée) : le choix T ou U sur les quits à 3 d'un cube fixé porte un filigrane, sans
  changer aucune valeur. Honnêtement : un filigrane, pas une protection forte (une vraie signature passe par une clé).

### 3.5 La musique et les fréquences : la partition des tâches

- **L'idée du créateur** : une note = une fréquence signature = une tâche ; un accord = des tâches en parallèle ; la
  mélodie = l'ordre ; la mesure = une barrière de synchronisation ; le silence = une attente. Une partition est un
  diagramme de Gantt.
- **Fait** : toute suite d'au moins deux appels de fonctions devient un **accord** ; le compilateur calcule ce que
  chaque appel lit et écrit (zones, entrées et sorties, appels compris) et range les tâches sans conflit dans une
  même **mesure**. Chaque fonction reçoit une note (la4 = 440 Hz, canal optique 193,70 THz). Rien à écrire dans le
  programme.
- **Les boucles en segments** (`pour i dans 0..N en segments { … }`) : la boucle se découpe en tâches, avec preuve
  d'indépendance ; **les tableaux cumulés** (`cumulant histo`) : une copie par segment, additionnées à la fin.
- **Le moteur V6** (image du créateur) : 6 **cylindres**, 6, 12 ou 18 segments (3 temps par piston) ; `en segments`
  vaut 12. Les segments portent les **ordinaux gaulois** de La Graufesenque : *cintux, allos, tritios, petuarios,
  pinpetos, suexos…* (`flou·tritios`).
- **Le multicœur réel** : la machine Rust joue les tâches d'une mesure sur de vrais cœurs (par défaut les cœurs moins
  un, laissé au système). Mesuré : ombre 256³, ×1,65 sur 2 cœurs ; ×18 en tout avec le code natif.
- **Une erreur reconnue** : l'ancien calcul donnait des canaux propres à chaque accord imbriqué ; refait avec des
  cylindres partagés (les gains « ×6 sur 6 cylindres » étaient faux : ×4,7).

---

## 4. Le langage vtx

### 4.1 Ce qu'on écrit

```
constante N = 64;
structure Point { x, y }
tableau genome[16384] de quits @2[0];

fonction principal() {
    soit p = Point { x: 3, y: 4 };
    soit c = #FF8000;                       // une couleur : un point du cube
    soit a = adn"GATTACA";                  // un nombre écrit en bases
    soit x = 1.5;                           // flottant quaternaire de 64 bits
    selon et4(vrai, inconnu) { vrai { afficher("oui"); } faux, inconnu { afficher("pas sûr"); } autre { } }
    pour i dans 0..N en segments { @2[100 + i] = i * 3; }
    hypothèse { @3[200] = 7; si x < 1.0 { annuler; } }
    afficher(p.x + p.y, c.r, a, x);
}
```

- **Mots-clés en français** : `fonction soit si sinon tantque retour constante pour dans donnees arrêter continuer
  hypothèse annuler valider selon` ; alias `et`, `ou`, `non`, `entree`, `données`, `arreter`.
- **Types** (SPU-64) : `entier` (64 bits), `entier_32` (`5S`), `entier_petuar` (`5LL`, 128 bits), `flottant` (64),
  `flottant_32` (`1.5S`), `flottant_petuar` (`1.5Q`), `logique`, `texte`, structures et références, tableaux (fixes,
  dynamiques `[a, b]`, de quits, de logiques, de flottants), dictionnaires.
- **Le cube dans le langage** : `@e[a]` (étage e), `@(x)[a]` (étage calculé), `@[a]` (adresse longue), champs
  `.r .v .b .a` (16 bits sur le SPU-64), `.q(i)`, `cube_adresse`, `ranger_cube`, `jeter_cube`, `gdot`, `gemv`.
- **Signés** par des opérateurs pointés : `.< .<= .> .>= ./ .% .>>`.
- **Prélude** (écrit en vtx, compilé seulement s'il sert) : textes, listes, dictionnaires à hachage, mathématiques
  (fdlibm porté en flottant quaternaire, à moins de 2 ulps), hasard reproductible et `bruit()` de la machine,
  affichage le plus court qui redonne le nombre (Dragon4 exact), dessin (`pixel`, `trait`, `triangle`…), mémoire
  (`liberer`, `ramasser`, `sauver_tas`), voix (`parler`).

### 4.2 Les versions

| Version | Date | Ce qu'elle a apporté |
|---|---|---|
| 0.1 | mi-octobre 2026 | le langage de base, `vtx.py` (compilateur, assembleur, émulateur), premiers programmes (mémoire associative, spectres, canal T/U, chariot) |
| 0.2 | | étage variable, `&& || !`, `pour`, `constante`, `donnees`, prélude, `gemv`, priorité comme en Rust, division par zéro définie, élagage et sauts directs |
| 0.2.2 | | `arrêter`, `continuer`, alias, étages nommés (CPU, GPU, PARTAGE, DISQUE), corpus de conformité, machines Java et JavaScript |
| 0.3 | | données en segment, signés, tableaux et structures, `importer`, hypothèses, débogueur par instruction |
| 0.4 | 20 octobre | flottants binary32, longs, débogueur au niveau du source, partition des tâches, segments, cumulants, V6, logique de Belnap, QEGAL et COMPTE, tableaux de quits, réécriture en 16 éléments d'un coup |
| 0.5 (autonomie, paquet `vtx-0.5` le 24 octobre) | 20-24 octobre | texte, tas, références, canaux de fichiers ; **vtxc se compile lui-même** ; `vtx.exe` sans Python ; code natif ; atelier ; tableaux dynamiques, dictionnaires, ScoR ; ramasse-miettes ; flottants de 64 bits, entiers de 128 bits, `flottant_petuar` ; variables en registres, épissage, LDQ/STQ, Belnap en instructions ; **SPU-64**, vtx64.py et vtxc64 (point fixe, embarqué dans `vtx64.exe`), atelier sur la SPU-64, tables dans les cubes, expansion en ligne, règle échange |
| SPU-64 | 23 octobre | la machine 64 bits (point profond, adresse longue, brin, flottants quaternaires) ; `vtx64.py` ; **vtxc64 se compile lui-même** sur le SPU-64 |

---

## 5. Les compilateurs

| Compilateur | Écrit en | Cible | Rôle |
|---|---|---|---|
| `vtx.py` | Python | SPU-32 | la référence historique |
| `vtxc` (`vtxc.vtx`) | vtx | SPU-32 | se compile lui-même (point fixe), embarqué dans `vtx.exe` |
| `vtx64.py` | Python | SPU-64 | la référence 64 bits |
| `vtxc64` (`vtxc64.vtx`, 8 000 lignes) | vtx | SPU-64 | se compile lui-même sur le SPU-64 (point fixe M0 = M1 = M2) |

**La règle d'or** : les deux compilateurs d'une même machine produisent **exactement les mêmes mots**, vérifié sur
des milliers de programmes aléatoires, la suite de tests, les programmes du paquet et le compilateur lui-même.
Toute évolution se fait dans les deux.

**Le point fixe** (la preuve de l'autonomie) : le compilateur écrit en vtx est compilé une fois par Python (M0) ; M0
le compile (M1), M1 le recompile (M2) ; M1 = M2 mot pour mot. `vtx renouveler` fait passer une amélioration du
compilateur sans Python.

---

## 6. Les machines et l'outillage

- **Machines du SPU-32** : Python (référence), Java (retirée à la demande du créateur), JavaScript interprété et
  traduit en fonctions (×3,4), **Rust** (`vtx-spu`, `vtx`, `atelier`), et la **traduction en code natif** par rustc
  (×12 ; mise de côté : on n'y touche plus). Un **corpus de conformité** (487 programmes) : toutes les machines
  donnent les mêmes sorties, le même nombre d'instructions et la même mémoire.
- **Machines du SPU-64** : Python (`spu64/`, flottants par fractions exactes) et Rust (`vtx64`, 150 à 190 millions
  d'instructions par seconde, un cache séparé pour la page du code) ; corpus de 503 programmes ; plus de 40 000
  programmes aléatoires identiques. `vtx64 profil` compte les instructions par adresse.
- **`vtx.exe`** : la machine Rust qui embarque vtxc déjà compilé : `vtx programme.vtx` compile et exécute sans Python.
- **L'atelier** : en console (séquences ANSI, sans bibliothèque) puis en fenêtre Win32 écrite directement (éditeur,
  menus, cube en perspective / à plat / en quits, terminal, onglets Sortie et Terminal, arbre des liaisons du tas, pas
  à pas F7 F8 F9 F5, vue quaternaire et Belnap des registres). `vtx installer` associe les fichiers `.vtx` (icône du
  cube écrite par la machine elle-même). Depuis le 23 octobre, l'atelier travaille **par défaut sur la SPU-64**
  (vtxc64 embarqué ; registres de 64 bits, points profonds vus en 32 bits dans le cube, `cube ÉTAGE FRÉQUENCE`,
  vraie valeur au clic ; Ctrl+M repasse sur la SPU-32).
- **`vtx64.exe`** : la machine du SPU-64 avec vtxc64 embarqué : `vtx64 programme.vtx` sans Python, `vtx64 renouveler`
  avec point fixe exigé.
- **Le débogueur au niveau du source** : directives `.ligne`, `.fonction`, `.var` mises de côté par l'assembleur (code
  identique à l'octet), points d'arrêt par fichier et par ligne, pile, valeurs typées.
- **Gobatix** (même programme que Coatvtx, nom d'un dieu gaulois) : le futur modeleur, peinture et animation. Premier
  pas : service graphique, cube qui tourne, cube chromatique dessiné. Décidé : un cube vide comme zone de
  modélisation, de texture et de peinture, repérée en xyz hexadécimal ; la case contient un point profond (couleur,
  et l'état de Belnap dans l'alpha : inconnu = vide, vrai = matière, faux = creusé, variable = conflit).
  Deuxième pas (24 octobre, 0.5) : **l'interactif**, sur les deux machines (services 16 à 21) : `souris()`,
  `touche()`, `appuyee()`, `molette()`, `horloge()`, `cadence()` ; l'image finie (double tampon) ; l'atelier montre
  l'animation pendant qu'elle tourne, lui donne la souris et le clavier, l'enregistre en **GIF** (Ctrl+G) ;
  `vtx gobatix64`. **L'anti-cube exploité** : `anti_couleur` (255 − c, involutive) pose curseurs et objets animés sans
  sauvegarder le fond ; le GIF n'écrit que la différence d'une image à l'autre, les points inchangés étant *inconnus*
  (transparents). Les scénarios de gestes (`--scenario`) rejouent un programme interactif sans écran :
  `tests/test_gobatix.py`, même GIF octet pour octet sur le SPU-32 et le SPU-64.
- **Le miroir et l'opposé** (24 octobre) : idée du créateur, un RAID à double cube en miroir et un retour
  d'information simultané. Le miroir et l'opposé réunis donnent le double rail, c'est-à-dire Belnap bit par bit.
  Réalisé : **les cubes sur disque en miroir inversé** (le cube et son anti-cube, `etat_disque()`, réparation d'une
  copie perdue) ; **le cube des noms** dans vtxc64 (chaque nom haché une fois, sa place est son identité, les tables des
  rôles en miroir : −8,7 % sur la compilation de vtxc64) ; **les appels en série** `f(a): x, y, z;` (écrire moins).
  **L'ombre, troisième voix** (idée du créateur, « l'ombre en binaire, comparée sur les colonnes de liaison du cube,
  avec une formule intégrant le hex ») : par colonne de 256 mots, neuf ou exclusifs, dont huit suivent les bits de la
  coordonnée BB ; un mot abîmé est retrouvé, situé et rectifié ; les contradictions entre le cube et son anti-cube sont
  tranchées. 3,5 % du cube.
  **L'abîme en mode commun résolu** : l'anti-cube est rangé par symétrie centrale (le mot #RRGGBB à
  #(FF-RR)(FF-GG)(FF-BB), valeurs complémentées) ; la même place des deux fichiers porte deux mots différents, donc le
  même bit inversé ou la même page effacée dans les deux devient deux erreurs distinctes, rectifiées par l'ombre.

---

## 7. Applications écrites en vtx (et ce qu'elles ont prouvé)

| Programme | Ce qu'il montre | Résultat mesuré |
|---|---|---|
| Mémoire associative, chariot d'usine | recherche par similarité dans le cube (GDOT) | 100 % des tours sûrs dès 25 dB contre 67 % pour un arbre à seuils |
| Recherche : centrage, index, sonar, **grille de hachage sur pivots** | trouver vite malgré le bruit | la grille : 2,2 à 3,5 fois moins de calcul qu'IVF à 30 dB, 4 à 18 fois à 40 dB (première méthode au seuil « 2 à 4 fois » exigé) |
| IA sur le cube | un réseau 64 → 24 → 10, une couche = un `gemv` | 96,7 % sur les chiffres manuscrits ; ×15,7 moins d'instructions qu'en scalaire |
| Jeux (Doom-like, « Labyrinthe du cube », monde étendu) | rendu par rayons, sprites en ADN, ennemis à double brin, animation par GDOT, points de vie | 60 images/s dans le navigateur (JS traduit) ; comportements identiques à la référence Python |
| Génomique | motif de 16 bases dans 16 384, deux différences | ×6,1 avec QEGAL et COMPTE, 16 fois moins de mémoire |
| Logique : capteurs, initialisation | Belnap en pratique | ×2,8 avec 16 portes par mot ; un booléen confondrait 15 847 lectures sur 300 graphes |
| Ombre binaire, compression du cube | le cube grossier, les palettes ADN/ARN | volume 256³ comprimé 35,5 fois ; saut des blocs vides ×1,5 |
| Feu de camp | ombre quaternaire (analyse à la demande, 4 % des voxels), parcours exact, PBR Cook-Torrance, animation par la mémoire du cube (comme Pégase) | une image en un tiers de seconde en code natif |
| Correction d'erreur diamant | 3 quits de contrôle, état en Belnap | à 1 % d'erreur par quit : 12 % de mots faux sans code, 0,8 % avec |
| **ScoR** (spirale sur constellation de recherche) | l'IA native : graine hex, mémoire courte en ARN, sommeil et rêve (consolidation), spirale à énergie d'activation, épissage de Belnap, anti-cube (recherche contraire), raisonnement en chaînes, voix | 8 conclusions attendues sur 8 (diamant de Nixon : variable) ; 45 à 60 % de réponses appuyées : limite honnête, trois dimensions restent étroites. En pause. |
| Les compilateurs eux-mêmes | vtxc et vtxc64 | 160 000 mots, point fixe, mêmes mots que Python |

---

## 8. Les optimisations, et l'idée du magasin

### 8.1 Le principe (le créateur, 23 octobre)

**Un calcul qui transporte et répartit les objets dans un magasin** : ce qui sort le plus est près de la porte (les
registres, puis la mémoire) ; ce qui part ensemble est rangé ensemble (la localité) ; un rayon par durée de vie (le
frais se vide d'un coup). Et, comme **l'eau**, qui se met de niveau, suit la pente et creuse son lit là où elle
passe souvent : on mesure le flux (le profil d'exécution) et on élargit le lit là où ça coule fort.

### 8.2 Ce qui est fait dans les compilateurs

| Optimisation | Image | Effet mesuré |
|---|---|---|
| Élagage des fonctions jamais appelées, sauts directs sur les conditions | | 26 à 33 % de mots, 36 à 44 % d'instructions en moins (0.2) |
| **Variables en registres** R9 à R12 (usages pondérés ×8 par niveau de boucle) | le comptoir : les articles qui sortent le plus | boucle serrée 1,02 s → 0,63 s |
| **Épissage** : règles pile, constante, relecture, copie, avec analyse de vie des registres | l'ARN messager dont on retire les introns | tableaux −16 %, questions −20 % ; code 9 à 12 % plus court |
| **Réécriture en 16 (32) éléments d'un coup** des boucles sur tableaux rangés | une case où tout s'affiche en même temps | ×15,4 sur la fusion de témoignages (plafond ×16) |
| LDQ / STQ, Belnap en instructions, CMPI, LDIS/LDIU (SPU-64) | le quaternaire en une instruction | génome lu base par base 8,67 M → 3,70 M instructions |
| **Épissage par échange** (`MOV Ra,Rb ; … lit Ra …` → `… lit Rb …`), en deux temps comme l'auto-épissage des introns de groupe I et II, la vie des registres refaite seulement sur le site (24 octobre) | la transestérification : des liaisons échangées, aucune créée ni perdue | code −6 %, F5 −9 % |
| **Expansion en ligne** des petites fonctions (un seul `retour E`, une écriture, un appel), arguments déplacés seulement s'ils ne font que calculer (SPU-64, 24 octobre) | l'article posé directement au comptoir, sans aller-retour à la réserve | vtxc64 : 554 → 422 millions d'instructions pour le même travail ; bonjour64 −23 % |
| **Prélude à la demande** | | un programme d'une ligne 197 → 100 ms |
| **Tables dans les cubes** (vtxc64) | un rayon par rôle et durée de vie | voir 8.3 |

### 8.3 Les tables de noms dans les cubes (vtxc64, 23 octobre)

- vtxc64 cherchait chaque nom en parcourant des listes. Il range maintenant ses noms dans des **cubes de l'étage 3** :
  la fréquence du cube dit le rôle et la durée de vie (le permanent : mots-clés, intégrés ; ce qui vit toute la
  compilation : fonctions, constantes, textes, fonctions du prélude ; **le frais : les variables de la fonction en
  cours, rayon vidé d'un coup par `jeter_cube`**) ; le `#RRGGBB` de la case vient du hachage du nom (FNV-1a de
  64 bits).
- **Le hachage Robin Hood, comme l'eau qui se met de niveau** : quand deux noms veulent la même case, celui qui est
  déjà le plus loin de sa case d'origine la garde, l'autre continue ; les distances s'égalisent, et une recherche
  s'arrête dès qu'elle croise un nom plus proche de chez lui qu'elle ne l'est.
- **Une idée corrigée en route** : on avait d'abord appelé ces rayons des « températures » (en kelvins, mêlées au
  hachage et à la foulée du sondage). Le créateur a douté, à raison : le nombre en kelvins n'apporte rien au calcul ;
  ce qui sert, c'est la séparation par durée de vie. La température est abandonnée au profit de l'image du magasin.
- **Mesuré** : vtxc64 se compile en 550 à 625 millions d'instructions au lieu de 1,2 milliard (×2) ; un petit
  programme avec le prélude, 90 millions au lieu de 179. Le hachage seul fait environ un tiers du gain ; le reste vient
  du tas qui ne remet plus à zéro une mémoire déjà nulle et des accès directs dans les fonctions de base. Robin Hood
  ne change presque rien à la vitesse aujourd'hui (les tables sont très peu remplies : 16 millions de cases) ; il rend
  la recherche sûre et prévisible si elles se remplissent. **Les mots produits ne changent pas** (point fixe et tests
  différentiels).
- **Fait (24 octobre)** : l'expansion en ligne des toutes petites fonctions (`elem`, `poser`, `cube_t`…), dans
  vtx64.py et vtxc64 ensemble (docs/vtx64-langage.md, section 10). **Prochaines pistes mesurées** : les copies de
  registres (MOV, 12 % des instructions), le type de chaque expression gardé au lieu d'être recalculé dans vtxc64, et
  l'épissage (un cinquième du temps de compilation). **Fait aussi** : la règle échange (section 11 de
  docs/vtx64-langage.md) et le tas de vtxc64 sans plafond (il débordait sans le dire au-delà de 6,3 millions de mots).

---

## 9. Les innovations

### 9.1 Nouvelles (propres à Vercintorix)

1. **Le cube chromatique comme mémoire** : chaque mot est une couleur, chaque adresse un point `#RRGGBB`, et la même
   valeur se lit en hex, en quits et en bases d'ADN.
2. **Le point profond et l'adresse longue** : le mot de 64 bits est une couleur à 16 bits par voie, et une adresse
   porte son étage et son cube (fréquence) ; les cubes s'additionnent par fréquences.
3. **Les flottants quaternaires à état de Belnap** (32, 64 et 128 bits) : exposant en base 4, *inconnu* et *variable*
   distingués là où l'IEEE n'a qu'un NaN, en instructions de la machine.
4. **La logique de Belnap comme type du langage**, avec obligation de traiter les quatre cas, et 16 ou 32 valeurs
   traitées par instruction ; l'anti-cube.
5. **Le brin ADN / ARN de chaque mot** : la machine refuse d'écrire un résultat fixé ; le programme est protégé dès
   le départ.
6. **Les hypothèses dans le langage** : un bloc dont les écritures s'annulent ou se valident (le double brin).
7. **La partition musicale des tâches** : accords, mesures, notes, segments, cumulants, cylindres en V6, noms
   gaulois ; le parallélisme se déduit du programme, sans rien écrire.
8. **L'épissage** comme représentation intermédiaire du compilateur.
9. **La réécriture automatique en 16 / 32 éléments d'un coup** des boucles sur tableaux de quits.
10. **L'ombre quaternaire analysée à la demande** (vide, brume, plein, inconnu) pour le rendu volumique.
11. **La compression ADN / ARN** du cube, lisible sans décompresser.
12. **Le ScoR** : une IA à spirale sur constellation, sommeil et rêve, épissage de Belnap, recherche contraire dans
    l'anti-cube.
13. **La correction d'erreur diamant**, dont l'état est un logique de Belnap.
14. **Les tables du compilateur dans des cubes jetables**, rangées par rôle et durée de vie, hachées en Robin Hood.

### 9.2 Améliorées (techniques connues, adaptées au cube)

- La recherche par similarité (centrage sur la diagonale des gris, grille de hachage sur les distances aux pivots).
- Le calcul d'IA par `gemv` sur les voies du mot.
- Le compilateur auto-hébergé (point fixe), le test différentiel à des milliers de programmes, le corpus de
  conformité multi-machines.
- L'allocation des registres, l'analyse de vie, le ramasse-miettes prudent, le tas qui dure (`sauver_tas`).
- L'affichage exact le plus court (Dragon4) étendu au bord quaternaire (au bas d'une puissance de 4, le voisin du
  dessous est quatre fois plus près).
- Les cubes sur disque relus page par page au premier accès.

### 9.3 Écartées, corrigées ou en attente (honnêtement)

- **Écarté** : le canal caché T/U en matériel ; la « brume » (exécution spéculative visible) ; l'écriture simplifiée
  (point-virgule facultatif, sections), à repenser ; le suivi des constantes en Belnap dans l'épissage (0,1 % de
  calculs trouvés) ; les températures du compilateur (remplacées par les rayons par durée de vie).
- **Corrigé** : les gains « sur N canaux » des cylindres (trop beaux) ; les sauts limités à 65 536 mots ; la mémoire
  qui dure (un texte écrit dans le programme, rangé dans le tas, changeait à la recompilation) ; le premier flottant
  de 128 bits (binary128 de l'IEEE) remplacé par un format quaternaire ; un `.bat` livré en fins de ligne Unix.
- **En pause** : le ScoR (v1 faite) ; le jeu ; la traduction native (`natif/`, mise de côté).
- **Retiré** : la machine Java ; les machines JavaScript ne sont pas portées au SPU-64.

---

## 10. Règles de travail retenues

- Toute évolution dans **les deux compilateurs**, avec les **mêmes mots** et le corpus de conformité.
- **Mesurer avant de croire** : chaque gain annoncé est mesuré (instructions, secondes), chaque écart cherché par des
  programmes aléatoires contre une référence indépendante.
- **Corriger honnêtement** : une erreur trouvée est écrite dans ce carnet, avec sa correction.
- Les `.bat` livrés sont en **CRLF et ASCII** ; le créateur les lance lui-même.
- Le SPU-32 et ses programmes restent tels quels : le SPU-64 vit à côté.

---

## 11. Feuille de route

1. **Fait** : SPU-64 (machines Python et Rust), vtx64.py, vtxc64 et son point fixe, les tables dans les cubes.
2. **Fait (23 octobre)** : vtxc64 embarqué dans **vtx64.exe** (sans Python) et l'atelier Rust sur la SPU-64.
   **Fait (24 octobre)** : l'expansion en ligne des petites fonctions (vtx64.py et vtxc64 ensemble).
   **Ensuite** : le générateur natif (x86-64 et PE écrits en vtx) pour l'autonomie complète.
3. **L'atelier sur le SPU-64 écrit en vtx**, à la façon de VS Code (une couche mince de la machine pour la fenêtre,
   les événements, les dossiers et le presse-papiers) ; le brin posé automatiquement.
4. **Gobatix** : la zone de modélisation dans un cube vide, remplir, creuser, peindre, en xyz hexadécimal.
5. Plus tard : des instructions petuar si la vitesse gêne ; la vitesse en général ; le ScoR v2 ; le recuit simulé
   (un vrai algorithme à température) pour l'allocation des registres, si les deux compilateurs l'appliquent avec le
   même hasard déterministe.
6. Le but lointain : le SPU spectral (section 2), d'abord sur un banc d'essai à une liaison et des LED adressables.

---

## 12. Vocabulaire gaulois (hommage, à valider avec un spécialiste)

| Idée | Racine gauloise | Sens | Statut |
|---|---|---|---|
| `principal` | *rīx* | roi | racine attestée (noms en -rix) |
| nom du langage | *uer-* + *cingeto-* + *rīx* | sur- + guerrier, marcheur + roi | forme usuelle de Vercingétorix |
| `pour` | *cingo-* | avancer, marcher | reconstruit |
| quit, 128 bits (`petuar`) | *petru-* | quatre | admise |
| `vrai` / `faux` | *mat* / *anmat* | bon / pas bon | calendrier de Coligny |
| module | *briga* | hauteur fortifiée | attestée |
| mémoire, étages | *nemeton* | sanctuaire | attestée |
| segments 1 à 10 | *cintux, allos, tritios, petuarios, pinpetos, suexos, sextametos, oxtumetos, nametos, decametos* | premier à dixième | comptes de La Graufesenque |
| Gobatix | en référence à un dieu gaulois (peut-être *Gobannos*, le forgeron : à confirmer) | le modeleur | nom choisi |

## 13. Glossaire

- **quit** : chiffre en base 4 (2 bits). **point** : `#RRGGBB`. **point profond** : `#RRRRGGGGBBBBAAAA`.
- **étage** : un des 4 cubes de la mémoire (0 CPU, 1 GPU, 2 partagé, 3 disque). **fréquence** : le numéro d'un cube
  dans un étage. **adresse longue** : étage, fréquence, point.
- **brin** : libre, ADN (fixé), ARN (travail). **épissage** : retrait des introns par le compilateur.
- **accord, mesure, note, segment, cylindre** : la partition des tâches.
- **point fixe** : un compilateur qui se recompile à l'identique.
- **SPU** : le processeur du cube. **SPRAM** : sa RAM spectrale étagée. **MAR** : le registre d'adresse à 8 lasers.

---

# Annexe : le journal d'origine (versions 0.1 à 0.4)

*Gardé tel quel : la trace de ce qui a été imaginé, mesuré et corrigé, programme après programme, jusqu'au
20 octobre 2026. La suite (autonomie, SPU-64) est dans `vtx-0-5-autonomie.md`.*

Carnet vivant : à chaque programme écrit, on note ce qui manquait au langage. Dernière mise à jour : 20 octobre 2026, vtx 0.4 (flottants binary32, entiers de 64 bits, débogueur au niveau du source, partition automatique des tâches) et « Labyrinthe du cube » version 3. Référence complète du langage : `vtx-syntaxe-v0-4.md`.

### Programmes écrits en vtx

| Programme | Rôle | Mots (0.1 → 0.2) |
|---|---|---|
| `memoire_cube_v2.vtx` | Mémoire associative, plasticité, implants | 1 129 → 799 |
| `spectre_cube.vtx` | Appariement spectral (16 bandes = 4 mots) | 771 → 567 |
| `adn_tu.vtx` | Canal caché par synonymie T/U | 206 → 137 |
| `chariot.vtx` | Contrôleur de chariot (exact, GDOT, arbre), écrit en 0.2 | 441 |

### Fait dans vtx 0.2 (vérifié)

Suite de 26 tests ; les trois programmes de la 0.1 donnent exactement les mêmes sorties et la même mémoire ; l'émulateur JS donne les mêmes résultats que Python sur 150 cas du chariot et 17 programmes de test.

- Étage variable `@(e)[a]` (instructions LDX et STX).
- Opérateurs `&&`, `||`, `!` avec court-circuit, moins unaire.
- Priorité comme en Rust : le bit à bit lie plus fort que les comparaisons.
- Boucle `pour i dans a..b`, `constante N = 5;`, `donnees @2[0] = { ... };` (écrites une seule fois).
- Prélude, inclus seulement s'il est appelé : `abs inf sup min max poids gdotn copier melange`.
- Division par zéro définie (x / 0 = 0xFFFFFFFF, x % 0 = x).
- Commande `profil` : histogramme des instructions, GDOT, accès par étage.
- Compilateur : fonctions inutiles élaguées, conditions en sauts directs : 26 à 33 % de mots en moins, 36 à 44 % d'instructions en moins.

### Reste à faire

1. **Instruction matricielle (faite en 0.2.1 : `gemv`, 27 tests).** Dans le chariot, GDOT ne représente que 0,9 % des instructions de la recherche par similarité (671 par décision). Un moteur de produit scalaire ne sert à rien tant qu'on l'appelle une entrée à la fois : il faut une instruction « matrice × vecteur » qui score toutes les entrées d'un coup.
2. **Recherche approchée par quantification** (seaux de couleurs) : la vraie base de comparaison face à la similarité, plutôt que l'égalité exacte.
3. **Rejet des inconnus** : un tag jamais vu doit être refusé. La similarité répond toujours ; il faut un seuil de confiance.
4. Entiers signés natifs (aujourd'hui seulement `abs`, `inf`, `sup` dans le prélude).
5. Tableaux et structures.
6. Messages d'erreur avec colonne.
7. Port Rust : `vtx.rs` n'a jamais été compilé et n'a pas la 0.2. `vtx.py` reste la référence.
8. DMA matérielle (remplacée par `copier` du prélude).
9. Argmax matériel (le gagnant, ou les k meilleurs) : il reste 35 instructions par entrée une fois le produit scalaire déporté, ce qui plafonne le gain.
10. Clés multi-mots dans le format du cube pour les grandes bibliothèques.
12. Centrage et index par la moyenne : faits (voir résultats). Reste à tester sur des bibliothèques structurées (moyennes proches), avec maintenance de l'ordre trié lors des ajouts et de la plasticité.
13. Effacements T/U avec décodage d'effacements (non testé).
11. Test du moteur bruité : fait (`test_moteur_bruite.py`). Recherche en deux étages testée (`test_deux_etages.py`) : elle ne sauve rien sous 35 dB (k = 16 donne 6 à 44 % à 25 et 30 dB) ; à 35 dB et k = 64, 84 à 97,5 %. Reste à tester le moteur bruité sur les vrais cas (chariot, spectres).

### Vocabulaire actuel (vtx 0.2 avec gemv)

- **Mots-clés (12)** : `fonction soit si sinon tantque retour constante pour dans donnees arrêter continuer`.
- **Fonctions intégrées (8)** : `sortie entrée min4 max4 addm4 cmp3 gdot gemv`.
- **Prélude (9, inclus seulement s'ils sont appelés)** : `abs inf sup min max poids gdotn copier melange`.
- **Opérateurs** : `+ - * / % << >> <<q >>q & | ^ ~ ! && || == != < <= > >=`, moins unaire, plage `a..b`.
- **Accès au cube** : champs `.r .v .b .a`, quit `.q(i)`, mémoire `@e[a]` (étage littéral) et `@(e)[a]` (étage variable).
- **Littéraux** : décimal, `0x` hexadécimal, `0q` base 4, `#RRGGBB` (alpha 0), `#RRGGBBAA`, séparateur `_`.
- **Trois types** (0.4) : `entier` (mot de 32 bits non signé, par défaut), `flottant` (binary32), `long` (64 bits signé). Quatre étages mémoire, adresses sur 24 bits ; l'étage 0 contient aussi le code et la pile.
- **Commandes** : `run`, `profil`, `compile`, `asm`, `test`.

### Vocabulaire à adapter ou augmenter (propositions, à valider)

1. ~~Contrôle de boucle~~ **fait** : `arrêter` et `continuer`.
2. ~~Alias lisibles~~ **fait** : `et`, `ou`, `non` pour `&&`, `||`, `!` ; constantes `vrai` et `faux`.
3. **Types** : `entier`, `flottant`, `long` **faits** (0.4) ; restent `signé`, `couleur` (mot RGBA), `quit`, `octet`.
4. **Verbes propres au cube** : `centrer(mot)`, `moyenne(mot)`, `distance2(a, b)`, `interpoler(a, b, c, d, u, v)` ; pour la recherche `pivot`, `cellule`, `sonde`, `attention` (alias de `poids`).
5. ~~Étages nommés~~ **fait** : `CPU`, `GPU`, `PARTAGE`, `DISQUE` (`@PARTAGE[3]`).
6. ~~Accents et outils~~ **fait** : `entree` pour `entrée`, `données` pour `donnees`, `arreter` pour `arrêter`.
7. **Structure du programme** : `module` et `importer` pour ranger les programmes (aujourd'hui un seul fichier).
8. ~~Littéraux ADN~~ **fait** : `adn"ACGT"` (A = 0, C = 1, G = 2, T = U = 3, 16 lettres au plus, la première est la plus forte).

### Limites connues (liste honnête, il y en a encore trop)

- Flottants binary32 et longs de 64 bits depuis la 0.4 ; pas de flottants de 64 bits ; le signe des entiers passe par les opérateurs `.< .<= .> .>= ./ .% .>>`.
- Pas de chaînes ni de tableaux à plusieurs dimensions ; les tableaux et structures n'ont pas de contrôle d'indice à l'exécution (seulement pour un indice constant).
- Boucle `pour` croissante seulement (pas positif avec `par`) ; borne réévaluée à chaque tour.
- Code limité à 65 536 mots (saut sur 16 bits), les données en segment n'y comptent plus ; au plus 127 variables locales ; une seule valeur de retour.
- Erreurs avec numéro de ligne seulement, pas de colonne, pas d'avertissements (variable inutilisée, code mort).
- Une définition de l'utilisateur remplace en silence une fonction du prélude de même nom.
- Compilateur simple : trois registres de travail, beaucoup de PUSH et POP, environ 7 mots par ligne.
- `gemv` ne travaille que sur l'étage 2 ; `DMA` n'est pas implémentée ; les données `donnees` réservent la dernière adresse de l'étage 3.
- Écrire dans l'étage 0 peut écraser le code ou la pile.
- `vtx.rs` n'a jamais été compilé et n'a pas la 0.2 ; l'émulateur JS n'a pas `gemv`.
- Débogueur au niveau du source depuis la 0.4 ; pas encore de points d'arrêt conditionnels ni de surveillance de la mémoire.

### Documents à mettre à jour

- **Syntaxe vtx publiée en v0.1** : priorité des opérateurs, `pour`, `constante`, `donnees`, étage variable, `&&`, `||`, `!`, prélude, `gemv`.
- **Spécification du SPU (v0.4)** : instructions `LDX`, `STX`, `GEMV`, division par zéro définie, nouvelle priorité, cache RGBA, centrage et index.
- **Protocole du banc d'essai** : ajouter le moteur bruité, la relecture sélective et le sonar.

### Critères de la mise à niveau complète (à fixer avant le test différentiel)

1. Grammaire et vocabulaire gelés dans la syntaxe vtx mise à jour.
2. Tous les programmes de ce carnet compilent et donnent les mêmes sorties que leur référence numpy ou Python.
3. Test différentiel : au moins 1 000 programmes aléatoires, compilés avec et sans élagage ni sauts directs, sorties identiques. **Fait** : 1 000 programmes, 0 écart entre l'oracle, le compilé optimisé et le compilé simple.
4. Équivalence des machines : le même code machine donne les mêmes sorties sur Python et sur JS (et sur Rust après compilation chez l'utilisateur). **Python contre JS fait** : 400 programmes, 0 écart sur les sorties, le nombre d'instructions et la mémoire ; Rust à faire.
5. Charge réelle : la grille de hachage écrite en vtx retrouve le même souvenir que numpy sur toutes les requêtes.
6. Budgets de régression : taille et nombre d'instructions des programmes existants pas pires de plus de 5 %.
7. Chaque erreur de compilation prévue donne un message en français avec la ligne. **Fait** : message plus extrait de la ligne fautive (pas de colonne).

### Résultats à retenir

- **Test d'échelle** (`test_echelle.py`, données en mots hex) : le gain vient de la longueur des vecteurs, pas du nombre de souvenirs. Limite d'Amdahl avec argmax numérique : 2,5 fois (clé de 4 octets), 4,9 fois (16 octets), 14,5 fois (64 octets). GDOT seul ne fait gagner que 1,7 à 3 fois sur du code scalaire.
- Une clé d'un seul mot RGBA ne tient pas au-delà d'environ 64 souvenirs à 25 dB (98 %) ; à 4 096 souvenirs il en reste 35 %. Des clés de 16 octets tiennent 4 096 souvenirs dès 20 dB.
- Conversion maximale tolérable par score (en instructions du SPU) : 52, 136 et 471 pour 4, 16 et 64 octets. Ce sont des seuils à comparer à de vrais coûts, pas des mesures.

- Spectres : la distance minimale en entiers égale des classifieurs entraînés dès 15 dB (scène synthétique).
- Canal caché T/U : +12,3 % de capacité mesurée, mais −2,5 dB de marge si U est voisin de T sur le même axe.
- LOD : l'erreur géométrique est bornée (environ 5 fois moins de triangles à 0,5 px) ; l'ombrage par sommet limite, d'où l'ombrage par pixel.
- Chariot : la similarité réussit 100 % des tours sûrs dès 25 dB contre 67 % pour l'arbre à seuils, mais coûte 671 instructions par décision contre 96. L'égalité exacte échoue partout dès que l'éclairage varie.

- **Moteur bruité** (requête à 20 dB, bibliothèque aléatoire) : pour garder 95 % de la précision d'un moteur parfait, il faut environ 50 dB de rapport signal/bruit et un convertisseur de 6 bits avec des clés de 16 octets (jusqu'à 4 096 souvenirs), environ 40 dB et 5 bits avec 64 octets. Avec une clé de 4 octets, aucun moteur ne suffit à grande échelle.

- **Test décisif** (`test_decisif.py`, moteur bruité sur les vrais cas, lecture à 25 dB) : le centrage sur la diagonale grise (le moteur traite les vecteurs centrés, le numérique ajoute le terme exact D·(écart de moyenne)²) vaut environ 12 dB de précision de moteur, sans rien perdre. Chariot : brut 56 % à 25 dB, centré + 2 candidats vérifiés 99,9 %. Spectres : 39 % brut, 83,5 % centré + 2 candidats à 25 dB ; 98 % à 35 dB.
- **Hamming (21,18) sur 4 symboles** : utile seulement à faible taux d'erreur de mémoire (jusqu'à 2 % par quit) ; à 8 % il aggrave. Le gain de précision de recherche est petit (au plus 1,6 point) car la similarité tolère déjà une erreur isolée.

- **Région d'incertitude** (`test_position.py`) : le bruit dessine une boule autour de la lecture, pas un triangle. Nombre moyen d'autres entrées dans la boule à 95 % (M = 4 096, 20 dB) : 180 avec 4 octets, 0,02 avec 16 octets. C'est le critère de réussite de la recherche.
- **Index par la moyenne** : garde 58 % de la bibliothèque à 20 dB, 20 % à 30 dB, 6 % à 40 dB, sans perte de précision. Il n'élague bien qu'à fort rapport signal/bruit.
- **Décodage souple contre Hamming dur** (code (5,3) sur 4 symboles) : environ 2 dB de gain (erreur par bloc 0,76 % contre 4,42 % à 20 dB), mais le code coûte 40 % de débit : il ne rapporte du débit net qu'en dessous d'environ 17 dB.

- **Centrage et index en vtx** (`test_centrage.py`, M = 1 024, résultats identiques au calcul numpy dans 240 exécutions sur 240) : le centrage coûte 51 instructions par entrée contre 35 (+46 %) et 714 instructions fixes par requête (clé de 16 octets). L'index par la moyenne ramène le balayage à 7 instructions par entrée à 30 dB (fenêtre de 19 à 23 %) et 3 à 4 à 40 dB (6 à 8 %) : gain de 4 à 5 fois à 30 dB, 10 à 12 fois à 40 dB sur le programme brut. Index + centrage : 2,5 à 3,4 fois à 30 dB, 6 à 9 fois à 40 dB.

- **Index sur bibliothèques structurées** (`test_bibliotheques.py`, 4 096 entrées de 16 octets, rappel au moins 99 %) : l'index par la diagonale grise n'est pas compétitif. Part balayée à 30 dB : 21 % (aléatoire), 26 % (64 classes), 100 % (luminosité égale : il s'effondre), 12 % (spectres lisses). IVF à 64 groupes balaie 3 à 5 % partout ; PC1 (droite choisie dans les données) 10 à 20 %. Le critère « 2 à 4 fois supérieur » n'est pas atteint par l'index ; le centrage reste la correction de point zéro habituelle des calculs entiers quantifiés.
- Piste suivante : index par préfixe de code de Morton (les premiers quits de chaque voie), sans apprentissage, face à IVF.

- **Lectures répétées et élimination séquentielle** (`test_sequentiel.py`, moteur centré, 4 096 entrées de 16 octets, bruit indépendant entre lectures : hypothèse) : à 25 dB de moteur, une lecture donne 31,5 %, 16 lectures de tout 99 % (coût 16), l'élimination séquentielle avec marge z = 3 donne 99,5 % pour un coût de 1,33 lecture par entrée. À 30 dB : 100 % pour 1,04. À 20 dB : 98,5 % pour 2,45 (z = 3). La marge qui dépend de la « température » z fait gagner environ 12 fois sur la moyenne fixe. Un défaut fixe du moteur ne se moyenne pas : à vérifier.

- **Sonar par pivots** (`test_sonar.py`, inégalité triangulaire, anneaux de rayon 3,5·σ, rappel au moins 99 %) : il ne reste que 0,02 à 0,7 % de candidats à calculer, contre 3 à 5 % pour IVF, mais les comparaisons d'anneaux dominent : coût équivalent 5,6 à 16,5 % à 30 dB (IVF 3 à 5 %), 1,7 à 4,3 % à 40 dB (IVF 3 à 5 %). Il ne gagne nettement que sur les spectres lisses à 40 dB. Le poids d'une comparaison (0,3 calcul) est une hypothèse. Piste : grille de hachage sur les distances aux pivots pour supprimer les passes de comparaison (non testé).

- **Grille de hachage sur les distances aux pivots** (`test_grille.py`, rappel 100 % partout, 4 à 6 pivots) : coût équivalent 1,5 à 2,1 % à 30 dB sur trois bibliothèques sur quatre (IVF 4,7 à 5,3 %, soit 2,2 à 3,5 fois moins), 4,0 % sur les 64 classes serrées (IVF 3,1 %) ; à 40 dB 0,3 à 0,7 % (IVF 3,1 à 5,3 %, soit 4 à 18 fois moins). Première méthode à atteindre le seuil de 2 à 4 fois face à une méthode classique. Limites : table sans collisions de hachage, coût de lecture de cellule supposé à 0,3 calcul, bruit connu, IVF non optimisé, pas de comparaison avec HNSW, maintenance de la table à l'insertion non comptée.

- **Test différentiel** (`test_differentiel.py`) : 1 000 programmes aléatoires, 0 écart. Taille moyenne 915 mots sans optimisation, 494 avec (46 % en moins), instructions 2 808 contre 1 999 (29 % en moins). Le premier passage montrait 143 « écarts » : c'étaient des erreurs du générateur (variables de boucle hors de portée dans les `tantque`), corrigées ; aucun écart du compilateur. Lacunes : les expressions générées sont entièrement parenthésées, donc la table de priorités n'est testée que par les tests unitaires ; l'oracle et le compilateur partagent le même analyseur syntaxique ; ne sont pas couverts `entrée`, `constante`, `donnees`, `gemv`, la récursion.

### Protocoles

- [x] Reconnaissance (spectres) · canal caché T/U · chariot d'usine.
- [ ] Stabilité du LOD : niveaux par puissances de 2, échantillons emboîtés, seuil d'erreur.
- [ ] Test d'efficacité : voir la réponse du dernier échange (coût selon la taille, rejet des inconnus, comparaison à précision égale).

### Mise à niveau 0.2.2 : ce qui est fait (vérifié)

- Nouveautés : `arrêter`, `continuer`, alias `et ou non vrai faux`, étages nommés, alias `entree`, `données`, `arreter`, extrait de la ligne fautive dans les erreurs, option `optim=False` du compilateur.
- 31 tests du langage sur 31.
- **Priorités sans parenthèses** (`test_priorites.py`) : 3 000 expressions, les 20 opérateurs binaires couverts, 0 écart face à un évaluateur indépendant.
- **Budgets** (`test_budgets.py`, `budgets.json`) : mots et instructions des programmes de référence tenus ; le code machine de 304 programmes est identique avant et après le correctif.
- **Différentiel** : 1 000 programmes, 0 écart.
- **Équivalence des machines** : Python, JS (400 programmes) et **Java** (`Vtx.java`, 425 programmes : 400 aléatoires, 21 tests du langage, 4 programmes réels) donnent les mêmes sorties, le même nombre d'instructions et la même mémoire.
- **Corpus de conformité** : `corpus_conformite.txt` (programmes et entrées) et `corpus_attendu.txt` (résultats attendus : instructions|sorties|mémoire des étages 1 à 3). Toute nouvelle machine (Rust, Java, autre) doit reproduire ce fichier ligne à ligne.

### Mise à niveau : ce qui reste

1. Grille de hachage écrite en vtx et comparée à numpy.
2. Port du compilateur en Java ; émulateur Rust **fait** (`vtx-rs/`, vtx 0.4) ; compilateur et traducteur natif en Rust à faire.
3. Entiers signés natifs, tableaux, structures, chaînes, modules et importations.
4. Colonne dans les erreurs, avertissements (variable inutilisée, code mort), débogueur et trace.
5. Le test différentiel ne génère pas encore `entrée`, `constante`, `donnees`, `gemv`, la récursion, `arrêter` et `continuer`.

### Alias gaulois (hommage, à valider avec un spécialiste)

Le gaulois est attesté de façon fragmentaire ; aucun mot d'informatique n'existe : ce sont des néologismes bâtis sur des racines connues. Références à consulter : le dictionnaire de la langue gauloise de Xavier Delamarre, les inscriptions et le calendrier de Coligny.

| Idée | Racine gauloise | Sens | Statut |
|---|---|---|---|
| `principal` | *rīx* | roi | racine attestée (noms en -rix) |
| nom du langage | *uer-* + *cingeto-* + *rīx* | sur- + guerrier, marcheur + roi | forme usuelle du nom de Vercingétorix |
| `pour` (boucle qui avance) | *cingo-* | avancer, marcher | racine reconstruite, forme verbale proposée |
| quit (chiffre à quatre valeurs) | *petru-* | quatre (cf. Petrucores, « les quatre armées ») | racine admise |
| `vrai` / `faux` | *mat* / *anmat* | bon / pas bon | abréviations du calendrier de Coligny |
| module, ensemble de fonctions | *briga* | hauteur fortifiée | racine attestée (toponymes) |
| mémoire, étages | *nemeton* | sanctuaire, bois sacré | racine attestée |
| 1, 2, 3 d'un quit | *oino-*, *dau-*, *tri-* | un, deux, trois | racines admises ; le zéro n'existe pas |

### IA sur le cube (`test_ia_vtx.py`)

- **Réseau 64 -> 24 -> 10** sur les chiffres manuscrits (540 images de test), poids en octets signés rangés en mots hex (octet + 128, point zéro corrigé en numérique), une couche = un `gemv`, ReLU et requantification en vtx. Précision : flottant 96,5 %, entier 8 bits 96,7 %, vtx 96,7 % (540 images sur 540 identiques au calcul entier numpy).
- **Instructions par inférence** : scalaire 45 912, GDOT 18 384, `gemv` 2 932 (15,7 fois moins que le scalaire, 6,3 fois moins que GDOT ; 84 % du travail est déportable).
- **Bruit du moteur** : mesuré sous la pleine échelle théorique, il faut 50 dB (non signé 85,7 %, signé 94,3 %) ; mesuré sous la valeur efficace du signal (couche 1 : 56,841, couche 2 : 12,480), les résultats sont dans le tableau ci-dessous.
  - bruit 5 dB sous le signal : 63.9 %
  - bruit 10 dB sous le signal : 85.8 %
  - bruit 15 dB sous le signal : 94.5 %
  - bruit 20 dB sous le signal : 95.9 %
  - bruit 25 dB sous le signal : 96.3 %
  - bruit 30 dB sous le signal : 96.4 %
- **Test à faire : l'IA comme programmeuse** : 30 tâches vtx avec tests cachés, la spécification et le prélude en contexte, taux de réussite du premier essai, erreurs de compilation, comparaison avec et sans exemples ; à rejouer avec plusieurs modèles.

### Jeu de type Doom sur le cube (`rayons_vtx.py`, `rayons.vtx`, `rayons-demo.png`)

- **Preuve de concept faite** : moteur de rendu par lancer de rayons sur grille écrit en vtx (17 443 mots dont les tables), image de 128 × 64 mots RGBA dans l'étage 2, murs de quatre couleurs, brouillard de distance, plafond et sol en dégradé. 570 000 à 800 000 instructions par image (environ 700 000 en moyenne).
- **Contournements du langage** : pas d'entiers signés (tables sinus et cosinus décalées de 256), pas de tableaux (adresses à la main), `donnees` pour les tables de 1 024 valeurs.
- **À faire** : textures en patches à 4 coins, commandes configurables, portes, clés et interrupteurs, ennemis (états, vue par le même lanceur de rayons, plus court chemin), tests de qualité (images de référence, budgets d'instructions par image, équivalence Python, JS et Java, rejeu de parties scriptées).
- **Limites** : un jeu « à la Doom » avec des contenus originaux (les graphismes, niveaux et le nom Doom appartiennent à id Software) ; pas de son ; pas de test de ressenti ; l'émulateur Python est trop lent pour le temps réel (une page avec un émulateur JS à tableaux typés est le jalon suivant).

### vtx 0.3 : limites levées (vérifié)

Tout reste du quaternaire sur le cube : aucune instruction nouvelle dans le SPU, le mot reste de 16 quits (4 voies RGBA), les nouveautés se compilent vers les instructions existantes.

- **Données en segment** : `donnees` est rangé après le code et copié en assembleur (6 instructions par donnée). `rayons.vtx` passe de 17 443 à 2 867 mots (84 % en moins) avec une image identique ; `chariot.vtx` de 441 à 378 mots ; coût d'initialisation de 4 instructions de plus par bloc de données.
- **Signés** : `.<`, `.<=`, `.>`, `.>=` (comparaison par bascule du bit de signe), `./`, `.%` (division et reste, signe du dividende), `.>>` (décalage arithmétique), prélude `signe`.
- **Tableaux et structures** : `structure Point { x; y; }`, `tableau pts[4] de Point @PARTAGE[100];`, `pts[i].x`, `v[i]` ; indice constant hors du tableau refusé à la compilation.
- **Pas de boucle** : `pour i dans 0..10 par 3`.
- **Importation** : `importer "fichier.vtx";` insère le fichier une seule fois ; les numéros de ligne d'erreur se rapportent au texte assemblé.
- **Vérifications** : 41 tests du langage sur 41 ; différentiel 1 000 programmes, 0 écart ; priorités 3 000 expressions, 0 écart ; chariot, spectres et mémoire : mêmes sorties et même mémoire qu'avant ; corpus de conformité de 431 programmes (dont le jeu) rejoué sur Java, 0 écart ; budgets enregistrés à nouveau (chariot mode 2 : 210 à 222 instructions, initialisation comprise). La sauvegarde de la 0.2.2 ayant été perdue, la référence « avant » reconstitue l'ancienne initialisation des données.
- **Pas relancé** : l'émulateur JS (mêmes instructions, mais non rejoué sur le nouveau corpus).

### Bibliothèque du cube et couche ADN (`bibliotheque/`)

- **Contenu** : `cube.vtx` (voie, poser_voie, gris, ecart, distance2, melanger, centrer), `adn.vtx` (adn_voie, adn_porte, adn_ecrire, adn_appliquer et les constantes ADN_A, ADN_G, ADN_C, ADN_T, ADN_U), `essai.vtx` et `test_bibliotheque.py`. Utilisation : `importer "bibliotheque/cube.vtx";`.
- **Vérifié** : 300 paires de mots, 3 900 valeurs comparées à une référence Python, 0 écart ; 1 769 instructions par paire pour les 13 fonctions.
- **Convention (version biologique, à valider)** : la position est la valeur hexadécimale RRGGBB, le traitement est porté par l'alpha. Voies : A = rouge, G = vert, C = bleu. État tout ou rien : T = 1 = ADN, mémoire passive ; U = 0 = ARN, copie de travail active. Alpha : quit A3 = étage et quit A2 = type (inchangés), quit A1 = lettre de la voie (A = 1, G = 2, C = 3, 0 = aucune), bit 0 = état.
- **Traitement** : seul un ARN (U = 0) est traité, `adn_appliquer(m, x)` remplace la voie désignée par x ; un ADN (T = 1) est rendu inchangé. `transcrire` (T devient U) fait la copie de travail, `retrotranscrire` (U devient T) écrit en mémoire, `adn_executer` applique une mémoire sur une copie en la laissant intacte. Test : 300 paires, 4 800 valeurs, 0 écart.
- **Limites** : les noms sont une convention sans contenu biologique ; le descripteur ne compte que 7 états (3 voies, ouvert ou fermé, plus aucune) : c'est une couche de sélection et de prédication, le code d'opération reste dans le mot d'instruction.

### Pistes biologiques et physiques (idées, non implémentées)

- **Complémentarité** : en biologie A s'apparie à T (ou U) et G à C ; avec l'ordre A, C, G, T codés 0, 1, 2, 3, le complément est 3 moins la valeur. Un « double brin » (un mot et son complément) donnerait une détection d'erreur, comme la réparation de l'ADN.
- **Valeur d'une base** : la lettre choisit la voie, la valeur de la voie en est l'intensité. Ancrage physique possible : fréquence de référence par voie, longueurs d'onde des primaires CIE (700 nm = 428 THz, 546,1 nm = 549 THz, 435,8 nm = 688 THz), angle de teinte en degrés calculé à partir de RVB, loi de Beer-Lambert pour relier l'intensité à une absorbance.
- **Écriture de mémoires ADN** : un littéral du type `adn"ACGT..."` (lettres vers quits) rendrait la saisie de mémoires directe en hexadécimal.

### Jeu : ennemis à double brin (`jeu/`)

- **Contenu** : `ennemis.vtx` (module), `essai_tic.vtx` et `simulation.vtx` (programmes d'essai), `carte.vtx` (générée), `test_ennemis.py`. Ennemis = mots `#RRGGBBAA` (R colonne, V ligne, alpha = ADN), parcours en largeur pour le chemin, quatre ennemis, grille 16 × 16 avec boucle autour d'un bloc central.
- **Double brin = hypothèse** : l'ADN (T = 1) est l'état validé, l'ARN (U = 0) reçoit le déplacement hypothétique ; les conflits se résolvent par numéro (le plus petit l'emporte, les autres reviennent en arrière) ; la rétrotranscription valide.
- **Vérifié** : le vtx donne les mêmes résultats que la référence Python sur 80 tours sur 80 (deux modes) et 4 simulations complètes sur 4.
- **Coût** : 45 357 instructions par tour avec le double brin, 32 529 avec la mise à jour sur place (39 % de plus), pour une mémoire doublée.
- **Ordre de mise à jour** : sur 2 000 scénarios d'ennemis groupés, 48,5 % des résultats dépendent de l'ordre avec la mise à jour sur place, 0 % avec le double brin (20 scénarios sur 20 à résultat unique rejoués en vtx).
- **Anticipation (valeur prévue k tours plus loin, extrapolation linéaire)** : avec quatre ennemis proches, elle ne gagne rien (poursuite directe 6,7 tours, anticipation 9,1 à 12,0). Avec un seul ennemi à vitesse égale : directe 24,2 tours, k = 8 : 20,3, k = 2 : 28,6, k = 4 : 25,3. Avec un ennemi deux fois plus lent : directe 91,5 % de captures en 62,8 tours, k = 8 : 99,4 % en 42,4 tours, k = 4 : 80,7 % ; résultat peu régulier selon k.
- **À faire** : affichage des ennemis (sprites) dans le moteur de rendu, commandes, puzzles (portes, clés), page jouable avec émulateur JS.

### Hypothèses dans le langage (vtx 0.3)

- **Syntaxe** : `hypothèse { ... annuler; ... valider; ... }` (alias `hypothese`). Les écritures mémoire écrites dans le bloc sont journalisées ; `annuler;` les défait et sort du bloc, `valider;` (ou la fin du bloc) les garde. Les blocs s'imbriquent : une validation interne reste annulable par le bloc extérieur.
- **Réalisation** : le bloc devient une boucle à un tour, avec un journal d'annulation dans l'étage 3 (à partir de l'adresse 15 728 640, compteurs en 16 777 200 et 16 777 201). Aucune instruction nouvelle : les machines Python, Java et JS sont inchangées.
- **Règles** : seules les écritures écrites dans le bloc sont annulables (pas celles faites par les fonctions appelées) ; les variables locales ne sont pas défaites ; `retour`, `arrêter`, `continuer` ne peuvent pas sortir d'une hypothèse ; `annuler` et `valider` doivent être directement dans le bloc, hors boucle ; écriture dans l'étage 0 refusée.
- **Vérifié** : 50 tests du langage sur 50 ; différentiel 1 000 programmes, priorités 3 000 expressions, bibliothèque, ennemis et budgets sans régression.

### Jeu : puzzle clés et portes (`jeu/puzzle.vtx`, `jeu/test_puzzle.py`)

- Solveur en retour arrière écrit en vtx : chaque pas est une hypothèse, validée si elle mène à la sortie, annulée sinon ; la mémoire des cases explorées est écrite hors hypothèse.
- **Vérifié** sur 80 niveaux 8 x 8 aléatoires : solubilité identique à un parcours en largeur Python dans 80 cas sur 80 (63 résolus, 17 insolubles) ; les 63 chemins rendus sont valides ; 48 sont plus longs que le minimum (surplus moyen 9,3 pas) ; sur les 17 niveaux insolubles, le chemin est entièrement annulé (mémoire revenue à zéro) ; 12 188 instructions par niveau en moyenne, 78 581 au maximum.

### Jeu : sprites d'ennemis en ADN (`jeu/rendu.vtx`, `jeu/jeu.vtx`, `jeu/jeu_demo.py`, `jeu-demo.png`)

- **Contenu** : projection plane des murs (table des angles), tampon de profondeur par colonne, sprites 8 × 8 écrits en ADN (A transparent, C, G, T trois couleurs : 4 mots pour 64 pixels), projection signée des ennemis, ombrage par la distance.
- **Vérifié** : sur la pose de départ, deux ennemis visibles sont à la colonne attendue (64,0 contre 64,0 ; 104,7 contre 103,5) ; deux autres sont masqués par un pilier et par le bloc central, comme attendu. L'image est contrôlée à l'œil, pas contre un moteur de référence.
- **Coût** : 720 000 à 910 000 instructions par image (128 × 64), dont environ 16 000 pour quatre sprites.
- **Pas une accélération** : l'écriture ADN compacte et rend lisibles les données ; la vitesse viendra d'un lancer de rayons par grille (DDA) et d'un meilleur code compilé.

### Idée du son : notes superposées (`test_son.py`)

- Une note = une fréquence propre ; une valeur de 0 à 255 module son amplitude ; la composition est la somme ; on lit une note par corrélation. Notes orthogonales : 100 % de lectures à ±4 niveaux jusqu'à 1 024 notes sur 8 192 échantillons, même avec un convertisseur de 8 bits et 20 dB de bruit (gain de traitement de la fenêtre), facteur de crête 2,3 à 4 avec phases aléatoires.
- **Fragilité** : le défaut d'accord. À 64 notes et 12 bits, un désaccord de 0,02 période donne 91 à 95 %, de 0,1 période 25 à 36 %.
- **Limites** : capacité bornée par le produit durée × bande ; lecture d'une note = corrélation sur toute la fenêtre. C'est le multiplexage en longueur d'onde déjà prévu (huit lasers = huit notes), pas un gain gratuit.

### Optimisation du rendu, débogueur et arithmétique 64 bits (vtx 0.3)

- **Rendu** : lancer de rayons par grille (DDA) au lieu de la marche pas à pas, remplissage des colonnes par tables de plafond et de sol, ombrage des murs selon la face. 242 000 à 346 000 instructions par image de 128 × 64 contre 722 000 à 909 000 avant : environ 3 fois moins. Distances de mur comparées à un lancer de rayons en virgule flottante : erreur moyenne 3,5 unités de 1/256 de case, maximale 9,9 ; 83 colonnes sur 128 à moins de 4 unités. Les tables trigonométriques arrondies expliquent l'écart.
- **Sprites** : alphabet A, C, G = trois couleurs, T ou U = statut transparent. Un ennemi à l'état ARN (hypothèse) est dessiné en fantôme, un ADN (validé) est plein : la vue `mode 4` montre les positions validées et les déplacements hypothétiques avant validation. Le tour est découpé en trois phases (`hypotheses`, `resoudre`, `valider_tout`).
- **Débogueur** : `python3 vtx.py trace prog.vtx [entrées] [--de N] [--max N] [--arret ADRESSE] [--regs]` : une ligne par instruction (pas, adresse, mot, nom, opérandes), registres et drapeaux, arrêt avec état à une adresse.
- **64 bits et virgule fixe** (`bibliotheque/fixe.vtx`, `test_fixe.py`) : `mulhi`, `mul64`, `add64`, `sub64`, `fx_mul` (16.16 signé, arrondi vers le bas comme le décalage arithmétique de C) et `fx_div` (arrondie vers zéro, saturée). 669 paires dont les bords, 6 021 valeurs, 0 écart ; 846 instructions pour les neuf opérations. Le moteur de Doom d'origine utilisait cette virgule fixe 16.16, pas de flottants.
- **Priorités du langage** : flottants (bibliothèque logicielle binary32 d'abord), type 64 bits dans le compilateur (aujourd'hui par paires de mots), débogueur interactif (pas à pas, points d'arrêt sur lignes, lecture de la mémoire).

### Jeu : commandes configurables (`jeu/commandes.vtx`, `jeu/test_commandes.py`)

- Table touche -> action (avancer, reculer, pas de côté, tourner), remappage en cours de partie, déplacement en entiers signés avec collisions glissantes (le joueur est un carré de 80 unités de côté).
- **Vérifié** : 30 parties scriptées de 400 événements (touches et remappages), trajectoires identiques à la référence Python dans 30 cas sur 30 ; invariant « le joueur ne touche aucun mur » vérifié à chaque pas : 0 violation sur 12 000 positions ; 262 instructions par événement.

### Idée musicale clarifiée (à prototyper)

- Une note = une fréquence signature = une tâche ; un accord = des tâches en parallèle ; la mélodie = l'ordre ; la durée = la vitesse variable de la tâche ; la mesure = une barrière de synchronisation (modèle BSP) ; le silence = une attente.
- Une partition est un diagramme de Gantt (piano roll). Matériel : multiplexage en longueur d'onde ; la bande C (1 530 à 1 565 nm, soit 4,38 THz) compte environ 88 canaux à 50 GHz de pas. Les intervalles musicaux (octave = double fréquence) n'existent pas physiquement sur cette grille linéaire : les notes servent d'identifiants, pas d'harmonie. A4 multiplié par 2^40 donne environ 484 THz, soit 620 nm : une convention de correspondance, pas une physique.
- **Test à faire** : interpréteur de partitions en vtx, tâches de durées aléatoires, barrières aux mesures, vérification des contraintes d'ordre et du temps total.

### Jeu 2 : « Labyrinthe du cube » (`jeu2/`, `labyrinthe-du-cube.html`)

- **Niveau en valeurs du cube** (`generer_niveau.py`, `donnees_niveau.vtx`) : 16 mots ADN pour le terrain (A vide, C brique, G pierre, T porte A) ; objets en mots `#CCLLTTEE` (colonne, ligne, type, alpha ADN : T présent, U pris) : clés A et B, porte B, sortie, départs des ennemis et du joueur.
- **Monde** (`monde.vtx`) : chargement du niveau, collisions glissantes, clés, portes, sortie, commandes configurables. 220 parties scriptées de 70 touches identiques à la référence Python (220 sur 220) ; 1 713 instructions par touche.
- **Rendu** (`rendu2.vtx`) : 256 × 128, lancer de rayons par grille, murs texturés en ADN (16 × 16), sol et plafond par tables, sprites 16 × 16 triés par distance, ennemis interpolés entre deux tours. 1,2 à 1,7 million d'instructions par image ; 7,7 à 8,6 ms par image sur l'émulateur JS (Node), soit environ 60 images par seconde sur ordinateur (non mesuré sur téléphone).
- **Animation par le cube** (`animation.vtx`, `test_animation.py`, `animation-ennemi.png`) : six parties du corps en ADN, quatre poses clés par coordonnée rangées dans un seul mot (une voie par pose), interpolation par un GDOT contre un mot de poids, trois comportements (garde, marche, attaque). 192 sprites sur 192 identiques à la référence Python ; 13 043 instructions par sprite.
- **Comportement par la mémoire associative et courbe de gris** (`courbe-gris.png`) : l'état de l'ennemi (vitesse, proximité, alerte) est comparé aux trois clés par GDOT (367 instructions par décision). Précision 99,2 % à 30 niveaux de bruit, 88,7 % à 70. La confiance est bien calibrée : à 70 niveaux, 58 % de bonnes décisions sous 50 % de confiance contre 99,5 % au-dessus de 90 %. Le comportement proposé reste une hypothèse (ARN) et n'est inscrit dans l'ADN (voie bleue du mot) qu'au-delà de 60 % de confiance. Un ennemi en garde, loin du joueur, ne bouge pas.
- **Page** : émulateur JS à tableaux typés (`jeu2/vm_rapide.js`, étages 1 et 2 sur 65 536 mots), boucle à 60 pas par seconde pour les commandes, tour des ennemis toutes les 300 à 620 ms avec interpolation, visée à la souris, pavé tactile, mini-carte, état du joueur et des ennemis en mots hex. Images identiques entre Python et JS (5 sur 5) ; parties simulées : ennemis en garde tant que le joueur est loin, réveil et capture en 1,4 s à 3 cases, 4,0 s à 6 cases.
- **Limites** : pas de son ; le ressenti n'est pas testé par un humain ; textures en 4 couleurs ; pas de sol texturé ni d'éclairage dynamique ; vitesse sur téléphone non mesurée ; niveau unique.

### Idée : extension de la carte par fréquences (à prototyper)

- Chaque morceau de carte (16 × 16 cases, une tranche du cube) reçoit une fréquence signature ; « additionner les cubes » revient à les adresser côte à côte par leur fréquence, comme des bancs de mémoire sur des canaux de longueur d'onde. L'étage (quit A3) donne déjà quatre tranches ; les fréquences en ajouteraient autant que de canaux (environ 88 en bande C).
- Ce n'est pas une addition physique des valeurs (deux canaux qui se recouvrent se brouillent) : c'est un adressage. Test proposé : une carte de 2 × 2 morceaux reliés par des passages, chaque morceau chargé à la demande quand le joueur s'en approche, en comptant les instructions de chargement.

### Jeu 3 : monde étendu par signatures et points de vie (`jeu3/`)

- **Monde de 32 × 32** (`generer_monde.py`, `donnees_monde.vtx`, `monde3.vtx`) : quatre morceaux de 16 × 16 (des tranches du cube), chacun avec une signature de fréquence (do, mi, sol, la) rangée dans un mot à quatre voies. Le répertoire est rangé dans le désordre ; la partition dit quelle signature va à quelle place ; le chargeur retrouve chaque morceau par GDOT, comme la mémoire associative (69 174 instructions pour tout le monde). Morceaux à la bonne place : 100 % jusqu'à 30 niveaux de bruit sur la signature, 98 % à 60, 78 % à 90, 75 % à 120.
- **Points de vie** : 100 au départ ; un ennemi en attaque au contact retire 15 points, puis deux tours d'invulnérabilité ; trois trousses rendent 35 points. 702 tours avec ennemis : points de vie et invulnérabilité conformes au calcul Python 702 fois sur 702 ; aucun ennemi dans un mur ni superposé. 120 parties du joueur seul identiques au modèle Python.
- **Huit ennemis** (`ennemis32.vtx`) : parcours en largeur sur 1 024 cases, double brin, 161 000 instructions par tour.
- **Erreur trouvée par le test** : deux ennemis étaient posés dans des piliers ; le générateur vérifie maintenant que chaque objet est sur une case libre.
- **Équilibre** : un pilote automatique qui ignore les ennemis atteint la sortie avec des ennemis lents (48 s, 10 points de vie restants) et perd avec des ennemis moyens ; les ennemis lents sont le réglage par défaut.

### Traducteur du code machine vers JavaScript (`jeu3/vm_traduite.js`)

- Chaque bloc de base du code machine devient une fonction JavaScript compilée une fois (542 blocs, 4 393 instructions pour le jeu), les opérandes, les étages et les constantes `LDI` sont résolus à la traduction. Le nombre d'instructions est compté par bloc.
- **Vérifié** : mêmes images, même mémoire et même nombre d'instructions que Python et que l'émulateur instruction par instruction (6 états sur 6).
- **Vitesse** (Node) : 1,8 ms par image contre 6,1 ms, soit 3,4 fois plus vite ; environ 711 millions d'instructions SPU par seconde ; préparation 23 ms.
- **Hypothèse** : le code ne se modifie pas lui-même (vrai pour tout ce que produit le compilateur vtx).

### Feuille de route vers un vtx autonome et plus rapide

1. **Back-end natif** : traduire le code machine en WebAssembly, puis en code machine x86 ou ARM ; le port Rust peut en être la base. Objectif mesurable : le même programme vtx aussi rapide que la même logique écrite en C.
2. **Compilateur optimisant** : allocation de registres (aujourd'hui trois registres de travail et beaucoup de PUSH et POP), propagation des constantes, déroulage des petites boucles, mise en ligne des petites fonctions comme `voie`. Le jeu passe la majorité de son temps dans ces motifs.
3. **Auto-hébergement** : réécrire le compilateur vtx en vtx (analyseur, générateur, assembleur), puis le compiler avec lui-même ; c'est le critère classique d'un langage autonome. Prérequis : chaînes et tableaux d'octets, entrées et sorties de fichiers.
4. **Avantage propre** : vtx ne peut pas battre JavaScript ou Python sur leur propre machine ; il peut les battre là où le cube apporte quelque chose : `gdot` et `gemv` exécutés par un moteur matriciel (le jeu en fait déjà le cœur de l'animation, de la décision et du chargement), et la mémoire associative native.

### vtx 0.4 : flottants et 64 bits (vérifié)

- **Instructions du SPU** : FADD, FSUB, FMUL, FDIV, FEQ, FLT, FLE, FSQRT, ITOF, ITOFS, FTOI, FROUND (IEEE 754 binary32, arrondi au plus proche pair, NaN unique 0x7FC00000) ; ADC, SBC, MULHU pour les longs. Spécification passée en v0.5.
- **Langage** : littéraux `1.5`, `2e3`, `5L` ; annotations `soit x: flottant = 0;`, `fonction f(a: long): flottant` ; conversions implicites entier vers flottant et entier vers long, toutes les autres explicites (`flottant`, `flottant_signe`, `entier`, `arrondi`, `long`, `long_signe`, `long_de`, `bas`, `haut`, `bits`, `comme_flottant`, `racine`) ; `abs`, `min`, `max` pour les trois types ; division, reste et décalages des longs dans le prélude, compilés seulement s'ils servent ; `exp2` en flottant (erreur relative au plus 7,4 × 10⁻⁷, 130 instructions).
- **Vérifié** : code machine identique avant et après pour 342 programmes existants (réels, aléatoires, tests) ; 28 800 résultats flottants contre numpy float32, valeurs spéciales comprises (NaN, infinis, zéros signés, sous-normaux) : 0 écart ; 15 984 mots de 64 bits contre les entiers exacts de Python, bords compris : 0 écart ; 9 programmes typés sur 9 ; 7 erreurs de typage sur 7 avec message et ligne ; Java, JavaScript interprété et JavaScript traduit identiques à Python sur 19 programmes typés ; toute la non-régression tenue (52 tests, différentiel 1 000 programmes, priorités, budgets, bibliothèque, virgule fixe, puzzle, ennemis, commandes, niveau, animation).
- **Coût** : une opération sur deux longs coûte en moyenne environ 500 instructions (division bit à bit comprise) ; addition et soustraction 2 instructions plus le chargement.
- **Corpus de conformité** porté à 465 programmes (programmes typés, `exp2` et chargement du monde compris) : Python, Java, JavaScript interprété et JavaScript traduit identiques sur les 465 (sorties, nombre d'instructions, mémoire des étages 1 à 3).

### Jeu 3, version 3 (`jeu3/`)

- **Ennemis en huit directions** : parcours en largeur à huit voisins, diagonale permise seulement si les deux cases qui la bordent sont libres. Test du monde avec le réglage final : 830 tours, points de vie et invulnérabilité conformes au calcul Python 830 fois sur 830, 274 pas en diagonale, aucune violation (mur, superposition, coin coupé, saut de plus d'une case). Coût : environ 223 000 instructions par tour des ennemis.
- **Dégâts** : 10 points par ennemi en attaque sur l'une des huit cases voisines, trois tours d'invulnérabilité. Un pilote automatique qui ignore les ennemis atteint la sortie avec des ennemis lents (48 s, 50 points de vie au plus bas).
- **Confiance flottante** : la confiance du comportement proposé (l'hypothèse ARN) est calculée en flottant avec `exp2` ; seuil 0,6 ; affichée pour chaque ennemi.
- **Correction** : la mini-carte ne réservait que 16 × 16 pixels pour un monde de 32 × 32 cases, d'où l'affichage faux en haut à droite ; elle fait maintenant 32 × 32.

### Débogueur au niveau du source (`vtx.py deboguer`, `debogueur/`)

- **Fonctionnement** : le compilateur émet des directives (`.ligne`, `.fonction`, `.var`) que l'assembleur met de côté : le code machine ne change pas (342 programmes sur 342 identiques à l'octet). L'importation garde une carte des lignes : chaque arrêt et chaque erreur de compilation indique le bon fichier et la bonne ligne.
- **Commandes** : pas, suivant (par-dessus les appels, repéré par le pointeur de cadre R13), sortir, continuer, points d'arrêt par ligne et par fichier, valeurs typées (entier avec lecture signée, flottant, long de 64 bits), pile d'appels, mémoire, registres.
- **Vérifié** (`debogueur/test_debogueur.py`) : 16 vérifications sur 16 (séquence de pas à travers deux fichiers, pile, sortie de fonction, pas par-dessus, point d'arrêt dans une boucle d'un fichier importé avec les valeurs de i et du total à chaque tour, long de 64 bits, entier négatif, même nombre d'instructions qu'une exécution normale, session en ligne de commande). Sur le jeu complet (572 instructions source, 43 fonctions) : arrêt dans `blesser()` au moment où un ennemi touche le joueur, pile `blesser`, `tour_complet`, `principal`.
- **Limites** : « sortir » s'arrête à l'instruction suivante de l'appelant (le reste de la ligne d'appel est exécuté) ; pas de points d'arrêt conditionnels ni de surveillance d'une case mémoire.

### Idée : texture volumique dans le cube (à prototyper)

- Au lieu de déplier l'objet en UV, chaque point de l'objet prend la couleur du point correspondant d'un volume en 3D (texture volumique ou solide). Un étage adresse 2^24 mots, soit exactement 256 × 256 × 256 : un étage peut contenir un volume complet de 256³ couleurs `#RRGGBBAA`. Les quatre étages peuvent porter quatre attributs (couleur, normale, rugosité et métal, émission) pour un rendu PBR.
- Coût : 64 Mo par étage plein ; la finesse dépend du nombre de points (la mémoire), le 64 bits servant à adresser au-delà de 256³ et à garder des coordonnées précises.
- Sphère et cube : une texture d'environnement sphérique se range en cube (cubemap : la plus grande composante de la direction choisit la face) ; un point du cube normalisé donne un point de la sphère.

### Partition automatique des tâches (`vtx.py partition`, `partition/`)

- **Principe** : toute suite d'au moins deux appels de fonctions écrits comme instructions devient un accord. Le compilateur calcule les lectures et écritures de chaque appel (zones des tableaux, cases constantes, étage entier pour une adresse calculée, tous les étages pour un étage variable, entrées et sorties), fonctions appelées comprises (point fixe), puis range les tâches sans conflit dans une même mesure et donne à chaque fonction une note (la4 = 440 Hz pour la première, canal optique 193,70 THz). Rien n'est à écrire dans le programme.
- **Vérifié** (`partition/test_partition.py`) : démonstration à six tâches rangée en trois mesures comme attendu, mêmes sorties, même mémoire et même nombre d'instructions dans l'ordre écrit, l'ordre de la partition et cinq ordres mélangés dans chaque mesure ; 15 paires de tâches dirigées sur 15 bien placées (chaque sorte de conflit sépare, chaque absence de conflit réunit) ; 300 programmes aléatoires (150 à conflits nombreux, 150 à tâches souvent indépendantes avec 268 mesures à plusieurs tâches) identiques dans tous les ordres permis ; code machine des 343 programmes existants inchangé.
- **Temps** : sur la démonstration, 2 250 521 instructions de tâches en séquence contre 1 728 570 si chaque mesure joue ses tâches ensemble, soit un gain de 1,30 (le flou, à lui seul 1,45 million d'instructions, domine). Dans le jeu, les quatre accords trouvés sont tous en conflit (même tableau ou même zone) : aucun gain, ce qui est juste.
- **Limites** : analyse au niveau du tableau entier et de l'étage entier pour une adresse calculée, donc prudente ; seules les suites d'appels forment des tâches ; le temps joué ensemble est mesuré dans l'émulateur, sans coût de synchronisation entre mesures.

### Boucles en segments (vtx 0.4)

- **Syntaxe** : `pour i dans 0..TAILLE en segments { … }` découpe la boucle en 4 segments (un quit) ; `en 16 segments` de 2 à 64. Chaque segment devient une tâche de la partition.
- **Preuve d'indépendance** : écritures de tableau à la case de l'indice (`t[i + c]`, un seul décalage par tableau), aucune lecture du tableau écrit, aucune autre écriture lue par les autres ; sinon, segments joués l'un après l'autre. Un segment ne peut modifier aucune variable extérieure, ni sortir de la boucle (erreurs de compilation).
- **Démonstration** (`partition/orchestre_segments.vtx`) : la préparation de l'image et le flou écrits en segments ; mêmes sorties et même mémoire que la version sans segments ; 3,8 % d'instructions en plus (découpage) ; temps joué ensemble 658 141 instructions au lieu de 1 728 570 : gain de 3,55 au lieu de 1,30. L'histogramme (516 372 instructions) limite maintenant : il écrit à une case calculée (`histo[g]`) et ne se découpe pas en segments sans tableau par segment.
- **Mesure du temps** : un accord imbriqué (les segments du flou) raccourcit la tâche qui le contient (le flou dans l'accord principal).

### Tableaux cumulés et noms gaulois des segments (vtx 0.4)

- **Idée** (de l'utilisateur, par l'image des segments de piston) : nommer chaque segment, et découper aussi l'histogramme. Un histogramme écrit à une case calculée (`histo[g]`), donc ses segments se gênent ; la réponse est une copie du tableau par segment, additionnées à la fin.
- **Syntaxe** : `pour i dans 0..TAILLE en segments cumulant histo { … histo[g] = histo[g] + 1; }` ; plusieurs tableaux : `cumulant h, ps` ; champs de structure permis.
- **Sûreté** : le tableau cumulé ne s'écrit que sous la forme `T[x] = T[x] + v`, `v + T[x]` ou `T[x] - v` (même case, `v` sans lecture de `T`) ; toute autre lecture, adresse calculée ou fonction appelée qui l'atteint est une erreur de compilation. L'addition sur 32 bits ne dépend pas de l'ordre : le résultat est exactement celui de la boucle ordinaire. Ne marcherait pas avec des flottants (l'addition flottante dépend de l'ordre) : non permis pour l'instant, faute de type dans le tableau.
- **Mise en œuvre** : copies dans `@3[0xE00000..0xF00000]` (zone réservée, un tableau déclaré là est refusé) ; chaque segment remet sa copie à zéro puis travaille dessus ; après l'accord, une boucle ajoute les copies dans le tableau. La zone des copies compte comme lue et écrite par la tâche, pour la partition englobante.
- **Noms** : ordinaux gaulois du compte de La Graufesenque : *cintux, allos, tritios, petuarios, pinpetos, suexos, sextametos, oxtumetos, nametos, decametos* ; tâches nommées `histogramme·cintux`, etc. Seuls les noms des directives `.tache` changent : code machine identique pour tous les programmes existants.
- **Mesure** (`partition/orchestre_cumul.vtx`, l'histogramme en `segments cumulant histo`) : 2 422 666 instructions de tâches (+3,7 % : remise à zéro, adresses des copies, somme finale), 519 572 jouées ensemble ; gain **4,33** par rapport au programme d'origine joué en séquence (2 250 521 instructions) ; 3,42 avec les seuls segments, 1,30 sans segments (les 3,55 notés plus haut se rapportaient à la version en segments jouée en séquence). Chaque segment d'histogramme dure 153 893 instructions ; la limite est maintenant le flou (377 791 par segment).
- **Selon le nombre de segments et de canaux** (même programme, `en N segments` partout) : 4 segments → 4,33 ; 8 segments → 7,53 avec 8 canaux (4,33 avec 4 canaux) ; 16 segments → 11,93 sans limite de canaux, 7,53 avec 8 (gains rapportés au programme d'origine en séquence). Le gain suit le nombre de canaux du SPU : le découpage ne crée pas de travail parallèle au-delà de ce que la machine peut jouer. Coût du découpage : +4,7 % d'instructions à 16 segments.

### Émulateur en Rust (`vtx-rs/`)

- **Contenu** : `src/main.rs`, sans aucune bibliothèque externe (se compile sans accès à crates.io). Même sémantique que Python, Java et JavaScript, flottants et instructions 64 bits compris. Commandes `corpus` (rejoue le corpus de conformité) et `session` (appels successifs partageant la mémoire, chronométrés).
- **Vérifié** : 465 programmes du corpus de conformité, sorties, nombre d'instructions et mémoire identiques à Python (0 écart), y compris dans un dossier neuf par `verifier.py`.
- **Vitesse** (même ordinateur, une image du jeu de 1 372 871 instructions) : Rust interprète 3,6 ms (378 millions d'instructions par seconde) ; JavaScript interprète 6,4 ms (213 millions) ; JavaScript traduit 2,0 ms (675 millions). L'interprète Rust est 1,8 fois plus rapide que l'interprète JavaScript, mais plus lent que la traduction JavaScript, qui compile chaque bloc une fois.
- **Suite** : traducteur vers le code machine de l'ordinateur avec Cranelift (bibliothèque Rust, à compiler chez l'utilisateur : le registre crates.io est inaccessible depuis l'environnement de Claude), puis cible WebAssembly pour la page du jeu.

### Moteur V6 : 6 cylindres, 18 segments au plus (vtx 0.4)

- **Décision** (de l'utilisateur, par l'image du V6 essence à 3 segments par piston) : le SPU a 6 canaux, appelés cylindres ; une boucle se découpe en 6, 12 ou 18 segments (6 × 1, 2 ou 3 temps). `en segments` vaut 6 ; `en N segments` (2 ≤ N ≤ 18) est arrondi au multiple de 6 supérieur.
- **Pourquoi des multiples de 6** (mesuré sur `orchestre_cumul.vtx`, gains rapportés au programme d'origine en séquence) : sur 6 cylindres, 6 segments → 6,04 ; 16 segments → 5,50 (3 tours dont le dernier laisse 2 cylindres à vide) ; 18 segments → 6,04. Sur 8 canaux, 18 segments ne donnent aussi que 6,04 (8 + 8 + 2). Le gain plafonne au nombre de cylindres ; plus de segments ne sert qu'à équilibrer des segments inégaux.
- **Noms** : jusqu'à 6, le cylindre (`flou·tritios`) ; au-delà, cylindre·temps (`flou·tritios·allos`).
- **Jeu, une image** (`jeu3/image_mesure.vtx`) : 1 372 807 instructions par image, dont `rendre3` 1 251 872 (91 %) et `dessiner_sprites` 120 935. Gain actuel : **aucun**. Les sprites lisent l'image que le rendu écrit, donc les deux restent en séquence ; et la boucle des colonnes ne peut pas encore se découper, car `colonne` est une fonction appelée qui écrit `cadre` à une adresse calculée (`q = x + y·W`) et partage le tableau `pals`. Plafond si les 256 colonnes étaient prouvées indépendantes sur 6 cylindres : 1 251 872 / 6 + 120 935 ≈ 329 600 instructions, soit environ ×4,2 par image (calcul, pas mesure).
- **Rappel** : ces gains sont comptés en instructions sur un SPU à 6 cylindres. Les émulateurs actuels (Python, Java, JavaScript, Rust) jouent toujours une instruction après l'autre ; pour voir le gain sur un PC, il faut un émulateur qui joue chaque cylindre sur un cœur du processeur (fils d'exécution en Rust).

### Correction : les cylindres sont partagés entre les niveaux (simulation refaite)

- **Erreur trouvée** (en mesurant sur 2 cœurs : gain 2,34, impossible) : l'ancien calcul donnait à chaque accord imbriqué ses propres canaux. Les 6 segments de l'histogramme et les 6 du flou, joués dans la même mesure, comptaient donc sur 12 canaux alors qu'on en annonçait 6. Les gains « sans limite » étaient justes ; les gains « sur N canaux » étaient trop beaux.
- **Nouveau calcul** (`simuler_accord`) : un seul jeu de N cylindres pour tous les niveaux ; une tâche prête prend un cylindre libre, la plus longue d'abord ; une tâche qui ouvre un accord imbriqué rend son cylindre et attend. Vérifié : sur 1 cylindre, durée = séquence ; jamais moins que séquence / N ; plus de cylindres n'est jamais plus lent.
- **Chiffres corrigés** (`orchestre_cumul.vtx`, gains rapportés au programme d'origine en séquence, 2 250 521 instructions) :

| segments | 1 cœur | 2 | 4 | 6 | 8 | sans limite |
|---|---|---|---|---|---|---|
| 6 | 0,92 | 1,78 | 3,11 | 4,72 | 5,23 | 6,04 |
| 12 | 0,92 | 1,77 | 3,33 | 4,71 | 5,58 | 9,97 |
| 18 | 0,91 | 1,77 | 3,24 | 4,70 | 5,70 | 12,75 |

- Les « ×6,04 sur 6 cylindres » et « ×4,33 sur 4 canaux » notés plus haut étaient faux : c'est ×4,72 sur 6 cœurs et ×3,11 à 3,33 sur 4. La règle « multiple de 6 pour qu'aucun cylindre ne tourne à vide » ne tient plus aussi bien : comme l'histogramme et le flou se partagent les cylindres, les tours incomplets se comblent. Sur 4 cœurs, 12 segments font le mieux ; sur 8, 18.
- **Adaptation à la machine** : le nombre de segments est fixé à la compilation, le nombre de cylindres est celui des cœurs de la machine hôte (`cylindres_machine()`), ou `--cylindres N`. Sur 1 cœur, le découpage coûte 8 % (0,92) : rien à gagner, un peu à perdre.
- **Décision** (validée par l'utilisateur) : `en segments` vaut désormais 12 (au plus 18, arrondi au multiple de 6).
- **Réserve de cœurs** (idée de l'utilisateur) : par défaut, un cœur est laissé au système ; `--laisser N`. Sur 4 cœurs, 3 cylindres donnent 2,81 au lieu de 3,63 : c'est le prix de la fluidité du reste de la machine.

### Ombre binaire du cube (`ombre/`)

- **Idée** (de l'utilisateur) : un cube « rustique » à valeur binaire, ombre du cube chromatique. Mise en œuvre : 1 bit par voxel, 1 si la voie alpha (densité) atteint le seuil 128 ; 32 voxels par mot, donc 1/32 du volume. Une ombre grossière ajoute 1 bit par bloc de 8×8×8.
- **Démonstration** (`ombre/ombre.vtx`) : volume N³ dans l'étage 1 (une montagne enneigée sur un sol de neige, une sphère rouge), ombres calculées en segments, une image N×N avec un rayon par pixel. Trois modes : lire le volume à chaque pas, lire l'ombre fine, sauter d'un coup les blocs vides de l'ombre grossière. Le saut est exact : on calcule le nombre de pas jusqu'à la sortie du bloc sur chaque axe.
- **Vérifié** (`ombre/test_ombre.py`, référence numpy indépendante) : 32³ sur l'émulateur Python, ombre, ombre grossière et image identiques pixel par pixel dans les trois modes ; 60 scènes aléatoires (alphas 0, 1, 127, 128, 129, 255) identiques ; 64³, 128³ et 256³ sur la machine Rust, sommes de contrôle identiques à la référence.
- **Mesures du rendu** (instructions par image) :

| volume | lire le volume | ombre fine | ombre grossière | gain |
|---|---|---|---|---|
| 64³ (image 64×64) | 18 898 449 | 19 728 018 | 14 933 579 | 1,27 |
| 128³ (128×128) | 149 968 181 | 156 736 450 | 105 513 317 | 1,42 |
| 256³ (256×256) | 1 191 568 052 | 1 245 991 986 | 799 797 479 | 1,49 |

- **Ce que ça apprend.** (1) L'ombre fine ne fait pas gagner d'instructions : lire un bit coûte plus cher que lire le mot. Son intérêt est la place (32 fois moins), donc le cache et la bande passante d'une vraie machine, que l'émulateur ne compte pas. (2) Le saut des blocs vides gagne, et de plus en plus avec la taille. (3) Surtout, une image 256×256 tracée dans un volume 256³ coûte environ 800 millions d'instructions, soit 3,8 s sur la machine Rust (406 millions par seconde). C'est 36 fois le budget d'une image à 30 images par seconde. Pour l'arène au dragon, un volume complet tracé pas à pas est donc exclu tel quel. Pistes : une montagne en carte de hauteurs (un parcours en 2D par colonne, beaucoup moins cher), un dragon en voxels dans un petit volume seulement, des niveaux d'ombre plus grossiers (blocs de 32), et un parcours voxel par voxel exact au lieu de pas fixes.
- **Machine Rust** : nouvelle commande `vtx-spu lancer FICHIER [MAX_PAS]` (programme « mots;entrées », affiche les instructions, la durée et les sorties).

### Compression du cube par blocs et palettes, à la manière ADN / ARN (`compression/`)

- **Principe** : le volume est découpé en blocs de 8×8×8 = 512 voxels ; chaque bloc prend la forme la plus courte. Vide : 0 mot. Uniforme : 1 mot. Au plus 4 couleurs : palette de 4 mots et **1 quit par voxel** (36 mots). Au plus 16 couleurs : palette et 4 bits par voxel (80 mots). Sinon brut (512 mots). Un répertoire donne un mot par bloc : forme et position.
- **ADN / ARN** (piste de l'utilisateur : T en transition vers U) : la forme comprimée est l'ADN, rangée et passive ; transcrire un bloc (T devient U), c'est le recopier en clair dans une zone de travail, l'ARN, la seule qu'on traite. On peut aussi lire un voxel directement dans l'ADN, sans transcrire le bloc (`lire_adn`), ce qu'un format comme zip ne permet pas.
- **Vérifié** (`compression/test_compression.py`, référence Python indépendante) : 32³ sur l'émulateur Python, 8 scènes aléatoires couvrant les cinq formes, puis 64³, 128³ et 256³ sur la machine Rust ; répertoire et données identiques à la référence, et chaque bloc transcrit redonne exactement le volume.
- **Taux** sur le volume de démonstration : 32³ → 10,3 ; 64³ → 22,9 ; 128³ → 26,5 ; **256³ → 35,5** (473 220 mots au lieu de 16 777 216 : le volume tient dans 3 % d'un étage). Aucun bloc brut : la montagne n'a que quelques couleurs par bloc.
- **Limites** : la scène est synthétique, avec peu de couleurs ; une vraie texture (photo, bruit fin) aurait beaucoup de blocs bruts et un taux bien plus faible. Pas encore mesuré : le coût d'une lecture directe dans l'ADN comparé à une lecture en clair.

### Logique à quatre valeurs (`logique/`)

- **Origine** : idée de l'utilisateur (vrai, faux, variable, et l'antimatière ; un essai précédent en Rust avait tourné à l'enfer). Forme retenue : la logique de Belnap (1977), avec deux bits de preuve par valeur, v et f, rangés dans un quit. Inconnu = aucune preuve, en dehors du spectre vrai / faux ; variable = preuves dans les deux sens, le bruit. L'antimatière devient l'opération `anti`, qui échange inconnu et variable ; superposés, le cube et l'anti-cube échangent les triangles rouge-vert-bleu et cyan-magenta-jaune (`figures/cube-anticube-logique.png`).
- **Pourquoi c'est simple ici et pas en Rust** : avec deux bits de preuve, toutes les opérations sont des ET / OU / échanges de bits, sans table de 16 cas. Et la même instruction traite 16 logiques rangés dans un mot.
- **Langage** : type `logique`, valeurs `inconnu`, `faux`, `vrai`, `variable`, opérations `et4`, `ou4`, `non4`, `anti`, `fusion`, `consensus`, conversions, instruction `selon`. `vrai` et `faux` gardent leur sens d'entiers 1 et 0 (aucun programme existant ne change : code machine identique pour les 78 programmes et tests), et deviennent des logiques là où un logique est attendu. Un logique ne sert jamais de condition directe.
- **Vérifié** (`logique/test_logique.py`) : tables complètes contre la définition, 28 800 opérations sur des mots de 16 logiques, `selon`, double sens de vrai / faux, 11 erreurs refusées.
- **Démonstration** (`logique/capteurs.vtx`) : 4 096 portes vues par deux capteurs bruités. Résultat : vrai 1 636, faux 1 647, inconnu 62, variable 751, identique à la référence par trois méthodes. Instructions : booléens à l'ancienne 162 803 ; un logique par porte 146 447 ; **16 portes par mot 58 398, soit ×2,79**. La fusion elle-même ne coûte qu'un `OR` pour 16 portes ; l'essentiel du reste est le comptage des bits. Une instruction de comptage de bits dans le SPU augmenterait nettement le gain (à mesurer).

### Instructions QEGAL et COMPTE, tableaux de quits, génomique (`genomique/`)

- **SPU** : deux instructions nouvelles. `QEGAL` (0x4F) compare les 16 quits de deux mots et met 1 dans le bit bas de chaque quit égal ; `COMPTE` (0x50) compte les bits à 1. `nb_bits(qegal(a, b))` donne le nombre de quits égaux en 2 instructions. Ajoutées aux machines Python, Rust et JavaScript (interprète et traduction) ; corpus de conformité porté à 468 programmes (310 paires de mots, dont les bords, contrôlées contre une référence indépendante, plus les capteurs en deux modes) : 0 écart sur les quatre machines.
- **Machine Java retirée** (décision de l'utilisateur, qui se concentre sur Rust) : Rust la remplace ; les machines JavaScript restent pour le jeu dans le navigateur.
- **Langage** : `qegal()`, `nb_bits()` (et non `compte()`, nom trop courant que des programmes utilisent déjà pour leurs fonctions) ; tableaux `de quits` et `de logique`, rangés 16 par mot. Lecture et écriture d'un élément traduites par le compilateur ; un second tableau ordinaire au même endroit donne la vue mot par mot (les deux regards sur la même case : l'élément et les 16 quits d'un coup).
- **Démonstration** (`genomique/motif.vtx`) : chercher un motif de 16 bases dans un génome de 16 384 bases avec au plus 2 différences. 13 positions trouvées, identiques à la référence dans les quatre modes. Instructions : une base par mot 6 171 790 ; tableau de quits lu base par base 14 290 814 (×0,43 : ranger coûte cher si on lit élément par élément) ; 16 bases d'un coup en calcul de bits 1 848 818 (×3,34) ; **avec QEGAL et COMPTE 1 013 999 (×6,09)**, et 16 fois moins de mémoire.
- **Leçon** : le quaternaire paie quand on traite les 16 quits ensemble, pas quand on les range seulement. Prochaine étape : que le compilateur réécrive seul une boucle élément par élément en boucle de 16 d'un coup (réécriture prouvée, comme les segments).

### Réécriture automatique en 16 éléments d'un coup (`vectorise/`)

- **Idée** (de l'utilisateur : « une case où tout s'affiche en même temps, 16 quits à la fois », et une « compilation en amont ») : le programmeur écrit élément par élément, le compilateur réécrit la boucle pour traiter un mot, donc 16 éléments, par tour.
- **Mise en œuvre** : les accès aux tableaux rangés restent sous forme haute pendant la lecture d'une fonction ; une passe (`vectoriser`) reconnaît les boucles `pour i dans a..b { T[i] = … }` dont chaque valeur ne lit que des éléments d'indice `i` par des opérations quit par quit, puis une passe (`abaisser`) traduit tout en mots. Les bornes sont calculées une fois ; le début et la fin qui ne remplissent pas un mot sont traités élément par élément (boucles vides comprises). Toute autre boucle reste inchangée.
- **Vérifié** (`vectorise/test_vectorise.py`) : 400 programmes aléatoires (logiques et quits, bornes constantes ou lues à l'exécution, opérations interdites et indices décalés mêlés pour vérifier qu'ils ne sont pas réécrits) : sorties et mémoire identiques avec et sans réécriture 400/400 ; 244 programmes réécrits. Code machine inchangé pour les 81 programmes et tests existants.
- **Mesures** : fusion de 4 096 témoignages : tableau ordinaire 118 790 instructions, tableau rangé lu élément par élément 434 182, **réécrit 7 735 (×15,4 sur le tableau ordinaire)**. Comparaison de 16 384 bases : 454 656, 1 671 174, **30 775 (×14,8)**. Le plafond théorique est ×16.
- **Boucles qui comptent et qui somment** (ajout) : `si E1 == E2 { n = n + 1; }` (ou `!=`) devient `n = n + nb_bits(qegal(…))` par mot, `n = n + E` devient la somme des 16 quits (bits bas + 2 × bits hauts). Condition trouvée par le test aléatoire : la valeur d'un élément doit tenir dans son quit (`cmp3` et `qegal` remplissent les 15 autres quits du mot, ce qui fausse une somme ou une comparaison faite élément par élément). 400 programmes aléatoires identiques avec et sans réécriture. Compter les bases égales sur 16 384 : 327 710 instructions → 30 775 (×10,6).
- **Pas encore** : les indices décalés (`T[i + 1]`) ne sont pas réécrits ; la génomique (fenêtre glissante) demande encore le mot à mot écrit à la main.

### Feu de camp : ombre quaternaire et PBR (`feu/`)

- **Demande** : simuler un feu de camp réaliste, le modéliser en vtx et en faire le rendu PBR en vtx ; chaque voxel analysé, ombre quaternaire 0 vide, 1 brume (flammes, fumée), 2 plein (PBR complet et arrêt du rayon), 3 inconnu (pas encore analysé) ; le rayon traverse l'objet sans confondre les faces. (La recherche d'image de référence n'a rien rendu : scène construite d'après la forme habituelle d'un feu de camp.)
- **Scène** (`scene.vtx`, 128³ dans l'étage 1) : voxel `#MMVVCCAA` (matière, variation, chaleur, densité). Sol de neige et cendre, 11 pierres (ellipsoïdes à bord irrégulier), 5 bûches en tipi (cylindres en arithmétique entière ; bas carbonisé avec braises), lit de braises, marmite en fonte creuse, flammes (brume émissive, chaleur décroissante avec la hauteur, langues par bruit), fumée (brume qui dérive et s'élargit). Identique à une référence Python indépendante (197 245 voxels non vides).
- **Ombre quaternaire** (`rendu.vtx`) : un quit par voxel dans un tableau `de quits`, tout à 3 (inconnu) au départ. Un voxel n'est analysé que quand un rayon l'atteint : état selon la densité (deux seuils), et pour un plein ses 6 faces (lesquelles touchent du non plein) et sa normale (gradient sur les 26 voisins), rangées dans @3[v]. Image complète : **86 278 voxels analysés sur 2 097 152 (4 %)**, 1 097 millions d'instructions au lieu de 1 393 millions si tout est analysé d'avance, image identique.
- **Rayon** : parcours exact voxel par voxel (Amanatides et Woo), en flottants ; il connaît toujours sa face d'entrée. Brume : la flamme émet selon sa chaleur, la fumée absorbe et diffuse la lumière du feu ; le rayon continue. Plein : PBR (Cook-Torrance : distribution GGX, géométrie de Smith-Schlick, Fresnel de Schlick ; albédo, rugosité, métal ; braises émissives), deux lumières (le feu, avec ombres portées par un second parcours, et la lune), ambiance de nuit, puis arrêt. Une normale qui tournerait le dos au rayon est remplacée par celle de la face d'entrée : vérifié, 0 cas sur l'image entière.
- **Vérifié** (`feu/test_feu.py`) : scène identique à la référence ; voxel touché et face d'entrée identiques à une référence en flottants 32 bits pour tous les pixels qui touchent un voxel plein (53/53 en rapide, sur 400 pixels en complet) ; analyse à la demande = analyse complète.
- **Coût** : environ 1,1 milliard d'instructions par image 256 × 256, soit 2,9 s sur la machine Rust : une image fixe, pas encore du temps réel. Rendu encore en blocs (voxels de 128³, un rayon par pixel).
- **Suites possibles** : plusieurs rayons par pixel (bords lissés), flammes animées, volume 256³, saut des blocs vides par l'ombre quaternaire (16 voxels testés d'un coup avec `qegal`), et jouer les rayons sur les cœurs avec le multicœur Rust.

### Feu animé par la mémoire du cube, comme Pégase (`feu/anime.vtx`)

- **Demande** : modélisation et animation par le cube ; flammes animées, luminosité variable. (Précision donnée à l'utilisateur : aucun logiciel de modélisation 3D n'est utilisé ; la scène est écrite en équations dans vtx, le PBR aussi. **Coatvtx** est le nom retenu pour le futur programme vtx de modélisation, de matériaux et d'animation.)
- **Principe repris de Pégase** : 6 souvenirs de feu (calme, vif, rafale à gauche, rafale à droite, braises, flambée). Clé = mot du cube #RRGGBBAA (chaleur, vent, hauteur, agitation) ; deux mots de valeurs, quatre paramètres par mot (hauteur des flammes, rayon, penchant, vitesse de montée des langues ; puissance de la lumière, teinte, seuil des langues, balancement). À chaque image, une requête qui évolue avec le temps (chaleur et hauteur qui respirent, vent qui tourne lentement, agitation qui crépite) est comparée aux clés par la distance du cube ; poids 65536 / 2^(écart >> 11), un softmax en base 2 ; paramètres = moyenne pondérée voie par voie.
- **Image par image** : les flammes et la fumée sont effacées puis refaites avec ces paramètres ; les langues et la fumée montent (le bruit est lu plus bas à chaque image) ; la flamme se courbe dans le vent (penchant proportionnel au carré de la hauteur) ; la lumière du feu change de puissance et de teinte ; l'ombre quaternaire repart de « inconnu ».
- **Corrections en cours de route** : un souvenir avait un penchant de 2 au lieu de 128 (erreur de saisie hexadécimale), ce qui couchait la flamme d'un coup ; le rappel trop vif (écart >> 10) sautait d'un souvenir à l'autre, adouci à >> 11 ; le penchant linéaire donnait une lame droite, remplacé par une courbe ; la fumée pouvait sortir du volume par grand vent, son penchant est réduit.
- **Vérifié** : pour chaque image, les 8 paramètres et le volume complet sont identiques à une référence Python indépendante (6 images sur 6 à la mise au point, 3 ou 8 dans le test).
- **Résultat** : `feu/feu-anime.gif`, 24 images 256 × 256, 26,5 milliards d'instructions, 70 s sur la machine Rust (environ 3 s par image).
- **Suite décidée** : l'autonomie avec Rust (avant Coatvtx), sans hésiter à utiliser la logique à quatre valeurs.

### vtx 0.5, étape 1 : texte, tas, références, canaux (vers l'autonomie)

- **Décision** (de l'utilisateur) : autonomie totale, vtx se compile lui-même et reste un langage spécifique. Plan dans `vtx-0-5-autonomie.md`. Ordre ajusté (proposé, pour ne pas écrire le compilateur deux fois) : la machine Rust ne fait que la machine ; le compilateur écrit en vtx, embarqué dans `vtx.exe`, remplacera `vtx.py`.
- **Langage** : caractères `'é'`, textes `"…"` (longueur puis un caractère par mot, rangés après le code), `nul`, références à des structures (variables, paramètres, retours et champs typés ; `a.b.c = x`), tas dans l'étage 3 (`nouveau`, `nouveau_de`, `tas_marque`, `tas_retour`), fonctions de texte au prélude. Une référence est une adresse globale : l'étage dans les bits 24 et 25, ce qui permet de lire un texte rangé avec le code (étage 0) comme un bloc du tas (étage 3).
- **SPU** : trois instructions, ENTC (0x51), SORC (0x52), SYS (0x53) : canaux 0 (nombres), 1 (console en texte), 2 et suivants (fichiers, ouverts par la machine hôte). Ajoutées à Python et Rust (fichiers compris), et aux deux machines JavaScript (console seulement). Corpus porté à 470 programmes, dont un arbre binaire sur le tas et une liste de textes écrite sur la console : 0 écart sur les quatre machines. Le format du corpus ajoute « |T: » suivi du texte de la console quand il y en a.
- **Vérifié** : 67 tests du langage (dont 4 erreurs nouvelles sur les références) ; code machine inchangé pour les programmes existants (seules les fonctions nouvelles du prélude sont ajoutées, à la fin, pour ne pas décaler les lignes du débogueur).
- **Prochaine étape** : le multicœur de la machine Rust, puis le compilateur écrit en vtx (noyau d'abord).
- **Allègement** (remarque de l'utilisateur : « c'est lourd ») : construction directe `Noeud { valeur: 7, gauche: Noeud { valeur: 2 } }`, type déduit (`soit n = …` sans annotation), champs non nommés à `nul` (un bloc neuf est déjà à zéro, `n.gauche = nul` était inutile).
- **Noyau immuable** (décision de l'utilisateur) : le mot du cube et ses quits, la logique à quatre valeurs, les segments et la partition ne seront jamais retirés ; inscrit en tête de `vtx-0-5-autonomie.md`.

### Machine Rust multicœur (vrais cœurs, `multicoeur/`)

- **Principe** : le compilateur exporte, avec les mots, la table des accords (`vtx.py exporter prog.vtx [entrées]` : « mots;entrées;table »), c'est-à-dire pour chaque accord l'adresse où il commence et celle où il finit, et pour chaque mesure l'adresse de début et de fin de chaque tâche. Quand la machine Rust arrive au début d'un accord, elle joue ses mesures l'une après l'autre ; les tâches d'une mesure partent sur des fils d'exécution (les cylindres), qui se partagent la mémoire. Chaque fil a ses registres et sa propre pile (copie du cadre courant : variables locales et arguments, dans une zone de l'étage 0 à partir de 0x400000). C'est sûr parce que le compilateur a prouvé que les tâches d'une mesure n'écrivent pas les mêmes cases ; les sorties sont remises dans l'ordre des tâches.
- **Cylindres** : par défaut les cœurs de la machine moins un (laissé au système), ou `vtx-spu lancer FICHIER MAX_PAS CYLINDRES`.
- **Piège corrigé** : la première tâche d'un accord commence à l'adresse de l'accord (et une boucle de la tâche peut y revenir) ; la machine relançait l'accord à l'infini (dépassement de pile). La marque de l'accord en cours est maintenant ignorée.
- **Vérifié** (`multicoeur/test_multicoeur.py`) : programmes aléatoires en segments et cumulants, sorties (dont une somme de contrôle de chaque étage) identiques à l'émulateur Python sur 1, 2 et 3 cylindres ; orchestre et ombre identiques. Corpus : 470 programmes, 0 écart (le corpus reste joué en séquence). Vitesse en séquence inchangée (environ 390 millions d'instructions par seconde).
- **Mesure réelle** (2 cœurs dans l'environnement de travail) : rendu de l'ombre 256³ en entier, 5,50 s sur 1 cylindre, **3,33 s sur 2 (×1,65)** ; avec l'ombre précalculée, 4,27 s → 2,77 s (×1,54). Le gain n'atteint pas 2 : la génération du volume et une partie du travail restent en séquence. Sur 4 cœurs (3 cylindres par défaut), le gain devrait monter vers ×2,3 à ×2,6 : c'est une estimation à mesurer.
- **Limite** : le feu de camp n'en profite pas encore, car son analyse « à la demande » écrit l'ombre quaternaire pendant le rendu ; le compilateur ne peut donc pas prouver les pixels indépendants. À reprendre avec la logique à quatre valeurs (une écriture qui ne fait que passer de « inconnu » à une valeur sûre).

### vtx 0.5i : la forge (vtx en code natif) et le labyrinthe tout en vtx

- **Décision** (de l'utilisateur) : « Il faut du natif, Vercintorix mérite d'être natif. » Trois voies proposées (vtx → Rust pour la vitesse, générateur x86-64 propre pour l'autonomie, les deux) : choisie, **la vitesse d'abord** (vtx → Rust, optimisé par rustc).
- **Constat d'abord** : traduire les mots du SPU (`vtx traduire`) bute sur la convention du SPU (variables dans le cadre, arguments empilés), que LLVM ne peut pas défaire ; une traduction fonction par fonction des mots a été essayée et retirée (plus lente).
- **La forge** (`forge/forge.py`, prototype en Python) part de l'arbre typé de vtx.py : une fonction Rust par fonction vtx, une variable Rust par variable. Le sens exact du SPU est gardé opération par opération. La machine autour est faite des fichiers de vtx-rs eux-mêmes, sortis pour cela de main.rs et gobatix.rs : `memoire.rs` (étages, cubes, cubes sur disque), `sortie.rs` (les sorties de Gobatix), avec `miroir.rs`, `gif.rs`, `hote.rs`.
- **Ramasse-miettes** : une fonction qui peut ramasser (de près ou de loin) a un cadre dans la pile du SPU, où ses variables et les valeurs en cours sont recopiées avant chaque appel qui peut ramasser ; les autres n'ont rien. Le ramasse-miettes étant conservateur, la taille du tas après une purge peut différer de quelques blocs (pile différente) ; les valeurs, non.
- **Flottants purs** : une variable flottante dont les bits ne sont jamais regardés vit comme flottant de la machine (pas de NaN unique à chaque opération). Une erreur de l'analyse (les tâches d'un accord n'étaient pas parcourues) a été attrapée par le garde-fou de la forge, qui refuse plutôt que de se tromper.
- **Vérifié** : 3 267 programmes (exemples, programmes des tests de types avec leurs entrées, programmes au hasard) : sorties, texte et mémoire identiques au SPU émulé. Gobatix : peindre, cube_tournant, cube_chromatique et le labyrinthe, même GIF octet pour octet.
- **Mesures** : de 0,4 à 2 fois le temps du C (adn 2,3 fois plus rapide que le C écrit naturellement) ; le labyrinthe : 13,3 ms par image émulé, 0,45 traduit, 0,15 forgé (`docs/vtx-forge.md`).
- **Le labyrinthe tout en vtx** (`jeu3/labyrinthe.vtx`) : boucle, clavier, souris, horloge, tableau de bord ; l'image vit dans un cube à elle (l'étage 1 s'accorde sur le cube 12 le temps de peindre et présenter).
- **Horloge des images** : sous `--gif`, `--images` ou `--scenario`, `horloge()` compte le temps des images présentées : une partie se rejoue à l'identique sur toutes les machines.
- **Suite** : porter la forge dans vtxc (même texte Rust que forge.py), pour que `vtx forger` n'ait besoin que de rustc ; puis le SPU-64 ; le générateur x86-64 propre viendra après, comparé à la forge.

### Le chemin, le point de matière et la triangulation (25 octobre, réflexion en cours)

**Décisions et propositions de l'utilisateur**
- **Le 128 bits devient le standard moyen**, le 64 la configuration minimale ; le 32 est gelé, gardé pour la rétro-ingénierie des programmes écrits dans d'autres langages (avec son corpus de conformité). Les méthodes du 64 s'inscrivent dans le 128. Noms à fixer : par bits par voie (8, 16, 32, 64), ou 4×8, 4×16, 4×32, 4×64 (proposé par Claude, pour ne pas confondre avec les noms actuels).
- **L'écriture hex est gardée** : elle ne coûte rien à la machine (le compilateur la lit une fois ; seuls les bits sont rangés). Le chemin reste intact.
- **Fini le RGB(A), place au cumul des couleurs avec la matière** : le mot n'est plus seulement une couleur, c'est un *point de matière* : la couleur cumulée (le cube RGB, ce que la matière absorbe et renvoie), et la profondeur, la transparence, le reflet, la luminosité (l'émission)… On ne comprime plus : on étend le mot avec ce que le programme irait chercher ailleurs, et on accélère (une seule lecture, quatre voies calculées ensemble dans un registre vectoriel de 128 bits).
- **Respecter le chemin dans tout le fonctionnement** : les adresses, l'intégration des données, tout passe par le cube d'abord ; l'ADN vient après.

**Le chemin, pour toute chose** (à compléter et corriger)

| Étape | Ce que c'est | Exemples |
|---|---|---|
| Cube | tout est un point : une **place** (l'adresse, ses coordonnées dans le cube) et un **contenu** (couleur et matière) ; un compteur est un pas le long d'un axe | `#RRGGBB` d'une adresse ; un pixel ; une valeur |
| Hex | l'écriture exacte du point, pour l'humain ; aucun coût à l'exécution | `#A000C90F_…` |
| ADN | la forme rangée et transmise, ce qui dure : le programme compilé (les mots), les cubes sur disque avec leur anti-cube et leur ombre | `cube-1-42.cub`, les mots du SPU |
| ARN | la copie transcrite pour agir, ce qui s'exécute : la forge transcrit l'ADN du programme en ARN natif | le programme forgé |
| Programme | ce qui agit ; ses résultats redeviennent des points du cube (chemin inverse) | sorties, images, cubes écrits |

**Proposition pour le point de matière en 4×32** (Claude, à discuter) : trois voies de 32 bits pour la couleur (le cube chromatique, avec la précision du HDR) ; la quatrième voie, la matière, en quatre quarts de 8 bits (transparence, profondeur de transparence, reflet, rugosité ; la luminosité pour le feu reste à placer). Base physique : la lumière qui touche une matière est absorbée, transmise ou réfléchie, et les trois parts font toujours le tout (conservation de l'énergie) ; la profondeur de transparence est la distance où la lumière s'éteint dans la matière (Beer-Lambert).

**La triangulation** (idée de l'utilisateur) : un reflet, une illumination, et l'ombre en dessous référencent chaque colonne du cube sous trois angles : une triangulation. De quoi fiabiliser la recherche d'un hex, et traiter tout ce sur quoi on s'est cassé la tête : l'ordre, la perte, l'erreur. Avec l'alignement du code entre ces repères.
- Ce qui existe déjà : l'ombre (une projection : neuf ou exclusifs par colonne, localise et corrige un mot) et le miroir inversé (une copie par symétrie centrale).
- Ce que la triangulation ajoute : trois projections sous trois angles différents. Deux projections se croisent en un seul point : la place d'une erreur est trouvée par intersection ; la troisième confirme, et permet d'en traiter plusieurs. Une projection droite ne voit pas deux mots échangés dans une même colonne ; une projection en biais les voit : l'ordre devient vérifiable. C'est le principe de la tomographie (reconstruire un volume à partir de ses projections) et des codes à projections discrètes (transformée Mojette), qui servent à reconstruire des données perdues.
- À préciser : les trois angles (lumière d'en haut, reflet en biais, ombre au sol ?), ce que chaque projection additionne (ou exclusif, somme, somme pondérée), et ce que veut dire « l'alignement du code entre ».
