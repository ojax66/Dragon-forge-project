import { world, system, GameMode, ItemStack } from "@minecraft/server";

/* =========================================================
   ALTARES E CATALISADOR - SallyTek Studio

   Altar principal no meio, altares secundarios em volta. O
   jogador clica no altar com o item na mao pra por, e clica de
   mao vazia pra tirar. O item fica flutuando e girando em cima
   do altar.

   Quem guarda o item e uma entidade invisivel (sallytek:altar_core)
   dentro do bloco, com um container de 1 slot - e por isso que o
   item nao se perde ao sair do mundo. O que flutua em cima e so a
   aparencia: um item dropado de verdade, preso no lugar e com o
   "pegar" cancelado. Item dropado ja flutua e gira sozinho, que e
   exatamente o efeito pedido.

   O catalisador e a excecao: ele tem modelo e animacao proprios
   (os aneis giram cada um pro seu lado), entao em cima do altar
   ele vira a entidade sallytek:catalyst_display.
   ========================================================= */

const ALTAR_MAIN = "sallytek:main_altar";
const ALTAR_SECOND = "sallytek:secondary_altar";
const ALTAR_BLOCKS = [ALTAR_MAIN, ALTAR_SECOND];

const CORE = "sallytek:altar_core";
const DISPLAY = "sallytek:catalyst_display";

const CATALYST = "sallytek:catalyst";
const CATALYST_CHARGED = "sallytek:catalyst_charged";
const BASE_CRYSTAL = "sallytek:base_crystal";
const AMETHYST = "minecraft:amethyst_shard";

const TAG_PINNED = "sallytek_altar_item";   // item dropado que e enfeite de altar
const PROP_CHARGE = "sallytek:charge";      // ametistas ja absorvidas (0..RING.length)
const PROP_AGE = "sallytek:display_age";    // ha quantos tiques o enfeite existe
const PROP_CHARGED = "sallytek:charged";    // propriedade de entidade do catalisador

// Altura em que o item flutua, contada do canto de baixo do bloco do altar.
const FLOAT_Y = 1.15;
// Item dropado some sozinho em 5 min (6000 tiques). O nucleo troca o enfeite
// aos 4 min, antes de sumir; o item de verdade esta no container, entao a
// troca nao perde nada - so reinicia o giro, o que a essa altura ninguem ve.
const REFRESH_TICKS = 4800;

/* ------------------------------ o anel de altares -------------------------- */

// "pular 2 blocos e ir circulando, com espacos de 1 bloco entre os altares":
// o anel fica na distancia 3 do altar principal (os blocos 1 e 2 ficam vazios),
// e dentro do anel entra um altar sim, um nao. Da 12 posicoes, todas com
// exatamente 1 bloco de folga pros vizinhos.
const RING = [];
for (let dx = -3; dx <= 3; dx++) {
	for (let dz = -3; dz <= 3; dz++) {
		if (Math.max(Math.abs(dx), Math.abs(dz)) === 3 && (dx + dz) % 2 === 0) {
			RING.push({ dx, dz });
		}
	}
}

// Capacidade do catalisador: uma ametista por altar secundario do anel.
// Cada uma vale 100/12 = 8.33% da carga.
const RITUAL_CAPACITY = RING.length;

/* ------------------------------- nucleo do altar --------------------------- */

function findCore(dimension, loc) {
	return dimension.getEntitiesAtBlockLocation(loc).find((e) => e.typeId === CORE);
}

function summonCore(dimension, loc) {
	// Sem nameTag: altar nao mostra nome nenhum.
	return dimension.spawnEntity(CORE, { x: loc.x + 0.5, y: loc.y + 0.1, z: loc.z + 0.5 });
}

function coreAt(dimension, loc, criar) {
	const core = findCore(dimension, loc);
	if (core || !criar) return core;
	return summonCore(dimension, loc);
}

function heldItem(core) {
	return core.getComponent("minecraft:inventory")?.container?.getItem(0);
}

function setHeldItem(core, item) {
	core.getComponent("minecraft:inventory")?.container?.setItem(0, item);
}

/* --------------------------- o que flutua em cima -------------------------- */

function displayLocation(loc) {
	return { x: loc.x + 0.5, y: loc.y + FLOAT_Y, z: loc.z + 0.5 };
}

