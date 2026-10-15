"""Owner-bound named credentials and optional, rate-limited password login."""
from dataclasses import replace
from types import SimpleNamespace
import sqlite3
import time

from fastapi.testclient import TestClient
import pytest

from thelpviewer.server.accounts.common import AccountError, token_hash
from thelpviewer.server.accounts import passwords
from thelpviewer.server.accounts.sessions import new_session
from thelpviewer.server.accounts.store import AccountStore
from thelpviewer.server.app import create_app
from thelpviewer.server.config import load_config

PASSWORD = "Moonlit rivers carry 42 boats!"


@pytest.fixture
def owner(tmp_path):
    store = AccountStore(tmp_path)
    store.create_user("owner")
    store.create_user("other")
    with store._connect() as db:
        ident = db.execute("SELECT id FROM accounts WHERE username='owner'").fetchone()[0]
        other = db.execute("SELECT id FROM accounts WHERE username='other'").fetchone()[0]
        token = new_session(db, ident)
        other_token = new_session(db, other)
        db.execute("INSERT INTO credentials(credential_id,account_id,public_key,sign_count) VALUES (?,?,?,0)",
                   (b"first", ident, b"original key"))
    return store, ident, token, other_token


def verified(ident=b"second"):
    return SimpleNamespace(credential_id=ident, credential_public_key=b"new key", sign_count=0,
                           credential_device_type="multiDevice", credential_backed_up=True)


def test_add_rename_list_and_authenticate_multiple_passkeys(owner, monkeypatch):
    store, ident, token, other = owner
    assert store.security(token) == {"password_set": False, "passkeys": [{
        "id": "Zmlyc3Q", "name": "Passkey 1", "created_at": 0, "last_used_at": 0, "backed_up": False}]}
    store.rename_passkey(token, "Zmlyc3Q", "Windows - Edge")
    request = store.add_passkey_options(token, "example.test", "THelpViewer")
    assert len(request["options"]["excludeCredentials"]) == 1
    monkeypatch.setattr("webauthn.verify_registration_response", lambda **kw: verified())
    with pytest.raises(AccountError, match="belong"):
        store.verify_added_passkey(other, request["ceremony_id"], {}, "example.test", "https://example.test", "Other")
    store.verify_added_passkey(token, request["ceremony_id"], {}, "example.test", "https://example.test", "macOS - Safari")
    rows = store.security(token)["passkeys"]
    assert [r["name"] for r in rows] == ["Windows - Edge", "macOS - Safari"]
    assert rows[1]["created_at"] > 0 and rows[1]["backed_up"]
    assert "public_key" not in rows[1]
    assert store.security(other)["passkeys"] == []
    with pytest.raises(AccountError):
        store.rename_passkey(other, rows[0]["id"], "stolen")
    with pytest.raises(AccountError):
        store.verify_added_passkey(token, request["ceremony_id"], {}, "example.test", "https://example.test", "again")
    for row in rows:
        auth = store.authentication_options("owner", "example.test")
        assert len(auth["options"]["allowCredentials"]) == 2
        monkeypatch.setattr("webauthn.verify_authentication_response", lambda **kw: SimpleNamespace(
            new_sign_count=1, credential_device_type="multiDevice", credential_backed_up=True))
        signed_in = store.verify_authentication(auth["ceremony_id"], {"id": row["id"]}, "example.test", "https://example.test")
        assert store.session_account_id(signed_in) == ident
    assert all(row["last_used_at"] for row in store.security(token)["passkeys"])


@pytest.mark.parametrize("name", ["", " ", "x" * 81, "line\nnext", "bad\x00"])
def test_passkey_names_are_validated(owner, name):
    with pytest.raises(AccountError, match="name"):
        owner[0].rename_passkey(owner[2], "Zmlyc3Q", name)


def test_added_key_requires_current_recent_passkey_session_and_valid_signature(owner, monkeypatch):
    store, ident, token, _ = owner
    with store._connect() as db:
        db.execute("UPDATE sessions SET verified_at=0 WHERE token_hash=?", (token_hash(token),))
        password_session = new_session(db, ident, auth_method="password")
    for session in (token, password_session):
        with pytest.raises(AccountError, match="Confirm"):
            store.add_passkey_options(session, "example.test", "THelpViewer")
        with pytest.raises(AccountError, match="Confirm"):
            store.set_password(session, PASSWORD)
    with store._connect() as db:
        fresh = new_session(db, ident)
    request = store.add_passkey_options(fresh, "example.test", "THelpViewer")
    def reject(**kwargs):
        raise ValueError("wrong signature")
    monkeypatch.setattr("webauthn.verify_registration_response", reject)
    with pytest.raises(AccountError, match="verification"):
        store.verify_added_passkey(fresh, request["ceremony_id"], {}, "example.test", "https://example.test", "New")
    assert len(store.security(fresh)["passkeys"]) == 1


