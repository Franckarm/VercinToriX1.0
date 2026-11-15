# Vercintorix : les fondements

*Gravé le 15 novembre 2026 (0.6r), à la demande du créateur : « inscrire le fonctionnement de vtx dans le marbre, dans
son innovation et son efficacité ». Ce qui est écrit ici ne change que par une décision du créateur ; le reste du
langage s'y conforme. Chaque règle dit pourquoi elle existe.*

## 1. Les quatre valeurs

| valeur | code | ce qu'elle dit | deux preuves (oui, non) |
|---|---|---|---|
| inconnu | 0 | personne n'a répondu | aucune |
| faux | 1 | non | celle du non |
| vrai | 2 | oui | celle du oui |
| variable | 3 | oui et non à la fois : une contradiction | les deux |

- C'est la logique de Belnap : deux bits de preuve. Trois valeurs portent une preuve, la quatrième (inconnu) est
  l'indicateur de son absence.
- **On ne la réduit jamais à deux.** Un logique ne sert pas de condition de `si` : on écrit `selon`, qui doit traiter
  les quatre cas (ou `== vrai`). Le compilateur refuse une branche de `selon` qui ne peut jamais servir.
- Pourquoi : savoir qu'on ne sait pas, et savoir qu'on est contredit, sont les deux choses qu'un programme binaire
  efface. C'est mesuré (le duel, le combat) : les mêmes décisions qu'un binaire juste, avec bien moins d'instructions.

## 2. Le quaternaire dans la machine

- Le **quit** (deux bits) est l'unité. Un mot de Lugus a 128 bits : 64 quits.
- **L'étage d'une adresse est un quit** (`adr >> 62`) : quatre étages, pas un de plus. L'étage 0 porte le code et la
  pile, le 1 les cubes, le 2 le travail, le 3 le tas, les souvenirs et la provenance.
- Le **cube chromatique** : une place est une couleur `#RRGGBB` ; chaque cube a son anti-cube et son ombre (le miroir
  qui le répare).
- Au-dessus de la machine, le langage peut offrir des plans virtuels (une table de correspondance) : le quaternaire
  reste dans l'adresse de la machine.

## 3. Deux compilateurs, les mêmes mots

- Chaque machine a deux compilateurs qui doivent donner **exactement les mêmes mots** : pour Lugus, `vtx128.py` (la
  référence, en Python) et `vtxc128` (écrit en vtx, embarqué dans Lugus après son point fixe) ; pour Dunon, `vtx64.py`
  et `vtxc64`. Senos (32 bits) est gelé : il se lit, il ne reçoit plus rien.
- Tout ajout au langage se fait dans les deux, et se vérifie mot pour mot.
- Pourquoi : un compilateur seul peut se tromper sans que personne le voie ; deux compilateurs écrits différemment qui
  s'accordent au mot près, c'est une preuve.

## 4. Le chemin et les brins

- **Un programme naît en ARN et se fixe en ADN.** U est le travail, T ce qui est gardé. `lugus arnc PROG.vtx` le fait
  naître en ARNc (tout ce que l'ADN porterait) ; `lugus retrotranscrire` le fixe en ADN.
- Les stations : vtx → ARNc ⇄ ADN ⇄ hex ⇄ cube. Dans les deux sens, **chaque station rend les mêmes mots**.
- Le chemin est fait en vtx, par le lecteur d'ADN (`chimie/adn.vtx`) : le langage se range, se lit, se répare lui-même.

## 5. Les témoins : aucune erreur muette

- Trois témoins indépendants gardent les mots : la **signature** de chaque molécule, l'**ombre** (Reed-Solomon sur des
  colonnes entrelacées), les **neutrons** (quaternaires, sur GF(4)).
- **La triangulation** : une réparation n'est gardée que si deux témoins l'appuient. Au-delà, la molécule est gardée
  telle qu'elle a été lue, pour la preuve, et l'état est variable.
- Le **texte gardé** et la signature du **compilateur** permettent la rétrotranscription : le texte redonne-t-il les
  mots ? vrai, faux (retouché), inconnu (le compilateur a changé).
- Mesuré : zéro réparation de travers, zéro avarie passée sans être vue, dans tous les essais.

## 6. La carte : six faces et un centre

Pour chaque molécule (une fonction, une réaction), trois paires opposées, comme les faces d'un dé :

