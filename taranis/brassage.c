/* Le brassage de la sonde de Taranis, en C : un cœur, puis tous (OpenMP). Sortie : n, la somme, et les deux temps en
   millisecondes. Compilé par comparer.py (cl /O2 /openmp sous Windows, gcc -O2 -fopenmp ailleurs). */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#ifdef _OPENMP
#include <omp.h>
#endif

static uint32_t brasser(uint32_t i) {
    uint32_t x = i;
    for (int r = 0; r < 64; r++) {
        x ^= x << 13;
        x ^= x >> 17;
        x ^= x << 5;
        x = x * 2654435761u + i;
    }
    return x;
}

static double maintenant(void) {
#ifdef _OPENMP
    return omp_get_wtime();
#else
    return (double)clock() / CLOCKS_PER_SEC;
#endif
}

int main(int argc, char **argv) {
    long n = argc > 1 ? atol(argv[1]) : 16777216;
    uint32_t *t = malloc(n * sizeof(uint32_t));
    double a = maintenant();
    for (long i = 0; i < n; i++) t[i] = brasser((uint32_t)i);
    double b = maintenant();
    long i;
#pragma omp parallel for schedule(static)
    for (i = 0; i < n; i++) t[i] = brasser((uint32_t)i);
    double c = maintenant();
    unsigned long long s = 0;
    for (long k = 0; k < n; k++) s += t[k];
    printf("%ld %llu %.2f %.2f\n", n, s, (b - a) * 1e3, (c - b) * 1e3);
    free(t);
    return 0;
}
