#!/usr/bin/env python3
"""Adapta o modelo da Incubadora as regras de geometria de BLOCO do Bedrock.

O arquivo do Blockbench (tools/incubator_original.geo.json) foi autorado como
modelo de ENTIDADE: 24x23x24 px, ou seja uma vez e meia o cubo do bloco, e 24
cubos com rotacao livre nos tres eixos. Geometria de bloco e bem mais apertada:

  - o modelo tem que caber no cubo do bloco pra nunca esbarrar em regra de
    tamanho, corte de face ou culling de chunk;
  - rotacao de cubo so vale em UM eixo, em passo de 22.5 graus.

Este script gera a versao de bloco a partir do original:

  1. escala tudo por igual ate caber em 16x16x16 e assenta a base no y=0;
  2. reduz cada rotacao ao eixo de maior angulo, arredondado pro passo valido;
  3. ajusta visible_bounds pro tamanho novo;
  4. confere no fim que nada ficou fora das regras.

As UVs nao mudam: sao coordenadas de textura, nao de espaco.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tools", "incubator_original.geo.json")
DST = os.path.join(ROOT, "Incubadora [RP] - SallyTek Studio", "models", "blocks", "incubator.geo.json")

STEP = 22.5          # passo de rotacao aceito em geometria de bloco
BLOCK = 16.0         # o cubo do bloco
R = 5                # casas decimais na saida


def bounds(g):
    lo, hi = [1e9] * 3, [-1e9] * 3
    for bone in g["bones"]:
        for c in bone.get("cubes", []):
            o, s, inf = c["origin"], c["size"], c.get("inflate", 0)
            for i in range(3):
                lo[i] = min(lo[i], o[i] - inf)
                hi[i] = max(hi[i], o[i] + s[i] + inf)
    return lo, hi


def snap_rotation(rot):
    """Deixa so o eixo de maior angulo, arredondado pro passo de 22.5."""
    axis = max(range(3), key=lambda i: abs(rot[i]))
    out = [0.0, 0.0, 0.0]
    out[axis] = round(rot[axis] / STEP) * STEP
    return out


def main():
    d = json.load(open(SRC))
    g = d["minecraft:geometry"][0]

    lo, hi = bounds(g)
    tamanho = [hi[i] - lo[i] for i in range(3)]
    escala = min(BLOCK / t for t in tamanho)
    # depois de escalar, encosta a base no chao do bloco e centra em X/Z
    desloca = [
        -((lo[0] + hi[0]) / 2) * escala,
        -lo[1] * escala,
        -((lo[2] + hi[2]) / 2) * escala,
    ]

    girados = 0
    for bone in g["bones"]:
        if "pivot" in bone:
            bone["pivot"] = [round(v * escala + desloca[i], R) for i, v in enumerate(bone["pivot"])]
        if bone.get("rotation"):
            bone["rotation"] = snap_rotation(bone["rotation"])
        for c in bone.get("cubes", []):
            c["origin"] = [round(v * escala + desloca[i], R) for i, v in enumerate(c["origin"])]
            c["size"] = [round(v * escala, R) for v in c["size"]]
            if "pivot" in c:
                c["pivot"] = [round(v * escala + desloca[i], R) for i, v in enumerate(c["pivot"])]
            if "inflate" in c:
                c["inflate"] = round(c["inflate"] * escala, R)
            if c.get("rotation"):
                c["rotation"] = snap_rotation(c["rotation"])
                girados += 1

    lo2, hi2 = bounds(g)
    g["description"]["visible_bounds_width"] = 2
    g["description"]["visible_bounds_height"] = 2
    g["description"]["visible_bounds_offset"] = [0, 0.5, 0]

    problemas = []
    limites = ((-8, 8), (0, 16), (-8, 8))
    for i, ax in enumerate("XYZ"):
        if lo2[i] < limites[i][0] - 0.01 or hi2[i] > limites[i][1] + 0.01:
            problemas.append(f"{ax} fora do cubo do bloco: {lo2[i]:.3f}..{hi2[i]:.3f}")
    for bone in g["bones"]:
        for c in bone.get("cubes", []):
            r = c.get("rotation")
            if r and (sum(1 for v in r if abs(v) > 1e-9) > 1 or any(abs(v) % STEP > 1e-9 for v in r)):
                problemas.append(f"rotacao invalida: {r}")

    os.makedirs(os.path.dirname(DST), exist_ok=True)
    with open(DST, "w") as f:
        json.dump(d, f, indent="\t")
        f.write("\n")

    print(f"escala aplicada: {escala:.4f}  (o modelo tinha "
          f"{tamanho[0]:.1f} x {tamanho[1]:.1f} x {tamanho[2]:.1f} px)")
    print(f"rotacoes reduzidas a um eixo: {girados}")
    print("bounding box final:")
    for i, ax in enumerate("XYZ"):
        print(f"  {ax}: {lo2[i]:7.3f} .. {hi2[i]:7.3f}")
    print("regras de geometria de bloco:", "OK" if not problemas else "*** " + "; ".join(problemas))
    return 1 if problemas else 0


sys.exit(main())
