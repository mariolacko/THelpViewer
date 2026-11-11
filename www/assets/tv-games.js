// Turbo Vision games for THelp Viewer.
(function (root) {
"use strict";
const TV = root.THelpViewerTV = root.THelpViewerTV || {};

const LUDO_PLAYER_NAMES = ["Red", "Green", "Yellow", "Blue"];
const LUDO_PLAYER_COLORS = ["red", "green", "yellow", "blue"];
const LUDO_START_OFFSETS = [0, 10, 20, 30];
const LUDO_DEFAULT_MODES = ["human", "cpu", "cpu", "cpu"];
const LUDO_TRACK_LENGTH = 40;
const LUDO_HOME_START = 40;
const LUDO_FINISH = 43;
const LUDO_MOVE_STEP_MS = 55;
const LUDO_CAPTURE_FLASH_MS = 320;

const LUDO_COMMON_PATH = [
    [4, 0], [4, 1], [4, 2], [4, 3], [4, 4],
    [3, 4], [2, 4], [1, 4], [0, 4], [0, 5],
    [0, 6], [1, 6], [2, 6], [3, 6], [4, 6],
    [4, 7], [4, 8], [4, 9], [4, 10], [5, 10],
    [6, 10], [6, 9], [6, 8], [6, 7], [6, 6],
    [7, 6], [8, 6], [9, 6], [10, 6], [10, 5],
    [10, 4], [9, 4], [8, 4], [7, 4], [6, 4],
    [6, 3], [6, 2], [6, 1], [6, 0], [5, 0],
];

const LUDO_HOME_PATHS = [
    [[5, 1], [5, 2], [5, 3], [5, 4]],
    [[1, 5], [2, 5], [3, 5], [4, 5]],
    [[5, 9], [5, 8], [5, 7], [5, 6]],
    [[9, 5], [8, 5], [7, 5], [6, 5]],
];

const LUDO_BASE_POSITIONS = [
    [[1, 1], [1, 2], [2, 1], [2, 2]],
    [[1, 8], [1, 9], [2, 8], [2, 9]],
    [[8, 8], [8, 9], [9, 8], [9, 9]],
    [[8, 1], [8, 2], [9, 1], [9, 2]],
];

function ludoCoordinateForProgress(player, piece, progress) {
    if (progress < 0) {
        return LUDO_BASE_POSITIONS[player][piece].slice();
    }
    if (progress < LUDO_TRACK_LENGTH) {
        return LUDO_COMMON_PATH[(LUDO_START_OFFSETS[player] + progress) % LUDO_TRACK_LENGTH].slice();
    }
    return LUDO_HOME_PATHS[player][progress - LUDO_HOME_START].slice();
}

function ludoMoveProgressPath(from, target) {
    if (from < 0) {
        return [target];
    }
    const path = [];
    for (let progress = from + 1; progress <= target; progress++) {
        path.push(progress);
    }
    return path;
}

function validLudoModes(modes) {
    return Array.isArray(modes) && modes.length === 4 &&
        modes.every((mode) => mode === "human" || mode === "cpu" || mode === "off") &&
        modes.filter((mode) => mode !== "off").length >= 2 &&
        modes.includes("human");
}

class LudoGame {
    constructor(random = Math.random) {
        this.random = typeof random === "function" ? random : Math.random;
        this.reset();
    }

    reset(modes = this.modes || LUDO_DEFAULT_MODES) {
        this.modes = validLudoModes(modes) ? modes.slice() : LUDO_DEFAULT_MODES.slice();
        this.pieces = Array.from({ length: 4 }, () => [-1, -1, -1, -1]);
        this.currentPlayer = this._nextActive(-1);
        this.phase = "roll";
        this.die = 0;
        this.rollsLeft = 3;
        this.winner = null;
        this.lastCapture = null;
    }

    playerMode(player = this.currentPlayer) {
        return this.modes[player] || "off";
    }

    pieceCoordinate(player, piece) {
        return ludoCoordinateForProgress(player, piece, this.pieces[player][piece]);
    }

    legalPieces(player = this.currentPlayer, die = this.die) {
        if (this.winner !== null || player < 0 || player > 3 || die < 1 || die > 6) {
            return [];
        }
        const legal = [];
        for (let piece = 0; piece < 4; piece++) {
            if (this._targetProgress(player, piece, die) !== null) {
                legal.push(piece);
            }
        }
        return legal;
    }

    roll() {
        if (this.phase !== "roll" || this.winner !== null) {
            return null;
        }
        this.die = Math.floor(this.random() * 6) + 1;
        const legal = this.legalPieces();
        if (legal.length) {
            this.phase = "move";
            return { die: this.die, legal };
        }

        this.rollsLeft -= 1;
        if (this.rollsLeft > 0 && this._allPiecesInBase(this.currentPlayer)) {
            return { die: this.die, legal: [] };
        }
        const rolled = this.die;
        this._advanceTurn();
        return { die: rolled, legal: [] };
    }

    move(piece) {
        if (this.phase !== "move" || !this.legalPieces().includes(piece)) {
            return null;
        }
        const player = this.currentPlayer;
        const die = this.die;
        const from = this.pieces[player][piece];
        const target = this._targetProgress(player, piece, die);
        this.pieces[player][piece] = target;
        const captured = target < LUDO_TRACK_LENGTH
            ? this._captureAt(player, target)
            : [];
        this.lastCapture = captured.length ? captured : null;

        if (this.pieces[player].every((progress) => progress >= LUDO_HOME_START)) {
            this.winner = player;
            this.phase = "done";
            this.die = 0;
        } else if (die === 6) {
            this.phase = "roll";
            this.die = 0;
            this.rollsLeft = 1;
        } else {
            this._advanceTurn();
        }
        return { player, piece, from, target, captured, winner: this.winner };
    }

    chooseCpuPiece() {
        const legal = this.legalPieces();
        let bestPiece = null;
        let bestScore = -Infinity;
        for (const piece of legal) {
            const from = this.pieces[this.currentPlayer][piece];
            const target = this._targetProgress(this.currentPlayer, piece, this.die);
            const captures = target < LUDO_TRACK_LENGTH
                ? this._piecesAtCommonPosition(this.currentPlayer, target).length
                : 0;
            let score = target;
            if (from < 0) { score += 35; }
            if (target >= LUDO_HOME_START) { score += 70; }
            if (captures) { score += 100 + captures * 10; }
            if (target === LUDO_FINISH) { score += 20; }
            if (score > bestScore) {
                bestScore = score;
                bestPiece = piece;
            }
        }
        return bestPiece;
    }

    exportState() {
        return {
            v: 2,
            m: this.modes.map((mode) => mode[0]),
            p: this.pieces.flat(),
            c: this.currentPlayer,
            ph: this.phase,
            d: this.die,
            r: this.rollsLeft,
            w: this.winner,
        };
    }

    importState(state) {
        if (!state || state.v !== 2 || !Array.isArray(state.m) || !Array.isArray(state.p)) {
            return false;
        }
        const modeNames = { h: "human", c: "cpu", o: "off" };
        const modes = state.m.map((mode) => modeNames[mode]);
        if (!validLudoModes(modes) || state.p.length !== 16) {
            return false;
        }
        const progress = state.p.map(Number);
        if (progress.some((value) => !Number.isInteger(value) || value < -1 || value > LUDO_FINISH)) {
            return false;
        }
        const current = Number(state.c);
        const die = Number(state.d);
        const rolls = Number(state.r);
        const winner = state.w === null ? null : Number(state.w);
        if (!Number.isInteger(current) || modes[current] === "off" ||
                !["roll", "move", "done"].includes(state.ph) ||
                !Number.isInteger(die) || die < 0 || die > 6 ||
                !Number.isInteger(rolls) || rolls < 0 || rolls > 3 ||
                (winner !== null && (!Number.isInteger(winner) || winner < 0 || winner > 3))) {
            return false;
        }

        const pieces = Array.from({ length: 4 }, (_, player) => progress.slice(player * 4, player * 4 + 4));
        for (let player = 0; player < 4; player++) {
            const occupied = pieces[player].filter((value) => value >= 0);
            if (new Set(occupied).size !== occupied.length) {
                return false;
            }
        }
        if (state.ph === "move" && (die === 0 || !this._stateHasLegalMove(pieces, current, die))) {
            return false;
        }
        if (state.ph === "done" && (winner === null ||
                !pieces[winner].every((value) => value >= LUDO_HOME_START))) {
            return false;
        }

        this.modes = modes;
        this.pieces = pieces;
        this.currentPlayer = current;
        this.phase = state.ph;
        this.die = die;
        this.rollsLeft = rolls;
        this.winner = winner;
        this.lastCapture = null;
        return true;
    }

    _stateHasLegalMove(pieces, player, die) {
        const previousPieces = this.pieces;
        const previousModes = this.modes;
        const previousWinner = this.winner;
        this.pieces = pieces;
        this.modes = this.modes || LUDO_DEFAULT_MODES;
        this.winner = null;
        const hasMove = this.legalPieces(player, die).length > 0;
        this.pieces = previousPieces;
        this.modes = previousModes;
        this.winner = previousWinner;
        return hasMove;
    }

    _targetProgress(player, piece, die) {
        const progress = this.pieces[player][piece];
        if (progress < 0) {
            if (die !== 6 || this.pieces[player].includes(0)) {
                return null;
            }
            return 0;
        }
        const target = progress + die;
        if (target > LUDO_FINISH || this.pieces[player].includes(target)) {
            return null;
        }
        if (target >= LUDO_HOME_START) {
            const first = Math.max(LUDO_HOME_START, progress + 1);
            for (let position = first; position <= target; position++) {
                if (this.pieces[player].includes(position)) {
                    return null;
                }
            }
        }
        return target;
    }

    _piecesAtCommonPosition(player, progress) {
        const absolute = (LUDO_START_OFFSETS[player] + progress) % LUDO_TRACK_LENGTH;
        const found = [];
        for (let opponent = 0; opponent < 4; opponent++) {
            if (opponent === player || this.modes[opponent] === "off") { continue; }
            for (let piece = 0; piece < 4; piece++) {
                const otherProgress = this.pieces[opponent][piece];
                if (otherProgress >= 0 && otherProgress < LUDO_TRACK_LENGTH &&
                        (LUDO_START_OFFSETS[opponent] + otherProgress) % LUDO_TRACK_LENGTH === absolute) {
                    found.push([opponent, piece]);
                }
            }
        }
        return found;
    }

    _captureAt(player, progress) {
        const captured = this._piecesAtCommonPosition(player, progress);
        for (const [opponent, piece] of captured) {
            this.pieces[opponent][piece] = -1;
        }
        return captured;
    }

    _allPiecesInBase(player) {
        return this.pieces[player].every((progress) => progress < 0);
    }

    _nextActive(player) {
        for (let offset = 1; offset <= 4; offset++) {
            const candidate = (player + offset + 4) % 4;
            if (this.modes[candidate] !== "off") {
                return candidate;
            }
        }
        return 0;
    }

    _advanceTurn() {
        this.currentPlayer = this._nextActive(this.currentPlayer);
        this.phase = "roll";
        this.die = 0;
        this.rollsLeft = this._allPiecesInBase(this.currentPlayer) ? 3 : 1;
        this.lastCapture = null;
    }
}

class MastermindGame {
    constructor(random = Math.random, { codeLength = 4, colorCount = 6, maxTurns = 10 } = {}) {
        this.random = typeof random === "function" ? random : Math.random;
        this.codeLength = codeLength;
        this.colorCount = colorCount;
        this.maxTurns = maxTurns;
        this.reset();
    }

    reset(secret = null) {
        this.secret = Array.isArray(secret) && secret.length === this.codeLength
            ? secret.map((value) => this._normalizeColor(value))
            : Array.from({ length: this.codeLength }, () => Math.floor(this.random() * this.colorCount));
        this.currentGuess = new Array(this.codeLength).fill(0);
        this.cursor = 0;
        this.turns = [];
        this.status = "playing";
        return this;
    }

    _normalizeColor(value) {
        const color = Number(value);
        return Number.isInteger(color) && color >= 0 && color < this.colorCount ? color : 0;
    }

    setPeg(position, color) {
        if (this.status !== "playing" || position < 0 || position >= this.codeLength) { return false; }
        this.currentGuess[position] = this._normalizeColor(color);
        this.cursor = Math.min(this.codeLength - 1, position + 1);
        return true;
    }

    evaluate(guess) {
        let exact = 0;
        const secretCounts = new Array(this.colorCount).fill(0);
        const guessCounts = new Array(this.colorCount).fill(0);
        for (let index = 0; index < this.codeLength; index += 1) {
            if (guess[index] === this.secret[index]) {
                exact += 1;
            } else {
                secretCounts[this.secret[index]] += 1;
                guessCounts[guess[index]] += 1;
            }
        }
        const misplaced = secretCounts.reduce(
            (total, count, color) => total + Math.min(count, guessCounts[color]),
            0,
        );
        return { exact, misplaced };
    }

    submitGuess() {
        if (this.status !== "playing") { return null; }
        const guess = this.currentGuess.slice();
        const result = this.evaluate(guess);
        const turn = { guess, ...result };
        this.turns.push(turn);
        if (result.exact === this.codeLength) {
            this.status = "won";
        } else if (this.turns.length >= this.maxTurns) {
            this.status = "lost";
        } else {
            this.currentGuess = new Array(this.codeLength).fill(0);
            this.cursor = 0;
        }
        return turn;
    }
}

class TronGame {
    constructor({ width = 30, height = 18 } = {}) {
        this.width = Math.max(10, Math.trunc(Number(width) || 30));
        this.height = Math.max(8, Math.trunc(Number(height) || 18));
        this.reset();
    }

    reset() {
        const middle = Math.floor(this.height / 2);
        this.players = [
            { x: Math.floor(this.width / 4), y: middle, dx: 1, dy: 0, alive: true },
            { x: this.width - Math.floor(this.width / 4) - 1, y: middle, dx: -1, dy: 0, alive: true },
        ];
        this.pendingDirections = this.players.map(({ dx, dy }) => ({ dx, dy }));
        this.trails = this.players.map((player) => new Set([this._key(player.x, player.y)]));
        this.ticks = 0;
        this.status = "running";
        this.winner = null;
        return this;
    }

    _key(x, y) {
        return `${x},${y}`;
    }

    queueDirection(playerIndex, dx, dy) {
        const player = this.players[playerIndex];
        if (!player || !player.alive || this.status !== "running") { return false; }
        const horizontal = Number(dx) !== 0 && Number(dy) === 0;
        const vertical = Number(dy) !== 0 && Number(dx) === 0;
        if (!horizontal && !vertical) { return false; }
        const next = { dx: Math.sign(dx), dy: Math.sign(dy) };
        if (next.dx === -player.dx && next.dy === -player.dy) { return false; }
        this.pendingDirections[playerIndex] = next;
        return true;
    }

    clearPendingDirections() {
        this.pendingDirections = this.players.map(({ dx, dy }) => ({ dx, dy }));
    }

    occupied(x, y) {
        const key = this._key(x, y);
        return this.trails.some((trail) => trail.has(key));
    }

    tick() {
        if (this.status !== "running") { return this.status; }
        const next = this.players.map((player, index) => {
            if (!player.alive) { return null; }
            const direction = this.pendingDirections[index] || player;
            return { x: player.x + direction.dx, y: player.y + direction.dy, ...direction };
        });
        const crashed = next.map((position) => Boolean(position && (
            position.x < 0 || position.x >= this.width
            || position.y < 0 || position.y >= this.height
            || this.occupied(position.x, position.y)
        )));
        if (next[0] && next[1] && next[0].x === next[1].x && next[0].y === next[1].y) {
            crashed[0] = true;
            crashed[1] = true;
        }
        for (let index = 0; index < this.players.length; index += 1) {
            const player = this.players[index];
            const position = next[index];
            if (!player.alive || !position) { continue; }
            player.dx = position.dx;
            player.dy = position.dy;
            if (crashed[index]) {
                player.alive = false;
            } else {
                player.x = position.x;
                player.y = position.y;
                this.trails[index].add(this._key(position.x, position.y));
            }
        }
        this.clearPendingDirections();
        this.ticks += 1;
        const alive = this.players.map((player, index) => player.alive ? index : -1).filter((index) => index >= 0);
        if (alive.length < 2) {
            this.winner = alive.length === 1 ? alive[0] : null;
            this.status = alive.length === 1 ? "won" : "draw";
        }
        return this.status;
    }
}

class HanoiGame {
    constructor(diskCount = 5) {
        this.diskCount = Math.max(3, Math.min(7, Math.trunc(Number(diskCount) || 5)));
        this.reset();
    }

    reset() {
        this.towers = [
            Array.from({ length: this.diskCount }, (_, index) => this.diskCount - index),
            [],
            [],
        ];
        this.history = [];
        this.status = "playing";
        return this;
    }

    top(tower) {
        const items = this.towers[tower];
        return items?.length ? items[items.length - 1] : null;
    }

    canMove(from, to) {
        if (!Number.isInteger(from) || !Number.isInteger(to) || from < 0 || from > 2 || to < 0 || to > 2 || from === to) {
            return false;
        }
        const disk = this.top(from);
        const target = this.top(to);
        return disk !== null && (target === null || disk < target);
    }

    move(from, to) {
        if (this.status === "won" || !this.canMove(from, to)) { return false; }
        const disk = this.towers[from].pop();
        this.towers[to].push(disk);
        this.history.push({ from, to, disk });
        if (this.towers[2].length === this.diskCount) { this.status = "won"; }
        return true;
    }

    undo() {
        const move = this.history.pop();
        if (!move) { return false; }
        const disk = this.towers[move.to].pop();
        if (disk !== move.disk) {
            this.towers[move.to].push(disk);
            this.history.push(move);
            return false;
        }
        this.towers[move.from].push(disk);
        this.status = "playing";
        return true;
    }

    get moves() {
        return this.history.length;
    }

    get minimumMoves() {
        return (2 ** this.diskCount) - 1;
    }
}

const GAME_RULES_EXPORTS = {
    LudoGame,
    MastermindGame,
    TronGame,
    HanoiGame,
    LUDO_BASE_POSITIONS,
    LUDO_COMMON_PATH,
    LUDO_DEFAULT_MODES,
    LUDO_FINISH,
    LUDO_HOME_PATHS,
    LUDO_HOME_START,
    LUDO_PLAYER_COLORS,
    LUDO_PLAYER_NAMES,
    LUDO_START_OFFSETS,
    LUDO_TRACK_LENGTH,
};

Object.assign(TV, GAME_RULES_EXPORTS);

if (typeof module === "object" && module.exports && !(root && root.document)) {
    module.exports = GAME_RULES_EXPORTS;
    return;
}

const {
    escapeHtml,
    TVView,
    TVEvent,
    wrapTextLines,
    renderHotkeyMarkup,
    TVDialog,
    TVRect,
    TVStaticText,
    TVGroup,
    TVButton,
    bfNormal,
    bfDefault,
    TVLabel,
    TVInputLine,
    TVInfoRow,
    TVInfoBox,
    TVRadioButtons,
    TVCheckBoxes,
    TV_HELP_CONTEXTS,
    fillBorders,
    PUZZLE_START,
    PUZZLE_HIGHLIGHT_MAP,
    evMouseDown,
    evKeyDown,
    evCommand,
    sfDisabled,
    sfModal,
    sfActive,
    sfFocused,
    ofSelectable,
    ofFramed,
    ofPreProcess,
    ofCentered,
} = TV;

const openGamePalettes = new Set();
let gamePaletteObserver = null;
let gameApplicationColors = null;

const gameEffects = new Set();
let gameEffectTimer = null;
let gameMotionPreference = null;

function activeGame(view) {
    while (view && !(view instanceof TVGameDialog)) { view = view.owner; }
    return view?.isActive() || false;
}
function gameEffectAttribute(view, attribute) {
    const data = view.cell || {};
    if (data.ghost) { attribute &= 0xf7; }
    if (gameMotionPreference?.matches || !activeGame(view)) { return attribute; }
    let effect = data.flash ? { attribute: data.flash, duration: data.flashDuration || 160 }
        : data.pulse ? { attribute: attribute ^ 8, duration: 600 } : null;
    for (let owner = view; owner; owner = owner.owner) { if (owner.gameFlash) { effect = owner.gameFlash; } }
    if (!effect) { return attribute; }
    return Math.floor(performance.now() / (effect.duration / 2)) % 2 ? effect.attribute : attribute;
}
function syncGameEffects() {
    const needed = !gameMotionPreference?.matches && [...gameEffects].some(activeGame);
    if (needed && !gameEffectTimer) {
        gameEffectTimer = window.setInterval(() => {
            for (const view of gameEffects) { if (view.root) { paintGameTree(view); } }
        }, 50);
    } else if (!needed && gameEffectTimer) {
        window.clearInterval(gameEffectTimer); gameEffectTimer = null;
        gameEffects.forEach(paintGameTree);
    }
}
function trackGameEffect(view) {
    if (view.root && (view.cell?.flash || view.cell?.pulse || view.gameFlash)) { gameEffects.add(view); }
    else { gameEffects.delete(view); }
    syncGameEffects();
}

function gameAppColor(index) {
    if (!gameApplicationColors) {
        gameApplicationColors = new Map(TV.buildPaletteFromCurrentStyle().flatMap(group => group.items.map(item => [item.paletteIndex, item.attr])));
    }
    return gameApplicationColors.get(index) ?? TV.TV2_APP_COLOR_ATTRIBUTES[index - 1];
}

function paletteGroupOwner(view) {
    for (let owner = view.owner; owner; owner = owner.owner) { if (owner instanceof TVGamePaletteGroup) { return owner; } }
    return null;
}

function gamePalette(view, attribute) { return [gameEffectAttribute(view, attribute) + (paletteGroupOwner(view) ? 2 : 0)]; }
function gamePaper(view) { return (paletteGroupOwner(view)?.getPaletteAttribute() ?? gameAppColor(37)) & 0xf0; }
function gameInk(view, foreground) { return gamePaper(view) | foreground; }
function gameFrameColor(view) {
    let owner = view;
    while (owner && !(owner instanceof TVGameDialog)) { owner = owner.owner; }
    return gameInk(view, gameAppColor(owner?.getState(sfActive) ? 33 : 32) & 15);
}
function swapGameColor(attribute) { return ((attribute & 15) << 4) | (attribute >> 4); }

function paintGameTree(view) {
    view._drawPalette();
    view.children?.forEach(paintGameTree);
}

function watchGamePalette(view, enable) {
    if (!enable) {
        openGamePalettes.delete(view);
        for (const effect of gameEffects) {
            let owner = effect; while (owner && owner !== view) { owner = owner.owner; }
            if (owner === view) { gameEffects.delete(effect); }
        }
    }
    else { openGamePalettes.add(view); }
    if (openGamePalettes.size && !gamePaletteObserver) {
        gamePaletteObserver = new MutationObserver(() => {
            gameApplicationColors = null;
            for (const game of openGamePalettes) {
                if (game.destroyed || !game.isOpen()) { continue; }
                if (game.gameView) { game.gameView.render(); } else { game.render?.(); }
                paintGameTree(game);
            }
        });
        gamePaletteObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["style"] });
    } else if (!openGamePalettes.size && gamePaletteObserver) {
        gamePaletteObserver.disconnect(); gamePaletteObserver = null; gameApplicationColors = null;
    }
    if (openGamePalettes.size && !gameMotionPreference) {
        gameMotionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
        gameMotionPreference.addEventListener("change", syncGameEffects);
    } else if (!openGamePalettes.size && gameMotionPreference) {
        gameMotionPreference.removeEventListener("change", syncGameEffects); gameMotionPreference = null;
    }
    if (enable) {
        const restore = item => { if (item.cell?.flash || item.cell?.pulse || item.gameFlash) { gameEffects.add(item); } item.children?.forEach(restore); };
        restore(view); paintGameTree(view);
    }
    syncGameEffects();
}

