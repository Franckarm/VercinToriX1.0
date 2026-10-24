# Spécification du SPU-64 (version 1, 23 octobre 2026)

Machine de référence : `spu64/spu64.py` (Python). Machine rapide : `vtx-rs` (binaire `vtx64`). Les deux doivent donner, pour tout programme, les mêmes sorties, le même nombre d'instructions et la même mémoire. Conception d'ensemble : `docs/vtx-spu64-conception.md`.

Gravé : cube chromatique, quaternaire, ADN/ARN. Un mot de 64 bits est un **point profond** `#RRRRGGGGBBBBAAAA` : 16 chiffres hex, 32 quits, 32 bases.

## 1. Mots, registres, drapeaux

- Mot : 64 bits sans signe ; les opérations signées le lisent en complément à deux (complément à quatre en base 4 : mêmes bits).
- Registres `R0` à `R15`, 64 bits ; `R0` vaut toujours 0 (une écriture dans R0 est ignorée). Le compilateur réserve `R13` (cadre) et `R14` (pile).
- `PC` : l'indice de l'instruction dans l'étage 0 (48 bits).
- Drapeaux : `Z` (résultat nul), `C` (retenue ou emprunt), `N` (bit 63 du résultat). Chaque opération qui range un résultat dans un registre met Z et N à jour ; C vaut 0 sauf indication contraire.
- Au départ : registres à 0, sauf `R14` = `0x7FFFFFFF` (sommet de la pile) ; `PC` = 0 ; mémoire vide (tout vaut 0, brin libre).

## 2. La mémoire et l'adresse longue

Une adresse est un mot de 64 bits :

