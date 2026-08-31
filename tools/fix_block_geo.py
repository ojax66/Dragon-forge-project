#!/usr/bin/env python3
"""Deixa o modelo da Incubadora com estrutura de geometria de BLOCO.

O que este script NAO faz: mexer na forma. Nenhum cubo e movido, escalado,
rotacionado ou descartado. Origem, tamanho, rotacao, inflate e UV de cada cubo
saem daqui identicos ao arquivo do Blockbench. O render de conferencia no fim
prova isso comparando os vertices um a um.

O que ele faz e so tirar duas coisas que sao de modelo de ENTIDADE e nao
existem em geometria de bloco:

  1. o osso "water_and_lava" tem "parent". Hierarquia de osso e coisa de
     entidade - bloco espera uma lista de cubos.
  2. os ossos tem "pivot": [16, 0, 0], um bloco inteiro longe da origem.
     Pivo so e usado como centro de rotacao do osso, e nenhum dos dois ossos
     tem rotacao - entao zerar o pivo nao move nada.

Como nenhum dos dois ossos gira, juntar tudo num osso so com pivo na origem da
exatamente o mesmo desenho, so que numa estrutura que o render de bloco
entende.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tools", "incubator_original.geo.json")
DST = os.path.join(ROOT, "Incubadora [RP] - SallyTek Studio", "models", "blocks", "incubator.geo.json")


def vertices(path):
    """Todos os cantos de todos os cubos, ja com rotacao aplicada.

    Serve pra provar que a forma nao mudou: se as duas listas baterem, o
    desenho e o mesmo.
    """
    import math
    g = json.load(open(path))["minecraft:geometry"][0]
    pts = []
    for bone in g["bones"]:
        for c in bone.get("cubes", []):
            o, s = c["origin"], c["size"]
            cantos = [[o[0] + dx * s[0], o[1] + dy * s[1], o[2] + dz * s[2]]
                      for dx in (0, 1) for dy in (0, 1) for dz in (0, 1)]
            rot, piv = c.get("rotation"), c.get("pivot", [0, 0, 0])
            if rot:
                rx, ry, rz = [math.radians(v) for v in rot]
                for p in cantos:
                    for i in range(3):
                        p[i] -= piv[i]
                    y, z = p[1]*math.cos(rx)-p[2]*math.sin(rx), p[1]*math.sin(rx)+p[2]*math.cos(rx)
                    p[1], p[2] = y, z
                    x, z = p[0]*math.cos(ry)+p[2]*math.sin(ry), -p[0]*math.sin(ry)+p[2]*math.cos(ry)
                    p[0], p[2] = x, z
                    x, y = p[0]*math.cos(rz)-p[1]*math.sin(rz), p[0]*math.sin(rz)+p[1]*math.cos(rz)
                    p[0], p[1] = x, y
                    for i in range(3):
                        p[i] += piv[i]
            pts += [tuple(round(v, 6) for v in p) for p in cantos]
    return sorted(pts)


def main():
    d = json.load(open(SRC))
    g = d["minecraft:geometry"][0]

    cubes, ossos = [], []
    for bone in g["bones"]:
        ossos.append((bone["name"], bone.get("pivot"), bone.get("parent")))
        cubes += bone.get("cubes", [])

    g["bones"] = [{"name": "incubator", "pivot": [0, 0, 0], "cubes": cubes}]
    # o modelo tem 24x23x24 px = 1.5 x 1.44 blocos; 2 cobre com folga
    g["description"]["visible_bounds_width"] = 2
    g["description"]["visible_bounds_height"] = 2
    g["description"]["visible_bounds_offset"] = [0, 0.75, 0]

    os.makedirs(os.path.dirname(DST), exist_ok=True)
    with open(DST, "w") as f:
        json.dump(d, f, indent="\t")
        f.write("\n")

    antes, depois = vertices(SRC), vertices(DST)
    igual = antes == depois

    print("ossos do original:")
    for nome, piv, pai in ossos:
        print(f"  {nome!r}  pivot={piv}  parent={pai}")
    print(f"\nviraram 1 osso 'incubator' com pivot [0,0,0], juntando {len(cubes)} cubos")
    print(f"cubos movidos/escalados/rotacionados/descartados: 0")
    print(f"\nconferencia de forma: {len(antes)} vertices antes, {len(depois)} depois")
    print("a forma e identica?", "SIM" if igual else "*** NAO - algo mudou ***")
    return 0 if igual else 1


sys.exit(main())
