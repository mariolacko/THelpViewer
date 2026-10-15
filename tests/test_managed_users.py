"""Administrator-created profiles enroll their own, account-bound Passkeys."""

from dataclasses import replace
from types import SimpleNamespace
import re
import time

from fastapi.testclient import TestClient
import pytest

from thelpviewer.server.accounts.sessions import new_session
from thelpviewer.server.accounts.common import AccountError
from thelpviewer.server.app import create_app
from thelpviewer.server.config import load_config


def test_admin_creates_member_and_bound_invitation_without_changing_session(tmp_path, monkeypatch):
    manifest = tmp_path / "empty.json"
    manifest.write_text('{"sources": []}')
    config = replace(load_config(), state_dir=tmp_path / "var", helps_dir=tmp_path / "helps",
                     midi_sources_path=manifest, dos_config_path=manifest,
                     statistics_path=tmp_path / "var" / "statistics.sqlite3",
                     auth_origin="https://accounts.example.test", dev_auto_login=False)
    app = create_app(config)
    store = app.state.accounts
    store.create_user("admin", "Admin")
    with store._connect() as database:
        admin_id = database.execute("SELECT id FROM accounts WHERE username='admin'").fetchone()[0]
        admin_token = new_session(database, admin_id)
    payload = {"first_name": " Ján ", "last_name": " Novák ", "nickname": " JN ", "email": " JAN@EXAMPLE.TEST "}
    headers = {"Origin": config.auth_origin}
    with TestClient(app, base_url=config.auth_origin) as admin:
        assert admin.post("/api/admin/users", json=payload, headers=headers).status_code == 403
        admin.cookies.set("thelp_session", admin_token)
        original = store.session_user(admin_token)
        for bad_headers in ({}, {"Origin": "https://evil.test"}, {**headers, "Host": "evil.test"},
                            {**headers, "Sec-Fetch-Site": "cross-site"}):
            assert admin.post("/api/admin/users", json=payload, headers=bad_headers).status_code == 403
        for field in ("role", "active", "protected_admin", "disk_capacity_mb", "display_name"):
            assert admin.post("/api/admin/users", json={**payload, field: "admin"}, headers=headers).status_code == 422
        assert admin.post("/api/admin/users", json={**payload, "email": "invalid"}, headers=headers).status_code == 400
        assert admin.post("/api/admin/users", json={**payload, "first_name": "", "nickname": ""}, headers=headers).status_code == 400
        for field in ("first_name", "last_name", "nickname"):
            assert admin.post("/api/admin/users", json={**payload, field: "a\nb"}, headers=headers).status_code == 400
            assert admin.post("/api/admin/users", json={**payload, field: "x" * 101}, headers=headers).status_code == 422
        result = admin.post("/api/admin/users", json=payload, headers=headers)
        assert result.status_code == 201 and result.headers["cache-control"] == "no-store"
        assert "set-cookie" not in result.headers and admin.cookies["thelp_session"] == admin_token
        assert store.session_user(admin_token) == original
        data = result.json()
        user, invitation = data["user"], data["invitation"]
        assert user["email"] == user["username"] == "jan@example.test"
        assert (user["first_name"], user["last_name"], user["nickname"], user["display_name"]) == ("Ján", "Novák", "JN", "JN")
        assert user["role"] == "member" and user["active"] and not user["protected_admin"]
        assert user["disk_capacity_mb"] is None and user["disk"]["capacity_bytes"] == 64 * 1048576
        assert re.fullmatch(r"[A-Z2-9]{5}(?:-[A-Z2-9]{5}){4}", invitation["token"])
        assert 3590 <= invitation["expires_at"] - time.time() <= 3600
        assert admin.post("/api/admin/users", json=payload, headers=headers).status_code == 400
        with store._connect() as database:
            assert database.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 2
            assert database.execute("SELECT COUNT(*) FROM credentials WHERE account_id=?", (user["id"],)).fetchone()[0] == 0
            member_token = new_session(database, user["id"])
        admin.cookies.set("thelp_session", member_token)
        assert admin.post("/api/admin/users", json=payload, headers=headers).status_code == 403
        admin.cookies.set("thelp_session", admin_token)
        assert admin.get("/api/auth/session").json()["user"] == original

    def verify(**kwargs):
        assert kwargs["expected_rp_id"] == "accounts.example.test"
        assert kwargs["expected_origin"] == config.auth_origin
        assert kwargs["require_user_verification"] is True
        return SimpleNamespace(credential_id=b"new-member-key", credential_public_key=b"member-public-key",
                               sign_count=0, credential_device_type="multiDevice", credential_backed_up=True)

    monkeypatch.setattr("webauthn.verify_registration_response", verify)
    # A separate new-user client completes Register with the bound invitation.
    with TestClient(app, base_url=config.auth_origin) as member:
        registration = {"name": "Different input", "email": user["email"], "token": invitation["token"].lower(),
                        "first_name": "Different", "last_name": "Input", "nickname": "Other"}
        options = member.post("/api/auth/passkey/register/options", json=registration, headers=headers)
        assert options.status_code == 200
        enrollment = options.json()
        assert enrollment["enrollment"] is True and enrollment["profile"]["nickname"] == "JN"
        assert enrollment["options"]["user"]["name"] == user["email"]
        verified = member.post("/api/auth/passkey/enroll/verify", json={
            "ceremony_id": enrollment["ceremony_id"], "credential": {"id": "mock"},
        }, headers=headers)
        assert verified.status_code == 200 and verified.json()["authenticated"]
        member_session = member.get("/api/auth/session").json()
        assert member_session["user"]["role"] == "member" and member_session["user"]["nickname"] == "JN"
        assert store.session_account_id(member.cookies["thelp_session"]) == user["id"]
        assert store.session_user(admin_token) == original
        assert member.post("/api/auth/passkey/register/options", json=registration, headers=headers).status_code == 400
        assert member.post("/api/auth/passkey/enroll/verify", json={
            "ceremony_id": enrollment["ceremony_id"], "credential": {"id": "mock"},
        }, headers=headers).status_code == 400


