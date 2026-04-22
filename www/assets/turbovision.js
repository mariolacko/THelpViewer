// Turbo Vision bootstrap for generated help pages.
(function () {
"use strict";
const TV = window.THelpViewerTV = window.THelpViewerTV || {};
function init() {
    if (typeof TV.initTurboVision === "function") {
        TV.initTurboVision();
    }
}
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
} else {
    init();
}
})();
