# La liste de sécurité du 128 (décidée le 25 novembre 2026, 0.842)

Le cœur de Vercintorix compte en 128 bits. Ce qui suit reste en 128 : ni le Druide, ni Gutuater, ni Ésus, ni un réglage
automatique ne le passent en 64. Seul le créateur peut changer cette liste.

## Ce qui reste en 128, toujours

1. **L'entier par défaut de Lugus** : le choix du créateur (le 24 novembre). `0 - 1` vaut -1 sur tout le mot.
2. **Le cœur de vtx** : les deux compilateurs de Lugus (`vtx128.py`, `vtxc128`), leur prélude, la machine Lugus (mots,
   registres, mémoire de 128 bits) et ses services (SYS, ENTC à toute la largeur ; inconnu et faux sur tout le mot).
3. **Le cube mère de Lugus et les cubes des programmes** (`cube128-…`) : les mots de 128 bits, les adresses longues
   (étage 127-126, 120 bits), les pages, l'anti-cube et l'ombre (les sommets de secours).
4. **Le cube chromatique** : le point (#RRGGBBAA étendu), le point de matière, les 64 quits d'un mot, Belnap sur tout le
   mot (QEGAL, ET4, OU4, NON4, ANTI).
5. **Les nombres larges** : `entier_128` (`petuar`), `flottant_petuar`, la division de 128 bits de Gobannos.
6. **La mémoire du Druide** : ses cubes (les six points des variables, les codons, les synapses, la lignée, les
   cellules), sous le cube mère du programme.

## Ce qui est en 64 par nature (et n'est pas sur la liste)

- **Le graphique** : le Vergobret et Taranis travaillent avec les pilotes de la carte, donc en 64 bits au plus, sans
  option. Les programmes du graphique portent `dunon;` (Gergovie, Belenos).
- **Les formats d'échange qui sont de 64 bits** : les signatures et les neutrons de l'ADN (`adn.rs`, `chimie/adn.vtx`),
  les empreintes des modules, les hachages des dictionnaires, du catalogue et des tables de vtxc (masqués à 64 bits,
  pour garder les mêmes valeurs), le xorshift de `hasard`.
- **Le langage du SPU-64** (Dunon et ses suites).

## Ce que l'automatique a le droit de faire

- **Ésus** remplace une opération de 128 bits par une opération de 64 bits **seulement quand il prouve** que les
  opérandes et le résultat y tiennent : le résultat est exactement le même, rien n'est perdu. Cela vaut partout, la
  liste comprise, parce que la valeur ne change pas.
- **Gutuater** choisit à la forge des gènes qui ne changent aucune valeur (la carte directe, le lot, fondre…), en
  mesurant.
- **Le Druide** propose et fait évoluer l'ARN (Ésus connecté ou non, l'arrangement des cellules) ; il ne touche jamais
  l'ADN.
- **Un passage de 128 à 64 qui changerait une valeur** (couper un nombre) n'est jamais automatique : c'est un choix
  écrit par le programmeur (`dunon;`, et plus tard une largeur par molécule), et il est refusé sur ce qui figure dans la
  liste ci-dessus.
