// Turbo Vision dialogs for generated help pages.
(function () {
"use strict";
const TV = window.THelpViewerTV = window.THelpViewerTV || {};
const {
    escapeHtml,
    renderHotkeyMarkup,
    displayCp437Char,
    cloneColorPalette,
    setColorPaletteAttribute,
    buildDefaultColorPalette,
    applyColorPalette,
    dosColor,
    DOS_COLORS,
    COLOR_GROUPS,
    TVWindow,
    TVEvent,
    wfClose,
    wnNoNumber,
    TVDialog,
    TVView,
    TVRect,
    TVStaticText,
    TVImage,
    TVBarGauge,
    TVPercentGauge,
    TVLabel,
    TVPXPictureValidator,
    TVInputLine,
    TVGroup,
    TVListViewer,
    TVListBox,
    TVGridView,
    TVScrollBar,
    TVOutline,
    TVInfoBox,
    TVTerminal,
    TVCheckBoxes,
    TVRadioButtons,
    TVMultiCheckBoxes,
    TVButton,
    bfNormal,
    bfDefault,
    TVMessageBox,
    normalizeSearchText,
    fillBorders,
    MONTH_NAMES,
    DAYS_IN_MONTH,
    isLeapYear,
    dayOfWeek,
    measureCells,
    TV_HELP_CONTEXTS,
    evNothing,
    evMouseDown,
    evKeyDown,
    evCommand,
    evBroadcast,
    sfVisible,
    sfActive,
    sfDisabled,
    sfModal,
} = TV;

const {
    hcSearch,
    hcAbout,
    hcFileOpen,
    hcChangeDirectory,
    hcFind,
    hcColors,
    hcWidgetGallery,
    hcMidiPlayer,
    hcCalendar,
    hcAsciiTable,
    hcCalculator,
    hcStatistics,
    hcSystemInformation,
    hcAccount,
    hcRegistration,
    hcRegistrationTokens,
    hcServerConfiguration,
    hcServerTerminal,
    hcGridDemo,
} = TV_HELP_CONTEXTS;

class TVFileScrollButton extends TVButton {
    _drawParts() {
        return { ...super._drawParts(), dialog: false, className: "tv-file-open-scroll-button", tabIndex: -1 };
    }
}

class TVAsciiCellButton extends TVButton {
    _drawParts() {
        return {
            ...super._drawParts(), dialog: false, className: "tv-ascii-cell",
            labelMarkup: escapeHtml(displayCp437Char(this.value)), ariaLabel: `ASCII ${this.value}`,
        };
    }
}

class TVCalculatorButton extends TVButton {
    _drawParts() {
        return {
            ...super._drawParts(), baseClass: "tv-dialog-button tv-calc-button",
            ariaLabel: `Calculator key ${this.commandData.description || this.title}`,
            tooltip: this.commandData.description || "",
        };
    }
}

class TVCalendarButton extends TVButton {
    _drawParts() {
        const labels = {
            "calendar-prev": "Previous month", "calendar-next": "Next month", "calendar-today": "Today",
        };
        return {
            ...super._drawParts(), dialog: false, className: "tv-calendar-arrow",
            labelMarkup: renderHotkeyMarkup({
                "calendar-prev": displayCp437Char(30),
                "calendar-next": displayCp437Char(31),
            }[this.command] || this.title),
            ariaLabel: labels[this.command] || "",
        };
    }
}

class TVColorCellButton extends TVButton {
    _drawParts() {
        const data = this.commandData;
        const full = escapeHtml(displayCp437Char(219));
        return {
            ...super._drawParts(), dialog: false,
            className: `tv-color-cell${data.selected ? " is-selected" : ""}`,
            style: data.color ? `--tv-color-cell:${data.color}` : "",
            labelMarkup: data.selected
                ? `${full}<span class="tv-color-cell-marker">${escapeHtml(displayCp437Char(8))}</span>${full}`
                : full.repeat(3),
            ariaLabel: `Color ${this.value}`, ariaPressed: Boolean(data.selected),
            tabIndex: data.selected ? 0 : -1,
        };
    }
}

class TVMidiTrackButton extends TVButton {
    _drawParts() {
        const data = this.commandData;
        return {
            ...super._drawParts(), dialog: false,
            className: `tv-midi-track${data.selected ? " is-selected" : ""}`,
            ariaLabel: `${data.title || "MIDI track"}, ${data.credit || ""}, ${data.available ? "downloaded" : "not downloaded"}`,
            labelMarkup: [
                `<span class="tv-midi-track-index">${escapeHtml(String(data.index + 1).padStart(2, "0"))}</span>`,
                `<span class="tv-midi-track-title">${escapeHtml(data.title || "")}</span>`,
                `<span class="tv-midi-track-credit">${escapeHtml(data.credit || "")}</span>`,
                `<span class="tv-midi-track-availability" aria-hidden="true">${data.available ? " " : "☁"}</span>`,
            ].join(""),
        };
    }
}

class TVMidiControlButton extends TVButton {
    _drawParts() {
        const tooltips = {
            "midi-previous": "Previous track", "midi-pause": "Pause", "midi-next": "Next track",
        };
        return {
            ...super._drawParts(),
            ariaExpanded: this.command === "midi-more" ? Boolean(this.commandData.expanded) : null,
            tooltip: tooltips[this.command] || "",
        };
    }
}

class TVSearchResultButton extends TVButton {
    _drawParts() {
        const data = this.commandData;
        return {
            ...super._drawParts(), dialog: false,
            className: `tv-search-result${data.selected ? " is-selected" : ""}`,
            labelMarkup: [
                ["tv-search-result-title", data.title],
                ["tv-search-result-meta", data.meta],
            ].map(([className, value]) => `<span class="${className}">${escapeHtml(value || "")}</span>`).join(""),
        };
    }
}

class TVAboutDialog extends TVDialog {
    static viewName = "about";

    constructor() {
        const body = document.body;
        const siteName = body.dataset.tvSiteName || "THelpViewer";
        const generatorVersion = body.dataset.tvGeneratorVersion || "unknown";
        const generatorAuthors = body.dataset.tvAuthors || "Mario Lacko + Copilot + Codex";
        const okButton = new TVButton(new TVRect(9, 9, 19, 11), '~O~K', "about-ok", bfDefault);
        const aboutMain = new TVGroup(new TVRect(0, 0, 28, 11)).insertAll([
                new TVStaticText(new TVRect(0, 1, 28, 2), `\x03${siteName}`),
                new TVStaticText(new TVRect(0, 3, 28, 4), `\x03Version ${generatorVersion}`),
                new TVStaticText(new TVRect(0, 5, 28, 6), "\x03Copyright (c) 2026"),
                new TVStaticText(new TVRect(0, 7, 28, 8), `\x03${generatorAuthors}`),
                okButton,
            ]);

        super(new TVRect(0, 0, 32, 13), "About");
        this.setHelpCtx(hcAbout);
        this.insert(aboutMain);
        this.okButton = okButton;
        this.bindCommonClose(() => this.close());
        this.bindDrag();
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand && event.command === "about-ok") {
            this.close();
            this.clearEvent(event);
        }
    }
}

class TVLoginDialog extends TVDialog {
    static viewName = "login";

    constructor() {
        const username = new TVInputLine(new TVRect(2, 2, 45, 3), 254);
        const signIn = new TVButton(new TVRect(2, 5, 15, 7), "~S~ign In", "login-sign-in", bfDefault);
        const register = new TVButton(new TVRect(16, 5, 29, 7), "~R~egister", "login-register", bfNormal);
        const signOut = new TVButton(new TVRect(30, 5, 43, 7), "Sign ~O~ut", "login-sign-out", bfNormal);
        const close = new TVButton(new TVRect(44, 5, 57, 7), "~C~lose", "login-close", bfNormal);
        const status = new TVStaticText(new TVRect(2, 8, 56, 10), "Checking account status...");
        super(new TVRect(0, 0, 60, 13), "Account");
        this.setHelpCtx(hcAccount);
        this.insert(new TVGroup(new TVRect(0, 0, 58, 11)).insertAll([
            new TVLabel(new TVRect(2, 1, 25, 2), "~E~mail or username", username), username,
            signIn, register, signOut, close, status,
        ]));
        this.username = username;
        this.status = status;
        this.actions = [signIn, register, signOut];
        this.onRegister = null;
        this.onSessionChange = null;
        this.sessionRequestVersion = 0;
        this.bindCommonClose(() => this.close());
        this.bindDrag();
    }

    static decodeBase64Url(value) {
        const text = String(value).replace(/-/g, "+").replace(/_/g, "/");
        const bytes = atob(text.padEnd(Math.ceil(text.length / 4) * 4, "="));
        return Uint8Array.from(bytes, (char) => char.charCodeAt(0));
    }

    static encodeBase64Url(value) {
        const bytes = new Uint8Array(value || []);
        let text = "";
        bytes.forEach((byte) => { text += String.fromCharCode(byte); });
        return btoa(text).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
    }

    static async request(path, method = "GET", body) {
        const response = await fetch(path, {
            method,
            credentials: "same-origin",
            cache: "no-store",
            ...(body === undefined ? {} : {
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            }),
        });
        const payload = await response.text();
        let data;
        try {
            data = payload ? JSON.parse(payload) : {};
        } catch {
            throw new Error(`HTTP ${response.status}: invalid server response`);
        }
        if (!response.ok) { throw new Error(data.detail || `HTTP ${response.status}`); }
        return data;
    }

    static async post(path, body = {}) {
        return TVLoginDialog.request(path, "POST", body);
    }

    static credentialAnswer(credential, registering) {
        const encode = TVLoginDialog.encodeBase64Url;
        const response = {
            clientDataJSON: encode(credential.response.clientDataJSON),
            ...(registering
                ? {
                    attestationObject: encode(credential.response.attestationObject),
                    transports: credential.response.getTransports?.() || [],
                }
                : {
                    authenticatorData: encode(credential.response.authenticatorData),
                    signature: encode(credential.response.signature),
                    userHandle: credential.response.userHandle
                        ? encode(credential.response.userHandle) : null,
                }),
        };
        return {
            id: credential.id,
            rawId: encode(credential.rawId),
            type: credential.type,
            response,
            clientExtensionResults: credential.getClientExtensionResults?.() || {},
            authenticatorAttachment: credential.authenticatorAttachment || undefined,
        };
    }

    open() {
        super.open();
        this.username.focus();
        void this.refreshSession();
    }

    async refreshSession() {
        const version = ++this.sessionRequestVersion;
        try {
            const response = await fetch("/api/auth/session", { cache: "no-store", credentials: "same-origin" });
            if (!response.ok) { throw new Error(`HTTP ${response.status}`); }
            const session = await response.json();
            if (version === this.sessionRequestVersion) { this.updateSession(session); }
        } catch {
            if (version === this.sessionRequestVersion) { this.status.setText("Account server is unavailable."); }
        }
    }

    updateSession(data) {
        this.sessionRequestVersion += 1;
        this.onSessionChange?.(data);
        this.status.setText(!data.enabled
            ? "Passkey login is not configured for this host."
            : data.authenticated
                ? `Signed in as ${data.user.display_name} (${data.user.username}).`
                : "Sign in, or register with an invitation token.");
    }

    async passkey() {
        const username = this.username.getData().trim();
        if (!username) {
            this.status.setText("Enter email or username.");
            return;
        }
        if (!window.isSecureContext || !navigator.credentials?.create || !navigator.credentials?.get) {
            this.status.setText("Passkeys require HTTPS or localhost and a compatible browser.");
            return;
        }
        this.actions.forEach((button) => button.setState(sfDisabled, true));
        try {
            const prefix = "/api/auth/passkey/login";
            const request = await TVLoginDialog.post(`${prefix}/options`, { username });
            const options = request.options;
            const decode = TVLoginDialog.decodeBase64Url;
            options.challenge = decode(options.challenge);
            options.allowCredentials = (options.allowCredentials || []).map(
                (entry) => ({ ...entry, id: decode(entry.id) }),
            );
            const credential = await navigator.credentials.get({ publicKey: options });
            if (!credential) { throw new Error("Passkey operation was cancelled."); }
            await TVLoginDialog.post(`${prefix}/verify`, {
                ceremony_id: request.ceremony_id,
                credential: TVLoginDialog.credentialAnswer(credential, false),
            });
            await this.refreshSession();
        } catch (error) {
            this.status.setText(error?.message || "Passkey operation failed.");
        } finally {
            this.actions.forEach((button) => button.setState(sfDisabled, false));
        }
    }

    async signOut() {
        this.sessionRequestVersion += 1;
        this.status.setText("Signing out...");
        try {
            await TVLoginDialog.post("/api/auth/logout");
            await this.refreshSession();
        } catch (error) {
            this.status.setText(error?.message || "Sign out failed.");
        }
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what !== evCommand) { return; }
        if (event.command === "login-sign-in") { void this.passkey(); }
        else if (event.command === "login-register") { this.onRegister?.(); }
        else if (event.command === "login-sign-out") { void this.signOut(); }
        else if (event.command === "login-close") { this.close(); }
        else { return; }
        this.clearEvent(event);
    }
}

class TVRegistrationDialog extends TVDialog {
    static viewName = "registration";

    constructor() {
        const name = new TVInputLine(new TVRect(2, 2, 56, 3), 100);
        const email = new TVInputLine(new TVRect(2, 5, 56, 6), 254);
        const token = new TVInputLine(new TVRect(2, 8, 56, 9), 128)
            .setValidator(new TVPXPictureValidator("!!!!!-!!!!!-!!!!!-!!!!!-!!!!!", true));
        const register = new TVButton(new TVRect(13, 11, 28, 13), "~R~egister", "register-confirm", bfDefault);
        const cancel = new TVButton(new TVRect(30, 11, 45, 13), "~C~ancel", "register-cancel", bfNormal);
        const status = new TVStaticText(new TVRect(2, 14, 56, 16), "A registration token is valid for one hour.");
        super(new TVRect(0, 0, 60, 19), "Register Passkey");
        this.setHelpCtx(hcRegistration);
        this.insert(new TVGroup(new TVRect(0, 0, 58, 17)).insertAll([
            new TVLabel(new TVRect(2, 1, 30, 2), "~N~ame", name), name,
            new TVLabel(new TVRect(2, 4, 30, 5), "~E~mail", email), email,
            new TVLabel(new TVRect(2, 7, 30, 8), "Registration ~t~oken", token), token,
            register, cancel, status,
        ]));
        this.name = name;
        this.email = email;
        this.token = token;
        this.status = status;
        this.registerButton = register;
        this.onSessionChange = null;
        this.onConfirmed = null;
        this.messageBox = null;
        this.bindCommonClose(() => this.close());
        this.bindDrag();
    }

    open() {
        super.open();
        this.name.focus();
    }

    close() {
        this.token.setData("");
        super.close();
    }

    async registerPasskey() {
        const name = this.name.getData().trim();
        const email = this.email.getData().trim();
        const token = this.token.getData().trim();
        if (!name || !email || !token) {
            this.status.setText("Enter name, email and registration token.");
            return;
        }
        if (!this.token.valid()) {
            this.status.setText("Use a token in XXXXX-XXXXX-XXXXX-XXXXX-XXXXX format.");
            return;
        }
        if (!window.isSecureContext || !navigator.credentials?.create) {
            this.status.setText("Passkeys require HTTPS or localhost and a compatible browser.");
            return;
        }
        this.registerButton.setState(sfDisabled, true);
        let stage = "Registration request";
        try {
            const prefix = "/api/auth/passkey/register";
            const request = await TVLoginDialog.post(`${prefix}/options`, { name, email, token });
            const options = request.options;
            const decode = TVLoginDialog.decodeBase64Url;
            options.challenge = decode(options.challenge);
            options.user.id = decode(options.user.id);
            options.excludeCredentials = (options.excludeCredentials || []).map(
                (entry) => ({ ...entry, id: decode(entry.id) }),
            );
            if (options.rp?.id !== window.location.hostname) {
                throw new Error(`Passkey domain ${options.rp?.id || "?"} does not match this site`);
            }
            stage = "Passkey creation";
            const credential = await navigator.credentials.create({ publicKey: options });
            if (!credential) { throw new Error("Passkey operation was cancelled."); }
            stage = "Passkey verification";
            const verified = await TVLoginDialog.post(`${prefix}/verify`, {
                ceremony_id: request.ceremony_id,
                credential: TVLoginDialog.credentialAnswer(credential, true),
            });
            if (!verified.authenticated) { throw new Error("Registration was not confirmed by the server."); }
            this.token.setData("");
            stage = "Session check";
            const response = await fetch("/api/auth/session", { cache: "no-store", credentials: "same-origin" });
            if (!response.ok) { throw new Error(`Session check returned HTTP ${response.status}`); }
            const session = await response.json();
            if (!session.authenticated || !session.user) {
                throw new Error("Passkey was created, but the signed-in session is missing.");
            }
            this.onSessionChange?.(session);
            if (!this.messageBox) {
                this.messageBox = new TVMessageBox();
                this.owner?.insert(this.messageBox);
            }
            await this.messageBox.show({
                type: TVMessageBox.MF_INFORMATION,
                lines: [`Registered and signed in as ${session.user.display_name}.`],
            });
            this.close();
            this.onConfirmed?.();
        } catch (error) {
            const type = error?.name && error.name !== "Error" ? `${error.name}: ` : "";
            const reason = `${type}${error?.message || "Registration failed."}`;
            this.status.setText(`${stage} failed:\n${reason.length > 54 ? `${reason.slice(0, 53)}…` : reason}`);
        } finally {
            this.registerButton.setState(sfDisabled, false);
        }
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what !== evCommand) { return; }
        if (event.command === "register-confirm") { void this.registerPasskey(); }
        else if (event.command === "register-cancel") { this.close(); }
        else { return; }
        this.clearEvent(event);
    }
}

class TVRegistrationTokenDialog extends TVDialog {
    static viewName = "registration-token";

    constructor() {
        const token = new TVInputLine(new TVRect(2, 2, 71, 3), 128);
        const generate = new TVButton(new TVRect(9, 4, 25, 6), "~G~enerate", "token-generate", bfDefault);
        const remove = new TVButton(new TVRect(29, 4, 45, 6), "~D~elete", "token-delete", bfNormal)
            .setState(sfDisabled, true);
        const close = new TVButton(new TVRect(49, 4, 65, 6), "~C~lose", "token-close", bfNormal);
        const tokens = new TVListBox(new TVRect(2, 8, 71, 16));
        const status = new TVStaticText(new TVRect(2, 17, 71, 18), "Loading valid tokens...");
        super(new TVRect(0, 0, 76, 21), "Registration Token");
        this.setHelpCtx(hcRegistrationTokens);
        this.insert(new TVGroup(new TVRect(0, 0, 74, 19)).insertAll([
            new TVLabel(new TVRect(2, 1, 30, 2), "Token", token), token,
            generate, remove, close,
            new TVStaticText(new TVRect(2, 7, 71, 8), "Valid registration tokens"),
            tokens, status,
        ]));
        this.token = token;
        this.tokens = tokens;
        this.status = status;
        this.generateButton = generate;
        this.deleteButton = remove;
        this.confirmBox = null;
        this.refreshVersion = 0;
        this.tokens.bind({
            onSelect: (item) => this.selectToken(item),
            onActivate: (item) => {
                this.selectToken(item);
                if (item.token) { this.token.focus(); this.token.selectAll(); }
            },
        });
        this.bindCommonClose(() => this.close());
        this.bindDrag();
    }

    open() {
        this.token.setData("");
        super.open();
        void this.refreshTokens();
    }

    close() {
        this.refreshVersion += 1;
        this.token.setData("");
        this.tokens.newList([]);
        this.deleteButton.setState(sfDisabled, true);
        super.close();
    }

    selectToken(item) {
        this.token.setData(item?.token || "");
        this.deleteButton.setState(sfDisabled, !item);
        if (item) {
            this.status.setText(item.token
                ? `Valid until ${new Date(item.expires_at * 1000).toLocaleString()}.`
                : "Older token: value unavailable; it can still be deleted.");
        }
    }

    async refreshTokens() {
        const version = ++this.refreshVersion;
        try {
            const data = await TVLoginDialog.request("/api/auth/registration-tokens");
            if (version !== this.refreshVersion || !this.isOpen()) { return false; }
            const rows = data.tokens.map((item) => ({
                ...item,
                label: `${item.token || "[older token: value unavailable]"}  ${new Date(item.expires_at * 1000).toLocaleString()}`,
            }));
            this.tokens.newList(rows);
            this.tokens.select(-1);
            this.deleteButton.setState(sfDisabled, true);
            this.status.setText(rows.length ? `${rows.length} valid token(s). Select one to view or delete.` : "No valid tokens.");
            return true;
        } catch (error) {
            if (version === this.refreshVersion && this.isOpen()) {
                this.status.setText(error?.message || "Could not load tokens.");
            }
            return false;
        }
    }

    async generateToken() {
        this.generateButton.setState(sfDisabled, true);
        try {
            const data = await TVLoginDialog.post("/api/auth/registration-tokens");
            if (!this.isOpen()) { return; }
            const listed = await this.refreshTokens();
            if (!this.isOpen()) { return; }
            this.token.setData(data.token);
            this.token.focus();
            this.token.selectAll();
            this.status.setText(listed
                ? "Token generated. Copy it or select it later from the list."
                : "Token generated, but the list could not be refreshed.");
        } catch (error) {
            this.status.setText(error?.message || "Could not create token.");
        } finally {
            this.generateButton.setState(sfDisabled, false);
        }
    }

