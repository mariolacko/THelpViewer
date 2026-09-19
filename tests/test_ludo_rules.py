from pathlib import Path
import shutil
import subprocess
import unittest

NODE = shutil.which("node")
RULES_PATH = Path("www/assets/tv-games.js").resolve()


@unittest.skipIf(NODE is None, "Node.js is required for JavaScript rule tests")
def test_ludo_rules_cover_entry_capture_home_and_state_roundtrip():
    script = r"""
const assert = require("node:assert/strict");
const rules = require(process.argv[1]);
const { LudoGame, LUDO_COMMON_PATH, LUDO_HOME_PATHS } = rules;

assert.equal(LUDO_COMMON_PATH.length, 40);
assert.equal(new Set(LUDO_COMMON_PATH.map((cell) => cell.join(","))).size, 40);
assert.deepEqual(LUDO_HOME_PATHS.map((path) => path.length), [4, 4, 4, 4]);

const rolls = [0.99, 0.1];
const game = new LudoGame(() => rolls.shift());
assert.deepEqual(game.roll(), { die: 6, legal: [0, 1, 2, 3] });
assert.equal(game.move(2).target, 0);
assert.equal(game.currentPlayer, 0);
assert.equal(game.phase, "roll");
assert.equal(game.roll().die, 1);
assert.deepEqual(game.legalPieces(), [2]);
game.move(2);
assert.equal(game.currentPlayer, 1);

const capture = new LudoGame(() => 0);
capture.pieces[0][0] = 4;
capture.pieces[1][0] = 35;
capture.rollsLeft = 1;
capture.roll();
const captureResult = capture.move(0);
assert.deepEqual(captureResult.captured, [[1, 0]]);
assert.equal(capture.pieces[1][0], -1);

const blockedHome = new LudoGame();
blockedHome.pieces[0] = [40, 42, -1, -1];
assert.equal(blockedHome._targetProgress(0, 0, 3), null);
blockedHome.pieces[0] = [42, -1, -1, -1];
assert.equal(blockedHome._targetProgress(0, 0, 2), null);

const threeAttempts = new LudoGame(() => 0.1);
assert.equal(threeAttempts.roll().die, 1);
assert.equal(threeAttempts.currentPlayer, 0);
assert.equal(threeAttempts.rollsLeft, 2);
assert.equal(threeAttempts.die, 1);

const winner = new LudoGame(() => 0);
winner.pieces[0] = [41, 42, 43, 39];
winner.rollsLeft = 1;
winner.roll();
assert.equal(winner.move(3).winner, 0);
assert.equal(winner.phase, "done");

const restored = new LudoGame();
assert.equal(restored.importState(game.exportState()), true);
assert.deepEqual(restored.exportState(), game.exportState());
assert.equal(restored.importState({ ...game.exportState(), v: 1 }), false);
"""
    subprocess.run(
        [NODE, "-e", script, str(RULES_PATH)],
        check=True,
        capture_output=True,
        text=True,
    )
