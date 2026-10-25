# Spécification de Lugus, le SPU-128 (version 1, 25 octobre 2026)

Conception d'ensemble et décisions : `docs/vtx-spu128-conception.md`. Machine de référence prévue : `spu128/spu128.py`
(Python) ; machine rapide : `vtx-rs` (binaire `lugus`). Les deux devront donner, pour tout programme, les mêmes sorties,
le même nombre d'instructions et la même mémoire. Ce document reprend la spécification du SPU-64 (Dunon) et dit ce qui
change ; ce qu'il ne mentionne pas est comme au SPU-64.

Gravé : cube chromatique, quaternaire, ADN/ARN, logique de Belnap. Un mot de 128 bits est un **point de matière**
`#RRRRRRRR_VVVVVVVV_BBBBBBBB_MMMMMMMM` : 32 chiffres hex, 64 quits, 64 bases.

## 1. Mots, voies, registres, drapeaux

- **Mot** : 128 bits sans signe ; les opérations signées le lisent en complément à deux (complément à quatre en base 4 :
  mêmes bits).
- **Les voies** : le mot a quatre voies de 32 bits. La voie k occupe les bits 32k + 31 à 32k :
  voie 3 = R (bits 127-96), voie 2 = V (95-64), voie 1 = B (63-32), voie 0 = M, la matière (31-0).
