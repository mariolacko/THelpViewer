"""Administrator edits, per-account quotas and committed overlay usage."""

import base64
from dataclasses import replace
import json

from fastapi.testclient import TestClient

from thelpviewer.server.accounts.sessions import new_session
from thelpviewer.server.app import create_app
from thelpviewer.server.config import load_config


def test_admin_users_and_disk_limits(tmp_path):
    manifest = tmp_path / "empty.json"
    manifest.write_text('{"sources": [], "files": [{"path":"BASE.TXT","text":["shared"]}]}')
    config = replace(load_config(), state_dir=tmp_path / "var", helps_dir=tmp_path / "helps",
        midi_sources_path=manifest, dos_config_path=manifest, auth_origin="https://accounts.example.test",
        dev_auto_login=False, statistics_path=tmp_path / "var" / "statistics.sqlite3")
    app = create_app(config)
    accounts, dos = app.state.accounts, app.state.dos_prompt
    accounts.create_user("admin", "Admin")
    accounts.create_user("member", "Member")
    with accounts._connect() as database:
        ids = dict(database.execute("SELECT username,id FROM accounts"))
        tokens = {name: new_session(database, ident) for name, ident in ids.items()}
    change = {"email": "member@example.test", "role": "member",
              "active": True, "disk_capacity_mb": 1, "first_name": "Ján", "last_name": "Novák", "nickname": "JN"}
    with TestClient(app, base_url=config.auth_origin) as client:
        assert client.get("/api/admin/users").status_code == 403
        assert client.get("/api/dos/usage").status_code == 401
        client.cookies.set("thelp_session", tokens["member"])
        assert client.get("/api/admin/users").status_code == 403
        assert client.put(f'/api/admin/users/{ids["member"]}', json=change,
                          headers={"Origin": config.auth_origin}).status_code == 403
        assert client.get("/api/dos/usage").json() == {"used_bytes": 0, "capacity_bytes": 64 * 1048576,
                                                       "free_bytes": 64 * 1048576}
        client.cookies.set("thelp_session", tokens["admin"])
        result = client.get("/api/admin/users")
        assert result.status_code == 200 and result.headers["cache-control"] == "no-store"
        assert len(result.json()["users"]) == 2 and dos.state == "idle"
        path = f'/api/admin/users/{ids["member"]}'
        for headers in ({}, {"Origin": "https://evil.test"},
                        {"Origin": config.auth_origin, "Host": "evil.test"},
                        {"Origin": config.auth_origin, "Sec-Fetch-Site": "cross-site"}):
            assert client.put(path, json=change, headers=headers).status_code == 403
        headers = {"Origin": config.auth_origin, "X-Forwarded-Proto": "https"}
        assert client.put(path, json={**change, "unexpected": 1}, headers=headers).status_code == 422
        assert client.put(path, json={**change, "display_name": "Separate name"}, headers=headers).status_code == 422
        for capacity in (0, 257, True, "64"):
            assert client.put(path, json={**change, "disk_capacity_mb": capacity}, headers=headers).status_code == 422
        assert client.put(path, json=change, headers=headers).status_code == 200
        edited = next(user for user in client.get("/api/admin/users").json()["users"] if user["id"] == ids["member"])
        assert (edited["first_name"], edited["last_name"], edited["nickname"]) == ("Ján", "Novák", "JN")
        assert edited["display_name"] == "JN"
        for field in ("first_name", "last_name", "nickname"):
            assert client.put(path, json={**change, field: "x" * 101}, headers=headers).status_code == 422
            assert client.put(path, json={**change, field: "a\nb"}, headers=headers).status_code == 400
        assert dos.overlay_limit(ids["member"]) == 1048576
        dos.prepare()
        assert dos.state == "ready"
        payload = {"base_id": dos.base_id, "revision": 0, "account": "member", "deleted": [],
                   "files": {"SAVE.DAT": base64.b64encode(b"x" * 800000).decode()}}
        client.cookies.set("thelp_session", tokens["member"])
        assert client.put("/api/dos/overlay", json=payload, headers=headers).status_code == 200
        assert client.get("/api/dos/usage").json()["used_bytes"] == 800000
        assert client.get("/api/dos/session").json()["max_overlay_bytes"] == 1048576
        payload["revision"] = 1
        payload["files"] = {"BIG.DAT": base64.b64encode(b"x" * 1100000).decode()}
        assert client.put("/api/dos/overlay", json=payload, headers=headers).status_code == 409
        assert dos.disk_usage(ids["member"])["used_bytes"] == 800000
        client.cookies.set("thelp_session", tokens["admin"])
        assert client.put(path, json={**change, "disk_capacity_mb": None}, headers=headers).status_code == 200
        assert dos.overlay_limit(ids["member"]) == 64 * 1048576
        admin_path = f'/api/admin/users/{ids["admin"]}'
        admin_change = {**change, "email": "admin@example.test"}
        assert client.put(admin_path, json=admin_change, headers=headers).status_code == 400
        assert client.put(admin_path, json={**admin_change, "role": "admin", "active": False}, headers=headers).status_code == 400
        assert accounts.session_user(tokens["admin"])["role"] == "admin"
        assert next(user for user in result.json()["users"] if user["id"] == ids["admin"])["protected_admin"] is True
        # The founding administrator remains protected even with another admin.
        assert client.put(path, json={**change, "role": "admin"}, headers=headers).status_code == 200
        client.cookies.set("thelp_session", tokens["member"])
        for update in (admin_change, {**admin_change, "role": "admin", "active": False}):
            rejected = client.put(admin_path, json=update, headers=headers)
            assert rejected.status_code == 400 and "founding administrator" in rejected.json()["detail"]
        assert client.put(admin_path, json={**admin_change, "role": "admin", "disk_capacity_mb": 96}, headers=headers).status_code == 200
        assert client.put(admin_path, json={**admin_change, "protected_admin": False}, headers=headers).status_code == 422
        assert client.delete(admin_path, headers=headers).status_code in (404, 405)
        assert accounts.session_user(tokens["admin"])["role"] == "admin"
        client.cookies.set("thelp_session", tokens["admin"])
        assert client.put(path, json=change, headers=headers).status_code == 200
        client.cookies.set("thelp_session", tokens["member"])
        assert client.get("/api/admin/users").status_code == 403
        client.cookies.set("thelp_session", tokens["admin"])
        assert client.put(path, json={**change, "active": False}, headers=headers).status_code == 200
        assert accounts.session_user(tokens["member"]) is None
        assert dos.disk_usage(ids["member"])["used_bytes"] == 800000
        assert client.get("/api/terminal/jobs/example").status_code == 404
        assert client.post("/api/terminal/jobs/example/input", json={"text": "x"}).status_code == 404
    assert (config.state_dir / "dos" / "users" / ids["member"] / "c" / "1" / "SAVE.DAT").stat().st_size == 800000


