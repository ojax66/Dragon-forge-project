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

O ultimo e o unico com mais do que o identificador mudado: geometria de BLOCO
nao aceita osso com `parent`, e o catalisador tem tres. So que os quatro ossos
dele nao tem rotacao propria - a hierarquia so existe pra animacao mexer em
cada anel separado -, entao juntar todos os cubos num osso so da exatamente o
mesmo desenho parado. E o que o icone do item precisa; quem anima e a entidade,
que usa o arquivo original com os ossos.
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


def achatado(origem, ident):
    """Todos os cubos num osso so. So vale porque nenhum osso gira sozinho."""
    d = json.load(open(origem))
    g = d["minecraft:geometry"][0]
    for b in g["bones"]:
        if b.get("rotation"):
            raise SystemExit(f"osso {b['name']} tem rotacao propria - achatar mudaria o desenho")
    cubos = [c for b in g["bones"] for c in b.get("cubes", [])]
    g["description"]["identifier"] = ident
    g["bones"] = [{"name": "item", "pivot": [0, 0, 0], "cubes": cubos}]
    return d, len(cubos)


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
    d, n = achatado(origem, "geometry.catalyst_item")
    escreve(os.path.join(RP, "models", "blocks", "catalyst_item.geo.json"), d)
    print(f"{'geometry.catalyst_item':28s} <- os mesmos {n} cubos, num osso so (icone do item)")
    return 0


sys.exit(main())