| axe | une face | la face opposée |
|---|---|---|
| dedans, dehors | ce qu'elle est | ce qu'elle touche (rien, lit la mémoire, écrit la mémoire, le monde) |
| d'où elle vient | ses racines (qui l'appelle) | ses branches (ce qu'elle appelle) |
| le temps | ses promesses | sa mémoire (l'empreinte de son texte, son histoire d'un rangement à l'autre) |

**Le centre** est son état de Belnap **à chaque lecture** : intacte, réparée, abîmée sans réparation, ou inconnue.

## 7. Les promesses : la carte constate, la promesse engage

- Le programmeur promet ; la machine vérifie ; **une promesse rompue arrête** la compilation et le rangement, avec ce
  qui la rompt :
  - `touche rien | lecture | memoire | monde` : ce qu'une fonction touche au plus, elle et ses appels ;
  - `exige`, `garantit` : les contrats d'une réaction ;
  - `exemple f(2) == 4` : rejoué à chaque compilation ;
  - les unités physiques (des mètres ne s'ajoutent pas à des secondes) ;
  - `lourd` : un calcul critique, surveillé à l'entrée et à la sortie.
- Pourquoi : ce qui est promis et vérifié, une IA (ou un humain) peut s'y fier sans relire le code. C'est ce qui rend
  vtx natif pour l'IA.

## 8. Le doute ne se comble pas

- Ce qui n'est pas su est dit **inconnu**, jamais deviné : un brin sans carte n'a pas de noms, et la carte le dit.
- Quand il faut choisir sans savoir, le doute va du côté prudent : un service dont on ne retrouve pas le numéro compte
  pour « le monde ».
- La grammaire, elle, n'a pas d'ambiguïté : le texte d'un programme ne se lit que d'une façon. L'ambiguïté vit dans le
  sens (les quatre valeurs, et plus tard les lectures : `supposons … parmi`), pas dans l'écriture.

## 9. Le crible : chaque ajout se mesure, et ce qui ne sert pas se retire

- Chaque ajout vient avec son essai chiffré. On dit ce qui ne marche pas.
- Trois couches qui servent, plutôt que vingt : ce qui ne sert pas est retiré (la queue de l'ARN l'a été le soir même).
- La vitesse ne passe jamais avant le fonctionnement natif (le chemin, l'épissage, les atomes et les molécules,
  Belenos). Les écarts avec C et Rust sont dits tels qu'ils sont mesurés.

## 10. Comment on ajoute

1. Les deux compilateurs (les mêmes mots), et le lecteur en vtx s'il est touché ;
2. la référence en Python, quand il y en a une (le même résultat, octet pour octet) ;
3. un test qui le prouve, joué par `verifier.py` ;
4. la documentation (`docs/vtx-reactions.md`, la syntaxe), et un essai sur le PC du créateur par un `.bat`.

## Le vocabulaire, en une ligne chacun

| mot | ce que c'est |
|---|---|
| molécule | une fonction ou une réaction compilée ; atome : une ligne d'une réaction ; liaison : une donnée qui va d'un atome à un autre |
| ADN | le programme rangé pour durer : ses mots, ses témoins, son texte, sa carte |
| ARN, ARNc | une copie de travail tirée de l'ADN ; l'ARNc porte tout (on le rétrotranscrit en ADN entier) |
| isoforme | une sorte d'ARN : rapide (les mots seuls), sur (avec les témoins), memoire (avec ce qui est appris), complet, arnc |
| épissage | ce qu'on retire de l'ADN pour faire un ARN |
| intron | une section de l'ADN que le lecteur garde sans la comprendre (le texte, la carte…) |
| coiffe | la signature des mots d'un ARN, vérifiée avant de le lancer |
| signature, ombre, neutrons | les trois témoins (voir 5) |
| isotope lourd | une réaction marquée `lourd` : ses mots gardent leurs neutrons, la patrouille la relit à l'entrée et à la sortie |
| patrouille, apoptose | la relecture du code pendant qu'il tourne ; l'arrêt plutôt qu'un résultat incertain |
| épigénome | les souvenirs appris (des fonctions pures), gardés dans l'ADN |
| codon, gène | trois lectures lues ensemble ; une chaîne de codons |
| hex, cube | les mots écrits à la main de l'homme, chacun à sa place ; les mots rangés dans la mémoire en cube |
| Lugus, Dunon, Senos | les machines de 128, 64 et 32 bits ; Ogmios : l'atelier ; Belenos : le moteur graphique ; Taranis : la carte graphique |
