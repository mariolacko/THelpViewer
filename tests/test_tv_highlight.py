from pathlib import Path
import shutil
import subprocess

import pytest


HIGHLIGHT_PATHS = (
    Path("www/assets/tv-highlight.js"),
    Path("thelpviewer/converter/assets/tv-highlight.js"),
)
NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="Node.js is required for highlighter behavior tests")
def test_each_contiguous_code_block_detects_its_own_language():
    assert HIGHLIGHT_PATHS[0].read_bytes() == HIGHLIGHT_PATHS[1].read_bytes()
    script = r'''
const fs = require("fs");
global.window = { THelpViewerTV: {} };
global.Node = { TEXT_NODE: 3 };
eval(fs.readFileSync(process.argv[1], "utf8"));

function classList() {
    const values = new Set();
    return {
        add: (...names) => names.forEach((name) => values.add(name)),
        remove: (...names) => names.forEach((name) => values.delete(name)),
        contains: (name) => values.has(name),
    };
}
function line(text) {
    const wrapper = { nextElementSibling: null };
    return {
        wrapper,
        example: {
            textContent: text,
            innerHTML: "",
            classList: classList(),
            closest: (selector) => selector === ".tv-topic-line" ? wrapper : null,
        },
    };
}
function connect(lines) {
    lines.forEach((item, index) => {
        item.wrapper.nextElementSibling = lines[index + 1]?.wrapper || null;
    });
}

const pascal = [line("program Demo;"), line("begin"), line("end.")];
const c = [line("#include <stdio.h>"), line("int main(void) {"), line("return 0; }")];
const asm = [line("mov ax, bx"), line("int 21h")];
connect(pascal);
connect(c);
connect(asm);
pascal[pascal.length - 1].wrapper.nextElementSibling = { nextElementSibling: c[0].wrapper };
c[c.length - 1].wrapper.nextElementSibling = { nextElementSibling: asm[0].wrapper };

const examples = [...pascal, ...c, ...asm].map((item) => item.example);
window.THelpViewerTV.highlightCodeExamples({ querySelectorAll: () => examples });
for (const item of pascal) {
    if (!item.example.classList.contains("code-lang-pascal")) {
        throw new Error("Pascal block was not detected as Pascal");
    }
}
for (const item of c) {
    if (!item.example.classList.contains("code-lang-c")) {
        throw new Error("C block was not detected as C");
    }
}
for (const item of asm) {
    if (!item.example.classList.contains("code-lang-asm")) {
        throw new Error("ASM block was not detected as ASM");
    }
}
if (!c[0].example.innerHTML.includes("code-preproc")) {
    throw new Error("C preprocessor line was not highlighted");
}
if (!asm[0].example.innerHTML.includes("code-asm")) {
    throw new Error("ASM line was not highlighted");
}
'''
    subprocess.run(
        [NODE, "-e", script, str(HIGHLIGHT_PATHS[0])],
        check=True,
        capture_output=True,
        text=True,
    )
