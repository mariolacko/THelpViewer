"""Permanent data is isolated from rebuildable state, with verified migration."""

import base64
import errno
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import shutil
import uuid

import pytest

from thelpviewer.server.accounts.sessions import new_session
from thelpviewer.server.accounts.store import AccountStore
from thelpviewer.server.config import load_config
from thelpviewer.server.dos.store import DosPromptStore
from thelpviewer.server.storage import migrate_storage, migrate_backups, publish_docs
from thelpviewer.server.file_storage import directory_signature, relocate_directory


def config_for(root):
    empty = root / "dos.json"
    empty.write_text('{"sources": [], "files": [{"path": "BASE.TXT", "text": ["shared"]}]}')
    return replace(load_config(), state_dir=root / "var", data_dir=root / "data",
        helps_dir=root / "data" / "helps", sources_dir=root / "var" / "sources",
        docs_dir=root / "data" / "docs", docs_source_dir=root / "docs",
        statistics_path=root / "data" / "statistics.sqlite3", downloads_dir=root / "var" / "downloads",
        dos_config_path=empty)


def test_migration_preserves_accounts_tokens_private_disks_and_shared_base(tmp_path):
    config = config_for(tmp_path)
    accounts = AccountStore(config.state_dir)
    accounts.create_user("founder", "Founder")
    with accounts._connect() as database:
        ident = database.execute("SELECT id FROM accounts").fetchone()[0]
        session = new_session(database, ident)
        database.execute("INSERT INTO credentials(credential_id,account_id,public_key,sign_count,device_type,backed_up) "
                         "VALUES (?, ?, ?, ?, ?, ?)",
                         (b"passkey-id", ident, b"public-key", 3, "single_device", 0))
    token = accounts.issue_registration_token(session)
    original_key = (config.state_dir / "registration-tokens.key").read_bytes()
    store = DosPromptStore(config.state_dir / "dos", config.dos_config_path)
    store.prepare()
    base_id = store.base_id
    store.save(ident, {"base_id": base_id, "revision": 0, "directories": ["EMPTY"],
        "files": {"SAVE.DAT": base64.b64encode(b"private save").decode()}, "deleted": ["BASE.TXT"]})
    media = store.overlays.user_dir(ident) / "media" / "saved.iso"
    media.parent.mkdir(); media.write_bytes(b"private media")
    for name in ("sources", "helps"):
        path = tmp_path / name / "Product" / "fixture"
        path.parent.mkdir(parents=True); path.write_bytes(b"original content")
    (config.state_dir / "server-settings.json").write_text('{"dos_user_disk_mb": 64}')
    (config.state_dir / "content-settings.json").write_text('{"configured":true,"help_groups":[],"dos_packages":[]}')
    cache = store.root / "downloads" / "archive"
    cache.parent.mkdir(); cache.write_bytes(b"cached download")
    first = migrate_storage(config, project_root=tmp_path)
    assert migrate_storage(config, project_root=tmp_path) == first
    reloaded = AccountStore(config.persistent_dir)
    assert reloaded.session_account_id(session) == ident
    assert reloaded.session_user(session)["role"] == "admin"
    assert reloaded.list_registration_tokens(session)[0]["token"] == token
    assert (config.persistent_dir / "registration-tokens.key").read_bytes() == original_key
    with reloaded._connect() as database:
        assert tuple(database.execute("SELECT account_id,public_key,sign_count FROM credentials").fetchone()) == (ident, b"public-key", 3)
    new_store = DosPromptStore(config.state_dir / "dos", config.dos_config_path,
        users_dir=config.persistent_dir / "dos" / "users", disk_dir=config.state_dir / "dos" / "c")
    new_store.prepare()
    assert new_store.base_id == base_id
    assert new_store.overlay(ident) == (1, {"SAVE.DAT": b"private save"}, ["BASE.TXT"], ["EMPTY"])
    assert (new_store.overlays.user_dir(ident) / "c" / "1" / "EMPTY").is_dir()
    assert (new_store.overlays.user_dir(ident) / "media" / "saved.iso").read_bytes() == b"private media"
    assert (config.downloads_dir / "dos" / "archive").read_bytes() == b"cached download"
    assert not (config.state_dir / "dos" / "users").exists()
    assert (config.helps_dir / "Product" / "fixture").read_bytes() == b"original content"
    assert not (tmp_path / "helps").exists()
    assert (config.persistent_dir / first["backup"]).is_dir()
    assert not Path(first["backup"]).is_absolute()  # Portable between native and Docker paths.
    assert "var/dos/users" in first["completed"]
    new_store.rebuild(); new_store._worker.join(5)
    assert new_store.state == "ready"
    assert new_store.overlay(ident)[1] == {"SAVE.DAT": b"private save"}
    assert (new_store.overlays.user_dir(ident) / "media" / "saved.iso").is_file()


