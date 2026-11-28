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

**0.851e : les réactions.** `tests/test_reactions.py` joue tout par lugus (41 vérifications : sorties, contrats,
exemples, unités, erreurs, tableaux, la forge) ; ce qui lit l'intérieur de vtx128.py (la molécule, ses vagues et sa
formule ; les souvenirs et ce qu'ils épargnent ; la provenance, « vtx128.py pourquoi » ; le drapeau d'erreur) passe dans
`tests/test_reactions_lecteur.py` : ce sont les gestes du lecteur de la forge, qui restent jusqu'à l'étape 2 (alors
vtxc128 devra les montrer lui-même, par la carte).

**0.851f : l'étape 1 est faite.** Aussi par vtxc128 seul : Ogmios, Gobannos (les flottants), l'ADN (l'isotope : le
lecteur de référence range avec et sans « lourd »), la provenance (`lugus pourquoi`), la paillasse (ce que lit vtx128.py
est rangé dans `tests/attendus/paillasse.json`), gène, selon, vocabulaire, cubes nommés, maths128, modules. La suite de
vtx128.py elle-même (`test_vtx128.py`) et les deux anciens contrôles mot pour mot passent sous `--deux`.

**Ce qui tient encore à vtx128.py, et pourquoi :**
- **le lecteur de la forge** (`forge/forge128.py`, donc Taranis) : l'étape 2 ;
- **ce que lit ce lecteur** : `test_reactions_lecteur.py` (la molécule, les souvenirs, la provenance), `test_fischer.py`
  (chimie/fischer.py signe les molécules qu'il lit), `forge/test_forge128.py` ;
- **le lecteur d'ADN de référence** (`chimie/adn.py`), et le prélude de vtxc (`vtxc/prelude128.py`, `vocabulaire.py`) ;
- **le témoin** (à la main : `--temoin`) ;
- `vtxc/test_vtxc128_seul.py` lit la liste de ses programmes de test (`vtx128.TESTS`), sans rien compiler par lui.

**Étape 1 : vtxc128, le seul qui écrit les mots.** vtx128.py ne sert plus qu'à la forge (lire, typer). Les tests « mêmes
mots que vtx128.py » deviennent « les mêmes résultats » (la sortie de Lugus, la sortie forgée, les empreintes de
Gergovie, l'épreuve d'Alésia) ; le point fixe de vtxc128 reste (il se compile lui-même et retombe sur ses mots). Le
prélude n'a qu'une source (`vtxc/vocabulaire.py`, qui l'écrit dans vtxc). Ce qu'on perd : le second regard mot à mot ;
on le compense par des tests de résultats, et par le point fixe.

**Étape 2 : un seul lecteur du langage.** vtxc128 écrit l'arbre typé du programme dans un fichier ; la forge (et donc
Taranis) le lit au lieu de relire le texte par Python. Le lecteur Python disparaît : un changement du langage ne se fait
plus qu'une fois, en vtx.

**Étape 3 : la forge en vtx.** Plus de Python dans le chemin d'un programme (le Rust reste l'hôte de la machine).

## 0.852 : la forge écrite en vtx (étapes 2 et 3 d'un seul geste)

Décidé avec le créateur : plutôt qu'un arbre typé lu par la forge Python, **vtxc128 écrit lui-même le Rust**, depuis son
propre arbre et ses types, pendant qu'il écrit les mots. Par morceaux : ce qu'il ne sait pas encore, l'ancienne forge le
garde.

- **Dans vtxc128** (`vtxc/vtxc128.vtx`, les fonctions `rs_…`) : une neuvième entrée du protocole, `rust` (après
  `exemples`) ; à 1, vtxc128 écrit aussi `code.rs` : `FIN_CODE`, les adresses des textes nommés (`ETQ_n`, posées une fois
  les mots placés), et une fonction Rust par fonction gardée (`fn f_NOM(c: &mut Ctx, mut v_x: u128) -> u128`), écrite
  dans `fonction_code`, là où ses variables sont connues. Ce qui manque s'écrit `// pas encore : … (ligne N)`, **toutes
  les raisons**, une par ligne : on voit d'un coup ce qu'il reste.
