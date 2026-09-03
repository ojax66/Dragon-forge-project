#!/usr/bin/env python3
"""Prepara as geometrias da Incubadora a partir do arquivo do Blockbench.

O modelo original (tools/incubator_original.geo.json) e um modelo de ENTIDADE:
24 cubos com rotacao livre nos tres eixos, dois ossos com hierarquia e 24x23x24
px de tamanho. Nada disso vale em geometria de BLOCO, e tudo isso vale em
entidade. Por isso quem desenha o modelo original e a entidade que ja vive
dentro do bloco - e ela desenha o arquivo *sem tocar em um cubo*.

Saem daqui tres geometrias:

  models/entity/incubator.geo.json   copia literal do original, byte a byte.
                                     E o que a entidade renderiza no mundo.

  models/blocks/incubator_item.geo.json
                                     versao dentro das regras de bloco, usada
                                     SO pelo icone do item no inventario: os 29
                                     cubos sem rotacao, escalados pra caber em
                                     16x16x16. Nunca aparece no mundo.

  models/blocks/incubator_empty.geo.json
                                     geometria vazia. E o que o bloco vira
                                     depois de colocado, pra nao brigar com o
                                     modelo da entidade.
"""
import json, os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tools", "incubator_original.geo.json")
RP = os.path.join(ROOT, "Incubadora [RP] - SallyTek Studio")
DST_ENTITY = os.path.join(RP, "models", "entity", "incubator.geo.json")
DST_ITEM = os.path.join(RP, "models", "blocks", "incubator_item.geo.json")
DST_EMPTY = os.path.join(RP, "models", "blocks", "incubator_empty.geo.json")
ANTIGO = os.path.join(RP, "models", "blocks", "incubator.geo.json")

BLOCK = 16.0


def escreve(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent="\t")
        f.write("\n")


def caixa(cubes):
    lo, hi = [1e9] * 3, [-1e9] * 3
    for c in cubes:
        o, s, inf = c["origin"], c["size"], c.get("inflate", 0)
        for i in range(3):
            lo[i] = min(lo[i], o[i] - inf)
            hi[i] = max(hi[i], o[i] + s[i] + inf)
    return lo, hi


def main():
    # 1) o que a entidade renderiza: o original, copiado sem tocar
    os.makedirs(os.path.dirname(DST_ENTITY), exist_ok=True)
    shutil.copyfile(SRC, DST_ENTITY)
    identico = open(SRC, "rb").read() == open(DST_ENTITY, "rb").read()

    d = json.load(open(SRC))
    g = d["minecraft:geometry"][0]
    total = sum(len(b.get("cubes", [])) for b in g["bones"])

    # 2) icone do item: so os cubos sem rotacao, encaixados no cubo do bloco
    item = json.loads(json.dumps(d))
    gi = item["minecraft:geometry"][0]
    cubes = [c for b in gi["bones"] for c in b.get("cubes", []) if not c.get("rotation")]
    for c in cubes:
        c.pop("pivot", None)
    lo, hi = caixa(cubes)
    escala = min(BLOCK / (hi[i] - lo[i]) for i in range(3))
    desl = [-((lo[0] + hi[0]) / 2) * escala, -lo[1] * escala, -((lo[2] + hi[2]) / 2) * escala]
    for c in cubes:
        c["origin"] = [round(v * escala + desl[i], 3) for i, v in enumerate(c["origin"])]
        c["size"] = [round(v * escala, 3) for v in c["size"]]
        if "inflate" in c:
            c["inflate"] = round(c["inflate"] * escala, 3)
    gi["description"]["identifier"] = "geometry.incubator_item"
    gi["description"]["visible_bounds_width"] = 2
    gi["description"]["visible_bounds_height"] = 2
    gi["description"]["visible_bounds_offset"] = [0, 0.5, 0]
    gi["bones"] = [{"name": "item", "pivot": [0, 0, 0], "cubes": cubes}]
    escreve(DST_ITEM, item)

    # 3) geometria vazia pro bloco depois de colocado
    escreve(DST_EMPTY, {
        "format_version": "1.12.0",
        "minecraft:geometry": [{
            "description": {
                "identifier": "geometry.incubator_empty",
                "texture_width": 16,
                "texture_height": 16,
                "visible_bounds_width": 1,
                "visible_bounds_height": 1,
                "visible_bounds_offset": [0, 0.5, 0],
            },
            "bones": [{"name": "vazio", "pivot": [0, 0, 0]}],
        }],
    })

    if os.path.exists(ANTIGO):
        os.remove(ANTIGO)

    lo2, hi2 = caixa(cubes)
    print(f"entidade : models/entity/incubator.geo.json")
    print(f"           copia literal do original ({total} cubos) - identica? "
          f"{'SIM' if identico else '*** NAO ***'}")
    print(f"icone    : models/blocks/incubator_item.geo.json  ({len(cubes)} cubos, escala {escala:.4f})")
    print(f"           caixa {[(round(lo2[i],2), round(hi2[i],2)) for i in range(3)]}")
    print(f"vazia    : models/blocks/incubator_empty.geo.json")
    return 0 if identico else 1


sys.exit(main())
