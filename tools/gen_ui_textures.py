#!/usr/bin/env python3
"""Gera as texturas de UI da Incubadora a partir do mock-up de referencia.

  textures/ui/incubator_cell.png  celula de slot em nine-slice (18x18)

O fundo da tela (textures/ui/incubator_gui.png) NAO sai daqui: e arte do autor,
copiada pro pacote sem edicao.

A celula NAO e desenhada no fundo: ela e uma textura propria, aplicada pelo
JSON UI em cada slot via $background_images. Assim as celulas caem sempre em
cima dos slots de verdade, sem depender de eu acertar o pixel na arte.

As medidas sao as do mock-up (284x266, que e uma tela de 176x166 renderizada
em 1.611x). A paleta da celula e amostrada das barras que vieram no pacote.
"""
import math, os, random, struct, zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "Incubadora [RP] - SallyTek Studio", "textures", "ui")

W, H = 176, 166          # tela inteira, igual a de bau/fornalha da vanilla
CELL = 18

# ---- paleta: amostrada da arte das barras que vem no pacote ----------------
# O corpo do tanque (textures/items/incubator_fuel_0) e o contorno da setinha
# sao a referencia: a tela tem que parecer o mesmo material que os medidores.
BG        = (101, 40, 40)    # fundo do painel
CELL_IN   = (80, 27, 27)     # interior da celula = corpo do tanque
CELL_SHAD = (65, 22, 22)     # sombra da celula (cima/esquerda)
CELL_LITE = (136, 61, 61)    # brilho da celula (baixo/direita)
EDGE_OUT  = (34, 11, 11)     # contorno externo = sombra funda do tanque
EDGE_MID  = (49, 13, 13)     # contorno da setinha
EDGE_LITE = (136, 61, 61)    # bisel claro (cima/esquerda)
EDGE_SOFT = (116, 51, 51)
EDGE_DARK = (49, 16, 16)     # bisel escuro (baixo/direita)
GROOVE    = (64, 21, 21)     # friso que separa a maquina do inventario

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
# NAO e gerado aqui. textures/ui/incubator_gui.png e arte do autor, 176x166,
# copiada pro pacote sem edicao. Trocar = sobrescrever o arquivo.
# (Ja existiu um gerador de fundo neste script; saiu quando a arte de verdade
#  chegou, pra ninguem apagar o arquivo bom rodando o script sem querer.)

os.makedirs(OUT, exist_ok=True)
gen_cell()
print("gerado:", sorted(f for f in os.listdir(OUT) if f.startswith("incubator_")))
