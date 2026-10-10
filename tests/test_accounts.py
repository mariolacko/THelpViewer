"""Only an administrator can create accounts; WebAuthn ceremonies are one-use."""

from dataclasses import replace
import hashlib
import re
import sqlite3
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from thelpviewer.server.accounts import AccountError, AccountStore
from thelpviewer.server.app import create_app
from thelpviewer.server.config import load_config


def test_profile_preserves_identity_passkey_sessions_and_role(tmp_path):
    store = AccountStore(tmp_path)
    store.create_user("owner", "Original")
    store.create_user("member", "Member")
    with store._connect() as connection:
        ident = connection.execute("SELECT id FROM accounts WHERE username='owner'").fetchone()[0]
        connection.execute("UPDATE accounts SET username='old@example.test', email='old@example.test' WHERE id=?", (ident,))
        connection.execute("UPDATE accounts SET email='member@example.test' WHERE username='member'")
        connection.execute("INSERT INTO credentials(credential_id,account_id,public_key,sign_count) VALUES (?,?,?,0)",
                           (b"credential", ident, b"key"))
        session = store._new_session(connection, ident)
        other_session = store._new_session(connection, ident)
    user = store.update_profile(session, " NEW@EXAMPLE.TEST ",
                                first_name=" Ján ", last_name=" Novák ", nickname=" Reader ")
    assert user == {"username": "old@example.test", "display_name": "Reader", "email": "new@example.test", "role": "admin",
                    "first_name": "Ján", "last_name": "Novák", "nickname": "Reader"}
    assert store.update_profile(session, "new@example.test") == user
    for field in ("first_name", "last_name", "nickname"):
        for value in ("x" * 101, "Name\nOther", "a\x7fb"):
            with pytest.raises(AccountError):
                store.update_profile(session, "new@example.test", **{field: value})
        assert store.session_user(session) == user
    assert store.session_user(other_session) == user
    assert store.session_account_id(session) == ident
    assert store.authentication_options("NEW@EXAMPLE.TEST", "example.test")["options"]["allowCredentials"]
    for email in ("invalid", "member@example.test"):
        with pytest.raises(AccountError):
            store.update_profile(session, email)
        assert store.session_user(session) == user
    with pytest.raises(AccountError, match="Sign-in"):
        store.update_profile("invalid", "valid@example.test")
    full_name = store.update_profile(session, "new@example.test", nickname="")
    assert full_name["display_name"] == "Ján Novák"
    assert store.update_profile(session, "new@example.test", first_name="X", last_name="")["display_name"] == "X"
    assert len(store.update_profile(session, "new@example.test", first_name="x" * 100, last_name="y" * 100)["display_name"]) == 100
    with store._connect() as connection:
        assert connection.execute("SELECT public_key FROM credentials WHERE account_id=?", (ident,)).fetchone()[0] == b"key"
    store.logout(session)
    with pytest.raises(AccountError, match="Sign-in"):
        store.update_profile(session, "valid@example.test")


def test_profile_api_requires_owner_session_origin_and_rejects_role_changes(tmp_path):
    manifest = tmp_path / "empty.json"
    manifest.write_text('{"sources": []}')
    config = replace(load_config(), state_dir=tmp_path / "var", helps_dir=tmp_path / "helps",
                     statistics_path=tmp_path / "var" / "statistics.sqlite3",
                     midi_sources_path=manifest, auth_origin="https://accounts.example.test")
    app = create_app(config)
    store = app.state.accounts
    store.create_user("admin")
    store.create_user("reader", "Reader")
    with store._connect() as connection:
        ident = connection.execute("SELECT id FROM accounts WHERE username='reader'").fetchone()[0]
        session = store._new_session(connection, ident)
    payload = {"email": "reader@example.test",
               "first_name": "Reader", "last_name": "Two", "nickname": "RT"}
    with TestClient(app, base_url=config.auth_origin) as client:
        assert client.put("/api/auth/profile", json=payload, headers={"Origin": config.auth_origin}).status_code == 403
        client.cookies.set("thelp_session", session)
        assert client.put("/api/auth/profile", json=payload).status_code == 403
        assert client.put("/api/auth/profile", json=payload, headers={"Origin": "https://evil.test"}).status_code == 403
        assert client.put("/api/auth/profile", json={**payload, "role": "admin"}, headers={"Origin": config.auth_origin}).status_code == 422
        assert client.put("/api/auth/profile", json={**payload, "account_id": ident}, headers={"Origin": config.auth_origin}).status_code == 422
        assert client.put("/api/auth/profile", json={**payload, "display_name": "Separate name"}, headers={"Origin": config.auth_origin}).status_code == 422
        result = client.put("/api/auth/profile", json=payload, headers={"Origin": config.auth_origin})
        assert result.status_code == 200 and result.headers["cache-control"] == "no-store"
        assert result.json()["user"]["role"] == "member"
        assert result.json()["user"]["display_name"] == "RT"
        assert store.session_user(session)["email"] == "reader@example.test"
        assert result.json()["user"]["nickname"] == "RT"
        for field in ("first_name", "last_name", "nickname"):
            assert client.put("/api/auth/profile", json={**payload, field: 123}, headers={"Origin": config.auth_origin}).status_code == 422
            assert client.put("/api/auth/profile", json={**payload, field: "a\x00b"}, headers={"Origin": config.auth_origin}).status_code == 400
        assert client.put("/api/auth/profile", json={**payload, "nickname": ""}, headers={"Origin": config.auth_origin}).json()["user"]["nickname"] == ""
        assert client.put("/api/auth/profile", json={**payload, "email": "bad"}, headers={"Origin": config.auth_origin}).status_code == 400
        assert client.put("/api/auth/profile", json=payload, headers={"Origin": config.auth_origin, "Host": "evil.test"}).status_code == 503


