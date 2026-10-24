/* deux brins de 8 388 608 bases, une base par octet (l'écriture naturelle en C) */
#include <stdio.h>
#include <stdlib.h>
#define M 524288
int main(void) {
    unsigned char *u = malloc(M * 16), *v = malloc(M * 16);
    unsigned x = 2463534242u;
    for (int i = 0; i < M; i++) {
        x ^= x << 13; x ^= x >> 17; x ^= x << 5;
        for (int q = 0; q < 16; q++) u[i * 16 + q] = (x >> (2 * q)) & 3;
        x ^= x << 13; x ^= x >> 17; x ^= x << 5;
        for (int q = 0; q < 16; q++) v[i * 16 + q] = (x >> (2 * q)) & 3;
    }
    unsigned n = 0;
    for (int r = 0; r < 4; r++)
        for (int i = 0; i < M * 16; i++) n += u[i] == v[i];
    printf("%u\n", n);
    return 0;
}
