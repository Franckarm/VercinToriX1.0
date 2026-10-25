import colorsys, math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
random.seed(7)
N, B = 8, 3          # 8 x 8 x 8 places, 3 bits par axe
# --- le fil : courbe de Hilbert en 3D (Skilling) : chaque pas va d'une place à sa voisine
def hilbert(d):
    X = [0, 0, 0]
    # index -> transposé
    for i in range(B * 3):
        bit = (d >> (B * 3 - 1 - i)) & 1
        X[i % 3] |= bit << (B - 1 - i // 3)
    Nn = 2 << (B - 1)
    t = X[2] >> 1
    for i in range(2, 0, -1):
        X[i] ^= X[i - 1]
    X[0] ^= t
    Q = 2
    while Q != Nn:
        P = Q - 1
        for i in range(2, -1, -1):
            if X[i] & Q:
                X[0] ^= P
            else:
                t = (X[0] ^ X[i]) & P; X[0] ^= t; X[i] ^= t
        Q <<= 1
    return tuple(X)
fil = [hilbert(d) for d in range(N ** 3)]
assert all(sum(abs(a - b) for a, b in zip(fil[i], fil[i + 1])) == 1 for i in range(len(fil) - 1))
# --- le spectre le long du fil, et les matières aux ruptures
TEINTES = [("rouge", 0.0), ("orange", 0.08), ("jaune", 0.16), ("vert", 0.33), ("cyan", 0.5), ("bleu", 0.64), ("violet", 0.76), ("pourpre", 0.88)]
MATIERES = ["reflet", "lumineux", "transparent", "profondeur", "rugueux"]
# le fil monte en spirale du noir au blanc : huit tours, un par luminosité ; à chaque tour la couleur glisse d'une
# teinte à l'autre, et la matière s'intègre entre deux couleurs (reflet, lumière, transparence, profondeur, rugosité)
place = {}
for i in range(512):
    tour, k = divmod(i, 64)
    t, r = divmod(k, 8)
    lum = (i + 0.5) / 512                      # 0 : noir, 1 : blanc
    h = (t + r / 8) / 8
    m = "mat" if r < 3 else MATIERES[r - 3]
    if i < 6: m = "pole_noir"
    if i >= 506: m = "pole_blanc"
    place[fil[i]] = (h, m, i, lum)
def couleur_l(h, m, lum, ombrage=1.0):
    if m == "pole_noir": return tuple(int(c * ombrage) for c in (8, 8, 12))
    if m == "pole_blanc": return tuple(int(c * ombrage) for c in (250, 250, 246))
    sat = math.sin(math.pi * lum) ** 0.7       # pas de teinte aux deux pôles
    v = 0.08 + 0.92 * lum ** 0.8
    if m == "lumineux": v = min(1, v * 1.25); sat *= 0.8
    if m == "profondeur": v *= 0.55; sat = min(1, sat * 1.1)
    if m == "mat": sat *= 0.9
    r, g, b = colorsys.hsv_to_rgb(h % 1, sat * 0.9, v * ombrage)
    return (int(r * 255), int(g * 255), int(b * 255))
def couleur(h, m, ombrage):
    s, v = 0.85, 0.92
    if m == "mat": s, v = 0.75, 0.80
    if m == "lumineux": s, v = 0.65, 1.0
    if m == "profondeur": s, v = 0.95, 0.42
    r, g, b = colorsys.hsv_to_rgb(h % 1, s, v * ombrage if m != "lumineux" else min(1, v * (0.75 + 0.35 * ombrage)))
    return (int(r * 255), int(g * 255), int(b * 255))
# --- projection isométrique
W, H = 1500, 960
img = Image.new("RGBA", (W, H), (14, 15, 22, 255))
S = 30
OX, OY = 430, 370
def iso(x, y, z):
    return (OX + (x - y) * S * 0.866, OY + (x + y) * S * 0.5 - z * S)
# l'ombre, au-dehors : le cube projeté sur le sol, décalé par la lumière
ombre = Image.new("RGBA", (W, H), (0, 0, 0, 0))
od = ImageDraw.Draw(ombre)
dx, dy = 3.2, 1.6
coins = [(0, 0), (N, 0), (N, N), (0, N)]
sol = lambda x, y: (OX + (x - y) * S * 0.866 + dx * S, OY + (x + y) * S * 0.5 + N * S * 0.25 + dy * S + S * 1.2)
from itertools import product
pts = [sol(x, y) for x, y in coins] + [sol(x + 2.4, y + 2.4) for x, y in coins]
# enveloppe convexe simple
def enveloppe(p):
    p = sorted(set(p))
    def cr(o, a, b): return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lo, hi = [], []
    for q in p:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], q) <= 0: lo.pop()
        lo.append(q)
    for q in reversed(p):
        while len(hi) >= 2 and cr(hi[-2], hi[-1], q) <= 0: hi.pop()
        hi.append(q)
    return lo[:-1] + hi[:-1]
