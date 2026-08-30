import json, os

RP = "/home/user/Dragon-forge-project/Incubadora [RP] - SallyTek Studio"
UI = os.path.join(RP, "ui")
os.makedirs(UI, exist_ok=True)

# Indices dos botoes do ActionFormData. Precisa bater com scripts/main.js.
I_FUEL, I_ARROW, I_INPUT, I_OUTPUT, I_CLOSE = 0, 1, 2, 3, 4
I_INV = 5            # slots 5..40 = inventario do jogador (36 slots)
INV_COLS, INV_ROWS = 9, 4
CELL = 18

PANEL_W, PANEL_H = 180, 182
GRID_X, GRID_Y = 9, 106


def icon(index, size, offset=(0, 0), layer=3):
    """Imagem que le a textura do botao `index` da colecao form_buttons."""
    return {
        "type": "image",
        "size": size,
        "offset": list(offset),
        "layer": layer,
        "collection_index": index,
        "bindings": [
            {
                "binding_name": "#form_button_texture",
                "binding_name_override": "#texture",
                "binding_type": "collection",
                "binding_collection_name": "form_buttons",
            },
            {
                "binding_name": "#form_button_texture_file_system",
                "binding_name_override": "#texture_file_system",
                "binding_type": "collection",
                "binding_collection_name": "form_buttons",
            },
            {
                "binding_type": "view",
                "source_property_name": "(not (#texture = ''))",
                "target_property_name": "#visible",
            },
        ],
    }


def slot(index, offset, size=(CELL, CELL), icon_inset=1, with_cell=True):
    """Celula clicavel ligada ao botao `index` do formulario."""
    ctrl = {
        "type": "panel",
        "size": list(size),
        "offset": list(offset),
        "anchor_from": "top_left",
        "anchor_to": "top_left",
        "controls": [],
    }
    if with_cell:
        ctrl["controls"].append({"cell": {
            "type": "image",
            "texture": "textures/ui/incubator_slot",
            "size": ["100%", "100%"],
            "layer": 1,
        }})
    ctrl["controls"].append({"item_icon": icon(
        index,
        [size[0] - icon_inset * 2, size[1] - icon_inset * 2],
        (icon_inset, icon_inset),
    )})
    ctrl["controls"].append({"hit@incubator.form_slot_button": {
        "$collection_index": index,
        "size": ["100%", "100%"],
        "layer": 4,
    }})
    return ctrl


# --------------------------------------------------------------- area da maquina
machine = {
    "type": "panel",
    "size": ["100%", 74],
    "offset": [0, 20],
    "anchor_from": "top_left",
    "anchor_to": "top_left",
    "controls": [
        # --- coluna do combustivel (barra de lava + slot do balde) -------------
        {"fuel_recess": {
            "type": "image",
            "texture": "textures/ui/incubator_recess",
            "size": [20, 50],
            "offset": [11, 0],
            "layer": 1,
            "anchor_from": "top_left",
            "anchor_to": "top_left",
        }},
        {"fuel_bar": {
            "type": "panel",
            "size": [16, 46],
            "offset": [13, 2],
            "anchor_from": "top_left",
            "anchor_to": "top_left",
            "controls": [
                {"bar": icon(I_FUEL, ["100%", "100%"], (0, 0), layer=2)},
                {"hit@incubator.form_slot_button": {
                    "$collection_index": I_FUEL,
                    "size": ["100%", "100%"],
                    "layer": 4,
                }},
            ],
        }},
        {"fuel_slot": slot(I_FUEL, (12, 52))},
        # --- slot de entrada ---------------------------------------------------
        {"input_slot": slot(I_INPUT, (48, 12))},
        # --- barra de progresso ------------------------------------------------
        {"arrow_recess": {
            "type": "image",
            "texture": "textures/ui/incubator_recess",
            "size": [20, 50],
            "offset": [82, 0],
            "layer": 1,
            "anchor_from": "top_left",
            "anchor_to": "top_left",
        }},
        {"arrow_bar": {
            "type": "panel",
            "size": [16, 46],
            "offset": [84, 2],
            "anchor_from": "top_left",
            "anchor_to": "top_left",
            "controls": [
                {"bar": icon(I_ARROW, ["100%", "100%"], (0, 0), layer=2)},
                {"hit@incubator.form_slot_button": {
                    "$collection_index": I_ARROW,
                    "size": ["100%", "100%"],
                    "layer": 4,
                }},
            ],
        }},
        # --- slot de saida (maior, como o da fornalha) -------------------------
        {"output_slot": slot(I_OUTPUT, (128, 16), size=(26, 26), icon_inset=4)},
    ],
}

# ------------------------------------------------------------ grade do inventario
grid_controls = []
for row in range(INV_ROWS):
    for col in range(INV_COLS):
        index = I_INV + row * INV_COLS + col
        grid_controls.append({
            "inv_slot_%d" % index: slot(index, (col * CELL, row * CELL))
        })

inventory = {
    "type": "panel",
    "size": [INV_COLS * CELL, INV_ROWS * CELL],
    "offset": [GRID_X, GRID_Y],
    "anchor_from": "top_left",
    "anchor_to": "top_left",
    "controls": grid_controls,
}

