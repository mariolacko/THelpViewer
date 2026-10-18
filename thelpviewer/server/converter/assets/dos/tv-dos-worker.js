// File-on-demand adapter for the pinned DOSBox runtime with native text cells.
importScripts(self.location.origin + "/assets/dos/emulators/wdosbox.js?v=20261018a");

const createDosbox = WDOSBOX;
WDOSBOX = async function (options) {
    let local, channel, fs, disk;
    if (self.thelpLocalChannel) {
        channel = new BroadcastChannel(self.thelpLocalChannel);
        local = await new Promise((resolve, reject) => {
            const timer = setTimeout(() => { channel.close(); reject(new Error("Local folder connection timed out")); }, 10000);
            channel.onmessage = ({ data }) => {
                if (data?.type !== "init") { return; }
                clearTimeout(timer); resolve(data.local);
            };
            channel.postMessage("ready");
        });
        channel.onmessage = ({ data }) => {
            if (data?.type !== "replace") { return; }
            try {
                if (!fs) { throw new Error("DOS filesystem is not ready"); }
                if (typeof options._rescanFilesystem !== "function") { throw new Error("DOSBox does not support refreshing mounted folders"); }
                disk = replaceLocalDisk(fs, data.local, disk);
                // The pinned classic backend exports RESCAN directly; its
                // mapper is intentionally a no-op, so do not inject Ctrl-F4.
                options._rescanFilesystem();
                channel.postMessage({ id: data.id });
            } catch (error) { channel.postMessage({ id: data.id, error: error.message || "Cannot change the local DOS folder" }); }
        };
    }
    const initialized = options.onRuntimeInitialized;
    options.onRuntimeInitialized = () => {
        const extract = options._extractBundleToFs;
        options._extractBundleToFs = (...args) => {
            const result = extract(...args);
            installRemoteDisk(options.FS);
            if (channel) { disk = replaceLocalDisk(options.FS, local, null); fs = options.FS; local = null; }
            return result;
        };
        initialized?.();
    };
    return createDosbox(options);
};

function replaceLocalDisk(fs, local, previous) {
    const root = "/home/web_user/drive_d";
    for (const stream of fs.streams) {
        if (!stream?.node) { continue; }
        const path = fs.getPath(stream.node);
        if (path === root || path.startsWith(root + "/")) {
            throw new Error("Close files/programs using local D before changing the folder");
        }
    }
    const incoming = "/home/web_user/.jsdos/local-incoming", retired = "/home/web_user/.jsdos/local-previous";
    const remove = (path) => {
        const node = fs.lookupPath(path).node;
        if (fs.isDir(node.mode)) {
            for (const name of fs.readdir(path).filter((name) => name !== "." && name !== "..")) { remove(path + "/" + name); }
            fs.rmdir(path);
        } else { fs.unlink(path); }
    };
    let next;
    try { next = installLocalDisk(fs, local || { entries: [], writable: false, mount: null }, incoming); }
    catch (error) {
        if (fs.analyzePath(incoming).exists) { remove(incoming); }
        throw error;
    }
    const stateFile = "/home/web_user/.jsdos/local-state.json";
    const oldState = fs.analyzePath(stateFile).exists ? fs.readFile(stateFile).slice() : null;
    fs.rename(root, retired);
    try {
        fs.rename(incoming, root);
        fs.writeFile(stateFile, JSON.stringify(next.state));
    } catch (error) {
        if (fs.analyzePath(root).exists) { fs.rename(root, incoming); }
        fs.rename(retired, root);
        if (oldState) { fs.writeFile(stateFile, oldState); }
        if (fs.analyzePath(incoming).exists) { remove(incoming); }
        throw error;
    }
    previous?.retire(); next.activate(); remove(retired);
    return next;
}

