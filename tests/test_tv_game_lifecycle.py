from pathlib import Path
import shutil
import subprocess

import pytest


GAME_PATHS = (
    Path("www/assets/tv-games.js"),
    Path("thelpviewer/converter/assets/tv-games.js"),
)

NODE = shutil.which("node")


def test_high_score_prompt_is_a_managed_modal_dialog():
    assert GAME_PATHS[0].read_bytes() == GAME_PATHS[1].read_bytes()
    source = GAME_PATHS[0].read_text(encoding="utf-8")
    helper = source[
        source.index("function showBestNamePrompt"):
        source.index("// ── Puzzle", source.index("function showBestNamePrompt"))
    ]

    assert "const manager = ownerDialog?.manager || null" in helper
    assert "manager.register(`highscore:${++bestNamePromptSequence}`, dlg)" in helper
    assert "if (finished) { return; }" in helper
    assert "dlg.destroy();" in helper
    assert source.count("showBestNamePrompt(this, this.score") == 4
    assert "showBestNamePrompt(desktop, this.score" not in source


def test_games_pause_background_work_and_clear_transient_input():
    source = GAME_PATHS[0].read_text(encoding="utf-8")
    breakout = source[source.index("class TVBreakOutDialog"):source.index("class TVSokobanDialog")]
    reversi = source[source.index("class TVReversiDialog"):source.index("class TVLudoDialog")]
    ludo = source[source.index("class TVLudoDialog"):source.index("class TVSnakeDialog")]
    snake = source[source.index("class TVSnakeDialog"):]
    mines = source[source.index("class TVMinesDialog"):source.index("class TVBreakOutDialog")]

    assert 'this._onWindowBlur = () => this.keysDown.clear()' in breakout
    assert "this.keysDown.clear();\n        super.close();" in breakout
    assert "if (!this.isActive()) {\n                this.keysDown.clear();" in breakout

    assert "this.computerTimer = null" in reversi
    assert "window.clearTimeout(this.computerTimer)" in reversi
    assert "this._scheduleComputerMove();" in reversi
    assert "if (!this.isActive()) {\n                this._scheduleComputerMove();" in reversi

    assert "if (!this.isActive()) {\n                this.scheduleCpu();" in ludo
    assert "if (!this.isActive()) { return; }\n            this.tick();" in snake
    assert "if (!this.isActive()) { return; }\n            this.seconds++;" in mines


@pytest.mark.skipif(NODE is None, reason="Node.js is required for game behavior tests")
def test_mines_first_reveal_is_safe_and_board_counts_are_valid():
    script = r'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("const MINES_ROWS");
const end = source.indexOf("// ── BreakOut", start);
class TVDialog {}
eval(source.slice(start, end) + "\nglobalThis.TestMines = TVMinesDialog;");

const rows = 9;
const cols = 9;
const game = Object.create(TestMines.prototype);
game.board = Array.from({ length: rows }, () => new Array(cols).fill(0));
game.revealed = Array.from({ length: rows }, () => new Array(cols).fill(false));
game.flagged = Array.from({ length: rows }, () => new Array(cols).fill(false));
game.gameOver = false;
game.won = false;
game.started = false;
game.minesPlaced = false;
game.startTimer = () => {};
game.stopTimer = () => {};
game.render = () => {};

game.revealCell(4, 4);
if (game.board[4][4] === -1 || !game.revealed[4][4]) {
    throw new Error("the first revealed cell must be safe and revealed");
}
const mines = game.board.flat().filter((value) => value === -1).length;
if (mines !== 10) { throw new Error(`expected 10 mines, got ${mines}`); }
for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
        if (game.board[r][c] === -1) { continue; }
        let adjacent = 0;
        for (let dr = -1; dr <= 1; dr++) {
            for (let dc = -1; dc <= 1; dc++) {
                const nr = r + dr;
                const nc = c + dc;
                if (nr >= 0 && nr < rows && nc >= 0 && nc < cols && game.board[nr][nc] === -1) {
                    adjacent++;
                }
            }
        }
        if (game.board[r][c] !== adjacent) {
            throw new Error(`invalid adjacent count at ${r},${c}`);
        }
    }
}
'''
    subprocess.run(
        [NODE, "-e", script, str(GAME_PATHS[0])],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.mark.skipif(NODE is None, reason="Node.js is required for game behavior tests")
def test_mines_keyboard_moves_cursor_and_toggles_flags():
    script = r'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("const MINES_ROWS");
const end = source.indexOf("// ── BreakOut", start);
class TVDialog {}
eval(source.slice(start, end) + "\nglobalThis.TestMines = TVMinesDialog;");

const game = Object.create(TestMines.prototype);
game.cursorRow = 4;
game.cursorCol = 4;
game.gameOver = false;
game.won = false;
game.revealed = Array.from({ length: 9 }, () => new Array(9).fill(false));
game.flagged = Array.from({ length: 9 }, () => new Array(9).fill(false));
game.isActive = () => true;
let focused = false;
game.render = (focusCursor) => { focused = focusCursor; };

const key = (value) => {
    let prevented = false;
    game.onKeyDown({ key: value, target: null, preventDefault: () => { prevented = true; } });
    if (!prevented) { throw new Error(`${value} was not handled`); }
};
key("ArrowLeft");
if (game.cursorRow !== 4 || game.cursorCol !== 3 || !focused) {
    throw new Error("ArrowLeft did not move and focus the board cursor");
}
key("f");
if (!game.flagged[4][3]) { throw new Error("F did not toggle a flag"); }

let clickedFocus = false;
game.revealCell = (r, c, focusCursor) => { clickedFocus = r === 2 && c === 7 && focusCursor; };
game.onCellClick({
    target: { closest: () => ({ getAttribute: (name) => name.endsWith("-r") ? "2" : "7" }) },
});
if (!clickedFocus) { throw new Error("mouse reveal did not preserve the board cursor focus"); }
'''
    subprocess.run(
        [NODE, "-e", script, str(GAME_PATHS[0])],
        check=True,
        capture_output=True,
        text=True,
    )