def test_admin_invitation_passkey_and_session(tmp_path, monkeypatch):
    store = AccountStore(tmp_path)
    token = store.create_user("mario", "Mario Lacko")
    with pytest.raises(AccountError):
        store.create_user("mario")
    with pytest.raises(AccountError):
        store.registration_options("mario", "wrong", "example.test", "THelpViewer")

    enrollment = store.registration_options("mario", token, "example.test", "THelpViewer")
    assert enrollment["options"]["rp"]["id"] == "example.test"
    assert enrollment["options"]["authenticatorSelection"]["residentKey"] == "required"

    def registration_check(**kwargs):
        assert kwargs["expected_origin"] == "https://example.test"
        assert kwargs["expected_rp_id"] == "example.test"
        assert kwargs["require_user_verification"] is True
        return SimpleNamespace(credential_id=b"credential-1", credential_public_key=b"public-key",
                               sign_count=0, credential_device_type="multiDevice", credential_backed_up=True)

    monkeypatch.setattr("webauthn.verify_registration_response", registration_check)
    session = store.verify_registration(enrollment["ceremony_id"], {"id": "mock"},
                                        "example.test", "https://example.test")
    assert store.session_user(session) == {
        "username": "mario", "display_name": "Mario Lacko", "email": "", "role": "admin",
        "first_name": "", "last_name": "", "nickname": "",
    }
    with pytest.raises(AccountError):
        store.verify_registration(enrollment["ceremony_id"], {"id": "mock"},
                                  "example.test", "https://example.test")
    with pytest.raises(AccountError):
        store.registration_options("mario", token, "example.test", "THelpViewer")

    login = store.authentication_options("mario", "example.test")
    assert login["options"]["userVerification"] == "required"
    assert len(login["options"]["allowCredentials"]) == 1

    def authentication_check(**kwargs):
        assert kwargs["credential_public_key"] == b"public-key"
        assert kwargs["credential_current_sign_count"] == 0
        return SimpleNamespace(new_sign_count=1, credential_device_type="multiDevice", credential_backed_up=True)

    monkeypatch.setattr("webauthn.verify_authentication_response", authentication_check)
    session2 = store.verify_authentication(login["ceremony_id"], {"id": "Y3JlZGVudGlhbC0x"},
                                           "example.test", "https://example.test")
    assert store.session_user(session2)["username"] == "mario"
    with pytest.raises(AccountError):
        store.verify_authentication(login["ceremony_id"], {"id": "Y3JlZGVudGlhbC0x"},
                                    "example.test", "https://example.test")
    store.logout(session2)
    assert store.session_user(session2) is None


def test_passkey_api_requires_configured_origin_and_no_public_registration(tmp_path):
    config = replace(load_config(), state_dir=tmp_path / "var", helps_dir=tmp_path / "helps",
                     statistics_path=tmp_path / "var" / "statistics.sqlite3",
                     auth_origin="https://accounts.example.test")
    (tmp_path / "helps").mkdir()
    with TestClient(create_app(config), base_url="https://accounts.example.test") as client:
        assert client.get("/api/auth/session").json() == {
            "enabled": True, "authenticated": False, "user": None,
        }
        assert client.post("/api/auth/passkey/login/options", json={"username": "missing"}).status_code == 403
        token = AccountStore(tmp_path / "var").create_user("user")
        response = client.post("/api/auth/passkey/enroll/options", json={"username": "user", "token": token},
                               headers={"Origin": "https://accounts.example.test"})
        assert response.status_code == 200
        assert response.json()["options"]["rp"]["id"] == "accounts.example.test"
        assert client.post("/api/auth/register", json={"username": "anyone"}).status_code == 404
    with TestClient(create_app(config), base_url="https://other.example.test") as client:
        assert client.get("/api/auth/session").json()["enabled"] is False


