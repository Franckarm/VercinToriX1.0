# SPU-64 et Gobatix : conception (à valider avant tout code)

*23 octobre 2026. Décisions du créateur : la logique de Belnap est gardée (inconnu 0, faux 1, vrai 2, variable 3) ; le mot du SPU passe à 64 bits ; les cubes qui s'additionnent par fréquences utilisent une adresse longue de 64 bits ; Gobatix commence par un cube vide, zone de modélisation, de texture et de peinture, repérée en xyz hexadécimal. Pas de précipitation : ce document fixe le cap, rien n'est encore codé.*

*Décisions de l'après-midi : le SPU-64 se fait **avant** l'atelier en vtx (l'atelier sera écrit pour le SPU-64) ; **les tailles 32, 64 et 128 bits sont toutes quaternaires** (entiers et flottants) ; les machines JavaScript ne sont pas portées ; le modeleur (Gobatix, orthographe à confirmer) est le même programme que Coatvtx ; T (l'ADN) est le résultat fixé, U (l'ARN) le travail : section 7.*

## 0. Ce qui reste gravé

Cube chromatique (la mémoire est le cube des couleurs, écrite en hex), quaternaire (deux quits par chiffre hex), ADN/ARN (A C G T/U). Le passage à 64 bits double le point ; il ne change aucune de ces trois lectures.

## 1. Le mot de 64 bits : le point profond

| | SPU-32 (aujourd'hui) | SPU-64 |
|---|---|---|
| Écriture | `#RRGGBBAA` | `#RRRRGGGGBBBBAAAA` |
| Voies | 4 × 8 bits | 4 × 16 bits (couleur profonde, 65 536 niveaux par voie) |
| Quits / bases | 16 | 32 |
| Chiffres hex | 8 | 16 |

Le point de 32 bits est l'octet fort de chaque voie : `#3A7F1C80` devient `#3A007F001C008000`. Une image ou une texture garde donc ses couleurs, et y gagne la profondeur (HDR).

## 2. L'adresse longue (les cubes qui s'additionnent)

Une adresse est un mot de 64 bits :

| Bits | Champ | Sens |
|---|---|---|
| 63 à 48 (`AAAA`, 8 quits) | étage (1 quit), type (1 quit : donnée, instruction, adresse, contrôle), 6 quits réservés | |
| 47 à 24 | fréquence (24 bits) | quel cube : 16 millions de cubes par étage |
| 23 à 0 | `#RRGGBB` | le point dans le cube : x = RR, y = GG, z = BB |

- Plus besoin d'`accorder` pour lire un autre cube : un pointeur porte sa fréquence. Un pointeur vaut donc dans tous les cubes, ce qui lève la contrainte la plus gênante d'aujourd'hui.
- La mémoire reste en pages de 65 536 points créées à la première écriture : un cube jamais écrit ne coûte rien, et l'espace d'adresses (2^48 points par étage) n'est pas de la mémoire réservée.
- Les cubes rangés sur disque gardent leur fichier `cube-ÉTAGE-FRÉQUENCE.cub`. Nouveauté proposée : une page n'est lue sur disque qu'à son premier accès, pour qu'un modèle de 16 Go se parcoure sans être chargé entier.
- Le pointeur nul porte l'état *inconnu* : une adresse qui vaut 0 n'a jamais été donnée.

## 3. Les nombres

**Par défaut, dans l'atelier** : `soit x = 5;` donne un entier de 64 bits, et `1.5` un flottant quaternaire de 64 bits. Les tailles 32 et 128 s'écrivent à la main.

| Type | Taille | Écriture | Format |
|---|---|---|---|
| `entier` | 64 | `5` | entier de 64 bits (32 quits) |
| `entier_32`, `entier_petuar` | 32, 128 | proposé : `5S` (« simple »), `5LL` | |
| `flottant` | 64 | `1.5` | **quaternaire** : 1 quit d'état, 5 quits d'exposant (biais 512), 26 quits de mantisse |
| `flottant_32` | 32 | proposé : `1.5S` | **quaternaire** : 1 quit d'état, 4 quits d'exposant, 11 quits de mantisse |
| `flottant_petuar` | 128 | `1.5Q` | déjà fait : 1 quit d'état, 7 d'exposant, 56 de mantisse |
| `logique` | 2 bits | | Belnap, inchangé |

- **Le flottant de 64 bits.** L'état et l'exposant (6 quits) remplissent exactement les 3 premiers chiffres hex, et la mantisse 13 chiffres hex. Précision : 51 à 52 bits (environ 15,5 chiffres, contre 53 bits pour l'IEEE), étendue d'environ 10^±308. Mêmes quatre états qu'au petuar : une mémoire nulle est *inconnue*, 0/0 est *variable*.
- **Correction honnête sur le 32 bits quaternaire** : il a 21 à 22 bits de précision (environ 6,5 chiffres), contre 24 pour l'IEEE, et une étendue d'environ 10^±76. Il ne sert qu'à économiser de la place.
- **L'IEEE** reste pour l'échange : `vers_ieee64`, `de_ieee64`, `vers_ieee128`… Les suffixes `D` et le flottant binary32 actuel disparaissent du SPU-64.
- **Les entiers sont déjà quaternaires** : un entier de 32, 64 ou 128 bits est exactement 16, 32 ou 64 chiffres en base 4, et l'addition, la soustraction et la multiplication binaires sont les mêmes que chiffre par chiffre en base 4 (complément à quatre pour les négatifs). Le SPU-64 les montre ainsi : `0q…` en écriture, quits et ADN en lecture.

## 4. Le jeu d'instructions

- Une instruction est un point profond de 64 bits :
  - `RRRR` : l'opération (16 bits, de la place pour des familles entières) ;
  - `GGGG` : les registres, 4 champs de 4 bits ;
  - `BBBB` et `AAAA` : une valeur immédiate de 32 bits (fini la plupart des `LDI`).
- 16 registres de 64 bits ; R0 vaut 0.
- **Les opérations quaternaires deviennent des instructions** :
  - flottants quaternaires de 64 bits (addition, soustraction, multiplication, division, racine, comparaison) ;
  - Belnap sur 32 quits à la fois (ET4, OU4…) ;
  - LDQ et STQ ;
  - lecture et écriture par adresse longue.

  La machine Rust les calcule avec les entiers natifs de 64 et 128 bits : le flottant par défaut passe de milliers d'instructions à une seule.
- Le flottant_petuar garde le prélude au début ; ses instructions viendront ensuite.

## 5. Compatibilité et ordre de travail

Le SPU-32 actuel reste tel quel, figé : les programmes 0.4, ses 487 programmes de conformité et `natif/`, que je ne touche pas. Le SPU-64 est une machine nouvelle, construite à côté :

1. Valider ce document (formats, noms des types, écriture des littéraux). **Fait** (23 octobre).
2. Les machines SPU-64 Python et Rust, avec un corpus de conformité 64 bits. **Fait** : `docs/specification-spu64.md`, `spu64/`, `vtx64`.
3. Les deux compilateurs : une génération de code 64 bits (vtx.py, puis vtxc, avec les mêmes mots), les types par défaut de 64 bits.
4. vtxc se recompile lui-même sur le SPU-64 (point fixe), puis est embarqué dans vtx.exe.
5. L'atelier : le cube en points profonds, le pas à pas sur 64 bits, les tailles 32 et 128 au choix.
6. (Les machines JavaScript ne sont pas portées : décision du 23 octobre.)

C'est le chantier le plus lourd depuis l'autonomie : plusieurs séances, chacune vérifiée.

## 6. Gobatix : la zone de modélisation

- **Un cube vide** (un cube de mémoire à une fréquence) est la zone de travail : 256 × 256 × 256 cases. **La position d'une case est son adresse `#XXYYZZ`** : x = RR, y = GG, z = BB, en hexadécimal.
- **Ce que la case contient** : un point profond `#RRRRGGGGBBBBAAAA`.
  - La couleur (peinture, texture), en 16 bits par voie.
  - L'alpha : la case est-elle pleine, et de quelle matière. Proposition : le premier quit d'alpha porte l'état de Belnap, avec *inconnu* = vide (jamais touché), vrai = matière, faux = creusé, variable = en conflit entre deux opérations.
- **Modéliser**, c'est remplir ou vider des cases. **Peindre**, c'est changer leur couleur. **Une texture** est une tranche du cube (z fixe) : modèle et texture vivent dans le même cube.
- **Dans l'atelier** : une vue 3D de la zone qu'on tourne, un pinceau (remplir, creuser, peindre), le repère affiché en hex, et la même zone lisible quit par quit et en ADN.
- **Sur le SPU** : un programme vtx écrit le même cube (`zone[#102030] = couleur`), donc on modélise aussi par le code. L'atelier et le programme partagent le cube.
- Plus tard :
  - le maillage (extraire la surface pour exporter en OBJ) ;
  - plusieurs zones additionnées par fréquences (des calques) ;
  - l'animation par le cube, comme pour Pégase.

**Premier pas proposé** : le cube vide dans l'atelier, avec remplir, creuser et peindre à la souris, la vue 3D et le repère hex. Il peut se faire sur le SPU-32 actuel (points de 32 bits), puis passer en points profonds avec le SPU-64.

## 7. T et U : l'ADN fixé, l'ARN de travail

Décidé : **T (ADN) est le résultat fixé, U (ARN) le travail.** La valeur du quit (3) est la même ; ce qui change, c'est le statut. Pour que la machine le sache, il faut un endroit où l'écrire : le mot de 64 bits en a un, l'alpha de l'adresse et des données.

Proposition, par ordre de profit :

1. **Le brin de chaque mot** (retenu ; correction : pas dans l'alpha, qu'un entier ou un flottant de 64 bits occupe, mais un quit de marque à côté de chaque mot) : libre, ADN (fixé), ARN (en travail). Une écriture dans un mot ADN est refusée par la machine : c'est une protection native. `fixer(x)` transcrit l'ARN en ADN (comme `valider` d'une hypothèse), et `copier_arn(x)` fait une copie de travail.
   - Profit pour la **partition des tâches** : des données ADN ne changent plus, donc toutes les tâches peuvent les lire en même temps sans preuve d'indépendance. Plus d'accords joués ensemble, sur plus de cœurs.
   - Profit pour le **compilateur** : une valeur ADN est une constante, qu'il peut propager et ranger une seule fois.
2. **Les cubes ARN par-dessus un cube ADN** (copie à l'écriture ; retenu à l'essai : le « cube de transfert jetable ») : un cube ARN ne garde que les pages modifiées d'un cube ADN de base, à une autre fréquence. Les usages :
   - les hypothèses (annuler, c'est jeter le cube ARN ; valider, c'est le fixer) ;
   - Gobatix (calques, historique d'annulation, essais de peinture sans toucher au modèle) ;
   - le ScoR (l'ARN comme copie de travail, déjà dans son principe).
   C'est l'usage le plus profitable pour accélérer : une annulation coûte une page, pas une copie du cube.
3. **La brume** (écartée le 23 octobre) : un résultat calculé d'avance sur les deux branches d'un `si` (sur deux cylindres) reste ARN, donc en brume, jusqu'à ce que la condition soit connue, puis une branche est fixée en ADN et l'autre oubliée. C'est l'exécution spéculative des processeurs, rendue visible et vérifiable dans le langage. À ne tenter qu'après le SPU-64 de base.
4. **La signature de l'auteur** : dans un programme ou un cube fixé, le choix T ou U sur les quits qui valent 3 porte un bit caché par quit, sans changer aucune valeur. Il y a la place de signer un cube (environ un quart des quits). Honnêtement : c'est un filigrane, pas une protection forte. Une vraie signature passe par une clé (un code d'authentification calculé avec une clé secrète) ; le filigrane T/U peut la porter discrètement. Utile pour la mention « pas touche » de ton œuvre.

Ce qui ne marcherait pas : faire porter à U une information de calcul en plus (un « sous-code » qui accélère les opérations). Le bit T/U ne vit que sur les quits à 3. Il ne double pas la capacité et ne fait pas aller les calculs plus vite. Son vrai gain est le statut (fixé ou en travail), pas la quantité d'information.

