"""Gera textures/ui/incubator_gui.png: o fundo 176x166 da tela da Incubadora.

As coordenadas aqui PRECISAM bater com ui/incubator/screen.json (slots da
maquina) e com o layout fixo do Bedrock para a metade de baixo:
  - grade do inventario: 9x3 celulas de 18px em (7, 86)
  - hotbar:              9x1 celulas de 18px em (7, 143)
"""
import zlib, struct, random, os

OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Incubadora [RP] - SallyTek Studio", "textures", "ui", "incubator_gui.png",
)

W, H = 176, 166

# Slots da maquina (canto superior esquerdo, largura, altura)
FUEL_BAR   = (11, 17, 14, 52)
FUEL_SLOT  = (37, 34, 18, 18)
INPUT_SLOT = (67, 17, 18, 18)
ARROW_BAR  = (97, 17, 14, 52)
OUTPUT_SLOT = (133, 32, 18, 18)

INV_ORIGIN, HOTBAR_ORIGIN, CELL = (7, 86), (7, 143), 18

# Paleta do mock-up
BASE      = (74, 31, 26)
CRACK     = (36, 14, 11)
LAVA      = (194, 73, 10)
LAVA_HOT  = (231, 122, 18)
EDGE_LITE = (120, 52, 40)
EDGE_DARK = (33, 12, 10)
SLOT_IN   = (40, 16, 13)
SLOT_SHAD = (24, 9, 7)


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
    if not (0 <= x < W and 0 <= y < H):
        return
    d = px[y][x]
    f = a / 255.0
    for i in range(3):
        d[i] = int(round(d[i] * (1 - f) + c[i] * f))
    d[3] = 255


def recess(px, x0, y0, w, h):
    """Cava um nicho: fundo escuro, sombra em cima/esquerda, luz embaixo/direita."""
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            put(px, x, y, SLOT_IN)
    for i in range(w):
        put(px, x0 + i, y0, SLOT_SHAD)
        put(px, x0 + i, y0 + h - 1, EDGE_LITE, 150)
    for i in range(h):
        put(px, x0, y0 + i, SLOT_SHAD)
        put(px, x0 + w - 1, y0 + i, EDGE_LITE, 150)
    put(px, x0, y0, EDGE_DARK)


def main():
    rnd = random.Random(11)
    px = [[list(BASE) + [255] for _ in range(W)] for _ in range(H)]

    # ruido de tijolo
    for y in range(H):
        for x in range(W):
            n = rnd.randint(-9, 9)
            px[y][x] = [max(0, min(255, BASE[i] + n)) for i in range(3)] + [255]

    # veios de lava
    for _ in range(9):
        x, y = rnd.randrange(W), rnd.randrange(H)
        dx, dy = rnd.choice([(1, 0), (0, 1), (1, 1), (1, -1)])
        for _ in range(rnd.randrange(30, 90)):
            put(px, x, y, CRACK)
            put(px, x, y + 1, CRACK, 110)
            if rnd.random() < 0.22:
                put(px, x, y, LAVA if rnd.random() < 0.7 else LAVA_HOT, 200)
            x += dx + rnd.choice([-1, 0, 0, 0, 1])
            y += dy + rnd.choice([-1, 0, 0, 0, 1])
            if not (0 <= x < W and 0 <= y < H):
                break

    # moldura
    for x in range(W):
        put(px, x, 0, EDGE_DARK); put(px, x, H - 1, EDGE_DARK)
        put(px, x, 1, EDGE_LITE, 170); put(px, x, H - 2, SLOT_SHAD, 170)
    for y in range(H):
        put(px, 0, y, EDGE_DARK); put(px, W - 1, y, EDGE_DARK)
        put(px, 1, y, EDGE_LITE, 170); put(px, W - 2, y, SLOT_SHAD, 170)

    # nichos das barras e celulas da maquina
    for r in (FUEL_BAR, ARROW_BAR, FUEL_SLOT, INPUT_SLOT, OUTPUT_SLOT):
        recess(px, *r)

    # grade do inventario e hotbar
    for ox, oy, rows in ((INV_ORIGIN[0], INV_ORIGIN[1], 3), (HOTBAR_ORIGIN[0], HOTBAR_ORIGIN[1], 1)):
        for row in range(rows):
            for col in range(9):
                recess(px, ox + col * CELL, oy + row * CELL, CELL, CELL)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    write_png(OUT, W, H, px)
    print("gerado:", OUT)


main()