    async deleteToken() {
        const selected = this.tokens.selectedItem();
        if (!selected) { return; }
        if (!this.confirmBox) {
            this.confirmBox = new TVMessageBox();
            this.owner?.insert(this.confirmBox);
        }
        const answer = await this.confirmBox.show({
            type: TVMessageBox.MF_CONFIRMATION,
            lines: ["Delete the selected registration token?"],
            buttons: TVMessageBox.MF_YES_BUTTON | TVMessageBox.MF_NO_BUTTON,
        });
        if (answer !== "yes" || !this.isOpen()) { return; }
        this.deleteButton.setState(sfDisabled, true);
        try {
            await TVLoginDialog.request(`/api/auth/registration-tokens/${encodeURIComponent(selected.id)}`, "DELETE");
            if (!this.isOpen()) { return; }
            await this.refreshTokens();
            this.token.setData("");
            this.status.setText("Registration token deleted.");
        } catch (error) {
            this.status.setText(error?.message || "Could not delete token.");
            this.deleteButton.setState(sfDisabled, false);
        }
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what !== evCommand) { return; }
        if (event.command === "token-generate") { void this.generateToken(); }
        else if (event.command === "token-delete") { void this.deleteToken(); }
        else if (event.command === "token-close") { this.close(); }
        else { return; }
        this.clearEvent(event);
    }
}

class TVServerConfigurationDialog extends TVDialog {
    static viewName = "server-configuration";

    constructor() {
        super(new TVRect(0, 0, 62, 14), "Server Configuration");
        this.setHelpCtx(hcServerConfiguration);
        this.capacity = new TVInputLine(new TVRect(2, 2, 10, 3), 3);
        this.status = new TVStaticText(new TVRect(2, 10, 58, 12), "");
        this.saveButton = new TVButton(new TVRect(16, 7, 29, 9), "~S~ave", "server-settings-save", bfDefault);
        this.insert(new TVGroup(new TVRect(0, 0, 60, 12)).insertAll([
            new TVLabel(new TVRect(2, 1, 50, 2), "~D~OS private overlay per user (MiB)", this.capacity),
            this.capacity,
            new TVStaticText(new TVRect(2, 4, 58, 6), "1–256 MiB; default 128. Excludes shared C files.\nLowering the limit does not delete saved files."),
            this.saveButton,
            new TVButton(new TVRect(31, 7, 44, 9), "~C~ancel", "server-settings-cancel", bfNormal),
            this.status,
        ]));
        this.requestVersion = 0;
        this.rebuildTask = null;
        this.onBeforeRebuild = null;
        this.onRebuildStarted = null;
        this.bindCommonClose(() => this.close());
        this.bindDrag();
    }

    open() {
        super.open();
        this.capacity.setData("");
        this.capacity.focus();
        void this.loadSettings();
    }

    close() {
        this.requestVersion += 1;
        super.close();
    }

    async loadSettings() {
        const version = ++this.requestVersion;
        this.saveButton.setState(sfDisabled, true);
        this.status.setText("Loading server configuration...");
        try {
            const data = await TVLoginDialog.request("/api/admin/settings");
            if (version !== this.requestVersion || !this.isOpen()) { return; }
            this.capacity.setData(String(data.dos_user_disk_mb));
            this.capacity.selectAll();
            this.status.setText("Applies to every signed-in user's C drive.");
            this.saveButton.setState(sfDisabled, false);
        } catch (error) {
            if (version === this.requestVersion && this.isOpen()) { this.status.setText(error.message); }
        }
    }

    async saveSettings() {
        if (this.saveButton.state & sfDisabled) { return; }
        const value = this.capacity.getData().trim();
        const capacity = Number(value);
        if (!/^\d{1,3}$/.test(value) || capacity < 1 || capacity > 256) {
            this.status.setText("Enter a capacity between 1 and 256 MiB.");
            this.capacity.focus();
            return;
        }
        const version = ++this.requestVersion;
        this.saveButton.setState(sfDisabled, true);
        try {
            await TVLoginDialog.request("/api/admin/settings", "PUT", { dos_user_disk_mb: capacity });
            if (version === this.requestVersion && this.isOpen()) {
                this.status.setText("Saved. Restart open DOS sessions to reload capacity.");
            }
        } catch (error) {
            if (version === this.requestVersion && this.isOpen()) { this.status.setText(error.message); }
        } finally {
            if (version === this.requestVersion) { this.saveButton.setState(sfDisabled, false); }
        }
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what !== evCommand) { return; }
        switch (event.command) {
            case "server-settings-save": void this.saveSettings(); break;
            case "server-settings-cancel": this.close(); break;
            case "server-rebuild-dos": void this.rebuild("dos"); break;
            case "server-rebuild-midi": void this.rebuild("midi"); break;
            default: return;
        }
        this.clearEvent(event);
    }

    async rebuild(resource) {
        if (this.rebuildTask) { this.rebuildTask.progress?.open(); return; }
        const task = { progress: null };
        this.rebuildTask = task;
        const path = `/api/admin/rebuild/${resource}`;
        const title = resource === "dos" ? "Rebuild DOS C" : "Rebuild MIDI";
        try {
            let status = await TVLoginDialog.request(path);
            if (!status.rebuilding) {
                const box = new TVMessageBox();
                this.owner.insert(box);
                let answer;
                try {
                    answer = await box.show({ title, type: TVMessageBox.MF_CONFIRMATION,
                        lines: resource === "dos" ? [
                            "Replace the shared C drive from dos-prompt.json?",
                            "The current disk will move to a server backup.",
                            "Private overlays and cached archives will be kept.",
                            "Open DOS sessions must be restarted.",
                        ] : [
                            "Replace all game MIDI tracks, covers and catalog?",
                            "The current library will move to a server backup.",
                            "The old downloader stops before the data is replaced.",
                            "Sources will be downloaded again from midi-sources.json.",
                        ], buttons: TVMessageBox.MF_OK_CANCEL });
                } finally { box.destroy(); }
                if (answer !== "ok") { return; }
                this.requestVersion += 1;
                await this.onBeforeRebuild?.(resource);
                status = await TVLoginDialog.request(path, "POST");
                this.onRebuildStarted?.(resource);
            }
            this.saveButton.setState(sfDisabled, true);
            const progress = new TVIndexProgressDialog(title, "Preparing rebuild...");
            progress.setHelpCtx(hcServerConfiguration);
            task.progress = progress;
            this.owner.insert(progress);
            this.owner.dialogManager.register(`rebuild-${resource}`, progress);
            progress.open();
            for (;;) {
                if (this.destroyed) { return; }
                progress.update(status);
                progress.summary.setText(`${status.phase || "Rebuilding"}: ${status.processed || 0}/${status.total || 0}`);
                this.status.setText(`${title}: ${status.percent || 0}% · ${status.phase || status.state}`);
                if (["error", "partial"].includes(status.state)) { throw new Error(status.error || "Some rebuild downloads failed."); }
                if (status.state === "ready" && !status.rebuilding) {
                    this.status.setText(`Rebuilt. Backup: ${status.backup || "none (no previous data)"}`);
                    break;
                }
                await new Promise((resolve) => setTimeout(resolve, 1000));
                status = await TVLoginDialog.request(path);
            }
        } catch (error) {
            this.status.setText(error.message);
        } finally {
            task.progress?.destroy();
            this.rebuildTask = null;
            this.saveButton.setState(sfDisabled, false);
        }
    }
}

class TVViewGalleryDialog extends TVDialog {
    static viewName = "widget-gallery";

    constructor() {
        const nameInput = new TVInputLine(new TVRect(10, 1, 38, 2), 255).setData("Turbo Vision");
        const nameLabel = new TVLabel(new TVRect(2, 1, 10, 2), "~N~ame:", nameInput);
        const checks = new TVCheckBoxes(new TVRect(2, 4, 31, 7), [
                { label: "~F~rames", value: "frames", checked: true },
                { label: "~S~hadows", value: "shadows", checked: true },
                { label: "D~i~sabled", value: "disabled", disabled: true },
            ]);
        const radios = new TVRadioButtons(new TVRect(2, 10, 31, 13), [
                { label: "~T~ext", value: "text", checked: true },
                { label: "~G~raphics", value: "graphics" },
                { label: "~M~ono", value: "mono", disabled: true },
            ]);
        const multiChecks = new TVMultiCheckBoxes(new TVRect(2, 16, 31, 19), [
                { label: "~O~ff / On / Auto", value: "mode", state: 0 },
                { label: "~R~ead / Write / Both", value: "access", state: 1 },
                { label: "D~i~sabled", value: "disabled", state: 2, disabled: true },
            ]);
        const staticText = new TVStaticText(
            new TVRect(2, 20, 64, 21),
            "Static text · label hotkeys · disabled states",
        );
        const terminal = new TVTerminal(new TVRect(0, 1, 62, 4), 50);
        const infoBox = new TVInfoBox(new TVRect(2, 21, 64, 26), "Event log", [terminal]);
        const okButton = new TVButton(new TVRect(2, 27, 12, 29), "~O~K", "gallery-ok", bfDefault);
        const applyButton = new TVButton(new TVRect(13, 27, 24, 29), "~A~pply", "gallery-apply", bfNormal);
        const messageButton = new TVButton(new TVRect(25, 27, 38, 29), "~M~essage", "gallery-message", bfNormal);
        const clearLogButton = new TVButton(new TVRect(39, 27, 52, 29), "C~l~ear log", "gallery-clear-log", bfNormal);
        const disabledButton = new TVButton(new TVRect(53, 27, 64, 29), "Disabled", "", bfNormal)
            .setState(sfDisabled, true);
        const listBox = new TVListBox(new TVRect(34, 4, 64, 10));
        const galleryMain = new TVGroup(new TVRect(0, 0, 66, 30)).insertAll([
            nameLabel,
            nameInput,
            new TVStaticText(new TVRect(2, 3, 31, 4), "Check boxes"),
            checks,
            new TVStaticText(new TVRect(2, 9, 31, 10), "Radio buttons"),
            radios,
            new TVStaticText(new TVRect(2, 15, 31, 16), "Multi check boxes"),
            multiChecks,
            new TVStaticText(new TVRect(34, 3, 64, 4), "List viewer"),
            listBox,
            infoBox,
            staticText,
            okButton,
            applyButton,
            messageButton,
            clearLogButton,
            disabledButton,
        ]);

        super(new TVRect(0, 0, 68, 32), "Widget Gallery");
        this.setHelpCtx(hcWidgetGallery);
        this.insert(galleryMain);
        this.nameInput = nameInput;
        this.checks = checks;
        this.radios = radios;
        this.multiChecks = multiChecks;
        this.okButton = okButton;
        this.applyButton = applyButton;
        this.messageButton = messageButton;
        this.clearLogButton = clearLogButton;
        this.infoBox = infoBox.resolve(this.dialog);
        this.terminal = terminal.bind(terminal.root);
        this.messageBox = null;
        this.listBox = listBox;
        this.listBox.setItems([
            "TDialog",
            "TInputLine",
            "TListViewer",
            "TButton",
            "TScrollBar",
            "TCheckBoxes",
            "TRadioButtons",
            "TStaticText",
            "TLabel",
            "TMessageBox",
            "TMultiCheckBoxes",
            "TTerminal",
            "THistory",
        ], 0);
        this.listBox.bind({
            onSelect: (item) => this.setStatus(`Selected: ${item}`),
            onActivate: (item) => this.setStatus(`Activated: ${item}`),
        });
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bindGallery();
        this.setStatus("Ready");
    }

    bindGallery() {
        // TVDialog translates browser input to Turbo Vision events.
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evBroadcast) {
            if (event.infoPtr === this.nameInput) {
                this.setStatus(`Name: ${this.nameInput.getData() || "(empty)"}`);
            } else if (event.infoPtr === this.checks || event.infoPtr === this.radios) {
                const option = event.infoPtr.options[event.infoLong];
                if (option) {
                    const checked = event.infoPtr.mark(event.infoLong);
                    this.setStatus(`${option.value}: ${checked ? "on" : "off"}`);
                }
            } else if (event.infoPtr === this.multiChecks) {
                const option = this.multiChecks.options[event.infoLong];
                if (option) { this.setStatus(`${option.value}: state ${option.state}`); }
            } else { return; }
            this.clearEvent(event);
            return;
        }
        if (event.what !== evCommand) { return; }
        if (event.command === "gallery-ok") { this.close(); }
        else if (event.command === "gallery-apply") { this.setStatus("Apply command"); }
        else if (event.command === "gallery-clear-log") { this.terminal.clear(); }
        else if (event.command === "gallery-message") { void this.showMessage(); }
        else { return; }
        this.clearEvent(event);
    }

    async showMessage() {
        if (!this.messageBox) {
            this.messageBox = new TVMessageBox();
            this.owner?.insert(this.messageBox);
        }
        const command = await this.messageBox.show({
            type: TVMessageBox.MF_INFORMATION,
            lines: ["Turbo Vision message box"],
            buttons: TVMessageBox.MF_OK_CANCEL,
        });
        this.setStatus(`Message: ${command}`);
    }

    open() {
        super.open();
        window.requestAnimationFrame(() => this.listBox.updateScrollbar());
    }

    setStatus(message) {
        this.terminal.append(message);
    }
}

function normalizeFileDialogEntries(entries = []) {
    return entries.map((entry) => {
        const kind = entry.kind === "doc" ? "doc" : "help";
        const root = kind === "doc" ? "DOCS" : "HELP";
        const group = String(entry.group || "").replace(/[\\/]+/g, "\\");
        const directory = group ? `${root}\\${group}` : root;
        const fileName = String(entry.fileName || entry.name || entry.file || "").split(/[\\/]/).pop();
        return {
            ...entry,
            kind,
            directory,
            fileName,
            virtualPath: `${directory}\\${fileName}`,
            historyKey: `${kind}:${entry.file}`,
        };
    }).filter((entry) => entry.file && entry.fileName);
}

class TVHistoryStore {
    constructor(storageKey, maxItems = 10) {
        this.storageKey = storageKey;
        this.maxItems = maxItems;
    }

    keys() {
        try {
            const stored = JSON.parse(window.localStorage.getItem(this.storageKey) || "[]");
            return Array.isArray(stored)
                ? stored.filter((key) => typeof key === "string").slice(0, this.maxItems)
                : [];
        } catch {
            return [];
        }
    }

    entries(items, keyFor = (item) => item.historyKey) {
        const byKey = new Map(items.map((item) => [keyFor(item), item]));
        return this.keys().map((key) => byKey.get(key)).filter(Boolean);
    }

    remember(key) {
        if (!key) { return; }
        const keys = [key, ...this.keys().filter((item) => item !== key)].slice(0, this.maxItems);
        try {
            window.localStorage.setItem(this.storageKey, JSON.stringify(keys));
        } catch {
            // Storage may be unavailable under restrictive file:// environments.
        }
    }
}

class TVHistoryViewer extends TVListBox {
    constructor(bounds, historyId) {
        super(bounds);
        this.historyId = String(historyId || "file-open");
    }

    _semanticName() { return `${this.historyId}-history-list`; }

    defaultContent(item, index) {
        const text = item?.virtualPath ?? item?.displayPath ?? item?.value ?? item?.label;
        return escapeHtml(text == null ? String(index) : String(text));
    }
}

class TVHistory extends TVButton {
    constructor(bounds, link, historyId) {
        if (!(link instanceof TVInputLine)) {
            throw new TypeError("TVHistory expects a TVInputLine link");
        }
        const normalizedId = String(historyId || "");
        const command = normalizedId.includes("file-open")
            ? "file-open-history"
            : normalizedId.includes("directory")
                ? "change-dir-history"
                : normalizedId.includes("midi-filter")
                    ? "midi-filter-history"
                : "find-history";
        super(bounds, "", command, bfNormal);
        this.link = link;
        this.historyId = normalizedId || "thelp:history";
        this.store = new TVHistoryStore(this.historyId);
        this.setCommandData({ expanded: false });
        this.setState(sfDisabled, true);
        this.window = null;
    }

    _drawParts() {
        const parts = super._drawParts();
        const classes = ["tv-file-open-history-button"];
        if (this.command === "change-dir-history") { classes.push("tv-change-dir-history-button"); }
        if (this.command === "find-history") { classes.push("tv-find-history-button"); }
        return {
            ...parts,
            dialog: false,
            className: classes.join(" "),
            labelMarkup: [
                '<span class="tv-file-open-history-side" aria-hidden="true">▐</span>',
                '<span class="tv-file-open-history-arrow" aria-hidden="true">↓</span>',
                '<span class="tv-file-open-history-side" aria-hidden="true">▌</span>',
            ].join(""),
            ariaLabel: {
                "file-open-history": "History",
                "change-dir-history": "Directory history",
                "find-history": "Find history",
                "midi-filter-history": "Filter history",
            }[this.command],
            ariaExpanded: Boolean(this.commandData.expanded),
        };
    }

    keys() { return this.store.keys(); }
    entries(items, keyFor) { return this.store.entries(items, keyFor); }
    remember(key) { this.store.remember(key); }

    bindWindow(popup, items, onSelect) {
        if (!(popup instanceof TVHistoryWindow)) {
            throw new TypeError("TVHistory.bindWindow expects TVHistoryWindow");
        }
        this.window = popup.connect(this, items, onSelect);
        return this.window;
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand && event.infoPtr === this && event.command === this.command && this.window) {
            this.window.toggle();
            this.clearEvent(event);
        }
    }
}

class TVHistoryWindow extends TVWindow {
    constructor(bounds, historyId) {
        super(bounds, "", wnNoNumber);
        this.flags = wfClose;
        this.historyId = String(historyId || "file-open");
        this.viewer = new TVHistoryViewer(new TVRect(
            0,
            0,
            Math.max(0, bounds.width - 1),
            Math.max(0, bounds.height - 2),
        ), this.historyId);
        this.insert(this.viewer);
        this.setState(sfVisible, false);
        this.buttonView = null;
        this.items = () => [];
        this.onSelect = null;
        this.bound = false;
        this.onOutsideMouseDown = (nativeEvent) => {
            this.dispatchEvent(new TVEvent(evMouseDown, { infoPtr: this, nativeEvent }));
        };
    }

    _semanticName() { return `${this.historyId}-history-popup`; }

    connect(button, items = () => [], onSelect = null) {
        this.buttonView = button instanceof TVHistory ? button : null;
        this.items = items;
        this.onSelect = onSelect;
        if (this.bound) { return this; }
        this.bound = true;
        this.viewer.bind({
            onSelect: (item) => this.onSelect?.(item, false),
            onActivate: (item) => this.onSelect?.(item, true),
        });
        this._setOpen(false);
        this.refresh();
        return this;
    }

    refresh() {
        const items = this.items();
        this.viewer.setItems(items, items.length ? 0 : -1);
        this.buttonView?.setState(sfDisabled, false);
        return items;
    }

    isOpen() {
        return Boolean(this.root && this.getState(sfVisible));
    }

    _setOpen(open) {
        this.setState(sfVisible, open);
        this.root?.setAttribute("aria-hidden", open ? "false" : "true");
        this.buttonView?.root?.setAttribute("aria-expanded", open ? "true" : "false");
        if (this.buttonView) { this.buttonView.commandData.expanded = open; }
    }

    show() {
        if (!this.root) { return false; }
        this.refresh();
        this._setOpen(true);
        document.addEventListener("mousedown", this.onOutsideMouseDown);
        fillBorders(this.root);
        window.requestAnimationFrame(() => {
            this.viewer.updateScrollbar();
            this.viewer.selectedElement()?.focus();
        });
        return true;
    }

    toggle() {
        if (this.isOpen()) { this.hide(); }
        else { this.show(); }
    }

    hide({ restoreFocus = false } = {}) {
        document.removeEventListener("mousedown", this.onOutsideMouseDown);
        this._setOpen(false);
        if (restoreFocus) { this.buttonView?.focus(); }
    }

    close() { this.hide({ restoreFocus: true }); }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what !== evMouseDown || !event.nativeEvent || !this.isOpen()) { return; }
        const target = event.nativeEvent?.target;
        if (this.buttonView?.root?.contains(target) || this.root?.contains(target)) { return; }
        this.hide();
        this.clearEvent(event);
    }

    handleEscape(event) {
        if (event.key !== "Escape" || !this.isOpen()) { return false; }
        event.preventDefault();
        event.stopPropagation();
        this.hide({ restoreFocus: true });
        return true;
    }
}

class TVFileList extends TVListBox {
    static viewName = "file-open-files";

    constructor(bounds, numCols = 2) {
        super(bounds, numCols);
        this.rows = 8;
        this.onViewportChange = null;
    }

    bindRoot(root) {
        super.bindRoot(root);
        this.root?.style.setProperty("--tv-file-list-rows", String(this.rows));
        return this;
    }

    select(index, options = {}) {
        super.select(index, options);
        if (this.onViewportChange) { this.onViewportChange(); }
    }