def test_add_passkey_is_bound_to_one_session_expires_and_rejects_duplicate_keys(owner, monkeypatch):
    store, ident, token, _ = owner
    request = store.add_passkey_options(token, "example.test", "THelpViewer")
    with store._connect() as db:
        second_session = new_session(db, ident)
    monkeypatch.setattr("webauthn.verify_registration_response", lambda **kw: verified(b"first"))
    with pytest.raises(AccountError, match="belong"):
        store.verify_added_passkey(second_session, request["ceremony_id"], {}, "example.test", "https://example.test", "wrong session")
    with pytest.raises(AccountError, match="already registered"):
        store.verify_added_passkey(token, request["ceremony_id"], {}, "example.test", "https://example.test", "duplicate")
    request = store.add_passkey_options(token, "example.test", "THelpViewer")
    with store._connect() as db:
        db.execute("UPDATE ceremonies SET expires_at=0 WHERE id=?", (request["ceremony_id"],))
    with pytest.raises(AccountError, match="expired"):
        store.verify_added_passkey(token, request["ceremony_id"], {}, "example.test", "https://example.test", "expired")
    assert len(store.security(token)["passkeys"]) == 1


def test_password_verification_costs_one_kdf_for_unknown_and_passwordless_accounts(owner, monkeypatch):
    store, _, _, _ = owner
    calls = []
    monkeypatch.setattr(passwords, "_derive", lambda password, salt: calls.append((password,salt)) or b"X" * 32)
    for username in ("missing", "owner"):
        with pytest.raises(AccountError, match="Email/username or password is incorrect"):
            store.password_login(username, "wrong")
    assert len(calls) == 2


def test_password_kdf_limits_parallelism(owner):
    assert passwords._workers.acquire(False) and passwords._workers.acquire(False)
    try:
        with pytest.raises(passwords.PasswordRateLimit, match="busy"):
            passwords.encode(PASSWORD)
    finally:
        passwords._workers.release()
        passwords._workers.release()


def test_password_is_opt_in_salted_normalized_and_preserves_passkeys(owner):
    store, ident, token, other = owner
    with pytest.raises(AccountError, match="incorrect"):
        store.password_login("owner", PASSWORD)
    store.set_password(token, PASSWORD)
    assert store.security(token)["password_set"]
    with store._connect() as db:
        encoded = db.execute("SELECT password_hash FROM accounts WHERE id=?", (ident,)).fetchone()[0]
        another = new_session(db, ident)
        assert encoded.startswith("scrypt$32768$8$3$") and PASSWORD not in encoded
    session = store.password_login("OWNER", PASSWORD)
    assert store.session_account_id(session) == ident
    with pytest.raises(AccountError, match="Confirm"):
        store.set_password(session, PASSWORD)
    store.set_password(token, "Waterfall café and distant stars!")
    assert store.session_user(session) is None and store.session_user(another) is None
    assert store.session_user(other)
    assert store.session_user(token)
    assert store.password_login("owner", "Waterfall cafe\u0301 and distant stars!")
    assert len(store.security(token)["passkeys"]) == 1
    assert passwords.encode(PASSWORD) != passwords.encode(PASSWORD)
    with pytest.raises(AccountError, match="incorrect"):
        store.password_login("owner", PASSWORD)


@pytest.mark.parametrize("password", ["tiny", "a" * 20, "password123456789!", "123456789012345",
                                       "abc\x00" * 6, "x" * 129])
def test_weak_passwords_rejected_without_changing_credentials(owner, password):
    store, _, token, _ = owner
    with pytest.raises(AccountError):
        store.set_password(token, password)
    assert not store.security(token)["password_set"]


def test_password_failures_are_generic_throttled_across_aliases_and_reset_after_window(owner, monkeypatch):
    store, ident, token, _ = owner
    store.set_password(token, PASSWORD)
    with store._connect() as db:
        db.execute("UPDATE accounts SET email='owner@example.test' WHERE id=?", (ident,))
    monkeypatch.setattr(passwords, "matches", lambda *args: False)
    for number in range(10):
        with pytest.raises(AccountError, match="incorrect"):
            store.password_login("owner" if number % 2 else "OWNER@EXAMPLE.TEST", "wrong", "client")
    with pytest.raises(passwords.PasswordRateLimit):
        store.password_login("owner", PASSWORD, "other-client")
    # Lockout does not disable the account or its Passkeys.
    assert store.authentication_options("owner", "example.test")
    with store._connect() as db:
        db.execute("UPDATE password_attempts SET started_at=?", (int(time.time()) - 901,))
    with pytest.raises(AccountError, match="incorrect"):
        store.password_login("owner", "wrong", "client")


def test_old_database_migration_preserves_credentials_sessions_and_does_not_enable_password(tmp_path):
    path = tmp_path / "accounts.sqlite3"
    with sqlite3.connect(path) as db:
        db.executescript("CREATE TABLE accounts(id TEXT PRIMARY KEY,username TEXT,display_name TEXT,active INTEGER DEFAULT 1);"
                        "INSERT INTO accounts(id,username,display_name) VALUES ('abc','reader','Reader');"
                        "CREATE TABLE credentials(credential_id BLOB PRIMARY KEY,account_id TEXT,public_key BLOB,sign_count INTEGER,device_type TEXT,backed_up INTEGER);"
                        "INSERT INTO credentials VALUES (X'01','abc',X'02',3,'',0);"
                        "CREATE TABLE sessions(token_hash TEXT PRIMARY KEY,account_id TEXT,expires_at INTEGER);")
        db.execute("INSERT INTO sessions VALUES (?,?,?)", (token_hash("old"), "abc", int(time.time())+1000))
    store = AccountStore(tmp_path)
    assert store.security("old")["passkeys"][0]["name"] == "Passkey 1"
    assert not store.security("old")["password_set"]
    with pytest.raises(AccountError, match="Confirm"):
        store.set_password("old", PASSWORD)


