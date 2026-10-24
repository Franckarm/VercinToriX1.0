import sys
sys.setrecursionlimit(100000)
N = 500000
a = [0] * N
x = 2463534242
for i in range(N):
    x = (x ^ (x << 13)) & 0xFFFFFFFF
    x ^= x >> 17
    x = (x ^ (x << 5)) & 0xFFFFFFFF
    a[i] = x & 16777215
def trier(g, d):
    while g < d:
        p = a[(g + d) // 2]
        i, j = g, d
        while i <= j:
            while a[i] < p: i += 1
            while a[j] > p: j -= 1
            if i <= j:
                a[i], a[j] = a[j], a[i]
                i += 1; j -= 1
        if j - g < d - i:
            if g < j: trier(g, j)
            g = i
        else:
            if i < d: trier(i, d)
            d = j
trier(0, N - 1)
s = 0
for v in a:
    s = (s * 31 + v) & 0xFFFFFFFF
print(s)