    firstColumn() {
        const viewport = this.scrollViewport;
        if (!viewport || !viewport.clientWidth) { return 0; }
        const columnWidth = viewport.clientWidth / 2;
        return Math.max(0, Math.round(viewport.scrollLeft / columnWidth));
    }

    scrollColumns(delta) {
        const viewport = this.scrollViewport;
        if (!viewport || !this.items.length) { return; }
        const columns = Math.ceil(this.items.length / this.rows);
        const maxColumn = Math.max(0, columns - 2);
        const nextColumn = Math.min(maxColumn, Math.max(0, this.firstColumn() + delta));
        viewport.scrollLeft = nextColumn * (viewport.clientWidth / 2);
        if (this.onViewportChange) { this.onViewportChange(); }
    }

    ensureSelectionVisible() {
        if (!this.scrollViewport || this.selectedIndex < 0) { return; }
        const column = Math.floor(this.selectedIndex / this.rows);
        const firstColumn = this.firstColumn();
        if (column < firstColumn) {
            this.scrollColumns(column - firstColumn);
        } else if (column > firstColumn + 1) {
            this.scrollColumns(column - firstColumn - 1);
        }
    }

    keyDestination(index, key) {
        if (key === "ArrowRight") { return Math.min(this.items.length - 1, index + this.rows); }
        if (key === "ArrowLeft") { return Math.max(0, index - this.rows); }
        if (key === "PageDown") { return Math.min(this.items.length - 1, index + this.rows * 2); }
        if (key === "PageUp") { return Math.max(0, index - this.rows * 2); }
        return super.keyDestination(index, key);
    }
}

class TVFileOpenDialog extends TVDialog {
    static viewName = "file-open";

    constructor() {
        const nameInput = new TVInputLine(new TVRect(2, 2, 30, 3), 255).setData("*.*");
        const nameLabel = new TVLabel(new TVRect(1, 1, 12, 2), "~N~ame", nameInput);
        const filesLabel = new TVLabel(new TVRect(1, 4, 12, 5), "~F~iles");
        const openButton = new TVButton(new TVRect(34, 2, 45, 4), "~O~pen", "file-open-confirm", bfDefault);
        const cancelButton = new TVButton(new TVRect(34, 5, 45, 7), "Cancel", "file-open-cancel", bfNormal);
        const historyButton = new TVHistory(new TVRect(30, 2, 33, 3), nameInput, "thelp:file-open-history");
        const fileList = new TVFileList(new TVRect(2, 5, 33, 13), 2);
        const scrollLeftButton = new TVFileScrollButton(new TVRect(2, 13, 3, 14), displayCp437Char(17), "file-open-scroll-left", bfNormal);
        const scrollTrack = new TVStaticText(new TVRect(3, 13, 32, 14), "");
        const scrollRightButton = new TVFileScrollButton(new TVRect(32, 13, 33, 14), displayCp437Char(16), "file-open-scroll-right", bfNormal);
        const pathLabel = new TVStaticText(new TVRect(0, 15, 47, 16), "");
        const detailLabel = new TVStaticText(new TVRect(0, 16, 47, 17), "");
        const historyPopup = new TVHistoryWindow(new TVRect(0, 0, 32, 8), "file-open");
        const fileOpenMain = new TVGroup(new TVRect(0, 0, 47, 17)).insertAll([
            nameLabel,
            nameInput,
            historyButton,
            filesLabel,
            fileList,
            scrollLeftButton,
            scrollTrack,
            scrollRightButton,
            openButton,
            cancelButton,
            pathLabel,
            detailLabel,
            historyPopup,
        ]);

        super(new TVRect(0, 0, 49, 19), "Open a File");
        this.setHelpCtx(hcFileOpen);
        this.insert(fileOpenMain);
        this.setState(sfModal, true);
        this.entries = [];
        this.configured = false;
        this.currentDirectory = "";
        this.currentItems = [];
        this.onOpen = null;
        this.history = historyButton;
        this.nameInput = nameInput;
        this.pathLabel = pathLabel;
        this.detailLabel = detailLabel;
        this.openButton = openButton;
        this.cancelButton = cancelButton;
        this.historyButton = historyButton;
        this.historyPopup = historyPopup;
        this.scrollLeftButton = scrollLeftButton;
        this.scrollRightButton = scrollRightButton;
        this.scrollTrack = scrollTrack;
        this.fileList = fileList;
        this.fileList.onViewportChange = () => this.updateHorizontalScrollbar();
        this.historyList = historyPopup.viewer;
        this.fileList.bind({
            onSelect: (item) => this.selectItem(item),
            onActivate: (item) => this.activateItem(item),
        });
        this.historyWindow = this.historyButton.bindWindow(
            this.historyPopup,
            () => this.historyEntries(),
            (entry, activate) => this.selectHistory(entry, activate),
        );
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bindFileOpen();
    }

    configure(entries = [], onOpen = null) {
        this.entries = normalizeFileDialogEntries(entries);
        this.configured = true;
        this.onOpen = typeof onOpen === "function" ? onOpen : null;
        if (!this.directoryExists(this.currentDirectory)) {
            this.currentDirectory = "";
        }
        this.refresh();
    }

    bindFileOpen() {
        // Browser input is translated by TVDialog and handled in handleEvent.
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evKeyDown && this.historyWindow.handleEscape(event.nativeEvent)) {
            this.clearEvent(event);
            return;
        }
        if (event.what === evCommand) {
            if (event.command === "file-open-confirm") { this.openSelected(); }
            else if (event.command === "file-open-cancel") { this.close(); }
            else if (event.command === "file-open-scroll-left") { this.fileList.scrollColumns(-1); }
            else if (event.command === "file-open-scroll-right") { this.fileList.scrollColumns(1); }
            else { return; }
            this.clearEvent(event);
            return;
        }
        if (event.what === evBroadcast && event.infoPtr === this.nameInput) {
            this.selectNameMatch();
            this.clearEvent(event);
            return;
        }
        const keyEvent = event.nativeEvent;
        if (event.what !== evKeyDown || !keyEvent?.altKey || keyEvent.ctrlKey || keyEvent.metaKey) { return; }
        const key = keyEvent.key.toLowerCase();
        if (key === "n") {
            keyEvent.preventDefault();
            this.nameInput.focus();
            this.nameInput.selectAll();
        } else if (key === "f") {
            keyEvent.preventDefault();
            this.fileList.selectedElement()?.focus();
        } else if (key === "o") {
            keyEvent.preventDefault();
            this.openSelected();
        } else {
            return;
        }
        this.clearEvent(event);
    }

    open() {
        this.historyWindow.hide();
        this.refresh();
        super.open();
        window.requestAnimationFrame(() => {
            this.updateHorizontalScrollbar();
            this.nameInput.focus();
            this.nameInput.selectAll();
        });
    }

    close() {
        this.hideHistory();
        super.close();
    }

    directoryExists(path) {
        if (!path) { return true; }
        return this.entries.some((entry) => (
            entry.directory === path || entry.directory.startsWith(`${path}\\`)
        ));
    }

    parentDirectory(path) {
        const parts = String(path || "").split("\\").filter(Boolean);
        parts.pop();
        return parts.join("\\");
    }

    setDirectory(path) {
        const directory = String(path || "");
        if (!this.directoryExists(directory)) { return false; }
        this.currentDirectory = directory;
        this.refresh();
        return true;
    }

    buildItems() {
        if (!this.configured) {
            return [{ type: "status", label: "Loading HELP/DOCS..." }];
        }
        if (!this.entries.length) {
            return [{ type: "status", label: "No HELP or DOCS files" }];
        }
        const prefix = this.currentDirectory ? `${this.currentDirectory}\\` : "";
        const directories = new Map();
        const files = [];
        for (const entry of this.entries) {
            if (entry.directory === this.currentDirectory) {
                files.push({ type: "file", label: entry.fileName, entry });
                continue;
            }
            if (!entry.directory.startsWith(prefix)) { continue; }
            const rest = entry.directory.slice(prefix.length);
            const child = rest.split("\\")[0];
            if (!child) { continue; }
            const path = prefix + child;
            directories.set(path, {
                type: "directory",
                label: `${child}\\`,
                path,
            });
        }
        const result = [];
        if (this.currentDirectory) {
            result.push({
                type: "parent",
                label: "..\\",
                path: this.parentDirectory(this.currentDirectory),
            });
        }
        result.push(...Array.from(directories.values()).sort((left, right) => left.label.localeCompare(right.label)));
        result.push(...files.sort((left, right) => left.label.localeCompare(right.label)));
        return result;
    }

    refresh() {
        this.currentItems = this.buildItems();
        this.fileList.setItems(this.currentItems, this.currentItems.length ? 0 : -1);
        this.nameInput.setData("*.*");
        this.updateInfo(this.currentItems[0] || null);
        this.updateHistoryState();
        this.updateHorizontalScrollbar();
    }

    currentMaskPath() {
        const directory = this.currentDirectory ? `${this.currentDirectory}\\` : "";
        return `THelpViewer:\\${directory}*.*`;
    }

    selectItem(item) {
        if (!item || item.type === "status") { return; }
        this.nameInput.setData(item.type === "file" ? item.entry.fileName : `${item.label}*.*`);
        this.updateInfo(item);
    }

    updateInfo(item) {
        this.pathLabel.setText(` ${this.currentMaskPath()}`);
        if (!item) {
            this.detailLabel.setText("");
        } else if (item.type === "status") {
            this.detailLabel.setText(` ${item.label}`);
        } else if (item.type === "file") {
            const format = String(item.entry.format || (item.entry.kind === "doc" ? "Markdown" : "Help")).toUpperCase();
            const topics = Number.isInteger(item.entry.topics) ? `  ${item.entry.topics} topics` : "";
            this.detailLabel.setText(` ${item.entry.fileName}  ${format}${topics}`);
        } else {
            this.detailLabel.setText(` ${item.label}  Directory`);
        }
    }

    activateItem(item) {
        if (!item) { return; }
        if (item.type === "file") {
            this.openEntry(item.entry);
        } else if (item.type === "directory" || item.type === "parent") {
            this.currentDirectory = item.path;
            this.refresh();
            this.fileList.selectedElement()?.focus();
        }
    }

    selectNameMatch() {
        const query = this.nameInput.getData().trim().toLocaleLowerCase();
        if (!query || query.includes("*")) { return; }
        const index = this.currentItems.findIndex((item) => item.label.toLocaleLowerCase().startsWith(query));
        if (index >= 0) {
            this.fileList.select(index);
            this.updateInfo(this.currentItems[index]);
        }
    }

    openSelected() {
        const query = this.nameInput.getData().trim().toLocaleLowerCase();
        const exact = this.currentItems.find((item) => (
            item.type === "file" && item.entry.fileName.toLocaleLowerCase() === query
        ));
        if (exact) {
            this.openEntry(exact.entry);
            return;
        }
        this.activateItem(this.fileList.selectedItem());
    }

    openEntry(entry) {
        if (!entry || !this.onOpen) { return; }
        this.remember(entry);
        this.close();
        this.onOpen(entry);
    }

    updateHorizontalScrollbar() {
        const trackLength = 29;
        const columns = Math.max(1, Math.ceil(this.currentItems.length / this.fileList.rows));
        const maxColumn = Math.max(0, columns - 2);
        const position = maxColumn
            ? Math.round((this.fileList.firstColumn() / maxColumn) * (trackLength - 1))
            : -1;
        const cells = Array.from({ length: trackLength }, () => displayCp437Char(177));
        if (position >= 0) { cells[position] = displayCp437Char(254); }
        this.scrollTrack.setText(cells.join(""));
    }

    storedHistoryKeys() {
        return this.history.keys();
    }

    historyEntries() {
        return this.history.entries(this.entries);
    }

    remember(entry) {
        this.history.remember(entry.historyKey);
    }

    updateHistoryState() {
        this.historyWindow.refresh();
    }

    toggleHistory() {
        this.historyWindow.toggle();
    }

    hideHistory() {
        this.historyWindow.hide();
    }

    selectHistory(entry, activate = false) {
        if (!entry) { return; }
        this.currentDirectory = entry.directory;
        this.refresh();
        const index = this.currentItems.findIndex((item) => (
            item.type === "file" && item.entry.historyKey === entry.historyKey
        ));
        this.fileList.select(index);
        this.selectItem(this.currentItems[index]);
        if (activate) {
            this.openEntry(entry);
        } else {
            this.hideHistory();
            this.nameInput.focus();
        }
    }
}

class TVChangeDirectoryDialog extends TVDialog {
    static viewName = "change-dir";

    constructor() {
        const directoryInput = new TVInputLine(new TVRect(2, 2, 31, 3), 255).setData("");
        const directoryLabel = new TVLabel(new TVRect(1, 1, 18, 2), "~D~irectory", directoryInput);
        const treeLabel = new TVLabel(new TVRect(1, 4, 18, 5), "Directory ~t~ree");
        const changeButton = new TVButton(new TVRect(33, 4, 43, 6), "~C~hdir", "change-dir-confirm", bfDefault);
        const revertButton = new TVButton(new TVRect(33, 7, 43, 9), "~R~evert", "change-dir-revert", bfNormal);
        const cancelButton = new TVButton(new TVRect(33, 10, 43, 12), "Cancel", "change-dir-cancel", bfNormal);
        const historyButton = new TVHistory(new TVRect(31, 2, 34, 3), directoryInput, "thelp:directory-history");
        const directoryList = new TVOutline(new TVRect(2, 5, 31, 13));
        const detailView = new TVStaticText(new TVRect(2, 14, 42, 15), "");
        const historyPopup = new TVHistoryWindow(new TVRect(0, 0, 33, 8), "change-dir");
        const changeDirectoryMain = new TVGroup(new TVRect(0, 0, 44, 16)).insertAll([
            directoryLabel,
            directoryInput,
            historyButton,
            treeLabel,
            directoryList,
            changeButton,
            revertButton,
            cancelButton,
            detailView,
            historyPopup,
        ]);

        super(new TVRect(0, 0, 46, 18), "Change Directory");
        this.setHelpCtx(hcChangeDirectory);
        this.insert(changeDirectoryMain);
        this.setState(sfModal, true);
        this.entries = [];
        this.directories = [];
        this.directoryTree = [];
        this.currentDirectory = "";
        this.initialDirectory = "";
        this.onChange = null;
        this.history = historyButton;
        this.pathInput = directoryInput;
        this.detailView = detailView;
        this.changeButton = changeButton;
        this.revertButton = revertButton;
        this.cancelButton = cancelButton;
        this.historyButton = historyButton;
        this.historyPopup = historyPopup;
        this.directoryList = directoryList;
        this.historyList = historyPopup.viewer;
        this.directoryList.bind({
            onSelect: (item) => this.selectDirectory(item.path),
            onActivate: (item) => {
                this.selectDirectory(item.path);
                this.commit();
            },
        });
        this.historyWindow = this.historyButton.bindWindow(
            this.historyPopup,
            () => this.history.entries(this.directories).map((item) => ({
                ...item,
                displayPath: this.displayPath(item.path),
            })),
            (item, activate) => {
                this.selectDirectory(item.path);
                this.historyWindow.hide();
                if (activate) { this.commit(); }
                else { this.pathInput.focus(); }
            },
        );
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bindChangeDirectory();
    }

    configure(entries = [], onChange = null) {
        this.entries = normalizeFileDialogEntries(entries);
        this.onChange = typeof onChange === "function" ? onChange : null;
        this.rebuildDirectories();
        this.setDirectory(this.currentDirectory);
    }

    rebuildDirectories() {
        const paths = new Set(["", "HELP", "DOCS"]);
        for (const entry of this.entries) {
            const parts = entry.directory.split("\\").filter(Boolean);
            for (let count = 1; count <= parts.length; count += 1) {
                paths.add(parts.slice(0, count).join("\\"));
            }
        }
        this.directories = Array.from(paths).sort((left, right) => {
            if (!left) { return -1; }
            if (!right) { return 1; }
            return left.localeCompare(right);
        }).map((path) => {
            const depth = path ? path.split("\\").length : 0;
            const name = path ? path.split("\\").pop() : "THelpViewer:";
            return {
                path,
                historyKey: path || ".",
                label: path ? `${"  ".repeat(depth - 1)}${name}\\` : "THelpViewer:\\",
            };
        });
        const byPath = new Map(this.directories.map((item) => [item.path, { ...item, children: [] }]));
        for (const item of byPath.values()) {
            if (!item.path) { continue; }
            const parts = item.path.split("\\");
            parts.pop();
            byPath.get(parts.join("\\"))?.children.push(item);
        }
        for (const item of byPath.values()) {
            item.label = item.path ? `${item.path.split("\\").pop()}\\` : "THelpViewer:\\";
            item.children.sort((left, right) => left.label.localeCompare(right.label));
        }
        this.directoryTree = byPath.has("") ? [byPath.get("")] : [];
        this.historyWindow.refresh();
    }

    bindChangeDirectory() {
        // Browser input is translated by TVDialog and handled in handleEvent.
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evKeyDown && this.historyWindow.handleEscape(event.nativeEvent)) {
            this.clearEvent(event);
            return;
        }
        if (event.what === evCommand) {
            if (event.command === "change-dir-confirm") { this.commit(); }
            else if (event.command === "change-dir-revert") { this.setDirectory(this.initialDirectory); }
            else if (event.command === "change-dir-cancel") { this.close(); }
            else { return; }
            this.clearEvent(event);
            return;
        }
        if (
            event.infoPtr === this.pathInput
            && event.what === evBroadcast
            && event.nativeEvent?.type === "change"
        ) {
            this.selectInputPath();
            this.clearEvent(event);
            return;
        }
        const keyEvent = event.nativeEvent;
        if (event.what !== evKeyDown || !keyEvent) { return; }
        if (event.infoPtr === this.pathInput && keyEvent.key === "Enter") {
            keyEvent.preventDefault();
            this.selectInputPath();
            this.commit();
            this.clearEvent(event);
            return;
        }
        if (!keyEvent.altKey || keyEvent.ctrlKey || keyEvent.metaKey) { return; }
        const key = keyEvent.key.toLowerCase();
        if (key === "d") {
            keyEvent.preventDefault();
            this.pathInput.focus();
            this.pathInput.selectAll();
        } else if (key === "t") {
            keyEvent.preventDefault();
            this.directoryList.selectedElement()?.focus();
        } else if (key === "c") {
            keyEvent.preventDefault();
            this.commit();
        } else if (key === "r") {
            keyEvent.preventDefault();
            this.setDirectory(this.initialDirectory);
        } else {
            return;
        }
        this.clearEvent(event);
    }

    displayPath(path) {
        return `THelpViewer:\\${path ? `${path}\\` : ""}`;
    }

    normalizeInputPath(value) {
        return String(value || "")
            .replace(/^THelpViewer:/i, "")
            .replace(/[\\/]+/g, "\\")
            .replace(/^\\+|\\+$/g, "");
    }

    findDirectory(path) {
        const normalized = this.normalizeInputPath(path).toLocaleLowerCase();
        return this.directories.find((item) => item.path.toLocaleLowerCase() === normalized) || null;
    }

    setDirectory(path) {
        const item = this.findDirectory(path) || this.directories[0] || { path: "" };
        this.currentDirectory = item.path;
        this.directoryList.setTree(this.directoryTree, item.path, { expandAll: true });
        this.updatePath();
        return Boolean(item);
    }

    selectDirectory(path) {
        const item = this.findDirectory(path);
        if (!item) { return false; }
        this.currentDirectory = item.path;
        this.directoryList.selectKey(item.path);
        this.updatePath();
        return true;
    }

    selectInputPath() {
        const item = this.findDirectory(this.pathInput.getData());
        if (!item) {
            this.detailView.setText("Directory does not exist");
            return false;
        }
        return this.selectDirectory(item.path);
    }

    updatePath() {
        this.pathInput.setData(this.displayPath(this.currentDirectory));
        this.detailView.setText(`${this.entries.filter((entry) => entry.directory === this.currentDirectory).length} files`);
    }

    commit() {
        if (!this.selectInputPath()) { return; }
        const item = this.findDirectory(this.currentDirectory);
        this.history.remember(item?.historyKey);
        this.historyWindow.refresh();
        this.initialDirectory = this.currentDirectory;
        this.close();
        this.onChange?.(this.currentDirectory);
    }

    open() {
        this.historyWindow.hide();
        this.initialDirectory = this.currentDirectory;
        this.setDirectory(this.currentDirectory);
        super.open();
        window.requestAnimationFrame(() => {
            this.directoryList.updateScrollbar();
            this.pathInput.focus();
            this.pathInput.selectAll();
        });
    }

    close() {
        this.historyWindow.hide();
        super.close();
    }

}

class TVAsciiTable extends TVGroup {
    static viewName = "ascii-chart";

    constructor(bounds) {
        super(bounds);
        this.cells = Array.from({ length: 256 }, (_unused, code) => {
            const button = new TVAsciiCellButton(new TVRect(), displayCp437Char(code), "ascii-code", bfNormal).setValue(code);
            button.setCommandData({ selected: code === 0 });
            return button;
        });
        this.insertAll(this.cells);
    }

