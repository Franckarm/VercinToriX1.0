#!/usr/bin/env python3
"""Le vocabulaire étendu de la 0.61 : un seul texte, écrit pour Lugus, d'où sont tirés les deux préludes (vtx128.py pour
Lugus, vtx64.py pour Dunon), puis recopiés dans vtxc128 et vtxc64 (prelude128.py, prelude64.py).

    python3 vtxc/vocabulaire.py

Les mots viennent de ce que savent Rust (les méthodes des entiers, des flottants, des textes, des tranches et des
itérateurs), ses extensions officielles (num, itertools, rand), Arduino (map, constrain, bitRead, lowByte, sq, random,
millis, delay, String), et des moteurs que vtx doit pouvoir accueillir (Unreal Engine 5 : FMath, FVector, FQuat ;
Blender : mathutils, les nœuds de mathématiques). Ce ne sont pas ces bibliothèques recréées : c'est le vocabulaire
français qu'il faut pour y brancher ce qu'elles font. Chaque mot dit, dans sa ligne de commentaire, d'où il vient.

Règles du texte (pour que les deux compilateurs de chaque machine donnent les mêmes mots) :
- le flottant principal s'écrit flottant_petuar et ses nombres 1.0Q ; Dunon les lit flottant et 1.0 ;
- les fonctions mathématiques s'écrivent sinus_128… ; Dunon lit sinus_64… ;
- une variante d'un mot porte son suffixe : __mot_x (le flottant principal ; Dunon : __mot_f) ; ce programme écrit
  les autres (_f et _s sur Lugus, _s sur Dunon) en convertissant ;
- dans le prélude, un mot qui a des variantes n'est jamais appelé avec des flottants : on appelle sa variante ;
- pas de texte écrit entre guillemets (il irait dans tous les programmes)."""
import os
import re
import sys

ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
DEBUT = "// ---- 0.61 : le vocabulaire étendu (écrit par vtxc/vocabulaire.py : ne pas retoucher à la main)\n"
FIN = "// ---- fin du vocabulaire étendu\n"

# ------------------------------------------------------------------------------------------------ l'aide propre à chaque machine
AIDE_LUGUS = r"""
fonction __vn_etat(v: flottant_petuar) { retour __pq_etat(bits(v)); }
fonction __vn_su(v: flottant_petuar) { retour __pq_su(v); }
fonction __vn_doute(v: flottant_petuar): logique { retour __pq_doute(v); }
fonction __vn_infini(v: flottant_petuar) { retour __pq_ef(bits(v)) == 16383; }
fonction __vn_inconnu(): flottant_petuar { retour comme_flottant_petuar(0LL); }
fonction __vn_variable(): flottant_petuar { retour variable_petuar(); }
fonction __vn_hasard(): flottant_petuar { retour flottant_petuar(hasard_flottant()); }
fonction __vt_lire(t, i): flottant_petuar { retour comme_flottant_petuar(entier_petuar(@3[@3[(t & 16777215) + 2] + i])); }
fonction __vt_ecrire(t, i, v: flottant_petuar) { @3[@3[(t & 16777215) + 2] + i] = bits(v); }
fonction __vn_reste(a: flottant_petuar, b: flottant_petuar): flottant_petuar {
    // le reste exact (0.61b) : la division longue des mantisses, quit par quit (sept à la fois), en entiers
    soit x: entier_128 = bits(a);
    soit y: entier_128 = bits(b);
    soit sa = __pq_etat(x);
    soit sb = __pq_etat(y);
    si sa == 3 || sb == 3 { retour variable_petuar(); }
    si sa == 0 || sb == 0 { retour comme_flottant_petuar(0LL); }
    soit un: entier_128 = 1LL;
    soit mq: entier_128 = (un << 112) - un;
    soit ma: entier_128 = x & mq;
    soit mb: entier_128 = y & mq;
    soit ea = __pq_ef(x);
    soit eb = __pq_ef(y);
    si ea == 16383 || (eb != 16383 && mb == 0LL) { retour variable_petuar(); }
    si eb == 16383 || ma == 0LL { retour a; }
    si ea == 0 { ea = 1; }
    si eb == 0 { eb = 1; }
    si ea < eb { retour a; }
    soit r: entier_128 = ma % mb;
    soit d = ea - eb;
    tantque d > 0 {
        soit k = d;
        si k > 7 { k = 7; }
        r = (r << (2 * k)) % mb;
        d = d - k;
    }
    soit s: entier_128 = entier_128(sa) << 126;
    si r == 0LL { retour comme_flottant_petuar(s); }
    soit e = eb;
    soit q55: entier_128 = un << 110;
    tantque r < q55 && e > 1 { r = r << 2; e = e - 1; }
    si r < q55 { e = 0; }
    retour comme_flottant_petuar(s | (entier_128(e) << 112) | r);
}
fonction __vn_bn128(w: entier_128) {
    soit r = __bn_neuf(bas(w));
    soit h = __bn_neuf(haut(w));
    __bn_decaler(h, 64);
    __bn_ajouter(r, h);
    retour r;
}
fonction __vn_vers128(a): entier_128 {
    soit lo = 0;
    soit hi = 0;
    pour i dans 0..longueur(a) {
        si i < 4 {
            lo = lo | (a[i] << (16 * i));
        } sinon {
            hi = hi | (a[i] << (16 * (i - 4)));
        }
    }
    retour entier_128_de(hi, lo);
}
fonction __multiplier_ajouter_x(a: flottant_petuar, b: flottant_petuar, c: flottant_petuar): flottant_petuar {
    // 0.65 : le flottant de 128 bits, exact puis arrondi une seule fois
    soit x: entier_128 = bits(a);
    soit y: entier_128 = bits(b);
    soit z: entier_128 = bits(c);
    soit un: entier_128 = 1LL;
    soit q: entier_128 = (un << 112) - un;
    soit ea = __pq_ef(x);
    soit eb = __pq_ef(y);
    soit ec = __pq_ef(z);
    soit sa = __pq_etat(x);
    soit sb = __pq_etat(y);
    soit sc = __pq_etat(z);
    si sa == 0 || sa == 3 || sb == 0 || sb == 3 || sc == 0 || sc == 3 || ea == 16383 || eb == 16383 || ec == 16383
            || (x & q) == 0LL || (y & q) == 0LL || (z & q) == 0LL {
        retour a * b + c;
    }
    si ea == 0 { ea = 1; }
    si eb == 0 { eb = 1; }
    si ec == 0 { ec = 1; }
    soit r = __vn_fma_coeur(sa, __vn_bn128(x & q), ea, sb, __vn_bn128(y & q), eb, sc, __vn_bn128(z & q), ec, 112, 8247, 16383);
    soit m: entier_128 = __vn_vers128(r[2]);
    retour comme_flottant_petuar((entier_128(r[0]) << 126) | (entier_128(r[1]) << 112) | m);
}
"""
AIDE_DUNON = r"""
fonction __vn_etat(v: flottant) { retour bits(v) >> 62; }
fonction __vn_su(v: flottant) { soit e = bits(v) >> 62; retour e == 1 || e == 2; }
fonction __vn_doute(v: flottant): logique { si (bits(v) >> 62) == 3 { retour variable; } retour inconnu; }
fonction __vn_infini(v: flottant) { retour ((bits(v) >> 52) & 1023) == 1023; }
fonction __vn_inconnu(): flottant { retour comme_flottant(0); }
fonction __vn_variable(): flottant { retour comme_flottant(13835058055282163712); }
fonction __vn_hasard(): flottant { retour hasard_flottant(); }
fonction __vt_lire(t, i): flottant { retour comme_flottant(@3[@3[(t & 16777215) + 2] + i]); }
fonction __vt_ecrire(t, i, v: flottant) { @3[@3[(t & 16777215) + 2] + i] = bits(v); }
fonction __vn_reste(a: flottant, b: flottant): flottant {
    // le reste exact (0.61b) : la division longue des mantisses, quit par quit (cinq à la fois), en entiers
    soit x = bits(a);
    soit y = bits(b);
    soit sa = x >> 62;
    soit sb = y >> 62;
    si sa == 3 || sb == 3 { retour comme_flottant(13835058055282163712); }
    si sa == 0 || sb == 0 { retour comme_flottant(0); }
    soit mq = (1 << 52) - 1;
    soit ma = x & mq;
    soit mb = y & mq;
    soit ea = (x >> 52) & 1023;
    soit eb = (y >> 52) & 1023;
    si ea == 1023 || (eb != 1023 && mb == 0) { retour comme_flottant(13835058055282163712); }
    si eb == 1023 || ma == 0 { retour a; }
    si ea == 0 { ea = 1; }
    si eb == 0 { eb = 1; }
    si ea < eb { retour a; }
    soit r = ma % mb;
    soit d = ea - eb;
    tantque d > 0 {
        soit k = d;
        si k > 5 { k = 5; }
        r = (r << (2 * k)) % mb;
        d = d - k;
    }
    soit s = sa << 62;
    si r == 0 { retour comme_flottant(s); }
    soit e = eb;
    soit q25 = 1 << 50;
    tantque r < q25 && e > 1 { r = r << 2; e = e - 1; }
    si r < q25 { e = 0; }
    retour comme_flottant(s | (e << 52) | r);
}
"""

