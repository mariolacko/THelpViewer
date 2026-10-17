"""Public HELP rendering and degraded search work independently of MIDI demos."""

import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest

from test_browser_smoke import CHROME, NODE, _free_port, _wait_for_file, _wait_for_url


@pytest.mark.skipif(NODE is None or CHROME is None, reason="Node.js and Chrome are required")
def test_public_diagnostic_topics_and_skipped_source_warning_in_browser():
    with tempfile.TemporaryDirectory(prefix="thelp-public-browser-") as temporary:
        state = Path(temporary).resolve()
        helps = state / "helps"
        (helps / "References").mkdir(parents=True)
        topics = {
            "3": {"id": 3, "title": "No help available", "content": ["There is currently no help available for this item."]},
            "591": {"id": 591, "title": "Could not find file", "content": ["The compiler cannot find the supplied file."]},
            "29": {"id": 29, "title": "Match Not Found", "content": ["MS-DOS Help could not find the specified text."]},
            "719": {"id": 719, "title": "Could not find a match", "content": ["No C++ function matches the supplied arguments."]},
        }
        file = "References/diagnostics.json.gz"
        with gzip.open(helps / file, "wt", encoding="utf-8") as output:
            json.dump({"uhf_version": "2.0", "metadata": {"name": "Diagnostic reference",
                       "source": {"filename": "DIAG.HLP"}, "display": {"cols": 80, "rows": 24}},
                       "topics": topics, "index": []}, output)
        (helps / "broken.json.gz").write_bytes(b"Bad gzip")
        (helps / "catalog.json").write_text(json.dumps([
            {"file": file, "name": "Diagnostic reference", "source_file": "DIAG.HLP"},
            {"file": "broken.json.gz", "name": "Unreadable source", "source_file": "BROKEN.HLP"},
        ]), encoding="utf-8")
        midi = state / "midi.json"
        midi.write_text('{"sources": []}', encoding="utf-8")
        (state / "docs").mkdir()
        (state / "README.md").write_text("# Test reference", encoding="utf-8")
        (state / "CHANGELOG.md").write_text("# Test changelog", encoding="utf-8")
        port = _free_port()
        app_url = f"http://127.0.0.1:{port}/"
        server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "thelpviewer.server.app:app", "--host", "127.0.0.1",
             "--port", str(port), "--log-level", "warning"],
            cwd=Path.cwd(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env={**os.environ, "THELP_STATE_DIR": str(state), "THELP_HELPS_DIR": str(helps),
                 "THELP_STATISTICS_PATH": str(state / "statistics.sqlite3"),
                 "THELP_MIDI_SOURCES_PATH": str(midi), "THELP_DOCS_DIR": str(state / "docs"),
                 "THELP_README_PATH": str(state / "README.md"),
                 "THELP_CHANGELOG_PATH": str(state / "CHANGELOG.md")},
        )
        try:
            _wait_for_url(app_url + "healthz")
            with tempfile.TemporaryDirectory(prefix="thelp-public-chrome-") as profile:
                chrome = subprocess.Popen(
                    [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
                     "--no-first-run", "--no-default-browser-check", "--remote-debugging-port=0",
                     f"--user-data-dir={profile}", "about:blank"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    env={**os.environ, "CHROME_HEADLESS": "1"},
                )
                try:
                    debugging_port = int(_wait_for_file(Path(profile) / "DevToolsActivePort").splitlines()[0])
                    script = r'''
const [debuggingPort, appUrl, file] = process.argv.slice(1);
async function run() {
    const target = await (await fetch(`http://127.0.0.1:${debuggingPort}/json/new?${encodeURIComponent(appUrl)}`,
        { method: 'PUT' })).json();
    const socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
        socket.addEventListener('open', resolve, { once: true });
        socket.addEventListener('error', reject, { once: true });
    });
    let sequence = 0;
    const browserErrors = [];
    const pending = new Map();
    socket.addEventListener('message', (event) => {
        const message = JSON.parse(String(event.data));
        if (message.method === 'Runtime.exceptionThrown') {
            browserErrors.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
        }
        if (message.method === 'Runtime.consoleAPICalled' && message.params.type === 'error') {
            browserErrors.push(message.params.args.map(arg => arg.description || arg.value).join(' '));
        }
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
    const evaluate = async (expression, userGesture = false) => {
        const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true, userGesture });
        if (result.exceptionDetails) {
            throw new Error((result.exceptionDetails.exception?.description || result.exceptionDetails.text) + '\\n' + browserErrors.join('\\n'));
        }
        return result.result.value;
    };
    const wait = async (expression) => evaluate(`new Promise((resolve, reject) => {
        const deadline = Date.now() + 10000;
        const check = () => {
            if (${expression}) { resolve(true); return; }
            if (Date.now() > deadline) { reject(new Error('Timed out: ' + ${JSON.stringify(expression)})); return; }
            setTimeout(check, 30);
        }; check();
    })`);
    try {
        await send('Page.enable');
        await send('Runtime.enable');
        for (const topic of ['3', '591', '29', '719']) {
            await send('Page.navigate', { url: appUrl + '?' + new URLSearchParams({ file, topic }) });
            await wait(`document.querySelector('[data-tv-bundle-window]')?._tvWindowView?.currentTopic === ${JSON.stringify(topic)}
                && !document.getElementById('tv-public-fallback')`);
            const valid = await evaluate(`(() => {
                const view = document.querySelector('[data-tv-bundle-window]')._tvWindowView;
                const error = document.querySelector('.tv-msgbox-window');
                return view.bundle._catalogFile === ${JSON.stringify(file)}
                    && document.querySelector('meta[name="description"]').content.startsWith('Reference documentation from ')
                    && (!error || error.closest('.tv-dialog-overlay').hidden);
            })()`);
            if (!valid) { throw new Error('Diagnostic topic became a website error'); }
        }
        // Opening F1 help rebuilds the menu to add Contents. Disable the
        // periodic tick so a zero clock cannot be hidden by the next second.
        await evaluate(`(async () => {
            const TV = window.THelpViewerTV;
            const menuRoot = document.querySelector('[data-tv-menu-bar]');
            const app = document.querySelector('[data-tv-bundle-desktop]')._tvView.owner;
            const menu = menuRoot._tvMenuView, downloads = menu.downloadItem;
            const RealDate = window.Date;
            downloads.stop();
            clearInterval(app.desktopView.clockTimer);
            window.Date = class extends RealDate {
                constructor(...args) { super(...(args.length ? args : [2026,9,17,12,34,56])); }
            };
            TV.updateClocks();
            const before = menuRoot.querySelector('[data-tv-clock]');
            const zeroClocks = [];
            const observer = new MutationObserver(() => {
                if (menuRoot.querySelector('[data-tv-clock]')?.textContent === '00:00:00') {
                    zeroClocks.push('00:00:00');
                }
            });
            observer.observe(menuRoot, {childList:true,subtree:true,characterData:true});
            try {
                downloads.update({active:true,percent:25,errors:0,items:[{
                    id:'midi:test',kind:'midi',label:'Test song',state:'running',
                    percent:25,stage:'download',stage_percent:25,phase:'Downloading',
                },{
                    id:'dos:prepared',kind:'dos',label:'Prepared package',state:'waiting',
                    percent:99,stage:'install',stage_percent:null,phase:'Awaiting publication',
                }]}, menu);
                if (downloads.name !== '↓ 25%' || downloads.rows.get('dos:prepared').param !== 'Waiting'
                    || !downloads.rows.get('dos:prepared').name.startsWith('◷ ')) {
                    throw new Error('Waiting package was rendered as active processing');
                }
                const progress = downloads.showDialog(app.desktopView);
                progress.toggleDetails(true);
                if (!progress.details.items.some(row => row.label.includes('Prepared package') && row.label.endsWith('◷'))) {
                    throw new Error('Downloads details omitted the waiting icon');
                }
                progress.hideProgress();
                menu.itemElements.get(downloads).click();
                await new Promise(requestAnimationFrame);
                if (!menu.activeRoot || menu.getHelpCtx() !== TV.TV_HELP_CONTEXTS.hcDownloads) {
                    throw new Error('Downloads menu was not active before F1');
                }
                document.dispatchEvent(new KeyboardEvent('keydown', {
                    key:'F1',code:'F1',bubbles:true,cancelable:true,
                }));
                await new Promise((resolve,reject) => {
                    const deadline = RealDate.now()+5000;
                    const check = () => {
                        const help = Array.from(document.querySelectorAll('[data-tv-bundle-window]'))
                            .find(root => root._tvWindowView?.currentTopic === '2316');
                        if (help && menuRoot._tvMenuView !== menu) { resolve(); return; }
                        if (RealDate.now()>deadline) { reject(new Error('Downloads F1 did not rebuild the menu/open help')); return; }
                        setTimeout(check,20);
                    }; check();
                });
                await new Promise(requestAnimationFrame);
                const clock = menuRoot.querySelector('[data-tv-clock]');
                if (clock === before || clock.textContent !== '12:34:56' || zeroClocks.length) {
                    throw new Error('Clock reset while opening Downloads help: '+JSON.stringify({
                        text:clock.textContent,zeroClocks,
                    }));
                }
            } finally {
                observer.disconnect();
                window.Date = RealDate;
                TV.updateClocks();
                app.desktopView.clockTimer = setInterval(TV.updateClocks,1000);
            }
        })()`);
        // Restore the application's own help through the same desktop URL as
        // a shared Downloads-help link, not the generated-page fallback view.
        const helpState = {v:1,a:0,z:[0],w:[{t:'h',f:'../assets/tv-context-help.json',
            view:'topic',g:[20,20,76,28,0],topic:'2316',line:1,s:[0,0]}]};
        const helpHash = 'tv=1.' + Buffer.from(JSON.stringify(helpState)).toString('base64url');
        await send('Page.navigate', {url: appUrl + '?doc=README.md#' + helpHash});
        await wait(`document.querySelector('[data-tv-bundle-window]')?._tvWindowView?.currentTopic === '2316'`);
        const helpRows = await evaluate(`(() => {
            const root = document.querySelector('[data-tv-bundle-window]');
            const view = root._tvWindowView;
            const rows = Array.from(root.querySelectorAll('.tv-topic-line'));
            return {count:rows.length, expected:view.bundle.topics['2316'].content.length,
                whiteSpace:getComputedStyle(root.querySelector('.tv-topic-pre')).whiteSpace,
                tops:rows.slice(0,4).map(row => row.getBoundingClientRect().top),
                height:parseFloat(getComputedStyle(rows[0]).lineHeight)};
        })()`);
        if (helpRows.count !== helpRows.expected || helpRows.whiteSpace !== 'pre'
                || helpRows.tops.slice(1).some((top,index) => Math.abs(top-helpRows.tops[index]-helpRows.height)>1)) {
            throw new Error('Context HELP lost its source line breaks: ' + JSON.stringify(helpRows));
        }
        await evaluate(String.raw`(async () => {
            await document.fonts.ready;
            const app = document.querySelector('[data-tv-bundle-desktop]')._tvView.owner;
            const root = document.querySelector('[data-tv-bundle-window]');
            const originalView = root._tvWindowView;
            const bundle = originalView.bundle;
            for (const [id,topic] of Object.entries(bundle.topics)) {
                app.windowManager.showTopic(bundle,id);
                const rows = Array.from(root.querySelectorAll('.tv-topic-line'));
                const height = parseFloat(getComputedStyle(rows[0]).lineHeight);
                const tops = rows.map(row => row.getBoundingClientRect().top);
                if (root._tvWindowView !== originalView || rows.length !== topic.content.length
                        || tops.slice(1).some((top,index) => Math.abs(top-tops[index]-height)>1)) {
                    throw new Error('Context HELP row layout differs: '+id);
                }
                const viewport = root.querySelector('[data-tv-viewport]');
                if (viewport.scrollWidth > viewport.clientWidth+1
                        || root.querySelectorAll('.tv-scrollbar-y').length !== 1) {
                    throw new Error('Context HELP escapes its standard window: '+id);
                }
                const expectedLinks = Array.from(topic.content.join('\n').matchAll(/\[link:topic=(\d+)\]/g), match => match[1]);
                const renderedLinks = Array.from(root.querySelectorAll('.tv-topic-pre a[data-tv-bundle-topic]'),
                    link => link.dataset.tvBundleTopic);
                if (JSON.stringify(renderedLinks) !== JSON.stringify(expectedLinks)) {
                    throw new Error('Context HELP topic links were not rendered: '+id);
                }
                if (id !== '1000') {
                    const footer = topic.content.slice(topic.content.lastIndexOf('')+1);
                    for (const line of footer) {
                        const target = line.match(/\[link:topic=(\d+)\]/)[1];
                        app.windowManager.showTopic(bundle,id);
                        const link = Array.from(root.querySelectorAll('.tv-topic-pre a[data-tv-bundle-topic]'))
                            .findLast(link => link.dataset.tvBundleTopic === target);
                        link.click();
                        if (originalView.currentTopic !== target || root._tvWindowView !== originalView
                                || document.querySelectorAll('[data-tv-bundle-window]').length !== 1) {
                            throw new Error('Context HELP footer did not navigate in place: '+id+' -> '+target);
                        }
                    }
                }
            }
            app.windowManager.showTopic(bundle,'2060');
            root.querySelector('a[data-tv-bundle-topic="2315"]').click();
        })()`);
        await wait(`document.querySelector('[data-tv-bundle-window]')?._tvWindowView?.currentTopic === '2315'`);
        await send('Page.navigate', {url: appUrl + '?' + new URLSearchParams({file,topic:'719'})});
        await wait(`document.querySelector('[data-tv-bundle-window]')?._tvWindowView?.currentTopic === '719'`);
        await evaluate(`(async () => {
            const dialog = document.querySelector('.tv-search-window').closest('.tv-dialog-overlay')._tvView;
            dialog.open();
            await dialog.checkGlobalAvailability();
            dialog.setGlobal(true);
            dialog.input.setData('compiler');
            window.__originalFetch = window.fetch;
            window.__searchCalls = 0;
            window.fetch = async (url, options) => {
                const response = await window.__originalFetch(url, options);
                if (!String(url).startsWith('/api/search/global')) { return response; }
                const data = await response.json();
                // The update finishes before the first progress poll: results
                // must refresh even though no progress dialog was created.
                if (++window.__searchCalls === 1) { data.status.state = 'paused'; }
                return new Response(JSON.stringify(data), { status: response.status,
                    headers: { 'Content-Type': 'application/json' } });
            };
            dialog.renderResults('compiler');
        })()`);
        await wait(`window.__searchCalls >= 2
            && document.querySelector('.tv-search-window').closest('.tv-dialog-overlay')._tvView.matches.length === 1`);
        await evaluate(`window.fetch = window.__originalFetch`);
        const warning = await evaluate(`(() => {
            const dialog = document.querySelector('.tv-search-window').closest('.tv-dialog-overlay')._tvView;
            return { count: dialog.matches.length, skipped: dialog.indexWarnings,
                source: dialog.sourceView.root.textContent };
        })()`);
        if (warning.count !== 1 || warning.skipped !== 1 || !warning.source.includes('skipped')) {
            throw new Error('Healthy results or warning missing: ' + JSON.stringify(warning));
        }
        await evaluate(`(() => {
            const search = document.querySelector('.tv-search-window').closest('.tv-dialog-overlay')._tvView;
            search.showIndexProgress({ state: 'paused', phase: 'Waiting for HELP processing',
                percent: 37, processed: 1, total: 3 }, true);
            if (!search.indexProgress?.isOpen() || !search.indexProgress.summary.root.textContent.includes('Waiting for HELP processing')) {
                throw new Error('Paused index progress is not visible in the shared dialog');
            }
            search.clearIndexProgress();
        })()`);
        await evaluate(`(async () => {
            const TV = window.THelpViewerTV;
            const search = document.querySelector('.tv-search-window').closest('.tv-dialog-overlay')._tvView;
            const manager = search.owner.dialogManager;
            const account = manager.get('account');
            const session = { enabled: true, authenticated: true,
                user: { username: 'original@example.test', display_name: 'Original', email: 'original@example.test', role: 'admin',
                    first_name: 'Mario', last_name: 'Lacko', nickname: 'Majo' } };
            const originalFetch = window.fetch;
            let saved = null;
            let savedUser = null;
            let createdUser = null;
            const passkey = {id:'test-key',name:'Original Passkey'};
            let renamed = false;
            const disk = { used_bytes: 1048576, capacity_bytes: 64 * 1048576, free_bytes: 63 * 1048576 };
            const user = { id: 'test-user', username: 'reader', display_name: 'Reader', email: 'reader@example.test',
                role: 'member', active: true, disk_capacity_mb: null, disk,
                first_name: 'Ján', last_name: 'Novák', nickname: 'JN' };
            const allUsers = [user];
            window.fetch = async (url, options) => {
                if (String(url) === '/api/dos/usage') { return new Response(JSON.stringify(disk)); }
                if (String(url) === '/api/admin/users') {
                    if (options?.method === 'POST') {
                        createdUser = JSON.parse(options.body);
                        const added = { ...user, ...createdUser, id: 'new-user', role: 'member', display_name: createdUser.nickname };
                        allUsers.push(added);
                        return new Response(JSON.stringify({ user: added, invitation: { token: 'AAAAA-AAAAA-AAAAA-AAAAA-AAAAA',
                            expires_at: Math.floor(Date.now() / 1000) + 3600 } }), { status: 201 });
                    }
                    return new Response(JSON.stringify({ users: allUsers, dos_user_disk_mb: 64 }));
                }
                if (String(url) === '/api/admin/users/test-user') {
                    savedUser = JSON.parse(options.body); Object.assign(user, savedUser);
                    return new Response(JSON.stringify({ user }));
                }
                if (String(url) === '/api/admin/settings') {
                    return new Response(JSON.stringify({ dos_user_disk_mb: 64, backup_count: 2, download_cache_days: 30, runtime: { host: '0.0.0.0', port: 5448 } }));
                }
                if (String(url) === '/api/auth/session') { return new Response(JSON.stringify(session)); }
                if (String(url) === '/api/auth/security') {
                    return new Response(JSON.stringify({ passkeys: [passkey], password_set: false }));
                }
                if (String(url) === '/api/auth/passkeys/test-key' && options?.method === 'PUT') {
                    passkey.name = JSON.parse(options.body).name;
                    renamed = true;
                    return new Response(JSON.stringify({renamed:true}));
                }
                if (String(url) === '/api/auth/profile') {
                    saved = JSON.parse(options.body);
                    return new Response(JSON.stringify({ user: { ...session.user, ...saved, display_name: saved.nickname } }));
                }
                if (String(url) === '/api/auth/registration-tokens') {
                    if (options?.method === 'POST') { throw new Error('Add user generated a token without confirmation'); }
                    return new Response(JSON.stringify({ tokens: [] }));
                }
                return originalFetch(url, options);
            };
            try {
                account.open();
                await account.loadProfile();
                if (!(account instanceof TV.TVAccountDialog) || account.nameInput || account.root.textContent.includes('Display name')
                        || account.emailInput.getData() !== 'original@example.test'
                        || account.firstNameInput.getData() !== 'Mario' || account.lastNameInput.getData() !== 'Lacko'
                        || account.nicknameInput.getData() !== 'Majo' || !(account.emailInput.validator instanceof TV.TVEmailValidator)
                        || !account.identity.root.textContent.includes('Administrator')) {
                    throw new Error('Account profile controls were not populated');
                }
                const menu = TV.buildAccountMenu(session).subMenu;
                const config = menu.entries().find(item => item.subMenu);
                if (!menu.entries().some(item => item.command === 'account-profile')
                        || !config.subMenu.entries().some(item => item.command === 'account-rebuild-dos')) {
                    throw new Error('Production administrator menu is missing Account/Rebuild');
                }
                const edits = [[account.firstNameInput,'Ján'],[account.lastNameInput,'Novák'],
                    [account.nicknameInput,'Unstored nickname'],[account.emailInput,'draft@example.test']];
                for (const [input,value] of edits) {
                    input.root.focus(); input.root.value = value;
                    input.root.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:value}));
                }
                account.passkeyName.setData('macOS - Safari');
                account.renamePasskeyButton.root.click();
                await new Promise((resolve,reject) => {
                    const deadline = Date.now()+5000;
                    const check = () => {
                        if (renamed && !account.securityBusy) { resolve(); return; }
                        if (Date.now()>deadline) { reject(new Error('Passkey Rename did not finish')); return; }
                        setTimeout(check,10);
                    }; check();
                });
                if (saved || passkey.name !== 'macOS - Safari' || edits.some(([input,value]) => input.getData() !== value)) {
                    throw new Error('Passkey Rename changed/submitted profile fields');
                }
                account.firstNameInput.owner.drawView();
                if (edits.some(([input,value]) => input.getData() !== value || input.data !== value)) {
                    throw new Error('Profile edits disappeared after shared group redraw');
                }
                account.emailInput.setData('invalid');
                await account.saveProfile();
                if (saved || !account.isOpen() || document.activeElement !== account.emailInput.root) {
                    throw new Error('Invalid profile email was submitted or not focused');
                }
                account.firstNameInput.setData('Peter'); account.lastNameInput.setData('Nový'); account.nicknameInput.setData('PN');
                account.emailInput.setData('updated@example.test');
                await account.saveProfile();
                if (account.isOpen() || 'display_name' in saved || saved.email !== 'updated@example.test'
                        || saved.first_name !== 'Peter' || saved.last_name !== 'Nový' || saved.nickname !== 'PN'
                        || Object.keys(saved).length !== 4 || !document.querySelector('.tv-menu-right').textContent.includes('PN')) {
                    throw new Error('Profile did not save, close or update menu name');
                }
                account.open();
                await account.loadProfile();
                account.handleEvent(new TV.TVEvent(TV.evCommand, { command: 'account-cancel' }));
                if (account.isOpen()) { throw new Error('Account Cancel did not close'); }
                const member = TV.buildAccountMenu({ ...session, user: { ...session.user, role: 'member' } }).subMenu;
                if (member.entries().some(item => item.subMenu?.entries().some(child => child.command.startsWith('account-rebuild')))) {
                    throw new Error('Member can see rebuild commands');
                }
                const login = manager.get('login');
                login.open();
                if (!(login.username.validator instanceof TV.TVEmailValidator)) { throw new Error('Login has no email/username validator'); }
                login.username.setData('bad@example');
                await login.passkey();
                if (!login.status.root.textContent.includes('valid email')) { throw new Error('Login accepts malformed email'); }
                login.username.setData('reader');
                if (!login.username.valid()) { throw new Error('Login rejects legacy username'); }
                if (!login.root.textContent.includes('Login') || login === account) { throw new Error('Login still opens Account'); }
                login.close();
                if (!account.disk.root.textContent.includes('1.00 / 64 MiB')) { throw new Error('Account disk usage missing'); }
                const users = manager.get('users');
                users.open(); await users.refreshUsers();
                if (!(users.users instanceof TV.TVListBox) || users.nameInput || users.root.textContent.includes('Display name')
                        || users.role.getData() !== 0 || users.active.getData() !== 1
                        || users.capacity.getData() !== '') { throw new Error('Users controls not populated'); }
                if (users.firstNameInput.getData() !== 'Ján' || users.lastNameInput.getData() !== 'Novák'
                        || users.nicknameInput.getData() !== 'JN' || !(users.emailInput.validator instanceof TV.TVEmailValidator)) {
                    throw new Error('User profile fields or email validator not populated');
                }
                users.emailInput.root.value = 'reader @example.test';
                users.emailInput.root.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText' }));
                if (users.emailInput.getData() !== 'reader@example.test') { throw new Error('Email allows typed whitespace'); }
                users.emailInput.setData('reader@example');
                await users.saveUser();
                if (savedUser || document.activeElement !== users.emailInput.root) { throw new Error('Incomplete user email was submitted'); }
                users.emailInput.setData('');
                if (!users.emailInput.valid()) { throw new Error('Legacy account cannot retain blank email'); }
                users.emailInput.setData('reader@example.test');
                if (users.bounds.width !== 83 || users.users.bounds.height !== 26
                        || !(users.capacity.validator instanceof TV.TVFilterValidator)) {
                    throw new Error('Users geometry or capacity validator is incorrect');
                }
                const matrix = users.children[0].children.filter(view => view instanceof TV.TVButton);
                if (matrix.length !== 4 || new Set(matrix.map(view => String(view.bounds.x1) + ':' + view.bounds.y1)).size !== 4
                        || matrix.some(view => ![37, 59].includes(view.bounds.x1) || ![24, 26].includes(view.bounds.y1))) {
                    throw new Error('Users buttons are not laid out as a 2x2 matrix');
                }
                if (users.addButton.bounds.y1 !== 24 || users.saveButton.bounds.y1 !== 24
                        || users.addButton.bounds.y1 - users.disk.bounds.y2 !== 1) {
                    throw new Error('Add User/Save row has no blank row below the profile details');
                }
                users.capacity.setData('64');
                users.capacity.root.value = '64a';
                users.capacity.root.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText' }));
                if (users.capacity.getData() !== '64') { throw new Error('Capacity accepts typed letters'); }
                users.capacity.root.value = 'abc';
                users.capacity.root.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertFromPaste' }));
                if (users.capacity.getData() !== '64') { throw new Error('Capacity accepts pasted text'); }
                users.capacity.setData('257');
                await users.saveUser();
                if (savedUser || !users.status.root.textContent.includes('1–256 MiB')) {
                    throw new Error('Out-of-range capacity was submitted');
                }
                users.capacity.setData('');
                if (!users.capacity.valid()) { throw new Error('Inherited capacity is rejected'); }
                users.capacity.setData('96'); users.role.setData(1);
                await users.saveUser();
                if (savedUser.disk_capacity_mb !== 96 || savedUser.role !== 'admin'
                        || savedUser.first_name !== 'Ján' || savedUser.last_name !== 'Novák' || savedUser.nickname !== 'JN'
                        || 'display_name' in savedUser || !savedUser.active || Object.keys(savedUser).length !== 7) {
                    throw new Error('User edit did not save through TV controls');
                }
                users.selectUser({ ...user, protected_admin: true });
                if (!(users.role.state & TV.sfDisabled) || !(users.active.state & TV.sfDisabled)) {
                    throw new Error('Founding administrator controls are not protected');
                }
                if ([...users.role.choiceElements, ...users.active.choiceElements].some(input => !input.disabled)) {
                    throw new Error('Founding administrator native controls remain editable');
                }
                users.selectUser({ ...user, protected_admin: false });
                if ((users.role.state & TV.sfDisabled) || (users.active.state & TV.sfDisabled)) {
                    throw new Error('Ordinary account controls stayed disabled after founder selection');
                }
                if ([...users.role.choiceElements, ...users.active.choiceElements].some(input => input.disabled)) {
                    throw new Error('Ordinary account native controls stayed disabled');
                }
                users.close();
                const settings = manager.get('server-configuration');
                settings.open(); await settings.loadSettings();
                if (settings.capacity.getData() !== '64' || settings.runtime.items.length !== 2) {
                    throw new Error('Server configuration controls did not load');
                }
                const actions = settings.children[0].children.filter(child => child instanceof TV.TVButton
                    && ['account-help-packages', 'account-dos-packages', 'account-midi-sources'].includes(child.command));
                if (actions.length !== 3 || actions.some(button => button.bounds.y1 !== 15)) {
                    throw new Error('Server configuration launchers do not fit their action row');
                }
                for (const button of actions) {
                    const shadow = button.root.querySelector('.tv-dialog-button-shadow');
                    if (shadow.textContent !== ' ' + '▀'.repeat(button.bounds.width - 1)) {
                        throw new Error('Wide button shadow is still truncated');
                    }
                }
                if (!(settings.owner.owner instanceof TV.TVProgram)) { throw new Error('Desktop is not owned by the application'); }
                settings.children[0].children.find(button => button.command === 'account-users').root.click();
                if (!users.isOpen() || manager.activeTarget !== 'users') { throw new Error('Server Configuration Users button does nothing'); }
                await users.refreshUsers();
                const add = users.children[0].children.find(button => button.command === 'account-add-user');
                add.root.click();
                const addUser = manager.get('add-user');
                if (!addUser.isOpen() || manager.activeTarget !== 'add-user' || !(addUser instanceof TV.TVRegistrationDialog)
                        || addUser.token || !(addUser.email.validator instanceof TV.TVEmailValidator)) {
                    throw new Error('Add user does not use the shared profile form with an email validator');
                }
                addUser.name.setData('New'); addUser.lastName.setData('Reader'); addUser.nickname.setData('NR');
                addUser.email.setData('bad@example');
                await addUser.submit();
                if (createdUser || document.activeElement !== addUser.email.root) { throw new Error('Add user submitted invalid email'); }
                addUser.email.setData('new@example.test');
                const menuBeforeCreate = document.querySelector('.tv-menu-right').textContent;
                const creating = addUser.submit();
                await new Promise((resolve, reject) => {
                    const deadline = Date.now() + 5000;
                    const check = () => {
                        if (addUser.messageBox?.isOpen()) { resolve(); return; }
                        if (Date.now() > deadline) { reject(new Error('User creation did not show confirmation')); return; }
                        setTimeout(check, 10);
                    }; check();
                });
                addUser.messageBox.buttonViews[0].root.click();
                await creating;
                await users.refreshUsers('new-user');
                if (createdUser.first_name !== 'New' || createdUser.last_name !== 'Reader' || createdUser.nickname !== 'NR'
                        || createdUser.email !== 'new@example.test' || Object.keys(createdUser).length !== 4
                        || !addUser.created || addUser.invitation.getData() !== 'AAAAA-AAAAA-AAAAA-AAAAA-AAAAA'
                        || users.selectedUser.id !== 'new-user' || document.querySelector('.tv-menu-right').textContent !== menuBeforeCreate) {
                    throw new Error('User was not created/refreshed with a copyable invitation or admin session changed');
                }
                addUser.registerButton.root.click();
                if (addUser.isOpen() || addUser.invitation.getData()) { throw new Error('Done did not close/clear the invitation'); }
                users.close(); settings.close();
                const registration = manager.get('registration');
                registration.open();
                registration.name.setData('New User'); registration.email.setData('bad@example');
                registration.token.setData('AAAAA-AAAAA-AAAAA-AAAAA-AAAAA');
                await registration.submit();
                if (!(registration.email.validator instanceof TV.TVEmailValidator)
                        || !registration.status.root.textContent.includes('valid email')) {
                    throw new Error('Registration email is not validated before requesting a Passkey');
                }
                registration.close();
                for (const view of [account, users, settings, addUser, registration]) {
                    view.open();
                    const group = view.children.find(child => child instanceof TV.TVGroup);
                    for (const child of group.children) {
                        if (child.bounds.x2 > group.bounds.width || child.bounds.y2 > group.bounds.height) {
                            throw new Error('Control escapes dialog client area');
                        }
                    }
                    view.close();
                }
                const menuView = document.querySelector('[data-tv-menu-bar]')._tvMenuView;
                menuView.openMenu(menuView.menuRoots[menuView.menuRoots.length - 1]);
                await new Promise(requestAnimationFrame);
                const rect = menuView.activePopup.getBoundingClientRect();
                if (rect.left < -1 || rect.right > window.innerWidth + 1) { throw new Error('User menu escapes viewport: ' + JSON.stringify({ left: rect.left, right: rect.right, width: window.innerWidth, style: menuView.activePopup.style.cssText })); }
                menuView.closeMenus();
                if (manager.get('terminal') || TV.TVServerTerminalDialog) { throw new Error('Removed terminal still exists'); }
            } finally { window.fetch = originalFetch; account.close(); }
        })()`);
        await evaluate(`(async () => {
            const app = document.querySelector('[data-tv-bundle-desktop]')._tvView.owner;
            const player = app.dialogManager.get('midi');
            const originalFetch = window.fetch;
            const id = '1111111111111111';
            const data = 'data:audio/midi;base64,' + btoa(String.fromCharCode(...[
                77,84,104,100,0,0,0,6,0,0,0,1,0,96,
                77,84,114,107,0,0,0,23,
                0,255,81,3,7,161,32,0,192,0,0,144,60,100,
                176,0,128,60,0,0,255,47,0,
            ]));
            const pending = {id,item_id:id,source_id:'wanted',title:'Requested song',game:'Game',
                sequencer:'',available:false,file:'',cover:''};
            const other = {...pending,id:id+':other.mid',source_id:'other',available:true,file:data+'#other'};
            let polls = 0, priorities = 0, complete = false, failure = '';
            let holdCatalog = false, releaseCatalog = null, priorityRelease = null;
            window.fetch = async (url, options) => {
                if (String(url) === '/api/midi/catalog') {
                    if (holdCatalog) {
                        return new Promise(resolve => { releaseCatalog = () => resolve(new Response(JSON.stringify({
                            state:'ready',downloaded:0,total:0,tracks:[],errors:[],
                        }))); }); // Intentionally ignores AbortSignal: stale results must still be rejected.
                    }
                    polls++;
                    const ready = complete || polls >= 3 && !failure;
                    return new Response(JSON.stringify({state:'partial',downloaded:ready?2:1,total:2,errors:['unrelated album'],
                        tracks:[other,{...pending,...(ready?{id:id+':theme.mid',available:true,file:data}:{}),download_error:failure}]}));
                }
                if (String(url).startsWith('/api/midi/priority/')) {
                    priorities++;
                    if (priorityRelease) { await priorityRelease; }
                    return new Response('{}');
                }
                return originalFetch(url,options);
            };
            const until = (condition) => new Promise((resolve,reject) => {
                const deadline = Date.now()+15000;
                const check = () => {
                    if (condition()) { resolve(); return; }
                    if (Date.now()>deadline) { reject(new Error('MIDI condition timed out: '+player.displayView.statusView.root.textContent)); return; }
                    setTimeout(check,30);
                }; check();
            });
            try {
                player.open();
                await until(() => !player.catalogPending);
                player.selectTrack(1);
                await player.playSelected();
                if (!player.isLoading || !player.pendingPlay || !player.synth.context) {
                    throw new Error('Queued Play did not start its own wait/audio context');
                }
                await until(() => player.isPlaying);
                await new Promise(resolve => setTimeout(resolve,600));
                if (polls<3 || priorities!==1 || player.activeTrackFile!==data || player.pendingPlay
                    || player.synth.synth.getPlayerCurrentTick()<=0 || player.synth.context.state!=='running') {
                    throw new Error('Partial catalog prevented requested MIDI playback or selected another source');
                }
                player.pausePlayback();
                const tick = player.synth.synth.getPlayerCurrentTick();
                await player.playSelected();
                if (!player.isPlaying || player.synth.synth.getPlayerCurrentTick()<tick) {
                    throw new Error('Pause/resume restarted playback');
                }
                player.stopPlayback();
                // A delayed priority acknowledgement must not undo Stop.
                let acknowledge;
                priorityRelease = new Promise(resolve => { acknowledge=resolve; });
                player.allTracks=[pending]; player.applyFilter();
                const request = player.playSelected();
                player.stopPlayback(); acknowledge(); await request; priorityRelease=null;
                complete=true;
                await player.refreshCatalog();
                if (player.pendingPlay || player.isPlaying || player.isLoading) { throw new Error('Stop allowed late auto-play'); }
                // An album error must stop waiting even while the global state is partial.
                complete=false; failure='Invalid source MIDI';
                player.allTracks=[pending]; player.applyFilter();
                await player.playSelected(); await player.refreshCatalog();
                if (player.pendingPlay || player.isLoading || !player.displayView.statusView.root.textContent.includes(failure)) {
                    throw new Error('Per-track failure was hidden by global catalog state');
                }
                // An old catalog response cannot clear a newly reopened player's catalog.
                holdCatalog=true;
                const stale=player.refreshCatalog();
                await until(() => releaseCatalog);
                player.close(); holdCatalog=false; failure=''; complete=true;
                player.open(); await until(() => !player.catalogPending);
                releaseCatalog(); await stale;
                if (player.allTracks.length!==2) { throw new Error('Closed player applied a stale catalog response'); }
            } finally { player.close(); window.fetch=originalFetch; }
        })()`, true);
        await send('Page.navigate', { url: appUrl + '?topic=719&file=References/diagnostics.json.gz&line=1#bookmark' });
        await wait(`document.querySelector('[data-tv-bundle-window]')?._tvWindowView?.currentTopic === '719'
            && window.location.search === '?file=References%2Fdiagnostics.json.gz&topic=719&line=1'
            && window.location.hash === '#bookmark'`);
        const response = await fetch(appUrl + 'missing-page', { headers: { Accept: 'text/html' } });
        if (response.status !== 404 || response.headers.get('x-robots-tag') !== 'noindex') {
            throw new Error('Missing-page response is still indexable');
        }
        await send('Page.navigate', { url: appUrl + 'missing-page' });
        await wait(`document.querySelector('.tv-msgbox-window')?.textContent.includes('/missing-page')
            && !document.querySelector('.tv-msgbox-window').closest('.tv-dialog-overlay').hidden`);
    } finally { socket.close(); }
}
const timeout = setTimeout(() => { process.stderr.write('Public browser test timed out'); process.exit(1); }, 45000);
run().then(() => { clearTimeout(timeout); process.exit(0); })
    .catch((error) => { clearTimeout(timeout); process.stderr.write(String(error.stack || error)); process.exit(1); });
'''
                    result = subprocess.run([NODE, "-e", script, str(debugging_port), app_url, file],
                                            capture_output=True, text=True, timeout=50)
                    assert result.returncode == 0, result.stderr
                finally:
                    chrome.terminate()
                    chrome.wait(timeout=5)
        finally:
            server.terminate()
            server.wait(timeout=5)
