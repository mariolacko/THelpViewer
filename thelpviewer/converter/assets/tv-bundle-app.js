// Bundle viewer: single-page app that loads help JSON bundles on demand.
(function () {
"use strict";
const TV = window.THelpViewerTV = window.THelpViewerTV || {};
const {
    escapeHtml,
    renderHotkeyMarkup,
    fillBorders,
    fillDesktopPatterns,
    updateClocks,
    applyThemePreset,
    applyThemeAndSyncPalette,
    readStoredThemePreset,
    readStoredColorPalette,
    applyColorPalette,
    buildPaletteFromCurrentStyle,
    TVDialogManager,
    TVAboutDialog,
    TVPuzzleDialog,
    TVCalendarDialog,
    TVAsciiTableDialog,
    TVCalculatorDialog,
    TVColorsDialog,
    TVSearchDialog,
    TVTetrisDialog,
    TVMinesDialog,
    TVBreakOutDialog,
    TVSokobanDialog,
    TVLinesDialog,
    TVReversiDialog,
    TVSnakeDialog,
    TVScreenSaver,
    TVWidget,
    TVButton,
    TVMenuBox,
    measureCells,
    TurboVisionScrollbar,
    TurboVisionWindowResizer,
    bindCloseButtons,
    updateWindowFrameState,
    SCROLL_REPEAT_MS,
    TRACK_CHAR,
    DISABLED_TRACK_CHAR,
    THUMB_CHAR,
    highlightCodeExamples,
    DOS_COLORS,
} = TV;

// ── Catalog & data cache ────────────────────────────────────────────

const HELPS_DIR = "helps/";
const CATALOG_FILE = HELPS_DIR + "catalog.json";
const DOCS_DIR = "docs/";
const DOCS_CATALOG_FILE = DOCS_DIR + "catalog.json";
const bundleCache = new Map();
let catalogData = null;
let docsCatalogData = null;

function loadBundle(filename, { onProgress, signal } = {}) {
    if (bundleCache.has(filename)) {
        return Promise.resolve(bundleCache.get(filename));
    }
    const fetchUrl = HELPS_DIR + filename;
    return fetch(fetchUrl, { signal }).then(async (response) => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status} loading ${filename}`);
        }
        const contentLength = Number(response.headers.get("Content-Length")) || 0;

        let payloadBytes;
        if (!contentLength || !response.body) {
            payloadBytes = new Uint8Array(await response.arrayBuffer());
            if (onProgress) { onProgress(1, 1); }
        } else {
            const reader = response.body.getReader();
            const chunks = [];
            let received = 0;
            const simulateSlow = new URLSearchParams(window.location.search).has("slow");
            while (true) {
                if (signal && signal.aborted) {
                    await reader.cancel();
                    throw new DOMException("Aborted", "AbortError");
                }
                const { done, value } = await reader.read();
                if (done) { break; }
                chunks.push(value);
                received += value.length;
                if (onProgress) { onProgress(received, contentLength); }
                if (simulateSlow) { await new Promise((r) => setTimeout(r, 80)); }
            }
            // Reassemble
            const total = chunks.reduce((s, c) => s + c.length, 0);
            payloadBytes = new Uint8Array(total);
            let offset = 0;
            for (const chunk of chunks) {
                payloadBytes.set(chunk, offset);
                offset += chunk.length;
            }
        }

        let json;
        if (/\.gz$/i.test(filename)) {
            if (typeof DecompressionStream !== "function") {
                throw new Error("This browser does not support DecompressionStream for .json.gz bundles.");
            }
            const stream = new Blob([payloadBytes]).stream().pipeThrough(new DecompressionStream("gzip"));
            json = await new Response(stream).text();
        } else {
            json = new TextDecoder("utf-8").decode(payloadBytes);
        }
        const bundle = JSON.parse(json);
        if (bundle.uhf_version !== "2.0") {
            throw new Error(`Unsupported bundle version in ${filename}: ${bundle.uhf_version || "missing"}`);
        }
        bundle._catalogFile = filename;
        bundleCache.set(filename, bundle);
        return bundle;
    });
}

const UHF_BOX_TRIM_CHARS = " \t\u2500\u2502\u250c\u2510\u2514\u2518\u251c\u2524\u252c\u2534\u253c\u2550\u2551\u2554\u2557\u255a\u255d\u2560\u2563\u2566\u2569\u256c\u2580\u2584\u2588\u258c\u2590\u2591\u2592\u2593\u25a0\u2261";
const UHF_BOX_ONLY_CHARS = new Set(UHF_BOX_TRIM_CHARS.replace(/[ \t]/g, "") + "-_=|");

function bundleFormatName(bundle) {
    return (((bundle.metadata || {}).source || {}).format) || "help";
}

function bundleSourceFilename(bundle) {
    return (((bundle.metadata || {}).source || {}).filename) || "help";
}

function bundleSourceName(bundle) {
    return String(bundleSourceFilename(bundle) || "help").toLowerCase();
}

function normalizeSourceFileName(value) {
    return String(value || "").trim().toLowerCase();
}

function normalizeSourceFileStem(value) {
    const normalized = normalizeSourceFileName(value);
    if (!normalized) {
        return "";
    }
    const name = normalized.split(/[\\/]/).pop() || normalized;
    return name.replace(/\.[^.]+$/, "");
}

function findCatalogEntryBySourceFile(sourceFile) {
    const wanted = normalizeSourceFileName(sourceFile);
    if (!wanted || !Array.isArray(catalogData)) {
        return null;
    }
    const sourceFiles = (entry) => {
        const values = [];
        if (entry && typeof entry.source_file === "string") {
            values.push(entry.source_file);
        }
        if (entry && Array.isArray(entry.source_files)) {
            for (const value of entry.source_files) {
                if (typeof value === "string") {
                    values.push(value);
                }
            }
        }
        return values;
    };
    // Check explicit source files and the source_files array
    let found = catalogData.find((entry) => sourceFiles(entry).some((value) => normalizeSourceFileName(value) === wanted)) || null;
    if (found) { return found; }

    // Check bundle file path (catalog entry 'file')
    found = catalogData.find((entry) => normalizeSourceFileName(entry.file || "") === wanted) || null;
    if (found) { return found; }

    const wantedStem = normalizeSourceFileStem(sourceFile);
    if (!wantedStem) { return null; }

    // Stem fallback for source_files or bundle file
    found = catalogData.find((entry) => sourceFiles(entry).some((value) => normalizeSourceFileStem(value) === wantedStem) || normalizeSourceFileStem(entry.file || "") === wantedStem) || null;
    return found;
}

function bundleLoadingLabel(value, fallback = "") {
    if (value && typeof value === "object") {
        const name = String(value.name || "").trim();
        if (name) {
            return name;
        }
        const file = String(value.file || "").trim();
        if (file) {
            return file.split("/").pop() || file;
        }
    }
    const text = String(value || fallback || "").trim();
    if (!text) {
        return "Help";
    }
    return text.split("/").pop() || text;
}

function bundleTitle(bundle) {
    return ((bundle.metadata || {}).name) || "Help";
}

function bundleHeaderLabel(bundle) {
    const title = bundleTitle(bundle);
    const sourceName = bundleSourceName(bundle);
    return sourceName ? `${title} (${sourceName})` : title;
}

function bundleIndexLabel(bundle) {
    const formatName = bundleFormatName(bundle);
    if (formatName === "thelp") { return "Turbo Help Index"; }
    if (formatName === "m602") { return "Software602 Help Index"; }
    return "Help Index";
}

function bundleWindowSpec(bundle) {
    const display = ((bundle.metadata || {}).display) || {};
    const formatName = bundleFormatName(bundle);
    let cols = 82;
    let rows = 24;
    if (Number.isInteger(display.cols) && display.cols > 0) {
        cols = display.cols + 3;
    } else if (formatName === "fbhf") {
        cols = 50;
    }
    if (Number.isInteger(display.rows) && display.rows > 0) {
        rows = display.rows + 3;
    } else if (formatName === "fbhf") {
        rows = 18;
    }
    const hasExplicitDisplay = Number.isInteger(display.cols) && display.cols > 0
        && Number.isInteger(display.rows) && display.rows > 0;
    return {
        cols,
        rows,
        min_cols: hasExplicitDisplay ? cols : Math.min(cols, 80),
        min_rows: hasExplicitDisplay ? rows : Math.min(rows, 25),
    };
}

function bundleWindowKey(bundle) {
    return bundle._catalogFile || bundleSourceFilename(bundle) || bundleHeaderLabel(bundle);
}

function bundleTopicList(bundle) {
    const topics = bundle.topics && typeof bundle.topics === "object"
        ? Object.values(bundle.topics)
        : [];
    topics.sort((a, b) => (Number(a.id) || 0) - (Number(b.id) || 0));
    return topics;
}

function bundleHelpTopicRef(bundle) {
    const topics = bundleTopicList(bundle);
    const main = topics.find((topic) => topic && topic.is_main);
    if (main) { return String(main.id); }
    return topics.length ? String(topics[0].id) : null;
}

function normalizeDirectTopicRef(bundle, ref) {
    if (ref == null) { return null; }
    const raw = String(ref).trim();
    if (!raw) { return null; }
    const topics = bundle.topics && typeof bundle.topics === "object" ? bundle.topics : {};
    if (Object.prototype.hasOwnProperty.call(topics, raw)) {
        return raw;
    }
    if (/^[0-9]+$/.test(raw)) {
        const normalized = String(parseInt(raw, 10));
        if (Object.prototype.hasOwnProperty.call(topics, normalized)) {
            return normalized;
        }
    }
    if (/^[0-9A-Fa-f]+$/.test(raw)) {
        const parsed = parseInt(raw, 16);
        if (!Number.isNaN(parsed)) {
            const normalized = String(parsed);
            if (Object.prototype.hasOwnProperty.call(topics, normalized)) {
                return normalized;
            }
        }
    }
    return null;
}

function normalizeTopicAlias(value) {
    return String(value || "").trim().toLowerCase();
}

function bundleAliasMap(bundle) {
    if (bundle._topicAliasMap instanceof Map) {
        return bundle._topicAliasMap;
    }

    const aliasMap = new Map();
    const topics = bundle.topics && typeof bundle.topics === "object" ? bundle.topics : {};
    for (const [rawKey, topic] of Object.entries(topics)) {
        const resolvedTopic = normalizeDirectTopicRef(bundle, rawKey)
            || (topic && topic.id != null ? normalizeDirectTopicRef(bundle, topic.id) : null)
            || String(rawKey).trim();
        const aliases = topic && typeof topic === "object" ? topic.aliases : null;
        const addAlias = (value) => {
            const normalized = normalizeTopicAlias(value);
            if (!normalized || aliasMap.has(normalized)) {
                return;
            }
            aliasMap.set(normalized, resolvedTopic);
        };

        if (Array.isArray(aliases)) {
            aliases.forEach((value) => addAlias(value));
            continue;
        }
        if (aliases && typeof aliases === "object") {
            const ids = Array.isArray(aliases.ids) ? aliases.ids : [];
            const strings = Array.isArray(aliases.strings) ? aliases.strings : [];
            ids.forEach((value) => addAlias(value));
            strings.forEach((value) => addAlias(value));
        }
    }

    bundle._topicAliasMap = aliasMap;
    return aliasMap;
}

function normalizeTopicRef(bundle, ref) {
    const direct = normalizeDirectTopicRef(bundle, ref);
    if (direct) {
        return direct;
    }
    const alias = normalizeTopicAlias(ref);
    if (!alias) {
        return null;
    }
    return bundleAliasMap(bundle).get(alias) || null;
}

function flattenUhfIndexEntries(bundle) {
    const entries = [];
    if (!Array.isArray(bundle.index)) {
        return entries;
    }
    bundle.index.forEach((group) => {
        const groupEntries = Array.isArray(group && group.entries) ? group.entries : [];
        groupEntries.forEach((entry) => {
            entries.push({
                label: entry.label || "",
                context_id: entry.topic_id,
                context_hex: String(entry.topic_id),
            });
        });
    });
    return entries;
}

function bundleIndexEntries(bundle) {
    return flattenUhfIndexEntries(bundle);
}

function bundleHasIndexEntries(bundle) {
    return bundleIndexEntries(bundle).length > 0;
}

function bundleHasNavAction(bundle, action) {
    const wanted = String(action || "").toLowerCase();
    if (!wanted) { return false; }
    return bundleTopicList(bundle).some((topic) => {
        const nav = topic && topic.nav && typeof topic.nav === "object" ? topic.nav : {};
        return Object.values(nav).some((item) =>
            item
            && typeof item === "object"
            && String(item.action || "").toLowerCase() === wanted
        );
    });
}

function bundleCanShowIndex(bundle) {
    return bundleHasIndexEntries(bundle) || bundleHasNavAction(bundle, "index");
}

function bundleCanShowContents(bundle) {
    return (
        (Array.isArray(bundle.contents) && bundle.contents.length > 0)
        || bundleHasNavAction(bundle, "contents")
    );
}

function isUhfCodeStart(line) {
    return /^\[code(?::[A-Za-z0-9_-]+)?\]$/i.test(line);
}

function stripUhfMarkup(text) {
    let result = "";
    let index = 0;
    while (index < text.length) {
        const ch = text[index];
        if (ch !== "[") {
            result += ch;
            index += 1;
            continue;
        }
        if (text[index + 1] === "[") {
            result += "[";
            index += 2;
            continue;
        }
        const close = text.indexOf("]", index + 1);
        if (close < 0) {
            result += text.slice(index);
            break;
        }
        index = close + 1;
    }
    return result;
}

function compactVisibleText(text) {
    let cleaned = text;
    for (const ch of UHF_BOX_TRIM_CHARS) {
        if (ch === " " || ch === "\t") { continue; }
        cleaned = cleaned.split(ch).join(" ");
    }
    return cleaned.replace(/\s+/g, " ").trim();
}

function isUnderlineText(text) {
    const stripped = text.trim();
    if (!stripped) { return true; }
    for (const ch of stripped) {
        if (!UHF_BOX_ONLY_CHARS.has(ch)) {
            return false;
        }
    }
    return true;
}

function deriveUhfTopicTitle(topic) {
    if (topic && typeof topic.title === "string" && topic.title.trim()) {
        return topic.title.trim();
    }
    const content = Array.isArray(topic && topic.content) ? topic.content : [];
    let inCodeBlock = false;
    for (const line of content) {
        if (isUhfCodeStart(line)) {
            inCodeBlock = true;
            continue;
        }
        if (line === "[/code]") {
            inCodeBlock = false;
            continue;
        }
        if (inCodeBlock || line === "[rule]") {
            continue;
        }
        const compact = compactVisibleText(stripUhfMarkup(String(line || "")));
        if (compact && !isUnderlineText(compact)) {
            return compact;
        }
    }
    return topic && topic.id != null ? `Topic ${topic.id}` : "Topic";
}

function bundleTopicTitle(bundle, topic) {
    return deriveUhfTopicTitle(topic);
}

function renderUhfRule(bundle) {
    const width = Math.max((bundleWindowSpec(bundle).cols || 82) - 6, 1);
    return escapeHtml("─".repeat(width));
}

function parseUhfLinkTargetSpec(rawTarget) {
    const targetText = String(rawTarget || "").trim();
    if (!targetText) {
        return null;
    }

    const target = {};
    let recognized = false;
    for (const part of targetText.split(",")) {
        const chunk = part.trim();
        if (!chunk || !chunk.includes("=")) {
            return null;
        }
        const eq = chunk.indexOf("=");
        const key = chunk.slice(0, eq).trim().toLowerCase();
        const value = chunk.slice(eq + 1).trim();
        if (!value) {
            continue;
        }
        if (key === "file" || key === "source") {
            target.file = value;
            recognized = true;
            continue;
        }
        if (key === "topic" || key === "topic_id" || key === "id") {
            if (!/^-?\d+$/.test(value)) {
                return null;
            }
            target.topic = value;
            recognized = true;
            continue;
        }
        if (key === "alias") {
            target.alias = value;
            recognized = true;
            continue;
        }
        if (key === "line" || key === "row") {
            if (!/^\d+$/.test(value) || parseInt(value, 10) <= 0) {
                return null;
            }
            target.line = String(parseInt(value, 10));
            recognized = true;
        }
    }

    return recognized ? target : null;
}

function parseUhfTag(tagBody) {
    const lowered = tagBody.toLowerCase();
    if (lowered === "b") { return { name: "b", open: "<b>", close: "</b>", raw: tagBody }; }
    if (lowered === "i") { return { name: "i", open: "<i>", close: "</i>", raw: tagBody }; }
    if (lowered === "u") { return { name: "u", open: "<u>", close: "</u>", raw: tagBody }; }
    if (lowered === "r") { return { name: "r", open: '<span class="tv-uhf-reverse">', close: "</span>", raw: tagBody }; }

    let match = tagBody.match(/^link:(.+)$/i);
    if (match) {
        const linkTarget = parseUhfLinkTargetSpec(match[1]);
        if (!linkTarget) {
            return null;
        }
        const attrs = ['href="#"', 'data-tv-uhf-link="1"'];
        if (linkTarget.file) {
            attrs.push(`data-tv-source-file="${escapeHtml(linkTarget.file)}"`);
        }
        if (linkTarget.topic) {
            attrs.push(`data-tv-bundle-topic="${escapeHtml(linkTarget.topic)}"`);
        }
        if (linkTarget.alias) {
            attrs.push(`data-tv-topic-alias="${escapeHtml(linkTarget.alias)}"`);
        }
        if (linkTarget.line) {
            attrs.push(`data-tv-topic-line="${escapeHtml(linkTarget.line)}"`);
        }
        return {
            name: "link",
            open: `<a ${attrs.join(" ")}>`,
            close: "</a>",
            raw: tagBody,
        };
    }

    match = tagBody.match(/^nav:(back|contents|index)$/i);
    if (match) {
        return {
            name: "nav",
            open: `<a href="#" data-tv-nav="${escapeHtml(match[1].toLowerCase())}">`,
            close: "</a>",
            raw: tagBody,
        };
    }

    match = tagBody.match(/^fg:(\d{1,2})$/i);
    if (match) {
        const colorIndex = parseInt(match[1], 10);
        if (colorIndex >= 0 && colorIndex < DOS_COLORS.length) {
            return {
                name: "fg",
                open: `<span style="color:${DOS_COLORS[colorIndex]}">`,
                close: "</span>",
                raw: tagBody,
            };
        }
    }

    match = tagBody.match(/^bg:(\d{1,2})$/i);
    if (match) {
        const colorIndex = parseInt(match[1], 10);
        if (colorIndex >= 0 && colorIndex < DOS_COLORS.length) {
            return {
                name: "bg",
                open: `<span style="background:${DOS_COLORS[colorIndex]}">`,
                close: "</span>",
                raw: tagBody,
            };
        }
    }

    match = tagBody.match(/^color:(\d{1,2})(?::(\d{1,2}))?$/i);
    if (match) {
        const fg = parseInt(match[1], 10);
        const bg = match[2] != null ? parseInt(match[2], 10) : null;
        if (fg >= 0 && fg < DOS_COLORS.length && (bg == null || (bg >= 0 && bg < DOS_COLORS.length))) {
            const styles = [`color:${DOS_COLORS[fg]}`];
            if (bg != null) {
                styles.push(`background:${DOS_COLORS[bg]}`);
            }
            return {
                name: "color",
                open: `<span style="${styles.join(";")}">`,
                close: "</span>",
                raw: tagBody,
            };
        }
    }

    return null;
}

function renderUhfInline(text) {
    const root = { name: null, open: "", close: "", raw: "", children: [] };
    const stack = [root];

    function append(fragment) {
        stack[stack.length - 1].children.push(fragment);
    }

    let index = 0;
    while (index < text.length) {
        const open = text.indexOf("[", index);
        if (open < 0) {
            append(escapeHtml(text.slice(index)));
            break;
        }
        if (open > index) {
            append(escapeHtml(text.slice(index, open)));
        }
        if (text[open + 1] === "[") {
            append("[");
            index = open + 2;
            continue;
        }
        const close = text.indexOf("]", open + 1);
        if (close < 0) {
            append(escapeHtml(text.slice(open)));
            break;
        }
        const tagBody = text.slice(open + 1, close);
        if (tagBody.startsWith("/")) {
            const closeName = tagBody.slice(1).toLowerCase();
            if (stack.length > 1 && stack[stack.length - 1].name === closeName) {
                const node = stack.pop();
                append(node.open + node.children.join("") + node.close);
            } else {
                append(escapeHtml(text.slice(open, close + 1)));
            }
            index = close + 1;
            continue;
        }
        const descriptor = parseUhfTag(tagBody);
        if (!descriptor) {
            append(escapeHtml(text.slice(open, close + 1)));
            index = close + 1;
            continue;
        }
        stack.push({ ...descriptor, children: [] });
        index = close + 1;
    }

    while (stack.length > 1) {
        const node = stack.pop();
        stack[stack.length - 1].children.push(
            escapeHtml(`[${node.raw}]`) + node.children.join("")
        );
    }

    return root.children.join("");
}

function bundleFrozenRows(bundle, topic) {
    if (topic && Object.prototype.hasOwnProperty.call(topic, "frozen_rows")) {
        return Math.max(0, Number(topic.frozen_rows) || 0);
    }
    return Math.max(0, Number((bundle.metadata || {}).frozen_rows) || 0);
}

function wrapTopicLineMarkup(lineNumber, html) {
    return `<span class="tv-topic-line" data-tv-line="${lineNumber}">${html}</span>`;
}

function renderUhfTopicLines(topic, bundle) {
    const lines = [];
    const content = Array.isArray(topic && topic.content) ? topic.content : [];
    let inCodeBlock = false;
    let lineNumber = 0;

    content.forEach((line) => {
        if (isUhfCodeStart(line)) {
            inCodeBlock = true;
            return;
        }
        if (line === "[/code]") {
            inCodeBlock = false;
            return;
        }
        if (line === "[rule]") {
            lineNumber += 1;
            lines.push(wrapTopicLineMarkup(lineNumber, renderUhfRule(bundle)));
            return;
        }
        if (inCodeBlock) {
            lineNumber += 1;
            if (!line) {
                lines.push(
                    wrapTopicLineMarkup(
                        lineNumber,
                        '<span class="code-example code-example-empty">&nbsp;</span>',
                    )
                );
                            content.forEach((line) => {
                                const raw = String(line || "");
                                const leftTrim = raw.replace(/^[ \t]+/, "");
                                // THELP in-band markers (CP437 0x05 etc.) sometimes appear as
                                // visible glyphs such as '♣' or '►♣' at the start of a line. Treat
                                // a leading marker as a code-block toggle and, if the marker is
                                // followed by text, render the remainder as the first/last code line.
                                const THELP_MARKER_RE = /^[\u2663\u25BA\u25C4]+/;
                                if (leftTrim && THELP_MARKER_RE.test(leftTrim)) {
                                    const after = leftTrim.replace(THELP_MARKER_RE, "");
                                    inCodeBlock = !inCodeBlock;
                                    if (!after) {
                                        // Marker-only line — toggled mode, skip visible output
                                        return;
                                    }
                                    lineNumber += 1;
                                    if (inCodeBlock) {
                                        if (!after) {
                                            lines.push(
                                                wrapTopicLineMarkup(
                                                    lineNumber,
                                                    '<span class="code-example code-example-empty">&nbsp;</span>',
                                                ),
                                            );
                                        } else {
                                            lines.push(
                                                wrapTopicLineMarkup(
                                                    lineNumber,
                                                    `<span class="code-example">${renderUhfInline(after)}</span>`,
                                                ),
                                            );
                                        }
                                    } else {
                                        // closing marker with trailing text — treat as normal text
                                        lines.push(wrapTopicLineMarkup(lineNumber, renderUhfInline(after)));
                                    }
                                    return;
                                }

                                if (isUhfCodeStart(line)) {
                                    inCodeBlock = true;
                                    return;
                                }
                                if (line === "[/code]") {
                                    inCodeBlock = false;
                                    return;
                                }
                                if (line === "[rule]") {
                                    lineNumber += 1;
                                    lines.push(wrapTopicLineMarkup(lineNumber, renderUhfRule(bundle)));
                                    return;
                                }
                                if (inCodeBlock) {
                                    lineNumber += 1;
                                    if (!line) {
                                        lines.push(
                                            wrapTopicLineMarkup(
                                                lineNumber,
                                                '<span class="code-example code-example-empty">&nbsp;</span>',
                                            )
                                        );
                                    } else {
                                        lines.push(
                                            wrapTopicLineMarkup(
                                                lineNumber,
                                                `<span class="code-example">${renderUhfInline(String(line))}</span>`,
                                            )
                                        );
                                    }
                                    return;
                                }
                                lineNumber += 1;
                                lines.push(wrapTopicLineMarkup(lineNumber, renderUhfInline(String(line || ""))));
                            });
        html.push("</div>");
        return html.join("\n");
    }

    return [
        '<pre class="tv-pre tv-topic-pre">',
        "",
        ...lines,
        "</pre>",
    ].join("\n");
}

function buildUhfSearchIndex(bundle) {
    if (Array.isArray(bundle._searchIndex)) {
        return bundle._searchIndex;
    }

    const indexTermsByTopic = new Map();
    flattenUhfIndexEntries(bundle).forEach((entry) => {
        const topicKey = String(entry.context_id);
        if (!indexTermsByTopic.has(topicKey)) {
            indexTermsByTopic.set(topicKey, []);
        }
        if (entry.label) {
            indexTermsByTopic.get(topicKey).push(entry.label);
        }
    });

    bundle._searchIndex = bundleTopicList(bundle).map((topic) => {
        const bodyLines = [];
        const content = Array.isArray(topic && topic.content) ? topic.content : [];
        let inCodeBlock = false;
        content.forEach((line) => {
            if (isUhfCodeStart(line)) {
                inCodeBlock = true;
                return;
            }
            if (line === "[/code]") {
                inCodeBlock = false;
                return;
            }
            if (inCodeBlock || line === "[rule]") {
                return;
            }
            const compact = compactVisibleText(stripUhfMarkup(String(line || "")));
            if (compact && !isUnderlineText(compact)) {
                bodyLines.push(compact);
            }
        });

        let preview = bodyLines.slice(0, 3).join(" ").trim();
        if (preview.length > 180) {
            preview = preview.slice(0, 177).trimEnd() + "...";
        }

        const topicKey = String(topic.id);
        return {
            context_id: topic.id,
            context_hex: topicKey,
            title: bundleTopicTitle(bundle, topic),
            preview,
            index_terms: Array.from(new Set(indexTermsByTopic.get(topicKey) || [])).sort(),
            text: bodyLines.join("\n"),
        };
    });

    return bundle._searchIndex;
}

// ── Window rendering ────────────────────────────────────────────────

// ── Loading progress dialog (DOS Navigator Copy style) ──────────────

const PROGRESS_BAR_WIDTH = 32;

class TVLoadingDialog {
    constructor(desktop) {
        const {
            TVDialog,
            TVStaticText,
            TVGroup,
            TVButtonStrip,
            TVButton: TVBtn,
        } = TV;
        this.desktop = desktop;
        this.cancelled = false;
        this.abortController = new AbortController();


        const cancelButton = new TVBtn({
            x: 15, y: 5, w: 10,
            className: "is-default",
            attrs: { "data-tv-loading-cancel": true },
            labelMarkup: renderHotkeyMarkup("~C~ancel"),
        });

        const bodyGroup = new TVGroup({
            w: 38, h: 6,
            children: [
                new TVStaticText({ x: 0, y: 1, w: 38, align: "center", className: "tv-loading-filename", text: "" }),
                new TVStaticText({ x: 0, y: 2, w: 38, align: "center", className: "tv-loading-bar-line", text: "" }),
                new TVStaticText({ x: 0, y: 3, w: 38, align: "center", className: "tv-loading-percent", text: "0%" }),
                cancelButton,
            ],
        }).renderMarkup();

        this.dialog = new TVDialog({
            desktop,
            overlayClass: "tv-loading-overlay",
            ariaLabel: "Loading",
            title: "Loading",
            closeAttrs: { "data-tv-loading-close": true, "aria-label": "Cancel loading" },
            bodyMarkup: bodyGroup,
            footerMarkup: TVDialog.footerMarkup(),
            width: "40ch",
            height: "min(9em, calc(100% - 2em))",
            top: "5em",
        });
        this.dialog.bindDrag();

        // Bind Cancel button
        const cancelEl = this.dialog.query("[data-tv-loading-cancel]");
        if (cancelEl) {
            cancelEl.addEventListener("click", () => this.cancel());
        }
        // Bind close [■] button
        this.dialog.bindCommonClose(() => this.cancel());

        this.filenameEl = this.dialog.query(".tv-loading-filename");
        this.barEl = this.dialog.query(".tv-loading-bar-line");
        this.percentEl = this.dialog.query(".tv-loading-percent");
    }

    get signal() {
        return this.abortController.signal;
    }

    show(filename) {
        if (this.filenameEl) { this.filenameEl.textContent = filename; }
        this.update(0, 1);
        this.dialog.open();
    }

    update(received, total) {
        const ratio = total > 0 ? Math.min(received / total, 1) : 0;
        const filled = Math.round(ratio * PROGRESS_BAR_WIDTH);
        const empty = PROGRESS_BAR_WIDTH - filled;
        if (this.barEl) {
            this.barEl.textContent = "█".repeat(filled) + "░".repeat(empty);
        }
        if (this.percentEl) {
            this.percentEl.textContent = `${Math.round(ratio * 100)}%`;
        }
    }

    cancel() {
        this.cancelled = true;
        this.abortController.abort();
        this.destroy();
    }

    close() {
        this.dialog.close();
    }

    destroy() {
        this.dialog.close();
        this.dialog.overlay.remove();
    }
}

// ── Window rendering ────────────────────────────────────────────────

function renderScrollbar(axis) {
    const glyphs = axis === "y" ? ["▲", "▼"] : ["◄", "►"];
    return [
        `<div class="tv-scrollbar tv-scrollbar-${axis}" data-axis="${axis}">`,
        `<button type="button" class="tv-scroll-arrow tv-scroll-arrow-backward" data-role="backward" aria-label="Scroll ${axis} backward">${glyphs[0]}</button>`,
        `<div class="tv-scroll-track" data-role="track"><div class="tv-scroll-cells" data-role="cells"></div><div class="tv-scroll-thumb" data-role="thumb"></div></div>`,
        `<button type="button" class="tv-scroll-arrow tv-scroll-arrow-forward" data-role="forward" aria-label="Scroll ${axis} forward">${glyphs[1]}</button>`,
        `</div>`,
    ].join("");
}

function buildWindowHTML(bundle, contentHTML, caption) {
    const w = bundleWindowSpec(bundle);
    const style = `--tv-window-cols:${w.cols}; --tv-window-rows:${w.rows}; --tv-window-min-cols:${w.min_cols}; --tv-window-min-rows:${w.min_rows};`;
    return [
        `<main class="tv-window" data-tv-window data-tv-bundle-window="${escapeHtml(bundleWindowKey(bundle))}" style="${style}">`,
        `<div class="tv-shell">`,
        `<div class="tv-border-row tv-border-top" data-tv-move-handle>`,
        `<span class="tv-border-corner" aria-hidden="true">╔</span>`,
        `<a class="tv-close-control" data-tv-close-button data-tv-bundle-close href="#" aria-label="Close window">[<span class="tv-close-glyph" data-tv-close-glyph>■</span>]</a>`,
        `<span class="tv-border-fill" data-tv-border-fill="═" aria-hidden="true"></span>`,
        `<div class="tv-window-caption">${escapeHtml(caption)}</div>`,
        `<span class="tv-border-fill" data-tv-border-fill="═" aria-hidden="true"></span>`,
        `<a class="tv-zoom-control" data-tv-bundle-zoom href="#" aria-label="Zoom window">[<span class="tv-zoom-glyph" data-tv-zoom-glyph>↑</span>]</a>`,
        `<span class="tv-border-corner" aria-hidden="true">╗</span>`,
        `</div>`,
        `<div class="tv-client-row">`,
        `<span class="tv-border-side tv-border-side-left" data-tv-border-side="║" aria-hidden="true"></span>`,
        `<div class="tv-frame">`,
        `<div class="tv-scroll-shell" data-tv-scroll-frame>`,
        `<div class="tv-viewport" data-tv-viewport>`,
        contentHTML,
        `</div>`,
        `</div>`,
        `</div>`,
        renderScrollbar("y"),
        `<div class="tv-bottom-bar">`,
        `<span class="tv-scroll-corner tv-scroll-corner-left" aria-hidden="true">╚</span>`,
        renderScrollbar("x"),
        `<button type="button" class="tv-grow-handle" data-tv-resize-handle aria-label="Resize window">─┘</button>`,
        `</div>`,
        `</div>`,
        `</div>`,
        `</main>`,
    ].join("\n");
}

// ── Index page rendering ────────────────────────────────────────────

function renderBundleIndex(bundle) {
    const navItems = [];
    const sections = [];
    const groups = Array.isArray(bundle.index) ? bundle.index : [];
    const byLetter = new Map(groups.map((group) => [String(group.group || ""), group]));
    if (byLetter.has("#")) {
        sections.push(renderIndexSection("#", "#", byLetter.get("#").entries || []));
    }
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("").forEach((letter) => {
        const group = byLetter.get(letter);
        if (group && Array.isArray(group.entries) && group.entries.length) {
            navItems.push(`<a class="tv-index-jump" href="#" data-letter="${letter}">${letter}</a>`);
            sections.push(renderIndexSection(letter, letter, group.entries));
        } else {
            navItems.push(`<span class="tv-index-jump is-empty">${letter}</span>`);
        }
    });

    return [
        `<div class="tv-document tv-index-document">`,
        `<div class="tv-index-heading">${escapeHtml(bundleIndexLabel(bundle))}</div>`,
        `<nav class="tv-index-nav">${navItems.join("")}</nav>`,
        ...sections,
        `</div>`,
    ].join("\n");
}

function renderIndexSection(anchor, label, entries) {
    const items = entries.map((entry) => {
        const topicRef = String(entry.topic_id);
        const attrs = [
            'href="#"',
            `data-tv-bundle-topic="${escapeHtml(topicRef)}"`,
        ];
        if (entry.source_file) {
            attrs.push(`data-tv-source-file="${escapeHtml(entry.source_file)}"`);
        } else if (entry.file) {
            attrs.push(`data-tv-source-file="${escapeHtml(entry.file)}"`);
        }
        return `<div class="tv-index-entry"><a ${attrs.join(" ")}>${escapeHtml(entry.label)}</a></div>`;
    });
    return [
        `<section class="tv-index-section" id="idx-${escapeHtml(anchor)}">`,
        `<div class="tv-index-section-heading">`,
        `<span class="tv-index-section-label">${escapeHtml(label)}</span>`,
        `</div>`,
        `<div class="tv-index-section-body">`,
        ...items,
        `</div>`,
        `</section>`,
    ].join("\n");
}

function renderBundleContents(bundle) {
    const nodes = Array.isArray(bundle.contents) ? bundle.contents : [];
    return [
        `<div class="tv-document tv-index-document tv-contents-document">`,
        `<div class="tv-index-heading">Contents</div>`,
        `<div class="tv-contents-tree">`,
        renderContentsNodes(nodes),
        `</div>`,
        `</div>`,
    ].join("\n");
}

function buildBundleTargetDataset(target) {
    const attrs = {};
    if (target && target.topic_id != null) {
        attrs["data-tv-bundle-topic"] = String(target.topic_id);
    }
    if (target && target.source_file) {
        attrs["data-tv-source-file"] = String(target.source_file);
    }
    if (target && target.alias) {
        attrs["data-tv-topic-alias"] = String(target.alias);
    }
    if (target && target.line != null) {
        attrs["data-tv-topic-line"] = String(target.line);
    }
    return attrs;
}

function renderHtmlAttributes(attrs) {
    return Object.entries(attrs)
        .map(([key, value]) => `${key}="${escapeHtml(String(value))}"`)
        .join(" ");
}

function renderContentsNodes(nodes) {
    return nodes.map((node) => {
        const label = escapeHtml(String(node.label || ""));
        const targetAttrs = buildBundleTargetDataset(node);
        const labelHTML = Object.keys(targetAttrs).length
            ? `<a ${renderHtmlAttributes({ href: "#", "data-tv-uhf-link": "1", ...targetAttrs })}>${label}</a>`
            : label;
        const children = Array.isArray(node.children) && node.children.length
            ? `<div class="tv-contents-children">${renderContentsNodes(node.children)}</div>`
            : "";
        return [
            `<div class="tv-contents-node">`,
            `<div class="tv-contents-label">${labelHTML}</div>`,
            children,
            `</div>`,
        ].join("\n");
    }).join("\n");
}

// ── Topic navigation ────────────────────────────────────────────────

function findTopicByHex(bundle, contextHex) {
    const normalized = normalizeTopicRef(bundle, contextHex);
    if (!normalized) { return null; }
    return (bundle.topics && bundle.topics[normalized]) || null;
}

function renderTopicContent(bundle, topic) {
    return renderUhfTopic(topic, bundle);
}

// ── Window manager ──────────────────────────────────────────────────

class BundleWindowManager {
    constructor(desktop, onNavigate) {
        this.desktop = desktop;
        this.onNavigate = onNavigate || null;
        this.dialogManager = null;
        this.openWindows = new Map(); // source_name → DOM element
        this.scrollbars = [];
        this.resizers = [];
        this.history = []; // { bundle, contextHex | null, lineNumber | null }
        this.currentBundle = null;
        this.currentContextHex = null;
        this.currentLineNumber = null;
    }

    showIndex(bundle) {
        // If the bundle has no index entries, show the main/fallback topic
        // instead of an empty index page.
        if (!bundleHasIndexEntries(bundle)) {
            const fallback = bundleHelpTopicRef(bundle);
            if (fallback) {
                this.showTopic(bundle, fallback);
                return;
            }
        }
        this._pushHistory();
        this.currentBundle = bundle;
        this.currentContextHex = null;
        this.currentLineNumber = null;
        const contentHTML = renderBundleIndex(bundle);
        this._openWindow(bundle, contentHTML, bundleHeaderLabel(bundle));
        if (this.onNavigate) { this.onNavigate("Index"); }
        this._updateUrl();
    }

    showTopic(bundle, contextHex, lineNumber = null) {
        const topic = findTopicByHex(bundle, contextHex);
        if (!topic) { return; }
        this._pushHistory();
        this.currentBundle = bundle;
        this.currentContextHex = normalizeTopicRef(bundle, contextHex);
        this.currentLineNumber = this._normalizeLineNumber(lineNumber);
        const contentHTML = renderTopicContent(bundle, topic);
        const windowEl = this._openWindow(bundle, contentHTML, bundleHeaderLabel(bundle));
        this._focusTopicLine(windowEl, this.currentLineNumber);
        if (this.onNavigate) { this.onNavigate(bundleTopicTitle(bundle, topic)); }
        this._updateUrl();
    }

    showContents(bundle) {
        if (Array.isArray(bundle.contents) && bundle.contents.length) {
            this._pushHistory();
            this.currentBundle = bundle;
            this.currentContextHex = null;
            this.currentLineNumber = null;
            this._openWindow(bundle, renderBundleContents(bundle), bundleHeaderLabel(bundle));
            if (this.onNavigate) { this.onNavigate("Contents"); }
            this._updateUrl();
            return;
        }
        const fallback = bundleHelpTopicRef(bundle);
        if (fallback) {
            this.showTopic(bundle, fallback);
            return;
        }
        this._updateUrl();
    }

    async openSourceTopic(sourceFile, topicRef, lineNumber = null) {
        const entry = findCatalogEntryBySourceFile(sourceFile);
        if (!entry) {
            console.warn(`Bundle not found for source file: ${sourceFile}`);
            return;
        }
        const bundle = await loadBundle(entry.file);
        const normalizedTopic = topicRef != null ? String(topicRef).trim() : "";
        if (normalizedTopic) {
            this.showTopic(bundle, normalizedTopic, lineNumber);
            return;
        }
        const fallback = bundleHelpTopicRef(bundle);
        if (fallback) {
            this.showTopic(bundle, fallback, lineNumber);
            return;
        }
        this.showContents(bundle);
    }

    _normalizeLineNumber(value) {
        const numeric = Number(value);
        if (Number.isInteger(numeric) && numeric > 0) {
            return numeric;
        }
        return null;
    }

    _focusTopicLine(windowEl, lineNumber) {
        const normalized = this._normalizeLineNumber(lineNumber);
        if (!windowEl || !normalized) {
            return;
        }
        const viewport = windowEl.querySelector("[data-tv-viewport]");
        const targetLine = windowEl.querySelector(`[data-tv-line="${normalized}"]`);
        if (!viewport || !targetLine) {
            return;
        }
        windowEl.querySelectorAll(".tv-topic-line.is-target").forEach((line) => {
            line.classList.remove("is-target");
        });
        targetLine.classList.add("is-target");
        const targetTop = targetLine.offsetTop;
        const padding = Math.max(targetLine.offsetHeight * 2, 16);
        viewport.scrollTop = Math.max(0, targetTop - padding);
    }

    _updateUrl() {
        if (!this.currentBundle) { return; }
        const catalogFile = this.currentBundle._catalogFile;
        const entry = catalogFile
            ? catalogData.find((e) => e.file === catalogFile)
            : catalogData.find((e) => e.name === bundleHeaderLabel(this.currentBundle));
        const params = new URLSearchParams();
        if (entry) { params.set("file", entry.file); }
        if (this.currentContextHex) { params.set("topic", this.currentContextHex); }
        if (this.currentLineNumber) { params.set("line", String(this.currentLineNumber)); }
        const qs = params.toString();
        const url = qs ? `${window.location.pathname}?${qs}` : window.location.pathname;
        window.history.replaceState(null, "", url);
    }

    _pushHistory() {
        if (this.currentBundle) {
            this.history.push({
                bundle: this.currentBundle,
                contextHex: this.currentContextHex,
                lineNumber: this.currentLineNumber,
            });
        }
    }

    goBack() {
        const prev = this.history.pop();
        if (!prev) { return; }
        // Restore without pushing to history again
        this.currentBundle = prev.bundle;
        this.currentContextHex = prev.contextHex;
        this.currentLineNumber = this._normalizeLineNumber(prev.lineNumber);
        if (prev.contextHex) {
            const topic = findTopicByHex(prev.bundle, prev.contextHex);
            if (topic) {
                const contentHTML = renderTopicContent(prev.bundle, topic);
                const windowEl = this._openWindow(prev.bundle, contentHTML, bundleHeaderLabel(prev.bundle));
                this._focusTopicLine(windowEl, this.currentLineNumber);
                if (this.onNavigate) { this.onNavigate(bundleTopicTitle(prev.bundle, topic)); }
            }
        } else {
            this.currentLineNumber = null;
            const contentHTML = renderBundleIndex(prev.bundle);
            this._openWindow(prev.bundle, contentHTML, bundleHeaderLabel(prev.bundle));
            if (this.onNavigate) { this.onNavigate("Index"); }
        }
        this._updateUrl();
    }

    _openWindow(bundle, contentHTML, caption) {
        const key = bundleWindowKey(bundle);
        const existing = this.openWindows.get(key);
        if (existing) {
            // Update content in existing window
            const viewport = existing.querySelector("[data-tv-viewport]");
            if (viewport) {
                viewport.innerHTML = contentHTML;
                viewport.scrollTop = 0;
                viewport.scrollLeft = 0;
            }
            const captionEl = existing.querySelector(".tv-window-caption");
            if (captionEl) {
                captionEl.textContent = caption;
            }
            this._bindTopicLinks(existing, bundle);
            highlightCodeExamples(existing);
            fillBorders();
            return existing;
        }

        // Close existing windows (without resetting navigation state).
        for (const [k, el] of this.openWindows) {
            if (this.dialogManager) { this.dialogManager.unregisterWindow("help:" + k); }
            el.remove();
        }
        this.openWindows.clear();

        const windowHTML = buildWindowHTML(bundle, contentHTML, caption);
        const template = document.createElement("template");
        template.innerHTML = windowHTML.trim();
        const windowEl = template.content.firstElementChild;
        this.desktop.appendChild(windowEl);
        this.openWindows.set(key, windowEl);
        this._initWindowWidgets(windowEl);
        this._bindTopicLinks(windowEl, bundle);
        this._bindCloseButton(windowEl, key);
        this._bindZoomButton(windowEl);
        if (this.dialogManager) { this.dialogManager.registerWindow("help:" + key, windowEl); }
        highlightCodeExamples(windowEl);
        fillBorders();
        fillDesktopPatterns();
        return windowEl;
    }

    _initWindowWidgets(windowEl) {
        const frames = windowEl.querySelectorAll("[data-tv-scroll-frame]");
        for (const frame of frames) {
            this.scrollbars.push(new TurboVisionScrollbar(frame));
        }
        this.resizers.push(new TurboVisionWindowResizer(windowEl));
    }

    _bindTopicLinks(windowEl, bundle) {
        windowEl.querySelectorAll("[data-tv-uhf-link], [data-tv-bundle-topic]").forEach((link) => {
            if (link.dataset.tvBundleBound === "1") { return; }
            link.dataset.tvBundleBound = "1";
            link.addEventListener("click", async (event) => {
                event.preventDefault();
                const sourceFile = link.dataset.tvSourceFile || "";
                const lineNumber = this._normalizeLineNumber(link.dataset.tvTopicLine);
                const topicRef = (link.dataset.tvBundleTopic || link.dataset.tvTopicAlias || "").trim();
                try {
                    if (sourceFile) {
                        await this.openSourceTopic(sourceFile, topicRef, lineNumber);
                    } else if (topicRef) {
                        this.showTopic(bundle, topicRef, lineNumber);
                    } else if (lineNumber) {
                        this._pushHistory();
                        this._focusTopicLine(windowEl, lineNumber);
                        this.currentLineNumber = lineNumber;
                        this._updateUrl();
                    } else {
                        this.showTopic(bundle, link.dataset.tvBundleTopic);
                    }
                } catch (error) {
                    console.error("Failed to open linked topic", error);
                }
            });
        });
        windowEl.querySelectorAll("[data-tv-nav]").forEach((link) => {
            if (link.dataset.tvBundleBound === "1") { return; }
            link.dataset.tvBundleBound = "1";
            link.addEventListener("click", (event) => {
                event.preventDefault();
                const action = (link.getAttribute("data-tv-nav") || "").toLowerCase();
                if (action === "back") {
                    this.goBack();
                } else if (action === "index") {
                    this.showIndex(bundle);
                } else if (action === "contents") {
                    this.showContents(bundle);
                }
            });
        });
        // Bind letter navigation links in index
        windowEl.querySelectorAll("a[data-letter]").forEach((link) => {
            if (link.dataset.tvBundleBound === "1") { return; }
            link.dataset.tvBundleBound = "1";
            link.addEventListener("click", (event) => {
                event.preventDefault();
                const letter = link.getAttribute("data-letter");
                const section = windowEl.querySelector(`#idx-${letter}`);
                if (section) {
                    section.scrollIntoView({ behavior: "smooth", block: "start" });
                }
            });
        });
    }

    _bindCloseButton(windowEl, key) {
        const closeBtn = windowEl.querySelector("[data-tv-bundle-close]");
        if (!closeBtn) { return; }
        closeBtn.addEventListener("click", (event) => {
            event.preventDefault();
            windowEl.remove();
            this.openWindows.delete(key);
            if (this.dialogManager) { this.dialogManager.unregisterWindow("help:" + key); }
            this.currentBundle = null;
            this.currentContextHex = null;
            this._clearUrl();
            fillBorders();
            fillDesktopPatterns();
            if (this.onNavigate) { this.onNavigate(""); }
        });
    }

    _bindZoomButton(windowEl) {
        const zoomBtn = windowEl.querySelector("[data-tv-bundle-zoom]");
        if (!zoomBtn) { return; }
        zoomBtn.addEventListener("click", (event) => {
            event.preventDefault();
            this.toggleZoom(windowEl);
        });
    }

    toggleZoom(windowEl) {
        if (!windowEl) {
            // Zoom the first open window
            const first = this.openWindows.values().next().value;
            if (!first) { return; }
            windowEl = first;
        }
        const isMax = windowEl.classList.toggle("is-maximized");
        const glyph = windowEl.querySelector("[data-tv-zoom-glyph]");
        if (glyph) {
            glyph.textContent = isMax ? "↓" : "↑";
        }
        fillBorders();
        fillDesktopPatterns();
    }

    close(key) {
        const existing = this.openWindows.get(key);
        if (existing) {
            existing.remove();
            this.openWindows.delete(key);
            if (this.onNavigate) { this.onNavigate(""); }
        }
    }

    closeAll() {
        for (const [key, el] of this.openWindows) {
            if (this.dialogManager) { this.dialogManager.unregisterWindow("help:" + key); }
            el.remove();
        }
        this.openWindows.clear();
        this.history = [];
        this.currentBundle = null;
        this.currentContextHex = null;
        this._clearUrl();
        if (this.onNavigate) { this.onNavigate(""); }
    }

    tile() {
        const wins = [...this.openWindows.values()];
        const docs = [...this.desktop.querySelectorAll(".tv-doc-window")];
        const dialogs = this._visibleDialogs();
        const all = [...wins, ...docs, ...dialogs];
        if (all.length === 0) { return; }
        const cell = TV.measureCells ? TV.measureCells() : { width: 9, height: 16 };
        const dw = this.desktop.clientWidth;
        const dh = this.desktop.clientHeight;
        const cols = Math.ceil(Math.sqrt(all.length));
        const rows = Math.ceil(all.length / cols);
        const wCols = Math.floor(dw / cell.width / cols);
        const wRows = Math.floor(dh / cell.height / rows);
        all.forEach((el, i) => {
            const col = i % cols;
            const row = Math.floor(i / cols);
            el.classList.remove("is-maximized");
            el.style.setProperty("--tv-window-left", `${col * wCols * cell.width}px`);
            el.style.setProperty("--tv-window-top", `${row * wRows * cell.height}px`);
            el.style.setProperty("--tv-window-cols", String(wCols));
            el.style.setProperty("--tv-window-rows", String(wRows));
            const g = el.querySelector("[data-tv-zoom-glyph]");
            if (g) { g.textContent = "↑"; }
        });
        fillBorders();
    }

    cascade() {
        const wins = [...this.openWindows.values()];
        const docs = [...this.desktop.querySelectorAll(".tv-doc-window")];
        const dialogs = this._visibleDialogs();
        const all = [...wins, ...docs, ...dialogs];
        if (all.length === 0) { return; }
        const cell = TV.measureCells ? TV.measureCells() : { width: 9, height: 16 };
        const dw = this.desktop.clientWidth;
        const dh = this.desktop.clientHeight;
        const baseCols = Math.floor(dw / cell.width * 0.75);
        const baseRows = Math.floor(dh / cell.height * 0.75);
        const step = 2; // cells offset per window
        all.forEach((el, i) => {
            el.classList.remove("is-maximized");
            el.style.setProperty("--tv-window-left", `${i * step * cell.width}px`);
            el.style.setProperty("--tv-window-top", `${i * step * cell.height}px`);
            el.style.setProperty("--tv-window-cols", String(baseCols));
            el.style.setProperty("--tv-window-rows", String(baseRows));
            const g = el.querySelector("[data-tv-zoom-glyph]");
            if (g) { g.textContent = "↑"; }
        });
        fillBorders();
    }

    _visibleDialogs() {
        const overlays = this.desktop.querySelectorAll(".tv-dialog-overlay:not([hidden])");
        const dialogs = [];
        for (const overlay of overlays) {
            const win = overlay.querySelector(".tv-dialog-window");
            if (win) { dialogs.push(win); }
        }
        return dialogs;
    }

    _clearUrl() {
        window.history.replaceState(null, "", window.location.pathname);
    }
}