function bindGamePalette(view, root) {
    if (!view._gamePaletteEvents) {
        view._gamePaletteEvents = Object.fromEntries(["mouseenter", "mouseleave", "focus", "blur"].map(type => [type, () => {
            if (type === "mouseenter" || type === "mouseleave") { view._gameHovered = type === "mouseenter"; }
            else { view._gameFocused = type === "focus"; }
            paintGameTree(view);
        }]));
    }
    for (const [type, handler] of Object.entries(view._gamePaletteEvents)) {
        view._gamePaletteRoot?.removeEventListener(type, handler); root?.addEventListener(type, handler);
    }
    view._gamePaletteRoot = root; view._gameHovered = false; view._gameFocused = false;
    if (!root) { gameEffects.delete(view); syncGameEffects(); }
    if (root) { view._drawPalette(); }
}

class TVGamePaletteGroup extends TVGroup {
    _drawRole() { return "game-board"; }
    getPaletteAttribute() { return gameAppColor(37); }
    getPalette() {
        const nested = Boolean(paletteGroupOwner(this));
        if (!this._gamePalette || this._nestedGamePalette !== nested) {
            this._gamePalette = [0, ...Array.from({ length: 256 }, (_, index) => nested ? index + 2 : index)];
            this._nestedGamePalette = nested;
        }
        this._gamePalette[0] = gameEffectAttribute(this, this.getPaletteAttribute()) + (nested ? 2 : 0);
        return this._gamePalette;
    }
    bindRoot(root) { if (root === this.root) { return this; } super.bindRoot(root); bindGamePalette(this, root); return this; }
    destroy() { this.bindRoot(null); }
}

class TVGameText extends TVStaticText {
    _drawRole() { return ""; }
    getPaletteAttribute() { return this.attribute ?? (gamePaper(this) | (gameAppColor(37) & 15)); }
    getPalette() { return gamePalette(this, this.getPaletteAttribute()); }
    bindRoot(root) {
        if (root === this.root) { return this; }
        super.bindRoot(root); this._drawPalette();
        if (!root) { gameEffects.delete(this); syncGameEffects(); }
        return this;
    }
}
class TVGameFrameText extends TVGameText { getPaletteAttribute() { return gameFrameColor(this); } }

class TVGameButton extends TVButton {
    getPaletteAttribute() { return gamePaper(this) | (gameAppColor(37) & 15); }
    getPalette() { return gamePalette(this, this.getPaletteAttribute()); }
    _drawParts() {
        return { ...super._drawParts(), dialog: false, className: "tv-game-cell", style: this._paletteStyle() };
    }
    bindRoot(root) { if (root === this.root) { return this; } super.bindRoot(root); bindGamePalette(this, root); return this; }
}

function tileAttribute(view) {
    const data = view.cell;
    const base = data.frame ? gameFrameColor(view) : data.attribute ?? gameInk(view, data.foreground ?? (gameAppColor(37) & 15));
    if ((view._gameHovered || view._gameFocused) && !view.disabled && data.hotAttribute !== undefined) { return data.hotAttribute; }
    return base;
}
function paintGameTile(view) {
    if (!view.root) { return; }
    view._drawPalette();
    trackGameEffect(view);
    if (view.cell.label) { view.root.setAttribute("aria-label", view.cell.label); }
}
function setGameFlash(view, attribute, enable, duration = 160) {
    if (!view) { return; }
    view.gameFlash = enable ? { attribute, duration } : null;
    trackGameEffect(view); paintGameTree(view);
}
function sameGameTile(before, after) {
    return ["text", "kind", "attribute", "foreground", "frame", "hotAttribute", "label", "selected", "disabled", "tabIndex",
        "ghost", "pulse", "flash", "flashDuration"].every(key => before[key] === after[key]);
}
class TVGameTile extends TVGameText {
    constructor(bounds) { super(bounds, ""); this.cell = {}; }
    _drawRole() { return "game-cell"; }
    bindRoot(root) { super.bindRoot(root); if (this.cell) { paintGameTile(this); } return this; }
    getPaletteAttribute() { return tileAttribute(this); }
    setData(cell) {
        if (sameGameTile(this.cell, cell)) { return this; }
        this.cell = { ...cell }; this.setText(cell.text || " "); paintGameTile(this); return this;
    }
    destroy() { this.bindRoot(null); }
}
class TVGameTileButton extends TVGameButton {
    constructor(bounds, title, command, flags = bfNormal) { super(bounds, title, command, flags); this.cell = {}; }
    bindRoot(root) { super.bindRoot(root); if (this.cell) { paintGameTile(this); } return this; }
    getPaletteAttribute() { return tileAttribute(this); }
    _drawParts() {
        return { ...super._drawParts(), className: "tv-game-cell", labelMarkup: escapeHtml(this.title),
            ariaLabel: this.cell.label || "", tabIndex: this.cell.tabIndex ?? 0 };
    }
    setData(cell) {
        if (sameGameTile(this.cell, cell)) { return this; }
        this.cell = { ...cell };
        if (this.title !== cell.text) { this.setTitle(cell.text || " "); }
        this.setState(sfDisabled, Boolean(cell.disabled)); paintGameTile(this);
        if (this.root && this.root.tabIndex !== (cell.tabIndex ?? 0)) { this.root.tabIndex = cell.tabIndex ?? 0; }
        return this;
    }
}
class TVGameStatus extends TVStaticText {
    _drawAttrs(attrs = {}) { return super._drawAttrs({ ...attrs, "aria-live": "polite" }); }
}

class TVGameBoard extends TVGamePaletteGroup {
    constructor(bounds) {
        super(bounds);
        this.cells = [];
        this.columns = 0;
        this.messageText = "";
        this.message = new TVGameText(new TVRect(), "");
        this.message.attribute = this.constructor.messageAttribute ?? 0x0e;
        this.message.hide();
        this.insert(this.message);
    }
    getPaletteAttribute() { return this.constructor.attribute ?? 0x00; }
    setGrid(columns, data) {
        this.columns = columns;
        while (this.cells.length > data.length) {
            const cell = this.cells.pop(), root = cell.root;
            cell.destroy(); root?.remove(); this.remove(cell);
        }
        data.forEach((value, index) => {
            const x = (index % columns) * 2, y = Math.floor(index / columns), bounds = new TVRect(x, y, x + 2, y + 1);
            let cell = this.cells[index];
            if (!cell) {
                const command = this.constructor.cellCommand;
                cell = command ? new TVGameTileButton(bounds, "", command).setValue(index) : new TVGameTile(bounds);
                this.cells.push(cell); this.insertBefore(cell, this.message); cell.setData(value);
                if (this.root) { const root = TVView._fromHTML(cell.draw()); this.root.insertBefore(root, this.message.root); cell.resolve(root); }
            } else {
                if (!cell.bounds.equals(bounds)) { cell.locate(bounds); }
                cell.setData(value);
            }
        });
        return this;
    }
    changeBounds(bounds) { super.changeBounds(bounds); this.setMessage(this.messageText); return this; }
    setMessage(text = "") {
        this.messageText = text;
        if (!text) { this.message.hide(); return this; }
        const width = Math.min(this.size.x, Math.max(...text.split("\n").map(line => line.length)) + 4);
        const lines = wrapTextLines(text, Math.max(1, width - 4));
        const height = Math.min(this.size.y, lines.length + 2);
        const x = Math.floor((this.size.x - width) / 2), y = Math.floor((this.size.y - height) / 2);
        this.message.locate(new TVRect(x, y, x + width, y + height));
        this.message.setText("\x03\n" + lines.join("\n")); this.message.show(); return this;
    }
}

class TVBreakOutField extends TVGameBoard { static viewName = "break-field"; }
class TVSokobanField extends TVGameBoard { static viewName = "sokoban-field"; static messageAttribute = 0x1e; }
class TVLinesField extends TVGameBoard { static viewName = "lines-grid"; static attribute = 0x11; static messageAttribute = 0x1e; static cellCommand = "lines-cell"; }
class TVReversiField extends TVGameBoard { static viewName = "reversi-grid"; static attribute = 0x22; static cellCommand = "reversi-cell"; }
class TVTronField extends TVGameBoard {
    static viewName = "tron-field";
    _drawAttrs(attrs = {}) { return super._drawAttrs({ ...attrs, role: "img", "aria-label": "Tron arena" }); }
}
class TVSnakeField extends TVGameBoard { static viewName = "snake-field"; }

const {
    hcGames,
    hcPuzzle,
    hcTetris,
    hcMines,
    hcBreakOut,
    hcSokoban,
    hcLines,
    hcReversi,
    hcLudo,
    hcMastermind,
    hcSnake,
    hcHanoi,
    hcTron,
} = TV_HELP_CONTEXTS;

class TVMinesFaceButton extends TVGameButton {
    _drawParts() {
        return { ...super._drawParts(), dialog: false, className: "tv-game-cell" };
    }
}

class TVLudoPlayerButton extends TVGameButton {
    getPaletteAttribute() { return this._gameHovered || this._gameFocused ? gameAppColor(58) : gameInk(this, this.off ? 8 : [12, 10, 14, 9][this.value]); }
    _drawParts() {
        const data = this.commandData;
        return {
            ...super._drawParts(), dialog: false,
            className: "tv-game-cell",
            labelMarkup: TVInfoBox.rowHtml(Math.max(0, this.size.x - 2), this.title, ""),
            ariaLabel: `${data.playerName || this.title} player mode`,
        };
    }
}

// ── Best score helpers ──────────────────────────────────────────────

function loadBest(key) {
    try {
        const raw = localStorage.getItem(key);
        if (!raw) { return { score: 0, name: "" }; }
        // New JSON format
        if (raw.startsWith("{")) {
            const obj = JSON.parse(raw);
            return { score: Number(obj.score) || 0, name: String(obj.name || "") };
        }
        // Old number-only format
        return { score: parseInt(raw, 10) || 0, name: "" };
    } catch { return { score: 0, name: "" }; }
}

function saveBest(key, score, name) {
    try { localStorage.setItem(key, JSON.stringify({ score, name })); }
    catch { /* ignore */ }
}

let bestNamePromptSequence = 0;

class TVBestNameDialog extends TVDialog {
    static viewName = "best";

    constructor(ownerDialog, score, callback, {
    heading = "New High Score!",
    scoreLabel = "Score",
    } = {}) {
        const nameInput = new TVInputLine(new TVRect(1, 6, 27, 7), 15);
        const nameLabel = new TVLabel(new TVRect(1, 5, 27, 6), "Your name:", nameInput);
        const okButton = new TVButton(new TVRect(9, 8, 19, 10), '~O~K', "best-ok", bfDefault);
        const body = new TVGroup(new TVRect(0, 0, (0) + (28), (0) + (10))).insertAll([
            new TVStaticText(new TVRect(0, 1, 28, 2), `\x03${heading}`),
            new TVStaticText(new TVRect(0, 3, 28, 4), `\x03${scoreLabel}: ${score}`),
            nameLabel,
            nameInput,
            okButton,
        ]);
        super(new TVRect(0, 0, 32, 13), "High Score");
        this.setHelpCtx(ownerDialog?.getHelpCtx?.() || hcGames);
        this.insert(body);
        this.setState(sfModal, true);
        this.nameInput = nameInput;
        this.okButton = okButton;
        this.callback = callback;
        this.finished = false;
        this.bindCommonClose(() => this.finish());
        this.bindDrag();
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand && event.command === "best-ok") {
            this.finish();
            this.clearEvent(event);
        } else if (event.what === evKeyDown && event.infoPtr === this.nameInput && event.nativeEvent.key === "Enter") {
            event.nativeEvent.preventDefault();
            this.finish();
            this.clearEvent(event);
        }
    }

    finish() {
        if (this.finished) { return; }
        this.finished = true;
        const name = this.nameInput.getData().trim() || "Player";
        this.destroy();
        this.callback(name);
    }

    open() {
        super.open();
        this.nameInput.focus();
    }
}

function showBestNamePrompt(ownerDialog, score, callback, options = {}) {
    const dlg = new TVBestNameDialog(ownerDialog, score, callback, options);
    const manager = ownerDialog?.manager || null;
    if (manager) {
        manager.register(`highscore:${++bestNamePromptSequence}`, dlg);
    } else {
        ownerDialog.owner?.insert(dlg);
    }
    dlg.open();
}

const HALL_OF_FAME_LIMIT = 10;
const HALL_OF_FAME_PREFIX = "tv-hall-of-fame:";
const serverHallOfFame = new Map();
const HALL_OF_FAME_GAMES = Object.freeze({
    puzzle: { title: "Puzzle", unit: "moves", lowerIsBetter: true },
    tetris: { title: "Tetris", unit: "points", legacyKey: "tv-tetris-best" },
    pentix: { title: "Pentix", unit: "points", legacyKey: "tv-pentix-best" },
    mines: { title: "Mines", unit: "seconds", lowerIsBetter: true },
    breakout: { title: "Breakout", unit: "points", legacyKey: "tv-breakout-best" },
    sokoban: { title: "Sokoban", unit: "moves", lowerIsBetter: true },
    lines: { title: "Lines", unit: "points", legacyKey: "tv-lines-best" },
    reversi: { title: "Reversi", unit: "margin" },
    ludo: { title: "Ludo", unit: "moves", lowerIsBetter: true },
    mastermind: { title: "Mastermind", unit: "turns", lowerIsBetter: true },
    hanoi: { title: "Tower of Hanoi", unit: "moves", lowerIsBetter: true },
    snake: { title: "Snake", unit: "points", legacyKey: "tv-snake-best" },
    tron: { title: "Tron Light Cycles", unit: "ticks" },
});

function hallOfFameConfig(game) {
    return HALL_OF_FAME_GAMES[game] || { title: game, unit: "points" };
}

function sortHallOfFame(game, entries) {
    if (game === "sokoban") {
        return entries.sort((left, right) => (right.level || 10) - (left.level || 10) || left.score - right.score);
    }
    const config = hallOfFameConfig(game);
    return entries.sort((left, right) => config.lowerIsBetter
        ? left.score - right.score
        : right.score - left.score);
}

function loadLocalHallOfFame(game) {
    let entries = [];
    try {
        const parsed = JSON.parse(localStorage.getItem(HALL_OF_FAME_PREFIX + game) || "[]");
        if (Array.isArray(parsed)) {
            entries = parsed.filter((entry) => Number.isFinite(Number(entry?.score)) && Number(entry.score) > 0)
                .map((entry) => ({
                    name: String(entry.name || "Player").slice(0, 15),
                    score: Number(entry.score),
                    note: String(entry.note || "").slice(0, 12),
                    level: game === "sokoban" ? Number(entry.level) || 10 : 0,
                }));
        }
    } catch { /* ignore invalid saved data */ }
    const config = hallOfFameConfig(game);
    if (!entries.length && config.legacyKey) {
        const best = loadBest(config.legacyKey);
        if (best.score > 0) {
            entries.push({ name: best.name || "Player", score: best.score, note: "" });
        }
    }
    return sortHallOfFame(game, entries).slice(0, HALL_OF_FAME_LIMIT);
}

function normalizeHallOfFameEntries(game, entries) {
    if (!Array.isArray(entries)) { return []; }
    return sortHallOfFame(game, entries
        .filter((entry) => Number.isFinite(Number(entry?.score)) && Number(entry.score) > 0)
        .map((entry) => ({
            name: String(entry.name || "Player").slice(0, 15),
            score: Number(entry.score),
            note: String(entry.note || "").slice(0, 12),
            level: game === "sokoban" ? Number(entry.level) || 10 : 0,
        }))).slice(0, HALL_OF_FAME_LIMIT);
}

function loadHallOfFame(game) {
    return serverHallOfFame.get(game) || loadLocalHallOfFame(game);
}

async function loadServerHallOfFame(game) {
    const response = await fetch(`/api/hall-of-fame/${encodeURIComponent(game)}`, { cache: "no-store" });
    if (!response.ok) { throw new Error(`HTTP ${response.status}`); }
    const payload = await response.json();
    const entries = normalizeHallOfFameEntries(game, payload?.entries);
    serverHallOfFame.set(game, entries);
    return entries;
}

function hallOfFameQualifies(game, score, level = 0) {
    if (!Number.isFinite(score) || score <= 0) { return false; }
    const entries = loadHallOfFame(game);
    if (entries.length < HALL_OF_FAME_LIMIT) { return true; }
    const last = entries[entries.length - 1];
    if (game === "sokoban") {
        return level > last.level || (level === last.level && score < last.score);
    }
    return hallOfFameConfig(game).lowerIsBetter ? score < last.score : score > last.score;
}

function saveLocalHallOfFameScore(game, score, name, note = "", level = 0) {
    if (!Number.isFinite(score) || score <= 0) { return false; }
    const entries = loadLocalHallOfFame(game);
    entries.push({ name: String(name || "Player").slice(0, 15), score, note: String(note || "").slice(0, 12), level });
    const sorted = sortHallOfFame(game, entries).slice(0, HALL_OF_FAME_LIMIT);
    try {
        localStorage.setItem(HALL_OF_FAME_PREFIX + game, JSON.stringify(sorted));
        return true;
    } catch {
        return false;
    }
}

