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

The early LP splash has been fixed and checked through the title screen. The latest fix for double clicking The West Side discards touch releases aimed at a view removed during the transition. Both close-click and held-release scripted checks passed, and the user confirmed the crash is fixed on 2026-10-02.

**Still unverified:** full campaign completion, purchases and their persistence, home decoration, multiplayer, and full audio/video synchronization.

The local **iPad version 1.4.8 cannot run**: both ARM slices have `cryptid=1`, and touchHLE rejects the encrypted executable. Its declared iOS 6.0 requirement is also newer than touchHLE's supported app range. A decrypted, user-owned copy is needed before further compatibility testing.

See [CHANGELOG](CHANGELOG.md), the detailed [compatibility log](docs/COMPATIBILITY_LOG.md), [save/API audit](docs/SAVE_AND_API_AUDIT.md), and [roadmap](docs/ROADMAP.md). Referenced runtime logs are local evidence and are not included in this repository. README, CHANGELOG and the compatibility log are maintained in English.

## Prebuilt releases

A self-contained Apple Silicon package is planned so players can add only their own decrypted IPA. It needs portable video tools, bundled emulator resources, matching source/licenses, and release validation. No such binary package has been published yet. See [the release preparation guide](docs/RELEASING.md). The steps below build from source.

## Set up on a new Mac

GitHub contains the project tools and source patch. Build touchHLE locally before the first launch. These steps describe the tested Apple Silicon macOS setup; this project's game changes have not been verified on Intel Macs or Windows. On Apple Silicon, use a native Terminal session when building.

Run the commands below in **Terminal**, in order. Internet access is needed to download the source and build dependencies. The game itself must come from your own decrypted copy.

### 1. Install the build tools

Install Apple's Command Line Tools, which provide the C/C++ compilers:

```bash
xcode-select --install
```

Complete the installation dialog before continuing. If the tools are already installed, skip this step.