    select(code) {
        this.cells.forEach((cell, index) => {
            const selected = index === code;
            cell.commandData.selected = selected;
            cell.root?.classList.toggle("is-selected", selected);
            cell.root?.setAttribute("aria-pressed", selected ? "true" : "false");
        });
        this.cells[code]?.root?.focus();
    }
}

class TVAsciiTableDialog extends TVDialog {
    static viewName = "ascii";
    static palette = "ascii";

    constructor() {
        const chart = new TVAsciiTable(new TVRect());
        const report = new TVStaticText(new TVRect(), "");
        super(new TVRect(0, 0, 34, 12), "ASCII Chart");
        this.setHelpCtx(hcAsciiTable);
        this.insertAll([chart, report]);
        this.selectedCode = 0;
        this.chartView = chart;
        this.reportView = report;
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.updateReport(this.selectedCode);
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand && event.command === "ascii-code") {
            this.selectCode(Number(event.infoPtr?.value));
            this.clearEvent(event);
        } else if (event.what === evKeyDown) {
            this.onKeyDown(event.nativeEvent);
            if (event.nativeEvent?.defaultPrevented) { this.clearEvent(event); }
        }
    }

    open() {
        super.open();
        this.chartView.select(this.selectedCode);
        this.updateReport(this.selectedCode);
    }

    onKeyDown(event) {
        if (!this.isActive()) {
            return;
        }
        if (event.target && event.target.closest("input, textarea, select")) {
            return;
        }
        let nextCode = this.selectedCode;
        if (event.key === "ArrowLeft") {
            nextCode = (this.selectedCode + 255) & 0xFF;
        } else if (event.key === "ArrowRight") {
            nextCode = (this.selectedCode + 1) & 0xFF;
        } else if (event.key === "ArrowUp") {
            nextCode = (this.selectedCode + 224) & 0xFF;
        } else if (event.key === "ArrowDown") {
            nextCode = (this.selectedCode + 32) & 0xFF;
        } else {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        this.selectCode(nextCode);
    }

    selectCode(code) {
        if (!Number.isInteger(code) || code < 0 || code > 255) { return; }
        this.selectedCode = code;
        this.chartView.select(code);
        this.updateReport(code);
    }

    updateReport(code) {
        const char = code === 0 ? " " : displayCp437Char(code);
        const decimal = String(code).padStart(3, " ");
        const hex = code.toString(16).toUpperCase().padStart(2, "0");
        this.reportView.setText(`  Char: ${char} Decimal: ${decimal} Hex ${hex}`.padEnd(32, " "));
    }
}

class TVCalculatorDialog extends TVDialog {
    static viewName = "calc";

    constructor() {
        const buttonKeys = [
            ["CLEAR", "C", "C"],
            ["BACK", displayCp437Char(27), "Backspace"],
            ["PERCENT", "%", "%"],
            ["SIGN", displayCp437Char(241), "Change sign"],
            ["7", "7", "7"],
            ["8", "8", "8"],
            ["9", "9", "9"],
            ["DIVIDE", "/", "/"],
            ["4", "4", "4"],
            ["5", "5", "5"],
            ["6", "6", "6"],
            ["MULTIPLY", "*", "*"],
            ["1", "1", "1"],
            ["2", "2", "2"],
            ["3", "3", "3"],
            ["MINUS", "-", "-"],
            ["0", "0", "0"],
            ["DOT", ".", "."],
            ["EQUALS", "=", "="],
            ["PLUS", "+", "+"],
        ];
        const buttonValueMap = {
            CLEAR: "C",
            BACK: "\u001B",
            PERCENT: "%",
            SIGN: "\u00B1",
            DIVIDE: "/",
            MULTIPLY: "*",
            MINUS: "-",
            DOT: ".",
            EQUALS: "=",
            PLUS: "+",
        };
        const buttons = buttonKeys.map(([key, label, aria], index) => (
            new TVCalculatorButton(new TVRect(
                (index % 4) * 5,
                Math.floor(index / 4) * 2,
                (index % 4) * 5 + 5,
                Math.floor(index / 4) * 2 + 2,
            ), label, "calc-key", bfNormal)
                .setValue(key)
                .setCommandData({ description: aria })
        ));
        const displayView = new TVStaticText(new TVRect(2, 1, 20, 2), "");
        const keypad = new TVGroup(new TVRect(1, 3, 21, 13)).insertAll(buttons);
        const calcMain = new TVGroup(new TVRect(0, 0, 22, 14)).insertAll([
            displayView,
            keypad,
        ]);

        super(new TVRect(0, 0, 24, 15), "Calculator");
        this.setHelpCtx(hcCalculator);
        this.insert(calcMain);
        this.escapeCloses = false;
        this.buttonValueMap = buttonValueMap;
        this.status = "first";
        this.number = "0";
        this.sign = " ";
        this.operate = "=";
        this.operand = 0;
        this.displayView = displayView;
        this.buttons = buttons;
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.updateDisplay();
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand && event.command === "calc-key") {
            const token = String(event.infoPtr.value || "");
            this.calcKey(this.buttonValueMap[token] || token);
            this.clearEvent(event);
        } else if (event.what === evKeyDown) {
            this.onKeyDown(event.nativeEvent);
            if (event.nativeEvent?.defaultPrevented) { this.clearEvent(event); }
        }
    }

    onKeyDown(event) {
        if (!this.isActive()) {
            return;
        }
        if (event.target && event.target.closest("input, textarea, select")) {
            return;
        }
        const mapped = this.mapKeyEvent(event);
        if (!mapped) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        this.calcKey(mapped);
    }

    mapKeyEvent(event) {
        if (event.key === "Backspace") {
            return "\b";
        }
        if (event.key === "Escape") {
            return "\u001B";
        }
        if (event.key === "Enter") {
            return "\r";
        }
        if (event.key === "_") {
            return "_";
        }
        if (event.key && event.key.length === 1) {
            return event.key;
        }
        return "";
    }

    clear() {
        this.status = "first";
        this.number = "0";
        this.sign = " ";
        this.operate = "=";
        this.operand = 0;
    }

    error() {
        this.status = "error";
        this.number = "Error";
        this.sign = " ";
    }

    setDisplay(value) {
        if (!Number.isFinite(value)) {
            this.error();
            return;
        }
        if (value < 0) {
            this.sign = "-";
            this.number = String(-value);
        } else {
            this.sign = " ";
            this.number = String(value);
        }
        if (this.number.length > 25) {
            this.error();
        }
    }

    getDisplayValue() {
        return Number.parseFloat(this.number) || 0;
    }

    checkFirst() {
        if (this.status === "first") {
            this.status = "valid";
            this.number = "0";
            this.sign = " ";
        }
    }

    calcKey(key) {
        if (!key) {
            return;
        }
        let value = String(key).toUpperCase();
        if (this.status === "error" && value !== "C") {
            value = " ";
        }

        switch (value) {
            case "0":
            case "1":
            case "2":
            case "3":
            case "4":
            case "5":
            case "6":
            case "7":
            case "8":
            case "9":
                this.checkFirst();
                if (this.number.length < 15) {
                    if (this.number === "0") {
                        this.number = "";
                    }
                    this.number += value;
                }
                break;
            case ".":
                this.checkFirst();
                if (!this.number.includes(".")) {
                    this.number += ".";
                }
                break;
            case "\b":
            case "\u001B": {
                this.checkFirst();
                if (this.number.length <= 1) {
                    this.number = "0";
                } else {
                    this.number = this.number.slice(0, -1);
                }
                break;
            }
            case "_":
            case "\u00B1":
                this.sign = this.sign === " " ? "-" : " ";
                break;
            case "+":
            case "-":
            case "*":
            case "/":
            case "=":
            case "%":
            case "\r": {
                if (this.status === "valid") {
                    this.status = "first";
                    let r = this.getDisplayValue() * (this.sign === "-" ? -1 : 1);
                    if (value === "%") {
                        if (this.operate === "+" || this.operate === "-") {
                            r = (this.operand * r) / 100;
                        } else {
                            r /= 100;
                        }
                    }
                    switch (this.operate) {
                        case "+":
                            this.setDisplay(this.operand + r);
                            break;
                        case "-":
                            this.setDisplay(this.operand - r);
                            break;
                        case "*":
                            this.setDisplay(this.operand * r);
                            break;
                        case "/":
                            if (r === 0) {
                                this.error();
                            } else {
                                this.setDisplay(this.operand / r);
                            }
                            break;
                        default:
                            break;
                    }
                }
                this.operate = value === "\r" ? "=" : value;
                this.operand = this.getDisplayValue() * (this.sign === "-" ? -1 : 1);
                break;
            }
            case "C":
                this.clear();
                break;
            default:
                break;
        }
        this.updateDisplay();
    }

    updateDisplay() {
        const width = 18;
        const lead = Math.max(0, width - this.number.length - 2);
        const text = `${" ".repeat(lead)}${this.sign}${this.number} `;
        this.displayView.setText(text.slice(-width).padEnd(width, " "));
    }
}

class TVCalendarView extends TVGroup {
    static viewName = "calendar-grid";

    constructor(bounds) {
        super(bounds);
        this.cells = Array.from({ length: 42 }, () => {
            return new TVStaticText(new TVRect(), "  ");
        });
        this.insertAll(this.cells);
    }

    setMonth(first, days, today = 0, selected = today) {
        this.cells.forEach((cell, index) => {
            const day = first + index;
            const inMonth = day >= 1 && day <= days;
            cell.setText(inMonth ? String(day).padStart(2, " ") : "  ");
            cell.value = inMonth ? day : 0;
            cell.root?.classList.toggle("is-current", inMonth && day === today);
            cell.root?.classList.toggle("is-selected", inMonth && day === selected);
            cell.root?.classList.toggle("is-empty", !inMonth);
        });
    }
}

class TVCalendarDialog extends TVDialog {
    static viewName = "calendar";
    static palette = "calendar";

    constructor() {
        const now = new Date();
        const captionView = new TVStaticText(new TVRect(0, 0, 19, 1), "");
        const prevButton = new TVCalendarButton(new TVRect(19, 0, 22, 1), "<", "calendar-prev", bfNormal);
        const nextButton = new TVCalendarButton(new TVRect(22, 0, 25, 1), ">", "calendar-next", bfNormal);
        const todayButton = new TVCalendarButton(new TVRect(25, 0, 28, 1), "=", "calendar-today", bfNormal);
        const gridView = new TVCalendarView(new TVRect(0, 2, 28, 8));
        const calendarMain = new TVGroup(new TVRect(0, 0, 28, 8)).insertAll([
            captionView,
            prevButton,
            nextButton,
            todayButton,
            new TVStaticText(new TVRect(0, 1, 28, 2), "Mo  Tu  We  Th  Fr  Sa  Su  "),
            gridView,
        ]);
        super(new TVRect(0, 0, 30, 10), "Calendar");
        this.setHelpCtx(hcCalendar);
        this.insert(calendarMain);
        this.captionView = captionView;
        this.gridView = gridView;
        this.prevButton = prevButton;
        this.nextButton = nextButton;
        this.todayButton = todayButton;
        this.curYear = now.getFullYear();
        this.curMonth = now.getMonth() + 1;
        this.curDay = now.getDate();
        this.year = this.curYear;
        this.month = this.curMonth;
        this.day = this.curDay;
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.render();
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand) {
            if (event.command === "calendar-prev") { this.changeMonth(-1); }
            else if (event.command === "calendar-next") { this.changeMonth(1); }
            else if (event.command === "calendar-today") { this.resetToday(); }
            else { return; }
            this.clearEvent(event);
        } else if (event.what === evMouseDown && event.infoPtr?.owner === this.gridView) {
            const day = Number(event.infoPtr.value) || 0;
            if (day) { this.day = day; this.render(); }
            this.clearEvent(event);
        } else if (event.what === evKeyDown) {
            this.onKeyDown(event.nativeEvent);
            if (event.nativeEvent?.defaultPrevented) { this.clearEvent(event); }
        }
    }

    onKeyDown(event) {
        if (!this.isActive()) {
            return;
        }
        if (event.target && event.target.closest("input, textarea, select")) {
            return;
        }
        if (event.key === "+" || event.key === "ArrowRight") {
            event.preventDefault();
            this.changeDay(1);
        } else if (event.key === "-" || event.key === "ArrowLeft") {
            event.preventDefault();
            this.changeDay(-1);
        } else if (event.key === "ArrowUp") {
            event.preventDefault();
            this.changeDay(-7);
        } else if (event.key === "ArrowDown") {
            event.preventDefault();
            this.changeDay(7);
        } else if (event.key === "PageUp") {
            event.preventDefault();
            if (event.ctrlKey) { this.changeYear(-1); }
            else { this.changeMonth(-1); }
        } else if (event.key === "PageDown") {
            event.preventDefault();
            if (event.ctrlKey) { this.changeYear(1); }
            else { this.changeMonth(1); }
        } else if (event.key === "Home" || event.key === " ") {
            event.preventDefault();
            this.resetToday();
        }
    }

    changeMonth(delta) {
        this.month += delta;
        if (this.month > 12) {
            this.month = 1;
            this.year += 1;
        } else if (this.month < 1) {
            this.month = 12;
            this.year -= 1;
        }
        this.day = Math.min(this.day, this.daysInMonth(this.month, this.year));
        this.render();
    }

    changeYear(delta) {
        this.year = Math.max(1, this.year + delta);
        this.day = Math.min(this.day, this.daysInMonth(this.month, this.year));
        this.render();
    }

    changeDay(delta) {
        const date = new Date(Date.UTC(this.year, this.month - 1, this.day + delta));
        this.year = date.getUTCFullYear();
        this.month = date.getUTCMonth() + 1;
        this.day = date.getUTCDate();
        this.render();
    }

    resetToday() {
        this.year = this.curYear;
        this.month = this.curMonth;
        this.day = this.curDay;
        this.render();
    }

    daysInMonth(month, year) {
        return DAYS_IN_MONTH[month] + (month === 2 && isLeapYear(year) ? 1 : 0);
    }

    render() {
        this.captionView.setText(` ${MONTH_NAMES[this.month].padEnd(14, " ")}${String(this.year).padStart(4, " ")}`);
        const mondayIndex = (dayOfWeek(1, this.month, this.year) + 6) % 7;
        const first = 1 - mondayIndex;
        const days = this.daysInMonth(this.month, this.year);
        const today = this.year === this.curYear && this.month === this.curMonth ? this.curDay : 0;
        this.gridView.setMonth(first, days, today, this.day);
    }
}

class TVColorSelector extends TVGroup {
    constructor(bounds, colorCount = 16) {
        super(bounds);
        this.colorCount = colorCount === 8 ? 8 : 16;
        const background = this.colorCount === 8;
        this.background = background;
        this.buttons = Array.from({ length: this.colorCount }, (_unused, index) => {
            const button = new TVColorCellButton(new TVRect(), "", "color-index", bfNormal).setValue(index);
            button.setCommandData({ selected: index === 0, color: DOS_COLORS[index] });
            return button;
        });
        this.insertAll(this.buttons);
        this.selected = 0;
    }

    _semanticName() { return this.background ? "colors-background" : "colors-foreground"; }

    nextColor(key) {
        const maxColor = this.colorCount - 1;
        let color = this.selected;
        if (key === "ArrowLeft") { color = color > 0 ? color - 1 : maxColor; }
        else if (key === "ArrowRight") { color = color < maxColor ? color + 1 : 0; }
        else if (key === "ArrowUp") {
            color = color > 3 ? color - 4 : (color === 0 ? maxColor : color + maxColor - 4);
        } else if (key === "ArrowDown") {
            color = color < maxColor - 3 ? color + 4 : (color === maxColor ? 0 : color - maxColor + 4);
        } else { return -1; }
        return color;
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what !== evKeyDown || event.infoPtr?.owner !== this) { return; }
        const color = this.nextColor(event.nativeEvent?.key);
        if (color < 0) { return; }
        event.nativeEvent.preventDefault();
        event.nativeEvent.stopPropagation();
        this.select(color, true);
        event.what = evCommand;
        event.command = "color-index";
        event.infoPtr = this.buttons[color];
    }

    select(index, focus = false) {
        if (!Number.isInteger(index) || index < 0 || index >= this.buttons.length) { return; }
        this.selected = index;
        this.buttons.forEach((button, color) => {
            const selected = color === index;
            button.commandData.selected = selected;
            if (button.root) {
                button.drawView();
            }
        });
        if (focus) { this.buttons[index].root?.focus(); }
    }

    buttonAt(index) {
        return this.buttons[index] || null;
    }
}

class TVColorDisplay extends TVGroup {
    static viewName = "colors-display";

    constructor(bounds) {
        super(bounds);
        const sample = new TVStaticText(
            new TVRect(0, 0, bounds.width, bounds.height),
            "Text Text Text \nText Text Text ",
        );
        this.insert(sample);
    }

    setColors(foreground, background) {
        this.root?.style.setProperty("--tv-colors-sample-fg", foreground);
        this.root?.style.setProperty("--tv-colors-sample-bg", background);
    }
}

class TVColorGroupList extends TVListBox {
    static viewName = "colors-groups";

    defaultContent(item) { return escapeHtml(item?.name || ""); }
}

class TVColorItemList extends TVListBox {
    static viewName = "colors-items";

    defaultContent(item) { return escapeHtml(item?.name || ""); }
}

class TVColorsDialog extends TVDialog {
    static viewName = "colors";

    constructor() {
        const groupBox = new TVColorGroupList(new TVRect(2, 2, 18, 13));
        const itemBox = new TVColorItemList(new TVRect(20, 2, 41, 13));
        const foregroundView = new TVColorSelector(new TVRect(44, 2, 56, 6), 16);
        const backgroundView = new TVColorSelector(new TVRect(44, 8, 56, 10), 8);
        const displayView = new TVColorDisplay(new TVRect(43, 11, 57, 13));
        const okButton = new TVButton(new TVRect(31, 14, 41, 16), 'O~K~', "colors-ok", bfDefault);
        const cancelButton = new TVButton(new TVRect(43, 14, 55, 16), '~C~ancel', "colors-cancel", bfNormal);
        const resetAllButton = new TVButton(new TVRect(17, 14, 29, 16), '~R~eset All', "colors-reset-all", bfNormal);
        const defaultButton = new TVButton(new TVRect(5, 14, 15, 16), '~D~efault', "colors-default", bfNormal);
        const groupTitle = new TVLabel(new TVRect(1, 1, 7, 2), "~G~roup", groupBox);
        const itemTitle = new TVLabel(new TVRect(19, 1, 24, 2), "~I~tem", itemBox);
        const fgTitle = new TVLabel(new TVRect(44, 1, 56, 2), "~F~oreground", foregroundView);
        const bgTitle = new TVLabel(new TVRect(44, 7, 56, 8), "~B~ackground", backgroundView);
        const colorsMain = new TVGroup(new TVRect(0, 0, 59, 16)).insertAll([
                groupTitle,
                groupBox,
                itemTitle,
                itemBox,
                fgTitle,
                foregroundView,
                bgTitle,
                backgroundView,
                displayView,
                defaultButton,
                resetAllButton,
                okButton,
                cancelButton,
            ]);
        super(new TVRect(0, 0, 61, 18), "Colors");
        this.setHelpCtx(hcColors);
        this.insert(colorsMain);
        this.foregroundView = foregroundView;
        this.backgroundView = backgroundView;
        this.displayView = displayView;
        this.okButton = okButton;
        this.cancelButton = cancelButton;
        this.defaultButton = defaultButton;
        this.resetAllButton = resetAllButton;
        this.groupBox = groupBox;
        this.itemBox = itemBox;
        this.selectedGroup = 0;
        this.pendingPalette = cloneColorPalette(TV.getActiveColorPalette() || buildDefaultColorPalette());
        this.previousPalette = cloneColorPalette(this.pendingPalette);
        this.bindCommonClose(() => this.cancel());
        this.bindDrag();
        this.bind();
        this.renderGroups();
        this.renderItems();
        this.renderSelectors();
        this.renderDisplay();
    }

