# Le vocabulaire étendu de Vercintorix (0.61)

*Écrit par `vtxc/vocabulaire.py` à partir du texte même des mots : il ne peut pas dire autre chose que le code.*

Les mots viennent de ce que savent Rust (les méthodes des entiers, des flottants, des textes, des tranches et des
itérateurs), ses extensions officielles (num, itertools, rand), Arduino (map, constrain, bitRead, lowByte, sq,
random, millis, delay, String) et des moteurs que vtx doit pouvoir accueillir (Unreal Engine 5 : FMath, FVector,
FQuat, FMatrix ; Blender : mathutils et ses nœuds de mathématiques). Ce ne sont pas ces bibliothèques recréées :
c'est le vocabulaire français qu'il faut pour y brancher ce qu'elles font. Les mots déjà là avant (abs, min, max,
borne, pgcd, majuscules, decouper, trier…) sont dans la référence du langage.

**Un mot pour tous les types.** Un mot qui a des variantes les prend seul, d'après ses arguments : le flottant le
plus large, sinon l'entier le plus large (Lugus : flottants de 128, 64, 32 bits, entiers de 128, 64, 32 bits ;
Dunon : flottants de 64 et 32 bits, entiers de 128, 64, 32 bits). Une fonction du programme qui porte le même nom
garde la main. **Le doute ne se comble pas** : sur une valeur inconnue (jamais écrite) ou variable (contradictoire),
une question rend cet état ; une moyenne de rien est inconnue ; un texte qui n'est pas un nombre est variable.
**Les questions sur un texte ou un tableau** rendent 1 ou 0, comme `commence_par` ; « absent » s'écrit
18446744073709551615 (−1 lu signé), comme `position`.


## « nombres » : un mot pour tous les types (le compilateur choisit la variante)

*Machines : Lugus, Dunon.*

| Mots | Ce qu'ils font, d'où ils viennent |
|---|---|
| `carre` | Arduino sq |
| `remapper` | Arduino map, UE FMath::GetMappedRangeValueUnclamped, Blender « Map Range » |
| `est_fini` | Rust is_finite |
| `reste` | Rust % sur les flottants et les entiers signés, C fmod, UE FMath::Fmod ; exact, du signe du dividende ; reste(x, 0.0) : variable (un entier par zéro rend x, comme la machine) |

## « flottants » (Rust f64, UE FMath, Blender) : le flottant principal, et ses variantes

*Machines : Lugus, Dunon.*

| Mots | Ce qu'ils font, d'où ils viennent |
|---|---|
| `racine_cubique` | Rust cbrt |
| `hypotenuse` | Rust hypot (sans débordement) |
| `inverse` | Rust recip |
| `vers_degres`, `vers_radians` | Rust to_degrees, to_radians ; UE RadiansToDegrees |
| `copier_signe` | Rust copysign (un signe inconnu ou contradictoire le reste) |
| `multiplier_ajouter` | Rust mul_add, C fma, UE FMath::FMA ; 0.65 : exact, un seul arrondi (au plus proche, pair au milieu, comme la machine), sur chaque flottant ; sur les entiers, a · b + c |
| `le multiplier-ajouter exact`, `sur les mantisses (0.65)` | a·b + c calculé sans arrondi, puis arrondi une seule fois au plus proche, pair au milieu (comme la machine) ; sa, sb, sc les états (1 négatif, 2 positif), ma, mb, mc les mantisses (des grands entiers), xa, xb, xc les exposants (max(E, 1)) ; p les bits de mantisse, biais, emax l'exposant de l'infini. Rend [l'état, l'exposant écrit, la mantisse (un grand entier)] |
| `logarithme2`, `logarithme10`, `logarithme_base` | Rust log2, log10, log(base) |
| `sinus_hyp`, `cosinus_hyp`, `tangente_hyp` | Rust sinh, cosh, tanh (en série près de zéro : pas de perte de chiffres) |
| `argsinus_hyp`, `argcosinus_hyp`, `argtangente_hyp` | Rust asinh, acosh, atanh (hors du domaine : variable) |

## « interpolation » (UE FMath, Blender, Godot, Arduino)

*Machines : Lugus, Dunon.*

