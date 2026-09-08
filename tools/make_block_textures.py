#!/usr/bin/env python3
"""Instala a textura da Incubadora e deriva dela a versao sem lava.

Uso:  python3 tools/make_block_textures.py <incubadora_com_lava.png>

O modelo tem um osso proprio (`water_and_lava`) so pra chapa de lava, e o autor
pinta uma textura so: a **com lava**. A versao apagada e a mesma arte com todo
pixel de lava em alpha 0 - foi assim que o par antigo do pacote foi feito, e o
script confere isso antes de gravar (`--conferir`).

Saem daqui:
  textures/blocks/incubator_lit.png     copia literal do arquivo passado
  textures/blocks/incubator_unlit.png   a mesma arte, sem os pixels de lava
"""
import os, shutil, struct, sys, zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "Incubadora [RP] - SallyTek Studio")
DST = os.path.join(RP, "textures", "blocks")

sys.path.insert(0, os.path.join(ROOT, "tools"))


def read_png(path):
    """PNG RGBA/paleta -> (w, h, [[[r,g,b,a], ...], ...])."""
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


def eh_lava(p):
    """Laranja de lava: e o unico laranja vivo que aparece na arte do bloco."""
    r, g, b, a = p
    return a > 0 and r > 200 and 80 <= g <= 170 and b < 60


def apaga_lava(px):
    return [[([0, 0, 0, 0] if eh_lava(p) else list(p)) for p in row] for row in px]


def confere(lit_path, unlit_path):
    """Prova que 'apagada = acesa sem os pixels de lava' e mesmo a regra."""
    w, h, lit = read_png(lit_path)
    _, _, unlit = read_png(unlit_path)
    derivada = apaga_lava(lit)
    dif = sum(1 for y in range(h) for x in range(w) if derivada[y][x] != unlit[y][x])
    total = w * h
    print(f"conferencia: derivar a apagada a partir da acesa erra em {dif}/{total} px")
    return dif


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    if sys.argv[1] == "--conferir":
        return 0 if confere(os.path.join(DST, "incubator_lit.png"),
                            os.path.join(DST, "incubator_unlit.png")) < 40 else 1

    src = sys.argv[1]
    w, h, px = read_png(src)
    os.makedirs(DST, exist_ok=True)
    shutil.copyfile(src, os.path.join(DST, "incubator_lit.png"))
    unlit = apaga_lava(px)
    write_png(os.path.join(DST, "incubator_unlit.png"), w, h, unlit)
    n = sum(1 for row in px for p in row if eh_lava(p))
    print(f"incubator_lit.png   <- {os.path.basename(src)} ({w}x{h}, copia literal)")
    print(f"incubator_unlit.png <- a mesma arte com {n} px de lava apagados")
    return 0


sys.exit(main())
