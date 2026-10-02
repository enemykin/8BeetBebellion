# Self-contained macOS releases

## Target and current state

The first binary-release target is **Apple Silicon (arm64, M1 and newer)**. A release should let the player unzip it, add their own decrypted iPhone 1.4.5 IPA, and start the game without installing Rust, Python, Git, CMake, Boost or Homebrew.

This document defines the packaging procedure. **A self-contained release has not been built or validated yet.** The current repository instructions build from source. The existing local touchHLE release binary links only to macOS system libraries/frameworks, but the locally installed Homebrew FFmpeg/ffplay binaries depend on Homebrew libraries and cannot be copied alone into a portable package.

## Package contents

Use an explicit allowlist when assembling a new, empty staging directory under the ignored build directory:

```text
8BeetBebellion-macos-arm64/
  Start Bebellion.command
  input/                         empty; the player adds their IPA here
  reports/                       empty; runtime logs go here
  runtime/
    touchHLE                     ordinary release binary, no test tools
    ffmpeg                       portable arm64 build
    ffplay                       portable arm64 build
    touchHLE_dylibs/              upstream emulator support libraries + notices
    touchHLE_fonts/               upstream fonts + notices
    touchHLE_default_options.txt
  licenses/                      exact licenses/notices for shipped components
  README.txt                     short player instructions
  BUILD-MANIFEST.json            versions, commits, flags, deployment target
```

The upstream ARM support libraries are emulator components, not the game's executable. Preserve their license notices and those of the fonts. Do not include any user IPA, extracted game bundle, game assets, music, campaign saves, host preferences, old run logs, credentials, source-checkout .git directories or agent instructions. Do not zip the developer workspace or copy the existing runtime sandbox.

The production package uses only the ordinary binary. A separately named test package may be prepared later; it must preserve save isolation and identify its test tools clearly.

## Build the emulator

Follow the source setup in the main README, including the pinned touchHLE revision, submodule initialization and compatibility patch. Build on a native Apple Silicon Mac:

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

Prefer static FFmpeg libraries and a static SDL2 dependency for ffplay, leaving only macOS system dependencies. Ensure movie decoding, `scale=480:320,fps=30`, raw RGBA output, pipe input, audio playback and `-nodisp` work with the commands used in `movie_player.rs`. Disable unnecessary external codec libraries instead of inheriting a full Homebrew build's dependency graph. Never enable FFmpeg's nonfree configuration in a redistributable build.

A dynamic build is also possible, but every non-system dependency must be bundled recursively, its load paths rewritten to package-relative paths such as `@loader_path`, and its licenses and corresponding sources provided as required. Copying only ffmpeg/ffplay, or adding Homebrew directories to PATH, does not make the package self-contained.

Check every shipped native binary and dylib with `file`, `otool -L` and `otool -l`. There must be no unresolved paths to `/opt/homebrew`, `/usr/local/Cellar`, another build prefix or the developer's home directory. Check LC_RPATH entries as well as directly linked libraries. Run the bundled video tools with a restricted PATH containing only package tools and macOS system commands, using a small generated fixture rather than game content.

## Release launcher

The bundled launcher should use macOS's built-in zsh, set PATH to the bundled video-tools directory plus system command directories, and run the bundled touchHLE with the same gameplay options as Start Bebellion.command. It must not invoke Python or look for the source-checkout `vendor/touchHLE/target` directory.

It resolves the default IPA relative to the package root (`input/8Bit Rebellion v1.4.5.ipa`), accepts BEBELLION_IPA for another path, creates a fresh timestamped runtime log, and changes working directory to runtime before starting touchHLE so the upstream fonts, support libraries and default options can be found. Normal saves and display settings stay local to that runtime directory. Report missing IPA errors clearly. Preserve executable permissions in the archive.

For a future .app version, put emulator resources in Contents/Resources and writable saves/preferences in a user-data directory, not inside a signed application bundle. Adding the IPA must not modify the signed bundle either. A portable folder is the simpler first package.

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

GitHub releases are created through the owner's authenticated account. For new project commits use author/committer enemykin with the verified GitHub noreply address `316342448+enemykin@users.noreply.github.com`. Signing/notarization identities and upstream copyright notices are independent of Git commit authorship. Earlier published history is not rewritten by this configuration.
