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

const LUDO_RULES_EXPORTS = {
    LudoGame,
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

Object.assign(TV, LUDO_RULES_EXPORTS);

if (typeof module === "object" && module.exports && !(root && root.document)) {
    module.exports = LUDO_RULES_EXPORTS;
    return;
}

const {
    escapeHtml,
    renderHotkeyMarkup,
    TVDialog,
    TVStaticText,
    TVGroup,
    TVButton,
    TVButtonStrip,
    TVLabel,
    TVInputLine,
    TVInfoBox,
    TVFrame,
    fillBorders,
    PUZZLE_START,
    PUZZLE_HIGHLIGHT_MAP,
} = TV;

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

function showBestNamePrompt(desktop, score, callback) {
    const body = new TVGroup({
        w: 28, h: 10,
        children: [
            new TVStaticText({ x: 0, y: 1, w: 28, align: "center", title: true, text: "New High Score!" }),
            new TVStaticText({ x: 0, y: 3, w: 28, align: "center", text: `Score: ${score}` }),
            new TVLabel({ x: 1, y: 5, w: 26, text: "Your name:" }),
            new TVInputLine({
                x: 1, y: 6, w: 26,
                attrs: {
                    "data-tv-best-name-input": true,
                    maxlength: "15",
                    value: "",
                    placeholder: "Player",
                },
            }),
            new TVButton({ x: 9, y: 8, w: 10, className: "is-default", attrs: { "data-tv-best-ok": true }, label: '~O~K' }),
        ],
    }).renderMarkup();
    const dlg = new TVDialog({
        desktop,
        ariaLabel: "High Score",
        title: "High Score",
        closeAttrs: { "data-tv-best-close": true, "aria-label": "Close" },
        bodyMarkup: body,
        footerMarkup: TVDialog.footerMarkup(),
        width: "32ch",
        height: "min(13em, calc(100% - 2em))",
    });
    const input = dlg.query("[data-tv-best-name-input]");
    const finish = () => {
        const name = (input ? input.value.trim() : "") || "Player";
        dlg.close();
        dlg.overlay.remove();
        callback(name);
    };
    dlg.bindCommonClose(() => finish());
    dlg.bindDrag();
    const okBtn = dlg.query("[data-tv-best-ok]");
    if (okBtn) { okBtn.addEventListener("click", () => finish()); }
    if (input) {
        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter") { e.preventDefault(); finish(); }
        });
    }
    dlg.open();
    if (input) { input.focus(); }
}

// ── Puzzle (15-game) ────────────────────────────────────────────────

class TVPuzzleDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const GRID_W = 12;  // 4 cols × 3ch
        const INFO_X = GRID_W + 1;
        const puzzleMain = new TVGroup({
            w: INFO_X + 6, h: 4,
            children: [
                new TVStaticText({
                    x: 0, y: 0, w: GRID_W, h: 4,
                    attrs: { "data-tv-puzzle-grid": true },
                }),
                new TVStaticText({ x: INFO_X, y: 0, w: 6, text: "Move" }),
                new TVStaticText({
                    x: INFO_X, y: 1, w: 6,
                    attrs: { "data-tv-puzzle-moves": true },
                    text: "0",
                }),
            ],
        }).renderMarkup();
        super({
            desktop,
            windowClass: "tv-puzzle-window",
            ariaLabel: "Puzzle",
            title: "Puzzle",
            closeAttrs: {
                "data-tv-puzzle-close": true,
                "aria-label": "Close puzzle",
            },
            bodyMarkup: puzzleMain,
            footerMarkup: TVDialog.footerMarkup(),
            width: "20ch",
            height: "min(6em, calc(100% - 2em))",
            left: "4ch",
            top: "3em",
        });
        this.grid = this.query("[data-tv-puzzle-grid]");
        this.movesNode = this.query("[data-tv-puzzle-moves]");
        this.board = [...PUZZLE_START];
        this.moves = 0;
        this.solved = false;
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bind();
        this.scramble();
    }

    bind() {
        if (this.grid) {
            this.grid.addEventListener("click", (event) => this.onGridClick(event));
        }
        document.addEventListener("keydown", (event) => this.onKeyDown(event));
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
        this.solved = this.board.every((value, index) => value === PUZZLE_START[index]);
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
        if (!this.grid) {
            return;
        }
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
        this.grid.innerHTML = cells.join("");
        if (this.movesNode) {
            this.movesNode.textContent = String(this.moves).padStart(3, " ");
        }
    }
}

// ── Tetris (DOS Navigator style) ────────────────────────────────────

const TETRIS_COLS = 12;  // DN: Shi = 12
const TETRIS_ROWS = 18;
const TETRIS_PREVIEW_COLS = 7;
const TETRIS_PREVIEW_ROWS = 7;
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

class TVTetrisDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        // Layout in character cells: grid 24×20 left, info panel 22×20 right
        const GRID_W = TETRIS_COLS * 2;  // 24ch
        const INFO_X = GRID_W + 1;       // 25ch
        const INFO_W = 22;               // 22ch

        const infoBox = new TVInfoBox({
            x: INFO_X, y: 0, w: INFO_W, name: "info", title: "Info", borderClass: "tv-game-border",
            children: [
                new TVStaticText({ tag: "span", name: "score", attrs: { "data-tv-info-row": true } }),
                new TVStaticText({ tag: "span", name: "lines", attrs: { "data-tv-info-row": true } }),
                new TVStaticText({ tag: "span", name: "level", attrs: { "data-tv-info-row": true } }),
                new TVStaticText({ tag: "span", text: TVInfoBox.separator(INFO_W - 2, "Next"), attrs: { "data-tv-info-frame": true } }),
                new TVStaticText({ tag: "div", h: TETRIS_PREVIEW_ROWS, attrs: { "data-tv-tetris-preview": true } }),
            ],
        });
        const bestBox = new TVInfoBox({
            x: INFO_X, y: 13, w: INFO_W, name: "best", title: "Best", borderClass: "tv-game-border",
            children: [
                new TVStaticText({ tag: "span", name: "best", attrs: { "data-tv-info-row": true } }),
            ],
        });

        const tetrisMain = new TVGroup({
            w: INFO_X + INFO_W, h: 20,
            children: [
                // Grid (left side)
                new TVStaticText({
                    x: 0, y: 0, w: GRID_W, h: 18,
                    attrs: { "data-tv-tetris-grid": true },
                }),
                // Info panel (right side) — TVInfoBox containers
                infoBox,
                bestBox,
                // Buttons
                new TVButton({ x: INFO_X, y: 17, w: 10, attrs: { type: "button", "data-tv-tetris-new": true }, label: '~N~ew' }),
                new TVButton({ x: INFO_X + 11, y: 17, w: 10, attrs: { type: "button", "data-tv-tetris-pause": true }, label: '~P~ause' }),
                new TVButton({ x: INFO_X, y: 19, w: INFO_W, attrs: { type: "button", "data-tv-tetris-pentix": true }, label: 'Penti~x~' }),
            ],
        }).renderMarkup();

        super({
            desktop,
            ariaLabel: "Tetris",
            title: "Tetris",
            windowClass: "tv-tetris-window",
            closeAttrs: { "data-tv-tetris-close": true, "aria-label": "Close tetris" },
            bodyMarkup: tetrisMain,
            footerMarkup: TVDialog.footerMarkup(),
            width: "50ch",
            height: "min(24em, calc(100% - 2em))",
            left: "4ch",
            top: "2em",
        });

        this.gridEl = this.query("[data-tv-tetris-grid]");
        this.previewEl = this.query("[data-tv-tetris-preview]");
        this.infoBox = infoBox.resolve(this.root);
        this.bestBox = bestBox.resolve(this.root);

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
        this._loadBestData();

        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bind();
    }

    _loadBestData() {
        const b = loadBest(TETRIS_BEST_KEY);
        this.bestScore = b.score;
        this.bestName = b.name;
    }
    _saveBest() {
        saveBest(TETRIS_BEST_KEY, this.bestScore, this.bestName);
    }

    bind() {
        this._onKeyDown = (event) => this.onKeyDown(event);
        document.addEventListener("keydown", this._onKeyDown);
        const newBtn = this.query("[data-tv-tetris-new]");
        if (newBtn) { newBtn.addEventListener("click", () => this.newGame()); }
        const pauseBtn = this.query("[data-tv-tetris-pause]");
        if (pauseBtn) { pauseBtn.addEventListener("click", () => this.togglePause()); }
        const pentixBtn = this.query("[data-tv-tetris-pentix]");
        if (pentixBtn) { pentixBtn.addEventListener("click", () => this.togglePentix()); }
    }

    onKeyDown(event) {
        if (!this.isActive()) { return; }
        if (event.key === "Escape") { event.preventDefault(); this.close(); return; }
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
            case "x": case "X":
                event.preventDefault();
                this.togglePentix();
                break;
        }
    }

    togglePause() {
        if (this.gameOver) { return; }
        this.paused = !this.paused;
        if (this.paused) { this.stopTimer(); } else { this.startTimer(); }
        this.render();
    }

    togglePentix() {
        this.pentix = !this.pentix;
        const titleEl = this.dialog ? this.dialog.querySelector(".tv-dialog-title-text") : null;
        if (titleEl) { titleEl.textContent = this.pentix ? "Pentix" : "Tetris"; }
        const pentixBtn = this.query("[data-tv-tetris-pentix]");
        if (pentixBtn) {
            const labelEl = pentixBtn.querySelector(".tv-dialog-button-label");
            if (labelEl) { labelEl.innerHTML = renderHotkeyMarkup(this.pentix ? 'Tetri~s~' : 'Penti~x~'); }
        }
        this.newGame();
    }

    open() {
        super.open();
        this.newGame();
    }

    close() {
        this.stopTimer();
        super.close();
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
        if (this.score > this.bestScore) {
            this.bestScore = this.score;
            const desktop = this.overlay ? this.overlay.parentElement : document.querySelector(".tv-desktop") || document.body;
            showBestNamePrompt(desktop, this.score, (name) => {
                this.bestName = name;
                this._saveBest();
                this.renderInfo();
            });
        }
    }

    startTimer() {
        this.stopTimer();
        const delay = TETRIS_DELAYS[this.level - 1] || 80;
        this.timerId = setInterval(() => {
            if (!this.isActive() || this.gameOver || this.paused) { return; }
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
        this.infoBox.updateRow("score", "Score: " + this.score);
        this.infoBox.updateRow("lines", "Lines: " + this.lines);
        this.infoBox.updateRow("level", "Level: " + this.level);
        const bestText = this.bestName
            ? this.bestName + " " + this.bestScore
            : "Best:  " + this.bestScore;
        this.bestBox.updateRow("best", bestText);
    }

    renderGrid() {
        if (!this.gridEl) { return; }
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
            this.gridEl.innerHTML = `<div class="tv-tetris-overlay-msg">PAUSED<br><small>Press P</small></div>`;
        } else if (this.gameOver) {
            this.gridEl.innerHTML = lines.join("") +
                `<div class="tv-tetris-overlay-msg">GAME OVER<br><small>Score: ${this.score}</small><br><small>Press Enter</small></div>`;
        } else {
            this.gridEl.innerHTML = lines.join("");
        }
    }

    renderPreview() {
        if (!this.previewEl) { return; }
        const PCOLS = TETRIS_PREVIEW_COLS;
        const PROWS = TETRIS_PREVIEW_ROWS;
        const PAD = 20 - PCOLS * 2;
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
            this.previewEl.innerHTML = renderRows(emptyGrid);
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
        this.previewEl.innerHTML = renderRows(grid, color);
    }
}