def test_migration_preflight_conflict_changes_neither_source_nor_target(tmp_path):
    config = config_for(tmp_path)
    for root, content in [(tmp_path / "helps", b"old"), (config.helps_dir, b"different")]:
        root.mkdir(parents=True); (root / "topic.json.gz").write_bytes(content)
    sources = tmp_path / "sources"
    sources.mkdir(); (sources / "source.hlp").write_bytes(b"keep")
    with pytest.raises(ValueError, match="conflict"):
        migrate_storage(config, project_root=tmp_path)
    assert (tmp_path / "helps" / "topic.json.gz").read_bytes() == b"old"
    assert (config.helps_dir / "topic.json.gz").read_bytes() == b"different"
    assert (sources / "source.hlp").read_bytes() == b"keep"
    assert not config.sources_dir.exists()


def test_migration_merges_identical_files_and_preserves_empty_directories(tmp_path):
    config = config_for(tmp_path)
    old = tmp_path / "helps"
    old.mkdir(); (old / "same").write_bytes(b"same"); (old / "empty").mkdir()
    config.helps_dir.mkdir(parents=True)
    (config.helps_dir / "same").write_bytes(b"same")
    (config.helps_dir / "extra").write_bytes(b"extra")
    migrate_storage(config, project_root=tmp_path)
    assert (config.helps_dir / "empty").is_dir()
    assert (config.helps_dir / "extra").read_bytes() == b"extra"


@pytest.mark.parametrize("existing_target", [False, True])
@pytest.mark.parametrize("custom_data", [False, True])
def test_originals_move_from_data_to_working_sources_with_portable_journal(tmp_path, existing_target, custom_data):
    config = config_for(tmp_path)
    if custom_data:
        config = replace(config, data_dir=tmp_path / "permanent")
    old = config.persistent_dir / "sources"
    source = old / "Manual Product" / "HELP.HLP"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"\x00\xffmanual original\x1a")
    (source.parent / "LICENCE.TXT").write_bytes(b"retain this notice")
    (source.parent / "Empty").mkdir()
    before = directory_signature(old)
    if existing_target:
        shutil.copytree(old, config.sources_dir)
        (config.sources_dir / "extra.hlp").write_bytes(b"already installed")
    # A previous upgrade migrated root sources to data. The new step is distinct.
    journal_path = config.persistent_dir / "storage-migration.json"
    journal_path.write_text(json.dumps({"version": 1, "backup": "migration-backups/previous",
                                        "completed": ["sources"]}))
    journal = migrate_storage(config, project_root=tmp_path)
    assert journal["completed"] == ["sources", "data/sources"]
    assert not old.exists()
    assert before.items() <= directory_signature(config.sources_dir).items()
    backup = config.persistent_dir / journal["backup"] / "01-sources"
    assert directory_signature(backup) == before
    if existing_target:
        assert (config.sources_dir / "extra.hlp").read_bytes() == b"already installed"
    assert migrate_storage(config, project_root=tmp_path) == journal


@pytest.mark.parametrize("conflict", ["contents", "file-directory"])
def test_conflicting_incoming_source_trees_are_rejected_before_any_move(tmp_path, conflict):
    config = config_for(tmp_path)
    roots = [tmp_path / "sources", config.persistent_dir / "sources"]
    for root in roots:
        root.mkdir(parents=True)
    (roots[0] / "HELP.HLP").write_bytes(b"first original")
    if conflict == "contents":
        (roots[1] / "HELP.HLP").write_bytes(b"different original")
    else:
        (roots[1] / "HELP.HLP").mkdir()
    old_helps = tmp_path / "helps"
    old_helps.mkdir()
    (old_helps / "help.json.gz").write_bytes(b"keep published content")
    before = {root: directory_signature(root) for root in [old_helps, *roots]}
    with pytest.raises(ValueError, match="conflict"):
        migrate_storage(config, project_root=tmp_path)
    assert all(directory_signature(root) == signature for root, signature in before.items())
    assert not config.sources_dir.exists() and not config.helps_dir.exists()