function findDisplays(dimension, loc) {
	const at = displayLocation(loc);
	return dimension.getEntities({ location: at, maxDistance: 0.9 })
		.filter((e) => e.typeId === DISPLAY || (e.typeId === "minecraft:item" && e.hasTag(TAG_PINNED)));
}

function clearDisplay(dimension, loc) {
	for (const e of findDisplays(dimension, loc)) e.remove();
}

function spawnDisplay(dimension, loc, item) {
	clearDisplay(dimension, loc);
	if (!item) return;
	const at = displayLocation(loc);

	if (item.typeId === CATALYST || item.typeId === CATALYST_CHARGED) {
		// Modelo e animacao proprios: os aneis giram cada um pro seu lado.
		const ent = dimension.spawnEntity(DISPLAY, at);
		ent.setProperty(PROP_CHARGED, isCharged(item));
		return;
	}

	// Qualquer outro item: um drop de verdade, parado e sem poder ser pego.
	const mostra = new ItemStack(item.typeId, 1);
	const drop = dimension.spawnItem(mostra, at);
	drop.addTag(TAG_PINNED);
	drop.clearVelocity();
}

// Vazio e carregado sao dois blocos diferentes - assim o icone, a luz e o que
// o jogador carrega na mao ja saem certos, sem depender de dado no item.
function isCharged(item) {
	return item?.typeId === CATALYST_CHARGED;
}

/* Item dropado que e enfeite de altar nunca e pego por ninguem. */
world.beforeEvents.entityItemPickup.subscribe((ev) => {
	if (ev.item?.hasTag(TAG_PINNED)) ev.cancel = true;
});

/* ------------------------------ colocar/quebrar ---------------------------- */

world.afterEvents.playerPlaceBlock.subscribe((ev) => {
	if (!ALTAR_BLOCKS.includes(ev.block.typeId)) return;
	coreAt(ev.dimension, ev.block.location, true);
});

world.afterEvents.playerBreakBlock.subscribe((ev) => {
	if (!ALTAR_BLOCKS.includes(ev.brokenBlockPermutation.type.id)) return;
	const loc = ev.block.location;
	const core = findCore(ev.dimension, loc);
	clearDisplay(ev.dimension, loc);
	if (!core) return;
	const item = heldItem(core);
	if (item) ev.dimension.spawnItem(item, displayLocation(loc));
	core.remove();
});

/* ------------------------ clicar: poe o item ou tira ----------------------- */

// Tem que ser o evento "before": sem cancelar, clicar no altar com um bloco na
// mao colocaria o bloco em cima dele em vez de por o item no altar.
world.beforeEvents.playerInteractWithBlock.subscribe((ev) => {
	const block = ev.block;
	if (!ALTAR_BLOCKS.includes(block.typeId)) return;
	if (!ev.isFirstEvent) return;

	ev.cancel = true;
	const player = ev.player;
	const naMao = ev.itemStack;
	const dimension = block.dimension;
	const loc = { x: block.location.x, y: block.location.y, z: block.location.z };

	// Evento "before" nao pode mexer no mundo: o trabalho vai pro proximo tique.
	system.run(() => {
		const core = coreAt(dimension, loc, true);
		if (!core) return;
		const guardado = heldItem(core);

		if (guardado) {
			devolve(player, core, dimension, loc, guardado);
		} else if (naMao) {
			recebe(player, core, dimension, loc, naMao);
		} else if (block.typeId === ALTAR_MAIN) {
			mostraCarga(player, core);
		}
	});
});

function recebe(player, core, dimension, loc, naMao) {
	const inv = player.getComponent("minecraft:inventory")?.container;
	const slot = player.selectedSlotIndex;

	const posto = naMao.clone();
	posto.amount = 1;
	setHeldItem(core, posto);
	spawnDisplay(dimension, loc, posto);

	// Tira 1 da mao. No criativo a mao nao esvazia, como em qualquer outro caso.
	if (player.getGameMode?.() !== GameMode.Creative && inv) {
		if (naMao.amount > 1) {
			const resto = naMao.clone();
			resto.amount -= 1;
			inv.setItem(slot, resto);
		} else {
			inv.setItem(slot, undefined);
		}
	}
	player.playSound("random.pop", { location: displayLocation(loc) });
}

