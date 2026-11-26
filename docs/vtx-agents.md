# Les agents de Vercintorix : le Druide, Gutuater, le Vergobret (0.847)

*Décidé le 24 novembre, refait le 26 avec le créateur. Chaque agent a sa maison : le Druide dans le langage, Gutuater
dans le processeur, le Vergobret dans la carte graphique. Remplace la conception du 24
(`docs/archives/gutuater-druide-conception.md`) et la répartition du matin du 26 (où le Vergobret tenait l'exécution
en général : c'était faux). Les trois sont des programmes déterministes et lisibles, pas une IA : chaque décision se
retrouve dans un carnet ; sans eux (`VTX_GUTUATER=0`), la forge est la même sur toutes les machines.*

## 1. Qui fait quoi : une maison, un rôle

| Agent | Sa maison | Ce qu'il fait | Ce qu'il ne fait jamais |
|---|---|---|---|
| **Le Druide** | **le langage** (Ogmios, `lugus druide`, la forge) | il **conseille** : il lit le programme et dit ce qu'il voit, avec son état de Belnap ; il prépare les **potions** (le code proposé) ; il tient la **bibliothèque** (le code mort, ce qui définit quoi) ; il **fait évoluer** le cœur (Ésus, le dépliage : `druide/druide.vtx`) ; il **rapporte** ce que les deux autres ont appris | poser une potion sans le programmeur ; toucher l'ADN |
| **Gutuater** | **le processeur** : le graphisme et la 3D quand ils tournent au processeur | il tient les gènes du processeur : la **carte directe** (le monde d'un seul tenant), les **fils** (combien de cœurs pour une boucle : le réglage, `gutuater.savoir`), la carte des pages de l'étage 2 ; il mesure, apprend, se souvient (`gutuater/gutuater.vtx`) | inventer une variante ; écrire du code machine (le blocage des appels au système reste hors de lui) |
| **Le Vergobret** | **la carte graphique** (Taranis) | il tient les gènes de la carte : le **lot** (les boucles d'une image en un envoi), **fondre** (le lot en un seul noyau, avec sa garde), le choix **la carte ou le processeur** pour une boucle qui sait aller à la carte (`vergobret/vergobret.vtx`) | changer une largeur (il reste en 64 bits, sans bascule automatique : décision du 25 novembre) |
| **Ésus** (dans la forge) | le cœur, conduit par le Druide | l'épisseur : il prouve les bornes et prend l'opération de 64 bits quand tout y tient ; il change une division par une constante en multiplication | changer une valeur (sa preuve est sa garde) |

La chaîne : **le Druide** (ce qu'on écrit) → la forge → le programme forgé, qui mesure : ce qui tourne au processeur va
à **Gutuater**, ce qui tourne sur la carte au **Vergobret** ; chacun en tire son ARN, que la forge et le programme
lisent ensuite, et le Druide le dit au programmeur.

Les deux carnets suivent la même loi des preuves : un seul moteur, `gutuater/carnet.vtx` (avec `synapse.vtx`), que
`gutuater.vtx` et `vergobret.vtx` appellent chacun sous son nom. Les messages du programme forgé (`VTX_REGLAGE=1`)
disent qui parle : « gutuater : la boucle de la ligne … : apprend, 2 cœur(s) », « vergobret : le lot … : fondu … ».

## 2. Une seule mémoire : le nemeton

Le **nemeton** (le sanctuaire) d'un programme est le dossier où vivent ce que ses agents savent de lui :
`VTX_NEMETON/NOM`, sinon `~/.vercintorix/nemeton/NOM` (NOM : le nom du fichier du programme, sans `.vtx`). Il ne dépend
ni du dossier où le programme est forgé ni du paquet livré : c'est ce qui manquait en 0.844 (chaque essai, décompressé
dans un dossier neuf, repartait d'un Gutuater qui ne savait rien).

| Fichier du nemeton | Écrit par | Lu par |
|---|---|---|
| `gutuater.mesures` | le programme forgé, au processeur (« temps carte_directe 0 VARIANTE µs ») | Gutuater |
| `gutuater.carnet`, `gutuater.arn` | Gutuater (ses synapses ; le plan : « GENE LIEU ÉTAT ») | la forge (la carte directe), le Druide |
| `vergobret.mesures` | le programme forgé, sur la carte (« mesure lot LIEU A B », « infidele fondre LIEU ») | le Vergobret |
| `vergobret.carnet`, `vergobret.arn` | le Vergobret | le programme forgé (le lot, fondre), le Druide |
| `druide.conseils` | (à venir : la forge et le Druide d'évolution) | le Druide conseiller |

Un ARN posé à côté de l'exécutable passe avant le nemeton (les essais, les tests). `VTX_NEMETON_DIRE=1` dit où il est.
**Pas encore** : la mémoire du Druide d'évolution (ses cubes des bornes, PROG.esus, PROG.arn, PROG.conseils) vit encore à
côté de l'exécutable ; elle rejoindra le nemeton.

## 3. Une seule clé : l'empreinte

Le **lieu** d'un gène est l'empreinte de sa molécule et de son arbre sans les numéros de ligne (`lieu_de`, FNV-1a de
32 bits) : toucher le fichier ailleurs ne fait rien oublier. Le Druide range déjà ses cellules ainsi.

## 4. Une seule synapse

Les carnets suivent les mêmes règles de Belnap : il faut un poids de 3 d'un côté, et trois fois plus que de l'autre,
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
· le Vergobret : le lot 670194876 (les boucles de la carte en un envoi) : vrai
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
7. ce que Gutuater et le Vergobret ont appris de ce programme (leurs ARN, dans le nemeton).

**Les potions sont proposées, jamais posées** : on les recopie depuis la fenêtre des explications. Le geste qui les pose
(à la bonne place, après la garde des mêmes mots) viendra ensuite. Le Druide lit les jetons du texte (pas l'arbre du
compilateur) : il peut se tromper de contexte, d'où l'état « à vérifier » quand il n'est pas sûr.

## 6. Ce qui reste (dans l'ordre)

- La mémoire du Druide d'évolution dans le nemeton ; sa synapse fondue dans `synapse.vtx`.
- Les gènes de Gutuater qui manquent : les bandes et les segments (aujourd'hui choisis par la forge), la place des
  cubes en mémoire (voir l'écart avec le C++, `vtx-passation.md`, 0.847).
- Le geste qui pose une potion (dans Ogmios), avec la garde : les mêmes mots, la même sortie.
- Le Druide qui lit l'arbre du compilateur (vtxc128 sur une machine fille, comme le lecteur d'ADN) au lieu des jetons.
- La garde des mêmes mots, automatique (Gutuater compare vtx128.py et vtxc128 sur ce qu'il forge).
- Le réglage des fils (le choix des cœurs) écrit en vtx, dans Gutuater.
