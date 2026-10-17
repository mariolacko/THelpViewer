// DOSBox backend adapter; window and menu chrome remain shared TVision views.
(function () {
"use strict";
const TV = window.THelpViewerTV;
const { TVView, TVWindow, TVStaticText, TVMessageBox, TVRect, TVPoint, TVEvent, evKeyDown,
    evMouseDown, evMouseUp, evMouseMove, evCommand, sfVisible, sfDragging, escapeHtml, measureCells, fillBorders } = TV;
const PREFIX = new URL("dos/emulators/", document.currentScript.src).href;
let runtimePromise;

async function dosRequest(url, options = {}) {
    const response = await fetch(url, { ...options, cache: "no-store", signal: options.signal || AbortSignal.timeout(30000) });
    if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try { detail = (await response.json()).detail || detail; } catch { /* binary response */ }
        throw new Error(detail);
    }
    return response;
}

function loadRuntime() {
    if (!runtimePromise) {
        runtimePromise = new Promise((resolve, reject) => {
            if (window.emulators) { resolve(window.emulators); return; }
            const script = document.createElement("script");
            script.src = PREFIX + "emulators.js";
            const timer = setTimeout(() => {
                script.remove(); reject(new Error("DOSBox script loading timed out"));
            }, 20000);
            script.onload = () => { clearTimeout(timer); resolve(window.emulators); };
            script.onerror = () => { clearTimeout(timer); script.remove(); reject(new Error("Cannot load DOSBox runtime")); };
            document.head.appendChild(script);
        }).then((runtime) => { runtime.pathPrefix = PREFIX; return runtime; }).catch((error) => { runtimePromise = null; throw error; });
    }
    return runtimePromise;
}

const KEY_CODES = { Escape: 256, Enter: 257, Tab: 258, Backspace: 259, Insert: 260,
    Delete: 261, ArrowRight: 262, ArrowLeft: 263, ArrowDown: 264, ArrowUp: 265,
    PageUp: 266, PageDown: 267, Home: 268, End: 269, CapsLock: 280, NumLock: 282,
    ShiftLeft: 340, ControlLeft: 341, AltLeft: 342, MetaLeft: 343,
    ShiftRight: 344, ControlRight: 345, AltRight: 346, MetaRight: 347,
    Space: 32, Minus: 45, Equal: 61, BracketLeft: 91, BracketRight: 93,
    NumpadDecimal: 330, NumpadComma: 330, NumpadDivide: 331, NumpadMultiply: 332,
    NumpadSubtract: 333, NumpadAdd: 334, NumpadEnter: 335, NumpadEqual: 61,
    Backslash: 92, Semicolon: 59, Quote: 39, Comma: 44, Period: 46, Slash: 47,
    Backquote: 96 };
for (let n = 1; n <= 12; n++) { KEY_CODES[`F${n}`] = 289 + n; }
for (let n = 0; n <= 9; n++) { KEY_CODES[`Digit${n}`] = 48 + n; KEY_CODES[`Numpad${n}`] = 320 + n; }

class TVDosView extends TVView {
    static viewName = "dos-view";
    constructor(bounds) {
        super(bounds);
        this.eventMask |= evMouseUp | evMouseMove;
        this.ci = null;
        this.keys = new Set();
        this.buttons = new Set();
        this.listeners = [];
    }
    draw() {
        const attrs = Object.entries(this._drawAttrs()).map(([key, value]) => `${key}="${escapeHtml(String(value))}"`).join(" ");
        return `<div class="tv-dos-view" ${attrs}><canvas width="640" height="400" tabindex="0" aria-label="DOS keyboard and mouse input"></canvas></div>`;
    }
    bindRoot(root) {
        super.bindRoot(root);
        this.canvas = root?.querySelector("canvas") || null;
        if (!this.canvas) { return this; }
        this.canvas._tvView = this;
        const listen = (target, type, listener, capture = false) => {
            target.addEventListener(type, listener, capture); this.listeners.push([target, type, listener, capture]);
        };
        for (const type of ["keydown", "keyup"]) {
            listen(document, type, (nativeEvent) => {
                if (document.fullscreenElement === this.canvas && this.owner?.getKeyCommand(nativeEvent)) {
                    this.dispatchEvent(new TVEvent(evKeyDown, { nativeEvent, infoPtr: this }));
                }
            }, true);
        }
        for (const [type, what] of [["keydown", evKeyDown], ["keyup", evKeyDown],
            ["mousedown", evMouseDown], ["mouseup", evMouseUp], ["mousemove", evMouseMove]]) {
            const listener = (nativeEvent) => this.dispatchEvent(new TVEvent(what, { nativeEvent, infoPtr: this }));
            listen(this.canvas, type, listener);
        }
        listen(this.canvas, "blur", () => this.releaseInput());
        listen(this.canvas, "contextmenu", (event) => event.preventDefault());
        listen(document, "mouseup", (nativeEvent) => {
            if (this.buttons.size && nativeEvent.target !== this.canvas) {
                this.dispatchEvent(new TVEvent(evMouseUp, { nativeEvent, infoPtr: this }));
            }
        });
        return this;
    }
    capturesKey() { return true; }
    releaseInput() {
        for (const key of this.keys) { this.ci?.sendKeyEvent(key, false); }
        for (const button of this.buttons) { this.ci?.sendMouseButton(button, false); }
        this.keys.clear(); this.buttons.clear();
    }
    handleEvent(event) {
        const native = event.nativeEvent;
        const command = event.what === evKeyDown ? this.owner?.getKeyCommand(native) : "";
        if (!this.owner?.active && !(command && this.canvas && document.fullscreenElement === this.canvas)) { return; }
        if (command) {
            if (native.type === "keydown" && !native.repeat) {
                this.releaseInput();
                this.owner.dispatchEvent(new TVEvent(evCommand, { command }));
            }
            native.preventDefault(); native.stopPropagation(); this.clearEvent(event); return;
        }
        if (!this.ci) { return; }
        const blocked = this.owner.busy || this.owner.paused || this.owner.snapshotting || this.owner.getState?.(sfDragging);
        if (event.what === evKeyDown) {
            if (native.type === "keydown") { this.owner.resumeSound(); }
            if (!blocked) {
                const code = /^Key[A-Z]$/.test(native.code) ? native.code.charCodeAt(3) : KEY_CODES[native.code];
                if (code !== undefined) {
                    const pressed = native.type === "keydown";
                    if (!native.repeat) { this.ci.sendKeyEvent(code, pressed); }
                    pressed ? this.keys.add(code) : this.keys.delete(code);
                }
            }
        } else if ([evMouseDown, evMouseUp, evMouseMove].includes(event.what)) {
            if (blocked) { native.preventDefault(); native.stopPropagation(); this.clearEvent(event); return; }
            if (event.what === evMouseDown) { this.canvas.focus(); this.owner.resumeSound(); }
            const rect = this.canvas.getBoundingClientRect();
            // object-fit:contain leaves letterboxes which are not DOS coordinates.
            const scale = Math.min(rect.width / this.canvas.width, rect.height / this.canvas.height);
            const width = this.canvas.width * scale, height = this.canvas.height * scale;
            this.ci.sendMouseMotion(Math.max(0, Math.min(1, (native.clientX - rect.left - (rect.width - width) / 2) / width)),
                Math.max(0, Math.min(1, (native.clientY - rect.top - (rect.height - height) / 2) / height)));
            if (event.what !== evMouseMove) {
                const button = native.button === 2 ? 1 : native.button === 1 ? 2 : 0;
                const pressed = event.what === evMouseDown;
                this.ci.sendMouseButton(button, pressed);
                pressed ? this.buttons.add(button) : this.buttons.delete(button);
            }
        } else { return; }
        native.preventDefault(); native.stopPropagation(); this.clearEvent(event);
    }
    renderFrame(rgb, rgba) {
        if (!this.ci || !this.canvas || (!rgb && !rgba)) { return; }
        const width = this.ci.width(), height = this.ci.height();
        if (!this.screenReady || this.canvas.width !== width || this.canvas.height !== height) {
            this.screenReady = true;
            this.canvas.width = width; this.canvas.height = height;
            this.owner.fitScreen();
        }
        const image = new ImageData(width, height);
        if (rgba) { image.data.set(rgba); }
        else {
            for (let i = 0, j = 0; i < rgb.length; i += 3, j += 4) {
                image.data[j] = rgb[i]; image.data[j + 1] = rgb[i + 1]; image.data[j + 2] = rgb[i + 2]; image.data[j + 3] = 255;
            }
        }
        this.canvas.getContext("2d").putImageData(image, 0, 0);
    }
    chooseMedia(kind) {
        const input = document.createElement("input");
        input.type = "file"; input.accept = kind === "cd" ? ".iso" : ".img,.ima";
        input.addEventListener("change", () => {
            const file = input.files?.[0];
            if (file) { this.dispatchEvent(new TVEvent(evCommand, { command: "dos-media-selected", infoPtr: { file, kind } })); }
        }, { once: true });
        input.click();
    }
    destroy() {
        this.releaseInput();
        for (const [target, type, listener, capture] of this.listeners) { target.removeEventListener(type, listener, capture); }
        this.listeners = [];
        this.ci = null;
    }
}

class TVDosWindow extends TVWindow {
    static viewName = "dos-window";
    static role = "dos-window";
    constructor(bounds = new TVRect(0, 0, 82, 27), title = "DOS Prompt", number = 0) {
        super(bounds, title, number);
        this.setHelpCtx(TV.TV_HELP_CONTEXTS.hcDosPrompt);
        this.minSize = new TVPoint(42, 15);
        this.view = new TVDosView(new TVRect());
        this.status = new TVStaticText(new TVRect(1, 1, 78, 3), "Preparing DOS C drive...");
        this.insertAll([this.view, this.status]);
        this.active = false;
        this.paused = false;
        this.busy = false;
        this.disposed = false;
        this.media = "";
        this.localDrive = null;
        this.soundSources = new Set();
        this.onError = null;
        this.onChange = null;
        this.onClose = null;
        this.onMenu = null;
        this.closeAction = () => this.onClose?.();
    }
    hasScrollBars() { return false; }
    _screenGeometry(geometry, maxCols, maxRows, fromHeight = false) {
        const cell = measureCells(), canvas = this.view.canvas;
        const ratio = cell.width * canvas.height / (cell.height * canvas.width);
        const maxWidth = Math.max(1, Math.min(maxCols - 2, Math.floor((maxRows - 2) / ratio)));
        const minWidth = Math.max(this.minSize.x - 2, Math.ceil((this.minSize.y - 2) / ratio));
        const wanted = fromHeight ? Math.floor((geometry.rows - 2) / ratio) : geometry.cols - 2;
        const width = Math.min(maxWidth, Math.max(minWidth, wanted));
        return { ...geometry, cols: width + 2, rows: Math.ceil(width * ratio) + 2 };
    }
    fitScreen() {
        this.pendingScreenResize = true;
        const resizer = this.root?._tvResizer, canvas = this.view.canvas;
        if (!resizer?.desktop || !canvas?.width || !canvas.height
            || document.fullscreenElement === canvas || this.root.classList.contains("is-maximized")) { return this; }
        const cell = measureCells(), desktop = resizer.desktop;
        if (!desktop.clientWidth || !desktop.clientHeight) { return this; }
        // Match the shared frame's two columns/rows and its desktop margins.
        const maxCols = Math.max(3, Math.floor(desktop.clientWidth / cell.width) - 2);
        const maxRows = Math.max(3, Math.floor((desktop.clientHeight - 2 * cell.width) / cell.height));
        const fit = (geometry) => {
            const { cols, rows } = this._screenGeometry(geometry, maxCols, maxRows);
            return { cols, rows,
                left: Math.max(0, Math.min(geometry.left, desktop.clientWidth - cols * cell.width)),
                top: Math.max(0, Math.min(geometry.top, desktop.clientHeight - rows * cell.height)),
            };
        };
        const current = resizer.captureGeometry(), geometry = fit(current);
        if (this.zoomGeometry) { this.zoomGeometry = fit(this.zoomGeometry); }
        this.pendingScreenResize = false;
        if (["cols", "rows", "left", "top"].some((key) => geometry[key] !== current[key])) {
            resizer.place(geometry);
            fillBorders(this.root);
            this.onChange?.();
        }
        return this;
    }
    zoom() {
        const resizer = this.root?._tvResizer;
        if (!resizer?.desktop) { return this; }
        if (this.root.classList.contains("is-maximized")) {
            resizer.restore();
        } else if (this.zoomGeometry) {
            resizer.place(this.zoomGeometry);
            this.zoomGeometry = null;
        } else {
            const current = resizer.captureGeometry();
            const cell = measureCells();
            const maxCols = Math.floor(resizer.desktop.clientWidth / cell.width);
            const maxRows = Math.floor(resizer.desktop.clientHeight / cell.height);
            const scale = Math.max(1, Math.min(2,
                (maxCols - 2) / Math.max(1, current.cols - 2),
                (maxRows - 2) / Math.max(1, current.rows - 2)));
            const target = { cols: Math.min(maxCols, Math.round((current.cols - 2) * scale) + 2),
                rows: Math.min(maxRows, Math.round((current.rows - 2) * scale) + 2) };
            const { cols, rows } = this.view.canvas?.width && this.view.canvas.height
                ? this._screenGeometry(target, maxCols, maxRows) : target;
            this.zoomGeometry = current;
            resizer.place({ cols, rows,
                left: Math.max(0, Math.min(current.left - (cols - current.cols) * cell.width / 2,
                    resizer.desktop.clientWidth - cols * cell.width)),
                top: Math.max(0, Math.min(current.top - (rows - current.rows) * cell.height / 2,
                    resizer.desktop.clientHeight - rows * cell.height)),
            });
        }
        if (this.pendingScreenResize) { this.fitScreen(); }
        fillBorders(this.root);
        this.view.canvas?.focus();
        this.onChange?.();
        return this;
    }
    restoreSize() {
        this.zoomGeometry = null;
        super.restoreSize();
        this.fitScreen();
        this.view.canvas?.focus();
        this.onChange?.();
        return this;
    }
    getKeyCommand(key) {
        if (key.metaKey || key.shiftKey) { return ""; }
        if (key.altKey && !key.ctrlKey) {
            if (["Enter", "NumpadEnter"].includes(key.code)) { return "dos-fullscreen"; }
            if (["Pause", "F16"].includes(key.code)) { return "dos-pause"; }
        }
        if (key.ctrlKey && key.altKey) {
            if (key.code === "KeyM") { return "dos-menu"; }
            if (key.code === "KeyR") { return "dos-restart"; }
        }
        return "";
    }
    resumeSound() {
        try {
            const Audio = window.AudioContext || window.webkitAudioContext;
            this.audio ||= Audio ? new Audio() : null;
            void this.audio?.resume().catch(() => { /* Embedded browser may deny audio; DOS can still run silently. */ });
        } catch { this.audio = null; }
    }
    setActive(active) {
        this.active = active;
        this.syncPause();
    }
    setState(state, enable) {
        super.setState(state, enable);
        if ((state & sfDragging) !== 0 && this.view?.ci) { this.syncPause(); }
        return this;
    }
    syncPause() {
        if (!this.view.ci) { return; }
        const dragging = this.getState?.(sfDragging);
        if (this.starting && !dragging) { this.view.ci.resume(); return; }
        if (!this.active || this.paused || document.hidden || this.busy || this.snapshotting || dragging) {
            this.view.releaseInput(); this.view.ci.pause();
            for (const source of this.soundSources) { try { source.stop(); } catch { /* ended */ } }
            this.soundSources.clear();
            this.soundTime = 0;
        } else { this.view.ci.resume(); }
    }
    notice(text, temporary = false) {
        clearTimeout(this.noticeTimer);
        this.status.setText(text); this.status.setState(sfVisible, true);
        if (temporary) { this.noticeTimer = setTimeout(() => this.status.setState(sfVisible, false), 2500); }
    }
    async boot() {
        if (this.closing || !this.root?.isConnected) { return; }
        this.disposed = false;
        this.busy = true;
        let initializingDialog = null;
        try {
            this.resumeSound();
            this.onChange?.();
            this.notice("Checking DOS C drive...");
            let deadline = Date.now() + 180000, lastProgress = "";
            while (!this.disposed) {
                if (initializingDialog?.cancelled) { throw new DOMException("Initialization wait cancelled", "AbortError"); }
                const status = await (await dosRequest("/api/dos/status")).json();
                if (status.state === "ready") { break; }
                if (status.state === "error" || Date.now() > deadline) { throw new Error(status.error || "DOS preparation timed out"); }
                const progress = JSON.stringify([status.current, status.phase, status.processed, status.received, status.percent]);
                if (progress !== lastProgress) { deadline = Date.now() + 180000; lastProgress = progress; }
                if ((status.initializing || status.configuring || status.total) && TV.TVLoadingDialog && this.owner) {
                    if (!initializingDialog) {
                        initializingDialog = new TV.TVLoadingDialog(status.initializing || status.rebuilding
                            ? "Initializing DOS C" : "Updating DOS C");
                        this.owner.insert(initializingDialog);
                        initializingDialog.show("Preparing software...");
                    }
                    if (initializingDialog.cancelled) { throw new DOMException("Initialization wait cancelled", "AbortError"); }
                    initializingDialog.filenameView.setText(`${status.phase || "Preparing"}: ${status.current || "C drive"}`.slice(0, 38));
                    initializingDialog.update(status.percent || 0, 100);
                }
                this.notice(`Preparing shared C drive: ${status.current || "starting"}`);
                await new Promise((resolve) => setTimeout(resolve, 500));
            }
            if (this.disposed) { return; }
            initializingDialog?.destroy(true); initializingDialog = null;
            this.notice("Loading DOS C drive...");
            let local = null;
            if (this.localDrive) {
                this.notice("Opening local folder...");
                local = await this.localDrive.prepare();
                if (this.disposed) { return; }
            }
            const params = new URLSearchParams();
            if (this.media) { params.set("media", this.media); }
            const query = params.size ? "?" + params : "";
            this.session = await (await dosRequest("/api/dos/session" + query)).json();
            const response = await dosRequest("/api/dos/bundle" + query);
            // A second window may have saved between the metadata and ZIP requests.
            if (String(this.session.revision) !== response.headers.get("X-DOS-Revision")
                || this.session.base_id !== response.headers.get("X-DOS-Base")) { throw new Error("C drive changed while loading; please restart"); }
            const init = [new Uint8Array(await response.arrayBuffer())];
            if (this.session.media) {
                const media = await dosRequest("/api/dos/media/" + encodeURIComponent(this.session.media));
                init.push({ path: "media/" + this.session.media, contents: new Uint8Array(await media.arrayBuffer()) });
            }
            this.notice("Loading DOSBox runtime...");
            const runtime = await loadRuntime();
            // Keep the official WASM/module loader; only the worker entry adds
            // our file provider after the original filesystem is initialised.
            await runtime.wasmModules?.();
            let ci;
            const backends = this.session.allow_full_disk_fallback && !this.localDrive ? ["dosboxWorker", "dosboxDirect"] : ["dosboxWorker"];
            for (const backend of backends) {
                if (this.disposed) { return; }
                if (backend === "dosboxWorker") { this.notice("Starting DOSBox worker..."); }
                let expired = false, timer;
                // The worker may transfer buffers before failing; keep the originals
                // intact for the official direct backend used by restricted webviews.
                const files = backend === "dosboxWorker" ? init.map((entry) => entry instanceof Uint8Array
                    ? entry.slice() : { path: entry.path, contents: entry.contents.slice() }) : init;
                const workerScript = runtime.wdosboxJs;
                const prefix = runtime.pathPrefix;
                try {
                    if (backend === "dosboxWorker") {
                        const url = new URL("../tv-dos-worker.js?v=20261017m", PREFIX).href;
                        if (window.isSecureContext && TV.DosLocalConnection && typeof BroadcastChannel === "function") {
                            this.localConnection = new TV.DosLocalConnection(local);
                            runtime.wdosboxJs = this.localConnection.workerScript(url);
                            runtime.pathPrefix = "";
                        } else { runtime.wdosboxJs = "../tv-dos-worker.js?v=20261017m"; }
                    }
                    if (backend === "dosboxDirect") {
                        this.notice("Worker unavailable: loading full disk fallback...");
                        const full = await dosRequest("/api/dos/bundle" + query + (query ? "&" : "?") + "full=true");
                        if (full.headers.get("X-DOS-Base") !== this.session.base_id
                            || full.headers.get("X-DOS-Revision") !== String(this.session.revision)) { throw new Error("DOS C changed while loading fallback"); }
                        init[0] = new Uint8Array(await full.arrayBuffer());
                        this.notice("Starting DOSBox without worker...");
                    }
                    const startup = runtime[backend](files).then(async (instance) => {
                        if (expired || this.disposed) { await instance.exit(); }
                        return instance;
                    });
                    ci = await Promise.race([startup, new Promise((_, reject) => {
                        timer = setTimeout(() => { expired = true; reject(new Error(`DOSBox ${backend} startup timed out in this browser`)); }, 30000);
                    })]);
                    this.lazyDisk = backend === "dosboxWorker";
                    break;
                } catch (error) {
                    this.localConnection?.release(); this.localConnection = null;
                    if (backend === backends[backends.length - 1]) {
                        if (backend === "dosboxWorker" && (error.name === "SecurityError" || typeof window.Worker !== "function")) {
                            throw new Error("DOS file-on-demand requires Web Workers; this browser does not allow them.");
                        }
                        throw error;
                    }
                } finally {
                    clearTimeout(timer); runtime.wdosboxJs = workerScript; runtime.pathPrefix = prefix;
                    this.localConnection?.releaseScript();
                }
            }
            if (this.disposed) { await ci.exit(); return; }
            this.view.ci = ci;
            this.starting = true;
            this.notice("Starting DOS command shell...");
            ci.events().onFrame((rgb, rgba) => this.view.renderFrame(rgb, rgba));
            ci.events().onSoundPush((samples) => this.playSound(samples));
            ci.events().onExit(() => {
                if (this.view.ci === ci) {
                    this.view.ci = null;
                    clearInterval(this.saveTimer);
                    clearInterval(this.localSaveTimer);
                    this.localConnection?.release(); this.localConnection = null;
                    if (document.fullscreenElement === this.view.canvas) {
                        void document.exitFullscreen().catch((error) => this.onError?.(error));
                    }
                    this.notice("DOS stopped. Choose Restart from DOS Prompt."); this.onChange?.();
                }
            });
            // CI readiness precedes AUTOEXEC; do not accept input before the
            // managed virtual drives and user startup files have been mounted.
            await new Promise((resolve, reject) => {
                const timer = setTimeout(() => reject(new Error("DOS startup timed out")), 15000);
                this.cancelStartup = () => { clearTimeout(timer); resolve(); };
                ci.events().onStdout((text) => {
                    if (text.includes("Drive C does not exist") || text.includes("doesn't exist.")) {
                        clearTimeout(timer); reject(new Error("DOS drive mount failed"));
                    } else if (text.includes("THelpViewer DOS Prompt - use")) {
                        clearTimeout(timer); resolve();
                    } else if (text.includes("THelpViewer DOS session ended.")) {
                        // EXIT returns from the interactive COMMAND.COM to trusted
                        // AUTOEXEC, while the backend filesystem is still available.
                        void this.finishSession(ci);
                    }
                });
                // Keep emulation running for trusted AUTOEXEC even when the window
                // has become inactive during asynchronous preparation.
                ci.resume();
            });
            this.cancelStartup = null;
            if (this.disposed) { return; }
            this.status.setState(sfVisible, false);
            this.view.canvas.focus();
            this.visibility = () => { this.syncPause(); void this.autoSaveLocal(); };
            document.addEventListener("visibilitychange", this.visibility);
            this.saveTimer = setInterval(() => {
                if (this.active && !document.hidden && !this.busy && !this.closing && this.session.account) {
                    void this.save().catch((error) => this.notice(error.message));
                }
            }, 60000);
            this.localSaveTimer = setInterval(() => { void this.autoSaveLocal(); }, 2000);
        } catch (error) {
            if (this.disposed) { return; }
            const ci = this.view.ci; this.view.ci = null;
            if (ci) { await ci.exit(); }
            this.notice(error.name === "AbortError" ? "Initialization continues on the server. Choose Restart to reconnect." : error.message);
            if (error.name !== "AbortError") { this.onError?.(error); }
        } finally {
            if (!this.view.ci) { this.localConnection?.release(); this.localConnection = null; }
            initializingDialog?.destroy(true);
            this.cancelStartup = null; this.starting = false; this.busy = false; this.syncPause(); this.onChange?.();
        }
    }
    playSound(samples) {
        if (this.disposed || !this.view.ci || !this.audio || this.audio.state !== "running" || !this.active || this.paused || this.busy || this.snapshotting || this.getState?.(sfDragging)) { return; }
        const rate = this.view.ci.soundFrequency();
        if (!rate || !samples.length || this.soundTime > this.audio.currentTime + 0.3) { return; }
        const buffer = this.audio.createBuffer(1, samples.length, rate);
        buffer.copyToChannel(samples, 0);
        const source = this.audio.createBufferSource();
        source.buffer = buffer; source.connect(this.audio.destination);
        this.soundTime = Math.max(this.soundTime || 0, this.audio.currentTime + 0.02);
        source.start(this.soundTime); this.soundTime += buffer.duration;
        this.soundSources.add(source); source.onended = () => this.soundSources.delete(source);
    }
    async autoSaveLocal() {
        const ci = this.view.ci;
        if (!ci || !this.localDrive?.writable || this.localSaveFailed || this.checkingLocal
            || this.busy || this.saving || this.disposed) { return; }
        this.checkingLocal = true;
        try {
            // Inspect only the small revision record. Pause/traverse/read file
            // contents only after a mutation, never on every timer tick.
            if (await this.localDrive.hasChanges(ci) && this.view.ci === ci && !this.disposed) { await this.save(true); }
        } catch (error) {
            if (this.view.ci !== ci || this.disposed) { return; }
            this.localSaveFailed = true; this.paused = true; this.syncPause(); this.onChange?.();
            this.onError?.(new Error("Local D could not be saved: " + error.message
                + "\nChanges remain in this DOS window. Resolve the problem, then choose DOS Prompt → Retry local save."));
        } finally { this.checkingLocal = false; }
    }
    async save(localOnly = false) {
        if (!this.view.ci || (!this.session?.account && !this.localDrive?.writable)) { return; }
        // Close/cloud Save must not mistake a concurrent local-only flush for
        // a completed C upload. Serialize, then perform the requested save.
        while (this.saving) { await this.saving; }
        if (!this.view.ci) { return; }
        this.saving = this.saveSnapshot(localOnly).finally(() => { this.saving = null; });
        return this.saving;
    }
    async saveSnapshot(localOnly = false) {
        const ci = this.view.ci;
        const session = this.session;
        this.snapshotting = true;
        this.syncPause();
        try {
            if (this.localDrive) {
                await this.localDrive.save(ci);
                if (this.localSaveFailed) { this.localSaveFailed = false; this.onChange?.(); }
            }
            if (localOnly || !session.account) { return; }
            const files = {}, existing = new Set(), directories = new Set(), unchanged = {};
            let total = 0, overlayBytes = 0, remote = new Set(), dirty = new Set();
            if (this.lazyDisk) {
                const state = JSON.parse(new TextDecoder().decode(await ci.fsReadFile(".jsdos/file-state.json")));
                remote = new Set(state.remote); dirty = new Set(state.dirty);
            }
            const privateFiles = new Set(session.overlay_files || []);
            async function walk(node, prefix = "") {
                const path = [prefix, node.name === "." ? "" : node.name].filter(Boolean).join("/").replace(/^\/+/, "");
                if (node.nodes) {
                    if (path.toLowerCase().startsWith("drive_c/")) { directories.add(path.slice(8).toUpperCase()); }
                    for (const child of node.nodes) { await walk(child, path); }
                }
                else if (path.toLowerCase().startsWith("drive_c/")) {
                    const name = path.slice(8).toUpperCase(); existing.add(name);
                    if (remote.has(name) && !dirty.has(name)) {
                        if (privateFiles.has(name)) { unchanged[name] = session.remote_files[name].sha256; }
                        return;
                    }
                    const bytes = await ci.fsReadFile(path);
                    total += bytes.length;
                    if (total > session.max_c_bytes) { throw new Error("C drive exceeds its configured quota"); }
                    const hash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), (v) => v.toString(16).padStart(2, "0")).join("");
                    if (hash !== session.files[name]) {
                        overlayBytes += bytes.length;
                        if (overlayBytes > session.max_overlay_bytes) { throw new Error("Private C overlay exceeds its configured quota"); }
                        let binary = "";
                        for (let offset = 0; offset < bytes.length; offset += 32768) { binary += String.fromCharCode(...bytes.subarray(offset, offset + 32768)); }
                        files[name] = btoa(binary);
                    }
                }
            }
            await walk(await ci.fsTree());
            const deleted = Object.keys(this.session.files).filter((name) => !existing.has(name));
            const payload = { base_id: this.session.base_id, revision: this.session.revision,
                account: this.session.account, files, unchanged, deleted, directories: [...directories] };
            let result;
            try {
                result = await (await dosRequest("/api/dos/overlay", {
                    method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
                })).json();
            } catch (error) { error.dosCloudSave = true; throw error; }
            this.session.revision = result.revision;
        } finally { this.snapshotting = false; this.syncPause(); }
    }
    async restart(media = this.media, localDrive = this.localDrive) {
        if (this.busy || this.closing || this.disposed) { return; }
        this.busy = true; this.onChange?.();
        try {
            await this.save();
            if (this.closing || this.disposed) { return; }
            await this.stop(false, true);
            if (this.closing || !this.root?.isConnected) { return; }
            this.media = media; this.localDrive = localDrive; await this.boot();
        } finally { this.busy = false; this.syncPause(); this.onChange?.(); }
    }
    async finishSession(ci) {
        if (this.busy || this.disposed || this.view.ci !== ci) { return; }
        this.busy = true; this.onChange?.();
        try {
            if (document.fullscreenElement === this.view.canvas) { await document.exitFullscreen(); }
            await this.save();
            this.view.releaseInput(); await ci.exit();
        } catch (error) {
            this.paused = true; this.onError?.(error);
        } finally { this.busy = false; this.syncPause(); this.onChange?.(); }
    }
    async stop(save = true, keepFullscreen = false) {
        if (this.localChange) { await this.localChange; }
        if (save) {
            try { await this.save(); }
            catch (error) {
                if (!error.dosCloudSave || keepFullscreen) { throw error; }
                if (!await this.confirmCloseWithoutSave(error)) { return false; }
            }
        }
        else if (this.localDrive && this.view.ci) { await this.save(true); }
        this.disposed = true;
        this.cancelStartup?.(); this.cancelStartup = null;
        this.confirmation?.closeAction();
        if (this.fullscreenChanged && !keepFullscreen) {
            document.removeEventListener("fullscreenchange", this.fullscreenChanged);
            this.fullscreenChanged = null;
            if (document.fullscreenElement === this.view.canvas) { await document.exitFullscreen(); }
        }
        clearInterval(this.saveTimer); clearInterval(this.localSaveTimer); clearTimeout(this.noticeTimer);
        this.localConnection?.release(); this.localConnection = null;
        document.removeEventListener("visibilitychange", this.visibility);
        this.view.releaseInput();
        const ci = this.view.ci; this.view.ci = null;
        if (ci) { await ci.exit(); }
        if (this.audio) { await this.audio.close(); this.audio = null; }
    }
    async confirmCloseWithoutSave(error) {
        if (document.fullscreenElement === this.view.canvas) { await document.exitFullscreen(); }
        const box = new TVMessageBox(), owner = this.owner;
        this.confirmation = box; owner?.insert(box);
        const wasPaused = this.paused;
        this.paused = true; this.syncPause();
        try {
            return await box.show({ type: TVMessageBox.MF_WARNING, title: "Close without saving C?",
                lines: [error.message, "", "Close and discard this window's unsaved C changes?",
                    "The saved cloud disk will not be overwritten.",
                    ...(this.localDrive ? ["Local D changes have already been saved."] : []),
                    "Cancel keeps this DOS window and its changes open."],
                buttons: TVMessageBox.MF_OK_CANCEL }) === "ok";
        } finally {
            this.confirmation = null; box.destroy(); owner?.remove(box);
            this.paused = wasPaused; this.syncPause();
        }
    }
    fullScreen() {
        const canvas = this.view.canvas;
        if (document.fullscreenElement === canvas) {
            void document.exitFullscreen().catch((error) => this.onError?.(error)); return;
        }
        if (!canvas?.requestFullscreen) { this.onError?.(new Error("Fullscreen is unavailable in this browser")); return; }
        if (this.fullscreenRequest) { return; }
        if (this.fullscreenChanged) {
            document.removeEventListener("fullscreenchange", this.fullscreenChanged);
        }
        this.fullscreenChanged = () => {
            this.view.releaseInput(); canvas.focus();
            if (document.fullscreenElement === canvas) { return; }
            if (this.pendingScreenResize) { this.fitScreen(); }
            document.removeEventListener("fullscreenchange", this.fullscreenChanged);
            this.fullscreenChanged = null;
        };
        document.addEventListener("fullscreenchange", this.fullscreenChanged);
        this.fullscreenRequest = canvas.requestFullscreen().catch((error) => {
            document.removeEventListener("fullscreenchange", this.fullscreenChanged);
            this.fullscreenChanged = null; this.onError?.(error);
        }).finally(() => { this.fullscreenRequest = null; });
    }
    async confirmRestart() {
        if (this.confirmation || this.closing || this.disposed) { return false; }
        if (document.fullscreenElement === this.view.canvas) { await document.exitFullscreen(); }
        const box = new TVMessageBox();
        const owner = this.owner;
        this.confirmation = box; owner?.insert(box);
        try {
            return await box.show({ type: TVMessageBox.MF_CONFIRMATION, title: "Restart DOS",
                lines: [this.session?.account
                    ? "C drive changes will be saved. The running program stops."
                    : "Temporary C drive changes will be lost. DOS will restart.",
                    "Changes on floppy images are temporary and not saved.",
                    ...(this.localDrive ? ["Local D changes will be saved to the selected folder."] : []),
                    "Continue?"],
                buttons: TVMessageBox.MF_OK_CANCEL }) === "ok";
        } finally { this.confirmation = null; box.destroy(); owner?.remove(box); }
    }
    async chooseLocalFolder() {
        if (!TV.DosLocalDrive?.supported()) {
            throw new Error("Local folders require a browser with File System Access (for example Chrome or Edge), on HTTPS or localhost");
        }
        const handle = await window.showDirectoryPicker({ id: "thelp-dos-local", mode: "readwrite" });
        if (this.disposed || this.closing) { return; }
        if (document.fullscreenElement === this.view.canvas) { await document.exitFullscreen(); }
        const box = new TVMessageBox(); this.owner?.insert(box);
        this.confirmation = box;
        try {
            const result = await box.show({ type: TVMessageBox.MF_CONFIRMATION, title: "Connect local D",
                lines: ["DOS programs can change/delete files in the selected folder.",
                    "The running DOS session will not restart. Continue?"], buttons: TVMessageBox.MF_OK_CANCEL });
            if (result !== "ok" || this.disposed || this.closing) { return; }
        } finally { this.confirmation = null; box.destroy(); this.owner?.remove(box); }
        await this.changeLocalFolder(new TV.DosLocalDrive(handle));
    }
    changeLocalFolder(drive) {
        if (this.localChange) { return this.localChange; }
        const change = async () => {
            const ci = this.view.ci;
            if (!ci || !this.lazyDisk || !this.localConnection?.channel) {
                throw new Error("Changing local folders requires the Worker backend; restart DOS if its connection was lost");
            }
            this.busy = true; this.syncPause(); this.onChange?.();
            try {
                await this.save(true);
                // Refresh snapshots after flushing, especially when the user
                // reselects the same host folder with pending DOS writes.
                const local = drive ? await drive.prepare() : null;
                if (this.disposed || this.closing || this.view.ci !== ci) { return; }
                try { await this.localConnection.replace(local); }
                catch (error) {
                    // A lost reply is not proof of rollback. Bind the correct
                    // host capability before permitting any subsequent save.
                    const state = JSON.parse(new TextDecoder().decode(await ci.fsReadFile(".jsdos/local-state.json")));
                    if (state.mount === (drive?.id || null)) { this.localDrive = drive; }
                    throw error;
                }
                this.localDrive = drive; this.localSaveFailed = false;
            } finally { this.busy = false; this.syncPause(); this.onChange?.(); }
        };
        this.localChange = change().finally(() => { this.localChange = null; });
        return this.localChange;
    }
    handleEvent(event) {
        if (event.what === evCommand && event.command === TV.TV_COMMANDS?.RESIZE && event.infoPtr instanceof TVRect) {
            const drag = this.root?._tvResizer?.dragState, bounds = event.infoPtr;
            if (drag && this.view.canvas?.width && this.view.canvas.height) {
                const dx = Math.abs((event.nativeEvent.clientX - drag.startX) / drag.cellWidth / (drag.startCols - 2));
                const dy = Math.abs((event.nativeEvent.clientY - drag.startY) / drag.cellHeight / (drag.startRows - 2));
                const size = this._screenGeometry({ cols: bounds.width, rows: bounds.height },
                    drag.maxCols, drag.maxRows, dy > dx);
                bounds.x2 = bounds.x1 + size.cols;
                bounds.y2 = bounds.y1 + size.rows;
            }
            this.clearEvent(event);
            return;
        }
        if (event.what === evCommand && String(event.command).startsWith("dos-")) {
            const command = event.command, data = event.infoPtr;
            this.clearEvent(event);
            if (command === "dos-menu") {
                void (async () => {
                    if (document.fullscreenElement === this.view.canvas) { await document.exitFullscreen(); }
                    if (!this.disposed) { this.onMenu?.(); }
                })().catch((error) => this.onError?.(error));
            }
            else if (command === "dos-pause" && this.view.ci && !this.busy) { this.paused = !this.paused; this.syncPause(); this.onChange?.(); }
            else if (command === "dos-save") { void this.save().catch((error) => this.onError?.(error)); }
            else if (command === "dos-save-local") { void this.save(true).catch((error) => this.onError?.(error)); }
            else if (command === "dos-mount-local" || command === "dos-unmount-local") {
                if (this.busy || this.selectingLocal) { return; }
                this.selectingLocal = true; this.onChange?.();
                const task = command === "dos-mount-local" ? this.chooseLocalFolder()
                    : this.changeLocalFolder(null);
                void task.catch((error) => { if (error.name !== "AbortError") { this.onError?.(error); } })
                    .finally(() => { this.selectingLocal = false; this.onChange?.(); });
            }
            else if (command === "dos-restart" || command === "dos-eject") {
                if (this.busy) { return; }
                void (async () => { if (await this.confirmRestart()) { await this.restart(command === "dos-eject" ? "" : this.media); } })().catch((error) => this.onError?.(error));
            }
            else if (command === "dos-fullscreen") { this.fullScreen(); }
            else if (command === "dos-zoom") { this.zoom(); }
            else if (command === "dos-close") { this.onClose?.(); }
            else if (command === "dos-mount-cd" || command === "dos-mount-floppy") { this.view.chooseMedia(command === "dos-mount-cd" ? "cd" : "floppy"); }
            else if (command === "dos-media-selected") {
                void (async () => {
                    if (data.file.size > this.session.max_media_bytes) { throw new Error("Media exceeds the configured size limit"); }
                    if (!await this.confirmRestart()) { return; }
                    if (this.disposed || this.closing) { return; }
                    const result = await (await dosRequest("/api/dos/media?kind=" + data.kind, { method: "POST",
                        headers: { "X-DOS-Account": this.session.account }, body: data.file })).json();
                    await this.restart(result.id);
                })().catch((error) => this.onError?.(error));
            }
            return;
        }
        super.handleEvent(event);
    }
}
Object.assign(TV, { TVDosView, TVDosWindow });
})();
