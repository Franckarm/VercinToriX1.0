# Lugus, le SPU-128 : conception (à valider avant tout code)

*25 octobre 2026. Décisions du créateur : le 128 bits devient le standard moyen, le 64 la configuration minimale ; le 32
est gelé pour la rétro-ingénierie des programmes écrits dans d'autres langages. Le cube chromatique reste inchangé (le
noir et le blanc aux coins opposés, la diagonale des gris entre eux) ; la matière s'ajoute à chaque point : reflet,
lumière, transparence, profondeur, rugosité. L'écriture hex est gardée. Tout suit le chemin cube → hex → ADN → ARN →
programme, et inversement, les adresses comme les données. Ce que le 64 a apporté (fiabilité, cohérence, autonomie,
calcul, compression) s'inscrit dans le 128 ; la performance vient ensuite. Pas de précipitation : ce document fixe le
cap, rien n'est encore codé. Les propositions de Claude sont marquées comme telles, à trancher.*

## 0. Ce qui reste gravé

Cube chromatique (la mémoire est le cube des couleurs, écrite en hex), quaternaire (deux quits par chiffre hex),
ADN/ARN (A C G T/U), logique de Belnap (inconnu 0, faux 1, vrai 2, variable 3). Le passage à 128 bits double encore le
point ; il ne change aucune de ces lectures : un mot de 128 bits, c'est 32 chiffres hex, 64 quits, 64 bases.

## 1. Le mot : le point de matière

| | SPU-32 (gelé) | SPU-64 (minimal) | SPU-128 (standard) |
|---|---|---|---|
| Écriture | `#RRGGBBAA` | `#RRRRGGGGBBBBAAAA` | `#RRRRRRRR_VVVVVVVV_BBBBBBBB_MMMMMMMM` |
| Voies | 4 × 8 bits | 4 × 16 bits | 3 × 32 bits de couleur + 32 bits de matière |
| Couleurs | 16 777 216 | 281 474 976 710 656 | **79 228 162 514 264 337 593 543 950 336** |
| Quits / bases | 16 | 32 | 64 |

**La place reste la couleur.** Les trois premières voies sont la place du point dans le cube chromatique (R, V, B),
avec 32 bits par voie : la précision des images HDR du cinéma. Le noir est `#00000000_00000000_00000000_…`, le blanc
`#FFFFFFFF_FFFFFFFF_FFFFFFFF_…`, la diagonale des gris a ses trois voies égales.

**La quatrième voie est la matière** (proposition de partage, à valider) :

| Quits de la voie M | Bits | Contenu | Valeurs |
|---|---|---|---|
| 15 | 31-30 | **l'état**, Belnap : inconnu (jamais écrit), faux, vrai, variable (contradiction) | 4 |
| 14 à 12 | 29-24 | le **reflet** | 64 degrés |
| 11 à 9 | 23-18 | la **lumière** (émission) | 64 degrés |
| 8 à 6 | 17-12 | la **transparence** | 64 degrés |
| 5 à 3 | 11-6 | la **profondeur** (la distance où la lumière s'éteint dans la matière) | 64 degrés |
| 2 à 0 | 5-0 | la **rugosité** | 64 degrés |

En hex, la voie se lit par groupes entiers : l'état et le reflet font les deux premiers chiffres (8 bits), la lumière
et la transparence les trois suivants (12 bits), la profondeur et la rugosité les trois derniers (12 bits). Le mot garde
ses 32 chiffres hex. Chaque propriété tient en **trois quits, donc trois bases : un codon**, comme le code génétique (trois bases, 64
possibilités). La voie de matière est l'état suivi de cinq codons : 1 073 741 824 matières. En tout, un mot de 128 bits
distingue 2^128 points de matière (340 282 366 920 938 463 463 374 607 431 768 211 456).

Pour l'IA, un point de matière est un vecteur de huit nombres (R, V, B, reflet, lumière, transparence, profondeur,
rugosité) dans un espace où la distance a un sens : deux points proches sont deux matières proches, la diagonale est
l'axe de la luminosité.

**Ce n'est qu'une lecture du mot.** Un entier, un flottant, un texte ou un brin d'ADN occupent les 128 bits à leur
façon ; la machine ne regarde la matière que dans les instructions qui la lisent (section 4) et dans Gobatix.

