import { world, system, ItemStack } from "@minecraft/server";

// Aparece no Content Log ao entrar no mundo. Se esta linha nao aparecer, o
// modulo de script nao carregou e o problema e o manifest, nao o addon.
console.warn("[Incubadora] script carregado - @minecraft/server 2.9.0");

/* =========================================================
   INCUBADORAS - SallyTek Studio

   Duas maquinas, mesma mecanica: a de lava (balde de lava) e
   a de gelo (balde de agua). Tudo que muda entre elas esta na
   tabela MACHINES aqui embaixo - o resto do arquivo nao sabe
   qual e qual.

   Bloco customizado ainda nao tem container proprio, entao o
   inventario vive numa entidade invisivel colocada dentro do
   bloco. Clicar no bloco acerta a entidade e abre o container
   dela.

   O nome dado no summon vira o titulo do container, e o
   resource pack usa esse titulo em ui/chest_screen.json pra
   trocar a tela de bau pela tela da maquina. Qualquer outro
   bau do mundo continua com a tela normal.

   A ordem dos slots abaixo PRECISA bater com a grade de
   ui/incubator_screen.json.
   ========================================================= */

// Slots do container da entidade
const SLOT_FUEL_GAUGE = 0;   // item-display: barra de abastecimento
const SLOT_FUEL = 1;         // balde
const SLOT_INPUT = 2;        // item a chocar
const SLOT_PROGRESS = 3;     // item-display: barra de progresso
const SLOT_OUTPUT = 4;       // resultado

// Balanceamento, igual pras duas: cada balde rende 20s de forno e chocar leva
// 60s, ou seja 3 baldes por item.
const TOTAL_HATCH_TICKS = 1200;   // 60s de forno pra chocar um item
const TICKS_PER_POINT = 400;      // 20s de forno que cada balde rende
const TICKS_PER_STEP = 20;        // o timer da entidade bate 1x por segundo

const EMPTY_BUCKET = "minecraft:bucket";

// Tabela de receitas: item de entrada -> item de saida. Cada maquina aponta
// pra uma; hoje as duas usam a mesma, mas e so trocar aqui pra separarem.
const HATCH_RECIPES = {
	"sallytek:skrill_egg": "sallytek:skrill_egg_hatched",
	"minecraft:egg": "minecraft:chicken_spawn_egg"
};

/* ----------------------------- as duas maquinas ---------------------------- */

// ARROW_STAGES e FUEL_POINTS sao escritos por
// tools/install_gauge_textures.py - rode ele depois de trocar as texturas.
const MACHINES = [
	{
		nome: "lava",
		blockId: "sallytek:incubator",
		entityId: "sallytek:incubator",
		// Titulo do container. E tambem a chave de traducao no .lang e o valor
		// comparado em ui/chest_screen.json. Nao traduza aqui.
		containerName: "sallytek.incubator.block",
		fuelItem: "minecraft:lava_bucket",
		gaugePrefix: "sallytek:incubator_",
		arrowStages: 6,   // ARROW_STAGES lava
		fuelPoints: 6,    // FUEL_POINTS lava
		recipes: HATCH_RECIPES
	},
	{
		nome: "gelo",
		blockId: "sallytek:ice_incubator",
		entityId: "sallytek:ice_incubator",
		containerName: "sallytek.ice_incubator.block",
		fuelItem: "minecraft:water_bucket",
		gaugePrefix: "sallytek:ice_incubator_",
		arrowStages: 6,   // ARROW_STAGES gelo
		fuelPoints: 6,    // FUEL_POINTS gelo
		recipes: HATCH_RECIPES
	}
];

const PROP_FUEL = "sallytek:fuel";
const PROP_PROGRESS = "sallytek:progress";
// propriedade de entidade lida pelo render controller do resource pack
const PROP_LIT = "sallytek:lit";

function machineByBlock(typeId) {
	return MACHINES.find((m) => m.blockId === typeId);
}

function machineByEntity(typeId) {
	return MACHINES.find((m) => m.entityId === typeId);
}

function isGaugeItem(itemId) {
	return typeof itemId === "string" &&
		MACHINES.some((m) => itemId.startsWith(m.gaugePrefix));
}

/* ------------------------------ colocar/quebrar ---------------------------- */

