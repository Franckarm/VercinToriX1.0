# ScoR : la spirale sur constellation de recherche (v1 : le raisonnement)

Un premier essai, écrit en vtx (`scor.vtx`), de l'IA native imaginée pour Vercintorix. Il lit les documents du
projet, s'en fait une mémoire dans le cube, et répond à des questions.

```
cd scor
vtx scor.vtx            # huit questions de démonstration, puis les vôtres au clavier (ligne vide : fin)
```

Dans l'atelier : ouvrez `scor.vtx`, F5 ; les questions se tapent dans la ligne du terminal. L'étage 1 du cube
montre tous les mots consolidés à leur place ; l'étage 2, la dernière question et ses réponses.

## Comment il marche

| Étape | Idée | En pratique |
|---|---|---|
| Graine | le hex du mot | chaque mot naît avec **quatre points** (ses sens possibles), placés par le hex de son orthographe |
| Mémoire courte | l'ARN, dans l'ombre | les mots voisins d'une phrase se lient ; une phrase niée (pas, sans, jamais…) range ses liaisons dans l'**anti-cube** |
| Sommeil | consolidation | après chaque document, seules les liaisons revenues **deux fois** passent dans l'ADN ; les autres attendent une nuit puis sont oubliées |
| Rêve | ressorts dans le cube | 200 nuits rejouent l'ADN : deux mots liés rapprochent leurs points les plus proches (le sens partagé), des points au hasard s'écartent, le pas refroidit |
| Ombre | ce qui n'est pas consolidé ne sort pas | seuls les mots de l'ADN ressortent dans les cases du cube |
| Spirale | constellation, économie | autour de chaque point de la question, des couronnes de cases ; elle s'arrête quand la couronne suivante ne peut plus rien apporter (énergie d'activation) |
| Épissage | Belnap | la proximité n'est qu'une hypothèse ; l'état vient des phrases lues : **vrai** (affirmé, au cube), **faux** (seulement nié, à l'anti-cube), **variable** (affirmé et nié : critiqué), **inconnu** (proche sans preuve, ou jamais lu : reste dans l'ombre) |
| Recherche contraire | l'anti-cube, l'antiphrase | chaque réponse est cherchée aussi dans les phrases niées : c'est ainsi qu'une critique est trouvée |

## Le raisonnement (v1)

Le ScoR lit aussi les **relations** : « X est Y » et « X n'est pas Y » (le sujet juste avant le verbe, l'attribut
juste après, articles sautés). Il les enchaîne pour déduire ce qui n'est écrit nulle part, en logique de Belnap, et
montre toujours sa preuve (le nombre de phrases pour chaque lien) :

| Question | Réponse |
|---|---|
| le chat est-il un vivant ? | **vrai** : déduit : chat → mammifère (1) → animal (1) → vivant (1) |
| le requin est-il un mammifère ? | **faux** : déduit : requin → poisson (1), et « poisson n'est pas mammifère » (1) |
| le manchot est-il volant ? | **faux** : dit directement ; pourtant la règle générale manchot → oiseau → volant : **exception**, le fait le plus précis l'emporte |
| Nixon est-il pacifiste ? | **variable** : deux règles se contredisent : nixon → quaker → pacifiste ; mais nixon → républicain, et « républicain n'est pas pacifiste » |
| l'ARN est-il une preuve ? | **faux** : déduit : arn → hypothèse, et « hypothèse n'est pas preuve » |
| le chat est-il une licorne ? | **inconnu** : « licorne » jamais lu |

Autres questions : `qu'est-ce que X ?` (ce que X est, dit puis déduit, ce qu'il n'est pas, ce qui est un X) ;
`lien X Y` (le plus court chemin dans l'ADN, avec le poids de chaque liaison). Les faits d'essai sont dans
`faits.md` ; le ScoR lit ensuite les documents du projet, d'où il tire aussi des relations (plus bruitées : la prose
technique se laisse moins bien découper que des phrases simples).

## Il se souvient et apprend en parlant

Au premier lancement, le ScoR lit, dort et rêve, puis enregistre sa mémoire (`scor.memoire`) ; aux lancements
suivants il la recharge (1 seconde au lieu de 7). Pour tout relire, effacez `scor.memoire` et `scor.memoire.ent`.

Dans le dialogue :
- une **question** (avec « ? », ou `qu'est-ce que X`, `lien X Y`, ou des mots) : il cherche et raisonne ;
- une **affirmation** (« le chat est noir », « le requin n'est pas un poisson ») : il l'apprend, et dit ce qu'il en
  pensait avant : « J'ai appris que… », « Je le savais déjà… », ou « Tu me dis que…, mais j'avais compris le
  contraire (…) » ; la relation entre aussitôt dans son raisonnement ;
- **dors** : ce qu'on lui a dit au moins deux fois passe dans l'ADN, le cube est remis à jour ;
- une ligne vide : il ramasse ses miettes et enregistre sa mémoire.

Il répond à voix haute (la voix de Windows) aux questions tapées.

## Ce qu'il donne (mesuré, `test_scor.py`)

- Le rêve range les liaisons : avant, mots liés et mots au hasard sont à la même distance (rapport 0,99) ; après,
  les mots liés sont **7 fois plus proches** (rapport 0,14).
- La spirale ne visite qu'**environ 4 % du cube** par question (au plus 188 cases sur 4 096).
- Réponses : « logique inconnu » → *belnap* ; « hypothèse arn » → *comportement*, *proposé* ; « compilateur vtxc »
  → *embarqué* ; « erreur diamant » → *correction*, **variable** (une phrase niée la critique) ; « nuage licorne » →
  **inconnu** (jamais lu).
- **Limite honnête** : entre 25 et 33 réponses sur 56 sont appuyées par des phrases (45 à 60 %, selon l'état des documents lus). Une recherche par mots-clés trouve
  des mots tous appuyés, mais souvent généraux (*variable*, *vrai*, *texte*) ; la spirale trouve des mots plus
  rares et plus précis, mais souvent liés à un seul mot de la question. Trois dimensions (même avec quatre points
  par mot) restent étroites pour 1 000 mots : la v1 devra le mesurer sur plus de textes et comparer d'autres formes
  de constellation.

Les deux compilateurs (vtx.py et vtxc) produisent les mêmes mots pour `scor.vtx`.
