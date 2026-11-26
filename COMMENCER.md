# Commencer avec Vercintorix (0.845)

Ce guide va de zéro à un premier programme sur **Lugus**, la machine de vtx (mots de 128 bits). Les commandes sont pour
Windows (PowerShell) ; sous Linux, enlevez `.exe` et remplacez `\` par `/`. La référence du langage :
`docs\vtx-langage.md`.

## 1. Construire la machine (une seule fois)

Il faut Rust (https://rustup.rs). Dans le dossier `vtx-rs` du paquet :

```
cd "C:\chemin\vers\vtx-0.6\vtx-rs"
cargo build --release
```

Cela donne, dans `vtx-rs\target\release` : **`lugus.exe`** (la machine et son compilateur vtxc128, écrit en vtx),
**`ogmios.exe`** (l'atelier), `vtx64.exe` (Dunon, la machine de 64 bits) et `vtx.exe` (les outils : la toile, la
paillasse, les .exe). Python n'est pas nécessaire. `vtx installer` associe les fichiers `.vtx` à Ogmios et pose ses
raccourcis (Bureau, menu Démarrer).

**Si `cargo build` dit « linker `link.exe` not found »** alors que Visual Studio est installé : lancez la construction
depuis l'« Invite de commandes développeur » de Visual Studio, ou mettez Rust à jour (`rustup update`).

## 2. Lancer un programme

```
lugus programme.vtx [ENTRÉES…]              compile (vtxc128) puis exécute
lugus ranger programme.vtx                  l'ADN : le programme rangé avec ses trois témoins (programme.adn)
lugus programme.adn                         vérifié, réparé si besoin, puis lancé
vtx exe128 programme.vtx                    un exécutable Windows avec la machine et ses cubes, sans Rust chez l'utilisateur
python forge\forge128.py programme.vtx -o programme.exe     la forge : le programme en code natif, par Rust (le plus rapide)
vtx64 programme.vtx                         le même langage sur Dunon (64 bits)
```

Une erreur donne la ligne et ce qui ne va pas (`erreur ligne 3 : symbole attendu : « ; »`) ; un « ; » oublié est
signalé à la ligne suivante.

**`afficher` ou `sortie` ?** `afficher(x)` écrit en clair : un entier signé (`-2`), un flottant (`3.5`), un logique
(`variable`), un texte. `sortie(x)` écrit le mot de la machine tel quel (sans signe : sur Lugus, −2 s'écrit
340282366920938463463374607431768211454) : c'est le canal des tests.

## 3. Ogmios, l'atelier

`ogmios.exe` ouvre une vraie fenêtre : le texte à gauche, **la paillasse au centre** (les réactions en cases et en
liaisons, dans les deux sens avec le texte ; le clic droit pose ou édite une case), le cube à droite, et en bas la
Sortie, le Terminal, le Pas à pas, l'Arbre et la fenêtre des explications. F5 compile, range l'ADN et lance ; F7 et F8
avancent pas à pas (les variables par leur nom) ; Ctrl+P montre la provenance d'une valeur ; le menu **Cases** explique
chaque case. Un programme qui dessine (`presenter()`) ouvre sa propre fenêtre.

L'extension pour VS Code (`editeur\vscode-vtx`) donne aussi les couleurs du langage et Ctrl+Maj+B pour lancer.

## 4. Premiers programmes

Les exemples de Lugus sont dans `exemples128` (`LISEZMOI.md` les présente). Trois pour commencer :

**Bonjour** :

```
fonction principal() {
    afficher("Bonjour, Vercintorix !");
    afficher(6 * 7, 3 - 5, 7 / 2, 7.0 / 2);     // 42 -2 3 3.5
}
```

**Les quatre valeurs** : un `logique` ne sert pas de condition de `si` ; `selon` traite les quatre cas. Le flottant
porte aussi son état : 0/0 n'est pas un nombre, c'est une contradiction.

```
fonction dire(l: logique) {
    selon l {
        vrai { afficher("fermée"); }
        faux { afficher("ouverte"); }
        inconnu { afficher("personne n'a regardé"); }
        variable { afficher("les témoins se contredisent"); }
    }
}

fonction principal() {
    soit capteur_a: logique = vrai;
    soit capteur_b: logique = faux;
    dire(fusion(capteur_a, capteur_b));     // les témoins se contredisent
    dire(fusion(capteur_a, inconnu));       // fermée
    dire(et4(capteur_a, capteur_b));        // ouverte
    soit q = 0.0 / 0.0;
    selon etat(q) {
        variable { afficher("0/0 : une contradiction, pas un nombre"); }
        autre { afficher("autre"); }
    }
}
```

**Le cube** : un point de matière, un cube nommé, l'ADN.

```
cube relief @2;

fonction principal() {
    soit braise = #FF6020;
    afficher(braise.r, braise.etat);                  // 4294967295 vrai (chaque couleur sur 32 bits)
    pour i dans 0..4 {
        @relief[i] = i * 10;
    }
    afficher(@relief[3], texte_adn(adn"GATTACA"));    // 30, puis les 64 bases du mot
}
```

## 5. L'essentiel du langage en dix lignes

- Une instruction finit par `;` ; un bloc est entre `{ }` ; un commentaire commence par `//`.
- `soit x = 5;` crée une variable ; `x = x + 1;` la change. Types : entier (128 bits, par défaut), `flottant` (`1.5`, quaternaire de 128 bits), `entier_32` (`5S`), `flottant_64` (`1.5D`), `logique`, `texte` (`"abc"`), `point` (`#FF6020`), ou une structure.
- `si … { } sinon { }`, `tantque … { }`, `pour i dans a..b { }` (b exclu), `arrêter;`, `continuer;`.
- `fonction nom(a, b: flottant): flottant { retour …; }`.
- La mémoire : quatre étages, chacun fait de cubes (les fréquences) ; `@2[100]` lit ou écrit la place 100 de l'étage 2 ; un cube se nomme : `cube relief @2;` puis `@relief[i]`.
- `structure Point { x, y }`, puis `soit p = Point { x: 1, y: 2 };` et `p.x`.
- Le cube : le point de matière `#RRGGBB` (`p.r`, `p.v`, `p.b`, `p.etat`…), les quits (`x.q(i)`, `<<q`, `min4`…), les tableaux `de quits` et `de logique` (64 valeurs par mot sur Lugus).
- La logique : `vrai`, `faux`, `inconnu`, `variable`, et `et4`, `ou4`, `non4`, `anti`, `fusion`, `consensus`, `selon`.
- Plusieurs cœurs : `pour i dans 0..n en segments { … }`, ou simplement plusieurs appels de fonctions à la suite : le compilateur range lui-même dans des accords ce qui peut tourner en même temps.
- `afficher(x)` écrit un résultat en clair (`afficher(a, b, c)` : plusieurs sur une ligne) ; un texte se colle avec `+` (`"n = " + n`) ; maths : `racine sinus cosinus tangente exponentielle logarithme puissance arctangente plancher plafond pi()` ; hasard : `hasard(n)`, `hasard_entre(a, b)`, `hasard_flottant()`, `graine(n)` (reproductible) ou `graine_bruit()` (imprévisible), `bruit()`, `bruit_logique()`.
- `importer "fichier.vtx";` reprend un autre fichier.

La référence complète est `docs\vtx-langage.md`. Les programmes du paquet (`feu`, `ombre`, `logique`, `genomique`, `compression`…) sont autant d'exemples plus grands.
