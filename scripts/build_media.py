#!/usr/bin/env python3
"""Build pinned FFmpeg/ffplay with static SDL2 and no Homebrew runtime libraries."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def build(jobs: int) -> None:
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise SystemExit("This release build requires a native Apple Silicon Mac.")
    config = json.loads((ROOT / "config/release.json").read_text())
    media = ROOT / "build/media"
    prefix = media / "prefix"
    media.mkdir(parents=True, exist_ok=True)
    sdl = ROOT / "vendor/touchHLE/vendor/SDL"
    fingerprint = hashlib.sha256()
    for path in sorted(sdl.rglob("*")):
        if path.is_file() and ".git" not in path.parts:
            relative = path.relative_to(sdl).as_posix().encode()
            data = path.read_bytes()
            fingerprint.update(len(relative).to_bytes(8, "big"))
            fingerprint.update(relative)
            fingerprint.update(len(data).to_bytes(8, "big"))
            fingerprint.update(data)
    if fingerprint.hexdigest() != config["sdl2_source_sha256"]:
        raise SystemExit("SDL2 source does not match the pinned release fingerprint.")
    ff = config["ffmpeg"]
    archive = media / "downloads" / f"ffmpeg-{ff['version']}.tar.xz"
    archive.parent.mkdir(exist_ok=True)
    if not archive.exists():
        with urllib.request.urlopen(ff["url"]) as response:
            archive.write_bytes(response.read())
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ff["sha256"]:
        raise SystemExit("FFmpeg source checksum mismatch.")
    source = media / f"ffmpeg-{ff['version']}"
    if not source.exists():
        with tarfile.open(archive) as tar:
            # Reject traversal and links outside the source directory.
            for entry in tar.getmembers():
                destination = (media / entry.name).resolve()
                if not destination.is_relative_to(source.resolve()):
                    raise SystemExit("Unsafe source archive member.")
                if entry.issym() or entry.islnk():
                    raise SystemExit("Unexpected source archive link.")
            tar.extractall(media)
    env = os.environ.copy()
    env["MACOSX_DEPLOYMENT_TARGET"] = config["deployment_target"]
    env["PKG_CONFIG_PATH"] = str(prefix / "lib/pkgconfig")
    env["PKG_CONFIG_LIBDIR"] = str(prefix / "lib/pkgconfig")
    env.pop("PKG_CONFIG_SYSROOT_DIR", None)
    commands = [
        ["cmake", "-S", str(sdl), "-B", str(media / "sdl-build"),
         "-DCMAKE_POLICY_VERSION_MINIMUM=3.5", "-DCMAKE_BUILD_TYPE=Release",
         f"-DCMAKE_INSTALL_PREFIX={prefix}", "-DCMAKE_OSX_ARCHITECTURES=arm64",
         f"-DCMAKE_OSX_DEPLOYMENT_TARGET={config['deployment_target']}",
         "-DSDL_SHARED=OFF", "-DSDL_STATIC=ON", "-DSDL_TEST=OFF"],
        ["cmake", "--build", str(media / "sdl-build"), "--parallel", str(jobs)],
        ["cmake", "--install", str(media / "sdl-build")],
    ]
    flags = [f"--prefix={prefix}", "--cc=clang", "--arch=aarch64", "--target-os=darwin",
             "--disable-autodetect", "--disable-shared", "--enable-static",
             "--disable-doc", "--disable-debug", "--disable-network",
             "--disable-ffprobe", "--enable-ffplay", "--enable-sdl2",
             "--pkg-config-flags=--static",
             f"--extra-cflags=-mmacosx-version-min={config['deployment_target']}",
             f"--extra-ldflags=-mmacosx-version-min={config['deployment_target']}"]
    (media / "configure-flags.json").write_text(json.dumps(flags, indent=2) + "\n")
    with (media / "build.log").open("w") as log:
        for command in commands:
            subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run([str(source / "configure"), *flags], cwd=source, env=env,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(["make", f"-j{jobs}"], cwd=source, env=env,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(["make", "install"], cwd=source, env=env,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    print(f"Portable media tools: {prefix / 'bin'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=8)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    build(args.jobs)