- **Ce qu'il sait (0.852)** : l'entier de Lugus (128 bits) et celui de Dunon (`dunon;`, les formes de 64 bits de la
  forge) ; références de structures, poignées de textes et de tableaux ; soit, affectation, si/sinon, tantque, pour (le
  pas de 64 bits, comme la forge), retour, arrêter, continuer, bloc, accord (ses mesures dans l'ordre) ; nombres,
  variables, non, les opérations (signées comprises), comparaisons, et/ou, en condition et en valeur ; `@e[a]` en lecture
  et en écriture (étage écrit, calculé, ou aucun) ; champs, construction, `nouveau` ; les appels (arguments dans des
  `let`, de gauche à droite) ; les textes écrits ; sortie, entrée, ecrire_car, lire_car, les fichiers, bruit, __service,
  nb_bits, brin, marquer_adn/arn, liberer_brin.
- **`forge/forge_vtx.py`** n'est plus qu'un assembleur : le noyau, les mots de vtxc128, son Rust, la fin commune
  (`forge128.queue_programme`, sortie de `programme_rust`), puis rustc. `VTX_FORGE_VTX=1` : `forge128.py` essaie
  d'abord cette forge, et dit qui a écrit le Rust.
- **`forge/test_forge_vtx.py`** (dans `verifier.py`) : chaque programme que vtxc128 sait forger rend les mêmes sorties,
  le même texte et la même mémoire que Lugus émulé sur ses mots ; ceux qu'il laisse sont comptés par raison.
- **0.852b : Gergovie forgé par vtxc128.** Les trois manques sont faits :
  1. le cadre du ramasse-miettes (comme la forge Python) : les fonctions qui peuvent le lancer (celles qui lisent
     `pile()`, et qui les appellent : un point fixe, `rs_preparer`) ; une fonction qui en appelle une garde ses
     variables dans la pile de Lugus (l'enveloppe `f_` réserve la place, `fc_` est le corps), recopiées avant chaque
     tel appel ; une valeur gardée pendant qu'une suite peut ramasser est poussée (`c.pousser`), comme Lugus l'empile ;
  2. les logiques (rangés dans un mot ; vrai, faux, inconnu, variable ; `selon`) ;
  3. la recopie des données du programme (`__init`).
  Gergovie (l'orage, à demi-échelle) forgé par vtxc128 : **le même Rust que forge_vtx.py, les mêmes empreintes et les
  mêmes images que la forge Python**. Toutes les variantes de Gergovie, les cubes, le val, le rouleau, l'Auvergne et
  les fluides : rien ne manque.
- **`lugus forger PROG.vtx [-o EXE] [--rs F.rs] [--natif]` : la forge sans Python.** Le noyau de la forge
  (`forge/noyau_forge128.rs` et les sept modules qu'il recopie) et la fin commune (`forge/queue_vtx.rs`, copie de
  `forge128.queue_programme` sans zones ni noyaux ; `forge_vtx.py --queue` la récrit, le test vérifie qu'elle n'a pas
  bougé) sont embarqués dans lugus ; vtxc128 écrit le Rust, lugus assemble, rustc compile. Un programme vtx devient un
  exécutable natif avec lugus et rustc, rien d'autre.
- **Le ramasse-miettes et la mémoire** : il lit la pile de Lugus, que ni la forge Python ni celle-ci ne tiennent mot
  pour mot (les adresses de retour, les registres gardés) ; ce qu'il garde peut donc différer de Lugus émulé (et entre
  les deux forges), jamais les sorties. Le test le permet pour ses programmes « ramasse-miettes ».
- **Ce qui reste à la forge Python (la vitesse, pas le sens)** : les tableaux serrés (zones), l'étage 2 par la carte des
  pages (lire2, ecrire2, les liaisons des cubes), les boucles sur la carte (les noyaux SPIR-V de
  `taranis/noyau_vtx.py`), le Druide et Ésus (les codons de 64 bits, les relevés). C'est pourquoi `forge128.py` reste la
  forge par défaut des essais (avec la carte, l'écart est grand) ; `VTX_FORGE_VTX=1` ou `lugus forger` prennent celle de
  vtxc128.
- **0.852c : les segments et les bandes sur les cœurs**, comme la forge Python : un accord dont les notes sont les
  segments d'une même boucle (la même variable, le même corps) et dont le corps ne touche que le cube (`rs_sans_effet`,
  comme `sans_effet`) va aux cylindres (un par cœur, chacun son cube, puis `fusionner` ; refusé : les notes dans
  l'ordre) ; une boucle « en bandes » (vtxc128 en garde les lignes, `lignes_bandes`) va à l'équipe de Gutuater
  (`equipe_jouer`, quatre morceaux par cœur, le réglage `REGLAGE` mesuré ; deux cœurs sur le même mot : la machine
  s'arrête et le dit). La clé du réglage est la fonction et la ligne (la forge Python prend le programme, la ligne et le
  corps : leurs mémoires de Gutuater ne se partagent pas). Gergovie (l'orage, demi-échelle, deux cœurs ici) : les mêmes
  empreintes et images, **8,3 s contre 8,9 s pour la forge Python** (12,8 s avant, sur un cœur).
- **Ensuite** : Taranis, les noyaux de la carte écrits par vtxc128 (le travail de `taranis/noyau_vtx.py`, 1 400 lignes,
  et de `vers_la_carte`/`fondre` dans la forge : les trois noyaux, la fenêtre et les pages, les lots, le choix du
  vergobret) ; puis les zones et les pages de l'étage 2 ; alors l'ancienne forge et vtx128.py peuvent partir.

## Ce qui ne change pas

- La liste du 128 (`docs/vtx-liste-128.md`) ; le Vergobret en 64 bits ; le Druide sur l'ARN et le cube, jamais l'ADN.
- `dunon;` : un programme du graphique compte en 64 bits, ses services sont ceux de Dunon.
- Chaque essai joue les trois : le C++, vtx au processeur, Taranis.
