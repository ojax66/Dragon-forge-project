import { world, system, ItemStack } from "@minecraft/server";
import { ActionFormData } from "@minecraft/server-ui";

/* =========================================================
   INCUBADORA - SallyTek Studio

   Blocos customizados ainda nao suportam container proprio
   (nao existe componente "minecraft:inventory" de bloco nesta
   versao), entao a interface e desenhada por JSON UI em cima
   do formulario de servidor (ActionFormData). O RP substitui
   "server_form.long_form": quando o titulo do formulario e
   UI_MARKER, a tela da Incubadora aparece no lugar do
   formulario padrao; qualquer outro titulo continua usando a
   tela vanilla.

   A ordem dos botoes abaixo PRECISA bater com os
   "collection_index" de ui/incubator_screen.json.
   ========================================================= */

const BLOCK_ID = "sallytek:incubator";
const REGISTRY_KEY = "sallytek:incubator_locations";
const DATA_KEY = "sallytek:incubator_data";

// Titulo-marcador lido pelo binding do JSON UI. Nao traduza.
const UI_MARKER = "sallytek:incubator_ui";

// Indices dos botoes do formulario (espelham ui/incubator_screen.json)
const BTN_FUEL = 0;
const BTN_ARROW = 1;
const BTN_INPUT = 2;
const BTN_OUTPUT = 3;
const BTN_CLOSE = 4;
const BTN_INVENTORY = 5;   // 5..40 = os 36 slots do inventario do jogador
const INVENTORY_SLOTS = 36;

const ARROW_STAGES = 7;       // incubator_arrow_0 .. _6
const FUEL_PIPS = 10;         // incubator_fuel_0 .. _10
const TOTAL_HATCH_TICKS = 2000;                       // 100s pra chocar
const TICKS_PER_PIP = TOTAL_HATCH_TICKS / FUEL_PIPS;  // 200 ticks (10s) por balde
const MAX_FUEL_TICKS = FUEL_PIPS * TICKS_PER_PIP;

const FUEL_ITEM = "minecraft:lava_bucket";
const EMPTY_BUCKET = "minecraft:bucket";

// Tabela de receitas: item de entrada -> item de saida. Edite/adicione a vontade.
const HATCH_RECIPES = {
	"minecraft:egg": "minecraft:chicken_spawn_egg"
};

// Icone mostrado nos slots da UI. Itens fora desta tabela aparecem como
// slot vazio, entao adicione aqui todo item que entrar em HATCH_RECIPES.
const ITEM_TEXTURES = {
	"minecraft:egg": "textures/items/egg",
	"minecraft:chicken_spawn_egg": "textures/items/egg_chicken",
	"minecraft:lava_bucket": "textures/items/bucket_lava",
	"minecraft:bucket": "textures/items/bucket_empty"
};

function textureFor(itemId) {
	return itemId ? ITEM_TEXTURES[itemId] : undefined;
}

function isUsable(itemId) {
	return itemId === FUEL_ITEM || Object.prototype.hasOwnProperty.call(HATCH_RECIPES, itemId);
}

/* ------------------------------- persistencia ------------------------------ */

function loadRegistry() {
	const raw = world.getDynamicProperty(REGISTRY_KEY);
	if (!raw) return [];
	try { return JSON.parse(raw); } catch { return []; }
}
function saveRegistry(list) {
	world.setDynamicProperty(REGISTRY_KEY, JSON.stringify(list));
}
function loadData() {
	const raw = world.getDynamicProperty(DATA_KEY);
	if (!raw) return {};
	try { return JSON.parse(raw); } catch { return {}; }
}
function saveData(data) {
	world.setDynamicProperty(DATA_KEY, JSON.stringify(data));
}
function keyFor(dimensionId, loc) {
	return `${dimensionId}:${loc.x},${loc.y},${loc.z}`;
}
function defaultState() {
	return { progressTicks: 0, fuelTicks: 0, queuedItem: null, outputItem: null };
}
function readState(key) {
	const data = loadData();
	return data[key] ?? defaultState();
}
function writeState(key, state) {
	const data = loadData();
	data[key] = state;
	saveData(data);
}

function addIncubator(dimensionId, loc) {
	const list = loadRegistry();
	const k = keyFor(dimensionId, loc);
	if (!list.includes(k)) {
		list.push(k);
		saveRegistry(list);
	}
}
function removeIncubator(dimensionId, loc) {
	const list = loadRegistry();
	const k = keyFor(dimensionId, loc);
	const idx = list.indexOf(k);
	if (idx !== -1) {
		list.splice(idx, 1);
		saveRegistry(list);
	}
	const data = loadData();
	const state = data[k];
	if (state) {
		delete data[k];
		saveData(data);
	}
	return state;
}

