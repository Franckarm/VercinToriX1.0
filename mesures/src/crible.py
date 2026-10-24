N = 5000000
p = [1] * N
p[0] = p[1] = 0
i = 2
while i * i < N:
    if p[i] == 1:
        j = i * i
        while j < N:
            p[j] = 0
            j += i
    i += 1
print(sum(p))
