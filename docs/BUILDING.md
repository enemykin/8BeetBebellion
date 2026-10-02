# Build from source on macOS

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

Download the exact upstream revision specified in [config/touchhle.json](../config/touchhle.json), initialize its source submodules, and check the compatibility patch before applying it:

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

The tested bundle identifier is `com.alife.linkinpark`. These instructions target the iPhone version 1.4.5; iPad edition support is a separate [roadmap task](ROADMAP.md). The repository does not provide or download game binaries.

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

For the same isolated sessions used in testing, also build the separate feature-enabled binary and follow [the test launcher instructions](TEST_TOOLS.md). Launch it with **Test Bebellion.command**; restarting that launcher starts from a fresh copy of the normal local campaign saves. The ordinary release binary has no cheat menu.

The normal launcher enables `--landscape-content-layout`, keyboard controls, and the optional `--tolerate-nil-dictionary-keys` compatibility mode for the offline path. The latter deliberately skips malformed dictionary insertions and is not standard Foundation behavior.

Cutscenes play **inside the touchHLE window**: `ffmpeg` decodes video, and `ffplay` handles sound without a separate window. Both receive game data directly from the local IPA. Clicking the screen skips the active cutscene. If the required tools are missing, playback may be skipped; the log records the reason.

