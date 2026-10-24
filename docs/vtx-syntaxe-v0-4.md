# Vercintorix (vtx) : référence du langage, version 0.4

Cette référence remplace la syntaxe v0.1. Tout ce qui est décrit ici est implémenté dans `vtx.py` et vérifié par ses tests ; les limites sont listées à la fin.

## 1. Principes

- **Gravé, immuable : le cube chromatique, le quaternaire, l'ADN et l'ARN.** La mémoire est le cube des couleurs : chaque mot est un point `#RRGGBBAA`, écrit en hexadécimal, chaque étage un cube de 256³ points. Toute valeur se lit aussi en quits (deux par chiffre hex) et en bases (A = 0, C = 1, G = 2, T/U = 3, l'ARN écrit U). Un type de plusieurs mots est une suite de points du cube : `flottant_petuar` et `entier_petuar` en prennent quatre (32 chiffres hex, 64 quits, 64 bases). Une nouveauté du langage qui ne respecte pas ces trois lectures n'entre pas.
- Un programme vtx se compile vers le jeu d'instructions du SPU à cube chromatique ; chaque mot est un point `#RRGGBBAA` du cube (quatre voies de 8 bits, seize quits).
- Trois types : `entier` (le mot de 32 bits non signé, type par défaut), `flottant` (IEEE 754 binary32), `long` (entier signé de 64 bits, deux mots).
- Les mots-clés sont en français. Les identifiants peuvent contenir des lettres accentuées.
- Un même programme donne les mêmes sorties, le même nombre d'instructions et la même mémoire sur toutes les machines de référence (Python, Java, JavaScript interprété, JavaScript traduit).

## 2. Éléments lexicaux

**Commentaires** : `// jusqu'à la fin de la ligne`.

**Mots-clés** : `fonction soit si sinon tantque retour constante pour dans donnees arrêter continuer hypothèse annuler valider`, ainsi que `structure`, `tableau`, `de`, `par` et `importer` à leur place.

**Alias** : `et` `ou` `non` pour `&&` `||` `!` ; `entree` pour `entrée` ; `données` pour `donnees` ; `arreter` pour `arrêter` ; `hypothese` pour `hypothèse`.

**Constantes prédéfinies** : `vrai` (1), `faux` (0), `CPU` (0), `GPU` (1), `PARTAGE` (2), `DISQUE` (3).

| Littéral | Exemple | Type et valeur |
|---|---|---|
| Décimal | `1_000` | entier |
| Hexadécimal | `0xFF` | entier |
| Base 4 | `0q0123` | entier (un chiffre par quit) |
| Couleur | `#3A7F1C` ou `#3A7F1C80` | entier `#RRGGBBAA` (alpha 0 si absent) |
| ADN | `adn"GATTACA"` | entier, 1 à 16 lettres : A = 0, C = 1, G = 2, T = U = 3, la première lettre au poids fort ; de 17 à 64 lettres, un `entier_petuar` |
| Quatre points du cube | `#4000921F_B54442D1_8469898C_C51701B8` | `entier_petuar` : quatre points `#RRGGBBAA`, le plus fort d'abord (32 chiffres hex) |
| Flottant quaternaire | `1.5Q`, `2.5e-3000Q` | `flottant_petuar`, lu exactement (arrondi au plus proche, pair au milieu) |
| Flottant | `1.5`, `2e3`, `3.1415927` | flottant (arrondi au binary32 le plus proche) |
| Long | `5L`, `0xFFFF_FFFF_FFFFL` | long (jusqu'à 2^64 − 1) |

## 3. Types et conversions

| | entier | flottant | long |
|---|---|---|---|
| Taille | 1 mot | 1 mot | 2 mots (bas, haut) |
| Arithmétique | modulo 2^32, non signée | IEEE binary32, arrondi au plus proche pair | complément à deux sur 64 bits |
| Division par zéro | `x / 0` = 0xFFFFFFFF, `x % 0` = x | infini ou NaN (IEEE) | `x / 0` = −1, `x % 0` = x |
| Division | entière, non signée (`./` et `.%` : signées) | IEEE | tronquée vers zéro, reste du signe du dividende |
| Comparaisons | non signées (`.<` `.<=` `.>` `.>=` : signées) | IEEE (NaN n'est égal à rien) | signées |

**Conversions implicites** : un entier mélangé à un flottant devient flottant ; un entier mélangé à un long devient long (sans signe). Aucune autre conversion n'est implicite : mélanger un flottant et un long, ou ranger un flottant dans un entier, est une erreur de compilation qui indique la fonction à utiliser.

| Fonction | Effet |
|---|---|
| `flottant(x)` | entier non signé vers flottant |
| `flottant_signe(x)` | entier lu en complément à deux vers flottant |
| `entier(x)` | flottant vers entier signé, tronqué vers zéro, saturé (NaN donne 0) ; long vers son mot bas |
| `arrondi(x)` | flottant vers entier signé, au plus proche pair, saturé |
| `long(x)` | entier non signé vers long |
| `long_signe(x)` | entier en complément à deux vers long |
| `long_de(haut, bas)` | long à partir de deux mots |
| `bas(x)`, `haut(x)` | mots d'un long |
| `bits(x)` | les 32 bits d'un flottant, comme entier |
| `comme_flottant(x)` | un entier lu comme les 32 bits d'un flottant |

### Les types larges : `entier_64`, `flottant_64`, `entier_128`

| | `entier_64` | `flottant_64` | `entier_128` |
|---|---|---|---|
| Écriture | `5L` ; type `long` ou `entier_64` | `1.5D`, `2.5e-3D` ; type `flottant_64` | `5LL` ; type `entier_128` (alias gaulois `petuar`, « quatre », parce qu'il tient en quatre mots) |
| Taille, registres | 2 mots : R1 (bas) et R4 (haut) | 2 mots : R1 et R4 | 4 mots : R1, R3, R4, R6 (le mot bas d'abord) |
| Arithmétique | complément à deux sur 64 bits | IEEE binary64, arrondi au plus proche pair, NaN canonique | complément à deux sur 128 bits |
| Opérateurs | `+ - * / % & \| ^ << >>`, comparaisons signées | `+ - * /`, comparaisons IEEE | `+ - & \| ^ ~` et comparaisons en ligne ; `* / % << >>`, `abs`, `min`, `max` par le prélude |
| Comparaisons | signées | IEEE (NaN n'est égal à rien) | signées ; `>>` arithmétique |

Aucune conversion implicite entre ces types (sauf : un entier de 32 bits s'élargit en `entier_64` ou `entier_128`, sans signe) ; chaque mélange est une erreur de compilation qui nomme la fonction à utiliser. Fonctions : `flottant_64(x)` (depuis un entier, un `long`, un flottant ou un `entier_128`), `flottant_64_signe`, `flottant_64_de(haut, bas)`, `comme_flottant_64(x)` (un long lu comme les 64 bits d'un flottant), `entier(x)` et `arrondi(x)` (de 64 bits vers 32, saturés), `long(x)`, `arrondi_long(x)`, `bas(x)` et `haut(x)` (les deux moitiés d'un `entier_64` ou d'un `flottant_64` ; sur un `entier_128`, les deux moitiés de 64 bits), `entier_128(x)` (non signé depuis un entier de 32 bits, signé depuis un long), `entier_128_signe(x)`, `entier_128_de(haut, bas)` (deux longs). Les instructions du SPU sont les opcodes 0x5B à 0x6B (91 à 107) sur des paires de registres ; l'`entier_128` n'a pas d'instruction propre : quatre mots avec retenue (`ADC`, `SBC`) et des fonctions du prélude.

`afficher` écrit un `flottant_64` avec le plus court décimal qui se relit exactement (Dragon4 exact, mêmes chiffres que `repr` de Python) et un `entier_128` en décimal signé. Les fonctions mathématiques ont leur version 64 bits, tirée de fdlibm : `sinus_64 cosinus_64 tangente_64 exponentielle_64 logarithme_64 puissance_64 arctangente_64 arcsinus_64 arccosinus_64 plancher_64 plafond_64 pi_64`, et `racine`, `abs`, `min`, `max` acceptent les `flottant_64`. Exemples : `exemples/flottant64/` (`precision`, `mandelbrot64`, `newton64`) et `exemples/entier128/` (factorielles, Fibonacci(180), comparaisons).

### Le flottant quaternaire : `flottant_petuar` (128 bits)

Le flottant propre à Vercintorix. *Petuar* est « quatre » en gaulois (comme dans Petrocorii, « les quatre troupes », qui a donné le Périgord) : il tient en quatre points du cube, et tout en lui est quaternaire. Alias : `flottant_128`. Un `entier_petuar` (alias de `entier_128`, et de `petuar`) a la même taille.

| Quits | Chiffres hex | Contenu |
|---|---|---|
| 63 | le premier, ses deux bits forts | **l'état**, en logique de Belnap : `A` (0) inconnu, `C` (1) négatif, `G` (2) positif, `T`/`U` (3) variable |
| 62 à 56 | la fin du premier, puis les trois suivants | **l'exposant**, 7 quits en base 4, biais 8192 ; 16383 : l'infini |
| 55 à 0 | les 28 derniers | **la mantisse**, 56 chiffres en base 4 ; le premier n'est pas nul (sauf à l'exposant 0 : les sous-normaux) |

Valeur : mantisse × 4^(exposant − 8247). L'état et l'exposant tombent exactement sur les quatre premiers chiffres hex (le `RRGG` du point fort), la mantisse sur des chiffres hex entiers : arrondir au quit près, c'est arrondir au demi-chiffre hex. Précision : 111 à 112 bits (environ 34 chiffres décimaux ; en base 4 il n'y a pas de bit caché, le binary128 de l'IEEE en a 113). Étendue : de 10^−4964 (sous-normaux) à 1,19 × 10^4931. Exemples : `1Q` = `#A0004000_00000000_00000000_00000000` = `GGAAAAAACAAAA…` ; `1Q / 3Q` a pour mantisse `CCCC…C` (en base 4, un tiers vaut exactement 0,1111…) ; π = `#A000C90F_DAA22168_C234C4C6_628B80DC`.

**Les quatre états.** *Inconnu* : le nombre n'a pas été calculé (une mémoire jamais écrite est inconnue : quatre points nuls). *Variable* : contradiction (`0/0`, ∞ − ∞, 0 × ∞, racine d'un négatif) ; l'IEEE confond ces deux cas dans un seul NaN. Dans un calcul, variable l'emporte sur inconnu, inconnu sur un nombre. Une comparaison avec un état inconnu ou variable est fausse (dans les deux sens). Un `flottant_petuar` ne sert pas de condition (`si x` est refusé) : on le compare, ou on demande `etat(x)`, un `logique` (inconnu, faux = négatif, vrai = positif, variable) : `selon etat(x) { vrai { } faux { } inconnu { } variable { } }`.

**Opérations.** `+ - * /`, l'opposé, les six comparaisons, `racine`, `abs`, `min`, `max`, arrondis exactement au plus proche (pair au milieu), sur toutes les machines ; tout est écrit en vtx dans le prélude, sans instruction nouvelle du SPU. Un entier, un flottant ou un `flottant_64` s'élargit tout seul en `flottant_petuar` ; un `long` ou un `entier_petuar` se convertit avec `flottant_petuar(x)`. Vers les autres types : `flottant_64(x)`, `flottant(x)` (un seul arrondi), `entier_128(x)` (tronqué vers zéro, saturé), `long(x)` et `entier(x)` (les bits bas de `entier_128(x)`), `bits(x)` (les quatre points, comme un `entier_petuar`) et `comme_flottant_petuar(w)`. Échange avec le binary128 de l'IEEE 754 (les fichiers et les autres langages) : `vers_ieee128(x)` (exact) et `de_ieee128(w)` (arrondi à 111 ou 112 bits). `pi_petuar()`, `inconnu_petuar()`, `variable_petuar()`. `afficher` écrit les chiffres les plus courts qui redonnent exactement le nombre, ou `inconnu`, `variable`, `inf`.

**Les trois lectures d'une valeur de quatre points.** `texte_cube(w)` : `#RRGGBBAA_RRGGBBAA_RRGGBBAA_RRGGBBAA` ; `texte_adn(w)` : 64 bases, le quit 63 d'abord ; `texte_arn(w)` : la même avec U. Pour un flottant : `texte_adn(bits(x))`.

**Coût** (instructions du SPU, machine Rust : environ 300 millions par seconde) : addition 1 800, multiplication 3 400, division 19 000, racine 44 000 ; un `flottant_64` fait une opération en une instruction. Exemples : `exemples/petuar/` (`decouverte`, `quatre_etats`, `pi_machin`).

**Choix de la précision.** Le type écrit fixe la précision, variable par variable ; il n'y a pas de précision globale : `entier` reste de 32 bits parce que les adresses, les indices de tableaux, les registres et les mots du cube le sont. Passer *tout* en 64 bits doublerait les registres et la pile, ferait perdre les variables en registres (R9 à R12) et obligerait à convertir chaque indice. Un `soit x: flottant_64 = …` n'est pas plus long à écrire qu'un `soit x = …`, et le compilateur refuse chaque mélange.

Un flottant écrit en mémoire (`@2[0] = 1.5;`) y range ses 32 bits ; on le relit avec `comme_flottant(@2[0])`. Un long occupe deux mots : il s'écrit avec `bas(x)` et `haut(x)`.

## 4. Expressions

Priorités, de la plus faible à la plus forte (comme en Rust, le bit à bit lie plus fort que les comparaisons) :

| Niveau | Opérateurs |
|---|---|
| 1 | `\|\|` (court-circuit) |
| 2 | `&&` (court-circuit) |
| 3 | `==` `!=` `<` `<=` `>` `>=` `.<` `.<=` `.>` `.>=` |
| 4 | `\|` |
| 5 | `^` |
| 6 | `&` |
| 7 | `<<` `>>` `<<q` `>>q` (décalage d'un quit, soit 2 bits) `.>>` (décalage arithmétique) |
| 8 | `+` `-` |
| 9 | `*` `/` `%` `./` `.%` |
| 10 | unaires `-` `~` `!` |
| 11 | accès : `.r` `.v` `.b` `.a` (voies du mot), `.q(i)` (quit i), appels `f(…)`, mémoire `@e[a]` et `@(e)[a]`, tableaux `t[i]` et `t[i].champ` |

Selon le type : `%`, `&`, `|`, `^`, `~` et les décalages ne s'appliquent pas aux flottants ; les voies et les quits s'appliquent aux entiers. Dans une condition, un flottant est vrai s'il n'est pas ±0, un long s'il n'est pas nul. Une comparaison rend 0 ou 1.

## 5. Instructions

```
soit x = 3;                    // type déduit de la valeur
soit v: flottant = 0;          // type déclaré, la valeur est convertie
x = x + 1;
@2[10] = x;                    // écriture dans l'étage 2
@(e)[a] = x;                   // étage calculé
t[i].x = 5;                    // case de tableau, champ de structure
si c { … } sinon si d { … } sinon { … }
tantque c { … }
pour i dans 0..10 { … }        // borne haute exclue, pas de 1
pour i dans 0..10 par 3 { … }
pour i dans 0..4096 en segments { … }     // découpée en 12 segments (6 cylindres x 2 temps), joués ensemble s'ils sont indépendants
pour i dans 0..4096 en 18 segments { … }  // 6 cylindres x 3 temps ; au plus 18, arrondi au multiple de 6
pour i dans 0..4096 en segments cumulant histo { histo[g] = histo[g] + 1; }  // une copie de histo par segment
arrêter;  continuer;
retour v;
hypothèse { …  annuler;  …  valider; … }
```

**Hypothèse** : les écritures mémoire écrites dans le bloc sont notées dans un journal ; `annuler;` les défait et sort du bloc ; `valider;` ou la fin du bloc les garde. Les blocs s'imbriquent. Les variables locales et les écritures faites par les fonctions appelées ne sont pas défaites ; `retour`, `arrêter` et `continuer` ne peuvent pas sortir d'une hypothèse ; l'étage 0 y est interdit.

## 6. Déclarations

```
importer "bibliotheque/cube.vtx";          // inséré une seule fois
constante N = 16;  constante PI = 3.1415927;  constante GRAND = 5000000000L;
donnees @1[0] = { 1, 2, #FF0000FF, adn"ACGT", 0.5 };
structure Point { x; y; }
tableau pts[8] de Point @PARTAGE[100];     // indice constant vérifié à la compilation
tableau v[16] @2[0];
tableau adn[65536] de quits @1[0];        // 16 quits par mot (4 096 mots) ; adn[i] lit ou écrit un quit
tableau mots_adn[4096] @1[0];             // le même endroit vu mot par mot : 16 bases d'un coup
tableau etats[1000] de logique @2[0];     // 16 logiques par mot
fonction moyenne(a: flottant, b: flottant): flottant { retour (a + b) / 2.0; }
fonction principal() { … }                 // point d'entrée, sans paramètre
```

**Tableaux de quits et de logiques.** `de quits` range 16 valeurs de 0 à 3 par mot, `de logique` 16 logiques par mot : 16 fois moins de mémoire. `t[i]` lit ou écrit un seul élément (le compilateur calcule le mot `i / 16` et la place `i mod 16`) ; c'est commode, mais plus lent qu'un tableau ordinaire. Pour traiter 16 éléments d'un coup, on déclare un second tableau ordinaire au même endroit et on travaille mot par mot (`qegal`, `nb_bits`, `fusion`…). **Réécriture automatique, 16 éléments d'un coup.** Une boucle écrite élément par élément,
```
pour i dans 0..4096 { etat[i] = fusion(capteur_a[i], capteur_b[i]); }
```
est réécrite par le compilateur pour traiter un mot entier, donc 16 éléments, à chaque tour, quand trois conditions sont réunies : la boucle avance de 1 en 1 et ne contient que des écritures `T[i] = …` dans des tableaux rangés de même sorte ; chaque valeur ne lit que des éléments d'indice `i` exactement, et des constantes ; elle n'utilise que des opérations quit par quit (`et4`, `ou4`, `non4`, `anti`, `fusion`, `consensus` pour les logiques ; `min4`, `max4`, `addm4`, `cmp3`, `qegal`, `&`, `|`, `^` pour les quits). Les boucles qui comptent (`si a[i] == b[i] { n = n + 1; }`, ou `!=`) et qui somment des quits (`n = n + t[i]`) sont réécrites aussi, avec `qegal` et `nb_bits`, si la valeur de chaque élément tient dans son quit (pas de `cmp3` ni de `qegal` dans une somme ou une comparaison, constantes de 0 à 3). Les éléments du début et de la fin qui ne remplissent pas un mot restent traités un par un. Sinon, la boucle est gardée telle quelle : le résultat est toujours le même. Gain mesuré : environ ×15 sur un tableau ordinaire. Pour compter : ×10,6.

L'indice d'un tableau rangé ne doit pas appeler de fonction ; un tableau rangé ne peut pas être cumulé, et des segments qui y écrivent sont joués l'un après l'autre (deux éléments voisins partagent un mot).

Les données sont rangées après le code et copiées une seule fois au démarrage. Les champs de structure et les cases de tableau sont des entiers (un mot).

## 6 ter. Texte, tas, références et canaux (vtx 0.5)

Ajouts pour que vtx puisse s'écrire lui-même (voir `vtx-0-5-autonomie.md`).

```
soit t = "Bonjour, Vercintorix !";        // texte : longueur, puis un caractère par mot
soit c = 'é';                             // caractère : son numéro Unicode (233)
structure Noeud { valeur, gauche: Noeud, droite: Noeud }   // champs typés : un champ peut désigner une structure
soit n = Noeud { valeur: 7 };              // bloc neuf pris sur le tas ; les champs non nommés valent nul
soit a = Noeud { valeur: 1, gauche: Noeud { valeur: 2 } };
n.valeur = 8;
fonction profondeur(n: Noeud) { si n == nul { retour 0; } … }
ecrire_texte(1, "fini\n");                // canal 1 : la console en texte
soit f = ouvrir_lecture("prog.vtx");      // canaux 2 et suivants : fichiers
tantque fin_de(f) == 0 { soit x = lire_car(f); … }
fermer(f);
```

- **Texte** : un littéral `"…"` est rangé après le code (longueur, puis un caractère par mot). Échappements `\n`, `\t`, `\\`, `\'`, `\"`, `\0`. Sa valeur est une adresse globale (l'étage dans les bits 24 et 25), comme toute référence.
- **Références** : une variable, un paramètre, un retour ou un champ déclaré avec un nom de structure contient l'adresse d'un bloc. `x.champ` lit et écrit le champ (`a.b.c = 1` marche aussi). On ne peut que comparer deux références de même structure (`==`, `!=`) ou une référence à `nul`.
- **Tas** : dans l'étage 3, de 8 388 608 à 14 680 048. `Structure { champ: valeur, … }`, `nouveau(n)` (n mots), `nouveau_de(Structure)` (comme `Structure {}`), `tas_marque()`, `tas_retour(m)` (rend d'un coup tout ce qui a été pris depuis la marque). Pas de libération mot à mot. `nouveau` rend `nul` quand le tas est plein.
- **Le type `texte`** : `soit t: texte = "abc";`, `fonction nom(): texte`, `structure P { nom: texte }`. Une variable initialisée par un texte est un texte (`soit t = "abc";`). Pour la machine, un texte reste une adresse (un mot).
  - `a + b` colle deux textes en un texte neuf, pris sur le tas. Si l'un des deux n'est pas un texte, il est d'abord écrit en texte : `"n = " + n` (entier signé), `"x = " + 1.5`, `"g = " + 5L`, `"l = " + fusion(vrai, faux)` (`variable`).
  - `a == b` et `a != b` comparent le contenu de deux textes (`texte_egal`). Un texte comparé à autre chose qu'un texte (`t == nul`) compare les adresses.
  - `texte(x)` : un entier (signé), un flottant, un long ou un logique écrit en texte. `nombre(t)` : un texte de chiffres (avec un `-` éventuel) vers un entier. `sous_texte(t, debut, fin)` (fin exclue), `position(t, motif)` (la première position, ou −1 = 4294967295).
  - Limite : un texte rangé dans un champ est reconnu si le champ est déclaré `texte` dans toutes les structures qui ont un champ de ce nom ; une case de tableau ou une case mémoire (`@3[a]`) n'est jamais un texte (passez par une variable déclarée texte).
- **Fonctions de texte** (prélude) : `longueur(t)`, `car(t, i)`, `changer_car(t, i, c)`, `texte_egal(a, b)`, `texte_neuf(n)`, `ecrire_texte(canal, t)`, `ecrire_nombre(canal, n)`, et `texte`, `nombre`, `sous_texte`, `position`.
- **Canaux** : `lire_car(canal)` et `ecrire_car(canal, x)` ; canal 0 = `entrée()` et `sortie()`, canal 1 = console en texte, 2 et suivants = fichiers ouverts par `ouvrir_lecture(nom)` ou `ouvrir_ecriture(nom)` (le canal, ou 4294967295 en cas d'échec), `fermer(canal)`, `fin_de(canal)` (1 quand tout est lu). Les fichiers sont ceux du dossier courant de la machine Rust ou Python ; les machines du navigateur n'y ont pas accès. Lire un canal vide rend 4294967295.

## 6 bis. Logique à quatre valeurs

Le type `logique` range une valeur de la logique de Belnap dans un quit : deux bits de preuve, *v* (une preuve que c'est vrai) et *f* (une preuve que c'est faux).

| Valeur | v | f | Code | Sens |
|---|---|---|---|---|
| `inconnu` | 0 | 0 | 0 | aucune preuve : en dehors du spectre vrai / faux |
| `faux` | 0 | 1 | 1 | |
| `vrai` | 1 | 0 | 2 | |
| `variable` | 1 | 1 | 3 | des preuves dans les deux sens : les témoignages se contredisent (le bruit) |

```
soit porte: logique = fusion(capteur_a, capteur_b);
selon porte {
    vrai { ouvrir(); }
    faux, inconnu { attendre(); }     // plusieurs valeurs par branche
    autre { alerter(); }              // les valeurs non nommées ; une branche absente ne fait rien
}
```

| Opération | Définition | Effet |
|---|---|---|
| `et4(a, b)` | v = v₁ ET v₂, f = f₁ OU f₂ | conjonction |
| `ou4(a, b)` | v = v₁ OU v₂, f = f₁ ET f₂ | disjonction |
| `non4(a)` | échange v et f | vrai ↔ faux ; inconnu et variable restent |
| `anti(a)` | v = NON f, f = NON v | inconnu ↔ variable ; vrai et faux restent (l'antimatière) |
| `fusion(a, b)` | v = v₁ OU v₂, f = f₁ OU f₂ | rassembler deux témoignages : vrai et faux donnent variable |
| `consensus(a, b)` | v = v₁ ET v₂, f = f₁ ET f₂ | ne garder que ce sur quoi les deux s'accordent |
| `logique(x)` | | entier → logique : 0 donne faux, le reste vrai |
| `comme_logique(x)` | | le code 0 à 3 lu comme un logique |
| `entier(p)` | | le code du logique (0 à 3) |

**16 logiques par mot.** Les opérations sont de simples ET et OU sur les deux bits de chaque quit : appliquées à des entiers, elles traitent d'un coup les 16 logiques rangés dans le mot (un par quit, le quit 0 en bas). Une seule instruction `OR` fusionne 16 paires de témoignages.

**Règles.** Un logique ne sert pas de condition : `si p` est refusé, il faut `selon` ou une comparaison (`p == vrai`). Pas d'arithmétique, ni de `&&`, `||`, `!`, `~` sur un logique, ni de mélange avec un entier sans conversion. `vrai` et `faux` gardent leur ancien sens d'entiers 1 et 0 (`tantque vrai`), et deviennent des logiques là où un logique est attendu (variable ou paramètre `logique`, comparaison avec un logique, argument d'une opération logique). `et`, `ou`, `non` restent les alias de `&&`, `||`, `!` ; d'où les noms `et4`, `ou4`, `non4`.

**La frontière avec le binaire.** Belnap reste le cœur de Vercintorix (inconnu 0, faux 1, vrai 2, variable 3 : le bit fort dit « une preuve du vrai », le bit faible « une preuve du faux », et une mémoire vide est inconnue). Pour parler aux systèmes binaires (fichiers, autres langages, l'ombre du cube en 2D), deux fonctions traduisent vers un code d'échange et retour : `binaire(l)` rend 0 (non), 1 (oui), 2 (inconnu) ou 3 (variable), le bit fort disant « pas binaire » ; `quaternaire(b)` rend le logique. Sur 16 logiques rangés dans un mot : `binaire16(x)` et `quaternaire16(x)`, une poignée d'instructions pour les 16 à la fois. Un quit jamais écrit (inconnu) devient 2 : la traduction ne transforme jamais un « je ne sais pas » en « non ».

## 7. Fonctions intégrées

| Fonction | Effet | Instruction du SPU |
|---|---|---|
| `sortie(x)` | écrit x (un long écrit deux mots : bas puis haut) | OUT |
| `bruit()` | 32 bits imprévisibles de la machine hôte | SYS 5 |
| `entrée()` | lit un mot | IN |
| `gdot(a, b)` | somme des produits des quatre voies | GDOT |
| `qegal(a, b)` | 1 dans le bit bas de chaque quit égal (16 comparaisons d'un coup) | QEGAL |
| `nb_bits(x)` | nombre de bits à 1 | COMPTE |
| `gemv(n, w, q, k, o)` | n produits de w mots d'un coup, étage 2 | GEMV |
| `min4`, `max4`, `addm4` | par quit : minimum, maximum, somme modulo 4 | MIN, MAX, ADDM4 |
| `cmp3(x)` | complément à 3 de chaque quit | CMP3 |
| `x.q(i)` | le quit i d'un mot | EXQ |
| `t[i]`, `t[i] = v` (tableau de quits ou de logiques) | lit ou écrit un quit rangé, sans toucher aux 15 autres | LDQ, STQ |
| `et4`, `ou4`, `non4`, `anti` | logique de Belnap sur un logique ou sur 16 logiques d'un mot | ET4, OU4, NON4, ANTI |
| `fusion`, `consensus` | union et accord des preuves (16 à la fois) | OR, AND |
| `<<q`, `>>q` | décalage d'un nombre de quits | SHL, SHR |
| `binaire(l)`, `quaternaire(b)`, `binaire16`, `quaternaire16` | frontière avec le binaire (code d'échange 0 non, 1 oui, 2 inconnu, 3 variable) | prélude |
| `racine(x)` | racine carrée : flottant, `flottant_64`, `flottant_petuar` | FSQRT, DSQRT, prélude |
| `flottant_petuar` : `+ - * /`, comparaisons, `etat(x)` | flottant quaternaire de 128 bits (quatre points du cube) | prélude (sur ADC, SBC…) |
| `accorder(étage, f)`, `frequence(étage)` | l'étage regarde le cube de fréquence f | SYS 8, SYS 9 |
| `ranger_cube(étage, f)` | écrit le cube sur disque (`cube-ÉTAGE-FRÉQUENCE.cub`) | SYS 11 |
| `presenter()` | montre l'image de l'étage 1 (Gobatix : fenêtre, atelier, PNG ou GIF) | SYS 12 |
| `souris()`, `souris_x(m)`, `souris_y(m)`, `souris_boutons(m)`, `souris_dedans(m)` | la souris dans l'image (0 sans fenêtre) | SYS 16, prélude |
| `touche()`, `appuyee(t)`, `touche_gauche()`… | la prochaine touche (sans attendre), une touche enfoncée | SYS 17, SYS 21 |
| `molette()`, `horloge()`, `cadence(ms)` | crans de molette, millisecondes, cadence des images | SYS 20, 18, 19 |
| `anti_couleur(c)`, `pixel_anti(x, y)`, `rectangle_anti(x, y, l, h)` | l'anti-cube des couleurs (255 − c, involutif) | prélude |
| conversions | voir la section 3 | ITOF, ITOFS, FTOI, FROUND, ITOD, DTOI… |

## 8. Prélude

Inclus seulement s'il est utilisé : `abs inf sup min max signe poids gdotn copier melange exp2`, ainsi que les fonctions internes des opérateurs signés et des longs. `abs`, `min` et `max` acceptent aussi des flottants et des longs. `exp2(x)` calcule 2^x en flottant (erreur relative au plus 7,4 × 10⁻⁷ de −126 à 127,5 ; 130 instructions).

### Afficher

`sortie(x)` écrit le mot de la machine tel quel, sur le canal 0 : un entier de 32 bits **sans signe** (−2 s'écrit 4294967294) et un flottant par ses bits (3.5 s'écrit 1080033280). C'est le canal des tests et des autres programmes. Pour lire un résultat, `afficher(x)` l'écrit en clair sur la console, suivi d'un retour à la ligne, selon son type :

| `afficher(x)` avec x | écrit |
|---|---|
| entier | en complément à deux : `afficher(3 - 5)` → `-2` |
| flottant | 7 chiffres significatifs au plus : `3.5`, `0.333333`, `-2.5`, `3.0`, `1.0e20`, `1.23e-5`, `inf`, `nan` |
| long | `-1234567890123` |
| logique | `vrai`, `faux`, `inconnu`, `variable` |
| texte | le texte : `afficher("Bonjour")`, `afficher(nom)` |

`afficher(a, b, c)` écrit plusieurs valeurs sur une ligne, séparées par une espace : `afficher("total :", n, 1.5);`. `ecrire(x)` écrit une valeur sans retour à la ligne, selon son type comme `afficher`.

Sans retour à la ligne, sur un canal choisi : `ecrire_entier(c, n)` (signé), `ecrire_nombre(c, n)` (sans signe), `ecrire_flottant(c, x, d)` (d décimales, au plus 9), `ecrire_long(c, x)`, `ecrire_logique(c, l)`, `ecrire_hexa(c, n)` (`#FF6020C0`), `ecrire_texte(c, t)`, `ecrire_car(c, k)`. Le canal 1 est la console.

Rappel : `7 / 2` entre entiers vaut 3 (division entière) ; `7.0 / 2` vaut 3.5 (un entier mêlé à un flottant devient flottant).

### Mathématiques (flottants)

`pi()`, `racine(x)`, `plancher(x)`, `plafond(x)`, `sinus(x)`, `cosinus(x)`, `tangente(x)` (en radians), `exponentielle(x)`, `logarithme(x)` (népérien), `puissance(x, y)`, `exp2(x)`, `arctangente(x)`, `arctangente2(y, x)` (l'angle du point (x, y), de −π à π), `arcsinus(x)`, `arccosinus(x)`, et `abs`, `min`, `max`. Erreur mesurée contre la bibliothèque de Python : au plus 6 × 10⁻⁸ en relatif pour l'exponentielle et le logarithme, 2,5 × 10⁻⁷ pour les fonctions trigonométriques (en absolu), 5 × 10⁻⁷ pour la puissance (`maths/test_maths.py`). Pour les angles de plus de 10⁸ radians, `sinus` et `cosinus` rendent `nan`.

### Hasard

`hasard(n)` : un entier de 0 à n − 1 ; `hasard_entre(a, b)` : de a à b compris ; `hasard_flottant()` : de 0 (compris) à 1 (exclu) ; `hasard_mot()` : 32 bits. Générateur xorshift de 32 bits, son état est en `@3[14680057]`. Le hasard de la machine est **reproductible** : sans `graine(n)`, chaque lancement tire la même suite, sur toutes les machines (c'est ce qui permet de tester et de comparer). Pour changer la suite : `graine(entrée())`, ou toute autre valeur.

`bruit()` est l'autre source : 32 bits **imprévisibles**, pris à la machine hôte (aléa du système et horloge ; service SYS 5). `graine_bruit()` fait `graine(bruit())` : une suite différente à chaque lancement. `bruit_logique()` tire un logique (`inconnu`, `faux`, `vrai` ou `variable`). Un programme qui utilise `bruit` ne donne plus le même résultat d'un lancement à l'autre : pour le vérifier, gardez une graine fixe. Sur la machine quaternaire, cette source serait la lecture d'un quit instable, un état `variable` du signal.

### Tableaux dynamiques

Un tableau dynamique vit dans le tas (étage 3) et grandit seul. Il contient des mots : entiers, textes (un texte est un mot qui le désigne), autres tableaux, ou flottants (voir plus bas).

```
soit t = [5, 3, 9, 1];          // littéral
soit vide = tableau(0);         // n cases à 0
tableau carres[10];             // dans une fonction : comme soit carres = tableau(10)
t[0] = 100;  afficher(t[2]);    // lecture et écriture (pas de contrôle d'indice)
pour x dans t { ecrire(x); }    // parcours, x prend chaque valeur
pour mot: texte dans cles(d) {} // annotation si le compilateur ne voit pas que ce sont des textes
```

| Mot | Effet |
|---|---|
| `longueur(t)` | nombre d'éléments (marche aussi pour un texte) |
| `ajouter(t, v)` / `retirer(t)` | à la fin / enlève et rend le dernier |
| `inserer(t, i, v)` / `enlever(t, i)` | au rang i / enlève et rend l'élément i |
| `vider(t)`, `copie(t)`, `inverser(t)` | |
| `indice(t, v)` | premier rang de v, 4294967295 s'il n'y est pas |
| `contient(t, v)`, `somme(t)` | 1 ou 0 ; somme des éléments |
| `trier(t)` | ordre croissant, entiers signés |

**Tableaux de flottants.** Un littéral qui contient un flottant écrit (`[2.5, -1.0, 4]`) est un tableau de flottants ; les entiers écrits y deviennent des flottants. On peut aussi le déclarer : `soit t: flottant[] = tableau(0);`, et en paramètre ou en retour : `fonction moyenne(t: flottant[]): flottant`. Alors `t[i]` est un flottant, `t[i] = x`, `ajouter`, `inserer`, `indice`, `contient` rangent des flottants, `retirer` et `enlever` en rendent, `somme` additionne en flottants et `trier` trie par valeur (négatifs compris). `pour x dans t` donne des flottants ; `pour x: flottant dans t` l'impose quand le compilateur ne voit pas d'où vient le tableau. Un tableau mélangé (entiers et flottants à la fois) n'existe pas : chaque case est lue selon le type du tableau.

`contient`, `existe`, `commence_par`, `finit_par` rendent 1 ou 0, comme une comparaison, pour servir directement dans `si`. Un logique à quatre valeurs ne sert pas de condition : ces mots ne répondent jamais « inconnu ».

### Dictionnaires

`soit d = dico();` puis `ranger(d, cle, valeur)`, `trouver(d, cle)` (0 si la clé manque), `existe(d, cle)` (la clé a une entrée), `cles(d)` (un tableau de textes, dans l'ordre de la table de hachage, pas dans l'ordre d'arrivée). Les clés sont des textes, la valeur est un mot.

### Savoir à quatre valeurs

Un dictionnaire sait aussi *ce qu'il sait* de chaque clé, en logique à quatre valeurs (la logique de Belnap, faite pour une base qui reçoit des informations contradictoires) :

| | `savoir(d, cle)` | obtenu par |
|---|---|---|
| `vrai` | affirmé | `affirmer(d, cle, v)`, ou `ranger` |
| `faux` | nié | `nier(d, cle)` ; ou clé absente d'un dico **fermé** (`dico()`) |
| `inconnu` | jamais dit | clé absente d'un dico **ouvert** (`dico_ouvert()`), ou pas de dico (0) |
| `variable` | contredit | affirmé avec deux valeurs différentes, ou affirmé puis nié (ou l'inverse) |

`ranger` met à jour une valeur (un compteur, par exemple) : c'est une variable du programme, pas une affirmation, il ne crée jamais de contradiction. `affirmer` est un témoignage : un second témoignage différent rend la clé `variable` au lieu d'écraser le premier ; `trouver` rend la dernière valeur. Un dico fermé suppose qu'il sait tout (ce qui n'y est pas est faux) ; un dico ouvert sait qu'il ne sait pas tout.

**Changer le sens des mots.** Les quatre états gardent la même structure dans tous les domaines (inconnu : trop peu d'information ; variable : trop d'information), mais pas le même nom. `nommer(l, noms)` rend le nom choisi par le domaine, dans l'ordre inconnu, faux, vrai, variable :

```
soit recherche = ["hors de portée", "réfuté", "confirmé", "ambigu"];
afficher(nommer(savoir(d, "cube"), recherche));
```

### Mots sur les textes

`majuscules(t)`, `minuscules(t)`, `nettoyer(t)` (espaces au début et à la fin), `repeter(t, n)`, `remplacer(t, ancien, nouveau)`, `decouper(t, separateur)` (un tableau de textes), `assembler(tableau, separateur)`, `commence_par(t, debut)`, `finit_par(t, fin)`, `car_texte(c)` (un texte d'un caractère), et déjà `sous_texte`, `position`, `nombre`, `texte`. Divers : `pgcd(a, b)`, `borne(x, min, max)`.

### Lire au clavier

`lire_ligne()` attend une ligne tapée au clavier et la rend comme texte, sans le retour à la ligne ; `nombre(lire_ligne())` pour un entier. Ce qui a été écrit avant (la question) est affiché d'abord. Dans `atelier.exe`, la ligne se tape dans la fenêtre d'exécution. À la fin de l'entrée (fichier ou flux fermé), `lire_ligne()` rend un texte vide.

### La mémoire qui se libère, la mémoire qui dure

Chaque bloc du tas (`nouveau`, structures, tableaux, textes, dicos) porte un mot d'en-tête avec sa taille, juste avant lui.

- `liberer(h)` rend un bloc ; `nouveau` reprend d'abord un bloc libéré de la bonne taille (une liste par taille jusqu'à 64 mots, une liste pour les grands). Un tableau qui grandit et un dico qui grandit rendent eux-mêmes leurs anciens blocs.
- `ramasser()` : le ramasse-miettes. Il part de ce que tiennent les variables (la pile, de `pile()` au sommet) et des poignées protégées par `proteger(h)` (une poignée rangée seulement dans `@1` ou `@2` doit être protégée), suit toutes les liaisons, et libère les blocs qu'on ne peut plus atteindre ; il rend le nombre de mots libérés. Il est prudent : un nombre qui ressemble à une poignée garde son bloc. Appelez-le comme une instruction (`ramasser();` ou `soit n = ramasser();`).
- **Purge automatique** : quand le tas est plein, `nouveau` ramasse les miettes puis réessaie (les 600 000 derniers mots du tas, de 14 080 048 à 14 680 048, restent au ramasse-miettes pour travailler). Le balayage fond les blocs libres voisins en un seul, un grand bloc libre est découpé pour une petite demande, et une suite libre qui touche le sommet fait redescendre le tas. Si une purge ne rend presque rien, il n'y en a plus d'automatique jusqu'au prochain `ramasser()` (pas d'acharnement). Si le tas reste plein, les tableaux, textes et dicos arrêtent le programme avec le message « mémoire pleine » ; `nouveau` seul rend `nul`. `purges()` : le nombre de purges faites.
- `tas_utilise()` : les mots pris par le tas. `tas_marque()` et `tas_retour(m)` restent (tas_retour vide aussi les listes de blocs libres).
- `sauver_tas(nom, racine)` enregistre tout le tas dans le fichier `nom` (et son en-tête dans `nom.ent`) ; `charger_tas(nom)` le recharge et rend la racine (0 si le fichier n'existe pas). La racine est une poignée : pour une structure, `sauver_tas("m", entier(s))`, puis au lancement suivant `soit s: Souvenir = charger_tas("m");` (une déclaration explicite vaut conversion d'un entier en référence).
- `sauver_bloc(nom, adresse, n)` et `charger_bloc(nom, adresse, n)` : n mots à partir d'une adresse globale (étage dans les bits 24 et 25), dans un fichier binaire.
- Exemples : `exemples/premiers/ramasser.vtx`, `exemples/premiers/memoire.vtx`. Nouvelles fonctions intégrées : `pile()` (le sommet de la pile) et `__service(code, argument)` (un service de la machine hôte).

### Additionner les cubes : les fréquences

Chaque étage 1, 2 et 3 regarde un cube de 256³ mots choisi par sa **fréquence** (0 au départ). `accorder(étage, f)` fait regarder à l'étage le cube de fréquence f et rend l'ancienne fréquence : le contenu du cube quitté est gardé, celui du cube retrouvé revient intact. `frequence(étage)` dit quel cube est regardé. L'étage 0 (le code et la pile) ne change pas de cube (`accorder(0, …)` rend 4294967295). Il y a autant de cubes que de fréquences : la mémoire s'additionne cube par cube sans changer la taille des mots. Les pointeurs d'un cube (poignées du tas, par exemple) ne valent que dans ce cube. Exemple : `exemples/premiers/cubes.vtx`.

**Cubes sur disque.** `ranger_cube(étage, f)` écrit le cube de fréquence f dans le fichier `cube-ÉTAGE-FRÉQUENCE.cub`, à côté du programme (par exemple `cube-1-262.cub`) et rend le nombre de pages écrites. Si l'étage regarde ce cube, le fichier en est une copie et le cube reste en place ; si le cube est rangé, il quitte la mémoire. `accorder(étage, f)` retrouve un cube : en mémoire s'il y est encore, sinon dans son fichier (d'un lancement à l'autre aussi : le fichier reste). Le nom du fichier porte la fréquence : l'atelier et `vtx cubes DOSSIER` les listent avec le nom de la note quand la fréquence en est une (262 → do4, 330 → mi4, 392 → sol4). Dans l'atelier, `cubes` dit ce que regarde chaque étage et ce qui est en mémoire ou sur disque ; `cube ÉTAGE FRÉQUENCE` fait regarder ce cube à l'étage et l'affiche. Format : `VTXCUB01`, puis pour chaque page non nulle son numéro (u32) et ses 65 536 mots (u32, petit boutiste) ; les pages jamais écrites ne prennent pas de place. Exemple : `exemples/premiers/cubes_disque.vtx`.
Contraintes : un cube a au plus 2^24 mots (64 Mo) ; la page de 256 Ko est l'unité d'écriture et de lecture ; accorder un étage déplace ses 256 pages (lecture de tout le fichier si le cube vient du disque) : à réserver aux changements de cube, pas à l'intérieur d'une boucle serrée ; un pointeur ne vaut que dans son cube, donc il faut accorder avant de le suivre ; un cube rangé n'est pas lu par le programme tant qu'il n'est pas accordé ; aucun contrôle de version entre deux lancements (un programme qui change de format de données doit changer de fréquence) ; l'étage 0 ne change pas de cube. Variable d'environnement `VTX_CUBES_PAGES=N` : au-delà de N pages rangées en mémoire, le cube quitté va au disque tout seul. Services 11 (ranger) et 8 (accorder) : machines Rust et Python ; les machines JavaScript n'ont pas de disque.

La machine Rust ne prend la mémoire que là où l'on écrit (pages de 65 536 mots ; l'étage 0 d'un bloc de 64 Mo) : un petit programme prend quelques Mo, pas 256.

### Parler

`parler(t)` dit le texte `t` à voix haute : la machine Rust ouvre le canal spécial `voix:` et, à sa fermeture, le fait lire par la synthèse vocale de Windows (une voix française si elle est installée) ; ailleurs par `espeak-ng` ou `espeak` s'ils sont là, sinon rien. L'appel attend la fin de la phrase. La machine Python n'a pas de voix (sans accès aux fichiers, `parler` ne fait rien).

### Dessiner

**Gobatix, premier pas.** `presenter()` montre l'image préparée par `ecran` : la machine la copie vers une sortie et rend 0 tant que tout va bien, 1 quand la fenêtre a été fermée, 4294967295 si le programme n'a pas d'image (service 12). `vtx gobatix prog.vtx` ouvre une fenêtre Win32 (60 images par seconde au plus, `cadence(ms)` la change ; l'image est agrandie sans déformation ; la souris et le clavier y vont au programme) ; `vtx gobatix prog.vtx --images DOSSIER [--max N] [--pas K]` écrit `image-0001.png`… sans fenêtre (toutes les machines). Exemples : `exemples/gobatix/cube_tournant.vtx`, un cube en fil de fer qui tourne (flottants 32 bits, projection en perspective) ; `exemples/gobatix/cube_chromatique.vtx`, **le cube chromatique lui-même** : ses huit sommets sont les couleurs `#000000`… `#FFFFFF`, chaque face montre le fondu réel de ses couleurs, un quadrillage coupe chaque axe aux quits du poids fort (`0x40`, `0x80`, `0xC0`), et la diagonale des gris porte ses cinq points.

`ecran(l, h)` prépare une image de l × h points, rangée ligne par ligne dans l'étage 1 (sa taille en `@3[14680058]` et `@3[14680059]`) : chaque pixel est un point `#RRGGBBAA` du cube. `pixel(x, y, c)`, `trait(x0, y0, x1, y1, c)`, `rectangle(x, y, l, h, c)`, `disque(cx, cy, r, c)`, `triangle(x0, y0, c0, x1, y1, c1, x2, y2, c2)` (plein, la couleur fondue d'un sommet à l'autre : ombrage de Gouraud) y dessinent (ce qui sort de l'image est ignoré) ; `rgb(r, g, b)` donne la couleur `#RRGGBBFF`. Après l'exécution, l'atelier montre l'image (F6 : image, cube en perspective, à plat) ; `vtx dessin prog.vtx image.png [échelle]` l'écrit en PNG. Exemple : `exemples/premiers/dessin.vtx`.

**Gobatix interactif : souris, clavier, animation.** Mêmes fonctions sur le SPU-32 et le SPU-64 ; sans fenêtre (tests, fichiers), la souris, les touches et la molette valent 0.

- `presenter()` montre une **image finie** : le programme dessine déjà la suivante dans l'étage 1 sans que l'écran le voie (le double tampon), ce qui supprime le scintillement. `cadence(ms)` règle l'intervalle minimal entre deux images (16 ms par défaut, 60 images par seconde ; 0 : sans attendre) et rend l'ancienne ; c'est aussi la durée de chaque image d'un GIF. `horloge()` : les millisecondes depuis le lancement.
- `souris()` rend un mot : x (bits 0 à 11), y (12 à 23), en points de l'image ; boutons (24 à 26 : gauche 1, droit 2, milieu 4) ; « dans l'image » (27). `souris_x(m)`, `souris_y(m)`, `souris_boutons(m)`, `souris_dedans(m)` les lisent. `molette()` : les crans depuis le dernier appel (vers l'avant : positif ; comparer avec `.>`).
- `touche()` rend la prochaine touche appuyée **sans attendre** (0 s'il n'y en a pas) : un caractère (`97` pour « a », `13` Entrée, `27` Échap, `32` espace), ou 65536 + le code d'une touche sans caractère : `touche_gauche()`, `touche_haut()`, `touche_droite()`, `touche_bas()` (et F1 à F12, début, fin, pages, insertion, suppression). `appuyee(t)` rend 1 tant que la touche est enfoncée (pour un jeu : `si appuyee(touche_gauche()) == 1 { … }` ; Maj, Ctrl et Alt : `appuyee(65552)`, `appuyee(65553)`, `appuyee(65554)`). `lire_ligne()` reste la lecture d'une ligne entière dans le terminal.
- **L'anti-cube des couleurs.** `anti_couleur(c)` = 255 − c sur chaque voie (65 535 − c en points profonds), l'alpha gardé : la symétrie du cube par son centre gris, celle qui échange le triangle rouge-vert-bleu et le triangle cyan-magenta-jaune. Comme `anti(anti(c)) = c`, `pixel_anti(x, y)` et `rectangle_anti(x, y, l, h)` posent un curseur, une sélection ou un objet qui bouge **sans garder le fond** : on le pose avant `presenter()`, on le repose après, et l'image revient intacte (`exemples/gobatix/peindre.vtx`).
- Exemples : `exemples/gobatix/peindre.vtx` (peindre à la souris, palette, molette, un carré qui rebondit, poussé aux flèches) ; `exemples/gobatix/cube_tournant.vtx` (le cube suit la souris, molette : plus ou moins près, espace : pause).
- **Enregistrer.** Dans l'atelier, **Ctrl+G** (ou le bouton « Enregistrer (GIF) ») commence et finit l'enregistrement : chaque image présentée s'ajoute, et `programme-1.gif` s'écrit à côté du programme. Hors de l'atelier : `vtx gobatix prog.vtx --gif anim.gif [--max N] [--pas K]`. Le GIF garde la palette du cube (6 niveaux par voie, 216 couleurs, et 39 gris ; une trame ordonnée garde exactes les couleurs de la grille 0, 51, 102… 255) ; chaque image n'écrit que ce qui a changé : un point inchangé n'apporte aucune preuve nouvelle, il est *inconnu* et devient transparent ; une image identique allonge la précédente.
- **Rejouer des gestes.** `--scenario FICHIER` rejoue souris, touches et molette image par image (une ligne « IMAGE souris X Y BOUTONS », « IMAGE touche CODE », « IMAGE appui CODE », « IMAGE relache CODE », « IMAGE molette CRANS ») : pour montrer ou vérifier un programme interactif sans écran (`exemples/gobatix/peindre.scenario`, `tests/test_gobatix.py`).

### Correction d'erreur diamant (`importer "bibliotheque/diamant.vtx";`)

Un mot de 16 quits lu sur un canal bruité peut avoir un quit décalé d'un niveau. Les lectures à un pas d'un mot valide forment un losange, le diamant ; le code n'utilise que des mots dont les diamants ne se touchent pas.

- **Détecter** : `damier_proteger(d)` (30 bits de données, un quit de parité), `damier_etat(m)` : `vrai` si intact, `variable` si une erreur est vue ; `damier_donnee(m)`.
- **Corriger** : `diamant_proteger(d)` (26 bits de données, 3 quits de contrôle : la somme des quits pondérés par leur rang vaut 0 modulo 33), `diamant_etat(m)` : `vrai` intact, `faux` lecture fausse corrigée, `variable` erreur vue mais impossible à corriger, `inconnu` mot nul (jamais écrit) ; `diamant_corriger(m)`, `diamant_donnee(m)`.
- Mesuré (`bibliotheque/test_diamant.py`) : toute erreur d'un niveau est corrigée ; avec 1 % d'erreurs par quit, 12 % des mots seraient faux sans code, 0,8 % restent faux avec le diamant (0,3 % sont signalés `variable`). Deux erreurs dans un même mot sont souvent mal corrigées : c'est la limite d'un code à un seul diamant.

## 9. Mémoire et registres

- Quatre étages (0 à 3) de 2^24 mots. L'étage 0 contient le code, les données et la pile : y écrire peut écraser le programme.
- Réservés : l'état du hasard en 14 680 057 de l'étage 3 (juste après le pointeur du tas, 14 680 056), le journal des hypothèses dans l'étage 3 à partir de 15 728 640, ses compteurs en 16 777 200 et 16 777 201, et le drapeau d'initialisation des données à la dernière adresse de l'étage 3.
- Registres utilisés par le compilateur : R1 à R8 de travail (R1 résultat, R1 et R4 pour un long), R13 cadre, R14 pile.

## 10. Outils

| Commande | Effet |
|---|---|
| `python3 vtx.py run prog.vtx [entrées]` | compiler et exécuter |
| `vtx installer` / `vtx desinstaller` | associe les fichiers `.vtx` à l'atelier, avec l'icône du cube (Windows : registre de l'utilisateur ; Linux : type MIME et lanceur) |
| `vtx icone fichier.ico\|.png [taille]` | écrit l'icône du cube chromatique |
| `vtx arbre prog.vtx [entrées]` | exécute, puis écrit l'arbre des liaisons de la mémoire (objets du tas, dicos et leurs états, hypothèses) |
| `vtx dessin prog.vtx image.png [échelle]` | exécute, puis écrit l'image dessinée par le programme |
| `vtx gobatix prog.vtx [--images DOSSIER \| --gif FICHIER] [--max N] [--pas K] [--scenario FICHIER]` | exécute un programme qui appelle `presenter()` : fenêtre (Windows), images PNG ou animation GIF ; `vtx gobatix64` : la même chose sur le SPU-64 |
| `vtx cubes [DOSSIER]` | liste les cubes rangés sur disque (`cube-ÉTAGE-FRÉQUENCE.cub`) avec le nom de la note |
| `python3 vtx.py profil prog.vtx [entrées]` | histogramme des instructions et des accès par étage |
| `python3 vtx.py compile prog.vtx` / `asm prog.vtx` | assembleur, ou code machine en hexadécimal |
| `python3 vtx.py trace prog.vtx [entrées] [--de N] [--max N] [--arret ADR] [--regs]` | une ligne par instruction, registres, point d'arrêt |
| `python3 vtx.py deboguer prog.vtx [entrées]` | débogueur interactif au niveau du source (voir section 10 bis) |
| `python3 vtx.py partition prog.vtx [entrées]` | partition automatique des tâches : accords, mesures, notes, temps gagné (section 10 ter) |
| `python3 vtx.py test` | suite de tests du langage |

Machines : `vtx.py` (référence), `Vtx.java`, `jeu3/vm_rapide.js` (interprète), `jeu3/vm_traduite.js` (traduction du code machine en fonctions JavaScript, environ 3,5 fois plus rapide). Le corpus `corpus_conformite.txt` et ses résultats `corpus_attendu.txt` servent à valider toute nouvelle machine.

## 10 bis. Débogueur

`python3 vtx.py deboguer prog.vtx [entrées]` démarre le programme et s'arrête à sa première instruction. Les arrêts se font au début des instructions source, dans le programme et dans les fichiers importés ; le prélude est traversé sans arrêt.

| Commande | Effet |
|---|---|
| `p`, `pas` | instruction suivante, en entrant dans les fonctions appelées |
| `s`, `suivant` | instruction suivante de la même fonction, sans entrer dans les appels |
| `f`, `sortir` | termine la fonction en cours ; arrêt à l'instruction suivante de l'appelant |
| `c`, `continuer` | jusqu'au prochain point d'arrêt ou la fin |
| `a 12`, `a outils.vtx:10` | point d'arrêt à une ligne (d'un fichier importé avec `fichier:ligne`) |
| `e 12` | retire un point d'arrêt |
| `v nom`, `vars` | valeur d'une variable, ou de toutes celles de la fonction (entier avec sa lecture signée, flottant, long) |
| `pile` | pile d'appels avec fichier et ligne de chaque appel |
| `mem @2[100] 8` | 8 mots de l'étage 2 à partir de l'adresse 100 |
| `regs`, `où`, `sorties`, `aide`, `q` | registres, emplacement, sorties, aide, fin |

Chaque commande s'arrête après 50 millions d'instructions sans atteindre son arrêt, en indiquant l'endroit atteint. Le débogage ne change pas l'exécution : même nombre d'instructions qu'une exécution normale. Les erreurs de compilation dans un fichier importé indiquent ce fichier et sa ligne (`lib/outil.vtx, ligne 2 : expression attendue`).

Pour Python, la classe `Debogueur(src, entrées, dossier, nom)` offre les mêmes opérations : `demarrer`, `pas`, `suivant`, `sortir`, `continuer`, `arreter_a(ligne, fichier)`, `enlever`, `valeur(nom)`, `variables`, `pile`, `memoire`.

## 10 ter. Partition automatique des tâches

Rien n'est à écrire dans le programme. Dès qu'une fonction contient au moins deux appels de fonctions écrits l'un après l'autre comme instructions (`a(); b(); c();`), le compilateur en fait un **accord** :

1. Il calcule ce que chaque appel lit et écrit, fonctions appelées comprises : les tableaux (leur zone exacte), les cases à adresse constante, un étage entier pour une adresse calculée, tous les étages pour un étage variable, et les entrées et sorties, dont l'ordre compte.
2. Deux tâches sont en conflit si l'une écrit ce que l'autre lit ou écrit. Il range dans une même **mesure** les tâches sans conflit entre elles ; une tâche va dans la mesure qui suit la dernière tâche avec laquelle elle est en conflit.
3. Chaque fonction reçoit une **note**, sa fréquence signature : la4 (440 Hz) pour la première, puis les touches suivantes du piano. Chaque note a son canal optique sur la grille de 50 GHz à partir de 191,30 THz.
4. Le programme s'exécute mesure après mesure. Les tâches d'une même mesure peuvent être jouées ensemble ; l'émulateur les joue l'une après l'autre et mesure le temps qu'elles auraient pris ensemble.

`python3 vtx.py partition partition/orchestre.vtx` affiche par exemple :

```
accord 0 dans principal (orchestre.vtx, ligne 87) : 6 tâches en 3 mesure(s)
  mesure 1 : la4 preparer_image | la#4 preparer_memoire
  mesure 2 : si4 histogramme | do5 flou | do#5 recherche
  mesure 3 : ré5 contraste
```

**Segments.** `pour i dans a..b en segments { … }` découpe la boucle en 12 morceaux consécutifs (6 cylindres × 2 temps, comme un moteur V6) : 12 se partage aussi bien sur 2, 3, 4 ou 6 cœurs. `en N segments` accepte N de 2 à 18 et l'arrondit au multiple de 6 supérieur (6, 12 ou 18 : 6 cylindres × 1, 2 ou 3 temps), Le nombre de segments est fixé à la compilation ; le nombre de cylindres est celui de la machine qui joue le programme (ses cœurs), et le résultat ne dépend jamais de lui. `vtx.py partition` mesure le temps sur les cœurs de la machine moins un, laissé au système et à l'affichage (`--laisser N` pour en laisser N, `--cylindres N` pour imposer le nombre). Les accords imbriqués (les segments d'une tâche) partagent les mêmes cylindres que l'accord qui les contient. Chaque segment est une tâche. Le compilateur prouve qu'ils sont indépendants quand chaque écriture dans un tableau se fait à la case de l'indice (`t[i]`, `t[i + 3]`) et que rien d'autre n'est écrit que les autres lisent ; ils vont alors dans une même mesure. Sinon, ils sont joués l'un après l'autre, ce qui revient à la boucle ordinaire. Un segment ne peut pas modifier une variable déclarée hors de la boucle, ni sortir de la boucle (`arrêter`, `retour`, `hypothèse` sont refusés) : écrivez plutôt dans un tableau, à la case de l'indice. Les bornes sont évaluées une seule fois. Une fonction appelée dans un segment est prise en entier : si elle écrit un tableau à un indice reçu en paramètre, les segments sont joués l'un après l'autre.

**Tableaux cumulés.** Un histogramme ou une somme écrit à des cases qui ne dépendent pas de l'indice, donc les segments se gêneraient. `en segments cumulant T` (ou `cumulant T, U`) donne à chaque segment sa propre copie de `T`, remise à zéro, puis ajoute toutes les copies dans `T` une fois les segments finis. Le résultat est exactement celui de la boucle ordinaire, car l'addition sur 32 bits ne dépend pas de l'ordre. Pour que ce soit sûr, dans la boucle `T` ne peut s'écrire que sous la forme `T[x] = T[x] + valeur` (ou `valeur + T[x]`, ou `T[x] - valeur`), avec la même case des deux côtés et une valeur qui ne lit pas `T`. Toute autre lecture de `T`, une adresse calculée qui pourrait l'atteindre, ou une fonction appelée qui le touche, est refusée. Les champs de structure sont permis (`ps[k].n = ps[k].n + 1`). Les copies vivent dans `@3[14680064..15728640]` (0xE00000 à 0xF00000), zone réservée : un tableau déclaré là est refusé quand un programme utilise `cumulant`. Sans partition, `cumulant` est sans effet et la boucle est ordinaire.

**Noms des segments.** Dans la partition, les segments portent les ordinaux gaulois des comptes de fournées de La Graufesenque : *cintux* (1er), *allos* (2e), *tritios*, *petuarios*, *pinpetos*, *suexos* (6e). Avec 6 segments, le nom est celui du cylindre : `histogramme·tritios`. Avec 12 ou 18, c'est cylindre puis temps : `flou·tritios·allos` est le segment du 3e cylindre au 2e temps. Les formes sont celles des inscriptions (*cintux* et *allos* sont sûrs ; plusieurs autres sont reconstruits par les linguistes).

L'analyse est prudente : en cas de doute, elle sépare les tâches. Seuls les appels écrits comme instructions forment des tâches (pas `x = f();`), et les fonctions du prélude ne sont jamais réordonnées. Une tâche ne peut pas modifier les variables locales de l'appelant, ce qui rend le réordonnancement sûr.

## 11. Exemple

```
importer "bibliotheque/cube.vtx";

fonction luminance(c): flottant {
    retour 0.2126 * voie(c, 0) + 0.7152 * voie(c, 1) + 0.0722 * voie(c, 2);
}

fonction principal() {
    soit total: long = 0;
    soit n = entrée();
    pour i dans 0..n {
        soit c = entrée();
        total = total + c;
        sortie(arrondi(luminance(c)));
    }
    sortie(total);
}
```

## 12. Limites de la version 0.4

- Les tableaux, les structures et la mémoire ne contiennent que des mots : un long s'y range en deux écritures.
- Pas de contrôle d'indice à l'exécution ; les tableaux à plusieurs dimensions se font avec des tableaux de tableaux ; pas de flottants dans un tableau dynamique.
- Le `flottant_petuar` est calculé par le prélude (pas encore d'instruction du SPU) : de mille à quarante mille fois plus lent qu'un `flottant_64` ; pas de mathématiques `*_petuar` (sinus, exponentielle…) au-delà de `racine` ; pas de directive qui change la précision de tout un fichier.
- Un flottant_64, un long, un entier_petuar ou un flottant_petuar ne se range pas dans un tableau ou une structure : seulement des mots (`bas(x)` et `haut(x)`, ou les quatre mots de `bits(x)`).
- Le débogueur n'a pas encore de points d'arrêt conditionnels ni de surveillance d'une case mémoire, et ne montre pas les champs des structures par leur nom.
- Le compilateur n'optimise pas l'allocation des registres : beaucoup d'empilements et de dépilements.
