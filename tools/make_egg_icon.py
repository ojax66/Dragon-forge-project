#!/usr/bin/env python3
"""Gera a geometria do ICONE do ovo de Skrill, girada meia volta.

O Bedrock desenha o icone de um bloco customizado de um angulo fixo, olhando
pra face sul. Os espinhos do ovo apontam pro +z, que e justamente o sul, entao
no inventario eles ficavam virados pra camera, na frente do ovo - "ao
contrario". Colocado no mundo o modelo esta certo.

Como nao da pra dar um angulo so pro icone, o bloco ganhou o estado
`sallytek:placed`: em `false` (que e o estado do ITEM no inventario) ele usa a
geometria daqui, girada 180 graus em Y; o script liga `true` assim que o bloco
e colocado e a permutacao volta pro arquivo original, sem tocar em nada.

Girar meia volta em Y e exato, nao e aproximacao:
  ponto   (x, y, z)        -> (-x, y, -z)
  cubo    origin, size     -> origin.x vira -(origin.x + size.x), idem em z
  giro    (rx, ry, rz)     -> (-rx, ry, -rz)

A ultima linha sai de conjugar a rotacao do cubo pela matriz diag(-1, 1, -1):
ela troca o sinal de X e de Z e deixa Y quieto.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tools", "altar_originals", "skrill_egg_final.geo.json")
RP = os.path.join(ROOT, "Incubadora [RP] - SallyTek Studio")
DST = os.path.join(RP, "models", "blocks", "skrill_egg_item.geo.json")


def meia_volta(d, ident):
    g = d["minecraft:geometry"][0]
    for b in g["bones"]:
        if b.get("rotation"):
            raise SystemExit(f"osso {b['name']} tem rotacao propria - a conta abaixo nao serve")
        b["pivot"] = [-b["pivot"][0], b["pivot"][1], -b["pivot"][2]]
        for c in b.get("cubes", []):
            o, s = c["origin"], c["size"]
            c["origin"] = [round(-(o[0] + s[0]), 5), o[1], round(-(o[2] + s[2]), 5)]
            if "pivot" in c:
                p = c["pivot"]
                c["pivot"] = [round(-p[0], 5), p[1], round(-p[2], 5)]
            if "rotation" in c:
                r = c["rotation"]
                c["rotation"] = [round(-r[0], 5), r[1], round(-r[2], 5)]
    g["description"]["identifier"] = ident
    return d


def main():
    if not os.path.exists(SRC):
        print(f"falta {SRC}")
        return 1
    d = meia_volta(json.load(open(SRC)), "geometry.skrill_egg_item")
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    with open(DST, "w") as f:
        json.dump(d, f, indent="\t")
        f.write("\n")
    n = sum(len(b.get("cubes", [])) for b in d["minecraft:geometry"][0]["bones"])
    print(f"geometry.skrill_egg_item <- os mesmos {n} cubos, girados 180 graus em Y")
    return 0


sys.exit(main())
