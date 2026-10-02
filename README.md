# 8BeetBebellion

A compatibility project for running **Linkin Park 8-Bit Rebellion!** on modern computers using a patched [touchHLE](https://github.com/touchHLE/touchHLE).

The original game combines missions against PixxelKorp, character and apartment customization, and Linkin Park music. Completing the campaign unlocks **Blackbirds**. See [Linkinpedia](https://linkinpedia.com/wiki/8-Bit_Rebellion!).

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

See [CHANGELOG](CHANGELOG.md), the detailed [compatibility log](docs/COMPATIBILITY_LOG.md), [save/API audit](docs/SAVE_AND_API_AUDIT.md), and [roadmap](docs/ROADMAP.md). Referenced runtime logs are local evidence and are not included in this repository. README, CHANGELOG and the compatibility log are maintained in English.

## Set up on a new Mac

**Release status:** the self-contained Apple Silicon package is planned, but has not been built, validated or published yet. The steps below describe the intended release package. To run the game today, follow [the macOS source build instructions](docs/BUILDING.md). The packaging plan is documented in [the release preparation guide](docs/RELEASING.md).

The release will target **Apple Silicon Macs (M1 and newer)**. Its release notes will specify the tested macOS versions and signing/notarization status. You will need only the unpacked package and your own **decrypted iPhone version 1.4.5 IPA**, bundle ID `com.alife.linkinpark`.

### 1. Download and unpack the release

Once available, download the **macOS arm64 release ZIP** from [GitHub Releases](https://github.com/enemykin/8BeetBebellion/releases) and unpack it in a writable folder. GitHub's **Code → Download ZIP** and the automatic **Source code** archives contain source files and require the build steps linked above.

Keep the unpacked folder together. The planned layout includes:

```text
8BeetBebellion-macos-arm64/
  8-Bit Rebellion!.app
  input/
  reports/
  runtime/
  licenses/
  README.txt
  BUILD-MANIFEST.json
```

The application will include the patched touchHLE emulator, its resources, and FFmpeg/ffplay with their required libraries. Players will not need to install Python, Git, Rust/Cargo, CMake, Boost or Homebrew, or compile anything. Cutscene video and audio tools will be included in the package.

### 2. Add your IPA

Place your own decrypted IPA in the unpacked package's `input/` folder and name it:

```text
8Bit Rebellion v1.4.5.ipa
```

Use the currently supported **iPhone version 1.4.5**. Support for the iPad edition is planned in [the roadmap](docs/ROADMAP.md). The release will not contain or download the game, its music or its artwork.

### 3. Start the game

Double click **8-Bit Rebellion!.app** in the unpacked folder. No Terminal commands or dependency installation will be needed for the intended release package.

The launcher will read the IPA from `input/`, write startup logs to `reports/`, and keep saves and display preferences in `runtime/`, outside the application bundle. Keep these folders with the application when moving the package. A fresh package on another Mac starts a new campaign unless you transfer your existing offline saves.

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

This project runs a user-owned, decrypted copy of the original game through a patched touchHLE emulator. The supported goal is the offline single-player campaign; multiplayer and access to online accounts or services are not implemented. The game and its content belong to their respective rights holders and are supplied separately by the player.

The planned Apple Silicon release will bundle touchHLE, its support libraries and fonts, and FFmpeg/ffplay for cutscenes. These components retain their own licenses and upstream attribution. touchHLE source is licensed under MPL-2.0; upstream distributes its binaries under GPL-3.0-or-later because of dependency license compatibility. FFmpeg's applicable license depends on the exact build configuration.

Binary releases will include applicable license texts and notices in `licenses/`, plus a separate matching source archive with dependency sources, patches and build instructions. The repository's automatic source ZIP is not a substitute for that archive. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for component attribution and [the release preparation guide](docs/RELEASING.md) for packaging requirements. No self-contained binary release has been published yet.
