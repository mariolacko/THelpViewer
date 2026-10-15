# HTML Assets

Presentation assets for the generated TurboVision-style HTML viewer:

- `turbovision.css` — window chrome, typography and layout
- `tv-core.js` — theme engine, utility functions and base TV widgets
- `tv-context-help.js` — shared UHF `TVHelpWindow`/`TVHelpViewer` and THelpViewer context-help loader
- `tv-dialogs.js` — standalone dialog windows (About, ASCII, Calculator, Calendar, MIDI, Colors, Search)
- `tv-content.js` — independent HELP/DOS/MIDI package dialogs sharing TVPackagesDialog
- `tv-context-help.json` — native UHF 2.0 topics and index for context-sensitive F1 Help
- `tv-games.js` — built-in game rules and dialogs
- `tv-screensaver.js` — idle screensaver
- `tv-shell.js` — application/menu/status shell, shared download menu and progress workflow
- `tv-bundle-app.js` — SPA bundle loader, window manager and docs viewer
- `turbovision.js` — bootstrap that starts the shell
- `fonts/` — local web fonts for authentic DOS/VGA look
- `midi/synth/` — synthesizer and SoundFont assets; playable tracks come from the server's MIDI catalog

## Fonts

Bundled bitmap fonts are from
[The Ultimate Oldschool PC Font Pack](https://int10h.org/oldschool-pc-fonts/)
by VileR:

- `Web437_IBM_VGA_8x16.woff`
- `WebPlus_IBM_VGA_8x16.woff`

Licensed under [CC BY-SA 4.0](fonts/LICENSE.TXT).
See `fonts/README.TXT` and `fonts/LICENSE.TXT` for details.