function installLocalDisk(fs, local, target) {
    if (local.writable && typeof FileReaderSync !== "function") { throw new Error("Local DOS folders require FileReaderSync in a Worker"); }
    if (!Array.isArray(local.entries) || local.entries.length > 4096) { throw new Error("Invalid local DOS folder"); }
    const reader = typeof FileReaderSync === "function" ? new FileReaderSync() : null;
    const root = "/home/web_user/drive_d", loaders = new WeakMap();
    const state = { mount: local.mount, revision: 0, dirty: [], entries: local.entries.length }, dirty = new Set();
    let active = false;
    const stateFile = ".jsdos/local-state.json";
    const mark = (node) => {
        if (!active) { return; }
        const path = fs.getPath(node);
        if (!path.startsWith(root + "/")) { return; }
        dirty.add(path.slice(root.length + 1));
        state.revision++; state.dirty = Array.from(dirty);
        fs.writeFile(stateFile, JSON.stringify(state));
    };
    const deny = () => { throw new fs.ErrnoError(2); };
    fs.mkdir(target);
    // Keep the directory in the runtime's normal MEMFS tree. Its fsTree API
    // does not follow a second MEMFS mount; an empty shadow tree is unsafe for
    // write-back deletion. Each owned node still has local-only operations.
    for (const entry of local.entries) {
        const parts = entry.path.split("/");
        if (parts.some((part) => !part || part === "." || part === ".." || /[\\\0]/.test(part))) { deny(); }
        const path = target + "/" + entry.path;
        if (entry.directory) { fs.mkdir(path); }
        else {
            const slash = path.lastIndexOf("/");
            fs.createDataFile(path.slice(0, slash), path.slice(slash + 1), new Uint8Array(), true, true);
            const node = fs.lookupPath(path).node;
            node.usedBytes = entry.file.size;
            node.localFile = entry.file;
        }
    }
    const wrap = (node) => {
        const ops = node.node_ops, streams = node.stream_ops;
        const load = () => {
            if (!node.localFile) { return; }
            try { node.contents = new Uint8Array(reader.readAsArrayBuffer(node.localFile)); }
            catch { throw new fs.ErrnoError(29); }
            node.usedBytes = node.contents.length; node.localFile = null;
        };
        node.node_ops = { ...ops,
            setattr(target, attrs) {
                if (!local.writable) { deny(); }
                if (attrs.size !== undefined) {
                    if (attrs.size > local.maxFileBytes) { throw new fs.ErrnoError(51); }
                    if (attrs.size === 0) { node.localFile = null; node.contents = new Uint8Array(); node.usedBytes = 0; }
                    else { load(); }
                }
                const result = ops.setattr(target, attrs); mark(node); return result;
            },
        };
        if (fs.isDir(node.mode)) {
            for (const child of Object.values(node.contents)) { wrap(child); }
            node.node_ops.mknod = (...args) => {
                if (!local.writable) { deny(); }
                const child = ops.mknod(...args); wrap(child); state.entries++; mark(child); return child;
            };
            node.node_ops.symlink = deny;
            for (const method of ["unlink", "rmdir"]) {
                node.node_ops[method] = (parent, name) => {
                    if (!local.writable) { deny(); }
                    const target = fs.lookupPath(fs.getPath(parent) + "/" + name).node;
                    if (active) { loaders.get(target)?.(); }
                    const result = ops[method](parent, name); state.entries--; mark(target); return result;
                };
            }
            node.node_ops.rename = (old, parent, name) => {
                if (!local.writable) { deny(); }
                // Retain bytes before the original local path can be removed.
                const touch = (entry) => {
                    if (fs.isDir(entry.mode)) { Object.values(entry.contents).forEach(touch); }
                    else { loaders.get(entry)?.(); }
                    mark(entry);
                };
                const previous = parent.contents[name];
                touch(old); const result = ops.rename(old, parent, name);
                if (previous && previous !== old) { state.entries--; }
                touch(old); return result;
            };
        } else {
            loaders.set(node, load);
            node.stream_ops = { ...streams,
                read(stream, buffer, offset, length, position) {
                    if (!node.localFile) { return streams.read(stream, buffer, offset, length, position); }
                    try {
                        const data = new Uint8Array(reader.readAsArrayBuffer(node.localFile.slice(position, position + length)));
                        buffer.set(data, offset); return data.length;
                    } catch { throw new fs.ErrnoError(29); }
                },
                write(stream, buffer, offset, length, position, ...rest) {
                    if (!local.writable) { deny(); }
                    if (position + length > local.maxFileBytes) { throw new fs.ErrnoError(51); }
                    load(); const result = streams.write(stream, buffer, offset, length, position, ...rest); mark(node); return result;
                },
                mmap(...args) {
                    if (!local.writable && (args[3] & 2)) { deny(); }
                    load(); if (local.writable) { mark(node); } return streams.mmap(...args);
                },
                msync(...args) { if (!local.writable) { deny(); } const result = streams.msync(...args); mark(node); return result; },
            };
        }
    };
    wrap(fs.lookupPath(target).node);
    return { state, activate() { active = true; }, retire() { active = false; } };
}