def test_security_http_owner_origin_cookie_and_password_login(tmp_path):
    empty = tmp_path / "empty.json"
    empty.write_text('{"sources": []}')
    config = replace(load_config(), state_dir=tmp_path / "var", data_dir=tmp_path / "data",
        helps_dir=tmp_path / "helps", docs_dir=tmp_path / "docs", midi_sources_path=empty,
        dos_config_path=empty, statistics_path=tmp_path / "data/stats.sqlite3", auth_origin="https://account.test")
    app = create_app(config)
    store = app.state.accounts
    store.create_user("owner")
    with store._connect() as db:
        ident = db.execute("SELECT id FROM accounts").fetchone()[0]
        token = new_session(db, ident)
    with TestClient(app, base_url=config.auth_origin) as client:
        assert client.get("/api/auth/security").status_code == 403
        client.cookies.set("thelp_session", token)
        assert client.get("/api/auth/security").headers["cache-control"] == "no-store"
        payload = {"password": PASSWORD}
        assert client.put("/api/auth/password", json=payload).status_code == 403
        assert client.put("/api/auth/password", json=payload, headers={"Origin":"https://evil.test"}).status_code == 403
        headers = {"Origin":config.auth_origin}
        assert client.put("/api/auth/password", json={**payload,"account_id":ident}, headers=headers).status_code == 422
        assert client.put("/api/auth/password", json=payload, headers=headers).status_code == 200
        client.post("/api/auth/logout", headers=headers)
        assert client.post("/api/auth/password/login", json={"username":"owner","password":"wrong"}, headers=headers).status_code == 400
        response = client.post("/api/auth/password/login", json={"username":"owner",**payload}, headers=headers)
        assert response.status_code == 200 and "HttpOnly" in response.headers["set-cookie"] and "Secure" in response.headers["set-cookie"]
        assert client.get("/api/auth/session").json()["authenticated"]
        # A password-only session cannot add a persistent authenticator or change a password.
        assert client.post("/api/auth/passkeys/options", json={}, headers=headers).status_code == 400
        assert client.put("/api/auth/password", json=payload, headers=headers).status_code == 400


def test_key_metadata_and_creation_api_reject_cross_origin_cross_account_and_extra_fields(tmp_path, monkeypatch):
    empty = tmp_path / "empty.json"
    empty.write_text('{"sources": []}')
    config = replace(load_config(), state_dir=tmp_path / "var", data_dir=tmp_path / "data",
        helps_dir=tmp_path / "helps", docs_dir=tmp_path / "docs", midi_sources_path=empty,
        dos_config_path=empty, statistics_path=tmp_path / "data/stats.sqlite3", auth_origin="https://account.test")
    app = create_app(config)
    store = app.state.accounts
    store.create_user("owner")
    store.create_user("other")
    with store._connect() as db:
        ident = db.execute("SELECT id FROM accounts WHERE username='owner'").fetchone()[0]
        other = db.execute("SELECT id FROM accounts WHERE username='other'").fetchone()[0]
        token, other_token = new_session(db, ident), new_session(db, other)
    monkeypatch.setattr("webauthn.verify_registration_response", lambda **kw: verified())
    with TestClient(app, base_url=config.auth_origin) as client:
        headers = {"Origin":config.auth_origin}
        assert client.post("/api/auth/passkeys/options", json={}, headers=headers).status_code == 403
        client.cookies.set("thelp_session", token)
        assert client.post("/api/auth/passkeys/options", json={}).status_code == 403
        request = client.post("/api/auth/passkeys/options", json={}, headers=headers).json()
        payload = {"ceremony_id":request["ceremony_id"],"credential":{},"name":"Mac"}
        assert client.post("/api/auth/passkeys/verify", json={**payload,"account_id":other}, headers=headers).status_code == 422
        client.cookies.set("thelp_session", other_token)
        assert client.post("/api/auth/passkeys/verify", json=payload, headers=headers).status_code == 400
        client.cookies.set("thelp_session", token)
        assert client.post("/api/auth/passkeys/verify", json=payload, headers=headers).status_code == 200
        key = client.get("/api/auth/security").json()["passkeys"][0]
        assert key["name"] == "Mac" and "public_key" not in key
        client.cookies.set("thelp_session", other_token)
        assert client.put('/api/auth/passkeys/'+key["id"], json={"name":"Other"}, headers=headers).status_code == 400
        client.cookies.set("thelp_session", token)
        assert client.put('/api/auth/passkeys/'+key["id"], json={"name":"Renamed"}, headers=headers).status_code == 200
