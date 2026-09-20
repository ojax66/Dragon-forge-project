#!/usr/bin/env python3
"""Prepara as geometrias dos altares e do catalisador.

Os tres arquivos saem do Blockbench com o identificador `geometry.unknown`.
Se forem pro pacote assim, um sobrescreve o outro - entao a unica coisa que
este script muda neles e o identificador. Cubo nenhum e tocado.

Saem daqui:

  models/blocks/main_altar.geo.json       geometry.main_altar
  models/blocks/secondary_altar.geo.json  geometry.secondary_altar
  models/entity/catalyst.geo.json         geometry.catalyst
  models/blocks/catalyst_item.geo.json    geometry.catalyst_item

O ultimo e o unico com mais do que o identificador mudado, por duas razoes:

1. Geometria de BLOCO nao aceita osso com `parent`, e o catalisador tem tres.
   So que os quatro ossos dele nao tem rotacao propria - a hierarquia so existe
   pra animacao mexer em cada anel separado -, entao juntar todos os cubos num
   osso so da exatamente o mesmo desenho parado.
2. O modelo tem 5x7.8x2 px, ou seja um terco do cubo do bloco: no inventario
   ele saia minusculo. O icone e escalado pra encostar nas paredes do bloco.
   Escala uniforme nao mexe em angulo nenhum, entao o desenho e o mesmo, so
   maior - e isso vale so pro icone; quem anima e a entidade, que usa o arquivo
   original, do tamanho original.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tools", "altar_originals")
RP = os.path.join(ROOT, "Incubadora [RP] - SallyTek Studio")


def escreve(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent="\t")
        f.write("\n")


def com_identificador(origem, ident):
    d = json.load(open(origem))
    d["minecraft:geometry"][0]["description"]["identifier"] = ident
    return d


BLOCO = 16.0


def caixa(cubos):
    lo, hi = [1e9] * 3, [-1e9] * 3
    for c in cubos:
        o, s, inf = c["origin"], c["size"], c.get("inflate", 0)
        for i in range(3):
            lo[i] = min(lo[i], o[i] - inf)
            hi[i] = max(hi[i], o[i] + s[i] + inf)
    return lo, hi


def achatado(origem, ident):
    """Todos os cubos num osso so, escalados pra encher o cubo do bloco.

    Achatar so vale porque nenhum osso gira sozinho; escalar so mexe em
    tamanho, nunca em angulo, entao o desenho continua o mesmo.
    """
    d = json.load(open(origem))
    g = d["minecraft:geometry"][0]
    for b in g["bones"]:
        if b.get("rotation"):
            raise SystemExit(f"osso {b['name']} tem rotacao propria - achatar mudaria o desenho")
    cubos = [c for b in g["bones"] for c in b.get("cubes", [])]

    lo, hi = caixa(cubos)
    escala = min(BLOCO / (hi[i] - lo[i]) for i in range(3))
    # centraliza em x e z, apoia em y = 0
    desl = [-((lo[0] + hi[0]) / 2) * escala, -lo[1] * escala, -((lo[2] + hi[2]) / 2) * escala]

    def move(p):
        return [round(v * escala + desl[i], 4) for i, v in enumerate(p)]

    for c in cubos:
        c["origin"] = move(c["origin"])
        c["size"] = [round(v * escala, 4) for v in c["size"]]
        if "pivot" in c:
            c["pivot"] = move(c["pivot"])
        if "inflate" in c:
            c["inflate"] = round(c["inflate"] * escala, 4)

    g["description"]["identifier"] = ident
    g["description"]["visible_bounds_width"] = 2
    g["description"]["visible_bounds_height"] = 2
    g["description"]["visible_bounds_offset"] = [0, 0.5, 0]
    g["bones"] = [{"name": "item", "pivot": [0, 0, 0], "cubes": cubos}]
    return d, len(cubos), escala, caixa(cubos)


def main():
    saidas = [
        ("Altar_principal_final.geo.json", "geometry.main_altar",
         os.path.join(RP, "models", "blocks", "main_altar.geo.json")),
        ("Altar_secundario_final.geo.json", "geometry.secondary_altar",
         os.path.join(RP, "models", "blocks", "secondary_altar.geo.json")),
        ("Catalizador_final.geo.json", "geometry.catalyst",
         os.path.join(RP, "models", "entity", "catalyst.geo.json")),
    ]
    for arq, ident, dst in saidas:
        origem = os.path.join(SRC, arq)
        escreve(dst, com_identificador(origem, ident))
        print(f"{ident:28s} <- {arq}  (so o identificador mudou)")

    origem = os.path.join(SRC, "Catalizador_final.geo.json")
    d, n, escala, (lo, hi) = achatado(origem, "geometry.catalyst_item")
    escreve(os.path.join(RP, "models", "blocks", "catalyst_item.geo.json"), d)
    print(f"{'geometry.catalyst_item':28s} <- os mesmos {n} cubos, num osso so, "
          f"escala {escala:.3f} (icone do item)")
    print(f"{'':28s}    agora ocupa "
          f"{[round(hi[i] - lo[i], 2) for i in range(3)]} do cubo de 16")
    return 0


sys.exit(main())
