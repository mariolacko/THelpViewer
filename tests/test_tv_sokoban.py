"""Regression checks for the ten bundled Sokoban boards."""

from ast import literal_eval
from collections import deque
from pathlib import Path
import re


GAMES = Path("thelpviewer/converter/assets/tv-games.js")


def _levels():
    source = GAMES.read_text(encoding="utf-8")
    block = source.split("const SOKOBAN_LEVELS = [", 1)[1].split("const SOKOBAN_BEST_KEY", 1)[0]
    levels = []
    for width, height, rows in re.findall(
        r"\{\s*w:\s*(\d+),\s*h:\s*(\d+),\s*map:\s*((?:\"[^\"]*\"\s*\+?\s*)+)\}",
        block,
    ):
        board = "".join(literal_eval(row) for row in re.findall(r'"[^\"]*"', rows))
        levels.append((int(width), int(height), board))
    return levels


def _solution(width, height, board):
    walls = {index for index, cell in enumerate(board) if cell == "#"}
    goals = {index for index, cell in enumerate(board) if cell in ".*+"}
    boxes = frozenset(index for index, cell in enumerate(board) if cell in "$*")
    players = [index for index, cell in enumerate(board) if cell in "@+"]
    assert len(board) == width * height
    assert len(players) == 1
    assert boxes and len(goals) == len(boxes)
    start = (players[0], boxes)
    queue = deque([(start, "")])
    seen = {start}
    directions = (("U", 0, -1), ("D", 0, 1), ("L", -1, 0), ("R", 1, 0))
    while queue:
        (player, occupied), path = queue.popleft()
        if occupied <= goals:
            return path
        x, y = player % width, player // width
        for key, dx, dy in directions:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            next_cell = ny * width + nx
            if next_cell in walls:
                continue
            moved_boxes = occupied
            if next_cell in occupied:
                bx, by = nx + dx, ny + dy
                if not (0 <= bx < width and 0 <= by < height):
                    continue
                beyond = by * width + bx
                if beyond in walls or beyond in occupied:
                    continue
                moved_boxes = frozenset((occupied - {next_cell}) | {beyond})
            state = (next_cell, moved_boxes)
            if state not in seen:
                seen.add(state)
                queue.append((state, path + key))
    return None


def test_every_sokoban_level_has_a_legal_solution():
    levels = _levels()
    assert len(levels) == 10
    assert len({board for _, _, board in levels}) == 10
    for number, (width, height, board) in enumerate(levels, 1):
        assert width <= 9 and height <= 10
        path = _solution(width, height, board)
        assert path is not None, f"Sokoban level {number} cannot be solved"