| Mots | Ce qu'ils font, d'où ils viennent |
|---|---|
| `interpoler` | UE Lerp, Blender mix, Rust f64::lerp (nightly) |
| `interpolation_inverse` | UE GetRangePct, Godot inverse_lerp |
| `remapper_borne` | UE GetMappedRangeValueClamped, Blender « Map Range » (clamp) |
| `pas_lisse`, `pas_plus_lisse` | GLSL smoothstep, UE SmoothStep, Blender « Smooth Step », Perlin smootherstep |
| `rapprocher` | UE FInterpConstantTo, Godot move_toward (au plus « pas » à chaque appel) |
| `amortir` | UE FInterpTo (une part du chemin, selon le temps écoulé et la vitesse) |
| `presque_egal` | UE IsNearlyEqual, Rust (a - b).abs() <= tol ; le doute reste |
| `enrouler` | UE FMath::Wrap, Blender « Wrap », Rust rem_euclid sur un intervalle [a, b) |
| `aller_retour` | Blender pingpong |
| `aimanter` | UE GridSnap, Blender « Snap », Godot snapped (au multiple le plus proche) |
| `entree_douce`, `sortie_douce`, `entree_sortie_douce` | UE InterpEaseIn/Out (cubiques), easings.net |
| `lire_flottant` | Rust str::parse::<f64>, Arduino toFloat ; rien d'écrit : inconnu ; pas un nombre : variable (la virgule française est comprise ; plus de 34 chiffres : le dernier peut être arrondi deux fois) |

## « entiers et bits » (Rust u64, Arduino) : l'entier de 64 bits

*Machines : Lugus, Dunon.*

| Mots | Ce qu'ils font, d'où ils viennent |
|---|---|
| `compter_uns`, `compter_zeros`, `zeros_en_tete`, `zeros_en_queue` | Rust count_ones, count_zeros, leading_zeros, trailing_zeros |
| `tourner_gauche`, `tourner_droite`, `inverser_bits`, `echanger_octets` | Rust rotate_left, rotate_right, reverse_bits, swap_bytes |
| `est_puissance_de_deux`, `puissance_de_deux_suivante` | Rust is_power_of_two, next_power_of_two (0 si elle dépasse 64 bits) |
| `log2_entier`, `log10_entier`, `racine_entiere` | Rust ilog2, ilog10, isqrt (log de 0 : 18446744073709551615, comme « absent ») |
| `reste_euclidien`, `quotient_euclidien` | Rust rem_euclid, div_euclid (signés) ; num-integer mod_floor |
| `division_plafond`, `multiple_suivant`, `milieu` | Rust div_ceil, next_multiple_of, midpoint |
| `est_pair`, `est_impair` | num-integer is_even, is_odd |
| `addition_saturee`, `soustraction_saturee`, `multiplication_saturee`, `deborde_addition`, `deborde_multiplication` | Rust saturating_add, saturating_sub, saturating_mul (bornés à 0 et au plus grand entier) ; overflowing_add, overflowing_mul (vrai si le calcul déborde) |
| `lire_bit`, `poser_bit`, `effacer_bit`, `ecrire_bit`, `basculer_bit`, `masque_bit` | Arduino bitRead, bitSet, bitClear, bitWrite, bit() |
| `octet_bas`, `octet_haut`, `octet`, `mot_de` | Arduino lowByte, highByte, word(h, l) ; Rust to_le_bytes |

## « textes » (Rust str et char, Arduino String) ; les questions rendent 1 ou 0, comme commence_par

*Machines : Lugus, Dunon.*

| Mots | Ce qu'ils font, d'où ils viennent |
|---|---|
| `est_vide` | Rust is_empty, Arduino length() == 0 (un texte ou un tableau) |
| `contient_texte`, `position_derniere` | Rust contains, rfind ; Arduino indexOf, lastIndexOf |
| `rogner_debut`, `rogner_fin` | Rust trim_start, trim_end (nettoyer : trim) |
| `sans_prefixe`, `sans_suffixe` | Rust strip_prefix, strip_suffix (le texte tel quel s'il n'y est pas) |
| `remplacer_premier` | Rust replacen(a, b, 1) |
| `lignes`, `mots`, `couper_en_deux` | Rust lines, split_whitespace, split_once (des tableaux de textes) |
| `caracteres`, `texte_de_caracteres` | Rust chars().collect(), String::from_iter |
| `egal_sans_casse`, `comparer_textes` | Rust eq_ignore_ascii_case, Ord::cmp ; Arduino equalsIgnoreCase, compareTo |
| `est_espace`, `est_majuscule`, `est_minuscule`, `est_alphanumerique`, `est_ponctuation`, `est_hexadecimal`, `est_ascii`, `est_controle` | Rust char::is_whitespace…, Arduino isSpace, isUpperCase, isLowerCase, isAlphaNumeric, isPunct, isHexadecimalDigit, isAscii, isControl |
| `valeur_chiffre`, `chiffre_de` | Rust char::to_digit, char::from_digit (absent : 18446744073709551615) |
| `texte_base`, `lire_base` | Rust format!("{:x}") et from_str_radix, Arduino String(n, HEX) (sans signe, base 2 à 36) |
| `completer_gauche`, `completer_droite` | Rust format!("{:0>8}"), pad_start |

