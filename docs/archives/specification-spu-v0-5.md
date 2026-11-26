# Spécification v0.5 : SPU à cube chromatique

Statut : brouillon de travail. Chaque point est marqué **Retenu** (décidé pendant la discussion) ou **Proposé** (à valider ou à mesurer).

Modifications de la v0.4 : HEX comme groupement natif du quaternaire (section 1), rôle de vtx (section 6), cache RGBA de sortie (section 7, nouvelle), canal caché par synonymie T/U (section 8, nouvelle), sections renumérotées à partir de 9.

Modifications de la v0.3 : feuille de route en deux versions et section 8 sur le cube chromatique (tranches et points internes).

Modifications de la v0.2 : seuils de mesure du canal (section 4), constats sur le jeu d'instructions issus du langage vtx (section 7).

## 1. Le cube chromatique

**Retenu.** Le cube est le cube RGB adressé en hexadécimal.

- 3 axes : R, V, B. 256 niveaux par axe, de `00` à `FF`.
- Un point s'écrit `#RRGGBB` : 24 bits, soit 12 chiffres quaternaires (quits), soit 16 777 216 points.
- 1 quit = 2 bits. 1 chiffre hexadécimal = 2 quits. 1 axe = 4 quits.

Correspondance hexadécimal vers quits :

```
0=00 1=01 2=02 3=03 4=10 5=11 6=12 7=13
8=20 9=21 A=22 B=23 C=30 D=31 E=32 F=33
```

Exemple : `#3A7F1C` donne R = `0322`, V = `1333`, B = `0130`, soit `0322 1333 0130` en base 4.

**Retenu.** Le HEX n'est pas une base concurrente du quaternaire : 1 chiffre hexadécimal = 2 quits, exactement. Le cœur de la machine (ALU, cache) reste donc nativement en base 4 ; seul le chipset regroupe en binaire/HEX pour parler aux systèmes annexes (PCIe, USB), qui restent les seuls à demander une traduction (section 3).

## 2. Le mot de 32 bits : `#RRGGBBAA`

**Proposé.** Un mot de 32 bits est un point du cube plus un octet alpha : 16 quits, soit 4 voies (R, V, B, A) de 4 quits. Un mot de 64 bits est composé de deux mots de 32 bits.

L'octet alpha se lit ainsi :

| Quit | Rôle |
|---|---|
| A3 | Étage : 0 locale CPU, 1 locale GPU, 2 partagée, 3 disque spectral |
| A2 | Type : 0 donnée, 1 instruction, 2 adresse, 3 contrôle |
| A1, A0 | Réservés |

## 3. Mémoire étagée

**Retenu.**

- 4 étages, désignés par le chiffre d'étage.
- Deux bandes physiques distinctes : bande CPU (étages 0, 2, 3) et bande GPU (étages 1, 2, 3).
- Chipset purement électronique, sans laser : il regroupe les quits en binaire et en hexadécimal pour PCIe et USB.
- Les résultats sont réécrits en RAM (électronique), puis envoyés au disque spectral par le pont optique.

**Proposé.**

- Une adresse `#RRGGBB` désigne un mot dans l'étage choisi (16 777 216 mots par étage).
- Si le CPU et le GPU visent le même étage partagé (2 ou 3) au même créneau, le CPU est servi en premier et le GPU attend un créneau.

## 4. Couche physique

**Proposé.** Chaque voie (R, V, B, A) est une bande de couleur dont l'intensité porte la valeur. La profondeur par impulsion `d` est un paramètre à mesurer sur banc d'essai :

