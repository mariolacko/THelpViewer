# MIDI synthesizer assets

The CD/MIDI Player starts fetching these assets when its window opens. Audio
initialization still starts on Play, as required by browser autoplay policies. They are kept
under the site's `/assets/midi/synth/` path rather than copied into every
generated standalone HELP bundle.

- `js-synthesizer.min.js`: js-synthesizer 1.13.0, BSD-3-Clause, from
  `https://www.npmjs.com/package/js-synthesizer/v/1.13.0`.
- `libfluidsynth-2.4.6-with-libsndfile.js`: FluidSynth WASM build included in
  the same npm release, LGPL-2.1; source:
  `https://github.com/jet2jet/fluidsynth-emscripten`.
- `FluidR3Mono_GM.sf3`: MuseScore's FluidR3Mono General MIDI SoundFont, from
  `https://github.com/musescore/MuseScore/blob/1a4bd0feb9378cd145418dbcb40246980ca1013d/share/sound/FluidR3Mono_GM.sf3`.
  The supplied license/attribution is in `LICENSE.FluidR3Mono.md`.
- `FluidR3Mono_GM.sf3.br`: Brotli-compressed copy of that same file. The FastAPI
  asset handler sends it when the browser accepts Brotli, with the original
  `.sf3` as fallback. Regenerate with
  `brotli -q 5 -o FluidR3Mono_GM.sf3.br FluidR3Mono_GM.sf3` if the SoundFont
  changes, and update the content-hash URL in both `tv-dialogs.js` copies.
  The versioned URL permits one-year immutable caching on the server. The
  player records script, transfer, synthesizer-load and Play-to-ready times
  in its `synth.loadingTimes` object for performance comparisons.

SHA-256 of the exact vendored files:

```text
2aacd036d7058d40a371846ef2f5dc5f130d648ab3837fe2626591ba49a71254  FluidR3Mono_GM.sf3
b79968edfd9ece55090828ac8f2072af86b3e5beaca2e5e7a17d24184eaf2843  FluidR3Mono_GM.sf3.br
ea3932ef941246960064817bced92ab80a17d9c9e8404cc59fee6cacd1acb6d7  js-synthesizer.min.js
c108b7f00ed348892d46f9e6236618d76ae7f3d2b6cb860b2990c0c2ce9dc67c  libfluidsynth-2.4.6-with-libsndfile.js
```

The source code for the FluidSynth build is available at the link above. Keep
the three accompanying license notices when redistributing these assets.