# ------------------------------------------------------------------------------------------------ Dunon seul : les nombres de 0.6za
# (Lugus les a déjà, dans le bloc « le vocabulaire des nombres (0.6z) » de vtx128.py)
NOMBRES_DUNON = r"""
// le vocabulaire des nombres (0.6za, Dunon en 0.61) : un mot pour tous les types ; le doute ne se comble pas
fonction est_positif(x): logique { retour logique(x .> 0); }
fonction est_negatif(x): logique { retour logique(x .< 0); }
fonction est_nul(x): logique { retour logique(x == 0); }
fonction est_entier(x): logique { retour vrai; }
fonction est_infini(x): logique { retour faux; }
fonction est_su(x): logique { retour vrai; }
fonction partie_entiere(x) { retour x; }
fonction partie_decimale(x) { retour 0; }
fonction entre(x, a, b): logique { retour logique(x .>= a && x .<= b); }
fonction ecart(a, b) { si a .> b { retour a - b; } retour b - a; }
fonction __arrondi2(x, n) { retour x; }
fonction __signe_x(v: flottant_petuar): flottant_petuar {
    si !__vn_su(v) || v == 0.0Q { retour v; }
    si v < 0.0Q { retour 0.0Q - 1.0Q; }
    retour 1.0Q;
}
fonction __est_positif_x(v: flottant_petuar): logique { si !__vn_su(v) { retour __vn_doute(v); } retour logique(v > 0.0Q); }
fonction __est_negatif_x(v: flottant_petuar): logique { si !__vn_su(v) { retour __vn_doute(v); } retour logique(v < 0.0Q); }
fonction __est_nul_x(v: flottant_petuar): logique { si !__vn_su(v) { retour __vn_doute(v); } retour logique(v == 0.0Q); }
fonction __est_infini_x(v: flottant_petuar): logique { si !__vn_su(v) { retour __vn_doute(v); } retour logique(__vn_infini(v)); }
fonction __est_entier_x(v: flottant_petuar): logique {
    si !__vn_su(v) { retour __vn_doute(v); }
    si __vn_infini(v) { retour faux; }
    retour logique(__partie_entiere_x(v) == v);
}
fonction __est_su_x(v: flottant_petuar): logique { retour logique(__vn_su(v)); }
fonction __partie_entiere_x(v: flottant_petuar): flottant_petuar {
    si v < 0.0Q { retour plafond_128(v); }
    retour plancher_128(v);
}
fonction __partie_decimale_x(v: flottant_petuar): flottant_petuar {
    si __vn_su(v) && __vn_infini(v) { retour 0.0Q; }
    retour v - __partie_entiere_x(v);
}
fonction __entre_x(v: flottant_petuar, a: flottant_petuar, b: flottant_petuar): logique {
    si __vn_su(v) && __vn_su(a) && __vn_su(b) { retour logique(a <= v && v <= b); }
    si __vn_etat(v) == 3 || __vn_etat(a) == 3 || __vn_etat(b) == 3 { retour variable; }
    retour inconnu;
}
fonction __ecart_x(a: flottant_petuar, b: flottant_petuar): flottant_petuar { retour abs(a - b); }
fonction __borne_x(v: flottant_petuar, a: flottant_petuar, b: flottant_petuar): flottant_petuar {
    si v < a { retour a; }
    si v > b { retour b; }
    retour v;
}
fonction __arrondi2_x(v: flottant_petuar, n): flottant_petuar {
    si !__vn_su(v) || __vn_infini(v) { retour v; }
    soit q: flottant_petuar = 1.0Q;
    soit k = n;
    si n .< 0 { k = 0 - n; }
    pour i dans 0..k { q = q * 10.0Q; }
    soit m: flottant_petuar = abs(v);
    soit r: flottant_petuar = 0.0Q;
    si n .< 0 { r = __partie_entiere_x(m / q + 0.5Q) * q; } sinon { r = __partie_entiere_x(m * q + 0.5Q) / q; }
    si v < 0.0Q { retour 0.0Q - r; }
    retour r;
}
fonction __signe_w(x: entier_128): entier_128 { si x < 0LL { retour 0LL - 1LL; } si x > 0LL { retour 1LL; } retour 0LL; }
fonction __est_positif_w(x: entier_128): logique { retour logique(x > 0LL); }
fonction __est_negatif_w(x: entier_128): logique { retour logique(x < 0LL); }
fonction __est_nul_w(x: entier_128): logique { retour logique(x == 0LL); }
fonction __est_infini_w(x: entier_128): logique { retour faux; }
fonction __est_entier_w(x: entier_128): logique { retour vrai; }
fonction __est_su_w(x: entier_128): logique { retour vrai; }
fonction __partie_entiere_w(x: entier_128): entier_128 { retour x; }
fonction __partie_decimale_w(x: entier_128): entier_128 { retour 0LL; }
fonction __entre_w(x: entier_128, a: entier_128, b: entier_128): logique { retour logique(a <= x && x <= b); }
fonction __ecart_w(a: entier_128, b: entier_128): entier_128 { si a > b { retour a - b; } retour b - a; }
fonction __borne_w(x: entier_128, a: entier_128, b: entier_128): entier_128 { si x < a { retour a; } si x > b { retour b; } retour x; }
fonction __arrondi2_w(x: entier_128, n): entier_128 { retour x; }
fonction __signe_i(x: entier_32): entier_32 { si x .< 0S { retour 0S - 1S; } si x .> 0S { retour 1S; } retour 0S; }
fonction __est_positif_i(x: entier_32): logique { retour logique(x .> 0S); }
fonction __est_negatif_i(x: entier_32): logique { retour logique(x .< 0S); }
fonction __est_nul_i(x: entier_32): logique { retour logique(x == 0S); }
fonction __est_infini_i(x: entier_32): logique { retour faux; }
fonction __est_entier_i(x: entier_32): logique { retour vrai; }
fonction __est_su_i(x: entier_32): logique { retour vrai; }
fonction __partie_entiere_i(x: entier_32): entier_32 { retour x; }
fonction __partie_decimale_i(x: entier_32): entier_32 { retour 0S; }
fonction __entre_i(x: entier_32, a: entier_32, b: entier_32): logique { retour logique(x .>= a && x .<= b); }
fonction __ecart_i(a: entier_32, b: entier_32): entier_32 { si a .> b { retour a - b; } retour b - a; }
fonction __borne_i(x: entier_32, a: entier_32, b: entier_32): entier_32 { si x .< a { retour a; } si x .> b { retour b; } retour x; }
fonction __arrondi2_i(x: entier_32, n): entier_32 { retour x; }
"""

