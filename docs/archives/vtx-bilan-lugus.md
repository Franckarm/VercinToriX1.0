# Bilan : de la forge (0.5i) à Lugus et à la chimie (31 octobre 2026)

Ce qui a été ajouté, ce qui a été retiré ou laissé de côté, et les mesures refaites de Fibonacci à l'ADN. Depuis la
livraison 0.5i (la forge du SPU-32 et le labyrinthe).

## 1. Ajouts

### Lugus, la machine de 128 bits

| Ajout | Ce qu'il fait | Vérifié par |
|---|---|---|
| Spécification de Lugus (`docs/specification-spu128.md`) | mot de 128 bits, deux instructions par mot, largeurs .64 et .32, voies, matière, adresse courte | relue, puis codée deux fois |
| Machine de référence en Python (`spu128/spu128.py`) | la référence exacte (flottants en fractions) | `spu128/test_spu128.py` |
| Machine Rust (`lugus`) | la machine rapide ; chemin court en u64 pour les entiers de 64 bits | 9 000 programmes au hasard identiques à la référence, corpus de conformité |
| vtx128 (`vtx128.py`) | le langage sur Lugus : flottant de 128 bits par défaut, `entier_petuar`, le point de matière | suite de 94 tests ; 348 programmes aux mêmes sorties que Dunon |
| Bibliothèque mathématique de 128 bits | exponentielle, logarithme, sinus… puissance | à moins de 3 ulps (puissance : 7) contre une référence à 80 chiffres |
| vtxc128 (`vtxc/vtxc128.vtx`) | le compilateur écrit en vtx ; `lugus PROG.vtx` compile et lance sans Python | mêmes mots que vtx128.py, point fixe (il se compile lui-même) |
| La forge de Lugus (`forge/forge128.py`) | vtx → Rust → natif, avec la mémoire, le brin et les services de Lugus | mêmes sorties et même mémoire finale que Lugus émulé |
| L'atelier sur Lugus | troisième machine : F5, pas à pas en demi-mots, registres de 128 bits, points de matière dans le cube (transparence en alpha), Gobatix | `vtx-spu essai-pas128` |
| Exemples (`exemples128/`) | bonjour128, degrade128 | émulés, forgés et au pas à pas : identiques |

### Les noms gaulois

Senos (SPU-32), Dunon (SPU-64), Lugus (SPU-128) dans l'atelier : titre, menu, bouton, terminal, en-tête des programmes.

### La chimie de Vercintorix (`docs/vtx-chimie.md`)

Conception validée : la liaison est la donnée, les atomes (C, H, O, N) sont le code, le cube est le support, Fischer
l'indexation des colonnes, la surface façon Blueprint la syntaxe, Belnap la synchronisation, l'épissage là où la mesure
le montre utile. Maquette publiée : **la paillasse** (`surface/paillasse.html`).

### La vitesse : les trois essais

| Essai | Résultat | Gardé ? |
|---|---|---|
| 1. L'adaptation automatique (la forge range serré un tableau que seul son nom touche) | crible 4,2 → 1,8 fois le C ; tri 2,0 → 1,4 | **oui** |
| 2. Les gaz nobles (ne plus vérifier le brin des pages fixées) | aucun gain mesurable : la vérification ne coûte déjà qu'aux pages qui portent un brin | non : rien à retirer |
| 3. Les flottants de 32 et 64 bits calculés par le matériel du processeur | Mandelbrot en flottant de 64 bits : 0,85 → 0,75 s (−12 %) ; mêmes bits que le calcul logiciel | **oui**, mais le gain est petit (voir 3.2) |

## 2. Retraits et choses laissées de côté

- **Rien n'a été retiré du code.** Senos et Dunon restent tels quels et vérifiés ; Senos reste gelé.
- **L'essai 2** n'a rien changé : il n'y avait rien à gagner.
- **gemv** (le produit matrice × vecteur) n'est pas encore traduit par la forge de Lugus : un programme qui l'appelle est
  refusé par la forge (il tourne sur Lugus émulé).
- **L'épissage des atomes** (à la transcription ADN → ARN) attend un essai qui montre un gain.
- **Le dossier `natif/`** n'a pas été touché, comme convenu.
- **L'atelier Windows** compile ici en mode de vérification seulement ; la vraie fenêtre se construit chez toi.

## 3. Les mesures, de Fibonacci à l'ADN

Médiane de cinq lancements, lancement du processus compris, sur la machine de travail de Claude (31 octobre).
Même algorithme, même résultat partout (sauf Mandelbrot : chaque format de flottant donne son propre total).