Install [Homebrew](https://brew.sh/) if `brew --version` does not work. Its official installation command is:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the installer's **Next steps** to add Homebrew to your shell's PATH, then open a new Terminal window. See the [Homebrew installation guide](https://docs.brew.sh/Installation).

Install Python 3.10 or newer, Git, CMake, Boost and FFmpeg:

```bash
brew install python git cmake boost ffmpeg
```

Boost is required by touchHLE's CPU emulator. FFmpeg supplies `ffmpeg` for video and `ffplay` for cutscene audio. SDL2 and OpenAL Soft are built through touchHLE's default bundled/static configuration. The pinned upstream build requirements are documented in [touchHLE's build guide](https://github.com/touchHLE/touchHLE/blob/b432f552d8a754c0274da5156f030ca3ac4d0218/dev-docs/building.md).

Install Rust and Cargo through the [official rustup installer](https://rust-lang.org/tools/install/). Select the default stable toolchain:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
```

Check that the tools are available:

```bash
python3 --version
git --version
rustc --version
cargo --version
cmake --version
command -v ffmpeg ffplay
```

### 2. Download the project

Choose a working directory, then clone the repository:

```bash
mkdir -p "$HOME/Developer"
cd "$HOME/Developer"
git clone https://github.com/enemykin/8BeetBebellion.git
cd 8BeetBebellion
mkdir -p input reports
```

Keep this Terminal in the project directory for the next steps. Alternatively, use GitHub's **Code → Download ZIP**, unpack the archive and open Terminal in the unpacked project directory. The project commands are the same after that point.

### 3. Fetch, patch and build touchHLE

Download the exact upstream revision specified in [config/touchhle.json](config/touchhle.json), initialize its source submodules, and check the compatibility patch before applying it:

```bash
python3 scripts/bootstrap_touchhle.py
git -C vendor/touchHLE submodule update --init --recursive
git -C vendor/touchHLE apply --check ../../patches/touchhle-compatibility.patch
git -C vendor/touchHLE apply ../../patches/touchhle-compatibility.patch
```

Apply the patch **once to a clean checkout**. If the check fails, stop and inspect the error; do not apply it again to an already patched checkout. Do not update upstream to a different revision without checking compatibility.

Build the normal release binary and return to the project root:

```bash
cd vendor/touchHLE
CMAKE_POLICY_VERSION_MINIMUM=3.5 cargo build --release --locked
cd ../..
```

The first build downloads Cargo dependencies and compiles native libraries, so allow it to finish. `CMAKE_POLICY_VERSION_MINIMUM=3.5` keeps the pinned native dependencies compatible with newer CMake releases. A successful build creates `vendor/touchHLE/target/release/touchHLE`. Keep the upstream checkout in place: its bundled fonts, dynamic libraries and default options are needed at runtime.

### 4. Add your IPA and check it

In Finder, place your own **decrypted iPhone version 1.4.5** IPA in the project's `input/` directory, using the filename:

```text
8Bit Rebellion v1.4.5.ipa
```

The tested bundle identifier is `com.alife.linkinpark`. The encrypted iPad 1.4.8 copy is not a supported substitute. The repository does not provide or download game binaries.

From the project root, inspect the IPA and run the project tool tests:

```bash
python3 scripts/inspect_ipa.py 'input/8Bit Rebellion v1.4.5.ipa' --output reports/ipa-report.json
python3 -m unittest discover -s tests -v
```

The report should identify the expected bundle/version and show `appears_decrypted: true` in its `macho` section. This is an encryption-header check; it does not guarantee that a damaged or otherwise incompatible IPA will run. If the report shows `false`, the executable is encrypted and cannot be used with this setup.

### 5. Launch the game

From Finder, double click **Start Bebellion.command**, or run this from the project root:

```bash
./'Start Bebellion.command'
```

If a ZIP download lost the launcher's executable permission, restore it and run again:

```bash
chmod +x 'Start Bebellion.command'
./'Start Bebellion.command'
```

The launcher uses `input/8Bit Rebellion v1.4.5.ipa` by default. To select a differently named local IPA without renaming it:

```bash
BEBELLION_IPA='/absolute/path/to/your.ipa' ./'Start Bebellion.command'
```

Normal launches enable sound. Every run creates an ignored `reports/manual-run-*.log` with output, timestamps and the exit code. If startup fails, read that log. Common setup problems are a missing IPA, a missing release binary, an unapplied patch, missing upstream submodules, or tools not available on PATH. If cutscenes fail, check that both `ffmpeg` and `ffplay` are available.

Normal guest saves are stored under `vendor/touchHLE/touchHLE_sandbox/com.alife.linkinpark/`. A new Mac starts a new campaign unless you transfer your existing offline saves. Downloading the project does not transfer game progress or display preferences.

For the same isolated sessions used in testing, also build the separate feature-enabled binary and follow [the test launcher instructions](docs/TEST_TOOLS.md). Launch it with **Test Bebellion.command**; restarting that launcher starts from a fresh copy of the normal local campaign saves. The ordinary release binary has no cheat menu.

The normal launcher enables `--landscape-content-layout`, keyboard controls, and the optional `--tolerate-nil-dictionary-keys` compatibility mode for the offline path. The latter deliberately skips malformed dictionary insertions and is not standard Foundation behavior.

Cutscenes play **inside the touchHLE window**: `ffmpeg` decodes video, and `ffplay` handles sound without a separate window. Both receive game data directly from the local IPA. Clicking the screen skips the active cutscene. If the required tools are missing, playback may be skipped; the log records the reason.

### Controls

| Input | Action |
| --- | --- |
| A / D or Left / Right | Hold movement left / right |
| Space | Attack |
| W or Up | Enter the available door when its action icon is visible |
| Escape | Open / close the side menu |
| F9 | Open Display Settings (ordinary and test builds) |
| Mouse / touch | Normal game interaction; click to skip a cutscene |
| Mouse wheel / two-finger trackpad scroll | Scroll the visible long list under the pointer |

On macOS, scrolling reads the Natural scrolling preference at startup. Restart the game after changing that system setting.

Letter keys use physical key positions, including under English and Russian layouts. Door activation follows the game's own command and does not depend on mouse position. Game-specific commands and save compatibility fixes are restricted to the inspected 1.4.5 bundle.

## Display settings

Press **F9** to choose output size (480×320 Original, 960×640, HD, Full HD, QHD or 4K), windowed/fullscreen mode, and internal render scale (1×–4×). **Apply** updates the current game immediately and saves the selection for future launches. **Cancel** discards pending edits, including Reset to defaults. The original game proportions remain 3:2, with borders inside wider output. Higher render scales do not add detail to source sprites.

Windowed presets size the SDL output surface; macOS can scale the window for Retina display. Fullscreen uses the desktop mode with the selected output centered, shrinking it to fit if needed. The configuration is `8beet-display-settings-v1` in touchHLE's user data directory (normally `vendor/touchHLE` for the local launcher). Display preferences are shared by the normal and test launchers; offline game saves remain isolated in test sessions. Changing output size, window mode or render scale does not restart the game.

## Local test menu

For reversible purchase, poster and achievement tests, use the separate feature-gated test build and **Test Bebellion.command**. Press F8 in the playable world. The user confirmed that the menu works on 2026-10-02. Each launch uses an isolated copy of offline saves; restarting discards test changes. Ordinary builds contain no test menu. See [test tool instructions](docs/TEST_TOOLS.md).

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
