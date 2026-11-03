# neutrons, CRC-8 (0x07) : un million de mots de 128 bits (xorshift64), la somme de leurs neutrons ; la table de deux octets
N = 1000000
T = []
for k in range(256):
    c = k
    for _ in range(8):
        c = ((c << 1) ^ 7) & 255 if c & 128 else (c << 1) & 255
    T.append(c)
T2 = [0] * 65536
for y in range(256):
    for x in range(256):
        T2[x | (y << 8)] = T[T[x] ^ y]
M = (1 << 64) - 1
x, s = 88172645463325252, 0
for _ in range(N):
    x ^= (x << 13) & M; x ^= x >> 7; x ^= (x << 17) & M; h = x
    x ^= (x << 13) & M; x ^= x >> 7; x ^= (x << 17) & M; b = x
    c = T2[b & 65535]; c = T2[c ^ ((b >> 16) & 65535)]; c = T2[c ^ ((b >> 32) & 65535)]; c = T2[c ^ (b >> 48)]
    c = T2[c ^ (h & 65535)]; c = T2[c ^ ((h >> 16) & 65535)]; c = T2[c ^ ((h >> 32) & 65535)]; c = T2[c ^ (h >> 48)]
    s += c
print(s & M)
