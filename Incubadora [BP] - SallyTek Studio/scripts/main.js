import { world, system, ItemStack } from "@minecraft/server";

// Aparece no Content Log ao entrar no mundo. Se esta linha nao aparecer, o
// modulo de script nao carregou e o problema e o manifest, nao o addon.
console.warn("[Incubadora] script carregado - @minecraft/server 2.9.0");

/* =========================================================
   INCUBADORA - SallyTek Studio

   Bloco customizado ainda nao tem container proprio, entao o
   inventario vive numa entidade invisivel (sallytek:incubator)
   colocada dentro do bloco. Clicar no bloco acerta a entidade
   e abre o container dela.

   O nome dado no summon vira o titulo do container, e o
   resource pack usa esse titulo em ui/chest_screen.json pra
   trocar a tela de bau pela tela da Incubadora. Qualquer outro
   bau do mundo continua com a tela normal.

   A ordem dos slots abaixo PRECISA bater com a grade de
   ui/incubator_screen.json.
   ========================================================= */

const BLOCK_ID = "sallytek:incubator";
const ENTITY_ID = "sallytek:incubator";

// Titulo do container. E tambem a chave de traducao no .lang e o valor
// comparado em ui/chest_screen.json. Nao traduza aqui.
const CONTAINER_NAME = "sallytek.incubator.block";

// Slots do container da entidade
const SLOT_FUEL_GAUGE = 0;   // item-display: barra de lava
const SLOT_FUEL = 1;         // balde de lava
const SLOT_INPUT = 2;        // item a chocar
const SLOT_PROGRESS = 3;     // item-display: barra de progresso
const SLOT_OUTPUT = 4;       // resultado

// Contagens de quadros das barras. Quem mexe nelas e
// tools/install_gauge_textures.py - rode ele depois de trocar as texturas.
const ARROW_STAGES = 10;      // quadros de sallytek:incubator_arrow_*
const FUEL_POINTS = 4;      // capacidade do tanque, em baldes

// Balanceamento: cada balde rende 20s de forno e chocar leva 60s, ou seja
// 3 baldes por item. O tanque cheio (4 baldes) da pra um item e sobra troco.
const TOTAL_HATCH_TICKS = 1200;   // 60s de forno pra chocar um item
const TICKS_PER_POINT = 400;      // 20s de forno que cada balde rende
const MAX_FUEL_TICKS = FUEL_POINTS * TICKS_PER_POINT;
const TICKS_PER_STEP = 20;        // o timer da entidade bate 1x por segundo

const FUEL_ITEM = "minecraft:lava_bucket";
const EMPTY_BUCKET = "minecraft:bucket";

const PROP_FUEL = "sallytek:fuel";
const PROP_PROGRESS = "sallytek:progress";

// Tabela de receitas: item de entrada -> item de saida. Edite/adicione a vontade.
const HATCH_RECIPES = {
	"minecraft:egg": "minecraft:chicken_spawn_egg"
};

const GAUGE_PREFIX = "sallytek:incubator_";

function isGaugeItem(itemId) {
	return typeof itemId === "string" && itemId.startsWith(GAUGE_PREFIX);
}

/* ------------------------------ colocar/quebrar ---------------------------- */

function summonCore(dimension, loc) {
	// O nome vira o titulo do container - e o que o JSON UI compara.
	dimension.spawnEntity(ENTITY_ID, { x: loc.x + 0.5, y: loc.y, z: loc.z + 0.5 })
		.nameTag = CONTAINER_NAME;
}

function findCore(dimension, loc) {
	return dimension.getEntitiesAtBlockLocation(loc).find((e) => e.typeId === ENTITY_ID);
}

world.afterEvents.playerPlaceBlock.subscribe((ev) => {
	const block = ev.block;
	if (block.typeId !== BLOCK_ID) return;
	block.setPermutation(block.permutation.withState("sallytek:lit", false));
	if (!findCore(ev.dimension, block.location)) {
		summonCore(ev.dimension, block.location);
	}
});

world.afterEvents.playerBreakBlock.subscribe((ev) => {
	if (ev.brokenBlockPermutation.type.id !== BLOCK_ID) return;
	const core = findCore(ev.dimension, ev.block.location);
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
	if (block.typeId !== BLOCK_ID) return;
	if (!findCore(block.dimension, block.location)) {
		summonCore(block.dimension, block.location);
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

system.afterEvents.scriptEventReceive.subscribe((ev) => {
	if (ev.id !== "sallytek:incubator_tick") return;
	const core = ev.sourceEntity;
	if (!core || core.typeId !== ENTITY_ID) return;
	tickIncubator(core);
});

function tickIncubator(core) {
	const container = core.getComponent("minecraft:inventory")?.container;
	if (!container) return;

	const block = core.dimension.getBlock(core.location);
	if (!block || block.typeId !== BLOCK_ID) {
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

	// 1) Abastecer. Cada balde de lava do slot vira 1 ponto no tanque na hora,
	//    e o balde vazio volta - o tanque guarda a lava, nao o balde.
	fuel = refill(container, core, fuel);

	// 2) Trabalhar. Precisa de receita valida, espaco na saida e lava no tanque.
	const input = container.getItem(SLOT_INPUT);
	const output = container.getItem(SLOT_OUTPUT);
	const result = input ? HATCH_RECIPES[input.typeId] : undefined;
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

	updateGauges(core, container, fuel, progress);

	const isLit = working;
	if (block.permutation.getState("sallytek:lit") !== isLit) {
		block.setPermutation(block.permutation.withState("sallytek:lit", isLit));
	}
}

// 1 balde de lava = 1 ponto de armazenamento. So aceita se couber inteiro,
// pra nunca engolir um balde e dar menos de um ponto em troca.
function refill(container, core, fuel) {
	const bucket = container.getItem(SLOT_FUEL);
	if (!bucket || bucket.typeId !== FUEL_ITEM) return fuel;
	if (fuel + TICKS_PER_POINT > MAX_FUEL_TICKS) return fuel;

	if (bucket.amount > 1) {
		bucket.amount -= 1;
		container.setItem(SLOT_FUEL, bucket);
		// O slot ainda tem baldes de lava, entao o vazio cai no chao.
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
function updateGauges(core, container, fuel, progress) {
	const points = Math.min(FUEL_POINTS, Math.ceil(fuel / TICKS_PER_POINT));
	const stage = Math.min(
		ARROW_STAGES - 1,
		Math.floor((progress / TOTAL_HATCH_TICKS) * ARROW_STAGES)
	);
	setGauge(core, container, SLOT_FUEL_GAUGE, `${GAUGE_PREFIX}fuel_${points}`);
	setGauge(core, container, SLOT_PROGRESS, `${GAUGE_PREFIX}arrow_${stage}`);
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
