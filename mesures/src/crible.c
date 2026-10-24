#include <stdio.h>
#include <stdlib.h>
#define N 5000000
int main(void) {
    unsigned *p = malloc(N * sizeof(unsigned));
    for (unsigned q = 2; q < N; q++) p[q] = 1;
    for (unsigned i = 2; i * i < N; i++)
        if (p[i] == 1) for (unsigned j = i * i; j < N; j += i) p[j] = 0;
    unsigned n = 0;
    for (unsigned k = 2; k < N; k++) n += p[k];
    printf("%u\n", n);
    return 0;
}
