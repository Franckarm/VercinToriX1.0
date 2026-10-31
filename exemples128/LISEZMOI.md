# Exemples de Lugus (le SPU-128)

Des programmes écrits dans le langage de Lugus : le flottant par défaut a 128 bits (quaternaire, 112 bits de
mantisse), l'entier par défaut reste de 64 bits, l'`entier_petuar` en a 128, et une couleur écrite (`#FF8000`) est un
point de matière : trois couleurs de 32 bits et sa matière (état, reflet, lumière, transparence, profondeur, rugosité).

La première ligne `// machine : lugus` fait ouvrir le programme sur Lugus dans l'atelier (les fichiers de ce dossier
s'y ouvrent de toute façon).

| Programme | Ce qu'il montre |
|---|---|
| `bonjour128.vtx` | pi à 33 chiffres, 30 ! en entier_petuar, un point de matière et un mélange |
| `degrade128.vtx` | une image de points de matière, la transparence qui descend de gauche à droite |
| `panel.vtx` | une réaction : un panel d'atomes rangés par vagues, l'élément déduit de la valence (`python vtx128.py molecule`) |
| `mandel_reaction.vtx` | Mandelbrot en réaction : les atomes lourds d'une même vague forgés sur plusieurs cœurs |
| `chute.vtx` | une réaction avec unités physiques (m, m/s², s), contrats (`exige`, `garantit`) et exemples vérifiés à la compilation ; `python vtx128.py run` (vtxc128 ne connaît pas encore les réactions) |

    lugus exemples128/bonjour128.vtx                 compile (vtxc128 embarqué) et lance, sans Python
    python forge/forge128.py exemples128/bonjour128.vtx   l'exécutable natif (forgé)
    vtx-spu essai-pas128 exemples128/degrade128.vtx  le pas à pas et la vue de l'atelier, sans fenêtre

Les exemples du SPU-64 (`exemples64`) sont écrits dans le langage du SPU-64 : sur Lugus, certains demandent une
conversion écrite (le flottant y a 128 bits).
