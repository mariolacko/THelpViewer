// Server content setup: shared Turbo Vision views, commands and API progress.
(function () {
"use strict";
const TV = window.THelpViewerTV;
const { TVDialog, TVRect, TVGroup, TVStaticText, TVLabel, TVListBox, TVButton,
    TVMessageBox, TVLoginDialog, TVRegistrationDialog, TVIndexProgressDialog, bfDefault, evCommand,
    sfDisabled, sfModal, TVScrollBar, TV_HELP_CONTEXTS } = TV;

class TVContentSetupDialog extends TVDialog {
    static viewName = "content-setup";

    constructor() {
        super(new TVRect(0, 0, 86, 28), "Server Content Configuration");
        this.setHelpCtx(TV_HELP_CONTEXTS.hcServerConfiguration);
        this.setState(sfModal, true);
        this.helpList = new TVListBox(new TVRect(2, 3, 41, 18));
        this.dosList = new TVListBox(new TVRect(43, 3, 82, 18));
        this.helpList.hScrollBar = new TVScrollBar(new TVRect());
        this.dosList.hScrollBar = new TVScrollBar(new TVRect());
        this.installButton = new TVButton(new TVRect(20, 21, 41, 23), "~I~nstall selected", "content-install", bfDefault);
        this.refreshButton = new TVButton(new TVRect(43, 21, 57, 23), "~R~efresh", "content-refresh");
        this.statusText = new TVStaticText(new TVRect(2, 24, 82, 26), "");
        this.insert(new TVGroup(new TVRect(0, 0, 84, 26)).insertAll([
            new TVStaticText(new TVRect(2, 0, 82, 1), "Choose server content. Nothing downloads until you confirm Install."),
            new TVLabel(new TVRect(2, 2, 41, 3), "~H~ELP groups", this.helpList), this.helpList,
            new TVLabel(new TVRect(43, 2, 82, 3), "~D~OS packages", this.dosList), this.dosList,
            new TVStaticText(new TVRect(2, 19, 82, 21), "Click or Space toggles [x]. Arrows move. * means already installed.\nUnselected content and private DOS disks are kept."),
            this.installButton, this.refreshButton,
            new TVButton(new TVRect(59, 21, 73, 23), "~C~lose", "content-close"), this.statusText,
        ]));
        this.selectedHelp = new Set(); this.selectedDos = new Set();
        this.requestVersion = 0; this.pollTask = null; this.progress = null;
        this.onBeforeInstall = null; this.onInstalled = null;
        this.bindCommonClose(() => this.close()); this.bindDrag();
    }

    open() { super.open(); void this.loadChoices(); }

    close() { this.requestVersion += 1; super.close(); }

    async checkFirstRun() {
        const version = ++this.requestVersion;
        try {
            const data = await TVLoginDialog.request("/api/admin/content");
            if (!data.needs_setup) { return; }
            // Finish login/registration and its confirmation before opening first-run setup.
            while (version === this.requestVersion && !this.destroyed) {
                const active = this.manager?.get(this.manager.activeTarget);
                if (!(active instanceof TVMessageBox || active instanceof TVLoginDialog
                    || active instanceof TVRegistrationDialog) || !active.isOpen()) {
                    this.open(); return;
                }
                await new Promise((resolve) => setTimeout(resolve, 100));
            }
        } catch { /* No setup API on standalone pages or after sign-out. */ }
    }

    renderChoices(list, items, selected) {
        const render = () => list.setItems(items.map((item) => ({ ...item,
            label: `[${selected.has(item.id) ? "x" : " "}] ${item.label}${item.installed ? " *" : ""}`,
        })), Math.max(0, list.selectedIndex));
        const toggle = (item, _index, event) => {
            if (event?.type === "keydown" && ![" ", "Enter"].includes(event.key)) { return; }
            selected.has(item.id) ? selected.delete(item.id) : selected.add(item.id);
            render();
        };
        // The preceding single click already toggled a double-clicked row.
        render(); list.bind({ onSelect: toggle, onActivate: (item, index, event) => {
            if (event?.type === "keydown") { toggle(item, index, event); }
        } });
    }

    async loadChoices() {
        const version = ++this.requestVersion;
        this.installButton.setState(sfDisabled, true);
        this.statusText.setText("Loading server configuration...");
        try {
            const data = await TVLoginDialog.request("/api/admin/content");
            if (version !== this.requestVersion || !this.isOpen()) { return; }
            this.selectedHelp = new Set(data.selection.help_groups);
            this.selectedDos = new Set(data.selection.dos_packages);
            this.renderChoices(this.helpList, data.help_groups, this.selectedHelp);
            this.renderChoices(this.dosList, data.dos_packages, this.selectedDos);
            this.statusText.setText(data.needs_setup ? "First run: choose HELP groups and DOS packages, then Install." : "Selections are saved on the server; closing this dialog changes nothing.");
            this.installButton.setState(sfDisabled, false);
            this.helpList.focus();
            if (data.status.state === "building") { void this.followProgress(data.status); }
        } catch (error) {
            if (version === this.requestVersion && this.isOpen()) { this.statusText.setText(error.message); }
        }
    }

    async installSelected() {
        if (this.pollTask) { this.progress?.open(); return; }
        if (this.installButton.state & sfDisabled) { return; }
        const selection = { help_groups: [...this.selectedHelp], dos_packages: [...this.selectedDos] };
        const box = new TVMessageBox(); this.owner.insert(box);
        let answer;
        try {
            answer = await box.show({ title: "Install server content", type: TVMessageBox.MF_CONFIRMATION,
                lines: [`Install ${selection.help_groups.length} HELP group(s) and ${selection.dos_packages.length} DOS package(s)?`,
                    "Downloads and conversion run on the server.", "Existing unselected content and private disks are kept.",
                    "Other open DOS sessions must be restarted."], buttons: TVMessageBox.MF_OK_CANCEL });
        } finally { box.destroy(); }
        if (answer !== "ok" || !this.isOpen()) { return; }
        this.installButton.setState(sfDisabled, true);
        try {
            if (selection.dos_packages.length) { await this.onBeforeInstall?.(); }
            const status = await TVLoginDialog.request("/api/admin/content", "POST", selection);
            await this.followProgress(status);
        } catch (error) { this.statusText.setText(error.message); }
        finally { this.installButton.setState(sfDisabled, false); }
    }

    followProgress(initialStatus) {
        if (this.pollTask) { this.progress?.open(); return this.pollTask; }
        this.pollTask = this.pollProgress(initialStatus).finally(() => { this.pollTask = null; });
        return this.pollTask;
    }

    async pollProgress(status) {
        if (!this.progress) {
            this.progress = new TVIndexProgressDialog("Installing Server Content", "Preparing...");
            this.progress.setHelpCtx(this.helpCtx);
            this.owner.insert(this.progress);
            this.owner.dialogManager.register("content-progress", this.progress);
        }
        this.progress.open();
        this.installButton.setState(sfDisabled, true);
        try {
            while (!this.destroyed) {
                this.progress.update(status);
                this.progress.summary.setText(`${status.phase || status.state}: ${status.processed || 0}/${status.total || 0}`);
                this.statusText.setText(`${status.percent || 0}% · ${status.phase || status.state}`);
                if (status.state === "error") { throw new Error(status.error || "Content installation failed."); }
                if (status.state !== "building") {
                    this.statusText.setText(`Finished.${status.warnings?.length ? ` ${status.warnings.length} source warning(s): ${status.warnings[0]}` : ""}`);
                    await this.onInstalled?.();
                    break;
                }
                await new Promise((resolve) => setTimeout(resolve, 1000));
                status = await TVLoginDialog.request("/api/admin/content/status");
            }
        } catch (error) { this.statusText.setText(error.message); }
        finally { this.progress.close(); this.installButton.setState(sfDisabled, false); }
    }

    handleEvent(event) {
        super.handleEvent(event);
        if (event.what !== evCommand) { return; }
        switch (event.command) {
            case "content-install": void this.installSelected(); break;
            case "content-refresh": void this.loadChoices(); break;
            case "content-close": this.close(); break;
            default: return;
        }
        this.clearEvent(event);
    }
}

TV.TVContentSetupDialog = TVContentSetupDialog;
})();