// ── Minesweeper ─────────────────────────────────────────────────────

const MINES_ROWS = 9;
const MINES_COLS = 9;
const MINES_COUNT = 10;

class TVMinesDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const GRID_W = MINES_COLS * 2;  // 18ch
        const minesMain = new TVGroup({
            w: GRID_W + 2, h: MINES_ROWS + 1,
            children: [
                new TVStaticText({
                    x: 1, y: 0, w: 4,
                    attrs: { "data-tv-mines-info-value": true, "data-tv-mines-remaining": true },
                    text: String(MINES_COUNT),
                }),
                new TVButton({
                    x: 9, y: 0, w: 2,
                    dialog: false,
                    className: "tv-mines-face",
                    attrs: { type: "button", "data-tv-mines-face": true },
                    label: "☺",
                }),
                new TVStaticText({
                    x: 15, y: 0, w: 4,
                    attrs: { "data-tv-mines-info-value": true, "data-tv-mines-timer": true },
                    text: "0",
                }),
                new TVStaticText({
                    x: 1, y: 1, w: GRID_W, h: MINES_ROWS,
                    attrs: { "data-tv-mines-grid": true },
                }),
            ],
        }).renderMarkup();

        super({
            desktop,
            ariaLabel: "Minesweeper",
            title: "Mines",
            closeAttrs: { "data-tv-mines-close": true, "aria-label": "Close mines" },
            bodyMarkup: minesMain,
            footerMarkup: TVDialog.footerMarkup(),
            width: "22ch",
            height: "min(13em, calc(100% - 2em))",
        });

        this.gridEl = this.query("[data-tv-mines-grid]");
        this.remainingEl = this.query("[data-tv-mines-remaining]");
        this.timerEl = this.query("[data-tv-mines-timer]");
        this.faceBtn = this.query("[data-tv-mines-face]");

        this.board = [];
        this.revealed = [];
        this.flagged = [];
        this.gameOver = false;
        this.won = false;
        this.started = false;
        this.timerId = null;
        this.seconds = 0;

        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bind();
    }

    bind() {
        if (this.gridEl) {
            this.gridEl.addEventListener("click", (event) => this.onCellClick(event));
            this.gridEl.addEventListener("contextmenu", (event) => this.onCellRightClick(event));
        }
        if (this.faceBtn) {
            this.faceBtn.addEventListener("click", () => this.newGame());
        }
        this._onKeyDown = (event) => {
            if (!this.isActive()) { return; }
            if (event.key === "Escape") { event.preventDefault(); this.close(); }
        };
        document.addEventListener("keydown", this._onKeyDown);
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
        this.seconds = 0;
        this.stopTimer();

        let placed = 0;
        while (placed < MINES_COUNT) {
            const r = Math.floor(Math.random() * MINES_ROWS);
            const c = Math.floor(Math.random() * MINES_COLS);
            if (this.board[r][c] !== -1) {
                this.board[r][c] = -1;
                placed++;
            }
        }
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
        this.render();
    }

    startTimer() {
        this.stopTimer();
        this.timerId = setInterval(() => {
            this.seconds++;
            if (this.timerEl) { this.timerEl.textContent = String(this.seconds); }
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
        if (this.gameOver || this.won) { return; }
        if (this.flagged[r][c]) { return; }
        if (!this.started) { this.started = true; this.startTimer(); }
        this.reveal(r, c);
        this.render();
    }

    onCellRightClick(event) {
        event.preventDefault();
        const cell = event.target.closest("[data-tv-mine-r]");
        if (!cell) { return; }
        const r = Number.parseInt(cell.getAttribute("data-tv-mine-r"), 10);
        const c = Number.parseInt(cell.getAttribute("data-tv-mine-c"), 10);
        if (this.gameOver || this.won) { return; }
        if (this.revealed[r][c]) { return; }
        this.flagged[r][c] = !this.flagged[r][c];
        this.render();
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
        }
    }

    render() {
        if (!this.gridEl) { return; }
        const NUM_COLORS = ["", "#0000aa", "#00aa00", "#aa0000", "#000080", "#800000", "#008080", "#000000", "#555555"];
        const lines = [];
        for (let r = 0; r < MINES_ROWS; r++) {
            const cells = [];
            for (let c = 0; c < MINES_COLS; c++) {
                const attrs = `data-tv-mine-r="${r}" data-tv-mine-c="${c}"`;
                if (this.revealed[r][c]) {
                    if (this.board[r][c] === -1) {
                        const cls = this.gameOver ? "tv-mines-cell tv-mines-bomb" : "tv-mines-cell";
                        cells.push(`<button class="${cls}" ${attrs}>💣</button>`);
                    } else if (this.board[r][c] === 0) {
                        cells.push(`<button class="tv-mines-cell tv-mines-empty" ${attrs}> </button>`);
                    } else {
                        const color = NUM_COLORS[this.board[r][c]] || "#000";
                        cells.push(`<button class="tv-mines-cell tv-mines-number" style="color:${color}" ${attrs}>${this.board[r][c]}</button>`);
                    }
                } else if (this.flagged[r][c]) {
                    cells.push(`<button class="tv-mines-cell tv-mines-flag" ${attrs}>⚑</button>`);
                } else {
                    cells.push(`<button class="tv-mines-cell tv-mines-hidden" ${attrs}>■</button>`);
                }
            }
            lines.push(cells.join(""));
        }
        this.gridEl.innerHTML = lines.join("\n");

        const flagCount = this.flagged.flat().filter(Boolean).length;
        if (this.remainingEl) { this.remainingEl.textContent = String(MINES_COUNT - flagCount); }
        if (this.timerEl) { this.timerEl.textContent = String(this.seconds); }
        if (this.faceBtn) {
            const label = this.faceBtn.querySelector(".tv-dialog-button-label") || this.faceBtn;
            if (this.won) { label.textContent = "☺"; }
            else if (this.gameOver) { label.textContent = "☹"; }
            else { label.textContent = "☺"; }
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

class TVBreakOutDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const FIELD_X = 1;                // 1ch offset from left
        const FIELD_W = BREAK_COLS * 2;  // 28ch
        const INFO_X = FIELD_X + FIELD_W + 1;  // 30ch
        const INFO_W = 19;
        const infoBox = new TVInfoBox({
            x: INFO_X, y: 0, w: INFO_W, name: "info", title: "Info", borderClass: "tv-game-border",
            children: [
                new TVStaticText({ tag: "span", name: "score", attrs: { "data-tv-info-row": true } }),
                new TVStaticText({ tag: "span", name: "lives", attrs: { "data-tv-info-row": true } }),
                new TVStaticText({ tag: "span", name: "level", attrs: { "data-tv-info-row": true } }),
            ],
        });
        const bestBox = new TVInfoBox({
            x: INFO_X, y: 5, w: INFO_W, name: "best", title: "Best", borderClass: "tv-game-border",
            children: [
                new TVStaticText({ tag: "span", name: "best", attrs: { "data-tv-info-row": true } }),
            ],
        });
        const breakMain = new TVGroup({
            w: INFO_X + INFO_W, h: 20,
            children: [
                new TVStaticText({
                    x: FIELD_X, y: 0, w: FIELD_W, h: 20,
                    attrs: { "data-tv-break-field": true },
                }),
                infoBox,
                bestBox,
                new TVButton({ x: INFO_X, y: 17, w: INFO_W, attrs: { type: "button", "data-tv-break-new": true }, label: '~N~ew' }),
            ],
        }).renderMarkup();

        super({
            desktop,
            ariaLabel: "BreakOut",
            title: "BreakOut",
            closeAttrs: { "data-tv-break-close": true, "aria-label": "Close breakout" },
            bodyMarkup: breakMain,
            footerMarkup: TVDialog.footerMarkup(),
            width: "53ch",
            height: "min(22em, calc(100% - 2em))",
            left: "4ch",
            top: "2em",
        });

        this.fieldEl = this.query("[data-tv-break-field]");
        this.infoBox = infoBox.resolve(this.root);
        this.bestBox = bestBox.resolve(this.root);

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
        this.bind();
    }

    _loadBestData() {
        const b = loadBest(BREAK_BEST_KEY);
        this.bestScore = b.score;
        this.bestName = b.name;
    }
    _saveBest() {
        saveBest(BREAK_BEST_KEY, this.bestScore, this.bestName);
    }

    bind() {
        this._onKeyDown = (event) => {
            if (!this.isActive()) { return; }
            if (event.key === "Escape") { event.preventDefault(); this.close(); return; }
            this.keysDown.add(event.key);
            if (this.gameOver && (event.key === "Enter" || event.key === " " || event.key === "n" || event.key === "N")) {
                event.preventDefault();
                this.newGame();
                return;
            }
            if (this.waiting && (event.key === " " || event.key === "ArrowUp")) {
                event.preventDefault();
                this.launch();
                return;
            }
            if (event.key === "n" || event.key === "N") {
                event.preventDefault();
                this.newGame();
            }
        };
        this._onKeyUp = (event) => { this.keysDown.delete(event.key); };
        document.addEventListener("keydown", this._onKeyDown);
        document.addEventListener("keyup", this._onKeyUp);
        const newBtn = this.query("[data-tv-break-new]");
        if (newBtn) { newBtn.addEventListener("click", () => this.newGame()); }
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
            if (!this.isActive()) { return; }
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
        if (this.score > this.bestScore) {
            this.bestScore = this.score;
            const desktop = this.overlay ? this.overlay.parentElement : document.querySelector(".tv-desktop") || document.body;
            showBestNamePrompt(desktop, this.score, (name) => {
                this.bestName = name;
                this._saveBest();
                this.renderInfo();
            });
        }
    }

    render() {
        this.renderField();
        this.renderInfo();
    }

    renderInfo() {
        this.infoBox.updateRow("score", "Score: " + this.score);
        this.infoBox.updateRow("lives", "Lives: " + this.lives);
        this.infoBox.updateRow("level", "Level: " + this.level);
        const bestText = this.bestName
            ? this.bestName + " " + this.bestScore
            : "Best:  " + this.bestScore;
        this.bestBox.updateRow("best", bestText);
    }

    renderField() {
        if (!this.fieldEl) { return; }
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
            this.fieldEl.innerHTML = lines.join("") +
                `<div class="tv-break-overlay-msg">GAME OVER<br><small>Score: ${this.score}</small><br><small>Press Enter</small></div>`;
        } else if (this.waiting) {
            this.fieldEl.innerHTML = lines.join("") +
                `<div class="tv-break-overlay-msg"><small>Press Space</small></div>`;
        } else {
            this.fieldEl.innerHTML = lines.join("");
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
        "#. @$.#" +
        "#######"
    },
    { w: 8, h: 6, map:
        "  ####  " +
        "###  #  " +
        "#. $.#  " +
        "### .###" +
        "  #$ @.#" +
        "  ######"
    },
    { w: 9, h: 7, map:
        "  #####  " +
        "  # . #  " +
        "  #$# #  " +
        "###. $###" +
        "#  .$  .#" +
        "# @  $# #" +
        "#########"
    },
    { w: 7, h: 7, map:
        "#######" +
        "#     #" +
        "# # # #" +
        "#.$@$.#" +
        "#.# #.#" +
        "#  $  #" +
        "#######"
    },
    { w: 8, h: 8, map:
        "########" +
        "#      #" +
        "# #$## #" +
        "# . .$ #" +
        "#  $.  #" +
        "# ##$# #" +
        "#  @   #" +
        "########"
    },
];
const SOKOBAN_BEST_KEY = "tv-sokoban-best";

class TVSokobanDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const FIELD_W = 18;  // max 9 cols × 2ch
        const INFO_X = FIELD_W + 1;
        const INFO_W = 20;
        const infoBox = new TVInfoBox({
            x: INFO_X, y: 0, w: INFO_W, name: "info", title: "Info", borderClass: "tv-game-border",
            children: [
                new TVStaticText({ tag: "span", name: "level", attrs: { "data-tv-info-row": true } }),
                new TVStaticText({ tag: "span", name: "moves", attrs: { "data-tv-info-row": true } }),
                new TVStaticText({ tag: "span", name: "pushes", attrs: { "data-tv-info-row": true } }),
            ],
        });
        const sokobanMain = new TVGroup({
            w: INFO_X + INFO_W, h: 11,
            children: [
                new TVStaticText({
                    x: 0, y: 0, w: FIELD_W, h: 10,
                    attrs: { "data-tv-sokoban-field": true },
                }),
                infoBox,
                new TVButton({ x: INFO_X, y: 6, w: 8, attrs: { type: "button", "data-tv-sokoban-restart": true }, label: '~R~estart' }),
                new TVButton({ x: INFO_X + 11, y: 6, w: 8, attrs: { type: "button", "data-tv-sokoban-undo": true }, label: '~U~ndo' }),
                new TVButton({ x: INFO_X, y: 9, w: 8, attrs: { type: "button", "data-tv-sokoban-prev": true }, label: '< Prev' }),
                new TVButton({ x: INFO_X + 11, y: 9, w: 8, attrs: { type: "button", "data-tv-sokoban-next": true }, label: 'Next >' }),
            ],
        }).renderMarkup();

        super({
            desktop,
            ariaLabel: "Sokoban",
            title: "Sokoban",
            closeAttrs: { "data-tv-sokoban-close": true, "aria-label": "Close sokoban" },
            bodyMarkup: sokobanMain,
            footerMarkup: TVDialog.footerMarkup(),
            width: "44ch",
            left: "4ch",
            top: "2em",
        });

        this.fieldEl = this.query("[data-tv-sokoban-field]");
        this.infoBox = infoBox.resolve(this.root);

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

        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bind();
    }

    bind() {
        this._onKeyDown = (event) => this.onKeyDown(event);
        document.addEventListener("keydown", this._onKeyDown);
        const restartBtn = this.query("[data-tv-sokoban-restart]");
        if (restartBtn) { restartBtn.addEventListener("click", () => this.loadLevel(this.levelIndex)); }
        const undoBtn = this.query("[data-tv-sokoban-undo]");
        if (undoBtn) { undoBtn.addEventListener("click", () => this.undo()); }
        const prevBtn = this.query("[data-tv-sokoban-prev]");
        if (prevBtn) { prevBtn.addEventListener("click", () => this.changeLevel(-1)); }
        const nextBtn = this.query("[data-tv-sokoban-next]");
        if (nextBtn) { nextBtn.addEventListener("click", () => this.changeLevel(1)); }
    }

    onKeyDown(event) {
        if (!this.isActive()) { return; }
        if (event.key === "Escape") { event.preventDefault(); this.close(); return; }
        if (this.solved) {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                this.changeLevel(1);
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
        super.open();
        this.loadLevel(this.levelIndex);
        THelpViewerTV.fillBorders(this.dialog);
    }

    changeLevel(dir) {
        const next = this.levelIndex + dir;
        if (next >= 0 && next < SOKOBAN_LEVELS.length) {
            this.loadLevel(next);
        }
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
    }

    render() {
        this.renderField();
        this.renderInfo();
    }

    renderInfo() {
        this.infoBox.updateRow("level", "Level: " + (this.levelIndex + 1) + "/" + SOKOBAN_LEVELS.length);
        this.infoBox.updateRow("moves", "Moves: " + this.moves);
        this.infoBox.updateRow("pushes", "Pushes:" + this.pushes);
    }

    renderField() {
        if (!this.fieldEl) { return; }
        this.fieldEl.style.gridTemplateColumns = `repeat(${this.boardW}, 2ch)`;
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
            this.fieldEl.innerHTML = lines.join("") +
                `<div class="tv-sokoban-overlay-msg">SOLVED!<br><small>Moves: ${this.moves}</small><br><small>Press Enter</small></div>`;
        } else {
            this.fieldEl.innerHTML = lines.join("");
        }
    }
}