| Bits | Champ |
|---|---|
| 63, 62 | l'étage (0 code et pile, 1, 2, 3) |
| 61 à 48 | type et réserve (ignorés pour l'accès) |
| 47 à 24 | la fréquence : le cube (16 777 216 cubes par étage) |
| 23 à 0 | `#RRGGBB` : le point dans le cube (x = RR, y = GG, z = BB) |

L'indice d'un mot dans son étage est l'adresse modulo 2^48 : un tableau qui dépasse `#FFFFFF` continue dans le cube de la fréquence suivante. La mémoire est faite de pages de 65 536 mots, créées à la première écriture ; lire une case jamais écrite rend 0.

**Le brin.** Chaque mot porte en plus un quit de brin, hors de sa valeur : 0 libre, 1 **ADN** (fixé), 2 **ARN** (en travail), 3 réservé. Toute écriture dans un mot ADN arrête la machine avec l'erreur « écriture dans un mot ADN » (adresse donnée). Écrire dans un mot libre ou ARN garde son brin. La lecture ADN d'un mot écrit T pour ses quits à 3 s'il est ADN, U s'il est ARN.

**Cubes sur disque.** `SYS 11` écrit le cube (étage e, fréquence f) dans `cube64-e-f.cub` : `VTXCUB64`, puis pour chaque page non nulle son numéro (u32, page dans le cube : 256 pages de 65 536 mots), ses 65 536 mots (u64, petit boutiste) et ses 65 536 quits de brin (16 384 octets, 4 quits par octet, le premier dans les bits bas). Quand un programme lit ou écrit une page absente de la mémoire, la machine la cherche d'abord dans le fichier de son cube, s'il existe (dossier des fichiers de la machine ; jamais dans le corpus de conformité) : un cube rangé revient page par page, à la demande.

## 3. Format des instructions

Une instruction est un mot de 64 bits :

| Bits | 63 à 48 | 47 à 44 | 43 à 40 | 39 à 36 | 35 à 32 | 31 à 0 |
|---|---|---|---|---|---|---|
| Champ | opération | d | s | t | u (réservé, 0) | imm (32 bits) |

`imm` est lu signé (sext) pour ADDI, SUBI, CMPI, LDIS, LD, ST, LDF, STF, MARQUE, et sans signe pour les sauts et LDIU. `LDI` prend le mot suivant comme constante de 64 bits (l'instruction occupe deux mots).

## 4. Instructions

Notation : `d`, `s`, `t` les registres ; `D`, `S`, `T` leurs valeurs ; `M[a]` le mot à l'adresse a ; `M0[i]` le mot d'indice i de l'étage 0.

### Entiers

| Code | Nom | Effet |
|---|---|---|
| 00 | NOP | rien |
| 01 / 06 | ADD / ADDI | `d = S + T` / `d = S + sext(imm)` ; C = retenue (somme sans signe > 2^64 − 1) |
| 02 / 07 | SUB / SUBI | `d = S − T` / `d = S − sext(imm)` ; C = emprunt (S < soustrait, sans signe) |
| 0E / 0F | CMP / CMPI | comme SUB / SUBI sans ranger : Z, N, C |
| 03 | MUL | 64 bits bas du produit |
| 4E / 1E | MULHU / MULHS | 64 bits hauts du produit sans signe / signé |
| 0C / 0D | DIV / MOD | sans signe ; `x / 0` = 2^64 − 1, `x % 0` = x |
| 1A / 1B | DIVS / MODS | signés, quotient tronqué vers zéro, le reste a le signe de S ; `x / 0` = 2^64 − 1, `x % 0` = x ; `MIN / −1` = MIN, `MIN % −1` = 0 |
| 04 / 05 | SHL4 / SHR4 | décalage d'un quit (2 bits) |
| 08 / 09 / 17 | SHL / SHR / SAR | décalage de `T & 63` bits (SAR : arithmétique) |
| 14 / 15 / 16 | AND / OR / XOR | bit à bit |
| 12 | CMP3 | complément à 3 de chaque quit (non bit à bit) |
| 0A | LDI | `d = M0[PC + 1]` ; `PC += 2` |
| 18 / 19 | LDIS / LDIU | `d = sext(imm)` / `d = imm` (sans signe) |
| 0B | MOV | `d = S` |
| 1F / 22 | ETG / ETGX | `d = S` placé à l'étage `imm & 3` / `T & 3` (bits 63-62 remplacés ; fréquence et #RRGGBB gardés) : c'est `@e[a]` du langage |
| 1C / 1D | ZEXT32 / SEXT32 | les 32 bits bas de S, étendus par des zéros / par le signe |
| 4C / 4D | ADC / SBC | addition / soustraction avec la retenue C ; C = nouvelle retenue / nouvel emprunt |
| 50 | COMPTE | nombre de bits à 1 |

### Quaternaire (32 quits par mot ; quit 0 dans les bits bas)

| Code | Nom | Effet |
|---|---|---|
| 10 / 11 / 13 | MIN / MAX / ADDM4 | par quit : minimum, maximum, somme modulo 4 |
| 4F | QEGAL | 1 dans le bit bas de chaque quit égal entre S et T, 0 ailleurs |
| 56 / 57 | ET4 / OU4 | Belnap sur 32 quits : v = v1 ∧ v2, f = f1 ∨ f2 / l'inverse (bit haut du quit : v, bit bas : f) |
| 58 / 59 | NON4 / ANTI | échange v et f / puis complément |
| 5A | EXQ | `d = (S >> ((T & 31) × 2)) & 3` |
| 54 | LDQ | `d` = le quit `T & 31` du mot `M[S + (T >> 5)]` |
| 55 | STQ | écrit `D & 3` dans ce quit, sans toucher aux 31 autres |
| 38 | GDOT | somme des produits des quatre voies de 16 bits de S et T (64 bits bas) |
| 39 | GEMV | sur la pile (de haut en bas) : n, w, q, k, o (adresses longues) ; pour i < n : `M[o + i] = Σ_{j<w} GDOT(M[q + j], M[k + i·w + j])` |

### Mémoire, pile, sauts, entrées et sorties

| Code | Nom | Effet |
|---|---|---|
| 20 / 21 | LD / ST | `d = M[S + sext(imm)]` / `M[D + sext(imm)] = S` |
| 29 / 2A | LDX / STX | `d = M[S + T]` / `M[D + T] = S` |
| 25 / 26 | LDF / STF | `d = M0[R13 + sext(imm)]` / `M0[R13 + sext(imm)] = D` |
| 27 / 28 | PUSH / POP | `R14 −= 1 ; M0[R14] = S` / `d = M0[R14] ; R14 += 1` |
| 30 / 31 / 32 / 35 / 36 | JMP / JZ / JNZ / JC / JNC | saut à `imm` (toujours, si Z, si non Z, si C, si non C) |
| 33 / 34 | CALL / RET | empile `PC + 1` et saute / dépile `PC` |
| 23 / 24 | IN / OUT | lit un mot de l'entrée (0 si vide) / écrit S sur la sortie |
| 51 / 52 / 53 | ENTC / SORC / SYS | canal S lu dans d / S écrit sur le canal T / `d = service(S, T)` |
| 5E | MARQUE | met le brin `imm & 3` sur les T mots à partir de l'adresse S (sans regarder leur ancien brin) |
| 5F | BRIN | `d` = le brin du mot `M[S]` |
| 3F | HALT | arrêt |

Les adresses calculées (S + imm, D + T…) sont prises modulo 2^64. LDF, STF, PUSH, POP, CALL et RET adressent l'étage 0 par l'indice (modulo 2^48).

### Flottants quaternaires de 64 bits (`flottant`)

Format : quit 31 l'état de Belnap (0 inconnu, 1 négatif, 2 positif, 3 variable) ; quits 30 à 26 l'exposant E (10 bits ; 1023 = infini) ; quits 25 à 0 la mantisse M (52 bits, 26 chiffres en base 4, le premier non nul sauf pour E = 0). Valeur : `M × 4^(max(E, 1) − 537)`. Étendue : de 4^−536 (environ 2 × 10^−323) à presque 4^511 (environ 4,5 × 10^307) ; précision 51 à 52 bits.

| Code | Nom | Effet |
|---|---|---|
| 40 / 41 / 42 / 43 | FADD / FSUB / FMUL / FDIV | résultat exact arrondi au plus proche (pair au milieu) |
| 47 | FSQRT | racine carrée arrondie |
| 44 / 45 / 46 | FEQ / FLT / FLE | 1 ou 0 ; faux si un état est inconnu ou variable ; −0 = +0 |
| 5D | FCMP | 0 égaux, 1 S < T, 2 S > T, 3 sans ordre |
| 5B | FNEG | l'opposé (états négatif et positif échangés ; inconnu et variable inchangés) |
| 5C | FETAT | `d` = le quit d'état (0 à 3), comme un logique |
| 48 / 49 | ITOF / ITOFS | entier sans signe / signé vers flottant, arrondi |
| 4A / 4B | FTOI / FROUND | vers entier signé, tronqué / arrondi au plus proche pair ; saturé ; inconnu et variable donnent 0 |
| 6C / 6D | FVIEEE / FDIEEE | vers les bits du binary64 de l'IEEE (exact ou arrondi ; inconnu et variable donnent 0x7FF8000000000000) / depuis eux (NaN donne variable) |

**Cas particuliers** (les mêmes que le `flottant_petuar`) : un opérande variable donne variable ; sinon un opérande inconnu donne inconnu. ∞ − ∞, 0 × ∞, 0/0, ∞/∞ et la racine d'un négatif (non nul) donnent variable. x + (−x) = +0 ; (−0) + (−0) = −0 ; le signe d'un produit ou d'un quotient nul suit la règle des signes ; racine(−0) = −0. Un dépassement donne l'infini signé ; un résultat sous le plus petit sous-normal est arrondi (vers ±0 ou le plus petit sous-normal). Forme canonique : inconnu = 0, variable = `0xC000000000000000`, zéro = état et rien d'autre (`0x8000000000000000` pour +0), infini = état et E = 1023, mantisse nulle.

### Flottants quaternaires de 32 bits (`flottant_32`), dans les 32 bits bas d'un registre

Format : quit 15 l'état, quits 14 à 11 l'exposant E (8 bits ; 255 = infini), quits 10 à 0 la mantisse (22 bits). Valeur : `M × 4^(max(E, 1) − 138)`. Étendue : de 4^−137 (environ 3,3 × 10^−83) à presque 4^127 (environ 2,9 × 10^76) ; précision 21 à 22 bits. Les résultats sont rangés étendus par des zéros.

| Code | Nom | Effet |
|---|---|---|
| 60 / 61 / 62 / 63 | SADD / SSUB / SMUL / SDIV | comme FADD… |
| 67 | SSQRT | racine |
| 64 / 65 / 66 | SEQ / SLT / SLE | comparaisons |
| 6A | SNEG | l'opposé |
| 68 / 69 | STOF / FTOS | `flottant_32` vers `flottant` (exact) / l'inverse (arrondi) |

Les `flottant_petuar` (128 bits) se calculent par le prélude sur des paires de registres (Rn mot bas, Rn+3 mot haut) ; leurs instructions sont réservées (codes 70 à 7F).

## 5. Services (SYS d, s = code, t = argument)

| Code | Service |
|---|---|
| 1 / 2 | ouvrir un fichier en lecture / écriture (T = adresse du nom : longueur, puis un caractère par mot) ; rend le canal, ou 2^64 − 1 |
| 3 / 4 | fermer le canal T / le canal T est-il au bout ? |
| 5 | 64 bits imprévisibles |
| 6 / 7 | écrire / lire un bloc de mots dans un fichier : le nom (adresse d'un texte), l'adresse longue et le nombre de mots sont en `M[3:14680060..14680062]` (comme au SPU-32) ; huit octets par mot, petit-boutiste ; rend le nombre de mots (la lecture respecte le brin : un mot ADN refuse d'être réécrit) |
| 10 | arrêt « mémoire pleine » |
| 11 | ranger sur disque le cube T (T = adresse longue d'un mot du cube) ; rend le nombre de pages écrites |
| 13 | jeter le cube T (le cube de transfert jetable) : ses pages quittent la mémoire d'un coup, mots et brins, sans être relues du disque ; rend le nombre de pages jetées |
| 12 | présenter l'image (Gobatix) : largeur et hauteur en `M[3:14680058]` et `M[3:14680059]` (étage 3, fréquence 0), points en étage 1, fréquence 0, ligne par ligne ; un point profond donne la couleur de ses octets forts ; rend 0, 1 si la fenêtre a été fermée, 2^64 − 1 sans image |
| 16 | la souris : x (bits 0-11) et y (12-23) en points de l'image, boutons (24-26 : gauche 1, droit 2, milieu 4), dans l'image (27) ; 0 sans fenêtre |
| 17 | la prochaine touche appuyée, sans attendre (un caractère, ou 65 536 + code de touche) ; 0 s'il n'y en a pas |
| 18 | les millisecondes depuis le lancement |
| 19 | la cadence : T millisecondes au moins entre deux présentations (16 au départ) ; rend l'ancienne |
| 20 | les crans de molette depuis le dernier appel (signé) |
| 21 | 1 si la touche T est enfoncée, sinon 0 |
| 22 | l'état des cubes relus sur disque depuis le dernier appel (miroir inversé : le cube et son anti-cube) : 0 inconnu, 1 faux (une seule copie, réparée), 2 vrai (d'accord), 3 variable (contradiction) |

Les services 16 à 22 sont les mêmes au SPU-32 (sur 32 bits). Sans fenêtre (machines de référence, tests), 16, 17, 20
et 21 rendent 0.

Canaux : 0 les nombres (IN et OUT), 1 la console en texte (un caractère par mot), 2 et suivants les fichiers.

## 6. Ce qui change par rapport au SPU-32

Mêmes codes et même sens pour les opérations communes, élargies à 64 bits (32 quits). Disparus : l'étage dans l'instruction (il est dans l'adresse longue), les flottants binaires de l'IEEE (binary32 en 40 à 4B, binary64 en paires 5B à 6B, remplacés par les flottants quaternaires et par FVIEEE/FDIEEE pour l'échange), DMA, et les services 8 et 9 (accorder un étage : l'adresse longue porte la fréquence). Nouveaux : ETG, ETGX, CMPI, LDIS, LDIU, SAR, DIVS, MODS, MULHS, ZEXT32, SEXT32, MARQUE, BRIN, FCMP, FNEG, FETAT, la famille S, FVIEEE, FDIEEE, le brin, les pages lues à la demande depuis le disque.
