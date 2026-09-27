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

class TVGameSurface extends TVStaticText {
    constructor(bounds) {
        super(bounds, "");
    }
}

class TVTetrisPreview extends TVGameSurface { static viewName = "tetris-preview"; }
class TVMinesField extends TVGameSurface { static viewName = "mines-grid"; }
class TVBreakOutField extends TVGameSurface { static viewName = "break-field"; }
class TVSokobanField extends TVGameSurface { static viewName = "sokoban-field"; }
class TVLinesField extends TVGameSurface { static viewName = "lines-grid"; }
class TVReversiField extends TVGameSurface { static viewName = "reversi-grid"; }
class TVLudoBoard extends TVGameSurface {
    static viewName = "ludo-board";
}
class TVMastermindBoard extends TVGameSurface { static viewName = "mastermind-board"; }
class TVMastermindStatus extends TVGameSurface { static viewName = "mastermind-status"; }
class TVTronField extends TVGameSurface { static viewName = "tron-field"; }
class TVTronStatus extends TVGameSurface { static viewName = "tron-status"; }
class TVHanoiBoard extends TVGameSurface { static viewName = "hanoi-board"; }
class TVHanoiHistory extends TVGameSurface { static viewName = "hanoi-history"; }
class TVHanoiStatus extends TVGameSurface { static viewName = "hanoi-status"; }
class TVSnakeField extends TVGameSurface { static viewName = "snake-field"; }

class TVGameInfoBox extends TVInfoBox {
    static borderRole = "game-border";
}

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

class TVMinesFaceButton extends TVButton {
    _drawParts() {
        return { ...super._drawParts(), dialog: false, className: "tv-mines-face" };
    }
}

class TVLudoPlayerButton extends TVButton {
    _drawParts() {
        const data = this.commandData;
        return {
            ...super._drawParts(), dialog: false,
            className: `tv-ludo-player-toggle tv-ludo-${data.color || "red"}`,
            ariaLabel: `${data.playerName || this.title} player mode`,
        };
    }
}

class TVLudoPieceButton extends TVButton {
    _drawParts() {
        const data = this.commandData;
        return {
            ...super._drawParts(), dialog: false, className: data.classes || "",
            labelMarkup: '<span class="tv-ludo-piece-glyph">♟</span>',
            ariaLabel: `${data.playerName || "Ludo"} piece ${Number(this.value) + 1}`,
        };
    }
}

