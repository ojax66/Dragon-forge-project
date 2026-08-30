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
existe componente `minecraft:inventory` de bloco no schema, então não dá pra abrir
uma tela de baú/barril ligada ao bloco.

A UI usa então o caminho que funciona desde sempre: **JSON UI por cima do
formulário de servidor**. O resource pack substitui `server_form.long_form`
(`ui/server_form.json`) por um seletor:

- título do formulário igual a `sallytek:incubator_ui` → desenha
  `incubator.screen` (`ui/incubator_screen.json`), a tela da Incubadora;
- qualquer outro título → cai em `server_form.vanilla_long_form`, que é cópia
  fiel do `long_form` original da Mojang. Outros add-ons e formulários do mundo
  continuam funcionando normalmente.

Cada slot da tela é um botão do `ActionFormData` posicionado por
`collection_index` sobre a arte. As barras não são imagens fixas: o script manda
o caminho da textura como ícone do botão (`#form_button_texture`), e o JSON UI só
desenha o que chegar. Por isso `incubator_fuel_0..10` e `incubator_arrow_0..6`
funcionam sem nenhuma condição repetida no JSON.

### Ordem dos botões

`scripts/main.js` e `ui/incubator_screen.json` compartilham esta ordem — mexeu em
um, mexa no outro:

| índice | slot |
|---|---|
| 0 | barra/slot de combustível (balde de lava) |
| 1 | barra de progresso |
| 2 | slot de entrada |
| 3 | slot de saída |
| 4 | botão de fechar |
| 5–40 | os 36 slots do inventário do jogador |

## Como usar no jogo

Clique no bloco pra abrir a tela. Na grade de baixo aparecem os itens do seu
inventário que a Incubadora aceita — clique num deles pra colocar na entrada, ou
num balde de lava pra abastecer. O slot de saída entrega o resultado.

Receitas ficam em `HATCH_RECIPES` no `scripts/main.js`. Ao adicionar uma receita,
registre também o ícone do item em `ITEM_TEXTURES` do mesmo arquivo — item sem
ícone cadastrado aparece como slot vazio na grade.

## Limitações conhecidas

- **A tela é um retrato, não atualiza sozinha.** Formulário de servidor não tem
  binding ao vivo; as barras se atualizam a cada clique (o script reabre a tela).
- **Não é arrastar-e-soltar.** Item entra e sai por clique, porque os "slots" são
  botões de formulário, não slots de container de verdade.
- **Com o resource pack desligado** o jogo cai no formulário padrão do Bedrock —
  o texto de cada botão foi escrito pra continuar legível nesse caso.

Quando blocos customizados ganharem container próprio, dá pra trocar essa camada
por um container de verdade sem mexer na lógica de progresso/combustível.

## Assets gerados

`textures/ui/incubator_{bg_tile,frame,slot,slot_hover,recess}.png` foram criados
pra este add-on (o pacote original só tinha as barras e as texturas do bloco).
O script que gera eles está em `tools/gen_ui_textures.py`.
