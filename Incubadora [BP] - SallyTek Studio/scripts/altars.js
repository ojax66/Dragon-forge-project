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
const CATALYST_CHARGING = "sallytek:catalyst_charging";
const CATALYST_CHARGED = "sallytek:catalyst_charged";
const BASE_CRYSTAL = "sallytek:base_crystal";
const AMETHYST = "minecraft:amethyst_shard";

const TAG_PINNED = "sallytek_altar_item";     // item dropado que e enfeite de altar
const PROP_ENERGY = "sallytek:energy";        // % de energia, guardada no proprio item
const PROP_AGE = "sallytek:display_age";      // ha quantos tiques o enfeite existe
const PROP_CHARGE_STATE = "sallytek:charge_state"; // 0 vazio / 1 carregando (roxo claro) / 2 cheio, na entidade
const PROP_SENDING = "sallytek:sending";      // true no altar secundario enquanto a particula dele esta viajando

const PARTICLE_ENERGY = "sallytek:energy_wisp"; // particula roxa que viaja da ametista ate o catalisador
const VOO_DURACAO = 14; // tiques ate a particula chegar no altar principal

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

// 100% de energia = uma ametista por altar secundario do anel, entao cada
// ametista vale 100/12 = 8.33%. A conta nao para nos 100%: se o jogador
// reabastecer o anel com o catalisador ainda no lugar, a energia passa de 100
// e o sub-nome vira o aviso vermelho.
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

	if (isCatalyst(item)) {
		// Modelo e animacao proprios: os aneis giram cada um pro seu lado.
		const ent = dimension.spawnEntity(DISPLAY, at);
		ent.setProperty(PROP_CHARGE_STATE, chargeStateOf(item));
		// O sub-nome (%) fica gravado no item guardado dentro do altar, mas
		// quem flutua em cima e essa entidade - entidade nao mostra tooltip
		// de item. Sem isto o jogador nunca via a porcentagem sem tirar o
		// catalisador do altar.
		ent.nameTag = loreFor(energyOf(item))[0];
		return;
	}

	// Qualquer outro item: um drop de verdade, parado e sem poder ser pego.
	const mostra = new ItemStack(item.typeId, 1);
	const drop = dimension.spawnItem(mostra, at);
	drop.addTag(TAG_PINNED);
	drop.clearVelocity();
}

// Vazio, carregando e cheio sao tres blocos diferentes - assim o icone, a luz
// e o que o jogador carrega na mao ja saem certos.
function isCatalyst(item) {
	return item?.typeId === CATALYST || item?.typeId === CATALYST_CHARGING || item?.typeId === CATALYST_CHARGED;
}

// 0 vazio / 1 carregando (roxo claro, ainda enchendo) / 2 cheio (roxo).
function chargeStateOf(item) {
	if (item?.typeId === CATALYST_CHARGED) return 2;
	if (item?.typeId === CATALYST_CHARGING) return 1;
	return 0;
}

/* ------------------------ a energia e o sub-nome dela ---------------------- */

function energyOf(item) {
	const v = item?.getDynamicProperty?.(PROP_ENERGY);
	return typeof v === "number" ? v : 0;
}

// O sub-nome que aparece embaixo do nome do item, na cor da faixa:
//   0 a 25%   vermelho
//   25 a 75%  amarelo
//   75 a 100% verde
//   exatos 100%    verde brilhante, em negrito
//   acima de 100%  vermelho vivo, em negrito, com "!"
function loreFor(pct) {
	const n = Math.round(pct);
	if (pct > 100) return [`§c§lEnergia: ${n}% !`];
	if (pct >= 100) return [`§a§lEnergia: ${n}%`];
	if (pct >= 75) return [`§aEnergia: ${n}%`];
	if (pct >= 25) return [`§eEnergia: ${n}%`];
	return [`§cEnergia: ${n}%`];
}

// Monta o catalisador do jeito certo pra energia que ele tem: vazio (0%),
// carregando - roxo claro - (entre 0 e 100%) ou cheio - roxo - (100%+),
// com a energia gravada nele e o sub-nome ja escrito.
function catalystWith(pct) {
	const tipo = pct <= 0 ? CATALYST : pct >= 100 ? CATALYST_CHARGED : CATALYST_CHARGING;
	const item = new ItemStack(tipo, 1);
	item.setDynamicProperty(PROP_ENERGY, pct);
	item.setLore(loreFor(pct));
	return item;
}

// Catalisador recem-craftado nao tem energia nem sub-nome: carimba a
// energia certa (0%, 100% ou um meio-termo) na primeira vez que ele
// aparece na mao de alguem - por exemplo, vindo do inventario criativo.
function energiaPadrao(item) {
	if (item?.typeId === CATALYST_CHARGED) return 100;
	if (item?.typeId === CATALYST_CHARGING) return 50;
	return 0;
}

system.runInterval(() => {
	for (const player of world.getAllPlayers()) {
		const inv = player.getComponent("minecraft:inventory")?.container;
		if (!inv) continue;
		for (let i = 0; i < inv.size; i++) {
			const item = inv.getItem(i);
			if (!isCatalyst(item)) continue;
			if (typeof item.getDynamicProperty(PROP_ENERGY) === "number") continue;
			inv.setItem(i, catalystWith(energiaPadrao(item)));
		}
	}
}, 20);

/* ------------------------------------------------------------------------- */

