#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
static uint64_t fib(uint64_t n) { return n < 2 ? n : fib(n - 1) + fib(n - 2); }
int main(void) {
    uint64_t n = 2000000, compte = 0;
    uint64_t *crible = calloc(n, sizeof *crible);
    for (uint64_t i = 2; i < n; i++) if (crible[i] == 0) { compte++; for (uint64_t j = i * i; j < n; j += i) crible[j] = 1; }
    printf("premiers : %llu\n", (unsigned long long)compte);
    printf("fib(27) : %llu\n", (unsigned long long)fib(27));
    uint64_t h = 7;
    for (uint64_t k = 0; k < 3000000; k++) h = (h * 31 + k) ^ (h >> 3);
    printf("brassage : %lld\n", (long long)h);
    return 0;
}
