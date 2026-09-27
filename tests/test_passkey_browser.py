"""A real virtual authenticator enrolls and signs in through the Login dialog."""

from pathlib import Path
import os
import re
import subprocess
import sys
import tempfile

import pytest

from test_browser_smoke import CHROME, NODE, _free_port, _wait_for_file, _wait_for_url


@pytest.mark.skipif(NODE is None or CHROME is None, reason="Node.js and Chrome are required")
def test_passkey_enrollment_and_login_in_browser():
    with tempfile.TemporaryDirectory(prefix="thelp-passkey-state-") as state_dir:
        state = Path(state_dir)
        helps = state / "helps"
        helps.mkdir()
        port = _free_port()
        app_url = f"http://localhost:{port}/"
        server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "thelpviewer.server.app:app", "--host", "127.0.0.1",
             "--port", str(port), "--log-level", "warning"],
            cwd=Path.cwd(), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            env={**os.environ, "THELP_STATE_DIR": state_dir, "THELP_HELPS_DIR": str(helps),
                 "THELP_STATISTICS_PATH": str(state / "statistics.sqlite3"),
                 "THELP_AUTH_ORIGIN": app_url.rstrip("/")},
        )
        try:
            _wait_for_url(app_url + "healthz")
            bootstrap = server.stdout.readline().strip().split(": ", 1)[1]
            assert re.fullmatch(r"[A-Z2-9]{5}(?:-[A-Z2-9]{5}){4}", bootstrap)
            with tempfile.TemporaryDirectory(prefix="thelp-passkey-chrome-") as profile_dir:
                chrome = subprocess.Popen(
                    [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu",
                     "--disable-dev-shm-usage", "--no-first-run", "--no-default-browser-check",
                     "--remote-debugging-port=0", f"--user-data-dir={profile_dir}", "about:blank"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    env={**os.environ, "CHROME_HEADLESS": "1"},
                )
                try:
                    debugging_port = int(_wait_for_file(Path(profile_dir) / "DevToolsActivePort").splitlines()[0])
                    script = r'''
const [debuggingPort, appUrl, bootstrap] = process.argv.slice(1);
async function run() {
    const targetResponse = await fetch(`http://127.0.0.1:${debuggingPort}/json/new?${encodeURIComponent(appUrl)}`,
        { method: 'PUT' });
    if (!targetResponse.ok) { throw new Error(`Cannot create target: ${targetResponse.status}`); }
    const target = await targetResponse.json();
    const socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
        socket.addEventListener('open', resolve, { once: true });
        socket.addEventListener('error', reject, { once: true });
    });
    let sequence = 0;
    const pending = new Map();
    socket.addEventListener('message', (event) => {
        const message = JSON.parse(String(event.data));
        if (!pending.has(message.id)) { return; }
        const { resolve, reject } = pending.get(message.id);
        pending.delete(message.id);
        if (message.error) { reject(new Error(message.error.message)); }
        else { resolve(message.result); }
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
        const id = ++sequence;
        pending.set(id, { resolve, reject });
        socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async (expression, awaitPromise = false) => {
        const result = await send('Runtime.evaluate', { expression, awaitPromise, returnByValue: true });
        if (result.exceptionDetails) {
            throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
        }
        return result.result.value;
    };
    await send('Page.enable');
    await send('Runtime.enable');
    await send('WebAuthn.enable');
    await send('WebAuthn.addVirtualAuthenticator', { options: {
        protocol: 'ctap2', transport: 'internal', hasResidentKey: true,
        hasUserVerification: true, isUserVerified: true, automaticPresenceSimulation: true,
    } });
    await send('Page.navigate', { url: appUrl });
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            const item = Array.from(document.querySelectorAll('[data-tv-command="dialog-open"]'))
                .find((node) => node._tvMenuItem?.name.replaceAll('~', '') === 'Login / Passkey');
            if (item) { item.click(); resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Login menu did not load')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    await evaluate(`document.querySelector('.tv-login-window [data-tv-command="login-register"]').click()`);
    await evaluate(`(() => {
        const dialog = document.querySelector('.tv-registration-window');
        const inputs = dialog.querySelectorAll('.tv-input-line');
        inputs[0].value = 'Test User';
        inputs[1].value = 'test@example.test';
        inputs[2].value = 'INVALID-TOKEN';
        dialog.querySelector('[data-tv-command="register-confirm"]').click();
    })()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = () => {
            const status = document.querySelector('.tv-registration-window')?.closest('.tv-dialog-overlay')
                ?._tvView?.status?.root?.textContent || '';
            if (status.includes('XXXXX-XXXXX-XXXXX-XXXXX-XXXXX')) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Invalid token format was not shown: ' + status)); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    await evaluate(`(() => {
        const dialog = document.querySelector('.tv-registration-window');
        dialog.querySelectorAll('.tv-input-line')[2].value = 'AAAAA-AAAAA-AAAAA-AAAAA-AAAAA';
        dialog.querySelector('[data-tv-command="register-confirm"]').click();
    })()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = () => {
            const status = document.querySelector('.tv-registration-window')?.closest('.tv-dialog-overlay')
                ?._tvView?.status?.root?.textContent || '';
            if (status.includes('Registration request failed:')
                && status.includes('Invalid or expired registration token')) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Invalid token stage was not shown: ' + status)); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    await evaluate(`(() => {
        const dialog = document.querySelector('.tv-registration-window');
        const inputs = dialog.querySelectorAll('.tv-input-line');
        inputs[0].value = 'Test User';
        inputs[1].value = 'test@example.test';
        inputs[2].value = ${JSON.stringify(bootstrap)};
        dialog.querySelector('[data-tv-command="register-confirm"]').click();
    })()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 15000;
        const check = () => {
            const box = document.querySelector('.tv-msgbox-window');
            const status = document.querySelector('.tv-login-window')?.closest('.tv-dialog-overlay')
                ?._tvView?.status?.root?.textContent || '';
            if (box && !box.closest('.tv-dialog-overlay')?.hidden
                && box.textContent.includes('Registered and signed in as Test User')
                && status.includes('Signed in as Test User')) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Passkey confirmation did not open: ' + status)); return; }
            setTimeout(check, 50);
        };
        check();
    })`, true);
    await evaluate(`document.querySelector('.tv-msgbox-window [data-tv-command="msgbox-cmd"]').click()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = () => {
            const registration = document.querySelector('.tv-registration-window')?.closest('.tv-dialog-overlay');
            const login = document.querySelector('.tv-login-window')?.closest('.tv-dialog-overlay');
            if (registration?.hidden && login?.hidden) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Registration dialogs stayed open after OK')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    const tokenMenu = await evaluate(`Array.from(document.querySelectorAll('[data-tv-command="dialog-open"]'))
        .some((node) => node._tvMenuItem?.name.replaceAll('~', '') === 'Registration Token')`);
    if (!tokenMenu) { throw new Error('Admin registration-token menu is missing'); }
    await evaluate(`Array.from(document.querySelectorAll('[data-tv-command="dialog-open"]'))
        .find((node) => node._tvMenuItem?.name.replaceAll('~', '') === 'Registration Token').click()`);
    await evaluate(`document.querySelector('.tv-registration-token-window [data-tv-command="token-generate"]').click()`);
    const issuedToken = await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = () => {
            const token = document.querySelector('.tv-registration-token-window .tv-input-line')?.value || '';
            if (/^[A-Z2-9]{5}(?:-[A-Z2-9]{5}){4}$/.test(token)) { resolve(token); return; }
            if (Date.now() > deadline) { reject(new Error('Admin token was not generated')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    if (!/^[A-Z2-9]{5}(?:-[A-Z2-9]{5}){4}$/.test(issuedToken)) {
        throw new Error('Generated registration token has the wrong format');
    }
    await evaluate(`document.querySelector('.tv-registration-token-window [data-tv-command="token-close"]').click()`);
    await evaluate(`Array.from(document.querySelectorAll('[data-tv-command="dialog-open"]'))
        .find((node) => node._tvMenuItem?.name.replaceAll('~', '') === 'Registration Token').click()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = () => {
            const dialog = document.querySelector('.tv-registration-token-window');
            const row = dialog?.querySelector('.tv-vlist-item');
            const remove = dialog?.querySelector('[data-tv-command="token-delete"]');
            if (row?.textContent.includes(${JSON.stringify(issuedToken)}) && remove?.disabled) {
                resolve(true); return;
            }
            if (Date.now() > deadline) { reject(new Error('Issued token was not listed after reopening')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    await evaluate(`document.querySelector('.tv-registration-token-window .tv-vlist-item').click()`);
    await evaluate(`(() => {
        const dialog = document.querySelector('.tv-registration-token-window');
        if (dialog.querySelector('[data-tv-command="token-delete"]').disabled) {
            throw new Error('Delete stayed disabled after selecting a token');
        }
        if (dialog.querySelector('.tv-input-line').value !== ${JSON.stringify(issuedToken)}) {
            throw new Error('Selected token did not appear in the input');
        }
        dialog.querySelector('[data-tv-command="token-delete"]').click();
    })()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = () => {
            const box = Array.from(document.querySelectorAll('.tv-msgbox-window')).find((item) => (
                !item.closest('.tv-dialog-overlay')?.hidden
                && item.textContent.includes('Delete the selected registration token?')
            ));
            if (box) {
                resolve(true); return;
            }
            if (Date.now() > deadline) { reject(new Error('Delete confirmation did not open')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    const closePoint = await evaluate(`(() => {
        const box = Array.from(document.querySelectorAll('.tv-msgbox-window'))
            .find((item) => !item.closest('.tv-dialog-overlay')?.hidden);
        const rect = box.querySelector('.tv-dialog-close-control').getBoundingClientRect();
        return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
    })()`);
    await send('Input.dispatchMouseEvent', {
        type: 'mousePressed', x: closePoint.x, y: closePoint.y, button: 'left', clickCount: 1,
    });
    await send('Input.dispatchMouseEvent', {
        type: 'mouseReleased', x: closePoint.x, y: closePoint.y, button: 'left', clickCount: 1,
    });
    const afterClose = await evaluate(`fetch('/api/auth/registration-tokens')
        .then((response) => response.json())`, true);
    if (!afterClose.tokens.some((item) => item.token === issuedToken)) {
        throw new Error('Closing the confirmation revoked the token');
    }
    await evaluate(`document.querySelector('.tv-registration-token-window [data-tv-command="token-delete"]').click()`);
    await evaluate(`Array.from(document.querySelectorAll('.tv-msgbox-window'))
        .find((item) => !item.closest('.tv-dialog-overlay')?.hidden)
        .dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))`);
    const afterEscape = await evaluate(`fetch('/api/auth/registration-tokens')
        .then((response) => response.json())`, true);
    if (!afterEscape.tokens.some((item) => item.token === issuedToken)) {
        throw new Error('Escape revoked the token');
    }
    await evaluate(`document.querySelector('.tv-registration-token-window [data-tv-command="token-delete"]').click()`);
    await evaluate(`Array.from(document.querySelectorAll('.tv-msgbox-window'))
        .find((item) => !item.closest('.tv-dialog-overlay')?.hidden)
        .querySelector('[data-tv-command="msgbox-cmd"]').click()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = () => {
            const dialog = document.querySelector('.tv-registration-token-window');
            if (!dialog?.querySelector('.tv-vlist-item')
                && dialog?.textContent.includes('Registration token deleted.')) {
                resolve(true); return;
            }
            if (Date.now() > deadline) { reject(new Error('Deleted token remained in the list')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    await evaluate(`document.querySelector('.tv-registration-token-window [data-tv-command="token-close"]').click()`);
    await evaluate(`Array.from(document.querySelectorAll('[data-tv-command="dialog-open"]'))
        .find((node) => node._tvMenuItem?.name.replaceAll('~', '') === 'Login / Passkey').click()`);
    await evaluate(`document.querySelector('.tv-login-window [data-tv-command="login-sign-out"]').click()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = () => {
            const status = document.querySelector('.tv-login-window')?.closest('.tv-dialog-overlay')
                ?._tvView?.status?.root?.textContent || '';
            const tokenMenu = Array.from(document.querySelectorAll('[data-tv-command="dialog-open"]'))
                .some((node) => node._tvMenuItem?.name.replaceAll('~', '') === 'Registration Token');
            if (status.includes('Sign in, or register') && !tokenMenu) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Passkey sign-out failed: ' + status)); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    const tokenMenuAfterSignOut = await evaluate(`Array.from(document.querySelectorAll('[data-tv-command="dialog-open"]'))
        .some((node) => node._tvMenuItem?.name.replaceAll('~', '') === 'Registration Token')`);
    if (tokenMenuAfterSignOut) { throw new Error('Admin registration-token menu remained after sign-out'); }
    await evaluate(`(() => {
        const dialog = document.querySelector('.tv-login-window');
        dialog.querySelector('.tv-input-line').value = 'test@example.test';
        dialog.querySelector('[data-tv-command="login-sign-in"]').click();
    })()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 15000;
        const check = () => {
            const status = document.querySelector('.tv-login-window')?.closest('.tv-dialog-overlay')
                ?._tvView?.status?.root?.textContent || '';
            if (status.includes('Signed in as Test User')) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Passkey sign-in failed: ' + status)); return; }
            setTimeout(check, 50);
        };
        check();
    })`, true);
    const session = await evaluate(`fetch('/api/auth/session').then((response) => response.json())`, true);
    if (!session.authenticated || session.user.username !== 'test@example.test'
        || session.user.role !== 'admin') {
        throw new Error('Authenticated server session is missing');
    }
    socket.close();
}
const timeout = setTimeout(() => { process.stderr.write('Passkey browser test timed out\n'); process.exit(1); }, 45000);
run().then(() => { clearTimeout(timeout); process.exit(0); })
    .catch((error) => { clearTimeout(timeout); process.stderr.write(String(error.stack || error) + '\n'); process.exit(1); });
'''
                    result = subprocess.run(
                        [NODE, "-e", script, str(debugging_port), app_url, bootstrap],
                        capture_output=True, text=True, timeout=50,
                    )
                    assert result.returncode == 0, result.stderr
                finally:
                    chrome.terminate()
                    try:
                        chrome.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        chrome.kill()
                        chrome.wait(timeout=5)
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
