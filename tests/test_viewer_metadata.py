from pathlib import Path

from thelpviewer import __authors__, __version__
from thelpviewer.server.converter.writers.bundle import _render_bundle_index_html, _write_bundle_index
from thelpviewer.server.config import load_config


def test_checked_in_bundle_index_matches_generated_project_metadata():
    rendered = _render_bundle_index_html()

    assert Path("www/index.html").read_text(encoding="utf-8") == rendered
    assert f'data-tv-generator-version="{__version__}"' in rendered
    assert f'data-tv-authors="{__authors__}"' in rendered
    assert 'google-site-verification' not in rendered
    assert 'href="assets/thelp-icon.svg"' in rendered


def test_bundle_index_copies_public_preview_image(tmp_path):
    _write_bundle_index(tmp_path)
    assert (tmp_path / "assets" / "Thelp.png").read_bytes() == Path("Thelp.png").read_bytes()


def test_about_dialog_reads_generated_project_metadata():
    asset_paths = (
        Path("www/assets/tv-dialogs.js"),
        Path("thelpviewer/server/converter/assets/tv-dialogs.js"),
    )
    assert asset_paths[0].read_bytes() == asset_paths[1].read_bytes()

    source = asset_paths[0].read_text(encoding="utf-8")
    assert "body.dataset.tvGeneratorVersion" in source
    assert "body.dataset.tvAuthors" in source
    assert '"0.1.0"' not in source


def test_google_verification_setting_comes_from_environment(monkeypatch):
    monkeypatch.setenv("THELP_GOOGLE_SITE_VERIFICATION", "  verification-token  ")
    assert load_config().google_site_verification == "verification-token"
