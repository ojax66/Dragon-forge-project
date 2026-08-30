"""Gera as texturas de UI da Incubadora (fundo, moldura e slots)."""
import zlib, struct, random, os, math

OUT = "/home/user/Dragon-forge-project/Incubadora [RP] - SallyTek Studio/textures/ui"

def write_png(path, w, h, px):
    raw = b"".join(b"\x00" + b"".join(bytes(px[y][x]) for x in range(w)) for y in range(h))
    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    open(path, "wb").write(png)

def blank(w, h, c=(0, 0, 0, 0)):
    return [[list(c) for _ in range(w)] for _ in range(h)]

def blend(dst, c):
    a = c[3] / 255.0
    for i in range(3):
        dst[i] = int(round(dst[i] * (1 - a) + c[i] * a))
    dst[3] = max(dst[3], c[3])

# Paleta extraida do mock-up da UI final
BASE      = (74, 31, 26, 255)    # tijolo escuro do fundo
BASE_DARK = (56, 22, 18, 255)
BASE_LITE = (94, 41, 33, 255)
CRACK     = (36, 14, 11, 255)
LAVA      = (194, 73, 10, 255)
LAVA_HOT  = (231, 122, 18, 255)
EDGE_LITE = (120, 52, 40, 255)
EDGE_DARK = (33, 12, 10, 255)
SLOT_IN   = (40, 16, 13, 255)
SLOT_SHAD = (26, 10, 8, 255)

# ---------------------------------------------------------------- fundo tilable
def bg_tile(path, size=32, seed=7):
    rnd = random.Random(seed)
    px = blank(size, size, BASE)
    # ruido de tijolo
    for y in range(size):
        for x in range(size):
            n = rnd.randint(-10, 10)
            px[y][x] = [max(0, min(255, BASE[i] + n)) for i in range(3)] + [255]
    # veios de lava que dao a volta na textura (wrap = continua ao repetir)
    for _ in range(2):
        x, y = rnd.randrange(size), rnd.randrange(size)
        dx, dy = rnd.choice([(1, 0), (0, 1), (1, 1)])
        for step in range(size + rnd.randrange(size // 2)):
            blend(px[y % size][x % size], CRACK)
            blend(px[(y + 1) % size][x % size], (*CRACK[:3], 120))
            if rnd.random() < 0.28:
                blend(px[y % size][x % size], (*(LAVA if rnd.random() < 0.7 else LAVA_HOT)[:3], 190))
            x += dx + rnd.choice([-1, 0, 0, 0, 1])
            y += dy + rnd.choice([-1, 0, 0, 0, 1])
    write_png(path, size, size, px)

# ------------------------------------------------------- moldura em nine-slice
def frame(path, size=24, border=8):
    px = blank(size, size)
    for y in range(size):
        for x in range(size):
            edge = min(x, y, size - 1 - x, size - 1 - y)
            if edge >= border:
                continue  # centro transparente: o fundo tilable aparece
            if edge == 0:
                c = EDGE_DARK
            elif edge == 1:
                c = BASE_LITE if (x < border and y < border) or y < border else EDGE_LITE
            elif edge >= border - 2:
                c = EDGE_DARK
            else:
                c = BASE
            px[y][x] = list(c)
    # brilho no topo/esquerda, sombra em baixo/direita (bisel)
    for i in range(2, border - 2):
        for x in range(i, size - i):
            blend(px[i][x], (*BASE_LITE[:3], 90))
            blend(px[size - 1 - i][x], (*EDGE_DARK[:3], 90))
        for y in range(i, size - i):
            blend(px[y][i], (*BASE_LITE[:3], 70))
            blend(px[y][size - 1 - i], (*EDGE_DARK[:3], 70))
    write_png(path, size, size, px)

# ------------------------------------------------------------------ slot 18x18
def slot(path, hover=False, size=18):
    px = blank(size, size)
    for y in range(size):
        for x in range(size):
            edge = min(x, y, size - 1 - x, size - 1 - y)
            if edge == 0:
                c = EDGE_DARK
            elif edge == 1:
                c = SLOT_SHAD if (x < size / 2 and y < size / 2) else BASE_LITE
            else:
                c = SLOT_IN
            px[y][x] = list(c)
    # sombra interna no canto superior esquerdo
    for i in range(2, 4):
        for x in range(i, size - i):
            blend(px[i][x], (*SLOT_SHAD[:3], 110))
        for y in range(i, size - i):
            blend(px[y][i], (*SLOT_SHAD[:3], 110))
    if hover:
        for y in range(size):
            for x in range(size):
                if min(x, y, size - 1 - x, size - 1 - y) >= 1:
                    blend(px[y][x], (*LAVA_HOT[:3], 70))
    write_png(path, size, size, px)

# ------------------------------------------- nicho escuro atras das barras/saida
def recess(path, w=24, h=24):
    px = blank(w, h)
    for y in range(h):
        for x in range(w):
            edge = min(x, y, w - 1 - x, h - 1 - y)
            c = EDGE_DARK if edge == 0 else (SLOT_SHAD if edge < 3 else (22, 8, 7, 255))
            px[y][x] = list(c)
    write_png(path, w, h, px)

os.makedirs(OUT, exist_ok=True)
bg_tile(os.path.join(OUT, "incubator_bg_tile.png"))
frame(os.path.join(OUT, "incubator_frame.png"))
slot(os.path.join(OUT, "incubator_slot.png"))
slot(os.path.join(OUT, "incubator_slot_hover.png"), hover=True)
recess(os.path.join(OUT, "incubator_recess.png"))
print("ok:", sorted(os.listdir(OUT)))
