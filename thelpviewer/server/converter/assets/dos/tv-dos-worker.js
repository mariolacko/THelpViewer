// File-on-demand adapter for the pinned DOSBox runtime; vendor files stay unchanged.
importScripts(self.location.origin + "/assets/dos/emulators/wdosbox.js");

const createDosbox = WDOSBOX;
WDOSBOX = function (options) {
    const initialized = options.onRuntimeInitialized;
    options.onRuntimeInitialized = () => {
        const extract = options._extractBundleToFs;
        options._extractBundleToFs = (...args) => {
            const result = extract(...args);
            installRemoteDisk(options.FS);
            return result;
        };
        initialized?.();
    };
    return createDosbox(options);
};

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
