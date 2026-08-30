#!/usr/bin/env python3
"""Instala as texturas das barras (abastecimento e setinha) no resource pack.

Uso:  python3 tools/install_gauge_textures.py <pasta-com-os-pngs>

Classifica os PNGs pelo tamanho, ordena cada serie pela quantidade de pixel
laranja (do vazio pro cheio) e grava com nome numerado. Depois regenera tudo
que depende da contagem de quadros: os itens-display do behavior pack, o
item_texture.json, as linhas de idioma e as constantes do scripts/main.js.

Mandou mais quadros? Joga todos na pasta (os antigos junto) e roda de novo.
"""
import json, os, re, shutil, struct, sys, zlib
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "Incubadora [RP] - SallyTek Studio")
BP = os.path.join(ROOT, "Incubadora [BP] - SallyTek Studio")

ITEMS_DIR = os.path.join(BP, "items", "display")
TEX_DIR = os.path.join(RP, "textures", "items")
MAIN_JS = os.path.join(BP, "scripts", "main.js")

# As duas series usam laranjas diferentes: (128,49,6) na setinha e
# (179,67,6) na barra. O teste abaixo pega os dois e deixa de fora os
# marrons de fundo (80,27,27) e as bordas escuras.
def is_fill(p):
    r, g, b, a = p
    return a > 128 and r > 100 and g >= 30 and g <= 200 and b < 90 and r - b > 60
ARROW_SIZE = (32, 32)        # a setinha
FUEL_SIZE = (72, 266)        # a barra vertical de abastecimento

LANG = {
    "en_US.lang": {"tile": "Incubator", "block": "Incubator", "fuel": "Lava", "arrow": "Progress"},
    "pt_BR.lang": {"tile": "Incubadora", "block": "Incubadora", "fuel": "Lava", "arrow": "Progresso"},
}


# ------------------------------------------------------------------ PNG cru
def read_png(path):
    d = open(path, "rb").read()
    pos, idat, w, h, bd, ct, pal, trns = 8, b"", 0, 0, 8, 6, None, None
    while pos < len(d):
        ln = struct.unpack(">I", d[pos:pos + 4])[0]
        typ, data = d[pos + 4:pos + 8], d[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, bd, ct = struct.unpack(">IIBB", data[:10])
        elif typ == b"PLTE":
            pal = data
        elif typ == b"tRNS":
            trns = data
        elif typ == b"IDAT":
            idat += data
        elif typ == b"IEND":
            break
        pos += 12 + ln
    raw = zlib.decompress(idat)
    ch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ct]
    bpp, stride = ch * bd // 8, (w * ch * bd + 7) // 8
    out, prev, i = [], bytearray(stride), 0
    for _ in range(h):
        f = raw[i]; i += 1
        line = bytearray(raw[i:i + stride]); i += stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            if f == 1: line[x] = (line[x] + a) & 255
            elif f == 2: line[x] = (line[x] + b) & 255
            elif f == 3: line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if (pa <= pb and pa <= pc) else (b if pb <= pc else c))) & 255
        prev = line
        row = []
        for x in range(w):
            if ct == 3:
                idx = line[x]
                r, g, bl = pal[idx * 3:idx * 3 + 3]
                al = trns[idx] if trns and idx < len(trns) else 255
            elif ct == 6:
                r, g, bl, al = line[x * 4:x * 4 + 4]
            elif ct == 2:
                r, g, bl = line[x * 3:x * 3 + 3]; al = 255
            else:
                r = g = bl = line[x]; al = 255
            row.append([r, g, bl, al])
        out.append(row)
    return w, h, out


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


def fill_count(px):
    return sum(1 for row in px for p in row if is_fill(p))


# ----------------------------------------------------------------- series
def collect(src):
    arrows, fuel, ignored = [], [], []
    for name in sorted(os.listdir(src)):
        if not name.lower().endswith(".png"):
            continue
        path = os.path.join(src, name)
        try:
            w, h, px = read_png(path)
        except Exception as e:
            ignored.append((name, f"nao deu pra ler: {e}"))
            continue
        entry = (fill_count(px), name, w, h, px)
        if (w, h) == ARROW_SIZE:
            arrows.append(entry)
        elif (w, h) == FUEL_SIZE:
            fuel.append(entry)
        else:
            ignored.append((name, f"{w}x{h} nao e nem seta nem barra"))
    arrows.sort(key=lambda e: e[0])
    fuel.sort(key=lambda e: e[0])
    return arrows, fuel, ignored


def blank_frame(px):
    """Copia o quadro tirando o preenchimento: vira o estagio vazio."""
    out = [[list(p) for p in row] for row in px]
    for row in out:
        for p in row:
            if is_fill(p):
                p[3] = 0
    return out


