#!/usr/bin/env python3
"""Reconstroi o modelo da Incubadora como geometria de BLOCO valida.

O arquivo do Blockbench (tools/incubator_original.geo.json) foi autorado como
modelo de ENTIDADE, e traz quatro coisas que geometria de bloco nao digere:

  1. dois ossos, um deles com "parent" - hierarquia de osso e coisa de
     entidade; em bloco o modelo tem que ser uma lista de cubos e ponto;
  2. "pivot": [16, 0, 0] nos ossos, ou seja pivo a um bloco inteiro da
     origem do bloco;
  3. 24 cubos com rotacao livre nos tres eixos - bloco so aceita rotacao em
     um eixo, em passo de 22.5 graus;
  4. 24x23x24 px de tamanho, uma vez e meia o cubo do bloco.

Este script resolve os quatro de uma vez:

  - junta tudo num unico osso, sem parent e com pivot na origem;
  - descarta os cubos rotacionados (as labaredas decorativas), em vez de
    tentar arredondar a rotacao - arredondar ja foi tentado e nao resolveu;
  - escala o que sobrou ate caber em 16x16x16 e assenta a base no y=0;
  - arredonda as coordenadas, pra nao ficar lixo de ponto flutuante.

As UVs nao mudam: sao coordenadas de textura, entao a pintura continua caindo
exatamente onde o modelo original mandava.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tools", "incubator_original.geo.json")
DST = os.path.join(ROOT, "Incubadora [RP] - SallyTek Studio", "models", "blocks", "incubator.geo.json")

BLOCK = 16.0
R = 3


def caixa(cubes):
    lo, hi = [1e9] * 3, [-1e9] * 3
    for c in cubes:
        o, s, inf = c["origin"], c["size"], c.get("inflate", 0)
        for i in range(3):
            lo[i] = min(lo[i], o[i] - inf)
            hi[i] = max(hi[i], o[i] + s[i] + inf)
    return lo, hi


def main():
    d = json.load(open(SRC))
    g = d["minecraft:geometry"][0]

    # 1) junta os ossos e joga fora os cubos rotacionados
    cubes, descartados = [], 0
    for bone in g["bones"]:
        for c in bone.get("cubes", []):
            if c.get("rotation"):
                descartados += 1
                continue
            c.pop("pivot", None)
            cubes.append(c)

    # 2) escala pra caber no cubo do bloco e assenta no chao
    lo, hi = caixa(cubes)
    tam = [hi[i] - lo[i] for i in range(3)]
    escala = min(BLOCK / t for t in tam)
    desloca = [
        -((lo[0] + hi[0]) / 2) * escala,
        -lo[1] * escala,
        -((lo[2] + hi[2]) / 2) * escala,
    ]
    for c in cubes:
        c["origin"] = [round(v * escala + desloca[i], R) for i, v in enumerate(c["origin"])]
        c["size"] = [round(v * escala, R) for v in c["size"]]
        if "inflate" in c:
            c["inflate"] = round(c["inflate"] * escala, R)

    # 3) um osso so, sem parent, pivo na origem
    g["bones"] = [{"name": "incubator", "pivot": [0, 0, 0], "cubes": cubes}]
    g["description"]["visible_bounds_width"] = 2
    g["description"]["visible_bounds_height"] = 2
    g["description"]["visible_bounds_offset"] = [0, 0.5, 0]

    lo2, hi2 = caixa(cubes)
    problemas = []
    limites = ((-8, 8), (0, 16), (-8, 8))
    for i, ax in enumerate("XYZ"):
        if lo2[i] < limites[i][0] - 0.01 or hi2[i] > limites[i][1] + 0.01:
            problemas.append(f"{ax} fora do cubo do bloco: {lo2[i]:.3f}..{hi2[i]:.3f}")
    for c in cubes:
        if c.get("rotation"):
            problemas.append("sobrou cubo com rotacao")
        if any(v <= 0 for v in c["size"]):
            problemas.append(f"cubo com tamanho zero/negativo: {c['size']}")

    os.makedirs(os.path.dirname(DST), exist_ok=True)
    with open(DST, "w") as f:
        json.dump(d, f, indent="\t")
        f.write("\n")

    print(f"cubos mantidos: {len(cubes)}   descartados por rotacao: {descartados}")
    print(f"ossos: 1 (sem parent, pivot na origem)")
    print(f"escala: {escala:.4f}")
    print("bounding box final:", [(round(lo2[i], 2), round(hi2[i], 2)) for i in range(3)])
    print("regras de geometria de bloco:", "OK" if not problemas else "*** " + "; ".join(problemas))
    return 1 if problemas else 0


sys.exit(main())
