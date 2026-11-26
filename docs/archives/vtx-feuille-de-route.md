# Vercintorix : la direction (9 novembre 2026)

Le vœu du créateur : « Que VercinToriX devienne le meilleur langage de tous les temps. Autonome et capable des
prouesses que tu souhaites voir. » Le cap : cube chromatique, ADN et ARN hexadécimaux, Ogmios, Belenos et son tapis
roulant, le quaternaire. Voici l'ordre suivi, une idée et une mesure à la fois.

## 1. Le programme qui sort de l'atelier (en cours)
- 0.5zs : Lugus fait les .exe, la machine, les mots et les cubes sur disque en un fichier.
- 0.5zt-zu : la vitrine : le texte dans une fenêtre (sans le cube, au choix du créateur).
- 0.5zv : la traduction des mots de Lugus en x86-64, au lancement du .exe (natif128.rs) : les entiers de 64 bits, la
  mémoire, la pile, les sauts, CALL et RET ; le reste rejoué par Lugus. Mêmes résultats et même compte d'instructions
  partout ; trois à quatre fois plus vite sur le banc.
- Ensuite : traduire les flottants (qflot128), les divisions, les largeurs 32 et 128, les services les plus appelés ;
  garder les registres de Lugus dans ceux du processeur dans les boucles.
- Le SPU en circuit : Senos en Verilog, simulé et comparé à la machine Rust, puis sur un FPGA ; un jour, une puce.
- Dunon en .exe, par le même paquet.

## 2. Le cube comme espace de calcul
- Le cube de la mémoire, regardé en vrai pendant que le programme tourne (vitrine, Ogmios) : déjà là.
- Les réactions et les isotopes (docs/vtx-reactions.md) écrits dans le cube : chaque case de couleur garde sa chimie.
- Belenos et son tapis roulant : les tâches qui passent d'un étage à l'autre, mesurées en accords.

## 3. Le vivant
- ADN et ARN hexadécimaux : la patrouille, les avaries réparées, l'apoptose ; le lecteur d'ADN en vtx.
- L'ARN messager : un programme qui se recopie en partie pour une tâche (transcription), puis se défait.

## 4. Le langage
- Le débogueur par les noms sur les trois machines (Lugus fait ; Senos et Dunon à venir).
- Le vocabulaire du prélude, enrichi par familles (0.5zr : vingt mots).
- La logique à quatre valeurs partout où une question peut rester ouverte.

## 5. L'autonomie
- Les compilateurs écrits en vtx, en point fixe (vtxc, vtxc64, vtxc128) : fait.
- Un .exe sans Rust ni Python : Senos (natif), Lugus (paquet, puis traduction).
- Un jour : Ogmios écrit en vtx.