// ── Catalog menu items ──────────────────────────────────────────────

function buildCatalogMenuItems(catalog) {
    if (!catalog.length) { return []; }

    // Group entries by their group name; preserve insertion order.
    const groups = new Map();   // group → [entry, …]
    const ungrouped = [];
    for (const entry of catalog) {
        const group = entry.group || "";
        if (!group) {
            ungrouped.push(entry);
        } else {
            if (!groups.has(group)) { groups.set(group, []); }
            groups.get(group).push(entry);
        }
    }

    const items = [];
    let needSep = false;

    // Ungrouped entries go directly into the top-level menu.
    for (const entry of ungrouped) {
        items.push(new TVButton({
            dialog: false,
            className: "tv-menu-popup-item",
            attrs: { type: "button", "data-tv-bundle-open": entry.file, "data-tv-bundle-label": bundleLoadingLabel(entry) },
            labelMarkup: escapeHtml(entry.name),
        }));
        needSep = true;
    }

    // Each group becomes a submenu.
    for (const [group, entries] of groups) {
        if (needSep) {
            items.push('<div class="tv-menu-popup-separator" aria-hidden="true">'
                + '<span class="tv-border-corner">├</span>'
                + '<span class="tv-border-fill" data-tv-border-fill="─"></span>'
                + '<span class="tv-border-corner">┤</span>'
                + '</div>');
        }
        const subItems = entries.map((entry) =>
            new TVButton({
                dialog: false,
                className: "tv-menu-popup-item",
                attrs: { type: "button", "data-tv-bundle-open": entry.file, "data-tv-bundle-label": bundleLoadingLabel(entry) },
                labelMarkup: escapeHtml(entry.name),
            })
        );
        const subPopup = new TVMenuBox({
            className: "tv-menu-popup tv-submenu-popup",
            attrs: { "data-tv-submenu-popup": true, hidden: true },
            items: subItems,
        }).renderMarkup();

        items.push(
            `<div class="tv-submenu-root" data-tv-submenu-root>`
            + `<button type="button" class="tv-menu-popup-item tv-submenu-toggle" data-tv-submenu-toggle>`
            + `${escapeHtml(group)}<span class="tv-submenu-arrow">►</span>`
            + `</button>`
            + subPopup
            + `</div>`
        );
        needSep = false;
    }

    return items;
}

