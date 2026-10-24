# Python n'a pas de flottant de 32 bits : le calcul se fait en 64 bits (le total peut différer d'un poil)
total = 0
for py in range(300):
    ci = py * 0.008 - 1.2
    for px in range(400):
        cr = px * 0.0075 - 2.1
        x = y = 0.0
        k = 0
        while k < 200 and x * x + y * y <= 4.0:
            x, y = x * x - y * y + cr, 2.0 * x * y + ci
            k += 1
        total += k
print(total)