/* --------------------------------- eventos -------------------------------- */

world.afterEvents.playerPlaceBlock.subscribe((ev) => {
	const block = ev.block;
	if (block.typeId === BLOCK_ID) {
		addIncubator(ev.dimension.id, block.location);
		block.setPermutation(block.permutation.withState("sallytek:lit", false));
	}
});

world.afterEvents.playerBreakBlock.subscribe((ev) => {
	if (ev.brokenBlockPermutation.type.id !== BLOCK_ID) return;
	const state = removeIncubator(ev.dimension.id, ev.block.location);
	if (!state) return;
	// devolve o que estava dentro, igual a uma fornalha quebrada
	const loc = ev.block.location;
	for (const itemId of [state.queuedItem, state.outputItem]) {
		if (!itemId) continue;
		try { ev.dimension.spawnItem(new ItemStack(itemId, 1), loc); } catch { /* item invalido */ }
	}
});

// Clicar no bloco abre a interface (e cancela colocar bloco/usar item na mao).
world.beforeEvents.playerInteractWithBlock.subscribe((ev) => {
	if (ev.block.typeId !== BLOCK_ID) return;
	ev.cancel = true;
	const player = ev.player;
	const dimensionId = ev.block.dimension.id;
	// copia os valores: o objeto do evento nao vale mais dentro do system.run
	const loc = { x: ev.block.location.x, y: ev.block.location.y, z: ev.block.location.z };
	const key = keyFor(dimensionId, loc);
	system.run(() => {
		addIncubator(dimensionId, loc); // cobre blocos colocados antes desta versao
		openIncubator(player, key);
	});
});

/* ----------------------------------- UI ----------------------------------- */

function fuelPip(state) {
	return Math.min(FUEL_PIPS, Math.ceil(state.fuelTicks / TICKS_PER_PIP));
}
function arrowStage(state) {
	return Math.min(
		ARROW_STAGES - 1,
		Math.floor((state.progressTicks / TOTAL_HATCH_TICKS) * (ARROW_STAGES - 1))
	);
}

function openIncubator(player, key) {
	const state = readState(key);
	const container = player.getComponent("minecraft:inventory")?.container;
	const pct = Math.floor((state.progressTicks / TOTAL_HATCH_TICKS) * 100);

	const form = new ActionFormData()
		.title(UI_MARKER)
		// O texto abaixo so aparece se o resource pack estiver desligado
		// (ai o formulario cai no visual padrao do Bedrock).
		.body(
			`§6Combustivel: ${fuelPip(state)}/${FUEL_PIPS}\n` +
			`§eProgresso: ${pct}%\n` +
			`§aChocando: ${state.queuedItem ?? "nada"}`
		);

	form.button(`§6Lava ${fuelPip(state)}/${FUEL_PIPS}`, `textures/items/incubator_fuel_${fuelPip(state)}`);
	form.button(`§eProgresso ${pct}%`, `textures/items/incubator_arrow_${arrowStage(state)}`);
	form.button(`§aEntrada: ${state.queuedItem ?? "vazio"}`, textureFor(state.queuedItem));
	form.button(`§bSaida: ${state.outputItem ?? "vazio"}`, textureFor(state.outputItem));
	form.button("§7Fechar");

	// Os 36 slots do inventario. Itens que a Incubadora nao aceita ficam sem
	// icone, entao a grade mostra so o que da pra usar.
	for (let slot = 0; slot < INVENTORY_SLOTS; slot++) {
		const item = container?.getItem(slot);
		const usable = item && isUsable(item.typeId);
		form.button(usable ? `${item.typeId} x${item.amount}` : " ", usable ? textureFor(item.typeId) : undefined);
	}

	form.show(player).then((res) => {
		if (res.canceled || res.selection === undefined || res.selection === BTN_CLOSE) return;
		system.run(() => handleClick(player, key, res.selection));
		// espera a tela anterior fechar de verdade antes de reabrir atualizada
		system.runTimeout(() => openIncubator(player, key), 2);
	}).catch(() => { /* jogador saiu ou ja tinha outra tela aberta */ });
}

