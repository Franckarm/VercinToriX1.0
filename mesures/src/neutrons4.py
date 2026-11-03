# neutrons quaternaires (CRC sur GF(4)) : un million de mots de 128 bits (xorshift64), la somme de leurs neutrons ; la table de deux octets
N = 1000000
def m4(a, b):
    if a == 0 or b == 0:
        return 0
    l = (a - 1) + (b - 1)
    return (l - 3 if l >= 3 else l) + 1
T = []
for k in range(256):
    r = 0
    for q in (3, 2, 1, 0):
        t = ((k >> (2 * q)) & 3) ^ (r >> 6)
        r = (((r >> 4) & 3) << 6) | ((((r >> 2) & 3) ^ m4(t, 1)) << 4) | (((r & 3) ^ m4(t, 2)) << 2) | m4(t, 1)
    T.append(r)
T2 = [0] * 65536
for x in range(256):
    for y in range(256):
        T2[(x << 8) | y] = T[T[x] ^ y] << 8
M = (1 << 64) - 1
x, s = 88172645463325252, 0
for _ in range(N):
    x ^= (x << 13) & M; x ^= x >> 7; x ^= (x << 17) & M; h = x
    x ^= (x << 13) & M; x ^= x >> 7; x ^= (x << 17) & M; b = x
    c = T2[h >> 48]; c = T2[c ^ ((h >> 32) & 65535)]; c = T2[c ^ ((h >> 16) & 65535)]
    c = T2[c ^ (h & 65535)]; c = T2[c ^ (b >> 48)]; c = T2[c ^ ((b >> 32) & 65535)]
    c = T2[c ^ ((b >> 16) & 65535)]; c = T2[c ^ (b & 65535)]
    s += c >> 8
print(s & M)
