# La carte de Vercintorix, en une page (16 novembre 2026, 0.6y)

*Pour s'y retrouver : chaque chose, à quoi elle sert, où on la voit.*

## 1. Les machines : où tourne un programme

| Nom | Ce que c'est | État |
|---|---|---|
| **Lugus** | la machine de vtx : mots de 128 bits, quatre étages de mémoire en cube | la principale ; tout ce qui est neuf arrive ici |
| **Dunon** | la même chose à 64 bits | suit Lugus pour l'essentiel |
| **Senos** | l'ancienne machine à 32 bits | gelée : elle lit les vieux programmes, ne reçoit plus rien |

La machine n'existe pas en matériel : `lugus` la joue sur le PC.

## 2. Les outils : qui fait quoi

| Nom | Il sert à | Écrit en |
|---|---|---|
| **vtxc128** | compiler un texte vtx en mots de Lugus | vtx (se compile lui-même) |
| **vtx128.py** | la référence : doit donner les mêmes mots que vtxc128 | Python (le témoin, pas l'outil) |
| **Ogmios** (`atelier.exe`) | écrire, lancer (F5), voir la paillasse, la carte, le cube | Rust |
| **le lecteur d'ADN** | ranger, vérifier, réparer, juger les promesses | vtx |
| **Gobannos** | faire un .exe (Windows) ou un programme Linux à partir des mots | vtx |
| **la bibliothèque des flottants** | les flottants des .exe de Gobannos | vtx |
| **Belenos** / **Taranis** | les images / la carte graphique | vtx et Rust |

## 3. Le chemin d'un programme

```
texte .vtx ──vtxc128──▶ mots ──▶ ARNc (le travail) ⇄ ADN (le gardé) ⇄ hex (lisible) ⇄ cube (la mémoire)
                          └──Gobannos──▶ .exe
```

- **Les mots** : le programme compilé. `lugus PROG.vtx` compile et lance.
- **L'ADN** : les mots rangés pour durer, avec trois témoins qui réparent une avarie, le texte et la carte.
  `lugus ranger PROG.vtx`. L'**ARNc** est la même chose, en version de travail : `lugus arnc PROG.vtx`.
- **Le hex et le cube** : les mêmes mots, écrits pour l'œil (hex) ou rangés dans la mémoire en cube. Chaque station
  rend les mêmes mots dans les deux sens.

## 4. Les cubes : la mémoire

- Une adresse est un point du cube `#RRGGBB` ; **quatre étages**, et l'étage est un quit :
  0 le code et la pile, 1 les cubes (les images), 2 le travail, 3 le tas (textes, tableaux), les souvenirs et la provenance.
- Plusieurs cubes par étage, choisis par leur **fréquence** ; un cube peut être rangé sur le disque, avec son anti-cube
  et son ombre (ils réparent une avarie).
- On les voit dans Ogmios (la vue du cube).

## 5. Les faces : ce que la carte dit de chaque fonction

Chaque fonction compilée (une **molécule**) a six faces, deux à deux, et un centre. On les lit par
`lugus carte PROG.vtx`, ou dans Ogmios après F5 (la fenêtre des explications).

| Paire | Face | Face opposée |
|---|---|---|
| dedans / dehors | **ce qu'elle est** (nom, lignes, taille) | **ce qu'elle touche** : rien, lit la mémoire, l'écrit, le monde |
| d'où elle vient | **ses racines** (qui l'appelle) | **ses branches** (ce qu'elle appelle) |
| le temps | **ses promesses** (`touche rien`, `exige`…) | **sa mémoire** (a-t-elle changé depuis le dernier rangement ?) |

**Le centre** : son état à cette lecture, en quatre valeurs (intacte, réparée, abîmée, sans témoins).

## 6. Les quatre valeurs, partout

inconnu (personne n'a rien dit), faux, vrai, variable (oui et non à la fois). Un `logique` ne sert pas de condition de
`si` : on écrit `selon`, qui oblige à traiter les quatre. On les retrouve dans les lectures du clavier, `supposons … retenir`
(le verdict), les flottants (inconnu et variable au lieu d'un seul NaN), le centre des faces, les cylindres.

## 7. Ce qui n'est pas encore en vtx (l'autonomie)

| Encore en Rust | Pourquoi |
|---|---|
| la machine Lugus elle-même | il faut une machine pour jouer vtx ; Gobannos devra se traduire lui-même pour s'en passer |
| Ogmios (la fenêtre) | Windows pur ; une version en vtx existe, plus simple |
| la traduction des .exe de `vtx exe128` | Gobannos la remplacera quand il sera aussi rapide |

Python ne sert plus qu'aux **témoins** (les références qui vérifient) et aux tests.

## Si tu ne retiens que trois choses

1. On écrit du vtx ; `lugus` le lance ; Ogmios est l'atelier.
2. Le programme se range en ADN, qui se vérifie et porte sa carte (les six faces).
3. Gobannos en fait un .exe, sans Rust ni Python.