def test_founder_identity_migrates_and_is_preserved_after_profile_changes(tmp_path):
    import sqlite3
    import uuid
    from contextlib import closing
    import pytest
    from thelpviewer.server.accounts.common import AccountError
    from thelpviewer.server.accounts.store import AccountStore
    first, second = uuid.uuid4().hex, uuid.uuid4().hex
    with sqlite3.connect(tmp_path / "accounts.sqlite3") as database:
        database.execute("CREATE TABLE accounts (id TEXT PRIMARY KEY, username TEXT UNIQUE, display_name TEXT, "
                         "email TEXT DEFAULT '', role TEXT DEFAULT 'member', active INTEGER DEFAULT 1)")
        database.execute("INSERT INTO accounts (id, username, display_name, role) VALUES (?, 'first', 'Zulu', 'admin')", (first,))
        database.execute("INSERT INTO accounts (id, username, display_name, role) VALUES (?, 'second', 'Alpha', 'admin')", (second,))
    store = AccountStore(tmp_path)
    with closing(store._connect()) as database, database:
        token = new_session(database, second)
    users = store.list_users(token)
    assert users[0]["id"] == second  # Display sorting cannot select the founder.
    assert {row["id"] for row in users if row["protected_admin"]} == {first}
    assert all((row["first_name"], row["last_name"], row["nickname"]) == ("", "", "") for row in users)
    store.update_user(token, first, "first@example.test", "admin", True, 96, nickname="Changed name")
    for role, active in (("member", True), ("admin", False)):
        with pytest.raises(AccountError, match="founding administrator"):
            AccountStore(tmp_path).update_user(token, first, "first@example.test", role, active, 96)
    assert AccountStore(tmp_path).disk_capacity(first) == 96


def test_manifest_without_archive_hash_installs_and_reuses_download(tmp_path, monkeypatch):
    import io
    import zipfile
    from thelpviewer.server.dos.store import DosPromptStore
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("GAME.EXE", b"test software")
    manifest = tmp_path / "dos.json"
    manifest.write_text(json.dumps({"sources": [{"id": "game", "url": "https://software.test/game.zip",
        "format": "zip", "target": "GAMES", "launch": "GAME"}], "software_catalog": ["Software"]}))
    calls = []
    monkeypatch.setattr("thelpviewer.server.downloader.packages.fetch_source",
                        lambda *args, **kwargs: (calls.append(args[0]["url"]) or archive.getvalue()))
    store = DosPromptStore(tmp_path / "dos", manifest)
    store.prepare()
    assert store.state == "ready", store.error
    assert store.files["GAMES/GAME.EXE"] == b"test software"
    assert b"GAME" in store.files["SOFTWARE.TXT"]
    store.prepare(install_sources=True)
    assert store.state == "ready" and len(calls) == 1
