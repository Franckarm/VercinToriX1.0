#include <stdio.h>
static unsigned fib(unsigned n) { return n < 2 ? n : fib(n - 1) + fib(n - 2); }
int main(void) { printf("%u\n", fib(32)); return 0; }
