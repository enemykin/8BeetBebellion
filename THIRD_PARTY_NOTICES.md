# Third-party notices

This document identifies third-party components used by the project and planned for its self-contained Apple Silicon release. **No self-contained binary package has been published yet.** The current repository distributes project tools, documentation and a compatibility patch; upstream sources and local build output are not included.

## touchHLE and its dependencies

The compatibility patch modifies [touchHLE](https://github.com/touchHLE/touchHLE), pinned at commit `b432f552d8a754c0274da5156f030ca3ac4d0218`. This is a modified build, not an official upstream release. Existing copyright, authorship and license notices must be preserved.

According to the pinned [upstream license explanation](https://github.com/touchHLE/touchHLE/blob/b432f552d8a754c0274da5156f030ca3ac4d0218/README.md#license), touchHLE's own source is licensed under **Mozilla Public License 2.0**, while its binaries are distributed under **GNU General Public License version 3 or later** because of dependency license compatibility. Individual dependencies and bundled resources retain their respective terms.

The release notices must cover the exact shipped dependency set, including:

- Dynarmic and its dependencies, including Boost;
- SDL2 and OpenAL Soft, linked into the emulator;
- Rust crates and other native code identified by the pinned build;
- upstream ARM support libraries in `touchHLE_dylibs/`, with their `COPYING.*` notices;
- fonts in `touchHLE_fonts/`, with their Liberation and Noto license files.

The pinned source's `src/licenses.rs`, generated dependency notices, and individual license files provide the component attribution. This list does not replace their full notices. Upstream emulator support libraries and fonts are separate from the proprietary game's resources.

## FFmpeg, ffplay and SDL2

Current source builds use separately installed FFmpeg and ffplay. The planned release will bundle builds from pinned sources, with static FFmpeg libraries and static SDL2 for ffplay, leaving only macOS system dependencies.

[FFmpeg's licensing guidance](https://ffmpeg.org/legal.html) explains that its default license is LGPL-2.1-or-later, with GPL terms applying when GPL components are enabled. The final notices must state the actual versions, configuration and applicable license for each shipped build. A build configured with `--enable-nonfree` must not be distributed.

[SDL2](https://www.libsdl.org/license.php) uses the zlib license. Preserve its license text and notices for any additional included code. Static linking does not remove license obligations; the matching source package and build materials must satisfy the applicable terms of every shipped component.

## Binary release materials

Each binary release will include full applicable license texts, copyright notices and attribution in `licenses/`. Its download page will link a matching source archive containing patched touchHLE, relevant dependency sources, FFmpeg/SDL2 sources, build scripts, configuration and revision records. Where applicable licenses require additional materials for rebuilding or relinking, those must also be provided.

A repository ZIP containing only the compatibility patch is not the complete corresponding source for the bundled binaries. Exact versions and build flags will be recorded in `BUILD-MANIFEST.json`. See [the release preparation guide](docs/RELEASING.md) for the packaging procedure.

## Game content

Linkin Park 8-Bit Rebellion! and its game content belong to their respective rights holders. Neither the repository nor the planned binary or source release includes IPA files, decrypted game executables, artwork, music, extracted game resources or user saves. Players supply their own decrypted application locally. Licenses for the emulator and video tools do not grant rights to redistribute the game.
