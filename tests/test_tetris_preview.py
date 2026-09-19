import ast
from pathlib import Path
import re


GAMES_PATH = Path("thelpviewer/converter/assets/tv-games.js")


def _javascript_constant(source: str, name: str) -> int:
    match = re.search(rf"const {name} = (\d+);", source)
    assert match is not None
    return int(match.group(1))


def test_every_tetris_piece_has_a_cell_margin_inside_the_next_preview():
    source = GAMES_PATH.read_text(encoding="utf-8")
    figures_match = re.search(
        r"const TETRIS_FIGURES = (\[.*?\]);\nconst TETRIS_CELL_COUNT",
        source,
        re.DOTALL,
    )
    assert figures_match is not None

    figures = ast.literal_eval(figures_match.group(1))
    preview_cols = _javascript_constant(source, "TETRIS_PREVIEW_COLS")
    preview_rows = _javascript_constant(source, "TETRIS_PREVIEW_ROWS")

    for figure in figures:
        rows = [cell[0] for cell in figure]
        cols = [cell[1] for cell in figure]
        assert max(rows) - min(rows) + 1 <= preview_rows - 2
        assert max(cols) - min(cols) + 1 <= preview_cols - 2
