"""The opt-in local login issues real sessions, never production sessions."""

from dataclasses import replace
import json
import shutil
import subprocess

from fastapi.testclient import TestClient
import pytest

from thelpviewer.server.accounts.store import AccountStore
from thelpviewer.server.app import create_app
from thelpviewer.server.config import load_config


def local_config(tmp_path, **changes):
    return replace(load_config(), state_dir=tmp_path / "var", helps_dir=tmp_path / "helps",
                   statistics_path=tmp_path / "var" / "statistics.sqlite3",
                   auth_origin="http://localhost:5448", public_base_url="",
                   dev_auto_login=True, **changes)


def test_local_login_reuses_real_session_and_isolates_production_accounts(tmp_path):
    config = local_config(tmp_path)
    app = create_app(config)
    with TestClient(app, base_url=config.auth_origin) as client:
        response = client.get("/api/auth/session", headers={"Sec-Fetch-Site": "same-origin"})
        assert response.json() == {
            "enabled": True, "authenticated": True, "development": True, "user": {
                "username": "local-development-admin", "display_name": "Admin",
                "email": "", "role": "admin",
                "first_name": "", "last_name": "", "nickname": "",
            },
        }
        assert response.headers["cache-control"] == "no-store"
        assert "HttpOnly" in response.headers["set-cookie"]
        assert "SameSite=strict" in response.headers["set-cookie"]
        token = client.cookies["thelp_session"]
        assert "set-cookie" not in client.get("/api/auth/session").headers
        assert client.get("/api/admin/settings").status_code == 200
        assert client.post("/api/auth/registration-tokens", headers={"Origin": config.auth_origin}).status_code == 200
        account_id = app.state.accounts.session_account_id(token)
        # Upgrade the old default label even with an already valid session.
        with app.state.accounts._connect() as database:
            database.execute("UPDATE accounts SET display_name='Local Administrator', disk_capacity_mb=96 WHERE id=?", (account_id,))
        migrated = client.get("/api/auth/session")
        assert migrated.json()["user"]["display_name"] == "Admin"
        assert "set-cookie" not in migrated.headers
        assert app.state.accounts.session_account_id(token) == account_id
        assert app.state.accounts.disk_capacity(account_id) == 96
        # A user's custom profile label is not reset on subsequent logins.
        with app.state.accounts._connect() as database:
            database.execute("UPDATE accounts SET display_name='My admin' WHERE id=?", (account_id,))
        assert client.get("/api/auth/session").json()["user"]["display_name"] == "My admin"
        assert AccountStore(config.state_dir / "development").session_account_id(token) == account_id
        assert not AccountStore(config.state_dir).session_user(token)
        assert AccountStore(config.state_dir).bootstrap_token()
        assert client.post("/api/auth/logout", headers={"Origin": config.auth_origin}).status_code == 200
        assert not app.state.accounts.session_user(token)
        # Auto-login is intentional on the next reload, with a fresh session but the same DOS owner.
        assert client.get("/api/auth/session").json()["authenticated"]
        token = client.cookies["thelp_session"]
        assert app.state.accounts.session_account_id(token) == account_id

    with TestClient(create_app(replace(config, dev_auto_login=False)), base_url=config.auth_origin) as client:
        client.cookies.set("thelp_session", token)
        assert not client.get("/api/auth/session").json()["authenticated"]
        assert client.get("/api/admin/settings").status_code == 403
        assert client.post("/api/auth/registration-tokens", headers={"Origin": config.auth_origin}).status_code == 403


@pytest.mark.parametrize("headers", [
    {"Host": "public.example.test"}, {"Origin": "https://evil.example.test"},
    {"Sec-Fetch-Site": "cross-site"}, {"Sec-Fetch-Site": "same-site"},
    {"Forwarded": "host=localhost:5448"}, {"X-Forwarded-For": "127.0.0.1"},
    {"X-Forwarded-Host": "localhost:5448"}, {"X-Forwarded-Proto": "http"},
])
def test_local_login_rejects_public_proxied_or_cross_origin_requests(tmp_path, headers):
    config = local_config(tmp_path)
    with TestClient(create_app(config), base_url=config.auth_origin) as client:
        response = client.get("/api/auth/session", headers=headers)
        assert response.json()["authenticated"] is False
        assert "set-cookie" not in response.headers
        assert not (config.state_dir / "development" / "accounts.sqlite3").exists()


@pytest.mark.parametrize("changes", [
    {"auth_origin": "https://public.example.test"}, {"auth_origin": "http://192.168.1.2:5448"},
    {"auth_origin": "https://localhost:5448"}, {"auth_origin": "http://localhost:5448/path"},
    {"auth_origin": "http://user@localhost:5448"}, {"public_base_url": "https://public.example.test"},
])
def test_local_login_refuses_public_server_configuration(tmp_path, changes):
    config = replace(local_config(tmp_path), **changes)
    with pytest.raises(ValueError, match="THELP_DEV_AUTO_LOGIN"):
        create_app(config)
    assert not config.state_dir.exists()


def test_development_login_is_off_by_default(monkeypatch):
    monkeypatch.delenv("THELP_DEV_AUTO_LOGIN", raising=False)
    assert load_config().dev_auto_login is False
    monkeypatch.setenv("THELP_DEV_AUTO_LOGIN", "1")
    assert load_config().dev_auto_login is True


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker Compose is required")
def test_local_compose_replaces_public_port_and_normal_compose_disables_bypass():
    def compose(*files):
        args = ["docker", "compose"]
        for file in files:
            args.extend(["-f", file])
        result = subprocess.run([*args, "config", "--format", "json"], check=True,
                                capture_output=True, text=True, timeout=15)
        return json.loads(result.stdout)["services"]["viewer"]

    normal = compose("docker-compose.yml")
    assert normal["environment"]["THELP_DEV_AUTO_LOGIN"] == "0"
    local = compose("docker-compose.yml", "docker-compose.local.yml")
    assert local["environment"]["THELP_DEV_AUTO_LOGIN"] == "1"
    assert local["environment"]["THELP_PUBLIC_BASE_URL"] == ""
    assert len(local["ports"]) == 1
    assert local["ports"][0]["host_ip"] == "127.0.0.1"