- **La voie de matière** (lecture d'un point de matière ; les instructions de la matière, section 4.6) :

  | Codon | Bits | Quits | Contenu |
  |---|---|---|---|
  | 0 | 31-30 | 15 | l'état, Belnap (0 inconnu, 1 faux, 2 vrai, 3 variable) |
  | 1 | 29-24 | 14-12 | le reflet |
  | 2 | 23-18 | 11-9 | la lumière |
  | 3 | 17-12 | 8-6 | la transparence |
  | 4 | 11-6 | 5-3 | la profondeur |
  | 5 | 5-0 | 2-0 | la rugosité |

  Chaque propriété est un codon (trois quits, 64 degrés : 0 rien, 63 le plus). En hex, la voie se lit par groupes de
  2, 3 et 3 chiffres (état et reflet ; lumière et transparence ; profondeur et rugosité).
- **Registres** `R0` à `R15`, 128 bits ; `R0` vaut toujours 0. Le compilateur réserve `R13` (cadre) et `R14` (pile).
- **Drapeaux** : `Z` (résultat nul), `C` (retenue ou emprunt), `N` (le bit de signe du résultat, à la largeur de
  l'opération). Chaque opération qui range un résultat met Z et N à jour ; C vaut 0 sauf indication contraire.
- **Au départ** : registres à 0, sauf `R14` = `0x7FFFFFFF` (sommet de la pile, un indice de l'étage 0) ; `PC` = 0 ;
  mémoire vide (tout vaut 0, brin libre).

## 2. La mémoire et l'adresse

Une adresse est un mot de 128 bits (l'adresse du SPU-64, élargie) :

| Bits | Champ |
|---|---|
| 127, 126 | l'étage (0 code et pile, 1, 2, 3) |
| 125, 124 | le type (0 donnée, 1 instruction, 2 adresse, 3 contrôle ; ignoré pour l'accès) |
| 123, 122 | l'état (Belnap ; ignoré pour l'accès ; le pointeur nul est inconnu) |
| 121, 120 | réserve (ignorés) |
| 119 à 24 | la fréquence : le cube (2^96 cubes par étage) |
| 23 à 0 | `#RRGGBB` : le point dans le cube de 256³ (x = RR, y = GG, z = BB) |

L'**indice** d'un mot dans son étage est l'adresse modulo 2^120 : un tableau qui dépasse `#FFFFFF` continue dans le cube
de la fréquence suivante. La mémoire est faite de pages de 65 536 mots, créées à la première écriture ; lire une case
jamais écrite rend 0.

**Le brin** de chaque mot : comme au SPU-64 (un quit hors de la valeur : 0 libre, 1 ADN fixé, 2 ARN en travail,
3 réservé ; écrire dans un mot ADN arrête la machine avec l'erreur « écriture dans un mot ADN »).

**Cubes sur disque.** `SYS 11` écrit le cube (étage e, fréquence f) dans `cube128-e-f.cub` : `VTXCU128`, puis pour
chaque page non nulle son numéro (u32, page dans le cube : 256 pages de 65 536 mots), ses 65 536 mots (u128,
petit-boutiste) et ses 65 536 quits de brin (16 384 octets, quatre quits par octet, le premier dans les bits bas).
Chaque cube est écrit avec son **anti-cube** (le miroir inversé : complément, et places en symétrie centrale) et son
**ombre** (par colonne de 256 mots, les ou exclusifs qui localisent et corrigent un mot), comme aux SPU-32 et SPU-64 ;
`SYS 22` rend l'état de Belnap des relectures. Une page absente de la mémoire est d'abord cherchée dans le fichier de
son cube, s'il existe (jamais dans le corpus de conformité).

## 3. Le code : deux instructions par mot

Une **instruction** a 64 bits, au format du SPU-64 :

| Bits | 63 à 48 | 47 à 44 | 43 à 40 | 39 à 36 | 35 à 32 | 31 à 0 |
|---|---|---|---|---|---|---|
| Champ | opération | d | s | t | w : la largeur | imm (32 bits) |

Un **mot de code** (étage 0) porte deux instructions : la première dans les bits 127-64 (lue d'abord, comme on lit
l'hex), la seconde dans les bits 63-0. **PC** compte les demi-mots : l'instruction n° p est dans le mot p / 2 de
l'étage 0, la moitié haute si p est pair, la moitié basse s'il est impair. Les sauts, CALL et RET parlent en demi-mots.

**La largeur** `w` (les bits 35-32, qui étaient réservés au SPU-64) : 0 = 128 bits, 1 = 64 bits, 2 = 32 bits (3 est
refusé). Une opération entière à la largeur 64 ou 32 calcule sur les bits bas de ses opérandes, range son résultat
étendu par des zéros, et pose Z, N et C à cette largeur. Pour une opération flottante, `w` choisit le format
(section 4.4). L'entier par défaut du langage étant de 64 bits, la plupart des opérations du code compilé ont w = 1 :
une seule instruction, sans masque.

`imm` est lu signé (sext) pour ADDI, SUBI, CMPI, LDIS, LD, ST, LDF, STF, MARQUE, et sans signe pour les sauts, LDIU et
les champs de sélection (voie, codon, poids). **LDI** prend la demi-instruction suivante comme constante de 64 bits
(étendue par des zéros) ; **LDIH** remplace les 64 bits hauts de d par la demi-instruction suivante. Chacune occupe
deux demi-mots et compte pour un pas. Une constante de 128 bits s'écrit LDI puis LDIH.

## 4. Instructions

Notation : `d`, `s`, `t` les registres ; `D`, `S`, `T` leurs valeurs ; `M[a]` le mot à l'adresse a ; `M0[i]` le mot
d'indice i de l'étage 0 ; `L` la largeur (128, 64 ou 32 bits), `mask` = 2^L − 1. Les codes sont ceux du SPU-64 pour les
opérations communes ; les familles nouvelles commencent à 80 (hex).

### 4.1 Entiers (à la largeur w)

| Code | Nom | Effet |
|---|---|---|
| 00 | NOP | rien |
| 01 / 06 | ADD / ADDI | `d = (S + T) & mask` / `d = (S + sext(imm)) & mask` ; C = retenue |
| 02 / 07 | SUB / SUBI | `d = (S − T) & mask` / `d = (S − sext(imm)) & mask` ; C = emprunt |
| 0E / 0F | CMP / CMPI | comme SUB / SUBI sans ranger : Z, N, C |
| 03 | MUL | les L bits bas du produit |
| 4E / 1E | MULHU / MULHS | les L bits hauts du produit, sans signe / signé |
| 0C / 0D | DIV / MOD | sans signe ; `x / 0` = mask, `x % 0` = x |
| 1A / 1B | DIVS / MODS | signés, quotient tronqué vers zéro, reste du signe de S ; `x / 0` = mask, `x % 0` = x ; `MIN / −1` = MIN, `MIN % −1` = 0 |
| 04 / 05 | SHL4 / SHR4 | décalage d'un quit |
| 08 / 09 / 17 | SHL / SHR / SAR | décalage de `T & (L − 1)` bits (SAR : arithmétique) |
| 14 / 15 / 16 | AND / OR / XOR | bit à bit, sur L bits |
| 12 | CMP3 | complément à 3 de chaque quit (non bit à bit), sur L bits |
| 1C / 1D | ZEXT / SEXT | les L bits bas de S, étendus à 128 bits par des zéros / par le signe |
| 4C / 4D | ADC / SBC | avec la retenue C ; C = nouvelle retenue / nouvel emprunt |
| 50 | COMPTE | nombre de bits à 1 des L bits bas |
| 0A / 2B | LDI / LDIH | constante de la demi-instruction suivante : `d` = elle / `d` = ses 64 bits en haut, les 64 bits bas de D gardés |
| 18 / 19 | LDIS / LDIU | `d = sext(imm)` / `d = imm` |
| 0B | MOV | `d = S` |
| 1F / 22 | ETG / ETGX | `d = S` placé à l'étage `imm & 3` / `T & 3` (bits 127-126 remplacés) |

### 4.2 Quaternaire (L / 2 quits ; quit 0 dans les bits bas)

| Code | Nom | Effet |
|---|---|---|
| 10 / 11 / 13 | MIN / MAX / ADDM4 | par quit : minimum, maximum, somme modulo 4 |
| 4F | QEGAL | 1 dans le bit bas de chaque quit égal entre S et T, 0 ailleurs (64 bases d'ADN comparées d'un coup à w = 0) |
| 56 / 57 | ET4 / OU4 | Belnap par quit : v = v1 ∧ v2, f = f1 ∨ f2 / l'inverse (bit haut du quit : v, bit bas : f) |
| 58 / 59 | NON4 / ANTI | échange v et f / puis complément |
| 5A | EXQ | `d = (S >> ((T & (L/2 − 1)) × 2)) & 3` |
| 54 | LDQ | `d` = le quit `T & 63` du mot `M[S + (T >> 6)]` |
| 55 | STQ | écrit `D & 3` dans ce quit, sans toucher aux 63 autres |
| 39 | GEMV | comme au SPU-64, avec GDOT (4.5) |

### 4.3 Mémoire, pile, sauts, entrées et sorties, brin

Comme au SPU-64 : LD / ST (20 / 21), LDX / STX (29 / 2A), LDF / STF (25 / 26), PUSH / POP (27 / 28), JMP, JZ, JNZ, JC,
JNC (30, 31, 32, 35, 36), CALL / RET (33 / 34 ; CALL empile `PC + 1`, en demi-mots), IN / OUT (23 / 24), ENTC, SORC,
SYS (51, 52, 53), MARQUE / BRIN (5E / 5F), HALT (3F). Les adresses calculées sont prises modulo 2^128 ; LDF, STF,
PUSH, POP, CALL et RET adressent l'étage 0 par l'indice (modulo 2^120). Un mot lu ou écrit fait toujours 128 bits.

### 4.4 Flottants quaternaires (format choisi par w)

| w | Type | Format | Valeur | Étendue, précision |
|---|---|---|---|---|
| 0 | `flottant` | quit 63 l'état ; quits 62 à 56 l'exposant E (14 bits ; 16383 = infini) ; quits 55 à 0 la mantisse M (112 bits) | `M × 4^(max(E, 1) − 8247)` | 10^−4964 à 1,19 × 10^4931 ; 111 à 112 bits |
| 1 | `flottant_64` | le flottant du SPU-64 : état, E sur 10 bits (1023 = infini), M sur 52 bits | `M × 4^(max(E, 1) − 537)` | 2 × 10^−323 à 4,5 × 10^307 ; 51 à 52 bits |
| 2 | `flottant_32` | le flottant de 32 bits du SPU-64 : état, E sur 8 bits (255 = infini), M sur 22 bits | `M × 4^(max(E, 1) − 138)` | 3,3 × 10^−83 à 2,9 × 10^76 ; 21 à 22 bits |

Le format de 128 bits est celui du `flottant_petuar` d'aujourd'hui : mêmes bits, mêmes résultats (référence exacte :
`spu64/qflot.py`, format Q128, et `tests/ref_petuar.py`). Les formats de 64 et 32 bits sont rangés dans les bits bas,
étendus par des zéros.

| Code | Nom | Effet |
|---|---|---|
| 40 / 41 / 42 / 43 | FADD / FSUB / FMUL / FDIV | résultat exact arrondi au plus proche (pair au milieu) |
| 47 | FSQRT | racine carrée arrondie |
| 44 / 45 / 46 | FEQ / FLT / FLE | 1 ou 0 ; faux si un état est inconnu ou variable ; −0 = +0 |
| 5D | FCMP | 0 égaux, 1 S < T, 2 S > T, 3 sans ordre |
| 5B / 5C | FNEG / FETAT | l'opposé / le quit d'état (0 à 3) |
| 48 / 49 | ITOF / ITOFS | entier sans signe / signé (de la largeur `imm & 3` : 0 = 128, 1 = 64, 2 = 32) vers flottant, arrondi |
| 4A / 4B | FTOI / FROUND | vers entier signé de la largeur `imm & 3`, tronqué / arrondi au plus proche pair ; saturé ; inconnu et variable donnent 0 |
| 6E | FCONV | `d` = S converti du format `imm & 3` vers le format w (arrondi au plus proche) |
| 6C / 6D | FVIEEE / FDIEEE | vers les bits du binary de l'IEEE de même taille (w = 0 : binary128 ; 1 : binary64 ; 2 : binary32) / depuis eux ; inconnu et variable donnent le NaN canonique ; un NaN donne variable |

Cas particuliers : ceux du SPU-64 et du `flottant_petuar` (variable l'emporte sur inconnu, inconnu sur un nombre ;
∞ − ∞, 0 × ∞, 0/0, ∞/∞ et la racine d'un négatif non nul donnent variable ; formes canoniques : inconnu = 0, variable =
le quit d'état à 3 et rien d'autre, zéro = l'état seul, infini = l'état et E maximal).

### 4.5 Les voies (nouveau ; quatre voies de 32 bits)

| Code | Nom | Effet |
|---|---|---|
| 80 / 81 / 82 | VADD / VSUB / VMUL | par voie, modulo 2^32 (VMUL : les 32 bits bas du produit) |
| 83 / 84 | VMIN / VMAX | par voie, sans signe |
| 85 / 86 / 87 / 88 | VFADD / VFSUB / VFMUL / VFDIV | par voie, chaque voie lue comme un `flottant_32` quaternaire |
| 38 | GDOT | somme des produits des quatre voies de S et T (128 bits ; les produits de 64 bits, la somme exacte) |
| 89 | VBCAST | les 32 bits bas de S recopiés dans les quatre voies |
| 8A | VEXT | `d` = la voie `T & 3` de S (étendue par des zéros) |
| 8B | VINS | `d` = D, sa voie `imm & 3` remplacée par les 32 bits bas de S |

### 4.6 La matière (nouveau)

| Code | Nom | Effet |
|---|---|---|
| 90 | MATL | `d` = le codon `T & 7` de la voie M de S (0 l'état sur 2 bits, 1 à 5 les propriétés sur 6 bits, 6 et 7 : 0) |
| 91 | MATE | `d` = S, son codon `imm & 7` remplacé par les bits bas de T |
| 92 | MELANGE | `d` = le mélange de S et T au poids `p = imm & 511` (0 à 256) : chaque voie de couleur `(S × (256 − p) + T × p) >> 8` ; chaque propriété de matière de même ; l'état, la fusion de Belnap des deux états (OU bit à bit : inconnu et vrai donnent vrai ; vrai et faux donnent variable) |
| 93 | ANTIPOINT | `d` = S, ses trois voies de couleur complémentées (la symétrie par le gris du centre : le blanc devient le noir, chaque couleur sa complémentaire), la matière gardée |

## 5. Services (SYS d, s = code, t = argument)

Ceux du SPU-64 (1 à 7, 10 à 13, 16 à 23), sur 128 bits ; la valeur d'erreur est 2^128 − 1. Pour `SYS 12` (présenter
l'image), un point de matière donne à l'écran l'octet fort de chacune de ses voies de couleur : rouge = bits 127-120,
vert = 95-88, bleu = 63-56 (la matière est pour le rendu du programme, pas pour l'écran).

## 6. Conformité

Le corpus de conformité de Lugus aura la forme de ceux des SPU-32 et SPU-64 : une ligne par programme, « mots;entrées »
(les mots en décimal), et la ligne attendue « pas|sorties|mémoire ». Un pas est une demi-instruction jouée (LDI et
LDIH comptent pour un).

## 7. Ce qui change par rapport au SPU-64 (Dunon)

- Le mot, les registres et l'adresse passent à 128 bits ; la fréquence a 96 bits.
- Deux instructions par mot de code ; PC en demi-mots.
- La largeur w dans chaque instruction (128, 64, 32 bits) : ZEXT32 et SEXT32 deviennent ZEXT et SEXT à la largeur w.
- Les flottants par la largeur : le flottant de 128 bits (l'ancien `flottant_petuar`) devient une instruction ; la
  famille S (60 à 6A) disparaît, remplacée par w = 2 ; FCONV remplace STOF et FTOS.
- Nouveau : LDIH, les voies (80 à 8B), la matière (90 à 93), GDOT sur quatre voies de 32 bits.

## 8. Notes honnêtes

- Le flottant de 128 bits est une instruction de Lugus, mais pas du processeur hôte : la machine Rust et la forge le
  calculeront en entiers (de l'ordre de dix à cinquante instructions de l'hôte par opération), bien plus vite que le
  prélude d'aujourd'hui, moins vite qu'un flottant de l'IEEE fait par les circuits.
- La largeur w coûte un champ de l'instruction qui était libre ; elle évite un masque après chaque opération sur des
  entiers de 64 bits.
- Les codes, la répartition de la voie de matière et le format des cubes sur disque restent ouverts jusqu'à la fin des
  deux machines et du corpus : s'il faut les corriger, ce sera avant le compilateur.
