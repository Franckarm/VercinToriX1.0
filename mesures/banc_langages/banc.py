import sys
sys.setrecursionlimit(10000)
BITS = int(sys.argv[1]) if len(sys.argv) > 1 else 64
M = (1 << BITS) - 1
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)
n = 2000000
crible = [0] * n
compte = 0
for i in range(2, n):
    if crible[i] == 0:
        compte += 1
        j = i * i
        while j < n:
            crible[j] = 1
            j += i
print("premiers :", compte)
print("fib(27) :", fib(27))
h = 7
for k in range(3000000):
    if BITS == 64:
        h = ((h * 31 + k) & M) ^ (h >> 3)
    else:
        s = h - (1 << 128) if h >> 127 else h
        h = ((h * 31 + k) ^ (s >> 3)) & M
def signe(x):
    x &= (1 << 64) - 1
    return x - (1 << 64) if x >> 63 else x
print("brassage :", signe(h) if BITS == 64 else f"{signe(h >> 64)} {signe(h)}")
