# Rust Core pilot

Decision: retain the shipped C color mixer. Baseline: v0.2.0, commit `608005d48808af822c9c399477ed42ea439048c9`. The baseline NWA rebuilt byte-for-byte. The experimental workflow swaps the function only in its disposable CI checkout.

## Existing Tetris integration

Cargo builds the no_std Tetris static library for thumbv7em-none-eabihf with size optimization, LTO and panic abort. The Makefile extracts the reachable Rust code starting at the C ABI symbol `np_tetris_main`. The normal module tools then package the relocatable game and generate its launcher table entry. In `launcher/src/games.c`, `np_game_run` checks available RAM, copies the initial data, zeros BSS, sets the aligned heap boundary and calls the table entry. Tetris calls `numworks_utils::app::run(play)`. Its C wrapper establishes the game exit target, runs the callback and calls `np_app_end` on normal return or explicit leave. The launcher resumes control and backs up progress.

## Paired measurements

[ARM comparison and linked builds](https://github.com/Twil1ght-L4D2/TwiliPlay/actions/runs/45498540506) tested both routines against independent per-channel arithmetic across all 33 blend weights, boundary colors and seeded random pairs. All 5,841 cases passed per routine. The harness verified return and stack balance on each call.

| Measurement | Shipped C | Rust candidate |
|---|---:|---:|
| Standalone function bytes | 44 | 50 |
| Executed instructions per tested call | 13 | 15 |
| Installed package bytes | 2,319,740 | 2,319,956 |
| App RAM requirement | 133,384 | 133,384 |
| Conservative RAM headroom | 268 | 268 |

Instruction counts describe isolated ARM code in Unicorn. Whole-package sizes include link layout and other build outputs. The Rust candidate passed the package memory gates and the small-RAM emulator regression. This pilot contains no physical timing or FPS measurements. The normal build continues to compile the C implementation.