function buildDocsMenuItems(docs) {
    if (!docs.length) { return []; }

    const groups = new Map();
    const ungrouped = [];
    for (const entry of docs) {
        const group = entry.group || "";
        if (!group) {
            ungrouped.push(entry);
        } else {
            if (!groups.has(group)) { groups.set(group, []); }
            groups.get(group).push(entry);
        }
    }

    const items = [];
    let needSep = false;

    for (const entry of ungrouped) {
        items.push(new TVButton({
            dialog: false,
            className: "tv-menu-popup-item",
            attrs: { type: "button", "data-tv-doc-open": entry.file },
            labelMarkup: escapeHtml(entry.name),
        }));
        needSep = true;
    }

    for (const [group, entries] of groups) {
        if (needSep) {
            items.push('<div class="tv-menu-popup-separator" aria-hidden="true">'
                + '<span class="tv-border-corner">├</span>'
                + '<span class="tv-border-fill" data-tv-border-fill="─"></span>'
                + '<span class="tv-border-corner">┤</span>'
                + '</div>');
        }
        const subItems = entries.map((entry) =>
            new TVButton({
                dialog: false,
                className: "tv-menu-popup-item",
                attrs: { type: "button", "data-tv-doc-open": entry.file },
                labelMarkup: escapeHtml(entry.name),
            })
        );
        const subPopup = new TVMenuBox({
            className: "tv-menu-popup tv-submenu-popup",
            attrs: { "data-tv-submenu-popup": true, hidden: true },
            items: subItems,
        }).renderMarkup();

        items.push(
            `<div class="tv-submenu-root" data-tv-submenu-root>`
            + `<button type="button" class="tv-menu-popup-item tv-submenu-toggle" data-tv-submenu-toggle>`
            + `${escapeHtml(group)}<span class="tv-submenu-arrow">►</span>`
            + `</button>`
            + subPopup
            + `</div>`
        );
        needSep = false;
    }

    return items;
}

