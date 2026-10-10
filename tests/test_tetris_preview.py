import ast
from pathlib import Path
import re


GAMES_PATH = Path("thelpviewer/server/converter/assets/tv-games.js")
CSS_PATHS = (
    Path("thelpviewer/server/converter/assets/turbovision.css"),
    Path("www/assets/turbovision.css"),
)


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


def test_tetris_next_frame_uses_dialog_background_outside_the_black_preview():
    assert CSS_PATHS[0].read_bytes() == CSS_PATHS[1].read_bytes()
    css = CSS_PATHS[0].read_text(encoding="utf-8")

    preview_rule = re.search(r"\[data-tv-tetris-preview\] \{(.*?)\n\}", css, re.DOTALL)
    assert preview_rule is not None
    assert "background: var(--tv-dialog-bg);" in preview_rule.group(1)
    assert "grid-template-columns: 1ch 3ch repeat(7, 2ch) 4ch 1ch;" in preview_rule.group(1)

    assert re.search(
        r"\.tv-tetris-preview-pad,\s*"
        r"\[data-tv-tetris-preview\] \.tv-tetris-cell \{[^}]*background: #000000;",
        css,
        re.DOTALL,
    )


def test_tetris_dialog_uses_dos_navigator_constructor_geometry():
    source = GAMES_PATH.read_text(encoding="utf-8")
    dialog = source[source.index("class TVTetrisDialog"):source.index("// ── Minesweeper")]
    assert "new TVRect(2, 2, 2 + gridWidth, 2 + TETRIS_ROWS)" in dialog
    assert "const infoX = gridWidth + 4" in dialog
    assert "const infoWidth = TETRIS_INFO_WIDTH" in dialog
    assert "const previewView = new TVTetrisPreview(new TVRect())" in dialog
    assert "new TVRect(infoX, 1, infoX + infoWidth, 17)" in dialog
    assert 'super(new TVRect(0, 0, 54, 23), "Tetris")' in dialog
    assert 'installHallOfFame(this, "tetris")' in dialog