# ------------------------------------------------------------------------------------------------ le vocabulaire commun
COMMUN = r"""
// -- famille « nombres » : un mot pour tous les types (le compilateur choisit la variante)
// carre : Arduino sq
fonction carre(x) { retour x * x; }
fonction __carre_x(v: flottant_petuar): flottant_petuar { retour v * v; }
fonction __carre_w(x: entier_128): entier_128 { retour x * x; }
fonction __carre_i(x: entier_32): entier_32 { retour x * x; }
// remapper : Arduino map, UE FMath::GetMappedRangeValueUnclamped, Blender « Map Range »
fonction remapper(x, a1, b1, a2, b2) {
    si b1 == a1 { retour a2; }
    retour (x - a1) * (b2 - a2) ./ (b1 - a1) + a2;
}
fonction __remapper_x(v: flottant_petuar, a1: flottant_petuar, b1: flottant_petuar, a2: flottant_petuar, b2: flottant_petuar): flottant_petuar {
    si b1 == a1 { retour a2; }
    retour a2 + (v - a1) * (b2 - a2) / (b1 - a1);
}
// est_fini : Rust is_finite
fonction est_fini(x): logique { retour vrai; }
fonction __est_fini_x(v: flottant_petuar): logique {
    si !__vn_su(v) { retour __vn_doute(v); }
    retour logique(!__vn_infini(v));
}
fonction __est_fini_w(x: entier_128): logique { retour vrai; }
fonction __est_fini_i(x: entier_32): logique { retour vrai; }
// reste : Rust % sur les flottants et les entiers signés, C fmod, UE FMath::Fmod ; exact, du signe du dividende ;
// reste(x, 0.0) : variable (un entier par zéro rend x, comme la machine)
fonction reste(a, b) { retour a .% b; }
fonction __reste_x(a: flottant_petuar, b: flottant_petuar): flottant_petuar { retour __vn_reste(a, b); }
fonction __reste_w(a: entier_128, b: entier_128): entier_128 { si b == 0LL { retour a; } retour a % b; }
fonction __reste_i(a: entier_32, b: entier_32): entier_32 { retour a .% b; }

// -- famille « flottants » (Rust f64, UE FMath, Blender) : le flottant principal, et ses variantes
// racine_cubique : Rust cbrt
fonction racine_cubique(x: flottant_petuar): flottant_petuar {
    si !__vn_su(x) || x == 0.0Q || __vn_infini(x) { retour x; }
    soit a: flottant_petuar = abs(x);
    soit y: flottant_petuar = exponentielle_128(logarithme_128(a) / 3.0Q);
    pour k dans 0..3 { y = y - (y * y * y - a) / (3.0Q * y * y); }
    si x < 0.0Q { retour 0.0Q - y; }
    retour y;
}
// hypotenuse : Rust hypot (sans débordement)
fonction hypotenuse(a: flottant_petuar, b: flottant_petuar): flottant_petuar {
    si !__vn_su(a) || !__vn_su(b) { retour a + b; }
    soit m: flottant_petuar = abs(a);
    soit n: flottant_petuar = abs(b);
    si n > m { m = abs(b); n = abs(a); }
    si m == 0.0Q || __vn_infini(m) { retour m; }
    soit r: flottant_petuar = n / m;
    retour m * racine(1.0Q + r * r);
}
// inverse : Rust recip
fonction inverse(x: flottant_petuar): flottant_petuar { retour 1.0Q / x; }
// vers_degres, vers_radians : Rust to_degrees, to_radians ; UE RadiansToDegrees
fonction vers_degres(x: flottant_petuar): flottant_petuar { retour x / (pi_128() / 180.0Q); }
fonction vers_radians(x: flottant_petuar): flottant_petuar { retour x * pi_128() / 180.0Q; }
// copier_signe : Rust copysign (un signe inconnu ou contradictoire le reste)
fonction copier_signe(x: flottant_petuar, s: flottant_petuar): flottant_petuar {
    si !__vn_su(s) {
        si __vn_etat(s) == 3 { retour __vn_variable(); }
        retour __vn_inconnu();
    }
    si !__vn_su(x) { retour x; }
    si __vn_etat(s) == 1 { retour 0.0Q - abs(x); }
    retour abs(x);
}
// multiplier_ajouter : Rust mul_add, C fma, UE FMath::FMA ; 0.65 : exact, un seul arrondi (au plus proche, pair au
// milieu, comme la machine), sur chaque flottant ; sur les entiers, a · b + c
fonction multiplier_ajouter(a, b, c) { retour a * b + c; }
fonction __multiplier_ajouter_w(a: entier_128, b: entier_128, c: entier_128): entier_128 { retour a * b + c; }
fonction __multiplier_ajouter_i(a: entier_32, b: entier_32, c: entier_32): entier_32 { retour a * b + c; }
// le produit exact de deux grands entiers (limbes de 16 bits, le plus bas d'abord)
fonction __bn_produit(a, b) {
    soit r = __bn_neuf(0);
    pour i dans 0..longueur(b) {
        si b[i] != 0 {
            soit t = __bn_copie(a);
            __bn_mul(t, b[i]);
            __bn_decaler(t, 16 * i);
            __bn_ajouter(r, t);
        }
    }
    retour r;
}
// la valeur d'un grand entier qui tient dans 64 bits
fonction __bn_valeur(a) {
    soit v = 0;
    soit i = longueur(a);
    tantque i > 0 {
        i = i - 1;
        v = (v << 16) | a[i];
    }
    retour v;
}
// le multiplier-ajouter exact, sur les mantisses (0.65) : a·b + c calculé sans arrondi, puis arrondi une seule fois au
// plus proche, pair au milieu (comme la machine) ; sa, sb, sc les états (1 négatif, 2 positif), ma, mb, mc les mantisses
// (des grands entiers), xa, xb, xc les exposants (max(E, 1)) ; p les bits de mantisse, biais, emax l'exposant de l'infini.
// Rend [l'état, l'exposant écrit, la mantisse (un grand entier)]
fonction __vn_fma_coeur(sa, ma, xa, sb, mb, xb, sc, mc, xc, p, biais, emax) {
    // le produit : mp × 4^(xp − 2·biais) ; c : mc × 4^(xc' − 2·biais), avec xc' = xc + biais
    soit mp = __bn_produit(ma, mb);
    soit xp = xa + xb;
    soit xq = xc + biais;
    soit sp = 2;
    si sa != sb {
        sp = 1;
    }
    soit lp = __bn_bits(mp);
    soit lc = __bn_bits(mc);
    // un terme bien plus petit que l'autre ne compte que par son signe : il devient une miette, sous le dernier bit de
    // l'autre (la même place pour l'arrondi, et une somme qui reste courte)
    si xp + (lp + 1) / 2 + 2 <= xq {
        mp = __bn_neuf(1);
        xp = xq - 3;
        lp = 1;
    } sinon si lp >= p + 2 && xq + (lc + 1) / 2 + 2 <= xp {
        mc = __bn_neuf(1);
        xq = xp - 3;
        lc = 1;
    }
    // aligner
    soit x0 = xp;
    si xq < x0 {
        x0 = xq;
    }
    si xp > x0 {
        __bn_decaler(mp, 2 * (xp - x0));
    }
    si xq > x0 {
        __bn_decaler(mc, 2 * (xq - x0));
    }
    soit s = sp;
    soit m = mp;
    si sp == sc {
        __bn_ajouter(m, mc);
    } sinon {
        soit kc = __bn_cmp(mp, mc);
        si kc == 0 {
            // une somme nulle exacte : +0
            retour [2, 0, __bn_neuf(0)];
        }
        si kc == 1 {
            __bn_sub(m, mc);
        } sinon {
            m = mc;
            __bn_sub(m, mp);
            s = sc;
        }
    }
    // arrondir m × 4^(x0 − 2·biais) à p bits : la mantisse m / 4^k, l'exposant écrit x0 + k − biais, au moins 1 (en
    // dessous, un sous-normal) ; k peut être négatif (un décalage à gauche, exact)
    soit l = __bn_bits(m);
    soit k = 0;
    si l > p {
        k = (l - p + 1) / 2;
    } sinon {
        k = 0 - (p - l) / 2;
    }
    soit kmin = 1 + biais - x0;
    si kmin .> k {
        k = kmin;
    }
    si k .> 0 {
        soit demi = __bn_bit(m, 2 * k - 1);
        soit sous = 1 - __bn_bas_nul(m, 2 * k - 1);
        __bn_droite(m, 2 * k);
        si demi == 1 && (sous == 1 || __bn_bit(m, 0) == 1) {
            __bn_ajouter(m, __bn_neuf(1));
        }
    } sinon si k .< 0 {
        __bn_decaler(m, 2 * (0 - k));
    }
    soit ef = x0 + k - biais;
    si __bn_bits(m) > p {
        __bn_droite(m, 2);
        ef = ef + 1;
    }
    si ef .>= emax {
        retour [s, emax, __bn_neuf(0)];
    }
    si __bn_bits(m) < p - 1 {
        ef = 0;
    }
    retour [s, ef, m];
}

fonction __multiplier_ajouter_f(a: flottant, b: flottant, c: flottant): flottant {
    // 0.65 : le flottant de 64 bits, exact puis arrondi une seule fois
    soit x = bits(a);
    soit y = bits(b);
    soit z = bits(c);
    soit q = 4503599627370495;
    soit ea = (x >> 52) & 1023;
    soit eb = (y >> 52) & 1023;
    soit ec = (z >> 52) & 1023;
    soit sa = x >> 62;
    soit sb = y >> 62;
    soit sc = z >> 62;
    si sa == 0 || sa == 3 || sb == 0 || sb == 3 || sc == 0 || sc == 3 || ea == 1023 || eb == 1023 || ec == 1023
            || (x & q) == 0 || (y & q) == 0 || (z & q) == 0 {
        retour a * b + c;
    }
    si ea == 0 { ea = 1; }
    si eb == 0 { eb = 1; }
    si ec == 0 { ec = 1; }
    soit r = __vn_fma_coeur(sa, __bn_neuf(x & q), ea, sb, __bn_neuf(y & q), eb, sc, __bn_neuf(z & q), ec, 52, 537, 1023);
    retour comme_flottant((r[0] << 62) | (r[1] << 52) | __bn_valeur(r[2]));
}
fonction __multiplier_ajouter_s(a: flottant_32, b: flottant_32, c: flottant_32): flottant_32 {
    // 0.65 : le flottant de 32 bits, exact puis arrondi une seule fois
    soit x = bits(a);
    soit y = bits(b);
    soit z = bits(c);
    soit q = 4194303;
    soit ea = (x >> 22) & 255;
    soit eb = (y >> 22) & 255;
    soit ec = (z >> 22) & 255;
    soit sa = (x >> 30) & 3;
    soit sb = (y >> 30) & 3;
    soit sc = (z >> 30) & 3;
    si sa == 0 || sa == 3 || sb == 0 || sb == 3 || sc == 0 || sc == 3 || ea == 255 || eb == 255 || ec == 255
            || (x & q) == 0 || (y & q) == 0 || (z & q) == 0 {
        retour a * b + c;
    }
    si ea == 0 { ea = 1; }
    si eb == 0 { eb = 1; }
    si ec == 0 { ec = 1; }
    soit r = __vn_fma_coeur(sa, __bn_neuf(x & q), ea, sb, __bn_neuf(y & q), eb, sc, __bn_neuf(z & q), ec, 22, 138, 255);
    retour comme_flottant_32((r[0] << 30) | (r[1] << 22) | __bn_valeur(r[2]));
}
fonction __vn_puissance_exacte(b: flottant_petuar, k): flottant_petuar {
    // b^k par carrés successifs (k signé) : exact tant que le résultat tient dans la mantisse
    soit p: flottant_petuar = 1.0Q;
    soit e = k;
    si k .< 0 { e = 0 - k; }
    soit c: flottant_petuar = b;
    tantque e != 0 {
        si (e & 1) == 1 { p = p * c; }
        c = c * c;
        e = e >> 1;
    }
    si k .< 0 { retour 1.0Q / p; }
    retour p;
}
fonction __vn_log_base(x: flottant_petuar, b: flottant_petuar): flottant_petuar {
    si !__vn_su(x) { retour x; }
    soit r: flottant_petuar = logarithme_128(x) / logarithme_128(b);
    si !__vn_su(r) || __vn_infini(r) { retour r; }
    // une puissance exacte de la base donne l'entier exact
    soit k: flottant_petuar = __arrondi2_x(r, 0);
    si abs(r - k) < 0.000001Q && abs(k) < 4000.0Q {
        soit ki = entier(k);
        si __vn_puissance_exacte(b, ki) == x { retour k; }
    }
    retour r;
}
// logarithme2, logarithme10, logarithme_base : Rust log2, log10, log(base)
fonction logarithme2(x: flottant_petuar): flottant_petuar { retour __vn_log_base(x, 2.0Q); }
fonction logarithme10(x: flottant_petuar): flottant_petuar { retour __vn_log_base(x, 10.0Q); }
fonction logarithme_base(x: flottant_petuar, b: flottant_petuar): flottant_petuar { retour __vn_log_base(x, b); }
// sinus_hyp, cosinus_hyp, tangente_hyp : Rust sinh, cosh, tanh (en série près de zéro : pas de perte de chiffres)
fonction sinus_hyp(x: flottant_petuar): flottant_petuar {
    si !__vn_su(x) || x == 0.0Q { retour x; }
    si abs(x) < 0.5Q {
        soit s: flottant_petuar = x;
        soit t: flottant_petuar = x;
        soit x2: flottant_petuar = x * x;
        pour k dans 1..30 {
            soit kk: flottant_petuar = flottant_petuar(2 * k);
            t = t * x2 / (kk * (kk + 1.0Q));
            s = s + t;
        }
        retour s;
    }
    soit e: flottant_petuar = exponentielle_128(x);
    retour (e - 1.0Q / e) / 2.0Q;
}
fonction cosinus_hyp(x: flottant_petuar): flottant_petuar {
    si !__vn_su(x) { retour x; }
    soit e: flottant_petuar = exponentielle_128(abs(x));
    retour (e + 1.0Q / e) / 2.0Q;
}
fonction tangente_hyp(x: flottant_petuar): flottant_petuar {
    si !__vn_su(x) || x == 0.0Q { retour x; }
    si x > 40.0Q { retour 1.0Q; }
    si x < 0.0Q - 40.0Q { retour 0.0Q - 1.0Q; }
    retour sinus_hyp(x) / cosinus_hyp(x);
}
// argsinus_hyp, argcosinus_hyp, argtangente_hyp : Rust asinh, acosh, atanh (hors du domaine : variable)
fonction argsinus_hyp(x: flottant_petuar): flottant_petuar {
    si !__vn_su(x) || x == 0.0Q || __vn_infini(x) { retour x; }
    soit a: flottant_petuar = abs(x);
    soit r: flottant_petuar = 0.0Q;
    si a < 0.5Q {
        soit t: flottant_petuar = a;
        soit x2: flottant_petuar = a * a;
        r = a;
        pour n dans 0..70 {
            soit u: flottant_petuar = flottant_petuar(2 * n + 1);
            t = t * x2 * u * u / ((u + 1.0Q) * (u + 2.0Q));
            si (n & 1) == 0 { r = r - t; } sinon { r = r + t; }
        }
    } sinon {
        r = logarithme_128(a + racine(a * a + 1.0Q));
    }
    si x < 0.0Q { retour 0.0Q - r; }
    retour r;
}
fonction argcosinus_hyp(x: flottant_petuar): flottant_petuar {
    si !__vn_su(x) { retour x; }
    si x < 1.0Q { retour __vn_variable(); }
    si __vn_infini(x) { retour x; }
    retour logarithme_128(x + racine(x * x - 1.0Q));
}
fonction argtangente_hyp(x: flottant_petuar): flottant_petuar {
    si !__vn_su(x) || x == 0.0Q { retour x; }
    soit a: flottant_petuar = abs(x);
    si a > 1.0Q { retour __vn_variable(); }
    si a == 1.0Q { retour x / 0.0Q; }
    soit r: flottant_petuar = 0.0Q;
    si a < 0.5Q {
        soit t: flottant_petuar = a;
        soit x2: flottant_petuar = a * a;
        r = a;
        pour n dans 1..90 {
            t = t * x2;
            r = r + t / flottant_petuar(2 * n + 1);
        }
    } sinon {
        r = logarithme_128((1.0Q + a) / (1.0Q - a)) / 2.0Q;
    }
    si x < 0.0Q { retour 0.0Q - r; }
    retour r;
}

// -- famille « interpolation » (UE FMath, Blender, Godot, Arduino)
// interpoler : UE Lerp, Blender mix, Rust f64::lerp (nightly)
fonction interpoler(a: flottant_petuar, b: flottant_petuar, t: flottant_petuar): flottant_petuar { retour a + (b - a) * t; }
// interpolation_inverse : UE GetRangePct, Godot inverse_lerp
fonction interpolation_inverse(a: flottant_petuar, b: flottant_petuar, v: flottant_petuar): flottant_petuar {
    si b == a { retour 0.0Q; }
    retour (v - a) / (b - a);
}
// remapper_borne : UE GetMappedRangeValueClamped, Blender « Map Range » (clamp)
fonction remapper_borne(v: flottant_petuar, a1: flottant_petuar, b1: flottant_petuar, a2: flottant_petuar, b2: flottant_petuar): flottant_petuar {
    si b1 == a1 { retour a2; }
    soit t: flottant_petuar = __borne_x((v - a1) / (b1 - a1), 0.0Q, 1.0Q);
    retour a2 + (b2 - a2) * t;
}
// pas_lisse, pas_plus_lisse : GLSL smoothstep, UE SmoothStep, Blender « Smooth Step », Perlin smootherstep
fonction pas_lisse(e0: flottant_petuar, e1: flottant_petuar, x: flottant_petuar): flottant_petuar {
    si e1 == e0 { si x < e0 { retour 0.0Q; } retour 1.0Q; }
    soit t: flottant_petuar = __borne_x((x - e0) / (e1 - e0), 0.0Q, 1.0Q);
    retour t * t * (3.0Q - 2.0Q * t);
}
fonction pas_plus_lisse(e0: flottant_petuar, e1: flottant_petuar, x: flottant_petuar): flottant_petuar {
    si e1 == e0 { si x < e0 { retour 0.0Q; } retour 1.0Q; }
    soit t: flottant_petuar = __borne_x((x - e0) / (e1 - e0), 0.0Q, 1.0Q);
    retour t * t * t * (t * (t * 6.0Q - 15.0Q) + 10.0Q);
}
// rapprocher : UE FInterpConstantTo, Godot move_toward (au plus « pas » à chaque appel)
fonction rapprocher(c: flottant_petuar, cible: flottant_petuar, pas: flottant_petuar): flottant_petuar {
    soit d: flottant_petuar = cible - c;
    si abs(d) <= pas { retour cible; }
    si d > 0.0Q { retour c + pas; }
    retour c - pas;
}
// amortir : UE FInterpTo (une part du chemin, selon le temps écoulé et la vitesse)
fonction amortir(c: flottant_petuar, cible: flottant_petuar, dt: flottant_petuar, vitesse: flottant_petuar): flottant_petuar {
    si vitesse <= 0.0Q { retour cible; }
    retour c + (cible - c) * __borne_x(dt * vitesse, 0.0Q, 1.0Q);
}
// presque_egal : UE IsNearlyEqual, Rust (a - b).abs() <= tol ; le doute reste
fonction presque_egal(a: flottant_petuar, b: flottant_petuar, tol: flottant_petuar): logique {
    si !__vn_su(a) || !__vn_su(b) || !__vn_su(tol) {
        si __vn_etat(a) == 3 || __vn_etat(b) == 3 || __vn_etat(tol) == 3 { retour variable; }
        retour inconnu;
    }
    retour logique(abs(a - b) <= tol);
}
// enrouler : UE FMath::Wrap, Blender « Wrap », Rust rem_euclid sur un intervalle [a, b)
fonction enrouler(x: flottant_petuar, a: flottant_petuar, b: flottant_petuar): flottant_petuar {
    soit l: flottant_petuar = b - a;
    si l <= 0.0Q { retour a; }
    retour x - l * plancher_128((x - a) / l);
}
// aller_retour : Blender pingpong
fonction aller_retour(x: flottant_petuar, l: flottant_petuar): flottant_petuar {
    si l <= 0.0Q { retour 0.0Q; }
    soit t: flottant_petuar = enrouler(x, 0.0Q, 2.0Q * l);
    si t > l { retour 2.0Q * l - t; }
    retour t;
}
// aimanter : UE GridSnap, Blender « Snap », Godot snapped (au multiple le plus proche)
fonction aimanter(x: flottant_petuar, pas: flottant_petuar): flottant_petuar {
    si pas == 0.0Q { retour x; }
    retour pas * plancher_128(x / pas + 0.5Q);
}
// entree_douce, sortie_douce, entree_sortie_douce : UE InterpEaseIn/Out (cubiques), easings.net
fonction entree_douce(t: flottant_petuar): flottant_petuar { retour t * t * t; }
fonction sortie_douce(t: flottant_petuar): flottant_petuar { soit u: flottant_petuar = 1.0Q - t; retour 1.0Q - u * u * u; }
fonction entree_sortie_douce(t: flottant_petuar): flottant_petuar {
    si t < 0.5Q { retour 4.0Q * t * t * t; }
    soit u: flottant_petuar = 2.0Q - 2.0Q * t;
    retour 1.0Q - u * u * u / 2.0Q;
}
// lire_flottant : Rust str::parse::<f64>, Arduino toFloat ; rien d'écrit : inconnu ; pas un nombre : variable
// (la virgule française est comprise ; plus de 34 chiffres : le dernier peut être arrondi deux fois)
fonction lire_flottant(t): flottant_petuar {
    soit n = longueur(t);
    soit i = 0;
    tantque i < n && (car(t, i) == 32 || car(t, i) == 9) { i = i + 1; }
    soit f = n;
    tantque f > i && (car(t, f - 1) == 32 || car(t, f - 1) == 9 || car(t, f - 1) == 10 || car(t, f - 1) == 13) { f = f - 1; }
    si i == f { retour __vn_inconnu(); }
    soit neg = 0;
    si car(t, i) == 45 { neg = 1; i = i + 1; } sinon si car(t, i) == 43 { i = i + 1; }
    soit m: flottant_petuar = 0.0Q;
    soit chiffres = 0;
    soit e10 = 0;
    tantque i < f && car(t, i) >= 48 && car(t, i) <= 57 {
        m = m * 10.0Q + flottant_petuar(car(t, i) - 48);
        chiffres = chiffres + 1;
        i = i + 1;
    }
    si i < f && (car(t, i) == 46 || car(t, i) == 44) {
        i = i + 1;
        tantque i < f && car(t, i) >= 48 && car(t, i) <= 57 {
            m = m * 10.0Q + flottant_petuar(car(t, i) - 48);
            chiffres = chiffres + 1;
            e10 = e10 - 1;
            i = i + 1;
        }
    }
    si chiffres == 0 { retour __vn_variable(); }
    si i < f && (car(t, i) == 101 || car(t, i) == 69) {
        i = i + 1;
        soit eneg = 0;
        si i < f && car(t, i) == 45 { eneg = 1; i = i + 1; } sinon si i < f && car(t, i) == 43 { i = i + 1; }
        soit ev = 0;
        soit ed = 0;
        tantque i < f && car(t, i) >= 48 && car(t, i) <= 57 {
            si ev < 100000 { ev = ev * 10 + car(t, i) - 48; }
            ed = ed + 1;
            i = i + 1;
        }
        si ed == 0 { retour __vn_variable(); }
        si eneg == 1 { e10 = e10 - ev; } sinon { e10 = e10 + ev; }
    }
    si i != f { retour __vn_variable(); }
    si e10 .< 0 { m = m / __vn_puissance_exacte(10.0Q, 0 - e10); } sinon { m = m * __vn_puissance_exacte(10.0Q, e10); }
    si neg == 1 { retour 0.0Q - m; }
    retour m;
}

// -- famille « entiers et bits » (Rust u64, Arduino) : l'entier de 64 bits
// compter_uns, compter_zeros, zeros_en_tete, zeros_en_queue : Rust count_ones, count_zeros, leading_zeros, trailing_zeros
fonction compter_uns(x) { retour nb_bits(x); }
// 0.833 : la largeur de l'entier (128 sur Lugus, 64 sur Dunon ou avec « dunon; ») : nb_bits(0 - 1)
fonction compter_zeros(x) { retour nb_bits(0 - 1) - nb_bits(x); }
fonction zeros_en_tete(x) {
    si x == 0 { retour nb_bits(0 - 1); }
    soit n = 0;
    soit v = x;
    soit haut = 1 << (nb_bits(0 - 1) - 1);
    tantque (v & haut) == 0 { n = n + 1; v = v << 1; }
    retour n;
}
fonction zeros_en_queue(x) {
    si x == 0 { retour nb_bits(0 - 1); }
    soit n = 0;
    soit v = x;
    tantque (v & 1) == 0 { n = n + 1; v = v >> 1; }
    retour n;
}
// tourner_gauche, tourner_droite, inverser_bits, echanger_octets : Rust rotate_left, rotate_right, reverse_bits, swap_bytes
fonction tourner_gauche(x, n) { soit l = nb_bits(0 - 1); soit k = n % l; si k == 0 { retour x; } retour (x << k) | (x >> (l - k)); }
fonction tourner_droite(x, n) { soit l = nb_bits(0 - 1); soit k = n % l; si k == 0 { retour x; } retour (x >> k) | (x << (l - k)); }
fonction inverser_bits(x) {
    soit r = 0;
    soit v = x;
    pour i dans 0..nb_bits(0 - 1) { r = (r << 1) | (v & 1); v = v >> 1; }
    retour r;
}
fonction echanger_octets(x) {
    soit r = 0;
    soit v = x;
    pour i dans 0..nb_bits(0 - 1) / 8 { r = (r << 8) | (v & 255); v = v >> 8; }
    retour r;
}
// est_puissance_de_deux, puissance_de_deux_suivante : Rust is_power_of_two, next_power_of_two (0 si elle dépasse 64 bits)
fonction est_puissance_de_deux(x): logique { retour logique(x != 0 && (x & (x - 1)) == 0); }
fonction puissance_de_deux_suivante(x) {
    si x <= 1 { retour 1; }
    soit p = 1;
    tantque p < x && p != 0 { p = p << 1; }
    retour p;
}
// log2_entier, log10_entier, racine_entiere : Rust ilog2, ilog10, isqrt (log de 0 : (0 - 1), comme « absent »)
fonction log2_entier(x) { si x == 0 { retour (0 - 1); } retour nb_bits(0 - 1) - 1 - zeros_en_tete(x); }
fonction log10_entier(x) {
    si x == 0 { retour (0 - 1); }
    soit n = 0;
    soit v = x;
    tantque v >= 10 { v = v / 10; n = n + 1; }
    retour n;
}
fonction racine_entiere(x) {
    // 0.839 : la plus haute puissance de 4 du mot (2^126 sur Lugus, 2^62 sur Dunon : juste au-delà de 2^64 aussi)
    soit r = 0;
    soit v = x;
    soit b = 1 << (nb_bits(0 - 1) - 2);
    tantque b > v { b = b >> 2; }
    tantque b != 0 {
        si v >= r + b { v = v - (r + b); r = (r >> 1) + b; } sinon { r = r >> 1; }
        b = b >> 2;
    }
    retour r;
}
// reste_euclidien, quotient_euclidien : Rust rem_euclid, div_euclid (signés) ; num-integer mod_floor
fonction reste_euclidien(a, b) {
    soit r = a .% b;
    si r .< 0 { si b .< 0 { r = r - b; } sinon { r = r + b; } }
    retour r;
}
fonction quotient_euclidien(a, b) {
    soit q = a ./ b;
    si (a .% b) .< 0 { si b .> 0 { q = q - 1; } sinon { q = q + 1; } }
    retour q;
}
// division_plafond, multiple_suivant, milieu : Rust div_ceil, next_multiple_of, midpoint
fonction division_plafond(a, b) { soit q = a / b; si a % b != 0 { q = q + 1; } retour q; }
fonction multiple_suivant(x, m) {
    si m == 0 { retour x; }
    soit r = x % m;
    si r == 0 { retour x; }
    retour x + (m - r);
}
fonction milieu(a, b) { retour (a & b) + ((a ^ b) >> 1); }
// est_pair, est_impair : num-integer is_even, is_odd
fonction est_pair(x): logique { retour logique((x & 1) == 0); }
fonction est_impair(x): logique { retour logique((x & 1) == 1); }
// addition_saturee, soustraction_saturee, multiplication_saturee, deborde_addition, deborde_multiplication : Rust
// saturating_add, saturating_sub, saturating_mul (bornés à 0 et au plus grand entier) ; overflowing_add, overflowing_mul (vrai si
// le calcul déborde)
fonction addition_saturee(a, b) { soit s = a + b; si s < a { retour 0 - 1; } retour s; }
fonction soustraction_saturee(a, b) { si b > a { retour 0; } retour a - b; }
fonction multiplication_saturee(a, b) {
    si a != 0 && b > (0 - 1) / a { retour 0 - 1; }
    retour a * b;
}
fonction deborde_addition(a, b): logique { retour logique(a + b < a); }
fonction deborde_multiplication(a, b): logique { retour logique(a != 0 && b > (0 - 1) / a); }
// lire_bit, poser_bit, effacer_bit, ecrire_bit, basculer_bit, masque_bit : Arduino bitRead, bitSet, bitClear, bitWrite, bit()
fonction lire_bit(x, n) { retour (x >> n) & 1; }
fonction poser_bit(x, n) { retour x | (1 << n); }
fonction effacer_bit(x, n) { retour x & ~(1 << n); }
fonction basculer_bit(x, n) { retour x ^ (1 << n); }
fonction ecrire_bit(x, n, b) { si b != 0 { retour x | (1 << n); } retour x & ~(1 << n); }
fonction masque_bit(n) { retour 1 << n; }
// octet_bas, octet_haut, octet, mot_de : Arduino lowByte, highByte, word(h, l) ; Rust to_le_bytes
fonction octet_bas(x) { retour x & 255; }
fonction octet_haut(x) { retour (x >> 8) & 255; }
fonction octet(x, k) { retour (x >> (8 * k)) & 255; }
fonction mot_de(h, l) { retour ((h & 255) << 8) | (l & 255); }

// -- famille « textes » (Rust str et char, Arduino String) ; les questions rendent 1 ou 0, comme commence_par
// est_vide : Rust is_empty, Arduino length() == 0 (un texte ou un tableau)
fonction est_vide(t) { si longueur(t) == 0 { retour 1; } retour 0; }
// contient_texte, position_derniere : Rust contains, rfind ; Arduino indexOf, lastIndexOf
fonction contient_texte(t, m) { si position(t, m) != (0 - 1) { retour 1; } retour 0; }
fonction position_derniere(t, m) {
    soit n = longueur(t);
    soit k = longueur(m);
    si k > n { retour (0 - 1); }
    soit i = n - k + 1;
    tantque i > 0 {
        i = i - 1;
        soit j = 0;
        tantque j < k && car(t, i + j) == car(m, j) { j = j + 1; }
        si j == k { retour i; }
    }
    retour (0 - 1);
}
fonction __est_blanc(c) { retour c == 32 || c == 9 || c == 10 || c == 13; }
// rogner_debut, rogner_fin : Rust trim_start, trim_end (nettoyer : trim)
fonction rogner_debut(t): texte {
    soit a = 0;
    soit n = longueur(t);
    tantque a < n && __est_blanc(car(t, a)) { a = a + 1; }
    retour sous_texte(t, a, n);
}
fonction rogner_fin(t): texte {
    soit b = longueur(t);
    tantque b > 0 && __est_blanc(car(t, b - 1)) { b = b - 1; }
    retour sous_texte(t, 0, b);
}
// sans_prefixe, sans_suffixe : Rust strip_prefix, strip_suffix (le texte tel quel s'il n'y est pas)
fonction sans_prefixe(t, p): texte {
    si commence_par(t, p) == 1 { retour sous_texte(t, longueur(p), longueur(t)); }
    retour sous_texte(t, 0, longueur(t));
}
fonction sans_suffixe(t, s): texte {
    si finit_par(t, s) == 1 { retour sous_texte(t, 0, longueur(t) - longueur(s)); }
    retour sous_texte(t, 0, longueur(t));
}
// remplacer_premier : Rust replacen(a, b, 1)
fonction remplacer_premier(t, a, b): texte {
    soit p = position(t, a);
    si p == (0 - 1) || longueur(a) == 0 { retour sous_texte(t, 0, longueur(t)); }
    retour __texte_plus(__texte_plus(sous_texte(t, 0, p), b), sous_texte(t, p + longueur(a), longueur(t)));
}
// lignes, mots, couper_en_deux : Rust lines, split_whitespace, split_once (des tableaux de textes)
fonction lignes(t) {
    soit r = tableau(0);
    soit n = longueur(t);
    soit d = 0;
    pour i dans 0..n {
        si car(t, i) == 10 {
            soit f = i;
            si f > d && car(t, f - 1) == 13 { f = f - 1; }
            __ajouter(r, sous_texte(t, d, f));
            d = i + 1;
        }
    }
    si d < n {
        soit g = n;
        si car(t, n - 1) == 13 { g = n - 1; }
        __ajouter(r, sous_texte(t, d, g));
    }
    retour r;
}
fonction mots(t) {
    soit r = tableau(0);
    soit n = longueur(t);
    soit d = 0;
    soit dedans = 0;
    pour i dans 0..n {
        si __est_blanc(car(t, i)) {
            si dedans == 1 { __ajouter(r, sous_texte(t, d, i)); dedans = 0; }
        } sinon si dedans == 0 {
            d = i;
            dedans = 1;
        }
    }
    si dedans == 1 { __ajouter(r, sous_texte(t, d, n)); }
    retour r;
}
fonction couper_en_deux(t, sep) {
    soit r = tableau(0);
    soit p = position(t, sep);
    si p == (0 - 1) { __ajouter(r, sous_texte(t, 0, longueur(t))); retour r; }
    __ajouter(r, sous_texte(t, 0, p));
    __ajouter(r, sous_texte(t, p + longueur(sep), longueur(t)));
    retour r;
}
// caracteres, texte_de_caracteres : Rust chars().collect(), String::from_iter
fonction caracteres(t) {
    soit r = tableau(0);
    pour i dans 0..longueur(t) { __ajouter(r, car(t, i)); }
    retour r;
}
fonction texte_de_caracteres(tc): texte {
    soit n = longueur(tc);
    soit r = texte_neuf(n);
    pour i dans 0..n { changer_car(r, i, tc[i]); }
    retour r;
}
fonction __minuscule_car(c) {
    si c >= 65 && c <= 90 { retour c + 32; }
    si c >= 192 && c <= 222 && c != 215 { retour c + 32; }
    retour c;
}
// egal_sans_casse, comparer_textes : Rust eq_ignore_ascii_case, Ord::cmp ; Arduino equalsIgnoreCase, compareTo
fonction egal_sans_casse(a, b) {
    soit n = longueur(a);
    si n != longueur(b) { retour 0; }
    pour i dans 0..n { si __minuscule_car(car(a, i)) != __minuscule_car(car(b, i)) { retour 0; } }
    retour 1;
}
fonction comparer_textes(a, b) {
    soit na = longueur(a);
    soit nb = longueur(b);
    soit n = na;
    si nb < n { n = nb; }
    pour i dans 0..n {
        soit x = car(a, i);
        soit y = car(b, i);
        si x < y { retour (0 - 1); }
        si x > y { retour 1; }
    }
    si na < nb { retour (0 - 1); }
    si na > nb { retour 1; }
    retour 0;
}
// est_espace, est_majuscule, est_minuscule, est_alphanumerique, est_ponctuation, est_hexadecimal, est_ascii, est_controle :
// Rust char::is_whitespace…, Arduino isSpace, isUpperCase, isLowerCase, isAlphaNumeric, isPunct, isHexadecimalDigit,
// isAscii, isControl
fonction est_espace(c) { si c == 32 || c == 9 || c == 10 || c == 13 || c == 11 || c == 12 || c == 160 { retour 1; } retour 0; }
fonction est_majuscule(c) { si (c >= 65 && c <= 90) || (c >= 192 && c <= 222 && c != 215) || c == 338 { retour 1; } retour 0; }
fonction est_minuscule(c) { si (c >= 97 && c <= 122) || (c >= 223 && c <= 255 && c != 247) || c == 339 { retour 1; } retour 0; }
fonction est_alphanumerique(c) { si est_lettre(c) == 1 || est_chiffre(c) == 1 { retour 1; } retour 0; }
fonction est_ponctuation(c) {
    si (c >= 33 && c <= 47) || (c >= 58 && c <= 64) || (c >= 91 && c <= 96) || (c >= 123 && c <= 126) || c == 171 || c == 187 { retour 1; }
    retour 0;
}
fonction est_hexadecimal(c) { si (c >= 48 && c <= 57) || (c >= 65 && c <= 70) || (c >= 97 && c <= 102) { retour 1; } retour 0; }
fonction est_ascii(c) { si c < 128 { retour 1; } retour 0; }
fonction est_controle(c) { si c < 32 || c == 127 { retour 1; } retour 0; }
// valeur_chiffre, chiffre_de : Rust char::to_digit, char::from_digit (absent : (0 - 1))
fonction valeur_chiffre(c, base) {
    soit v = 99;
    si c >= 48 && c <= 57 { v = c - 48; } sinon si c >= 97 && c <= 122 { v = c - 87; } sinon si c >= 65 && c <= 90 { v = c - 55; }
    si v >= base { retour (0 - 1); }
    retour v;
}
fonction chiffre_de(v, base) {
    si v >= base || v >= 36 { retour (0 - 1); }
    si v < 10 { retour 48 + v; }
    retour 87 + v;
}
// texte_base, lire_base : Rust format!("{:x}") et from_str_radix, Arduino String(n, HEX) (sans signe, base 2 à 36)
fonction texte_base(n, base): texte {
    si base < 2 || base > 36 { retour texte_neuf(0); }
    si n == 0 { retour car_texte(48); }
    soit tc = tableau(0);
    soit v = n;
    tantque v != 0 { __ajouter(tc, chiffre_de(v % base, base)); v = v / base; }
    inverser(tc);
    retour texte_de_caracteres(tc);
}
fonction lire_base(t, base) {
    soit r = 0;
    pour i dans 0..longueur(t) {
        soit v = valeur_chiffre(car(t, i), base);
        si v == (0 - 1) { retour r; }
        r = r * base + v;
    }
    retour r;
}
// completer_gauche, completer_droite : Rust format!("{:0>8}"), pad_start
fonction completer_gauche(t, n, c): texte {
    soit m = longueur(t);
    si m >= n { retour sous_texte(t, 0, m); }
    retour __texte_plus(repeter(car_texte(c), n - m), t);
}
fonction completer_droite(t, n, c): texte {
    soit m = longueur(t);
    si m >= n { retour sous_texte(t, 0, m); }
    retour __texte_plus(t, repeter(car_texte(c), n - m));
}

// -- famille « tableaux » (Rust slice et Vec, itertools) : des tableaux d'entiers
// premier, dernier : Rust first, last (0 pour un tableau vide)
fonction premier(t) { si longueur(t) == 0 { retour 0; } retour t[0]; }
fonction dernier(t) { soit n = longueur(t); si n == 0 { retour 0; } retour t[n - 1]; }
// echanger, remplir : Rust swap, fill
fonction echanger(t, i, j) { soit x = t[i]; t[i] = t[j]; t[j] = x; }
fonction remplir(t, v) { pour i dans 0..longueur(t) { t[i] = v; } }
// tourner_tableau, tourner_tableau_droite : Rust rotate_left, rotate_right
fonction tourner_tableau(t, k) {
    soit n = longueur(t);
    si n == 0 { retour; }
    soit d = k % n;
    si d == 0 { retour; }
    soit c = copie(t);
    pour i dans 0..n { t[i] = c[(i + d) % n]; }
}
fonction tourner_tableau_droite(t, k) {
    soit n = longueur(t);
    si n == 0 { retour; }
    tourner_tableau(t, n - k % n);
}
// est_trie, trier_decroissant : Rust is_sorted, sort_by(|a, b| b.cmp(a)) (signés)
fonction est_trie(t) { pour i dans 1..longueur(t) { si t[i] .< t[i - 1] { retour 0; } } retour 1; }
fonction trier_decroissant(t) { trier(t); inverser(t); }
// recherche_dichotomique : Rust binary_search (dans un tableau trié, signé ; absent : (0 - 1))
fonction recherche_dichotomique(t, v) {
    soit a = 0;
    soit b = longueur(t);
    tantque a < b {
        soit m = (a + b) / 2;
        si t[m] == v { retour m; }
        si t[m] .< v { a = m + 1; } sinon { b = m; }
    }
    retour (0 - 1);
}
// produit, moyenne, mediane : Rust iter().product(), statistiques (un tableau vide : la moyenne est inconnue)
fonction produit(t) { soit p = 1; pour x dans t { p = p * x; } retour p; }
fonction moyenne(t): flottant_petuar {
    soit n = longueur(t);
    si n == 0 { retour __vn_inconnu(); }
    soit s = 0;
    pour x dans t { s = s + x; }
    retour flottant_petuar_signe(s) / flottant_petuar(n);
}
fonction mediane(t): flottant_petuar {
    soit n = longueur(t);
    si n == 0 { retour __vn_inconnu(); }
    soit c = copie(t);
    trier(c);
    si n % 2 == 1 { retour flottant_petuar_signe(c[n / 2]); }
    retour (flottant_petuar_signe(c[n / 2 - 1]) + flottant_petuar_signe(c[n / 2])) / 2.0Q;
}
// cumul, differences : itertools scan (les sommes au fil), windows(2) (les écarts successifs)
fonction cumul(t) { soit r = tableau(0); soit s = 0; pour x dans t { s = s + x; ajouter(r, s); } retour r; }
fonction differences(t) { soit r = tableau(0); pour i dans 1..longueur(t) { ajouter(r, t[i] - t[i - 1]); } retour r; }
// fenetres, paquets : Rust windows(k), chunks(k) (des tableaux de tableaux)
fonction fenetres(t, k) {
    soit r = tableau(0);
    soit n = longueur(t);
    si k == 0 || k > n { retour r; }
    pour i dans 0..n - k + 1 { ajouter(r, tranche(t, i, i + k)); }
    retour r;
}
fonction paquets(t, k) {
    soit r = tableau(0);
    soit n = longueur(t);
    si k == 0 { retour r; }
    soit i = 0;
    tantque i < n {
        soit f = i + k;
        si f > n { f = n; }
        ajouter(r, tranche(t, i, f));
        i = f;
    }
    retour r;
}
// aplatir, concatener, prolonger : Rust concat (flatten), [a, b].concat(), extend
fonction aplatir(tt) { soit r = tableau(0); pour u dans tt { pour x dans u { ajouter(r, x); } } retour r; }
fonction concatener(a, b) { soit r = copie(a); pour x dans b { ajouter(r, x); } retour r; }
fonction prolonger(a, b) { soit c = copie(b); pour x dans c { ajouter(a, x); } }
// dedoublonner : Rust dedup (les répétitions qui se suivent ; sans_doublons : toutes)
fonction dedoublonner(t) {
    soit n = longueur(t);
    si n < 2 { retour; }
    soit w = 1;
    pour i dans 1..n { si t[i] != t[w - 1] { t[w] = t[i]; w = w + 1; } }
    tantque longueur(t) > w { retirer(t); }
}
// separer : Rust split_at (deux tableaux)
fonction separer(t, i) {
    soit r = tableau(0);
    soit n = longueur(t);
    soit k = i;
    si k > n { k = n; }
    ajouter(r, tranche(t, 0, k));
    ajouter(r, tranche(t, k, n));
    retour r;
}
// intervalle, intervalle_pas : Rust (a..b).collect(), step_by (signés)
fonction intervalle(a, b) { soit r = tableau(0); soit i = a; tantque i .< b { ajouter(r, i); i = i + 1; } retour r; }
fonction intervalle_pas(a, b, p) {
    soit r = tableau(0);
    si p == 0 { retour r; }
    soit i = a;
    si p .> 0 { tantque i .< b { ajouter(r, i); i = i + p; } } sinon { tantque i .> b { ajouter(r, i); i = i + p; } }
    retour r;
}
// zipper, entrelacer, produit_cartesien : Rust zip, itertools interleave, iproduct!
fonction zipper(a, b) {
    soit r = tableau(0);
    soit n = longueur(a);
    si longueur(b) < n { n = longueur(b); }
    pour i dans 0..n { soit p = tableau(0); ajouter(p, a[i]); ajouter(p, b[i]); ajouter(r, p); }
    retour r;
}
fonction entrelacer(a, b) {
    soit r = tableau(0);
    soit na = longueur(a);
    soit nb = longueur(b);
    soit n = na;
    si nb > n { n = nb; }
    pour i dans 0..n {
        si i < na { ajouter(r, a[i]); }
        si i < nb { ajouter(r, b[i]); }
    }
    retour r;
}
fonction produit_cartesien(a, b) {
    soit r = tableau(0);
    pour x dans a { pour y dans b { soit p = tableau(0); ajouter(p, x); ajouter(p, y); ajouter(r, p); } }
    retour r;
}
// position_max, position_min, chercher_dernier : itertools position_max, position_min ; Rust rposition
fonction position_max(t) {
    soit n = longueur(t);
    si n == 0 { retour (0 - 1); }
    soit k = 0;
    pour i dans 1..n { si t[i] .> t[k] { k = i; } }
    retour k;
}
fonction position_min(t) {
    soit n = longueur(t);
    si n == 0 { retour (0 - 1); }
    soit k = 0;
    pour i dans 1..n { si t[i] .< t[k] { k = i; } }
    retour k;
}
fonction chercher_dernier(t, v) {
    soit i = longueur(t);
    tantque i > 0 { i = i - 1; si t[i] == v { retour i; } }
    retour (0 - 1);
}
// tronquer_tableau, redimensionner, repeter_tableau : Rust truncate, resize, repeat
fonction tronquer_tableau(t, n) { tantque longueur(t) > n { retirer(t); } }
fonction redimensionner(t, n, v) {
    tantque longueur(t) > n { retirer(t); }
    tantque longueur(t) < n { ajouter(t, v); }
}
fonction repeter_tableau(t, k) { soit r = tableau(0); pour j dans 0..k { pour x dans t { ajouter(r, x); } } retour r; }
// combinaisons, permutations : itertools combinations(k), permutations (dans l'ordre ; prudence : n! tableaux)
fonction combinaisons(t, k) {
    soit r = tableau(0);
    soit n = longueur(t);
    si k > n { retour r; }
    soit idx = tableau(0);
    pour i dans 0..k { ajouter(idx, i); }
    soit fini = 0;
    tantque fini == 0 {
        soit c = tableau(0);
        pour j dans 0..k { ajouter(c, t[idx[j]]); }
        ajouter(r, c);
        soit p = k;
        soit trouve = 0;
        tantque p > 0 && trouve == 0 {
            p = p - 1;
            si idx[p] != p + n - k { trouve = 1; }
        }
        si trouve == 0 {
            fini = 1;
        } sinon {
            idx[p] = idx[p] + 1;
            pour q dans p + 1..k { idx[q] = idx[q - 1] + 1; }
        }
    }
    retour r;
}
fonction permutations(t) {
    soit r = tableau(0);
    soit n = longueur(t);
    soit idx = intervalle(0, n);
    soit encore = 1;
    tantque encore == 1 {
        soit c = tableau(0);
        pour j dans 0..n { ajouter(c, t[idx[j]]); }
        ajouter(r, c);
        si n < 2 {
            encore = 0;
        } sinon {
            soit i = n - 1;
            tantque i > 0 && idx[i - 1] >= idx[i] { i = i - 1; }
            si i == 0 {
                encore = 0;
            } sinon {
                soit j2 = n - 1;
                tantque idx[j2] <= idx[i - 1] { j2 = j2 - 1; }
                soit tmp = idx[i - 1];
                idx[i - 1] = idx[j2];
                idx[j2] = tmp;
                soit a2 = i;
                soit b2 = n - 1;
                tantque a2 < b2 {
                    soit t2 = idx[a2];
                    idx[a2] = idx[b2];
                    idx[b2] = t2;
                    a2 = a2 + 1;
                    b2 = b2 - 1;
                }
            }
        }
    }
    retour r;
}

// -- famille « hasard » (rand, Arduino random) : la même suite à chaque lancement, comme hasard()
// pile_ou_face, hasard_logique : rand gen_bool(0.5), une valeur de Belnap tirée
fonction pile_ou_face(): logique { si hasard(2) == 0 { retour faux; } retour vrai; }
fonction hasard_logique(): logique { retour comme_logique(hasard(4)); }
// hasard_chance : rand gen_bool(p) (1 avec la probabilité p)
fonction hasard_chance(p: flottant_petuar) { si __vn_hasard() < p { retour 1; } retour 0; }
// hasard_entre_flottant, hasard_normal : rand gen_range(a..b), rand_distr Normal (Box et Muller)
fonction hasard_entre_flottant(a: flottant_petuar, b: flottant_petuar): flottant_petuar { retour a + (b - a) * __vn_hasard(); }
fonction hasard_normal(m: flottant_petuar, e: flottant_petuar): flottant_petuar {
    soit u1: flottant_petuar = 1.0Q - __vn_hasard();
    soit u2: flottant_petuar = __vn_hasard();
    retour m + e * racine(0.0Q - 2.0Q * logarithme_128(u1)) * cosinus_128(2.0Q * pi_128() * u2);
}
// piocher_plusieurs, tirage_pondere : rand choose_multiple (sans remise), WeightedIndex
fonction piocher_plusieurs(t, k) { soit c = copie(t); brasser(c); tantque longueur(c) > k { retirer(c); } retour c; }
fonction tirage_pondere(poids) {
    soit total = 0;
    pour w dans poids { total = total + w; }
    si total == 0 { retour (0 - 1); }
    soit r = hasard(total);
    soit acc = 0;
    soit n = longueur(poids);
    pour i dans 0..n {
        acc = acc + poids[i];
        si r < acc { retour i; }
    }
    retour n - 1;
}

// -- famille « temps » (Arduino millis, delay) : horloge() est millis
// attendre : Arduino delay, std::thread::sleep (la machine compte ses millisecondes)
fonction attendre(ms) { soit t0 = horloge(); tantque horloge() - t0 < ms { } }

// -- famille « vecteurs, quaternions, matrices » (UE FVector, FQuat, FMatrix ; Blender mathutils ; glam)
// vecteur : FVector(x, y, z), mathutils.Vector ; un tableau de flottants (v[0], v[1], v[2] ; les autres mots prennent aussi
// 2 ou 4 cases ; un quaternion : w, x, y, z, comme Blender ; une matrice : 16 cases, ligne par ligne)
fonction vecteur(x: flottant_petuar, y: flottant_petuar, z: flottant_petuar): flottant[] {
    soit v = tableau(3);
    __vt_ecrire(v, 0, x);
    __vt_ecrire(v, 1, y);
    __vt_ecrire(v, 2, z);
    retour v;
}
// vecteur_somme, vecteur_difference, vecteur_echelle : +, -, * k
fonction vecteur_somme(a, b): flottant[] {
    soit n = longueur(a);
    soit r = tableau(n);
    pour i dans 0..n { __vt_ecrire(r, i, __vt_lire(a, i) + __vt_lire(b, i)); }
    retour r;
}
fonction vecteur_difference(a, b): flottant[] {
    soit n = longueur(a);
    soit r = tableau(n);
    pour i dans 0..n { __vt_ecrire(r, i, __vt_lire(a, i) - __vt_lire(b, i)); }
    retour r;
}
fonction vecteur_echelle(a, k: flottant_petuar): flottant[] {
    soit n = longueur(a);
    soit r = tableau(n);
    pour i dans 0..n { __vt_ecrire(r, i, __vt_lire(a, i) * k); }
    retour r;
}
// produit_scalaire, produit_vectoriel : FVector::DotProduct, CrossProduct ; mathutils dot, cross
fonction produit_scalaire(a, b): flottant_petuar {
    soit s: flottant_petuar = 0.0Q;
    pour i dans 0..longueur(a) { s = s + __vt_lire(a, i) * __vt_lire(b, i); }
    retour s;
}
fonction produit_vectoriel(a, b): flottant[] {
    soit r = tableau(3);
    __vt_ecrire(r, 0, __vt_lire(a, 1) * __vt_lire(b, 2) - __vt_lire(a, 2) * __vt_lire(b, 1));
    __vt_ecrire(r, 1, __vt_lire(a, 2) * __vt_lire(b, 0) - __vt_lire(a, 0) * __vt_lire(b, 2));
    __vt_ecrire(r, 2, __vt_lire(a, 0) * __vt_lire(b, 1) - __vt_lire(a, 1) * __vt_lire(b, 0));
    retour r;
}
// norme, norme_carree, normaliser, distance : Size, SizeSquared, GetSafeNormal, FVector::Dist ; length, normalized
fonction norme_carree(a): flottant_petuar { retour produit_scalaire(a, a); }
fonction norme(a): flottant_petuar { retour racine(produit_scalaire(a, a)); }
fonction normaliser(a): flottant[] {
    soit l: flottant_petuar = norme(a);
    si l == 0.0Q { retour vecteur_echelle(a, 1.0Q); }
    retour vecteur_echelle(a, 1.0Q / l);
}
fonction distance(a, b): flottant_petuar { retour norme(vecteur_difference(a, b)); }
// vecteur_interpoler : FMath::Lerp sur des vecteurs, mathutils lerp
fonction vecteur_interpoler(a, b, t: flottant_petuar): flottant[] {
    soit n = longueur(a);
    soit r = tableau(n);
    pour i dans 0..n { __vt_ecrire(r, i, __vt_lire(a, i) + (__vt_lire(b, i) - __vt_lire(a, i)) * t); }
    retour r;
}
// reflechir, projeter, angle_entre : FMath::GetReflectionVector, ProjectOnTo ; mathutils reflect, project, angle
fonction reflechir(v, nn): flottant[] {
    soit k: flottant_petuar = 2.0Q * produit_scalaire(v, nn);
    soit n = longueur(v);
    soit r = tableau(n);
    pour i dans 0..n { __vt_ecrire(r, i, __vt_lire(v, i) - k * __vt_lire(nn, i)); }
    retour r;
}
fonction projeter(v, sur): flottant[] {
    soit d2: flottant_petuar = produit_scalaire(sur, sur);
    si d2 == 0.0Q { retour vecteur_echelle(sur, 0.0Q); }
    retour vecteur_echelle(sur, produit_scalaire(v, sur) / d2);
}
fonction angle_entre(a, b): flottant_petuar {
    soit d: flottant_petuar = norme(a) * norme(b);
    si d == 0.0Q { retour __vn_inconnu(); }
    retour arccosinus_128(__borne_x(produit_scalaire(a, b) / d, 0.0Q - 1.0Q, 1.0Q));
}
// tourner_vecteur : FVector::RotateAngleAxis (Rodrigues ; l'angle en radians)
fonction tourner_vecteur(v, axe, angle: flottant_petuar): flottant[] {
    soit k = normaliser(axe);
    soit c: flottant_petuar = cosinus_128(angle);
    soit s: flottant_petuar = sinus_128(angle);
    soit kv = produit_vectoriel(k, v);
    soit kd: flottant_petuar = produit_scalaire(k, v);
    soit r = tableau(3);
    pour i dans 0..3 { __vt_ecrire(r, i, __vt_lire(v, i) * c + __vt_lire(kv, i) * s + __vt_lire(k, i) * kd * (1.0Q - c)); }
    retour r;
}
// quaternion, quaternion_axe_angle : mathutils.Quaternion((w, x, y, z)), FQuat(Axis, Angle)
fonction quaternion(w: flottant_petuar, x: flottant_petuar, y: flottant_petuar, z: flottant_petuar): flottant[] {
    soit q = tableau(4);
    __vt_ecrire(q, 0, w);
    __vt_ecrire(q, 1, x);
    __vt_ecrire(q, 2, y);
    __vt_ecrire(q, 3, z);
    retour q;
}
fonction quaternion_axe_angle(axe, angle: flottant_petuar): flottant[] {
    soit k = normaliser(axe);
    soit s: flottant_petuar = sinus_128(angle / 2.0Q);
    soit q = tableau(4);
    __vt_ecrire(q, 0, cosinus_128(angle / 2.0Q));
    pour i dans 0..3 { __vt_ecrire(q, i + 1, __vt_lire(k, i) * s); }
    retour q;
}
// quaternion_produit, quaternion_conjugue, quaternion_normer : q1 @ q2, conjugated, normalized
fonction quaternion_produit(a, b): flottant[] {
    soit aw: flottant_petuar = __vt_lire(a, 0);
    soit ax: flottant_petuar = __vt_lire(a, 1);
    soit ay: flottant_petuar = __vt_lire(a, 2);
    soit az: flottant_petuar = __vt_lire(a, 3);
    soit bw: flottant_petuar = __vt_lire(b, 0);
    soit bx: flottant_petuar = __vt_lire(b, 1);
    soit by: flottant_petuar = __vt_lire(b, 2);
    soit bz: flottant_petuar = __vt_lire(b, 3);
    soit q = tableau(4);
    __vt_ecrire(q, 0, aw * bw - ax * bx - ay * by - az * bz);
    __vt_ecrire(q, 1, aw * bx + ax * bw + ay * bz - az * by);
    __vt_ecrire(q, 2, aw * by - ax * bz + ay * bw + az * bx);
    __vt_ecrire(q, 3, aw * bz + ax * by - ay * bx + az * bw);
    retour q;
}
fonction quaternion_conjugue(a): flottant[] {
    soit q = tableau(4);
    __vt_ecrire(q, 0, __vt_lire(a, 0));
    pour i dans 1..4 { __vt_ecrire(q, i, 0.0Q - __vt_lire(a, i)); }
    retour q;
}
fonction quaternion_normer(a): flottant[] { retour normaliser(a); }
// quaternion_tourner : FQuat::RotateVector, q @ v
fonction quaternion_tourner(q, v): flottant[] {
    soit p = tableau(4);
    __vt_ecrire(p, 0, 0.0Q);
    pour i dans 0..3 { __vt_ecrire(p, i + 1, __vt_lire(v, i)); }
    soit m = quaternion_produit(quaternion_produit(q, p), quaternion_conjugue(q));
    soit r = tableau(3);
    pour j dans 0..3 { __vt_ecrire(r, j, __vt_lire(m, j + 1)); }
    retour r;
}
// quaternion_interpoler : FQuat::Slerp, mathutils slerp (par le plus court chemin)
fonction quaternion_interpoler(a, b, t: flottant_petuar): flottant[] {
    soit d: flottant_petuar = produit_scalaire(a, b);
    soit sg: flottant_petuar = 1.0Q;
    si d < 0.0Q { sg = 0.0Q - 1.0Q; d = 0.0Q - d; }
    soit s0: flottant_petuar = 1.0Q - t;
    soit s1: flottant_petuar = t;
    si d < 0.9995Q {
        soit th0: flottant_petuar = arccosinus_128(d);
        soit sn: flottant_petuar = sinus_128(th0);
        s0 = sinus_128((1.0Q - t) * th0) / sn;
        s1 = sinus_128(t * th0) / sn;
    }
    soit q = tableau(4);
    pour i dans 0..4 { __vt_ecrire(q, i, __vt_lire(a, i) * s0 + __vt_lire(b, i) * sg * s1); }
    si d < 0.9995Q { retour q; }
    retour normaliser(q);
}
// matrice_identite, matrice_produit, matrice_point, matrice_transposee : FMatrix, mathutils.Matrix (4 × 4)
fonction matrice_identite(): flottant[] {
    soit m = tableau(16);
    pour i dans 0..16 { __vt_ecrire(m, i, 0.0Q); }
    pour j dans 0..4 { __vt_ecrire(m, 5 * j, 1.0Q); }
    retour m;
}
fonction matrice_produit(a, b): flottant[] {
    soit m = tableau(16);
    pour i dans 0..4 {
        pour j dans 0..4 {
            soit s: flottant_petuar = 0.0Q;
            pour k dans 0..4 { s = s + __vt_lire(a, 4 * i + k) * __vt_lire(b, 4 * k + j); }
            __vt_ecrire(m, 4 * i + j, s);
        }
    }
    retour m;
}
fonction matrice_point(m, v): flottant[] {
    // un point (x, y, z, 1) transformé, puis divisé par w
    soit r = tableau(3);
    soit w: flottant_petuar = __vt_lire(m, 12) * __vt_lire(v, 0) + __vt_lire(m, 13) * __vt_lire(v, 1) + __vt_lire(m, 14) * __vt_lire(v, 2) + __vt_lire(m, 15);
    pour i dans 0..3 {
        soit s: flottant_petuar = __vt_lire(m, 4 * i) * __vt_lire(v, 0) + __vt_lire(m, 4 * i + 1) * __vt_lire(v, 1) + __vt_lire(m, 4 * i + 2) * __vt_lire(v, 2) + __vt_lire(m, 4 * i + 3);
        si w != 1.0Q && w != 0.0Q { s = s / w; }
        __vt_ecrire(r, i, s);
    }
    retour r;
}
fonction matrice_transposee(a): flottant[] {
    soit m = tableau(16);
    pour i dans 0..4 { pour j dans 0..4 { __vt_ecrire(m, 4 * i + j, __vt_lire(a, 4 * j + i)); } }
    retour m;
}
// matrice_translation, matrice_echelle, matrice_rotation : Matrix.Translation, Matrix.Scale, Matrix.Rotation(angle, 4, axe)
fonction matrice_translation(x: flottant_petuar, y: flottant_petuar, z: flottant_petuar): flottant[] {
    soit m = matrice_identite();
    __vt_ecrire(m, 3, x);
    __vt_ecrire(m, 7, y);
    __vt_ecrire(m, 11, z);
    retour m;
}
fonction matrice_echelle(x: flottant_petuar, y: flottant_petuar, z: flottant_petuar): flottant[] {
    soit m = matrice_identite();
    __vt_ecrire(m, 0, x);
    __vt_ecrire(m, 5, y);
    __vt_ecrire(m, 10, z);
    retour m;
}
fonction matrice_rotation(axe, angle: flottant_petuar): flottant[] {
    soit k = normaliser(axe);
    soit x: flottant_petuar = __vt_lire(k, 0);
    soit y: flottant_petuar = __vt_lire(k, 1);
    soit z: flottant_petuar = __vt_lire(k, 2);
    soit c: flottant_petuar = cosinus_128(angle);
    soit s: flottant_petuar = sinus_128(angle);
    soit u: flottant_petuar = 1.0Q - c;
    soit m = matrice_identite();
    __vt_ecrire(m, 0, c + x * x * u);
    __vt_ecrire(m, 1, x * y * u - z * s);
    __vt_ecrire(m, 2, x * z * u + y * s);
    __vt_ecrire(m, 4, y * x * u + z * s);
    __vt_ecrire(m, 5, c + y * y * u);
    __vt_ecrire(m, 6, y * z * u - x * s);
    __vt_ecrire(m, 8, z * x * u - y * s);
    __vt_ecrire(m, 9, z * y * u + x * s);
    __vt_ecrire(m, 10, c + z * z * u);
    retour m;
}

// -- famille « couleurs » (Blender, UE FLinearColor, FastLED CHSV)
// couleur_tsv : Blender « HSV to RGB », FastLED CHSV : teinte (degrés), saturation, valeur (de 0 à 1) vers (r, v, b) de 0 à 1
fonction couleur_tsv(h: flottant_petuar, s: flottant_petuar, v: flottant_petuar): flottant[] {
    soit r = tableau(3);
    soit hh: flottant_petuar = enrouler(h, 0.0Q, 360.0Q) / 60.0Q;
    soit i = entier(plancher_128(hh));
    soit f: flottant_petuar = hh - flottant_petuar(i);
    soit p: flottant_petuar = v * (1.0Q - s);
    soit q: flottant_petuar = v * (1.0Q - s * f);
    soit t: flottant_petuar = v * (1.0Q - s * (1.0Q - f));
    soit a: flottant_petuar = v;
    soit b: flottant_petuar = t;
    soit c: flottant_petuar = p;
    si i == 1 { a = q; b = v; c = p; }
    si i == 2 { a = p; b = v; c = t; }
    si i == 3 { a = p; b = q; c = v; }
    si i == 4 { a = t; b = p; c = v; }
    si i >= 5 { a = v; b = p; c = q; }
    __vt_ecrire(r, 0, a);
    __vt_ecrire(r, 1, b);
    __vt_ecrire(r, 2, c);
    retour r;
}
// tsv_vers_rgb : la même, en couleur de la machine (comme rgb(r, g, b), chaque voie de 0 à 255)
fonction tsv_vers_rgb(h: flottant_petuar, s: flottant_petuar, v: flottant_petuar) {
    soit c = couleur_tsv(h, s, v);
    retour rgb(entier(__vt_lire(c, 0) * 255.0Q + 0.5Q), entier(__vt_lire(c, 1) * 255.0Q + 0.5Q), entier(__vt_lire(c, 2) * 255.0Q + 0.5Q));
}
// srgb_vers_lineaire, lineaire_vers_srgb : FLinearColor::FromSRGBColor, Blender (la courbe sRGB de l'IEC 61966-2-1)
fonction srgb_vers_lineaire(c: flottant_petuar): flottant_petuar {
    si c <= 0.04045Q { retour c / 12.92Q; }
    retour puissance_128((c + 0.055Q) / 1.055Q, 2.4Q);
}
fonction lineaire_vers_srgb(c: flottant_petuar): flottant_petuar {
    si c <= 0.0031308Q { retour c * 12.92Q; }
    retour 1.055Q * puissance_128(c, 1.0Q / 2.4Q) - 0.055Q;
}
// luminance : Rec. 709 (Blender, UE GetLuminance)
fonction luminance(r: flottant_petuar, g: flottant_petuar, b: flottant_petuar): flottant_petuar { retour 0.2126Q * r + 0.7152Q * g + 0.0722Q * b; }

// -- famille « cube » : les places du cube chromatique (#RRGGBB)
// adresse_point, coord_x, coord_y, coord_z : la place d'un point et ses trois coordonnées (RR, GG, BB)
fonction adresse_point(x, y, z) { retour ((x & 255) << 16) | ((y & 255) << 8) | (z & 255); }
fonction coord_x(a) { retour (a >> 16) & 255; }
fonction coord_y(a) { retour (a >> 8) & 255; }
fonction coord_z(a) { retour a & 255; }
// voisin : le point d'à côté sur un axe (0 : x, 1 : y, 2 : z), dans un sens (1 ou (0 - 1)), le cube refermé
fonction voisin(a, axe, sens) {
    soit d = 1;
    si sens .< 0 || sens == (0 - 1) { d = 255; }
    si axe == 0 { retour adresse_point(coord_x(a) + d, coord_y(a), coord_z(a)); }
    si axe == 1 { retour adresse_point(coord_x(a), coord_y(a) + d, coord_z(a)); }
    retour adresse_point(coord_x(a), coord_y(a), coord_z(a) + d);
}
// morton, demorton_x, demorton_y, demorton_z : les bits des trois coordonnées entrelacés (deux points proches, deux
// places proches)
fonction morton(x, y, z) {
    soit r = 0;
    pour i dans 0..8 {
        r = r | (((x >> i) & 1) << (3 * i + 2)) | (((y >> i) & 1) << (3 * i + 1)) | (((z >> i) & 1) << (3 * i));
    }
    retour r;
}
fonction __demorton(m, k) {
    soit r = 0;
    pour i dans 0..8 { r = r | (((m >> (3 * i + k)) & 1) << i); }
    retour r;
}
fonction demorton_x(m) { retour __demorton(m, 2); }
fonction demorton_y(m) { retour __demorton(m, 1); }
fonction demorton_z(m) { retour __demorton(m, 0); }
// distance_cube : la distance de Manhattan entre deux places (les pas d'un point à son voisin)
fonction distance_cube(a, b) {
    retour ecart(coord_x(a), coord_x(b)) + ecart(coord_y(a), coord_y(b)) + ecart(coord_z(a), coord_z(b));
}

// -- famille « codes » : l'ADN d'un entier (A C G T : 0 1 2 3, la première au poids fort) ; 0.833 : 64 bases sur Lugus,
// 32 sur Dunon ou en « dunon; » (nb_bits(0 - 1) / 2)
// complement_adn, inverser_bases, anti_sens : A↔T, C↔G (3 − q) ; les bases lues à l'envers ; le brin d'en face
fonction complement_adn(x) { retour ~x; }
fonction inverser_bases(x) {
    soit r = 0;
    soit v = x;
    pour i dans 0..nb_bits(0 - 1) / 2 { r = (r << 2) | (v & 3); v = v >> 2; }
    retour r;
}
fonction anti_sens(x) { retour inverser_bases(~x); }
// compter_base, teneur_gc, ecart_bases : combien de fois une base, les G et les C, les bases qui diffèrent
fonction compter_base(x, b) { retour nb_bits(qegal(x, (b & 3) * ((0 - 1) / 3))); }
fonction teneur_gc(x) { retour compter_base(x, 1) + compter_base(x, 2); }
fonction ecart_bases(a, b) { retour nb_bits(0 - 1) / 2 - nb_bits(qegal(a, b)); }
"""

