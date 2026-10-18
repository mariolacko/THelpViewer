# Bundled DOS emulator

DOSBox backend based on npm `emulators` **8.5.2**, with THelp's native
text-screen bridge:

- Package: https://registry.npmjs.org/emulators/-/emulators-8.5.2.tgz
- Upstream: https://github.com/js-dos/emulators
- Package git commit: `6bbf0925d221a7304ea8e0dda1e89b8dc01569b2`
- npm tarball SHA-1: `f6974960e14505919b007e58fc37a345a7cac673`
- npm integrity: `sha512-XW+1SsuYd/egY1EmuOpq6k9kUqrGyoaN8o1sqkVvDJRFWy4lrCqst3of6TBZj1m//4aU/ZSt5VbqQBcRl+Uk1Q==`
- Licence: GPL-2.0; full text is [LICENSE.txt](LICENSE.txt).

Included runtime files: `emulators.js`, `wdosbox.js`, `wdosbox.wasm`,
`wlibzip.js`, `wlibzip.wasm`. Only the classic DOSBox worker backend is used;
DOSBox-X binaries, the js-dos player interface and player styles are not used.
The TVision/browser adapter is in `tv-dos.js` outside this vendor directory.
`wdosbox.js`/`wdosbox.wasm` are rebuilt with
[text-screen.cpp](../native/text-screen.cpp). `emulators.js` preserves the typed
`thelp-screen` message in its log transport; all ordinary logs remain unchanged.
`wlibzip.js`/`wlibzip.wasm` remain the upstream package binaries.

Matching upstream source snapshots and build scripts are provided for download:

- [emulators source](sources/emulators.tar.gz): commit above, including the
  TypeScript API, libzip, native wrapper and build instructions/scripts;
- [DOSBox source](sources/dosbox.tar.gz): pinned submodule commit
  `528578d5a6f76afd4d5ef4e722b5670826f1183a` from
  https://github.com/js-dos/dosbox;
- [Sokol source](sources/sokol.tar.gz): pinned submodule commit
  `fa3d7cbe9ca85b8b87824ac366c724cb0e33a6af` from
  https://github.com/floooh/sokol, with its own licence in that archive.

GitHub source archives do not recursively expand git submodules. To rebuild,
use the top-level build documentation and restore the pinned DOSBox/Sokol
contents under `native/dosbox` and `native/sokol-lib`, or check out the exact
upstream commit and initialise its submodules. Upstream optional backends have
their own dependencies; they are not shipped as runtime binaries here.
### Rebuilding the shipped classic backend

[build.py](../native/build.py) extracts these pinned sources to a fresh work
directory and applies the native hook and corresponding TypeScript protocol
edit. It builds only classic DOSBox/libzip (no optional SDL/Sokol backends),
appends the upstream worker footer and produces the modified API plus backend
JS/WASM in the output directory. It does not overwrite source archives.
With Docker, from the repository root:

```sh
dos_build_dir=$(mktemp -d)
docker run --rm --platform linux/amd64 \
  -v "$PWD/www/assets/dos:/assets:ro" -v "$dos_build_dir:/work" \
  emscripten/emsdk:4.0.8 \
  python3 /assets/native/build.py --work-dir /work/build --output-dir /work/output
```

The tested SDK image digest is
`sha256:92c97951b9a6835cb5da9592e9d95226f67e09ecd01a541d817a5b4801f235a4`.
Publish `emulators.js`, `wdosbox.js` and `wdosbox.wasm` together to both asset
trees, retaining the bridge/build sources and incrementing client cache keys.
The two API statements patched in the minified bundle correspond exactly to
the explicit `onLog` change recorded in the build script; no other API is changed.

Keep these source downloads and licence notices available when deploying or
redistributing the bundled emulator. FreeDOS software has separate package
licences/sources in the prepared C drive.
