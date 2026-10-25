import math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
random.seed(5)
W, H = 1600, 1000
img = Image.new("RGBA", (W, H), (14, 15, 22, 255))
F = lambda t: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", t)
FB = lambda t: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", t)
def cube(OX, OY, S, N, matiere=None, diag=False):
    """Le cube chromatique en nuage de points : x = rouge, y = vert, z = bleu ; vu de biais pour que la diagonale
    du noir au blanc se voie de bout en bout."""
    global img
    az, el = math.radians(-45 + 12), math.radians(0)
    def proj(x, y, z):
        x, y, z = x - (N - 1) / 2, y - (N - 1) / 2, z - (N - 1) / 2
        # le noir en bas, le blanc en haut : on incline le cube pour que la diagonale monte
        X = x * math.cos(az) - y * math.sin(az)
        Y = x * math.sin(az) + y * math.cos(az)
        Z = z
        # inclinaison de la diagonale vers le haut
        t = math.radians(-54.74 + 8)
        Y2 = Y * math.cos(t) - Z * math.sin(t); Z2 = Y * math.sin(t) + Z * math.cos(t)
        Y3 = Y2 * math.cos(el) - Z2 * math.sin(el); Z3 = Y2 * math.sin(el) + Z2 * math.cos(el)
        return OX + X * S, OY - Z3 * S, Y3
    cal = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(cal)
    lueur = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lueur)
    # les arêtes du cube
    for p in [(0,0,0),(1,0,0),(0,1,0),(0,0,1),(1,1,0),(1,0,1),(0,1,1),(1,1,1)]:
        for q in [(0,0,0),(1,0,0),(0,1,0),(0,0,1),(1,1,0),(1,0,1),(0,1,1),(1,1,1)]:
            if sum(abs(a - b) for a, b in zip(p, q)) == 1 and p < q:
                A = proj(*[v * (N - 1) for v in p]); B = proj(*[v * (N - 1) for v in q])
                d.line([A[:2], B[:2]], fill=(120, 120, 135, 120), width=1)
    pts = []
    for x in range(N):
        for y in range(N):
            for z in range(N):
                px, py, dep = proj(x, y, z)
                pts.append((dep, x, y, z, px, py))
    pts.sort(reverse=True)
    r0 = S * 0.33
    for dep, x, y, z, px, py in pts:
        c = tuple(int(255 * v / (N - 1)) for v in (x, y, z))
        r = r0 * (1 + 0.012 * -dep * 3)
        a = 230
        sur = x == y == z
        if diag and not sur: a = 150
        if diag and sur: r *= 1.6
        if matiere == "transparence": a = 70
        if matiere == "profondeur": c = tuple(int(v * 0.45) for v in c)
        if matiere == "lumière":
            c = tuple(min(255, int(v * 1.1 + 35)) for v in c)
            ld.ellipse([px - r * 3, py - r * 3, px + r * 3, py + r * 3], fill=c + (45,))
        d.ellipse([px - r, py - r, px + r, py + r], fill=c + (a,), outline=(255, 255, 255, 140) if diag and sur else None)
        if matiere == "reflet":
            d.ellipse([px - r * 0.6, py - r * 0.65, px - r * 0.05, py - r * 0.15], fill=(255, 255, 255, 220))
        if matiere == "rugosité":
            for _ in range(5):
                u, v = random.uniform(-r, r), random.uniform(-r, r)
                if u * u + v * v < r * r:
                    q = random.choice([0.4, 1.5])
                    d.point((px + u, py + v), fill=tuple(min(255, int(t * q)) for t in c) + (255,))
    if diag:
        A = proj(0, 0, 0); B = proj(N - 1, N - 1, N - 1)
        d.line([A[:2], B[:2]], fill=(235, 235, 235, 230), width=3)
        for k in range(N):
            px, py, _ = proj(k, k, k); r = r0 * 1.5; g = int(255 * k / (N - 1))
            d.ellipse([px - r, py - r, px + r, py + r], fill=(g, g, g, 255), outline=(255, 255, 255, 200))
    if matiere == "lumière":
        img = Image.alpha_composite(img, lueur.filter(ImageFilter.GaussianBlur(6)))
    img = Image.alpha_composite(img, cal)
    return proj
# --- le grand cube, avec sa diagonale du noir au blanc
N = 8
proj = cube(380, 380, 38, N, diag=True)
dr = ImageDraw.Draw(img)
coins = {"noir": (0, 0, 0), "rouge": (7, 0, 0), "vert": (0, 7, 0), "bleu": (0, 0, 7), "jaune": (7, 7, 0),
         "magenta": (7, 0, 7), "cyan": (0, 7, 7), "blanc": (7, 7, 7)}