// Faxina: uma vez por segundo cada enfeite confere se ainda tem motivo pra
// existir. Sem isto, um altar quebrado por explosao ou /setblock deixaria a
// entidade orfa girando no ar.
system.afterEvents.scriptEventReceive.subscribe((ev) => {
	if (ev.id !== "sallytek:display_tick") return;
	const e = ev.sourceEntity;
	if (!e || e.typeId !== DISPLAY) return;
	const p = {
		x: Math.floor(e.location.x),
		y: Math.floor(e.location.y),
		z: Math.floor(e.location.z)
	};
	// enfeite de altar: o altar esta um bloco abaixo (ver FLOAT_Y)
	if (ALTAR_BLOCKS.includes(e.dimension.getBlock({ ...p, y: p.y - 1 })?.typeId)) return;
	e.remove();
});

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

	if (block.typeId === ALTAR_MAIN) {
		ritual(core, block, item);
	} else if (core.getDynamicProperty(PROP_SENDING) && !voos.some((v) => v.doadorCore.id === core.id)) {
		// O mundo recarregou no meio de um voo (a lista de voos e so em
		// memoria) - sem isto este altar nunca mais mandaria energia.
		core.setDynamicProperty(PROP_SENDING, false);
	}
}

// Voos em andamento: cada ametista encontrada vira um destes, e some quando a
// particula chega no altar principal e entrega a energia de verdade.
const voos = [];

function ritual(core, block, item) {
	// So o altar principal, com um catalisador em cima, puxa magia.
	if (!isCatalyst(item)) return;

	// So um voo por vez pra este altar - sem isso a energia enche rapido
	// demais e a particula nao da tempo de mostrar nada.
	if (voos.some((v) => v.core.id === core.id)) return;

	const doador = proximaAmetista(core.dimension, block.location);
	if (!doador) return;

	// A ametista fica no lugar dela (ainda ametista) enquanto a energia viaja.
	doador.core.setDynamicProperty(PROP_SENDING, true);
	voos.push({
		core,
		mainLoc: { x: block.location.x, y: block.location.y, z: block.location.z },
		doadorCore: doador.core,
		doadorLoc: doador.loc,
		tique: 0,
	});
	core.dimension.playSound("random.orb", displayLocation(doador.loc));
}

// A cada tique: avanca cada particula um pouco no caminho dela e, quando
// chega no altar principal, ai sim - so ai - a ametista vira cristal base e o
// catalisador ganha a fatia de energia dela.
system.runInterval(() => {
	for (let i = voos.length - 1; i >= 0; i--) {
		const voo = voos[i];
		voo.tique++;
		const t = Math.min(voo.tique / VOO_DURACAO, 1);

		try {
			const de = displayLocation(voo.doadorLoc);
			const para = displayLocation(voo.mainLoc);
			const pos = {
				x: de.x + (para.x - de.x) * t,
				y: de.y + (para.y - de.y) * t + Math.sin(Math.PI * t) * 0.4, // arco leve
				z: de.z + (para.z - de.z) * t,
			};
			voo.core.dimension.spawnParticle(PARTICLE_ENERGY, pos);
		} catch {
			// altar sumiu no meio do caminho - a particula so nao aparece;
			// o voo ainda termina normalmente e o cleanup abaixo decide o resto.
		}

		if (t >= 1) {
			terminaVoo(voo);
			voos.splice(i, 1);
		}
	}
}, 1);

function terminaVoo(voo) {
	voo.doadorCore.setDynamicProperty(PROP_SENDING, false);

	// Confere se os dois lados continuam do jeito esperado - o jogador pode
	// ter mexido em algum dos altares enquanto a particula viajava.
	const aindaTemAmetista = heldItem(voo.doadorCore)?.typeId === AMETHYST;
	const catalisador = heldItem(voo.core);
	if (!aindaTemAmetista || !isCatalyst(catalisador)) return;

	// A ametista entrega a magia e fica sendo um cristal base no altar dela.
	const cristal = new ItemStack(BASE_CRYSTAL, 1);
	setHeldItem(voo.doadorCore, cristal);
	spawnDisplay(voo.doadorCore.dimension, voo.doadorLoc, cristal);
	voo.doadorCore.setDynamicProperty(PROP_AGE, 0);

	// Cada ametista vale uma fatia de 100% dividida pelos altares do anel.
	// Arredonda pra 2 casas: 100/12 não é exato em ponto flutuante, e sem
	// isso a 12a ametista fecha em 99.99999999999999 em vez de 100 - o
	// catalisador nunca vira o catalisador cheio.
	const antes = energyOf(catalisador);
	const agora = Math.round((antes + 100 / RITUAL_CAPACITY) * 100) / 100;
	const novo = catalystWith(agora);
	setHeldItem(voo.core, novo);
	spawnDisplay(voo.core.dimension, voo.mainLoc, novo);
	voo.core.setDynamicProperty(PROP_AGE, 0);

	const centro = displayLocation(voo.mainLoc);
	voo.core.dimension.playSound("random.orb", centro);
	// Passou de 100 agora: o catalisador encheu.
	if (antes < 100 && agora >= 100) {
		voo.core.dimension.playSound("beacon.activate", centro);
	}
}

// Procura, no anel, o primeiro altar secundario com uma ametista em cima que
// ainda nao esteja mandando a energia dela pra algum lugar.
function proximaAmetista(dimension, centro) {
	for (const { dx, dz } of RING) {
		const loc = { x: centro.x + dx, y: centro.y, z: centro.z + dz };
		const block = dimension.getBlock(loc);
		if (!block || block.typeId !== ALTAR_SECOND) continue;
		const core = findCore(dimension, loc);
		if (!core) continue;
		if (core.getDynamicProperty(PROP_SENDING)) continue;
		if (heldItem(core)?.typeId === AMETHYST) return { core, loc };
	}
	return undefined;
}