// ── Lines (Color Lines / Shar) ──────────────────────────────────────

const LINES_SIZE = 9;
const LINES_COLORS = ["#ff5555", "#55ff55", "#5555ff", "#ffff55", "#ff55ff", "#55ffff", "#ffffff"];
const LINES_MATCH = 5; // need 5 in a row
const LINES_SPAWN = 3; // new balls per turn
const LINES_BEST_KEY = "tv-lines-best";

class TVLinesDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const GRID_W = LINES_SIZE * 2;  // 18ch
        const INFO_X = GRID_W + 1;
        const INFO_W = 18;
        const infoBox = new TVInfoBox({
            x: INFO_X, y: 0, w: INFO_W, name: "info", title: "Info", borderClass: "tv-game-border",
            children: [
                new TVStaticText({ tag: "span", name: "score", attrs: { "data-tv-info-row": true } }),
                new TVStaticText({ tag: "span", name: "best", attrs: { "data-tv-info-row": true } }),
            ],
        });
        const nextBox = new TVInfoBox({
            x: INFO_X, y: 5, w: INFO_W, name: "next", title: "Next", borderClass: "tv-game-border",
            children: [
                new TVStaticText({ tag: "span", name: "next", attrs: { "data-tv-info-row": true } }),
            ],
        });
        const linesMain = new TVGroup({
            w: INFO_X + INFO_W, h: LINES_SIZE + 1,
            children: [
                new TVStaticText({
                    x: 0, y: 0, w: GRID_W, h: LINES_SIZE,
                    attrs: { "data-tv-lines-grid": true },
                }),
                infoBox,
                nextBox,
                new TVButton({ x: INFO_X, y: 9, w: INFO_W, attrs: { type: "button", "data-tv-lines-new": true }, label: '~N~ew' }),
            ],
        }).renderMarkup();

        super({
            desktop,
            ariaLabel: "Lines",
            title: "Lines",
            closeAttrs: { "data-tv-lines-close": true, "aria-label": "Close lines" },
            bodyMarkup: linesMain,
            footerMarkup: TVDialog.footerMarkup(),
            width: "41ch",
            height: "min(13em, calc(100% - 2em))",
            left: "4ch",
            top: "2em",
        });

        this.gridEl = this.query("[data-tv-lines-grid]");
        this.infoBox = infoBox.resolve(this.root);
        this.nextBox = nextBox.resolve(this.root);

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
        this.bind();
    }

    _loadBestData() {
        const b = loadBest(LINES_BEST_KEY);
        this.bestScore = b.score;
        this.bestName = b.name;
    }
    _saveBest() {
        saveBest(LINES_BEST_KEY, this.bestScore, this.bestName);
    }

    bind() {
        if (this.gridEl) {
            this.gridEl.addEventListener("click", (event) => this.onCellClick(event));
        }
        this._onKeyDown = (event) => {
            if (!this.isActive()) { return; }
            if (event.key === "Escape") { event.preventDefault(); this.close(); }
            if (event.key === "n" || event.key === "N") { event.preventDefault(); this.newGame(); }
        };
        document.addEventListener("keydown", this._onKeyDown);
        const newBtn = this.query("[data-tv-lines-new]");
        if (newBtn) { newBtn.addEventListener("click", () => this.newGame()); }
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
        if (this.score > this.bestScore) {
            this.bestScore = this.score;
            const desktop = this.overlay ? this.overlay.parentElement : document.querySelector(".tv-desktop") || document.body;
            showBestNamePrompt(desktop, this.score, (name) => {
                this.bestName = name;
                this._saveBest();
                this.renderInfo();
            });
        }
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
        this.infoBox.updateRow("score", "Score: " + this.score);
        const bestText = this.bestName
            ? this.bestName + " " + this.bestScore
            : "Best:  " + this.bestScore;
        this.infoBox.updateRow("best", bestText);
        const balls = this.nextColors.map((c) =>
            `<span style="color:${LINES_COLORS[(c - 1) % LINES_COLORS.length]}">● </span>`
        ).join("");
        this.nextBox.updateRowHTML("next", balls, LINES_SPAWN * 2);
    }

    renderGrid() {
        if (!this.gridEl) { return; }
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
            this.gridEl.innerHTML = lines.join("") +
                `<div class="tv-lines-overlay-msg">GAME OVER<br><small>Score: ${this.score}</small><br><small>Press N</small></div>`;
        } else {
            this.gridEl.innerHTML = lines.join("");
        }
    }
}