def test_identical_and_distinct_incoming_originals_merge_without_loss(tmp_path):
    config = config_for(tmp_path)
    for root, extra in [(tmp_path / "sources", "root.hlp"),
                        (config.persistent_dir / "sources", "data.hlp")]:
        root.mkdir(parents=True)
        (root / "same.hlp").write_bytes(b"same original")
        (root / extra).write_bytes(extra.encode())
    journal = migrate_storage(config, project_root=tmp_path)
    assert set(path.name for path in config.sources_dir.iterdir()) == {"same.hlp", "root.hlp", "data.hlp"}
    assert journal["completed"] == ["sources", "data/sources"]


@pytest.mark.parametrize("linked", ["source", "target", "descendant", "ancestor"])
def test_originals_migration_refuses_links_without_changing_sources(tmp_path, linked):
    config = config_for(tmp_path)
    old = config.persistent_dir / "sources"
    old.mkdir(parents=True)
    (old / "HELP.HLP").write_bytes(b"manual original")
    if linked == "source":
        alias = config.persistent_dir / "originals"
        old.rename(alias)
        old.symlink_to(alias, target_is_directory=True)
    elif linked == "target":
        config.sources_dir.parent.mkdir()
        config.sources_dir.symlink_to(old, target_is_directory=True)
    elif linked == "descendant":
        (old / "alias.hlp").symlink_to(old / "HELP.HLP")
    else:
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        config.state_dir.symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic"):
        migrate_storage(config, project_root=tmp_path)
    assert (old / "HELP.HLP").read_bytes() == b"manual original"


def test_explicit_originals_directory_override_is_not_migrated(tmp_path):
    config = replace(config_for(tmp_path), sources_dir=tmp_path / "custom-inputs")
    old = config.persistent_dir / "sources"
    old.mkdir(parents=True)
    (old / "HELP.HLP").write_bytes(b"manual original")
    migrate_storage(config, project_root=tmp_path)
    assert (old / "HELP.HLP").read_bytes() == b"manual original"
    assert not config.sources_dir.exists()


