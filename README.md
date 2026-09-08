# Incubadora Funcional — SallyTek Studio / Dragon Forge

Add-on de Minecraft Bedrock com o bloco `sallytek:incubator`, que funciona como
uma fornalha: você põe um item pra chocar, abastece com balde de lava e o
progresso corre até sair o resultado.

```
Incubadora [BP] - SallyTek Studio/   behavior pack (blocos + script)
Incubadora [RP] - SallyTek Studio/   resource pack (modelos, texturas e UI)
tools/                               scripts que geram/instalam os assets
tools/frames/                        os quadros das barras, como vieram
```

Blocos: `sallytek:incubator`, `sallytek:skrill_egg` e
`sallytek:skrill_egg_hatched`.

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

Os quadros ficam versionados em `tools/frames/`, entao dá pra rodar de novo a
qualquer momento sem depender do chat.

Hoje: **6 quadros de setinha** e **7 de abastecimento** — ou seja, o tanque
guarda **6 baldes**, e cada balde continua valendo **1 ponto**.

**Dois quadros foram montados aqui, não vieram no lote.** As duas séries são
espaçadas por igual e faltava um degrau em cada uma: o nível 2 do tanque (a
lava sobe 43px por marca, e vieram 1, 3, 4, 5 e 6) e o estágio 1 da setinha (o
preenchimento anda 5px por quadro, e vieram 10, 15, 20 e 25). Como os quadros
de cada série são idênticos abaixo da linha de preenchimento — conferido pixel
a pixel —, dá pra montar o que falta recortando os que vieram, sem inventar
desenho: é o que `tools/frames/fuel_2.png` e `tools/frames/arrow_1.png` são.
Mandando os originais, é só sobrescrever os dois arquivos e rodar o instalador.

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

O fundo (`textures/ui/incubator_gui.png`) é **arte do autor**, 176x166,
copiada pro pacote sem edição — ninguém gera esse arquivo. `gen_ui_textures.py`
só faz a célula; ele já teve um gerador de fundo, que saiu justamente pra
ninguém apagar a arte boa rodando o script sem querer.

A paleta da célula é amostrada das barras que vieram no pacote: o interior
`#501B1B` é exatamente a cor do corpo do tanque, e `#411616` / `#883D3D` são a
sombra e o brilho.

### Quem desenha o modelo é a entidade

O arquivo do Blockbench é um modelo de **entidade**, e isso não é opinião: são
24 cubos com rotação livre nos três eixos, dois ossos com hierarquia (`parent`),
pivô em `[16, 0, 0]` e 24×23×24 px. Geometria de **bloco** não aceita nenhuma
dessas quatro coisas. Tentar adaptar custou várias rodadas e sempre saía
invisível ou corrompendo o desenho em volta.

A saída é usar a entidade que **já existe** dentro do bloco pro contêiner: ela
também passou a desenhar o modelo. Modelo de entidade não tem limite de
tamanho, de rotação nem de hierarquia de osso, então o arquivo vai **copiado
byte a byte** (`tools/fix_block_geo.py` confere).

| arquivo | quem usa | o que é |
|---|---|---|
| `models/entity/incubator.geo.json` | a entidade, no mundo | o original, sem tocar |
| `models/blocks/incubator_item.geo.json` | só o ícone do item | os 29 cubos sem rotação, escalados pra caber no bloco |
| `models/blocks/incubator_empty.geo.json` | o bloco depois de colocado | vazia |

O bloco ganhou o estado `sallytek:placed`. Em `false` (que é o estado do **item**
no inventário) ele usa a geometria do ícone; o script liga `true` assim que o
bloco é colocado, e aí a permutação troca por geometria vazia — o bloco some e
o palco fica pro modelo da entidade. O brilho continua sendo do bloco:
`sallytek:lit == true` dá `light_emission: 8`, como no original.

A troca entre textura apagada e acesa é do render controller
(`render_controllers/incubator.render_controllers.json`), que lê a propriedade
de entidade `sallytek:lit` — declarada com `client_sync: true` pra chegar no
cliente, e escrita pelo script com `core.setProperty`.

**Quando ela acende:** `sallytek:lit` liga com **lava no tanque**
(`fuel > 0` em `scripts/main.js`), não só enquanto está chocando. Ou seja: pôs o
balde, ela já fica com a textura de lava (`textures/blocks/incubator_lit`) e com
`light_emission: 8`, e só apaga quando o tanque zera. Como o relógio da entidade
bate 1x por segundo, a troca acontece no tique seguinte ao balde.

