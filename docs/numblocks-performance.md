# NumBlocks performance baseline

The production baseline is TwiliPlay v0.2.0 rebuilt from main commit `1d88a9caf5b83f71b2a6b2346bc76a670308f42b`. The Performance Foundation work for v0.3.0 adds host-side measurements. The 25-game N0120 executable has SHA-256 `d94a55ff1fc5f9442f5617aa955dad7baf3cb62db19eccfaf397ecf8e5a5e225`.

## Reproduce the walking replay

Use the Linux toolchain in `.github/actions/setup/action.yml` (xPack ARM GCC 15.2.1-1.1, nwlink 1.0.0, Python 3.12 and Unicorn 2.1.4). From the repository root run

```sh
NWLINK=nwlink make -j2 foundation
python3 tools/profile_numblocks.py build/foundation
```

The profiler launches NumBlocks from its catalogue entry with fresh emulator storage, creates a world with the existing save regression's input sequence, and samples the 1,500 virtual ms during which forward is held. Startup and Home/save are outside the sampling window. It reads frame and tick counters from the packaged game's RAM and maps program counters to functions using its matching intermediate ELF. Each sample represents one emulator instruction chunk. Sleep and firmware calls follow the emulator model. The percentages describe exclusive samples on this walk. They cannot establish hardware frame rate, time per instruction or performance in a different world.

| Rank | Function | Samples / 1,500 | Share | Work |
|---|---|---:|---:|---|
| 1 | `trace` | 322 | 21.5% | Advance a ray through the cached world and skip empty regions |
| 2 | `cell_hit` | 197 | 13.1% | Determine and shade the surface hit inside a nonempty cell |
| 3 | `render_frame` | 174 | 11.6% | Frame assembly and work inlined into the outer renderer |
| 4 | `light_box` | 97 | 6.5% | Update cached world lighting |
| 5 | `sample_at` | 66 | 4.4% | Sample the scene for the adaptive renderer |

The four individually identified rendering functions above account for 759 samples (50.6%). Other rendering helpers also appear lower in the profile. The game's counters advanced by **29 frames and 28 simulation ticks** within the window. Both fresh-storage runs matched every reported count, the final walking image (RGB565 SHA-256 `152a8ff0bd870ee70cd480a1d5854fb92b4fabc180d6f6fb3064cc1307c8e0cd`), and the saved world record (`cd91fd4e31aabc8830f0e75870adaef227971773f5a70497a43460ea3b4fc8d1`). [Repeated profile and build log](https://github.com/Twil1ght-L4D2/TwiliPlay/actions/runs/45562611284)

## Memory and compatibility

| N0120 measurement | Bytes |
|---|---:|
| NumBlocks installed flash including its previews | 377,052 |
| Of which previews | 11,428 |
| NumBlocks initialized data | 128 |
| NumBlocks BSS | 130,264 |
| Whole launcher footprint excluding games and shared components | 50,795 |
| Entire application installed / available | 2,319,740 / 2,555,904 |
| Required app RAM / strictest checked limit | 133,384 / 133,652 |

The module shares its arena with other games and declares zero additional heap reservation. Its block and light arrays each occupy 38,400 bytes (40 × 40 × 24). Together they account for 76,800 bytes of the BSS. The generator uses a separate 13,200-byte stack cache in the packaged configuration. The measured stack high-water mark was **25,436 bytes** on both runs, leaving 7,332 bytes in the emulated 32 KiB stack. The initial exploratory run lacked the stack paint and its 32,768-byte reading is invalid. The corrected stack watermark covers the entire session, including startup and Home. It is separate from the app-RAM budget.

The merged main build passed all three RAM gates (133,652, 148,928 and 153,676 bytes), the regression job and all 25 emulated launch checks. [N0120 regression and build results](https://github.com/Twil1ght-L4D2/TwiliPlay/actions/runs/45501709743) Five NumBlocks host test executables passed, including the packaged configuration, loading a world saved in another dimension, and an old world's terrain across the structure-generation change. The walking replay checks the saved world's header and progress, Home exit, stack guard, firmware RAM, and app-RAM cleanup.

## Fixed-step visual control

For a future A/B comparison, use the existing host player at a fixed simulation time so a faster renderer cannot move the player farther before the screenshot. This is a separate Overworld workload in the standalone host configuration. With GCC 14.2.0 on x86-64 Linux, two fresh runs gave identical counters and pixel files.

```sh
make -C games/numblocks host test
out=$(mktemp -d)
games/numblocks/build/play --seed 120 --time 6000 --frames 60 --ms-per-frame 50 \
  --keys 0-59:fwd --shots 0,30,59 --out "$out"
sha256sum "$out"/shot*.ppm
```

The host counters reported 7,744 traces and 62,345 cell steps per frame, or 8.1 steps per traced ray. The three PPM digests in frame order were

```text
2e9cd7e06a43e753b355508c418653520ec3265c233f4c3b5b6a03ac93c78444
8c0d22e8a1c8a156b0c5de9839d26584834d57f4055cf1892b516fb2f0bd9681
affcd2a8a45ca4a13600faa80c87770abe90f129db4f02bdf9c42c2ccce1449f
```

## First optimization to test

Try a small C change to the ordinary cell-step path of `trace`. It already selects the axis crossed at each step, but reconstructs the entry face from three floating-point differences when a cell can be hit. Prototype carrying the selected face forward on unambiguous crossings. Preserve the original resolution for edge/corner ties, rounding-sensitive crossings, the initial cell, and region jumps. Check the emitted Thumb-2 instructions for extra spills. This exchanges arithmetic at a potential hit for bookkeeping while stepping through empty cells, so a win needs measurement.

Compare equal camera poses and simulation ticks, including axis-aligned rays, exact ties, water, glass and partially filled blocks. Require equal baseline pixels, hit/depth results and world state at equivalent ticks, then measure ARM instructions per fixed frame across identical fixtures and repeat the packaged replay and memory gates. Keep the current code if it wins or if the candidate changes observable output.

A per-cell Rust FFI call would cross the ABI in the inner loop and need access to mutable hit state and several world arrays. The profile gives no measured advantage for that change. A future no_std Rust comparison could operate on a batch of rays through one call, after the C experiment isolates an arithmetic kernel worth comparing. This baseline contains no production optimization.
