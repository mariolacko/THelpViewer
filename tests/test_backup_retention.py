"""Retain bounded recovery generations, only after a successful replacement."""

import json
from pathlib import Path
import uuid

import pytest

from thelpviewer.server.converter.build import build_help_groups
from thelpviewer.server.dos.store import DosPromptStore
from thelpviewer.server.midi.library import MidiLibrary
from thelpviewer.server.rebuild import prune_backups


def snapshot(root, prefix):
    path = root / f"{prefix}{uuid.uuid4().hex}"
    path.mkdir(parents=True)
    (path / "saved.txt").write_text(path.name)
    return path


def test_retention_preserves_newest_copy_other_families_and_foreign_names(tmp_path):
    old = [snapshot(tmp_path, "dos-base-"), snapshot(tmp_path, "dos-packages-")]
    newest = snapshot(tmp_path, "dos-packages-")
    other = snapshot(tmp_path, "midi-")
    foreign = tmp_path / "dos-base-not-a-managed-uuid"
    foreign.mkdir()
    # Pin the just-published recovery copy, even if an older sibling was touched.
    (old[0] / "extra").write_text("new directory timestamp")
    removed = prune_backups(newest, ("dos-base-", "dos-packages-"), 1)
    assert set(removed) == set(old)
    assert newest.is_dir() and other.is_dir() and foreign.is_dir()


def test_retention_does_not_follow_links_or_delete_a_linked_tree(tmp_path, caplog):
    root, outside = tmp_path / "backups", tmp_path / "outside"
    outside.mkdir()
    saved = outside / "private.txt"
    saved.write_text("permanent")
    old = snapshot(root, "midi-")
    (old / "external").symlink_to(outside, target_is_directory=True)
    linked = root / f"midi-{uuid.uuid4().hex}"
    linked.symlink_to(outside, target_is_directory=True)
    newest = snapshot(root, "midi-")
    assert prune_backups(newest, ("midi-",), 1) == []
    assert saved.read_text() == "permanent" and old.is_dir() and linked.is_symlink()
    assert "Skipping linked backup" in caplog.text
    proxy = tmp_path / "linked-root"
    proxy.symlink_to(root, target_is_directory=True)
    assert prune_backups(proxy / newest.name, ("midi-",), 1) == []
    assert "symbolic links" in caplog.text


def test_retention_removal_error_is_logged_and_keeps_committed_data(tmp_path, monkeypatch, caplog):
    old, newest = snapshot(tmp_path, "midi-"), snapshot(tmp_path, "midi-")

    def fail(path):
        raise PermissionError("read only")

    monkeypatch.setattr("thelpviewer.server.rebuild.shutil.rmtree", fail)
    assert prune_backups(newest, ("midi-",), 1) == []
    assert old.is_dir() and newest.is_dir()
    assert "Could not remove old backup" in caplog.text


@pytest.mark.parametrize("keep", [None, 0, -1, 101, True, "2", 1.5])
def test_invalid_retention_never_removes_a_backup(tmp_path, keep):
    newest = snapshot(tmp_path, "midi-")
    with pytest.raises(ValueError, match="Backup count"):
        prune_backups(newest, ("midi-",), keep)
    assert newest.is_dir()


@pytest.mark.parametrize("keep", [2, 3])
def test_help_build_retention_and_conversion_failure(tmp_path, monkeypatch, keep):
    sources, helps = tmp_path / "sources", tmp_path / "helps"
    source = sources / "HelpPC 2.10" / "C.TXT"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"@C language\r\n:ReferenceTopic\r\n%Reference text\r\n")
    options = {} if keep == 2 else {"backup_count": keep}
    backups = []
    for _ in range(5):
        result = build_help_groups(["dos-reference"], sources, helps, **options)
        if result["backup"]:
            backups.append(Path(result["backup"]))
    root = tmp_path / "backups/help"
    assert set(root.glob("help-*")) == set(backups[-keep:])
    assert not list(tmp_path.glob(".helps-previous-*"))
    assert all((backup / "HelpPC 2.10/c.json.gz").is_file() for backup in backups[-keep:])

    def fail(*args, **kwargs):
        raise ValueError("conversion failed")

    monkeypatch.setattr("thelpviewer.server.converter.build.export_bundle_tree", fail)
    before = set(root.glob("help-*"))
    with pytest.raises(ValueError, match="conversion failed"):
        build_help_groups(["dos-reference"], sources, helps, backup_count=1)
    assert set(root.glob("help-*")) == before
    assert (helps / "HelpPC 2.10/c.json.gz").is_file()


