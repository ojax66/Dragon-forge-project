# Incubadora Funcional — SallyTek Studio / Dragon Forge

Add-on de Minecraft Bedrock com o bloco `sallytek:incubator`, que funciona como
uma fornalha: você põe um item pra chocar, abastece com balde de lava e o
progresso corre até sair o resultado.

```
Incubadora [BP] - SallyTek Studio/   behavior pack (bloco + script)
Incubadora [RP] - SallyTek Studio/   resource pack (modelo, texturas e UI)
```

## Como a interface foi feita

Nesta versão do jogo **bloco customizado ainda não tem container próprio** — não
existe componente `minecraft:inventory` de bloco no schema. A saída é a que
funciona desde sempre: o inventário mora numa **entidade invisível** colocada
dentro do bloco, e a tela de contêiner dela é remodelada por JSON UI.

1. Ao colocar o bloco, o script invoca `sallytek:incubator` (entidade) no lugar,
   com o nome `sallytek.incubator.block`. Esse nome vira o **título do
   contêiner**.
2. `ui/chest_screen.json` usa `modifications` pra inserir uma variante de
   `small_chest_screen` que só vale quando
   `$new_container_title = 'sallytek.incubator.block'`. Aí o `$screen_content`
   aponta pra tela da Incubadora. Qualquer outro baú do mundo continua igual —
   nada de vanilla é redefinido.
3. `ui/incubator_screen.json` desenha a metade de cima (as 5 células da máquina
   posicionadas sobre `textures/ui/incubator_gui`), e a metade de baixo reusa
   `common.inventory_panel_bottom_half` + `common.hotbar_grid_template`, que é o
   inventário real do jogador.

Como são slots de contêiner de verdade, **arrastar, clicar e shift-clicar
funcionam** e a tela atualiza sozinha.

### As barras são itens

Não dá pra mandar um número pro cliente dentro de um contêiner — só itens. Então
as barras são itens-display (`sallytek:incubator_fuel_0..10` e
`sallytek:incubator_arrow_0..6`, definidos em `items/display/`) que o script
troca a cada segundo no slot correspondente. O JSON UI só desenha o ícone do item
com `$cell_image_size` zerado e um renderizador alto, e o resultado é uma barra
que anima.

### Ordem dos slots

`scripts/main.js` e a grade de `ui/incubator_screen.json` compartilham esta
ordem — mexeu em um, mexa no outro:

| índice | slot |
|---|---|
| 0 | barra de lava (item-display) |
| 1 | balde de lava |
| 2 | entrada |
| 3 | barra de progresso (item-display) |
| 4 | saída |

### Coordenadas

A tela tem 200x200. A metade de baixo é posicionada pelo Bedrock, não por nós:
a grade do inventário fica em (19, 120) e a hotbar em (19, 177), células de 18px
— `(200-162)/2` na horizontal, `200-26-54` e `200-5-18` na vertical.
`tools/gen_gui_texture.py` desenha o fundo já com essas células no lugar; se
mudar o tamanho da tela, mude lá também.

As células cinza da vanilla são escondidas com
`"$background_images": "common.empty_panel"` (na metade de baixo e nos slots
próprios), então o que aparece é a arte vermelha do fundo. **Não** zere
`$cell_image_size` pra isso: o `item_cell` usa esse valor como tamanho, e zerá-lo
desalinha o item dentro do slot.

Os dois slots de barra levam `"$button_ref": "common.empty_panel"`. Sem botão,
o jogador não consegue tirar o item-display do lugar — as barras não são itens
que dá pra pegar.

## Como usar no jogo

Clique no bloco pra abrir. Balde de lava no slot da esquerda, item pra chocar no
slot de cima, resultado sai no slot da direita. Pra quebrar o bloco, **agache** —
a entidade encolhe a hitbox quando você agacha, liberando o bloco atrás dela.

Receitas ficam em `HATCH_RECIPES` no `scripts/main.js`.

## Compatibilidade

Alvo: **Minecraft Bedrock 1.26.40+** (testado como alvo do 1.26.45).

O ponto que mais quebra este add-on é a versão do módulo de script no
`manifest.json`. O registro npm de `@minecraft/server` publica cada beta com a
versão do jogo no nome (`2.10.0-beta.1.26.44-stable`), o que dá o mapeamento:

| Jogo | módulo beta | módulo **estável** |
|---|---|---|
| 1.26.20–21 | 2.8.0-beta | 2.7.0 |
| 1.26.30–36 | 2.9.0-beta | 2.8.0 |
| 1.26.40–45 | 2.10.0-beta | **2.9.0** |

O pacote original pedia `"2.8.0-beta"` — a linha beta do 1.26.20, que não existe
mais no 1.26.45. Módulo que não resolve = pack recusado no carregamento, e um
bloco de pack recusado aparece invisível e sem função. Agora o manifest pede
`"2.9.0"`, estável, então o mundo **não** precisa do experimento "Beta APIs".

Todas as APIs usadas em `scripts/main.js` foram conferidas contra o `index.d.ts`
do `@minecraft/server@2.9.0` — nenhuma é beta (o d.ts estável não tem uma única
anotação `@beta`).

Ao mudar de versão do jogo, refaça a conferência assim:

```sh
curl -s https://registry.npmjs.org/@minecraft/server \
  | python3 -c "import json,sys,re; d=json.load(sys.stdin); \
      print([v for v in d['versions'] if re.match(r'.*-beta\\.1\\.26\\..*-stable$', v)][-5:])"
```

O beta que cita a sua versão do jogo indica a linha; a estável é a anterior.

O resource pack declara dependência do behavior pack (e vice-versa), então ativar
um puxa o outro e os dois nunca ficam separados no mundo.

Ao entrar no mundo o script escreve `[Incubadora] script carregado` no Content
Log. Se essa linha não aparecer, o módulo de script não carregou e o problema
está no manifest, não no resto do add-on.

### O modelo do bloco

O modelo veio autorado como modelo de **entidade**: 24 cubos com rotação livre
nos três eixos. Geometria de **bloco** no Bedrock só aceita rotação em um eixo,
em passos de 22,5° — modelo recusado é bloco invisível, que era o sintoma.
`tools/fix_block_geo.py` reduz cada rotação ao eixo dominante, arredonda pro
passo válido e confere os limites documentados (±30px do centro da base, e pelo
menos 1px dentro do bloco base). O original está em
`tools/incubator_original.geo.json`.

Se for reexportar o modelo, rode o script de novo — ou modele já dentro das
regras de bloco no Blockbench.

## Limitações conhecidas

- **Quebrar exige agachar**, pela hitbox da entidade (mesmo truque do addon de
  referência).
- Se o slot de lava estiver com mais de um balde, o **balde vazio cai no chão**
  em vez de voltar pro slot, que continua ocupado.
- O bloco quebrado por explosão ou `/setblock` só devolve o conteúdo no próximo
  tique da entidade.
- Os 24 cubos rotacionados do modelo ficaram com a rotação arredondada, então o
  bloco não é pixel a pixel igual ao arquivo original do Blockbench.

## Assets gerados

`textures/ui/incubator_gui.png` (o fundo 176x166 da tela) foi criado pra este
add-on — o pacote original só tinha as barras e as texturas do bloco. O script
que gera ele está em `tools/gen_gui_texture.py`.