function buildBundleContentsMenuItems(nodes) {
    if (!Array.isArray(nodes)) { return []; }
    const items = [];

    nodes.forEach((node) => {
        const label = String((node && node.label) || "").trim();
        if (!label) { return; }

        const childItems = buildBundleContentsMenuItems(node.children || []);
        const targetAttrs = buildBundleTargetDataset(node);
        const hasTarget = Object.keys(targetAttrs).length > 0;
        const labelMarkup = renderBundleMenuLabel(label, node && node.hotkey);

        if (childItems.length) {
            const subItems = [];
            if (hasTarget) {
                subItems.push(new TVButton({
                    dialog: false,
                    className: "tv-menu-popup-item",
                    attrs: { type: "button", "data-tv-menu-link": "1", ...targetAttrs },
                    labelMarkup,
                }));
                subItems.push('<div class="tv-menu-popup-separator" aria-hidden="true">'
                    + '<span class="tv-border-corner">├</span>'
                    + '<span class="tv-border-fill" data-tv-border-fill="─"></span>'
                    + '<span class="tv-border-corner">┤</span>'
                    + '</div>');
            }
            subItems.push(...childItems);
            const subPopup = new TVMenuBox({
                className: "tv-menu-popup tv-submenu-popup",
                attrs: { "data-tv-submenu-popup": true, hidden: true },
                items: subItems,
            }).renderMarkup();
            items.push(
                `<div class="tv-submenu-root" data-tv-submenu-root>`
                + `<button type="button" class="tv-menu-popup-item tv-submenu-toggle" data-tv-submenu-toggle>`
                + `${labelMarkup}<span class="tv-submenu-arrow">►</span>`
                + `</button>`
                + subPopup
                + `</div>`
            );
            return;
        }

        if (hasTarget) {
            items.push(new TVButton({
                dialog: false,
                className: "tv-menu-popup-item",
                attrs: { type: "button", "data-tv-menu-link": "1", ...targetAttrs },
                labelMarkup,
            }));
            return;
        }

        items.push(`<div class="tv-menu-popup-item is-disabled">${escapeHtml(label)}</div>`);
    });

    return items;
}

