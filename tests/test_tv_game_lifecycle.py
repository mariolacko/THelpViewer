from pathlib import Path
import shutil
import subprocess

import pytest


GAME_PATHS = (
    Path("www/assets/tv-games.js"),
    Path("thelpviewer/converter/assets/tv-games.js"),
)

NODE = shutil.which("node")


def test_hall_of_fame_uses_managed_modal_dialogs_for_every_game():
    assert GAME_PATHS[0].read_bytes() == GAME_PATHS[1].read_bytes()
    source = GAME_PATHS[0].read_text(encoding="utf-8")
    helper = source[
        source.index("class TVBestNameDialog"):
        source.index("// ── Puzzle", source.index("class TVBestNameDialog"))
    ]

    assert "const manager = ownerDialog?.manager || null" in helper
    assert "manager.register(`highscore:${++bestNamePromptSequence}`, dlg)" in helper
    assert "if (this.finished) { return; }" in helper
    assert "this.destroy();" in helper
    assert 'event.command === "best-ok"' in helper
    assert "const HALL_OF_FAME_LIMIT = 10" in helper
    assert "function showHallOfFame(ownerDialog, game)" in helper
    hall = helper[
        helper.index("function hallOfFameRows(game, entries)"):
        helper.index("function installHallOfFame", helper.index("function hallOfFameRows(game, entries)"))
    ]
    assert "new TVGroup(new TVRect(0, 0, 43, 13))" in hall
    assert "new TVHallRow(new TVRect(" in hall
    assert 'new TVStaticText(new TVRect(1, 3, 42, 4), "\\x03No scores yet.")' in hall
    assert "class TVHallBody" not in source
    assert "class TVHallEmpty" not in source
    assert "class TVInfoSeparator" not in source
    assert "class TVMinesValue" not in source
    assert "class TVMinesTimer" not in source
    assert '<div class="tv-hall-' not in hall
    assert 'fetch(`/api/hall-of-fame/${encodeURIComponent(game)}`' in helper
    assert "return saveLocalHallOfFameScore(game, score, name, note, level);" in helper
    assert "manager.register(`hall:${game}:${++bestNamePromptSequence}`, dlg)" in helper
    assert "class TVGameDialog extends TVDialog" in helper
    assert "this.frame.createTitleControl(" in helper
    assert 'event.command === "hall-of-fame"' in helper
    assert '"hall-of-fame"' in helper
    assert source.count("installHallOfFame(this,") == 12
    assert '"~T~op 10", "tetris-top10"' in source
    assert 'showHallOfFame(this.gameWindow(), this.pentix ? "pentix" : "tetris")' in source
    for game in ("puzzle", "mines", "breakout", "sokoban", "lines", "reversi", "ludo", "mastermind", "snake", "tron", "hanoi"):
        assert f'installHallOfFame(this, "{game}")' in source
        assert f'"{game}": {{ title:' in helper or f'{game}: {{ title:' in helper
    assert 'tetris: { title:' in helper
    assert 'installHallOfFame(this, "tetris")' in source
    # Tetris/Pentix owns its original Top 10 flow; the other games share the
    # generic score submission helper.
    assert source.count('submitHallOfFameScore(this, "') >= 11


