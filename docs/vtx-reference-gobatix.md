# Faire de VercinToriX une référence, et commencer Gobatix (25 novembre 2026, soir)

*Une proposition de Claude, à discuter avec le créateur. Rien n'est encore codé pour Gobatix.*

## 1. Ce qui fait d'un langage une référence

Un langage ne devient pas une référence par ses qualités seules. Il le devient quand trois choses se rencontrent :

1. **Une œuvre qui ne pouvait naître qu'avec lui.** C a eu Unix, Lua les jeux, Ruby le site Rails, Python la science.
   Pour VercinToriX, cette œuvre est **Gobatix** : un modeleur où la scène est un cube de points hex qui portent leur
   matière, où l'on creuse avec l'anti-cube, où une IA décrit et Gobatix construit. Aucun autre langage n'a le cube, le
   quaternaire et l'ADN dans son cœur : c'est là que vtx est imbattable, pas dans un duel de vitesse contre le C.
2. **Des mesures que tout le monde peut refaire.** L'épreuve de Gergovie (le C++, vtx au processeur, Taranis, les mêmes
   empreintes) et l'épreuve d'Alésia existent déjà : il faut les rendre publiques, stables, et les tenir à jour à
   chaque version, sur GitHub.
3. **Un socle qui ne bouge plus.** Une version 1.0 du langage : la syntaxe, le prélude et les mots de Lugus gelés (ce
   qui marche à la 1.0 marche toujours ensuite), la liste de sécurité du 128 comme une loi, une documentation qui
   s'apprend en une après-midi (le carnet, la syntaxe, des exemples courts qui montrent le quaternaire).

## 2. La méthode : Gobatix comme moteur de vtx

Plutôt que d'attendre que vtx soit fini pour commencer Gobatix, commencer Gobatix petit, **maintenant**, et laisser
ses besoins dicter ce que vtx doit encore apprendre. Chaque manque rencontré devient une tâche du langage, mesurée,
puis gelée. C'est la façon la plus sûre de ne pas se perdre : on sait toujours pour quoi on travaille.

### Gobatix 0.1 : le cube de modélisation

- Un cube de modélisation (par exemple 256³ points) dans le cube chromatique : chaque point, un hex qui porte sa
  couleur et sa matière (reflet, lumière, transparence, profondeur, rugosité).
- Trois gestes : **poser** (de la matière), **creuser** (l'anti-cube : l'antimatière additionnée au modèle),
  **peindre** (changer la couleur et la matière sans toucher la forme).
- Les pinceaux en quaternaire : vrai (le point est posé), faux (il est creusé), inconnu (pas touché), variable (le
  bord, la pénombre de la forme : ce qu'un lissage ou l'IA tranchera).
- La vue par Belenos : le rayon de Gergovie sert déjà à voir un cube de points ; Taranis le montre sur la carte.

### Gobatix 0.2 : la scène est un ADN

- Le modèle enregistré est un ADN (ce qui dure, vérifié par ses trois témoins) ; chaque geste est de l'ARN (le
  travail) : annuler, refaire, l'historique, c'est relire l'ARN. Le chemin cube → hex → ADN → ARN est le format même
  du fichier.

### Gobatix 0.3 : la fenêtre et la main

- Une fenêtre à part (comme Ogmios), la souris, les outils sur le côté ; la paillasse peut piloter Gobatix (une case
  « poser », une case « creuser »).

### Gobatix 0.4 : ne pas vivre en vase clos

- Exporter et importer des formats courants (voxels, nuages de points, maillages OBJ ou PLY) : un modèle fait dans
  Gobatix doit pouvoir partir ailleurs, et l'inverse.

### Gobatix 0.5 : l'IA qui modélise

- Une scène décrite en texte (une porte, un mur, un arbre : des points hex et des matières) que Gobatix construit :
  la promesse de départ (« une IA décrit, Gobatix construit »).

### Ensuite : l'animation

- Les images clés comme de l'ARN, le rendu de films par Belenos ; puis le montage, plus tard.

## 3. Ce que vtx doit garder en tête pendant ce temps

- **La vitesse au processeur** : vtx est encore derrière le C++ (21,4 contre 33,3 images par seconde sur Gergovie) ;
  Gobatix en profitera à chaque gain, et ses besoins diront où chercher.
- **L'autonomie** (les exécutables sans Rust) : toujours bloquée sur les appels système ; elle n'empêche pas de
  commencer Gobatix.
- **Ogmios** : Gobatix s'appuiera sur ses fenêtres ; ce qui manque à l'un servira à l'autre.

## 4. La méthode de l'ombre du créateur (à reprendre)

L'alternance sur les points négatifs de la clepsydre, qui désignent l'ombre : positif, négatif, cube, anti-cube,
forme. Ce que Claude en comprend, à vérifier avec lui : l'ombre vit dans l'anti-cube comme un dépôt négatif ; une
image refait le côté positif de la clepsydre (la lumière), la suivante le côté négatif (l'ombre) ; chaque dépôt
persiste deux images avant d'être remplacé (la persistance qu'il voulait pour que ça coule) ; Belenos en a la charge,
avec la maîtrise des lots de cubes, de pixels et de l'ARN qu'ont Gutuater et le Vergobret.
