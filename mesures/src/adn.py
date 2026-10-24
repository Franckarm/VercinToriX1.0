M = 524288
u = bytearray(M * 16); v = bytearray(M * 16)
x = 2463534242
for i in range(M):
    x = (x ^ (x << 13)) & 0xFFFFFFFF; x ^= x >> 17; x = (x ^ (x << 5)) & 0xFFFFFFFF
    for q in range(16): u[i * 16 + q] = (x >> (2 * q)) & 3
    x = (x ^ (x << 13)) & 0xFFFFFFFF; x ^= x >> 17; x = (x ^ (x << 5)) & 0xFFFFFFFF
    for q in range(16): v[i * 16 + q] = (x >> (2 * q)) & 3
n = 0
for r in range(4):
    for i in range(M * 16):
        n += u[i] == v[i]
print(n)
