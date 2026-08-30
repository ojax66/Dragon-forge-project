#!/usr/bin/env python3
"""Gera as texturas de UI da Incubadora a partir do mock-up de referencia.

  textures/ui/incubator_cell.png  celula de slot em nine-slice (18x18)
  textures/ui/incubator_gui.png   fundo da tela (176x166)

A celula NAO e desenhada no fundo: ela e uma textura propria, aplicada pelo
JSON UI em cada slot via $background_images. Assim as celulas caem sempre em
cima dos slots de verdade, sem depender de eu acertar o pixel na arte.

Paleta e medidas tiradas do mock-up (284x266, que e uma tela de 176x166
renderizada em 1.611x).
"""
import math, os, random, struct, zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "Incubadora [RP] - SallyTek Studio", "textures", "ui")

W, H = 176, 166          # tela inteira, igual a de bau/fornalha da vanilla
CELL = 18

# ---- paleta amostrada do mock-up ----
BG        = (101, 40, 40)    # fundo do painel
CELL_IN   = (80, 27, 27)     # interior da celula
CELL_SHAD = (65, 22, 22)     # sombra da celula (cima/esquerda)
CELL_LITE = (136, 61, 61)    # brilho da celula (baixo/direita)
EDGE_OUT  = (28, 7, 7)       # contorno externo do painel
EDGE_MID  = (83, 34, 34)
EDGE_LITE = (138, 61, 61)    # bisel claro (cima/esquerda)
EDGE_SOFT = (116, 51, 51)
EDGE_DARK = (49, 16, 16)     # bisel escuro (baixo/direita)
LAVA      = (222, 104, 24)   # nucleo do veio
LAVA_HOT  = (250, 160, 60)   # brilho
LAVA_EDGE = (150, 55, 14)   # borda do veio

# Nicho do tanque: e a mesma celula esticada pelo JSON UI, entao aqui so
# ficam registradas as medidas pra quem for conferir com o mock-up.
#   tanque  (7, 16) 18x61      balde  (31, 57) 18x18
#   entrada (74, 36) 18x18     setinha (95, 33) 26x26
#   saida   (124, 33) 26x26
#   grade 9x3 em (7, 86), hotbar em (7, 143), passo 18


