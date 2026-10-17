import pytest

from thelpviewer.server.downloader.direct import run
from thelpviewer.server.downloader.errors import SourceUnavailable


def test_direct_dry_run_does_not_fetch_or_extract(tmp_path, capsys):
    def unexpected(*_args, **_kwargs):
        pytest.fail("Dry-run started processing")
    assert run(["msdos622"], tmp_path / "downloads", True, unexpected) == []
    assert "HELP.HLP" in capsys.readouterr().out
    assert not (tmp_path / "downloads").exists()


def test_direct_fails_when_pinned_archive_cannot_be_collected(tmp_path):
    def missing(*_args, **_kwargs):
        raise ValueError("Missing archive members: HELP.HLP")
    with pytest.raises(SourceUnavailable, match="Missing archive members: HELP.HLP"):
        run(["msdos622"], tmp_path / "downloads", False, missing)


def test_direct_submits_product_selection_to_the_shared_processor(tmp_path):
    plans = []
    def process(source, **options):
        plans.append((source, options))
        return []
    run(["msdos622", "qb45"], tmp_path / "downloads", False, process)
    assert [source.collection for source, _ in plans] == [
        "Microsoft MS-DOS 6.22", "Microsoft QuickBASIC 4.5"]
    assert plans[0][0].members == ("HELP.HLP",)
    assert all(options["url"].startswith("https://") for _, options in plans)


def test_provider_leaves_originals_and_download_caches_to_the_processor(tmp_path):
    original = tmp_path / "sources/Microsoft MS-DOS 6.22/HELP.HLP"
    original.parent.mkdir(parents=True)
    original.write_bytes(b"existing original")
    seen = []
    def process(source, **_options):
        seen.append(source)
        return []
    assert run(["msdos622"], tmp_path / "downloads", False, process) == []
    assert seen and original.read_bytes() == b"existing original"
    assert not (tmp_path / "downloads").exists()