def test_document_publisher_updates_managed_docs_but_keeps_edits_and_private_docs_private(tmp_path):
    source, destination = tmp_path / "docs", tmp_path / "data" / "docs"
    source.mkdir()
    (source / "Guide.md").write_text("v1")
    (source / "Other.md").write_text("other")
    (source / "Format RE.md").write_text("private")
    publish_docs(source, destination)
    (destination / "Other.md").write_text("administrator edit")
    (destination / "Extra.md").write_text("permanent extra document")
    (source / "Guide.md").write_text("v2")
    (source / "Other.md").write_text("repo update")
    publish_docs(source, destination)
    assert (destination / "Guide.md").read_text() == "v2"
    assert (destination / "Other.md").read_text() == "administrator edit"
    assert (destination / "Extra.md").read_text() == "permanent extra document"
    assert not (destination / "Format RE.md").exists()
    (destination / "escape").symlink_to(source, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic"):
        publish_docs(source, destination)


def test_demo_midi_removed_but_synth_assets_remain():
    for root in (Path("www/assets/midi"), Path("thelpviewer/server/converter/assets/midi")):
        assert not list(root.glob("*.mid"))
        assert not (root / "README.md").exists()
        assert (root / "synth" / "FluidR3Mono_GM.sf3").is_file()


@pytest.mark.parametrize("cross_device", [False, True])
def test_directory_relocation_preserves_contents_and_empty_directories(tmp_path, monkeypatch, cross_device):
    source, target = tmp_path / "old", tmp_path / "backups/help/saved"
    source.mkdir()
    (source / "original.bin").write_bytes(bytes(range(256)))
    (source / "empty").mkdir()
    before = directory_signature(source)
    rename = Path.rename
    def move(path, destination):
        if path == source and cross_device:
            raise OSError(errno.EXDEV, "different filesystems")
        return rename(path, destination)
    monkeypatch.setattr(Path, "rename", move)
    relocate_directory(source, target)
    assert not source.exists() and directory_signature(target) == before
    assert not list(target.parent.glob(".backup-copy-*"))


def test_cross_device_copy_is_verified_before_the_original_is_removed(tmp_path, monkeypatch):
    source, target = tmp_path / "old", tmp_path / "backups/help/saved"
    source.mkdir()
    (source / "saved.bin").write_bytes(b"keep original")
    rename, copy = Path.rename, shutil.copytree
    def move(path, destination):
        if path == source:
            raise OSError(errno.EXDEV, "different filesystems")
        return rename(path, destination)
    def corrupt(origin, destination, **kwargs):
        result = copy(origin, destination, **kwargs)
        (destination / "saved.bin").write_bytes(b"bad copy")
        return result
    monkeypatch.setattr(Path, "rename", move)
    monkeypatch.setattr(shutil, "copytree", corrupt)
    with pytest.raises(ValueError, match="verification failed"):
        relocate_directory(source, target)
    assert (source / "saved.bin").read_bytes() == b"keep original"
    assert not target.exists() and not list(target.parent.glob(".backup-copy-*"))


@pytest.mark.parametrize("collision", [None, "identical", "different", "link"])
def test_backup_migration_groups_all_families_and_refuses_conflicts_before_moving(tmp_path, collision):
    config = config_for(tmp_path)
    root = config.state_dir / "backups"
    help_id = uuid.uuid4().hex
    pairs = [
        (config.helps_dir.parent / f".helps-previous-{help_id}", root / "help" / f"help-{help_id}"),
        *[(root / name, root / "dos" / name) for name in (f"dos-base-{uuid.uuid4().hex}", f"dos-packages-{uuid.uuid4().hex}")],
        (root / f"midi-{uuid.uuid4().hex}", root / "midi" / "placeholder"),
    ]
    pairs[-1] = (pairs[-1][0], root / "midi" / pairs[-1][0].name)
    for index, (source, _target) in enumerate(pairs):
        source.mkdir(parents=True)
        (source / "saved.bin").write_bytes(bytes([index, 0, 255]))
        (source / "empty").mkdir()
    originals = {target: directory_signature(source) for source, target in pairs}
    protected = config.persistent_dir / "dos/users/user/SAVE.DAT"
    protected.parent.mkdir(parents=True)
    protected.write_bytes(b"private data")
    foreign = root / "dos-packages-not-a-managed-id"
    foreign.mkdir()
    source, target = pairs[-1]
    if collision == "link":
        target.parent.mkdir(parents=True)
        target.symlink_to(source, target_is_directory=True)
    elif collision:
        shutil.copytree(source, target)
        if collision == "different":
            (target / "saved.bin").write_bytes(b"conflict")
    if collision in {"different", "link"}:
        with pytest.raises(ValueError, match="conflict|symbolic"):
            migrate_backups(config)
        assert all(directory_signature(source) == originals[target] for source, target in pairs)
    else:
        assert set(migrate_backups(config)) == set(pairs)
        assert all(not source.exists() and directory_signature(target) == originals[target] for source, target in pairs)
        assert migrate_backups(config) == []
    assert foreign.is_dir() and protected.read_bytes() == b"private data"


def test_application_startup_moves_existing_help_backups_before_starting_workers(tmp_path):
    from fastapi.testclient import TestClient
    from thelpviewer.server.app import create_app
    config = config_for(tmp_path)
    config = replace(config, midi_sources_path=config.dos_config_path, virtual_docs=())
    ident = uuid.uuid4().hex
    old = config.helps_dir.parent / f".helps-previous-{ident}"
    old.mkdir(parents=True)
    (old / "saved.bin").write_bytes(b"recovery generation")
    app = create_app(config)
    assert old.is_dir()  # Constructing/importing the app does not migrate backups.
    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200
        assert not old.exists()
        assert (config.state_dir / "backups/help" / f"help-{ident}" / "saved.bin").read_bytes() == b"recovery generation"
        assert all((config.state_dir / "backups" / kind).is_dir() for kind in ("help", "dos", "midi"))


@pytest.mark.parametrize("unsafe", ["root", "group-link", "group-file"])
def test_backup_migration_refuses_unsafe_destinations_even_without_legacy_backups(tmp_path, unsafe):
    config = config_for(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    root = config.state_dir / "backups"
    root.parent.mkdir(parents=True)
    if unsafe == "root":
        root.symlink_to(outside, target_is_directory=True)
    else:
        root.mkdir()
        if unsafe == "group-link":
            (root / "help").symlink_to(outside, target_is_directory=True)
        else:
            (root / "help").write_bytes(b"keep original file")
    with pytest.raises(ValueError, match="symbolic|directory"):
        migrate_backups(config)
    assert list(outside.iterdir()) == []
    if unsafe == "group-file":
        assert (root / "help").read_bytes() == b"keep original file"