| Quits par voie | Niveaux | Impulsions pour un octet | Rapport requis (10⁻³, avec correction d'erreur) | Rapport requis (10⁻⁹) |
|---|---|---|---|---|
| 1 | 4 | 4 | 26 dB | 31 dB |
| 2 | 16 | 2 | 40 dB | 45 dB |
| 4 | 256 | 1 | 65 dB | 70 dB |

Le rapport est le rapport d'amplitude entre la pleine échelle et le bruit, en dB (20·log10). Ces seuils viennent d'une simulation (`canal_spectral.py` : bruit gaussien constant, décision à mi-distance entre les niveaux). Le modèle est optimiste : il ignore le bruit dépendant de l'intensité, la dérive, l'interférence entre symboles et les non-linéarités.

**Proposé.** Profondeur par défaut : 1 quit par voie (4 niveaux, 4 impulsions par octet). Passer à 2 quits si le banc mesure plus de 45 dB (ou 40 dB avec correction d'erreur). 4 quits par voie ne sont visés que pour des liaisons lentes et très propres (plus de 70 dB).

**Diaphonie et étalonnage.** L'étalonnage par matrice 3×3 est obligatoire dès 16 niveaux. En simulation (16 niveaux, 40 dB) : sans étalonnage, une diaphonie de 2 % donne 15 % d'erreurs et une diaphonie de 10 % en donne 87 %. Avec un étalonnage exact, la perte est négligeable (bruit accru de 3 % au plus à 10 % de diaphonie). Avec 10 % d'erreur sur l'estimation de la matrice, le taux d'erreur est multiplié par 1,3 (diaphonie de 2 %) à 14 (diaphonie de 10 %) par rapport à un canal sans diaphonie. Un réétalonnage périodique est prévu.

**Critère du banc d'essai.** Mesurer le rapport pleine échelle / bruit réel de la chaîne et le comparer au tableau ci-dessus.

## 5. Jeu d'instructions

**Implémenté (vtx 0.4).** Une instruction est un point du cube plus alpha, au format `#RRGGBBAA` :

- **R** : code d'opération (8 bits).
- **V** : registre destination (2 quits) puis registre source (2 quits).
- **B** : registre `rt` (2 quits de tête), valeur immédiate sur 8 bits, décalage signé ou poids faible d'une adresse de saut.
- **A** : étage de l'opérande mémoire (quit A3), type = instruction (quit A2).

Registres : `R0` (toujours nul) à `R15` de 32 bits, compteur de programme `PC` de 24 bits, indicateurs Z (zéro) et C (retenue ou emprunt). Le compilateur réserve R13 (cadre) et R14 (pile).

| Code | Mnémonique | Effet |
|---|---|---|
| 00 | NOP | Aucune opération |
| 01 / 06 | ADD / ADDI | `rd = rs + rt` / `rd = rs + imm` ; C = retenue |
| 02 / 07 / 0E | SUB / SUBI / CMP | Soustraction (CMP ne range rien) ; C = emprunt |
| 03 | MUL | Produit, 32 bits bas |
| 04 / 05 | SHL4 / SHR4 | Décalage d'un quit (×4 ou ÷4) |
| 08 / 09 | SHL / SHR | Décalage de `rt` bits |
| 0A | LDI | Charge le mot suivant |
| 0B | MOV | Copie de registre |
| 0C / 0D | DIV / MOD | Division et reste non signés ; `x / 0` = 0xFFFFFFFF, `x % 0` = x |
| 10 / 11 | MIN / MAX | Minimum ou maximum chiffre par chiffre (quits) |
| 12 | CMP3 | Complément à 3 de chaque quit (soit le non bit à bit) |
| 13 | ADDM4 | Addition modulo 4 chiffre par chiffre, sans retenue |
| 14 / 15 / 16 | AND / OR / XOR | Bit à bit |
| 20 / 21 | LD / ST | Lecture ou écriture d'un mot dans l'étage de l'instruction |
| 29 / 2A | LDX / STX | Lecture ou écriture dans l'étage donné par un registre |
| 22 | DMA | Réservé (non implémenté : `copier` du prélude) |
| 23 / 24 | IN / OUT | Entrée ou sortie d'un mot |
| 25 / 26 | LDF / STF | Lecture ou écriture relative au cadre (R13 + décalage signé) |
| 27 / 28 | PUSH / POP | Pile (R14) |
| 30 | JMP | Saut |
| 31 / 32 | JZ / JNZ | Saut si zéro ou non zéro |
| 35 / 36 | JC / JNC | Saut si retenue ou non |
| 33 / 34 | CALL / RET | Appel et retour |
| 38 | GDOT | Somme des produits des quatre voies de deux mots |
| 39 | GEMV | n produits de w mots d'un coup (arguments sur la pile, étage 2) |
| 3F | HALT | Arrêt |
| 40 / 41 / 42 / 43 | FADD / FSUB / FMUL / FDIV | Flottants IEEE 754 binary32, arrondi au plus proche pair ; tout NaN rendu sous la forme 0x7FC00000 |
| 44 / 45 / 46 | FEQ / FLT / FLE | Comparaisons flottantes, résultat 0 ou 1 (fausses avec NaN) |
| 47 | FSQRT | Racine carrée flottante |
| 48 / 49 | ITOF / ITOFS | Entier non signé ou signé vers flottant |
| 4A / 4B | FTOI / FROUND | Flottant vers entier signé, tronqué ou arrondi au plus proche pair, saturé (NaN donne 0) |
| 4C / 4D | ADC / SBC | Addition ou soustraction avec la retenue C : chaînage des mots pour le 64 bits |
| 4E | MULHU | 32 bits hauts du produit non signé de deux mots |
| 4F | QEGAL | égalité quit par quit : pour chacun des 16 quits, 1 dans son bit bas s'il est égal au quit de même rang, 0 sinon |
| 50 | COMPTE | nombre de bits à 1 du mot (0 à 32) |
| 51 | ENTC | lit un mot sur le canal donné par un registre (0 : entrées numériques, 1 : console en texte, 2 et suivants : fichiers) ; 4294967295 si rien à lire |
| 52 | SORC | écrit un mot sur un canal |
| 53 | SYS | service de la machine hôte : 1 ouvrir en lecture, 2 ouvrir en écriture (nom = texte en mémoire), 3 fermer, 4 fin atteinte ; 12 présenter l'image ; 16 à 21 la souris, la touche suivante, l'horloge, la cadence, la molette, une touche enfoncée (comme au SPU-64, `docs/specification-spu64.md`) |
| 54 | LDQ | `LDQ Rd, Rs, Rt, @e` : lit un quit d'un tableau rangé (16 quits par mot, le quit 0 dans les bits bas) : mot `e:[Rs + (Rt >> 4)]`, place `(Rt & 15) × 2` ; Rd reçoit le quit (0 à 3) ; pose Z, remet C à zéro |
| 55 | STQ | `STQ Rd, Rs, Rt, @e` : écrit `Rd & 3` à la même place, sans toucher aux 15 autres quits du mot ; ne change pas les drapeaux |
| 56 | ET4 | et de Belnap sur les 16 quits : preuve du vrai (bit haut de chaque quit) `v1 & v2`, preuve du faux (bit bas) `f1 | f2` |
| 57 | OU4 | ou de Belnap sur les 16 quits : `v1 | v2`, `f1 & f2` |
| 58 | NON4 | non de Belnap : échange, dans chaque quit, les preuves du vrai et du faux |
| 59 | ANTI | NON4 puis complément de tous les bits (`v = ~f`, `f = ~v`) |
| 5A | EXQ | `EXQ Rd, Rs, Rt` : le quit `Rt & 15` de Rs, `(Rs >> ((Rt & 15) × 2)) & 3` |

Exemple : `ADDI R1, R2, #05` s'encode `#06120510` (le quit A2 de l'alpha vaut 1 : type instruction).

**Flottants et 64 bits, choix retenus.** Les flottants suivent IEEE 754 binary32 : c'est le seul format dont les quatre machines de référence (Python, Java, JavaScript interprété et traduit) donnent les mêmes bits pour chaque opération, NaN compris une fois rendu unique. Les entiers de 64 bits ne demandent pas de registres plus larges : une paire de registres, ADC et SBC pour la retenue et MULHU pour le produit suffisent ; la division et les décalages de 64 bits sont dans le prélude.

**Instructions quaternaires.** QEGAL et COMPTE traitent les 16 quits d'un mot en une instruction : `COMPTE(QEGAL(a, b))` (en vtx : `nb_bits(qegal(a, b))`) donne le nombre de quits égaux, par exemple le nombre de bases communes à deux séquences d'ADN de 16 bases. Comme les autres instructions de calcul, elles posent Z selon le résultat et remettent C à zéro. Les machines de référence sont désormais Python, Rust et les deux machines JavaScript ; la machine Java a été retirée.

**Logique de Belnap (ET4, OU4, NON4, ANTI, EXQ).** Chaque quit porte deux preuves : le bit haut dit « on a une preuve du vrai », le bit bas « une preuve du faux » ; d'où inconnu (00), faux (01), vrai (10), variable (11, les deux à la fois). ET4, OU4, NON4 et ANTI appliquent la logique à quatre valeurs aux 16 quits d'un mot en une instruction (il en fallait 7 à 10) ; `fusion` et `consensus` restent OR et AND. EXQ lit un quit d'un registre (il en fallait 4). Toutes posent Z selon le résultat et remettent C à zéro.

**Quits rangés (LDQ, STQ).** Un tableau de quits ou de logiques range 16 éléments par mot. Sans instruction dédiée, lire un élément demandait cinq à six instructions binaires (adresse du mot, décalage, masque) et en écrire un une dizaine ; LDQ et STQ le font en une. L'adresse se calcule comme pour un tableau ordinaire (base dans Rs, indice dans Rt) : la machine prend le mot `Rs + (Rt >> 4)` et la place `(Rt & 15) × 2` dans ce mot. Les compilateurs les emploient pour `t[i]` et `t[i] = v` quand l'indice est simple. Mesure (génome de 16 384 bases, recherche d'un motif base par base) : le tableau de quits coûtait 2,5 fois le tableau « une base par mot » ; il coûte maintenant 1,08 fois, avec 16 fois moins de mémoire.

## 6. Chaîne logicielle

**Proposé.**

- Émulateur de référence, avec un canal spectral bruité et paramétrable.
- Assembleur : mnémoniques vers mots `#RRGGBBAA`.
- Format de programme : une instruction par ligne, en hexadécimal (`06120510`).
- Compilateur : d'abord un sous-ensemble de C, puis un backend LLVM.

**Implémenté.** Compilateur vtx (`vtx.py`), assembleur et émulateur de référence ; émulateurs Java (`Vtx.java`) et JavaScript (`vm_rapide.js`) ; traducteur du code machine en fonctions JavaScript (`vm_traduite.js`, un bloc de base par fonction, environ 3,5 fois plus rapide que l'interprète). Les quatre machines donnent les mêmes sorties, le même nombre d'instructions et la même mémoire sur le corpus de conformité.

**Retenu.** vtx reste le langage de référence de cette machine : ses primitives (`.r`, `.v`, `.b`, `.a`, `.q(i)`, `ADDM4`, `CMP3`, `GDOT`) correspondent directement aux opérations natives du SPU, sans rien à traduire entre le langage et le jeu d'instructions — contrairement à un langage pensé pour une machine binaire (complément à deux, adressage par octet), qui porterait ces hypothèses jusque dans le compilateur.

## 7. Cache RGBA de sortie

**Proposé.** À la sortie du CPU (et du GPU), un petit banc de LED RGBA individuellement adressables sert de
cache : chaque LED est pilotée par un registre électronique qui la maintient allumée à la couleur commandée
jusqu'au prochain ordre. La lumière n'est que la sortie visible de ce registre, pas la mémoire elle-même —
ce n'est pas du stockage optique, mais ça évite d'avoir à capter une impulsion au bon instant : la valeur
reste lisible en continu, à tout moment.

Équivalent existant : une LED adressable comme la WS2812 (« NeoPixel ») est exactement ce composant — un
registre par LED, maintenue à la couleur commandée. Un premier banc d'essai peut être construit avec ce
composant, sans rien inventer côté matériel.

**À décider.** Nombre de LED du cache, lien entre sa profondeur et la profondeur de la couche physique
(section 4), politique de remplacement.

## 8. Canal caché : synonymie T/U et capacité

**Étudié, non retenu comme opération matérielle.** Dans un encodage inspiré de l'ADN (0-1-2-3 → A-C-G-T), le
chiffre 3 (T) pourrait aussi s'écrire U, une couleur distincte associée à la même valeur logique. Le choix
entre T et U ne change rien à la valeur transportée, mais peut lui-même porter une information
supplémentaire : un canal caché, superposé au canal principal.

Capacité :

- En gardant les 4 valeurs (0 à 3) exactement équiprobables — pour ne pas perturber les statistiques du
  canal principal, ce qui le rendrait détectable — seul le quart des positions où la valeur vaut 3 offre ce
  choix, et chacune porte alors 1 bit caché en plus. Capacité moyenne : 1/4 × 1 bit = **0,25 bit par quit,
  soit +12,5 %** par rapport aux 2 bits d'un quit ordinaire.
- Le plafond théorique, si l'on acceptait de rendre la valeur 3 artificiellement plus fréquente (2/5 des
  positions au lieu de 1/4) pour exploiter au mieux les 5 symboles physiques (A, C, G, T, U), est de
  log₂(5) ≈ 2,32 bits par position, soit +16,1 %. Ce plafond n'est pas recommandé : il déforme la
  distribution du canal principal, ce qui expose le canal caché à la détection statistique (stéganalyse).

Faisabilité avec le cube de base :

- **Non, pas comme opération native de l'ALU.** Les opérations chiffre par chiffre (`ADDM4`, `MIN`, `MAX`,
  `CMP3`) supposent une arithmétique modulo 4 uniforme sur tous les quits. Une position à 5 symboles casse
  cette uniformité et demanderait un cas particulier à chaque opération, partout où un « 3 » peut
  apparaître.
- **Oui, comme fonction logicielle, au niveau de vtx.** Rien n'empêche d'écrire, en langage vtx, un couple
  `compresser()` / `decompresser()` qui parcourt une suite de quits déjà quaternaires et qui, à chaque quit
  valant 3, consomme ou produit un bit supplémentaire d'un flux annexe, en choisissant T ou U à l'émission.
  Le matériel reste uniforme et propre ; c'est le logiciel qui porte cette astuce, à la frontière de
  sérialisation (typiquement vers le disque spectral).

## 9. À décider ou à mesurer

- Validation sur banc d'essai de la profondeur par impulsion et des seuils de la section 4.
- Contenu exact de l'octet alpha (champs réservés).
- Nombre de registres et taille réelle des étages.
- Politique d'arbitrage et cohérence de l'étage partagé.
- Ordre des primaires et matrice d'étalonnage.
- Jeu d'instructions v0.2 (constats du langage vtx) : sauts sur N et C pour les comparaisons, chargement d'un immédiat large (`LDI`), pointeur de pile (`R14`) avec `PUSH` et `POP`, décalages généraux et opérations bit à bit (ET, OU, OU exclusif) pour les champs `.r`, `.v`, `.b`, `.a`.
- Instruction d'interpolation (`INTERP`) et requête de région par quatre coins (section 10).

## 10. Feuille de route et cube chromatique

**Retenu.** Deux versions :

- **Version 1, hybride** : la lumière transporte les données et calcule l'algèbre linéaire, l'électronique mémorise et décide. Le cache et les registres restent, en électronique.
- **Version 2, tout-optique à flux** : le chipset est la seule passerelle entre électrique et lumière, le MAR devient son émetteur. Pas de cache ni de registres : des lignes à retard servent de tampons, et un programme est une configuration de routes. Cette version convient aux flux (image, calcul matriciel), pas à un ordinateur généraliste.

Le cube chromatique est le format commun aux deux.

**Proposé.** Rôle du cube dans chaque version :

| | Version 1 (hybride) | Version 2 (tout-optique, flux) |
|---|---|---|
| Mots | `#RRGGBBAA` sur 4 voies (R, V, B, A) | même format, à l'entrée et à la sortie du chipset |
| Adresse | point du cube sur 24 bits, étage dans alpha, sous-cubes = banques | un instant dans une ligne à retard ; la voie choisit la route |
| Instruction | un point du cube : R opération, V et B opérandes | une transformation appliquée à un point du cube |
| Calcul | opérations par voie, produit scalaire sur 4 voies | transformations linéaires du cube, saturation pour seuil |
| Précision | 256 niveaux aux frontières, 4 en liaison | cube grossier à l'intérieur (4 ou 16 niveaux), 256 au chipset |
| Programme vtx | suite d'instructions | graphe de transformations, compilé en routes |

**Localité 3D.** En entrelaçant les quits des trois axes (code de Morton), deux points proches dans le cube ont des adresses proches : utile pour les banques et pour les voisinages lus par le GPU.

**Opérations saturantes par voie.** Une couleur plafonne à 255 au lieu de repartir à 0, comme dans le traitement d'image. Cela donne des opérations sur 4 voies par impulsion. En optique, la saturation d'un composant peut jouer le rôle de seuil.

**Profondeur variable.** Chaque étage optique retire quelques dB de rapport signal/bruit (section 4). Le cube à 256 niveaux n'est réaliste qu'aux frontières ; à l'intérieur, on travaille à 4 ou 16 niveaux.

**Tranches et points internes.** Une tranche du cube est un plan à hauteur fixe sur un axe : 256 tranches de 65 536 points. À partir de 4 points initiaux (les coins), on décrit une région entière, et les points internes se déduisent par interpolation :

- *Géométrie et couleurs* : un patch de 4 coins remplace des centaines de points. L'interpolation bilinéaire d'un point est une somme pondérée de 4 valeurs par voie, soit un produit scalaire sur 4 voies (trois par point pour R, V et B) : un calcul naturel pour l'optique linéaire. Le trafic entre le MAR et le GPU diminue d'autant : 4 points au lieu de 256 pour un patch de 16 par 16. Si le bruit des 4 coins est indépendant, il est divisé par deux au centre du patch.
- *Adressage* : une région de mémoire se demande par ses 4 coins, et la RAM renvoie tous les points internes en rafale. Les adresses internes doivent être générées exactement, avec des compteurs : l'interpolation analogique convient aux valeurs, pas aux adresses.
- *Version 2* : les 4 coins arrivent en 4 impulsions successives, des lignes à retard les alignent, des atténuateurs appliquent les poids et un coupleur fait la somme. C'est un interpolateur optique, et les points internes forment un continuum, numérisé seulement au chipset.

**Limites.** Quatre points ne sont pas toujours dans un même plan : l'interpolation donne alors une surface gauche (patch bilinéaire) et non une tranche plane. Elle ne convient qu'aux données continues (surfaces, dégradés, images), pas au texte ni au code, et les points internes sont approchés, pas stockés. La couleur ne peut pas servir d'adresse fine : on ne distingue que quelques centaines à quelques milliers de couleurs pures, et le cube repose sur des intensités portées par des voies fixes. Seules la voie et l'instant peuvent donc router la lumière.

## 11. Suite

Phase 1 en cours : spécification, langage vtx avec compilateur et émulateur de référence (`vtx.py`, `vtx.rs`), protocole du banc d'essai (`protocole-banc-essai-v0-1.md`) et script d'analyse des mesures (`analyse_banc.py`). Prochaine étape : mesures réelles sur le banc d'essai à une liaison, puis extension du jeu d'instructions (section 9) et prototype du cache RGBA (section 7) avec des LED adressables.