    bind() {
        this.groupBox.bind({
            onSelect: (_group, index) => this.onGroupSelect(index),
        });
        this.itemBox.bind({
            onSelect: (_item, index) => this.onItemSelect(index),
        });
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand) {
            if (event.command === "colors-ok") { this.confirm(); }
            else if (event.command === "colors-cancel") { this.cancel(); }
            else if (event.command === "colors-default") { this.restoreSelectedDefault(); }
            else if (event.command === "colors-reset-all") { this.resetAllColors(); }
            else if (event.command === "color-index") {
                const selector = event.infoPtr?.owner;
                if (selector === this.foregroundView || selector === this.backgroundView) {
                    this.selectColor(selector, Number(event.infoPtr.value));
                    if (event.nativeEvent?.type === "keydown") {
                        selector.select(Number(event.infoPtr.value), true);
                    }
                }
            }
            else { return; }
            this.clearEvent(event);
        }
    }

    open() {
        this.previousPalette = cloneColorPalette(TV.getActiveColorPalette() || buildDefaultColorPalette());
        this.pendingPalette = cloneColorPalette(this.previousPalette);
        this.renderGroups();
        this.renderItems();
        this.renderSelectors();
        this.renderDisplay();
        super.open();
        window.requestAnimationFrame(() => {
            this.groupBox.updateScrollbar();
            this.itemBox.updateScrollbar();
            this.groupBox.selectedElement()?.focus();
        });
    }

    onGroupSelect(index) {
        if (!Number.isInteger(index) || index < 0 || index >= COLOR_GROUPS.length) {
            return;
        }
        this.selectedGroup = index;
        this.renderGroups();
        this.renderItems();
        this.renderSelectors();
        this.renderDisplay();
    }

    onItemSelect(index) {
        const group = this.pendingPalette[this.selectedGroup];
        if (!group || !Number.isInteger(index) || index < 0 || index >= group.items.length) {
            return;
        }
        group.index = index;
        this.renderItems();
        this.renderSelectors();
        this.renderDisplay();
    }

    selectColor(selector, colorIndex) {
        if (!Number.isInteger(colorIndex)) { return; }
        const group = this.pendingPalette[this.selectedGroup];
        if (!group) { return; }
        const item = group.items[group.index] || group.items[0];
        if (!item) { return; }
        let attr;
        if (selector === this.foregroundView) {
            attr = (item.attr & 0xF0) | (colorIndex & 0x0F);
        } else {
            attr = ((colorIndex & 0x0F) << 4) | (item.attr & 0x0F);
        }
        setColorPaletteAttribute(this.pendingPalette, item.paletteIndex, attr);
        applyColorPalette(this.pendingPalette, false);
        this.renderItems();
        this.renderSelectors();
        this.renderDisplay();
    }

    selectedItem() {
        const group = this.pendingPalette[this.selectedGroup];
        return group ? (group.items[group.index] || group.items[0]) : null;
    }

    confirm() {
        applyColorPalette(this.pendingPalette, true);
        this.close();
    }

    cancel() {
        applyColorPalette(this.previousPalette, false);
        this.close();
    }

    restoreSelectedDefault() {
        const group = this.pendingPalette[this.selectedGroup];
        const item = group?.items[group.index];
        const defaultItem = buildDefaultColorPalette()[this.selectedGroup]?.items[group?.index];
        if (!item || !defaultItem) {
            return;
        }
        setColorPaletteAttribute(this.pendingPalette, item.paletteIndex, defaultItem.attr);
        applyColorPalette(this.pendingPalette, false);
        this.renderGroups();
        this.renderItems();
        this.renderSelectors();
        this.renderDisplay();
    }

    resetAllColors() {
        const groupIndexes = this.pendingPalette.map((group) => group.index);
        this.pendingPalette = buildDefaultColorPalette();
        this.pendingPalette.forEach((group, index) => {
            const previousIndex = groupIndexes[index];
            if (Number.isInteger(previousIndex) && previousIndex >= 0 && previousIndex < group.items.length) {
                group.index = previousIndex;
            }
        });
        applyColorPalette(this.pendingPalette, false);
        this.renderGroups();
        this.renderItems();
        this.renderSelectors();
        this.renderDisplay();
    }

    renderGroups() {
        this.groupBox.setItems(this.pendingPalette, this.selectedGroup);
    }

    renderItems() {
        if (!this.itemBox.root) {
            return;
        }
        const group = this.pendingPalette[this.selectedGroup];
        this.itemBox.setItems(group.items, group.index);
    }

    renderSelectors() {
        const item = this.selectedItem();
        if (!item) {
            return;
        }
        const fg = item.attr & 0x0F;
        const bg = (item.attr >> 4) & 0x0F;
        this.foregroundView.select(fg);
        this.backgroundView.select(bg);
    }

    renderDisplay() {
        const item = this.selectedItem();
        if (!item) {
            return;
        }
        const fg = dosColor(item.attr, 0);
        const bg = dosColor(item.attr, 4);
        this.displayView.setColors(fg, bg);
    }
}

const MIDI_DEFAULT_TEMPO_US = 500000;

function midiReadString(view, state, length) {
    let text = "";
    for (let index = 0; index < length; index += 1) {
        text += String.fromCharCode(view.getUint8(state.offset));
        state.offset += 1;
    }
    return text;
}

function midiReadU8(view, state) {
    if (state.offset >= view.byteLength) {
        throw new Error("Unexpected end of MIDI data.");
    }
    const value = view.getUint8(state.offset);
    state.offset += 1;
    return value;
}

function midiReadU16(view, state) {
    if (state.offset + 2 > view.byteLength) {
        throw new Error("Unexpected end of MIDI data.");
    }
    const value = view.getUint16(state.offset, false);
    state.offset += 2;
    return value;
}

function midiReadU32(view, state) {
    if (state.offset + 4 > view.byteLength) {
        throw new Error("Unexpected end of MIDI data.");
    }
    const value = view.getUint32(state.offset, false);
    state.offset += 4;
    return value;
}

function midiReadVariableLength(view, state, limit) {
    let value = 0;
    for (let count = 0; count < 4; count += 1) {
        if (state.offset >= limit) {
            throw new Error("Unexpected end of MIDI variable length value.");
        }
        const byte = midiReadU8(view, state);
        value = (value << 7) | (byte & 0x7F);
        if ((byte & 0x80) === 0) {
            return value;
        }
    }
    throw new Error("MIDI variable length value is too long.");
}

function midiEventDataLength(status) {
    const type = status & 0xF0;
    return type === 0xC0 || type === 0xD0 ? 1 : 2;
}

function parseMidiFile(arrayBuffer) {
    const view = new DataView(arrayBuffer);
    const state = { offset: 0 };
    if (midiReadString(view, state, 4) !== "MThd") {
        throw new Error("MIDI header not found.");
    }
    const headerLength = midiReadU32(view, state);
    const headerEnd = state.offset + headerLength;
    const format = midiReadU16(view, state);
    const trackCount = midiReadU16(view, state);
    const division = midiReadU16(view, state);
    state.offset = headerEnd;
    if ((division & 0x8000) !== 0) {
        throw new Error("SMPTE MIDI timing is not supported.");
    }
    if (format > 1) {
        throw new Error(`Unsupported MIDI format ${format}.`);
    }
    const ticksPerBeat = division || 384;
    const events = [];
    let maxTick = 0;

    for (let trackIndex = 0; trackIndex < trackCount; trackIndex += 1) {
        if (midiReadString(view, state, 4) !== "MTrk") {
            throw new Error("MIDI track chunk not found.");
        }
        const trackLength = midiReadU32(view, state);
        const trackEnd = state.offset + trackLength;
        let tick = 0;
        let runningStatus = 0;

        while (state.offset < trackEnd) {
            const delta = midiReadVariableLength(view, state, trackEnd);
            tick += delta;
            maxTick = Math.max(maxTick, tick);
            let status = midiReadU8(view, state);
            if (status < 0x80) {
                if (!runningStatus) {
                    throw new Error("MIDI running status without previous status.");
                }
                state.offset -= 1;
                status = runningStatus;
            } else if (status < 0xF0) {
                runningStatus = status;
            } else {
                runningStatus = 0;
            }

            if (status === 0xFF) {
                const metaType = midiReadU8(view, state);
                const length = midiReadVariableLength(view, state, trackEnd);
                if (metaType === 0x51 && length >= 3) {
                    const tempo = (view.getUint8(state.offset) << 16)
                        | (view.getUint8(state.offset + 1) << 8)
                        | view.getUint8(state.offset + 2);
                    events.push({ type: "tempo", tick, tempo });
                }
                state.offset += length;
                if (metaType === 0x2F) {
                    state.offset = trackEnd;
                }
                continue;
            }

            if (status === 0xF0 || status === 0xF7) {
                const length = midiReadVariableLength(view, state, trackEnd);
                state.offset += length;
                continue;
            }

            const channel = status & 0x0F;
            const eventType = status & 0xF0;
            const dataLength = midiEventDataLength(status);
            const note = midiReadU8(view, state);
            const value = dataLength === 2 ? midiReadU8(view, state) : 0;
            if (eventType === 0x90 && value > 0) {
                events.push({ type: "noteOn", tick, channel, note, velocity: value });
            } else if (eventType === 0x80 || (eventType === 0x90 && value === 0)) {
                events.push({ type: "noteOff", tick, channel, note });
            }
        }
        state.offset = trackEnd;
    }

    events.sort((left, right) => {
        if (left.tick !== right.tick) {
            return left.tick - right.tick;
        }
        if (left.type === right.type) {
            return 0;
        }
        return left.type === "tempo" ? -1 : 1;
    });

    let tempo = MIDI_DEFAULT_TEMPO_US;
    let lastTick = 0;
    let seconds = 0;
    for (const event of events) {
        seconds += ((event.tick - lastTick) * tempo) / ticksPerBeat / 1000000;
        event.time = seconds;
        lastTick = event.tick;
        if (event.type === "tempo") {
            tempo = event.tempo || tempo;
        }
    }

    const activeNotes = new Map();
    const notes = [];
    for (const event of events) {
        if (event.type === "noteOn") {
            const key = `${event.channel}:${event.note}`;
            const pending = activeNotes.get(key) || [];
            pending.push(event);
            activeNotes.set(key, pending);
        } else if (event.type === "noteOff") {
            const key = `${event.channel}:${event.note}`;
            const pending = activeNotes.get(key);
            if (!pending || !pending.length) {
                continue;
            }
            const start = pending.shift();
            if (!pending.length) {
                activeNotes.delete(key);
            }
            notes.push({
                time: start.time,
                duration: Math.max(0.04, event.time - start.time),
                midi: start.note,
                velocity: start.velocity,
                channel: start.channel,
            });
        }
    }

    for (const pending of activeNotes.values()) {
        for (const start of pending) {
            notes.push({
                time: start.time,
                duration: 0.4,
                midi: start.note,
                velocity: start.velocity,
                channel: start.channel,
            });
        }
    }

    notes.sort((left, right) => left.time - right.time || left.midi - right.midi);
    const duration = notes.reduce((max, note) => Math.max(max, note.time + note.duration), seconds);
    if (!notes.length) {
        throw new Error("No playable MIDI notes found.");
    }
    return {
        format,
        trackCount,
        ticksPerBeat,
        maxTick,
        notes,
        duration,
    };
}

function formatMidiTime(seconds) {
    const safeSeconds = Math.max(0, Math.floor(seconds || 0));
    const minutes = Math.floor(safeSeconds / 60);
    const rest = String(safeSeconds % 60).padStart(2, "0");
    return `${minutes}:${rest}`;
}

class TVMidiSynth {
    constructor() {
        this.context = null;
        this.synth = null;
        this.audioNode = null;
        this.initPromise = null;
        this.progressTimer = null;
        this.totalTicks = 0;
        this.generation = 0;
        this.sequence = null;
        this.paused = false;
        this.onProgress = null;
        this.onDone = null;
        this.loadingTimes = {};
    }

    static loadScript(url) {
        return new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = url;
            script.onload = resolve;
            script.onerror = () => reject(new Error(`Cannot load MIDI synthesizer: ${url}`));
            document.head.appendChild(script);
        });
    }

    static loadAssets() {
        if (!this.assetsPromise) {
            this.assetsPromise = (async () => {
                const base = "/assets/midi/synth/";
                const scriptsStarted = performance.now();
                await this.loadScript(`${base}libfluidsynth-2.4.6-with-libsndfile.js`);
                await this.loadScript(`${base}js-synthesizer.min.js`);
                await window.JSSynth.waitForReady();
                const scriptsMs = performance.now() - scriptsStarted;
                const soundfontStarted = performance.now();
                const response = await fetch(`${base}FluidR3Mono_GM.sf3?v=2aacd036d705`);
                if (!response.ok) { throw new Error(`Cannot load MIDI SoundFont (HTTP ${response.status}).`); }
                const soundFont = await response.arrayBuffer();
                this.assetTiming = {
                    scriptsMs,
                    soundfontFetchMs: performance.now() - soundfontStarted,
                    soundfontBytes: soundFont.byteLength,
                };
                return soundFont;
            })().catch((error) => {
                this.assetsPromise = null;
                throw error;
            });
        }
        return this.assetsPromise;
    }

    async ensureContext() {
        const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
        if (!AudioContextCtor) {
            throw new Error("Web Audio is not available in this browser.");
        }
        if (!this.context) {
            this.context = new AudioContextCtor();
        }
        if (this.context.state === "suspended") {
            await this.context.resume();
        }
        if (!this.initPromise) {
            this.initPromise = (async () => {
                const soundFont = await TVMidiSynth.loadAssets();
                const synthStarted = performance.now();
                const synth = new window.JSSynth.Synthesizer();
                synth.init(this.context.sampleRate);
                const audioNode = synth.createAudioNode(this.context, 4096);
                audioNode.connect(this.context.destination);
                try {
                    const soundfontStarted = performance.now();
                    await synth.loadSFont(soundFont);
                    this.loadingTimes = {
                        ...TVMidiSynth.assetTiming,
                        synthInitMs: performance.now() - synthStarted,
                        soundfontLoadMs: performance.now() - soundfontStarted,
                    };
                } catch (error) {
                    audioNode.disconnect();
                    synth.close();
                    throw error;
                }
                this.synth = synth;
                this.audioNode = audioNode;
                return synth;
            })().catch((error) => {
                this.initPromise = null;
                throw error;
            });
        }
        return this.initPromise;
    }

    async play(sequence, onProgress, onDone, offset = 0) {
        this.stop(false);
        const generation = this.generation;
        const synth = await this.ensureContext();
        if (generation !== this.generation) { return false; }
        await synth.resetPlayer();
        await synth.addSMFDataToPlayer(sequence.data);
        if (generation !== this.generation) { return false; }
        await synth.playPlayer();
        // FluidSynth can report zero total ticks just after playback starts.
        // The parser has already read the final tick from every MIDI track.
        this.totalTicks = Math.max(1, sequence.maxTick || synth.getPlayerTotalTicks());
        if (offset > 0) {
            const ratio = Math.min(1, offset / sequence.duration);
            synth.seekPlayer(Math.min(this.totalTicks - 1, Math.floor(this.totalTicks * ratio)));
        }
        this.sequence = sequence;
        this.onProgress = onProgress;
        this.onDone = onDone;
        this.progressTimer = window.setInterval(() => this.reportProgress(), 150);
        this.reportProgress();
        return true;
    }

    async seekTo(ratio) {
        if (!this.sequence) { return false; }
        const tick = Math.floor(this.totalTicks * Math.max(0, Math.min(1, ratio)));
        this.synth.seekPlayer(Math.min(this.totalTicks - 1, tick));
        this.reportProgress();
        return true;
    }

    reportProgress() {
        if (!this.synth || !this.sequence || this.paused) { return; }
        const ratio = Math.max(0, Math.min(1, this.synth.getPlayerCurrentTick() / this.totalTicks));
        this.onProgress?.(ratio * this.sequence.duration, this.sequence.duration);
        if (!this.synth.isPlayerPlaying()) { this.finish(); }
    }

    finish() {
        const onDone = this.onDone;
        const sequence = this.sequence;
        this.stop(false);
        if (onDone) {
            onDone(sequence);
        }
    }

    pause() {
        if (!this.sequence) { return null; }
        const ratio = Math.max(0, Math.min(1, this.synth.getPlayerCurrentTick() / this.totalTicks));
        const position = { ratio, elapsed: ratio * this.sequence.duration, duration: this.sequence.duration };
        if (this.progressTimer !== null) {
            window.clearInterval(this.progressTimer);
            this.progressTimer = null;
        }
        this.synth.stopPlayer();
        this.paused = true;
        return position;
    }

    async resume() {
        if (!this.paused || !this.sequence) { return false; }
        const synth = await this.ensureContext();
        await synth.playPlayer();
        this.paused = false;
        this.progressTimer = window.setInterval(() => this.reportProgress(), 150);
        this.reportProgress();
        return true;
    }

    stop(report = true) {
        this.generation += 1;
        this.paused = false;
        if (this.progressTimer !== null) {
            window.clearInterval(this.progressTimer);
            this.progressTimer = null;
        }
        this.synth?.stopPlayer();
        const progress = this.onProgress;
        this.sequence = null;
        this.totalTicks = 0;
        this.onProgress = null;
        this.onDone = null;
        if (report && progress) {
            progress(0, 0);
        }
    }
}

class TVMidiTrackList extends TVListBox {
    static viewName = "midi-track-list";

    itemMarkup(track, index) {
        return new TVMidiTrackButton(new TVRect(), "", "midi-track", bfNormal)
            .setValue(index)
            .setCommandData({
                listIndex: index,
                selected: index === this.selectedIndex,
                index,
                title: track.title,
                credit: track.credit,
                available: track.available,
            })
            .draw();
    }
}

class TVMidiDisplay extends TVGroup {
    static viewName = "midi-display";

    constructor(bounds) {
        super(bounds);
        this.trackLabelView = new TVStaticText(new TVRect(0, 0, 6, 1), "Track");
        this.trackNumberView = new TVStaticText(new TVRect(6, 0, 10, 1), "01");
        this.timeView = new TVStaticText(new TVRect(20, 0, 40, 1), "0:00 / 0:00");
        this.titleView = new TVStaticText(new TVRect(0, 1, 40, 2), "");
        this.statusView = new TVStaticText(new TVRect(0, 2, 40, 3), "Ready.");
        this.insertAll([
            this.trackLabelView,
            this.trackNumberView,
            this.timeView,
            this.titleView,
            this.statusView,
        ]);
    }

    resolve(root) {
        super.resolve(root);
        for (const [view, part] of [
            [this.trackLabelView, "label"],
            [this.trackNumberView, "number"],
            [this.timeView, "time"],
            [this.titleView, "title"],
            [this.statusView, "status"],
        ]) {
            view.root?.setAttribute("data-tv-midi-part", part);
        }
        return this;
    }

    setTrack(track, number) {
        this.trackNumberView.setText(number);
        this.titleView.setText(track.title);
        this.timeView.setText("0:00 / 0:00");
    }

    setTime(elapsed, duration) {
        this.timeView.setText(`${formatMidiTime(elapsed)} / ${formatMidiTime(duration)}`);
    }

    setStatus(message) {
        this.statusView.setText(message);
    }
}

class TVMidiPlayerDialog extends TVDialog {
    static viewName = "midi";

    constructor() {
        const previousButton = new TVMidiControlButton(new TVRect(1, 6, 9, 8), "◄◄", "midi-previous", bfNormal);
        const playButton = new TVButton(new TVRect(10, 6, 17, 8), "►", "midi-play", bfDefault);
        const pauseButton = new TVMidiControlButton(new TVRect(18, 6, 25, 8), "▌▌", "midi-pause", bfNormal);
        const stopButton = new TVButton(new TVRect(26, 6, 33, 8), "■", "midi-stop", bfNormal);
        const nextButton = new TVMidiControlButton(new TVRect(34, 6, 41, 8), "►►", "midi-next", bfNormal);
        const moreButton = new TVMidiControlButton(new TVRect(42, 6, 52, 8), "~M~ore", "midi-more", bfNormal)
            .setCommandData({ expanded: false });
        const filterInput = new TVInputLine(new TVRect(8, 1, 48, 2), 255);
        const filterLabel = new TVLabel(new TVRect(0, 1, 8, 2), "~F~ilter:", filterInput);
        const filterHistory = new TVHistory(new TVRect(48, 1, 51, 2), filterInput, "thelp:midi-filter-history");
        const filterHistoryPopup = new TVHistoryWindow(new TVRect(0, 0, 32, 6), "midi-filter");
        const randomNext = new TVCheckBoxes(new TVRect(0, 3, 51, 4), [
            { label: "~R~andom next track" },
        ]);
        const cover = new TVImage(new TVRect(1, 0, 11, 5));
        const display = new TVMidiDisplay(new TVRect(12, 0, 52, 3));
        const meter = new TVBarGauge(new TVRect(12, 4, 52, 5), 100);
        const advanced = new TVGroup(new TVRect(1, 16, 52, 21)).insertAll([
            filterLabel,
            filterInput,
            filterHistory,
            randomNext,
            filterHistoryPopup,
        ]);
        advanced.setState(sfVisible, false);
        const trackList = new TVMidiTrackList(new TVRect(1, 8, 52, 16));
        trackList.setState(sfVisible, false);
        const main = new TVGroup(new TVRect(0, 0, 53, 8)).insertAll([
            cover,
            display,
            meter,
            previousButton,
            playButton,
            pauseButton,
            stopButton,
            nextButton,
            moreButton,
            trackList,
            advanced,
        ]);
        super(new TVRect(0, 0, 55, 10), "CD/MIDI Player");
        this.setHelpCtx(hcMidiPlayer);
        this.insert(main);
        this.selectedIndex = -1;
        this.tracks = [];
        this.allTracks = [];
        this.pendingPlay = null;
        this.catalogTimer = null;
        this.catalogPending = false;
        this.lastCatalog = null;
        this.downloadProgress = null;
        this.downloadDismissed = false;
        this.downloadCloseTimer = null;
        this.cache = new Map();
        this.loadSerial = 0;
        this.isPlaying = false;
        this.isLoading = false;
        this.activeTrackFile = null;
        this.pausedPosition = null;
        this.playbackStats = null;
        this.onPlaybackEvent = null;
        this.synth = new TVMidiSynth();
        this.displayView = display;
        this.coverView = cover;
        this.meter = meter;
        this.previousButton = previousButton;
        this.playButton = playButton;
        this.pauseButton = pauseButton;
        this.stopButton = stopButton;
        this.nextButton = nextButton;
        this.moreButton = moreButton;
        this.mainView = main;
        this.advancedView = advanced;
        this.filterInput = filterInput;
        this.filterHistory = filterHistory;
        this.filterHistoryPopup = filterHistoryPopup;
        this.historyWindow = filterHistory.bindWindow(
            filterHistoryPopup,
            () => filterHistory.keys().map((value) => ({ historyKey: value, value })),
            (item) => {
                this.filterInput.setData(item.value);
                this.applyFilter();
                this.historyWindow.hide();
                this.filterInput.focus();
            },
        );
        this.randomNext = randomNext;
        this.trackListBox = trackList;
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bind();
        this.trackListBox.setItems([], -1);
        this.updateDisplay();
    }