// ── Reversi (Othello) ───────────────────────────────────────────────

const REVERSI_SIZE = 8;
const REVERSI_BEST_KEY = "tv-reversi-wins";

class TVReversiDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const GRID_W = REVERSI_SIZE * 2;  // 16ch
        const INFO_X = GRID_W + 1;
        const INFO_W = 17;
        const infoBox = new TVInfoBox({
            x: INFO_X, y: 0, w: INFO_W, name: "info", title: "Info", borderClass: "tv-game-border",
            children: [
                new TVStaticText({ tag: "span", name: "black", attrs: { "data-tv-info-row": true } }),
                new TVStaticText({ tag: "span", name: "white", attrs: { "data-tv-info-row": true } }),
                new TVStaticText({ tag: "span", name: "turn", attrs: { "data-tv-info-row": true } }),
            ],
        });
        const reversiMain = new TVGroup({
            w: INFO_X + INFO_W, h: REVERSI_SIZE,
            children: [
                new TVStaticText({
                    x: 0, y: 0, w: GRID_W, h: REVERSI_SIZE,
                    attrs: { "data-tv-reversi-grid": true },
                }),
                infoBox,
                new TVButton({ x: INFO_X, y: 6, w: INFO_W, attrs: { type: "button", "data-tv-reversi-new": true }, label: '~N~ew' }),
            ],
        }).renderMarkup();

        super({
            desktop,
            ariaLabel: "Reversi",
            title: "Reversi",
            closeAttrs: { "data-tv-reversi-close": true, "aria-label": "Close reversi" },
            bodyMarkup: reversiMain,
            footerMarkup: TVDialog.footerMarkup(),
            width: "38ch",
            height: "min(10em, calc(100% - 2em))",
            left: "4ch",
            top: "2em",
        });

        this.gridEl = this.query("[data-tv-reversi-grid]");
        this.infoBox = infoBox.resolve(this.root);

        // 0=empty, 1=black(player), 2=white(computer)
        this.board = [];
        this.currentPlayer = 1;
        this.gameOver = false;

        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bind();
    }

    bind() {
        if (this.gridEl) {
            this.gridEl.addEventListener("click", (event) => this.onCellClick(event));
        }
        this._onKeyDown = (event) => {
            if (!this.isActive()) { return; }
            if (event.key === "Escape") { event.preventDefault(); this.close(); }
            if (event.key === "n" || event.key === "N") { event.preventDefault(); this.newGame(); }
        };
        document.addEventListener("keydown", this._onKeyDown);
        const newBtn = this.query("[data-tv-reversi-new]");
        if (newBtn) { newBtn.addEventListener("click", () => this.newGame()); }
    }

    open() {
        super.open();
        this.newGame();
        THelpViewerTV.fillBorders(this.dialog);
    }

    newGame() {
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
        }
        this.render();
        // If it's computer's turn, play after a short delay
        if (!this.gameOver && this.currentPlayer === 2) {
            setTimeout(() => this._computerMove(), 300);
        }
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
        this.infoBox.updateRow("black", "\u25CF You:  " + black);
        this.infoBox.updateRow("white", "\u25CB CPU:  " + white);
        if (this.gameOver) {
            const result = black > white ? "You win!" : (white > black ? "CPU wins" : "Draw");
            this.infoBox.updateRow("turn", result);
        } else {
            this.infoBox.updateRow("turn", "Turn: " + (this.currentPlayer === 1 ? "You" : "CPU"));
        }
    }

    renderGrid() {
        if (!this.gridEl) { return; }
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
        this.gridEl.innerHTML = lines.join("");
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

class TVLudoDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const infoBox = new TVInfoBox({
            w: 22,
            name: "info",
            title: "Game",
            borderClass: "tv-game-border",
            children: [
                new TVStaticText({ tag: "span", name: "turn", attrs: { "data-tv-info-row": true } }),
                new TVStaticText({ tag: "span", name: "dice", attrs: { "data-tv-info-row": true } }),
                new TVStaticText({ tag: "span", name: "status", attrs: { "data-tv-info-row": true } }),
            ],
        });
        const playerButtons = LUDO_PLAYER_NAMES.map((name, player) => new TVButton({
            dialog: false,
            className: `tv-ludo-player-toggle tv-ludo-${LUDO_PLAYER_COLORS[player]}`,
            attrs: { "data-tv-ludo-player-mode": player, "aria-label": `${name} player mode` },
            label: name,
        }));
        const playersBox = new TVInfoBox({
            w: 22,
            title: "Players",
            borderClass: "tv-game-border",
            className: "tv-ludo-players",
            children: playerButtons,
        });
        const controls = new TVButtonStrip({
            className: "tv-ludo-controls",
            buttons: [
                new TVButton({ attrs: { "data-tv-ludo-roll": true }, label: "~R~oll" }),
                new TVButton({ attrs: { "data-tv-ludo-new": true }, label: "~N~ew" }),
            ],
        });
        const side = new TVGroup({
            className: "tv-ludo-side",
            children: [infoBox, playersBox, controls],
        });
        const main = new TVGroup({
            className: "tv-ludo-main",
            children: [
                new TVStaticText({
                    className: "tv-ludo-board",
                    attrs: { "data-tv-ludo-board": true, role: "grid", "aria-label": "Ludo board" },
                }),
                side,
            ],
        }).renderMarkup();

        super({
            desktop,
            windowClass: "tv-ludo-window",
            ariaLabel: "Ludo",
            title: "Ludo",
            closeAttrs: { "data-tv-ludo-close": true, "aria-label": "Close Ludo" },
            bodyMarkup: main,
            footerMarkup: TVDialog.footerMarkup(),
            width: "71ch",
            height: "min(26em, calc(100% - 2em))",
            left: "3ch",
            top: "2em",
        });

        this.game = new LudoGame();
        this.infoBox = infoBox.resolve(this.root);
        this.boardEl = this.query("[data-tv-ludo-board]");
        this.rollButton = this.query("[data-tv-ludo-roll]");
        this.playerButtons = this.queryAll("[data-tv-ludo-player-mode]");
        this.cpuTimer = null;
        this.moveTimer = null;
        this.captureFlashTimer = null;
        this.selectedPiece = null;
        this.notice = "";
        this.started = false;
        this.animating = false;
        this.animation = null;
        this.captureFlash = null;

        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bind();
    }

    bind() {
        if (this.boardEl) {
            this.boardEl.addEventListener("click", (event) => {
                const piece = event.target.closest("[data-tv-ludo-piece]");
                if (!piece) { return; }
                this.moveHumanPiece(Number(piece.getAttribute("data-tv-ludo-piece")));
            });
        }
        if (this.rollButton) {
            this.rollButton.addEventListener("click", () => this.rollHuman());
        }
        const newButton = this.query("[data-tv-ludo-new]");
        if (newButton) {
            newButton.addEventListener("click", () => this.newGame());
        }
        this.playerButtons.forEach((button) => {
            button.addEventListener("click", () => {
                this.cyclePlayerMode(Number(button.getAttribute("data-tv-ludo-player-mode")));
            });
        });
        this._onKeyDown = (event) => this.onKeyDown(event);
        document.addEventListener("keydown", this._onKeyDown);
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
            const selected = this.query(`[data-tv-ludo-piece="${this.selectedPiece}"]`);
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
            if (this.animating || !this.isOpen() || this.game.playerMode() !== "cpu") { return; }
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
        this.infoBox.updateRow("turn", `Turn: ${name}`);
        this.infoBox.updateRow("dice", `Dice: ${this.game.die || "-"}`);
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
        this.infoBox.updateRow("status", status);
        if (this.rollButton) {
            this.rollButton.disabled = this.animating || this.game.winner !== null ||
                this.game.playerMode() !== "human" || this.game.phase !== "roll";
        }
    }

    renderPlayers() {
        this.playerButtons.forEach((button, player) => {
            const mode = this.game.modes[player];
            const home = this.game.pieces[player].filter((progress) => progress >= LUDO_HOME_START).length;
            const current = this.game.currentPlayer === player && this.game.winner === null;
            const name = LUDO_PLAYER_NAMES[player].padEnd(6);
            const label = `${current ? ">" : " "} ${LUDO_PLAYER_NAMES[player][0]} ${name} ${LUDO_MODE_LABELS[mode]} ${home}/4`;
            button.innerHTML = TVInfoBox.rowHtml(20, label, "tv-game-border");
            button.classList.toggle("is-current", this.game.currentPlayer === player && this.game.winner === null);
            button.classList.toggle("is-off", mode === "off");
        });
    }

    renderBoard() {
        if (!this.boardEl) { return; }
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
        const line = (html, className = "") => new TVStaticText({
            className: `tv-ludo-ascii-line ${className}`.trim(),
            html,
        }).renderMarkup();
        const textCell = (text, classes = []) => new TVStaticText({
            tag: "span",
            className: ["tv-ludo-ascii-cell", ...classes].join(" "),
            text,
        }).renderMarkup();
        const pathSegment = (text) => new TVStaticText({
            tag: "span",
            className: "tv-ludo-ascii-path",
            text,
        }).renderMarkup();
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
            return new TVButton({
                dialog: false,
                className: pieceClasses,
                attrs: {
                    "data-tv-ludo-piece": piece,
                    "aria-label": `${LUDO_PLAYER_NAMES[player]} piece ${piece + 1}`,
                    disabled: !isLegal,
                },
                labelMarkup: '<span class="tv-ludo-piece-glyph">♟</span>',
            }).renderMarkup();
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
        this.boardEl.innerHTML = lines.join("");
    }
}