**Du 64 au 128** (comme du 32 au 64) : chaque voie de 16 bits devient les 16 bits forts de la voie de 32 bits. Un point
profond garde ainsi ses couleurs. Sa voie A (l'alpha) devient la matière : proposition, l'alpha opaque donne la
transparence nulle, et les autres propriétés valent zéro, l'état « vrai ».

## 2. L'adresse : celle du SPU-64, élargie

Décidé : l'adresse du SPU-64 (étage, fréquence, `#RRGGBB`), élargie à 128 bits. Les programmes, l'atelier et les
fichiers de cubes passent du 64 au 128 sans changer de logique.

| Bits | Champ |
|---|---|
| 127, 126 | l'étage (0 code et pile, 1, 2, 3) |
| 125, 124 | le type (donnée, instruction, adresse, contrôle) |
| 123, 122 | l'état (Belnap ; le pointeur nul est *inconnu*) |
| 121 à 120 | réserve |
| 119 à 24 | la fréquence : le cube (2^96 cubes par étage) |
| 23 à 0 | `#RRGGBB` : le point dans le cube de 256³ (x = RR, y = GG, z = BB) |

- **Tout passe par le cube** : une adresse est un point `#RRGGBB` d'un cube, et la fréquence dit lequel. Les 96 bits de
  fréquence se lisent aussi comme trois coordonnées de 32 bits dans le « cube des cubes » : l'espace des places a la même
  forme que le point de matière.
- **Ajouter 1 à une adresse** avance en BB, puis GG, puis RR, puis dans le cube de la fréquence suivante, comme au
  SPU-64 : un tableau parcourt le cube naturellement, l'arithmétique des pointeurs reste une addition.
- La mémoire reste faite de pages créées à la première écriture : l'espace d'adresses n'est pas réservé.

(Proposition écartée : l'adresse en trois voies de place x, y, z. Elle revient au même par un autre rangement des bits,
mais elle aurait obligé à tout reprendre.)

## 3. Les nombres

| Type | Taille | Écriture | Format |
|---|---|---|---|
| `entier` | 64 | `5` | entier de 64 bits (32 quits) : le plus rapide, natif sur toutes les machines hôtes |
| `entier_128` (aussi `petuar`) | 128 | `5LL` | entier de 128 bits (64 quits), complément à quatre pour les signés ; une instruction du SPU-128 |
| `entier_32` | 32 | `5S` | dans le quart bas d'un registre |
| `flottant` | 128 | `1.5` | **le flottant quaternaire** (l'ancien `flottant_petuar`, devenu natif) : 1 quit d'état, 7 quits d'exposant, 56 quits de mantisse |
| `flottant_64` | 64 | `1.5D` | le flottant quaternaire du SPU-64 (1 quit d'état, 5 d'exposant, 26 de mantisse) |
| `flottant_32` | 32 | `1.5S` | le flottant quaternaire de 32 bits du SPU-64 |
| `point` | 128 | `#…_…_…_…`, `matiere(r, v, b, reflet, lumiere, transparence, profondeur, rugosite)` | le point de matière |
| `logique` | 2 bits | `vrai faux inconnu variable` | Belnap, inchangé |

**Le flottant par défaut.** C'est le flottant quaternaire de 128 bits, déjà défini et vérifié (`flottant_petuar` :
111 à 112 bits de précision, étendue 10^±4931, quatre états, arrondi exact au plus proche). Sur le SPU-32 et le SPU-64,
il était calculé par le prélude : de mille à quarante mille fois plus lent qu'un flottant natif. Sur le SPU-128, il
devient une instruction. Les implémentations existantes (le prélude, `tests/ref_petuar.py`) servent de référence :
le résultat de chaque opération est déjà connu.

**Les flottants des voies.** Une voie de 32 bits peut porter un `flottant_32` quaternaire : la couleur en HDR flottant
(un rouge plus lumineux que le blanc de l'écran, pour la lumière du feu). Les instructions vectorielles (section 4)
calculent les quatre voies d'un coup.

**L'échange avec l'IEEE** : `vers_ieee32/64/128` et `de_ieee32/64/128`, comme aujourd'hui.

**L'entier par défaut reste de 64 bits** (décidé, pour la rapidité). Les processeurs hôtes calculent nativement sur
64 bits ; sur 128, l'addition coûte deux instructions, la multiplication trois ou quatre, la division bien plus (un
appel de fonction), et chaque valeur prend deux fois plus de place en mémoire et dans le cache. Compteurs, indices,
tailles : 64 bits suffisent toujours. Le 128 est là pour ce qui en a besoin : les points de matière, le flottant
quaternaire, l'ADN de 64 bases, les grands nombres. Un entier de 64 bits occupe la moitié basse d'un registre ou d'un
mot ; plus tard, un tableau d'entiers de 64 bits pourra en ranger deux par mot.

## 4. Le jeu d'instructions

**Le mot d'instruction porte deux instructions** (décidé) : la double hélice du code. Une instruction du SPU-128
garde le format du SPU-64 (64 bits : opération sur 16 bits, quatre registres, une valeur immédiate de 32 bits) ; un mot
de 128 bits en porte deux, jouées l'une après l'autre. Le code est aussi dense qu'au SPU-64, et le mot reste lisible
en hex, en quits et en ADN. Un saut vise une demi-instruction (l'indice du mot × 2 + la moitié).

- **16 registres de 128 bits** ; R0 vaut 0.
- **Entiers** : les opérations du SPU-64, élargies à 128 bits (64 quits), plus les formes 64 et 32 bits.
- **Quaternaire sur 64 quits** : MIN, MAX, ADDM4, QEGAL, COMPTE, ET4, OU4, NON4, ANTI, EXQ, LDQ, STQ. Un mot compare
  64 bases d'ADN d'un coup, deux fois plus qu'au SPU-64.
- **Flottants** : FADD, FSUB, FMUL, FDIV, FSQRT, FCMP, FNEG, FETAT, les conversions, pour les trois tailles.
- **Les voies** (nouveau) : VADD, VSUB, VMUL, VMIN, VMAX sur les quatre voies de 32 bits (entiers ou `flottant_32`),
  GDOT sur les voies, et le mélange de deux points de matière (MELANGE : la couleur pondérée, chaque codon de matière
  pondéré, l'état par la logique de Belnap).
- **La matière** : MATIERE (lire ou écrire un codon), ETAT (le quit d'état d'un point), ANTIPOINT (l'anti-cube : la
  symétrie par le gris du centre, sur la couleur et la matière).
- **Mémoire, pile, sauts, entrées et sorties, brin** : comme au SPU-64, avec l'adresse de la section 2.

## 5. Ce que le 64 a apporté, inscrit dans le 128

**Fiabilité.**
- **Le brin de chaque mot** (libre, ADN fixé, ARN en travail) : une écriture dans un mot ADN est refusée par la machine.
- **Les cubes sur disque** avec leur anti-cube (miroir inversé par la symétrie du centre) et leur ombre ;
  `etat_disque()` rend l'état de Belnap de la relecture.
- **La triangulation** (idée du créateur) : chaque point a trois témoins indépendants : sa place (la couleur dans le
  cube), son contenu, et l'ombre au-dehors. S'y ajoute un quatrième : la matière prévue par la place (la lumière et le
  reflet se rassemblent vers le blanc, la profondeur vers le noir). Un point qui contredit sa place, son ombre ou sa
  prévision est suspect, et se vérifie par les autres.
- **L'état dans chaque point** : une mémoire jamais écrite est *inconnue*, une contradiction est *variable* ; une erreur
  ne se cache plus derrière une valeur ordinaire.

**Cohérence.**
- Deux machines (Python de référence, Rust rapide) qui donnent, pour tout programme, les mêmes sorties, le même nombre
  d'instructions et la même mémoire ; un corpus de conformité 128 bits.
- Deux compilateurs (vtx128.py de référence, vtxc128 écrit en vtx) qui donnent les mêmes mots.
- La forge, qui transcrit l'ADN du programme en ARN natif, avec le même sens que la machine.

**Autonomie.**
- vtxc128 se compile lui-même (point fixe), embarqué dans vtx.exe ; la forge portée dans vtxc128, pour que
  `vtx forger` n'ait besoin que de rustc.
- Plus tard, le générateur x86-64 propre, comparé à la forge.

**Calcul.**
- Le flottant quaternaire de 128 bits devient une instruction (au lieu de milliers).
- Les voies calculées ensemble (quatre opérations en une).
- L'ADN sur 64 bases par mot.

**Compression.**
- **Le code** : deux instructions par mot (section 4).
- **Les cubes** : la compression par blocs et palettes du dossier `compression/` (vide, uniforme, 4 ou 16 couleurs,
  brut ; la forme rangée ADN, la forme de travail ARN), élargie aux points de matière.
- **La prévision par la place** (nouveau) : la matière prévue à partir de la couleur, et seul l'écart rangé ; un point
  qui suit la prévision ne coûte presque rien, une exception coûte quelques bits de plus (un piano noir laqué : sombre et
  très réfléchissant). À mesurer d'abord sur nos scènes (le feu de camp, les textures du labyrinthe) avant d'en fixer
  le format.
- **Le 256 rangé en 128** : une valeur de 256 bits (64 bits par voie) peut tenir en 128 bits quand elle est prévisible
  (prévision et écart), sinon elle garde ses 256 bits. Honnêtement : aucune compression sans perte ne garantit le
  rapport de deux pour un sur des données quelconques ; la machine doit toujours pouvoir revenir à la forme pleine.

## 6. La performance (ensuite)

- **La forge vers le 128** : le mot de 128 bits est un entier natif de Rust (u128) et tient dans un registre vectoriel
  du processeur (SSE2 sur x86, NEON sur ARM, présents partout) ; les voies se calculent avec les instructions
  vectorielles.
- **Le flottant quaternaire natif** : de l'ordre de dix à cinquante instructions de la machine hôte par opération (au
  lieu de milliers aujourd'hui) ; à mesurer, et à comparer au binary128 logiciel des autres langages.
- **La fiche des performances** refaite sur le 128, face au C, à Rust et aux autres.

## 7. Ordre de travail

1. Valider ce document : le partage de la voie de matière, l'adresse, les types par défaut, les deux instructions par
   mot, les noms.
2. La spécification exacte (`specification-spu128.md`), puis les machines SPU-128 Python et Rust, avec leur corpus de
   conformité.
3. Le compilateur de référence vtx128.py, puis vtxc128 (mêmes mots) et son point fixe.
4. La fiabilité (brin, miroir, ombre, triangulation) et la compression (blocs et palettes, prévision).
5. Gobatix et l'atelier sur le SPU-128 (les points de matière dans la vue, la peinture de la matière).
6. La forge sur le SPU-128, puis la performance et la fiche.

Le SPU-32 reste tel quel, gelé, avec ses 487 programmes de conformité ; le SPU-64 reste la configuration minimale,
toujours vérifiée. C'est un chantier de plusieurs séances, chacune vérifiée.

## 8. Décisions du 25 octobre (midi)

1. **La voie de matière** : l'état puis cinq codons de 64 degrés (le plus efficace, et le mot garde ses 32 chiffres hex :
   la voie se lit par groupes de 2, 3 et 3 chiffres). La répartition pourra être revue après la mesure de la prévision
   (section 5).
2. **L'adresse** : celle du SPU-64, élargie (section 2).
3. **L'entier par défaut** : 64 bits, pour la rapidité ; le 128 au choix (section 3).
4. **Deux instructions par mot** : oui (section 4).
5. **Les noms** : un nom gaulois pour chaque SPU (section 9).

## 9. Les noms gaulois des machines (hommage, formes à valider avec un spécialiste)

| Machine | Nom | Sens | Pourquoi |
|---|---|---|---|
| SPU-32 | **Senos** | vieux, ancien (dans les noms de lieu comme *Senomagos*) | la machine gelée, gardée pour la mémoire des anciens programmes |
| SPU-64 | **Dunon** | la forteresse, l'enceinte (Lug*dunum*, Ver*dun*) | le socle, la configuration minimale |
| SPU-128 | **Lugus** | le dieu de la lumière et de tous les arts | la machine de la lumière et de la matière ; et *Lugdunum*, « la forteresse de Lug », Lyon : Lugus bâti sur Dunon |
| SPU-256 (plus tard) | **Albios** | le monde lumineux, le blanc (dans *Albiorix*, « roi du monde ») | le pôle blanc du cube, la profondeur la plus grande |
