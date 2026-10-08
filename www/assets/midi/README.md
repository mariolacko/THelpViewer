# MIDI Samples

These legacy demo files remain bundled for direct file links and existing
links. The MIDI Player playlist now comes from the server's game-MIDI catalog
in `var/midi/library.sqlite3`; see the Game MIDI library section in the root
README.

The player uses the bundled FluidSynth-based synthesizer and FluidR3Mono
General MIDI SoundFont in [`synth/`](synth/README.md). It plays the instruments
and percussion assigned in each MIDI file rather than one oscillator sound.
The playback gauge supports click-to-seek. At the end of a track, the player
starts the next track; the `Random next track` checkbox under More changes
that to a random selection. MIDI downloads continue in the background, with
an automatic progress dialog rather than a Downloads button in the player.
The old Commons and ToBeFree external presets were
removed from the dialog.

To verify the downloaded files:

```sh
shasum -a 256 *.mid
```

Original demo files:

These are original THelpViewer demo loops, not arrangements of existing songs.

| File | Notes |
| --- | --- |
| `modern-neon-grid.mid` | Original modern demo loop |
| `modern-byte-runner.mid` | Original modern demo loop |
| `modern-soft-circuit.mid` | Original modern demo loop |
| `modern-terminal-drift.mid` | Original modern demo loop |
| `modern-night-cache.mid` | Original modern demo loop |
| `modern-pixel-rain.mid` | Original modern demo loop |
| `modern-vector-sunrise.mid` | Original modern demo loop |
| `modern-copper-lanes.mid` | Original modern demo loop |
| `modern-glass-towers.mid` | Original modern demo loop |
| `modern-data-stream.mid` | Original modern demo loop |

OpenGameArt CC0 files:

These files are listed as CC0 on their OpenGameArt source pages.

| File | Source |
| --- | --- |
| `oga-komiku-disco-challenge.mid` | `https://opengameart.org/content/helice-incredible-adventure-fantasy-disco-rpg-battle-music-and-midi-files-pack` |
| `oga-komiku-pop-city.mid` | `https://opengameart.org/content/helice-incredible-adventure-fantasy-disco-rpg-battle-music-and-midi-files-pack` |
| `oga-komiku-big-dancefloor.mid` | `https://opengameart.org/content/helice-incredible-adventure-fantasy-disco-rpg-battle-music-and-midi-files-pack` |
| `oga-komiku-everything-is-groovy.mid` | `https://opengameart.org/content/helice-incredible-adventure-fantasy-disco-rpg-battle-music-and-midi-files-pack` |
| `oga-komiku-road-1-chill.mid` | `https://opengameart.org/content/helice-incredible-adventure-fantasy-disco-rpg-battle-music-and-midi-files-pack` |
| `oga-komiku-road-1-fight.mid` | `https://opengameart.org/content/helice-incredible-adventure-fantasy-disco-rpg-battle-music-and-midi-files-pack` |
| `oga-komiku-road-2-chill.mid` | `https://opengameart.org/content/helice-incredible-adventure-fantasy-disco-rpg-battle-music-and-midi-files-pack` |
| `oga-komiku-road-3-fight.mid` | `https://opengameart.org/content/helice-incredible-adventure-fantasy-disco-rpg-battle-music-and-midi-files-pack` |
| `oga-komiku-road-4-fight.mid` | `https://opengameart.org/content/helice-incredible-adventure-fantasy-disco-rpg-battle-music-and-midi-files-pack` |
| `oga-komiku-we-have-to-dance-together.mid` | `https://opengameart.org/content/helice-incredible-adventure-fantasy-disco-rpg-battle-music-and-midi-files-pack` |
| `oga-komiku-dropda-basstion.mid` | `https://opengameart.org/content/helice-incredible-adventure-fantasy-disco-rpg-battle-music-and-midi-files-pack` |
| `oga-komiku-the-test.mid` | `https://opengameart.org/content/helice-incredible-adventure-fantasy-disco-rpg-battle-music-and-midi-files-pack` |
| `oga-roppy-broken-arm.mid` | `https://opengameart.org/content/original-midi-album` |
| `oga-roppy-casual-afternoon.mid` | `https://opengameart.org/content/original-midi-album` |
| `oga-roppy-icy-garden.mid` | `https://opengameart.org/content/original-midi-album` |
| `oga-roppy-journey-forgotten.mid` | `https://opengameart.org/content/original-midi-album` |
| `oga-roppy-no-one.mid` | `https://opengameart.org/content/original-midi-album` |
| `oga-roppy-standardized-anxiety.mid` | `https://opengameart.org/content/original-midi-album` |
| `oga-roppy-without-time.mid` | `https://opengameart.org/content/original-midi-album` |
| `oga-nene-long-away-home.mid` | `https://opengameart.org/content/long-away-home-8bit` |
| `oga-tozan-stringsvop.mid` | `https://opengameart.org/content/stringsvop` |

