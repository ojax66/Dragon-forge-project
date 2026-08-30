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

A metade de baixo é posicionada pelo Bedrock, não por nós: numa tela de 176x166,
a grade do inventário fica em (7, 86) e a hotbar em (7, 143), células de 18px.
`tools/gen_gui_texture.py` desenha o fundo já com essas células no lugar — se
mudar a altura da tela, mude lá também.

## Como usar no jogo

Clique no bloco pra abrir. Balde de lava no slot da esquerda, item pra chocar no
slot de cima, resultado sai no slot da direita. Pra quebrar o bloco, **agache** —
a entidade encolhe a hitbox quando você agacha, liberando o bloco atrás dela.

Receitas ficam em `HATCH_RECIPES` no `scripts/main.js`.

## Limitações conhecidas

- **Quebrar exige agachar**, pela hitbox da entidade (mesmo truque do addon de
  referência).
- Se o slot de lava estiver com mais de um balde, o **balde vazio cai no chão**
  em vez de voltar pro slot, que continua ocupado.
- O bloco quebrado por explosão ou `/setblock` só devolve o conteúdo no próximo
  tique da entidade.

## Assets gerados

`textures/ui/incubator_gui.png` (o fundo 176x166 da tela) foi criado pra este
add-on — o pacote original só tinha as barras e as texturas do bloco. O script
que gera ele está em `tools/gen_gui_texture.py`.
