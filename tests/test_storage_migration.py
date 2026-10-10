"""Permanent data is isolated from rebuildable state, with verified migration."""

import base64
from dataclasses import replace
import json
from pathlib import Path
import sqlite3

import pytest

from thelpviewer.server.accounts import AccountStore
from thelpviewer.server.config import load_config
from thelpviewer.server.dos_prompt import DosPromptStore
from thelpviewer.server.storage import migrate_storage, publish_docs


def config_for(root):
    empty = root / "dos.json"
    empty.write_text('{"sources": [], "files": [{"path": "BASE.TXT", "text": ["shared"]}]}')
    return replace(load_config(), state_dir=root / "var", data_dir=root / "data",
        helps_dir=root / "data" / "helps", sources_dir=root / "data" / "sources",
        docs_dir=root / "data" / "docs", docs_source_dir=root / "docs",
        statistics_path=root / "data" / "statistics.sqlite3", downloads_dir=root / "var" / "downloads",
        dos_config_path=empty)


def test_migration_preserves_accounts_tokens_private_disks_and_shared_base(tmp_path):
    config = config_for(tmp_path)
    accounts = AccountStore(config.state_dir)
    accounts.create_user("founder", "Founder")
    with accounts._connect() as database:
        ident = database.execute("SELECT id FROM accounts").fetchone()[0]
        session = accounts._new_session(database, ident)
        database.execute("INSERT INTO credentials VALUES (?, ?, ?, ?, ?, ?)",
                         (b"passkey-id", ident, b"public-key", 3, "single_device", 0))
    token = accounts.issue_registration_token(session)
    original_key = (config.state_dir / "registration-tokens.key").read_bytes()
    store = DosPromptStore(config.state_dir / "dos", config.dos_config_path)
    store.prepare()
    base_id = store.base_id
    store.save(ident, {"base_id": base_id, "revision": 0, "directories": ["EMPTY"],
        "files": {"SAVE.DAT": base64.b64encode(b"private save").decode()}, "deleted": ["BASE.TXT"]})
    media = store._user_dir(ident) / "media" / "saved.iso"
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
    assert (new_store._user_dir(ident) / "c" / "1" / "EMPTY").is_dir()
    assert (new_store._user_dir(ident) / "media" / "saved.iso").read_bytes() == b"private media"
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
    assert (new_store._user_dir(ident) / "media" / "saved.iso").is_file()


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
