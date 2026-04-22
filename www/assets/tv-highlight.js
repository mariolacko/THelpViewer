/**
 * tv-highlight.js — Borland-style syntax highlighting for Pascal, C and ASM.
 *
 * Operates on .code-example spans produced by the converter.  Detects the
 * primary language automatically and handles inline `asm … end` blocks in
 * Pascal code.
 *
 * Colour classes used: code-keyword, code-string, code-comment, code-number,
 * code-preproc, code-asm (CSS variables --tv-code-*).
 */

/* global TV */
(function (TV) {
"use strict";

// ── keyword sets ────────────────────────────────────────────────────

const PASCAL_KW = new Set([
    "and","array","asm","begin","case","const","constructor","destructor",
    "div","do","downto","else","end","file","for","function","goto","if",
    "implementation","in","inherited","inline","interface","label","mod",
    "nil","not","object","of","or","packed","procedure","program","record",
    "repeat","set","shl","shr","string","then","to","type","unit","until",
    "uses","var","while","with","xor",
]);

const C_KW = new Set([
    "auto","break","case","char","const","continue","default","do","double",
    "else","enum","extern","float","for","goto","if","int","long","register",
    "return","short","signed","sizeof","static","struct","switch","typedef",
    "union","unsigned","void","volatile","while",
    // common C++ / Borland extensions seen in help examples
    "asm","bool","catch","cdecl","class","delete","far","friend","huge",
    "inline","interrupt","mutable","namespace","near","new","operator",
    "pascal","private","protected","public","template","this","throw",
    "true","false","try","using","virtual",
    // Win16/Win32 common typedefs seen in Borland help files
    "BOOL","BYTE","DWORD","FAR","HANDLE","HINSTANCE","HWND","LONG","LPARAM",
    "LPCSTR","LPSTR","LPVOID","NEAR","NULL","PASCAL","TRUE","FALSE","UINT",
    "VOID","WINAPI","WORD","WPARAM","CALLBACK","LRESULT","HDC","HBRUSH",
    "HCURSOR","HICON","HMENU","HMODULE","MSG","WNDCLASS","RECT","POINT",
].map((word) => word.toLowerCase()));

const ASM_KW = new Set([
    // x86 registers
    "ah","al","ax","bh","bl","bp","bx","ch","cl","cs","cx","dh","di",
    "dl","ds","dx","eax","ebp","ebx","ecx","edi","edx","es","esi","esp",
    "fs","gs","si","sp","ss",
    // common x86 instructions
    "aaa","aad","aam","aas","adc","add","and","call","cbw","clc","cld",
    "cli","cmc","cmp","cmps","cmpsb","cmpsw","cwd","daa","das","dec",
    "div","enter","hlt","idiv","imul","in","inc","ins","int","into",
    "iret","ja","jae","jb","jbe","jc","jcxz","je","jg","jge","jl","jle",
    "jmp","jna","jnae","jnb","jnbe","jnc","jne","jng","jnge","jnl",
    "jnle","jno","jnp","jns","jnz","jo","jp","jpe","jpo","js","jz",
    "lahf","lds","lea","leave","les","lfs","lgs","lock","lods","lodsb",
    "lodsw","loop","loope","loopne","loopnz","loopz","lss","mov","movs",
    "movsb","movsw","movsx","movzx","mul","neg","nop","not","or","out",
    "outs","pop","popa","popad","popf","popfd","push","pusha","pushad",
    "pushf","pushfd","rcl","rcr","rep","repe","repne","repnz","repz",
    "ret","retf","retn","rol","ror","sahf","sal","sar","sbb","scas",
    "scasb","scasw","shl","shr","stc","std","sti","stos","stosb","stosw",
    "sub","test","wait","xchg","xlat","xlatb","xor",
    // data directives
    "db","dd","dw","dq","dt","dup","offset","ptr","seg","byte","word",
    "dword","fword","qword","tbyte","near","far","short",
]);

const C_PREPROC_RE = /^\s*#\s*(include|define|ifdef|ifndef|endif|else|elif|pragma|if|undef|error|warning|line)\b/;

// ── language detection ──────────────────────────────────────────────

function stripForLangDetect(text) {
    return String(text || "")
        .replace(/\/\*[\s\S]*?\*\//g, " ")
        .replace(/\/\/.*$/gm, " ")
        .replace(/\(\*[\s\S]*?\*\)/g, " ")
        .replace(/"(?:\\.|[^"\\])*"/g, " ")
        .replace(/'(?:''|\\.|[^'\\])*'/g, " ");
}

function detectCodeLang(text) {
    const raw = String(text || "");
    const probe = stripForLangDetect(raw);
    let cScore = 0, pascalScore = 0;
    if (/#include|#define|#if\b|#elif\b|#undef\b|#pragma\b|->|::|\b(?:printf|scanf|malloc|calloc|realloc|free|sizeof|new|delete|class|template|virtual|namespace|using|operator|cdecl|pascal|near|far)\b|\b(?:void|int|char|short|long|float|double|unsigned|signed)\s+\w/i.test(probe)) cScore += 5;
    if (/\bNULL\b|\bHWND\b|\bDWORD\b|\bLPSTR\b|\bWINAPI\b|\bHANDLE\b|\bLRESULT\b|\bWPARAM\b/i.test(probe)) cScore += 3;
    if (/[{};]/.test(probe)) cScore += 1;
    if (/\/\*|\*\/|\/\//.test(raw)) cScore += 1;
    if (/\b(begin|end|procedure|function|program|unit|uses|then|repeat|until|implementation|interface)\b/i.test(probe)) pascalScore += 5;
    if (/\b(var|const|type|record|object|constructor|destructor|inherited|downto|packed|nil|array|set|writeln|readln|integer|boolean)\b/i.test(probe)) pascalScore += 3;
    if (/\(\*|\*\)|:=|\bdiv\b|\bmod\b/i.test(probe)) pascalScore += 2;
    return cScore > pascalScore ? "c" : "pascal";
}

// ── helpers ─────────────────────────────────────────────────────────

function esc(text) {
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function spanWrap(cls, inner) {
    return `<span class="${cls}">${inner}</span>`;
}

// ── per-language token regexes ──────────────────────────────────────

// Pascal: { … }, (* … *), // …, '…'
const PASCAL_TOKEN_RE = /(\{[^}]*\}|\(\*[\s\S]*?\*\)|\/\/.*$|'(?:''|[^'])*')/gi;
// C: /* … */, // …, "…", '…'
const C_TOKEN_RE = /(\/\*[\s\S]*?\*\/|\/\/.*$|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')/gm;
// ASM: ; …
const ASM_COMMENT_RE = /(;.*$)/gm;
// Numbers: $FF, 0xFF, 0FFh, 123, 12.34
const NUMBER_RE = /(?<![&\w])(\$[0-9A-Fa-f]+|0x[0-9A-Fa-f]+|[0-9][0-9A-Fa-f]*[hH]|\d+(?:\.\d+)?)(?!\w)/g;

// ── plain fragment highlighting (keywords + numbers) ────────────────

function hlPlainPascal(text) {
    let r = text.replace(/\b(\w+)\b/g, (w) =>
        PASCAL_KW.has(w.toLowerCase()) ? spanWrap("code-keyword", w) : w
    );
    r = r.replace(NUMBER_RE, (_, n) => spanWrap("code-number", n));
    return r;
}

function hlPlainC(text) {
    if (C_PREPROC_RE.test(text)) return spanWrap("code-preproc", text);
    let r = text.replace(/\b(\w+)\b/g, (w) =>
        C_KW.has(w.toLowerCase()) ? spanWrap("code-keyword", w) : w
    );
    r = r.replace(NUMBER_RE, (_, n) => spanWrap("code-number", n));
    // Highlight common C/C++ punctuation/operators like { } ; * + - / etc.
    // as keyword-coloured tokens to match original Borland viewer.
    r = r.replace(/([{};*+\-\/=%|^&()[\]])/g, (m) => spanWrap("code-keyword", m));
    // Escaped HTML entities for angle brackets and ampersand appear as
    // `&lt;`, `&gt;`, `&amp;` in the escaped input; highlight them too so
    // the displayed characters get the same keyword colouring.
    r = r.replace(/&lt;|&gt;|&amp;/g, (m) => spanWrap("code-keyword", m));
    return r;
}

function hlPlainAsm(text) {
    let r = text.replace(/\b(\w+)\b/g, (w) =>
        ASM_KW.has(w.toLowerCase()) ? spanWrap("code-keyword", w) : w
    );
    r = r.replace(NUMBER_RE, (_, n) => spanWrap("code-number", n));
    return r;
}

// ── line-level highlighting ─────────────────────────────────────────

function hlTokenize(escaped, tokenRe, plainFn) {
    const parts = [];
    let cur = 0, m;
    tokenRe.lastIndex = 0;
    while ((m = tokenRe.exec(escaped)) !== null) {
        if (m.index > cur) parts.push(plainFn(escaped.slice(cur, m.index)));
        const tok = m[0];
        if (tok.startsWith("'") || tok.startsWith('"')) {
            parts.push(spanWrap("code-string", tok));
        } else {
            parts.push(spanWrap("code-comment", tok));
        }
        cur = tokenRe.lastIndex;
    }
    if (cur < escaped.length) parts.push(plainFn(escaped.slice(cur)));
    return parts.join("");
}

function hlLinePascal(escaped) {
    return hlTokenize(escaped, PASCAL_TOKEN_RE, hlPlainPascal);
}

function hlLineC(escaped) {
    return hlTokenize(escaped, C_TOKEN_RE, hlPlainC);
}

function hlLineAsm(escaped) {
    // ASM comments use ; to end-of-line
    const parts = [];
    let cur = 0, m;
    ASM_COMMENT_RE.lastIndex = 0;
    while ((m = ASM_COMMENT_RE.exec(escaped)) !== null) {
        if (m.index > cur) parts.push(hlPlainAsm(escaped.slice(cur, m.index)));
        parts.push(spanWrap("code-comment", m[0]));
        cur = ASM_COMMENT_RE.lastIndex;
    }
    if (cur < escaped.length) parts.push(hlPlainAsm(escaped.slice(cur)));
    return parts.join("");
}

// ── inline asm detection in Pascal ──────────────────────────────────
//
// Pascal `asm … end` blocks: each line inside gets ASM highlighting.
// We track state across lines.

const ASM_OPEN_RE = /\basm\b/i;
const ASM_CLOSE_RE = /\bend\b/i;

/**
 * Highlight all .code-example elements inside *container*.
 *
 * For Pascal code, tracks inline `asm … end` blocks across lines so
 * that assembler instructions get the asm colour class.
 */
function highlightCodeExamples(container) {
    const els = container.querySelectorAll(".code-example");
    if (!els.length) return;

    // Detect primary language from the combined text
    const lang = detectCodeLang(Array.from(els, (el) => el.textContent || "").join("\n"));
    const baseClass = lang === "c" ? "code-lang-c" : "code-lang-pascal";

    if (lang === "c") {
        // C mode — use DOM-based highlighting to avoid fragile HTML
        // string serialization that previously produced malformed tags.
        els.forEach((el) => {
            el.classList.remove("code-lang-c", "code-lang-pascal", "code-lang-asm");
            el.classList.add("code-lang-c");
            const raw = el.textContent || "";
            if (!raw.trim()) return;

            // Entire preprocessor directive — wrap whole line while
            // preserving existing inline elements.
            if (C_PREPROC_RE.test(raw)) {
                if (!el.children.length) {
                    const w = document.createElement("span");
                    w.className = "code-preproc";
                    w.textContent = raw;
                    el.innerHTML = "";
                    el.appendChild(w);
                } else {
                    const wrapper = document.createElement("span");
                    wrapper.className = "code-preproc";
                    Array.from(el.childNodes).forEach((n) => wrapper.appendChild(n.cloneNode(true)));
                    el.innerHTML = "";
                    el.appendChild(wrapper);
                }
                return;
            }

            // Tokenize text nodes into spans/nodes safely using the DOM.
            function createFragmentForC(text) {
                const frag = document.createDocumentFragment();
                // Tokenize with comments and strings first, then numbers/words/punct
                const tokenRE = /(\/\*[\s\S]*?\*\/|\/\/.*?$|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\$[0-9A-Fa-f]+|0x[0-9A-Fa-f]+|[0-9][0-9A-Fa-f]*[hH]|\d+(?:\.\d+)?|\b\w+\b|[{};*+\-\/=%|^&()\[\]<>])/gm;
                let last = 0;
                tokenRE.lastIndex = 0;
                let m;
                while ((m = tokenRE.exec(text)) !== null) {
                    if (m.index > last) {
                        frag.appendChild(document.createTextNode(text.slice(last, m.index)));
                    }
                    const tok = m[0];
                    let node;
                    // Comments (block or line)
                    if (tok.startsWith("/*") || tok.startsWith("//")) {
                        node = document.createElement("span");
                        node.className = "code-comment";
                        node.textContent = tok;
                    } else if (tok.startsWith('"') || tok.startsWith("'")) {
                        node = document.createElement("span");
                        node.className = "code-string";
                        node.textContent = tok;
                    } else {
                        NUMBER_RE.lastIndex = 0;
                        if (NUMBER_RE.test(tok)) {
                            node = document.createElement("span");
                            node.className = "code-number";
                            node.textContent = tok;
                        } else if (/^\w+$/.test(tok) && C_KW.has(tok.toLowerCase())) {
                            node = document.createElement("span");
                            node.className = "code-keyword";
                            node.textContent = tok;
                        } else if (/^[{};*+\-\/=%|^&()\[\]<>]$/.test(tok) || tok === "<" || tok === ">" || tok === "&") {
                            node = document.createElement("span");
                            node.className = "code-keyword";
                            node.textContent = tok;
                        } else {
                            node = document.createTextNode(tok);
                        }
                    }
                    frag.appendChild(node);
                    last = tokenRE.lastIndex;
                }
                if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
                return frag;
            }

            function processChildNode(node) {
                const frag = document.createDocumentFragment();
                if (node.nodeType === Node.TEXT_NODE) {
                    frag.appendChild(createFragmentForC(node.nodeValue || ""));
                    return frag;
                }
                if (node.nodeType === Node.ELEMENT_NODE) {
                    const el2 = document.createElement(node.tagName.toLowerCase());
                    Array.from(node.attributes).forEach((a) => el2.setAttribute(a.name, a.value));
                    Array.from(node.childNodes).forEach((ch) => el2.appendChild(processChildNode(ch)));
                    frag.appendChild(el2);
                    return frag;
                }
                return frag;
            }

            if (!el.children.length) {
                el.innerHTML = "";
                el.appendChild(createFragmentForC(raw));
                return;
            }

            const fragment = document.createDocumentFragment();
            Array.from(el.childNodes).forEach((node) => fragment.appendChild(processChildNode(node)));
            el.innerHTML = "";
            el.appendChild(fragment);
        });
        return;
    }

    // Pascal mode — track inline asm blocks
    let inAsm = false;
    els.forEach((el) => {
        el.classList.remove("code-lang-c", "code-lang-pascal", "code-lang-asm");
        el.classList.add(baseClass);
        const raw = el.textContent || "";
        if (!raw.trim()) return;
        const escaped = esc(raw);

        function highlightNodePascal(node, asmMode) {
            if (node.nodeType === Node.TEXT_NODE) {
                const txt = node.nodeValue || "";
                if (!txt) return "";
                if (asmMode) {
                    return spanWrap("code-asm", hlLineAsm(esc(txt)));
                }
                return hlLinePascal(esc(txt));
            }
            if (node.nodeType === Node.ELEMENT_NODE) {
                const tag = node.tagName.toLowerCase();
                const attrs = Array.from(node.attributes)
                    .map((a) => `${a.name}="${a.value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")}"`)
                    .join(" ");
                const inner = Array.from(node.childNodes).map((n) => highlightNodePascal(n, asmMode)).join("");
                return `<${tag}${attrs ? ' ' + attrs : ''}>${inner}</${tag}>`;
            }
            return "";
        }

        if (inAsm) {
            // Inside an asm block — check if this line ends it
            if (ASM_CLOSE_RE.test(raw)) {
                inAsm = false;
                if (!el.children.length) {
                    el.innerHTML = hlLinePascal(escaped);
                } else {
                    el.innerHTML = Array.from(el.childNodes).map((n) => highlightNodePascal(n, false)).join("");
                }
            } else {
                el.classList.remove(baseClass);
                el.classList.add("code-lang-asm");
                if (!el.children.length) {
                    el.innerHTML = spanWrap("code-asm", hlLineAsm(escaped));
                } else {
                    el.innerHTML = Array.from(el.childNodes).map((n) => highlightNodePascal(n, true)).join("");
                    el.innerHTML = spanWrap("code-asm", el.innerHTML);
                }
            }
            return;
        }

        // Not in asm — check if this line opens an asm block
        if (ASM_OPEN_RE.test(raw)) {
            // If the line is just `asm` (with possible keyword decoration),
            // highlight as Pascal keyword and enter asm mode.
            // If asm and end are on the same line, just highlight as Pascal.
            if (ASM_CLOSE_RE.test(raw)) {
                // Single-line asm…end — highlight as mixed
                if (!el.children.length) {
                    el.innerHTML = hlLinePascal(escaped);
                } else {
                    el.innerHTML = Array.from(el.childNodes).map((n) => highlightNodePascal(n, false)).join("");
                }
            } else {
                if (!el.children.length) {
                    el.innerHTML = hlLinePascal(escaped);
                } else {
                    el.innerHTML = Array.from(el.childNodes).map((n) => highlightNodePascal(n, false)).join("");
                }
                inAsm = true;
            }
            return;
        }

        if (!el.children.length) {
            el.innerHTML = hlLinePascal(escaped);
        } else {
            el.innerHTML = Array.from(el.childNodes).map((n) => highlightNodePascal(n, false)).join("");
        }
    });
}

// ── export ──────────────────────────────────────────────────────────

TV.highlightCodeExamples = highlightCodeExamples;

})(window.THelpViewerTV || (window.THelpViewerTV = {}));
