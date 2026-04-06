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
    // Win16/Win32 common typedefs seen in Borland help files
    "BOOL","BYTE","DWORD","FAR","HANDLE","HINSTANCE","HWND","LONG","LPARAM",
    "LPCSTR","LPSTR","LPVOID","NEAR","NULL","PASCAL","TRUE","FALSE","UINT",
    "VOID","WINAPI","WORD","WPARAM","CALLBACK","LRESULT","HDC","HBRUSH",
    "HCURSOR","HICON","HMENU","HMODULE","MSG","WNDCLASS","RECT","POINT",
]);

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

function detectCodeLang(container) {
    const text = container.textContent || "";
    let cScore = 0, pascalScore = 0;
    if (/#include|#define|->|printf|scanf|malloc|sizeof\s*\(|void\s+\w|int\s+\w|char\s+\w/.test(text)) cScore += 5;
    if (/\bNULL\b|\bHWND\b|\bDWORD\b|\bLPSTR\b|\bWINAPI\b|\bHANDLE\b/.test(text)) cScore += 3;
    if (/[{};]/.test(text)) cScore += 1;
    if (/\/\*|\*\/|\/\//.test(text)) cScore += 1;
    if (/\b(begin|end|procedure|function|program|unit|uses|then|repeat|until)\b/i.test(text)) pascalScore += 5;
    if (/\b(var|const|type|record|object|constructor|destructor|inherited)\b/i.test(text)) pascalScore += 3;
    if (/\(\*|\*\)|:=|\{[^}]*\}/.test(text)) pascalScore += 2;
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
const NUMBER_RE = /(?<![&\w])(\$[0-9A-Fa-f]+|0x[0-9A-Fa-f]+|[0-9][0-9A-Fa-f]*[hH]|\d+(?:\.\d+)?)(?![\w;])/g;

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
        C_KW.has(w) ? spanWrap("code-keyword", w) : w
    );
    r = r.replace(NUMBER_RE, (_, n) => spanWrap("code-number", n));
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
    const probe = document.createElement("div");
    els.forEach((el) => probe.appendChild(el.cloneNode(true)));
    const lang = detectCodeLang(probe);

    if (lang === "c") {
        // C mode — straightforward, no inline asm tracking needed for
        // the help files (inline asm in BC++ uses asm { } which is rare
        // in help examples).
        els.forEach((el) => {
            const raw = el.textContent;
            if (raw.trim()) el.innerHTML = hlLineC(esc(raw));
        });
        return;
    }

    // Pascal mode — track inline asm blocks
    let inAsm = false;
    els.forEach((el) => {
        const raw = el.textContent;
        if (!raw.trim()) return;
        const escaped = esc(raw);

        if (inAsm) {
            // Inside an asm block — check if this line ends it
            if (ASM_CLOSE_RE.test(raw)) {
                // The `end` keyword itself still gets Pascal highlighting
                inAsm = false;
                el.innerHTML = hlLinePascal(escaped);
            } else {
                el.innerHTML = spanWrap("code-asm", hlLineAsm(escaped));
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
                el.innerHTML = hlLinePascal(escaped);
            } else {
                el.innerHTML = hlLinePascal(escaped);
                inAsm = true;
            }
            return;
        }

        el.innerHTML = hlLinePascal(escaped);
    });
}

// ── export ──────────────────────────────────────────────────────────

TV.highlightCodeExamples = highlightCodeExamples;

})(window.THelpViewerTV || (window.THelpViewerTV = {}));
