// Turbo Vision screen savers — base class and individual saver modes.
(function () {
"use strict";
const TV = window.THelpViewerTV = window.THelpViewerTV || {};
const { escapeHtml, displayCp437Char } = TV;

const SAVER_FPS = 15;

// ── Base screen saver ───────────────────────────────────────────────

class TVScreenSaver {
    static _overlay = null;
    static _canvas = null;
    static _active = null;

    static _ensureOverlay() {
        if (TVScreenSaver._overlay) {
            return;
        }
        const overlay = document.createElement("div");
        overlay.className = "tv-saver-overlay";
        overlay.hidden = true;
        overlay.setAttribute("aria-label", "Screen saver — click or press any key to dismiss");
        const canvas = document.createElement("div");
        canvas.className = "tv-saver-canvas";
        overlay.appendChild(canvas);
        document.body.appendChild(overlay);
        overlay.addEventListener("click", () => TVScreenSaver.stop());
        overlay.addEventListener("keydown", () => TVScreenSaver.stop());
        TVScreenSaver._overlay = overlay;
        TVScreenSaver._canvas = canvas;
    }

    static stop() {
        if (TVScreenSaver._active) {
            TVScreenSaver._active.stop();
        }
    }

    static get active() {
        return TVScreenSaver._active;
    }

    constructor() {
        TVScreenSaver._ensureOverlay();
        this.overlay = TVScreenSaver._overlay;
        this.canvas = TVScreenSaver._canvas;
        this.running = false;
        this.timerId = null;
        this.cols = 80;
        this.rows = 25;
    }

    start() {
        TVScreenSaver.stop();
        TVScreenSaver._active = this;
        this.overlay.hidden = false;
        this.overlay.tabIndex = 0;
        this.overlay.focus();
        this.running = true;
        this._measure();
        this.init();
        this.timerId = setInterval(() => {
            if (this.running) { this.tick(); }
        }, 1000 / SAVER_FPS);
    }

    stop() {
        this.running = false;
        this.overlay.hidden = true;
        if (this.timerId !== null) {
            clearInterval(this.timerId);
            this.timerId = null;
        }
        this.canvas.textContent = "";
        if (TVScreenSaver._active === this) {
            TVScreenSaver._active = null;
        }
    }

    _measure() {
        const cell = TV.measureCells ? TV.measureCells() : { width: 9, height: 16 };
        this.cols = Math.max(1, Math.floor(this.overlay.clientWidth / cell.width));
        this.rows = Math.max(1, Math.floor(this.overlay.clientHeight / cell.height));
    }

    init() { }
    tick() { }
}

// ── Stars ────────────────────────────────────────────────────────────

const STAR_COUNT = 60;
const STAR_CHARS = [".", "·", "∙", "*", "✦", "★"];
const STAR_COLORS = ["#555555", "#aaaaaa", "#ffffff", "#ffff55", "#55ffff", "#ff55ff"];

class TVScreenSaverStars extends TVScreenSaver {
    init() {
        this.stars = [];
        for (let i = 0; i < STAR_COUNT; i++) {
            this.stars.push(this._newStar());
        }
    }

    _newStar() {
        return {
            x: Math.random() * this.cols,
            y: Math.random() * this.rows,
            speed: 0.05 + Math.random() * 0.3,
            charIdx: Math.floor(Math.random() * STAR_CHARS.length),
            colorIdx: Math.floor(Math.random() * STAR_COLORS.length),
        };
    }

    tick() {
        for (const s of this.stars) {
            s.y += s.speed;
            if (s.y >= this.rows) {
                s.x = Math.random() * this.cols;
                s.y = 0;
                s.speed = 0.05 + Math.random() * 0.3;
                s.charIdx = Math.floor(Math.random() * STAR_CHARS.length);
                s.colorIdx = Math.floor(Math.random() * STAR_COLORS.length);
            }
        }
        const grid = Array.from({ length: this.rows }, () => new Array(this.cols).fill(null));
        for (const s of this.stars) {
            const r = Math.floor(s.y);
            const c = Math.floor(s.x);
            if (r >= 0 && r < this.rows && c >= 0 && c < this.cols) {
                grid[r][c] = s;
            }
        }
        const lines = [];
        for (let r = 0; r < this.rows; r++) {
            const spans = [];
            for (let c = 0; c < this.cols; c++) {
                const s = grid[r][c];
                if (s) {
                    spans.push(`<span style="color:${STAR_COLORS[s.colorIdx]}">${STAR_CHARS[s.charIdx]}</span>`);
                } else {
                    spans.push(" ");
                }
            }
            lines.push(spans.join(""));
        }
        this.canvas.innerHTML = lines.join("\n");
    }
}

// ── Bounce ───────────────────────────────────────────────────────────

class TVScreenSaverBounce extends TVScreenSaver {
    init() {
        this.text = "THelpViewer";
        this.x = Math.floor(Math.random() * Math.max(1, this.cols - this.text.length));
        this.y = Math.floor(Math.random() * Math.max(1, this.rows - 1));
        this.dx = Math.random() > 0.5 ? 1 : -1;
        this.dy = Math.random() > 0.5 ? 1 : -1;
        this.color = 0;
    }

    tick() {
        this.x += this.dx;
        this.y += this.dy;
        const maxX = this.cols - this.text.length;
        const maxY = this.rows - 1;
        if (this.x <= 0 || this.x >= maxX) { this.dx = -this.dx; this.color = (this.color + 1) % STAR_COLORS.length; }
        if (this.y <= 0 || this.y >= maxY) { this.dy = -this.dy; this.color = (this.color + 1) % STAR_COLORS.length; }
        this.x = Math.max(0, Math.min(maxX, this.x));
        this.y = Math.max(0, Math.min(maxY, this.y));
        const lines = [];
        for (let r = 0; r < this.rows; r++) {
            if (r === Math.floor(this.y)) {
                const pad = " ".repeat(Math.floor(this.x));
                lines.push(`${pad}<span style="color:${STAR_COLORS[this.color]};font-weight:bold">${escapeHtml(this.text)}</span>`);
            } else {
                lines.push(" ".repeat(this.cols));
            }
        }
        this.canvas.innerHTML = lines.join("\n");
    }
}

// ── Clock ────────────────────────────────────────────────────────────

const BIG_DIGITS = [
    ["┌─┐", "│ │", "│ │", "└─┘"],
    ["  ┐", "  │", "  │", "  ┘"],
    ["┌─┐", "┌─┘", "│  ", "└─┘"],
    ["┌─┐", " ─┤", " ─┤", "└─┘"],
    ["┐ ┐", "└─┤", "  │", "  ┘"],
    ["┌─┐", "└─┐", "  │", "└─┘"],
    ["┌─┐", "├─┐", "│ │", "└─┘"],
    ["┌─┐", "  │", "  │", "  ┘"],
    ["┌─┐", "├─┤", "│ │", "└─┘"],
    ["┌─┐", "└─┤", "  │", "└─┘"],
];
const BIG_COLON = ["   ", " · ", " · ", "   "];

class TVScreenSaverClock extends TVScreenSaver {
    tick() {
        const now = new Date();
        const time = [now.getHours(), now.getMinutes(), now.getSeconds()]
            .map((v) => String(v).padStart(2, "0")).join(":");
        const date = [
            now.getFullYear(),
            String(now.getMonth() + 1).padStart(2, "0"),
            String(now.getDate()).padStart(2, "0"),
        ].join("-");

        const bigRows = 4;
        const segments = [];
        for (const ch of time) {
            segments.push(ch === ":" ? BIG_COLON : BIG_DIGITS[parseInt(ch, 10)] || BIG_COLON);
        }
        const bigLines = [];
        for (let row = 0; row < bigRows; row++) {
            bigLines.push(segments.map((s) => s[row]).join(" "));
        }
        const bigWidth = bigLines[0] ? [...bigLines[0]].length : 0;
        const startCol = Math.max(0, Math.floor((this.cols - bigWidth) / 2));
        const startRow = Math.max(0, Math.floor((this.rows - bigRows - 2) / 2));

        const lines = [];
        for (let r = 0; r < this.rows; r++) {
            if (r >= startRow && r < startRow + bigRows) {
                const pad = " ".repeat(startCol);
                lines.push(`${pad}<span style="color:#55ffff">${bigLines[r - startRow]}</span>`);
            } else if (r === startRow + bigRows + 1) {
                const datePad = " ".repeat(Math.max(0, Math.floor((this.cols - date.length) / 2)));
                lines.push(`${datePad}<span style="color:#aaaaaa">${date}</span>`);
            } else {
                lines.push("");
            }
        }
        this.canvas.innerHTML = lines.join("\n");
    }
}

// ── Matrix ───────────────────────────────────────────────────────────

const MATRIX_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@#$%&*+=<>?/\\|~^(){}[].:;,";

class TVScreenSaverMatrix extends TVScreenSaver {
    init() {
        this.matrixGrid = Array.from({ length: this.rows }, () =>
            new Array(this.cols).fill(" ")
        );
        this.matrixBright = Array.from({ length: this.rows }, () =>
            new Array(this.cols).fill(0)
        );
        this.streams = [];
        for (let c = 0; c < this.cols; c++) {
            if (Math.random() < 0.4) {
                this.streams.push(this._newStream(c, true));
            }
        }
    }

    _newStream(col, randomStart) {
        return {
            col,
            head: randomStart ? -Math.floor(Math.random() * this.rows) : -1,
            speed: 0.3 + Math.random() * 0.7,
            trail: 5 + Math.floor(Math.random() * 15),
            accum: 0,
        };
    }

    tick() {
        for (const s of this.streams) {
            s.accum += s.speed;
            while (s.accum >= 1) {
                s.accum -= 1;
                s.head++;
                if (s.head >= 0 && s.head < this.rows) {
                    this.matrixGrid[s.head][s.col] = MATRIX_CHARS[
                        Math.floor(Math.random() * MATRIX_CHARS.length)
                    ];
                    this.matrixBright[s.head][s.col] = s.trail;
                }
                const tailRow = s.head - s.trail;
                if (tailRow >= 0 && tailRow < this.rows) {
                    this.matrixBright[tailRow][s.col] = 0;
                    this.matrixGrid[tailRow][s.col] = " ";
                }
            }
        }
        for (let r = 0; r < this.rows; r++) {
            for (let c = 0; c < this.cols; c++) {
                if (this.matrixBright[r][c] > 0) {
                    this.matrixBright[r][c] -= 0.15;
                    if (this.matrixBright[r][c] <= 0) {
                        this.matrixBright[r][c] = 0;
                        this.matrixGrid[r][c] = " ";
                    }
                }
            }
        }
        this.streams = this.streams.filter((s) => s.head - s.trail < this.rows);
        if (Math.random() < 0.15) {
            const col = Math.floor(Math.random() * this.cols);
            this.streams.push(this._newStream(col, false));
        }
        this._render();
    }

    _render() {
        const lines = [];
        for (let r = 0; r < this.rows; r++) {
            const spans = [];
            for (let c = 0; c < this.cols; c++) {
                const b = this.matrixBright[r][c];
                const ch = this.matrixGrid[r][c];
                if (b > 0 && ch !== " ") {
                    const isHead = this.streams.some(
                        (s) => s.col === c && Math.floor(s.head) === r
                    );
                    if (isHead) {
                        spans.push(`<span style="color:#ccffcc">${ch}</span>`);
                    } else {
                        const intensity = Math.min(1, b / 8);
                        const g = Math.floor(80 + intensity * 175);
                        spans.push(`<span style="color:rgb(0,${g},0)">${ch}</span>`);
                    }
                } else {
                    spans.push(" ");
                }
            }
            lines.push(spans.join(""));
        }
        this.canvas.innerHTML = lines.join("\n");
    }
}

// ── Registry ─────────────────────────────────────────────────────────

const SAVER_MODES = {
    stars: TVScreenSaverStars,
    bounce: TVScreenSaverBounce,
    clock: TVScreenSaverClock,
    matrix: TVScreenSaverMatrix,
};

TVScreenSaver.modes = SAVER_MODES;

Object.assign(TV, {
    TVScreenSaver,
    TVScreenSaverStars,
    TVScreenSaverBounce,
    TVScreenSaverClock,
    TVScreenSaverMatrix,
});
})();
