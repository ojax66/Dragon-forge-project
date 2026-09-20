#!/usr/bin/env python3
"""Instala as texturas das barras (abastecimento e setinha) no resource pack.

Uso:  python3 tools/install_gauge_textures.py                 # as duas maquinas
      python3 tools/install_gauge_textures.py <pasta> <lava|gelo>

Sem argumento ele reinstala as duas a partir das pastas versionadas
(tools/frames e tools/frames_ice). Com argumento, troca os quadros de uma
maquina so pelos de <pasta>.

Classifica os PNGs pelo tamanho, ordena cada serie pela quantidade de pixel
preenchido (do vazio pro cheio) e grava com nome numerado. Depois regenera
tudo que depende da contagem de quadros: os itens-display do behavior pack, o
item_texture.json, as linhas de idioma e as contagens da tabela MACHINES do
scripts/main.js.

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

# O que conta como "cheio" em cada maquina. A de lava usa dois laranjas
# diferentes ((128,49,6) na setinha e (179,67,6) na barra) e a de gelo usa os
# azuis da agua; os dois testes deixam de fora o fundo e o contorno.
def fill_lava(p):
    r, g, b, a = p
    return a > 128 and r > 100 and g >= 30 and g <= 200 and b < 90 and r - b > 60


def fill_gelo(p):
    r, g, b, a = p
    return a > 128 and b > 150 and b - r > 100 and b - g > 60


ARROW_SIZE = (32, 32)        # a setinha
FUEL_SIZE = (72, 266)        # a barra vertical de abastecimento

MACHINES = {
    "lava": {"prefix": "incubator", "frames": "frames", "fill": fill_lava,
             "tile": {"en_US.lang": "Incubator", "pt_BR.lang": "Incubadora"}},
    "gelo": {"prefix": "ice_incubator", "frames": "frames_ice", "fill": fill_gelo,
             "tile": {"en_US.lang": "Ice Incubator", "pt_BR.lang": "Incubadora de Gelo"}},
}

LANG = {
    "en_US.lang": {"fuel": "Lava", "fuel_gelo": "Water", "arrow": "Progress",
                   "egg": "Skrill Egg", "egg_hatched": "Hatched Skrill Egg",
                   "main_altar": "Main Altar", "secondary_altar": "Secondary Altar",
                   "catalyst": "Empty Catalyst", "catalyst_charged": "Charged Catalyst",
                   "base_crystal": "Base Crystal"},
    "pt_BR.lang": {"fuel": "Lava", "fuel_gelo": "Agua", "arrow": "Progresso",
                   "egg": "Ovo de Skrill", "egg_hatched": "Ovo de Skrill Chocado",
                   "main_altar": "Altar Principal", "secondary_altar": "Altar Secundario",
                   "catalyst": "Catalisador Vazio", "catalyst_charged": "Catalisador Carregado",
                   "base_crystal": "Cristal Base"},
}

# Itens que nao sao barra mas moram no mesmo item_texture.json. Sem isto o
# regenerate() aqui embaixo apagaria eles toda vez que rodasse - foi o que
# deixou o cristal base sem textura na 1.20.0.
ITENS_FIXOS = {
    "sallytek:base_crystal": "textures/items/base_crystal",
}

# is_fill vira o teste da maquina que esta sendo instalada no momento
is_fill = fill_lava


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
        # prefix ja vem com a serie junto ("incubator_arrow"), e
        # "ice_incubator_arrow_0.png" nao comeca com "incubator_arrow_",
        # entao limpar uma maquina nunca leva a outra.
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
def contagem(prefix, serie):
    """Quantos quadros <prefix>_<serie>_N.png existem hoje no resource pack."""
    n = 0
    while os.path.exists(os.path.join(TEX_DIR, f"{prefix}_{serie}_{n}.png")):
        n += 1
    return n


def regenerate():
    """Reescreve itens-display, item_texture, idiomas e main.js pras DUAS
    maquinas, sempre a partir do que esta gravado em textures/items."""
    shutil.rmtree(ITEMS_DIR, ignore_errors=True)
    os.makedirs(ITEMS_DIR, exist_ok=True)

    tex = {"texture_name": "atlas.items", "resource_pack_name": "sallytek_incubator",
           "texture_data": {k: {"textures": v} for k, v in ITENS_FIXOS.items()}}
    conta = {}
    for maq, cfg in MACHINES.items():
        pref = cfg["prefix"]
        conta[maq] = {serie: contagem(pref, serie) for serie in ("fuel", "arrow")}
        for serie, count in conta[maq].items():
            for i in range(count):
                name = f"{pref}_{serie}_{i}"
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
            f"tile.sallytek:incubator.name={MACHINES['lava']['tile'][fn]}",
            f"tile.sallytek:ice_incubator.name={MACHINES['gelo']['tile'][fn]}",
            f"tile.sallytek:skrill_egg.name={t['egg']}",
            f"tile.sallytek:skrill_egg_hatched.name={t['egg_hatched']}",
            f"tile.sallytek:main_altar.name={t['main_altar']}",
            f"tile.sallytek:secondary_altar.name={t['secondary_altar']}",
            f"tile.sallytek:catalyst.name={t['catalyst']}",
            f"tile.sallytek:catalyst_charged.name={t['catalyst_charged']}",
            f"item.sallytek:base_crystal={t['base_crystal']}",
            "",
            "## titulo do container (apelido da entidade invisivel)",
            f"sallytek.incubator.block={MACHINES['lava']['tile'][fn]}",
            f"sallytek.ice_incubator.block={MACHINES['gelo']['tile'][fn]}",
            "",
            "## itens-display das barras",
        ]
        for maq, cfg in MACHINES.items():
            pref = cfg["prefix"]
            rotulo = t["fuel_gelo"] if maq == "gelo" else t["fuel"]
            lines += [f"item.sallytek:{pref}_fuel_{i}={rotulo}" for i in range(conta[maq]["fuel"])]
            lines += [f"item.sallytek:{pref}_arrow_{i}={t['arrow']}" for i in range(conta[maq]["arrow"])]
        with open(os.path.join(RP, "texts", fn), "w") as f:
            f.write("\n".join(lines) + "\n")

    # a tabela MACHINES do script: 1 balde = 1 ponto, entao a capacidade e
    # quadros - 1 (o quadro 0 e o tanque vazio)
    src = open(MAIN_JS).read()
    for maq in MACHINES:
        src = re.sub(rf"arrowStages: \d+,(\s*// ARROW_STAGES {maq})",
                     rf"arrowStages: {conta[maq]['arrow']},\1", src)
        src = re.sub(rf"fuelPoints: \d+,(\s*// FUEL_POINTS {maq})",
                     rf"fuelPoints: {conta[maq]['fuel'] - 1},\1", src)
    open(MAIN_JS, "w").write(src)
    return conta


def instala_maquina(maq, pasta):
    global is_fill
    cfg = MACHINES[maq]
    is_fill = cfg["fill"]
    arrows, fuel, ignored = collect(pasta)
    if not arrows and not fuel:
        print(f"[{maq}] nenhuma textura reconhecida em {pasta}")
        return None
    n_arrow, arrow_novo = install(arrows, cfg["prefix"] + "_arrow", *ARROW_SIZE) if arrows else (0, False)
    n_fuel, fuel_novo = install(fuel, cfg["prefix"] + "_fuel", *FUEL_SIZE) if fuel else (0, False)
    print(f"[{maq}] setinha: {n_arrow} quadros"
          + ("  (estagio 0 vazio gerado aqui)" if arrow_novo else ""))
    for i, (c, name, *_ ) in enumerate(arrows):
        print(f"   {cfg['prefix']}_arrow_{i + (1 if arrow_novo else 0)} <- {name}  ({c} px cheios)")
    print(f"[{maq}] abastecimento: {n_fuel} quadros -> capacidade {n_fuel - 1} baldes"
          + ("  (estagio 0 vazio gerado aqui)" if fuel_novo else ""))
    for i, (c, name, *_ ) in enumerate(fuel):
        print(f"   {cfg['prefix']}_fuel_{i + (1 if fuel_novo else 0)} <- {name}  ({c} px cheios)")
    for name, motivo in ignored:
        print(f"   ignorado: {name} - {motivo}")
    return n_arrow, n_fuel


def main():
    if len(sys.argv) == 1:
        alvos = [(maq, os.path.join(ROOT, "tools", cfg["frames"]))
                 for maq, cfg in MACHINES.items()]
    elif len(sys.argv) == 3 and sys.argv[2] in MACHINES:
        alvos = [(sys.argv[2], sys.argv[1])]
    else:
        print(__doc__)
        return 2

    for maq, pasta in alvos:
        if instala_maquina(maq, pasta) is None:
            return 1
    conta = regenerate()
    print()
    for maq, c in conta.items():
        print(f"{maq}: {c['arrow']} quadros de setinha, {c['fuel']} de abastecimento "
              f"-> tanque de {c['fuel'] - 1} baldes")
    return 0


sys.exit(main())
