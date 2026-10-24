/* la même chose écrite par un expert : 16 bases par mot de 32 bits, comparées par calcul de bits et __builtin_popcount */
#include <stdio.h>
#include <stdlib.h>
#define M 524288
int main(void) {
    unsigned *u = malloc(M * 4), *v = malloc(M * 4);
    unsigned x = 2463534242u;
    for (int i = 0; i < M; i++) {
        x ^= x << 13; x ^= x >> 17; x ^= x << 5; u[i] = x;
        x ^= x << 13; x ^= x >> 17; x ^= x << 5; v[i] = x;
    }
    unsigned n = 0;
    for (int r = 0; r < 4; r++)
        for (int i = 0; i < M; i++) {
            unsigned d = u[i] ^ v[i];
            unsigned e = ~(d | (d >> 1)) & 0x55555555u;
            n += __builtin_popcount(e);
        }
    printf("%u\n", n);
    return 0;
}