function installRemoteDisk(fs) {
    let manifest;
    try { manifest = JSON.parse(fs.readFile(".jsdos/disk.json", { encoding: "utf8" })); }
    catch { return; }
    const root = fs.cwd().replace(/\/$/, "") + "/drive_c/";
    const dirty = new Set(), cache = new Map(), loaders = new Map();
    const chunkSize = 65536, maxCachedChunks = 256;
    const stateFile = ".jsdos/file-state.json";
    const state = { remote: Object.keys(manifest.files), dirty: [] };
    const canonical = (path) => String(path).startsWith(root) ? String(path).slice(root.length).toUpperCase() : "";
    const writeState = () => { state.dirty = Array.from(dirty); fs.writeFile(stateFile, JSON.stringify(state)); };
    const mark = (path) => {
        const name = canonical(path);
        if (name && !dirty.has(name)) { dirty.add(name); writeState(); }
    };
    const chunk = (name, info, index) => {
        const key = name + ":" + index;
        if (cache.has(key)) {
            const data = cache.get(key); cache.delete(key); cache.set(key, data); return data;
        }
        const query = new URLSearchParams({ name, sha256: info.sha256, base_id: manifest.base_id,
            account: manifest.account, base_file: String(info.base), offset: String(index * chunkSize), size: String(chunkSize) });
        const request = new XMLHttpRequest();
        request.open("GET", self.location.origin + "/api/dos/file?" + query, false);
        request.responseType = "arraybuffer";
        request.timeout = 30000;
        request.send();
        if (request.status !== 200) { throw new fs.ErrnoError(29); }
        const data = new Uint8Array(request.response || []);
        if (data.length !== Math.min(chunkSize, info.size - index * chunkSize)) { throw new fs.ErrnoError(29); }
        cache.set(key, data);
        if (cache.size > maxCachedChunks) { cache.delete(cache.keys().next().value); }
        return data;
    };
    for (const [name, info] of Object.entries(manifest.files)) {
        const slash = name.lastIndexOf("/");
        const parent = slash < 0 ? "drive_c" : "drive_c/" + name.slice(0, slash);
        const path = parent + "/" + name.slice(slash + 1);
        fs.createDataFile(parent, name.slice(slash + 1), new Uint8Array(), true, true);
        const node = fs.lookupPath(path).node;
        const streamOps = node.stream_ops, nodeOps = node.node_ops;
        node.usedBytes = info.size;
        let materialized = false;
        const load = () => {
            if (materialized) { return; }
            const contents = new Uint8Array(info.size);
            for (let offset = 0; offset < info.size; offset += chunkSize) {
                contents.set(chunk(name, info, Math.floor(offset / chunkSize)), offset);
            }
            node.contents = contents; node.usedBytes = info.size; materialized = true;
        };
        loaders.set(node, { load, base: info.base });
        node.stream_ops = {
            ...streamOps,
            read(stream, buffer, offset, length, position) {
                if (materialized) { return streamOps.read(stream, buffer, offset, length, position); }
                const count = Math.max(0, Math.min(length, info.size - position));
                let copied = 0;
                while (copied < count) {
                    const start = position + copied;
                    const part = chunk(name, info, Math.floor(start / chunkSize));
                    const partOffset = start % chunkSize;
                    const size = Math.min(count - copied, part.length - partOffset);
                    buffer.set(part.subarray(partOffset, partOffset + size), offset + copied); copied += size;
                }
                return count;
            },
            write(...args) { load(); mark(fs.getPath(node)); return streamOps.write(...args); },
            mmap(...args) { load(); return streamOps.mmap(...args); },
        };
        node.node_ops = {
            ...nodeOps,
            setattr(target, attrs) {
                if (attrs.size !== undefined) {
                    if (attrs.size === 0) { node.contents = new Uint8Array(); node.usedBytes = 0; materialized = true; }
                    else { load(); }
                    mark(fs.getPath(node));
                }
                return nodeOps.setattr(target, attrs);
            },
        };
    }
    const write = fs.write;
    fs.write = (stream, ...args) => { const result = write(stream, ...args); mark(fs.getPath(stream.node)); return result; };
    const unlink = fs.unlink;
    fs.unlink = (path) => { mark(fs.getPath(fs.lookupPath(path).node)); return unlink(path); };
    const rename = fs.rename;
    fs.rename = (oldPath, newPath) => {
        const prepare = (node) => {
            if (fs.isDir(node.mode)) { Object.values(node.contents).forEach(prepare); }
            else if (loaders.has(node) && !loaders.get(node).base) { loaders.get(node).load(); }
        };
        prepare(fs.lookupPath(oldPath).node);
        const result = rename(oldPath, newPath);
        const markTree = (node) => {
            if (fs.isDir(node.mode)) { Object.values(node.contents).forEach(markTree); }
            else { mark(fs.getPath(node)); }
        };
        markTree(fs.lookupPath(newPath).node);
        return result;
    };
    writeState();
}
