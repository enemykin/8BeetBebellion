# 8BeetBebellion

A compatibility project for running **Linkin Park 8-Bit Rebellion!** on modern computers using a patched [touchHLE](https://github.com/touchHLE/touchHLE).

The project contains tools, documentation and a reproducible source patch. **No game IPA, artwork, music, extracted assets, saves or game binaries are distributed.** You must supply your own decrypted copy of the game.

## Current status

The working target is the **iPhone version 1.4.5**, bundle ID `com.alife.linkinpark`. Testing has been performed on macOS with Apple Silicon. Windows remains a project target, but this project's game compatibility changes have not been verified there.

Confirmed by manual testing:

- The game reaches the character editor and playable world.
- Map transitions and all internal entrances work in **Casino Row, City Center, The Beach, The West Side, Downtown, SoHo and The Park**.
- Character changes survive a restart. The poster mission's count and defaced posters persist after the save compatibility fix.
- Keyboard movement and attack work, including reversing direction during an attack.
- Double clicks in the center no longer unexpectedly open the menu or Profile.

The early LP splash has been fixed and checked through the title screen. A fix for double clicking The West Side on the map has passed a scripted game check; a user retest of that final fix is still pending.

**Still unverified:** full campaign completion, purchases and their persistence, home decoration, multiplayer, and full audio/video synchronization. Mouse-wheel scrolling for long menus is planned.

The local **iPad version 1.4.8 cannot run**: both ARM slices have `cryptid=1`, and touchHLE rejects the encrypted executable. Its declared iOS 6.0 requirement is also newer than touchHLE's supported app range. A decrypted, user-owned copy is needed before further compatibility testing.

See [CHANGELOG](CHANGELOG.md), the detailed [compatibility log](docs/COMPATIBILITY_LOG.md), [save/API audit](docs/SAVE_AND_API_AUDIT.md), and [roadmap](docs/ROADMAP.md). Referenced runtime logs are local evidence and are not included in this repository. README, CHANGELOG and the compatibility log are maintained in English.

## Setup and build

Requirements: Python 3.10+, Git, Rust/Cargo, CMake, and the platform build dependencies documented by [touchHLE](https://github.com/touchHLE/touchHLE). Install FFmpeg (`ffmpeg` and `ffplay` on `PATH`) for cutscenes.

```bash
git clone https://github.com/enemykin/8BeetBebellion.git
cd 8BeetBebellion
mkdir -p input reports
```

Place your own decrypted IPA in `input/`, then inspect it and run the tool tests:

```bash
python3 scripts/inspect_ipa.py 'input/8Bit Rebellion v1.4.5.ipa' --output reports/ipa-report.json
python3 -m unittest discover -s tests -v
```

Fetch the pinned upstream revision, apply the patch **once to a clean checkout**, and build:

```bash
python3 scripts/bootstrap_touchhle.py
git -C vendor/touchHLE apply ../../patches/touchhle-compatibility.patch
cd vendor/touchHLE
CMAKE_POLICY_VERSION_MINIMUM=3.5 cargo build --release --locked
```

The pinned commit is recorded in [config/touchhle.json](config/touchhle.json). Do not apply the patch again to an already patched checkout or update upstream without checking compatibility.

## Run on macOS

From the project root, double click **Start Bebellion.command**, or run:

```bash
./'Start Bebellion.command'
```

The launcher uses `input/8Bit Rebellion v1.4.5.ipa` by default. To select another local IPA:

```bash
BEBELLION_IPA='/absolute/path/to/your.ipa' ./'Start Bebellion.command'
```

Normal launches enable sound. Every run creates an ignored `reports/manual-run-*.log` with output, timestamps and the exit code. Guest saves remain in the local touchHLE sandbox.

The launcher enables `--landscape-content-layout`, keyboard controls, and the optional `--tolerate-nil-dictionary-keys` compatibility mode for the offline path. The latter deliberately skips malformed dictionary insertions and is not standard Foundation behavior.

Cutscenes play **inside the touchHLE window**: `ffmpeg` decodes video, and `ffplay` handles sound without a separate window. Both receive game data directly from the local IPA. Clicking the screen skips the active cutscene. If the required tools are missing, playback may be skipped; the log records the reason.

### Controls

| Input | Action |
| --- | --- |
| A / D or Left / Right | Hold movement left / right |
| Space | Attack |
| W or Up | Enter the available door when its action icon is visible |
| Escape | Open / close the side menu |
| Mouse / touch | Normal game interaction; click to skip a cutscene |

Letter keys use physical key positions, including under English and Russian layouts. Door activation follows the game's own command and does not depend on mouse position. Game-specific commands and save compatibility fixes are restricted to the inspected 1.4.5 bundle.

## Repository layout

```text
config/touchhle.json                Pinned upstream revision
patches/touchhle-compatibility.patch Source changes against that revision
scripts/bootstrap_touchhle.py       Fetch the upstream source
scripts/inspect_ipa.py              Inspect a local IPA without publishing its assets
tests/                             Tool tests
docs/                              Research, evidence and roadmap
CHANGELOG.md                       Changes and validation status
Start Bebellion.command             macOS launcher
```

`input/`, generated reports, game saves, build output and the upstream checkout are local only. Agent instruction files are also excluded from publication.

## Scope and third-party code

The first priority is compatibility with the original application. A remake would require a separate decision after investigating the limits of emulation. Network compatibility currently supports continued offline execution; it does not implement multiplayer or provide access to accounts or services.

The patch retains touchHLE's license notices. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). This project does not distribute the game or claim ownership of its content.
