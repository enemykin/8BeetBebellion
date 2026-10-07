#!/usr/bin/env python3
"""Assemble an allowlisted Apple Silicon application and matching source archive."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "vendor/touchHLE"


def run(args, **kwargs):
    return subprocess.check_output([str(a) for a in args], **kwargs)


def digest(path):
    with Path(path).open("rb") as file:
        result = hashlib.sha256()
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            result.update(chunk)
        return result.hexdigest()


def audit_binary(path):
    description = run(["file", path], text=True)
    if "Mach-O 64-bit executable arm64" not in description:
        raise RuntimeError(f"Not an arm64 host executable: {path}")
    libraries = run(["otool", "-L", path], text=True)
    for line in libraries.splitlines()[1:]:
        dependency = line.strip().split(" (", 1)[0]
        if not dependency.startswith(("/usr/lib/", "/System/Library/")):
            raise RuntimeError(f"External runtime dependency in {path}: {dependency}")
    loads = run(["otool", "-l", path], text=True)
    if "LC_RPATH" in loads:
        raise RuntimeError(f"Unexpected runtime search path in {path}")
    return {"sha256": digest(path), "dependencies": libraries.splitlines()[1:],
            "deployment_target": re.search(r"\n\s+(?:minos|version) ([0-9.]+)", loads).group(1)}


def tracked_copy(source, destination):
    """Copy only Git-tracked source, recursively entering tracked submodules."""
    files = run(["git", "-C", source, "ls-files", "-z"]).decode().split("\0")
    for name in filter(None, files):
        if Path(name).name == "AGENTS.md":
            continue
        src = source / name
        dst = destination / name
        if src.is_symlink():
            if not src.resolve().is_relative_to(UPSTREAM.resolve()):
                raise RuntimeError(f"Source symlink escapes upstream tree: {src}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst, follow_symlinks=False)
        elif src.is_dir():
            tracked_copy(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def is_finder_metadata(name):
    return any(part == ".DS_Store" or part.startswith("._") for part in Path(name).parts)


def source_archive(releases, config, manifest):
    source_name = f"8BeetBebellion-{config['version']}-sources"
    staging = ROOT / "build/source-staging" / source_name
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    tracked_copy(UPSTREAM, staging / "touchHLE")
    # New compatibility modules are intentionally untracked in the local upstream checkout.
    for name in ("src/display_settings.rs", "src/sound_settings.rs", "src/frameworks/uikit/rebellion_scroll.rs",
                 "src/frameworks/uikit/rebellion_test_tools.rs", "src/frameworks/uikit/rebellion_render.rs",
                 "src/frameworks/opengles/atlas_guard.rs",
                 "src/host_settings.h", "src/host_settings_macos.m", "src/host_settings_windows.c"):
        shutil.copy2(UPSTREAM / name, staging / "touchHLE" / name)
    cargo = staging / "cargo"
    cargo_config = run(["cargo", "vendor", "--locked", "--offline", cargo], cwd=UPSTREAM, text=True)
    cargo_config = cargo_config.replace(str(cargo), "../cargo")
    config_dir = staging / "touchHLE/.cargo"
    config_dir.mkdir(exist_ok=True)
    (config_dir / "config.toml").write_text(cargo_config)
    for directory in ("scripts", "config", "native", "patches", "docs", "tests"):
        destination = staging / "project" / directory
        destination.mkdir(parents=True)
        for src in (ROOT / directory).iterdir():
            if src.is_file() and not src.name.startswith(".") and src.name not in ("FIRST_TASK.md", "GAME_CONTEXT.md") and src.suffix not in (".pyc",):
                shutil.copy2(src, destination / src.name)
    for filename in ("README.md", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / filename, staging / "project" / filename)
    ffmpeg = config["ffmpeg"]
    shutil.copy2(ROOT / f"build/media/downloads/ffmpeg-{ffmpeg['version']}.tar.xz", staging)
    shutil.copy2(ROOT / "build/media/configure-flags.json", staging / "ffmpeg-configure-flags.json")
    (staging / "BUILD-MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (staging / "BUILDING.txt").write_text(
        "8BeetBebellion 0.3 corresponding source\n\n"
        "No proprietary game content is included.\n"
        "Install a native Apple Silicon C/C++ toolchain, Rust/Cargo, CMake, Boost, "
        "pkg-config and Python 3.10+. Use macOS 26.6.2 / the recorded compiler versions "
        "to reproduce the tested build environment.\n\n"
        "touchHLE/ is already patched and contains exact native submodule sources. "
        "cargo/ contains the locked Rust dependency sources. Do not reapply the patch.\n"
        "cd touchHLE\nCMAKE_POLICY_VERSION_MINIMUM=3.5 cargo build --release --locked --offline\n\n"
        "To use the project packaging scripts, place this touchHLE tree at "
        "project/vendor/touchHLE and supply the FFmpeg archive in project/build/media/downloads/. "
        "The media builder verifies source fingerprints without Git metadata. Run "
        "python3 scripts/build_media.py from project/; for final packaging, use the "
        "layout and commands in project/scripts/package_macos.py (Git revision checks "
        "apply to the developer checkout).\n\n"
        "Build SDL2 from touchHLE/vendor/SDL with CMake: SDL_SHARED=OFF, SDL_STATIC=ON, "
        "SDL_TEST=OFF, Release, arm64, deployment target 11.0. Install into a private prefix. "
        "Extract the FFmpeg source archive and use ffmpeg-configure-flags.json with paths "
        "adapted to that prefix; PKG_CONFIG_PATH and PKG_CONFIG_LIBDIR must refer only to "
        "its lib/pkgconfig. make -j8; make install.\n\n"
        "Compile project/native/launcher.m with clang -fobjc-arc -framework Cocoa "
        "-mmacosx-version-min=11.0 -arch arm64. See project/scripts/package_macos.py "
        "for Info.plist, resource layout, licenses and signing. The launcher is MIT licensed; "
        "touchHLE binary/source and dependencies retain their own licenses.\n")
    archive = releases / (source_name + ".tar.gz")
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(staging, arcname=source_name,
                filter=lambda entry: None if is_finder_metadata(entry.name) else entry)
    return archive, cargo


def collect_notices(source, target):
    for src in source.rglob("*"):
        if src.is_file() and src.name.upper().startswith(("LICENSE", "LICENCE", "COPYING", "NOTICE", "AUTHORS")):
            if ".git" in src.parts or "target" in src.relative_to(source).parts:
                continue
            dst = target / src.relative_to(source)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def build_icon(resources):
    """Convert the chosen original artwork to the standard macOS icon sizes."""
    source = ROOT / "native/app-icon.png"
    iconset = ROOT / "build/AppIcon.iconset"
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir()
    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            suffix = "@2x" if scale == 2 else ""
            output = iconset / f"icon_{size}x{size}{suffix}.png"
            run(["sips", "-z", str(size * scale), str(size * scale), source, "--out", output])
    run(["iconutil", "-c", "icns", iconset, "-o", resources / "AppIcon.icns"])


def package(include_sources):
    config = json.loads((ROOT / "config/release.json").read_text())
    releases = ROOT / "build/releases"
    releases.mkdir(parents=True, exist_ok=True)
    package_name = f"8BeetBebellion-{config['version']}-macos-arm64"
    staging = ROOT / "build/package-staging" / package_name
    if staging.exists():
        shutil.rmtree(staging)
    macos = staging / "8BeetBebellion.app/Contents/MacOS"
    resources = macos.parent / "Resources"
    macos.mkdir(parents=True)
    resources.mkdir()
    for directory in ("input", "runtime", "reports", "licenses"):
        (staging / directory).mkdir()
    run(["clang", "-fobjc-arc", "-Wall", "-Wextra", "-Werror", "-framework", "Cocoa",
         f"-mmacosx-version-min={config['deployment_target']}", "-arch", "arm64",
         ROOT / "native/launcher.m", "-o", macos / "launcher"])
    shutil.copy2(UPSTREAM / "target/release/touchHLE", macos / "touchHLE")
    for binary in ("ffmpeg", "ffplay"):
        shutil.copy2(ROOT / "build/media/prefix/bin" / binary, macos / binary)
    for resource in ("touchHLE_fonts", "touchHLE_dylibs"):
        shutil.copytree(UPSTREAM / resource, resources / resource)
    shutil.copy2(UPSTREAM / "touchHLE_default_options.txt", resources)
    build_icon(resources)
    info = {"CFBundleName": "8BeetBebellion", "CFBundleDisplayName": "8BeetBebellion",
            "CFBundleIdentifier": "com.enemykin.8beetbebellion", "CFBundleExecutable": "launcher",
            "CFBundlePackageType": "APPL", "CFBundleIconFile": "AppIcon.icns",
            "CFBundleShortVersionString": config["version"],
            "CFBundleVersion": config["version"], "LSMinimumSystemVersion": config["deployment_target"],
            "NSHighResolutionCapable": True, "LSApplicationCategoryType": "public.app-category.games"}
    (macos.parent / "Info.plist").write_bytes(plistlib.dumps(info))
    manifest = {"release": config, "project_commit": run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "project_dirty": bool(run(["git", "status", "--porcelain"], cwd=ROOT)),
                "touchhle_commit": run(["git", "rev-parse", "HEAD"], cwd=UPSTREAM, text=True).strip(),
                "compatibility_patch_sha256": digest(ROOT / "patches/touchhle-compatibility.patch"),
                "icon_source_sha256": digest(ROOT / "native/app-icon.png"),
                "media_configure": json.loads((ROOT / "build/media/configure-flags.json").read_text()),
                "macos_test_host": run(["sw_vers", "-productVersion"], text=True).strip(),
                "rustc": run(["rustc", "--version"], text=True).strip(),
                "clang": run(["clang", "--version"], text=True).splitlines()[0],
                "signing": "ad-hoc; not Developer ID signed or notarized", "host_binaries": {}}
    for binary in ("launcher", "touchHLE", "ffmpeg", "ffplay"):
        run(["codesign", "--force", "--sign", "-", macos / binary])
    run(["codesign", "--force", "--sign", "-", staging / "8BeetBebellion.app"])
    run(["codesign", "--verify", "--deep", "--strict", staging / "8BeetBebellion.app"])
    for binary in ("launcher", "touchHLE", "ffmpeg", "ffplay"):
        manifest["host_binaries"][binary] = audit_binary(macos / binary)
    manifest["touchhle_submodules"] = run(["git", "submodule", "status", "--recursive"], cwd=UPSTREAM, text=True).splitlines()
    (staging / "BUILD-MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    licenses = staging / "licenses"
    shutil.copy2(ROOT / "THIRD_PARTY_NOTICES.md", licenses)
    shutil.copy2(ROOT / "native/LICENSE", licenses / "launcher-MIT.txt")
    collect_notices(UPSTREAM / "vendor", licenses / "native-dependencies")
    collect_notices(resources, licenses / "resources")
    shutil.copy2(UPSTREAM / "LICENSE", licenses / "touchHLE-MPL-2.0.txt")
    license_runtime = ROOT / "build/license-runtime"
    license_runtime.mkdir(exist_ok=True)
    (licenses / "touchHLE-copyright.txt").write_bytes(run([macos / "touchHLE", "--copyright"], cwd=staging,
        env={**os.environ, "BEBELLION_DATA_DIR": str(license_runtime)}, stderr=subprocess.STDOUT))
    for name in ("COPYING.GPLv2", "COPYING.GPLv3", "COPYING.LGPLv2.1", "COPYING.LGPLv3", "LICENSE.md"):
        shutil.copy2(ROOT / f"build/media/ffmpeg-{config['ffmpeg']['version']}" / name, licenses / ("FFmpeg-" + name))
    shutil.copy2(licenses / "FFmpeg-COPYING.GPLv3", licenses / "touchHLE-GPL-3.0.txt")
    (staging / "README.txt").write_text(
        "8BeetBebellion 0.3 — Apple Silicon (M1 and newer)\n\n"
        "1. Unpack the complete archive in a writable folder.\n"
        "2. Put your own decrypted iPhone 1.4.5 IPA in input/. One IPA may keep its filename. "
        "If several are present, name the intended one 8Bit Rebellion v1.4.5.ipa.\n"
        "3. Open 8BeetBebellion.app. No development tools or Homebrew are required.\n\n"
        "A/D or arrows: movement; Space: attack; W/Up: door; Esc: menu; "
        "F9: live display settings and Mute sound / Unmute sound; wheel/trackpad: long menus.\n"
        "Saves and preferences: runtime/. Startup logs: reports/. Keep all folders together.\n"
        "No game content or cheat menu is included. Full campaign completion remains unverified.\n\n"
        "Signing: ad-hoc only, not Developer ID signed or Apple notarized. "
        "macOS may block the downloaded application. This candidate does not yet meet "
        "the intended notarized first-launch experience. Do not disable Gatekeeper.\n"
        "Built with a macOS 11.0 deployment target; runtime testing is on macOS 26.6.2. "
        "Older macOS and a second clean Mac remain unverified.\n\n"
        "Upstream and component attribution: licenses/. Matching sources are supplied "
        "as a separate release asset. FFmpeg/ffplay use LGPL-2.1-or-later without GPL "
        "or nonfree configuration; SDL2 uses zlib. touchHLE binaries use GPL-3.0-or-later.\n")
    artifacts = []
    if include_sources:
        archive, cargo = source_archive(releases, config, manifest)
        artifacts.append(archive)
        collect_notices(cargo, licenses / "rust-dependencies")
    # --copyright can prepopulate writable folders. Never ship even generated runtime files.
    for directory in ("input", "runtime", "reports"):
        if any((staging / directory).iterdir()):
            raise RuntimeError(f"Nonempty user-data folder in package: {directory}")
    archive = releases / (package_name + ".zip")
    if archive.exists():
        archive.unlink()
    run(["ditto", "-c", "-k", "--norsrc", "--keepParent", staging, archive])
    # Finder can create metadata in staging while it is being inspected.
    # Filter the completed ZIP too, preserving permissions and symlink records.
    clean_archive = archive.with_suffix(".clean.zip")
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(clean_archive, "w") as clean:
        for entry in source.infolist():
            if is_finder_metadata(entry.filename):
                continue
            clean.writestr(entry, source.read(entry))
    clean_archive.replace(archive)
    artifacts.append(archive)
    (releases / "SHA256SUMS").write_text("".join(f"{digest(p)}  {p.name}\n" for p in sorted(artifacts)))
    print(f"Application: {staging / '8BeetBebellion.app'}")
    for artifact in artifacts:
        print(f"Release asset: {artifact}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", action="store_true", help="Include complete matching source archive")
    package(parser.parse_args().sources)