def test_missing_passkey_dependency_returns_actionable_json(tmp_path, monkeypatch):
    config = replace(load_config(), state_dir=tmp_path / "var", helps_dir=tmp_path / "helps",
                     statistics_path=tmp_path / "var" / "statistics.sqlite3",
                     auth_origin="https://accounts.example.test")
    (tmp_path / "helps").mkdir()

    def missing_dependency(*args, **kwargs):
        raise ModuleNotFoundError("No module named 'webauthn'", name="webauthn")

    monkeypatch.setattr(AccountStore, "new_registration_options", missing_dependency)
    with TestClient(create_app(config), base_url="https://accounts.example.test") as client:
        response = client.post(
            "/api/auth/passkey/register/options",
            json={"name": "Example User", "email": "user@example.test", "token": "AAAAA-AAAAA-AAAAA-AAAAA-AAAAA"},
            headers={"Origin": "https://accounts.example.test"},
        )
        assert response.status_code == 503
        assert response.json() == {
            "detail": "Passkey server dependency is unavailable; rebuild the viewer Docker image."
        }


def test_bootstrap_admin_and_one_hour_admin_registration_tokens(tmp_path, monkeypatch):
    store = AccountStore(tmp_path / "var")
    bootstrap = store.bootstrap_token()
    assert bootstrap and store.bootstrap_token() != bootstrap
    bootstrap = store.bootstrap_token()
    assert re.fullmatch(r"[A-Z2-9]{5}(?:-[A-Z2-9]{5}){4}", bootstrap)
    options = store.new_registration_options("Mario Lacko", "Mario@Example.test",
                                             bootstrap.replace("-", "").lower(),
                                             "example.test", "THelpViewer")

    def verified(**kwargs):
        assert kwargs["expected_origin"] == "https://example.test"
        assert kwargs["require_user_verification"] is True
        return SimpleNamespace(credential_id=kwargs["expected_challenge"],
                               credential_public_key=b"public-key", sign_count=0,
                               credential_device_type="multiDevice", credential_backed_up=True)

    monkeypatch.setattr("webauthn.verify_registration_response", verified)
    admin_session = store.verify_new_registration(options["ceremony_id"], {"id": "mock"},
                                                  "example.test", "https://example.test")
    assert store.session_user(admin_session) == {
        "username": "mario@example.test", "display_name": "Mario Lacko",
        "email": "mario@example.test", "role": "admin",
        "first_name": "", "last_name": "", "nickname": "",
    }
    assert store.bootstrap_token() is None
    assert store.list_users(admin_session)[0]["protected_admin"] is True
    with pytest.raises(AccountError):
        store.new_registration_options("Another", "another@example.test", bootstrap,
                                       "example.test", "THelpViewer")
    with pytest.raises(AccountError):
        store.verify_new_registration(options["ceremony_id"], {"id": "mock"},
                                      "example.test", "https://example.test")

    invitation = store.issue_registration_token(admin_session)
    assert re.fullmatch(r"[A-Z2-9]{5}(?:-[A-Z2-9]{5}){4}", invitation)
    listed = store.list_registration_tokens(admin_session)
    assert len(listed) == 1 and listed[0]["token"] == invitation
    assert listed[0]["expires_at"] > 0
    assert AccountStore(tmp_path / "var").list_registration_tokens(admin_session) == listed
    assert ((tmp_path / "var" / "registration-tokens.key").stat().st_mode & 0o777) == 0o600
    with sqlite3.connect(store.path) as connection:
        ciphertext = connection.execute(
            "SELECT token_ciphertext FROM registration_tokens WHERE token_hash = ?", (listed[0]["id"],)
        ).fetchone()[0]
    assert invitation.encode() not in ciphertext
    member_options = store.new_registration_options("Reader", "reader@example.test", invitation,
                                                    "example.test", "THelpViewer")
    member_session = store.verify_new_registration(member_options["ceremony_id"], {"id": "mock"},
                                                   "example.test", "https://example.test")
    assert store.session_user(member_session)["role"] == "member"
    assert {user["username"] for user in store.list_users(admin_session) if user["protected_admin"]} == {"mario@example.test"}
    assert store.list_registration_tokens(admin_session) == []
    with pytest.raises(AccountError):
        store.issue_registration_token(member_session)
    with pytest.raises(AccountError):
        store.list_registration_tokens(member_session)
    with pytest.raises(AccountError):
        store.new_registration_options("Another", "another@example.test", invitation,
                                       "example.test", "THelpViewer")

    older_token = "AAAAA-AAAAA-AAAAA-AAAAA-AAAAA"
    older_hash = hashlib.sha256(older_token.encode()).hexdigest()
    with sqlite3.connect(store.path) as connection:
        admin_id = connection.execute("SELECT id FROM accounts WHERE role = 'admin'").fetchone()[0]
        connection.execute(
            "INSERT INTO registration_tokens(token_hash, issuer_id, expires_at) VALUES (?, ?, ?)",
            (older_hash, admin_id, 9999999999),
        )
    assert store.list_registration_tokens(admin_session) == [
        {"id": older_hash, "token": None, "expires_at": 9999999999},
    ]
    with pytest.raises(AccountError):
        store.delete_registration_token(member_session, older_hash)
    store.delete_registration_token(admin_session, older_hash)
    with pytest.raises(AccountError):
        store.new_registration_options("Older", "older@example.test", older_token,
                                       "example.test", "THelpViewer")

    config = replace(load_config(), state_dir=tmp_path / "var", helps_dir=tmp_path / "helps",
                     statistics_path=tmp_path / "var" / "statistics.sqlite3",
                     auth_origin="https://example.test")
    (tmp_path / "helps").mkdir()
    with TestClient(create_app(config), base_url="https://example.test") as client:
        assert client.post("/api/auth/registration-tokens", headers={"Origin": "https://example.test"}).status_code == 403
        assert client.get("/api/auth/registration-tokens").status_code == 403
        client.cookies.set("thelp_session", admin_session)
        response = client.post("/api/auth/registration-tokens", headers={"Origin": "https://example.test"})
        assert response.status_code == 200 and response.json()["expires_in"] == 3600
        issued = response.json()["token"]
        listed = client.get("/api/auth/registration-tokens")
        assert listed.status_code == 200 and listed.headers["cache-control"] == "no-store"
        assert [row["token"] for row in listed.json()["tokens"]] == [issued]
        token_hash = listed.json()["tokens"][0]["id"]
        assert client.delete(f"/api/auth/registration-tokens/{token_hash}").status_code == 403
        deleted = client.delete(f"/api/auth/registration-tokens/{token_hash}",
                                headers={"Origin": "https://example.test"})
        assert deleted.status_code == 204
        assert client.get("/api/auth/registration-tokens").json()["tokens"] == []
        with pytest.raises(AccountError):
            store.new_registration_options("Deleted", "deleted@example.test", issued,
                                           "example.test", "THelpViewer")
        response = client.post("/api/auth/registration-tokens", headers={"Origin": "https://example.test"})
        expired = response.json()["token"]
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE registration_tokens SET expires_at = 0")
    assert store.list_registration_tokens(admin_session) == []
    with pytest.raises(AccountError):
        store.new_registration_options("Late", "late@example.test", expired,
                                       "example.test", "THelpViewer")