function summonCore(machine, dimension, loc) {
	// O nome vira o titulo do container - e o que o JSON UI compara.
	dimension.spawnEntity(machine.entityId, { x: loc.x + 0.5, y: loc.y, z: loc.z + 0.5 })
		.nameTag = machine.containerName;
}

function findCore(machine, dimension, loc) {
	return dimension.getEntitiesAtBlockLocation(loc).find((e) => e.typeId === machine.entityId);
}

world.afterEvents.playerPlaceBlock.subscribe((ev) => {
	const block = ev.block;
	const machine = machineByBlock(block.typeId);
	if (!machine) return;
	// "placed" troca a geometria do bloco por uma vazia: o modelo original
	// quem desenha e a entidade. A geometria base so serve pro icone do item.
	block.setPermutation(block.permutation
		.withState("sallytek:lit", false)
		.withState("sallytek:placed", true));
	if (!findCore(machine, ev.dimension, block.location)) {
		summonCore(machine, ev.dimension, block.location);
	}
});

world.afterEvents.playerBreakBlock.subscribe((ev) => {
	const machine = machineByBlock(ev.brokenBlockPermutation.type.id);
	if (!machine) return;
	const core = findCore(machine, ev.dimension, ev.block.location);
	if (!core) return;

	// Devolve o conteudo (menos os itens-display) antes de sumir com a entidade.
	const container = core.getComponent("minecraft:inventory")?.container;
	if (container) {
		for (let slot = 0; slot < container.size; slot++) {
			const item = container.getItem(slot);
			if (item && !isGaugeItem(item.typeId)) {
				ev.dimension.spawnItem(item, ev.block.location);
			}
			container.setItem(slot, undefined);
		}
	}
	core.remove();
});

// Bloco colocado antes desta versao (ou entidade perdida): recria a entidade
// no primeiro clique. Com a entidade no lugar, o clique vai nela e nao aqui.
world.afterEvents.playerInteractWithBlock.subscribe((ev) => {
	const block = ev.block;
	const machine = machineByBlock(block.typeId);
	if (!machine) return;
	if (!findCore(machine, block.dimension, block.location)) {
		summonCore(machine, block.dimension, block.location);
		block.setPermutation(block.permutation.withState("sallytek:placed", true));
		ev.player.onScreenDisplay.setActionBar("§eIncubadora religada. Clique de novo pra abrir.");
	}
});

/* --------------------- faxina: item-display nunca e do jogador ------------- */

// As barras sao itens de verdade dentro do container. Se algum escapar pro
// inventario de alguem (versao antiga, /give, criativo), some com ele: esse
// item nao serve pra nada na mao e so polui o inventario.
system.runInterval(() => {
	for (const player of world.getAllPlayers()) {
		const container = player.getComponent("minecraft:inventory")?.container;
		if (!container) continue;
		for (let slot = 0; slot < container.size; slot++) {
			if (isGaugeItem(container.getItem(slot)?.typeId)) {
				container.setItem(slot, undefined);
			}
		}
	}
}, 20);

/* ------------------------- relogio: 1x por segundo ------------------------- */

// As duas maquinas batem o mesmo evento; quem e quem sai do typeId da entidade.
system.afterEvents.scriptEventReceive.subscribe((ev) => {
	if (ev.id !== "sallytek:incubator_tick") return;
	const core = ev.sourceEntity;
	if (!core) return;
	const machine = machineByEntity(core.typeId);
	if (!machine) return;
	tickIncubator(machine, core);
});

