# Les agents de Vercintorix : le Vergobret, Gutuater, le Druide (0.846)

*Décidé le 24 novembre, refait le 26 avec le créateur : « mieux répartir les rôles ». Remplace la conception du 24
(`docs/archives/gutuater-druide-conception.md`). Les trois sont des programmes déterministes et lisibles, pas une IA :
chaque décision se retrouve dans un carnet ; sans eux (`VTX_GUTUATER=0`), la forge est la même sur toutes les machines.*

## 1. Qui fait quoi : un moment, un rôle

| Agent | Son moment | Ce qu'il fait | Ce qu'il ne fait jamais |
|---|---|---|---|
| **Le Druide** | **l'écriture** (Ogmios, `lugus druide`) | il **conseille** : il lit le programme et dit ce qu'il voit, avec son état de Belnap ; il prépare les **potions** (le code proposé) ; il tient la **bibliothèque** (le code mort, ce qui définit quoi) ; il **se souvient** des bornes des variables (le relevé d'Ésus) et des cellules ; il **rapporte** ce que les autres agents ont appris | poser une potion sans le programmeur ; toucher l'ADN |
| **Gutuater** | **la forge** | il **choisit les gènes** (les variantes que la forge sait faire : la carte directe, le lot, fondre ; à terme Ésus et le dépliage, aujourd'hui choisis par l'évolution du Druide) ; il **garde** (une variante infidèle est tue pour toujours ; les mêmes mots) | inventer une variante ; écrire du code machine (le blocage des appels au système reste hors de lui) |
| **Le Vergobret** | **l'exécution** | il **mesure et choisit** : la carte ou le processeur, combien de fils, le lot exprimé ou non quand Gutuater ne sait pas ; il écrit ses mesures pour Gutuater | changer une largeur (il reste en 64 bits, côté graphique, sans bascule automatique : décision du 25 novembre) |
| **Ésus** (dans la forge) | **la forge** | l'épisseur du cœur : il prouve les bornes et prend l'opération de 64 bits quand tout y tient ; il change une division par une constante en multiplication | changer une valeur (sa preuve est sa garde) |

La chaîne : **le Druide** (ce qu'on écrit) → **Gutuater** (ce qu'on forge) → **le Vergobret** (ce qui tourne) → ses
mesures reviennent à Gutuater, et ce que Gutuater apprend revient au Druide, qui le dit au programmeur.

## 2. Une seule mémoire : le nemeton

Le **nemeton** (le sanctuaire) d'un programme est le dossier où vivent ce que ses agents savent de lui :
`VTX_NEMETON/NOM`, sinon `~/.vercintorix/nemeton/NOM` (NOM : le nom du fichier du programme, sans `.vtx`). Il ne dépend
ni du dossier où le programme est forgé ni du paquet livré : c'est ce qui manquait en 0.844 (chaque essai, décompressé
dans un dossier neuf, repartait d'un Gutuater qui ne savait rien).

| Fichier du nemeton | Écrit par | Lu par |
|---|---|---|
| `gutuater.mesures` | le Vergobret (et le programme forgé : « temps GENE LIEU VARIANTE µs ») | Gutuater |
| `gutuater.carnet` | Gutuater (ses synapses) | Gutuater |
| `gutuater.arn` | Gutuater (le plan : « GENE LIEU ÉTAT ») | la forge, le Vergobret, le Druide |
| `druide.conseils` | (à venir : la forge et le Druide d'évolution) | le Druide conseiller |

Un ARN posé à côté de l'exécutable passe avant le nemeton (les essais, les tests). `VTX_NEMETON_DIRE=1` dit où il est.
**Pas encore** : la mémoire du Druide d'évolution (ses cubes des bornes, PROG.esus, PROG.arn, PROG.conseils) vit encore à
côté de l'exécutable ; elle rejoindra le nemeton.

## 3. Une seule clé : l'empreinte

Le **lieu** d'un gène est l'empreinte de sa molécule et de son arbre sans les numéros de ligne (`lieu_de`, FNV-1a de
32 bits) : toucher le fichier ailleurs ne fait rien oublier. Le Druide range déjà ses cellules ainsi.

## 4. Une seule synapse

Les deux carnets suivent les mêmes règles de Belnap : il faut un poids de 3 d'un côté, et trois fois plus que de l'autre,
pour croire (vrai) ou nier (faux) ; sinon inconnu, ou variable quand les preuves se contredisent ; l'usure au-delà de 24 ;
une infidélité est une preuve contre définitive. Le seuil d'une petite preuve tremble (la résonance stochastique). La
synapse est écrite une fois, en vtx (`gutuater/synapse.vtx`) ; le Druide d'évolution en garde une copie qui suit les mêmes
règles (à fondre dans `synapse.vtx`).

## 5. Le Druide dans Ogmios (0.846)

Après F5, ou par **Ctrl+D** (Exécuter, « Le Druide »), le Druide relit le programme enregistré et parle dans la **fenêtre
des explications** (en bas à droite), sous ce qu'explique la paillasse :

```
Le Druide :
· ligne 6 (à vérifier) : ce « selon » ne dit rien pour inconnu (personne n'a parlé) ni pour variable (les témoins se
  contredisent) : le programme n'y fera rien. Est-ce voulu ?
    la potion : inconnu { } variable { }
· ligne 14 (sûr) : une adresse du cube écrite à la main (@2[(49 << 24) + …]) : nommé, le cube se lit @cube_49[…], et le
  compilateur refuse qu'un autre le recouvre
    la potion : cube cube_49 @2 frequence 49;

Ce que savent les agents de ce programme :
· Gutuater : la carte directe (le monde d'un seul tenant au processeur) : vrai
```

Chaque conseil porte son état : **sûr** (vrai), **à vérifier** (inconnu), **selon le cas** (variable). Ce qu'il sait voir
aujourd'hui (`druide/conseiller.vtx`, écrit en vtx, embarqué dans Lugus et Ogmios ; `lugus druide PROG.vtx` le dit en
console) :

1. une constante définie deux fois (les compilateurs la prennent sans rien dire : la constante `VIDE` de la 0.831) ;
2. un `selon` sur un logique qui ne dit rien pour inconnu ou pour variable (la potion : les branches qui manquent) ;
3. une adresse du cube écrite à la main, ou une famille (la potion : la déclaration du cube nommé, la fréquence lue dans
   sa constante) ;
4. `entier_64` ou `long` dans un programme de Lugus (ils comptent en 128 bits) ;
5. `si … == vrai` (inconnu et variable rangés avec le non : selon le cas) ;
6. une fonction que rien n'appelle dans le fichier (la bibliothèque : du code mort, ou une fonction pour ceux qui
   l'importent : à vérifier) ;
7. ce que Gutuater a appris de ce programme (son ARN, dans le nemeton).

**Les potions sont proposées, jamais posées** : on les recopie depuis la fenêtre des explications. Le geste qui les pose
(à la bonne place, après la garde des mêmes mots) viendra ensuite. Le Druide lit les jetons du texte (pas l'arbre du
compilateur) : il peut se tromper de contexte, d'où l'état « à vérifier » quand il n'est pas sûr.

## 6. Ce qui reste (dans l'ordre)

- La mémoire du Druide d'évolution dans le nemeton ; sa synapse fondue dans `synapse.vtx`.
- Les gènes d'Ésus et du dépliage choisis par Gutuater (le Druide garde la connaissance, Gutuater la décision).
- Le geste qui pose une potion (dans Ogmios), avec la garde : les mêmes mots, la même sortie.
- Le Druide qui lit l'arbre du compilateur (vtxc128 sur une machine fille, comme le lecteur d'ADN) au lieu des jetons.
- La garde des mêmes mots, automatique (Gutuater compare vtx128.py et vtxc128 sur ce qu'il forge).
- Le Vergobret écrit en vtx.
