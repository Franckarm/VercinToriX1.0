# Un seul compilateur (décidé le 27 novembre 2026, 0.851)

*La décision du créateur : passer de quatre compilateurs (six avec Senos) à un seul : **vtxc128**, écrit en vtx, qui se
compile lui-même. Dunon reste lui-même face à Lugus, et Lugus face à Dunon : **Dunon est `dunon;`** (ses règles de 64
bits, ses services, joué par la machine de Lugus, comme tout le graphique). La machine SPU-64 séparée est gelée, comme
Senos (le SPU-32).*

## Ce qui existe (avant)

| | Lugus (128) | SPU-64 séparé | Senos (SPU-32, gelé) |
|---|---|---|---|
| en Python | vtx128.py (13 700 lignes) | vtx64.py (10 900) | vtx.py |
| écrit en vtx | vtxc128 (15 000 lignes) | vtxc64 (10 500) | vtxc.vtx |

La règle d'avant : les deux compilateurs d'une machine donnent les mêmes mots. Elle a attrapé de vraies erreurs (le
`charger_l` de vtxc, les masques de 128 bits) ; elle double aussi chaque changement du langage, et la vérification dure
plus de deux heures.

**Ce qui tient à vtx128.py, en dehors de compiler :** la forge (`forge/forge128.py` lit et type chaque programme avec
son lecteur, son analyseur et son générateur) ; Taranis (les noyaux de la carte passent par la forge) ; le prélude et le
vocabulaire de vtxc (`vtxc/vocabulaire.py`, `vtxc/prelude128.py`) ; une cinquantaine de tests et d'outils.

## Le chemin

**Étape 0 (fait, 0.851).** `verifier.py` ne joue plus par défaut les étapes des machines gelées (20 étapes : le SPU-32,
le SPU-64 séparé, les machines JavaScript) ; `--geles` (ou `--complet`) les joue. Chaque étape dit son temps, et la fin
nomme les cinq plus longues. Rien n'est effacé.

**Étape 1, premier pas (fait, 0.851b).** `vtxc/test_vtxc128_seul.py` : vtxc128 vérifié sans Python. Le point fixe
part du compilateur embarqué dans lugus (optimisé : il retombe sur ses 279 122 mots ; non optimisé : M1 = M2). 88
programmes (la suite de vtx128.py, la suite de Lugus, les réactions des exemples, cinq erreurs, plus 28 programmes tirés
au hasard à graines fixes) sont compilés sous trois réglages : la même sortie, et celle du témoin
`tests/attendus/vtxc128_seul.json` (rangé quand les deux compilateurs donnaient encore les mêmes mots). Les programmes
tirés au hasard ne se jouent pas (certains tournent sans fin) : l'empreinte de leurs mots est gardée. Un exemple faux
arrête `lugus PROG.vtx`. Ogmios pas à pas : 42/42. Environ 7 minutes. Dans `verifier.py`, il remplace les deux contrôles
mot pour mot contre vtx128.py (19 minutes), qui ne se jouent plus qu'avec `--deux`.

**0.851c (fait)** : 21 tests compilent Lugus par vtxc128 seul (`tests/un_compilateur.py` : les gestes communs) :
codon, bords128, logiques128, duel, quatre vérités, combat, gutuater, druide conseiller, rangées128, supposons, valeurs,
nombres, types de fonction, promesses, reste, fma, modules, catalogue, cubes mères, faces, vocabulaire étendu. 

**Le témoin (décidé avec le créateur, 0.851d)** : la machine Python de vtx128.py reste, petite, à la main, pour voir si
une modification change ce que fait un programme. `tests/test_temoin_python.py` (une poignée d'exemples de Lugus joués
par lugus et par vtx128.py, ou les programmes donnés en argument) ; `verifier.py --temoin` le joue, avec les
comparaisons à la machine Python des tests du catalogue, des cubes mères et du combat (`VTX_TEMOIN=1`). Par défaut,
rien de Python ne joue un programme de Lugus. Un écart n'est pas forcément une erreur de lugus : le témoin peut être en
retard sur un mot ajouté seulement à vtxc128.

Restent : les réactions (`test_reactions.py` lit l'analyse de vtx128.py : les vagues, les souvenirs, la provenance),
fischer, provenance, paillasse, ogmios, gobannos (flottants), adn ; les tests Lugus et Dunon qui passent `vtx128` comme
module (gene, selon, vocabulaire, cubes nommés) ; et ceux qui vérifient vtx128.py lui-même (test_vtx128, son
différentiel, maths128), qui iront avec `--deux`.

Ce qui reste de l'étape 1 (avant 0.851c) : une quarantaine de tests compilent encore par vtx128.py (`tests/test_reactions.py`,
`test_modules.py`, `test_logiques128.py`, `test_types_fonction.py`, `test_provenance.py`…) ; ils passent à `lugus`, un
par un. Tant qu'ils ne sont pas passés, un mot nouveau du langage doit encore aller dans vtx128.py.

**Étape 1 : vtxc128, le seul qui écrit les mots.** vtx128.py ne sert plus qu'à la forge (lire, typer). Les tests « mêmes
mots que vtx128.py » deviennent « les mêmes résultats » (la sortie de Lugus, la sortie forgée, les empreintes de
Gergovie, l'épreuve d'Alésia) ; le point fixe de vtxc128 reste (il se compile lui-même et retombe sur ses mots). Le
prélude n'a qu'une source (`vtxc/vocabulaire.py`, qui l'écrit dans vtxc). Ce qu'on perd : le second regard mot à mot ;
on le compense par des tests de résultats, et par le point fixe.

**Étape 2 : un seul lecteur du langage.** vtxc128 écrit l'arbre typé du programme dans un fichier ; la forge (et donc
Taranis) le lit au lieu de relire le texte par Python. Le lecteur Python disparaît : un changement du langage ne se fait
plus qu'une fois, en vtx.

**Étape 3 : la forge en vtx.** Plus de Python dans le chemin d'un programme (le Rust reste l'hôte de la machine).

## Ce qui ne change pas

- La liste du 128 (`docs/vtx-liste-128.md`) ; le Vergobret en 64 bits ; le Druide sur l'ARN et le cube, jamais l'ADN.
- `dunon;` : un programme du graphique compte en 64 bits, ses services sont ceux de Dunon.
- Chaque essai joue les trois : le C++, vtx au processeur, Taranis.
