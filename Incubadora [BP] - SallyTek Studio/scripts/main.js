import { world, system, ItemStack } from "@minecraft/server";

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

const ARROW_STAGES = 7;      // sallytek:incubator_arrow_0 .. _6
const FUEL_PIPS = 10;        // sallytek:incubator_fuel_0 .. _10

const TOTAL_HATCH_TICKS = 2000;                       // 100s pra chocar
const TICKS_PER_PIP = TOTAL_HATCH_TICKS / FUEL_PIPS;  // 200 ticks por balde
const MAX_FUEL_TICKS = FUEL_PIPS * TICKS_PER_PIP;
const TICKS_PER_STEP = 20;                            // o timer da entidade bate 1x por segundo

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

	const input = container.getItem(SLOT_INPUT);
	const output = container.getItem(SLOT_OUTPUT);
	const result = input ? HATCH_RECIPES[input.typeId] : undefined;

	// Da pra trabalhar? Precisa de receita valida e espaco na saida.
	const outputHasRoom = result !== undefined &&
		(!output || (output.typeId === result && output.amount < output.maxAmount));

	// Acende a lava so quando ha o que chocar, igual a fornalha.
	if (fuel <= 0 && outputHasRoom) {
		fuel = consumeBucket(container, core, fuel);
	}

	if (fuel > 0) {
		fuel = Math.max(0, fuel - TICKS_PER_STEP);
		if (outputHasRoom) {
			progress += TICKS_PER_STEP;
			if (progress >= TOTAL_HATCH_TICKS) {
				progress = 0;
				produce(container, input, result, output);
			}
		} else {
			progress = 0;
		}
	} else {
		// Sem lava o progresso volta, como a fornalha apagando.
		progress = Math.max(0, progress - TICKS_PER_STEP);
	}

	core.setDynamicProperty(PROP_FUEL, fuel);
	core.setDynamicProperty(PROP_PROGRESS, progress);

	updateGauges(core, container, fuel, progress);

	const isLit = fuel > 0;
	if (block.permutation.getState("sallytek:lit") !== isLit) {
		block.setPermutation(block.permutation.withState("sallytek:lit", isLit));
	}
}

function consumeBucket(container, core, fuel) {
	const bucket = container.getItem(SLOT_FUEL);
	if (!bucket || bucket.typeId !== FUEL_ITEM) return fuel;

	if (bucket.amount > 1) {
		bucket.amount -= 1;
		container.setItem(SLOT_FUEL, bucket);
		// O slot ainda esta cheio de baldes de lava, entao o vazio cai no chao.
		core.dimension.spawnItem(new ItemStack(EMPTY_BUCKET, 1), core.location);
	} else {
		container.setItem(SLOT_FUEL, new ItemStack(EMPTY_BUCKET, 1));
	}
	return Math.min(MAX_FUEL_TICKS, fuel + TICKS_PER_PIP);
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
	const pip = Math.min(FUEL_PIPS, Math.ceil(fuel / TICKS_PER_PIP));
	const stage = Math.min(
		ARROW_STAGES - 1,
		Math.floor((progress / TOTAL_HATCH_TICKS) * (ARROW_STAGES - 1))
	);
	setGauge(core, container, SLOT_FUEL_GAUGE, `${GAUGE_PREFIX}fuel_${pip}`);
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
