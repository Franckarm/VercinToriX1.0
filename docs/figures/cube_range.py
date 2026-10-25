import colorsys, math, random
from PIL import Image, ImageDraw, ImageFont
random.seed(3)
W, H = 1600, 1000
img = Image.new("RGB", (W, H), (14, 15, 22))
dr = ImageDraw.Draw(img, "RGBA")
F = lambda t: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", t)
FB = lambda t: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", t)
TEINTES = ["rouge", "orange", "jaune", "vert", "cyan", "bleu", "violet", "pourpre"]
HUE = [0.0, 0.08, 0.16, 0.33, 0.5, 0.64, 0.76, 0.88]
MAT = ["reflet", "lumière", "transparence", "profondeur", "rugosité"]
COL = []                       # colonnes : 3 de couleur puis les 5 matières, pour chaque teinte
for t in range(8):
    h0, h1 = HUE[t], (HUE[t + 1] if t < 7 else 1.0)
    for r in range(8):
        COL.append((h0 + (h1 - h0) * r / 8, None if r < 3 else MAT[r - 3], t))
NC, NS, NL = len(COL), 6, 7     # colonnes, saturations (du gris au pur), couches (du noir au blanc)
def coul(h, m, sat, lum):
    v = lum
    s = sat * math.sin(math.pi * lum) ** 0.6
    if m == "lumière": v = min(1, v * 1.3); s *= 0.8
    if m == "profondeur": v *= 0.55
    r, g, b = colorsys.hsv_to_rgb(h % 1, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))
cw, cd = 9, 16                 # largeur d'une colonne, profondeur d'une rangée (isométrique)
OX, OY, GAP = 50, 870, 112
def p(c, s, z):              # colonne, saturation (0 au fond : le gris), couche
    return (OX + c * cw + (NS - s) * cd * 1.3, OY - z * GAP - (NS - s) * cd * 0.42)
for z in range(NL):
    lum = z / (NL - 1)
    for s in range(NS):
        sat = s / (NS - 1)
        for c, (h, m, t) in enumerate(COL):
            if z == 0: col, m2 = (6, 6, 9), None
            elif z == NL - 1: col, m2 = (250, 250, 245), None
            else: col, m2 = coul(h, m, sat, lum), m
            a, b_ = p(c, s, z), p(c + 1, s, z)
            c_, d_ = p(c + 1, s + 1, z), p(c, s + 1, z)
            al = 120 if m2 == "transparence" else 255
            dr.polygon([a, b_, c_, d_], fill=col + (al,), outline=(0, 0, 0, 40))
            if m2 == "rugosité":
                for _ in range(4):
                    u, v = random.random(), random.random()
                    x = a[0] + (b_[0] - a[0]) * u + (d_[0] - a[0]) * v; y = a[1] + (b_[1] - a[1]) * u + (d_[1] - a[1]) * v
                    dr.point((x, y), fill=coul(h, m2, sat, min(1, lum * random.choice([0.5, 1.4]))))
            if m2 == "reflet" and s == NS - 1:
                dr.ellipse([a[0] + 2, a[1] - 3, a[0] + 6, a[1] + 0], fill=(255, 255, 255, 230))
    nom = "noir : tout est absorbé (profondeur absolue)" if z == 0 else "blanc : tout est renvoyé (lumière et reflet purs)" if z == NL - 1 else f"luminosité {z} / {NL - 1}"
    x, y = p(NC, NS, z)
    dr.text((x + 12, y - 8), nom, font=F(13), fill=(200, 200, 210))
# repères sous la couche du bas
for t in range(8):
    x, y = p(t * 8 + 1, NS, 0)
    dr.text((x - 6, y + 14), TEINTES[t], font=F(11), fill=(160, 160, 170))
x, y = p(0, 0, 0)
dr.text((OX - 30, OY + 62), "→ le spectre : chaque couleur glisse vers la suivante, ses matières entre les deux (reflet · lumière · transparence · profondeur · rugosité)", font=F(12), fill=(160, 160, 170))
dr.text((40, 26), "Le cube rangé : des couches du noir au blanc ; dans chaque couche, le spectre et ses matières, du gris (au fond) au pur (devant)", font=FB(19), fill=(235, 235, 228))
# --- à droite : le mot de 128 bits
X0, Y0 = 1000, 110
dr.text((X0, Y0), "Le point de matière de 128 bits", font=FB(20), fill=(235, 235, 228))
y = Y0 + 44
parts = [("R", 32, (220, 70, 70)), ("V", 32, (70, 190, 90)), ("B", 32, (80, 120, 230)),
         ("reflet", 6, (235, 235, 235)), ("lumière", 6, (250, 230, 120)), ("transp.", 6, (150, 200, 220)),
         ("prof.", 6, (60, 70, 120)), ("rugos.", 6, (150, 120, 90)), ("état", 2, (200, 120, 220))]
x = X0; k = 560 / 128
for nom, n, c in parts:
    dr.rectangle([x, y, x + n * k - 2, y + 44], fill=c)
    if n >= 32:
        dr.text((x + 6, y + 14), f"{nom}  {n} bits", font=FB(13), fill=(255, 255, 255))
    x += n * k
y += 54
dr.text((X0, y), "à droite, la matière : reflet, lumière, transparence, profondeur, rugosité\n(6 bits chacune), et l'état (2 bits)", font=F(12), fill=(170, 170, 180))
y += 50
dr.text((X0, y), "Couleurs du cube chromatique (3 × 32 bits) :", font=F(15), fill=(200, 200, 210)); y += 26
dr.text((X0, y), "79 228 162 514 264 337 593 543 950 336", font=FB(22), fill=(255, 225, 120)); y += 36
dr.text((X0, y), "= 2^96, environ 79 milliards de milliards de milliards", font=F(14), fill=(170, 170, 180)); y += 40
dr.text((X0, y), "Matière : 5 propriétés de 64 degrés (6 bits chacune)", font=F(15), fill=(200, 200, 210)); y += 26
dr.text((X0, y), "1 073 741 824 matières", font=FB(22), fill=(150, 210, 240)); y += 34
dr.text((X0, y), "État : un quit de Belnap (inconnu, faux, vrai, variable)", font=F(15), fill=(200, 200, 210)); y += 40
dr.text((X0, y), "En tout : 2^128 points de matière", font=FB(17), fill=(235, 235, 228)); y += 26
dr.text((X0, y), "340 282 366 920 938 463 463 374 607 431 768 211 456", font=F(15), fill=(235, 235, 228)); y += 50
dr.text((X0, y), "La configuration minimale, 64 bits :", font=FB(15), fill=(200, 200, 210)); y += 24
dr.text((X0, y), "3 × 16 bits de couleur : 281 474 976 710 656 couleurs", font=F(14), fill=(200, 200, 210)); y += 22
dr.text((X0, y), "5 × 3 bits de matière (8 degrés) + 1 bit d'état", font=F(14), fill=(200, 200, 210)); y += 34
dr.text((X0, y), "La rétro-ingénierie, 32 bits :", font=FB(15), fill=(200, 200, 210)); y += 24
dr.text((X0, y), "3 × 8 bits de couleur : 16 777 216 couleurs, + 8 bits (alpha)", font=F(14), fill=(200, 200, 210))
img.save("cube_range.png")
print("ok")
