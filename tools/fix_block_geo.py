"""Deixa o modelo do bloco dentro das regras de geometria de bloco do Bedrock.

O modelo veio autorado como modelo de ENTIDADE: 24 cubos com rotacao livre nos
tres eixos e UVs passando de 64px. Geometria de BLOCO so aceita rotacao em um
eixo, em passos de 22.5 graus. Modelo recusado = bloco invisivel.

Este script:
  - reduz cada rotacao ao eixo dominante e arredonda pro passo de 22.5;
  - encaixa as UVs por face dentro da textura de 64x64;
  - confere os limites documentados (+-30px do centro da base, e pelo menos
    1px dentro do bloco base).

O original fica em tools/incubator_original.geo.json.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tools", "incubator_original.geo.json")
DST = os.path.join(ROOT, "Incubadora [RP] - SallyTek Studio", "models", "blocks", "incubator.geo.json")
STEP = 22.5
LIMIT = 30.0


def snap(angle):
    return round(angle / STEP) * STEP


def fix_rotation(rot):
    """Mantem so o eixo de maior angulo, arredondado pro passo valido."""
    axis = max(range(3), key=lambda i: abs(rot[i]))
    out = [0.0, 0.0, 0.0]
    out[axis] = snap(rot[axis])
    return out, axis


def main():
    d = json.load(open(SRC))
    g = d["minecraft:geometry"][0]
    tw = g["description"].get("texture_width", 64)
    th = g["description"].get("texture_height", 64)

    rot_fixed = rot_dropped = uv_fixed = 0

    for bone in g["bones"]:
        if bone.get("rotation"):
            bone["rotation"], _ = fix_rotation(bone["rotation"])
        for cube in bone.get("cubes", []):
            rot = cube.get("rotation")
            if rot:
                new, _ = fix_rotation(rot)
                if all(abs(v) < 1e-9 for v in new):
                    cube.pop("rotation", None)
                    cube.pop("pivot", None)
                    rot_dropped += 1
                else:
                    cube["rotation"] = new
                    rot_fixed += 1

            uv = cube.get("uv")
            if isinstance(uv, dict):
                for face in uv.values():
                    u = face.get("uv")
                    us = face.get("uv_size")
                    if not (u and us):
                        continue
                    # uv_size negativo espelha a face: preserva o sinal
                    for i, (size, span) in enumerate(((tw, us[0]), (th, us[1]))):
                        lo = min(u[i], u[i] + span)
                        hi = max(u[i], u[i] + span)
                        if hi > size:
                            u[i] -= hi - size
                            uv_fixed += 1
                        if lo < 0:
                            u[i] -= lo
                            uv_fixed += 1

    # confere os limites de geometria de bloco
    lo = [1e9] * 3
    hi = [-1e9] * 3
    for bone in g["bones"]:
        for cube in bone.get("cubes", []):
            o, s = cube["origin"], cube["size"]
            infl = cube.get("inflate", 0)
            for i in range(3):
                lo[i] = min(lo[i], o[i] - infl)
                hi[i] = max(hi[i], o[i] + s[i] + infl)

    problemas = []
    for i, ax in enumerate("XYZ"):
        if lo[i] < -LIMIT or hi[i] > LIMIT:
            problemas.append(f"{ax} fora de +-{LIMIT}: {lo[i]}..{hi[i]}")
    # pelo menos 1px dentro do bloco base
    base = [(-8, 8), (0, 16), (-8, 8)]
    for i, ax in enumerate("XYZ"):
        if hi[i] <= base[i][0] or lo[i] >= base[i][1]:
            problemas.append(f"{ax} nao encosta no bloco base")

    json.dump(d, open(DST, "w"), indent="\t")
    open(DST, "a").write("\n")

    print(f"rotacoes reduzidas a um eixo: {rot_fixed}")
    print(f"rotacoes zeradas e removidas: {rot_dropped}")
    print(f"coordenadas de UV corrigidas: {uv_fixed}")
    print("bounding box final:", [(round(lo[i], 2), round(hi[i], 2)) for i in range(3)])
    print("limites de bloco:", "OK" if not problemas else "*** " + "; ".join(problemas))
    return 1 if problemas else 0


sys.exit(main())