# ------------------------------------------------------------------------------------------------ Lugus seul : les fonctions en valeur
VALEURS_LUGUS = r"""
// -- famille « tableaux, avec une fonction » (Rust Iterator ; Lugus, et Dunon depuis la 0.65)
// transformer, filtrer, plier, tous, au_moins_un, aucun, trouver_si, rang_si, compter_si, pour_chacun, garder_si, trier_par :
// Rust map, filter, fold, all, any, !any, find, position, filter().count(), for_each, retain, sort_by_key (la fonction
// rend 1 ou 0 pour une question ; ces mots rendent 1 ou 0, ou (0 - 1) pour « absent »)
fonction transformer(t, __fv) { soit r = tableau(0); pour x dans t { ajouter(r, __fv(x)); } retour r; }
fonction filtrer(t, __fv) { soit r = tableau(0); pour x dans t { si __fv(x) != 0 { ajouter(r, x); } } retour r; }
fonction plier(t, __fv, depart) { soit acc = depart; pour x dans t { acc = __fv(acc, x); } retour acc; }
fonction tous(t, __fv) { pour x dans t { si __fv(x) == 0 { retour 0; } } retour 1; }
fonction au_moins_un(t, __fv) { pour x dans t { si __fv(x) != 0 { retour 1; } } retour 0; }
fonction aucun(t, __fv) { pour x dans t { si __fv(x) != 0 { retour 0; } } retour 1; }
fonction trouver_si(t, __fv) { pour x dans t { si __fv(x) != 0 { retour x; } } retour 0; }
fonction rang_si(t, __fv) {
    soit n = longueur(t);
    pour i dans 0..n { si __fv(t[i]) != 0 { retour i; } }
    retour (0 - 1);
}
fonction compter_si(t, __fv) { soit k = 0; pour x dans t { si __fv(x) != 0 { k = k + 1; } } retour k; }
fonction pour_chacun(t, __fv) { pour x dans t { __fv(x); } }
fonction garder_si(t, __fv) {
    soit w = 0;
    soit n = longueur(t);
    pour i dans 0..n { si __fv(t[i]) != 0 { t[w] = t[i]; w = w + 1; } }
    tantque longueur(t) > w { retirer(t); }
}
fonction trier_par(t, __fv) {
    soit n = longueur(t);
    pour i dans 1..n {
        soit x = t[i];
        soit kx = __fv(x);
        soit j = i;
        tantque j > 0 && __fv(t[j - 1]) .> kx { t[j] = t[j - 1]; j = j - 1; }
        t[j] = x;
    }
}
"""