## « tableaux » (Rust slice et Vec, itertools) : des tableaux d'entiers

*Machines : Lugus, Dunon.*

| Mots | Ce qu'ils font, d'où ils viennent |
|---|---|
| `premier`, `dernier` | Rust first, last (0 pour un tableau vide) |
| `echanger`, `remplir` | Rust swap, fill |
| `tourner_tableau`, `tourner_tableau_droite` | Rust rotate_left, rotate_right |
| `est_trie`, `trier_decroissant` | Rust is_sorted, sort_by(|a, b| b.cmp(a)) (signés) |
| `recherche_dichotomique` | Rust binary_search (dans un tableau trié, signé ; absent : 18446744073709551615) |
| `produit`, `moyenne`, `mediane` | Rust iter().product(), statistiques (un tableau vide : la moyenne est inconnue) |
| `cumul`, `differences` | itertools scan (les sommes au fil), windows(2) (les écarts successifs) |
| `fenetres`, `paquets` | Rust windows(k), chunks(k) (des tableaux de tableaux) |
| `aplatir`, `concatener`, `prolonger` | Rust concat (flatten), [a, b].concat(), extend |
| `dedoublonner` | Rust dedup (les répétitions qui se suivent ; sans_doublons : toutes) |
| `separer` | Rust split_at (deux tableaux) |
| `intervalle`, `intervalle_pas` | Rust (a..b).collect(), step_by (signés) |
| `zipper`, `entrelacer`, `produit_cartesien` | Rust zip, itertools interleave, iproduct! |
| `position_max`, `position_min`, `chercher_dernier` | itertools position_max, position_min ; Rust rposition |
| `tronquer_tableau`, `redimensionner`, `repeter_tableau` | Rust truncate, resize, repeat |
| `combinaisons`, `permutations` | itertools combinations(k), permutations (dans l'ordre ; prudence : n! tableaux) |

## « hasard » (rand, Arduino random) : la même suite à chaque lancement, comme hasard()

*Machines : Lugus, Dunon.*

| Mots | Ce qu'ils font, d'où ils viennent |
|---|---|
| `pile_ou_face`, `hasard_logique` | rand gen_bool(0.5), une valeur de Belnap tirée |
| `hasard_chance` | rand gen_bool(p) (1 avec la probabilité p) |
| `hasard_entre_flottant`, `hasard_normal` | rand gen_range(a..b), rand_distr Normal (Box et Muller) |
| `piocher_plusieurs`, `tirage_pondere` | rand choose_multiple (sans remise), WeightedIndex |

## « temps » (Arduino millis, delay) : horloge() est millis

*Machines : Lugus, Dunon.*

| Mots | Ce qu'ils font, d'où ils viennent |
|---|---|
| `attendre` | Arduino delay, std::thread::sleep (la machine compte ses millisecondes) |

## « vecteurs, quaternions, matrices » (UE FVector, FQuat, FMatrix ; Blender mathutils ; glam)

*Machines : Lugus, Dunon.*

| Mots | Ce qu'ils font, d'où ils viennent |
|---|---|
| `vecteur` | FVector(x, y, z), mathutils.Vector ; un tableau de flottants (v[0], v[1], v[2] ; les autres mots prennent aussi 2 ou 4 cases ; un quaternion : w, x, y, z, comme Blender ; une matrice : 16 cases, ligne par ligne) |
| `vecteur_somme`, `vecteur_difference`, `vecteur_echelle` | +, -, * k |
| `produit_scalaire`, `produit_vectoriel` | FVector::DotProduct, CrossProduct ; mathutils dot, cross |
| `norme`, `norme_carree`, `normaliser`, `distance` | Size, SizeSquared, GetSafeNormal, FVector::Dist ; length, normalized |
| `vecteur_interpoler` | FMath::Lerp sur des vecteurs, mathutils lerp |
| `reflechir`, `projeter`, `angle_entre` | FMath::GetReflectionVector, ProjectOnTo ; mathutils reflect, project, angle |
| `tourner_vecteur` | FVector::RotateAngleAxis (Rodrigues ; l'angle en radians) |
| `quaternion`, `quaternion_axe_angle` | mathutils.Quaternion((w, x, y, z)), FQuat(Axis, Angle) |
| `quaternion_produit`, `quaternion_conjugue`, `quaternion_normer` | q1 @ q2, conjugated, normalized |
| `quaternion_tourner` | FQuat::RotateVector, q @ v |
| `quaternion_interpoler` | FQuat::Slerp, mathutils slerp (par le plus court chemin) |
| `matrice_identite`, `matrice_produit`, `matrice_point`, `matrice_transposee` | FMatrix, mathutils.Matrix (4 × 4) |
| `matrice_translation`, `matrice_echelle`, `matrice_rotation` | Matrix.Translation, Matrix.Scale, Matrix.Rotation(angle, 4, axe) |

## « couleurs » (Blender, UE FLinearColor, FastLED CHSV)

*Machines : Lugus, Dunon.*

| Mots | Ce qu'ils font, d'où ils viennent |
|---|---|
| `couleur_tsv` | Blender « HSV to RGB », FastLED CHSV : teinte (degrés), saturation, valeur (de 0 à 1) vers (r, v, b) de 0 à 1 |
| `tsv_vers_rgb` | la même, en couleur de la machine (comme rgb(r, g, b), chaque voie de 0 à 255) |
| `srgb_vers_lineaire`, `lineaire_vers_srgb` | FLinearColor::FromSRGBColor, Blender (la courbe sRGB de l'IEC 61966-2-1) |
| `luminance` | Rec. 709 (Blender, UE GetLuminance) |

## « cube » : les places du cube chromatique (#RRGGBB)

*Machines : Lugus, Dunon.*

| Mots | Ce qu'ils font, d'où ils viennent |
|---|---|
| `adresse_point`, `coord_x`, `coord_y`, `coord_z` | la place d'un point et ses trois coordonnées (RR, GG, BB) |
| `voisin` | le point d'à côté sur un axe (0 : x, 1 : y, 2 : z), dans un sens (1 ou 18446744073709551615), le cube refermé |
| `morton`, `demorton_x`, `demorton_y`, `demorton_z` | les bits des trois coordonnées entrelacés (deux points proches, deux places proches) |
| `distance_cube` | la distance de Manhattan entre deux places (les pas d'un point à son voisin) |

## « codes » : l'ADN d'un entier de 64 bits (32 bases, A C G T : 0 1 2 3, la première au poids fort)

*Machines : Lugus, Dunon.*

| Mots | Ce qu'ils font, d'où ils viennent |
|---|---|
| `complement_adn`, `inverser_bases`, `anti_sens` | A↔T, C↔G (3 − q) ; les bases lues à l'envers ; le brin d'en face |
| `compter_base`, `teneur_gc`, `ecart_bases` | combien de fois une base, les G et les C, les bases qui diffèrent |

## « tableaux, avec une fonction » (Rust Iterator ; Lugus, et Dunon depuis la 0.65)

*Machines : Lugus, Dunon.*

| Mots | Ce qu'ils font, d'où ils viennent |
|---|---|
| `transformer`, `filtrer`, `plier`, `tous`, `au_moins_un`, `aucun`, `trouver_si`, `rang_si`, `compter_si`, `pour_chacun`, `garder_si`, `trier_par` | Rust map, filter, fold, all, any, !any, find, position, filter().count(), for_each, retain, sort_by_key (la fonction rend 1 ou 0 pour une question ; ces mots rendent 1 ou 0, ou 18446744073709551615 pour « absent ») |

*203 mots publics ; et, pour Dunon, le vocabulaire des nombres de 0.6za (signe, est_positif,
est_negatif, est_nul, est_entier, est_infini, est_su, partie_entiere, partie_decimale, entre, ecart, borne,
arrondi à n décimales), qu'il n'avait pas.*

## Ce qui n'y est pas, et pourquoi

- **les broches d'Arduino** (`pinMode`, `digitalWrite`, `analogRead`) : Lugus et Dunon n'ont pas de broches ;
  les simuler dans un tableau n'apprendrait rien. Elles viendront avec un service de la machine (un vrai port).
- **les bibliothèques entières** (Servo, Wire, les crates, les modules d'UE5 ou de Blender) : le vocabulaire
  prépare le branchement (vecteurs, quaternions, matrices, couleurs, interpolations) ; une extension se branche
  par ses mots, elle n'est pas recopiée.
- **`multiplier_ajouter` fusionné** (un seul arrondi) : fait en 0.65, exact sur les trois flottants, en entiers
  (les mantisses en grands entiers, un seul arrondi au plus proche, pair au milieu). (`reste` l'est depuis 0.61b.)
- **les itérateurs paresseux** de Rust (`map` sans tableau au bout) : vtx rend des tableaux.
- **les mots qui prennent une fonction** (`transformer`, `filtrer`…) : sur Lugus seulement (Dunon n'a pas
  encore les fonctions passées en valeur).
- **les tableaux de flottants ou de textes** pour `premier`, `dernier`, `moyenne`… : ces mots lisent des
  entiers (`t[0]` lit toujours bien un flottant ou un texte).
