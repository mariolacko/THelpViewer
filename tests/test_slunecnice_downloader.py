from io import BytesIO
from pathlib import Path
import zipfile
import pytest

from thelpviewer.server.downloader.slunecnice import find_download_url
from thelpviewer.server.downloader.catalog import product_spec
from thelpviewer.server.converter.ingest import HelpInput, ingest_help
from thelpviewer.server.downloader.errors import SourceUnavailable


def test_find_game_cheater_signed_download_url() -> None:
    html = """
    <a href="/sw/game-cheater/stahnout/4321/1/?md5=abc&amp;expires=123">
      download.slunecnice.cz
    </a>
    """
    assert find_download_url(html, "https://www.slunecnice.cz/sw/game-cheater/stahnout/") == (
        "https://www.slunecnice.cz/sw/game-cheater/stahnout/4321/1/?md5=abc&expires=123"
    )


def test_find_program_literal_without_following_partner_offer():
    html = r'''
    <script>
    var partnerUrl = "https://bits.avcdn.net/gen?productid=1968";
    var softwareUrl = "https:\/\/www.slunecnice.cz\/sw\/game-cheater\/stahnout\/4321\/1\/?md5=abc&expires=123";
    window.location.href = partnerUrl;
    </script>
    '''
    assert find_download_url(html, "https://www.slunecnice.cz/sw/game-cheater/stahnout/") == (
        "https://www.slunecnice.cz/sw/game-cheater/stahnout/4321/1/?md5=abc&expires=123"
    )


@pytest.mark.parametrize("url", [
    "https://unrelated.example/sw/game-cheater/stahnout/4321/1/?md5=abc&expires=123",
    "http://www.slunecnice.cz/sw/game-cheater/stahnout/4321/1/?md5=abc&expires=123",
    "https://www.slunecnice.cz/sw/other/stahnout/4321/1/?md5=abc&expires=123",
    "https://www.slunecnice.cz/sw/game-cheater/stahnout/4321/1/?md5=abc",
])
def test_unavailable_or_unrelated_download_is_a_recoverable_source_failure(url):
    import json
    with pytest.raises(SourceUnavailable, match="download link was not found"):
        find_download_url(f"var softwareUrl = {json.dumps(url)};",
                          "https://www.slunecnice.cz/sw/game-cheater/stahnout/")


def test_collects_only_game_cheater_database_files(tmp_path: Path) -> None:
    names = product_spec("game-cheater").conversion.required_filenames
    inner = BytesIO()
    with zipfile.ZipFile(inner, "w") as archive:
        for name in names:
            archive.writestr("GCDATA/" + name, b"data")
        archive.writestr("UFAND.EXE", b"program")
    source = tmp_path / "installer.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("INSTGC.EXE", inner.getvalue())
    files = ingest_help(HelpInput(source, "Game-Cheater", members=names, inner_member="INSTGC.EXE"),
                        tmp_path / "sources", None)
    assert {path.name for path in files} == {name.upper() for name in names}