screen = {
    "namespace": "incubator",

    # Botao invisivel que dispara o clique de um botao do ActionFormData.
    "form_slot_button@common.button": {
        "$collection_index|default": 0,
        "collection_index": "$collection_index",
        "$pressed_button_name": "button.form_button_click",
        "$button_bindings": [
            {
                "binding_type": "collection_details",
                "binding_collection_name": "form_buttons",
            }
        ],
        "controls": [
            {"default": {"type": "panel", "size": ["100%", "100%"]}},
            {"hover": {
                "type": "image",
                "texture": "textures/ui/incubator_slot_hover",
                "size": ["100%", "100%"],
                    "alpha": 0.55,
            }},
            {"pressed": {
                "type": "image",
                "texture": "textures/ui/incubator_slot_hover",
                "size": ["100%", "100%"],
                    "alpha": 0.85,
            }},
        ],
    },

    # Tela custom da Incubadora, desenhada por cima do long_form.
    "screen": {
        "type": "panel",
        "size": [PANEL_W, PANEL_H],
        "anchor_from": "center",
        "anchor_to": "center",
        "controls": [
            {"background": {
                "type": "image",
                "texture": "textures/ui/incubator_bg_tile",
                "size": ["100% - 8px", "100% - 8px"],
                "offset": [4, 4],
                "anchor_from": "top_left",
                "anchor_to": "top_left",
                "tiled": True,
                "layer": 0,
            }},
            {"frame": {
                "type": "image",
                "texture": "textures/ui/incubator_frame",
                "size": ["100%", "100%"],
                "layer": 1,
            }},
            {"title": {
                "type": "label",
                "text": "sallytek.incubator.title",
                "color": [0.93, 0.82, 0.75],
                "shadow": True,
                "layer": 5,
                "offset": [0, 6],
                "anchor_from": "top_middle",
                "anchor_to": "top_middle",
            }},
            {"machine@incubator.machine": {"layer": 2}},
            {"inventory_label": {
                "type": "label",
                "text": "sallytek.incubator.inventory",
                "color": [0.93, 0.82, 0.75],
                "shadow": True,
                "layer": 5,
                "offset": [-10, 94],
                "anchor_from": "top_right",
                "anchor_to": "top_right",
            }},
            {"inventory@incubator.inventory_grid": {"layer": 2}},
            {"close@incubator.form_slot_button": {
                "$collection_index": I_CLOSE,
                "size": [12, 12],
                "offset": [-5, 5],
                "anchor_from": "top_right",
                "anchor_to": "top_right",
                "layer": 6,
                "controls": [
                    {"default": {
                        "type": "image",
                        "texture": "textures/ui/close_button_default_light",
                        "size": ["100%", "100%"],
                    }},
                    {"hover": {
                        "type": "image",
                        "texture": "textures/ui/close_button_hover_light",
                        "size": ["100%", "100%"],
                    }},
                    {"pressed": {
                        "type": "image",
                        "texture": "textures/ui/close_button_pressed",
                        "size": ["100%", "100%"],
                    }},
                ],
            }},
        ],
    },

    "machine": machine,
    "inventory_grid": inventory,
}

with open(os.path.join(UI, "incubator_screen.json"), "w") as f:
    json.dump(screen, f, indent=2)

# --------------------------------------------------------------- server_form.json
MARKER = "sallytek:incubator_ui"
server_form = {
    "namespace": "server_form",

    # Copia fiel do long_form original da Mojang, so que renomeada. Continua
    # sendo usada por qualquer outro ActionFormData do mundo.
    "vanilla_long_form@common_dialogs.main_panel_no_buttons": {
        "$title_panel": "common_dialogs.standard_title_label",
        "$title_size": ["100% - 15px", 10],
        "$title_max_size": ["100% - 15px", 10],
        "size": [225, 200],
        "$text_name": "#title_text",
        "$title_text_binding_type": "none",
        "$child_control": "server_form.long_form_panel",
    },

    # long_form vira um seletor: titulo marcado -> UI da Incubadora,
    # qualquer outro titulo -> formulario padrao.
    "long_form": {
        "type": "panel",
        "size": ["100%", "100%"],
        "layer": 2,
        "controls": [
            {"vanilla@server_form.vanilla_long_form": {
                "bindings": [
                    {"binding_name": "#title_text", "binding_name_override": "#title_text"},
                    {
                        "binding_type": "view",
                        "source_property_name": "(not (#title_text = '%s'))" % MARKER,
                        "target_property_name": "#visible",
                    },
                ],
            }},
            {"incubator@incubator.screen": {
                "layer": 3,
                "bindings": [
                    {"binding_name": "#title_text", "binding_name_override": "#title_text"},
                    {
                        "binding_type": "view",
                        "source_property_name": "(#title_text = '%s')" % MARKER,
                        "target_property_name": "#visible",
                    },
                ],
            }},
        ],
    },
}

with open(os.path.join(UI, "server_form.json"), "w") as f:
    json.dump(server_form, f, indent=2)

with open(os.path.join(UI, "_ui_defs.json"), "w") as f:
    json.dump({"ui_defs": ["ui/incubator_screen.json"]}, f, indent=2)

print("gerado:", sorted(os.listdir(UI)))
