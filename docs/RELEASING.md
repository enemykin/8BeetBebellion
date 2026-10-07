# Self-contained macOS releases

## Target and current state

The first binary-release target is **Apple Silicon (arm64, M1 and newer)**. A release should let the player unzip it, add their own decrypted iPhone 1.4.5 IPA, and start the game without installing Rust, Python, Git, CMake, Boost or Homebrew.

This document defines the packaging procedure for [prerelease 0.3](https://github.com/enemykin/8BeetBebellion/releases/tag/v0.3). It is ad-hoc signed and is not notarized. The README describes the prebuilt ZIP; [BUILDING.md](BUILDING.md) covers development from source. All four shipped host executables link only to macOS system libraries/frameworks. FFmpeg/ffplay are built from pinned sources with static dependencies, rather than copied from Homebrew.

## Selected design

Use statically linked FFmpeg libraries and statically linked SDL2 for ffplay. Ship a native **8BeetBebellion.app** in a ZIP for Apple Silicon. The player unpacks the ZIP, places their decrypted IPA in the adjacent input directory, and opens the application. All non-system runtime dependencies are supplied by the package; only macOS frameworks/libraries remain external. Developer ID signing and notarization are part of the intended ordinary first-launch experience.

Version 0.3 uses this layout and static media tools. The chosen eight-beet pixel icon is stored in `native/app-icon.png`; the package builder converts it to standard macOS icon sizes and records its source checksum in the build manifest. Its current signature is ad-hoc; a Developer ID identity is not installed on the build Mac. The native launcher and source builds have been checked locally, but a second clean Mac and older macOS versions remain unverified.

Project builds also embed this PNG in touchHLE's application picker, so its running application icon is available before any IPA is selected. The build script finds it in the developer checkout or in the source archive's `project/native/` directory. The native launcher's missing-IPA alert explicitly uses the bundled `AppIcon.icns` generated from the same image. Once an IPA is loaded, macOS displays the guest game's icon centered in a transparent square canvas with artwork occupying approximately 80% of its width, instead of filling the entire Dock slot.

## Build version 0.3

On a native Apple Silicon Mac, first prepare the patched touchHLE checkout using [BUILDING.md](BUILDING.md). Install `pkg-config` as an additional build-time tool. Then run from the project root:

```bash
CMAKE_POLICY_VERSION_MINIMUM=3.5 cargo build --manifest-path vendor/touchHLE/Cargo.toml --release --locked
python3 scripts/build_media.py
python3 scripts/package_macos.py --sources
```

`config/release.json` pins the release version, FFmpeg archive checksum, SDL2 revision/source fingerprint, architecture and deployment target. Media build logs are under `build/media/`. Output assets are `build/releases/8BeetBebellion-0.3-macos-arm64.zip`, `8BeetBebellion-0.3-sources.tar.gz` and `SHA256SUMS`. The assembled application is under `build/package-staging/`. All are ignored by Git.

The package builder audits host Mach-O dependencies and rejects non-system libraries and runtime search paths. It collects licenses and corresponding sources, creates empty input/runtime/reports directories, and signs the package ad-hoc. It never reads the user's input directory. `launcher --check` checks package files and IPA selection without starting the game. Runtime startup accepts a single arbitrarily named IPA, or the documented default name if several are present. F9 groups native dropdown controls under Video and Audio. Its persistent Sound choice controls game and cutscene audio after Apply; Cancel discards pending video and audio edits. For quiet development checks, set `BEBELLION_MUTE=1` when starting the native launcher; it forces OpenAL's null backend and SDL's dummy audio driver so even an unmute test cannot disturb other work.

The build deployment target is macOS 11.0. This is not a compatibility claim: local runtime checks are on macOS 26.6.2. Developer ID signing, notarization and clean-device checks below remain pending before a stable release.

## Package contents

Use an explicit allowlist when assembling a new, empty staging directory under the ignored build directory:

```text
8BeetBebellion-0.3-macos-arm64/
  8BeetBebellion.app/
    Contents/
      Info.plist
      MacOS/
        launcher                 native executable; no Python required
        touchHLE                 ordinary release binary, no test tools
        ffmpeg                   static arm64 build
        ffplay                   static arm64 build, including SDL2
      Resources/
        touchHLE_dylibs/          upstream support libraries + notices
        touchHLE_fonts/           upstream fonts + notices
        touchHLE_default_options.txt
  input/                         empty; the player adds their IPA here
  reports/                       empty; runtime logs go here
  runtime/                       empty; local saves/preferences created at launch
  licenses/                      exact licenses/notices for shipped components
  README.txt                     short player instructions
  BUILD-MANIFEST.json            versions, commits, flags, deployment target
```

The upstream ARM support libraries are emulator components, not the game's executable. Preserve their license notices and those of the fonts. Do not include any user IPA, extracted game bundle, game assets, music, campaign saves, host preferences, old run logs, credentials, source-checkout .git directories or agent instructions. Do not zip the developer workspace or copy the existing runtime sandbox.

The production package uses only the ordinary binary. A separately named test package may be prepared later; it must preserve save isolation and identify its test tools clearly.

## Build the emulator

Follow [the macOS source setup](BUILDING.md), including the pinned touchHLE revision, submodule initialization and compatibility patch. Build on a native Apple Silicon Mac:

```bash
cd vendor/touchHLE
CMAKE_POLICY_VERSION_MINIMUM=3.5 cargo test --lib --locked
CMAKE_POLICY_VERSION_MINIMUM=3.5 cargo build --release --locked
file target/release/touchHLE
otool -L target/release/touchHLE
cd ../..
```

Keep the default static feature enabled. It builds SDL2 and OpenAL Soft into touchHLE. Boost and the compilers are build-time requirements and need not be installed on the player's Mac. Inspect the Mach-O deployment target with `otool -l`; record it and test the oldest macOS version claimed in the release notes. Building on a recent Mac does not by itself prove support for older macOS versions.

## Build portable video tools

Build FFmpeg and ffplay from a pinned official [FFmpeg source release](https://ffmpeg.org/download.html), with the required game codecs and filters. Keep the exact source archive, checksum, configuration flags and any patches for the corresponding-source download.

The selected build uses static FFmpeg libraries and a static SDL2 dependency for ffplay, leaving only macOS system dependencies. Ensure movie decoding, `scale=480:320,fps=30`, raw RGBA output, pipe input, audio playback and `-nodisp` work with the commands used in `movie_player.rs`. Disable unnecessary external codec libraries instead of inheriting a full Homebrew build's dependency graph. Never enable FFmpeg's nonfree configuration in a redistributable build.

The release dependency audit must confirm that this static configuration does not pull in external Homebrew dylibs. Keeping FFmpeg external libraries disabled reduces the dependency set that must be built, licensed and maintained.

Check every shipped native binary and dylib with `file`, `otool -L` and `otool -l`. There must be no unresolved paths to `/opt/homebrew`, `/usr/local/Cellar`, another build prefix or the developer's home directory. Check LC_RPATH entries as well as directly linked libraries. Run the bundled video tools with a restricted PATH containing only package tools and macOS system commands, using a small generated fixture rather than game content.

## Release launcher

The native launcher resolves the package root from its own .app location, sets the child process PATH to Contents/MacOS plus system command directories, and runs the bundled touchHLE with the same gameplay options as Start Bebellion.command. It must not invoke Python or look for the source-checkout vendor/touchHLE/target directory.

The default IPA is input/8Bit Rebellion v1.4.5.ipa beside the .app. Accept BEBELLION_IPA for another path and report a missing IPA clearly. Create a timestamped runtime log under reports and use the adjacent runtime directory for writable saves and host preferences. Bundled emulator fonts, support libraries and default options remain in Contents/Resources. A native missing-IPA message should explain which folder to use.

Never write saves, preferences, game files or logs into the signed .app. Adding the IPA beside the application must not change its signature. The launcher must preserve the running child's lifecycle and exit status. Verify paths containing spaces and launch from Finder as well as Terminal.

## Licenses and corresponding source

Upstream touchHLE states that its binaries are distributed under **GPL version 3 or later**, while touchHLE source files retain MPL-2.0 notices. Include applicable license texts and dependency notices; do not replace upstream authorship with the project author's name. See the pinned [upstream license explanation](https://github.com/touchHLE/touchHLE/blob/b432f552d8a754c0274da5156f030ca3ac4d0218/README.md#license).

Prepare a matching corresponding-source asset for the binary release, including patched touchHLE sources, exact native submodule sources, relevant Cargo dependency sources (cargo vendor can collect these), FFmpeg/SDL sources, build scripts, patches, configuration and version records. Exclude .git data, build output, proprietary game content and local user data. A project source ZIP containing only the compatibility patch is not the complete source for all shipped binaries. Record how to rebuild from the source asset.

The actual FFmpeg configuration determines whether LGPL or GPL terms apply. Follow the [official FFmpeg distribution guidance](https://ffmpeg.org/legal.html), including matching sources, notices and attribution on the download page. Preserve notices for any additional bundled libraries. No game IPA is part of either release asset.

## Signing, verification and publication

To provide ordinary first-launch behavior on another Mac, use **Developer ID signing and Apple notarization**, then staple the ticket where supported. This requires the owner's Apple Developer credentials and signing certificate; GitHub authentication is separate. Ad-hoc signing is not Developer ID signing and does not make a download notarized. Do not promise a warning-free first launch for an unsigned package. Follow [Apple's distribution documentation](https://developer.apple.com/macos/distribution/); do not disable Gatekeeper as part of the release.

Before marking a binary release ready, extract the final archive into a fresh path with no Homebrew dependencies on PATH. Verify the no-IPA error, bundled video fixture, title screen, playable world, controls, scrolling, F9 live changes, cutscenes and persistence across restart. Use the player's own local IPA without adding it to any archive. A second clean Mac is needed to verify the stated no-dependencies setup. Keep private runtime evidence under reports; publish only a concise validation summary.

After these checks, create these assets:

- the portable arm64 ZIP (or a signed/notarized distribution container);
- matching corresponding-source archive;
- SHA256SUMS covering both;
- release notes with minimum tested macOS, architecture, build commit, limitations, signing status, and source/license attribution.

Create a **GitHub Release** for a version tag pointing to the validated commit, and upload the assets to that release. GitHub's automatically generated Source code ZIP is not the prebuilt game launcher. A draft release can hold artifacts while verification is pending; publish it only when the notes accurately describe its state. Keep large generated binaries out of ordinary Git commits.

GitHub releases are created through the owner's authenticated account. For new project commits use author/committer enemykin with the verified GitHub noreply address `316342448+enemykin@users.noreply.github.com`. Signing/notarization identities and upstream copyright notices are independent of Git commit authorship. Historical project commits previously attributed to Codex are corrected to the owner's identity; upstream authorship and copyright notices remain intact.