Mutopia Project files:

Source: Mutopia Project, https://www.mutopiaproject.org/

| File | Mutopia source |
| --- | --- |
| `vocalise-1.mid` | `https://www.mutopiaproject.org/ftp/AbtF/Vocalise1/Vocalise1.mid` |
| `when-the-swallows-homeward-fly.mid` | `https://www.mutopiaproject.org/ftp/AbtF/swallows/swallows.mid` |
| `andre-sonatine-op34-1.mid` | `https://www.mutopiaproject.org/ftp/AndreJ/O34/andre-sonatine/andre-sonatine.mid` |
| `giselle.mid` | `https://www.mutopiaproject.org/ftp/AdamA/giselle/giselle.mid` |
| `minuit-chretiens.mid` | `https://www.mutopiaproject.org/ftp/AdamA/minuit_chretiens/minuit_chretiens.mid` |
| `blue-mountains.mid` | `https://www.mutopiaproject.org/ftp/AdamsS/bluemtns/bluemtns.mid` |
| `rumores-de-la-caleta.mid` | `https://www.mutopiaproject.org/ftp/AlbenizIMF/O71/Rumores_de_la-caleta/Rumores_de_la-caleta.mid` |
| `alkan-op31-1.mid` | `https://www.mutopiaproject.org/ftp/AlkanCV/O31/alkan-op31-1/alkan-op31-1.mid` |
| `alkan-op31-2.mid` | `https://www.mutopiaproject.org/ftp/AlkanCV/O31/alkan-op31-2/alkan-op31-2.mid` |
| `alkan-toccatina.mid` | `https://www.mutopiaproject.org/ftp/AlkanCV/O75/toccatina/toccatina.mid` |
| `cpe-bach-rondo.mid` | `https://www.mutopiaproject.org/ftp/BachCPE/cpe-bach-rondo/cpe-bach-rondo.mid` |
| `bach-bwv-259.mid` | `https://www.mutopiaproject.org/ftp/BachJS/BWV259/bwv-259/bwv-259.mid` |
| `bach-bwv-269.mid` | `https://www.mutopiaproject.org/ftp/BachJS/BWV269/bwv_269/bwv_269.mid` |
| `bach-bwv-347.mid` | `https://www.mutopiaproject.org/ftp/BachJS/BWV347/bwv347/bwv347.mid` |
| `bach-anna-magdalena-20a.mid` | `https://www.mutopiaproject.org/ftp/BachJS/BWV515/anna-magdalena-20a/anna-magdalena-20a.mid` |
| `bach-invention-01.mid` | `https://www.mutopiaproject.org/ftp/BachJS/BWV772/bach-invention-01/bach-invention-01.mid` |
| `bach-invention-02.mid` | `https://www.mutopiaproject.org/ftp/BachJS/BWV773/bach-invention-02/bach-invention-02.mid` |
| `bach-invention-03.mid` | `https://www.mutopiaproject.org/ftp/BachJS/BWV774/bach-invention-03/bach-invention-03.mid` |
| `bach-invention-04.mid` | `https://www.mutopiaproject.org/ftp/BachJS/BWV775/bach-invention-04/bach-invention-04.mid` |
| `bach-invention-05.mid` | `https://www.mutopiaproject.org/ftp/BachJS/BWV776/bach-invention-05/bach-invention-05.mid` |
| `bach-invention-06.mid` | `https://www.mutopiaproject.org/ftp/BachJS/BWV777/bach-invention-06/bach-invention-06.mid` |
| `bach-invention-07.mid` | `https://www.mutopiaproject.org/ftp/BachJS/BWV778/bach-invention-07/bach-invention-07.mid` |
| `bach-invention-08.mid` | `https://www.mutopiaproject.org/ftp/BachJS/BWV779/bach-invention-08/bach-invention-08.mid` |
| `bach-invention-09.mid` | `https://www.mutopiaproject.org/ftp/BachJS/BWV780/bach-invention-09/bach-invention-09.mid` |
| `bach-invention-10.mid` | `https://www.mutopiaproject.org/ftp/BachJS/BWV781/bach-invention-10/bach-invention-10.mid` |
| `bach-invention-11.mid` | `https://www.mutopiaproject.org/ftp/BachJS/BWV782/bach-invention-11/bach-invention-11.mid` |
| `bach-invention-12.mid` | `https://www.mutopiaproject.org/ftp/BachJS/BWV783/bach-invention-12/bach-invention-12.mid` |
| `bach-invention-13.mid` | `https://www.mutopiaproject.org/ftp/BachJS/BWV784/bach-invention-13/bach-invention-13.mid` |
| `bach-invention-14.mid` | `https://www.mutopiaproject.org/ftp/BachJS/BWV785/bach-invention-14/bach-invention-14.mid` |
| `bach-invention-15.mid` | `https://www.mutopiaproject.org/ftp/BachJS/BWV786/bach-invention-15/bach-invention-15.mid` |