function handleClick(player, key, selection) {
	const state = readState(key);
	const container = player.getComponent("minecraft:inventory")?.container;

	if (selection === BTN_FUEL) {
		refuelFrom(player, container, state, findSlotWith(container, FUEL_ITEM));
	} else if (selection === BTN_ARROW) {
		// so atualiza a tela
	} else if (selection === BTN_INPUT) {
		if (state.queuedItem) {
			giveItem(player, container, state.queuedItem);
			state.queuedItem = null;
			state.progressTicks = 0;
			player.onScreenDisplay.setActionBar("§eItem retirado da incubadora.");
		} else {
			player.onScreenDisplay.setActionBar("§7Clique num item da grade pra colocar aqui.");
		}
	} else if (selection === BTN_OUTPUT) {
		if (state.outputItem) {
			giveItem(player, container, state.outputItem);
			state.outputItem = null;
			player.onScreenDisplay.setActionBar("§bVoce coletou o item chocado!");
		}
	} else if (selection >= BTN_INVENTORY) {
		const slot = selection - BTN_INVENTORY;
		const item = container?.getItem(slot);
		if (!item) return;
		if (item.typeId === FUEL_ITEM) {
			refuelFrom(player, container, state, slot);
		} else if (HATCH_RECIPES[item.typeId]) {
			if (state.queuedItem) {
				player.onScreenDisplay.setActionBar("§cA incubadora ja esta ocupada.");
			} else {
				state.queuedItem = item.typeId;
				state.progressTicks = 0;
				takeOne(container, slot, item);
				player.onScreenDisplay.setActionBar("§aItem colocado na incubadora.");
			}
		} else {
			player.onScreenDisplay.setActionBar("§cEsse item nao serve aqui.");
		}
	}

	writeState(key, state);
}

function findSlotWith(container, itemId) {
	if (!container) return -1;
	for (let slot = 0; slot < INVENTORY_SLOTS; slot++) {
		if (container.getItem(slot)?.typeId === itemId) return slot;
	}
	return -1;
}

function refuelFrom(player, container, state, slot) {
	if (slot < 0 || !container) {
		player.onScreenDisplay.setActionBar("§cVoce nao tem balde de lava.");
		return;
	}
	if (state.fuelTicks >= MAX_FUEL_TICKS) {
		player.onScreenDisplay.setActionBar("§cO tanque de lava ja esta cheio.");
		return;
	}
	const item = container.getItem(slot);
	if (!item || item.typeId !== FUEL_ITEM) return;

	state.fuelTicks = Math.min(MAX_FUEL_TICKS, state.fuelTicks + TICKS_PER_PIP);
	takeOne(container, slot, item);
	giveItem(player, container, EMPTY_BUCKET);
	player.onScreenDisplay.setActionBar(`§6Lava abastecida: ${fuelPip(state)}/${FUEL_PIPS}`);
}

function takeOne(container, slot, item) {
	if (item.amount > 1) {
		const rest = item.clone();
		rest.amount -= 1;
		container.setItem(slot, rest);
	} else {
		container.setItem(slot, undefined);
	}
}

function giveItem(player, container, itemId) {
	const stack = new ItemStack(itemId, 1);
	if (container && container.emptySlotsCount > 0) {
		container.addItem(stack);
	} else {
		player.dimension.spawnItem(stack, player.location);
	}
}

/* --------------------- loop: progresso e combustivel ---------------------- */

system.runInterval(() => {
	const list = loadRegistry();
	if (list.length === 0) return;

	const data = loadData();
	let registryChanged = false;

	for (const key of [...list]) {
		const [dimensionId, coords] = key.split(":");
		const [x, y, z] = coords.split(",").map(Number);

		let dimension;
		try {
			dimension = world.getDimension(dimensionId);
		} catch {
			continue;
		}

		let block;
		try {
			block = dimension.getBlock({ x, y, z });
		} catch {
			continue; // chunk descarregado: tenta de novo depois
		}
		if (!block) continue;

		if (block.typeId !== BLOCK_ID) {
			const idx = list.indexOf(key);
			if (idx !== -1) list.splice(idx, 1);
			delete data[key];
			registryChanged = true;
			continue;
		}

		const state = data[key] ?? defaultState();

		if (state.queuedItem && state.fuelTicks > 0 && !state.outputItem) {
			state.progressTicks += 20;
			state.fuelTicks = Math.max(0, state.fuelTicks - 20);

			if (state.progressTicks >= TOTAL_HATCH_TICKS) {
				state.outputItem = HATCH_RECIPES[state.queuedItem];
				state.queuedItem = null;
				state.progressTicks = 0;
			}
		}

		const isLit = state.fuelTicks > 0;
		if (block.permutation.getState("sallytek:lit") !== isLit) {
			block.setPermutation(block.permutation.withState("sallytek:lit", isLit));
		}

		data[key] = state;
	}

	saveData(data);
	if (registryChanged) saveRegistry(list);
}, 20);