def write_png(path, w, h, px):
    raw = b"".join(b"\x00" + b"".join(bytes(px[y][x]) for x in range(w)) for y in range(h))
    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    open(path, "wb").write(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def put(px, x, y, c, a=255):
    if not (0 <= x < len(px[0]) and 0 <= y < len(px)):
        return
    d = px[y][x]
    f = a / 255.0
    for i in range(3):
        d[i] = int(round(d[i] * (1 - f) + c[i] * f))
    d[3] = 255


# ------------------------------------------------------------- celula 18x18
def gen_cell():
    px = [[list(CELL_IN) + [255] for _ in range(CELL)] for _ in range(CELL)]
    for i in range(CELL):
        put(px, i, 0, CELL_SHAD)              # topo
        put(px, 0, i, CELL_SHAD)              # esquerda
        put(px, i, CELL - 1, CELL_LITE)       # baixo
        put(px, CELL - 1, i, CELL_LITE)       # direita
    write_png(os.path.join(OUT, "incubator_cell.png"), CELL, CELL, px)
    # nine-slice de 1px: a celula estica pro tanque (18x61) e pra saida (26x26)
    with open(os.path.join(OUT, "incubator_cell.json"), "w") as f:
        f.write('{\n  "nineslice_size": 1,\n  "base_size": [ 18, 18 ]\n}\n')


# ----------------------------------------------------------- fundo 176x166
def gen_background():
    rnd = random.Random(20260830)
    px = [[list(BG) + [255] for _ in range(W)] for _ in range(H)]

    # manchas largas e suaves, pra pedra nao ficar chapada
    for _ in range(40):
        cx, cy = rnd.randrange(W), rnd.randrange(H)
        r = rnd.randrange(10, 30)
        tint = rnd.choice([(114, 46, 44), (88, 33, 33)])
        for y in range(max(0, cy - r), min(H, cy + r)):
            for x in range(max(0, cx - r), min(W, cx + r)):
                d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                if d < r:
                    put(px, x, y, tint, int(34 * (1 - d / r)))

    for y in range(H):
        for x in range(W):
            n = rnd.randint(-3, 3)
            for i in range(3):
                px[y][x][i] = max(0, min(255, px[y][x][i] + n))

    # veios de lava finos e claros, como no mock-up: nucleo laranja vivo com
    # uma borda laranja escura - nada de contorno preto grosso
    def vein(x, y, ang, life, width, depth=0):
        for step in range(life):
            ang += rnd.uniform(-0.13, 0.13)
            x += math.cos(ang)
            y += math.sin(ang)
            if not (0 <= x < W and 0 <= y < H):
                return
            ix, iy = int(x), int(y)
            w = width * (1 - 0.55 * step / life)
            r_edge = max(1, int(round(w + 0.5)))
            for oy in range(-r_edge, r_edge + 1):
                for ox in range(-r_edge, r_edge + 1):
                    if ox * ox + oy * oy <= r_edge * r_edge:
                        put(px, ix + ox, iy + oy, LAVA_EDGE, 150)
            r_core = max(0, int(round(w - 0.4)))
            for oy in range(-r_core, r_core + 1):
                for ox in range(-r_core, r_core + 1):
                    if ox * ox + oy * oy <= r_core * r_core:
                        put(px, ix + ox, iy + oy, LAVA)
            if rnd.random() < 0.35:
                put(px, ix, iy, LAVA_HOT)
            if depth < 1 and rnd.random() < 0.022:
                vein(x, y, ang + rnd.choice([-1, 1]) * rnd.uniform(0.5, 1.0),
                     int(life * 0.5), width * 0.7, depth + 1)

    # A metade de baixo fica coberta pela grade, entao os veios nascem na area
    # da maquina (y < 84), que e a parte da arte que realmente aparece.
    for _ in range(3):
        borda = rnd.randrange(3)
        if borda == 0:   sx, sy, a = rnd.randrange(20, W - 20), 4, math.pi / 2
        elif borda == 1: sx, sy, a = 4, rnd.randrange(10, 80), 0.0
        else:            sx, sy, a = W - 5, rnd.randrange(10, 80), math.pi
        vein(sx, sy, a + rnd.uniform(-0.8, 0.8), rnd.randrange(70, 130), rnd.uniform(1.0, 1.6))
    # um escapando por baixo, so pra nao ficar seco
    vein(rnd.randrange(W), H - 5, -math.pi / 2 + rnd.uniform(-0.7, 0.7),
         rnd.randrange(40, 70), rnd.uniform(0.9, 1.3))

    # moldura: contorno escuro, bisel claro em cima/esquerda, escuro embaixo/direita
    for x in range(W):
        put(px, x, 0, EDGE_OUT); put(px, x, 1, EDGE_MID)
        put(px, x, 2, EDGE_LITE); put(px, x, 3, EDGE_SOFT)
        put(px, x, H - 1, EDGE_OUT); put(px, x, H - 2, EDGE_DARK)
    for y in range(H):
        put(px, 0, y, EDGE_OUT); put(px, 1, y, EDGE_MID)
        put(px, 2, y, EDGE_LITE); put(px, 3, y, EDGE_SOFT)
        put(px, W - 1, y, EDGE_OUT); put(px, W - 2, y, EDGE_DARK)

    write_png(os.path.join(OUT, "incubator_gui.png"), W, H, px)


os.makedirs(OUT, exist_ok=True)
gen_cell()
gen_background()
print("gerado:", sorted(f for f in os.listdir(OUT) if f.startswith("incubator_")))
