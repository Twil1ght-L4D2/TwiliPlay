# Settings reader pilot

Keep the v0.2.0 C readers. Both implementations passed 196,618 host cases each, including every two-byte motion record, every theme ID with each version byte, every theme ID with each magic byte at version one, missing records and incorrect lengths. The pre-animation launcher at 2193c8b used the same theme format. A missing animation record defaults to on. An invalid theme ID is filtered by the existing theme caller.

The baseline reproduced the release SHA-256. Installed size grew from 2,319,740 to 2,319,788 bytes with the Rust readers. Both builds required 133,384 bytes of app RAM, leaving 268 bytes in the tightest tested configuration. The candidate passed save recovery and small-RAM ARM emulator tests. It introduced an unsafe pointer boundary to read the same two fixed-size records and demonstrated no additional validation benefit. Runtime speed and hardware behavior were not measured in this experiment.

The candidate patch applies only inside the disposable CI checkout. [Build and comparison](https://github.com/Twil1ght-L4D2/TwiliPlay/actions/runs/45500738749).
