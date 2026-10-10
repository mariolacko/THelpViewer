from pathlib import Path

from thelpviewer.server.downloader.slunecnice import DATABASE_FILENAMES, _collect_database_files, find_download_url


def test_find_game_cheater_signed_download_url() -> None:
    html = """
    <a href="/sw/game-cheater/stahnout/4321/1/?md5=abc&amp;expires=123">
      download.slunecnice.cz
    </a>
    """
    assert find_download_url(html, "https://www.slunecnice.cz/sw/game-cheater/stahnout/") == (
        "https://www.slunecnice.cz/sw/game-cheater/stahnout/4321/1/?md5=abc&expires=123"
    )


def test_collects_only_game_cheater_database_files(tmp_path: Path) -> None:
    data_dir = tmp_path / "GCDATA"
    data_dir.mkdir()
    for name in DATABASE_FILENAMES:
        (data_dir / name).write_bytes(b"data")
    (tmp_path / "UFAND.EXE").write_bytes(b"program")

    files = _collect_database_files(tmp_path)

    assert {path.name for path in files} == DATABASE_FILENAMES