od.polygon(enveloppe(pts), fill=(0, 0, 0, 120))
ombre = ombre.filter(ImageFilter.GaussianBlur(14))
img = Image.alpha_composite(img, ombre)
# les voxels, de l'arrière vers l'avant
lueur = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ld = ImageDraw.Draw(lueur)
ordre_dessin = sorted(product(range(N), repeat=3), key=lambda p: (p[0] + p[1], p[2]))
for (x, y, z) in ordre_dessin:
    h, m, i, lum = place[(x, y, z)]
    calque = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(calque)
    a = 90 if m == "transparent" else 255
    haut = [iso(x, y, z + 1), iso(x + 1, y, z + 1), iso(x + 1, y + 1, z + 1), iso(x, y + 1, z + 1)]
    gauche = [iso(x, y + 1, z + 1), iso(x + 1, y + 1, z + 1), iso(x + 1, y + 1, z), iso(x, y + 1, z)]
    droite = [iso(x + 1, y, z + 1), iso(x + 1, y + 1, z + 1), iso(x + 1, y + 1, z), iso(x + 1, y, z)]
    for face, om in ((haut, 1.0), (gauche, 0.72), (droite, 0.55)):
        d.polygon(face, fill=couleur_l(h, m, lum, om) + (a,), outline=(0, 0, 0, 60 if a == 255 else 30))
    if m == "rugueux":
        for face, om in ((haut, 1.0), (gauche, 0.72), (droite, 0.55)):
            xs = [p[0] for p in face]; ys = [p[1] for p in face]
            for _ in range(26):
                u, v = random.random(), random.random()
                px = face[0][0] + (face[1][0] - face[0][0]) * u + (face[3][0] - face[0][0]) * v
                py = face[0][1] + (face[1][1] - face[0][1]) * u + (face[3][1] - face[0][1]) * v
                c = couleur_l(h, m, lum, om * random.choice([0.55, 0.7, 1.25]))
                d.rectangle([px, py, px + 1.6, py + 1.6], fill=c + (255,))
    if m in ("reflet", "pole_blanc"):
        cx = sum(p[0] for p in haut) / 4; cy = sum(p[1] for p in haut) / 4
        for r, al in ((9, 50), (6, 110), (3, 220)):
            d.ellipse([cx - r * 1.4 - 4, cy - r * 0.7 - 2, cx + r * 1.4 - 4, cy + r * 0.7 - 2], fill=(255, 255, 255, al))
    if m == "lumineux":
        cx = sum(p[0] for p in haut) / 4; cy = (sum(p[1] for p in haut) / 4) + S * 0.4
        ld.ellipse([cx - 34, cy - 30, cx + 34, cy + 30], fill=couleur_l(h, m, lum) + (120,))
    img = Image.alpha_composite(img, calque)
img = Image.alpha_composite(img, lueur.filter(ImageFilter.GaussianBlur(12)))
dr = ImageDraw.Draw(img)
F = lambda t: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", t)
FB = lambda t: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", t)
dr.text((40, 30), "Le cube : un globe de lumière entre le noir et le blanc", font=FB(26), fill=(235, 235, 228))
dr.text((40, 66), "8 × 8 × 8 places. Le fil parcourt tout le volume d'une place à sa voisine, en montant du noir au blanc.", font=F(16), fill=(170, 172, 185))
dr.text((470, 840), "l'ombre : la seule chose hors du cube", font=F(17), fill=(150, 150, 160))
dr.line([(640, 835), (620, 790)], fill=(120, 120, 130), width=1)
# --- le fil déroulé : huit tours, du noir (en bas) au blanc (en haut) ; à gauche, l'axe des gris
x0, y0 = 960, 150
dr.text((x0 - 60, 100), "Le fil en spirale, déroulé : un tour par luminosité", font=FB(18), fill=(235, 235, 228))
cw, rh = 7, 74
for tour in range(8):
    y = y0 + (7 - tour) * rh
    g = int(255 * (tour + 0.5) / 8)
    dr.rectangle([x0 - 50, y, x0 - 22, y + 50], fill=(g, g, g))
    for k in range(64):
        i = tour * 64 + k
        h, m, _, lum = place[fil[i]]
        c = couleur_l(h, m, lum)
        xx = x0 + k * cw
        al = 110 if m == "transparent" else 255
        img.alpha_composite(Image.new("RGBA", (cw - 1, 50), c + (al,)), (int(xx), int(y)))
        if m == "rugueux":
            for _ in range(10):
                dr.point((xx + random.randint(0, cw - 2), y + random.randint(0, 49)), fill=couleur_l(h, m, lum, random.choice([0.5, 1.4])))
        if m == "reflet":
            dr.rectangle([xx + 1, y + 4, xx + 3, y + 9], fill=(255, 255, 255))
        if m == "lumineux":
            dr.rectangle([xx, y, xx + cw - 2, y + 49], outline=(255, 255, 225))
    dr.text((x0 + 64 * cw + 10, y + 18), f"tour {tour + 1}", font=F(13), fill=(170, 172, 185))
dr.text((x0 - 70, y0 + 8 * rh - 14), "axe des gris", font=F(12), fill=(170, 172, 185))
dr.text((x0, y0 + 8 * rh + 6), "← noir : la profondeur absolue (tout est absorbé)", font=F(14), fill=(200, 200, 210))
dr.text((x0, y0 - 26), "blanc : la lumière et le reflet purs (tout est renvoyé) →", font=F(14), fill=(200, 200, 210))
for t, (nom, _) in enumerate(TEINTES):
    dr.text((x0 + t * 8 * cw, y0 + 8 * rh + 30), nom, font=F(10), fill=(150, 150, 160))
dr.text((x0, y0 + 8 * rh + 50), "dans chaque teinte : 3 places de couleur,\npuis reflet · lumière · transparence · profondeur · rugosité", font=F(12), fill=(150, 150, 160))
img = img.convert("RGB")
img.save("cube_matiere.png")
print("ok")
