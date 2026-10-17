// Browser-owned directory capability. Local D never goes through the server API.
(function () {
"use strict";
const MAX_ENTRIES = 4096, MAX_FILE_BYTES = 64 * 1024 * 1024;
const PART = /^[A-Z0-9!#$%&'()@^_{}~`-]{1,8}(?:\.[A-Z0-9!#$%&'()@^_{}~`-]{1,3})?$/;
const DEVICE = /^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)/;

function localPath(path) {
    if (typeof path !== "string" || path.length > 240 || !path.split("/").every((part) => PART.test(part) && !DEVICE.test(part))) {
        throw new Error("Invalid local DOS path");
    }
    return path;
}

function dosNames(entries) {
    const used = new Set(entries.map((entry) => entry.name.toUpperCase()).filter((name) => PART.test(name) && !DEVICE.test(name)));
    const assigned = new Set();
    return entries.map((entry) => {
        let name = entry.name.toUpperCase();
        if (!PART.test(name) || DEVICE.test(name) || assigned.has(name)) {
            const clean = entry.name.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toUpperCase().replace(/[^A-Z0-9._-]/g, "_");
            const dot = clean.lastIndexOf("."), stem = (dot > 0 ? clean.slice(0, dot) : clean).replace(/\./g, "_") || "FILE";
            const ext = dot > 0 ? clean.slice(dot + 1).slice(0, 3) : "";
            let number = 1;
            do {
                const suffix = "~" + number++;
                name = stem.slice(0, 8 - suffix.length) + suffix + (ext ? "." + ext : "");
            } while (used.has(name) || assigned.has(name));
        }
        assigned.add(name);
        return { entry, name };
    });
}

// This channel belongs to one emulator, not one selected folder. It carries
// immutable File snapshots, never the directory capability or a host path.
class DosLocalConnection {
    constructor(local = null) {
        this.pending = new Map();
        this.channelName = "thelp-dos-local-" + crypto.randomUUID();
        this.channel = new BroadcastChannel(this.channelName);
        this.channel.onmessage = ({ data }) => {
            if (data === "ready") { this.channel?.postMessage({ type: "init", local }); local = null; return; }
            const pending = this.pending.get(data?.id);
            if (!pending) { return; }
            clearTimeout(pending.timer); this.pending.delete(data.id);
            if (data.error) { pending.reject(new Error(data.error)); }
            else { pending.resolve(); }
        };
    }
    workerScript(workerUrl) {
        const source = `self.thelpLocalChannel=${JSON.stringify(this.channelName)};importScripts(${JSON.stringify(workerUrl)});`;
        this.workerUrl = URL.createObjectURL(new Blob([source], { type: "text/javascript" }));
        return this.workerUrl;
    }
    replace(local) {
        if (!this.channel) { return Promise.reject(new Error("Local folder connection is closed")); }
        const id = crypto.randomUUID();
        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                // Outcome is unknown: do not claim the old folder still owns
                // the disk or allow its next autosave to delete host files.
                this.release(); reject(new Error("Local folder change timed out; restart DOS before saving D"));
            }, 10000);
            this.pending.set(id, { resolve, reject, timer });
            try { this.channel.postMessage({ type: "replace", id, local }); }
            catch (error) { clearTimeout(timer); this.pending.delete(id); reject(error); }
        });
    }
    releaseScript() {
        if (this.workerUrl) { URL.revokeObjectURL(this.workerUrl); this.workerUrl = ""; }
    }
    release() {
        this.channel?.close(); this.channel = null;
        this.releaseScript();
        for (const pending of this.pending.values()) {
            clearTimeout(pending.timer); pending.reject(new Error("Local folder connection is closed; restart DOS"));
        }
        this.pending.clear();
    }
}