def test_managed_invitation_is_bound_expiring_and_respects_disabled_account(tmp_path):
    from thelpviewer.server.accounts.store import AccountStore
    store = AccountStore(tmp_path)
    store.create_user("admin", "Admin")
    with store._connect() as database:
        ident = database.execute("SELECT id FROM accounts WHERE username='admin'").fetchone()[0]
        admin = new_session(database, ident)
    first = store.create_managed_user(admin, "first@example.test", "First")
    second = store.create_managed_user(admin, "second@example.test", "Second")
    with pytest.raises(AccountError):
        store.new_registration_options("Second", "second@example.test", first["invitation"]["token"], "example.test", "THelpViewer")
    with store._connect() as database:
        database.execute("UPDATE invitations SET expires_at=0 WHERE account_id=?", (first["user"]["id"],))
        database.execute("UPDATE accounts SET active=0 WHERE id=?", (second["user"]["id"],))
    for record in (first, second):
        with pytest.raises(AccountError):
            store.new_registration_options(record["user"]["display_name"], record["user"]["email"],
                                           record["invitation"]["token"], "example.test", "THelpViewer")


def test_self_registration_stores_profile_details_with_ceremony(tmp_path, monkeypatch):
    from thelpviewer.server.accounts.store import AccountStore
    store = AccountStore(tmp_path)
    token = store.bootstrap_token()
    options = store.new_registration_options("Ján Novák", "jan@example.test", token, "example.test", "THelpViewer",
                                              first_name=" Ján ", last_name=" Novák ", nickname=" JN ")
    assert options["options"]["user"]["displayName"] == "JN"
    monkeypatch.setattr("webauthn.verify_registration_response", lambda **kwargs: SimpleNamespace(
        credential_id=b"first-key", credential_public_key=b"public-key", sign_count=0,
        credential_device_type="multiDevice", credential_backed_up=True))
    session = store.verify_new_registration(options["ceremony_id"], {"id": "mock"}, "example.test", "https://example.test")
    user = store.session_user(session)
    assert (user["first_name"], user["last_name"], user["nickname"], user["display_name"]) == ("Ján", "Novák", "JN", "JN")
    assert user["role"] == "admin"
