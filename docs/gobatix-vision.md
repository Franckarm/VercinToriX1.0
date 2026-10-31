# Gobatix : la vision (notée le 31 octobre 2026, rien n'est codé)

Gobatix sera le logiciel de modélisation 3D et d'animation de Vercintorix, pour la création de films, en concurrent de
Blender. C'est le même programme que celui qu'on appelait Coatvtx. Il viendra **quand vtx sera au point** ; ce document
garde l'idée pour qu'elle ne se perde pas.

Le service d'image de la machine (`presenter()`, la fenêtre, les GIF), qui portait jusqu'ici le nom de Gobatix,
s'appelle désormais **la toile** (`vtx toile PROG.vtx`) : le nom Gobatix est réservé au logiciel.

## Trois logiciels distincts

| Logiciel | Pour qui | Ce qu'il fait |
|---|---|---|
| **L'atelier** | le programmeur | écrire, lancer et suivre pas à pas les programmes vtx ; la paillasse y viendra |
| **Gobatix** | le créateur d'images et de films | modéliser, texturer, peindre, animer, rendre |
| **Le montage** (plus tard) | le monteur | assembler les plans, le son, les effets |

## Les idées de l'utilisateur

- **Un cube formé exprès** pour la modélisation : un cube vide qui sert de zone de modélisation, de textures et de
  peinture, repérée en hex plutôt qu'en xyz. On doit aussi pouvoir modéliser sur la machine elle-même.
- **L'anti-cube de modélisation** : de l'antimatière qu'on pose pour creuser, additionnée au cube du modèle.
- **Une référence Hex comme point**, pour qu'une IA modélise rapidement un objet, une porte, une scène.
- **L'animation** derrière, pour la création de films.

## Ce qui rendrait Gobatix différent de Blender

- **L'IA d'abord.** Une IA écrit très bien du texte et mal des maillages de triangles. Une scène écrite en points Hex,
  chacun avec sa couleur et sa matière, est une langue qu'une IA sait écrire : elle décrit, Gobatix construit.
- **Des points de matière plutôt que des triangles.** Chaque point du cube porte sa couleur et sa matière (reflet,
  lumière, transparence, profondeur, rugosité) : la matière fait partie du modèle, pas d'une étape à part.
- **Le cube comme espace de la scène**, l'anti-cube pour creuser, Fischer pour retrouver vite un point.
- **Les liaisons** : des millions de points qui réagissent par vagues, en même temps.

Blender, c'est trente ans de travail : Gobatix ne gagnera pas en le copiant, mais par sa différence.

## Ce que vtx doit apporter avant

1. **Les liaisons et les vagues** (en cours de conception) : le calcul de millions de points en même temps.
2. **La densité** (l'adaptation automatique, faite pour les tableaux) : des scènes qui tiennent en mémoire.
3. **Le point de matière de Lugus** (fait).
4. **Fischer dans le cube** (conçu) : retrouver vite un point.
5. **La carte graphique** : le temps réel et le rendu de films demandent le GPU. vtx calcule aujourd'hui sur le
   processeur ; la forge devra aussi écrire pour la carte graphique (des programmes de calcul pour le GPU).
6. **Les formats d'échange** : lire et écrire les formats des autres logiciels, pour ne pas vivre en vase clos.