// ── Snake ────────────────────────────────────────────────────────────

const SNAKE_COLS = 20;
const SNAKE_ROWS = 15;
const SNAKE_DELAYS = [200, 160, 130, 110, 90, 75, 60, 50, 40, 35];
const SNAKE_BEST_KEY = "tv-snake-best";

class TVSnakeDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const FIELD_W = SNAKE_COLS * 2;  // 40ch
        const INFO_X = FIELD_W + 1;
        const INFO_W = 18;
        const infoBox = new TVInfoBox({
            x: INFO_X, y: 0, w: INFO_W, name: "info", title: "Info", borderClass: "tv-game-border",
            children: [
                new TVStaticText({ tag: "span", name: "score", attrs: { "data-tv-info-row": true } }),
                new TVStaticText({ tag: "span", name: "level", attrs: { "data-tv-info-row": true } }),
                new TVStaticText({ tag: "span", name: "length", attrs: { "data-tv-info-row": true } }),
            ],
        });
        const bestBox = new TVInfoBox({
            x: INFO_X, y: 5, w: INFO_W, name: "best", title: "Best", borderClass: "tv-game-border",
            children: [
                new TVStaticText({ tag: "span", name: "best", attrs: { "data-tv-info-row": true } }),
            ],
        });
        const snakeMain = new TVGroup({
            w: INFO_X + INFO_W, h: SNAKE_ROWS,
            children: [
                new TVStaticText({
                    x: 0, y: 0, w: FIELD_W, h: SNAKE_ROWS,
                    attrs: { "data-tv-snake-field": true },
                }),
                infoBox,
                bestBox,
                new TVButton({ x: INFO_X, y: 13, w: INFO_W, attrs: { type: "button", "data-tv-snake-new": true }, label: '~N~ew' }),
            ],
        }).renderMarkup();

        super({
            desktop,
            ariaLabel: "Snake",
            title: "Snake",
            closeAttrs: { "data-tv-snake-close": true, "aria-label": "Close snake" },
            bodyMarkup: snakeMain,
            footerMarkup: TVDialog.footerMarkup(),
            width: "64ch",
            height: "min(19em, calc(100% - 2em))",
            left: "4ch",
            top: "2em",
        });

        this.fieldEl = this.query("[data-tv-snake-field]");
        this.infoBox = infoBox.resolve(this.root);
        this.bestBox = bestBox.resolve(this.root);

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
        this.bind();
    }

    _loadBestData() {
        const b = loadBest(SNAKE_BEST_KEY);
        this.bestScore = b.score;
        this.bestName = b.name;
    }
    _saveBest() {
        saveBest(SNAKE_BEST_KEY, this.bestScore, this.bestName);
    }

    bind() {
        this._onKeyDown = (event) => {
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
        };
        document.addEventListener("keydown", this._onKeyDown);
        const newBtn = this.query("[data-tv-snake-new]");
        if (newBtn) { newBtn.addEventListener("click", () => this.newGame()); }
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
        this.timerId = setInterval(() => this.tick(), delay);
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
        if (this.score > this.bestScore) {
            this.bestScore = this.score;
            const desktop = this.overlay ? this.overlay.parentElement : document.querySelector(".tv-desktop") || document.body;
            showBestNamePrompt(desktop, this.score, (name) => {
                this.bestName = name;
                this._saveBest();
                this.renderInfo();
            });
        }
    }

    render() {
        this.renderField();
        this.renderInfo();
    }

    renderInfo() {
        this.infoBox.updateRow("score", "Score: " + this.score);
        this.infoBox.updateRow("level", "Level: " + this.level);
        this.infoBox.updateRow("length", "Length:" + this.snake.length);
        const bestText = this.bestName
            ? this.bestName + " " + this.bestScore
            : "Best:  " + this.bestScore;
        this.bestBox.updateRow("best", bestText);
    }

    renderField() {
        if (!this.fieldEl) { return; }
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
                    cells.push('<span class="tv-snake-cell tv-snake-body">██</span>');
                } else if (v === 3) {
                    cells.push('<span class="tv-snake-cell tv-snake-food">◆ </span>');
                } else {
                    cells.push('<span class="tv-snake-cell">  </span>');
                }
            }
            lines.push(cells.join(""));
        }

        if (this.gameOver) {
            this.fieldEl.innerHTML = lines.join("") +
                `<div class="tv-snake-overlay-msg">GAME OVER<br><small>Score: ${this.score}</small><br><small>Press Enter</small></div>`;
        } else {
            this.fieldEl.innerHTML = lines.join("");
        }
    }
}

Object.assign(TV, {
    TVPuzzleDialog,
    TVTetrisDialog,
    TVMinesDialog,
    TVBreakOutDialog,
    TVSokobanDialog,
    TVLinesDialog,
    TVReversiDialog,
    TVLudoDialog,
    TVSnakeDialog,
});
})(typeof window !== "undefined" ? window : globalThis);
