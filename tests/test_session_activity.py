"""Rolling login inactivity and foreground-only renewal, independent of polling."""
from contextlib import closing
import sqlite3
import time
import shutil
import subprocess

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from thelpviewer.server.accounts.common import AccountError, token_hash
from thelpviewer.server.accounts.sessions import new_session, owner, SESSION_LIFETIME, SESSION_MAX_LIFETIME
from thelpviewer.server.accounts.store import AccountStore
from thelpviewer.server.config import load_config
from thelpviewer.server.routes.auth import create_auth_router
from dataclasses import replace


def test_inactivity_renewal_expiry_revocation_and_recent_proof(tmp_path, monkeypatch):
    now = [int(time.time())]
    monkeypatch.setattr(time, "time", lambda: now[0])
    store = AccountStore(tmp_path)
    store.create_user("reader")
    with closing(store._connect()) as db, db:
        ident = db.execute("SELECT id FROM accounts").fetchone()[0]
        token = new_session(db, ident)
    start = now[0]
    now[0] += SESSION_LIFETIME - 1
    assert store.session_user(token)
    assert store.session_activity(token)
    with closing(store._connect()) as db:
        row = db.execute("SELECT * FROM sessions").fetchone()
        assert row["expires_at"] == now[0] + SESSION_LIFETIME
        assert row["verified_at"] == start and row["auth_method"] == "passkey"
        with pytest.raises(AccountError, match="Confirm"):
            owner(db, token, recent_passkey=True)
    now[0] += SESSION_LIFETIME
    assert store.session_user(token) is None
    assert store.session_account_id(token) is None
    assert not store.session_activity(token)  # A late heartbeat cannot revive it.
    with pytest.raises(AccountError):
        store.list_users(token)
    with closing(store._connect()) as db, db:
        token = new_session(db, ident)
        db.execute("UPDATE accounts SET active=0")
    assert not store.session_activity(token)
    with closing(store._connect()) as db, db:
        db.execute("UPDATE accounts SET active=1")
    store.logout(token)
    assert not store.session_activity(token)


def test_active_session_still_requires_new_login_after_thirty_days(tmp_path, monkeypatch):
    now = [int(time.time())]
    monkeypatch.setattr(time, "time", lambda: now[0])
    store = AccountStore(tmp_path)
    store.create_user("reader")
    with closing(store._connect()) as db, db:
        token = new_session(db, db.execute("SELECT id FROM accounts").fetchone()[0])
    start = now[0]
    for _ in range(60):
        now[0] += SESSION_LIFETIME // 2
        if now[0] < start + SESSION_MAX_LIFETIME:
            assert store.session_activity(token)
        else:
            assert not store.session_activity(token)
    assert store.session_user(token) is None


def test_old_sessions_get_at_most_one_day_without_reviving_expired_ones(tmp_path, monkeypatch):
    now = int(time.time())
    monkeypatch.setattr(time, "time", lambda: now)
    with sqlite3.connect(tmp_path / "accounts.sqlite3") as db:
        db.executescript("CREATE TABLE accounts(id TEXT PRIMARY KEY,username TEXT,display_name TEXT,active INTEGER DEFAULT 1);"
                        "INSERT INTO accounts VALUES ('a','reader','Reader',1);"
                        "CREATE TABLE sessions(token_hash TEXT PRIMARY KEY,account_id TEXT,expires_at INTEGER);")
        db.executemany("INSERT INTO sessions VALUES (?,'a',?)", [(token_hash("valid"), now+30*86400),
                       (token_hash("short"), now+100), (token_hash("expired"), now-1)])
    store = AccountStore(tmp_path)
    with closing(store._connect()) as db:
        rows = {row["token_hash"]: row for row in db.execute("SELECT * FROM sessions")}
    assert rows[token_hash("valid")]["expires_at"] == now + SESSION_LIFETIME
    assert rows[token_hash("short")]["expires_at"] == now + 100
    assert store.session_user("expired") is None and not store.session_activity("expired")
    # Opening the store a second time cannot roll the one-time migration forward.
    with closing(store._connect()) as db:
        assert db.execute("SELECT created_at FROM sessions LIMIT 1").fetchone()[0] == now


