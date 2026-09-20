from pathlib import Path
import re


CSS_PATHS = (
    Path("www/assets/turbovision.css"),
    Path("thelpviewer/converter/assets/turbovision.css"),
)


def test_border_fill_content_does_not_change_frame_width():
    assert CSS_PATHS[0].read_bytes() == CSS_PATHS[1].read_bytes()
    css = CSS_PATHS[0].read_text(encoding="utf-8")
    rule = re.search(r"^\.tv-border-fill \{(.*?)\n\}", css, re.DOTALL | re.MULTILINE)

    assert rule is not None
    assert "contain: inline-size;" in rule.group(1)
