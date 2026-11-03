/* neutrons quaternaires (CRC sur GF(4)) : un million de mots de 128 bits (xorshift64), la somme de leurs neutrons ; la table de deux octets */
#include <stdio.h>
#include <stdint.h>
#define N 1000000
static uint16_t T[256], T2[65536];
static int m4(int a, int b) { if (!a || !b) return 0; int l = (a - 1) + (b - 1); if (l >= 3) l -= 3; return l + 1; }
int main(void) {
    for (int k = 0; k < 256; k++) { int r = 0; for (int q = 3; q >= 0; q--) { int t = ((k >> (2 * q)) & 3) ^ (r >> 6);
        r = (((r >> 4) & 3) << 6) | ((((r >> 2) & 3) ^ m4(t, 1)) << 4) | (((r & 3) ^ m4(t, 2)) << 2) | m4(t, 1); } T[k] = r; }
    for (int x = 0; x < 256; x++) for (int y = 0; y < 256; y++) T2[(x << 8) | y] = (uint16_t)(T[T[x] ^ y] << 8);
    uint64_t x = 88172645463325252ULL, s = 0;
    for (long i = 0; i < N; i++) {
        x ^= x << 13; x ^= x >> 7; x ^= x << 17; uint64_t h = x;
        x ^= x << 13; x ^= x >> 7; x ^= x << 17; uint64_t b = x;
        uint64_t c = T2[h >> 48];
        c = T2[c ^ ((h >> 32) & 65535)]; c = T2[c ^ ((h >> 16) & 65535)]; c = T2[c ^ (h & 65535)];
        c = T2[c ^ (b >> 48)]; c = T2[c ^ ((b >> 32) & 65535)]; c = T2[c ^ ((b >> 16) & 65535)];
        c = T2[c ^ (b & 65535)];
        s += c >> 8;
    }
    printf("%llu\n", (unsigned long long)s);
    return 0;
}