for n, p in coins.items():
    x, y, dep = proj(*p)
    if n in ("rouge", "cyan"):
        dr.text((x + 14, y + 6), n + " (derrière)", font=F(12), fill=(150, 150, 160))
    else:
        dr.text((x + 14, y - 8), n, font=FB(14), fill=(235, 235, 228))
dr.text((40, 26), "Le cube chromatique, inchangé : du noir au blanc par la diagonale des gris ; la matière s'ajoute à chaque point",
        font=FB(19), fill=(235, 235, 228))
dr.text((40, 58), "La place d'un point (R, V, B) reste sa couleur ; sa matière est en plus, dans le même mot.", font=F(15), fill=(170, 172, 185))
dr.text((40, 640), "la diagonale (en blanc) : noir → gris → blanc, la luminosité sans teinte", font=F(14), fill=(200, 200, 210))
# --- les cinq matières : le même cube, avec chaque matière
mats = ["reflet", "lumière", "transparence", "profondeur", "rugosité"]
for i, m in enumerate(mats):
    ox = 110 + i * 175
    cube(ox, 830, 13, 8, matiere=m)
    dr = ImageDraw.Draw(img)
    dr.text((ox - 30, 935), m, font=FB(14), fill=(220, 220, 228))
dr.text((40, 690), "La matière, à chaque point du cube : le même cube vu avec chacune de ses cinq matières", font=F(15), fill=(200, 200, 210))
# --- à droite : le mot de 128 bits
X0, Y0 = 1000, 110
dr.text((X0, Y0), "Le point de matière de 128 bits", font=FB(20), fill=(235, 235, 228))
y = Y0 + 44; x = X0; k = 560 / 128
for nom, n, c in [("R", 32, (220, 70, 70)), ("V", 32, (70, 190, 90)), ("B", 32, (80, 120, 230)), ("", 6, (235, 235, 235)),
                  ("", 6, (250, 230, 120)), ("", 6, (150, 200, 220)), ("", 6, (60, 70, 120)), ("", 6, (150, 120, 90)), ("", 2, (200, 120, 220))]:
    dr.rectangle([x, y, x + n * k - 2, y + 44], fill=c)
    if nom: dr.text((x + 6, y + 14), f"{nom}  {n} bits", font=FB(13), fill=(255, 255, 255))
    x += n * k
y += 54
dr.text((X0, y), "la place dans le cube (la couleur)", font=F(12), fill=(170, 170, 180))
dr.text((X0 + 96 * k - 150, y + 16), "la matière (5 × 6 bits) et l'état (2 bits)", font=F(12), fill=(170, 170, 180))
y += 40
dr.text((X0, y), "Couleurs du cube chromatique (3 × 32 bits) :", font=F(15), fill=(200, 200, 210)); y += 26
dr.text((X0, y), "79 228 162 514 264 337 593 543 950 336", font=FB(22), fill=(255, 225, 120)); y += 34
dr.text((X0, y), "= 2^96, environ 79 milliards de milliards de milliards", font=F(14), fill=(170, 170, 180)); y += 40
dr.text((X0, y), "Matière : reflet, lumière, transparence, profondeur, rugosité", font=F(15), fill=(200, 200, 210)); y += 22
dr.text((X0, y), "(64 degrés chacune)", font=F(15), fill=(200, 200, 210)); y += 26
dr.text((X0, y), "1 073 741 824 matières", font=FB(22), fill=(150, 210, 240)); y += 36
dr.text((X0, y), "État : un quit de Belnap (inconnu, faux, vrai, variable)", font=F(15), fill=(200, 200, 210)); y += 40
dr.text((X0, y), "En tout : 2^128 points de matière", font=FB(17), fill=(235, 235, 228)); y += 26
dr.text((X0, y), "340 282 366 920 938 463 463 374 607 431 768 211 456", font=F(15), fill=(235, 235, 228)); y += 50
dr.text((X0, y), "Pour l'IA : un point = un vecteur de huit nombres", font=FB(15), fill=(200, 200, 210)); y += 24
dr.text((X0, y), "(R, V, B, reflet, lumière, transparence, profondeur, rugosité)", font=F(14), fill=(200, 200, 210)); y += 22
dr.text((X0, y), "deux points proches dans le cube sont deux matières proches", font=F(14), fill=(200, 200, 210)); y += 36
dr.text((X0, y), "64 bits (minimal) : 3 × 16 bits de couleur, 281 474 976 710 656 couleurs", font=F(13), fill=(170, 170, 180)); y += 20
dr.text((X0, y), "32 bits (rétro-ingénierie) : 3 × 8 bits, 16 777 216 couleurs, + alpha", font=F(13), fill=(170, 170, 180))
img.convert("RGB").save("cube_diagonale.png")
print("ok")