class DosLocalDrive {
    constructor(handle) {
        this.handle = handle;
        this.id = crypto.randomUUID();
        this.writable = true;
        this.records = new Map();
        this.savedRevision = 0;
    }
    static supported() {
        return window.isSecureContext && typeof window.showDirectoryPicker === "function" && typeof BroadcastChannel === "function";
    }
    async prepare() {
        const records = new Map(), entries = [];
        const visit = async (directory, prefix = "") => {
            const children = [];
            for await (const handle of directory.values()) {
                children.push(handle);
                if (records.size + children.length > MAX_ENTRIES) { throw new Error("Local folder exceeds 4096 DOS entries; choose a smaller folder"); }
            }
            children.sort((a, b) => a.name < b.name ? -1 : a.name > b.name ? 1 : 0);
            for (const { entry: handle, name } of dosNames(children)) {
                const path = localPath(prefix + name);
                if (records.size >= MAX_ENTRIES) { throw new Error("Local folder exceeds 4096 DOS entries"); }
                const record = { handle, name: handle.name, kind: handle.kind };
                records.set(path, record);
                if (handle.kind === "directory") {
                    entries.push({ path, directory: true });
                    await visit(handle, path + "/");
                } else {
                    const file = await handle.getFile();
                    if (file.size > MAX_FILE_BYTES) { throw new Error("A local file exceeds the 64 MiB DOS file limit: " + path); }
                    record.file = file;
                    entries.push({ path, file });
                }
            }
        };
        await visit(this.handle);
        this.records = records;
        this.savedRevision = 0;
        return { mount: this.id, entries, writable: this.writable, maxFileBytes: MAX_FILE_BYTES };
    }
    async node(path, kind, create = false) {
        const parts = localPath(path).split("/");
        let directory = this.handle, prefix = "";
        for (let index = 0; index < parts.length; index++) {
            prefix += (prefix ? "/" : "") + parts[index];
            const name = this.records.get(prefix)?.name || parts[index];
            if (index === parts.length - 1 && kind === "file") { return directory.getFileHandle(name, { create }); }
            directory = await directory.getDirectoryHandle(name, { create });
        }
        return directory;
    }
    async verify(path, record) {
        const handle = await this.node(path, record.kind);
        if (!await handle.isSameEntry(record.handle)) { throw new Error("Local folder changed outside DOS: " + path); }
        if (record.kind === "file") {
            const current = await handle.getFile();
            if (current.size !== record.file.size || current.lastModified !== record.file.lastModified) {
                throw new Error("Local file changed outside DOS: " + path);
            }
            // Metadata alone is not sufficient for an overwrite. A stale File
            // snapshot can also throw NotReadableError here; do not overwrite it.
            const before = new Uint8Array(await record.file.arrayBuffer()), now = new Uint8Array(await current.arrayBuffer());
            if (before.length !== now.length || before.some((byte, index) => byte !== now[index])) {
                throw new Error("Local file changed outside DOS: " + path);
            }
        }
        return handle;
    }
    async readState(ci) {
        const state = JSON.parse(new TextDecoder().decode(await ci.fsReadFile(".jsdos/local-state.json")));
        if (state.mount !== this.id || !Number.isSafeInteger(state.revision)
            || state.revision < this.savedRevision || !Array.isArray(state.dirty)) {
            throw new Error("Invalid local DOS disk state");
        }
        return state;
    }
    async hasChanges(ci) {
        return this.writable && (await this.readState(ci)).revision !== this.savedRevision;
    }
    async save(ci) {
        if (!this.writable) { return; }
        const state = await this.readState(ci);
        if (state.revision === this.savedRevision) { return; }
        const dirty = new Set(state.dirty.map(localPath)), desired = new Map();
        const walk = (node, prefix = "") => {
            const path = prefix ? prefix + "/" + node.name : node.name;
            localPath(path);
            if (desired.has(path) || desired.size >= MAX_ENTRIES) { throw new Error("Invalid local DOS directory tree"); }
            desired.set(path, node.nodes ? "directory" : "file");
            for (const child of node.nodes || []) { walk(child, path); }
        };
        const find = (node) => node.name === "drive_d" ? node : (node.nodes || []).map(find).find(Boolean);
        const root = find(await ci.fsTree());
        if (!root?.nodes) { throw new Error("Local D drive is unavailable; no local files were removed"); }
        root.nodes.forEach((node) => walk(node));
        if (desired.size !== state.entries) { throw new Error("Incomplete local DOS directory tree; no local files were removed"); }
        const changes = new Map(), deleted = [];
        let total = 0;
        // Preflight every affected entry before writing anything. Resolve every
        // operation from the selected root, never from a DOS-supplied host path.
        for (const [path, kind] of desired) {
            const old = this.records.get(path);
            if (old && old.kind !== kind) { throw new Error("Local file/directory type changed; reconnect the folder: " + path); }
            if (!old || dirty.has(path)) {
                if (old) { await this.verify(path, old); }
                else {
                    try { await this.node(path, kind); throw new Error("A local entry already exists outside DOS: " + path); }
                    catch (error) { if (error.name !== "NotFoundError") { throw error; } }
                }
                const data = kind === "file" ? await ci.fsReadFile("drive_d/" + path) : null;
                total += data?.length || 0;
                if (data?.length > MAX_FILE_BYTES || total > MAX_FILE_BYTES) { throw new Error("Local DOS changes exceed the 64 MiB save limit"); }
                changes.set(path, { kind, data });
            }
        }
        for (const [path, record] of this.records) {
            if (!desired.has(path)) { await this.verify(path, record); deleted.push(path); }
        }
        for (const [path, { kind, data }] of changes) {
            const handle = await this.node(path, kind, true);
            if (!this.records.has(path)) {
                // A newly created empty entry is ours even if the following
                // write fails. Keep its baseline so Retry is not a false conflict.
                this.records.set(path, { handle, name: handle.name, kind, file: kind === "file" ? await handle.getFile() : null });
            }
            if (kind === "file") {
                const stream = await handle.createWritable();
                try { await stream.write(data); await stream.close(); }
                catch (error) { await stream.abort().catch(() => {}); throw error; }
            }
            this.records.set(path, { handle, name: handle.name, kind, file: kind === "file" ? await handle.getFile() : null });
        }
        // Never recursively remove a host directory: externally added files
        // must survive, even if DOS removed its old directory snapshot.
        deleted.sort((a, b) => b.split("/").length - a.split("/").length);
        for (const path of deleted) {
            const record = this.records.get(path), slash = path.lastIndexOf("/");
            const parent = slash < 0 ? this.handle : await this.node(path.slice(0, slash), "directory");
            await parent.removeEntry(record.name);
            this.records.delete(path);
        }
        this.savedRevision = state.revision;
    }
}
window.THelpViewerTV.DosLocalDrive = DosLocalDrive;
window.THelpViewerTV.DosLocalConnection = DosLocalConnection;
})();