function renderBundleMenuLabel(label, hotkey = "") {
    const cleanLabel = String(label || "");
    const cleanHotkey = String(hotkey || "").trim();
    if (!cleanHotkey) {
        return escapeHtml(cleanLabel);
    }
    const matchIndex = cleanLabel.toLowerCase().indexOf(cleanHotkey.toLowerCase());
    if (matchIndex < 0) {
        return escapeHtml(cleanLabel);
    }
    const markedLabel = cleanLabel.slice(0, matchIndex)
        + "~" + cleanLabel[matchIndex] + "~"
        + cleanLabel.slice(matchIndex + 1);
    return renderHotkeyMarkup(markedLabel);
}

function buildBundleContentsMenuRoot(bundle) {
    const nodes = Array.isArray(bundle && bundle.contents) ? bundle.contents : [];
    if (!nodes.length) {
        return "";
    }

    const items = buildBundleContentsMenuItems(nodes);
    if (!items.length) {
        return "";
    }

    const popupHTML = new TVMenuBox({
        attrs: { "data-tv-menu-popup": true, hidden: true },
        items,
    }).renderMarkup();
    const toggle = new TVButton({
        dialog: false,
        className: "tv-menu-item tv-menu-button",
        attrs: { type: "button", "data-tv-menu-toggle": true, "aria-haspopup": "true", "aria-expanded": "false" },
        labelMarkup: renderHotkeyMarkup(nodes.some((node) => node && node.hotkey) ? "~M~enu" : "~C~ontents"),
    }).renderMarkup();

    return [
        `<div class="tv-menu-root" data-tv-menu-root data-tv-bundle-menu-root>`,
        toggle,
        popupHTML,
        `</div>`,
    ].join("");
}

// ── Minimal Markdown → HTML renderer ────────────────────────────────

