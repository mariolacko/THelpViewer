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
        empty = state / "empty.json"
        empty.write_text('{"sources": []}')
        (state / "content-settings.json").write_text('{"configured":true,"help_groups":[],"dos_packages":[]}')
        port = _free_port()
        app_url = f"http://localhost:{port}/"
        server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "thelpviewer.server.app:app", "--host", "127.0.0.1",
             "--port", str(port), "--log-level", "warning"],
            cwd=Path.cwd(), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            env={**os.environ, "THELP_STATE_DIR": state_dir, "THELP_HELPS_DIR": str(helps),
                 "THELP_STATISTICS_PATH": str(state / "statistics.sqlite3"),
                 "THELP_MIDI_SOURCES_PATH": str(empty), "THELP_DOS_CONFIG_PATH": str(empty),
                 "THELP_AUTH_ORIGIN": app_url.rstrip("/")},
        )
        try:
            _wait_for_url(app_url + "healthz")
            bootstrap = server.stdout.readline().strip().split(": ", 1)[1]
            assert re.fullmatch(r"[A-Z2-9]{5}(?:-[A-Z2-9]{5}){4}", bootstrap)
            with tempfile.TemporaryDirectory(prefix="thelp-passkey-chrome-") as profile_dir:
                chrome = subprocess.Popen(
                    [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--window-size=1280,900",
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
    const firstAuthenticator = await send('WebAuthn.addVirtualAuthenticator', { options: {
        protocol: 'ctap2', transport: 'internal', hasResidentKey: true,
        hasUserVerification: true, isUserVerified: true, automaticPresenceSimulation: true,
    } });
    await send('Page.navigate', { url: appUrl });
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            const item = document.querySelector('[data-tv-command="account-login"]');
            if (item) { item.click(); resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Login menu did not load')); return; }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    const guestPlacement=await evaluate(`(()=>{const nav=document.querySelector('.tv-menu-items'),item=document.querySelector('.tv-menu-right');return nav&&item&&Math.abs(nav.getBoundingClientRect().right-item.getBoundingClientRect().right)<1;})()`);
    if(!guestPlacement)throw new Error('Login was not aligned to the right');
    await evaluate(`document.querySelector('.tv-login-window [data-tv-command="login-register"]').click()`);
    await evaluate(`(() => {
        const dialog = document.querySelector('.tv-registration-window');
        const view = dialog.closest('.tv-dialog-overlay')._tvView;
        view.name.setData('Test'); view.lastName.setData('User');
        view.email.setData('test@example.test'); view.token.setData('INVALID-TOKEN');
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
        dialog.closest('.tv-dialog-overlay')._tvView.token.setData('AAAAA-AAAAA-AAAAA-AAAAA-AAAAA');
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
        const view = dialog.closest('.tv-dialog-overlay')._tvView;
        view.name.setData('Test'); view.lastName.setData('User');
        view.email.setData('test@example.test'); view.token.setData(${JSON.stringify(bootstrap)});
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
    const tokenMenu = await evaluate(`Array.from(document.querySelectorAll('[data-tv-command="account-registration-token"]'))
        .some((node) => node._tvMenuItem?.name.replaceAll('~', '') === 'Registration Token')`);
    if (!tokenMenu) { throw new Error('Admin registration-token menu is missing'); }
    // Manage actual credentials through the account's shared TVision controls.
    const waitSecurity = async expression => evaluate(`new Promise((resolve,reject)=>{
        const end=Date.now()+15000;const check=()=>{if(${expression}){resolve(true);return;}
        if(Date.now()>end){reject(Error('Account security did not finish: '+window.securityDialog?.status?.text));return;}
        setTimeout(check,30);};check();})`,true);
    await evaluate(`document.querySelector('[data-tv-command="account-profile"]').click()`);
    await waitSecurity(`(window.securityDialog=document.querySelector('.tv-account-window')?.closest('.tv-dialog-overlay')?._tvView)
        && !securityDialog.saveButton.disabled && securityDialog.selectedPasskey`);
    if(!await evaluate(`securityDialog.selectedPasskey.name===securityDialog.passkeyName.getData()
        && securityDialog.selectedPasskey.name!=='Passkey'`))throw Error('Registration did not save its suggested key name');
    await evaluate(`void securityDialog.firstNameInput.focus()`);
    await send('Input.dispatchKeyEvent', {type:'keyDown',key:'p',code:'KeyP',modifiers:1});
    await send('Input.dispatchKeyEvent', {type:'keyUp',key:'p',code:'KeyP',modifiers:1});
    if(!await evaluate(`document.activeElement===securityDialog.passwordInput.root`))throw Error('Alt+P did not focus New password');
    await evaluate(`(()=>{
        if(securityDialog.passwordInput.root.type!=='password'||securityDialog.repeatPassword.root.type!=='password')throw Error('Unmasked account password');
        securityDialog.passkeyName.setData('Windows - Edge');
        securityDialog.renamePasskeyButton.root.click();
    })()`);
    await waitSecurity(`securityDialog.status.text==='Passkey renamed.'`);
    await evaluate(`(()=>{
        securityDialog.passwordInput.setData('short');securityDialog.repeatPassword.setData('short');
        securityDialog.passwordButton.root.click();
        if(!securityDialog.status.text.includes('15-128'))throw Error('Weak password accepted by the dialog');
        securityDialog.passwordInput.setData('Moonlit rivers carry 42 boats!');
        securityDialog.repeatPassword.setData('Moonlit rivers carry 42 boats!');
        securityDialog.passwordButton.root.click();
    })()`);
    await waitSecurity(`securityDialog.status.text.includes('Password saved.')`);
    // The existing key confirms the session, then a second real authenticator
    // creates the new key. This models adding another device, not a mock key.
    await send('Runtime.addBinding',{name:'testPreparePasskeyDevice'});
    const switchDevice = async event => {
        const message=JSON.parse(String(event.data));
        if(message.method!=='Runtime.bindingCalled'||message.params.name!=='testPreparePasskeyDevice')return;
        await send('WebAuthn.removeVirtualAuthenticator',{authenticatorId:firstAuthenticator.authenticatorId});
        await send('WebAuthn.addVirtualAuthenticator',{options:{protocol:'ctap2',transport:'internal',
            hasResidentKey:true,hasUserVerification:true,isUserVerified:true,automaticPresenceSimulation:true}});
        await evaluate(`window.testPasskeyDeviceReady()`);
    };
    socket.addEventListener('message',switchDevice);
    await evaluate(`(()=>{
        window.accountOriginalCreate=navigator.credentials.create.bind(navigator.credentials);
        navigator.credentials.create=async options=>{
            await new Promise(resolve=>{window.testPasskeyDeviceReady=resolve;window.testPreparePasskeyDevice('ready');});
            return window.accountOriginalCreate(options);
        };
        securityDialog.passkeyName.setData('macOS - Safari');securityDialog.addPasskeyButton.root.click();
    })()`);
    await waitSecurity(`securityDialog.status.text==='New Passkey added.'`);
    socket.removeEventListener('message',switchDevice);
    await send('Runtime.removeBinding',{name:'testPreparePasskeyDevice'});
    await evaluate(`navigator.credentials.create=window.accountOriginalCreate`);
    const security=await evaluate(`fetch('/api/auth/security').then(r=>r.json())`,true);
    if(!security.password_set||security.passkeys.length!==2
        ||!security.passkeys.some(key=>key.name==='Windows - Edge')||!security.passkeys.some(key=>key.name==='macOS - Safari')){
        throw Error('Named Passkeys/password were not saved: '+JSON.stringify(security));
    }
    if(!await evaluate(`!securityDialog.passwordInput.getData()&&!securityDialog.repeatPassword.getData()`))throw Error('Account retained password text');
    if(process.env.THELP_ACCOUNT_SCREENSHOT){const shot=await send('Page.captureScreenshot',{format:'png'});
        require('node:fs').writeFileSync(process.env.THELP_ACCOUNT_SCREENSHOT,Buffer.from(shot.data,'base64'));}
    await evaluate(`securityDialog.close()`);
    const accountTitle=await evaluate(`document.querySelector('.tv-menu-right > .tv-menu-root > .tv-menu-button')?.textContent`);
    if(accountTitle!=='Test User')throw new Error('Authenticated user name missing from top menu: '+accountTitle);
    await evaluate(`(()=>{window.accountTestLogin=document.querySelector('.tv-login-window').closest('.tv-dialog-overlay')._tvView;
        accountTestLogin.updateSession({enabled:true,authenticated:true,user:{username:'member@example.test',display_name:'Member One',role:'member'}});})()`);
    if(await evaluate(`document.querySelector('.tv-menu-right [data-tv-command="account-server-configuration"]')!==null||document.querySelector('.tv-menu-right [data-tv-command="account-registration-token"]')!==null`))throw new Error('Member sees admin account menu');
    await evaluate(`document.querySelector('.tv-users-window [data-tv-command="account-add-user"]').click()`);
    if(await evaluate(`!document.querySelector('.tv-add-user-window').closest('.tv-dialog-overlay').hidden`))throw new Error('Member opened Add user');
    await evaluate(`accountTestLogin.updateSession({enabled:true,authenticated:true,user:{username:'member@example.test',display_name:'Member ~Two~',role:'member'}})`);
    if(await evaluate(`document.querySelector('.tv-menu-right .tv-menu-button')?.textContent`)!=='Member ~Two~')throw new Error('Same-role user name change was not rendered literally');
    await evaluate(`accountTestLogin.updateSession({enabled:true,authenticated:false})`);
    if(await evaluate(`document.querySelector('.tv-menu-right [data-tv-command="account-login"]')?.textContent`)!=='Login')throw new Error('Member sign-out did not restore Login');
    await evaluate(`accountTestLogin.refreshSession()`,true);
    await evaluate(`Array.from(document.querySelectorAll('[data-tv-command="account-server-configuration"]'))
        .find((node) => node._tvMenuItem?.name.replaceAll('~', '') === 'Server Configuration').click()`);
    await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+5000;const check=()=>{
        const input=document.querySelector('.tv-server-configuration-window .tv-input-line');
        if(input?.value==='64'){resolve(true);return;}
        if(Date.now()>deadline){reject(new Error('Default DOS overlay capacity did not load'));return;}setTimeout(check,30);
    };check();})`,true);
    await evaluate(`(()=>{const dialog=document.querySelector('.tv-server-configuration-window');
        dialog.querySelector('.tv-input-line').value='96';dialog.querySelector('[data-tv-command="server-settings-save"]').click();})()`);
    await evaluate(`new Promise((resolve,reject)=>{const deadline=Date.now()+5000;const check=()=>{
        if(document.querySelector('.tv-server-configuration-window')?.textContent.includes('Saved.')){resolve(true);return;}
        if(Date.now()>deadline){reject(new Error('DOS overlay settings did not save'));return;}setTimeout(check,30);
    };check();})`,true);
    const settings=await evaluate(`fetch('/api/admin/settings').then(r=>r.json())`,true);
    if(settings.dos_user_disk_mb!==96)throw new Error('DOS overlay capacity was not persisted');
    await evaluate(`document.querySelector('.tv-server-configuration-window [data-tv-command="server-settings-cancel"]').click()`);
    await evaluate(`Array.from(document.querySelectorAll('[data-tv-command="account-registration-token"]'))
        .find((node) => node._tvMenuItem?.name.replaceAll('~', '') === 'Registration Token').click()`);
    await evaluate(`(() => {
        const dialog = accountTestLogin.owner.dialogManager.get('registration-token');
        if (!dialog.copyButton?.disabled) { throw new Error('Copy must be disabled before a token is available'); }
    })()`);
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
    await send('Browser.grantPermissions', { origin: new URL(appUrl).origin,
        permissions: ['clipboardReadWrite', 'clipboardSanitizedWrite'] });
    const copyPoint = await evaluate(`(() => {
        const dialog = accountTestLogin.owner.dialogManager.get('registration-token');
        const buttons = dialog.content.children.filter(view => view instanceof window.THelpViewerTV.TVButton);
        const body = dialog.content.root.getBoundingClientRect();
        if (buttons.length !== 4 || dialog.copyButton.disabled) { throw new Error('Token dialog lacks four usable buttons'); }
        buttons.forEach((button, index) => {
            const rect = button.root.getBoundingClientRect();
            if (rect.left < body.left || rect.right > body.right || rect.bottom > body.bottom
                    || (index && rect.left <= buttons[index - 1].root.getBoundingClientRect().right)) {
                throw new Error('Token dialog buttons overlap or leave the client area');
            }
        });
        const rect = dialog.copyButton.root.getBoundingClientRect();
        return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 4 };
    })()`);
    await send('Input.dispatchMouseEvent', { type: 'mousePressed', ...copyPoint, button: 'left', clickCount: 1 });
    await send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...copyPoint, button: 'left', clickCount: 1 });
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 3000;
        const check = () => {
            const dialog = accountTestLogin.owner.dialogManager.get('registration-token');
            if (dialog.status.text === 'Token copied to clipboard.') { resolve(); return; }
            if (Date.now() > deadline) { reject(new Error('Copy button did not confirm clipboard success')); return; }
            setTimeout(check, 20);
        }; check();
    })`, true);
    if (!await evaluate(`navigator.clipboard.readText().then(text => text === ${JSON.stringify(issuedToken)})`, true)) {
        throw new Error('Clipboard does not contain exactly the generated token');
    }
    await evaluate(`document.querySelector('.tv-registration-token-window [data-tv-command="token-close"]').click()`);
    await evaluate(`Array.from(document.querySelectorAll('[data-tv-command="account-registration-token"]'))
        .find((node) => node._tvMenuItem?.name.replaceAll('~', '') === 'Registration Token').click()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = () => {
            const dialog = document.querySelector('.tv-registration-token-window');
            const row = dialog?.querySelector('.tv-vlist-item');
            const remove = dialog?.querySelector('[data-tv-command="token-delete"]');
            const copy = dialog?.closest('.tv-dialog-overlay')._tvView.copyButton;
            if (row?.textContent.includes(${JSON.stringify(issuedToken)}) && remove?.disabled && copy?.disabled) {
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
        if (dialog.closest('.tv-dialog-overlay')._tvView.copyButton.disabled) {
            throw new Error('Copy stayed disabled after selecting a token');
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
    await evaluate(`(async () => {
        const dialog = accountTestLogin.owner.dialogManager.get('registration-token');
        if (!dialog.copyButton.disabled) { throw new Error('Deleted token remains copyable'); }
        const descriptor = Object.getOwnPropertyDescriptor(navigator, 'clipboard');
        Object.defineProperty(navigator, 'clipboard', { configurable: true,
            value: { writeText: () => Promise.reject(new Error('Permission denied')) } });
        try {
            dialog.token.setData('TEST-COPY');
            await dialog.copyToken();
            if (!dialog.status.text.includes('Ctrl+C or Cmd+C') || document.activeElement !== dialog.token.root
                    || dialog.token.root.selectionStart !== 0 || dialog.token.root.selectionEnd !== 9) {
                throw new Error('Clipboard rejection did not provide selected manual-copy fallback');
            }
            Object.defineProperty(navigator, 'clipboard', { configurable: true, value: undefined });
            await dialog.copyToken();
            if (!dialog.status.text.includes('Ctrl+C or Cmd+C')) { throw new Error('Missing clipboard API was not handled'); }
        } finally {
            if (descriptor) { Object.defineProperty(navigator, 'clipboard', descriptor); }
            else { delete navigator.clipboard; }
            dialog.token.setData('');
        }
    })()`, true);
    await evaluate(`document.querySelector('.tv-registration-token-window [data-tv-command="token-close"]').click()`);
    await evaluate(`document.querySelector('[data-tv-command="account-logout"]').click()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 5000;
        const check = () => {
            const status = document.querySelector('.tv-login-window')?.closest('.tv-dialog-overlay')
                ?._tvView?.status?.root?.textContent || '';
            const tokenMenu = Array.from(document.querySelectorAll('[data-tv-command="account-registration-token"]'))
                .some((node) => node._tvMenuItem?.name.replaceAll('~', '') === 'Registration Token');
            if (status.includes('Sign In uses a Passkey') && !tokenMenu) { resolve(true); return; }
            if (Date.now() > deadline) {
                fetch('/api/auth/session').then(r=>r.json()).then(session=>reject(new Error('Passkey sign-out failed: '+status+' authenticated='+session.authenticated)));
                return;
            }
            setTimeout(check, 30);
        };
        check();
    })`, true);
    const tokenMenuAfterSignOut = await evaluate(`Array.from(document.querySelectorAll('[data-tv-command="account-registration-token"]'))
        .some((node) => node._tvMenuItem?.name.replaceAll('~', '') === 'Registration Token')`);
    if (tokenMenuAfterSignOut) { throw new Error('Admin registration-token menu remained after sign-out'); }
    if(await evaluate(`document.querySelector('.tv-menu-right [data-tv-command="account-login"]')?.textContent.replaceAll('~','')`)!=='Login')throw new Error('Guest Login menu was not restored');
    await evaluate(`(()=>{const dialog=document.querySelector('.tv-login-window').closest('.tv-dialog-overlay')._tvView;
        dialog.username.setData('test@example.test');dialog.passwordInput.setData('Moonlit rivers carry 42 boats!');
        dialog.dialog.querySelector('[data-tv-command="login-password"]').click();})()`);
    await waitSecurity(`document.querySelector('.tv-login-window').closest('.tv-dialog-overlay')._tvView.status.text.includes('Signed in as Test User')`);
    await evaluate(`document.querySelector('.tv-login-window').closest('.tv-dialog-overlay')._tvView.signOut()`,true);
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
    // Create from the real administrator dialog, then enroll as the new user.
    await evaluate(`(() => {
        const login = document.querySelector('.tv-login-window').closest('.tv-dialog-overlay')._tvView;
        const users = login.owner.dialogManager.get('users');
        users.open(); users.addButton.root.click();
        const add = login.owner.dialogManager.get('add-user');
        add.name.setData('New'); add.lastName.setData('Member'); add.nickname.setData('NM');
        add.email.setData('new.member@example.test'); add.registerButton.root.click();
    })()`);
    const managed = await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            const add = document.querySelector('.tv-add-user-window').closest('.tv-dialog-overlay')._tvView;
            if (add.created && add.messageBox?.isOpen()) {
                resolve({ token: add.invitation.getData(), email: add.email.getData() }); return;
            }
            if (Date.now() > deadline) { reject(new Error('Add User failed: ' + add.status.getText())); return; }
            setTimeout(check, 30);
        }; check();
    })`, true);
    const adminAfterCreate = await evaluate(`fetch('/api/auth/session').then(r => r.json())`, true);
    if (adminAfterCreate.user.username !== session.user.username || adminAfterCreate.user.role !== 'admin') {
        throw new Error('Creating a member replaced the administrator session');
    }
    await evaluate(`(() => {
        const add = document.querySelector('.tv-add-user-window').closest('.tv-dialog-overlay')._tvView;
        add.messageBox.buttonViews[0].root.click(); add.registerButton.root.click();
    })()`);
    await send('Network.clearBrowserCookies');
    await evaluate(`accountTestLogin.refreshSession()`, true);
    await evaluate(`(() => {
        accountTestLogin.onRegister();
        const registration = accountTestLogin.owner.dialogManager.get('registration');
        registration.name.setData('Ignored'); registration.nickname.setData('Ignored');
        registration.email.setData(${JSON.stringify(managed.email)});
        registration.token.setData(${JSON.stringify(managed.token)});
        registration.registerButton.root.click();
    })()`);
    await evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 15000;
        const check = () => {
            const registration = accountTestLogin.owner.dialogManager.get('registration');
            if (registration.messageBox?.isOpen()) { resolve(); return; }
            if (Date.now() > deadline) { reject(new Error('Managed-user enrollment failed: ' + registration.status.getText())); return; }
            setTimeout(check, 50);
        }; check();
    })`, true);
    const memberSession = await evaluate(`fetch('/api/auth/session').then(r => r.json())`, true);
    if (!memberSession.authenticated || memberSession.user.username !== managed.email || memberSession.user.role !== 'member'
        || memberSession.user.first_name !== 'New' || memberSession.user.last_name !== 'Member' || memberSession.user.nickname !== 'NM') {
        throw new Error('Managed-user Passkey did not enroll the existing prepared profile');
    }
    await evaluate(`accountTestLogin.owner.dialogManager.get('registration').messageBox.buttonViews[0].root.click()`);
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