    bind() {
        this.trackListBox.bind({
            onSelect: (_track, index, nativeEvent) => {
                this.selectTrack(index);
                if (nativeEvent?.type === "click") { void this.playSelected(); }
            },
            onActivate: (_track, index, nativeEvent) => {
                if (nativeEvent?.type === "dblclick") { return; }
                this.selectTrack(index);
                void this.playSelected();
            },
        });
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evKeyDown && this.historyWindow.handleEscape(event.nativeEvent)) {
            this.clearEvent(event);
            return;
        }
        if (event.what === evMouseDown && event.infoPtr === this.meter
                && event.nativeEvent?.type === "click") {
            const bounds = this.meter.root?.getBoundingClientRect();
            if (bounds?.width && this.synth.sequence) {
                const ratio = Math.max(0, Math.min(1, (event.nativeEvent.clientX - bounds.left) / bounds.width));
                void this.seekTo(ratio);
            }
            this.clearEvent(event);
        } else if (event.what === evCommand) {
            if (event.command === "midi-previous") { this.previousTrack(); }
            else if (event.command === "midi-play") { void this.playSelected(); }
            else if (event.command === "midi-pause") { this.pausePlayback(); }
            else if (event.command === "midi-stop") { this.stopPlayback(); }
            else if (event.command === "midi-next") { this.nextTrack(); }
            else if (event.command === "midi-more") { this.toggleAdvanced(); }
            else { return; }
            this.clearEvent(event);
        } else if (event.what === evBroadcast && event.infoPtr === this.filterInput
                && event.nativeEvent?.type === "input") {
            this.applyFilter();
            this.clearEvent(event);
        } else if (event.what === evKeyDown && event.infoPtr === this.filterInput
                && event.nativeEvent?.key === "Enter") {
            this.rememberFilter();
            this.clearEvent(event);
        }
    }

    rememberFilter() {
        this.filterHistory.remember(this.filterInput.getData().trim());
        this.historyWindow.refresh();
    }

    close() {
        this.rememberFilter();
        this.historyWindow.hide();
        if (this.catalogTimer) { clearTimeout(this.catalogTimer); }
        this.catalogTimer = null;
        this.pendingPlay = null;
        this.clearDownloadProgress();
        this.stopPlayback();
        super.close();
    }

    open() {
        this.historyWindow.hide();
        this.downloadDismissed = false;
        super.open();
        // Start fetching the large SoundFont while the player is being browsed.
        // Playback still resumes Web Audio from the user's Play/click gesture.
        void TVMidiSynth.loadAssets().catch((error) => {
            if (this.isOpen()) { this.setStatus(`MIDI synthesizer preload failed: ${error.message}`); }
        });
        void this.refreshCatalog();
    }

    applyFilter() {
        const selectedId = this.selectedTrack()?.id;
        const query = this.filterInput.getData().trim().toLocaleLowerCase();
        this.tracks = this.allTracks.filter((track) => !query || [
            track.game, track.title, track.sequencer,
        ].some((value) => String(value || "").toLocaleLowerCase().includes(query)));
        const remembered = this.tracks.findIndex((track) => track.id === selectedId);
        this.selectedIndex = remembered >= 0 ? remembered : (this.tracks.length ? 0 : -1);
        const scrollTop = this.trackListBox.scrollViewport?.scrollTop || 0;
        this.trackListBox.setItems(this.tracks, this.selectedIndex);
        if (this.trackListBox.scrollViewport) { this.trackListBox.scrollViewport.scrollTop = scrollTop; }
        if (!this.isPlaying) {
            if (!this.pausedPosition || this.pausedPosition.file !== this.selectedTrack()?.file) {
                this.pausedPosition = null;
                this.updateDisplay();
            }
        }
    }

    showDownloadProgress(status) {
        if (this.downloadDismissed || !(this.owner instanceof TV.TVDesktop)) { return; }
        if (this.downloadCloseTimer) { clearTimeout(this.downloadCloseTimer); this.downloadCloseTimer = null; }
        if (!this.downloadProgress || this.downloadProgress.destroyed) {
            this.downloadProgress = new TVMidiDownloadProgressDialog();
            this.downloadProgress.onHide = () => { this.downloadDismissed = true; };
            this.owner.insert(this.downloadProgress);
        }
        this.downloadProgress.update(status);
        if (!this.downloadProgress.isOpen()) { this.downloadProgress.open(); }
    }

    clearDownloadProgress() {
        if (this.downloadCloseTimer) { clearTimeout(this.downloadCloseTimer); }
        this.downloadCloseTimer = null;
        this.downloadProgress?.destroy();
        this.downloadProgress = null;
    }

    async refreshCatalog() {
        if (!this.isOpen() || this.catalogPending) { return; }
        this.catalogPending = true;
        try {
            const response = await fetch("/api/midi/catalog", { cache: "no-store" });
            if (!response.ok) { throw new Error(`HTTP ${response.status}`); }
            const catalog = await response.json();
            if (!this.isOpen()) { return; }
            this.lastCatalog = catalog;
            const tracks = Array.isArray(catalog.tracks) ? catalog.tracks : [];
            if (tracks.length !== this.allTracks.length || tracks.some((track, index) =>
                track.id !== this.allTracks[index]?.id || track.available !== this.allTracks[index]?.available
                || track.cover !== this.allTracks[index]?.cover)) {
                this.allTracks = tracks;
                this.applyFilter();
            }
            if (!this.isPlaying && !this.pausedPosition) {
                if (catalog.state === "downloading") {
                    this.setStatus(`Downloading game MIDI: ${catalog.downloaded}/${catalog.total}...`);
                } else if (catalog.state === "error" || catalog.state === "partial") {
                    this.setStatus(catalog.errors?.[0] || "Some MIDI downloads failed; restart to retry.");
                } else {
                    this.setStatus(tracks.length ? `${catalog.downloaded} game MIDI tracks ready.` : "No game MIDI tracks available.");
                }
            }
            if (catalog.state === "downloading") {
                this.showDownloadProgress(catalog);
            } else if (this.downloadProgress && !this.downloadCloseTimer) {
                this.downloadProgress.update(catalog);
                this.downloadCloseTimer = setTimeout(() => { this.clearDownloadProgress(); }, 650);
            }
            if (this.pendingPlay) {
                const wanted = this.pendingPlay;
                const ready = tracks.find((track) => track.id === wanted.id && track.available)
                    || tracks.find((track) => track.item_id === wanted.itemId && track.available);
                if (ready) {
                    this.pendingPlay = null;
                    const index = this.tracks.findIndex((track) => track.id === ready.id);
                    if (index >= 0) { this.selectTrack(index); }
                    void this.playTrack(ready, index >= 0 ? String(index + 1).padStart(2, "0") : "--");
                }
            }
            if (catalog.state === "downloading") {
                this.catalogTimer = setTimeout(() => { void this.refreshCatalog(); }, this.pendingPlay ? 1000 : 3000);
            }
        } catch (error) {
            if (this.isOpen()) {
                this.setStatus(`MIDI catalog unavailable: ${error.message}`);
                this.catalogTimer = setTimeout(() => {
                    this.catalogTimer = null;
                    void this.refreshCatalog();
                }, 3000);
            }
        } finally {
            this.catalogPending = false;
        }
    }

    toggleAdvanced(expanded = !this.advancedView.getState(sfVisible)) {
        expanded = Boolean(expanded);
        this.trackListBox.setState(sfVisible, expanded);
        this.advancedView.setState(sfVisible, expanded);
        this.mainView.changeBounds(new TVRect(0, 0, 53, expanded ? 21 : 8));
        this.moreButton.commandData.expanded = expanded;
        this.moreButton.root?.setAttribute("aria-expanded", expanded ? "true" : "false");
        this.moreButton.setTitle(expanded ? "~L~ess" : "~M~ore");
        this.locate(new TVRect(0, 0, 55, expanded ? 23 : 10));
        this.trackListBox.updateScrollbar();
    }

    captureUrlState() {
        return { expanded: this.advancedView.getState(sfVisible), random: Boolean(this.randomNext.getData() & 1) };
    }

    restoreUrlState(state) {
        this.toggleAdvanced(Boolean(state?.expanded));
        this.randomNext.setData(state?.random ? 1 : 0);
    }

    selectTrack(index) {
        if (!Number.isInteger(index) || index < 0 || index >= this.tracks.length) {
            return;
        }
        if (this.pausedPosition?.file !== this.tracks[index].file) { this.pausedPosition = null; }
        this.selectedIndex = index;
        if (this.trackListBox.selectedIndex !== index) { this.trackListBox.select(index); }
        if (!this.pausedPosition) { this.updateDisplay(); }
    }

    previousTrack() {
        if (!this.tracks.length) { return; }
        const nextIndex = (this.selectedIndex - 1 + this.tracks.length) % this.tracks.length;
        this.selectTrack(nextIndex);
        if (this.isPlaying || this.isLoading) {
            this.playSelected();
        }
    }

    nextTrack(autoplay = this.isPlaying || this.isLoading) {
        if (!this.tracks.length) { return; }
        const nextIndex = this.randomNext.getData() & 1 && this.tracks.length > 1
            ? (this.selectedIndex + 1 + Math.floor(Math.random() * (this.tracks.length - 1))) % this.tracks.length
            : (this.selectedIndex + 1) % this.tracks.length;
        this.selectTrack(nextIndex);
        if (autoplay) { void this.playSelected(); }
    }

    selectedTrack() {
        return this.tracks[this.selectedIndex] || null;
    }

    updateDisplay() {
        const track = this.selectedTrack();
        this.updateTrackDisplay(track || { title: "Waiting for game MIDI catalog..." },
            track ? String(this.selectedIndex + 1).padStart(2, "0") : "--");
        this.updateProgress(0, 0, { status: false });
    }

    updateTrackDisplay(track, number) {
        this.displayView.setTrack({
            ...track,
            title: track.game ? `${track.game}: ${track.title}` : track.title,
        }, number);
        this.coverView.setImage(track.cover || "", track.game ? `${track.game} cover` : "");
    }

    async loadTrack(track) {
        if (this.cache.has(track.file)) {
            return this.cache.get(track.file);
        }
        const response = await fetch(track.file);
        if (!response.ok) {
            throw new Error(`Cannot load ${track.file} (${response.status}).`);
        }
        const data = await response.arrayBuffer();
        const sequence = { ...parseMidiFile(data), data };
        this.cache.set(track.file, sequence);
        if (this.cache.size > 24) { this.cache.delete(this.cache.keys().next().value); }
        return sequence;
    }

    async playSelected() {
        this.rememberFilter();
        const track = this.selectedTrack();
        if (!track) { this.setStatus("No game MIDI track is available yet."); return; }
        this.pendingPlay = null;
        if (this.trackListBox.selectedIndex !== this.selectedIndex) {
            this.trackListBox.select(this.selectedIndex);
        }
        if (!track.available) {
            this.stopPlayback();
            await this.prioritizeTrack(track);
            return;
        }
        if (this.pausedPosition?.file === track.file && this.synth.sequence) {
            await this.resumePlayback();
        } else {
            await this.playTrack(track, String(this.selectedIndex + 1).padStart(2, "0"));
        }
    }

    async prioritizeTrack(track) {
        this.pendingPlay = { id: track.id, itemId: track.item_id };
        this.setStatus(`Downloading ${track.title} first...`);
        this.downloadDismissed = false;
        try {
            const response = await fetch(`/api/midi/priority/${encodeURIComponent(track.source_id)}/${encodeURIComponent(track.item_id)}`, {
                method: "POST",
            });
            if (!response.ok) { throw new Error(`HTTP ${response.status}`); }
        } catch (error) {
            this.pendingPlay = null;
            this.setStatus(`Cannot queue MIDI download: ${error.message}`);
            return;
        }
        if (this.catalogTimer) { clearTimeout(this.catalogTimer); }
        this.catalogTimer = setTimeout(() => { void this.refreshCatalog(); }, 300);
    }

    async playTrack(track, number) {
        const playStarted = performance.now();
        const serial = ++this.loadSerial;
        this.finishPlaybackStats();
        this.synth.stop(false);
        this.isPlaying = false;
        this.isLoading = true;
        this.pausedPosition = null;
        this.activeTrackFile = track.file;
        this.updateTrackDisplay(track, number);
        this.setStatus(`Loading ${track.title} and SoundFont...`);
        this.updateProgress(0, 0, { status: false });
        this.playButton.setState(sfDisabled, true);
        try {
            // Resume audio synchronously with the Play gesture, before the MIDI fetch.
            const [sequence] = await Promise.all([this.loadTrack(track), this.synth.ensureContext()]);
            if (serial !== this.loadSerial) {
                return;
            }
            const started = await this.synth.play(
                sequence,
                (elapsed, duration) => this.updateProgress(elapsed, duration),
                () => {
                    if (serial !== this.loadSerial) { return; }
                    this.finishPlaybackStats();
                    this.isPlaying = false;
                    this.nextTrack(true);
                },
            );
            if (!started || serial !== this.loadSerial) { return; }
            this.synth.loadingTimes.playReadyMs = performance.now() - playStarted;
            this.isPlaying = true;
            this.playbackStats = {
                track, durationMs: 0, activeSince: performance.now(),
            };
            this.setStatus(`Playing ${track.title} (${formatMidiTime(sequence.duration)}).`);
        } catch (error) {
            if (serial !== this.loadSerial) { return; }
            this.isPlaying = false;
            this.setStatus(error && error.message ? error.message : "MIDI playback failed.");
        } finally {
            if (serial === this.loadSerial) {
                this.isLoading = false;
                this.playButton.setState(sfDisabled, false);
            }
        }
    }

    async resumePlayback() {
        const serial = this.loadSerial;
        this.isLoading = true;
        this.playButton.setState(sfDisabled, true);
        try {
            const resumed = await this.synth.resume();
            if (!resumed || serial !== this.loadSerial) { return; }
            this.pausedPosition = null;
            this.isPlaying = true;
            if (this.playbackStats) { this.playbackStats.activeSince = performance.now(); }
            this.setStatus(`Playing ${this.selectedTrack()?.title || "MIDI"}.`);
        } catch (error) {
            if (serial === this.loadSerial) { this.stopPlayback(error?.message || "MIDI resume failed."); }
        } finally {
            if (serial === this.loadSerial) {
                this.isLoading = false;
                this.playButton.setState(sfDisabled, false);
            }
        }
    }

    pausePlayback() {
        this.pausePlaybackStats();
        this.isPlaying = false;
        this.isLoading = false;
        const paused = this.synth.pause();
        if (paused) {
            this.pausedPosition = { ...paused, file: this.activeTrackFile };
            this.updateProgress(paused.elapsed, paused.duration, { status: false });
        } else {
            this.loadSerial += 1;
            this.synth.stop(false);
        }
        this.playButton.setState(sfDisabled, false);
        this.setStatus("Paused.");
    }

    stopPlayback(message = "Stopped.") {
        this.finishPlaybackStats();
        this.loadSerial += 1;
        this.isPlaying = false;
        this.isLoading = false;
        this.pausedPosition = null;
        this.activeTrackFile = null;
        this.synth.stop();
        this.playButton.setState(sfDisabled, false);
        this.updateProgress(0, 0, { status: false });
        this.setStatus(message);
    }

    pausePlaybackStats() {
        const stats = this.playbackStats;
        if (stats?.activeSince != null) {
            stats.durationMs += Math.max(0, performance.now() - stats.activeSince);
            stats.activeSince = null;
        }
    }

    finishPlaybackStats(beacon = false) {
        if (!this.playbackStats) { return; }
        this.pausePlaybackStats();
        const { track, durationMs } = this.playbackStats;
        this.playbackStats = null;
        this.onPlaybackEvent?.({
            event: "midi_play", scope: track.source_id, topic: track.id,
            game: track.game, name: track.title, duration_ms: durationMs,
        }, { beacon });
    }

    updateProgress(elapsed, duration, { status = true } = {}) {
        const ratio = duration > 0 ? Math.max(0, Math.min(1, elapsed / duration)) : 0;
        this.meter.updateView(ratio * 100);
        this.displayView.setTime(elapsed, duration);
        if (status && duration > 0) {
            this.setStatus(`Playing ${formatMidiTime(elapsed)} / ${formatMidiTime(duration)}.`);
        }
    }

    async seekTo(ratio) {
        const sequence = this.synth.sequence;
        if (!sequence) { return; }
        try {
            await this.synth.seekTo(ratio);
            this.updateProgress(sequence.duration * ratio, sequence.duration);
        } catch (error) {
            this.stopPlayback(error?.message || "MIDI seek failed.");
        }
    }

    setStatus(message) {
        this.displayView.setStatus(message);
    }
}

class TVGridDemoDialog extends TVDialog {
    static viewName = "grid-demo";

    constructor() {
        super(new TVRect(0, 0, 66, 19), "Grid Viewer");
        this.setHelpCtx(hcGridDemo);
        this.grid = new TVGridView(new TVRect(2, 2, 62, 13), [
            { title: "Object", width: 20 },
            { title: "Base", width: 18 },
            { title: "Purpose", width: 38 },
        ]);
        this.headerButton = new TVButton(new TVRect(2, 15, 20, 17), "~H~ide headers", "grid-headers");
        this.status = new TVStaticText(new TVRect(2, 14, 62, 15), "Arrow keys select a cell; both scrollbars are shared TVScrollBar views.");
        this.insert(new TVGroup(new TVRect(0, 0, 64, 17)).insertAll([
            new TVStaticText(new TVRect(2, 1, 62, 2), "TVGridView: selectable rows and columns"),
            this.grid,
            this.status,
            this.headerButton,
            new TVButton(new TVRect(23, 15, 33, 17), "~O~K", "grid-ok", bfDefault),
        ]));
        this.grid.setRows([
            ["TVView", "—", "Position, drawing, state and events"],
            ["TVGroup", "TVView", "Ownership and event propagation"],
            ["TVWindow", "TVGroup", "Frame, move, grow, close and zoom"],
            ["TVDialog", "TVWindow", "Modal dialog composition"],
            ["TVListViewer", "TVView", "Selection and keyboard navigation"],
            ["TVListBox", "TVListViewer", "Viewport and standard scrollbar"],
            ["TVGridView", "TVListBox", "Cells, visible headers, two-axis scroll"],
            ["TVTerminal", "TVView", "Streaming process output"],
            ["TVScrollBar", "TVView", "Shared vertical/horizontal scroll engine"],
            ["TVEditor", "TVView", "Text document viewport"],
        ]);
        this.grid.bind({ onSelect: (row, index) => {
            this.status.setText(`Row ${index + 1}, column ${this.grid.selectedColumn + 1}: ${row[this.grid.selectedColumn]}`);
        } });
        this.bindCommonClose(() => this.close());
        this.bindDrag();
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what !== evCommand) { return; }
        if (event.command === "grid-ok") { this.close(); }
        else if (event.command === "grid-headers") {
            this.grid.setHeadersVisible(!this.grid.headersVisible);
            this.headerButton.setTitle(this.grid.headersVisible ? "~H~ide headers" : "~S~how headers");
        }
        else { return; }
        this.clearEvent(event);
    }
}

class TVServerTerminalDialog extends TVDialog {
    static viewName = "server-terminal";

