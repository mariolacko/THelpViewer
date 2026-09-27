// Turbo Vision screen savers — base class and individual saver modes.
(function () {
"use strict";
const TV = window.THelpViewerTV = window.THelpViewerTV || {};
const { TVView, TVRect, TVEvent, evMouseDown, evMouseMove, evKeyDown, escapeHtml } = TV;

const SAVER_FPS = 15;

// ── Base screen saver ───────────────────────────────────────────────

class TVScreenSaver extends TVView {
    static _overlay = null;
    static _canvas = null;
    static _active = null;
    static _idleTimer = null;
    static _idleBound = false;

    static _ensureOverlay() {
        if (TVScreenSaver._overlay) {
            return;
        }
        const overlay = document.createElement("div");
        overlay.className = "tv-saver-overlay";
        overlay.hidden = true;
        overlay.setAttribute("aria-label", "Screen saver — move the mouse, click or press any key to dismiss");
        const canvas = document.createElement("div");
        canvas.className = "tv-saver-canvas";
        overlay.appendChild(canvas);
        document.body.appendChild(overlay);
        const forward = (what) => (nativeEvent) => {
            TVScreenSaver._active?.dispatchEvent(new TVEvent(what, { nativeEvent }));
        };
        overlay.addEventListener("click", forward(evMouseDown));
        overlay.addEventListener("mousedown", forward(evMouseDown));
        overlay.addEventListener("mousemove", forward(evMouseMove));
        overlay.addEventListener("touchstart", forward(evMouseDown));
        overlay.addEventListener("keydown", forward(evKeyDown));
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

    static installIdleStart(timeoutMs = 5 * 60 * 1000) {
        if (TVScreenSaver._idleBound) {
            return;
        }
        const saverNames = Object.keys(TVScreenSaver.modes || {});
        if (!saverNames.length) {
            return;
        }
        const resetIdleTimer = () => {
            if (TVScreenSaver._idleTimer !== null) {
                clearTimeout(TVScreenSaver._idleTimer);
            }
            TVScreenSaver._idleTimer = setTimeout(() => {
                TVScreenSaver._idleTimer = null;
                if (!TVScreenSaver.active) {
                    const name = saverNames[Math.floor(Math.random() * saverNames.length)];
                    new TVScreenSaver.modes[name]().start();
                }
            }, timeoutMs);
        };
        for (const eventName of ["mousemove", "mousedown", "keydown", "scroll", "touchstart"]) {
            document.addEventListener(eventName, resetIdleTimer, { passive: true });
        }
        TVScreenSaver._idleBound = true;
        resetIdleTimer();
    }

    constructor() {
        super(new TVRect());
        TVScreenSaver._ensureOverlay();
        this.eventMask |= evMouseMove;
        this.overlay = TVScreenSaver._overlay;
        this.canvas = TVScreenSaver._canvas;
        this.running = false;
        this.timerId = null;
        this.cols = 80;
        this.rows = 25;
        this.previousFocus = null;
        this._onResize = () => {
            if (!this.running) { return; }
            this._measure();
            this.init();
            this.update();
        };
    }

    start() {
        const previousFocus = TVScreenSaver._active?.previousFocus || document.activeElement;
        TVScreenSaver.stop();
        TVScreenSaver._active = this;
        this.bindRoot(this.overlay);
        this.previousFocus = previousFocus instanceof HTMLElement ? previousFocus : null;
        this.overlay.hidden = false;
        this.overlay.tabIndex = 0;
        this.overlay.focus();
        this.running = true;
        this._measure();
        this.init();
        this.update();
        window.addEventListener("resize", this._onResize, { passive: true });
        this.timerId = setInterval(() => {
            if (this.running) { this.update(); }
        }, 1000 / SAVER_FPS);
    }

    stop() {
        this.running = false;
        this.overlay.hidden = true;
        if (this.timerId !== null) {
            clearInterval(this.timerId);
            this.timerId = null;
        }
        window.removeEventListener("resize", this._onResize);
        this.canvas.textContent = "";
        this.overlay.style.background = "";
        this.bindRoot(null);
        if (TVScreenSaver._active === this) {
            TVScreenSaver._active = null;
        }
        const previousFocus = this.previousFocus;
        this.previousFocus = null;
        if (previousFocus?.isConnected) {
            previousFocus.focus();
        }
    }

    _measure() {
        const cell = TV.measureCells ? TV.measureCells() : { width: 9, height: 16 };
        this.cellWidth = cell.width;
        this.cellHeight = cell.height;
        this.cols = Math.max(1, Math.floor(this.overlay.clientWidth / cell.width));
        this.rows = Math.max(1, Math.floor(this.overlay.clientHeight / cell.height));
    }

    handleEvent(event) {
        if (event.what === evMouseDown || event.what === evMouseMove || event.what === evKeyDown) {
            event.nativeEvent?.preventDefault?.();
            event.nativeEvent?.stopPropagation?.();
            this.stop();
            this.clearEvent(event);
        }
    }

    init() { }
    update() { }
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

    update() {
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

    update() {
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
    update() {
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

    update() {
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

// ── Projector ────────────────────────────────────────────────────────
// Adapted from DOS Navigator 1.51's TProjector concept (RIT Research Labs).
// A transparent canvas aperture reveals the live page in place of DOS's saved
// text-mode screen buffer.

class TVScreenSaverProjector extends TVScreenSaver {
    init() {
        this.canvas.textContent = "";
        this.overlay.style.background = "transparent";
        this.surface = document.createElement("canvas");
        this.surface.width = this.overlay.clientWidth;
        this.surface.height = this.overlay.clientHeight;
        this.surface.style.width = "100%";
        this.surface.style.height = "100%";
        this.canvas.appendChild(this.surface);
        this.context = this.surface.getContext("2d");
        this.centerX = Math.floor(this.cols / 2);
        this.centerY = Math.floor(this.rows / 2);
        this.dx = 0;
        this.dy = 0;
        this.stepsRemaining = 0;
        this.frame = 0;
        this.draw();
    }

    update() {
        if (++this.frame % 2 !== 0) { return; }
        if (this.stepsRemaining <= 0) {
            this.dx = Math.floor(Math.random() * 5) - 2;
            this.dy = Math.floor(Math.random() * 5) - 2;
            if (this.dx === 0 && this.dy === 0) { this.dx = 1; }
            this.stepsRemaining = 5 + Math.floor(Math.random() * 12);
        }
        const nextX = this.centerX + this.dx;
        const nextY = this.centerY + this.dy;
        if (nextX < 0 || nextX >= this.cols) { this.dx = -this.dx; }
        if (nextY < 0 || nextY >= this.rows) { this.dy = -this.dy; }
        this.centerX = Math.max(0, Math.min(this.cols - 1, this.centerX + this.dx));
        this.centerY = Math.max(0, Math.min(this.rows - 1, this.centerY + this.dy));
        if (nextX !== this.centerX || nextY !== this.centerY) { this.stepsRemaining = 0; }
        else { this.stepsRemaining--; }
        this.draw();
    }

    draw() {
        if (!this.context) { return; }
        const ctx = this.context;
        ctx.fillStyle = "#000000";
        ctx.fillRect(0, 0, this.surface.width, this.surface.height);
        const edgeDistance = Math.max(
            Math.abs(this.centerX - this.cols / 2) / Math.max(1, this.cols / 2),
            Math.abs(this.centerY - this.rows / 2) / Math.max(1, this.rows / 2),
        );
        const radius = Math.max(1, Math.min(4, Math.round(1 + 3 * edgeDistance)));
        const aspect = Math.max(1, Math.round(this.cellHeight / this.cellWidth));
        for (let y = -radius; y <= radius; y++) {
            const halfWidth = Math.ceil(Math.sqrt(radius * radius - y * y) * aspect);
            ctx.clearRect(
                (this.centerX - halfWidth) * this.cellWidth,
                (this.centerY + y) * this.cellHeight,
                (2 * halfWidth + 1) * this.cellWidth,
                this.cellHeight,
            );
        }
    }
}

// ── Registry ─────────────────────────────────────────────────────────

const SAVER_MODES = {
    stars: TVScreenSaverStars,
    bounce: TVScreenSaverBounce,
    clock: TVScreenSaverClock,
    matrix: TVScreenSaverMatrix,
    projector: TVScreenSaverProjector,
};

TVScreenSaver.modes = SAVER_MODES;

Object.assign(TV, {
    TVScreenSaver,
    TVScreenSaverStars,
    TVScreenSaverBounce,
    TVScreenSaverClock,
    TVScreenSaverMatrix,
    TVScreenSaverProjector,
});
})();
