from thelpviewer.server.converter.base import HelpDocument
from thelpviewer.server.converter.writers.html import HelpHtmlRenderer


def _renderer(metadata: dict[str, object] | None = None) -> HelpHtmlRenderer:
    return HelpHtmlRenderer(
        HelpDocument(
            format_name="thelp",
            source_name="TEST.HLP",
            topics=[],
            index_entries=[],
            metadata=metadata or {},
        )
    )


def test_generic_help_window_min_width_keeps_outer_frame_width():
    renderer = _renderer()

    cols, rows = renderer._window_geometry()
    min_cols, min_rows = renderer._window_min_geometry(cols, rows)

    assert (cols, rows) == (82, 24)
    assert (min_cols, min_rows) == (82, 24)


def test_explicit_help_geometry_keeps_exact_minimum():
    renderer = _renderer({"width": 80, "height": 25})

    cols, rows = renderer._window_geometry()
    min_cols, min_rows = renderer._window_min_geometry(cols, rows)

    assert (cols, rows) == (83, 28)
    assert (min_cols, min_rows) == (83, 28)