def test_old_registration_token_is_rejected_even_if_its_hash_is_stored(tmp_path):
    store = AccountStore(tmp_path / "var")
    old_token = "legacy-enrollment-token_with-43-characters-123"
    with store._connect() as connection:
        connection.execute(
            "INSERT INTO registration_tokens(token_hash, bootstrap, expires_at) "
            "VALUES (?, 1, 9999999999)",
            (hashlib.sha256(old_token.encode()).hexdigest(),),
        )
    with pytest.raises(AccountError, match="Invalid registration token format"):
        store.new_registration_options("Legacy User", "legacy@example.test", old_token,
                                       "example.test", "THelpViewer")


def test_old_registration_token_table_gains_encrypted_value_column(tmp_path):
    state_dir = tmp_path / "var"
    state_dir.mkdir()
    with sqlite3.connect(state_dir / "accounts.sqlite3") as connection:
        connection.execute(
            "CREATE TABLE registration_tokens (token_hash TEXT PRIMARY KEY, "
            "issuer_id TEXT, bootstrap INTEGER NOT NULL DEFAULT 0, expires_at INTEGER NOT NULL)"
        )
    with AccountStore(state_dir)._connect() as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(registration_tokens)")}
    assert "token_ciphertext" in columns


def test_public_robots_uses_configured_https_origin_behind_http_proxy(tmp_path):
    config = replace(load_config(), state_dir=tmp_path / "var", helps_dir=tmp_path / "helps",
                     statistics_path=tmp_path / "var" / "statistics.sqlite3",
                     public_base_url="", auth_origin="https://help.example.test")
    (tmp_path / "helps").mkdir()
    with TestClient(create_app(config), base_url="http://help.example.test") as client:
        assert "Sitemap: https://help.example.test/sitemap.xml" in client.get("/robots.txt").text