function tickIncubator(machine, core) {
	const container = core.getComponent("minecraft:inventory")?.container;
	if (!container) return;

	// Incubadora que perdeu o apelido (versao 1.16.0 nascia sem ele) para de
	// abrir a tela certa: devolve o apelido no primeiro tique.
	if (core.nameTag !== machine.containerName) core.nameTag = machine.containerName;

	const block = core.dimension.getBlock(core.location);
	if (!block || block.typeId !== machine.blockId) {
		// O bloco sumiu sem passar pelo evento de quebrar (explosao, /setblock...).
		for (let slot = 0; slot < container.size; slot++) {
			const item = container.getItem(slot);
			if (item && !isGaugeItem(item.typeId)) {
				core.dimension.spawnItem(item, core.location);
			}
		}
		core.remove();
		return;
	}

	let fuel = core.getDynamicProperty(PROP_FUEL) ?? 0;
	let progress = core.getDynamicProperty(PROP_PROGRESS) ?? 0;

	// 1) Abastecer. Cada balde do slot vira 1 ponto no tanque na hora, e o
	//    balde vazio volta - o tanque guarda o conteudo, nao o balde.
	fuel = refill(machine, container, core, fuel);

	// 2) Trabalhar. Precisa de receita valida, espaco na saida e tanque cheio.
	const input = container.getItem(SLOT_INPUT);
	const output = container.getItem(SLOT_OUTPUT);
	const result = input ? machine.recipes[input.typeId] : undefined;
	const outputHasRoom = result !== undefined &&
		(!output || (output.typeId === result && output.amount < output.maxAmount));

	const working = outputHasRoom && fuel > 0;
	if (working) {
		fuel = Math.max(0, fuel - TICKS_PER_STEP);
		progress += TICKS_PER_STEP;
		if (progress >= TOTAL_HATCH_TICKS) {
			progress = 0;
			produce(container, input, result, output);
		}
	} else {
		// Parou: o progresso volta, como a fornalha esfriando.
		progress = Math.max(0, progress - TICKS_PER_STEP);
	}

	core.setDynamicProperty(PROP_FUEL, fuel);
	core.setDynamicProperty(PROP_PROGRESS, progress);

	updateGauges(machine, core, container, fuel, progress);

	// O bloco fica invisivel e so responde pela luz; quem troca entre a
	// textura vazia e a cheia e o render controller da entidade, lendo a
	// propriedade sallytek:lit.
	// Acende assim que tem o que gastar no tanque - nao so enquanto choca.
	const isLit = fuel > 0;
	if (core.getProperty(PROP_LIT) !== isLit) {
		core.setProperty(PROP_LIT, isLit);
	}
	if (block.permutation.getState("sallytek:lit") !== isLit ||
		block.permutation.getState("sallytek:placed") !== true) {
		block.setPermutation(block.permutation
			.withState("sallytek:lit", isLit)
			.withState("sallytek:placed", true));
	}
}

// 1 balde = 1 ponto de armazenamento. So aceita se couber inteiro, pra nunca
// engolir um balde e dar menos de um ponto em troca.
function refill(machine, container, core, fuel) {
	const bucket = container.getItem(SLOT_FUEL);
	if (!bucket || bucket.typeId !== machine.fuelItem) return fuel;
	if (fuel + TICKS_PER_POINT > machine.fuelPoints * TICKS_PER_POINT) return fuel;

	if (bucket.amount > 1) {
		bucket.amount -= 1;
		container.setItem(SLOT_FUEL, bucket);
		// O slot ainda tem baldes cheios, entao o vazio cai no chao.
		core.dimension.spawnItem(new ItemStack(EMPTY_BUCKET, 1), core.location);
	} else {
		container.setItem(SLOT_FUEL, new ItemStack(EMPTY_BUCKET, 1));
	}
	return fuel + TICKS_PER_POINT;
}

function produce(container, input, result, output) {
	if (output) {
		output.amount += 1;
		container.setItem(SLOT_OUTPUT, output);
	} else {
		container.setItem(SLOT_OUTPUT, new ItemStack(result, 1));
	}

	if (input.amount > 1) {
		input.amount -= 1;
		container.setItem(SLOT_INPUT, input);
	} else {
		container.setItem(SLOT_INPUT, undefined);
	}
}

// As barras sao itens: o script troca o item-display de cada slot e o JSON UI
// so desenha o icone dele. E assim que a barra "anima" dentro do container.
function updateGauges(machine, core, container, fuel, progress) {
	const points = Math.min(machine.fuelPoints, Math.ceil(fuel / TICKS_PER_POINT));
	const stage = Math.min(
		machine.arrowStages - 1,
		Math.floor((progress / TOTAL_HATCH_TICKS) * machine.arrowStages)
	);
	setGauge(core, container, SLOT_FUEL_GAUGE, `${machine.gaugePrefix}fuel_${points}`);
	setGauge(core, container, SLOT_PROGRESS, `${machine.gaugePrefix}arrow_${stage}`);
}

function setGauge(core, container, slot, itemId) {
	const current = container.getItem(slot);
	if (current?.typeId === itemId) return;
	// Se o jogador largou outra coisa no slot da barra, o item cai no chao em
	// vez de ser apagado pela troca do item-display.
	if (current && !isGaugeItem(current.typeId)) {
		core.dimension.spawnItem(current, core.location);
	}
	container.setItem(slot, new ItemStack(itemId, 1));
}
