// Turbo Vision dialogs for generated help pages.
(function () {
"use strict";
const TV = window.THelpViewerTV = window.THelpViewerTV || {};
const {
    escapeHtml,
    renderHotkeyMarkup,
    displayCp437Char,
    cloneColorPalette,
    buildDefaultColorPalette,
    buildPaletteFromCurrentStyle,
    applyColorPalette,
    applyThemePreset,
    dosColor,
    DOS_COLORS,
    COLOR_GROUPS,
    TVDialog,
    TVStaticText,
    TVLabel,
    TVInputLine,
    TVGroup,
    TVListViewer,
    TVVerticalListViewer,
    TVButtonStrip,
    TVButton,
    normalizeSearchText,
    fillBorders,
    MONTH_NAMES,
    DAYS_IN_MONTH,
    isLeapYear,
    dayOfWeek,
} = TV;

class TVAboutDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const body = document.body;
        const siteName = body.dataset.tvSiteName || "THelpViewer";
        const generatorVersion = body.dataset.tvGeneratorVersion || "0.1.0";
        const aboutMain = new TVGroup({
            w: 28, h: 14,
            children: [
                new TVStaticText({ x: 0, y: 1, w: 28, align: "center", title: true, text: siteName }),
                new TVStaticText({ x: 0, y: 3, w: 28, align: "center", text: `Version ${generatorVersion}` }),
                new TVStaticText({ x: 0, y: 5, w: 28, align: "center", text: "Copyright (c) 2026" }),
                new TVStaticText({ x: 0, y: 7, w: 28, align: "center", text: "Mario Lacko + Copilot" }),
                new TVButton({ x: 9, y: 9, w: 10, className: "is-default", attrs: { "data-tv-about-ok": true }, label: '~O~K' }),
            ],
        }).renderMarkup();

        super({
            desktop,
            ariaLabel: "About",
            title: "About",
            closeAttrs: {
                "data-tv-about-close": true,
                "aria-label": "Close about dialog",
            },
            bodyMarkup: aboutMain,
            footerMarkup: TVDialog.footerMarkup(),
            width: "32ch",
            height: "min(13em, calc(100% - 2em))",
        });
        this.okButton = this.query("[data-tv-about-ok]");
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        if (this.okButton) {
            this.okButton.addEventListener("click", () => this.close());
        }
    }
}

class TVAsciiTableDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const chart = new TVListViewer({
            className: "tv-ascii-chart",
            attrs: { "data-tv-ascii-chart": true },
        });
        const report = new TVStaticText({
            className: "tv-ascii-report",
            attrs: { "data-tv-ascii-report": true },
        });
        super({
            desktop,
            ariaLabel: "ASCII Table",
            title: "ASCII Chart",
            bodyClass: "tv-ascii-body",
            closeAttrs: {
                "data-tv-ascii-close": true,
                "aria-label": "Close ASCII table",
            },
            bodyMarkup: [chart.renderMarkup(), report.renderMarkup()],
            footerMarkup: TVDialog.footerMarkup(),
            width: "34ch",
            height: "min(12em, calc(100% - 2em))",
            left: "4ch",
            top: "3em",
        });
        this.selectedCode = 0;
        this.chart = this.query("[data-tv-ascii-chart]");
        this.report = this.query("[data-tv-ascii-report]");
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        if (this.chart) {
            this.chart.addEventListener("click", (event) => this.onCellEvent(event));
            this.chart.addEventListener("focusin", (event) => this.onCellEvent(event));
            this.chart.addEventListener("mousemove", (event) => {
                if (event.buttons & 1) {
                    this.onCellEvent(event);
                }
            });
        }
        document.addEventListener("keydown", (event) => this.onKeyDown(event));
        this.renderChart();
    }

    open() {
        super.open();
        this.renderChart();
    }

    renderChart() {
        if (!this.chart) {
            return;
        }
        const items = [];
        for (let code = 0; code < 256; code += 1) {
            const selected = code === this.selectedCode ? " is-selected" : "";
            items.push(
                `<button type="button" class="tv-ascii-cell${selected}" data-tv-ascii-code="${code}" aria-label="ASCII ${code}">${escapeHtml(displayCp437Char(code))}</button>`
            );
        }
        this.chart.innerHTML = items.join("");
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

    onCellEvent(event) {
        const cell = event.target.closest("[data-tv-ascii-code]");
        if (!cell) {
            return;
        }
        const code = Number.parseInt(cell.getAttribute("data-tv-ascii-code"), 10);
        if (!Number.isInteger(code) || code < 0 || code > 255) {
            return;
        }
        this.selectCode(code);
    }

    selectCode(code) {
        this.selectedCode = code;
        if (this.chart) {
            this.chart.querySelectorAll("[data-tv-ascii-code]").forEach((element) => {
                const cellCode = Number.parseInt(element.getAttribute("data-tv-ascii-code"), 10);
                element.classList.toggle("is-selected", cellCode === code);
            });
        }
        this.updateReport(code);
    }

    updateReport(code) {
        if (!this.report) {
            return;
        }
        const char = code === 0 ? " " : displayCp437Char(code);
        const decimal = String(code).padStart(3, " ");
        const hex = code.toString(16).toUpperCase().padStart(2, "0");
        this.report.textContent = `  Char: ${char} Decimal: ${decimal} Hex ${hex}`.padEnd(32, " ");
    }
}

class TVCalculatorDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
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
        const buttonsMarkup = buttonKeys.map(([key, label, aria]) =>
            new TVButton({
                baseClass: "tv-calc-button",
                attrs: {
                    "data-tv-calc-key": key,
                    "aria-label": `Calculator key ${aria}`,
                },
                labelMarkup: escapeHtml(label),
            }).renderMarkup()
        ).join("");
        const calcMain = new TVGroup({
            className: "tv-calc-main",
            children: [
                new TVStaticText({
                    className: "tv-calc-display",
                    attrs: { "data-tv-calc-display": true, "aria-live": "polite" },
                }),
                new TVGroup({
                    className: "tv-calc-keypad",
                    html: buttonsMarkup,
                }),
            ],
        }).renderMarkup();

        super({
            desktop,
            ariaLabel: "Calculator",
            title: "Calculator",
            closeAttrs: {
                "data-tv-calc-close": true,
                "aria-label": "Close calculator",
            },
            bodyMarkup: calcMain,
            footerMarkup: TVDialog.footerMarkup(),
            width: "24ch",
            height: "min(15em, calc(100% - 2em))",
            left: "5ch",
            top: "3em",
        });
        this.buttonValueMap = buttonValueMap;
        this.status = "first";
        this.number = "0";
        this.sign = " ";
        this.operate = "=";
        this.operand = 0;
        this.display = this.query("[data-tv-calc-display]");
        this.buttons = this.queryAll("[data-tv-calc-key]");
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bind();
        this.updateDisplay();
    }

    bind() {
        this.buttons.forEach((button) => {
            button.addEventListener("click", () => {
                const token = button.getAttribute("data-tv-calc-key") || "";
                this.calcKey(this.buttonValueMap[token] || token);
            });
        });
        document.addEventListener("keydown", (event) => this.onKeyDown(event));
        document.addEventListener("keyup", (event) => this.onKeyUp(event));
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

    onKeyUp(event) {
        if (!this.isActive()) {
            return;
        }
        if (event.key === "Enter" || event.key === "Backspace" || event.key === "Escape") {
            event.preventDefault();
            event.stopPropagation();
        }
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
        if (!this.display) {
            return;
        }
        const width = 18;
        const lead = Math.max(0, width - this.number.length - 2);
        const text = `${" ".repeat(lead)}${this.sign}${this.number} `;
        this.display.textContent = text.slice(-width).padEnd(width, " ");
    }
}

class TVCalendarDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const now = new Date();
        const calendarMain = new TVGroup({
            className: "tv-calendar-main",
            children: [
                new TVGroup({
                    className: "tv-calendar-header",
                    children: [
                        new TVStaticText({
                            attrs: { "data-tv-calendar-caption": true },
                        }),
                        new TVButton({
                            dialog: false,
                            className: "tv-calendar-arrow",
                            attrs: {
                                type: "button",
                                "data-tv-calendar-prev": true,
                                "aria-label": "Previous month",
                            },
                            labelMarkup: escapeHtml(displayCp437Char(30)),
                        }),
                        new TVStaticText({
                            attrs: { "aria-hidden": "true" },
                            text: "  ",
                        }),
                        new TVButton({
                            dialog: false,
                            className: "tv-calendar-arrow",
                            attrs: {
                                type: "button",
                                "data-tv-calendar-next": true,
                                "aria-label": "Next month",
                            },
                            labelMarkup: escapeHtml(displayCp437Char(31)),
                        }),
                    ],
                }),
                new TVStaticText({
                    text: "Su Mo Tu We Th Fr Sa",
                }),
                new TVStaticText({
                    className: "tv-calendar-grid",
                    attrs: { "data-tv-calendar-grid": true },
                }),
            ],
        }).renderMarkup();
        super({
            desktop,
            windowClass: "tv-calendar-window",
            ariaLabel: "Calendar",
            title: "Calendar",
            bodyClass: "tv-calendar-body",
            closeAttrs: {
                "data-tv-calendar-close": true,
                "aria-label": "Close calendar",
            },
            bodyMarkup: calendarMain,
            footerMarkup: TVDialog.footerMarkup(),
            width: "27ch",
            height: "min(11em, calc(100% - 2em))",
            left: "4ch",
            top: "3em",
        });
        this.caption = this.query("[data-tv-calendar-caption]");
        this.grid = this.query("[data-tv-calendar-grid]");
        this.prevButton = this.query("[data-tv-calendar-prev]");
        this.nextButton = this.query("[data-tv-calendar-next]");
        this.curYear = now.getFullYear();
        this.curMonth = now.getMonth() + 1;
        this.curDay = now.getDate();
        this.year = this.curYear;
        this.month = this.curMonth;
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bind();
        this.render();
    }

    bind() {
        if (this.prevButton) {
            this.prevButton.addEventListener("click", () => this.changeMonth(-1));
        }
        if (this.nextButton) {
            this.nextButton.addEventListener("click", () => this.changeMonth(1));
        }
        document.addEventListener("keydown", (event) => this.onKeyDown(event));
    }

    onKeyDown(event) {
        if (!this.isActive()) {
            return;
        }
        if (event.target && event.target.closest("input, textarea, select")) {
            return;
        }
        if (event.key === "+" || event.key === "ArrowDown") {
            event.preventDefault();
            this.changeMonth(1);
        } else if (event.key === "-" || event.key === "ArrowUp") {
            event.preventDefault();
            this.changeMonth(-1);
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
        this.render();
    }

    daysInMonth(month, year) {
        return DAYS_IN_MONTH[month] + (month === 2 && isLeapYear(year) ? 1 : 0);
    }

    render() {
        if (!this.grid || !this.caption) {
            return;
        }
        this.caption.textContent = `${MONTH_NAMES[this.month].padStart(9, " ")} ${String(this.year).padStart(4, " ")}`;
        const first = 1 - dayOfWeek(1, this.month, this.year);
        const days = this.daysInMonth(this.month, this.year);
        const cells = [];
        let current = first;
        for (let row = 0; row < 6; row += 1) {
            for (let col = 0; col < 7; col += 1) {
                const inMonth = current >= 1 && current <= days;
                const isToday = inMonth
                    && this.year === this.curYear
                    && this.month === this.curMonth
                    && current === this.curDay;
                cells.push(
                    `<span class="tv-calendar-cell${isToday ? " is-current" : ""}${!inMonth ? " is-empty" : ""}">${inMonth ? String(current).padStart(2, " ") : "  "}</span>`
                );
                current += 1;
            }
        }
        this.grid.innerHTML = cells.join("");
    }
}

class TVColorsDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const okButton = new TVButton({
            className: "is-default",
            attrs: { "data-tv-colors-ok": true },
            label: '~O~K',
        });
        const cancelButton = new TVButton({
            attrs: { "data-tv-colors-cancel": true },
            label: '~C~ancel',
        });
        const resetButton = new TVButton({
            attrs: { "data-tv-colors-reset": true },
            label: '~R~eset',
        });
        const buttonStrip = new TVButtonStrip({
            className: "tv-colors-dialog-buttons",
            buttons: [okButton, resetButton, cancelButton],
        }).renderMarkup();
        const groupTitle = new TVLabel({
            text: "~G~roup",
            hotkey: true,
        }).renderMarkup();
        const itemTitle = new TVLabel({
            text: "~I~tem",
            hotkey: true,
        }).renderMarkup();
        const fgTitle = new TVLabel({
            text: "~F~oreground",
            hotkey: true,
        }).renderMarkup();
        const bgTitle = new TVLabel({
            text: "~B~ackground",
            hotkey: true,
        }).renderMarkup();
        const sampleTitle = new TVStaticText({
            text: "Text",
        }).renderMarkup();
        super({
            desktop,
            ariaLabel: "Colors",
            title: "Colors",
            closeAttrs: {
                "data-tv-colors-close": true,
                "aria-label": "Close colors dialog",
            },
            bodyMarkup: `
                <div class="tv-colors-main">
                    <div class="tv-colors-panels">
                        <div class="tv-colors-column">
                            ${groupTitle}
                            ${TVVerticalListViewer.renderMarkup({
                                rootClass: "tv-colors-listviewer",
                                rootAttrs: { "data-tv-colors-groups": true },
                                viewportClass: "tv-colors-list-viewport",
                            })}
                        </div>
                        <div class="tv-colors-column">
                            ${itemTitle}
                            ${TVVerticalListViewer.renderMarkup({
                                rootClass: "tv-colors-listviewer",
                                rootAttrs: { "data-tv-colors-items": true },
                                viewportClass: "tv-colors-list-viewport",
                            })}
                        </div>
                        <div class="tv-colors-side">
                            ${fgTitle}
                            <div class="tv-colors-selector" data-tv-colors-foreground></div>
                            ${bgTitle}
                            <div class="tv-colors-selector is-background" data-tv-colors-background></div>
                            ${sampleTitle}
                            <div class="tv-colors-display" data-tv-colors-display></div>
                        </div>
                    </div>
                    ${buttonStrip}
                </div>
            `,
            footerMarkup: TVDialog.footerMarkup(),
            width: "61ch",
            height: "min(18em, calc(100% - 2em))",
            left: "3ch",
            top: "2em",
        });
        this.groupList = this.query("[data-tv-colors-groups]");
        this.itemList = this.query("[data-tv-colors-items]");
        this.foreground = this.query("[data-tv-colors-foreground]");
        this.background = this.query("[data-tv-colors-background]");
        this.display = this.query("[data-tv-colors-display]");
        this.okButton = this.query("[data-tv-colors-ok]");
        this.resetButton = this.query("[data-tv-colors-reset]");
        this.cancelButton = this.query("[data-tv-colors-cancel]");
        this.groupBox = new TVVerticalListViewer(this.groupList, {
            itemClassName: "tv-colors-list-item",
            itemAttrName: "data-tv-colors-group",
            renderItemContent: (group) => escapeHtml(group.name),
        });
        this.itemBox = new TVVerticalListViewer(this.itemList, {
            itemClassName: "tv-colors-list-item",
            itemAttrName: "data-tv-colors-item",
            renderItemContent: (item) => escapeHtml(item.name),
        });
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
        if (this.foreground) {
            this.foreground.addEventListener("click", (event) => this.onSelectorClick(event, "fg"));
        }
        if (this.background) {
            this.background.addEventListener("click", (event) => this.onSelectorClick(event, "bg"));
        }
        if (this.okButton) {
            this.okButton.addEventListener("click", () => this.confirm());
        }
        if (this.resetButton) {
            this.resetButton.addEventListener("click", () => this.resetPalette());
        }
        if (this.cancelButton) {
            this.cancelButton.addEventListener("click", () => this.cancel());
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

    onSelectorClick(event, type) {
        const button = event.target.closest("[data-tv-color-index]");
        if (!button) {
            return;
        }
        const colorIndex = Number.parseInt(button.getAttribute("data-tv-color-index"), 10);
        if (!Number.isInteger(colorIndex)) {
            return;
        }
        const group = this.pendingPalette[this.selectedGroup];
        if (!group) {
            return;
        }
        const item = group.items[group.index] || group.items[0];
        if (!item) {
            return;
        }
        if (type === "fg") {
            item.attr = (item.attr & 0xF0) | (colorIndex & 0x0F);
        } else {
            item.attr = ((colorIndex & 0x0F) << 4) | (item.attr & 0x0F);
        }
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

    resetPalette() {
        applyThemePreset(TV.getActiveThemePreset(), false);
        this.pendingPalette = cloneColorPalette(buildPaletteFromCurrentStyle());
        applyColorPalette(this.pendingPalette, false);
        this.renderGroups();
        this.renderItems();
        this.renderSelectors();
        this.renderDisplay();
        window.requestAnimationFrame(() => {
            this.groupBox.updateScrollbar();
            this.itemBox.updateScrollbar();
        });
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
        if (this.foreground) {
            this.foreground.innerHTML = this.renderSelectorCells(16, fg);
        }
        if (this.background) {
            this.background.innerHTML = this.renderSelectorCells(8, bg);
        }
    }

    renderSelectorCells(count, selected) {
        const marker = displayCp437Char(8);
        const icon = displayCp437Char(219).repeat(3);
        const cells = [];
        for (let index = 0; index < count; index += 1) {
            const isSelected = index === selected;
            cells.push(`
                <button
                    type="button"
                    class="tv-color-cell${isSelected ? " is-selected" : ""}"
                    data-tv-color-index="${index}"
                    style="--tv-color-cell:${DOS_COLORS[index]};"
                    aria-label="Color ${index}"
                >${escapeHtml(isSelected ? `${displayCp437Char(219)}${marker}${displayCp437Char(219)}` : icon)}</button>
            `);
        }
        return cells.join("");
    }

    renderDisplay() {
        if (!this.display) {
            return;
        }
        const item = this.selectedItem();
        if (!item) {
            return;
        }
        const fg = dosColor(item.attr, 0);
        const bg = dosColor(item.attr, 4);
        this.display.innerHTML = `<span class="tv-colors-display-sample" style="color:${fg};background:${bg};">${escapeHtml("Text Text Text ")}</span>`;
    }
}

class TVSearchDialog extends TVDialog {
    constructor(desktop = document.querySelector(".tv-desktop") || document.body) {
        const okButton = new TVButton({
            className: "is-default",
            attrs: { "data-tv-search-ok": true },
            label: '~O~K',
        });
        const cancelButton = new TVButton({
            attrs: { "data-tv-search-cancel": true },
            label: '~C~ancel',
        });
        const buttonStrip = new TVButtonStrip({
            className: "tv-search-buttons",
            buttons: [okButton, cancelButton],
        });
        const searchMain = new TVGroup({
            className: "tv-search-main",
            children: [
                new TVGroup({
                    tag: "label",
                    columns: "auto minmax(0,1fr)",
                    gap: "1ch",
                    align: "center",
                    children: [
                        new TVLabel({
                            text: "Find:",
                        }),
                        new TVInputLine({
                            attrs: {
                                spellcheck: "false",
                                autocomplete: "off",
                                "data-tv-search-input": true,
                            },
                        }),
                    ],
                }),
                new TVStaticText({
                    text: "Enter text and choose a topic.",
                }),
                new TVGroup({
                    className: "tv-search-results-panel",
                    children: [
                        TVVerticalListViewer.renderMarkup({
                            rootClass: "tv-search-results-scroll",
                            rootAttrs: { "data-tv-search-results": true },
                            viewportClass: "tv-search-results",
                        }),
                    ],
                }),
            ],
        }).renderMarkup();

        super({
            desktop,
            ariaLabel: "Search help",
            title: "Find",
            bodyClass: "tv-search-body",
            closeAttrs: {
                "data-tv-search-close": true,
                "aria-label": "Close search",
            },
            bodyMarkup: `
                ${searchMain}
                ${buttonStrip.renderMarkup()}
            `,
            footerMarkup: TVDialog.footerMarkup(),
            width: "76ch",
            height: "min(26em, calc(100% - 2ch))",
            left: "2ch",
            top: "2em",
        });
        this.searchData = window.TV_SEARCH_INDEX && Array.isArray(window.TV_SEARCH_INDEX.topics)
            ? window.TV_SEARCH_INDEX
            : { topics: [] };
        this.input = this.query("[data-tv-search-input]");
        this.okButton = this.query("[data-tv-search-ok]");
        this.cancelButton = this.query("[data-tv-search-cancel]");
        this.resultsBox = new TVVerticalListViewer(this.query("[data-tv-search-results]"), {
            itemClassName: "tv-search-result",
            itemAttrName: "data-tv-search-index",
            renderItemMarkup: (entry, index, selected) => {
                const terms = entry.index_terms && entry.index_terms.length
                    ? `Index: ${entry.index_terms.slice(0, 4).join(", ")}`
                    : entry.title;
                return `
                    <button type="button" class="tv-search-result${selected ? " is-selected" : ""}" data-tv-search-index="${index}">
                        <span class="tv-search-result-title">${escapeHtml(entry.title)}</span>
                        <span class="tv-search-result-meta">${escapeHtml(terms)}</span>
                        <span class="tv-search-result-preview">${escapeHtml(entry.preview || entry.text.slice(0, 180))}</span>
                    </button>
                `;
            },
        });
        this.results = this.resultsBox.viewport;
        this.matches = [];
        this.selectedIndex = -1;
        this.bindCommonClose(() => this.close());
        this.bindDrag();
        this.bind();
    }

    bind() {
        if (!this.root) {
            return;
        }

        this.input.addEventListener("input", () => this.renderResults(this.input.value));
        this.resultsBox.bind({
            onSelect: (_entry, index) => {
                this.selectIndex(index);
                this.openSelected();
            },
            onActivate: (_entry, index) => {
                this.selectIndex(index);
                this.openSelected();
            },
        });
        this.okButton.addEventListener("click", () => this.openSelected());
        this.cancelButton.addEventListener("click", () => this.close());
        document.addEventListener("keydown", (event) => this.onKeyDown(event));
    }

    onKeyDown(event) {
        if (event.key === "F3") {
            event.preventDefault();
            if (this.isOpen()) {
                this.input.focus();
                this.input.select();
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
        super.open();
        if (typeof initialQuery === "string") {
            this.input.value = initialQuery;
        }
        this.renderResults(this.input.value);
        window.requestAnimationFrame(() => this.resultsBox.updateScrollbar());
        this.input.focus();
        this.input.select();
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
        this.okButton.classList.toggle("is-active", this.selectedIndex >= 0);
    }

    openSelected() {
        if (this.selectedIndex < 0 || this.selectedIndex >= this.matches.length) {
            return;
        }
        window.location.href = this.matches[this.selectedIndex].href;
    }

    renderResults(query) {
        if (!this.results) {
            return;
        }
        this.matches = [];
        this.selectedIndex = -1;
        this.okButton.classList.remove("is-active");
        if (!this.searchData.topics.length) {
            this.results.innerHTML = "<div class=\"tv-search-empty\">Search index is not available for this help file.</div>";
            this.resultsBox.updateScrollbar();
            fillBorders();
            return;
        }

        const trimmed = query.trim();
        if (!trimmed) {
            this.results.innerHTML = "<div class=\"tv-search-empty\">Type text to search across all generated topics.</div>";
            this.resultsBox.updateScrollbar();
            fillBorders();
            return;
        }

        const matches = this.search(trimmed);
        if (!matches.length) {
            this.results.innerHTML = `<div class="tv-search-empty">No matches for "${escapeHtml(trimmed)}".</div>`;
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
    TVAsciiTableDialog,
    TVCalculatorDialog,
    TVCalendarDialog,
    TVColorsDialog,
    TVSearchDialog,
});
})();