# ------------------------------------------------------------------------------------------------ les variantes écrites par ce programme
ENTETE = re.compile(r"^fonction (\w+)\(([^)]*)\)(?::\s*([\w\[\]]+))?\s*\{", re.M)


def variantes(texte, secondaires):
    """Pour chaque mot dont un paramètre est le flottant principal : ses variantes pour les autres flottants
    (convertir, appeler, reconvertir). Un mot __mot_x donne __mot_f, __mot_s ; un mot public donne __mot_f, __mot_s."""
    sortie = []
    for m in ENTETE.finditer(texte):
        nom, params, ret = m.group(1), m.group(2), m.group(3)
        if nom.startswith("__") and not nom.endswith("_x"):
            continue
        if nom.startswith("__vn_") or nom.startswith("__vt_"):
            continue
        ps = [p.strip() for p in params.split(",") if p.strip()]
        if not any(p.endswith(": flottant_petuar") for p in ps):
            continue
        racine_nom = nom[2:-2] if nom.startswith("__") else nom
        for suf, typ, retour_conv in secondaires:
            nps, args = [], []
            for p in ps:
                n = p.split(":")[0].strip()
                if p.endswith(": flottant_petuar"):
                    nps.append(f"{n}: {typ}")
                    args.append(f"flottant_petuar({n})")
                else:
                    nps.append(p)
                    args.append(n)
            appel = f"{nom}({', '.join(args)})"
            if ret == "flottant_petuar":
                tete, corps = f": {typ}", f"{retour_conv}({appel})"
            elif ret:
                tete, corps = f": {ret}", appel
            else:
                tete, corps = "", appel
            sortie.append(f"fonction __{racine_nom}_{suf}({', '.join(nps)}){tete} {{ retour {corps}; }}")
    return "\n".join(sortie) + "\n"


