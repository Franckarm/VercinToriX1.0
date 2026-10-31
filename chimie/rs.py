"""Reed-Solomon sur GF(256) (le polynôme 0x11D) : le codage systématique et le décodage des erreurs et des effacements
(2 erreurs + effacements <= r). L'ombre des colonnes de l'ADN (chimie/adn.py) : chaque colonne de mots est lue en seize
voies d'octets, chacune un mot de code. Écrit d'après la méthode classique (syndromes, Berlekamp-Massey, Chien, Forney) ;
vérifié par chimie/adn.py essai et tests/test_adn.py."""
# Reed-Solomon sur GF(256) (polynôme 0x11D) : codage systématique, décodage erreurs et effacements (2e + f <= r)
EXP = [0] * 512
LOG = [0] * 256
x = 1
for i in range(255):
    EXP[i] = x
    LOG[x] = i
    x <<= 1
    if x & 0x100:
        x ^= 0x11D
for i in range(255, 512):
    EXP[i] = EXP[i - 255]


def mul(a, b):
    return 0 if a == 0 or b == 0 else EXP[LOG[a] + LOG[b]]


def div(a, b):
    if b == 0:
        raise ZeroDivisionError
    return 0 if a == 0 else EXP[(LOG[a] - LOG[b]) % 255]


def pw(a, n):
    return 0 if a == 0 else EXP[(LOG[a] * n) % 255]


def inv(a):
    return EXP[255 - LOG[a]]


def p_mul(p, q):
    r = [0] * (len(p) + len(q) - 1)
    for j, b in enumerate(q):
        for i, a in enumerate(p):
            r[i + j] ^= mul(a, b)
    return r


def p_add(p, q):
    r = [0] * max(len(p), len(q))
    r[len(r) - len(p):] = p
    for i in range(len(q)):
        r[i + len(r) - len(q)] ^= q[i]
    return r


def p_scale(p, x):
    return [mul(a, x) for a in p]


def p_eval(p, x):
    y = p[0]
    for c in p[1:]:
        y = mul(y, x) ^ c
    return y


def generateur(r):
    g = [1]
    for i in range(r):
        g = p_mul(g, [1, EXP[i]])
    return g


GEN = {}


def coder(msg, r):
    """msg (liste d'octets, le plus fort d'abord) -> les r octets de contrôle"""
    g = GEN.setdefault(r, generateur(r))
    out = list(msg) + [0] * r
    for i in range(len(msg)):
        c = out[i]
        if c:
            for j in range(1, len(g)):
                out[i + j] ^= mul(g[j], c)
    return out[len(msg):]


def syndromes(cw, r):
    return [0] + [p_eval(cw, EXP[i]) for i in range(r)]


def localisateur_effacements(pos_coef):
    e = [1]
    for p in pos_coef:
        e = p_mul(e, p_add([1], [EXP[p], 0]))
    return e


def evaluateur(synd, loc, r):
    _, rem = divmod_poly(p_mul(synd, loc), [1] + [0] * (r + 1))
    return rem


def divmod_poly(dividende, diviseur):
    out = list(dividende)
    for i in range(len(dividende) - (len(diviseur) - 1)):
        c = out[i]
        if c:
            for j in range(1, len(diviseur)):
                if diviseur[j]:
                    out[i + j] ^= mul(diviseur[j], c)
    sep = -(len(diviseur) - 1)
    return out[:sep], out[sep:]


def corriger_valeurs(cw, synd, pos_err):
    n = len(cw)
    coef_pos = [n - 1 - p for p in pos_err]
    loc = localisateur_effacements(coef_pos)
    omega = evaluateur(synd[::-1], loc, len(loc) - 1)[::-1]
    X = [EXP[p] for p in coef_pos]
    E = [0] * n
    for i, Xi in enumerate(X):
        Xi_inv = inv(Xi)
        prime = 1
        for j in range(len(X)):
            if j != i:
                prime = mul(prime, 1 ^ mul(Xi_inv, X[j]))
        if prime == 0:
            return None
        y = p_eval(omega[::-1], Xi_inv)
        y = mul(pw(Xi, 1), y)
        E[pos_err[i]] = div(y, prime)
    return [c ^ e for c, e in zip(cw, E)]


def trouver_localisateur(synd, r, effacements=None, nb_eff=0):
    if effacements:
        err_loc = list(effacements)
        old_loc = list(effacements)
    else:
        err_loc, old_loc = [1], [1]
    decal = len(synd) - r
    for i in range(r - nb_eff):
        k = (i + decal + nb_eff) if effacements else (i + decal)
        delta = synd[k]
        for j in range(1, len(err_loc)):
            delta ^= mul(err_loc[-(j + 1)], synd[k - j])
        old_loc = old_loc + [0]
        if delta != 0:
            if len(old_loc) > len(err_loc):
                new_loc = p_scale(old_loc, delta)
                old_loc = p_scale(err_loc, inv(delta))
                err_loc = new_loc
            err_loc = p_add(err_loc, p_scale(old_loc, delta))
    while len(err_loc) and err_loc[0] == 0:
        del err_loc[0]
    if (len(err_loc) - 1 - nb_eff) * 2 + nb_eff > r:
        return None
    return err_loc


def trouver_erreurs(err_loc, n):
    errs = len(err_loc) - 1
    pos = [n - 1 - i for i in range(n) if p_eval(err_loc, pw(2, i)) == 0]
    if len(pos) != errs:
        return None
    return pos


def forney_syndromes(synd, pos, n):
    fs = list(synd[1:])
    for p in [n - 1 - q for q in pos]:
        x = EXP[p]
        for j in range(len(fs) - 1):
            fs[j] = mul(fs[j], x) ^ fs[j + 1]
    return fs


def decoder(cw, r, effaces=()):
    """cw : le mot de code (données + contrôle). Rend le mot corrigé, ou None (au-delà de la capacité)."""
    cw = list(cw)
    n = len(cw)
    if len(effaces) > r:
        return None
    for p in effaces:
        cw[p] = 0
    synd = syndromes(cw, r)
    if max(synd) == 0:
        return cw
    fsynd = forney_syndromes(synd, effaces, n)
    err_loc = trouver_localisateur(fsynd, r, nb_eff=len(effaces))
    if err_loc is None:
        return None
    pos = trouver_erreurs(err_loc[::-1], n)
    if pos is None:
        return None
    toutes = list(effaces) + [p for p in pos if p not in effaces]
    out = corriger_valeurs(cw, synd, toutes)
    if out is None or max(syndromes(out, r)) != 0:
        return None
    return out
