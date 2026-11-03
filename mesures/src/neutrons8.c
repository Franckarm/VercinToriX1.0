/* neutrons, CRC-8 (0x07) : un million de mots de 128 bits (xorshift64), la somme de leurs neutrons ; la table de deux octets */
#include <stdio.h>
#include <stdint.h>
#define N 1000000
static uint16_t T[256], T2[65536];
int main(void) {
    for (int k = 0; k < 256; k++) { int c = k; for (int j = 0; j < 8; j++) c = (c & 128) ? ((c << 1) ^ 7) & 255 : (c << 1) & 255; T[k] = c; }
    for (int y = 0; y < 256; y++) for (int x = 0; x < 256; x++) T2[x | (y << 8)] = T[T[x] ^ y];
    uint64_t x = 88172645463325252ULL, s = 0;
    for (long i = 0; i < N; i++) {
        x ^= x << 13; x ^= x >> 7; x ^= x << 17; uint64_t h = x;
        x ^= x << 13; x ^= x >> 7; x ^= x << 17; uint64_t b = x;
        uint64_t c = T2[b & 65535];
        c = T2[c ^ ((b >> 16) & 65535)]; c = T2[c ^ ((b >> 32) & 65535)]; c = T2[c ^ (b >> 48)];
        c = T2[c ^ (h & 65535)]; c = T2[c ^ ((h >> 16) & 65535)]; c = T2[c ^ ((h >> 32) & 65535)]; c = T2[c ^ (h >> 48)];
        s += c;
    }
    printf("%llu\n", (unsigned long long)s);
    return 0;
}