class TVMastermindColorButton extends TVButton {
    _drawParts() {
        return {
            ...super._drawParts(),
            className: `tv-mastermind-color tv-mastermind-color-${this.commandData.color ?? 0}`,
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

    setRows(rows) {
        this.body.children.slice().forEach((view) => this.body.remove(view));
        this.body.insertAll(rows);
        this.drawContent();
    }
}

class TVHallRow extends TVGroup {
    constructor(bounds, kind, rank, player, score) {
        super(bounds);
        this.kind = String(kind || "");
        this.insertAll([
            new TVStaticText(new TVRect(1, 0, 5, 1), rank),
            new TVStaticText(new TVRect(6, 0, 24, 1), player),
            new TVStaticText(new TVRect(25, 0, 42, 1), score),
        ]);
    }

    _drawRole() { return this.kind; }
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
    const body = new TVGroup(new TVRect(0, 0, 43, 13)).insertAll(
        hallOfFameRows(game, loadHallOfFame(game)),
    );
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

class TVGameDialog extends TVDialog {
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
        if (!wasOpen && this.hallOfFameGame) {
            void loadServerHallOfFame(this.hallOfFameGame).catch(() => {});
        }
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

class TVPuzzleBoard extends TVStaticText {
    static viewName = "puzzle-grid";

    constructor(bounds) {
        super(bounds, "");
    }
}

class TVPuzzleDialog extends TVGameDialog {
    static viewName = "puzzle";
    static palette = "viewer";

    constructor() {
        const GRID_W = 12;  // 4 cols × 3ch
        const INFO_X = GRID_W + 1;
        const gridView = new TVPuzzleBoard(new TVRect(0, 0, GRID_W, 4));
        const movesView = new TVStaticText(new TVRect(INFO_X, 1, INFO_X + 6, 2), "0");
        const puzzleMain = new TVGroup(new TVRect(0, 0, (0) + (INFO_X + 6), (0) + (4))).insertAll([
                gridView,
                new TVStaticText(new TVRect(INFO_X, 0, INFO_X + 6, 1), "Move"),
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
        if (event.what === evMouseDown && event.infoPtr === this.gridView) {
            this.onGridClick(event.nativeEvent);
            this.clearEvent(event);
        } else if (event.what === evKeyDown) {
            this.onKeyDown(event.nativeEvent);
            if (event.nativeEvent?.defaultPrevented) { this.clearEvent(event); }
        }
    }

    onGridClick(event) {
        const tile = event.target.closest("[data-tv-puzzle-index]");
        if (!tile) {
            return;
        }
        if (this.solved) {
            this.scramble();
            return;
        }
        const index = Number.parseInt(tile.getAttribute("data-tv-puzzle-index"), 10);
        if (Number.isInteger(index)) {
            this.moveTile(index);
        }
    }

    onKeyDown(event) {
        if (!this.isActive()) {
            return;
        }
        if (event.target && event.target.closest("input, textarea, select")) {
            return;
        }
        if (this.solved && (event.key.startsWith("Arrow") || event.key.length === 1)) {
            event.preventDefault();
            this.scramble();
            return;
        }
        if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(event.key)) {
            event.preventDefault();
            this.moveByKey(event.key);
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
        const cells = this.board.map((value, index) => {
            const tileCode = value === " " ? -1 : value.charCodeAt(0) - 65;
            const highlight = !this.solved && tileCode >= 0 && PUZZLE_HIGHLIGHT_MAP[tileCode] === 1;
            return `
                <button
                    type="button"
                    class="tv-puzzle-cell${highlight ? " is-highlight" : ""}${value === " " ? " is-blank" : ""}"
                    data-tv-puzzle-index="${index}"
                    aria-label="${value === " " ? "Blank tile" : `Puzzle tile ${escapeHtml(value)}`}"
                >${escapeHtml(value === " " ? " " : value)}</button>
            `;
        });
        this.gridView._setHTML(cells.join(""));
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
    "#ffffff", "#ffff55", "#ff55ff", "#ff5555",
    "#55ffff", "#55ff55", "#5555ff",
];
const TETRIS_DELAYS = [1600, 1200, 1000, 600, 500, 400, 300, 200, 100, 80];
const TETRIS_BEST_KEY = "tv-tetris-best";
const PENTIX_BEST_KEY = "tv-pentix-best";

class TVTetrisGameInfo extends TVInfoBox {
    static borderRole = "game-border";

    constructor(bounds, previewView) {
        const scoreView = new TVInfoRow(new TVRect());
        const linesView = new TVInfoRow(new TVRect());
        const levelView = new TVInfoRow(new TVRect());
        const bestNameView = new TVInfoRow(new TVRect());
        const bestScoreView = new TVInfoRow(new TVRect());
        const nextSeparator = new TVStaticText(new TVRect(), TVInfoBox.separator(bounds.width - 2, "Next"));
        const bestSeparator = new TVStaticText(new TVRect(), TVInfoBox.separator(bounds.width - 2, "Best"));
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

class TVTetrisGameView extends TVStaticText {
    static viewName = "tetris-grid";

    constructor(bounds) {
        super(bounds, "");
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
            this.onKeyDown(event.nativeEvent);
            if (event.nativeEvent?.defaultPrevented) { this.clearEvent(event); }
        }
    }

    onKeyDown(event) {
        const window = this.gameWindow();
        if (!window?.isActive()) { return; }
        if (event.key === "Escape") { event.preventDefault(); window.close(); return; }
        if (this.gameOver) {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                this.newGame();
            }
            return;
        }
        if (this.paused) {
            if (event.key === "p" || event.key === "P") {
                event.preventDefault();
                this.togglePause();
            }
            return;
        }
        switch (event.key) {
            case "ArrowLeft":
            case "Home":
                event.preventDefault();
                this.moveFig(-1, 0);
                break;
            case "ArrowRight":
            case "PageUp":
                event.preventDefault();
                this.moveFig(1, 0);
                break;
            case "ArrowDown":
            case " ":
                event.preventDefault();
                this.hardDrop();
                break;
            case "ArrowUp":
                event.preventDefault();
                this.rotate();
                break;
            case "n": case "N":
                event.preventDefault();
                this.newGame();
                break;
            case "p": case "P":
                event.preventDefault();
                this.togglePause();
                break;
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

        const curColor = TETRIS_COLORS[this.curFig % 7];
        const lines = [];
        for (let row = 0; row < TETRIS_ROWS; row++) {
            const cells = [];
            for (let col = 0; col < TETRIS_COLS; col++) {
                const v = display[row][col];
                if (v > 0) {
                    const color = TETRIS_COLORS[(15 - v) % 7];
                    cells.push(`<span class="tv-tetris-cell tv-tetris-filled" style="color:${color}">██</span>`);
                } else if (v < 0) {
                    cells.push(`<span class="tv-tetris-cell tv-tetris-ghost" style="color:${curColor}">░░</span>`);
                } else {
                    cells.push(`<span class="tv-tetris-cell">  </span>`);
                }
            }
            lines.push(cells.join(""));
        }

        if (this.paused) {
            this._setHTML(`<div class="tv-tetris-overlay-msg">PAUSED<br><small>Press P</small></div>`);
        } else if (this.gameOver) {
            this._setHTML(lines.join("") +
                `<div class="tv-tetris-overlay-msg">GAME OVER<br><small>Score: ${this.score}</small><br><small>Press Enter</small></div>`);
        } else {
            this._setHTML(lines.join(""));
        }
    }

    renderPreview() {
        const PCOLS = TETRIS_PREVIEW_COLS;
        const PROWS = TETRIS_PREVIEW_ROWS;
        const PAD = (TETRIS_INFO_WIDTH - 2) - PCOLS * 2;
        const emptyCell = '<span class="tv-tetris-cell">  </span>';
        const border = '<span class="tv-tetris-preview-border tv-game-border">\u2502</span>';
        const renderRows = (grid, color = "") => {
            const rows = [];
            for (let row = 0; row < PROWS; row++) {
                rows.push(border);
                rows.push(`<span class="tv-tetris-preview-pad">${" ".repeat(Math.floor(PAD / 2))}</span>`);
                for (let col = 0; col < PCOLS; col++) {
                    rows.push(grid[row][col]
                        ? `<span class="tv-tetris-cell tv-tetris-filled" style="color:${color}">██</span>`
                        : emptyCell);
                }
                rows.push(`<span class="tv-tetris-preview-pad">${" ".repeat(Math.ceil(PAD / 2))}</span>`);
                rows.push(border);
            }
            return rows.join("");
        };
        if (!this.preview || this.gameOver) {
            const emptyGrid = Array.from({ length: PROWS }, () => new Array(PCOLS).fill(false));
            this.previewView._setHTML(renderRows(emptyGrid));
            return;
        }
        const fig = TETRIS_FIGURES[this.nextFig];
        const color = TETRIS_COLORS[this.nextFig % 7];
        // Find bounding box of figure
        let minR = 99, maxR = 0, minC = 99, maxC = 0;
        for (const [r, c] of fig) {
            if (r < minR) { minR = r; }
            if (r > maxR) { maxR = r; }
            if (c < minC) { minC = c; }
            if (c > maxC) { maxC = c; }
        }
        const figW = maxC - minC + 1;
        const figH = maxR - minR + 1;
        const offC = Math.floor((PCOLS - figW) / 2) - minC;
        const offR = Math.floor((PROWS - figH) / 2) - minR;
        const grid = Array.from({ length: PROWS }, () => new Array(PCOLS).fill(false));
        for (const [r, c] of fig) {
            const nr = r + offR;
            const nc = c + offC;
            if (nr >= 0 && nr < PROWS && nc >= 0 && nc < PCOLS) { grid[nr][nc] = true; }
        }
        this.previewView._setHTML(renderRows(grid, color));
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
        const previewView = new TVTetrisPreview(new TVRect());
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

class TVMinesDialog extends TVGameDialog {
    static viewName = "mines";

    constructor() {
        const GRID_W = MINES_COLS * 2;  // 18ch
        const remainingView = new TVStaticText(new TVRect(1, 0, 5, 1), String(MINES_COUNT));
        const faceButton = new TVMinesFaceButton(new TVRect(9, 0, 11, 1), "☺", "mines-face", bfNormal);
        const timerView = new TVStaticText(new TVRect(15, 0, 19, 1), "0");
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
        } else if (event.what === evMouseDown && event.infoPtr === this.gridView) {
            if (event.nativeEvent.type === "contextmenu") { this.onCellRightClick(event.nativeEvent); }
            else { this.onCellClick(event.nativeEvent); }
            this.clearEvent(event);
        } else if (event.what === evKeyDown) {
            this.onKeyDown(event.nativeEvent);
            if (event.nativeEvent?.defaultPrevented) { this.clearEvent(event); }
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
            this.timerView.setText(String(this.seconds));
        }, 1000);
    }

    stopTimer() {
        if (this.timerId !== null) {
            clearInterval(this.timerId);
            this.timerId = null;
        }
    }

    onCellClick(event) {
        const cell = event.target.closest("[data-tv-mine-r]");
        if (!cell) { return; }
        const r = Number.parseInt(cell.getAttribute("data-tv-mine-r"), 10);
        const c = Number.parseInt(cell.getAttribute("data-tv-mine-c"), 10);
        this.cursorRow = r;
        this.cursorCol = c;
        this.revealCell(r, c, true);
    }

    onCellRightClick(event) {
        event.preventDefault();
        const cell = event.target.closest("[data-tv-mine-r]");
        if (!cell) { return; }
        const r = Number.parseInt(cell.getAttribute("data-tv-mine-r"), 10);
        const c = Number.parseInt(cell.getAttribute("data-tv-mine-c"), 10);
        this.cursorRow = r;
        this.cursorCol = c;
        this.toggleFlag(r, c, true);
    }

    onKeyDown(event) {
        if (!this.isActive()) { return; }
        if (event.key === "Escape") {
            event.preventDefault();
            this.close();
            return;
        }
        const targetButton = event.target?.closest?.("button");
        if (targetButton && !targetButton.matches("[data-tv-mine-r]")) { return; }
        let nextRow = this.cursorRow;
        let nextCol = this.cursorCol;
        if (event.key === "ArrowUp") {
            nextRow = Math.max(0, nextRow - 1);
        } else if (event.key === "ArrowDown") {
            nextRow = Math.min(MINES_ROWS - 1, nextRow + 1);
        } else if (event.key === "ArrowLeft") {
            nextCol = Math.max(0, nextCol - 1);
        } else if (event.key === "ArrowRight") {
            nextCol = Math.min(MINES_COLS - 1, nextCol + 1);
        } else if (event.key === "Home") {
            nextCol = 0;
        } else if (event.key === "End") {
            nextCol = MINES_COLS - 1;
        } else if (event.key === " " || event.key === "Enter") {
            event.preventDefault();
            this.revealCell(this.cursorRow, this.cursorCol, true);
            return;
        } else if (event.key === "f" || event.key === "F") {
            event.preventDefault();
            this.toggleFlag(this.cursorRow, this.cursorCol, true);
            return;
        } else {
            return;
        }
        event.preventDefault();
        this.cursorRow = nextRow;
        this.cursorCol = nextCol;
        this.render(true);
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
        const NUM_COLORS = ["", "#0000aa", "#00aa00", "#aa0000", "#000080", "#800000", "#008080", "#000000", "#555555"];
        const lines = [];
        for (let r = 0; r < MINES_ROWS; r++) {
            const cells = [];
            for (let c = 0; c < MINES_COLS; c++) {
                const isCursor = r === this.cursorRow && c === this.cursorCol;
                const cursorClass = isCursor ? " is-cursor" : "";
                const stateLabel = this.revealed[r][c]
                    ? (this.board[r][c] === -1 ? "mine" : `revealed ${this.board[r][c] || "empty"}`)
                    : (this.flagged[r][c] ? "flagged" : "hidden");
                const attrs = `type="button" tabindex="${isCursor ? 0 : -1}" aria-label="Row ${r + 1}, column ${c + 1}, ${stateLabel}" data-tv-mine-r="${r}" data-tv-mine-c="${c}"`;
                if (this.revealed[r][c]) {
                    if (this.board[r][c] === -1) {
                        const cls = this.gameOver ? `tv-mines-cell tv-mines-bomb${cursorClass}` : `tv-mines-cell${cursorClass}`;
                        cells.push(`<button class="${cls}" ${attrs}>💣</button>`);
                    } else if (this.board[r][c] === 0) {
                        cells.push(`<button class="tv-mines-cell tv-mines-empty${cursorClass}" ${attrs}> </button>`);
                    } else {
                        const color = NUM_COLORS[this.board[r][c]] || "#000";
                        cells.push(`<button class="tv-mines-cell tv-mines-number${cursorClass}" style="color:${color}" ${attrs}>${this.board[r][c]}</button>`);
                    }
                } else if (this.flagged[r][c]) {
                    cells.push(`<button class="tv-mines-cell tv-mines-flag${cursorClass}" ${attrs}>⚑</button>`);
                } else {
                    cells.push(`<button class="tv-mines-cell tv-mines-hidden${cursorClass}" ${attrs}>■</button>`);
                }
            }
            lines.push(cells.join(""));
        }
        this.gridView._setHTML(lines.join("\n"));

        const flagCount = this.flagged.flat().filter(Boolean).length;
        this.remainingView.setText(String(MINES_COUNT - flagCount));
        this.timerView.setText(String(this.seconds));
        this.faceButton.setTitle(this.gameOver && !this.won ? "☹" : "☺");
        if (focusCursor) {
            const cursor = this.gridView._query(
                `[data-tv-mine-r="${this.cursorRow}"][data-tv-mine-c="${this.cursorCol}"]`
            );
            if (cursor) { cursor.focus(); }
        }
    }
}

// ── BreakOut ────────────────────────────────────────────────────────

const BREAK_COLS = 14;
const BREAK_ROWS = 5;
const BREAK_PADDLE_W = 4;
const BREAK_BEST_KEY = "tv-breakout-best";
const BREAK_BRICK_COLORS = ["#ff5555", "#ffff55", "#55ff55", "#55ffff", "#5555ff"];
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
        const scoreRow = new TVInfoRow(new TVRect());
        const livesRow = new TVInfoRow(new TVRect());
        const levelRow = new TVInfoRow(new TVRect());
        const bestRow = new TVInfoRow(new TVRect());
        const infoBox = new TVGameInfoBox(new TVRect(INFO_X, 0, INFO_X + INFO_W, 5), "Info", [
                scoreRow,
                livesRow,
                levelRow,
            ]);
        const bestBox = new TVGameInfoBox(new TVRect(INFO_X, 5, INFO_X + INFO_W, 8), "Best", [
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
            this.onKeyDown(event.nativeEvent);
            if (event.nativeEvent?.defaultPrevented) { this.clearEvent(event); }
        }
    }

    onKeyDown(event) {
        if (!this.isActive()) { return; }
        if (event.key === "Escape") { event.preventDefault(); this.close(); return; }
        this.keysDown.add(event.key);
        if (this.gameOver && (event.key === "Enter" || event.key === " " || event.key === "n" || event.key === "N")) {
            event.preventDefault();
            this.newGame();
        } else if (this.waiting && (event.key === " " || event.key === "ArrowUp")) {
            event.preventDefault();
            this.launch();
        } else if (event.key === "n" || event.key === "N") {
            event.preventDefault();
            this.newGame();
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
        // Build display grid: fieldW × fieldH
        const lines = [];
        for (let row = 0; row < this.fieldH; row++) {
            const cells = [];
            for (let col = 0; col < this.fieldW; col++) {
                // Bricks at rows 1..BREAK_ROWS
                const brickRow = row - 1;
                if (brickRow >= 0 && brickRow < BREAK_ROWS && col < BREAK_COLS && this.bricks[brickRow][col]) {
                    const color = BREAK_BRICK_COLORS[brickRow % BREAK_BRICK_COLORS.length];
                    cells.push(`<span class="tv-break-cell tv-break-brick" style="color:${color}">▓▓</span>`);
                } else if (row === this.fieldH - 1 && col >= this.paddleX && col < this.paddleX + BREAK_PADDLE_W) {
                    cells.push('<span class="tv-break-cell tv-break-paddle">▀▀</span>');
                } else if (row === this.ballY && col === this.ballX) {
                    cells.push('<span class="tv-break-cell tv-break-ball">⬤ </span>');
                } else {
                    cells.push('<span class="tv-break-cell">  </span>');
                }
            }
            lines.push(cells.join(""));
        }

        if (this.gameOver) {
            this.fieldView._setHTML(lines.join("") +
                `<div class="tv-break-overlay-msg">GAME OVER<br><small>Score: ${this.score}</small><br><small>Press Enter</small></div>`);
        } else if (this.waiting) {
            this.fieldView._setHTML(lines.join("") +
                `<div class="tv-break-overlay-msg"><small>Press Space</small></div>`);
        } else {
            this.fieldView._setHTML(lines.join(""));
        }
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
        const restartButton = new TVButton(new TVRect(INFO_X, 6, INFO_X + 9, 8), '~R~estart', "sokoban-restart", bfNormal);
        const undoButton = new TVButton(new TVRect(INFO_X + 10, 6, INFO_X + 19, 8), '~U~ndo', "sokoban-undo", bfNormal);
        const prevButton = new TVButton(new TVRect(INFO_X, 9, INFO_X + 9, 11), '< Prev', "sokoban-prev", bfNormal);
        const nextButton = new TVButton(new TVRect(INFO_X + 10, 9, INFO_X + 19, 11), 'Next >', "sokoban-next", bfNormal);
        const levelRow = new TVInfoRow(new TVRect());
        const movesRow = new TVInfoRow(new TVRect());
        const pushesRow = new TVInfoRow(new TVRect());
        const infoBox = new TVGameInfoBox(new TVRect(INFO_X, 0, INFO_X + INFO_W, 5), "Info", [
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
            this.onKeyDown(event.nativeEvent);
            if (event.nativeEvent?.defaultPrevented) { this.clearEvent(event); }
        }
    }

    onKeyDown(event) {
        if (!this.isActive()) { return; }
        if (event.key === "Escape") { event.preventDefault(); this.close(); return; }
        if (this.solved) {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                if (this.levelIndex === SOKOBAN_LEVELS.length - 1) {
                    this.newGame();
                } else {
                    this.changeLevel(1);
                }
            }
            return;
        }
        switch (event.key) {
            case "ArrowUp": event.preventDefault(); this.move(0, -1); break;
            case "ArrowDown": event.preventDefault(); this.move(0, 1); break;
            case "ArrowLeft": event.preventDefault(); this.move(-1, 0); break;
            case "ArrowRight": event.preventDefault(); this.move(1, 0); break;
            case "r": case "R": event.preventDefault(); this.loadLevel(this.levelIndex); break;
            case "u": case "U": event.preventDefault(); this.undo(); break;
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
        if (this.fieldView.root) { this.fieldView.root.style.gridTemplateColumns = `repeat(${this.boardW}, 2ch)`; }
        const lines = [];
        for (let y = 0; y < this.boardH; y++) {
            const cells = [];
            for (let x = 0; x < this.boardW; x++) {
                const cell = this.board[y][x];
                const isPlayer = (x === this.playerX && y === this.playerY);
                if (isPlayer) {
                    const onTarget = (cell === ".");
                    cells.push(`<span class="tv-sokoban-cell tv-sokoban-player${onTarget ? " tv-sokoban-on-target" : ""}">☻ </span>`);
                } else if (cell === "#") {
                    cells.push('<span class="tv-sokoban-cell tv-sokoban-wall">██</span>');
                } else if (cell === "$") {
                    cells.push('<span class="tv-sokoban-cell tv-sokoban-box">▓▓</span>');
                } else if (cell === "*") {
                    cells.push('<span class="tv-sokoban-cell tv-sokoban-box-done">▓▓</span>');
                } else if (cell === ".") {
                    cells.push('<span class="tv-sokoban-cell tv-sokoban-target">··</span>');
                } else {
                    cells.push('<span class="tv-sokoban-cell">  </span>');
                }
            }
            lines.push(cells.join(""));
        }
        if (this.solved) {
            const prompt = this.levelIndex === SOKOBAN_LEVELS.length - 1
                ? "Press Enter for new game" : "Press Enter for next level";
            this.fieldView._setHTML(lines.join("") +
                `<div class="tv-sokoban-overlay-msg">SOLVED!<br><small>Moves: ${this.moves}</small><br><small>${prompt}</small></div>`);
        } else {
            this.fieldView._setHTML(lines.join(""));
        }
    }
}

// ── Lines (Color Lines / Shar) ──────────────────────────────────────

const LINES_SIZE = 9;
const LINES_COLORS = ["#ff5555", "#55ff55", "#5555ff", "#ffff55", "#ff55ff", "#55ffff", "#ffffff"];
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
        const scoreRow = new TVInfoRow(new TVRect());
        const bestRow = new TVInfoRow(new TVRect());
        const nextRow = new TVInfoRow(new TVRect());
        const infoBox = new TVGameInfoBox(new TVRect(INFO_X, 0, INFO_X + INFO_W, 4), "Info", [
                scoreRow,
                bestRow,
            ]);
        const nextBox = new TVGameInfoBox(new TVRect(INFO_X, 5, INFO_X + INFO_W, 8), "Next", [
                nextRow,
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
        } else if (event.what === evMouseDown && event.infoPtr === this.gridView) {
            this.onCellClick(event.nativeEvent);
            this.clearEvent(event);
        } else if (event.what === evKeyDown) {
            this.onKeyDown(event.nativeEvent);
            if (event.nativeEvent?.defaultPrevented) { this.clearEvent(event); }
        }
    }

    onKeyDown(event) {
        if (!this.isActive()) { return; }
        if (event.key === "Escape") { event.preventDefault(); this.close(); }
        else if (event.key === "n" || event.key === "N") { event.preventDefault(); this.newGame(); }
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

    onCellClick(event) {
        const cell = event.target.closest("[data-tv-lines-r]");
        if (!cell || this.gameOver) { return; }
        const r = Number.parseInt(cell.getAttribute("data-tv-lines-r"), 10);
        const c = Number.parseInt(cell.getAttribute("data-tv-lines-c"), 10);
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
        const balls = this.nextColors.map((c) =>
            `<span style="color:${LINES_COLORS[(c - 1) % LINES_COLORS.length]}">● </span>`
        ).join("");
        this.nextBox.updateRowHTML(this.nextRow, balls, LINES_SPAWN * 2);
    }

    renderGrid() {
        const lines = [];
        for (let r = 0; r < LINES_SIZE; r++) {
            const cells = [];
            for (let c = 0; c < LINES_SIZE; c++) {
                const attrs = `data-tv-lines-r="${r}" data-tv-lines-c="${c}"`;
                const v = this.board[r][c];
                const isSel = this.selected && this.selected.r === r && this.selected.c === c;
                if (v > 0) {
                    const color = LINES_COLORS[(v - 1) % LINES_COLORS.length];
                    const cls = isSel ? "tv-lines-cell tv-lines-ball tv-lines-selected" : "tv-lines-cell tv-lines-ball";
                    cells.push(`<button class="${cls}" style="color:${color}" ${attrs}>● </button>`);
                } else {
                    cells.push(`<button class="tv-lines-cell tv-lines-empty" ${attrs}>· </button>`);
                }
            }
            lines.push(cells.join(""));
        }
        if (this.gameOver) {
            this.gridView._setHTML(lines.join("") +
                `<div class="tv-lines-overlay-msg">GAME OVER<br><small>Score: ${this.score}</small><br><small>Press N</small></div>`);
        } else {
            this.gridView._setHTML(lines.join(""));
        }
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
        const blackRow = new TVInfoRow(new TVRect());
        const whiteRow = new TVInfoRow(new TVRect());
        const turnRow = new TVInfoRow(new TVRect());
        const infoBox = new TVGameInfoBox(new TVRect(INFO_X, 0, INFO_X + INFO_W, 5), "Info", [
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
        } else if (event.what === evMouseDown && event.infoPtr === this.gridView) {
            this.onCellClick(event.nativeEvent);
            this.clearEvent(event);
        } else if (event.what === evKeyDown) {
            this.onKeyDown(event.nativeEvent);
            if (event.nativeEvent?.defaultPrevented) { this.clearEvent(event); }
        }
    }

    onKeyDown(event) {
        if (!this.isActive()) { return; }
        if (event.key === "Escape") { event.preventDefault(); this.close(); }
        else if (event.key === "n" || event.key === "N") { event.preventDefault(); this.newGame(); }
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

    onCellClick(event) {
        const cell = event.target.closest("[data-tv-reversi-r]");
        if (!cell || this.gameOver || this.currentPlayer !== 1) { return; }
        const r = Number.parseInt(cell.getAttribute("data-tv-reversi-r"), 10);
        const c = Number.parseInt(cell.getAttribute("data-tv-reversi-c"), 10);
        this._makeMove(r, c, 1);
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
        if (!this.gridView.root) { return; }
        const validMoves = new Set();
        if (!this.gameOver && this.currentPlayer === 1) {
            for (let r = 0; r < REVERSI_SIZE; r++) {
                for (let c = 0; c < REVERSI_SIZE; c++) {
                    if (this._getFlips(r, c, 1).length > 0) {
                        validMoves.add(r * REVERSI_SIZE + c);
                    }
                }
            }
        }
        const lines = [];
        for (let r = 0; r < REVERSI_SIZE; r++) {
            const cells = [];
            for (let c = 0; c < REVERSI_SIZE; c++) {
                const attrs = `data-tv-reversi-r="${r}" data-tv-reversi-c="${c}"`;
                const v = this.board[r][c];
                const isValid = validMoves.has(r * REVERSI_SIZE + c);
                if (v === 1) {
                    cells.push(`<button class="tv-reversi-cell tv-reversi-black" ${attrs}>● </button>`);
                } else if (v === 2) {
                    cells.push(`<button class="tv-reversi-cell tv-reversi-white" ${attrs}>○ </button>`);
                } else if (isValid) {
                    cells.push(`<button class="tv-reversi-cell tv-reversi-valid" ${attrs}>· </button>`);
                } else {
                    cells.push(`<button class="tv-reversi-cell tv-reversi-empty" ${attrs}>  </button>`);
                }
            }
            lines.push(cells.join(""));
        }
        this.gridView._setHTML(lines.join(""));
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

class TVLudoDialog extends TVGameDialog {
    static viewName = "ludo";

    constructor() {
        const turnRow = new TVInfoRow(new TVRect());
        const diceRow = new TVInfoRow(new TVRect());
        const statusRow = new TVInfoRow(new TVRect());
        const infoBox = new TVGameInfoBox(new TVRect(46, 0, 68, 5), "Game", [
                turnRow,
                diceRow,
                statusRow,
            ]);
        const playerButtons = LUDO_PLAYER_NAMES.map((name, player) => (
            new TVLudoPlayerButton(new TVRect(0, player + 1, 22, player + 2), name, "ludo-player-mode", bfNormal)
                .setValue(player)
                .setCommandData({ color: LUDO_PLAYER_COLORS[player], playerName: name })
        ));
        const playersBox = new TVGameInfoBox(new TVRect(46, 6, 68, 12), "Players", playerButtons);
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
            else if (event.command === "ludo-player-mode") { this.cyclePlayerMode(Number(event.infoPtr.value)); }
            else { return; }
            this.clearEvent(event);
        } else if (event.what === evMouseDown && event.infoPtr === this.boardView) {
            const piece = event.nativeEvent.target.closest("[data-tv-ludo-piece]");
            if (piece) { this.moveHumanPiece(Number(piece.getAttribute("data-tv-ludo-piece"))); }
            this.clearEvent(event);
        } else if (event.what === evKeyDown) {
            this.onKeyDown(event.nativeEvent);
            if (event.nativeEvent?.defaultPrevented) { this.clearEvent(event); }
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

    onKeyDown(event) {
        if (!this.isActive()) { return; }
        if (event.key === "Escape") {
            event.preventDefault();
            this.close();
            return;
        }
        if (event.key === "n" || event.key === "N") {
            event.preventDefault();
            this.newGame();
            return;
        }
        if ((event.key === "r" || event.key === "R" || event.key === " ") && this.game.phase === "roll") {
            event.preventDefault();
            this.rollHuman();
            return;
        }
        if (this.animating || this.game.phase !== "move" || this.game.playerMode() !== "human") { return; }
        const legal = this.game.legalPieces();
        if (!legal.length) { return; }
        if (/^[1-4]$/.test(event.key)) {
            const piece = Number(event.key) - 1;
            if (legal.includes(piece)) {
                event.preventDefault();
                this.moveHumanPiece(piece);
            }
            return;
        }
        if (["ArrowLeft", "ArrowUp", "ArrowRight", "ArrowDown"].includes(event.key)) {
            event.preventDefault();
            const direction = event.key === "ArrowLeft" || event.key === "ArrowUp" ? -1 : 1;
            const current = Math.max(0, legal.indexOf(this.selectedPiece));
            this.selectedPiece = legal[(current + direction + legal.length) % legal.length];
            this.renderBoard();
            const selected = this.boardView._query(`[data-tv-ludo-piece="${this.selectedPiece}"]`);
            if (selected) { selected.focus(); }
            return;
        }
        if (event.key === "Enter" && legal.includes(this.selectedPiece)) {
            event.preventDefault();
            this.moveHumanPiece(this.selectedPiece);
        }
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
            this.dialog.classList.remove("is-ludo-capture-flash");
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
            this.dialog.classList.add("is-ludo-capture-flash");
        }
        this.render();
        this.captureFlashTimer = window.setTimeout(() => {
            this.captureFlash = null;
            if (this.dialog) {
                this.dialog.classList.remove("is-ludo-capture-flash");
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
            button._setHTML(TVInfoBox.rowHtml(20, label, "tv-game-border"));
            button.root?.classList.toggle("is-current", this.game.currentPlayer === player && this.game.winner === null);
            button.root?.classList.toggle("is-off", mode === "off");
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
        const connected = (fromRow, fromCol, toRow, toCol) => LUDO_ROUTE_EDGES.has(
            `${LUDO_CELL_KEY(fromRow, fromCol)}>${LUDO_CELL_KEY(toRow, toCol)}`
        );
        const line = (html, textKind = "") => `<div class="${escapeHtml(`tv-ludo-ascii-line ${textKind}`.trim())}">${html}</div>`;
        const textCell = (text, classes = []) => `<span class="${escapeHtml(["tv-ludo-ascii-cell", ...classes].join(" "))}">${escapeHtml(text)}</span>`;
        const pathSegment = (text) => `<span class="tv-ludo-ascii-path">${escapeHtml(text)}</span>`;
        const cellContent = (row, col) => {
            const key = LUDO_CELL_KEY(row, col);
            if (!activeCells.has(key)) { return textCell(" "); }
            const startPlayer = LUDO_START_CELLS.get(key);
            const homePlayer = LUDO_HOME_CELLS.get(key);
            const base = LUDO_BASE_CELLS.get(key);
            const occupant = occupied.get(key);
            const cellClasses = [];
            if (startPlayer !== undefined) {
                cellClasses.push("tv-ludo-start", `tv-ludo-${LUDO_PLAYER_COLORS[startPlayer]}`);
            } else if (homePlayer !== undefined) {
                cellClasses.push("tv-ludo-home", `tv-ludo-${LUDO_PLAYER_COLORS[homePlayer]}`);
            } else if (base) {
                cellClasses.push("tv-ludo-base", `tv-ludo-${LUDO_PLAYER_COLORS[base[0]]}`);
            }
            if (!occupant) {
                return textCell(cellClasses.length ? "●" : "○", cellClasses);
            }

            const [player, piece] = occupant;
            const isLegal = player === this.game.currentPlayer && legal.has(piece);
            const isCapturedFlash = this.captureFlash && this.captureFlash.has(`${player}:${piece}`);
            const pieceClasses = [
                "tv-ludo-ascii-piece",
                `tv-ludo-${LUDO_PLAYER_COLORS[player]}`,
                ...cellClasses,
                isLegal ? "is-legal" : "",
                isLegal && piece === this.selectedPiece ? "is-selected" : "",
                animation && player === animation.player && piece === animation.piece ? "is-moving" : "",
                isCapturedFlash ? "is-captured" : "",
            ].filter(Boolean).join(" ");
            return new TVLudoPieceButton(new TVRect(), "", "ludo-piece", bfNormal)
                .setValue(piece)
                .setCommandData({ classes: pieceClasses, playerName: LUDO_PLAYER_NAMES[player] })
                .setState(sfDisabled, !isLegal)
                .draw();
        };

        const lines = [line(" ".repeat(45))];
        for (let row = 0; row < LUDO_BOARD_SIZE; row++) {
            const nodeParts = ["  "];
            for (let col = 0; col < LUDO_BOARD_SIZE; col++) {
                nodeParts.push(cellContent(row, col));
                if (col < LUDO_BOARD_SIZE - 1) {
                    nodeParts.push(pathSegment(connected(row, col, row, col + 1) ? "───" : "   "));
                }
            }
            nodeParts.push("  ");
            lines.push(line(nodeParts.join("")));
            if (row === LUDO_BOARD_SIZE - 1) { break; }

            const pathParts = ["  "];
            for (let col = 0; col < LUDO_BOARD_SIZE; col++) {
                pathParts.push(pathSegment(connected(row, col, row + 1, col) ? "│" : " "));
                if (col < LUDO_BOARD_SIZE - 1) { pathParts.push("   "); }
            }
            pathParts.push("  ");
            lines.push(line(pathParts.join("")));
        }
        lines.push(line(" ".repeat(45)));
        this.boardView._setHTML(lines.join(""));
    }
}

// ── Mastermind ───────────────────────────────────────────────────────

class TVMastermindDialog extends TVGameDialog {
    static viewName = "mastermind";

    constructor() {
        const paletteButtons = Array.from({ length: 6 }, (_, color) => {
            const x = 34 + (color % 3) * 6;
            const y = 2 + Math.floor(color / 3) * 2;
            return new TVMastermindColorButton(new TVRect(x, y, x + 5, y + 2), String(color + 1), "mastermind-color", bfNormal)
                .setValue(color)
                .setCommandData({ color });
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
            if (event.command === "mastermind-color") { this.setColor(Number(event.infoPtr.value)); }
            else if (event.command === "mastermind-guess") { this.submitGuess(); }
            else if (event.command === "mastermind-new") { this.newGame(); }
            else { return; }
            this.clearEvent(event);
        } else if (event.what === evMouseDown && event.infoPtr === this.boardView) {
            const peg = event.nativeEvent.target.closest("[data-tv-mastermind-peg]");
            if (peg) {
                this.game.cursor = Number(peg.dataset.tvMastermindPeg);
                this.render();
            }
            this.clearEvent(event);
        } else if (event.what === evKeyDown) {
            this.onKeyDown(event.nativeEvent);
            if (event.nativeEvent?.defaultPrevented) { this.clearEvent(event); }
        }
    }

    onKeyDown(event) {
        if (!this.isActive()) { return; }
        if (/^[1-6]$/.test(event.key)) {
            event.preventDefault();
            this.setColor(Number(event.key) - 1);
        } else if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
            event.preventDefault();
            const step = event.key === "ArrowLeft" ? -1 : 1;
            this.game.cursor = (this.game.cursor + step + this.game.codeLength) % this.game.codeLength;
            this.render();
        } else if (event.key === "Enter" || event.key.toLocaleLowerCase() === "g") {
            event.preventDefault();
            this.submitGuess();
        } else if (event.key.toLocaleLowerCase() === "n") {
            event.preventDefault();
            this.newGame();
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

    renderPeg(color, { current = false, position = -1 } = {}) {
        const classes = [
            "tv-mastermind-peg",
            `tv-mastermind-color-${color}`,
            current && position === this.game.cursor ? "is-selected" : "",
        ].filter(Boolean).join(" ");
        const attrs = current ? ` type="button" data-tv-mastermind-peg="${position}"` : "";
        const tag = current ? "button" : "span";
        return `<${tag}${attrs} class="${classes}" aria-label="Color ${color + 1}">●</${tag}>`;
    }

    render() {
        const rows = [];
        for (let index = 0; index < this.game.maxTurns; index += 1) {
            const turn = this.game.turns[index];
            const isCurrent = this.game.status === "playing" && index === this.game.turns.length;
            const pegs = turn
                ? turn.guess.map((color) => this.renderPeg(color)).join("")
                : isCurrent
                    ? this.game.currentGuess.map((color, position) => this.renderPeg(color, { current: true, position })).join("")
                    : '<span class="tv-mastermind-empty">· · · ·</span>';
            const feedback = turn ? ` ${"●".repeat(turn.exact)}${"○".repeat(turn.misplaced)}` : "";
            rows.push(`<div class="tv-mastermind-row${isCurrent ? " is-current" : ""}"><span>${String(index + 1).padStart(2, " ")}.</span>${pegs}<span class="tv-mastermind-feedback">${feedback}</span></div>`);
        }
        this.boardView._setHTML(rows.join(""));
        this.guessButton.setState(sfDisabled, this.game.status !== "playing");
        if (this.game.status === "won") {
            this.statusView.setText(`Code broken in ${this.game.turns.length} turn(s).`);
        } else if (this.game.status === "lost") {
            this.statusView._setHTML(`No turns left. Code: ${this.game.secret.map((color) => this.renderPeg(color)).join("")}`);
        } else {
            this.statusView.setText("1-6 choose color, arrows move, Enter guesses.");
        }
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
        const statusView = new TVTronStatus(new TVRect(infoX, 5, infoX + 22, 9));
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
            this.onKeyDown(event.nativeEvent);
            if (event.nativeEvent?.defaultPrevented) { this.clearEvent(event); }
        }
    }

    onKeyDown(event) {
        if (!this.isActive()) { return; }
        const key = event.key.length === 1 ? event.key.toLocaleLowerCase() : event.key;
        const direction = TRON_DIRECTIONS.get(key);
        if (direction) {
            event.preventDefault();
            this.game.queueDirection(direction[0], direction[1], direction[2]);
        } else if (key === "n" || (this.game.status !== "running" && event.key === "Enter")) {
            event.preventDefault();
            this.newGame();
        } else if (key === "p") {
            event.preventDefault();
            this.togglePause();
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
                const playerClass = owner === 0 ? " tv-tron-player-one" : owner === 1 ? " tv-tron-player-two" : "";
                const headClass = head !== undefined ? " is-head" : "";
                cells.push(`<span class="tv-tron-cell${playerClass}${headClass}">${owner === undefined ? "  " : head !== undefined ? "@@" : "██"}</span>`);
            }
        }
        this.fieldView._setHTML(cells.join(""));
    }
}

// ── Tower of Hanoi ──────────────────────────────────────────────────

class TVHanoiDialog extends TVGameDialog {
    static viewName = "hanoi";

    constructor() {
        const boardView = new TVHanoiBoard(new TVRect(1, 1, 55, 11));
        const historyView = new TVHanoiHistory(new TVRect(56, 1, 76, 9));
        const undoButton = new TVButton(new TVRect(56, 9, 68, 11), "~U~ndo", "hanoi-undo", bfNormal);
        const newButton = new TVButton(new TVRect(56, 12, 68, 14), "~N~ew", "hanoi-new", bfDefault);
        const statusView = new TVHanoiStatus(new TVRect(1, 12, 55, 14));
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
        this.bind();
        this.render();
    }

    bind() {
        this.boardView.root.addEventListener("dragstart", (event) => {
            const disk = event.target.closest("[data-tv-hanoi-disk][draggable=\"true\"]");
            if (!disk) { event.preventDefault(); return; }
            this.dragTower = Number(disk.dataset.tvHanoiTower);
            this.selectedTower = this.dragTower;
            event.dataTransfer?.setData("text/plain", String(this.dragTower));
            if (event.dataTransfer) { event.dataTransfer.effectAllowed = "move"; }
            disk.closest(".tv-hanoi-tower")?.classList.add("is-selected");
        });
        this.boardView.root.addEventListener("dragover", (event) => {
            if (event.target.closest("[data-tv-hanoi-tower]")) { event.preventDefault(); }
        });
        this.boardView.root.addEventListener("drop", (event) => {
            const tower = event.target.closest("[data-tv-hanoi-tower]");
            if (!tower || this.dragTower === null) { return; }
            event.preventDefault();
            const from = this.dragTower;
            this.dragTower = null;
            this.selectedTower = null;
            this.focusedTower = Number(tower.dataset.tvHanoiTower);
            this.move(from, this.focusedTower, true);
        });
        this.boardView.root.addEventListener("dragend", () => {
            this.dragTower = null;
            this.selectedTower = null;
            this.render(false);
        });
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand) {
            if (event.command === "hanoi-undo") { this.undo(); }
            else if (event.command === "hanoi-new") { this.newGame(); }
            else { return; }
            this.clearEvent(event);
        } else if (event.what === evMouseDown && event.infoPtr === this.boardView) {
            const tower = event.nativeEvent.target.closest("[data-tv-hanoi-tower]");
            if (tower) {
                this.focusedTower = Number(tower.dataset.tvHanoiTower);
                this.activateTower(this.focusedTower);
            }
            this.clearEvent(event);
        } else if (event.what === evKeyDown) {
            this.onKeyDown(event.nativeEvent);
            if (event.nativeEvent?.defaultPrevented) { this.clearEvent(event); }
        }
    }

    onKeyDown(event) {
        if (!this.isActive()) { return; }
        if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
            event.preventDefault();
            const step = event.key === "ArrowLeft" ? -1 : 1;
            this.focusTower((this.focusedTower + step + 3) % 3);
        } else if (/^[1-3]$/.test(event.key)) {
            event.preventDefault();
            this.focusTower(Number(event.key) - 1);
        } else if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            this.activateTower(this.focusedTower);
        } else if (event.key.toLocaleLowerCase() === "u") {
            event.preventDefault();
            this.undo();
        } else if (event.key.toLocaleLowerCase() === "n") {
            event.preventDefault();
            this.newGame();
        }
    }

    open() {
        super.open();
        this.newGame();
        window.requestAnimationFrame(() => this.focusTower(0));
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
        this.boardView._query(`[data-tv-hanoi-tower="${this.focusedTower}"]`)?.focus();
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
            this.boardView._query(`[data-tv-hanoi-tower="${this.focusedTower}"]`)?.focus();
        }
    }

    renderBoard() {
        this.boardView._setHTML(this.game.towers.map((disks, tower) => {
            const top = this.game.top(tower);
            const diskMarkup = disks.map((disk) => (
                `<span class="tv-hanoi-disk tv-hanoi-disk-${disk}" data-tv-hanoi-disk="${disk}" data-tv-hanoi-tower="${tower}"`
                + ` style="--tv-hanoi-disk-width:${4 + disk * 2}ch" draggable="${disk === top}">${disk}</span>`
            )).join("");
            const selected = this.selectedTower === tower ? " is-selected" : "";
            return `<div class="tv-hanoi-tower${selected}" data-tv-hanoi-tower="${tower}" role="button" tabindex="${tower === this.focusedTower ? 0 : -1}" aria-label="Tower ${tower + 1}"><span class="tv-hanoi-rod" aria-hidden="true"></span>${diskMarkup}<span class="tv-hanoi-base" aria-hidden="true">${"═".repeat(16)}</span><span class="tv-hanoi-number">${tower + 1}</span></div>`;
        }).join(""));
    }

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
        const scoreRow = new TVInfoRow(new TVRect());
        const levelRow = new TVInfoRow(new TVRect());
        const lengthRow = new TVInfoRow(new TVRect());
        const bestRow = new TVInfoRow(new TVRect());
        const infoBox = new TVGameInfoBox(new TVRect(INFO_X, 0, INFO_X + INFO_W, 5), "Info", [
                scoreRow,
                levelRow,
                lengthRow,
            ]);
        const bestBox = new TVGameInfoBox(new TVRect(INFO_X, 5, INFO_X + INFO_W, 8), "Best", [
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
            this.onKeyDown(event.nativeEvent);
            if (event.nativeEvent?.defaultPrevented) { this.clearEvent(event); }
        }
    }

    onKeyDown(event) {
        if (!this.isActive()) { return; }
        if (event.key === "Escape") { event.preventDefault(); this.close(); return; }
        if (this.gameOver && (event.key === "Enter" || event.key === " " || event.key === "n" || event.key === "N")) {
            event.preventDefault();
            this.newGame();
            return;
        }
        switch (event.key) {
            case "ArrowUp":    if (this.dir.dy !== 1)  { this.nextDir = { dx: 0, dy: -1 }; } event.preventDefault(); break;
            case "ArrowDown":  if (this.dir.dy !== -1) { this.nextDir = { dx: 0, dy: 1 }; }  event.preventDefault(); break;
            case "ArrowLeft":  if (this.dir.dx !== 1)  { this.nextDir = { dx: -1, dy: 0 }; } event.preventDefault(); break;
            case "ArrowRight": if (this.dir.dx !== -1) { this.nextDir = { dx: 1, dy: 0 }; }  event.preventDefault(); break;
            case "n": case "N": event.preventDefault(); this.newGame(); break;
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

        const lines = [];
        for (let y = 0; y < SNAKE_ROWS; y++) {
            const cells = [];
            for (let x = 0; x < SNAKE_COLS; x++) {
                const v = grid[y][x];
                if (v === 2) {
                    cells.push('<span class="tv-snake-cell tv-snake-head">@@</span>');
                } else if (v === 1) {
                    cells.push('<span class="tv-snake-cell tv-snake-segment">██</span>');
                } else if (v === 3) {
                    cells.push('<span class="tv-snake-cell tv-snake-food">◆ </span>');
                } else {
                    cells.push('<span class="tv-snake-cell">  </span>');
                }
            }
            lines.push(cells.join(""));
        }

        if (this.gameOver) {
            this.fieldView._setHTML(lines.join("") +
                `<div class="tv-snake-overlay-msg">GAME OVER<br><small>Score: ${this.score}</small><br><small>Press Enter</small></div>`);
        } else {
            this.fieldView._setHTML(lines.join(""));
        }
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