    constructor() {
        super(new TVRect(0, 0, 84, 27), "Server Terminal");
        this.setHelpCtx(hcServerTerminal);
        this.jobId = new TVInputLine(new TVRect(10, 1, 24, 2), 12);
        this.key = new TVInputLine(new TVRect(35, 1, 79, 2), 64).setSecret();
        this.input = new TVInputLine(new TVRect(10, 22, 68, 23), 2048);
        this.sendButton = new TVButton(new TVRect(69, 21, 79, 23), "~S~end", "terminal-send");
        this.status = new TVStaticText(new TVRect(27, 3, 79, 4), "Enter the ID and key printed by the server command.");
        const terminal = new TVTerminal(new TVRect(2, 5, 80, 21), 200);
        this.insert(new TVGroup(new TVRect(0, 0, 82, 25)).insertAll([
            new TVLabel(new TVRect(2, 1, 10, 2), "Job ~I~D:", this.jobId),
            this.jobId,
            new TVLabel(new TVRect(27, 1, 35, 2), "~K~ey:", this.key),
            this.key,
            new TVButton(new TVRect(2, 3, 15, 5), "~C~onnect", "terminal-connect", bfDefault),
            this.status,
            terminal,
            new TVLabel(new TVRect(2, 22, 10, 23), "~I~nput:", this.input),
            this.input,
            this.sendButton,
            new TVButton(new TVRect(69, 23, 79, 25), "~C~lose", "terminal-close"),
        ]));
        this.terminal = terminal.bind(terminal.root);
        this.input.setState(sfDisabled, true);
        this.sendButton.setState(sfDisabled, true);
        this.connection = null;
        this.pollTimer = null;
        this.bindCommonClose(() => this.close());
        this.bindDrag();
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what !== evCommand) { return; }
        if (event.command === "terminal-close") { this.close(); }
        else if (event.command === "terminal-connect") { void this.connect(); }
        else if (event.command === "terminal-send") { void this.send(); }
        else { return; }
        this.clearEvent(event);
    }

    close() {
        this.disconnect();
        this.key.setData("");
        super.close();
    }

    disconnect() {
        if (this.pollTimer) { clearTimeout(this.pollTimer); }
        this.pollTimer = null;
        this.connection = null;
        this.input.setState(sfDisabled, true);
        this.sendButton.setState(sfDisabled, true);
    }

    async connect() {
        this.disconnect();
        const id = this.jobId.getData().trim();
        const key = this.key.getData().trim();
        if (!/^[A-Za-z0-9_-]{12}$/.test(id) || !key) {
            this.status.setText("Enter a valid job ID and access key.");
            return;
        }
        this.connection = { id, key, offset: 0 };
        this.terminal.clear();
        await this.poll();
    }

    async poll() {
        const connection = this.connection;
        if (!connection || !this.isOpen()) { return; }
        try {
            const response = await fetch(`/api/terminal/jobs/${encodeURIComponent(connection.id)}?offset=${connection.offset}`, {
                headers: { "X-THelp-Terminal-Key": connection.key }, cache: "no-store",
            });
            if (!response.ok) { throw new Error(`HTTP ${response.status}`); }
            const result = await response.json();
            if (this.connection !== connection) { return; }
            connection.offset = result.offset;
            if (result.output) {
                this.terminal.appendChunk(result.output.replace(/\x1b\[[0-?]*[ -/]*[@-~]/g, ""));
            }
            this.input.setState(sfDisabled, !result.running);
            this.sendButton.setState(sfDisabled, !result.running);
            this.status.setText(result.running
                ? `${result.label}: running`
                : `${result.label}: finished (exit ${result.exit_code}) — input locked`);
            if (result.running || result.output?.length) {
                this.pollTimer = setTimeout(() => { void this.poll(); }, 350);
            }
        } catch (error) {
            if (this.connection !== connection) { return; }
            this.status.setText(`Connection failed: ${String(error?.message || error)}`);
            this.disconnect();
        }
    }

    async send() {
        const connection = this.connection;
        const text = this.input.getData();
        if (!connection || !text || this.input.disabled) { return; }
        try {
            const response = await fetch(`/api/terminal/jobs/${encodeURIComponent(connection.id)}/input`, {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-THelp-Terminal-Key": connection.key },
                body: JSON.stringify({ text }),
            });
            if (!response.ok) { throw new Error(`HTTP ${response.status}`); }
            this.input.setData("");
            this.input.focus();
        } catch (error) {
            this.status.setText(`Input rejected: ${String(error?.message || error)}`);
            if (String(error?.message).includes("409")) { this.input.setState(sfDisabled, true); }
        }
    }
}

function statisticsFlag(country) {
    const code = String(country || "").toUpperCase();
    if (!/^[A-Z]{2}$/.test(code)) { return "🌍"; }
    return String.fromCodePoint(...Array.from(code, (letter) => 0x1F1E6 + letter.charCodeAt(0) - 65));
}

function statisticsSystemIcon(system) {
    return ({ Windows: "🪟", macOS: "🍎", iOS: "🍎", Linux: "🐧", Android: "🤖" })[system] || "💻";
}

class TVStatisticsDialog extends TVDialog {
    static viewName = "statistics";

    constructor() {
        const okButton = new TVButton(new TVRect(25, 22, 35, 24), "~O~K", "statistics-ok", bfDefault);
        const refreshButton = new TVButton(new TVRect(37, 22, 49, 24), "~R~efresh", "statistics-refresh", bfNormal);
        super(new TVRect(0, 0, 78, 27), "Server Statistics");
        this.setHelpCtx(hcStatistics);
        this.summary = new TVStaticText(new TVRect(1, 1, 75, 3), "Loading server statistics...");
        this.categories = new TVListBox(new TVRect(1, 4, 24, 20));
        this.details = new TVListBox(new TVRect(26, 4, 75, 20));
        this.details.hScrollBar = new TVScrollBar(new TVRect());
        this.privacy = new TVStaticText(
            new TVRect(1, 20, 75, 21),
            "Aggregate counters only — no IP, cookie, visitor ID or raw user agent.",
        );
        this.data = null;
        this.sections = [];
        this.insert(new TVGroup(new TVRect(0, 0, 76, 25)).insertAll([
            this.summary,
            new TVStaticText(new TVRect(1, 3, 24, 4), "Category"),
            new TVStaticText(new TVRect(26, 3, 75, 4), "Ranked values / count"),
            this.categories,
            this.details,
            this.privacy,
            okButton,
            refreshButton,
        ]));
        this.okButton = okButton;
        this.refreshButton = refreshButton;
        this.categories.bind({ onSelect: (_item, index) => this.showSection(index) });
        this.bindCommonClose(() => this.close());
        this.bindDrag();
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what !== evCommand) { return; }
        if (event.command === "statistics-ok") { this.close(); }
        else if (event.command === "statistics-refresh") { void this.reload(); }
        else { return; }
        this.clearEvent(event);
    }

    open() {
        super.open();
        void this.reload();
    }

    sectionRows(key) {
        const rows = Array.isArray(this.data?.[key]) ? this.data[key] : [];
        if (key === "midi_tracks") {
            return [
                `Total: ${Number(this.data?.midi_plays) || 0} plays · ${Number(this.data?.midi_minutes) || 0} min`,
                ...rows.map((row, index) =>
                    `${String(index + 1).padStart(2, " ")}. ${row.value}  ${Number(row.count) || 0}× · ${Number(row.minutes) || 0} min`),
            ];
        }
        if (!rows.length) { return ["No data yet."]; }
        return rows.map((row, index) => {
            let value = String(row?.value || "Unknown");
            if (key === "country") { value = `${statisticsFlag(value)} ${value}`; }
            else if (key === "os") { value = `${statisticsSystemIcon(value)} ${value}`; }
            return `${String(index + 1).padStart(2, " ")}. ${value}  ${Number(row?.count) || 0}`;
        });
    }

    showSection(index) {
        const section = this.sections[index];
        this.details.newList(section ? this.sectionRows(section.key) : ["No data yet."]);
    }

    async reload() {
        this.summary.setText("Loading server statistics...");
        this.categories.newList([]);
        this.details.newList([]);
        let phase = "Server API";
        try {
            let response;
            for (let attempt = 0; attempt < 2; attempt += 1) {
                try {
                    response = await fetch("/api/statistics/summary", { cache: "no-store" });
                    if (response.ok || response.status < 500 || attempt) { break; }
                } catch (error) {
                    if (attempt) { throw error; }
                }
                await new Promise((resolve) => setTimeout(resolve, 400));
            }
            if (!response.ok) { throw new Error(`HTTP ${response.status}`); }
            this.data = await response.json();
            phase = "Statistics display";
            this.summary.setText([
                `Visits ${Number(this.data.visits) || 0}  HELP ${Number(this.data.help_opens) || 0}  Docs ${Number(this.data.document_opens) || 0}  Topics ${Number(this.data.topic_views) || 0}`,
                `Dialogs ${Number(this.data.dialog_opens) || 0}  Tools ${Number(this.data.tool_opens) || 0}  Search ${Number(this.data.searches) || 0}  Games ${Number(this.data.game_launches) || 0}/${Number(this.data.game_completions) || 0}`,
            ].join("\n"));
            this.sections = [
                ["📅 Daily visits", "daily"], ["🌍 Countries", "country"],
                ["↗ Referrers", "referrer"], ["📖 HELP files", "help_file"],
                ["📄 Documents", "document"], ["🔗 Topics", "topic"],
                ["▣ Active time", "active_duration"], ["📖 HELP time", "help_duration"],
                ["📄 Document time", "document_duration"], ["▤ Dialogs", "dialog"],
                ["⌛ Dialog time", "dialog_duration"],
                ["♫ MIDI playback", "midi_tracks"],
                ["⚒ Tools", "tool"], ["⌛ Tool time", "tool_duration"],
                ["⌕ Searches", "search"], ["↗ Links", "link"],
                ["🎮 Games", "game"], ["🏁 Game results", "game_outcome"],
                ["⏱ Game time", "game_duration"], ["🖥 Screens", "resolution"],
                ["▣ Viewports", "viewport"], ["💻 Devices", "device"],
                ["↕ Orientation", "orientation"], ["☝ Pointer", "pointer"],
                ["≈ Reduced motion", "reduced_motion"],
                ["⚙ Systems", "os"], ["🌐 Browsers", "browser"],
                ["🗣 Languages", "language"], ["🕒 Time zones", "timezone"],
                ["◉ Pixel ratio", "pixel_ratio"], ["🎨 Color depth", "color_depth"],
                ["▦ Themes", "theme"], ["⇥ TTFB", "page_ttfb"],
                ["⌛ Page load", "page_load"], ["▰ LCP", "lcp"],
                ["↔ CLS", "cls"], ["⌁ INP", "inp"],
                ["↓ HELP load", "help_load"], ["⇲ HELP unpack", "help_decompress"],
                ["▧ HELP render", "help_render"], ["⚠ Client errors", "client_error"],
            ].map(([label, key]) => ({ label, key }));
            this.categories.newList(this.sections);
            this.showSection(0);
        } catch (error) {
            this.data = null;
            this.sections = [];
            const reason = String(error?.message || error);
            this.summary.setText(`${phase} unavailable: ${reason}`);
            this.details.newList([`${phase}: ${reason}`, "Press Refresh to retry."]);
        }
    }
}

function systemInformationBrowser() {
    const userAgent = String(navigator.userAgent || "");
    const brands = navigator.userAgentData?.brands;
    if (Array.isArray(brands) && brands.length) {
        const brand = brands.find((item) => !/not.?a.?brand/i.test(item.brand)) || brands[0];
        return `${brand.brand} ${brand.version}`;
    }
    const patterns = [
        ["Edge", /Edg\/(\d+(?:\.\d+)?)/],
        ["Opera", /(?:OPR|Opera)\/(\d+(?:\.\d+)?)/],
        ["Firefox", /Firefox\/(\d+(?:\.\d+)?)/],
        ["Chrome", /(?:Chrome|CriOS)\/(\d+(?:\.\d+)?)/],
        ["Safari", /Version\/(\d+(?:\.\d+)?).*Safari/],
    ];
    for (const [name, pattern] of patterns) {
        const match = userAgent.match(pattern);
        if (match) { return `${name} ${match[1]}`; }
    }
    return "Unknown";
}

function systemInformationOperatingSystem() {
    const platform = String(navigator.userAgentData?.platform || navigator.platform || "");
    const userAgent = String(navigator.userAgent || "");
    if (/Android/i.test(userAgent)) { return "Android"; }
    if (/iPhone|iPad|iPod/i.test(userAgent)) { return "iOS"; }
    if (/Win/i.test(platform) || /Windows/i.test(userAgent)) { return "Windows"; }
    if (/Mac/i.test(platform) || /Mac OS/i.test(userAgent)) { return "macOS"; }
    if (/Linux/i.test(platform) || /Linux/i.test(userAgent)) { return "Linux"; }
    return platform || "Unknown";
}

function systemInformationStorage(name) {
    const key = "thelp:system-information-test";
    try {
        const storage = window[name];
        if (!storage) { return "Unavailable"; }
        storage.setItem(key, "1");
        storage.removeItem(key);
        return "Available";
    } catch {
        return "Blocked";
    }
}

function systemInformationSections() {
    const body = document.body;
    const screenInfo = window.screen || {};
    const cell = measureCells();
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "Unknown";
    const orientation = screenInfo.orientation?.type || "Unknown";
    const pageKind = body.dataset.tvPageKind || "generated HELP";
    const generatedAt = body.dataset.tvGeneratedAt || "Not reported";
    const platform = navigator.userAgentData?.platform || navigator.platform || "Unknown";
    const applicationRows = [
        `Name: ${body.dataset.tvSiteName || "THelpViewer"}`,
        `Version: ${body.dataset.tvGeneratorVersion || "Unknown"}`,
        `Authors: ${body.dataset.tvAuthors || "Unknown"}`,
        `Page mode: ${pageKind}`,
        `Theme: ${TV.getActiveThemePreset?.() || "default"}`,
        `Generated: ${generatedAt}`,
    ];
    if (body.dataset.tvFormatName) { applicationRows.push(`Format: ${body.dataset.tvFormatName}`); }
    if (body.dataset.tvTopicCount) { applicationRows.push(`Topics: ${body.dataset.tvTopicCount}`); }
    if (body.dataset.tvIndexCount) { applicationRows.push(`Index entries: ${body.dataset.tvIndexCount}`); }

    return [
        {
            label: "▣ Application",
            rows: applicationRows,
        },
        {
            label: "🌐 Browser",
            rows: [
                `Browser: ${systemInformationBrowser()}`,
                `Operating system: ${systemInformationOperatingSystem()}`,
                `Platform: ${platform}`,
                `Online: ${navigator.onLine ? "Yes" : "No"}`,
                `Cookies: ${navigator.cookieEnabled ? "Enabled" : "Disabled"}`,
                `Do Not Track: ${navigator.doNotTrack || "Not set"}`,
                `Logical processors: ${navigator.hardwareConcurrency || "Unknown"}`,
                `Touch points: ${navigator.maxTouchPoints || 0}`,
            ],
        },
        {
            label: "🖥 Display",
            rows: [
                `Screen: ${screenInfo.width || 0} × ${screenInfo.height || 0}`,
                `Available: ${screenInfo.availWidth || 0} × ${screenInfo.availHeight || 0}`,
                `Viewport: ${window.innerWidth || 0} × ${window.innerHeight || 0}`,
                `Pixel ratio: ${window.devicePixelRatio || 1}×`,
                `Color depth: ${screenInfo.colorDepth || 0} bit`,
                `Orientation: ${orientation}`,
                `TV cell: ${Math.round(cell.width * 100) / 100} × ${Math.round(cell.height * 100) / 100} px`,
            ],
        },
        {
            label: "🗣 Locale",
            rows: [
                `Language: ${navigator.language || "Unknown"}`,
                `Languages: ${(navigator.languages || []).join(", ") || "Unknown"}`,
                `Time zone: ${timezone}`,
            ],
        },
        {
            label: "▤ Storage",
            rows: [
                `Local storage: ${systemInformationStorage("localStorage")}`,
                `Session storage: ${systemInformationStorage("sessionStorage")}`,
                `IndexedDB: ${"indexedDB" in window ? "Available" : "Unavailable"}`,
                `Cache storage: ${"caches" in window ? "Available" : "Unavailable"}`,
            ],
        },
        {
            label: "⚙ Capabilities",
            rows: [
                `DecompressionStream: ${"DecompressionStream" in window ? "Yes" : "No"}`,
                `WebAssembly: ${"WebAssembly" in window ? "Yes" : "No"}`,
                `Web Audio: ${("AudioContext" in window || "webkitAudioContext" in window) ? "Yes" : "No"}`,
                `Web MIDI: ${typeof navigator.requestMIDIAccess === "function" ? "Yes" : "No"}`,
                `Service Worker: ${"serviceWorker" in navigator ? "Yes" : "No"}`,
                `Clipboard: ${"clipboard" in navigator ? "Yes" : "No"}`,
            ],
        },
        {
            label: "↔ Server",
            rows: ["Loading server information..."],
            server: true,
        },
    ];
}

async function systemInformationServerRows() {
    const requestJson = async (url) => {
        const response = await fetch(url, { cache: "no-store" });
        if (!response.ok) { throw new Error(`HTTP ${response.status}`); }
        return response.json();
    };
    const [healthResult, helpsResult, docsResult] = await Promise.allSettled([
        requestJson("/healthz"),
        requestJson("/helps/catalog.json"),
        requestJson("/docs/catalog.json"),
    ]);
    if (healthResult.status !== "fulfilled") {
        return [
            "Status: Unavailable or static viewer",
            `Origin: ${window.location.origin === "null" ? "Local file" : window.location.origin}`,
        ];
    }
    const health = healthResult.value || {};
    const helps = helpsResult.status === "fulfilled" && Array.isArray(helpsResult.value)
        ? helpsResult.value.length
        : "Unavailable";
    const docs = docsResult.status === "fulfilled" && Array.isArray(docsResult.value)
        ? docsResult.value.length
        : "Unavailable";
    return [
        `Status: ${health.status === "ok" ? "Online" : String(health.status || "Unknown")}`,
        `Version: ${health.version || "Unknown"}`,
        `HELP catalog: ${helps}`,
        `Docs catalog: ${docs}`,
        `Origin: ${window.location.origin}`,
    ];
}

class TVSystemInformationDialog extends TVDialog {
    static viewName = "system-information";

    constructor() {
        const okButton = new TVButton(new TVRect(25, 22, 35, 24), "~O~K", "system-information-ok", bfDefault);
        const refreshButton = new TVButton(new TVRect(37, 22, 49, 24), "~R~efresh", "system-information-refresh", bfNormal);
        super(new TVRect(0, 0, 78, 27), "System Information");
        this.setHelpCtx(hcSystemInformation);
        this.summary = new TVStaticText(new TVRect(1, 1, 75, 3), "THelpViewer system and runtime information");
        this.categories = new TVListBox(new TVRect(1, 4, 24, 20));
        this.details = new TVListBox(new TVRect(26, 4, 75, 20));
        this.note = new TVStaticText(
            new TVRect(1, 20, 75, 21),
            "Displayed locally — opening this dialog does not submit these details.",
        );
        this.sections = [];
        this.insert(new TVGroup(new TVRect(0, 0, 76, 25)).insertAll([
            this.summary,
            new TVStaticText(new TVRect(1, 3, 24, 4), "Category"),
            new TVStaticText(new TVRect(26, 3, 75, 4), "Value"),
            this.categories,
            this.details,
            this.note,
            okButton,
            refreshButton,
        ]));
        this.okButton = okButton;
        this.refreshButton = refreshButton;
        this.categories.bind({ onSelect: (_item, index) => this.showSection(index) });
        this.bindCommonClose(() => this.close());
        this.bindDrag();
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what !== evCommand) { return; }
        if (event.command === "system-information-ok") { this.close(); }
        else if (event.command === "system-information-refresh") { void this.reload(); }
        else { return; }
        this.clearEvent(event);
    }

    open() {
        super.open();
        void this.reload();
    }

    showSection(index) {
        const section = this.sections[index];
        this.details.newList(section?.rows?.length ? section.rows : ["No information available."]);
    }

    async reload() {
        const selected = Math.max(0, this.categories.selectedIndex || 0);
        this.sections = systemInformationSections();
        this.categories.newList(this.sections);
        this.categories.select(Math.min(selected, this.sections.length - 1));
        this.showSection(this.categories.selectedIndex);
        const server = this.sections.find((section) => section.server);
        server.rows = await systemInformationServerRows();
        if (this.sections[this.categories.selectedIndex] === server) {
            this.showSection(this.categories.selectedIndex);
        }
    }
}

class TVFindDialog extends TVDialog {
    static viewName = "find";

