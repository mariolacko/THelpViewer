from dataclasses import replace

from fastapi.testclient import TestClient
import pytest

from thelpviewer.server.accounts.sessions import new_session
from thelpviewer.server.app import create_app
from thelpviewer.server.config import load_config
from thelpviewer.server.settings import ServerSettings


def test_server_settings_default_validation_and_persistence(tmp_path):
    settings = ServerSettings(tmp_path / "settings.json")
    assert settings.get() == {"dos_user_disk_mb": 64, "backup_count": 2}
    assert not settings.path.exists()
    for invalid in (0, 257, -1, True, "128", 1.5):
        with pytest.raises(ValueError):
            settings.update({"dos_user_disk_mb": invalid})
    settings.update({"dos_user_disk_mb": 64})
    assert ServerSettings(settings.path).get() == {"dos_user_disk_mb": 64, "backup_count": 2}
    for invalid in (0, 101, -1, True, "2", 1.5):
        with pytest.raises(ValueError):
            settings.update({"backup_count": invalid})
    settings.update({"backup_count": 3})
    assert ServerSettings(settings.path).get() == {"dos_user_disk_mb": 64, "backup_count": 3}
    settings.update({"dos_user_disk_mb": 32})
    assert settings.get() == {"dos_user_disk_mb": 32, "backup_count": 3}


def test_new_backup_default_preserves_existing_disk_setting(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"dos_user_disk_mb": 128}')
    assert ServerSettings(path).get() == {"dos_user_disk_mb": 128, "backup_count": 2}
    assert path.read_text() == '{"dos_user_disk_mb": 128}'  # Reads do not rewrite configuration.


def test_only_admin_can_read_and_change_persisted_server_settings(tmp_path):
    manifest = tmp_path / "empty.json"
    manifest.write_text('{"sources": []}')
    config = replace(load_config(), state_dir=tmp_path / "var", helps_dir=tmp_path / "helps",
        dos_config_path=manifest, midi_sources_path=manifest, auth_origin="https://testserver",
        statistics_path=tmp_path / "var" / "statistics.sqlite3")
    app = create_app(config)
    accounts = app.state.accounts
    accounts.create_user("admin")
    accounts.create_user("member")
    with accounts._connect() as database:
        ids = dict(database.execute("SELECT username,id FROM accounts"))
        tokens = {name: new_session(database, ident) for name, ident in ids.items()}
    with TestClient(app, base_url=config.auth_origin) as client:
        assert client.get("/api/admin/settings").status_code == 403
        client.cookies.set("thelp_session", tokens["member"])
        assert client.get("/api/admin/settings").status_code == 403
        assert client.put("/api/admin/settings", json={"dos_user_disk_mb": 64, "backup_count": 2}, headers={"Origin": "https://testserver"}).status_code == 403
        client.cookies.set("thelp_session", tokens["admin"])
        assert client.get("/api/admin/settings").json()["dos_user_disk_mb"] == 64
        assert client.get("/api/admin/settings").json()["backup_count"] == 2
        assert app.state.dos_prompt.settings is app.state.midi_library.settings is app.state.server_settings
        assert app.state.dos_prompt.state == "idle"  # Configuration must not download games.
        data = {"dos_user_disk_mb": 64, "backup_count": 3}
        assert client.put("/api/admin/settings", json=data, headers={"Origin": "https://evil.test"}).status_code == 403
        response = client.put("/api/admin/settings", json=data, headers={"Origin": "https://testserver"})
        assert response.status_code == 200 and response.headers["Cache-Control"] == "no-store"
        assert ServerSettings(config.state_dir / "server-settings.json").get() == data
        assert app.state.dos_prompt.overlay_limit() == 64 * 1024 * 1024
        for invalid in (0, 257, "64", True):
            assert client.put("/api/admin/settings", json={**data, "dos_user_disk_mb": invalid}, headers={"Origin": "https://testserver"}).status_code == 422
        for invalid in (0, 101, -1, "2", True, 2.5):
            assert client.put("/api/admin/settings", json={**data, "backup_count": invalid}, headers={"Origin": "https://testserver"}).status_code == 422
        assert ServerSettings(config.state_dir / "server-settings.json").get() == data
        assert client.put("/api/admin/settings", json={**data, "arbitrary": 1}, headers={"Origin": "https://testserver"}).status_code == 422
