import ast
from pathlib import Path
import re
import shutil
import subprocess

import pytest


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


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required")
def test_tetris_preview_centers_every_piece_and_keeps_its_owned_frame():
    assert CSS_PATHS[0].read_bytes() == CSS_PATHS[1].read_bytes()
    assert GAMES_PATH.read_bytes() == Path("www/assets/tv-games.js").read_bytes()
    script = r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
global.window={};global.document={addEventListener(){}};
eval(fs.readFileSync('www/assets/tv-core.js','utf8'));
const TV=window.THelpViewerTV,{TVGroup,TVStaticText,TVRect,TVButton,TVView,escapeHtml,wrapTextLines,bfNormal,sfDisabled,sfActive}=TV;
class TVGameDialog {}
global.getComputedStyle=()=>({getPropertyValue(name){
 for(const [index,token] of Object.entries(TV.TV2_PALETTE_TOKENS)){
  if(name===`--tv-palette-${token}-fg`)return TV.DOS_COLORS[TV.TV2_APP_COLOR_ATTRIBUTES[index-1]&15];
  if(name===`--tv-palette-${token}-bg`)return TV.DOS_COLORS[TV.TV2_APP_COLOR_ATTRIBUTES[index-1]>>4];
 }
 return '';
}});
const source=fs.readFileSync(process.argv[1],'utf8'),start=source.indexOf('const TETRIS_COLS');
eval(source.slice(source.indexOf('const openGamePalettes'),source.indexOf('const {\n    hcGames'))+source.slice(start,source.indexOf('class TVTetrisGameInfo',start))
 +'\nglobalThis.Preview=TVTetrisPreview;globalThis.figures=TETRIS_FIGURES;');
const preview=new Preview(new TVRect(0,5,23,12));
assert(preview instanceof TVGroup);
const children=[...preview.children];
const bounds=view=>[view.bounds.x1,view.bounds.y1,view.bounds.x2,view.bounds.y2];
const checkFrame=(width,height)=>{
 assert.deepEqual(preview.children,children);
 assert(children.every(child=>child instanceof TVStaticText&&child.owner===preview));
 assert.deepEqual(bounds(preview.leftSide),[0,0,1,height]);
 assert.deepEqual(bounds(preview.field),[1,0,width-1,height]);
 assert.deepEqual(bounds(preview.rightSide),[width-1,0,width,height]);
 assert.equal(preview.leftSide.getText(),Array(height).fill('│').join('\n'));
 assert.equal(preview.rightSide.getText(),preview.leftSide.getText());
};
checkFrame(23,7);
for(const [index,figure] of figures.entries()){
 preview.setData(index);checkFrame(23,7);
 assert.equal(preview.getData(),index);
 assert.equal(preview.field.getColor(1),15-index%7);
 const lines=preview.field.getText().split('\n'),occupied=[];
 assert.equal(lines.length,7);
 lines.forEach((line,row)=>{
  assert.equal(line.length,21);assert.equal(line.slice(0,3),'   ');assert.equal(line.slice(-4),'    ');
  for(let col=0;col<7;col++){
   const glyph=line.slice(3+col*2,5+col*2);
   assert(['  ','██'].includes(glyph));if(glyph==='██')occupied.push([row,col]);
  }
 });
 assert.equal(occupied.length,figure.length);
 assert(occupied.every(([r,c])=>r>0&&r<6&&c>0&&c<6),'figure touched its grid edge');
 const normalize=cells=>{const minR=Math.min(...cells.map(([r])=>r)),minC=Math.min(...cells.map(([,c])=>c));
  return cells.map(([r,c])=>[r-minR,c-minC]).sort().map(cell=>cell.join(',')).join(';');};
 assert.equal(normalize(occupied),normalize(figure),'preview changed the figure shape');
}
preview.growTo(19,7);checkFrame(19,7);
assert(preview.field.getText().split('\n').every(line=>line.length===17));
preview.growTo(23,9);checkFrame(23,9);
preview.setData(null);assert.equal(preview.getData(),null);
assert.equal(preview.field.getText(),' '.repeat(21)+('\n'+' '.repeat(21)).repeat(6));
checkFrame(23,9);
'''
    result = subprocess.run(
        [shutil.which("node"), "-e", script, str(GAMES_PATH)],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr


def test_tetris_dialog_uses_dos_navigator_constructor_geometry():
    source = GAMES_PATH.read_text(encoding="utf-8")
    dialog = source[source.index("class TVTetrisDialog"):source.index("// ── Minesweeper")]
    assert "new TVRect(2, 2, 2 + gridWidth, 2 + TETRIS_ROWS)" in dialog
    assert "const infoX = gridWidth + 4" in dialog
    assert "const infoWidth = TETRIS_INFO_WIDTH" in dialog
    assert "const previewView = new TVTetrisPreview(new TVRect(0, 5, infoWidth, 12))" in dialog
    assert "new TVRect(infoX, 1, infoX + infoWidth, 17)" in dialog
    assert 'super(new TVRect(0, 0, 54, 23), "Tetris")' in dialog
    assert 'installHallOfFame(this, "tetris")' in dialog