function renderMarkdown(md) {
    const lines = md.replace(/\r\n?/g, "\n").split("\n");
    const html = [];
    let inCode = false;
    let codeLines = null;
    let inList = false;
    let listTag = "";
    let inTable = false;

    function inlineMarkup(text) {
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
            .replace(/\*([^*]+)\*/g, '<i>$1</i>')
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    }

    function closeList() {
        if (inList) { html.push(`</${listTag}>`); inList = false; }
    }
    function closeTable() {
        if (inTable) { html.push("</tbody></table>"); inTable = false; }
    }

    function isTableRow(line) { return line.trim().startsWith("|") && line.trim().endsWith("|"); }
    function isSepRow(line) { return /^\|[-:\s|]+\|$/.test(line.trim()); }
    function parseRow(line, tag) {
        const cells = line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|");
        return "<tr>" + cells.map((c) => `<${tag}>${inlineMarkup(c.trim())}</${tag}>`).join("") + "</tr>";
    }

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        // Fenced code block
        if (line.startsWith("```") ) {
            if (inCode) {
                // End code block
                html.push("<pre>" + codeLines.join("\n") + "</pre>");
                codeLines = null;
                inCode = false;
            } else {
                closeList(); closeTable();
                codeLines = [];
                inCode = true;
            }
            continue;
        }
        if (inCode) {
            codeLines.push(line.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"));
            continue;
        }
        // Table: header row followed by separator row
        if (!inTable && isTableRow(line) && i + 1 < lines.length && isSepRow(lines[i + 1])) {
            closeList();
            html.push("<table>");
            html.push("<thead>" + parseRow(line, "th") + "</thead>");
            html.push("<tbody>");
            inTable = true;
            i++; // skip separator row
            continue;
        }
        if (inTable) {
            if (isTableRow(line)) { html.push(parseRow(line, "td")); continue; }
            closeTable();
        }
        // Blank → close list, add empty paragraph for spacing
        if (!line.trim()) { closeList(); html.push("<p></p>"); continue; }
        // Headings
        const hMatch = line.match(/^(#{1,6})\s+(.*)/);
        if (hMatch) {
            closeList();
            const level = hMatch[1].length;
            html.push(`<h${level}>${inlineMarkup(hMatch[2])}</h${level}>`);
            continue;
        }
        // Horizontal rule
        if (/^[-*_]{3,}\s*$/.test(line)) { closeList(); html.push("<hr>"); continue; }
        // Unordered list
        const ulMatch = line.match(/^(\s*)[-*+]\s+(.*)/);
        if (ulMatch) {
            if (!inList || listTag !== "ul") { closeList(); html.push("<ul>"); inList = true; listTag = "ul"; }
            html.push(`<li>${inlineMarkup(ulMatch[2])}</li>`);
            continue;
        }
        // Ordered list
        const olMatch = line.match(/^(\s*)\d+\.\s+(.*)/);
        if (olMatch) {
            if (!inList || listTag !== "ol") { closeList(); html.push("<ol>"); inList = true; listTag = "ol"; }
            html.push(`<li>${inlineMarkup(olMatch[2])}</li>`);
            continue;
        }
        // List continuation: indented line appended to last <li>
        if (inList && /^\s{2,}/.test(line)) {
            const last = html.length - 1;
            if (last >= 0 && html[last].startsWith("<li>")) {
                html[last] = html[last].replace(/<\/li>$/, ` ${inlineMarkup(line.trim())}</li>`);
                continue;
            }
        }
        // Regular paragraph line
        closeList();
        html.push(`<p>${inlineMarkup(line)}</p>`);
    }
    if (inCode && codeLines) {
        html.push("<pre>" + codeLines.join("\n") + "</pre>");
    }
    closeList();
    closeTable();
    return html.join("");
}

// ── Menu bar for bundle page ────────────────────────────────────────

function buildBundleMenuBar(catalog, activeBundle = null) {
    const menuBar = document.querySelector("[data-tv-menu-bar]");
    if (!menuBar) { return; }

    // ≡ system menu
    const sysPopupItems = [
        { type: "dialog", dialog: "about", label: "~A~bout" },
        { type: "dialog", dialog: "calendar", label: "Ca~l~endar" },
        { type: "dialog", dialog: "ascii", label: "Ascii ~T~able" },
        { type: "dialog", dialog: "calc", label: "~C~alculator" },
        { type: "dialog", dialog: "colors", label: "C~o~lors" },
        { type: "separator" },
        { type: "submenu", label: "~S~creen saver", items: [
            { type: "saver", mode: "stars", label: "~S~tars" },
            { type: "saver", mode: "bounce", label: "~B~ounce" },
            { type: "saver", mode: "clock", label: "Cloc~k~" },
            { type: "saver", mode: "matrix", label: "~M~atrix" },
        ] },
        { type: "separator" },
        { type: "theme", theme: "light", label: "~L~ight Theme" },
        { type: "theme", theme: "dark", label: "~D~ark Theme" },
        { type: "theme", theme: "auto", label: "A~u~to Theme" },
    ];
    const sysPopupHTML = new TVMenuBox({
        attrs: { "data-tv-menu-popup": true, hidden: true },
        items: sysPopupItems.map((entry) => {
            if (entry.type === "separator") {
                return '<div class="tv-menu-popup-separator" aria-hidden="true">'
                    + '<span class="tv-border-corner">├</span>'
                    + '<span class="tv-border-fill" data-tv-border-fill="─"></span>'
                    + '<span class="tv-border-corner">┤</span>'
                    + '</div>';
            }
            if (entry.type === "submenu") {
                const subItems = entry.items.map((sub) => new TVButton({
                    dialog: false,
                    className: "tv-menu-popup-item",
                    attrs: { type: "button", "data-tv-saver-start": sub.mode },
                    labelMarkup: renderHotkeyMarkup(sub.label),
                }));
                const subPopup = new TVMenuBox({
                    className: "tv-menu-popup tv-submenu-popup",
                    attrs: { "data-tv-submenu-popup": true, hidden: true },
                    items: subItems,
                }).renderMarkup();
                return `<div class="tv-submenu-root" data-tv-submenu-root>`
                    + `<button type="button" class="tv-menu-popup-item tv-submenu-toggle" data-tv-submenu-toggle>`
                    + `${renderHotkeyMarkup(entry.label)}<span class="tv-submenu-arrow">►</span>`
                    + `</button>`
                    + subPopup
                    + `</div>`;
            }
            const attrs = entry.type === "theme"
                ? { type: "button", "data-tv-theme-set": entry.theme }
                : entry.type === "saver"
                    ? { type: "button", "data-tv-saver-start": entry.mode }
                    : { type: "button", "data-tv-dialog-open": entry.dialog };
            return new TVButton({
                dialog: false,
                className: "tv-menu-popup-item",
                attrs,
                labelMarkup: renderHotkeyMarkup(entry.label),
            });
        }),
    }).renderMarkup();
    const sysToggle = new TVButton({
        dialog: false,
        className: "tv-menu-item tv-menu-button",
        attrs: { type: "button", "data-tv-menu-toggle": true, "aria-haspopup": "true", "aria-expanded": "false" },
        labelMarkup: renderHotkeyMarkup("~≡~"),
    }).renderMarkup();

    // File menu with catalog entries
    const filePopupHTML = new TVMenuBox({
        attrs: { "data-tv-menu-popup": true, hidden: true },
        items: buildCatalogMenuItems(catalog),
    }).renderMarkup();
    const fileToggle = new TVButton({
        dialog: false,
        className: "tv-menu-item tv-menu-button",
        attrs: { type: "button", "data-tv-menu-toggle": true, "aria-haspopup": "true", "aria-expanded": "false" },
        labelMarkup: renderHotkeyMarkup("~H~elp Files"),
    }).renderMarkup();

    // Docs menu with documentation markdown files
    const docsItems = buildDocsMenuItems(docsCatalogData || []);
    const docsPopupHTML = new TVMenuBox({
        attrs: { "data-tv-menu-popup": true, hidden: true },
        items: docsItems,
    }).renderMarkup();
    const docsToggle = new TVButton({
        dialog: false,
        className: "tv-menu-item tv-menu-button",
        attrs: { type: "button", "data-tv-menu-toggle": true, "aria-haspopup": "true", "aria-expanded": "false" },
        labelMarkup: renderHotkeyMarkup("~D~ocs"),
    }).renderMarkup();

    // Windows menu (TV standard)
    const winPopupItems = [
        { cmd: "tile", label: "~T~ile", hotkey: "" },
        { cmd: "cascade", label: "C~a~scade", hotkey: "" },
        { cmd: "list", label: "Window ~L~ist", hotkey: "Alt-0" },
        { cmd: "zoom", label: "~Z~oom", hotkey: "F5" },
        { cmd: "close", label: "~C~lose", hotkey: "Alt-F3" },
    ];
    const winPopupHTML = new TVMenuBox({
        attrs: { "data-tv-menu-popup": true, hidden: true },
        items: winPopupItems.map((entry) =>
            new TVButton({
                dialog: false,
                className: "tv-menu-popup-item",
                attrs: { type: "button", "data-tv-window-cmd": entry.cmd },
                labelMarkup: renderHotkeyMarkup(entry.label) +
                    `<span class="tv-menu-hotkey">${escapeHtml(entry.hotkey)}</span>`,
            })
        ),
    }).renderMarkup();
    const winToggle = new TVButton({
        dialog: false,
        className: "tv-menu-item tv-menu-button",
        attrs: { type: "button", "data-tv-menu-toggle": true, "aria-haspopup": "true", "aria-expanded": "false" },
        labelMarkup: renderHotkeyMarkup("~W~indows"),
    }).renderMarkup();

    // Games menu
    const gamesPopupItems = [
        { type: "dialog", dialog: "breakout", label: "~B~reakOut" },
        { type: "dialog", dialog: "lines", label: "~L~ines" },
        { type: "dialog", dialog: "mines", label: "~M~ines" },
        { type: "dialog", dialog: "puzzle", label: "~P~uzzle" },
        { type: "dialog", dialog: "reversi", label: "~R~eversi" },
        { type: "dialog", dialog: "snake", label: "S~n~ake" },
        { type: "dialog", dialog: "sokoban", label: "~S~okoban" },
        { type: "dialog", dialog: "tetris", label: "~T~etris" },
    ];
    const gamesPopupHTML = new TVMenuBox({
        attrs: { "data-tv-menu-popup": true, hidden: true },
        items: gamesPopupItems.map((entry) =>
            new TVButton({
                dialog: false,
                className: "tv-menu-popup-item",
                attrs: { type: "button", "data-tv-dialog-open": entry.dialog },
                labelMarkup: renderHotkeyMarkup(entry.label),
            })
        ),
    }).renderMarkup();
    const gamesToggle = new TVButton({
        dialog: false,
        className: "tv-menu-item tv-menu-button",
        attrs: { type: "button", "data-tv-menu-toggle": true, "aria-haspopup": "true", "aria-expanded": "false" },
        labelMarkup: renderHotkeyMarkup("~G~ames"),
    }).renderMarkup();

    const bundleContentsRootHTML = buildBundleContentsMenuRoot(activeBundle);

    menuBar.innerHTML = [
        `<nav class="tv-menu-items">`,
        `<div class="tv-menu-root" data-tv-menu-root>`,
        sysToggle,
        sysPopupHTML,
        `</div>`,
        `<div class="tv-menu-root" data-tv-menu-root>`,
        fileToggle,
        filePopupHTML,
        `</div>`,
        `<div class="tv-menu-root" data-tv-menu-root>`,
        docsToggle,
        docsPopupHTML,
        `</div>`,
        `<div class="tv-menu-root" data-tv-menu-root>`,
        gamesToggle,
        gamesPopupHTML,
        `</div>`,
        `<div class="tv-menu-root" data-tv-menu-root>`,
        winToggle,
        winPopupHTML,
        `</div>`,
        bundleContentsRootHTML ? `<div class="tv-menu-separator" aria-hidden="true">|</div>` : ``,
        bundleContentsRootHTML,
        `</nav>`,
        `<div class="tv-menu-clock" data-tv-clock>00:00:00</div>`,
    ].join("");
}

// ── Bundle application ──────────────────────────────────────────────

class TVBundleApp {
    constructor() {
        this.desktop = null;
        this.windowManager = null;
        this.dialogManager = null;
        this._menuBundleKey = "";
        this._menuGlobalsBound = false;
        this._closeMenus = null;
    }

    start() {
        // Theme
        document.documentElement.classList.add("tv-js");
        applyThemePreset(readStoredThemePreset(), false);
        const storedPalette = readStoredColorPalette();
        if (storedPalette) {
            applyColorPalette(storedPalette, false);
        } else {
            TV.setActiveColorPalette(buildPaletteFromCurrentStyle());
        }

        this.desktop = document.querySelector("[data-tv-bundle-desktop]");
        if (!this.desktop) { return; }

        this.dialogManager = new TVDialogManager(this.desktop);
        this.dialogManager.onChange = () => this._updateStatusLine("");
        this._updateStatusLine("");

        // Register standard dialogs
        this._registerDialog("about", () => new TVAboutDialog(this.desktop));
        this._registerDialog("puzzle", () => new TVPuzzleDialog(this.desktop));
        this._registerDialog("calendar", () => new TVCalendarDialog(this.desktop));
        this._registerDialog("ascii", () => new TVAsciiTableDialog(this.desktop));
        this._registerDialog("calc", () => new TVCalculatorDialog(this.desktop));
        this._registerDialog("colors", () => new TVColorsDialog(this.desktop));
        this._registerDialog("tetris", () => new TVTetrisDialog(this.desktop));
        this._registerDialog("mines", () => new TVMinesDialog(this.desktop));
        this._registerDialog("breakout", () => new TVBreakOutDialog(this.desktop));
        this._registerDialog("sokoban", () => new TVSokobanDialog(this.desktop));
        this._registerDialog("lines", () => new TVLinesDialog(this.desktop));
        this._registerDialog("reversi", () => new TVReversiDialog(this.desktop));
        this._registerDialog("snake", () => new TVSnakeDialog(this.desktop));
        this._registerBundleSearch();
        this.dialogManager.applyActiveStates();

        // Fetch catalog dynamically and build menu
        this._loadCatalog();

        // Layout
        fillBorders();
        fillDesktopPatterns();
        updateClocks();
        window.setInterval(updateClocks, 1000);
        window.addEventListener("resize", fillBorders, { passive: true });
        window.addEventListener("resize", fillDesktopPatterns, { passive: true });
        window.addEventListener("load", fillBorders, { passive: true });
        window.addEventListener("load", fillDesktopPatterns, { passive: true });

        this.windowManager = new BundleWindowManager(this.desktop, (hint) => {
            this._updateStatusLine(hint);
            this._syncBundleMenu();
        });
        this.windowManager.dialogManager = this.dialogManager;
    }

    _updateStatusLine(hint) {
        const hasHelpWindow = this.windowManager && this.windowManager.openWindows.size > 0;
        const currentBundle = this.windowManager ? this.windowManager.currentBundle : null;
        const statusLine = document.querySelector("[data-tv-status-line]");
        if (!statusLine) { return; }
        const items = [];
        if (hasHelpWindow) {
            items.push(new TVButton({
                dialog: false,
                className: "tv-status-item",
                attrs: { type: "button", "data-tv-bundle-back": true },
                labelMarkup: renderHotkeyMarkup("~B~ack"),
            }).renderMarkup());
            if (currentBundle && bundleCanShowIndex(currentBundle)) {
                items.push(new TVButton({
                    dialog: false,
                    className: "tv-status-item",
                    attrs: { type: "button", "data-tv-bundle-index": true },
                    labelMarkup: renderHotkeyMarkup("~I~ndex"),
                }).renderMarkup());
            }
            if (currentBundle && bundleCanShowContents(currentBundle)) {
                items.push(new TVButton({
                    dialog: false,
                    className: "tv-status-item",
                    attrs: { type: "button", "data-tv-bundle-contents": true },
                    labelMarkup: renderHotkeyMarkup("C~o~ntent"),
                }).renderMarkup());
            }
            items.push(new TVButton({
                dialog: false,
                className: "tv-status-item",
                attrs: { type: "button", "data-tv-dialog-open": "search" },
                labelMarkup: renderHotkeyMarkup("~F3~ Search"),
            }).renderMarkup());
            items.push(new TVButton({
                dialog: false,
                className: "tv-status-item",
                attrs: { type: "button", "data-tv-bundle-close-all": true },
                labelMarkup: renderHotkeyMarkup("~Alt-F3~ Close"),
            }).renderMarkup());
        }
        items.push(new TVButton({
            dialog: false,
            className: "tv-status-item",
            attrs: { type: "button", "data-tv-dialog-open": "about" },
            labelMarkup: renderHotkeyMarkup("~F1~ About"),
        }).renderMarkup());
        items.push(`<span class="tv-status-hint" data-tv-status-hint>${escapeHtml(hint || "THelpViewer")}</span>`);
        items.push(`<a class="tv-status-link" href="https://github.com/mariolacko/THelpViewer" target="_blank" rel="noopener">GitHub</a>`);
        statusLine.innerHTML = items.join("");
        this._bindStatusButtons();
    }

    _bindStatusButtons() {
        const statusLine = document.querySelector("[data-tv-status-line]");
        if (!statusLine) { return; }
        const closeAllBtn = statusLine.querySelector("[data-tv-bundle-close-all]");
        if (closeAllBtn) {
            closeAllBtn.addEventListener("click", (event) => {
                event.preventDefault();
                this.windowManager.closeAll();
                fillBorders();
                fillDesktopPatterns();
            });
        }
        const backBtn = statusLine.querySelector("[data-tv-bundle-back]");
        if (backBtn) {
            backBtn.addEventListener("click", (event) => {
                event.preventDefault();
                if (this.windowManager) { this.windowManager.goBack(); }
            });
        }
        const indexBtn = statusLine.querySelector("[data-tv-bundle-index]");
        if (indexBtn) {
            indexBtn.addEventListener("click", (event) => {
                event.preventDefault();
                if (this.windowManager && this.windowManager.currentBundle) {
                    this.windowManager.showIndex(this.windowManager.currentBundle);
                }
            });
        }
        const contentsBtn = statusLine.querySelector("[data-tv-bundle-contents]");
        if (contentsBtn) {
            contentsBtn.addEventListener("click", (event) => {
                event.preventDefault();
                if (this.windowManager && this.windowManager.currentBundle) {
                    this.windowManager.showContents(this.windowManager.currentBundle);
                }
            });
        }
        statusLine.querySelectorAll("[data-tv-dialog-open]").forEach((el) => {
            el.addEventListener("click", (event) => {
                event.preventDefault();
                this.dialogManager.open(el.getAttribute("data-tv-dialog-open") || "");
            });
        });
    }

    _registerDialog(name, factory) {
        try {
            const dialog = factory();
            if (dialog) {
                this.dialogManager.register(name, dialog);
                return dialog;
            }
        } catch (error) {
            console.error(`Failed to initialize dialog: ${name}`, error);
        }
        return null;
    }

    _registerBundleSearch() {
        const searchDialog = this._registerDialog("search", () => new TVSearchDialog(this.desktop));
        if (!searchDialog) { return; }
        this.searchDialog = searchDialog;
        // Provide empty search data initially
        searchDialog.searchData = { topics: [] };
        // Override openSelected to navigate within bundle viewer
        const self = this;
        searchDialog.openSelected = function () {
            if (this.selectedIndex < 0 || this.selectedIndex >= this.matches.length) {
                return;
            }
            const match = this.matches[this.selectedIndex];
            this.close();
            if (self.windowManager && self.windowManager.currentBundle) {
                self.windowManager.showTopic(self.windowManager.currentBundle, match.context_hex);
            }
        };
    }

    _updateSearchData(bundle) {
        if (this.searchDialog && bundle) {
            this.searchDialog.searchData = { topics: buildUhfSearchIndex(bundle) };
        }
    }

    _collectWindowListItems() {
        const items = [];
        if (this.windowManager) {
            for (const [key, el] of this.windowManager.openWindows) {
                const caption = el.querySelector(".tv-window-caption");
                items.push({ label: caption ? caption.textContent : key, type: "window", key, element: el });
            }
        }
        this.desktop.querySelectorAll(".tv-doc-window").forEach((el) => {
            const caption = el.querySelector(".tv-window-caption");
            items.push({ label: caption ? caption.textContent : "Document", type: "doc", element: el });
        });
        if (this.dialogManager) {
            this.dialogManager.dialogs.forEach((dialog, name) => {
                if (dialog && dialog.isOpen()) {
                    const captionEl = dialog.dialog ? dialog.dialog.querySelector(".tv-dialog-title-text") : null;
                    items.push({
                        label: captionEl ? captionEl.textContent : name,
                        type: "dialog",
                        key: name,
                    });
                }
            });
        }
        return items;
    }

    _showWindowList() {
        let items = this._collectWindowListItems();
        if (items.length === 0) { return; }

        const { TVDialog } = TV;

        const renderItems = (list, selectedIdx) =>
            list.map((item, i) =>
                `<button class="tv-winlist-item${i === selectedIdx ? ' is-selected' : ''}" data-tv-winlist-idx="${i}" type="button">${escapeHtml(item.label)}</button>`
            ).join("");

        const dialog = new TVDialog({
            desktop: this.desktop,
            windowClass: "tv-winlist-window",
            bodyClass: "tv-winlist-body",
            ariaLabel: "Window List",
            title: "Window List",
            closeAttrs: {
                "data-tv-winlist-close": true,
                "aria-label": "Close window list",
            },
            bodyMarkup: '<div class="tv-winlist-items"></div>',
            footerMarkup: TVDialog.footerMarkup(),
            width: "40ch",
            height: "min(14em, calc(100% - 2em))",
        });

        const itemsContainer = dialog.query(".tv-winlist-items");
        let selectedIdx = 0;

        const refresh = () => {
            items = this._collectWindowListItems();
            if (selectedIdx >= items.length) { selectedIdx = Math.max(0, items.length - 1); }
            if (itemsContainer) {
                itemsContainer.innerHTML = renderItems(items, selectedIdx);
            }
        };

        const updateSelection = () => {
            if (itemsContainer) {
                itemsContainer.querySelectorAll(".tv-winlist-item").forEach((el, i) => {
                    el.classList.toggle("is-selected", i === selectedIdx);
                });
            }
        };

        const observer = new MutationObserver(() => {
            if (dialog.isOpen()) { refresh(); }
        });
        observer.observe(this.desktop, { childList: true });

        if (this.dialogManager) {
            this.dialogManager.register("windowlist", dialog);
        }

        const cleanup = () => {
            observer.disconnect();
            dialog.close();
            dialog.overlay.remove();
            if (this.dialogManager) {
                this.dialogManager.dialogs.delete("windowlist");
            }
            document.removeEventListener("keydown", onKey);
        };

        dialog.bindCommonClose(cleanup);
        dialog.bindDrag();

        const activate = (idx) => {
            const item = items[idx];
            if (!item) { return; }
            if (item.type === "dialog" && this.dialogManager) {
                this.dialogManager.bringToFront(item.key);
            } else if ((item.type === "window" || item.type === "doc") && item.element) {
                this.desktop.appendChild(item.element);
                updateWindowFrameState(item.element, true);
            }
            cleanup();
        };

        const onKey = (event) => {
            if (!dialog.isOpen()) { return; }
            if (event.key === "Escape") { event.preventDefault(); cleanup(); return; }
            if (event.key === "ArrowDown") { event.preventDefault(); selectedIdx = (selectedIdx + 1) % items.length; updateSelection(); return; }
            if (event.key === "ArrowUp") { event.preventDefault(); selectedIdx = (selectedIdx - 1 + items.length) % items.length; updateSelection(); return; }
            if (event.key === "Enter") { event.preventDefault(); activate(selectedIdx); return; }
        };
        document.addEventListener("keydown", onKey);

        dialog.overlay.addEventListener("click", (event) => {
            const btn = event.target.closest("[data-tv-winlist-idx]");
            if (btn) {
                activate(parseInt(btn.dataset.tvWinlistIdx, 10));
            }
        });

        refresh();
        dialog.open();
    }

    async _loadCatalog() {
        // Load both help and docs catalogs in parallel.
        const [helpResp, docsResp] = await Promise.allSettled([
            fetch(CATALOG_FILE),
            fetch(DOCS_CATALOG_FILE),
        ]);

        if (helpResp.status === "fulfilled" && helpResp.value.ok) {
            catalogData = await helpResp.value.json();
            if (!Array.isArray(catalogData)) { catalogData = []; }
        } else {
            catalogData = [];
        }

        if (docsResp.status === "fulfilled" && docsResp.value.ok) {
            docsCatalogData = await docsResp.value.json();
            if (!Array.isArray(docsCatalogData)) { docsCatalogData = []; }
        } else {
            docsCatalogData = [];
        }
        buildBundleMenuBar(catalogData, null);
        fillBorders();
        this._bindMenus();
        this._showWelcome();
        this._handleUrlParams();
    }

    _syncBundleMenu() {
        if (!Array.isArray(catalogData)) { return; }
        const currentBundle = this.windowManager ? this.windowManager.currentBundle : null;
        const hasContentsMenu = !!(currentBundle && Array.isArray(currentBundle.contents) && currentBundle.contents.length);
        const nextKey = hasContentsMenu ? bundleWindowKey(currentBundle) : "";
        if (nextKey === this._menuBundleKey) {
            return;
        }
        this._menuBundleKey = nextKey;
        buildBundleMenuBar(catalogData, hasContentsMenu ? currentBundle : null);
        fillBorders();
        this._bindMenus();
    }

    /** Read ?file=, ?topic=, ?line=, ?search=, ?docs= from the URL and act on them. */
    async _handleUrlParams() {
        const params = new URLSearchParams(window.location.search);
        const fileParam = params.get("file");
        const docsParam = params.get("docs");

        // Handle ?docs= independently of ?file=
        if (docsParam && docsCatalogData) {
            const docEntry = docsCatalogData.find(
                (e) => e.file === docsParam || e.name === docsParam
            );
            if (docEntry) {
                this.dialogManager.close("welcome");
                try {
                    const resp = await fetch(DOCS_DIR + docEntry.file);
                    if (resp.ok) {
                        const md = await resp.text();
                        this._openDocWindow(docEntry.file, md);
                    }
                } catch (err) {
                    console.error(`Failed to load doc from URL: ${docEntry.file}`, err);
                }
                if (!fileParam) { return; }
            }
        }

        if (!fileParam || !catalogData) { return; }

        // Find matching catalog entry (by file path or by name).
        const entry = catalogData.find(
            (e) => e.file === fileParam || e.name === fileParam
        );
        if (!entry) { return; }

        // Load bundle.
        const loadingDialog = new TVLoadingDialog(this.desktop);
        loadingDialog.show(bundleLoadingLabel(entry));
        try {
            const bundle = await loadBundle(entry.file, {
                onProgress: (r, t) => loadingDialog.update(r, t),
                signal: loadingDialog.signal,
            });
            loadingDialog.destroy();
            this.dialogManager.close("welcome");
            this._updateSearchData(bundle);

            const topicParam = params.get("topic");
            const lineParam = params.get("line");
            const searchParam = params.get("search");

            if (topicParam) {
                this.windowManager.showTopic(bundle, topicParam, lineParam);
            } else if (lineParam) {
                const fallbackTopic = bundleHelpTopicRef(bundle);
                if (fallbackTopic) {
                    this.windowManager.showTopic(bundle, fallbackTopic, lineParam);
                } else {
                    this.windowManager.showIndex(bundle);
                }
            } else {
                this.windowManager.showIndex(bundle);
            }

            if (searchParam && this.searchDialog) {
                this.searchDialog.searchData = { topics: buildUhfSearchIndex(bundle) };
                this.dialogManager.open("search");
                const input = this.searchDialog.query("input[type=text]");
                if (input) {
                    input.value = searchParam;
                    input.dispatchEvent(new Event("input", { bubbles: true }));
                }
            }
        } catch (error) {
            loadingDialog.destroy();
            if (error.name !== "AbortError") {
                console.error(`Failed to load bundle from URL param: ${entry.file}`, error);
            }
        }
    }

    _openDocWindow(filename, markdownText) {
        const htmlContent = renderMarkdown(markdownText);
        const title = filename.replace(/\.md$/i, "").replace(/_/g, " ");
        const contentHTML = `<div class="tv-document tv-doc-document">${htmlContent}</div>`;
        const w = { cols: 78, rows: 24, min_cols: 40, min_rows: 8 };
        const style = `--tv-window-cols:${w.cols}; --tv-window-rows:${w.rows}; --tv-window-min-cols:${w.min_cols}; --tv-window-min-rows:${w.min_rows};`;
        const windowHTML = [
            `<main class="tv-window tv-doc-window" data-tv-window style="${style}">`,
            `<div class="tv-shell">`,
            `<div class="tv-border-row tv-border-top" data-tv-move-handle>`,
            `<span class="tv-border-corner" aria-hidden="true">╔</span>`,
            `<a class="tv-close-control" data-tv-close-button href="#" aria-label="Close window">[<span class="tv-close-glyph" data-tv-close-glyph>■</span>]</a>`,
            `<span class="tv-border-fill" data-tv-border-fill="═" aria-hidden="true"></span>`,
            `<div class="tv-window-caption">${escapeHtml(title)}</div>`,
            `<span class="tv-border-fill" data-tv-border-fill="═" aria-hidden="true"></span>`,
            `<a class="tv-zoom-control" href="#" aria-label="Zoom window">[<span class="tv-zoom-glyph" data-tv-zoom-glyph>↑</span>]</a>`,
            `<span class="tv-border-corner" aria-hidden="true">╗</span>`,
            `</div>`,
            `<div class="tv-client-row">`,
            `<span class="tv-border-side tv-border-side-left" data-tv-border-side="║" aria-hidden="true"></span>`,
            `<div class="tv-frame">`,
            `<div class="tv-scroll-shell" data-tv-scroll-frame>`,
            `<div class="tv-viewport" data-tv-viewport>`,
            contentHTML,
            `</div>`,
            `</div>`,
            `</div>`,
            renderScrollbar("y"),
            `<div class="tv-bottom-bar">`,
            `<span class="tv-scroll-corner tv-scroll-corner-left" aria-hidden="true">╚</span>`,
            renderScrollbar("x"),
            `<button type="button" class="tv-grow-handle" data-tv-resize-handle aria-label="Resize window">─┘</button>`,
            `</div>`,
            `</div>`,
            `</div>`,
            `</main>`,
        ].join("\n");

        // Close previous doc windows
        this.desktop.querySelectorAll(".tv-doc-window").forEach((el) => {
            if (this.dialogManager) { this.dialogManager.unregisterWindow("docs"); }
            el.remove();
        });

        const template = document.createElement("template");
        template.innerHTML = windowHTML.trim();
        const windowEl = template.content.firstElementChild;
        this.desktop.appendChild(windowEl);

        // Register with window manager for focus/z-index management
        if (this.dialogManager) {
            this.dialogManager.registerWindow("docs", windowEl);
        }

        // Update URL with ?docs= parameter
        const docsUrl = new URL(window.location);
        docsUrl.searchParams.set("docs", filename);
        window.history.replaceState(null, "", docsUrl);

        // Init widgets
        const frames = windowEl.querySelectorAll("[data-tv-scroll-frame]");
        for (const frame of frames) {
            new TurboVisionScrollbar(frame);
        }
        new TurboVisionWindowResizer(windowEl);

        // Close button
        const closeBtn = windowEl.querySelector("[data-tv-close-button]");
        if (closeBtn) {
            closeBtn.addEventListener("click", (e) => {
                e.preventDefault();
                if (this.dialogManager) { this.dialogManager.unregisterWindow("docs"); }
                windowEl.remove();
                // Remove ?docs= from URL
                const closeUrl = new URL(window.location);
                closeUrl.searchParams.delete("docs");
                window.history.replaceState(null, "", closeUrl);
                fillBorders();
                fillDesktopPatterns();
            });
        }
        // Zoom
        const zoomBtn = windowEl.querySelector(".tv-zoom-control");
        if (zoomBtn) {
            zoomBtn.addEventListener("click", (e) => {
                e.preventDefault();
                const isMax = windowEl.classList.toggle("is-maximized");
                const glyph = windowEl.querySelector("[data-tv-zoom-glyph]");
                if (glyph) { glyph.textContent = isMax ? "↓" : "↑"; }
                fillBorders();
                fillDesktopPatterns();
            });
        }

        // Intercept .md links to open in-viewer instead of navigating
        const self = this;
        const baseDir = filename.includes("/") ? filename.replace(/[^/]+$/, "") : "";
        windowEl.querySelectorAll("a[href]").forEach((link) => {
            const href = link.getAttribute("href");
            if (href && href.endsWith(".md")) {
                link.addEventListener("click", async (e) => {
                    e.preventDefault();
                    // Resolve relative path and normalize ../
                    const raw = baseDir ? baseDir + decodeURIComponent(href) : decodeURIComponent(href);
                    const parts = raw.split("/");
                    const normalized = [];
                    for (const p of parts) {
                        if (p === "..") { normalized.pop(); }
                        else if (p && p !== ".") { normalized.push(p); }
                    }
                    const resolved = normalized.join("/");
                    try {
                        const resp = await fetch(DOCS_DIR + encodeURI(resolved));
                        if (!resp.ok) { throw new Error(`HTTP ${resp.status}`); }
                        const md = await resp.text();
                        self._openDocWindow(resolved, md);
                    } catch (error) {
                        console.error(`Failed to load doc ${resolved}:`, error);
                    }
                });
            }
        });

        fillBorders();
        fillDesktopPatterns();
    }

    _showWelcome() {
        const {
            TVDialog,
            TVStaticText,
            TVGroup,
            TVButton: TVBtn,
        } = TV;
        const welcomeBody = new TVGroup({
            w: 30, h: 9,
            children: [
                new TVStaticText({ x: 0, y: 1, w: 30, align: "center", title: true, text: "THelpViewer" }),
                new TVStaticText({ x: 0, y: 3, w: 30, align: "center", text: "Select a help file from the" }),
                new TVStaticText({ x: 0, y: 4, w: 30, align: "center", text: "File menu to get started." }),
                new TVStaticText({ x: 0, y: 6, w: 30, align: "center", text: `${Array.isArray(catalogData) ? catalogData.length : 0} help file(s) available.` }),
                new TVButton({ x: 10, y: 8, w: 10, className: "is-default", attrs: { "data-tv-welcome-ok": true }, label: '~O~K' }),
            ],
        }).renderMarkup();
        const dialog = new TVDialog({
            desktop: this.desktop,
            ariaLabel: "Welcome",
            title: "Welcome",
            closeAttrs: {
                "data-tv-about-close": true,
                "aria-label": "Close welcome dialog",
            },
            bodyMarkup: welcomeBody,
            footerMarkup: TVDialog.footerMarkup(),
            width: "34ch",
            height: "min(12em, calc(100% - 2em))",
        });
        dialog.bindCommonClose(() => {
            dialog.close();
            dialog.overlay.remove();
        });
        dialog.bindDrag();
        const ok = dialog.query("[data-tv-welcome-ok]");
        if (ok) {
            ok.addEventListener("click", () => {
                dialog.close();
                dialog.overlay.remove();
            });
        }
        this.dialogManager.register("welcome", dialog);
        this.dialogManager.open("welcome");
    }

    _bindMenus() {
        const menuRoots = Array.from(document.querySelectorAll("[data-tv-menu-root]"));
        let activeRoot = null;

        menuRoots.forEach((root) => {
            const toggle = root.querySelector("[data-tv-menu-toggle]");
            if (!toggle || toggle.dataset.tvMenuBound === "1") { return; }
            toggle.dataset.tvMenuBound = "1";
            toggle.addEventListener("click", (event) => {
                event.preventDefault();
                if (activeRoot === root) {
                    closeMenus();
                } else {
                    closeMenus();
                    const popup = root.querySelector("[data-tv-menu-popup]");
                    if (popup) {
                        popup.hidden = false;
                        toggle.setAttribute("aria-expanded", "true");
                        toggle.classList.add("is-current");
                        activeRoot = root;
                        requestAnimationFrame(fillBorders);
                    }
                }
            });
        });

        document.querySelectorAll("[data-tv-dialog-open]").forEach((element) => {
            if (element.dataset.tvMenuBound === "1") { return; }
            element.dataset.tvMenuBound = "1";
            element.addEventListener("click", (event) => {
                event.preventDefault();
                closeMenus();
                this.dialogManager.open(element.getAttribute("data-tv-dialog-open") || "");
            });
        });

        document.querySelectorAll("[data-tv-theme-set]").forEach((element) => {
            if (element.dataset.tvMenuBound === "1") { return; }
            element.dataset.tvMenuBound = "1";
            element.addEventListener("click", (event) => {
                event.preventDefault();
                closeMenus();
                applyThemeAndSyncPalette(element.getAttribute("data-tv-theme-set") || "default", true);
                this.dialogManager.applyActiveStates();
                fillBorders();
            });
        });

        document.querySelectorAll("[data-tv-bundle-open]").forEach((element) => {
            if (element.dataset.tvMenuBound === "1") { return; }
            element.dataset.tvMenuBound = "1";
            element.addEventListener("click", async (event) => {
                event.preventDefault();
                closeMenus();
                const filename = element.dataset.tvBundleOpen;
                const bundleLabel = element.dataset.tvBundleLabel || "";
                const cached = bundleCache.has(filename);
                let loadingDialog = null;
                if (!cached) {
                    loadingDialog = new TVLoadingDialog(this.desktop);
                    loadingDialog.show(bundleLoadingLabel(bundleLabel, filename));
                }
                try {
                    const bundle = await loadBundle(filename, {
                        onProgress: (received, total) => {
                            if (loadingDialog) { loadingDialog.update(received, total); }
                        },
                        signal: loadingDialog ? loadingDialog.signal : undefined,
                    });
                    if (loadingDialog) { loadingDialog.destroy(); }
                    this._updateSearchData(bundle);
                    this.windowManager.showIndex(bundle);
                } catch (error) {
                    if (loadingDialog) { loadingDialog.destroy(); }
                    if (error.name === "AbortError") { return; }
                    console.error(`Failed to load bundle ${filename}:`, error);
                }
            });
        });

        document.querySelectorAll("[data-tv-current-topic], [data-tv-menu-link]").forEach((element) => {
            if (element.dataset.tvMenuBound === "1") { return; }
            element.dataset.tvMenuBound = "1";
            element.addEventListener("click", async (event) => {
                event.preventDefault();
                closeMenus();
                if (!this.windowManager || !this.windowManager.currentBundle) {
                    return;
                }
                const sourceFile = element.dataset.tvSourceFile || "";
                const lineNumber = this.windowManager._normalizeLineNumber(element.dataset.tvTopicLine);
                const topicRef = (
                    element.dataset.tvCurrentTopic
                    || element.dataset.tvBundleTopic
                    || element.dataset.tvTopicAlias
                    || ""
                ).trim();
                if (sourceFile) {
                    await this.windowManager.openSourceTopic(sourceFile, topicRef, lineNumber);
                    return;
                }
                if (!topicRef) {
                    return;
                }
                this.windowManager.showTopic(this.windowManager.currentBundle, topicRef, lineNumber);
            });
        });

        document.querySelectorAll("[data-tv-doc-open]").forEach((element) => {
            if (element.dataset.tvMenuBound === "1") { return; }
            element.dataset.tvMenuBound = "1";
            element.addEventListener("click", async (event) => {
                event.preventDefault();
                closeMenus();
                const docFile = element.dataset.tvDocOpen;
                try {
                    const resp = await fetch(DOCS_DIR + docFile);
                    if (!resp.ok) { throw new Error(`HTTP ${resp.status}`); }
                    const md = await resp.text();
                    this._openDocWindow(docFile, md);
                } catch (error) {
                    console.error(`Failed to load doc ${docFile}:`, error);
                }
            });
        });

        document.querySelectorAll("[data-tv-window-cmd]").forEach((element) => {
            if (element.dataset.tvMenuBound === "1") { return; }
            element.dataset.tvMenuBound = "1";
            element.addEventListener("click", (event) => {
                event.preventDefault();
                closeMenus();
                const cmd = element.dataset.tvWindowCmd;
                if (cmd === "zoom") {
                    this.windowManager.toggleZoom();
                } else if (cmd === "close") {
                    this.windowManager.closeAll();
                    fillBorders();
                    fillDesktopPatterns();
                } else if (cmd === "tile") {
                    this.windowManager.tile();
                } else if (cmd === "cascade") {
                    this.windowManager.cascade();
                } else if (cmd === "list") {
                    this._showWindowList();
                }
            });
        });

        // Screen saver triggers
        document.querySelectorAll("[data-tv-saver-start]").forEach((element) => {
            if (element.dataset.tvMenuBound === "1") { return; }
            element.dataset.tvMenuBound = "1";
            element.addEventListener("click", (event) => {
                event.preventDefault();
                closeMenus();
                const mode = element.dataset.tvSaverStart;
                const saver = TVScreenSaver.modes[mode];
                if (saver) {
                    new saver().start();
                }
            });
        });

        document.querySelectorAll("[data-tv-bundle-back]").forEach((element) => {
            if (element.dataset.tvMenuBound === "1") { return; }
            element.dataset.tvMenuBound = "1";
            element.addEventListener("click", (event) => {
                event.preventDefault();
                if (this.windowManager) {
                    this.windowManager.goBack();
                }
            });
        });

        if (!this._menuGlobalsBound) {
            this._menuGlobalsBound = true;
            document.addEventListener("click", (event) => {
                if (!event.target.closest("[data-tv-menu-root]")) {
                    if (this._closeMenus) {
                        this._closeMenus();
                    }
                }
            });

            document.addEventListener("keydown", (event) => {
                if (event.key === "Escape") {
                    const openMenu = document.querySelector("[data-tv-menu-root] [data-tv-menu-popup]:not([hidden])");
                    if (!openMenu) {
                        return;
                    }
                    event.preventDefault();
                    if (this._closeMenus) {
                        this._closeMenus();
                    }
                    return;
                }
                // F5 → Zoom
                if (event.key === "F5" && !event.ctrlKey && !event.altKey && !event.shiftKey) {
                    event.preventDefault();
                    this.windowManager.toggleZoom();
                    return;
                }
                // Alt-F3 → Close
                if (event.key === "F3" && event.altKey && !event.ctrlKey && !event.shiftKey) {
                    event.preventDefault();
                    this.windowManager.closeAll();
                    fillBorders();
                    fillDesktopPatterns();
                    return;
                }
                // Alt-0 → Window List
                if (event.key === "0" && event.altKey && !event.ctrlKey && !event.shiftKey) {
                    event.preventDefault();
                    this._showWindowList();
                    return;
                }
            });
        }

        function closeMenus() {
            closeSubmenus();
            menuRoots.forEach((root) => {
                const popup = root.querySelector("[data-tv-menu-popup]");
                const toggle = root.querySelector("[data-tv-menu-toggle]");
                if (popup) { popup.hidden = true; }
                if (toggle) {
                    toggle.setAttribute("aria-expanded", "false");
                    toggle.classList.remove("is-current");
                }
            });
            activeRoot = null;
        }
        this._closeMenus = closeMenus;

        function closeSubmenus() {
            document.querySelectorAll("[data-tv-submenu-popup]").forEach((popup) => {
                popup.hidden = true;
            });
            document.querySelectorAll("[data-tv-submenu-toggle]").forEach((el) => {
                el.classList.remove("is-submenu-open");
            });
        }

        // Bind submenu toggles: hover opens nested popup.
        document.querySelectorAll("[data-tv-submenu-toggle]").forEach((toggle) => {
            if (toggle.dataset.tvMenuBound === "1") { return; }
            toggle.dataset.tvMenuBound = "1";
            const root = toggle.closest("[data-tv-submenu-root]");
            if (!root) { return; }
            const popup = root.querySelector("[data-tv-submenu-popup]");
            if (!popup) { return; }

            toggle.addEventListener("click", (event) => {
                event.preventDefault();
                event.stopPropagation();
                const isOpen = !popup.hidden;
                closeSubmenus();
                if (!isOpen) {
                    popup.hidden = false;
                    toggle.classList.add("is-submenu-open");
                    requestAnimationFrame(() => fillBorders(popup));
                }
            });

            root.addEventListener("mouseenter", () => {
                closeSubmenus();
                popup.hidden = false;
                toggle.classList.add("is-submenu-open");
                requestAnimationFrame(() => fillBorders(popup));
            });

            root.addEventListener("mouseleave", (event) => {
                // Only close if mouse isn't moving to the submenu popup
                const related = event.relatedTarget;
                if (related && (popup.contains(related) || root.contains(related))) { return; }
                popup.hidden = true;
                toggle.classList.remove("is-submenu-open");
            });
        });
    }
}

// ── Bootstrap ───────────────────────────────────────────────────────

function initBundleApp() {
    const body = document.body;
    if (!body || body.dataset.tvPageKind !== "bundle-index") {
        return;
    }
    new TVBundleApp().start();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initBundleApp, { once: true });
} else {
    initBundleApp();
}

Object.assign(TV, { TVBundleApp, BundleWindowManager });
})();