MATHS = ("sinus", "cosinus", "tangente", "exponentielle", "logarithme", "puissance", "arctangente2", "arctangente",
         "arcsinus", "arccosinus", "plancher", "plafond", "pi", "exp2")


def pour_dunon(t):
    t = re.sub(r"\b(" + "|".join(MATHS) + r")_128\(", r"\1_64(", t)
    t = re.sub(r"\b(__\w+?)_x\b", r"\1_f", t)
    t = t.replace("flottant_petuar", "flottant")
    t = re.sub(r"(\d)Q\b", r"\1", t)
    return t


def bloc_lugus():
    corps = COMMUN + VALEURS_LUGUS
    return (DEBUT + AIDE_LUGUS + corps
            + "// les variantes pour le flottant de 64 et de 32 bits\n"
            + variantes(corps, (("f", "flottant", "flottant_64"), ("s", "flottant_32", "flottant_32")))
            + FIN)


def bloc_dunon():
    # 0.65 : Dunon a les fonctions passées en valeur : les mots qui prennent une fonction aussi
    corps = NOMBRES_DUNON + COMMUN + VALEURS_LUGUS
    var = variantes(corps, (("s", "flottant_32", "flottant_32"),))
    return DEBUT + AIDE_DUNON + pour_dunon(corps) + "// les variantes pour le flottant de 32 bits\n" + pour_dunon(var) + FIN