@pytest.mark.skipif(NODE is None, reason="Node.js is required for Mastermind behavior tests")
def test_mastermind_scores_exact_and_misplaced_pegs_with_duplicates():
    script = r'''
const { MastermindGame } = require(process.argv[1]);
const game = new MastermindGame(() => 0);
game.reset([0, 0, 1, 2]);
game.currentGuess = [0, 1, 0, 3];
const first = game.submitGuess();
if (first.exact !== 1 || first.misplaced !== 2 || game.status !== "playing") {
    throw new Error(`bad duplicate scoring: ${JSON.stringify(first)}`);
}
game.currentGuess = [0, 0, 1, 2];
const win = game.submitGuess();
if (win.exact !== 4 || win.misplaced !== 0 || game.status !== "won" || game.turns.length !== 2) {
    throw new Error("winning guess was not recorded");
}
const loss = new MastermindGame(() => 0, { maxTurns: 1 });
loss.reset([0, 0, 0, 0]);
loss.currentGuess = [1, 1, 1, 1];
loss.submitGuess();
if (loss.status !== "lost" || loss.submitGuess() !== null) {
    throw new Error("turn limit was not enforced");
}
'''
    result = subprocess.run(
        [NODE, "-e", script, str(GAME_PATHS[0].resolve())],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_games_pause_background_work_and_clear_transient_input():
    source = GAME_PATHS[0].read_text(encoding="utf-8")
    breakout = source[source.index("class TVBreakOutDialog"):source.index("class TVSokobanDialog")]
    reversi = source[source.index("class TVReversiDialog"):source.index("class TVLudoDialog")]
    ludo = source[source.index("class TVLudoDialog"):source.index("class TVSnakeDialog")]
    snake = source[source.index("class TVSnakeDialog"):]
    tron = source[source.index("class TVTronDialog"):source.index("class TVHanoiDialog")]
    mines = source[source.index("class TVMinesDialog"):source.index("class TVBreakOutDialog")]

    assert 'document.addEventListener("keydown"' not in breakout
    assert "onDialogKeyUp(event)" in breakout
    assert "this.keysDown.clear();\n        super.close();" in breakout
    assert "if (!this.isActive() || !document.hasFocus()) {\n                this.keysDown.clear();" in breakout

    assert "this.computerTimer = null" in reversi
    assert "window.clearTimeout(this.computerTimer)" in reversi
    assert "this._scheduleComputerMove();" in reversi
    assert "if (!this.isActive()) {\n                this._scheduleComputerMove();" in reversi

    assert "if (!this.isActive()) {\n                this.scheduleCpu();" in ludo
    assert "if (!this.isActive()) { return; }\n            this.tick();" in snake
    assert "if (!this.isActive()) { return; }\n            this.seconds++;" in mines
    assert "if (!this.isActive() || !document.hasFocus()) {\n                this.game.clearPendingDirections();" in tron
    assert "this.inactivePause = true;" in tron


@pytest.mark.skipif(NODE is None, reason="Node.js is required for game behavior tests")
def test_tron_resolves_simultaneous_input_and_collisions_from_one_tick():
    script = r'''
const { TronGame } = require(process.argv[1]);
const game = new TronGame({ width: 10, height: 8 });
game.players = [
    { x: 4, y: 4, dx: 1, dy: 0, alive: true },
    { x: 6, y: 4, dx: -1, dy: 0, alive: true },
];
game.trails = [new Set(["4,4"]), new Set(["6,4"])];
game.clearPendingDirections();
game.tick();
if (game.status !== "draw" || game.players.some((player) => player.alive)) {
    throw new Error("same-cell collision was not resolved simultaneously");
}

game.reset();
const before = game.players.map((player) => ({ x: player.x, y: player.y }));
if (!game.queueDirection(0, 0, -1) || !game.queueDirection(1, 0, 1)) {
    throw new Error("simultaneous direction input was rejected");
}
if (game.queueDirection(0, -1, 0)) {
    throw new Error("a direct reverse turn was accepted");
}
game.tick();
if (game.players[0].x !== before[0].x || game.players[0].y !== before[0].y - 1
    || game.players[1].x !== before[1].x || game.players[1].y !== before[1].y + 1) {
    throw new Error("queued player directions were not applied in the same tick");
}
'''
    result = subprocess.run(
        [NODE, "-e", script, str(GAME_PATHS[0].resolve())],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for game behavior tests")
def test_hanoi_validates_moves_tracks_history_and_undoes():
    script = r'''
const { HanoiGame } = require(process.argv[1]);
const game = new HanoiGame(3);
if (game.minimumMoves !== 7 || game.move(1, 2)) {
    throw new Error("initial Hanoi state is invalid");
}
if (!game.move(0, 2) || !game.move(0, 1) || game.move(1, 2)) {
    throw new Error("Hanoi legal-move validation failed");
}
if (game.moves !== 2 || !game.undo() || game.moves !== 1
    || game.top(0) !== 2 || game.top(1) !== null) {
    throw new Error("Hanoi undo did not restore the previous state");
}
game.reset();
for (const [from, to] of [[0, 2], [0, 1], [2, 1], [0, 2], [1, 0], [1, 2], [0, 2]]) {
    if (!game.move(from, to)) { throw new Error(`legal solution move ${from}->${to} failed`); }
}
if (game.status !== "won" || game.moves !== 7 || game.history.length !== 7) {
    throw new Error("three-disk solution was not recognized");
}
if (!game.undo() || game.status !== "playing" || game.moves !== 6) {
    throw new Error("undo after completion failed");
}
'''
    result = subprocess.run(
        [NODE, "-e", script, str(GAME_PATHS[0].resolve())],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for game behavior tests")
def test_mines_first_reveal_is_safe_and_board_counts_are_valid():
    script = r'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("const MINES_ROWS");
const end = source.indexOf("// ── BreakOut", start);
class TVGameDialog {}
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
class TVGameDialog {}
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
