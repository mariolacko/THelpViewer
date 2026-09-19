// tv-highlight.js — lightweight syntax highlighting for code examples.
(function (TV) {
"use strict";

const PASCAL_KW = new Set([
    "and", "array", "asm", "begin", "case", "const", "constructor", "destructor",
    "div", "do", "downto", "else", "end", "file", "for", "function", "goto", "if",
    "implementation", "in", "inherited", "inline", "interface", "label", "mod",
    "nil", "not", "object", "of", "or", "packed", "procedure", "program", "record",
    "repeat", "set", "shl", "shr", "string", "then", "to", "type", "unit", "until",
    "uses", "var", "while", "with", "xor",
]);

const C_KW = new Set([
    "auto", "break", "case", "char", "const", "continue", "default", "do", "double",
    "else", "enum", "extern", "float", "for", "goto", "if", "int", "long", "register",
    "return", "short", "signed", "sizeof", "static", "struct", "switch", "typedef",
    "union", "unsigned", "void", "volatile", "while", "asm", "bool", "catch", "cdecl",
    "class", "delete", "far", "friend", "huge", "inline", "interrupt", "mutable",
    "namespace", "near", "new", "operator", "pascal", "private", "protected", "public",
    "template", "this", "throw", "true", "false", "try", "using", "virtual", "bool",
    "byte", "word", "dword", "handle", "hwnd", "hinstance", "uint", "lparam", "wparam",
    "lresult", "callback", "winapi", "null",
]);

const ASM_KW = new Set([
    "aaa", "aad", "aam", "aas", "adc", "add", "and", "call", "cbw", "clc", "cld",
    "cli", "cmc", "cmp", "cmps", "cwd", "daa", "das", "dec", "div", "hlt", "idiv",
    "imul", "in", "inc", "int", "into", "iret", "ja", "jae", "jb", "jbe", "jc",
    "jcxz", "je", "jg", "jge", "jl", "jle", "jmp", "jna", "jnae", "jnb", "jnbe",
    "jnc", "jne", "jng", "jnge", "jnl", "jnle", "jno", "jnp", "jns", "jnz", "jo",
    "jp", "jpe", "jpo", "js", "jz", "lahf", "lds", "lea", "les", "lock", "lods",
    "loop", "mov", "movs", "mul", "neg", "nop", "not", "or", "out", "pop", "push",
    "rcl", "rcr", "rep", "repe", "repne", "ret", "rol", "ror", "sahf", "sal", "sar",
    "sbb", "scas", "shl", "shr", "stc", "std", "sti", "stos", "sub", "test", "wait",
    "xchg", "xlat", "xor", "db", "dd", "dw", "dq", "dt", "dup", "offset", "ptr",
    "seg", "byte", "word", "dword", "fword", "qword", "tbyte", "near", "far", "short",
    "ax", "bx", "cx", "dx", "si", "di", "bp", "sp", "cs", "ds", "es", "ss", "al",
    "ah", "bl", "bh", "cl", "ch", "dl", "dh", "eax", "ebx", "ecx", "edx", "esi",
    "edi", "ebp", "esp",
]);

const C_PREPROC_RE = /^\s*#\s*(include|define|ifdef|ifndef|endif|else|elif|pragma|if|undef|error|warning|line)\b/;
const PASCAL_TOKEN_RE = /(\{[^}]*\}|\(\*[\s\S]*?\*\)|\/\/.*$|'(?:''|[^'])*')/gm;
const C_TOKEN_RE = /(\/\*[\s\S]*?\*\/|\/\/.*$|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')/gm;
const ASM_COMMENT_RE = /(;.*$)/gm;
const NUMBER_RE = /(?<![&\w])(\$[0-9A-Fa-f]+|0x[0-9A-Fa-f]+|[0-9][0-9A-Fa-f]*[hH]|\d+(?:\.\d+)?)(?!\w)/g;

function esc(text) {
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

function spanWrap(cls, inner) {
    return `<span class="${cls}">${inner}</span>`;
}

function continuesWithBackslash(raw) {
    return /\\\s*$/.test(raw);
}

function detectCodeLang(text) {
    const probe = String(text || "");
    let cScore = 0;
    let pascalScore = 0;
    let asmScore = 0;

    if (/#include|#define|#pragma|->|::|\b(?:printf|scanf|malloc|free|sizeof|class|template|namespace|virtual)\b/i.test(probe)) { cScore += 5; }
    if (/\b(?:void|int|char|short|long|float|double|unsigned|signed|struct|typedef)\b/.test(probe)) { cScore += 3; }
    if (/\{[^}]*\}|\/\*|\*\//.test(probe)) { cScore += 2; }

    if (/\b(?:begin|end|procedure|function|program|unit|uses|implementation|interface|record|object)\b/i.test(probe)) { pascalScore += 5; }
    if (/\b(?:var|const|type|string|nil|array|set|downto|inherited)\b/i.test(probe)) { pascalScore += 3; }
    if (/\(\*|\*\)|:=|\bdiv\b|\bmod\b/i.test(probe)) { pascalScore += 2; }

    if (/\b(?:mov|push|pop|jmp|call|cmp|lea|xor|or|and|int|ret)\b/i.test(probe)) { asmScore += 5; }
    if (/\b(?:ax|bx|cx|dx|si|di|bp|sp|cs|ds|es|ss|eax|ebx|ecx|edx)\b/i.test(probe)) { asmScore += 4; }
    if (/^\s*;.*$/m.test(probe)) { asmScore += 2; }

    if (asmScore > cScore && asmScore > pascalScore) {
        return "asm";
    }
    return cScore > pascalScore ? "c" : "pascal";
}

function hlPlainPascal(text) {
    let result = text.replace(/\b(\w+)\b/g, (word) => (
        PASCAL_KW.has(word.toLowerCase()) ? spanWrap("code-keyword", word) : word
    ));
    result = result.replace(NUMBER_RE, (_m, number) => spanWrap("code-number", number));
    return result;
}

function hlPlainC(text) {
    if (C_PREPROC_RE.test(text)) {
        return spanWrap("code-preproc", text);
    }
    let result = text.replace(/\b(\w+)\b/g, (word) => (
        C_KW.has(word.toLowerCase()) ? spanWrap("code-keyword", word) : word
    ));
    result = result.replace(NUMBER_RE, (_m, number) => spanWrap("code-number", number));
    return result;
}

function hlPlainAsm(text) {
    let result = text.replace(/\b(\w+)\b/g, (word) => (
        ASM_KW.has(word.toLowerCase()) ? spanWrap("code-keyword", word) : word
    ));
    result = result.replace(NUMBER_RE, (_m, number) => spanWrap("code-number", number));
    return result;
}

function hlTokenize(escaped, tokenRe, plainFn) {
    const parts = [];
    let cursor = 0;
    tokenRe.lastIndex = 0;
    let match;
    while ((match = tokenRe.exec(escaped)) !== null) {
        if (match.index > cursor) {
            parts.push(plainFn(escaped.slice(cursor, match.index)));
        }
        const token = match[0];
        if (token.startsWith("'") || token.startsWith('"')) {
            parts.push(spanWrap("code-string", token));
        } else {
            parts.push(spanWrap("code-comment", token));
        }
        cursor = tokenRe.lastIndex;
    }
    if (cursor < escaped.length) {
        parts.push(plainFn(escaped.slice(cursor)));
    }
    return parts.join("");
}

function hlLinePascal(raw, inBlockComment) {
    const parts = [];
    let cursor = 0;
    let index = 0;
    let blockComment = inBlockComment;

    function flushCode(until) {
        if (until <= cursor) {
            return;
        }
        parts.push(hlPlainPascal(esc(raw.slice(cursor, until))));
    }

    while (index < raw.length) {
        if (blockComment === "paren") {
            const end = raw.indexOf("*)", index);
            if (end < 0) {
                parts.push(spanWrap("code-comment", esc(raw.slice(index))));
                return { html: parts.join(""), inBlockComment: "paren" };
            }
            parts.push(spanWrap("code-comment", esc(raw.slice(index, end + 2))));
            index = end + 2;
            cursor = index;
            blockComment = false;
            continue;
        }

        if (blockComment === "brace") {
            const end = raw.indexOf("}", index);
            if (end < 0) {
                parts.push(spanWrap("code-comment", esc(raw.slice(index))));
                return { html: parts.join(""), inBlockComment: "brace" };
            }
            parts.push(spanWrap("code-comment", esc(raw.slice(index, end + 1))));
            index = end + 1;
            cursor = index;
            blockComment = false;
            continue;
        }

        if (raw.startsWith("//", index)) {
            flushCode(index);
            parts.push(spanWrap("code-comment", esc(raw.slice(index))));
            return { html: parts.join(""), inBlockComment: false };
        }

        if (raw.startsWith("(*", index)) {
            flushCode(index);
            const end = raw.indexOf("*)", index + 2);
            if (end < 0) {
                parts.push(spanWrap("code-comment", esc(raw.slice(index))));
                return { html: parts.join(""), inBlockComment: "paren" };
            }
            parts.push(spanWrap("code-comment", esc(raw.slice(index, end + 2))));
            index = end + 2;
            cursor = index;
            continue;
        }

        if (raw[index] === "{") {
            flushCode(index);
            const end = raw.indexOf("}", index + 1);
            if (end < 0) {
                parts.push(spanWrap("code-comment", esc(raw.slice(index))));
                return { html: parts.join(""), inBlockComment: "brace" };
            }
            parts.push(spanWrap("code-comment", esc(raw.slice(index, end + 1))));
            index = end + 1;
            cursor = index;
            continue;
        }

        if (raw[index] === "'") {
            let end = index + 1;
            while (end < raw.length) {
                if (raw[end] === "'") {
                    if (raw[end + 1] === "'") {
                        end += 2;
                        continue;
                    }
                    end += 1;
                    break;
                }
                end += 1;
            }
            flushCode(index);
            parts.push(spanWrap("code-string", esc(raw.slice(index, Math.min(end, raw.length)))));
            index = Math.min(end, raw.length);
            cursor = index;
            continue;
        }

        index += 1;
    }

    flushCode(raw.length);
    return { html: parts.join(""), inBlockComment: false };
}

function hlLineC(raw, inBlockComment, inPreprocContinuation) {
    const parts = [];
    let cursor = 0;
    let index = 0;
    let blockComment = inBlockComment;
    const continuesPreproc = continuesWithBackslash(raw);

    if (!blockComment && (inPreprocContinuation || C_PREPROC_RE.test(raw))) {
        return {
            html: spanWrap("code-preproc", esc(raw)),
            inBlockComment: false,
            inPreprocContinuation: continuesPreproc,
        };
    }

    function flushCode(until) {
        if (until <= cursor) {
            return;
        }
        parts.push(hlPlainC(esc(raw.slice(cursor, until))));
    }

    while (index < raw.length) {
        if (blockComment) {
            const end = raw.indexOf("*/", index);
            if (end < 0) {
                parts.push(spanWrap("code-comment", esc(raw.slice(index))));
                return { html: parts.join(""), inBlockComment: true, inPreprocContinuation: false };
            }
            parts.push(spanWrap("code-comment", esc(raw.slice(index, end + 2))));
            index = end + 2;
            cursor = index;
            blockComment = false;
            continue;
        }

        if (raw.startsWith("//", index)) {
            flushCode(index);
            parts.push(spanWrap("code-comment", esc(raw.slice(index))));
            return { html: parts.join(""), inBlockComment: false, inPreprocContinuation: false };
        }

        if (raw.startsWith("/*", index)) {
            flushCode(index);
            const end = raw.indexOf("*/", index + 2);
            if (end < 0) {
                parts.push(spanWrap("code-comment", esc(raw.slice(index))));
                return { html: parts.join(""), inBlockComment: true, inPreprocContinuation: false };
            }
            parts.push(spanWrap("code-comment", esc(raw.slice(index, end + 2))));
            index = end + 2;
            cursor = index;
            continue;
        }

        if (raw[index] === '"' || raw[index] === "'") {
            const quote = raw[index];
            let end = index + 1;
            while (end < raw.length) {
                if (raw[end] === "\\") {
                    end += 2;
                    continue;
                }
                if (raw[end] === quote) {
                    end += 1;
                    break;
                }
                end += 1;
            }
            flushCode(index);
            parts.push(spanWrap("code-string", esc(raw.slice(index, Math.min(end, raw.length)))));
            index = Math.min(end, raw.length);
            cursor = index;
            continue;
        }

        index += 1;
    }

    flushCode(raw.length);
    return { html: parts.join(""), inBlockComment: false, inPreprocContinuation: false };
}

function hlLineAsm(escaped) {
    const parts = [];
    let cursor = 0;
    ASM_COMMENT_RE.lastIndex = 0;
    let match;
    while ((match = ASM_COMMENT_RE.exec(escaped)) !== null) {
        if (match.index > cursor) {
            parts.push(hlPlainAsm(escaped.slice(cursor, match.index)));
        }
        parts.push(spanWrap("code-comment", match[0]));
        cursor = ASM_COMMENT_RE.lastIndex;
    }
    if (cursor < escaped.length) {
        parts.push(hlPlainAsm(escaped.slice(cursor)));
    }
    return parts.join("");
}

function highlightCodeExamples(container) {
    const scope = container && container.querySelectorAll ? container : document;
    const examples = Array.from(scope.querySelectorAll(".code-example"));
    if (!examples.length) {
        return;
    }

    const lang = detectCodeLang(examples.map((el) => el.textContent || "").join("\n"));
    let inPascalAsm = false;
    let inCBlockComment = false;
    let inCPreprocContinuation = false;
    let inPascalBlockComment = false;

    examples.forEach((el) => {
        const raw = el.textContent || "";
        el.classList.remove("code-lang-c", "code-lang-pascal", "code-lang-asm");

        if (!raw.trim()) {
            return;
        }

        if (lang === "c") {
            el.classList.add("code-lang-c");
            const result = hlLineC(raw, inCBlockComment, inCPreprocContinuation);
            el.innerHTML = result.html;
            inCBlockComment = result.inBlockComment;
            inCPreprocContinuation = result.inPreprocContinuation;
            return;
        }

        if (lang === "asm") {
            el.classList.add("code-lang-asm");
            el.innerHTML = spanWrap("code-asm", hlLineAsm(esc(raw)));
            return;
        }

        if (inPascalAsm && !/\bend\b/i.test(raw)) {
            el.classList.add("code-lang-asm");
            el.innerHTML = spanWrap("code-asm", hlLineAsm(esc(raw)));
            return;
        }

        el.classList.add("code-lang-pascal");
        const result = hlLinePascal(raw, inPascalBlockComment);
        el.innerHTML = result.html;
        inPascalBlockComment = result.inBlockComment;

        if (/\basm\b/i.test(raw) && !/\bend\b/i.test(raw)) {
            inPascalAsm = true;
            return;
        }
        if (inPascalAsm && /\bend\b/i.test(raw)) {
            inPascalAsm = false;
        }
    });
}

TV.highlightCodeExamples = highlightCodeExamples;
})(window.THelpViewerTV || (window.THelpViewerTV = {}));