def test_failed_help_publication_restores_live_tree_without_pruning(tmp_path, monkeypatch):
    sources, helps = tmp_path / "sources", tmp_path / "helps"
    source = sources / "HelpPC 2.10" / "C.TXT"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"@C language\r\n:ReferenceTopic\r\n%Reference text\r\n")
    for _ in range(4):
        build_help_groups(["dos-reference"], sources, helps, backup_count=3)
    before = set((tmp_path / "backups/help").glob("help-*"))
    live = (helps / "HelpPC 2.10/c.json.gz").read_bytes()
    rename = Path.rename

    def fail_publish(path, target):
        if path.name.startswith(".helps-build-") and target == helps:
            raise OSError("cannot publish")
        return rename(path, target)

    monkeypatch.setattr(Path, "rename", fail_publish)
    with pytest.raises(OSError, match="cannot publish"):
        build_help_groups(["dos-reference"], sources, helps, backup_count=1)
    assert set((tmp_path / "backups/help").glob("help-*")) == before
    assert not list(tmp_path.glob(".helps-previous-*"))
    assert (helps / "HelpPC 2.10/c.json.gz").read_bytes() == live
    assert not list(tmp_path.glob(".helps-build-*"))


@pytest.mark.parametrize("keep", [1, 2, 3])
def test_dos_base_and_package_changes_share_configured_limit(tmp_path, keep):
    manifest = tmp_path / "dos.json"
    manifest.write_text(json.dumps({"sources": [], "files": [{"path": "TEST.TXT", "text": ["shared"]}]}))
    store = DosPromptStore(tmp_path / "dos", manifest)
    if keep != 2:
        store.settings.update({"backup_count": keep})
    store.prepare()
    backups = []
    for operation in ("rebuild", "configure", "rebuild", "configure", "rebuild"):
        if operation == "configure":
            store.configure([])
        else:
            store.rebuild()
            store._worker.join(timeout=5)
            assert not store._worker.is_alive()
        assert store.state == "ready", store.error
        backups.append(tmp_path / store.backup)
    assert set((tmp_path / "backups/dos").iterdir()) == set(backups[-keep:])
    assert all((backup / "c/TEST.TXT").is_file() for backup in backups[-keep:])
    # A failed rebuild retains its new recovery copy and all prior snapshots.
    before = set((tmp_path / "backups/dos").iterdir())
    manifest.write_text("not valid JSON")
    store.rebuild()
    store._worker.join(timeout=5)
    assert store.state == "error"
    assert before < set((tmp_path / "backups/dos").iterdir())


@pytest.mark.parametrize("keep", [2, 3])
@pytest.mark.parametrize("failure_state", ["partial", "error"])
def test_midi_retention_and_partial_failure_preserve_recovery(tmp_path, monkeypatch, keep, failure_state):
    manifest = tmp_path / "midi.json"
    manifest.write_text('{"sources": []}')
    library = MidiLibrary(tmp_path / "midi", manifest)
    if keep != 2:
        library.settings.update({"backup_count": keep})
    backups = []
    for _ in range(5):
        library.rebuild()
        library._worker.join(timeout=5)
        assert not library._worker.is_alive()
        assert library.rebuild_status()["state"] == "ready"
        backups.append(tmp_path / library.rebuild_status()["backup"])
    assert set((tmp_path / "backups/midi").iterdir()) == set(backups[-keep:])
    before = set((tmp_path / "backups/midi").iterdir())

    def partial():
        library._state = failure_state
        library._errors = ["source unavailable"]

    monkeypatch.setattr(library, "run_once", partial)
    library.rebuild()
    library._worker.join(timeout=5)
    assert library.rebuild_status()["state"] == failure_state
    assert before < set((tmp_path / "backups/midi").iterdir())


def test_help_backup_uses_configured_state_directory_and_retains_rollback_on_archive_error(tmp_path, monkeypatch, caplog):
    sources, helps = tmp_path / "var/sources", tmp_path / "data/helps"
    backups = tmp_path / "var/backups/help"
    source = sources / "HelpPC 2.10/C.TXT"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"@C language\r\n:Reference\r\n%Help\r\n")
    options = {"backup_dir": backups}
    build_help_groups(["dos-reference"], sources, helps, **options)
    result = build_help_groups(["dos-reference"], sources, helps, **options)
    assert Path(result["backup"]).parent == backups
    assert not list(helps.parent.glob(".helps-previous-*"))
    def fail(*_args):
        raise OSError("backup volume unavailable")
    monkeypatch.setattr("thelpviewer.server.converter.build.relocate_directory", fail)
    result = build_help_groups(["dos-reference"], sources, helps, **options)
    retained = Path(result["backup"])
    assert retained.parent == helps.parent and retained.name.startswith(".helps-previous-")
    assert (retained / "HelpPC 2.10/c.json.gz").is_file()
    assert (helps / "HelpPC 2.10/c.json.gz").is_file()
    assert "recovery copy remains" in caplog.text