    constructor() {
        const findInput = new TVInputLine(new TVRect(2, 2, 32, 3), 255).setData("");
        const findLabel = new TVLabel(new TVRect(1, 1, 20, 2), "~T~ext to find", findInput);
        const findButton = new TVButton(new TVRect(35, 1, 45, 3), "~F~ind", "find-confirm", bfDefault);
        const cancelButton = new TVButton(new TVRect(35, 3, 45, 5), "Cancel", "find-cancel", bfNormal);
        const findStatus = new TVStaticText(new TVRect(2, 7, 33, 9), "");
        const scope = new TVRadioButtons(new TVRect(2, 4, 33, 6), [
            { label: "Search ~a~ll HELP/Docs", value: "global" },
            { label: "Find in ~a~ctive window", value: "local" },
        ]);
        const historyButton = new TVHistory(new TVRect(32, 2, 35, 3), findInput, "thelp:find-history");
        const historyPopup = new TVHistoryWindow(new TVRect(0, 0, 34, 7), "find");
        const findMain = new TVGroup(new TVRect(0, 0, 47, 10)).insertAll([
            findLabel,
            findInput,
            historyButton,
            findButton,
            cancelButton,
            scope,
            findStatus,
            historyPopup,
        ]);
        super(new TVRect(0, 0, 49, 12), "Find");
        this.setHelpCtx(hcFind);
        this.insert(findMain);
        this.setState(sfModal, true);
        this.history = historyButton;
        this.findHandler = null;
        this.findAgainHandler = null;
        this.globalFindHandler = null;
        this.targetLabel = "active window";
        this.globalAvailable = false;
        this.availabilityChecked = false;
        this.availabilitySerial = 0;
        this.input = findInput;
        this.statusView = findStatus;
        this.scope = scope;
        this.findButton = findButton;
        this.cancelButton = cancelButton;
        this.historyButton = historyButton;
        this.historyPopup = historyPopup;
        this.historyList = historyPopup.viewer;
        this.historyWindow = this.historyButton.bindWindow(
            this.historyPopup,
            () => this.history.keys().map((value) => ({ historyKey: value, value })),
            (item, activate) => {
                this.input.setData(item.value);
                this.historyWindow.hide();
                if (activate) { this.performFind(); }
                else { this.input.focus(); }
            },
        );
        this.bindCommonClose(() => this.close());
        this.bindDrag();
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evKeyDown && this.historyWindow.handleEscape(event.nativeEvent)) {
            this.clearEvent(event);
            return;
        }
        if (event.what === evCommand && event.command === "find-confirm") {
            this.performFind();
            this.clearEvent(event);
        } else if (event.what === evCommand && event.command === "find-cancel") {
            this.close();
            this.clearEvent(event);
        } else if (
            event.what === evKeyDown
            && event.infoPtr === this.input
            && event.nativeEvent?.key === "Enter"
        ) {
            event.nativeEvent.preventDefault();
            this.performFind();
            this.clearEvent(event);
        } else if (event.what === evBroadcast && event.infoPtr === this.scope) {
            this.updateScopeStatus();
            this.clearEvent(event);
        }
    }

    updateScopeStatus() {
        this.statusView.setText(this.scope.mark(0)
            ? this.globalAvailable ? "Search across HELP files and Docs"
                : this.availabilityChecked ? "Server search is unavailable." : "Checking server search..."
            : this.findHandler ? `Find in ${this.targetLabel}` : "No active window for local Find.");
    }

    setAvailability(globalAvailable) {
        this.globalAvailable = Boolean(globalAvailable && this.globalFindHandler);
        const localAvailable = Boolean(this.findHandler);
        this.scope.setButtonState(1, this.globalAvailable);
        this.scope.setButtonState(2, localAvailable);
        if ((this.scope.mark(0) && !this.globalAvailable) || (this.scope.mark(1) && !localAvailable)) {
            this.scope.setData(localAvailable ? 1 : 0);
        }
        this.updateScopeStatus();
    }

    async checkGlobalAvailability() {
        const serial = ++this.availabilitySerial;
        try {
            const response = await fetch("/api/search/status", { cache: "no-store" });
            const data = response.ok ? await response.json() : null;
            if (serial === this.availabilitySerial) {
                this.availabilityChecked = true;
                this.setAvailability(Boolean(data && ["ready", "building"].includes(data.state)));
            }
        } catch {
            if (serial === this.availabilitySerial) {
                this.availabilityChecked = true;
                this.setAvailability(false);
            }
        }
    }

    configure({ find = null, findAgain = null, globalFind = null, targetLabel = "active window" } = {}) {
        this.findHandler = typeof find === "function" ? find : null;
        this.findAgainHandler = typeof findAgain === "function" ? findAgain : null;
        this.globalFindHandler = typeof globalFind === "function" ? globalFind : null;
        this.targetLabel = String(targetLabel || "active window");
        this.setAvailability(false);
        this.historyWindow.refresh();
    }

    open(initialQuery = "") {
        this.historyWindow.hide();
        this.availabilityChecked = false;
        this.scope.setData(this.findHandler ? 1 : 0);
        this.setAvailability(false);
        if (initialQuery) { this.input.setData(initialQuery); }
        this.historyWindow.refresh();
        super.open();
        void this.checkGlobalAvailability();
        this.input.focus();
        this.input.selectAll();
    }

    performFind() {
        const query = this.input.getData().trim();
        if (query && this.scope.mark(0) && this.globalAvailable && this.globalFindHandler) {
            this.history.remember(query);
            this.close();
            this.globalFindHandler(query);
            return true;
        }
        if (!query) {
            this.statusView.setText("Enter text to find.");
            return false;
        }
        if (this.scope.mark(0) && !this.globalAvailable) {
            this.statusView.setText("Server search is not available.");
            return false;
        }
        if (!this.findHandler) {
            this.statusView.setText("No active window. Select Search all HELP/Docs.");
            return false;
        }
        this.history.remember(query);
        this.historyWindow.refresh();
        const found = Boolean(this.findHandler(query));
        this.statusView.setText(found ? `Found in ${this.targetLabel}` : `Text not found in ${this.targetLabel}`);
        if (found) { this.close(); }
        return found;
    }

    findAgain() {
        return this.findAgainHandler ? Boolean(this.findAgainHandler()) : false;
    }

    close() {
        this.historyWindow.hide();
        super.close();
    }

}

class TVSearchResultsList extends TVListBox {
    static viewName = "search-results";

    constructor(bounds) {
        super(bounds);
        this.messageView = null;
    }

    setMessage(text) {
        const messageView = new TVStaticText(new TVRect(), String(text ?? ""));
        messageView.owner = this;
        this.messageView = messageView;
        super.setItems([messageView], -1);
        messageView.resolve(this.itemsRoot());
    }

    setItems(items, selectedIndex = -1) {
        this.messageView = null;
        super.setItems(items, selectedIndex);
    }

    itemMarkup(entry, index) {
        if (entry === this.messageView) {
            return entry.draw();
        }
        const source = entry.source_file || entry.file || "Current HELP file";
        return new TVSearchResultButton(new TVRect(), "", "search-index", bfNormal)
            .setValue(index)
            .setCommandData({
                listIndex: index,
                selected: index === this.selectedIndex,
                title: entry.title,
                meta: source,
            })
            .draw();
    }
}

class TVIndexProgressDialog extends TVDialog {
    static viewName = "index-progress";

    constructor(title = "Building Global Index", initialSummary = "Preparing HELP files and Docs...") {
        super(new TVRect(0, 0, 46, 10), title);
        this.setState(sfModal, true);
        this.summary = new TVStaticText(new TVRect(2, 1, 42, 2), initialSummary);
        this.file = new TVStaticText(new TVRect(2, 4, 42, 5), "");
        this.bar = new TVBarGauge(new TVRect(2, 2, 42, 3), 100);
        this.percent = new TVPercentGauge(new TVRect(19, 3, 26, 4), 100);
        this.insert(new TVGroup(new TVRect(0, 0, 44, 8)).insertAll([
            this.summary, this.bar, this.percent, this.file,
            new TVButton(new TVRect(17, 6, 29, 8), "~H~ide", "index-hide", bfDefault),
        ]));
        this.onHide = null;
        this.bindCommonClose(() => this.hideProgress());
        this.bindDrag();
    }

    update(status) {
        const percent = Math.max(0, Math.min(100, Number(status.percent) || 0));
        this.summary.setText(`${status.processed || 0} / ${status.total || 0} files indexed`);
        this.file.setText(String(status.file || "").slice(-40));
        this.bar.updateView(percent);
        this.percent.updateView(percent);
    }

    hideProgress() {
        this.onHide?.();
        this.close();
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evCommand && event.command === "index-hide") {
            this.hideProgress();
            this.clearEvent(event);
        }
    }
}

class TVMidiDownloadProgressDialog extends TVIndexProgressDialog {
    static viewName = "midi-download-progress";

    constructor() {
        super("Downloading Game MIDI", "Preparing game MIDI files...");
    }

    update(status) {
        const downloaded = Number(status.downloaded) || 0;
        const total = Number(status.total) || 0;
        const percent = status.state === "ready" ? 100
            : total ? Math.max(0, Math.min(100, Math.floor(100 * downloaded / total))) : 0;
        this.summary.setText(`${downloaded} / ${total} MIDI tracks ready`);
        this.file.setText(String(status.current || "").slice(-40));
        this.bar.updateView(percent);
        this.percent.updateView(percent);
    }
}

class TVSearchDialog extends TVDialog {
    static viewName = "search";

    constructor() {
        const searchInput = new TVInputLine(new TVRect(7, 1, 61, 2), 255);
        const searchLabel = new TVLabel(new TVRect(1, 1, 7, 2), "~F~ind:", searchInput);
        const scope = new TVRadioButtons(new TVRect(1, 3, 31, 5), [
            { label: "Search ~a~ll HELP/Docs", value: "global" },
            { label: "Find in ~a~ctive HELP file", value: "local" },
        ]);
        const resultsBox = new TVSearchResultsList(new TVRect(1, 6, 61, 23));
        const sourceView = new TVStaticText(new TVRect(1, 23, 61, 24), "");
        const okButton = new TVButton(new TVRect(62, 1, 73, 3), '~O~K', "search-ok", bfDefault);
        const cancelButton = new TVButton(new TVRect(62, 4, 73, 6), '~C~ancel', "search-cancel", bfNormal);
        const searchMain = new TVGroup(new TVRect(0, 0, 74, 24)).insertAll([
            searchLabel,
            searchInput,
            scope,
            new TVStaticText(new TVRect(32, 4, 61, 5), "Choose a topic."),
            resultsBox,
            sourceView,
            okButton,
            cancelButton,
        ]);

        super(new TVRect(0, 0, 76, 26), "Find");
        this.setHelpCtx(hcSearch);
        this.insert(searchMain);
        this.searchData = window.TV_SEARCH_INDEX && Array.isArray(window.TV_SEARCH_INDEX.topics)
            ? window.TV_SEARCH_INDEX
            : { topics: [] };
        this.input = searchInput;
        this.scope = scope;
        this.globalAvailable = false;
        this.availabilityChecked = false;
        this.availabilitySerial = 0;
        this.okButton = okButton;
        this.cancelButton = cancelButton;
        this.resultsBox = resultsBox;
        this.sourceView = sourceView;
        this.matches = [];
        this.selectedIndex = -1;
        this.searchSerial = 0;
        this.searchTimer = null;
        this.indexMonitorTimer = null;
        this.indexMonitorSerial = 0;
        this.indexProgress = null;
        this.progressDismissed = false;
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bind();
    }

    bind() {
        if (!this.root) {
            return;
        }

        this.resultsBox.bind({
            onSelect: (_entry, index) => {
                this.selectIndex(index);
            },
            onActivate: (_entry, index) => {
                this.selectIndex(index);
                this.openSelected();
            },
        });
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what === evBroadcast && event.infoPtr === this.input) {
            this.renderResults(this.input.getData());
            this.clearEvent(event);
        } else if (event.what === evBroadcast && event.infoPtr === this.scope) {
            this.renderResults(this.input.getData());
            this.clearEvent(event);
        } else if (event.what === evCommand) {
            if (event.command === "search-ok") { this.openSelected(); }
            else if (event.command === "search-cancel") { this.close(); }
            else { return; }
            this.clearEvent(event);
        } else if (event.what === evKeyDown) {
            this.onKeyDown(event.nativeEvent);
            if (event.nativeEvent?.defaultPrevented) { this.clearEvent(event); }
        }
    }

    onKeyDown(event) {
        if (event.key === "F3") {
            event.preventDefault();
            if (this.isOpen()) {
                this.input.focus();
                this.input.selectAll();
            } else {
                this.open("");
            }
            return;
        }
        if (event.key === "Escape" && this.isActive()) {
            event.preventDefault();
            this.close();
            return;
        }
        if (!this.isActive()) {
            return;
        }
        if (event.key === "Enter") {
            event.preventDefault();
            this.openSelected();
            return;
        }
        if (event.key === "ArrowDown") {
            event.preventDefault();
            this.moveSelection(1);
            return;
        }
        if (event.key === "ArrowUp") {
            event.preventDefault();
            this.moveSelection(-1);
        }
    }

    open(initialQuery = "") {
        this.availabilityChecked = false;
        this.scope.setData(this.searchData.topics.length ? 1 : 0);
        this.setAvailability(false);
        super.open();
        void this.checkGlobalAvailability();
        if (typeof initialQuery === "string") {
            this.input.setData(initialQuery);
        }
        this.renderResults(this.input.getData());
        window.requestAnimationFrame(() => this.resultsBox.updateScrollbar());
        this.input.focus();
        this.input.selectAll();
    }

    close() {
        clearTimeout(this.searchTimer);
        this.searchSerial += 1;
        this.scope.setData(0);
        super.close();
    }

    moveSelection(delta) {
        if (!this.matches.length) {
            return;
        }
        const next = this.selectedIndex < 0
            ? 0
            : Math.max(0, Math.min(this.matches.length - 1, this.selectedIndex + delta));
        this.selectIndex(next);
    }

    selectIndex(index) {
        if (!Number.isInteger(index) || index < 0 || index >= this.matches.length) {
            this.selectedIndex = -1;
            this.updateSelectionUi();
            return;
        }
        this.selectedIndex = index;
        this.updateSelectionUi();
    }

    updateSelectionUi() {
        this.resultsBox.select(this.selectedIndex);
        this.okButton.setState(sfDisabled, this.selectedIndex < 0);
        const match = this.matches[this.selectedIndex];
        const name = match?.help_name || (match?.kind === "doc" ? "Docs" : "");
        this.sourceView.setText(name ? `Source: ${name}`.slice(0, 60) : "");
    }

    openSelected() {
        if (this.selectedIndex < 0 || this.selectedIndex >= this.matches.length) {
            return;
        }
        const match = this.matches[this.selectedIndex];
        if (match.kind === "doc") {
            window.location.href = `/?search_doc=${encodeURIComponent(match.file)}`;
            return;
        }
        window.location.href = match.file
            ? `/?file=${encodeURIComponent(match.file)}&topic=${encodeURIComponent(match.context_hex)}`
            : match.href;
    }

    isGlobal() { return this.scope.mark(0) && this.globalAvailable; }

    setAvailability(globalAvailable) {
        this.globalAvailable = Boolean(globalAvailable);
        const localAvailable = Boolean(this.searchData.topics.length);
        this.scope.setButtonState(1, this.globalAvailable);
        this.scope.setButtonState(2, localAvailable);
        if ((this.scope.mark(0) && !this.globalAvailable) || (this.scope.mark(1) && !localAvailable)) {
            this.scope.setData(localAvailable ? 1 : 0);
        }
        if (this.isOpen()) { this.renderResults(this.input.getData()); }
    }

    async checkGlobalAvailability() {
        const serial = ++this.availabilitySerial;
        try {
            const response = await fetch("/api/search/status", { cache: "no-store" });
            const status = response.ok ? await response.json() : null;
            if (serial === this.availabilitySerial) {
                this.availabilityChecked = true;
                this.setAvailability(Boolean(status && ["ready", "building"].includes(status.state)));
            }
        } catch {
            if (serial === this.availabilitySerial) {
                this.availabilityChecked = true;
                this.setAvailability(false);
            }
        }
    }

    setGlobal(enable) {
        this.scope.setData(enable ? 0 : 1);
        if (this.isOpen()) { this.renderResults(this.input.getData()); }
    }

    showIndexProgress(status) {
        if (this.progressDismissed || !(this.owner instanceof TV.TVDesktop)) { return; }
        if (!this.indexProgress || this.indexProgress.destroyed) {
            this.indexProgress = new TVIndexProgressDialog();
            this.indexProgress.onHide = () => { this.progressDismissed = true; };
            this.owner.insert(this.indexProgress);
        }
        this.indexProgress.update(status);
        if (!this.indexProgress.isOpen()) { this.indexProgress.open(); }
    }

    clearIndexProgress() {
        this.indexProgress?.destroy();
        this.indexProgress = null;
        this.progressDismissed = false;
    }

    async monitorIndex() {
        const serial = ++this.indexMonitorSerial;
        if (this.indexMonitorTimer) { clearTimeout(this.indexMonitorTimer); }
        this.indexMonitorTimer = null;
        try {
            const response = await fetch("/api/search/status", { cache: "no-store" });
            if (!response.ok) { throw new Error(`HTTP ${response.status}`); }
            const status = await response.json();
            if (serial !== this.indexMonitorSerial) { return; }
            if (status.state === "building") {
                this.showIndexProgress(status);
                this.indexMonitorTimer = setTimeout(() => { void this.monitorIndex(); }, 250);
            } else if (status.state === "ready" && this.indexProgress) {
                this.indexProgress.update({ ...status, percent: 100 });
                this.indexMonitorTimer = setTimeout(() => {
                    if (serial !== this.indexMonitorSerial) { return; }
                    this.indexMonitorTimer = null;
                    this.clearIndexProgress();
                    if (this.isOpen() && this.isGlobal()) {
                        this.renderResults(this.input.getData());
                    }
                }, 600);
            } else {
                this.clearIndexProgress();
            }
        } catch {
            if (serial !== this.indexMonitorSerial) { return; }
            this.clearIndexProgress();
        }
    }

    async searchGlobal(query, serial) {
        try {
            const response = await fetch(`/api/search/global?q=${encodeURIComponent(query)}`, { cache: "no-store" });
            if (serial !== this.searchSerial || !this.isGlobal()) { return; }
            if (response.status === 202) {
                this.resultsBox.setMessage("Building global index. Results will appear when ready.");
                void this.monitorIndex();
                return;
            }
            if (!response.ok) { throw new Error(`HTTP ${response.status}`); }
            const data = await response.json();
            if (serial !== this.searchSerial || !this.isGlobal()) { return; }
            this.matches = Array.isArray(data.results) ? data.results : [];
            if (!this.matches.length) {
                this.resultsBox.setMessage(`No matches for "${query}" in HELP files or Docs.`);
            } else {
                this.resultsBox.setItems(this.matches, 0);
                this.selectIndex(0);
            }
            this.resultsBox.updateScrollbar();
        } catch (error) {
            if (serial === this.searchSerial) {
                this.resultsBox.setMessage(`Global search is unavailable: ${String(error?.message || error)}`);
            }
        }
    }

    renderResults(query) {
        if (!this.resultsBox.itemsRoot()) {
            return;
        }
        this.matches = [];
        this.selectedIndex = -1;
        this.sourceView.setText("");
        this.okButton.setState(sfDisabled, true);
        clearTimeout(this.searchTimer);
        const serial = ++this.searchSerial;
        const trimmed = query.trim();
        if (!this.globalAvailable && !this.searchData.topics.length) {
            this.resultsBox.setMessage(this.availabilityChecked
                ? "No active HELP file or server search is available."
                : "No active HELP file; checking server search availability.");
            this.resultsBox.updateScrollbar();
            return;
        }
        if (this.isGlobal()) {
            if (!trimmed) {
                this.resultsBox.setMessage("Type text to search HELP files and Docs.");
            } else {
                this.resultsBox.setMessage("Searching HELP files and Docs...");
                this.searchTimer = setTimeout(() => { void this.searchGlobal(trimmed, serial); }, 180);
            }
            this.resultsBox.updateScrollbar();
            return;
        }
        if (!this.searchData.topics.length) {
            this.resultsBox.setMessage("Search index is not available for this help file.");
            this.resultsBox.updateScrollbar();
            fillBorders();
            return;
        }

        if (!trimmed) {
            this.resultsBox.setMessage("Type text to search across all generated topics.");
            this.resultsBox.updateScrollbar();
            fillBorders();
            return;
        }

        const matches = this.search(trimmed);
        if (!matches.length) {
            this.resultsBox.setMessage(`No matches for "${trimmed}".`);
            this.resultsBox.updateScrollbar();
            fillBorders();
            return;
        }

        this.matches = matches.slice(0, 60);
        this.resultsBox.setItems(this.matches, 0);
        this.selectIndex(0);
        fillBorders();
    }

    search(query) {
        const terms = normalizeSearchText(query).split(/\s+/).filter(Boolean);
        if (!terms.length) {
            return [];
        }

        const matches = [];
        outer: for (const entry of this.searchData.topics) {
            entry._titleNorm ||= normalizeSearchText(entry.title);
            entry._termsNorm ||= normalizeSearchText((entry.index_terms || []).join("\n"));
            entry._textNorm ||= normalizeSearchText(`${entry.preview || ""}\n${entry.text || ""}\n${entry.context_hex || ""}`);

            let score = 0;
            for (const term of terms) {
                if (entry._titleNorm.includes(term)) {
                    score += 12;
                    continue;
                }
                if (entry._termsNorm.includes(term)) {
                    score += 8;
                    continue;
                }
                if (entry._textNorm.includes(term)) {
                    score += 3;
                    continue;
                }
                continue outer;
            }
            matches.push({ ...entry, _score: score });
        }

        matches.sort((left, right) => {
            if (right._score !== left._score) {
                return right._score - left._score;
            }
            return left.context_id - right.context_id;
        });
        return matches;
    }
}


Object.assign(TV, {
    TVAboutDialog,
    TVLoginDialog,
    TVRegistrationDialog,
    TVRegistrationTokenDialog,
    TVServerConfigurationDialog,
    TVViewGalleryDialog,
    TVHistory,
    TVHistoryViewer,
    TVHistoryWindow,
    TVFileList,
    TVFileOpenDialog,
    TVChangeDirectoryDialog,
    TVAsciiTable,
    TVAsciiTableDialog,
    TVCalculatorDialog,
    TVCalendarView,
    TVCalendarDialog,
    TVColorSelector,
    TVColorDisplay,
    TVColorsDialog,
    TVMidiPlayerDialog,
    TVGridDemoDialog,
    TVServerTerminalDialog,
    TVStatisticsDialog,
    TVSystemInformationDialog,
    TVFindDialog,
    TVSearchDialog,
});
})();
