#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
typedef __int128 i128;
static i128 fib(i128 n) { return n < 2 ? n : fib(n - 1) + fib(n - 2); }
int main(void) {
    i128 n = 2000000, compte = 0;
    i128 *crible = calloc((size_t)n, sizeof *crible);
    for (i128 i = 2; i < n; i++) if (crible[i] == 0) { compte++; for (i128 j = i * i; j < n; j += i) crible[j] = 1; }
    printf("premiers : %llu\n", (unsigned long long)compte);
    printf("fib(27) : %llu\n", (unsigned long long)fib(27));
    unsigned __int128 h = 7;
    for (i128 k = 0; k < 3000000; k++) h = (h * 31 + (unsigned __int128)k) ^ (unsigned __int128)((i128)h >> 3);
    printf("brassage : %lld %lld\n", (long long)(h >> 64), (long long)h);
    return 0;
}
