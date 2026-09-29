import pytest

from thelpviewer.downloader.direct import run
from thelpviewer.downloader.extractor import ExtractorTools


def test_direct_dry_run_does_not_fetch_or_extract(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        "thelpviewer.downloader.direct.download_file",
        lambda *_: pytest.fail("dry-run downloaded a file"),
    )

    collected = run(
        ["msdos622"],
        tmp_path / "sources",
        tmp_path / "downloads",
        True,
        ExtractorTools(None, None, None),
    )

    assert collected == []
    assert "HELP.HLP" in capsys.readouterr().out


def test_direct_fails_when_pinned_archive_cannot_be_collected(tmp_path, monkeypatch):
    monkeypatch.setattr("thelpviewer.downloader.direct.download_file", lambda _url, dest: dest)
    monkeypatch.setattr(
        "thelpviewer.downloader.direct.collect_archive_members",
        lambda *_: (_ for _ in ()).throw(ValueError("Missing archive members: HELP.HLP")),
    )

    with pytest.raises(RuntimeError, match="Missing archive members: HELP.HLP"):
        run(
            ["msdos622"],
            tmp_path / "sources",
            tmp_path / "downloads",
            False,
            ExtractorTools(None, None, None),
        )


def test_direct_stages_products_under_their_own_names(tmp_path, monkeypatch):
    labels = []
    monkeypatch.setattr("thelpviewer.downloader.direct.download_file", lambda _url, dest: dest)

    def fake_collect(_archive, _members, label, _sources_dir, _extractor):
        labels.append(label)
        return []

    monkeypatch.setattr("thelpviewer.downloader.direct.collect_archive_members", fake_collect)
    run(
        ["msdos622", "qb45"],
        tmp_path / "sources",
        tmp_path / "downloads",
        False,
        ExtractorTools(None, None, None),
    )

    assert labels == [
        "Microsoft MS-DOS 6.22",
        "Microsoft QuickBASIC 4.5",
    ]


def test_direct_skips_files_already_collected_by_archive_search(tmp_path, monkeypatch):
    source = tmp_path / "sources" / "Microsoft MS-DOS 6.22" / "HELP.HLP"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"existing")
    monkeypatch.setattr(
        "thelpviewer.downloader.direct.download_file",
        lambda *_: pytest.fail("existing candidate was downloaded twice"),
    )

    assert run(
        ["msdos622"],
        tmp_path / "sources",
        tmp_path / "downloads",
        False,
        ExtractorTools(None, None, None),
    ) == []
