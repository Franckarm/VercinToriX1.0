# Commencer avec Vercintorix

Ce guide va de zéro à un premier programme : construire `vtx.exe`, installer l'éditeur, écrire et lancer du vtx. Les commandes sont pour Windows (PowerShell) ; sous macOS ou Linux, enlevez `.exe` et remplacez `\` par `/`.

## 1. Construire vtx.exe (une seule fois)

Il faut Rust (https://rustup.rs). Dans PowerShell, placez-vous dans le dossier `vtx-rs` du paquet :

```
cd "C:\chemin\vers\vtx-0.5\vtx-rs"
cargo build --release
```

La première fois, cela prend environ une minute. Le résultat est `vtx-rs\target\release\vtx.exe`. C'est tout Vercintorix : le compilateur (écrit en vtx), la machine qui exécute, et la traduction en code natif. Python n'est pas nécessaire.

Pour pouvoir taper simplement `vtx` dans n'importe quel dossier, ajoutez ce dossier au chemin de recherche :

```
$env:Path += ";C:\chemin\vers\vtx-0.5\vtx-rs\target\release"
```

(valable pour cette fenêtre ; pour toujours : Paramètres Windows, « Modifier les variables d'environnement », variable `Path`, « Nouveau », puis le dossier `...\vtx-rs\target\release`).

## 2. Lancer un programme

```
vtx programme.vtx                 compile puis exécute
vtx programme.vtx 3 4             avec les entrées 3 et 4 (lues par entrée())
vtx traduire programme.vtx        fabrique programme.exe, en code natif (environ 12 fois plus rapide)
programme.exe 3 4                 lance la version native
```

Ce qui s'affiche : d'abord les nombres donnés à `sortie()`, sur une ligne, séparés par des virgules ; ensuite le texte écrit sur la console (`ecrire_texte(1, …)`). Une erreur donne le fichier, la ligne et ce qui ne va pas :

```
erreur faute.vtx, ligne 3 : symbole attendu : « ; »
```

(Un « ; » oublié est signalé à la ligne suivante : c'est là que le compilateur s'aperçoit qu'il manque.)

**`sortie` ou `afficher` ?** `sortie(x)` écrit le mot de la machine tel quel : un entier de 32 bits sans signe, si bien que `sortie(3 - 5)` donne 4294967294, et un flottant par ses bits (`sortie(3.5)` donne 1080033280). C'est le canal des tests. Pour lire un résultat, utilisez `afficher(x)` : il écrit en clair, sur sa ligne, un entier signé (`-2`), un flottant (`3.5`), un long, un logique (`variable`) ou un texte. Et attention : `7 / 2` entre entiers vaut 3 ; écrivez `7.0 / 2` pour obtenir 3.5.

### La machine 64 bits : vtx64

La même construction fabrique aussi `vtx64.exe`, la machine du SPU-64 avec son compilateur (vtxc64) embarqué :

```
vtx64 programme.vtx               compile pour le SPU-64 puis exécute (mots de 64 bits, points profonds)
vtx64 compiler programme.vtx      écrit seulement les mots
```

Les exemples sont dans `exemples64` (`vtx64 exemples64\bonjour64.vtx`). Le langage du SPU-64 : `docs\vtx64-langage.md`.

**Si `cargo build` dit « linker `link.exe` not found »** alors que Visual Studio est installé (par exemple Visual
Studio 2026 sur un autre disque) : lancez la construction depuis l'« Invite de commandes développeur » de Visual
Studio, qui sait où sont ses outils C++ ; ou mettez Rust à jour (`rustup update`).

## 3. L'éditeur : Visual Studio Code et l'extension vtx

Le paquet contient une extension pour VS Code : couleurs du langage, extraits de code, et un raccourci pour lancer le programme ouvert.

1. Copiez l'extension dans le dossier des extensions de VS Code (PowerShell, depuis le dossier `vtx-0.5`) :
   ```
   Copy-Item -Recurse editeur\vscode-vtx "$env:USERPROFILE\.vscode\extensions\vercintorix.vtx-0.5.0"
   ```
2. Fermez et rouvrez VS Code.
3. Ouvrez le dossier `vtx-0.5` (Fichier, Ouvrir le dossier), puis un fichier `.vtx` : les mots du langage sont en couleur.
4. **Ctrl+Maj+B** lance le programme ouvert. VS Code demande les entrées (laissez vide s'il n'y en a pas). Une erreur est soulignée à la bonne ligne.
5. Les extraits : tapez `principal`, `fonction`, `pour`, `si`, `selon`, `structure`, `tableau`… puis Tab, et le squelette s'écrit.

Les autres tâches (Terminal, Exécuter la tâche) : « traduire en code natif » et « construire la machine ».

## 3 bis. L'atelier : une fenêtre pour écrire, lancer et voir le cube

**`atelier.exe`** (dans `vtx-rs\target\release`, construit avec `vtx.exe`) est une vraie fenêtre Windows, sans VS Code ni console :

- en haut, les menus **Fichier** (Nouveau, Ouvrir, Enregistrer, Enregistrer sous, Quitter), **Édition** (Annuler, Couper, Copier, Coller, Tout sélectionner), **Exécuter**, **Cube**, **Aide**, et des boutons : Ouvrir, Enregistrer, **▶ Lancer (F5)**, Pas à pas (F7), les **entrées** du programme, l'**étage** du cube (0 à 3), la **vue** (F6) ;
- à gauche, le programme : la souris, la sélection et le presse-papiers sont ceux de Windows ; Entrée garde le retrait (un niveau de plus après « { ») ; une erreur de compilation sélectionne la ligne fautive ;
- à droite, **le cube** : en perspective (l'étage vu comme un cube de 256 × 256 × 256 mots, chaque mot non nul est un petit cube de sa couleur ; la molette zoome) ou à plat (chaque mot un carré ; un clic donne l'adresse et la valeur, la molette fait défiler). Les petits nombres, presque noirs comme couleurs, prennent une teinte selon leur grandeur (du violet au jaune) ;
- en dessous, ce qu'a donné le programme : instructions, sorties, et tout ce qu'il a écrit sur la console.

Sous le cube, à gauche, le **terminal** : ce que le programme écrit y apparaît au fur et à mesure ; s'il pose une question (`lire_ligne()`), tapez la réponse dans la ligne du dessous et Entrée ; **Maj+F5** arrête un programme qui ne finit pas. Le reste du temps, cette ligne prend des commandes : `aide`, `lancer`, `mot ADRESSE`, `etage N`, `arbre`, `effacer`, et `cubes` (ce que regarde chaque étage, les cubes en mémoire et ceux rangés sur disque, nommés `cube-ÉTAGE-FRÉQUENCE.cub`) avec `cube ÉTAGE FRÉQUENCE` pour en regarder un.

À droite, l'**arbre des liaisons** : après l'exécution, les objets que le programme a créés (tableaux, dictionnaires, textes), chacun avec sa couleur du cube ; un clic ouvre une ligne. Dans un dictionnaire, chaque clé montre son état : vrai en vert, faux en rouge, inconnu en gris, variable en orange. À plat (F6), un clic dans le cube choisit un mot : l'arbre le décode (hex, quits, lecture ADN/ARN) et montre ce qu'il désigne.

**Plus de précision.** `1.5D` est un flottant de 64 bits (`flottant_64`), `5L` un entier de 64 bits (`entier_64`), `5LL` un entier de 128 bits (`entier_petuar`, ou `entier_128`) : `exemples/flottant64/`, `exemples/entier128/`. **Le flottant quaternaire** : `1.5Q` est un `flottant_petuar`, quatre points du cube (32 chiffres hex, 64 quits, 64 bases d'ADN), environ 34 chiffres, avec un état à quatre valeurs (inconnu, négatif, positif, variable) : `exemples/petuar/` (`decouverte`, `quatre_etats`, `pi_machin`). **Le cube chromatique qui tourne** : `vtx gobatix exemples/gobatix/cube_chromatique.vtx` (une fenêtre sous Windows ; `--images dossier` écrit des PNG, `--gif anim.gif` une animation ; `vtx gobatix64` sur la SPU-64) ; en fil de fer, et à la souris : `cube_tournant.vtx`.

**La machine.** Un programme peut nommer sa machine dans ses premières lignes : `// machine : spu-32` ou `// machine : spu-64` ; l'atelier l'ouvre alors sur elle (Ctrl+M change toujours). Sinon, l'atelier travaille par défaut sur la **SPU-64** (vtxc64, mots de 64 bits) : le titre et le bouton de la barre la nomment, **Ctrl+M** (ou le menu Exécuter) passe sur la SPU-32 et retour ; un fichier du dossier `exemples` s'ouvre sur la SPU-32. Sur la SPU-64, le cube montre chaque point profond `#RRRRGGGGBBBBAAAA` par l'octet fort de chaque voie ; un clic ou `mot` donne la vraie valeur de 64 bits ; le pas à pas montre les registres sur 64 bits.

Un programme qui **dessine** (`ecran`, `pixel`, `trait`, `rectangle`, `disque`, `triangle`, sur les deux machines) voit son image à la place du cube ; F6 passe de l'image au cube et à la vue à plat. **Un programme animé** (qui appelle `presenter()` à chaque image) se voit bouger pendant qu'il tourne : **cliquez l'image**, la souris, la molette et le clavier vont au programme (`souris()`, `touche()`, `appuyee()`, `molette()` ; Échap compris, F5 et Maj+F5 restent à l'atelier). **Ctrl+G** (ou le bouton « ● Enregistrer (GIF) ») commence puis finit l'enregistrement d'une animation, écrite à côté du programme (`programme-1.gif`) ; Cube › Image du programme en PNG. Essayez `exemples/gobatix/peindre.vtx` (peindre à la souris, un carré qui rebondit, poussé aux flèches) et `cube_tournant.vtx` (le cube suit la souris). Le programme fini, la vue en perspective du cube se tourne à la souris : glisser avec le bouton gauche fait un quart de tour, avec le bouton droit la déplace, un double clic la remet. Les **numéros de ligne** sont à gauche du texte ; une erreur de compilation met le sien en rouge.

**Faire reconnaître les fichiers `.vtx`** : menu Aide, « Associer les fichiers .vtx à l'atelier », ou dans un terminal :

```
vtx installer
```

Les fichiers `.vtx` prennent l'icône du cube et s'ouvrent dans l'atelier par un double-clic (Windows : seulement pour votre compte, sans droits d'administrateur ; gardez `vtx.exe` et `atelier.exe` à leur place, ou relancez la commande après les avoir déplacés). Sous Linux, la même commande installe le type de fichier, l'icône et un lanceur (l'atelier s'ouvre dans un terminal). `vtx desinstaller` défait tout.

Le **pas à pas** se fait dans la fenêtre même : **F7** exécute jusqu'à la ligne suivante (en entrant dans les fonctions), **F8** aussi mais sans entrer dans les fonctions appelées, **F9** pose ou enlève un point d'arrêt (●) sur la ligne du curseur, **F5** continue jusqu'au prochain point d'arrêt, **Échap** (ou Maj+F5) arrête. La ligne où la machine s'est arrêtée est marquée ▶ en jaune dans la gouttière. L'onglet **Pas à pas** (sous le cube) montre les registres R1 à R12 et le cadre de la fonction (variables locales −1, −2…, paramètres +2, +3…), chacun en décimal, **en quaternaire** (les 16 quits du mot, du quit 15 au quit 0) et **en logique de Belnap** (· inconnu, f faux, v vrai, ± variable), puis les sorties et la console. Modifier le texte arrête le pas à pas. Quand le programme finit, sa mémoire passe au cube et à l'arbre.

La **vue en quits** (F6 : perspective → à plat → en quits) montre chaque mot de l'étage comme un carré de 4 × 4 cases, ses 16 quits (le quit 15 en haut à gauche), chacun de sa couleur de Belnap : gris inconnu, rouge faux, vert vrai, orange variable ; un clic choisit un mot. En ligne de commande : `vtx quits programme.vtx image.png [ÉTAGE] [BASE] [LARGEUR]`.

L'atelier en console (`vtx atelier programme.vtx`, décrit ci-dessous) reste disponible dans n'importe quel terminal.

### L'atelier en console (`vtx atelier`)

L'écran a trois parties. À gauche, l'éditeur, avec les couleurs du langage et les numéros de ligne. En haut à droite, **le cube** : un étage de la mémoire, chaque mot `#RRGGBBAA` dessiné de sa propre couleur. En bas à droite, ce qu'a donné le programme ; pendant le pas à pas, les registres, les variables et la console.

| Touche | Effet |
|---|---|
| F5 | enregistre, compile et lance ; une erreur met sa ligne en rouge et y place le curseur |
| F7 | **pas à pas** : exécute jusqu'à la ligne suivante, en entrant dans les fonctions appelées ; la ligne qui va s'exécuter est en vert |
| F8 | pas « par-dessus » : la ligne entière, fonctions appelées comprises |
| F9 | pose ou enlève un **point d'arrêt** (●) sur la ligne du curseur ; pendant le pas à pas, F5 continue jusqu'au prochain |
| Échap | arrête le pas à pas (la mémoire reste visible dans le cube) |
| F4 | les entrées du programme (nombres séparés par des espaces) |
| F2 ou Ctrl+S | enregistre |
| Ctrl+O | ouvre un autre fichier |
| F6 | passe de l'éditeur au cube et retour |
| Ctrl+Z, Ctrl+K, Ctrl+D | annule (mot par mot), supprime la ligne, duplique la ligne |
| Ctrl+Q | quitte (deux fois si le fichier n'est pas enregistré) |

Pendant le pas à pas, le panneau montre les registres R1 à R8, le cadre de la fonction en cours (ses variables locales en −1, −2… et ses paramètres en +2, +3…), les sorties et la console ; le cube montre la mémoire au moment présent. On ne peut pas modifier le texte pendant le pas à pas : Échap d'abord.

Dans le cube : les flèches et Page↑/↓ déplacent la sélection (son adresse et sa valeur s'affichent sous l'image), `0` à `3` choisissent l'étage, `l` et `L` la largeur de l'image (16 à 4096 mots par ligne), `a` ajuste le zoom, `+`/`-` zooment, `m` passe des couleurs aux valeurs (les petits nombres, presque noirs en couleurs, deviennent visibles en dégradé).

Pour voir une image : ouvrez `exemples\rayons.vtx`, F4 et tapez `600 900 100`, F5, puis F6, `2` (l'image est dans l'étage 2) et `l` (128 mots par ligne). Pour voir le pas à pas et les hypothèses à l'œuvre : `exemples\hasard\reines.vtx`, F7, F8…

Il faut une console qui comprend les couleurs vraies : Windows 10 ou 11, macOS, Linux.

## 4. Premiers programmes

Ils sont dans `exemples\premiers`. Ouvrez-les, lancez-les, modifiez-les.

**bonjour.vtx** : tout programme commence par la fonction `principal`.

```
fonction principal() {
    ecrire_texte(1, "Bonjour, Vercintorix !\n");
    sortie(6 * 7);
}
```

**somme.vtx** : `soit` crée une variable ; `entrée()` lit une entrée donnée au lancement (`vtx somme.vtx 3 4`).

```
fonction principal() {
    soit a = entrée();
    soit b = entrée();
    ecrire_texte(1, "a + b = ");
    ecrire_nombre(1, a + b);
    ecrire_car(1, '\n');
}
```

**carres.vtx** : fonctions, boucle `pour` (de 0 à 9 : la borne de fin est exclue), tableau rangé dans la mémoire du cube (`@1[0]` : étage 1, adresse 0).

```
tableau carres[10] @1[0];

fonction carre(x) {
    retour x * x;
}

fonction principal() {
    pour i dans 0..10 {
        carres[i] = carre(i);
    }
    soit total = 0;
    pour i dans 0..10 {
        total = total + carres[i];
    }
    sortie(total);
}
```

**porte.vtx** : la logique à quatre valeurs. Un `logique` ne sert pas de condition de `si` : on traite les quatre cas avec `selon`.

```
fonction dire(l: logique) {
    selon l {
        vrai { ecrire_texte(1, "fermée\n"); }
        faux { ecrire_texte(1, "ouverte\n"); }
        inconnu { ecrire_texte(1, "personne n'a regardé\n"); }
        variable { ecrire_texte(1, "les témoins se contredisent\n"); }
    }
}

fonction principal() {
    soit capteur_a: logique = vrai;
    soit capteur_b: logique = faux;
    dire(fusion(capteur_a, capteur_b));     // variable
    dire(fusion(capteur_a, inconnu));       // vrai
    dire(et4(capteur_a, capteur_b));        // faux
}
```

**calcul.vtx** : `afficher`, les flottants et les fonctions mathématiques (`racine`, `sinus`, `puissance`, `exponentielle`, `logarithme`, `pi()`…).

```
fonction principal() {
    afficher(3 - 5);                    // -2
    afficher(7 / 2);                    // 3 : division entière
    afficher(7.0 / 2);                  // 3.5
    afficher(sinus(pi() / 6.0));        // 0.5
    soit rayon: flottant = 2.5;
    ecrire_texte(1, "aire du disque : ");
    ecrire_flottant(1, pi() * rayon * rayon, 2);     // 19.63, deux décimales
    ecrire_car(1, '\n');
}
```

**des.vtx** : le hasard. `hasard_entre(1, 6)` lance un dé. `graine_bruit()` prend la graine dans le bruit de la machine : une partie différente à chaque lancement. `graine(7)` rejoue toujours la même suite, sur toutes les machines, ce qui sert à vérifier : `vtx des.vtx 7`.

**hasard\reines.vtx** (dans `exemples\hasard`) : les huit reines, résolues par trois idées ensemble. Le hasard propose l'ordre des colonnes ; la logique à quatre valeurs juge (une case est `inconnu`, `vrai` pour une reine, `faux` si elle est menacée, et poser une reine sur une case menacée donne `variable`, une contradiction) ; l'hypothèse permet de revenir en arrière (`annuler` défait tout ce qui a été écrit). Chaque lancement donne une autre solution ; `vtx reines.vtx 7` rejoue toujours la même.

**textes.vtx** : le type texte. `+` colle deux textes, et change au passage un nombre, un flottant ou un logique en texte (`"n = " + n`) ; `==` et `!=` comparent le contenu ; `afficher` prend plusieurs valeurs, séparées par une espace (`afficher("total :", 42, 1.5)`).

```
fonction salut(qui: texte): texte {
    retour "Bonjour, " + qui + " !";
}

fonction principal() {
    soit nom = "Vercintorix";
    afficher(salut(nom));                 // Bonjour, Vercintorix !
    afficher("total :", 42, 1.5, vrai);   // total : 42 1.5 vrai
}
```

**cube.vtx** : le mot du cube `#RRGGBBAA` et ses quatre voies.

```
fonction principal() {
    soit braise = #FF6020C0;
    sortie(braise.r);      // 255
    sortie(braise.v);      // 96
    sortie(braise.b);      // 32
    sortie(braise.a);      // 192
}
```

## 5. L'essentiel du langage en dix lignes

- Une instruction finit par `;` ; un bloc est entre `{ }` ; un commentaire commence par `//`.
- `soit x = 5;` crée une variable ; `x = x + 1;` la change. Types : entier (par défaut), `flottant` (`1.5`), `long` (`5L`), `logique`, `texte` (`"abc"`), ou une structure.
- `si … { } sinon { }`, `tantque … { }`, `pour i dans a..b { }` (b exclu), `arrêter;`, `continuer;`.
- `fonction nom(a, b: flottant): flottant { retour …; }`.
- La mémoire : quatre étages de 16 millions de mots ; `@2[100]` lit ou écrit l'adresse 100 de l'étage 2. Les tableaux nomment une zone : `tableau t[64] @1[0];`.
- `structure Point { x, y }`, puis `soit p = Point { x: 1, y: 2 };` et `p.x`.
- Le cube : `#RRGGBBAA`, les voies `.r .v .b .a`, les quits (`x.q(i)`, `<<q`, `min4`…), les tableaux `de quits` et `de logique` (16 valeurs par mot).
- La logique : `vrai`, `faux`, `inconnu`, `variable`, et `et4`, `ou4`, `non4`, `anti`, `fusion`, `consensus`, `selon`.
- Plusieurs cœurs : `pour i dans 0..n en segments { … }`, ou simplement plusieurs appels de fonctions à la suite : le compilateur range lui-même dans des accords ce qui peut tourner en même temps.
- `afficher(x)` écrit un résultat en clair (`afficher(a, b, c)` : plusieurs sur une ligne) ; un texte se colle avec `+` (`"n = " + n`) ; maths : `racine sinus cosinus tangente exponentielle logarithme puissance arctangente plancher plafond pi()` ; hasard : `hasard(n)`, `hasard_entre(a, b)`, `hasard_flottant()`, `graine(n)` (reproductible) ou `graine_bruit()` (imprévisible), `bruit()`, `bruit_logique()`.
- `importer "fichier.vtx";` reprend un autre fichier.

La référence complète est `docs\vtx-syntaxe-v0-4.md`. Les programmes du paquet (`feu`, `ombre`, `logique`, `genomique`, `compression`…) sont autant d'exemples plus grands.