function devolve(player, core, dimension, loc, guardado) {
	setHeldItem(core, undefined);
	clearDisplay(dimension, loc);
	const inv = player.getComponent("minecraft:inventory")?.container;
	if (inv && inv.emptySlotsCount > 0) {
		inv.addItem(guardado);
	} else {
		dimension.spawnItem(guardado, displayLocation(loc));
	}
	player.playSound("random.pop", { location: displayLocation(loc) });
}

function mostraCarga(player, core) {
	const carga = core.getDynamicProperty(PROP_CHARGE) ?? 0;
	const pct = Math.round((carga / RITUAL_CAPACITY) * 100);
	player.onScreenDisplay.setActionBar(
		`§dCatalisador: §f${pct}% §7(${carga}/${RITUAL_CAPACITY} ametistas)`);
}

/* ------------------------------- o ritual ---------------------------------- */

system.afterEvents.scriptEventReceive.subscribe((ev) => {
	if (ev.id !== "sallytek:altar_tick") return;
	const core = ev.sourceEntity;
	if (!core || core.typeId !== CORE) return;
	tickAltar(core);
});

function tickAltar(core) {
	const loc = {
		x: Math.floor(core.location.x),
		y: Math.floor(core.location.y),
		z: Math.floor(core.location.z)
	};
	const block = core.dimension.getBlock(loc);
	if (!block || !ALTAR_BLOCKS.includes(block.typeId)) {
		// O altar sumiu sem passar pelo evento de quebrar (explosao, /setblock...).
		const item = heldItem(core);
		if (item) core.dimension.spawnItem(item, displayLocation(loc));
		clearDisplay(core.dimension, loc);
		core.remove();
		return;
	}

	const item = heldItem(core);

	// O enfeite some sozinho depois de 5 min (drop e drop). Repoe antes disso.
	const idade = (core.getDynamicProperty(PROP_AGE) ?? 0) + 20;
	if (!item) {
		clearDisplay(core.dimension, loc);
		core.setDynamicProperty(PROP_AGE, 0);
	} else if (idade >= REFRESH_TICKS || findDisplays(core.dimension, loc).length === 0) {
		spawnDisplay(core.dimension, loc, item);
		core.setDynamicProperty(PROP_AGE, 0);
	} else {
		core.setDynamicProperty(PROP_AGE, idade);
	}

	if (block.typeId === ALTAR_MAIN) ritual(core, block, item);
}

function ritual(core, block, item) {
	// So o altar principal com um catalisador vazio em cima puxa magia.
	if (!item || item.typeId !== CATALYST || isCharged(item)) return;

	let carga = core.getDynamicProperty(PROP_CHARGE) ?? 0;
	if (carga >= RITUAL_CAPACITY) return;

	// Uma ametista por segundo, pra dar pra ver a carga subindo.
	const doador = proximaAmetista(core.dimension, block.location);
	if (!doador) return;

	// A ametista entrega a magia e fica sendo um cristal base.
	setHeldItem(doador.core, new ItemStack(BASE_CRYSTAL, 1));
	spawnDisplay(doador.core.dimension, doador.loc, new ItemStack(BASE_CRYSTAL, 1));
	doador.core.setDynamicProperty(PROP_AGE, 0);

	carga += 1;
	core.setDynamicProperty(PROP_CHARGE, carga);

	const centro = displayLocation(block.location);
	core.dimension.playSound("random.orb", centro);

	if (carga >= RITUAL_CAPACITY) {
		// 100%: o catalisador fica cheio.
		const cheio = new ItemStack(CATALYST_CHARGED, 1);
		setHeldItem(core, cheio);
		spawnDisplay(core.dimension, block.location, cheio);
		core.setDynamicProperty(PROP_AGE, 0);
		core.dimension.playSound("beacon.activate", centro);
	}
}

// Procura, no anel, o primeiro altar secundario com uma ametista em cima.
function proximaAmetista(dimension, centro) {
	for (const { dx, dz } of RING) {
		const loc = { x: centro.x + dx, y: centro.y, z: centro.z + dz };
		const block = dimension.getBlock(loc);
		if (!block || block.typeId !== ALTAR_SECOND) continue;
		const core = findCore(dimension, loc);
		if (!core) continue;
		if (heldItem(core)?.typeId === AMETHYST) return { core, loc };
	}
	return undefined;
}