def poser(fichier, bloc):
    chemin = os.path.join(racine, fichier)
    src = open(chemin, encoding="utf-8").read()
    if DEBUT in src:
        a = src.index(DEBUT)
        b = src.index(FIN, a) + len(FIN)
        src = src[:a] + src[b:]
    repere = "// la dernière fonction du prélude"
    if repere not in src:
        # Dunon : le prélude se ferme comme celui de Lugus, par une fonction vide jamais appelée (vtxc lit chaque
        # fonction jusqu'à la suivante)
        k = src.index("PRELUDE = \"\"\"")
        f = src.index('\n"""', k) + 1
        src = (src[:f] + repere + " : vtxc lit chaque fonction jusqu'à la suivante ; celle-ci n'est jamais appelée\n"
               "fonction __fin_du_prelude() {\n}\n" + src[f:])
    i = src.index(repere)
    nouveau = src[:i] + bloc + src[i:]
    if nouveau != open(chemin, encoding="utf-8").read():
        open(chemin, "w", encoding="utf-8").write(nouveau)
        print(fichier, ": vocabulaire posé")
    else:
        print(fichier, ": déjà à jour")


if __name__ == "__main__":
    poser("vtx128.py", bloc_lugus())
    poser("vtx64.py", bloc_dunon())


def documenter():
    """docs/vtx-vocabulaire.md : chaque famille, ses mots, d'où ils viennent, sur quelles machines (tiré du texte même)."""
    out = ["# Le vocabulaire étendu de Vercintorix (0.61)", "",
           "*Écrit par `vtxc/vocabulaire.py` à partir du texte même des mots : il ne peut pas dire autre chose que le code.*",
           "",
           "Les mots viennent de ce que savent Rust (les méthodes des entiers, des flottants, des textes, des tranches et des",
           "itérateurs), ses extensions officielles (num, itertools, rand), Arduino (map, constrain, bitRead, lowByte, sq,",
           "random, millis, delay, String) et des moteurs que vtx doit pouvoir accueillir (Unreal Engine 5 : FMath, FVector,",
           "FQuat, FMatrix ; Blender : mathutils et ses nœuds de mathématiques). Ce ne sont pas ces bibliothèques recréées :",
           "c'est le vocabulaire français qu'il faut pour y brancher ce qu'elles font. Les mots déjà là avant (abs, min, max,",
           "borne, pgcd, majuscules, decouper, trier…) sont dans la référence du langage.", "",
           "**Un mot pour tous les types.** Un mot qui a des variantes les prend seul, d'après ses arguments : le flottant le",
           "plus large, sinon l'entier le plus large (Lugus : flottants de 128, 64, 32 bits, entiers de 128, 64, 32 bits ;",
           "Dunon : flottants de 64 et 32 bits, entiers de 128, 64, 32 bits). Une fonction du programme qui porte le même nom",
           "garde la main. **Le doute ne se comble pas** : sur une valeur inconnue (jamais écrite) ou variable (contradictoire),",
           "une question rend cet état ; une moyenne de rien est inconnue ; un texte qui n'est pas un nombre est variable.",
           "**Les questions sur un texte ou un tableau** rendent 1 ou 0, comme `commence_par` ; « absent » s'écrit",
           "(0 - 1) (−1 lu signé), comme `position`.", ""]
    blocs = ((COMMUN, "Lugus, Dunon"), (VALEURS_LUGUS, "Lugus, Dunon"))
    total = 0
    for texte, machines in blocs:
        lignes = texte.split("\n")
        k = 0
        while k < len(lignes):
            l = lignes[k]
            if l.startswith("// -- famille"):
                famille = l[len("// -- famille "):].strip()
                out += ["", f"## {famille[0].upper() + famille[1:]}", "", f"*Machines : {machines}.*", "",
                        "| Mots | Ce qu'ils font, d'où ils viennent |", "|---|---|"]
                k += 1
                continue
            if l.startswith("// ") and not l.startswith("// -- "):
                j = k
                bloc = []
                while j < len(lignes) and lignes[j].startswith("// "):
                    bloc.append(lignes[j][3:].strip())
                    j += 1
                if j < len(lignes) and lignes[j].startswith("fonction ") and " : " in " ".join(bloc):
                    gauche, droite = " ".join(bloc).split(" : ", 1)
                    noms = [n.strip() for n in gauche.split(",") if n.strip()]
                    total += len(noms)
                    out.append(f"| {', '.join('`' + n + '`' for n in noms)} | {droite.strip()} |")
                    k = j
                    continue
            k += 1
    publics = set(re.findall(r"^fonction ([a-z]\w*)\(", COMMUN + VALEURS_LUGUS, re.M))
    vus = set(re.findall(r"`(\w+)`", "\n".join(out)))
    manquent = sorted(publics - vus)
    if manquent:
        print("sans ligne dans la documentation :", " ".join(manquent))
    out += ["", f"*{len(publics)} mots publics ; et, pour Dunon, le vocabulaire des nombres de 0.6za (signe, est_positif,",
            "est_negatif, est_nul, est_entier, est_infini, est_su, partie_entiere, partie_decimale, entre, ecart, borne,",
            "arrondi à n décimales), qu'il n'avait pas.*", "",
            "## Ce qui n'y est pas, et pourquoi", "",
            "- **les broches d'Arduino** (`pinMode`, `digitalWrite`, `analogRead`) : Lugus et Dunon n'ont pas de broches ;",
            "  les simuler dans un tableau n'apprendrait rien. Elles viendront avec un service de la machine (un vrai port).",
            "- **les bibliothèques entières** (Servo, Wire, les crates, les modules d'UE5 ou de Blender) : le vocabulaire",
            "  prépare le branchement (vecteurs, quaternions, matrices, couleurs, interpolations) ; une extension se branche",
            "  par ses mots, elle n'est pas recopiée.",
            "- **`multiplier_ajouter` fusionné** (un seul arrondi) : fait en 0.65, exact sur les trois flottants, en entiers",
            "  (les mantisses en grands entiers, un seul arrondi au plus proche, pair au milieu). (`reste` l'est depuis 0.61b.)",
            "- **les itérateurs paresseux** de Rust (`map` sans tableau au bout) : vtx rend des tableaux.",
            "- **les mots qui prennent une fonction** (`transformer`, `filtrer`…) : sur Lugus seulement (Dunon n'a pas",
            "  encore les fonctions passées en valeur).",
            "- **les tableaux de flottants ou de textes** pour `premier`, `dernier`, `moyenne`… : ces mots lisent des",
            "  entiers (`t[0]` lit toujours bien un flottant ou un texte)."]
    chemin = os.path.join(racine, "docs", "vtx-vocabulaire.md")
    open(chemin, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("docs/vtx-vocabulaire.md :", len(publics), "mots publics,", total, "dans les tableaux")


if __name__ == "__main__" and "--doc" in sys.argv:
    documenter()