async function saveHallOfFameScore(game, score, name, note = "", level = 0) {
    if (!Number.isFinite(score) || score <= 0) { return false; }
    const entry = {
        name: String(name || "Player").slice(0, 15),
        score,
        note: String(note || "").slice(0, 12),
        level,
    };
    try {
        const response = await fetch(`/api/hall-of-fame/${encodeURIComponent(game)}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(entry),
        });
        if (!response.ok) { throw new Error(`HTTP ${response.status}`); }
        const payload = await response.json();
        serverHallOfFame.set(game, normalizeHallOfFameEntries(game, payload?.entries));
        return payload?.accepted !== false;
    } catch {
        return saveLocalHallOfFameScore(game, score, name, note, level);
    }
}

function submitHallOfFameScore(ownerDialog, game, score, {
    name = "",
    note = "",
    level = 0,
    onSaved = null,
} = {}) {
    if (!hallOfFameQualifies(game, score, level)) {
        return false;
    }
    const save = (playerName) => {
        void saveHallOfFameScore(game, score, playerName, note, level).then((saved) => {
            if (saved && onSaved) { onSaved(playerName); }
        });
    };
    if (name) {
        save(name);
    } else {
        const config = hallOfFameConfig(game);
        showBestNamePrompt(ownerDialog, score, save, {
            heading: "Hall of Fame!",
            scoreLabel: game === "sokoban" ? `Moves, level ${level}` : config.unit[0].toUpperCase() + config.unit.slice(1),
        });
    }
    return true;
}

function formatHallOfFameScore(game, entry) {
    if (game === "sokoban") { return `${entry.score} moves Lv.${entry.level || 10}`; }
    const config = hallOfFameConfig(game);
    const note = entry.note ? ` ${entry.note}` : "";
    return `${entry.score} ${config.unit}${note}`;
}

class TVHallOfFameDialog extends TVDialog {
    static viewName = "hall";

    constructor(title, helpCtx, body) {
        super(new TVRect(0, 0, 45, 15), title);
        this.setHelpCtx(helpCtx);
        this.insert(body);
        this.body = body;
        this.setState(sfModal, true);
    }

    open() { super.open(); watchGamePalette(this, true); }
    close() { watchGamePalette(this, false); super.close(); }
    destroy() { watchGamePalette(this, false); super.destroy(); releaseGameChildren(this); }

    setRows(rows) {
        releaseGameChildren(this.body);
        this.body.children.slice().forEach((view) => this.body.remove(view));
        this.body.insertAll(rows);
        this.drawContent();
    }
}

class TVHallRow extends TVGamePaletteGroup {
    constructor(bounds, kind, rank, player, score) {
        super(bounds);
        this.kind = String(kind || "");
        this.insertAll([
            new TVStaticText(new TVRect(1, 0, 5, 1), rank),
            new TVStaticText(new TVRect(6, 0, 24, 1), player),
            new TVStaticText(new TVRect(25, 0, 42, 1), String(score).padStart(17)),
        ]);
    }

    getPaletteAttribute() { return gameAppColor(this.kind === "hall-header" ? 58 : 57); }
}

function hallOfFameRows(game, entries) {
    const rows = entries.length
        ? entries.map((entry, index) => new TVHallRow(
            new TVRect(0, index + 2, 43, index + 3),
            "hall-row",
            `${String(index + 1).padStart(2, " ")}.`,
            entry.name,
            formatHallOfFameScore(game, entry),
        ))
        : [new TVStaticText(new TVRect(1, 3, 42, 4), "\x03No scores yet.")];
    return [
        new TVHallRow(new TVRect(0, 1, 43, 2), "hall-header", "#", "Player", game === "sokoban" ? "Score / Level" : "Score"),
        ...rows,
    ];
}

function showHallOfFame(ownerDialog, game) {
    const config = hallOfFameConfig(game);
    const body = new TVGamePaletteGroup(new TVRect(0, 0, 43, 13)).insertAll(
        hallOfFameRows(game, loadHallOfFame(game)),
    );
    body.getPaletteAttribute = () => gameAppColor(57);
    const dlg = new TVHallOfFameDialog(
        `${config.title} Hall of Fame`,
        ownerDialog?.getHelpCtx?.() || hcGames,
        body,
    );
    const manager = ownerDialog?.manager || null;
    if (manager) {
        manager.register(`hall:${game}:${++bestNamePromptSequence}`, dlg);
    } else {
        ownerDialog.owner?.insert(dlg);
    }
    dlg.bindCommonClose(() => dlg.destroy());
    dlg.bindDrag();
    dlg.open();
    void loadServerHallOfFame(game).then((entries) => {
        if (!dlg.destroyed) { dlg.setRows(hallOfFameRows(game, entries)); }
    }).catch(() => {});
}

function releaseGameChildren(owner) {
    for (const view of owner.children || []) {
        releaseGameChildren(view); view.destroy?.(); view.bindRoot(null);
    }
}

class TVGameDialog extends TVDialog {
    destroy() {
        if (this.destroyed) { return; }
        watchGamePalette(this, false);
        super.destroy();
        releaseGameChildren(this);
    }

    getGameResult() {
        const status = String(this.game?.status || "").toLowerCase();
        if (this.solved || this.won || status === "won") { return "won"; }
        if (status === "lost") { return "lost"; }
        if (status === "draw") { return "draw"; }
        if (this.gameOver) { return "lost"; }
        return "abandoned";
    }

    open() {
        const wasOpen = this.isOpen();
        super.open();
        if (!this.destroyed) { watchGamePalette(this, true); }
        if (!wasOpen && this.hallOfFameGame) {
            void loadServerHallOfFame(this.hallOfFameGame).catch(() => {});
        }
    }

    close() { watchGamePalette(this, false); super.close(); }

    setState(state, enable) {
        const result = super.setState(state, enable);
        if ((state & sfActive) !== 0 && this.root) { paintGameTree(this); syncGameEffects(); }
        return result;
    }

    setHallOfFame(game) {
        this.hallOfFameGame = String(game || "");
        const button = this.frame.createTitleControl(
            "hall-of-fame",
            "H",
            `${hallOfFameConfig(this.hallOfFameGame).title} Hall of Fame`,
        );
        this.titlebar?.appendChild(button);
        return this;
    }

    handleEvent(event) {
        if ((event.what & (evCommand | evKeyDown | evMouseDown)) !== 0 && !this.isActive()) {
            this.clearEvent(event); return;
        }
        super.handleEvent(event);
        if (event.what === evCommand && event.command === "hall-of-fame" && this.hallOfFameGame) {
            showHallOfFame(this, this.hallOfFameGame);
            this.clearEvent(event);
        }
    }
}

function installHallOfFame(ownerDialog, game) {
    ownerDialog.setHallOfFame(game);
}

// ── Puzzle (15-game) ────────────────────────────────────────────────

class TVPuzzleCellButton extends TVGameButton {
    getPaletteAttribute() {
        return this._gameHovered || this._gameFocused ? gameAppColor(135) : gameAppColor(this.highlighted ? 14 : 13);
    }
    _drawParts() {
        return {
            ...super._drawParts(), dialog: false,
            className: `tv-game-cell${this.highlighted ? " is-highlight" : ""}${this.title === " " ? " is-blank" : ""}`,
            labelMarkup: escapeHtml(` ${this.title} `),
            ariaLabel: this.title === " " ? "Blank tile" : `Puzzle tile ${this.title}`,
        };
    }

    setTile(value, highlighted) {
        this.highlighted = Boolean(highlighted);
        if (this.title !== value) { this.setTitle(value); }
        if (this.root) {
            this.root.classList.toggle("is-highlight", this.highlighted);
            this.root.classList.toggle("is-blank", this.title === " ");
            this._drawPalette();
            const label = this._drawParts().ariaLabel;
            if (this.root.getAttribute("aria-label") !== label) { this.root.setAttribute("aria-label", label); }
        }
    }
}

class TVPuzzleBoard extends TVGamePaletteGroup {
    static viewName = "puzzle-grid";
    getPaletteAttribute() { return gameAppColor(13); }

    constructor(bounds) {
        super(bounds);
        this.cells = PUZZLE_START.map((value, index) => {
            const x = (index % 4) * 3, y = Math.floor(index / 4);
            return new TVPuzzleCellButton(new TVRect(x, y, x + 3, y + 1), value, "puzzle-tile", bfNormal).setValue(index);
        });
        this.insertAll(this.cells);
    }

    setBoard(board, solved) {
        this.cells.forEach((cell, index) => {
            const value = board[index], code = value === " " ? -1 : value.charCodeAt(0) - 65;
            cell.setTile(value, !solved && code >= 0 && PUZZLE_HIGHLIGHT_MAP[code] === 1);
        });
    }
}

class TVPuzzleDialog extends TVGameDialog {
    static viewName = "puzzle";
    static palette = "viewer";

    constructor() {
        const GRID_W = 12;  // 4 cols × 3ch
        const INFO_X = GRID_W + 1;
        const INFO_W = 5;
        const gridView = new TVPuzzleBoard(new TVRect(0, 0, GRID_W, 4));
        const movesView = new TVStaticText(new TVRect(INFO_X, 1, INFO_X + INFO_W, 2), "0");
        const puzzleMain = new TVGroup(new TVRect(0, 0, INFO_X + INFO_W, 4)).insertAll([
                gridView,
                new TVStaticText(new TVRect(INFO_X, 0, INFO_X + INFO_W, 1), "Move"),
                movesView,
            ]);
        super(new TVRect(0, 0, 20, 6), "Puzzle");
        this.setHelpCtx(hcPuzzle);
        this.insert(puzzleMain);
        installHallOfFame(this, "puzzle");
        this.gridView = gridView;
        this.movesView = movesView;
        this.board = [...PUZZLE_START];
        this.moves = 0;
        this.solved = false;
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.scramble();
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand && event.command === "puzzle-tile" && this.gridView.cells.includes(event.infoPtr)) {
            if (this.solved) { this.scramble(); }
            else { this.moveTile(event.infoPtr.value); }
            this.clearEvent(event);
        } else if (event.what === evKeyDown && this.isActive() && !(event.infoPtr instanceof TVInputLine)) {
            const key = event.nativeEvent?.key || "";
            if (this.solved && (key.startsWith("Arrow") || key.length === 1)) {
                event.nativeEvent.preventDefault();
                this.scramble();
                this.clearEvent(event);
            } else if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(key)) {
                event.nativeEvent.preventDefault();
                this.moveByKey(key);
                this.clearEvent(event);
            }
        }
    }

    open() {
        super.open();
        this.render();
    }

    blankIndex() {
        return this.board.indexOf(" ");
    }

    moveByKey(key) {
        const blank = this.blankIndex();
        const x = blank % 4;
        const y = Math.floor(blank / 4);
        let target = -1;
        if (key === "ArrowDown" && y > 0) {
            target = blank - 4;
        } else if (key === "ArrowUp" && y < 3) {
            target = blank + 4;
        } else if (key === "ArrowRight" && x > 0) {
            target = blank - 1;
        } else if (key === "ArrowLeft" && x < 3) {
            target = blank + 1;
        }
        if (target >= 0) {
            this.swapWithBlank(target);
        }
    }

    moveTile(index) {
        const blank = this.blankIndex();
        const diff = index - blank;
        const sameRow = Math.floor(index / 4) === Math.floor(blank / 4);
        if ((Math.abs(diff) === 1 && sameRow) || Math.abs(diff) === 4) {
            this.swapWithBlank(index);
        }
    }

    swapWithBlank(index) {
        const blank = this.blankIndex();
        [this.board[blank], this.board[index]] = [this.board[index], this.board[blank]];
        this.moves = Math.min(999, this.moves + 1);
        this.checkSolved();
        this.render();
    }

    checkSolved() {
        const wasSolved = this.solved;
        this.solved = this.board.every((value, index) => value === PUZZLE_START[index]);
        if (!wasSolved && this.solved) {
            submitHallOfFameScore(this, "puzzle", this.moves);
        }
    }

    scramble() {
        this.board = [...PUZZLE_START];
        this.moves = 0;
        this.solved = false;
        let lastBlank = -1;
        for (let step = 0; step < 120; step += 1) {
            const blank = this.blankIndex();
            const x = blank % 4;
            const y = Math.floor(blank / 4);
            const candidates = [];
            if (y > 0) {
                candidates.push(blank - 4);
            }
            if (y < 3) {
                candidates.push(blank + 4);
            }
            if (x > 0) {
                candidates.push(blank - 1);
            }
            if (x < 3) {
                candidates.push(blank + 1);
            }
            const filtered = candidates.filter((candidate) => candidate !== lastBlank);
            const choicePool = filtered.length ? filtered : candidates;
            const choice = choicePool[Math.floor(Math.random() * choicePool.length)];
            lastBlank = blank;
            [this.board[blank], this.board[choice]] = [this.board[choice], this.board[blank]];
        }
        if (this.board.every((value, index) => value === PUZZLE_START[index])) {
            [this.board[15], this.board[14]] = [this.board[14], this.board[15]];
        }
        this.render();
    }

    render() {
        this.gridView.setBoard(this.board, this.solved);
        this.movesView.setText(String(this.moves).padStart(3, " "));
    }
}

// ── Tetris (DOS Navigator style) ────────────────────────────────────

const TETRIS_COLS = 12;  // DN: Shi = 12
const TETRIS_ROWS = 18;
const TETRIS_PREVIEW_COLS = 7;
const TETRIS_PREVIEW_ROWS = 7;
const TETRIS_INFO_WIDTH = 23;
const TETRIS_FIGURES = [
    [[0,2],[1,2],[2,2],[2,1]],
    [[0,1],[1,1],[2,1],[2,2]],
    [[0,1],[1,1],[2,1],[3,1]],
    [[1,1],[1,2],[2,1],[2,2]],
    [[0,1],[1,1],[1,2],[2,1]],
    [[0,1],[1,1],[1,2],[2,2]],
    [[0,2],[1,2],[1,1],[2,1]],
    [[0,0]],
    [[0,0],[1,0]],
    [[0,1],[1,1],[2,1]],
    [[0,0],[1,0],[1,1]],
    [[0,2],[1,2],[2,2],[3,2],[4,2]],
    [[0,1],[1,0],[1,1],[1,2],[2,1]],
    [[1,1],[1,2],[2,1],[2,2],[2,3]],
    [[1,1],[1,2],[2,0],[2,1],[2,2]],
    [[0,0],[0,2],[1,0],[1,1],[1,2]],
    [[0,0],[1,0],[1,1],[2,1],[2,2]],
    [[0,1],[1,1],[2,1],[2,2],[3,2]],
    [[0,2],[1,2],[2,1],[2,2],[3,1]],
    [[0,0],[0,1],[1,1],[2,1],[2,2]],
    [[0,1],[0,2],[1,1],[2,0],[2,1]],
    [[0,0],[1,0],[1,1],[1,2],[2,1]],
    [[0,2],[1,0],[1,1],[1,2],[2,1]],
    [[0,0],[0,1],[0,2],[1,1],[2,1]],
    [[0,1],[1,1],[1,2],[2,1],[3,1]],
    [[0,2],[1,1],[1,2],[2,2],[3,2]],
    [[0,0],[1,0],[2,0],[2,1],[2,2]],
    [[0,2],[0,1],[1,2],[2,2],[3,2]],
];
const TETRIS_CELL_COUNT = [
    4,4,4,4,4,4,4, 1,2,3,3, 5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5
];
const TETRIS_CROT = [
    4,4,4,4,3,4,4, 1,2,3,2, 5,3,4,4,3,3,4,4,3,3,3,3,3,4,4,3,4
];
const TETRIS_COLORS = [
    15, 14, 13, 12, 11, 10, 9,
];
const TETRIS_DELAYS = [1600, 1200, 1000, 600, 500, 400, 300, 200, 100, 80];
const TETRIS_BEST_KEY = "tv-tetris-best";
const PENTIX_BEST_KEY = "tv-pentix-best";

class TVTetrisPreview extends TVGamePaletteGroup {
    static viewName = "tetris-preview";

    constructor(bounds) {
        super(bounds);
        this.figure = null;
        this.attribute = 0x0f;
        this.leftSide = new TVGameFrameText(new TVRect(), "");
        this.field = new TVGameText(new TVRect(), "");
        this.field.attribute = this.attribute;
        this.rightSide = new TVGameFrameText(new TVRect(), "");
        this.insertAll([this.leftSide, this.field, this.rightSide]);
        this.layoutPreview();
    }

    changeBounds(bounds) {
        super.changeBounds(bounds);
        this.layoutPreview();
        return this;
    }

    layoutPreview() {
        const width = this.size.x, height = this.size.y, side = Math.min(1, width / 2);
        this.leftSide.locate(new TVRect(0, 0, side, height));
        this.field.locate(new TVRect(side, 0, Math.max(side, width - side), height));
        this.rightSide.locate(new TVRect(width - side, 0, width, height));
        const border = Array.from({ length: Math.max(0, Math.floor(height)) }, () => "│").join("\n");
        this.leftSide.setText(border);
        this.rightSide.setText(border);
        this.setData(this.figure);
    }

    getData() { return this.figure; }

    setData(figure) {
        const grid = Array.from({ length: TETRIS_PREVIEW_ROWS }, () => new Array(TETRIS_PREVIEW_COLS).fill(false));
        if (figure !== null) {
            const cells = TETRIS_FIGURES[figure];
            const rows = cells.map(([row]) => row), cols = cells.map(([, col]) => col);
            const minR = Math.min(...rows), minC = Math.min(...cols);
            const height = Math.max(...rows) - minR + 1, width = Math.max(...cols) - minC + 1;
            const offR = Math.floor((TETRIS_PREVIEW_ROWS - height) / 2) - minR;
            const offC = Math.floor((TETRIS_PREVIEW_COLS - width) / 2) - minC;
            cells.forEach(([row, col]) => { grid[row + offR][col + offC] = true; });
        }
        const padding = Math.max(0, Math.floor(this.field.size.x) - TETRIS_PREVIEW_COLS * 2);
        const text = grid.map(row => " ".repeat(Math.floor(padding / 2))
            + row.map(filled => filled ? "██" : "  ").join("")
            + " ".repeat(Math.ceil(padding / 2))).join("\n");
        const attribute = figure === null ? 0x0f : 15 - figure % 7;
        const changedColor = this.attribute !== attribute;
        this.figure = figure;
        this.attribute = attribute;
        this.field.setText(text);
        this.field.attribute = attribute;
        if (changedColor) { this.field._drawPalette(); }
        return this;
    }
}

class TVTetrisGameInfo extends TVInfoBox {

    constructor(bounds, previewView) {
        const scoreView = new TVInfoRow(new TVRect(0, 1, bounds.width, 2));
        const linesView = new TVInfoRow(new TVRect(0, 2, bounds.width, 3));
        const levelView = new TVInfoRow(new TVRect(0, 3, bounds.width, 4));
        const bestNameView = new TVInfoRow(new TVRect(0, 13, bounds.width, 14));
        const bestScoreView = new TVInfoRow(new TVRect(0, 14, bounds.width, 15));
        const nextSeparator = new TVStaticText(new TVRect(0, 4, bounds.width, 5), TVInfoBox.separator(bounds.width - 2, "Next"));
        const bestSeparator = new TVStaticText(new TVRect(0, 12, bounds.width, 13), TVInfoBox.separator(bounds.width - 2, "Best"));
        super(bounds, "Info", [
            scoreView,
            linesView,
            levelView,
            nextSeparator,
            previewView,
            bestSeparator,
            bestNameView,
            bestScoreView,
        ]);
        this.scoreView = scoreView;
        this.linesView = linesView;
        this.levelView = levelView;
        this.bestNameView = bestNameView;
        this.bestScoreView = bestScoreView;
    }

    update(game) {
        this.updateRow(this.scoreView, "Score: " + game.score);
        this.updateRow(this.linesView, "Lines: " + game.lines);
        this.updateRow(this.levelView, "Level: " + game.level);
        this.updateRow(this.bestNameView, "Name: " + (game.bestName || "Anonymous"));
        this.updateRow(this.bestScoreView, "Score: " + game.bestScore);
    }
}

class TVTetrisGameView extends TVGameBoard {
    static viewName = "tetris-grid";

    constructor(bounds) {
        super(bounds);
        this.options |= ofFramed | ofSelectable | ofPreProcess;
        this.eventMask = 0xffff;
        this.glass = [];
        this.curFig = 0;
        this.nextFig = 0;
        this.fig = [];
        this.posX = 0;
        this.posY = 0;
        this.score = 0;
        this.lines = 0;
        this.level = 1;
        this.startLevel = 1;
        this.gameOver = true;
        this.paused = false;
        this.timerId = null;
        this.pentix = false;
        this.preview = true;
        this.bestScore = 0;
        this.bestName = "";
        this.infoView = null;
        this.previewView = null;
        this._loadBestData();
    }

    attach(infoView, previewView) {
        this.infoView = infoView;
        this.previewView = previewView;
        return this;
    }

    gameWindow() {
        let view = this.owner;
        while (view && !(view instanceof TVDialog)) { view = view.owner; }
        return view;
    }

    _loadBestData() {
        const b = loadBest(this.pentix ? PENTIX_BEST_KEY : TETRIS_BEST_KEY);
        this.bestScore = b.score;
        this.bestName = b.name;
    }
    _saveBest() {
        saveBest(this.pentix ? PENTIX_BEST_KEY : TETRIS_BEST_KEY, this.bestScore, this.bestName);
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand) {
            if (event.command === "tetris-new") { this.newGame(); }
            else if (event.command === "tetris-pause") { this.togglePause(); }
            else if (event.command === "tetris-setup") { this.gameWindow()?.openSetup(); }
            else if (event.command === "tetris-top10") {
                showHallOfFame(this.gameWindow(), this.pentix ? "pentix" : "tetris");
            }
            else { return; }
            this.clearEvent(event);
        } else if (event.what === evKeyDown) {
            const nativeEvent = event.nativeEvent;
            if (!nativeEvent || nativeEvent.defaultPrevented) { return; }
            keyInput: {
                const window = this.gameWindow();
                if (!window?.isActive()) { break keyInput; }
                if (nativeEvent.key === "Escape") { nativeEvent.preventDefault(); window.close(); break keyInput; }
                if (this.gameOver) {
                    if (nativeEvent.key === "Enter" || nativeEvent.key === " ") {
                        nativeEvent.preventDefault();
                        this.newGame();
                    }
                    break keyInput;
                }
                if (this.paused) {
                    if (nativeEvent.key === "p" || nativeEvent.key === "P") {
                        nativeEvent.preventDefault();
                        this.togglePause();
                    }
                    break keyInput;
                }
                switch (nativeEvent.key) {
                    case "ArrowLeft":
                    case "Home":
                        nativeEvent.preventDefault();
                        this.moveFig(-1, 0);
                        break;
                    case "ArrowRight":
                    case "PageUp":
                        nativeEvent.preventDefault();
                        this.moveFig(1, 0);
                        break;
                    case "ArrowDown":
                    case " ":
                        nativeEvent.preventDefault();
                        this.hardDrop();
                        break;
                    case "ArrowUp":
                        nativeEvent.preventDefault();
                        this.rotate();
                        break;
                    case "n": case "N":
                        nativeEvent.preventDefault();
                        this.newGame();
                        break;
                    case "p": case "P":
                        nativeEvent.preventDefault();
                        this.togglePause();
                        break;
                }
            }
            if (nativeEvent.defaultPrevented) { this.clearEvent(event); }
        }
    }



    togglePause() {
        if (this.gameOver) { return; }
        this.paused = !this.paused;
        if (this.paused) { this.stopTimer(); } else { this.startTimer(); }
        this.render();
    }

    applySettings({ startLevel, pentix, preview }) {
        this.startLevel = Math.max(1, Math.min(10, Number(startLevel) || 1));
        this.pentix = Boolean(pentix);
        this.preview = Boolean(preview);
        this._loadBestData();
        const window = this.gameWindow();
        const title = this.pentix ? "Pentix" : "Tetris";
        if (window) {
            window.title = title;
            window.frame.drawTitle();
        }
        this.newGame();
    }

    setState(state, enable) {
        super.setState(state, enable);
        if (!enable && (state & (sfActive | sfFocused)) !== 0 && !this.gameOver && !this.paused) {
            this.togglePause();
        }
        return this;
    }

    get maxFig() { return this.pentix ? 28 : 7; }

    newGame() {
        this.glass = Array.from({ length: TETRIS_ROWS }, () => new Array(TETRIS_COLS).fill(0));
        this.score = 0;
        this.lines = 0;
        this.level = this.startLevel;
        this.gameOver = false;
        this.paused = false;
        this.nextFig = Math.floor(Math.random() * this.maxFig);
        this.spawnPiece();
        this.startTimer();
        this.render();
    }

    spawnPiece() {
        this.curFig = this.nextFig;
        this.nextFig = Math.floor(Math.random() * this.maxFig);
        const src = TETRIS_FIGURES[this.curFig];
        this.fig = src.map(([r, c]) => [r, c]);
        this.posX = (TETRIS_COLS >> 1) - 2;
        this.posY = -this.fig[0][0];
        if (!this.validMove(0, 0)) {
            this.gameOver = true;
            this.stopTimer();
            for (const [r, c] of this.fig) {
                const nr = r + this.posY;
                const nc = c + this.posX;
                if (nr >= 0 && nr < TETRIS_ROWS && nc >= 0 && nc < TETRIS_COLS) {
                    this.glass[nr][nc] = (15 - this.curFig % 7);
                }
            }
            this._checkBest();
        }
    }

    validMove(dx, dy, fig) {
        const cells = fig || this.fig;
        for (const [r, c] of cells) {
            const nr = r + this.posY + dy;
            const nc = c + this.posX + dx;
            if (nc < 0 || nc >= TETRIS_COLS || nr >= TETRIS_ROWS) { return false; }
            if (nr >= 0 && this.glass[nr][nc] !== 0) { return false; }
        }
        return true;
    }

    moveFig(dx, dy) {
        if (this.validMove(dx, dy)) {
            this.posX += dx;
            this.posY += dy;
            this.render();
            return true;
        }
        return false;
    }

    rotate() {
        const crot = TETRIS_CROT[this.curFig];
        const rotated = this.fig.map(([r, c]) => [c, crot + 1 - r]);
        const minR = Math.min(...rotated.map(([r]) => r));
        const minC = Math.min(...rotated.map(([, c]) => c));
        const normalized = rotated.map(([r, c]) => [r - minR, c - minC]);
        if (this.validMove(0, 0, normalized)) {
            this.fig = normalized;
            this.render();
        }
    }

    moveDown() {
        if (this.gameOver || this.paused) { return; }
        if (this.moveFig(0, 1)) { return; }
        for (const [r, c] of this.fig) {
            const nr = r + this.posY;
            const nc = c + this.posX;
            if (nr >= 0 && nr < TETRIS_ROWS && nc >= 0 && nc < TETRIS_COLS) {
                this.glass[nr][nc] = (15 - this.curFig % 7);
            }
        }
        const prevMul = this.preview ? 7 : 10;
        this.score += Math.floor(((TETRIS_ROWS - this.posY) * 2 + this.level * 6) * prevMul / 10);
        let cleared = 0;
        for (let row = TETRIS_ROWS - 1; row >= 0; row--) {
            if (this.glass[row].every((cell) => cell !== 0)) {
                this.glass.splice(row, 1);
                this.glass.unshift(new Array(TETRIS_COLS).fill(0));
                this.score += (cleared + TETRIS_ROWS - row) * 30;
                this.lines++;
                cleared++;
                row++;
            }
        }
        if (this.glass.every((row) => row.every((c) => c === 0))) {
            this.score += Math.floor(this.level * 300 * prevMul / 10);
        }
        const threshold = 90 - (9 - this.startLevel) * 10;
        if (this.lines > threshold) {
            const newLevel = Math.min(10, 1 + Math.floor((this.lines - threshold) / 20) + this.startLevel);
            if (newLevel > this.level) {
                this.level = Math.max(newLevel, this.startLevel);
                this.startTimer();
            }
        }
        this.spawnPiece();
        this.render();
    }

    hardDrop() {
        while (this.validMove(0, 1)) {
            this.posY++;
        }
        this.moveDown();
    }

    _checkBest() {
        const isBest = this.score > this.bestScore;
        const game = this.pentix ? "pentix" : "tetris";
        submitHallOfFameScore(this.gameWindow(), game, this.score, {
            note: `${this.startLevel}→${this.level}`,
            onSaved: (name) => {
                if (!isBest) { return; }
                this.bestScore = this.score;
                this.bestName = name;
                this._saveBest();
                this.renderInfo();
            },
        });
    }

    startTimer() {
        this.stopTimer();
        const delay = TETRIS_DELAYS[this.level - 1] || 80;
        this.timerId = setInterval(() => {
            if (!this.gameWindow()?.isActive() || this.gameOver || this.paused) { return; }
            this.moveDown();
        }, delay);
    }

    stopTimer() {
        if (this.timerId !== null) {
            clearInterval(this.timerId);
            this.timerId = null;
        }
    }

    render() {
        this.renderGrid();
        this.renderPreview();
        this.renderInfo();
    }

    renderInfo() {
        this.infoView?.update(this);
    }

    renderGrid() {
        const display = this.glass.map((row) => [...row]);

        if (!this.gameOver && !this.paused) {
            let ghostY = 0;
            while (this.validMove(0, ghostY + 1)) { ghostY++; }
            for (const [r, c] of this.fig) {
                const gr = r + this.posY + ghostY;
                const gc = c + this.posX;
                if (gr >= 0 && gr < TETRIS_ROWS && gc >= 0 && gc < TETRIS_COLS && display[gr][gc] === 0) {
                    display[gr][gc] = -1;
                }
            }
            for (const [r, c] of this.fig) {
                const nr = r + this.posY;
                const nc = c + this.posX;
                if (nr >= 0 && nr < TETRIS_ROWS && nc >= 0 && nc < TETRIS_COLS) {
                    display[nr][nc] = (15 - this.curFig % 7);
                }
            }
        }

        const color = TETRIS_COLORS[this.curFig % 7];
        this.setGrid(TETRIS_COLS, display.flatMap(row => row.map(value => value > 0
            ? { text: "██", kind: "filled", foreground: TETRIS_COLORS[(15 - value) % 7] }
            : value < 0 ? { text: "░░", kind: "ghost", foreground: color, ghost: true } : { text: "  " })));
        if (this.paused) {
            this.cells.forEach(cell => cell.hide());
            this.setMessage("PAUSED\nPress P");
        } else {
            this.cells.forEach(cell => cell.show());
            this.setMessage(this.gameOver ? `GAME OVER\nScore: ${this.score}\nPress Enter` : "");
        }
    }

    renderPreview() {
        this.previewView.setData(this.preview && !this.gameOver ? this.nextFig : null);
    }
}

class TVTetrisSetupDialog extends TVDialog {
    static viewName = "tetris-setup";

    constructor(gameView, onAccept) {
        const levelInput = new TVInputLine(new TVRect(18, 2, 22, 3), 2).setData(String(gameView.startLevel));
        const gameType = new TVRadioButtons(new TVRect(2, 5, 28, 7), [
            { label: "~T~etris", value: "tetris", checked: !gameView.pentix },
            { label: "~P~entix", value: "pentix", checked: gameView.pentix },
        ]);
        const preview = new TVCheckBoxes(new TVRect(2, 9, 28, 10), [
            { label: "Show ~n~ext piece", value: "preview", checked: gameView.preview },
        ]);
        const okButton = new TVButton(new TVRect(6, 12, 16, 14), "~O~K", "tetris-setup-ok", bfDefault);
        const cancelButton = new TVButton(new TVRect(18, 12, 28, 14), "Cancel", "tetris-setup-cancel", bfNormal);
        const body = new TVGroup(new TVRect(0, 0, 30, 14)).insertAll([
            new TVLabel(new TVRect(2, 2, 17, 3), "Starting ~l~evel", levelInput),
            levelInput,
            new TVStaticText(new TVRect(2, 4, 28, 5), "Game"),
            gameType,
            preview,
            okButton,
            cancelButton,
        ]);
        super(new TVRect(0, 0, 34, 17), "Tetris Setup");
        this.setHelpCtx(hcTetris);
        this.insert(body);
        this.setState(sfModal, true);
        this.levelInput = levelInput;
        this.gameType = gameType;
        this.preview = preview;
        this.onAccept = onAccept;
        this.bindCommonClose(() => this.destroy());
        this.bindDrag();
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what !== evCommand) { return; }
        if (event.command === "tetris-setup-ok") {
            this.onAccept({
                startLevel: this.levelInput.getData(),
                pentix: this.gameType.getData() === 1,
                preview: (this.preview.getData() & 1) !== 0,
            });
            this.destroy();
            this.clearEvent(event);
        } else if (event.command === "tetris-setup-cancel") {
            this.destroy();
            this.clearEvent(event);
        }
    }

    open() {
        super.open();
        this.levelInput.focus();
        this.levelInput.selectAll();
    }
}

class TVTetrisDialog extends TVGameDialog {
    static viewName = "tetris";

    constructor() {
        const gridWidth = TETRIS_COLS * 2;
        // DOS Navigator TGameWindow.Init: game (2,2)-(2+Shi*2,2+Vis),
        // info (4+Shi*2,1)-(27+Shi*2,Vis-3), dialog width 30+Shi*2.
        const infoX = gridWidth + 4;
        const infoWidth = TETRIS_INFO_WIDTH;
        const gameView = new TVTetrisGameView(new TVRect(2, 2, 2 + gridWidth, 2 + TETRIS_ROWS));
        const previewView = new TVTetrisPreview(new TVRect(0, 5, infoWidth, 12));
        const infoView = new TVTetrisGameInfo(new TVRect(infoX, 1, infoX + infoWidth, 17), previewView);
        gameView.attach(infoView, previewView);
        const newButton = new TVButton(new TVRect(infoX, 17, infoX + 10, 19), "~N~ew", "tetris-new", bfNormal);
        const setupButton = new TVButton(new TVRect(infoX + 11, 17, infoX + 21, 19), "~S~etup", "tetris-setup", bfNormal);
        const topButton = new TVButton(new TVRect(infoX, 19, infoX + 10, 21), "~T~op 10", "tetris-top10", bfNormal);
        const pauseButton = new TVButton(new TVRect(infoX + 11, 19, infoX + 21, 21), "~P~ause", "tetris-pause", bfNormal);
        const main = new TVGroup(new TVRect(0, 0, 52, 21)).insertAll([
            gameView,
            infoView,
            newButton,
            setupButton,
            topButton,
            pauseButton,
        ]);
        super(new TVRect(0, 0, 54, 23), "Tetris");
        this.setHelpCtx(hcTetris);
        this.options |= ofCentered;
        this.insert(main);
        installHallOfFame(this, "tetris");
        this.gameView = gameView;
        this.infoView = infoView.resolve(this.root);
        this.gameView.attach(this.infoView, previewView);
        this.bindCommonClose(() => this.close());
        this.bindDrag();
    }

    handleEvent(event) {
        super.handleEvent(event);
        this.gameView.handleEvent(event);
    }

    openSetup() {
        const dialog = new TVTetrisSetupDialog(this.gameView, (settings) => {
            this.gameView.applySettings(settings);
            this.setHelpCtx(hcTetris);
        });
        if (this.manager) {
            this.manager.register(`tetris-setup:${++bestNamePromptSequence}`, dialog);
        } else {
            this.owner?.insert(dialog);
        }
        dialog.open();
    }

    open() {
        super.open();
        this.gameView.newGame();
    }

    close() {
        this.gameView.stopTimer();
        super.close();
    }

    destroy() {
        this.gameView.stopTimer();
        super.destroy();
    }
}

// ── Minesweeper ─────────────────────────────────────────────────────

const MINES_ROWS = 9;
const MINES_COLS = 9;
const MINES_COUNT = 10;

class TVMinesCellButton extends TVGameButton {
    getPaletteAttribute() {
        if (this.cellState === "bomb") { return 0x4f; }
        if (this.cellState === "empty") { return 0x77; }
        if (this.cellState === "number") { return 0x70 | this.numberColor; }
        if (this.cellState === "flag") { return 0x74; }
        return this._gameHovered ? 0xf0 : 0x78;
    }
    _drawParts() {
        return {
            ...super._drawParts(), dialog: false,
            className: `tv-game-cell${this.cursor ? " is-cursor" : ""}${["bomb", "empty", "number"].includes(this.cellState) ? " is-readonly" : ""}`,
            labelMarkup: escapeHtml(this.title),
            ariaLabel: `Row ${Math.floor(this.value / MINES_COLS) + 1}, column ${this.value % MINES_COLS + 1}, ${this.description || "hidden"}`,
            tabIndex: this.cursor ? 0 : -1,
        };
    }

    setData({ value, revealed, flagged, gameOver, cursor }) {
        const colors = [0, 1, 2, 4, 1, 4, 3, 0, 8];
        this.cellState = revealed ? value === -1 ? (gameOver ? "bomb" : "")
            : value ? "number" : "empty" : flagged ? "flag" : "hidden";
        this.numberColor = revealed && value > 0 ? colors[value] : 0;
        this.cursor = cursor;
        this.description = revealed ? value === -1 ? "mine" : `revealed ${value || "empty"}` : flagged ? "flagged" : "hidden";
        const title = revealed ? value === -1 ? "💣" : value ? String(value) : " " : flagged ? "⚑" : "■";
        if (this.title !== title) { this.setTitle(title); }
        if (this.root) {
            this.root.classList.toggle("is-readonly", revealed);
            this.root.classList.toggle("is-cursor", this.cursor);
            this._drawPalette();
            if (this.root.tabIndex !== (this.cursor ? 0 : -1)) { this.root.tabIndex = this.cursor ? 0 : -1; }
            const label = this._drawParts().ariaLabel;
            if (this.root.getAttribute("aria-label") !== label) { this.root.setAttribute("aria-label", label); }
        }
        return this;
    }

    handleEvent(event) {
        if (event.what === evMouseDown && event.nativeEvent?.type === "contextmenu" && !this.disabled) {
            event.nativeEvent.preventDefault();
            event.what = evCommand;
            event.command = "mines-flag";
            event.infoPtr = this;
        } else { super.handleEvent(event); }
    }
}

class TVMinesField extends TVGamePaletteGroup {
    static viewName = "mines-grid";
    getPaletteAttribute() { return 0x78; }

    constructor(bounds) {
        super(bounds);
        this.cells = Array.from({ length: MINES_ROWS * MINES_COLS }, (_, index) => {
            const x = (index % MINES_COLS) * 2, y = Math.floor(index / MINES_COLS);
            return new TVMinesCellButton(new TVRect(x, y, x + 2, y + 1), "■", "mines-reveal", bfNormal).setValue(index);
        });
        this.insertAll(this.cells);
    }

    setBoard(game) {
        this.cells.forEach((cell, index) => {
            const row = Math.floor(index / MINES_COLS), col = index % MINES_COLS;
            cell.setData({ value: game.board[row][col], revealed: game.revealed[row][col],
                flagged: game.flagged[row][col], gameOver: game.gameOver,
                cursor: row === game.cursorRow && col === game.cursorCol });
        });
    }
}

class TVMinesDialog extends TVGameDialog {
    static viewName = "mines";

    constructor() {
        const GRID_W = MINES_COLS * 2;  // 18ch
        const remainingView = new TVGameText(new TVRect(1, 0, 5, 1), String(MINES_COUNT));
        remainingView.getPaletteAttribute = () => gameInk(remainingView, 4);
        const faceButton = new TVMinesFaceButton(new TVRect(9, 0, 11, 1), "☺", "mines-face", bfNormal);
        const timerView = new TVGameText(new TVRect(15, 0, 19, 1), "   0");
        timerView.getPaletteAttribute = () => gameInk(timerView, 4);
        const gridView = new TVMinesField(new TVRect(1, 1, 1 + GRID_W, 1 + MINES_ROWS));
        const minesMain = new TVGroup(new TVRect(0, 0, (0) + (GRID_W + 2), (0) + (MINES_ROWS + 1))).insertAll([
                remainingView,
                faceButton,
                timerView,
                gridView,
            ]);

        super(new TVRect(0, 0, 22, 13), "Mines");
        this.setHelpCtx(hcMines);
        this.insert(minesMain);

        installHallOfFame(this, "mines");
        this.gridView = gridView;
        this.remainingView = remainingView;
        this.timerView = timerView;
        this.faceButton = faceButton;

        this.board = [];
        this.revealed = [];
        this.flagged = [];
        this.gameOver = false;
        this.won = false;
        this.started = false;
        this.minesPlaced = false;
        this.cursorRow = 0;
        this.cursorCol = 0;
        this.timerId = null;
        this.seconds = 0;

        this.bindCommonClose(() => this.close());
        this.bindDrag();
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand && event.command === "mines-face") {
            this.newGame();
            this.clearEvent(event);
        } else if (event.what === evCommand && ["mines-reveal", "mines-flag"].includes(event.command)
            && this.isActive() && this.gridView.cells.includes(event.infoPtr)) {
            this.cursorRow = Math.floor(event.infoPtr.value / MINES_COLS);
            this.cursorCol = event.infoPtr.value % MINES_COLS;
            if (event.command === "mines-flag") { this.toggleFlag(this.cursorRow, this.cursorCol, true); }
            else { this.revealCell(this.cursorRow, this.cursorCol, true); }
            this.clearEvent(event);
        } else if (event.what === evKeyDown && this.isActive() && !(event.infoPtr instanceof TVInputLine)) {
            if (event.infoPtr instanceof TVButton && !this.gridView.cells.includes(event.infoPtr)) { return; }
            const nativeEvent = event.nativeEvent, key = nativeEvent?.key;
            if (key === " " || key === "Enter") { this.revealCell(this.cursorRow, this.cursorCol, true); }
            else if (key === "f" || key === "F") { this.toggleFlag(this.cursorRow, this.cursorCol, true); }
            else {
                if (key === "ArrowUp") { this.cursorRow = Math.max(0, this.cursorRow - 1); }
                else if (key === "ArrowDown") { this.cursorRow = Math.min(MINES_ROWS - 1, this.cursorRow + 1); }
                else if (key === "ArrowLeft") { this.cursorCol = Math.max(0, this.cursorCol - 1); }
                else if (key === "ArrowRight") { this.cursorCol = Math.min(MINES_COLS - 1, this.cursorCol + 1); }
                else if (key === "Home") { this.cursorCol = 0; }
                else if (key === "End") { this.cursorCol = MINES_COLS - 1; }
                else { return; }
                this.render(true);
            }
            nativeEvent.preventDefault();
            this.clearEvent(event);
        }
    }

    open() {
        super.open();
        this.newGame();
    }

    close() {
        this.stopTimer();
        super.close();
    }

    newGame() {
        this.board = Array.from({ length: MINES_ROWS }, () => new Array(MINES_COLS).fill(0));
        this.revealed = Array.from({ length: MINES_ROWS }, () => new Array(MINES_COLS).fill(false));
        this.flagged = Array.from({ length: MINES_ROWS }, () => new Array(MINES_COLS).fill(false));
        this.gameOver = false;
        this.won = false;
        this.started = false;
        this.minesPlaced = false;
        this.cursorRow = 0;
        this.cursorCol = 0;
        this.seconds = 0;
        this.stopTimer();
        this.render();
    }

    placeMines(safeRow, safeCol) {
        const cells = [];
        for (let r = 0; r < MINES_ROWS; r++) {
            for (let c = 0; c < MINES_COLS; c++) {
                if (r !== safeRow || c !== safeCol) {
                    cells.push([r, c]);
                }
            }
        }
        for (let index = cells.length - 1; index > 0; index--) {
            const swapIndex = Math.floor(Math.random() * (index + 1));
            [cells[index], cells[swapIndex]] = [cells[swapIndex], cells[index]];
        }
        cells.slice(0, MINES_COUNT).forEach(([r, c]) => {
            this.board[r][c] = -1;
        });
        for (let r = 0; r < MINES_ROWS; r++) {
            for (let c = 0; c < MINES_COLS; c++) {
                if (this.board[r][c] === -1) { continue; }
                let count = 0;
                for (let dr = -1; dr <= 1; dr++) {
                    for (let dc = -1; dc <= 1; dc++) {
                        const nr = r + dr;
                        const nc = c + dc;
                        if (nr >= 0 && nr < MINES_ROWS && nc >= 0 && nc < MINES_COLS && this.board[nr][nc] === -1) {
                            count++;
                        }
                    }
                }
                this.board[r][c] = count;
            }
        }
        this.minesPlaced = true;
    }

    startTimer() {
        this.stopTimer();
        this.timerId = setInterval(() => {
            if (!this.isActive()) { return; }
            this.seconds++;
            this.timerView.setText(String(this.seconds).padStart(4));
        }, 1000);
    }

    stopTimer() {
        if (this.timerId !== null) {
            clearInterval(this.timerId);
            this.timerId = null;
        }
    }

    revealCell(r, c, focusCursor = false) {
        if (this.gameOver || this.won || this.flagged[r][c]) { return; }
        if (!this.minesPlaced) {
            this.placeMines(r, c);
        }
        if (!this.started) {
            this.started = true;
            this.startTimer();
        }
        this.reveal(r, c);
        this.render(focusCursor);
    }

    toggleFlag(r, c, focusCursor = false) {
        if (this.gameOver || this.won || this.revealed[r][c]) { return; }
        this.flagged[r][c] = !this.flagged[r][c];
        this.render(focusCursor);
    }

    reveal(r, c) {
        if (r < 0 || r >= MINES_ROWS || c < 0 || c >= MINES_COLS) { return; }
        if (this.revealed[r][c] || this.flagged[r][c]) { return; }
        this.revealed[r][c] = true;
        if (this.board[r][c] === -1) {
            this.gameOver = true;
            this.stopTimer();
            for (let rr = 0; rr < MINES_ROWS; rr++) {
                for (let cc = 0; cc < MINES_COLS; cc++) {
                    if (this.board[rr][cc] === -1) { this.revealed[rr][cc] = true; }
                }
            }
            return;
        }
        if (this.board[r][c] === 0) {
            for (let dr = -1; dr <= 1; dr++) {
                for (let dc = -1; dc <= 1; dc++) {
                    this.reveal(r + dr, c + dc);
                }
            }
        }
        this.checkWin();
    }

    checkWin() {
        let unrevealed = 0;
        for (let r = 0; r < MINES_ROWS; r++) {
            for (let c = 0; c < MINES_COLS; c++) {
                if (!this.revealed[r][c]) { unrevealed++; }
            }
        }
        if (unrevealed === MINES_COUNT) {
            this.won = true;
            this.stopTimer();
            submitHallOfFameScore(this, "mines", Math.max(1, this.seconds));
        }
    }

    render(focusCursor = false) {
        this.gridView.setBoard(this);

        const flagCount = this.flagged.flat().filter(Boolean).length;
        this.remainingView.setText(String(MINES_COUNT - flagCount));
        this.timerView.setText(String(this.seconds).padStart(4));
        this.faceButton.setTitle(this.gameOver && !this.won ? "☹" : "☺");
        if (focusCursor) {
            this.gridView.cells[this.cursorRow * MINES_COLS + this.cursorCol].focus();
        }
    }
}

// ── BreakOut ────────────────────────────────────────────────────────

const BREAK_COLS = 14;
const BREAK_ROWS = 5;
const BREAK_PADDLE_W = 4;
const BREAK_BEST_KEY = "tv-breakout-best";
const BREAK_BRICK_COLORS = [12, 14, 10, 11, 9];
const BREAK_FPS = 20;

class TVBreakOutDialog extends TVGameDialog {
    static viewName = "break";

    constructor() {
        const FIELD_X = 1;                // 1ch offset from left
        const FIELD_W = BREAK_COLS * 2;  // 28ch
        const INFO_X = FIELD_X + FIELD_W + 1;  // 30ch
        const INFO_W = 19;
        const fieldView = new TVBreakOutField(new TVRect(FIELD_X, 0, FIELD_X + FIELD_W, 20));
        const newButton = new TVButton(new TVRect(INFO_X, 17, INFO_X + INFO_W, 19), '~N~ew', "break-new", bfNormal);
        const scoreRow = new TVInfoRow(new TVRect(0, 1, INFO_W, 2));
        const livesRow = new TVInfoRow(new TVRect(0, 2, INFO_W, 3));
        const levelRow = new TVInfoRow(new TVRect(0, 3, INFO_W, 4));
        const bestRow = new TVInfoRow(new TVRect(0, 1, INFO_W, 2));
        const infoBox = new TVInfoBox(new TVRect(INFO_X, 0, INFO_X + INFO_W, 5), "Info", [
                scoreRow,
                livesRow,
                levelRow,
            ]);
        const bestBox = new TVInfoBox(new TVRect(INFO_X, 5, INFO_X + INFO_W, 8), "Best", [
                bestRow,
            ]);
        const breakMain = new TVGroup(new TVRect(0, 0, (0) + (INFO_X + INFO_W), (0) + (20))).insertAll([
                fieldView,
                infoBox,
                bestBox,
                newButton,
            ]);

        super(new TVRect(0, 0, 53, 22), "BreakOut");
        this.setHelpCtx(hcBreakOut);
        this.insert(breakMain);

        installHallOfFame(this, "breakout");
        this.fieldView = fieldView;
        this.newButton = newButton;
        this.infoBox = infoBox.resolve(this.root);
        this.bestBox = bestBox.resolve(this.root);
        this.scoreRow = scoreRow;
        this.livesRow = livesRow;
        this.levelRow = levelRow;
        this.bestRow = bestRow;

        // Field dimensions: BREAK_COLS×2 chars wide, 20 rows tall
        this.fieldW = BREAK_COLS;
        this.fieldH = 20;

        this.bricks = [];
        this.paddleX = 0;
        this.ballX = 0;
        this.ballY = 0;
        this.ballDX = 0;
        this.ballDY = 0;
        this.score = 0;
        this.lives = 3;
        this.level = 1;
        this.gameOver = true;
        this.waiting = false; // ball on paddle
        this.timerId = null;
        this.bestScore = 0;
        this.bestName = "";
        this._loadBestData();
        this.keysDown = new Set();

        this.bindCommonClose(() => this.close());
        this.bindDrag();
    }

    _loadBestData() {
        const b = loadBest(BREAK_BEST_KEY);
        this.bestScore = b.score;
        this.bestName = b.name;
    }
    _saveBest() {
        saveBest(BREAK_BEST_KEY, this.bestScore, this.bestName);
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand && event.command === "break-new") {
            this.newGame();
            this.clearEvent(event);
        } else if (event.what === evKeyDown) {
            const nativeEvent = event.nativeEvent;
            if (!nativeEvent || nativeEvent.defaultPrevented) { return; }
            keyInput: {
                if (!this.isActive()) { break keyInput; }
                if (nativeEvent.key === "Escape") { nativeEvent.preventDefault(); this.close(); break keyInput; }
                this.keysDown.add(nativeEvent.key);
                if (this.gameOver && (nativeEvent.key === "Enter" || nativeEvent.key === " " || nativeEvent.key === "n" || nativeEvent.key === "N")) {
                    nativeEvent.preventDefault();
                    this.newGame();
                } else if (this.waiting && (nativeEvent.key === " " || nativeEvent.key === "ArrowUp")) {
                    nativeEvent.preventDefault();
                    this.launch();
                } else if (nativeEvent.key === "n" || nativeEvent.key === "N") {
                    nativeEvent.preventDefault();
                    this.newGame();
                }
            }
            if (nativeEvent.defaultPrevented) { this.clearEvent(event); }
        }
    }



    onDialogKeyUp(event) {
        this.keysDown.delete(event.key);
    }

    open() {
        super.open();
        this.newGame();
    }

    close() {
        this.stopTimer();
        this.keysDown.clear();
        super.close();
    }

    newGame() {
        this.score = 0;
        this.lives = 3;
        this.level = 1;
        this.gameOver = false;
        this._buildBricks();
        this._resetBall();
        this.startTimer();
        this.render();
    }

    _buildBricks() {
        this.bricks = [];
        for (let r = 0; r < BREAK_ROWS; r++) {
            const row = [];
            for (let c = 0; c < BREAK_COLS; c++) {
                row.push(true);
            }
            this.bricks.push(row);
        }
    }

    _resetBall() {
        this.paddleX = Math.floor((this.fieldW - BREAK_PADDLE_W) / 2);
        this.ballX = this.paddleX + Math.floor(BREAK_PADDLE_W / 2);
        this.ballY = this.fieldH - 2;
        this.ballDX = Math.random() > 0.5 ? 1 : -1;
        this.ballDY = -1;
        this.waiting = true;
    }

    launch() {
        this.waiting = false;
        this.ballDX = Math.random() > 0.5 ? 1 : -1;
        this.ballDY = -1;
    }

    startTimer() {
        this.stopTimer();
        const delay = Math.max(30, 80 - this.level * 5);
        this.timerId = setInterval(() => {
            if (!this.isActive() || !document.hasFocus()) {
                this.keysDown.clear();
                return;
            }
            this.tick();
        }, delay);
    }

    stopTimer() {
        if (this.timerId !== null) {
            clearInterval(this.timerId);
            this.timerId = null;
        }
    }

    tick() {
        if (this.gameOver) { return; }
        // Move paddle
        if (this.keysDown.has("ArrowLeft") || this.keysDown.has("Home")) {
            if (this.paddleX > 0) { this.paddleX--; }
            if (this.waiting) { this.ballX = this.paddleX + Math.floor(BREAK_PADDLE_W / 2); }
        }
        if (this.keysDown.has("ArrowRight") || this.keysDown.has("PageUp")) {
            if (this.paddleX < this.fieldW - BREAK_PADDLE_W) { this.paddleX++; }
            if (this.waiting) { this.ballX = this.paddleX + Math.floor(BREAK_PADDLE_W / 2); }
        }
        if (this.waiting) {
            this.render();
            return;
        }
        // Move ball
        const nx = this.ballX + this.ballDX;
        const ny = this.ballY + this.ballDY;

        // Wall collisions
        if (nx < 0 || nx >= this.fieldW) { this.ballDX = -this.ballDX; }
        if (ny < 0) { this.ballDY = -this.ballDY; }

        // Paddle collision
        if (ny >= this.fieldH - 1 && this.ballDY > 0) {
            if (nx >= this.paddleX && nx < this.paddleX + BREAK_PADDLE_W) {
                this.ballDY = -1;
                // Adjust angle based on where ball hits paddle
                const hitPos = nx - this.paddleX;
                if (hitPos === 0) { this.ballDX = -1; }
                else if (hitPos === BREAK_PADDLE_W - 1) { this.ballDX = 1; }
            } else {
                // Missed
                this.lives--;
                if (this.lives <= 0) {
                    this.gameOver = true;
                    this._checkBest();
                    this.stopTimer();
                    this.render();
                    return;
                }
                this._resetBall();
                this.render();
                return;
            }
        }

        this.ballX += this.ballDX;
        this.ballY += this.ballDY;
        this.ballX = Math.max(0, Math.min(this.fieldW - 1, this.ballX));
        this.ballY = Math.max(0, Math.min(this.fieldH - 1, this.ballY));

        // Brick collision
        // Bricks occupy rows 1..BREAK_ROWS in the field
        const brickRow = this.ballY - 1;
        if (brickRow >= 0 && brickRow < BREAK_ROWS && this.ballX >= 0 && this.ballX < BREAK_COLS) {
            if (this.bricks[brickRow][this.ballX]) {
                this.bricks[brickRow][this.ballX] = false;
                this.ballDY = -this.ballDY;
                this.score += (BREAK_ROWS - brickRow) * 10;
            }
        }

        // Check if all bricks cleared
        const remaining = this.bricks.flat().filter(Boolean).length;
        if (remaining === 0) {
            this.level++;
            this._buildBricks();
            this._resetBall();
            this.startTimer();
        }

        this.render();
    }

    _checkBest() {
        const isBest = this.score > this.bestScore;
        submitHallOfFameScore(this, "breakout", this.score, {
            onSaved: (name) => {
                if (!isBest) { return; }
                this.bestScore = this.score;
                this.bestName = name;
                this._saveBest();
                this.renderInfo();
            },
        });
    }

    render() {
        this.renderField();
        this.renderInfo();
    }

    renderInfo() {
        this.infoBox.updateRow(this.scoreRow, "Score: " + this.score);
        this.infoBox.updateRow(this.livesRow, "Lives: " + this.lives);
        this.infoBox.updateRow(this.levelRow, "Level: " + this.level);
        const bestText = this.bestName
            ? this.bestName + " " + this.bestScore
            : "Best:  " + this.bestScore;
        this.bestBox.updateRow(this.bestRow, bestText);
    }

    renderField() {
        const cells = [];
        for (let row = 0; row < this.fieldH; row++) {
            for (let col = 0; col < this.fieldW; col++) {
                const brick = row - 1;
                cells.push(brick >= 0 && brick < BREAK_ROWS && this.bricks[brick][col]
                    ? { text: "▓▓", kind: "brick", foreground: BREAK_BRICK_COLORS[brick] }
                    : row === this.fieldH - 1 && col >= this.paddleX && col < this.paddleX + BREAK_PADDLE_W
                        ? { text: "▀▀", kind: "paddle", foreground: (gameAppColor(41) >> 4) }
                        : row === this.ballY && col === this.ballX ? { text: "⬤ ", kind: "ball", foreground: 15 } : { text: "  " });
            }
        }
        this.fieldView.setGrid(this.fieldW, cells).setMessage(this.gameOver
            ? `GAME OVER\nScore: ${this.score}\nPress Enter` : this.waiting ? "Press Space" : "");
    }
}

// ── Sokoban ─────────────────────────────────────────────────────────

const SOKOBAN_LEVELS = [
    // Each level: { w, h, map } where map chars: # wall, @ player, $ box, . target, * box-on-target, + player-on-target, space floor
    { w: 7, h: 5, map:
        "  ###  " +
        "  #.#  " +
        "###$###" +
        "#  @$.#" +
        "#######"
    },
    { w: 8, h: 6, map:
        "########" +
        "# .    #" +
        "#  ##  #" +
        "# $  $ #" +
        "# @ .  #" +
        "########"
    },
    { w: 9, h: 7, map:
        "#########" +
        "# .     #" +
        "#  ##   #" +
        "# $   $ #" +
        "#   @ . #" +
        "#   . $ #" +
        "#########"
    },
    { w: 7, h: 7, map:
        "#######" +
        "#     #" +
        "#$# # #" +
        "#.$@$.#" +
        "#.# # #" +
        "#     #" +
        "#######"
    },
    { w: 8, h: 8, map:
        "########" +
        "#      #" +
        "# #*## #" +
        "# . .$ #" +
        "#  $.  #" +
        "# ##$# #" +
        "#  @   #" +
        "########"
    },
    { w: 9, h: 7, map:
        "#########" +
        "# .  .  #" +
        "#   #   #" +
        "# $$  $ #" +
        "#   @   #" +
        "#   # . #" +
        "#########"
    },
    { w: 9, h: 8, map:
        "#########" +
        "# .   . #" +
        "#   #   #" +
        "# $ # $ #" +
        "#   @   #" +
        "# $ # $ #" +
        "# .   . #" +
        "#########"
    },
    { w: 9, h: 7, map:
        "#########" +
        "# .  .  #" +
        "#   #   #" +
        "# $   $ #" +
        "#   @   #" +
        "#   $ . #" +
        "#########"
    },
    { w: 9, h: 8, map:
        "#########" +
        "# .  #  #" +
        "# $  # .#" +
        "#    $  #" +
        "## #    #" +
        "#  @ $ .#" +
        "#       #" +
        "#########"
    },
    { w: 9, h: 8, map:
        "#########" +
        "# .   . #" +
        "#  # #  #" +
        "# $ $ $ #" +
        "#   @   #" +
        "#   $ . #" +
        "#     . #" +
        "#########"
    },
];
const SOKOBAN_BEST_KEY = "tv-sokoban-best";

class TVSokobanDialog extends TVGameDialog {
    static viewName = "sokoban";

    constructor() {
        const FIELD_W = 18;  // max 9 cols × 2ch
        const INFO_X = FIELD_W + 1;
        const INFO_W = 20;
        const fieldView = new TVSokobanField(new TVRect(0, 0, FIELD_W, 10));
        const restartButton = new TVButton(new TVRect(INFO_X, 6, INFO_X + 11, 8), '~R~estart', "sokoban-restart", bfNormal);
        const undoButton = new TVButton(new TVRect(INFO_X + 12, 6, INFO_X + INFO_W, 8), '~U~ndo', "sokoban-undo", bfNormal);
        const prevButton = new TVButton(new TVRect(INFO_X, 9, INFO_X + 9, 11), '< Prev', "sokoban-prev", bfNormal);
        const nextButton = new TVButton(new TVRect(INFO_X + 10, 9, INFO_X + 19, 11), 'Next >', "sokoban-next", bfNormal);
        const levelRow = new TVInfoRow(new TVRect(0, 1, INFO_W, 2));
        const movesRow = new TVInfoRow(new TVRect(0, 2, INFO_W, 3));
        const pushesRow = new TVInfoRow(new TVRect(0, 3, INFO_W, 4));
        const infoBox = new TVInfoBox(new TVRect(INFO_X, 0, INFO_X + INFO_W, 5), "Info", [
                levelRow,
                movesRow,
                pushesRow,
            ]);
        const sokobanMain = new TVGroup(new TVRect(0, 0, (0) + (INFO_X + INFO_W), (0) + (11))).insertAll([
                fieldView,
                infoBox,
                restartButton,
                undoButton,
                prevButton,
                nextButton,
            ]);

        super(new TVRect(0, 0, 44, 18), "Sokoban");
        this.setHelpCtx(hcSokoban);
        this.insert(sokobanMain);

        installHallOfFame(this, "sokoban");
        this.fieldView = fieldView;
        this.restartButton = restartButton;
        this.undoButton = undoButton;
        this.prevButton = prevButton;
        this.nextButton = nextButton;
        this.infoBox = infoBox.resolve(this.root);
        this.levelRow = levelRow;
        this.movesRow = movesRow;
        this.pushesRow = pushesRow;

        this.levelIndex = 0;
        this.board = [];
        this.boardW = 0;
        this.boardH = 0;
        this.playerX = 0;
        this.playerY = 0;
        this.moves = 0;
        this.pushes = 0;
        this.history = [];
        this.solved = false;
        this.completedMoves = Array(SOKOBAN_LEVELS.length).fill(null);
        this.scoreSubmitted = false;

        this.bindCommonClose(() => this.close());
        this.bindDrag();
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand) {
            if (event.command === "sokoban-restart") { this.loadLevel(this.levelIndex); }
            else if (event.command === "sokoban-undo") { this.undo(); }
            else if (event.command === "sokoban-prev") { this.changeLevel(-1); }
            else if (event.command === "sokoban-next") { this.changeLevel(1); }
            else { return; }
            this.clearEvent(event);
        } else if (event.what === evKeyDown) {
            const nativeEvent = event.nativeEvent;
            if (!nativeEvent || nativeEvent.defaultPrevented) { return; }
            keyInput: {
                if (!this.isActive()) { break keyInput; }
                if (nativeEvent.key === "Escape") { nativeEvent.preventDefault(); this.close(); break keyInput; }
                if (this.solved) {
                    if (nativeEvent.key === "Enter" || nativeEvent.key === " ") {
                        nativeEvent.preventDefault();
                        if (this.levelIndex === SOKOBAN_LEVELS.length - 1) {
                            this.newGame();
                        } else {
                            this.changeLevel(1);
                        }
                    }
                    break keyInput;
                }
                switch (nativeEvent.key) {
                    case "ArrowUp": nativeEvent.preventDefault(); this.move(0, -1); break;
                    case "ArrowDown": nativeEvent.preventDefault(); this.move(0, 1); break;
                    case "ArrowLeft": nativeEvent.preventDefault(); this.move(-1, 0); break;
                    case "ArrowRight": nativeEvent.preventDefault(); this.move(1, 0); break;
                    case "r": case "R": nativeEvent.preventDefault(); this.loadLevel(this.levelIndex); break;
                    case "u": case "U": nativeEvent.preventDefault(); this.undo(); break;
                }
            }
            if (nativeEvent.defaultPrevented) { this.clearEvent(event); }
        }
    }



    open() {
        const wasOpen = this.isOpen();
        super.open();
        if (!wasOpen) { this.newGame(); }
        THelpViewerTV.fillBorders(this.dialog);
    }

    close() {
        const previousLevels = this.completedMoves.slice(0, this.levelIndex);
        const canRank = this.isOpen() && !this.scoreSubmitted
            && previousLevels.every(Number.isInteger) && (this.moves > 0 || this.solved || previousLevels.length > 0);
        const score = previousLevels.reduce((total, moves) => total + moves, 0) + this.moves;
        const level = this.levelIndex + 1;
        if (canRank) { this.scoreSubmitted = true; }
        super.close();
        if (canRank) { submitHallOfFameScore(this, "sokoban", score, { level }); }
    }

    changeLevel(dir) {
        const next = this.levelIndex + dir;
        if (next >= 0 && next < SOKOBAN_LEVELS.length) {
            this.loadLevel(next);
        }
    }

    newGame() {
        this.completedMoves.fill(null);
        this.scoreSubmitted = false;
        this.loadLevel(0);
    }

    loadLevel(index) {
        this.levelIndex = index;
        const level = SOKOBAN_LEVELS[index];
        this.boardW = level.w;
        this.boardH = level.h;
        this.board = [];
        this.moves = 0;
        this.pushes = 0;
        this.history = [];
        this.solved = false;
        for (let y = 0; y < level.h; y++) {
            const row = [];
            for (let x = 0; x < level.w; x++) {
                const ch = level.map[y * level.w + x] || " ";
                if (ch === "@") { this.playerX = x; this.playerY = y; row.push(" "); }
                else if (ch === "+") { this.playerX = x; this.playerY = y; row.push("."); }
                else if (ch === "$") { row.push("$"); }
                else if (ch === "*") { row.push("*"); }
                else { row.push(ch); }
            }
            this.board.push(row);
        }
        this.render();
    }

    cellAt(x, y) {
        if (x < 0 || x >= this.boardW || y < 0 || y >= this.boardH) { return "#"; }
        return this.board[y][x];
    }

    move(dx, dy) {
        if (this.solved) { return; }
        const nx = this.playerX + dx;
        const ny = this.playerY + dy;
        const cell = this.cellAt(nx, ny);
        if (cell === "#") { return; }
        if (cell === "$" || cell === "*") {
            // Push box
            const bx = nx + dx;
            const by = ny + dy;
            const behind = this.cellAt(bx, by);
            if (behind === "#" || behind === "$" || behind === "*") { return; }
            // Save state before push
            this.history.push({
                px: this.playerX, py: this.playerY,
                bx: nx, by: ny, bCell: cell,
                tx: bx, ty: by, tCell: behind,
            });
            // Move box
            this.board[ny][nx] = (cell === "*") ? "." : " ";
            this.board[by][bx] = (behind === ".") ? "*" : "$";
            this.playerX = nx;
            this.playerY = ny;
            this.moves++;
            this.pushes++;
        } else {
            // Simple move
            this.history.push({
                px: this.playerX, py: this.playerY,
                bx: -1, by: -1, bCell: "", tx: -1, ty: -1, tCell: "",
            });
            this.playerX = nx;
            this.playerY = ny;
            this.moves++;
        }
        this.checkSolved();
        this.render();
    }

    undo() {
        if (this.history.length === 0 || this.solved) { return; }
        const h = this.history.pop();
        this.playerX = h.px;
        this.playerY = h.py;
        this.moves--;
        if (h.bx >= 0) {
            this.board[h.by][h.bx] = h.bCell;
            this.board[h.ty][h.tx] = h.tCell;
            this.pushes--;
        }
        this.render();
    }

    checkSolved() {
        // All boxes must be on targets (no '$' remaining)
        for (let y = 0; y < this.boardH; y++) {
            for (let x = 0; x < this.boardW; x++) {
                if (this.board[y][x] === "$") { return; }
            }
        }
        this.solved = true;
        this.completedMoves[this.levelIndex] = this.moves;
        if (!this.scoreSubmitted && this.completedMoves.every(Number.isInteger)) {
            this.scoreSubmitted = true;
            submitHallOfFameScore(this, "sokoban", this.completedMoves.reduce((sum, moves) => sum + moves, 0), {
                level: SOKOBAN_LEVELS.length,
            });
        }
    }

    render() {
        this.renderField();
        this.renderInfo();
    }

    renderInfo() {
        this.infoBox.updateRow(this.levelRow, "Level: " + (this.levelIndex + 1) + "/" + SOKOBAN_LEVELS.length);
        this.infoBox.updateRow(this.movesRow, "Moves: " + this.moves);
        this.infoBox.updateRow(this.pushesRow, "Pushes:" + this.pushes);
    }

    renderField() {
        const cells = [];
        for (let y = 0; y < this.boardH; y++) {
            for (let x = 0; x < this.boardW; x++) {
                const value = this.board[y][x];
                cells.push(x === this.playerX && y === this.playerY
                    ? { text: "☻ ", kind: "player", attribute: value === "." ? 0x2e : 0x0e }
                    : value === "#" ? { text: "██", kind: "wall", attribute: 0x87 }
                        : value === "$" ? { text: "▓▓", kind: "box", attribute: 0x06 }
                            : value === "*" ? { text: "▓▓", kind: "box-done", attribute: 0x2a }
                                : value === "." ? { text: "··", kind: "target", attribute: 0x0a } : { text: "  " });
            }
        }
        const prompt = this.levelIndex === SOKOBAN_LEVELS.length - 1 ? "Press Enter for new game" : "Press Enter for next level";
        this.fieldView.setGrid(this.boardW, cells).setMessage(this.solved ? `SOLVED!\nMoves: ${this.moves}\n${prompt}` : "");
    }
}

// ── Lines (Color Lines / Shar) ──────────────────────────────────────

const LINES_SIZE = 9;
const LINES_COLORS = [12, 10, 9, 14, 13, 11, 15];
const LINES_MATCH = 5; // need 5 in a row
const LINES_SPAWN = 3; // new balls per turn
const LINES_BEST_KEY = "tv-lines-best";

class TVLinesDialog extends TVGameDialog {
    static viewName = "lines";

    constructor() {
        const GRID_W = LINES_SIZE * 2;  // 18ch
        const INFO_X = GRID_W + 1;
        const INFO_W = 18;
        const gridView = new TVLinesField(new TVRect(0, 0, GRID_W, LINES_SIZE));
        const newButton = new TVButton(new TVRect(INFO_X, 9, INFO_X + INFO_W, 11), '~N~ew', "lines-new", bfNormal);
        const scoreRow = new TVInfoRow(new TVRect(0, 1, INFO_W, 2));
        const bestRow = new TVInfoRow(new TVRect(0, 2, INFO_W, 3));
        const nextRow = new TVInfoRow(new TVRect(0, 1, INFO_W, 2));
        const nextBalls = Array.from({ length: LINES_SPAWN }, (_, index) => new TVGameTile(new TVRect(2 + index * 2, 1, 4 + index * 2, 2)));
        const infoBox = new TVInfoBox(new TVRect(INFO_X, 0, INFO_X + INFO_W, 4), "Info", [
                scoreRow,
                bestRow,
            ]);
        const nextBox = new TVInfoBox(new TVRect(INFO_X, 5, INFO_X + INFO_W, 8), "Next", [
                nextRow,
                ...nextBalls,
            ]);
        const linesMain = new TVGroup(new TVRect(0, 0, INFO_X + INFO_W, LINES_SIZE + 2)).insertAll([
                gridView,
                infoBox,
                nextBox,
                newButton,
            ]);

        super(new TVRect(0, 0, 41, 13), "Lines");
        this.setHelpCtx(hcLines);
        this.insert(linesMain);

        installHallOfFame(this, "lines");
        this.gridView = gridView;
        this.newButton = newButton;
        this.infoBox = infoBox.resolve(this.root);
        this.nextBox = nextBox.resolve(this.root);
        this.scoreRow = scoreRow;
        this.bestRow = bestRow;
        this.nextRow = nextRow;
        this.nextBalls = nextBalls;

        this.board = [];
        this.selected = null; // {r, c}
        this.score = 0;
        this.gameOver = false;
        this.nextColors = [];
        this.bestScore = 0;
        this.bestName = "";
        this._loadBestData();

        this.bindCommonClose(() => this.close());
        this.bindDrag();
    }

    _loadBestData() {
        const b = loadBest(LINES_BEST_KEY);
        this.bestScore = b.score;
        this.bestName = b.name;
    }
    _saveBest() {
        saveBest(LINES_BEST_KEY, this.bestScore, this.bestName);
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand && event.command === "lines-new") {
            this.newGame();
            this.clearEvent(event);
        } else if (event.what === evCommand && event.command === "lines-cell" && this.isActive()
            && this.gridView.cells.includes(event.infoPtr)) {
            this.activateCell(Math.floor(event.infoPtr.value / LINES_SIZE), event.infoPtr.value % LINES_SIZE);
            this.clearEvent(event);
        } else if (event.what === evKeyDown) {
            const nativeEvent = event.nativeEvent;
            if (!nativeEvent || nativeEvent.defaultPrevented) { return; }
            keyInput: {
                if (!this.isActive()) { break keyInput; }
                if (nativeEvent.key === "Escape") { nativeEvent.preventDefault(); this.close(); }
                else if (nativeEvent.key === "n" || nativeEvent.key === "N") { nativeEvent.preventDefault(); this.newGame(); }
            }
            if (nativeEvent.defaultPrevented) { this.clearEvent(event); }
        }
    }



    open() {
        super.open();
        this.newGame();
        THelpViewerTV.fillBorders(this.dialog);
    }

    newGame() {
        this.board = Array.from({ length: LINES_SIZE }, () => new Array(LINES_SIZE).fill(0));
        this.selected = null;
        this.score = 0;
        this.gameOver = false;
        this.nextColors = this._randomColors(LINES_SPAWN);
        this._spawnBalls(LINES_SPAWN);
        this.render();
    }

    _randomColors(count) {
        const colors = [];
        for (let i = 0; i < count; i++) {
            colors.push(1 + Math.floor(Math.random() * LINES_COLORS.length));
        }
        return colors;
    }

    _spawnBalls(count) {
        const empty = [];
        for (let r = 0; r < LINES_SIZE; r++) {
            for (let c = 0; c < LINES_SIZE; c++) {
                if (this.board[r][c] === 0) { empty.push([r, c]); }
            }
        }
        const toSpawn = Math.min(count, empty.length);
        for (let i = 0; i < toSpawn; i++) {
            const idx = Math.floor(Math.random() * empty.length);
            const [r, c] = empty[idx];
            this.board[r][c] = this.nextColors[i] || (1 + Math.floor(Math.random() * LINES_COLORS.length));
            empty.splice(idx, 1);
        }
        this.nextColors = this._randomColors(LINES_SPAWN);
        // Check if board is full
        if (empty.length <= toSpawn) {
            const remaining = [];
            for (let r = 0; r < LINES_SIZE; r++) {
                for (let c = 0; c < LINES_SIZE; c++) {
                    if (this.board[r][c] === 0) { remaining.push(1); }
                }
            }
            if (remaining.length === 0) {
                this.gameOver = true;
                this._checkBest();
            }
        }
    }

    _checkBest() {
        const isBest = this.score > this.bestScore;
        submitHallOfFameScore(this, "lines", this.score, {
            onSaved: (name) => {
                if (!isBest) { return; }
                this.bestScore = this.score;
                this.bestName = name;
                this._saveBest();
                this.renderInfo();
            },
        });
    }

    activateCell(r, c) {
        if (this.gameOver) { return; }
        if (this.board[r][c] !== 0) {
            // Select this ball
            this.selected = { r, c };
            this.render();
            return;
        }
        if (!this.selected) { return; }
        // Try to move selected ball to empty cell
        if (this._findPath(this.selected.r, this.selected.c, r, c)) {
            this.board[r][c] = this.board[this.selected.r][this.selected.c];
            this.board[this.selected.r][this.selected.c] = 0;
            this.selected = null;
            const removed = this._removeLines();
            if (removed === 0) {
                this._spawnBalls(LINES_SPAWN);
                this._removeLines(); // check after spawn too
            }
            this.render();
        }
    }

    _findPath(sr, sc, er, ec) {
        // BFS pathfinding
        const visited = Array.from({ length: LINES_SIZE }, () => new Array(LINES_SIZE).fill(false));
        const queue = [[sr, sc]];
        visited[sr][sc] = true;
        const dirs = [[0, 1], [0, -1], [1, 0], [-1, 0]];
        while (queue.length > 0) {
            const [cr, cc] = queue.shift();
            if (cr === er && cc === ec) { return true; }
            for (const [dr, dc] of dirs) {
                const nr = cr + dr;
                const nc = cc + dc;
                if (nr >= 0 && nr < LINES_SIZE && nc >= 0 && nc < LINES_SIZE && !visited[nr][nc] && this.board[nr][nc] === 0) {
                    visited[nr][nc] = true;
                    queue.push([nr, nc]);
                }
            }
        }
        return false;
    }

    _removeLines() {
        const toRemove = new Set();
        const directions = [[0, 1], [1, 0], [1, 1], [1, -1]];
        for (let r = 0; r < LINES_SIZE; r++) {
            for (let c = 0; c < LINES_SIZE; c++) {
                if (this.board[r][c] === 0) { continue; }
                const color = this.board[r][c];
                for (const [dr, dc] of directions) {
                    const line = [[r, c]];
                    let nr = r + dr;
                    let nc = c + dc;
                    while (nr >= 0 && nr < LINES_SIZE && nc >= 0 && nc < LINES_SIZE && this.board[nr][nc] === color) {
                        line.push([nr, nc]);
                        nr += dr;
                        nc += dc;
                    }
                    if (line.length >= LINES_MATCH) {
                        for (const [lr, lc] of line) {
                            toRemove.add(lr * LINES_SIZE + lc);
                        }
                    }
                }
            }
        }
        for (const key of toRemove) {
            const r = Math.floor(key / LINES_SIZE);
            const c = key % LINES_SIZE;
            this.board[r][c] = 0;
        }
        if (toRemove.size > 0) {
            this.score += toRemove.size * 2;
        }
        return toRemove.size;
    }

    render() {
        this.renderGrid();
        this.renderInfo();
    }

    renderInfo() {
        this.infoBox.updateRow(this.scoreRow, "Score: " + this.score);
        const bestText = this.bestName
            ? this.bestName + " " + this.bestScore
            : "Best:  " + this.bestScore;
        this.infoBox.updateRow(this.bestRow, bestText);
        this.nextBalls.forEach((ball, index) => ball.setData({ text: "● ", foreground: LINES_COLORS[(this.nextColors[index] - 1) % LINES_COLORS.length] }));
    }

    renderGrid() {
        this.gridView.setGrid(LINES_SIZE, this.board.flatMap((row, r) => row.map((value, c) => ({
            text: value ? "● " : "· ",
            kind: value ? "ball" + (this.selected?.r === r && this.selected?.c === c ? " selected" : "") : "empty",
            foreground: value ? LINES_COLORS[(value - 1) % LINES_COLORS.length] : 9,
            pulse: Boolean(value && this.selected?.r === r && this.selected?.c === c),
            label: `Row ${r + 1}, column ${c + 1}, ${value ? "ball " + value : "empty"}`,
        })))).setMessage(this.gameOver ? `GAME OVER\nScore: ${this.score}\nPress N` : "");
    }
}

// ── Reversi (Othello) ───────────────────────────────────────────────

const REVERSI_SIZE = 8;
const REVERSI_BEST_KEY = "tv-reversi-wins";

class TVReversiDialog extends TVGameDialog {
    static viewName = "reversi";

    constructor() {
        const GRID_W = REVERSI_SIZE * 2;  // 16ch
        const INFO_X = GRID_W + 1;
        const INFO_W = 17;
        const blackRow = new TVInfoRow(new TVRect(0, 1, INFO_W, 2));
        const whiteRow = new TVInfoRow(new TVRect(0, 2, INFO_W, 3));
        const turnRow = new TVInfoRow(new TVRect(0, 3, INFO_W, 4));
        const infoBox = new TVInfoBox(new TVRect(INFO_X, 0, INFO_X + INFO_W, 5), "Info", [
                blackRow,
                whiteRow,
                turnRow,
            ]);
        const gridView = new TVReversiField(new TVRect(0, 0, GRID_W, REVERSI_SIZE));
        const newButton = new TVButton(new TVRect(INFO_X, 6, INFO_X + INFO_W, 8), '~N~ew', "reversi-new", bfNormal);
        const reversiMain = new TVGroup(new TVRect(0, 0, (0) + (INFO_X + INFO_W), (0) + (REVERSI_SIZE))).insertAll([
                gridView,
                infoBox,
                newButton,
            ]);

        super(new TVRect(0, 0, 38, 10), "Reversi");
        this.setHelpCtx(hcReversi);
        this.insert(reversiMain);

        installHallOfFame(this, "reversi");
        this.gridView = gridView;
        this.newButton = newButton;
        this.infoBox = infoBox.resolve(this.root);
        this.blackRow = blackRow;
        this.whiteRow = whiteRow;
        this.turnRow = turnRow;

        // 0=empty, 1=black(player), 2=white(computer)
        this.board = [];
        this.currentPlayer = 1;
        this.gameOver = false;
        this.computerTimer = null;

        this.bindCommonClose(() => this.close());
        this.bindDrag();
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand && event.command === "reversi-new") {
            this.newGame();
            this.clearEvent(event);
        } else if (event.what === evCommand && event.command === "reversi-cell" && this.isActive()
            && this.gridView.cells.includes(event.infoPtr)) {
            if (!this.gameOver && this.currentPlayer === 1) {
                this._makeMove(Math.floor(event.infoPtr.value / REVERSI_SIZE), event.infoPtr.value % REVERSI_SIZE, 1);
            }
            this.clearEvent(event);
        } else if (event.what === evKeyDown) {
            const nativeEvent = event.nativeEvent;
            if (!nativeEvent || nativeEvent.defaultPrevented) { return; }
            keyInput: {
                if (!this.isActive()) { break keyInput; }
                if (nativeEvent.key === "Escape") { nativeEvent.preventDefault(); this.close(); }
                else if (nativeEvent.key === "n" || nativeEvent.key === "N") { nativeEvent.preventDefault(); this.newGame(); }
            }
            if (nativeEvent.defaultPrevented) { this.clearEvent(event); }
        }
    }



    open() {
        super.open();
        this.newGame();
        THelpViewerTV.fillBorders(this.dialog);
    }

    close() {
        window.clearTimeout(this.computerTimer);
        this.computerTimer = null;
        super.close();
    }

    newGame() {
        window.clearTimeout(this.computerTimer);
        this.computerTimer = null;
        this.board = Array.from({ length: REVERSI_SIZE }, () => new Array(REVERSI_SIZE).fill(0));
        const mid = REVERSI_SIZE / 2;
        this.board[mid - 1][mid - 1] = 2;
        this.board[mid - 1][mid] = 1;
        this.board[mid][mid - 1] = 1;
        this.board[mid][mid] = 2;
        this.currentPlayer = 1;
        this.gameOver = false;
        this.render();
    }

    _getFlips(r, c, player) {
        if (this.board[r][c] !== 0) { return []; }
        const opponent = player === 1 ? 2 : 1;
        const allFlips = [];
        const dirs = [[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]];
        for (const [dr, dc] of dirs) {
            const flips = [];
            let nr = r + dr;
            let nc = c + dc;
            while (nr >= 0 && nr < REVERSI_SIZE && nc >= 0 && nc < REVERSI_SIZE && this.board[nr][nc] === opponent) {
                flips.push([nr, nc]);
                nr += dr;
                nc += dc;
            }
            if (flips.length > 0 && nr >= 0 && nr < REVERSI_SIZE && nc >= 0 && nc < REVERSI_SIZE && this.board[nr][nc] === player) {
                allFlips.push(...flips);
            }
        }
        return allFlips;
    }

    _hasValidMove(player) {
        for (let r = 0; r < REVERSI_SIZE; r++) {
            for (let c = 0; c < REVERSI_SIZE; c++) {
                if (this._getFlips(r, c, player).length > 0) { return true; }
            }
        }
        return false;
    }

    _countPieces() {
        let black = 0;
        let white = 0;
        for (let r = 0; r < REVERSI_SIZE; r++) {
            for (let c = 0; c < REVERSI_SIZE; c++) {
                if (this.board[r][c] === 1) { black++; }
                else if (this.board[r][c] === 2) { white++; }
            }
        }
        return { black, white };
    }

    _makeMove(r, c, player) {
        const flips = this._getFlips(r, c, player);
        if (flips.length === 0) { return false; }
        this.board[r][c] = player;
        for (const [fr, fc] of flips) {
            this.board[fr][fc] = player;
        }
        this._nextTurn();
        return true;
    }

    _nextTurn() {
        const opponent = this.currentPlayer === 1 ? 2 : 1;
        if (this._hasValidMove(opponent)) {
            this.currentPlayer = opponent;
        } else if (this._hasValidMove(this.currentPlayer)) {
            // Opponent passes, current player goes again
        } else {
            this.gameOver = true;
            const { black, white } = this._countPieces();
            if (black > white) {
                submitHallOfFameScore(this, "reversi", black - white);
            }
        }
        this.render();
        // If it's computer's turn, play after a short delay
        if (!this.gameOver && this.currentPlayer === 2) {
            this._scheduleComputerMove();
        }
    }

    _scheduleComputerMove() {
        window.clearTimeout(this.computerTimer);
        this.computerTimer = window.setTimeout(() => {
            this.computerTimer = null;
            if (!this.isOpen() || this.gameOver || this.currentPlayer !== 2) { return; }
            if (!this.isActive()) {
                this._scheduleComputerMove();
                return;
            }
            this._computerMove();
        }, 300);
    }

    _computerMove() {
        if (this.gameOver || this.currentPlayer !== 2) { return; }
        // Simple strategy: pick move that flips most pieces, with corner/edge preference
        let bestMove = null;
        let bestScore = -1;
        const corners = [[0,0],[0,7],[7,0],[7,7]];
        for (let r = 0; r < REVERSI_SIZE; r++) {
            for (let c = 0; c < REVERSI_SIZE; c++) {
                const flips = this._getFlips(r, c, 2);
                if (flips.length === 0) { continue; }
                let score = flips.length;
                // Corner bonus
                if (corners.some(([cr, cc]) => cr === r && cc === c)) { score += 100; }
                // Edge bonus
                else if (r === 0 || r === 7 || c === 0 || c === 7) { score += 5; }
                if (score > bestScore) {
                    bestScore = score;
                    bestMove = [r, c];
                }
            }
        }
        if (bestMove) {
            this._makeMove(bestMove[0], bestMove[1], 2);
        }
    }

    render() {
        this.renderGrid();
        this.renderInfo();
    }

    renderInfo() {
        const { black, white } = this._countPieces();
        this.infoBox.updateRow(this.blackRow, "\u25CF You:  " + black);
        this.infoBox.updateRow(this.whiteRow, "\u25CB CPU:  " + white);
        if (this.gameOver) {
            const result = black > white ? "You win!" : (white > black ? "CPU wins" : "Draw");
            this.infoBox.updateRow(this.turnRow, result);
        } else {
            this.infoBox.updateRow(this.turnRow, "Turn: " + (this.currentPlayer === 1 ? "You" : "CPU"));
        }
    }

    renderGrid() {
        this.gridView.setGrid(REVERSI_SIZE, this.board.flatMap((row, r) => row.map((value, c) => {
            const valid = !this.gameOver && this.currentPlayer === 1 && this._getFlips(r, c, 1).length > 0;
            return { text: value === 1 ? "● " : value === 2 ? "○ " : valid ? "· " : "  ",
                kind: value === 1 ? "black" : value === 2 ? "white" : valid ? "valid" : "empty",
                attribute: value === 1 ? 0x20 : value === 2 ? 0x2f : valid ? 0x2a : 0x22,
                hotAttribute: value === 1 ? 0x20 : value === 2 ? 0x2f : valid ? 0x2a : 0x22,
                label: `Row ${r + 1}, column ${c + 1}, ${value === 1 ? "black" : value === 2 ? "white" : valid ? "legal move" : "empty"}` };
        })));
    }
}

// ── Ludo / Clovece, nezlob se ─────────────────────────────────────

const LUDO_BOARD_SIZE = 11;
const LUDO_MODE_LABELS = { human: "You", cpu: "CPU", off: "Off" };
const LUDO_CELL_KEY = (row, col) => `${row},${col}`;
const LUDO_COMMON_CELLS = new Set(LUDO_COMMON_PATH.map(([row, col]) => LUDO_CELL_KEY(row, col)));
const LUDO_HOME_CELLS = new Map();
const LUDO_BASE_CELLS = new Map();
const LUDO_START_CELLS = new Map();
const LUDO_ROUTE_EDGES = new Set();

const addLudoEdge = (from, to) => {
    const fromKey = LUDO_CELL_KEY(...from);
    const toKey = LUDO_CELL_KEY(...to);
    LUDO_ROUTE_EDGES.add(`${fromKey}>${toKey}`);
    LUDO_ROUTE_EDGES.add(`${toKey}>${fromKey}`);
};

LUDO_COMMON_PATH.forEach((cell, index) => {
    addLudoEdge(cell, LUDO_COMMON_PATH[(index + 1) % LUDO_COMMON_PATH.length]);
});

LUDO_HOME_PATHS.forEach((path, player) => {
    path.forEach(([row, col]) => LUDO_HOME_CELLS.set(LUDO_CELL_KEY(row, col), player));
});
LUDO_BASE_POSITIONS.forEach((positions, player) => {
    positions.forEach(([row, col], piece) => LUDO_BASE_CELLS.set(LUDO_CELL_KEY(row, col), [player, piece]));
});
LUDO_START_OFFSETS.forEach((offset, player) => {
    const [row, col] = LUDO_COMMON_PATH[offset];
    LUDO_START_CELLS.set(LUDO_CELL_KEY(row, col), player);
});

class TVLudoBoard extends TVGamePaletteGroup {
    static viewName = "ludo-board";
    _drawAttrs(attrs = {}) { return super._drawAttrs({ ...attrs, role: "grid", "aria-label": "Ludo board" }); }
    constructor(bounds) {
        super(bounds);
        this.paths = new TVGameFrameText(this.getExtent(), "");
        this.insert(this.paths);
        this.markers = Array.from({ length: LUDO_BOARD_SIZE * LUDO_BOARD_SIZE }, (_, index) => {
            const x = 2 + (index % LUDO_BOARD_SIZE) * 4, y = 1 + Math.floor(index / LUDO_BOARD_SIZE) * 2;
            return this.insert(new TVGameTile(new TVRect(x, y, x + 1, y + 1)));
        });
        this.pieces = Array.from({ length: 16 }, (_, index) => {
            const piece = new TVGameTileButton(new TVRect(0, 0, 1, 1), "♟", "ludo-piece").setValue(index % 4);
            piece.player = Math.floor(index / 4); piece.hide(); return this.insert(piece);
        });
        const connected = (r, c, nr, nc) => LUDO_ROUTE_EDGES.has(`${LUDO_CELL_KEY(r, c)}>${LUDO_CELL_KEY(nr, nc)}`);
        const lines = [" ".repeat(45)];
        for (let row = 0; row < LUDO_BOARD_SIZE; row++) {
            let nodes = "  ", links = "  ";
            for (let col = 0; col < LUDO_BOARD_SIZE; col++) {
                nodes += " "; links += connected(row, col, row + 1, col) ? "│" : " ";
                if (col < LUDO_BOARD_SIZE - 1) {
                    nodes += connected(row, col, row, col + 1) ? "───" : "   "; links += "   ";
                }
            }
            lines.push(nodes + "  ");
            if (row < LUDO_BOARD_SIZE - 1) { lines.push(links + "  "); }
        }
        lines.push(" ".repeat(45)); this.paths.setText(lines.join("\n"));
    }
}

class TVLudoDialog extends TVGameDialog {
    static viewName = "ludo";

    constructor() {
        const turnRow = new TVInfoRow(new TVRect(0, 1, 22, 2));
        const diceRow = new TVInfoRow(new TVRect(0, 2, 22, 3));
        const statusRow = new TVInfoRow(new TVRect(0, 3, 22, 4));
        const infoBox = new TVInfoBox(new TVRect(46, 0, 68, 5), "Game", [
                turnRow,
                diceRow,
                statusRow,
            ]);
        const playerButtons = LUDO_PLAYER_NAMES.map((name, player) => (
            new TVLudoPlayerButton(new TVRect(0, player + 1, 22, player + 2), name, "ludo-player-mode", bfNormal)
                .setValue(player)
                .setCommandData({ playerName: name })
        ));
        const playersBox = new TVInfoBox(new TVRect(46, 6, 68, 12), "Players", playerButtons);
        const rollButton = new TVButton(new TVRect(46, 14, 56, 16), "~R~oll", "ludo-roll", bfNormal);
        const newButton = new TVButton(new TVRect(57, 14, 67, 16), "~N~ew", "ludo-new", bfNormal);
        const boardView = new TVLudoBoard(new TVRect(0, 0, 45, 23));
        const main = new TVGroup(new TVRect(0, 0, 68, 24)).insertAll([
            boardView,
            infoBox,
            playersBox,
            rollButton,
            newButton,
        ]);

        super(new TVRect(0, 0, 71, 26), "Ludo");
        this.setHelpCtx(hcLudo);
        this.insert(main);

        installHallOfFame(this, "ludo");
        this.game = new LudoGame();
        this.infoBox = infoBox.resolve(this.root);
        this.turnRow = turnRow;
        this.diceRow = diceRow;
        this.statusRow = statusRow;
        this.boardView = boardView;
        this.rollButton = rollButton;
        this.newButton = newButton;
        this.playerButtons = playerButtons;
        this.cpuTimer = null;
        this.moveTimer = null;
        this.captureFlashTimer = null;
        this.selectedPiece = null;
        this.notice = "";
        this.started = false;
        this.animating = false;
        this.animation = null;
        this.captureFlash = null;
        this.moveCount = 0;
        this.hallRecorded = false;

        this.bindCommonClose(() => this.close());
        this.bindDrag();
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand) {
            if (event.command === "ludo-roll") { this.rollHuman(); }
            else if (event.command === "ludo-new") { this.newGame(); }
            else if (event.command === "ludo-player-mode" && this.playerButtons.includes(event.infoPtr)) { this.cyclePlayerMode(Number(event.infoPtr.value)); }
            else if (event.command === "ludo-piece" && this.isActive() && this.boardView.pieces.includes(event.infoPtr)
                && event.infoPtr.player === this.game.currentPlayer) { this.moveHumanPiece(event.infoPtr.value); }
            else { return; }
            this.clearEvent(event);
        } else if (event.what === evKeyDown) {
            const nativeEvent = event.nativeEvent;
            if (!nativeEvent || nativeEvent.defaultPrevented) { return; }
            keyInput: {
                if (!this.isActive()) { break keyInput; }
                if (nativeEvent.key === "Escape") {
                    nativeEvent.preventDefault();
                    this.close();
                    break keyInput;
                }
                if (nativeEvent.key === "n" || nativeEvent.key === "N") {
                    nativeEvent.preventDefault();
                    this.newGame();
                    break keyInput;
                }
                if ((nativeEvent.key === "r" || nativeEvent.key === "R" || nativeEvent.key === " ") && this.game.phase === "roll") {
                    nativeEvent.preventDefault();
                    this.rollHuman();
                    break keyInput;
                }
                if (this.animating || this.game.phase !== "move" || this.game.playerMode() !== "human") { break keyInput; }
                const legal = this.game.legalPieces();
                if (!legal.length) { break keyInput; }
                if (/^[1-4]$/.test(nativeEvent.key)) {
                    const piece = Number(nativeEvent.key) - 1;
                    if (legal.includes(piece)) {
                        nativeEvent.preventDefault();
                        this.moveHumanPiece(piece);
                    }
                    break keyInput;
                }
                if (["ArrowLeft", "ArrowUp", "ArrowRight", "ArrowDown"].includes(nativeEvent.key)) {
                    nativeEvent.preventDefault();
                    const direction = nativeEvent.key === "ArrowLeft" || nativeEvent.key === "ArrowUp" ? -1 : 1;
                    const current = Math.max(0, legal.indexOf(this.selectedPiece));
                    this.selectedPiece = legal[(current + direction + legal.length) % legal.length];
                    this.renderBoard();
                    this.boardView.pieces[this.game.currentPlayer * 4 + this.selectedPiece]?.focus();
                    break keyInput;
                }
                if (nativeEvent.key === "Enter" && legal.includes(this.selectedPiece)) {
                    nativeEvent.preventDefault();
                    this.moveHumanPiece(this.selectedPiece);
                }
            }
            if (nativeEvent.defaultPrevented) { this.clearEvent(event); }
        }
    }

    open() {
        super.open();
        if (!this.started) {
            this.newGame();
        } else {
            this.render();
            this.scheduleCpu();
        }
        fillBorders(this.dialog);
    }

    close() {
        window.clearTimeout(this.cpuTimer);
        this.cpuTimer = null;
        this.clearAnimation();
        super.close();
    }

    newGame(modes = this.game.modes) {
        window.clearTimeout(this.cpuTimer);
        this.clearAnimation();
        this.game.reset(modes);
        this.started = true;
        this.selectedPiece = null;
        this.notice = "";
        this.moveCount = 0;
        this.hallRecorded = false;
        this.render();
        this.notifyStateChange();
        this.scheduleCpu();
    }

    cyclePlayerMode(player) {
        if (this.animating) { return; }
        const modes = this.game.modes.slice();
        const active = modes.filter((mode) => mode !== "off").length;
        const humans = modes.filter((mode) => mode === "human").length;
        if (modes[player] === "human") {
            if (humans === 1) {
                this.notice = "Keep one human";
                this.renderInfo();
                return;
            }
            modes[player] = "cpu";
        } else if (modes[player] === "cpu") {
            if (active === 2) {
                modes[player] = "human";
            } else {
                modes[player] = "off";
            }
        } else {
            modes[player] = "human";
        }
        this.newGame(modes);
    }

    rollHuman() {
        if (this.animating) { return; }
        if (this.game.playerMode() !== "human" || this.game.phase !== "roll") { return; }
        const previousPlayer = this.game.currentPlayer;
        const result = this.game.roll();
        if (!result) { return; }
        this.selectedPiece = result.legal.length ? result.legal[0] : null;
        this.notice = !result.legal.length && this.game.currentPlayer === previousPlayer
            ? "Try again"
            : "";
        this.render();
        this.notifyStateChange();
        this.scheduleCpu();
    }

    moveHumanPiece(piece) {
        if (this.animating) { return; }
        if (this.game.playerMode() !== "human" || this.game.phase !== "move") { return; }
        this.performMove(piece);
    }



    scheduleCpu() {
        window.clearTimeout(this.cpuTimer);
        this.cpuTimer = null;
        if (this.animating || !this.isOpen() || this.game.winner !== null || this.game.playerMode() !== "cpu") { return; }
        this.cpuTimer = window.setTimeout(() => {
            this.cpuTimer = null;
            if (this.animating || !this.isOpen() || this.game.playerMode() !== "cpu") { return; }
            if (!this.isActive()) {
                this.scheduleCpu();
                return;
            }
            if (this.game.phase === "roll") {
                this.game.roll();
                this.selectedPiece = null;
                this.notice = "";
                this.render();
                this.notifyStateChange();
                this.scheduleCpu();
            } else if (this.game.phase === "move") {
                this.performMove(this.game.chooseCpuPiece());
            }
        }, 450);
    }

    performMove(piece) {
        const beforePieces = this.game.pieces.map((pieces) => pieces.slice());
        const result = this.game.move(piece);
        if (!result) { return null; }
        this.moveCount += 1;
        this.selectedPiece = null;
        this.notice = result.captured.length ? "Piece captured" : "";
        this.animateMove(result, beforePieces);
        return result;
    }

    clearAnimation() {
        window.clearTimeout(this.moveTimer);
        window.clearTimeout(this.captureFlashTimer);
        this.moveTimer = null;
        this.captureFlashTimer = null;
        this.animating = false;
        this.animation = null;
        this.captureFlash = null;
        if (this.dialog) {
            setGameFlash(this.boardView, 0x4e, false);
        }
    }

    animateMove(result, beforePieces) {
        const path = ludoMoveProgressPath(result.from, result.target);
        if (!path.length) {
            this.finishMoveAnimation(result);
            return;
        }
        window.clearTimeout(this.cpuTimer);
        window.clearTimeout(this.moveTimer);
        this.cpuTimer = null;
        this.animating = true;
        this.animation = {
            pieces: beforePieces,
            player: result.player,
            piece: result.piece,
            progress: result.from,
            captured: result.captured,
        };
        this.renderInfo();
        this.renderPlayers();

        let index = 0;
        const step = () => {
            if (!this.isOpen()) {
                this.clearAnimation();
                return;
            }
            this.animation.progress = path[index];
            this.renderBoard();
            index += 1;
            if (index < path.length) {
                this.moveTimer = window.setTimeout(step, LUDO_MOVE_STEP_MS);
            } else {
                this.moveTimer = window.setTimeout(() => this.finishMoveAnimation(result), LUDO_MOVE_STEP_MS);
            }
        };
        step();
    }

    finishMoveAnimation(result) {
        window.clearTimeout(this.moveTimer);
        this.moveTimer = null;
        this.animating = false;
        this.animation = null;
        if (result.captured.length) {
            this.flashCapture(result.captured);
            return;
        }
        this.finishMove();
    }

    flashCapture(captured) {
        this.captureFlash = new Set(captured.map(([player, piece]) => `${player}:${piece}`));
        if (this.dialog) {
            setGameFlash(this.boardView, 0x4e, true, 320);
        }
        this.render();
        this.captureFlashTimer = window.setTimeout(() => {
            this.captureFlash = null;
            if (this.dialog) {
                setGameFlash(this.boardView, 0x4e, false);
            }
            this.finishMove();
        }, LUDO_CAPTURE_FLASH_MS);
    }

    finishMove() {
        window.clearTimeout(this.captureFlashTimer);
        this.captureFlashTimer = null;
        this.captureFlash = null;
        if (this.game.winner !== null && !this.hallRecorded) {
            this.hallRecorded = true;
            const winner = this.game.winner;
            submitHallOfFameScore(this, "ludo", Math.max(1, this.moveCount), {
                name: this.game.modes[winner] === "cpu" ? `CPU ${LUDO_PLAYER_NAMES[winner]}` : "",
            });
        }
        this.render();
        this.notifyStateChange();
        this.scheduleCpu();
    }

    captureUrlState() {
        return this.game.exportState();
    }

    restoreUrlState(state) {
        window.clearTimeout(this.cpuTimer);
        this.clearAnimation();
        if (!this.game.importState(state)) { return false; }
        this.started = true;
        this.selectedPiece = null;
        this.notice = "";
        this.moveCount = 0;
        this.hallRecorded = this.game.winner !== null;
        this.render();
        this.scheduleCpu();
        return true;
    }

    notifyStateChange() {
        if (this.manager && this.manager.onChange) {
            this.manager.onChange();
        }
    }

    render() {
        this.renderBoard();
        this.renderInfo();
        this.renderPlayers();
    }

    renderInfo() {
        const player = this.game.winner === null ? this.game.currentPlayer : this.game.winner;
        const name = LUDO_PLAYER_NAMES[player];
        this.infoBox.updateRow(this.turnRow, `Turn: ${name}`);
        this.infoBox.updateRow(this.diceRow, `Dice: ${this.game.die || "-"}`);
        let status = this.notice;
        if (this.game.winner !== null) {
            status = `${name} wins!`;
        } else if (this.animating) {
            status = this.notice || "Moving";
        } else if (this.game.playerMode() === "cpu") {
            status = "CPU thinking";
        } else if (this.game.phase === "move") {
            status = "Choose a piece";
        } else if (!status) {
            status = this.game.rollsLeft > 1 ? `Roll (${this.game.rollsLeft})` : "Roll the dice";
        }
        this.infoBox.updateRow(this.statusRow, status);
        this.rollButton.setState(sfDisabled, this.animating || this.game.winner !== null ||
            this.game.playerMode() !== "human" || this.game.phase !== "roll");
    }

    renderPlayers() {
        this.playerButtons.forEach((button, player) => {
            const mode = this.game.modes[player];
            const home = this.game.pieces[player].filter((progress) => progress >= LUDO_HOME_START).length;
            const current = this.game.currentPlayer === player && this.game.winner === null;
            const name = LUDO_PLAYER_NAMES[player].padEnd(6);
            const label = `${current ? ">" : " "} ${LUDO_PLAYER_NAMES[player][0]} ${name} ${LUDO_MODE_LABELS[mode]} ${home}/4`;
            if (button.title !== label) { button.setTitle(label); }
            button.off = mode === "off";
            button._drawPalette();
        });
    }

    renderBoard() {
        const animation = this.animation;
        const pieces = animation ? animation.pieces : this.game.pieces;
        const activeCells = new Set([
            ...LUDO_COMMON_CELLS,
            ...LUDO_HOME_CELLS.keys(),
            ...LUDO_BASE_CELLS.keys(),
        ]);
        const occupied = new Map();
        let animatedMover = null;
        for (let player = 0; player < 4; player++) {
            if (this.game.modes[player] === "off") { continue; }
            for (let piece = 0; piece < 4; piece++) {
                if (animation && player === animation.player && piece === animation.piece) {
                    animatedMover = [player, piece];
                    continue;
                }
                const [row, col] = ludoCoordinateForProgress(player, piece, pieces[player][piece]);
                occupied.set(LUDO_CELL_KEY(row, col), [player, piece]);
            }
        }
        if (animation && animatedMover) {
            const [row, col] = ludoCoordinateForProgress(animation.player, animation.piece, animation.progress);
            occupied.set(LUDO_CELL_KEY(row, col), animatedMover);
        }
        const legal = !this.animating && this.game.playerMode() === "human" && this.game.phase === "move"
            ? new Set(this.game.legalPieces())
            : new Set();
        this.boardView.pieces.forEach(piece => piece.hide());
        this.boardView.markers.forEach((marker, index) => {
            const row = Math.floor(index / LUDO_BOARD_SIZE), col = index % LUDO_BOARD_SIZE, key = LUDO_CELL_KEY(row, col);
            const start = LUDO_START_CELLS.get(key), home = LUDO_HOME_CELLS.get(key), base = LUDO_BASE_CELLS.get(key);
            const occupant = occupied.get(key);
            const square = start ?? home ?? base?.[0];
            marker.setData({ text: square !== undefined ? "●" : "○", frame: square === undefined, foreground: square === undefined ? undefined : [12, 10, 14, 9][square] });
            marker.setState(TV.sfVisible, activeCells.has(key) && !occupant);
            if (!occupant) { return; }
            const [player, piece] = occupant, view = this.boardView.pieces[player * 4 + piece];
            const isLegal = player === this.game.currentPlayer && legal.has(piece);
            const moving = animation && player === animation.player && piece === animation.piece;
            const captured = this.captureFlash?.has(`${player}:${piece}`);
            const x = 2 + col * 4, y = 1 + row * 2;
            view.locate(new TVRect(x, y, x + 1, y + 1));
            const selected = isLegal && piece === this.selectedPiece;
            const attribute = isLegal ? gameAppColor(58) : gameInk(view, [12, 10, 14, 9][player]);
            view.setData({ text: "♟", attribute: selected ? swapGameColor(attribute) : attribute,
                hotAttribute: isLegal ? swapGameColor(gameAppColor(58)) : undefined,
                flash: captured ? 0xfe : moving ? swapGameColor(gameAppColor(58)) : undefined, flashDuration: moving ? 110 : 160,
                disabled: !isLegal, label: `${LUDO_PLAYER_NAMES[player]} piece ${piece + 1}` });
            view.show();
        });
    }
}

// ── Mastermind ───────────────────────────────────────────────────────

class TVMastermindRow extends TVGamePaletteGroup {
    constructor(bounds, index) {
        super(bounds); this.isCurrentTurn = false;
        this.number = new TVGameText(new TVRect(0, 0, 3, 1), String(index + 1).padStart(2, " ") + ".");
        this.number.getPaletteAttribute = () => this.getPaletteAttribute();
        this.pegs = Array.from({ length: 4 }, (_, position) => new TVGameTileButton(
            new TVRect(3 + position * 2, 0, 5 + position * 2, 1), "· ", "mastermind-peg").setValue(position));
        this.feedback = new TVGameText(new TVRect(11, 0, bounds.width, 1), "");
        this.insertAll([this.number, ...this.pegs, this.feedback]);
    }
    getPaletteAttribute() { return gameAppColor(this.isCurrentTurn ? 58 : 37); }
    setTurn(turn, current, game) {
        this.isCurrentTurn = current;
        this._drawPalette();
        this.pegs.forEach((peg, position) => {
            const color = turn ? turn.guess[position] : current ? game.currentGuess[position] : null;
            peg.setData({ text: color === null ? "· " : "●",
                foreground: color === null ? gameAppColor(44) & 15 : current && position === game.cursor ? gameAppColor(40) & 15 : [12, 10, 14, 9, 13, 11][color],
                selected: current && position === game.cursor, disabled: !current,
                tabIndex: current && position === game.cursor ? 0 : -1,
                label: color === null ? "Empty turn" : `Position ${position + 1}, color ${color + 1}` });
        });
        this.feedback.setText(turn ? ` ${"●".repeat(turn.exact)}${"○".repeat(turn.misplaced)}` : "");
        paintGameTree(this);
    }
}

class TVMastermindBoard extends TVGamePaletteGroup {
    static viewName = "mastermind-board";
    constructor(bounds) {
        super(bounds);
        this.rows = Array.from({ length: 10 }, (_, index) => this.insert(new TVMastermindRow(new TVRect(0, index, bounds.width, index + 1), index)));
    }
    setData(game) { this.rows.forEach((row, index) => row.setTurn(game.turns[index], game.status === "playing" && index === game.turns.length, game)); }
}

class TVMastermindStatus extends TVGamePaletteGroup {
    constructor(bounds) {
        super(bounds);
        this.label = new TVStaticText(new TVRect(0, 0, bounds.width, 2), "");
        this.secret = Array.from({ length: 4 }, (_, index) => new TVGameTile(new TVRect(20 + index * 2, 0, 22 + index * 2, 1)));
        this.insertAll([this.label, ...this.secret]);
    }
    setData(game) {
        this.label.setText(game.status === "won" ? `Code broken in ${game.turns.length} turn(s).`
            : game.status === "lost" ? "No turns left. Code: " : "1-6 choose color, arrows move, Enter guesses.");
        this.secret.forEach((peg, position) => {
            peg.setData({ text: "●", foreground: [12, 10, 14, 9, 13, 11][game.secret[position]] });
            peg.setState(TV.sfVisible, game.status === "lost");
        });
    }
}

class TVMastermindDialog extends TVGameDialog {
    static viewName = "mastermind";

    constructor() {
        const paletteButtons = Array.from({ length: 6 }, (_, color) => {
            const x = 34 + (color % 3) * 6;
            const y = 2 + Math.floor(color / 3) * 2;
            return new TVButton(new TVRect(x, y, x + 5, y + 2), String(color + 1), "mastermind-color", bfNormal)
                .setValue(color);
        });
        const boardView = new TVMastermindBoard(new TVRect(3, 1, 31, 11));
        const guessButton = new TVButton(new TVRect(34, 8, 45, 10), "~G~uess", "mastermind-guess", bfDefault);
        const newButton = new TVButton(new TVRect(34, 11, 45, 13), "~N~ew", "mastermind-new", bfNormal);
        const statusView = new TVMastermindStatus(new TVRect(3, 14, 51, 16));
        const body = new TVGroup(new TVRect(0, 0, 52, 16)).insertAll([
                boardView,
                new TVStaticText(new TVRect(34, 1, 51, 2), "Colors"),
                ...paletteButtons,
                guessButton,
                newButton,
                statusView,
            ]);
        super(new TVRect(0, 0, 56, 18), "Mastermind");
        this.setHelpCtx(hcMastermind);
        this.insert(body);
        installHallOfFame(this, "mastermind");
        this.game = new MastermindGame();
        this.boardView = boardView;
        this.statusView = statusView;
        this.guessButton = guessButton;
        this.newButton = newButton;
        this.paletteButtons = paletteButtons;
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.render();
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand) {
            if (event.command === "mastermind-color" && this.paletteButtons.includes(event.infoPtr)) { this.setColor(Number(event.infoPtr.value)); }
            else if (event.command === "mastermind-peg" && this.isActive() && this.boardView.rows.some(row => row.isCurrentTurn && row.pegs.includes(event.infoPtr))) {
                this.game.cursor = event.infoPtr.value; this.render();
            }
            else if (event.command === "mastermind-guess") { this.submitGuess(); }
            else if (event.command === "mastermind-new") { this.newGame(); }
            else { return; }
            this.clearEvent(event);
        } else if (event.what === evKeyDown) {
            const nativeEvent = event.nativeEvent;
            if (!nativeEvent || nativeEvent.defaultPrevented) { return; }
            keyInput: {
                if (!this.isActive()) { break keyInput; }
                if (/^[1-6]$/.test(nativeEvent.key)) {
                    nativeEvent.preventDefault();
                    this.setColor(Number(nativeEvent.key) - 1);
                } else if (nativeEvent.key === "ArrowLeft" || nativeEvent.key === "ArrowRight") {
                    nativeEvent.preventDefault();
                    const step = nativeEvent.key === "ArrowLeft" ? -1 : 1;
                    this.game.cursor = (this.game.cursor + step + this.game.codeLength) % this.game.codeLength;
                    this.render();
                } else if (nativeEvent.key === "Enter" || nativeEvent.key.toLocaleLowerCase() === "g") {
                    nativeEvent.preventDefault();
                    this.submitGuess();
                } else if (nativeEvent.key.toLocaleLowerCase() === "n") {
                    nativeEvent.preventDefault();
                    this.newGame();
                }
            }
            if (nativeEvent.defaultPrevented) { this.clearEvent(event); }
        }
    }



    setColor(color) {
        const position = this.game.cursor;
        if (this.game.setPeg(position, color)) { this.render(); }
    }

    submitGuess() {
        const turn = this.game.submitGuess();
        if (!turn) { return; }
        this.render();
        if (this.game.status === "won") {
            submitHallOfFameScore(this, "mastermind", this.game.turns.length);
        }
    }

    newGame() {
        this.game.reset();
        this.render();
    }

    render() {
        this.boardView.setData(this.game);
        this.guessButton.setState(sfDisabled, this.game.status !== "playing");
        this.statusView.setData(this.game);
        fillBorders(this.root);
    }
}

// ── Tron Light Cycles ────────────────────────────────────────────────

const TRON_COLS = 30;
const TRON_ROWS = 18;
const TRON_TICK_MS = 90;
const TRON_DIRECTIONS = new Map([
    ["w", [0, 0, -1]], ["a", [0, -1, 0]], ["s", [0, 0, 1]], ["d", [0, 1, 0]],
    ["ArrowUp", [1, 0, -1]], ["ArrowLeft", [1, -1, 0]],
    ["ArrowDown", [1, 0, 1]], ["ArrowRight", [1, 1, 0]],
]);

class TVTronDialog extends TVGameDialog {
    static viewName = "tron";

    constructor() {
        const fieldWidth = TRON_COLS * 2;
        const infoX = fieldWidth + 2;
        const fieldView = new TVTronField(new TVRect(0, 0, fieldWidth, TRON_ROWS));
        const statusView = new TVGameStatus(new TVRect(infoX, 5, infoX + 22, 9), "");
        const newButton = new TVButton(new TVRect(infoX, 10, infoX + 15, 12), "~N~ew round", "tron-new", bfDefault);
        const pauseButton = new TVButton(new TVRect(infoX, 13, infoX + 15, 15), "~P~ause", "tron-pause", bfNormal);
        const tronMain = new TVGroup(new TVRect(0, 0, (0) + (infoX + 22), (0) + (TRON_ROWS))).insertAll([
                fieldView,
                new TVStaticText(new TVRect(infoX, 0, infoX + 22, 1), "P1: W A S D"),
                new TVStaticText(new TVRect(infoX, 2, infoX + 22, 3), "P2: Arrow keys"),
                statusView,
                newButton,
                pauseButton,
                new TVStaticText(new TVRect(infoX, 16, infoX + 22, 18), "Avoid every trail.\nBoth move together."),
            ]);
        super(new TVRect(0, 0, 88, 23), "Tron Light Cycles");
        this.setHelpCtx(hcTron);
        this.insert(tronMain);
        installHallOfFame(this, "tron");
        this.game = new TronGame({ width: TRON_COLS, height: TRON_ROWS });
        this.fieldView = fieldView;
        this.statusView = statusView;
        this.newButton = newButton;
        this.pauseButton = pauseButton;
        this.timerId = null;
        this.manualPause = false;
        this.inactivePause = false;
        this.scoreSubmitted = false;
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.render();
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand) {
            if (event.command === "tron-new") { this.newGame(); }
            else if (event.command === "tron-pause") { this.togglePause(); }
            else { return; }
            this.clearEvent(event);
        } else if (event.what === evKeyDown) {
            const nativeEvent = event.nativeEvent;
            if (!nativeEvent || nativeEvent.defaultPrevented) { return; }
            keyInput: {
                if (!this.isActive()) { break keyInput; }
                const key = nativeEvent.key.length === 1 ? nativeEvent.key.toLocaleLowerCase() : nativeEvent.key;
                const direction = TRON_DIRECTIONS.get(key);
                if (direction) {
                    nativeEvent.preventDefault();
                    this.game.queueDirection(direction[0], direction[1], direction[2]);
                } else if (key === "n" || (this.game.status !== "running" && nativeEvent.key === "Enter")) {
                    nativeEvent.preventDefault();
                    this.newGame();
                } else if (key === "p") {
                    nativeEvent.preventDefault();
                    this.togglePause();
                }
            }
            if (nativeEvent.defaultPrevented) { this.clearEvent(event); }
        }
    }



    open() {
        super.open();
        this.newGame();
    }

    close() {
        this.stopTimer();
        this.game.clearPendingDirections();
        super.close();
    }

    newGame() {
        this.game.reset();
        this.manualPause = false;
        this.inactivePause = false;
        this.scoreSubmitted = false;
        this.startTimer();
        this.render();
    }

    togglePause() {
        if (this.game.status !== "running") { return; }
        this.manualPause = !this.manualPause;
        this.game.clearPendingDirections();
        this.renderStatus();
    }

    startTimer() {
        this.stopTimer();
        this.timerId = window.setInterval(() => {
            if (!this.isActive() || !document.hasFocus()) {
                this.game.clearPendingDirections();
                if (!this.inactivePause) {
                    this.inactivePause = true;
                    this.renderStatus();
                }
                return;
            }
            if (this.inactivePause) {
                this.inactivePause = false;
                this.renderStatus();
            }
            if (this.manualPause || this.game.status !== "running") { return; }
            this.game.tick();
            if (this.game.status !== "running") { this.finishRound(); }
            this.render();
        }, TRON_TICK_MS);
    }

    stopTimer() {
        if (this.timerId !== null) {
            window.clearInterval(this.timerId);
            this.timerId = null;
        }
    }

    finishRound() {
        if (this.scoreSubmitted || this.game.winner === null) { return; }
        this.scoreSubmitted = true;
        submitHallOfFameScore(this, "tron", this.game.ticks, {
            note: `P${this.game.winner + 1}`,
        });
    }

    render() {
        this.renderField();
        this.renderStatus();
        fillBorders(this.root);
    }

    renderStatus() {
        if (this.inactivePause) {
            this.statusView.setText("Inactive window\nPaused automatically");
        } else if (this.manualPause) {
            this.statusView.setText("PAUSED\nPress P to resume");
        } else if (this.game.status === "draw") {
            this.statusView.setText(`DRAW\nTicks: ${this.game.ticks}`);
        } else if (this.game.status === "won") {
            this.statusView.setText(`PLAYER ${this.game.winner + 1} WINS\nTicks: ${this.game.ticks}`);
        } else {
            this.statusView.setText(`Running\nTicks: ${this.game.ticks}`);
        }
        this.pauseButton.setTitle(this.manualPause ? "~R~esume" : "~P~ause");
    }

    renderField() {
        const owners = new Map();
        this.game.trails.forEach((trail, player) => {
            trail.forEach((key) => owners.set(key, player));
        });
        const heads = new Map();
        this.game.players.forEach((player, index) => {
            if (player.alive) { heads.set(`${player.x},${player.y}`, index); }
        });
        const cells = [];
        for (let y = 0; y < TRON_ROWS; y += 1) {
            for (let x = 0; x < TRON_COLS; x += 1) {
                const key = `${x},${y}`;
                const owner = owners.get(key);
                const head = heads.get(key);
                cells.push({ text: owner === undefined ? "  " : head !== undefined ? "@@" : "██",
                    attribute: head !== undefined ? 0xf0 : owner === 0 ? 0x1b : owner === 1 ? 0x4e : 0x00 });
            }
        }
        this.fieldView.setGrid(TRON_COLS, cells);
    }
}

// ── Tower of Hanoi ──────────────────────────────────────────────────

class TVHanoiDisk extends TVGameText {
    constructor(bounds, disk) {
        super(bounds, "\x03" + disk); this.value = disk; this.alternate = false; this.draggable = false;
        this.onStart = nativeEvent => this.dispatchEvent(new TVEvent(evCommand, { command: "hanoi-drag-start", infoPtr: this, nativeEvent }));
        this.onEnd = nativeEvent => this.dispatchEvent(new TVEvent(evCommand, { command: "hanoi-drag-end", infoPtr: this, nativeEvent }));
    }
    getPaletteAttribute() { return this.alternate ? 0x1e : 0x30; }
    bindRoot(root) {
        this.root?.removeEventListener("dragstart", this.onStart); this.root?.removeEventListener("dragend", this.onEnd);
        super.bindRoot(root);
        this.root?.addEventListener("dragstart", this.onStart); this.root?.addEventListener("dragend", this.onEnd);
        if (this.root) { this.root.draggable = this.draggable; }
        return this;
    }
    destroy() { this.bindRoot(null); }
}

class TVHanoiTower extends TVGamePaletteGroup {
    constructor(bounds, tower) {
        super(bounds); this.value = tower; this.selected = false; this.focused = false;
        const rod = new TVGameText(new TVRect(8.5, 1, 9.5, 8), ""); rod.attribute = 0x66;
        const base = new TVGameText(new TVRect(1, 8, 17, 9), "═".repeat(16)); base.getPaletteAttribute = () => gameInk(base, 6);
        const number = new TVGameText(new TVRect(0, 9, 18, 10), "\x03" + (tower + 1));
        this.insertAll([rod, base, number]);
        this.onOver = nativeEvent => this.dispatchEvent(new TVEvent(evCommand, { command: "hanoi-drag-over", infoPtr: this, nativeEvent }));
        this.onDrop = nativeEvent => this.dispatchEvent(new TVEvent(evCommand, { command: "hanoi-drop", infoPtr: this, nativeEvent }));
    }
    getPaletteAttribute() { return gameAppColor(this.selected || this._gameFocused ? 58 : 37); }
    bindRoot(root) {
        this.root?.removeEventListener("dragover", this.onOver); this.root?.removeEventListener("drop", this.onDrop);
        super.bindRoot(root);
        this.root?.addEventListener("dragover", this.onOver); this.root?.addEventListener("drop", this.onDrop);
        if (this.root) {
            this.root.setAttribute("role", "button"); this.root.setAttribute("aria-label", `Tower ${this.value + 1}`);
            this.root.tabIndex = this.focused ? 0 : -1; this._drawPalette();
        }
        return this;
    }
    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evMouseDown && event.nativeEvent?.type === "click") {
            event.what = evCommand; event.command = "hanoi-tower"; event.infoPtr = this;
        }
    }
    destroy() { this.children.forEach(child => child.destroy?.()); this.bindRoot(null); }
}

class TVHanoiBoard extends TVGamePaletteGroup {
    static viewName = "hanoi-board";
    constructor(bounds) {
        super(bounds);
        this.towers = Array.from({ length: 3 }, (_, index) => this.insert(new TVHanoiTower(new TVRect(index * 18, 0, index * 18 + 18, 10), index)));
        this.disks = Array.from({ length: 5 }, (_, index) => this.towers[0].insert(new TVHanoiDisk(new TVRect(), index + 1)));
    }
    setBoard(game, focused, selected) {
        this.towers.forEach((tower, index) => {
            tower.focused = focused === index; tower.selected = selected === index;
            if (tower.root) { tower.root.tabIndex = tower.focused ? 0 : -1; }
            game.towers[index].forEach((value, level) => {
                const disk = this.disks[value - 1], width = 4 + value * 2, x = (18 - width) / 2;
                if (disk.owner !== tower) {
                    disk.owner.remove(disk); tower.insert(disk);
                    if (disk.root && tower.root) { tower.root.append(disk.root); }
                }
                disk.locate(new TVRect(x, 7 - level, x + width, 8 - level));
                disk.alternate = level % 2 === 0; disk.draggable = value === game.top(index) && game.status !== "won";
                if (disk.root) { disk.root.draggable = disk.draggable; disk._drawPalette(); }
            });
            paintGameTree(tower);
        });
    }
}

class TVHanoiDialog extends TVGameDialog {
    static viewName = "hanoi";

    constructor() {
        const boardView = new TVHanoiBoard(new TVRect(1, 1, 55, 11));
        const historyView = new TVGameStatus(new TVRect(56, 1, 76, 9), "");
        const undoButton = new TVButton(new TVRect(56, 9, 68, 11), "~U~ndo", "hanoi-undo", bfNormal);
        const newButton = new TVButton(new TVRect(56, 12, 68, 14), "~N~ew", "hanoi-new", bfDefault);
        const statusView = new TVGameStatus(new TVRect(1, 12, 55, 14), "");
        const hanoiMain = new TVGroup(new TVRect(0, 0, 77, 15)).insertAll([
                boardView,
                historyView,
                undoButton,
                newButton,
                statusView,
            ]);
        super(new TVRect(0, 0, 81, 19), "Tower of Hanoi");
        this.setHelpCtx(hcHanoi);
        this.insert(hanoiMain);
        installHallOfFame(this, "hanoi");
        this.game = new HanoiGame(5);
        this.boardView = boardView;
        this.historyView = historyView;
        this.statusView = statusView;
        this.undoButton = undoButton;
        this.newButton = newButton;
        this.focusedTower = 0;
        this.selectedTower = null;
        this.dragTower = null;
        this.scoreSubmitted = false;
        this.message = "Select a source tower.";
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.render();
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand) {
            if (event.command === "hanoi-undo") { this.undo(); }
            else if (event.command === "hanoi-new") { this.newGame(); }
            else if (event.command === "hanoi-tower" && this.isActive() && this.boardView.towers.includes(event.infoPtr)) {
                this.focusedTower = event.infoPtr.value; this.activateTower(this.focusedTower);
            } else if (event.command === "hanoi-drag-start" && this.isActive() && this.boardView.disks.includes(event.infoPtr)) {
                const disk = event.infoPtr;
                if (!disk.draggable) { event.nativeEvent.preventDefault(); return; }
                this.dragTower = disk.owner.value; this.selectedTower = this.dragTower;
                event.nativeEvent.dataTransfer?.setData("text/plain", String(this.dragTower));
                if (event.nativeEvent.dataTransfer) { event.nativeEvent.dataTransfer.effectAllowed = "move"; }
                this.render();
            } else if (["hanoi-drag-over", "hanoi-drop"].includes(event.command) && this.isActive()
                && this.dragTower !== null && this.boardView.towers.includes(event.infoPtr)) {
                event.nativeEvent.preventDefault();
                if (event.command === "hanoi-drop") {
                    const from = this.dragTower; this.dragTower = null; this.selectedTower = null;
                    this.focusedTower = event.infoPtr.value; this.move(from, this.focusedTower, true);
                }
            } else if (event.command === "hanoi-drag-end" && this.boardView.disks.includes(event.infoPtr)) {
                this.dragTower = null; this.selectedTower = null; if (this.isOpen()) { this.render(); }
            } else { return; }
            this.clearEvent(event);
        } else if (event.what === evKeyDown) {
            const nativeEvent = event.nativeEvent;
            if (!nativeEvent || nativeEvent.defaultPrevented) { return; }
            keyInput: {
                if (!this.isActive()) { break keyInput; }
                if (nativeEvent.key === "ArrowLeft" || nativeEvent.key === "ArrowRight") {
                    nativeEvent.preventDefault();
                    const step = nativeEvent.key === "ArrowLeft" ? -1 : 1;
                    this.focusTower((this.focusedTower + step + 3) % 3);
                } else if (/^[1-3]$/.test(nativeEvent.key)) {
                    nativeEvent.preventDefault();
                    this.focusTower(Number(nativeEvent.key) - 1);
                } else if (nativeEvent.key === "Enter" || nativeEvent.key === " ") {
                    nativeEvent.preventDefault();
                    this.activateTower(this.focusedTower);
                } else if (nativeEvent.key.toLocaleLowerCase() === "u") {
                    nativeEvent.preventDefault();
                    this.undo();
                } else if (nativeEvent.key.toLocaleLowerCase() === "n") {
                    nativeEvent.preventDefault();
                    this.newGame();
                }
            }
            if (nativeEvent.defaultPrevented) { this.clearEvent(event); }
        }
    }



    open() {
        super.open();
        this.newGame();
        window.requestAnimationFrame(() => { if (!this.destroyed && this.isActive()) { this.focusTower(0); } });
    }

    close() {
        this.dragTower = null; this.selectedTower = null;
        super.close();
    }

    newGame() {
        this.game.reset();
        this.focusedTower = 0;
        this.selectedTower = null;
        this.dragTower = null;
        this.scoreSubmitted = false;
        this.message = "Select a source tower.";
        this.render();
    }

    focusTower(tower) {
        this.focusedTower = Math.max(0, Math.min(2, Number(tower) || 0));
        this.render(false);
        this.boardView.towers[this.focusedTower].focus();
    }

    activateTower(tower) {
        if (this.game.status === "won") { return; }
        if (this.selectedTower === null) {
            if (this.game.top(tower) === null) {
                this.message = "That tower is empty.";
            } else {
                this.selectedTower = tower;
                this.message = `Disk ${this.game.top(tower)} selected. Choose a destination.`;
            }
            this.render(true);
            return;
        }
        const from = this.selectedTower;
        this.selectedTower = null;
        if (from === tower) {
            this.message = "Selection cancelled.";
            this.render(true);
            return;
        }
        this.move(from, tower, true);
    }

    move(from, to, focus = false) {
        if (!this.game.move(from, to)) {
            this.message = "Illegal move: smaller disks must stay on top.";
            this.render(focus);
            return false;
        }
        this.message = `Moved disk to tower ${to + 1}.`;
        if (this.game.status === "won" && !this.scoreSubmitted) {
            this.scoreSubmitted = true;
            this.message = `Solved in ${this.game.moves} moves (minimum ${this.game.minimumMoves}).`;
            submitHallOfFameScore(this, "hanoi", this.game.moves, { note: `${this.game.diskCount} disks` });
        }
        this.render(focus);
        return true;
    }

    undo() {
        this.selectedTower = null;
        if (!this.game.undo()) {
            this.message = "No move to undo.";
        } else {
            this.scoreSubmitted = false;
            this.message = "Last move undone.";
        }
        this.render(true);
    }

    render(focus = false) {
        this.renderBoard();
        this.renderHistory();
        this.statusView.setText(`${this.message}\nMoves: ${this.game.moves} / minimum ${this.game.minimumMoves}`);
        this.undoButton.setState(sfDisabled, this.game.history.length === 0);
        fillBorders(this.root);
        if (focus) {
            this.boardView.towers[this.focusedTower].focus();
        }
    }

    renderBoard() { this.boardView.setBoard(this.game, this.focusedTower, this.selectedTower); }

    renderHistory() {
        const recent = this.game.history.slice(-7);
        const rows = recent.map((move, index) => {
            const number = this.game.history.length - recent.length + index + 1;
            return `${String(number).padStart(2, " ")}. ${move.from + 1}→${move.to + 1} disk ${move.disk}`;
        });
        this.historyView.setText(["Move history", "────────────", ...(rows.length ? rows : ["(empty)"])].join("\n"));
    }
}

// ── Snake ────────────────────────────────────────────────────────────

const SNAKE_COLS = 20;
const SNAKE_ROWS = 15;
const SNAKE_DELAYS = [200, 160, 130, 110, 90, 75, 60, 50, 40, 35];
const SNAKE_BEST_KEY = "tv-snake-best";

class TVSnakeDialog extends TVGameDialog {
    static viewName = "snake";

    constructor() {
        const FIELD_W = SNAKE_COLS * 2;  // 40ch
        const INFO_X = FIELD_W + 1;
        const INFO_W = 18;
        const fieldView = new TVSnakeField(new TVRect(0, 0, FIELD_W, SNAKE_ROWS));
        const newButton = new TVButton(new TVRect(INFO_X, 13, INFO_X + INFO_W, 15), '~N~ew', "snake-new", bfNormal);
        const scoreRow = new TVInfoRow(new TVRect(0, 1, INFO_W, 2));
        const levelRow = new TVInfoRow(new TVRect(0, 2, INFO_W, 3));
        const lengthRow = new TVInfoRow(new TVRect(0, 3, INFO_W, 4));
        const bestRow = new TVInfoRow(new TVRect(0, 1, INFO_W, 2));
        const infoBox = new TVInfoBox(new TVRect(INFO_X, 0, INFO_X + INFO_W, 5), "Info", [
                scoreRow,
                levelRow,
                lengthRow,
            ]);
        const bestBox = new TVInfoBox(new TVRect(INFO_X, 5, INFO_X + INFO_W, 8), "Best", [
                bestRow,
            ]);
        const snakeMain = new TVGroup(new TVRect(0, 0, (0) + (INFO_X + INFO_W), (0) + (SNAKE_ROWS))).insertAll([
                fieldView,
                infoBox,
                bestBox,
                newButton,
            ]);

        super(new TVRect(0, 0, 64, 19), "Snake");
        this.setHelpCtx(hcSnake);
        this.insert(snakeMain);

        installHallOfFame(this, "snake");
        this.fieldView = fieldView;
        this.newButton = newButton;
        this.infoBox = infoBox.resolve(this.root);
        this.bestBox = bestBox.resolve(this.root);
        this.scoreRow = scoreRow;
        this.levelRow = levelRow;
        this.lengthRow = lengthRow;
        this.bestRow = bestRow;

        this.snake = [];
        this.dir = { dx: 1, dy: 0 };
        this.nextDir = { dx: 1, dy: 0 };
        this.food = null;
        this.score = 0;
        this.level = 1;
        this.gameOver = true;
        this.timerId = null;
        this.bestScore = 0;
        this.bestName = "";
        this._loadBestData();

        this.bindCommonClose(() => this.close());
        this.bindDrag();
    }

    _loadBestData() {
        const b = loadBest(SNAKE_BEST_KEY);
        this.bestScore = b.score;
        this.bestName = b.name;
    }
    _saveBest() {
        saveBest(SNAKE_BEST_KEY, this.bestScore, this.bestName);
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand && event.command === "snake-new") {
            this.newGame();
            this.clearEvent(event);
        } else if (event.what === evKeyDown) {
            const nativeEvent = event.nativeEvent;
            if (!nativeEvent || nativeEvent.defaultPrevented) { return; }
            keyInput: {
                if (!this.isActive()) { break keyInput; }
                if (nativeEvent.key === "Escape") { nativeEvent.preventDefault(); this.close(); break keyInput; }
                if (this.gameOver && (nativeEvent.key === "Enter" || nativeEvent.key === " " || nativeEvent.key === "n" || nativeEvent.key === "N")) {
                    nativeEvent.preventDefault();
                    this.newGame();
                    break keyInput;
                }
                switch (nativeEvent.key) {
                    case "ArrowUp":    if (this.dir.dy !== 1)  { this.nextDir = { dx: 0, dy: -1 }; } nativeEvent.preventDefault(); break;
                    case "ArrowDown":  if (this.dir.dy !== -1) { this.nextDir = { dx: 0, dy: 1 }; }  nativeEvent.preventDefault(); break;
                    case "ArrowLeft":  if (this.dir.dx !== 1)  { this.nextDir = { dx: -1, dy: 0 }; } nativeEvent.preventDefault(); break;
                    case "ArrowRight": if (this.dir.dx !== -1) { this.nextDir = { dx: 1, dy: 0 }; }  nativeEvent.preventDefault(); break;
                    case "n": case "N": nativeEvent.preventDefault(); this.newGame(); break;
                }
            }
            if (nativeEvent.defaultPrevented) { this.clearEvent(event); }
        }
    }



    open() {
        super.open();
        this.newGame();
    }

    close() {
        this.stopTimer();
        super.close();
    }

    newGame() {
        this.stopTimer();
        const startX = Math.floor(SNAKE_COLS / 2);
        const startY = Math.floor(SNAKE_ROWS / 2);
        this.snake = [
            { x: startX, y: startY },
            { x: startX - 1, y: startY },
            { x: startX - 2, y: startY },
        ];
        this.dir = { dx: 1, dy: 0 };
        this.nextDir = { dx: 1, dy: 0 };
        this.score = 0;
        this.level = 1;
        this.gameOver = false;
        this._spawnFood();
        this.render();
        this.startTimer();
    }

    _spawnFood() {
        const occupied = new Set(this.snake.map(s => s.y * SNAKE_COLS + s.x));
        const free = [];
        for (let y = 0; y < SNAKE_ROWS; y++) {
            for (let x = 0; x < SNAKE_COLS; x++) {
                if (!occupied.has(y * SNAKE_COLS + x)) { free.push({ x, y }); }
            }
        }
        if (free.length === 0) { this.food = null; return; }
        this.food = free[Math.floor(Math.random() * free.length)];
    }

    startTimer() {
        this.stopTimer();
        const delay = SNAKE_DELAYS[Math.min(this.level - 1, SNAKE_DELAYS.length - 1)];
        this.timerId = setInterval(() => {
            if (!this.isActive()) { return; }
            this.tick();
        }, delay);
    }

    stopTimer() {
        if (this.timerId) { clearInterval(this.timerId); this.timerId = null; }
    }

    tick() {
        if (this.gameOver) { this.stopTimer(); return; }
        this.dir = { ...this.nextDir };
        const head = this.snake[0];
        const nx = head.x + this.dir.dx;
        const ny = head.y + this.dir.dy;

        // Wall collision
        if (nx < 0 || nx >= SNAKE_COLS || ny < 0 || ny >= SNAKE_ROWS) {
            this._endGame();
            return;
        }

        // Self collision
        for (let i = 0; i < this.snake.length; i++) {
            if (this.snake[i].x === nx && this.snake[i].y === ny) {
                this._endGame();
                return;
            }
        }

        this.snake.unshift({ x: nx, y: ny });

        // Eat food
        if (this.food && nx === this.food.x && ny === this.food.y) {
            this.score += 10 * this.level;
            // Level up every 5 foods
            const newLevel = Math.min(1 + Math.floor(this.snake.length / 5), SNAKE_DELAYS.length);
            if (newLevel !== this.level) {
                this.level = newLevel;
                this.startTimer();
            }
            this._spawnFood();
        } else {
            this.snake.pop();
        }

        // Check if board full (win)
        if (this.snake.length >= SNAKE_COLS * SNAKE_ROWS) {
            this._endGame();
            return;
        }

        this.render();
    }

    _endGame() {
        this.gameOver = true;
        this.stopTimer();
        this._checkBest();
        this.render();
    }

    _checkBest() {
        const isBest = this.score > this.bestScore;
        submitHallOfFameScore(this, "snake", this.score, {
            onSaved: (name) => {
                if (!isBest) { return; }
                this.bestScore = this.score;
                this.bestName = name;
                this._saveBest();
                this.renderInfo();
            },
        });
    }

    render() {
        this.renderField();
        this.renderInfo();
    }

    renderInfo() {
        this.infoBox.updateRow(this.scoreRow, "Score: " + this.score);
        this.infoBox.updateRow(this.levelRow, "Level: " + this.level);
        this.infoBox.updateRow(this.lengthRow, "Length:" + this.snake.length);
        const bestText = this.bestName
            ? this.bestName + " " + this.bestScore
            : "Best:  " + this.bestScore;
        this.bestBox.updateRow(this.bestRow, bestText);
    }

    renderField() {
        // Build grid from snake cells
        const grid = Array.from({ length: SNAKE_ROWS }, () => new Array(SNAKE_COLS).fill(0));
        // 1=body, 2=head, 3=food
        for (let i = 0; i < this.snake.length; i++) {
            const s = this.snake[i];
            grid[s.y][s.x] = i === 0 ? 2 : 1;
        }
        if (this.food) { grid[this.food.y][this.food.x] = 3; }

        this.fieldView.setGrid(SNAKE_COLS, grid.flatMap(row => row.map(value => value === 2
            ? { text: "@@", kind: "head", foreground: 14 } : value === 1 ? { text: "██", kind: "segment", foreground: 10 }
                : value === 3 ? { text: "◆ ", kind: "food", foreground: 12 } : { text: "  " })))
            .setMessage(this.gameOver ? `GAME OVER\nScore: ${this.score}\nPress Enter` : "");
    }
}

Object.assign(TV, {
    TVGameDialog,
    TVPuzzleDialog,
    TVTetrisGameView,
    TVTetrisGameInfo,
    TVTetrisSetupDialog,
    TVTetrisDialog,
    TVMinesDialog,
    TVBreakOutDialog,
    TVSokobanDialog,
    TVLinesDialog,
    TVReversiDialog,
    TVLudoDialog,
    TVMastermindDialog,
    TVTronDialog,
    TVHanoiDialog,
    TVSnakeDialog,
});
})(typeof window !== "undefined" ? window : globalThis);