def squarify(px, w, h):
    """Centraliza o quadro num canvas quadrado, com as sobras transparentes.

    Icone de item no Bedrock e sempre quadrado: o atlas nao aceita 72x266 e
    acaba cortando/deformando a barra. Com o quadro dentro de um quadrado de
    266x266, o atlas fica feliz e o JSON UI so precisa desenhar o item grande
    o suficiente pra barra dentro dele sair no tamanho certo.
    """
    side = max(w, h)
    if w == h:
        return px, side
    ox, oy = (side - w) // 2, (side - h) // 2
    out = [[[0, 0, 0, 0] for _ in range(side)] for _ in range(side)]
    for y in range(h):
        for x in range(w):
            out[oy + y][ox + x] = list(px[y][x])
    return out, side


def install(series, prefix, w, h):
    """Grava os quadros como <prefix>_0..N. Cria o vazio se nao veio nenhum."""
    for old in os.listdir(TEX_DIR):
        if old.startswith(prefix + "_") and old.endswith(".png"):
            os.remove(os.path.join(TEX_DIR, old))

    frames = [px for _, _, _, _, px in series]
    if series and series[0][0] > 0:
        frames.insert(0, blank_frame(series[0][4]))
        criado = True
    else:
        criado = False

    side = None
    for i, px in enumerate(frames):
        sq, side = squarify(px, w, h)
        write_png(os.path.join(TEX_DIR, f"{prefix}_{i}.png"), side, side, sq)
    return len(frames), criado


# ------------------------------------------------- o que depende da contagem
def regenerate(n_fuel, n_arrow):
    shutil.rmtree(ITEMS_DIR, ignore_errors=True)
    os.makedirs(ITEMS_DIR, exist_ok=True)

    tex = {"texture_name": "atlas.items", "resource_pack_name": "sallytek_incubator", "texture_data": {}}
    for prefix, count in (("incubator_fuel", n_fuel), ("incubator_arrow", n_arrow)):
        for i in range(count):
            name = f"{prefix}_{i}"
            tex["texture_data"][f"sallytek:{name}"] = {"textures": f"textures/items/{name}"}
            item = {
                "format_version": "1.20.80",
                "minecraft:item": {
                    "description": {
                        "identifier": f"sallytek:{name}",
                        "menu_category": {"category": "none", "is_hidden_in_commands": True},
                    },
                    "components": {
                        "minecraft:icon": {"textures": {"default": f"sallytek:{name}"}},
                        "minecraft:max_stack_size": 1,
                    },
                },
            }
            with open(os.path.join(ITEMS_DIR, name + ".json"), "w") as f:
                json.dump(item, f, indent="\t"); f.write("\n")

    with open(os.path.join(RP, "textures", "item_texture.json"), "w") as f:
        json.dump(tex, f, indent="\t"); f.write("\n")

    for fn, t in LANG.items():
        lines = [
            f"tile.sallytek:incubator.name={t['tile']}",
            "",
            "## titulo do container (nome da entidade invisivel)",
            f"sallytek.incubator.block={t['block']}",
            "",
            "## itens-display das barras",
        ]
        lines += [f"item.sallytek:incubator_fuel_{i}={t['fuel']}" for i in range(n_fuel)]
        lines += [f"item.sallytek:incubator_arrow_{i}={t['arrow']}" for i in range(n_arrow)]
        with open(os.path.join(RP, "texts", fn), "w") as f:
            f.write("\n".join(lines) + "\n")

    # constantes do script: 1 balde = 1 ponto, entao a capacidade e quadros - 1
    src = open(MAIN_JS).read()
    src = re.sub(r"const ARROW_STAGES = \d+;", f"const ARROW_STAGES = {n_arrow};", src)
    src = re.sub(r"const FUEL_POINTS = \d+;", f"const FUEL_POINTS = {n_fuel - 1};", src)
    open(MAIN_JS, "w").write(src)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    src = sys.argv[1]
    arrows, fuel, ignored = collect(src)

    if not arrows and not fuel:
        print("nenhuma textura reconhecida em", src)
        return 1

    n_arrow, arrow_novo = install(arrows, "incubator_arrow", *ARROW_SIZE) if arrows else (0, False)
    n_fuel, fuel_novo = install(fuel, "incubator_fuel", *FUEL_SIZE) if fuel else (0, False)
    regenerate(n_fuel, n_arrow)

    print(f"setinha:      {n_arrow} quadros" + ("  (estagio 0 vazio gerado aqui)" if arrow_novo else ""))
    for i, (c, name, *_ ) in enumerate(arrows):
        print(f"   incubator_arrow_{i + (1 if arrow_novo else 0)} <- {name}  ({c} px de lava)")
    print(f"abastecimento: {n_fuel} quadros -> capacidade {n_fuel - 1} baldes"
          + ("  (estagio 0 vazio gerado aqui)" if fuel_novo else ""))
    for i, (c, name, *_ ) in enumerate(fuel):
        print(f"   incubator_fuel_{i + (1 if fuel_novo else 0)} <- {name}  ({c} px de lava)")
    for name, motivo in ignored:
        print(f"ignorado: {name} — {motivo}")
    return 0


sys.exit(main())
