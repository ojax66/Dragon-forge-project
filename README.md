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

### Ícone de item é sempre quadrado

O atlas de itens do Bedrock só aceita ícone quadrado. A barra do tanque é
72×266, e mandada assim ela era cortada pelo atlas — o medidor não mexia ao
abastecer e só mostrava um pedaço de lava no topo quando cheio.
`tools/install_gauge_textures.py` grava cada quadro **centralizado num canvas
quadrado** (266×266, sobras transparentes). Aí é só desenhar o item a 59×59 que
a barra dentro dele sai com `59 × 72/266 = 16` de largura por 59 de altura, que
é a medida do mock-up. A setinha já vem 32×32, quadrada, e não precisa disso.

### As barras são itens

Não dá pra mandar um número pro cliente dentro de um contêiner — só itens. Então
as barras são itens-display (`sallytek:incubator_fuel_*` e
`sallytek:incubator_arrow_*`, em `items/display/`) que o script troca a cada
segundo no slot correspondente. O JSON UI só desenha o ícone do item, e o
resultado é uma barra que anima.

**Trocar ou acrescentar quadros:** jogue todos os PNGs numa pasta e rode

```sh
python3 tools/install_gauge_textures.py <pasta>
```

Ele separa as séries pelo tamanho (32x32 = setinha, 72x266 = abastecimento),
ordena cada uma pela quantidade de pixel laranja — do vazio pro cheio —, grava
numerado, e regenera o que depende da contagem: os itens-display, o
`item_texture.json`, os `.lang` e as constantes `ARROW_STAGES` e `FUEL_POINTS`
do `scripts/main.js`. Se a série não tiver um quadro vazio, ele gera um tirando
o preenchimento do menor quadro.

Hoje: **10 quadros de setinha** e **5 de abastecimento**.

### Ordem dos slots

`scripts/main.js` e a grade de `ui/incubator_screen.json` compartilham esta
ordem — mexeu em um, mexa no outro:

| índice | slot | posição na tela |
|---|---|---|
| 0 | barra de lava (item-display) | 14, 26 |
| 1 | balde de lava | 42, 48 |
| 2 | entrada | 78, 28 |
| 3 | setinha de progresso (item-display) | 104, 30 |
| 4 | saída | 150, 30 |

### Coordenadas

A tela tem **176x166**, o mesmo tamanho de baú/fornalha da vanilla. As posições
saíram do mock-up de referência (284x266, que é essa tela renderizada em
1,611x — as colunas da grade caem exatas no passo 18 da vanilla):

| elemento | posição | tamanho |
|---|---|---|
| tanque de lava | 7, 16 | 18 × 61 (barra 16 × 59) |
| slot do balde | 31, 57 | 18 × 18 |
| entrada | 74, 36 | 18 × 18 |
| setinha | 95, 33 | 26 × 26 |
| saída | 124, 33 | 26 × 26 |
| título | 58, 6 | — |
| "Inventário" | direita −11, 72 | — |
| grade 9×3 | 7, 86 | células 18 |
| hotbar 9×1 | 7, 143 | células 18 |

A grade e a hotbar são posicionadas pelo Bedrock, não por nós — `7, 86` e
`7, 143` saem de `(176−162)/2`, `166−26−54` e `166−5−18`. No mock-up esse bloco
está ~3px mais alto; ficou na posição da vanilla porque é onde estão os slots
clicáveis de verdade.

### A cor das células

As células vermelhas são uma **textura de slot** (`textures/ui/incubator_cell`,
18×18 em nine-slice de 1px), passada em `$background_images` no lugar do
`common.cell_image_panel` da vanilla — nos slots da máquina **e** no inventário
e na hotbar do jogador. Nada de item colorido fingindo ser célula, e nada de
célula assada no fundo: quem desenha é o próprio JSON UI, em cima do slot de
verdade, então nunca sai do lugar. O mesmo arquivo estica pro tanque (18×61) e
pra saída (26×26).

O fundo (`textures/ui/incubator_gui`) tem só o painel, a moldura e os veios de
lava. Os dois são gerados por `tools/gen_ui_textures.py`, com a paleta amostrada
do mock-up: fundo `#652828`, célula `#501B1B`, sombra `#411616`, brilho `#883D3D`.

### O modelo do bloco

O modelo vai **sem edição nenhuma**: `tools/fix_block_geo.py` não move, escala,
rotaciona nem descarta cubo algum. Origem, tamanho, rotação, `inflate` e UV de
cada um dos 53 cubos saem idênticos ao arquivo do Blockbench, e o script
confere isso comparando os 424 vértices um a um — falha se algum sair do lugar.

O que ele arruma é só estrutura, duas coisas que são de modelo de **entidade** e
não existem em geometria de bloco:

- o osso `water_and_lava` tinha **`parent`** — hierarquia de osso é coisa de
  entidade; bloco espera uma lista de cubos;
- os dois ossos tinham **`pivot: [16, 0, 0]`**, um bloco inteiro longe da
  origem. Pivô só serve como centro de rotação do osso, e nenhum dos dois gira —
  então zerar não move nada.

Como nenhum osso gira, juntar tudo num osso só com pivô na origem dá exatamente
o mesmo desenho, numa estrutura que o render de bloco entende.

As texturas do bloco (`incubator_lit.png`, `incubator_unlit.png`) são as
originais, byte a byte.

**Se ainda assim não renderizar**, o modelo tem duas coisas que geometria de
bloco não aceita e que não dá pra arrumar sem mexer na forma: 24 cubos com
rotação livre nos três eixos (bloco só aceita um eixo, em passo de 22,5°) e
24×23×24 px de tamanho. Aí o único jeito de mostrar esse modelo exato é
renderizá-lo na entidade — modelo de entidade não tem nenhuma dessas restrições,
e este foi autorado como um.

## Limitações conhecidas

- **Quebrar exige agachar**, pela hitbox da entidade (mesmo truque do addon de
  referência).
- **No controle por toque aparece o botão "Abrir"** em vez de abrir no toque.
  O contêiner mora numa entidade, e o Bedrock sempre pede o botão pra interagir
  com entidade — bloco abre no toque, entidade não. Não dá pra contornar por
  script: `@minecraft/server` 2.9.0 não tem nenhuma API que abra um contêiner
  para o jogador (conferido no `index.d.ts`). Só some quando bloco customizado
  puder ter contêiner próprio.
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
