# Vercintorix : bilan des technologies, et l'atelier écrit en vtx

*23 octobre 2026. Partie 1 : sommes-nous raccord ? Ce qui est fait, ce qui est seulement sur le papier, ce qui diverge. Partie 2 : l'atelier « à la façon de VS Code », en vrai programme, écrit en vtx.*

## Partie 1 : bilan

### Les trois piliers gravés

| Pilier | Où il vit aujourd'hui | Raccord ? |
|---|---|---|
| **Cube chromatique** | La mémoire : 4 étages de 256³ points `#RRGGBBAA`, des cubes additionnés par fréquences, des cubes sur disque. L'atelier dessine le cube (perspective, à plat, en quits). Gobatix montre le cube des couleurs. | **Oui.** Écart : l'octet alpha décrit dans la spécification (quit d'étage, quit de type) n'est pas utilisé par la machine ; l'étage est dans les bits 24 et 25 de l'adresse. L'adresse longue du SPU-64 le replacera dans `AAAA`. |
| **Quaternaire** | Quits, littéraux `0q…`, `<<q`, `.q(i)`, LDQ et STQ, tableaux de quits, Belnap en instructions (ET4, OU4, NON4, ANTI, EXQ), QEGAL, COMPTE, MIN4, MAX4, ADDM4, le `flottant_petuar`. | **En partie.** Honnêtement : la machine calcule en binaire (Rust, Python) et le quaternaire est une lecture exacte des mêmes bits (un mot = 16 quits, l'addition binaire = l'addition quaternaire chiffre par chiffre). Le `flottant` (32 bits) et le `flottant_64` restent des formats IEEE binaires : le SPU-64 les remplacera par des flottants quaternaires. |
| **ADN / ARN** | `adn"…"` (jusqu'à 64 bases), `texte_adn`, `texte_arn`, la génomique (QEGAL, COMPTE), les hypothèses, le ScoR (l'ARN comme copie de travail, l'ADN comme résultat). | **En partie.** La synonymie T/U (canal caché, section 8 de la spécification) et l'idée « U porte l'hypothèse, T le statut » ne sont pas des types du langage : T et U valent tous deux 3. À décider : un type `brin` qui distingue T et U, ou laisser T/U à la seule lecture. |

### Les autres technologies

| Technologie | État | Remarque |
|---|---|---|
| Logique de Belnap (inconnu, faux, vrai, variable) | **Fait**, gardée (23 octobre) | Frontière binaire : `binaire()` et `quaternaire()`. |
| Fréquences, musique : accords, mesures, segments (cylindres en V6) | **Fait** | Les accords sont la partition des tâches ; les cubes s'additionnent par fréquence et portent des noms de notes (262 = do4). |
| Hypothèses (annuler, valider) | **Fait** | Le journal des écritures ; c'est la place naturelle de U. |
| Correction d'erreur diamant | **Fait** (bibliothèque) | |
| Épissage (le compilateur retire les « introns ») | **Fait** | Raccord avec l'ADN : vocabulaire et méthode. |
| Ombre du cube (projection 2D) | **Fait** (`ombre/`, `feu/`) | Ta remarque : le binaire y trouve sa place, puisqu'une ombre est une surface. Et « reporter l'ombre à réfléchir » : réfléchir l'ombre, c'est un lancer de rayons secondaires (reflets) ; `feu/` a déjà le parcours de rayons dans le cube, et le reflet en est le pas suivant. |
| GDOT, GEMV (produits sur les voies) | **Fait** | La base d'un futur calcul d'IA dans le cube. |
| ScoR (IA à spirale, épissage) | **En pause** | v1 : raisonnement, voix, mémoire. |
| Autonomie (vtxc se compile lui-même) | **Fait** | Python ne sert plus qu'aux tests. |
| Traduction native x86-64 (`natif/`) | **Mis de côté** | Elle traduit le SPU-32 ; le SPU-64 en demandera une autre. |
| Machines JavaScript | Faites, SPU-32 | À décider pour le SPU-64 : les garder (navigateur) ou non. |
| `flottant_petuar` (quaternaire, 128 bits) | **Fait** | Le modèle des futurs flottants quaternaires de 32 et 64 bits. |
| SPU-64, point profond, adresse longue | **Conçu**, pas codé | `claude/vtx-spu64-conception.md`. |
| Gobatix | Premier pas : service graphique, cube qui tourne, cube chromatique | Décidé : un cube vide comme zone de modélisation, de texture et de peinture, en xyz hexadécimal. |

### Points à raccorder (tes décisions)

1. **Coatvtx et Gobatix.** Coatvtx était le nom du futur programme de modélisation, PBR et animation, et Gobatix est maintenant le modeleur. Est-ce le même programme renommé, ou Gobatix (modeleur, peinture) d'abord, puis Coatvtx (rendu PBR, animation, montage) comme deuxième logiciel ?
2. **T et U** : un type qui les distingue, ou seulement la lecture ?
3. **Machines JavaScript** pour le SPU-64 : les garder ?
4. **La spécification matérielle** (lasers, MAR, prisme, disque spectral) : elle reste le but lointain. Le logiciel lui est fidèle par le format des mots, des instructions et de la mémoire. L'octet alpha, lui, n'y est pas encore (voir plus haut).

## Partie 2 : l'atelier écrit en vtx

### Ce qui est possible, honnêtement

« Entièrement en vtx » au sens strict est impossible sur un PC : il faut toujours quelqu'un pour ouvrir une fenêtre Windows et recevoir le clavier. Mais on peut ramener cette part à une couche très mince de la machine Rust, comme un système d'exploitation, et écrire **tout l'atelier en vtx** : l'éditeur, les onglets, l'explorateur, le terminal, la coloration, la vue du cube, le pas à pas. Le même `.exe` (vtx.exe) le lance, et l'atelier devient un programme vtx comme un autre, qui s'améliore en vtx.

### Ce que la machine doit offrir (services, peu nombreux)

| Service | Rôle | Existe ? |
|---|---|---|
| Fenêtre | montrer l'image de l'étage 1 | oui (12, `presenter`, double tampon ; 19, `cadence`) ; à étendre : taille de la fenêtre, redimensionnement |
| Événements | touches (avec Ctrl, Maj, Alt), caractères tapés, souris (position, clics, molette), fermeture | **oui** (0.5) : souris, molette, touches, touches enfoncées dont Maj, Ctrl, Alt, horloge (16 à 21) ; la fermeture : `presenter()` rend 1 |
| Fichiers | lire, écrire | oui (canaux) |
| Dossiers | lister un dossier | non : **nouveau** |
| Presse-papiers | copier, coller avec Windows | non : **nouveau** |
| Compiler et lancer | compiler un fichier avec vtxc, le lancer dans une seconde machine, lire sa sortie, son pas à pas et sa mémoire | non : **nouveau** (la machine sait déjà le faire pour l'atelier actuel) |

### Ce qui s'écrit en vtx

- **Le texte à l'écran** : une police à chasse fixe rangée dans un cube (des glyphes en quits), dessinée par le prélude.
- **L'éditeur** : tampon de lignes, curseur, sélection, annuler et rétablir, rechercher et remplacer, retrait automatique, coloration de la syntaxe vtx (mots-clés français, nombres, textes, commentaires).
- **La disposition à la façon de VS Code** : barre d'activité, explorateur de fichiers, onglets, éditeur, panneau du bas (Sortie, Terminal, Problèmes), barre d'état, palette de commandes (Ctrl+Maj+P).
- **Le propre de Vercintorix** : la vue du cube de la mémoire, le mot sous le curseur lu en hex, en quits et en ADN, le pas à pas (F7, F8, F9, F5), et plus tard la zone de Gobatix dans un onglet.

### Vitesse

La machine fait environ 180 à 300 millions d'instructions par seconde. Redessiner une fenêtre de 1280 × 800 entière coûte de 10 à 20 millions d'instructions, ce qui donne 15 à 30 images par seconde. Avec un redessin partiel (la seule ligne tapée), on passe à des centaines d'images par seconde. Ça suffit pour un éditeur, sans attendre la vitesse de l'autonomie.

### Ordre proposé

1. Les nouveaux services dans la machine Rust : événements, dossiers, presse-papiers, taille de la fenêtre. Leur version Python est pour les tests, avec des événements simulés.
2. La police et le texte dessiné (prélude), avec un test en images PNG.
3. L'éditeur seul : ouvrir, taper, enregistrer, avec la coloration.
4. La disposition (explorateur, onglets, panneau, barre d'état).
5. Compiler, lancer, la sortie, le terminal (service « compiler et lancer »).
6. La vue du cube et le pas à pas.
7. Remplacer l'atelier en Rust (`fenetre.rs`) quand l'atelier en vtx fait tout ce qu'il fait.

**Question de calendrier.** L'atelier en vtx peut commencer sur le SPU-32 actuel et passer au SPU-64 avec les compilateurs. L'ordre logique : l'atelier d'abord (outil de travail), puis le SPU-64 (qu'on développera alors dans le nouvel atelier). Ou bien le SPU-64 d'abord, pour ne pas écrire l'atelier deux fois. L'écart est faible : le code vtx de l'atelier se recompile, il ne se réécrit pas.