| Programme | C | Rust | Go | Java | JavaScript | Python | Senos forgé | Lugus forgé | Senos émulé | Dunon émulé | Lugus émulé |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fib | 0,004 | 0,007 | 0,013 | 0,080 | 0,052 | 0,28 | 0,008 | 0,012 | 0,66 | 0,75 | 1,24 |
| crible | 0,030 | 0,030 | 0,036 | 0,119 | 0,067 | 1,07 | 0,054 | 0,061 | 0,96 | 1,36 | 2,23 |
| mandel | 0,019 | 0,018 | 0,018 | 0,084 | 0,114 | 1,33 | 0,021 | 1,10 (0,75 en 64 bits) | 0,87 | 2,54 | 3,90 |
| tri | 0,046 | 0,045 | 0,045 | 0,224 | 0,106 | 1,13 | 0,063 | 0,069 | 0,72 | 0,86 | 1,46 |
| adn | 0,019 | 0,014 | 0,058 | 0,159 | 0,227 | 6,19 | 0,013 | 0,019 | 0,22 | 0,22 | 0,39 |

(secondes ; Java compte le démarrage de sa machine virtuelle, environ 0,05 s ; le C écrit par un expert pour l'ADN, 16
bases par mot : 0,008.)

### 3.1 Ce que disent ces chiffres

- **Forgé, vtx joue dans la cour du C, de Rust et de Go** sur les entiers : Senos forgé de 0,7 à 2,0 fois le C, Lugus
  forgé de 1,0 à 3,0 fois. Sur les entiers, il bat Java et JavaScript partout, et Python de 17 à 330 fois.
- **Sur l'ADN**, vtx égale le C écrit simplement, sur toutes ses machines forgées : le mot ADN range les bases et les
  compare d'un coup.
- **Lugus forgé est maintenant proche de Senos forgé** (crible 0,061 contre 0,054 ; tri 0,069 contre 0,063), alors que
  ses mots sont quatre fois plus grands : c'est l'adaptation automatique.
- **Émulé**, Lugus prend environ 1,7 fois le temps de Dunon émulé : chaque mot de 16 octets coûte plus cher à
  déplacer, et les instructions décodent deux largeurs.

### 3.2 Le flottant quaternaire : la limite honnête

Mandelbrot en flottant de 128 bits : 1,10 s, contre 0,84 s pour le C sur `__float128` (le binary128 logiciel de gcc) :
1,3 fois, une bonne place pour un format logiciel. En flottant de 64 bits, le calcul par le matériel n'a gagné que
12 % : chaque opération doit être ramenée sur la grille quaternaire, et cette chaîne de dépendances (convertir,
calculer, arrondir, reconvertir) coûte une quarantaine de cycles, contre quatre pour un double. La piste suivante :
garder les flottants de 64 bits en doubles entre deux opérations dans la forge (sans reconvertir), en espérant deux à
trois fois plus vite ; le flottant quaternaire restera plus lent que le double tant qu'il n'existe pas de processeur
quaternaire.

## 4. Vérification

`python verifier.py` : toutes les étapes (Senos, Dunon, Lugus, les compilateurs, les forges, l'atelier en console, les
flottants, les cubes sur disque, ScoR, la traduction native, les machines JavaScript). Résultat au 31 octobre :
**47 étapes, tout est conforme.**

Deux défauts trouvés en chemin et corrigés :
- le calcul des flottants par le matériel prenait l'infini pour un zéro ; la suite de vtx128 l'a vu (333 écarts sur les
  flottants de 32 bits), le banc d'essai contre les fractions exactes compte maintenant les infinis ;
- le banc d'essai des flottants, écrit le 25 octobre, fabriquait des nombres mal formés (presque tous « inconnu ») : ses
  1 400 000 « opérations identiques » ne prouvaient presque rien. Refait, il compare maintenant de vrais nombres des trois
  formats (plus de deux millions d'opérations, toutes identiques), et les accélérations du 25 octobre sont vérifiées.

## 5. La suite proposée

1. Les flottants de 64 bits gardés en doubles dans la forge (mesuré sur Mandelbrot).
2. La paillasse : tes retours sur la maquette, puis son portage dans l'atelier.
3. Les liaisons écrites dans le langage : elles lèvent la limite de l'adaptation automatique (savoir d'avance qui
   touche quoi) et ouvrent les réactions simultanées sur plusieurs cœurs.
4. La fiabilité : le miroir segmenté et la triangulation.