def test_activity_http_cookie_origin_and_background_get(tmp_path):
    config = replace(load_config(), auth_origin="https://account.test", dev_auto_login=False)
    store = AccountStore(tmp_path)
    store.create_user("reader")
    with closing(store._connect()) as db, db:
        token = new_session(db, db.execute("SELECT id FROM accounts").fetchone()[0])
        before = int(time.time()) + 100
        db.execute("UPDATE sessions SET expires_at=?", (before,))
    app = FastAPI()
    app.include_router(create_auth_router(config, store))
    with TestClient(app, base_url=config.auth_origin) as client:
        client.cookies.set("thelp_session", token)
        for _ in range(3):
            response = client.get("/api/auth/session")
            assert response.json()["authenticated"] and "set-cookie" not in response.headers
        with closing(store._connect()) as db:
            assert db.execute("SELECT expires_at FROM sessions").fetchone()[0] == before
        assert client.post("/api/auth/activity").status_code == 403
        assert client.post("/api/auth/activity", headers={"Origin": "https://evil.test"}).status_code == 403
        response = client.post("/api/auth/activity", headers={"Origin": config.auth_origin})
        assert response.json()["authenticated"]
        cookie = response.headers["set-cookie"]
        assert all(part in cookie for part in ["Max-Age=86400", "HttpOnly", "Secure", "SameSite=strict"])
        assert response.headers["cache-control"] == "no-store"
        store.logout(token)
        response = client.post("/api/auth/activity", headers={"Origin": config.auth_origin})
        assert not response.json()["authenticated"] and "Max-Age=0" in response.headers["set-cookie"]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required")
def test_browser_activity_not_background_polling_renews_and_stale_reply_is_ignored():
    script = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('www/assets/tv-shell.js','utf8');
const code=source.slice(source.indexOf('class TVSessionActivity {'),source.indexOf('class TVApplication extends'))+';this.Activity=TVSessionActivity;';
const listeners=new Map(),requests=[];let tick=100000,timer,reply,hold=false,changed=0;
const document={hidden:false,addEventListener(type,fn){listeners.set(type,fn);},removeEventListener(type){listeners.delete(type);}};
const context={document,AbortSignal,Date:{now:()=>tick},setInterval(fn){timer=fn;return 1;},clearInterval(){timer=null;},
 fetch:async(url,options)=>{requests.push({url,...options});if(hold)await new Promise(resolve=>reply=resolve);return{ok:true,json:async()=>({authenticated:true,user:{username:'reader'}})};}};
vm.runInNewContext(code,context);
(async()=>{
 const activity=new context.Activity(session=>{changed++;activity.setSession(session);}).start();
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(requests[0].method,'GET');assert.equal(requests.length,2);
 assert.equal(requests[1].method,'POST'); // Initial foreground visit renews immediately.
 tick+=60000;timer();await new Promise(resolve=>setImmediate(resolve));
 assert.equal(requests.at(-1).method,'GET'); // Idle background polling must not renew.
 listeners.get('keydown')({isTrusted:false});tick+=60000;timer();await new Promise(resolve=>setImmediate(resolve));
 assert.equal(requests.at(-1).method,'GET');
 document.hidden=true;listeners.get('pointerdown')({isTrusted:true});tick+=60000;timer();await new Promise(resolve=>setImmediate(resolve));
 assert.equal(requests.at(-1).method,'GET');
 document.hidden=false;tick+=60000;listeners.get('visibilitychange')();await new Promise(resolve=>setImmediate(resolve));
 assert.equal(requests.at(-1).url,'/api/auth/activity');
 tick+=60000;listeners.get('wheel')({isTrusted:true});await new Promise(resolve=>setImmediate(resolve));
 assert.equal(requests.at(-1).method,'POST');
 hold=true;tick+=60000;listeners.get('keydown')({isTrusted:true});const before=changed;
 activity.setSession(null);reply();await activity.request;assert.equal(changed,before);
 activity.destroy();assert.equal(listeners.size,0);assert.equal(timer,null);
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
    result = subprocess.run([shutil.which("node"), "-e", script], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