### Só existe uma textura pintada

O modelo tem um osso só pra chapa de lava (`water_and_lava`), e a arte que vem
do Blockbench é a **com lava**. A versão apagada é a mesma arte com todo pixel
de lava em alpha 0 — não é escolha minha, é a regra do par que já estava no
pacote: refazendo a apagada antiga a partir da acesa antiga, o resultado bate em
4082 dos 4096 pixels (os 14 que sobram são retoques de cinza). Quem faz isso é

```sh
python3 tools/make_block_textures.py <incubadora_com_lava.png>
```

que grava `incubator_lit.png` como cópia literal do arquivo e deriva
`incubator_unlit.png`. `--conferir` refaz a conta em cima do par instalado.

## Sobre o nome do bloco

O **rótulo de título saiu da tela** (não existe `title_label` em
`ui/incubator_screen.json`), e é isso que dá pra fazer sem quebrar nada.

O apelido da entidade (`nameTag = "sallytek.incubator.block"`) **ficou**. Ele é
a única forma comprovada de a porteira de `ui/chest_screen.json` reconhecer que
o contêiner aberto é a Incubadora. Na versão 1.16.0 a entidade nasceu sem
apelido pra sumir com o nome flutuante em cima do bloco; o preço foi a tela
voltar a abrir como baú comum, então o apelido voltou. Quem tinha uma Incubadora
da 1.16.0 recebe o apelido de volta no primeiro tique do relógio.

Ou seja: **a mira encostada no bloco ainda mostra o nome flutuando.** Isso é do
Bedrock — entidade com apelido desenha o apelido — e só sai junto com o apelido,
que é o que faz a tela funcionar.

O **item** continua com nome (`Incubadora`) — é o que aparece no inventário e no
criativo; sem isso ele ficaria com o identificador cru na mão.

## O ovo de Skrill

Dois blocos, mesmo modelo (`geometry.eggs_block`, copiado do Blockbench sem
tocar), só muda a textura:

| bloco | textura | onde entra |
|---|---|---|
| `sallytek:skrill_egg` | `textures/blocks/skrill_egg` | é o que se põe pra chocar |
| `sallytek:skrill_egg_hatched` | `textures/blocks/skrill_egg_hatched` | é o que sai |

A ligação entre os dois é uma linha da tabela de receitas do `scripts/main.js`:

```js
const HATCH_RECIPES = {
	"sallytek:skrill_egg": "sallytek:skrill_egg_hatched",
	...
};
```

Os dois são **blocos de verdade** — dá pra colocar no mundo, quebrar e o item
deles é o que circula pela Incubadora. O modelo vai direto em
`minecraft:geometry`, sem entidade nenhuma no meio: o arquivo do ovo tem um osso
só, sem `parent`, e cabe em 12x16x16, então não esbarra em nada do que derrubou
a Incubadora (lá o problema é a hierarquia de ossos). Rotação livre de cubo, o
ovo tem, e isso geometria de bloco aceita — o limite de 22,5° é do componente
`minecraft:transformation`, que gira o bloco inteiro, não dos cubos do modelo.

**A arte do ovo chocado ainda não chegou**, então `skrill_egg_hatched.png` é hoje
uma cópia de `skrill_egg.png` — o bloco funciona e nada fica sem textura, mas os
dois estão iguais. Trocar é sobrescrever esse arquivo, nada mais.

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
- **Encostar a mira no bloco mostra o nome flutuando.** É o preço do apelido da
  entidade, e o apelido é o que faz a tela da Incubadora abrir.

## O que foi gerado aqui, e não veio pronto

| arquivo | como sai |
|---|---|
| `textures/ui/incubator_cell.png` | `tools/gen_ui_textures.py` |
| `textures/blocks/incubator_unlit.png` | `tools/make_block_textures.py` (deriva da acesa) |
| `models/blocks/incubator_item.geo.json` | `tools/fix_block_geo.py` (só o ícone do item) |
| `models/blocks/incubator_empty.geo.json` | `tools/fix_block_geo.py` |
| `textures/items/incubator_*.png` | `tools/install_gauge_textures.py` |
| `tools/frames/fuel_2.png`, `tools/frames/arrow_1.png` | recorte dos quadros vizinhos |
| `textures/blocks/skrill_egg_hatched.png` | cópia provisória do ovo não chocado |

Todo o resto — modelo da Incubadora, textura da Incubadora, fundo da tela,
modelo do ovo, textura do ovo, quadros das barras — é arquivo do autor, copiado
sem edição.
