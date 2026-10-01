#!/usr/bin/env python3
"""Inspect an IPA without extracting or redistributing its proprietary contents."""

from __future__ import annotations

import argparse
import hashlib
import json
import plistlib
import struct
import sys
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

MACHO_MAGICS = {
    b"\xce\xfa\xed\xfe": ("little", 32),
    b"\xfe\xed\xfa\xce": ("big", 32),
    b"\xcf\xfa\xed\xfe": ("little", 64),
    b"\xfe\xed\xfa\xcf": ("big", 64),
}
FAT_MAGICS = {
    b"\xca\xfe\xba\xbe": ("big", 32),
    b"\xbe\xba\xfe\xca": ("little", 32),
    b"\xca\xfe\xba\xbf": ("big", 64),
    b"\xbf\xba\xfe\xca": ("little", 64),
}
CPU_TYPES = {
    7: "x86",
    0x01000007: "x86_64",
    12: "arm",
    0x0100000C: "arm64",
    18: "powerpc",
    0x01000012: "powerpc64",
}
ARM_SUBTYPES = {
    5: "armv4t",
    6: "armv6",
    7: "armv5tej",
    8: "arm_xscale",
    9: "armv7",
    10: "armv7f",
    11: "armv7s",
    12: "armv7k",
    13: "armv8",
}
LC_LOAD_DYLIB = 0x0C
LC_LOAD_WEAK_DYLIB = 0x80000018
LC_REEXPORT_DYLIB = 0x8000001F
LC_LAZY_LOAD_DYLIB = 0x20
LC_LOAD_UPWARD_DYLIB = 0x80000023
DYLIB_COMMANDS = {
    LC_LOAD_DYLIB,
    LC_LOAD_WEAK_DYLIB,
    LC_REEXPORT_DYLIB,
    LC_LAZY_LOAD_DYLIB,
    LC_LOAD_UPWARD_DYLIB,
}
LC_ENCRYPTION_INFO = 0x21
LC_ENCRYPTION_INFO_64 = 0x2C


class InspectionError(RuntimeError):
    """Raised when an IPA is malformed or cannot be inspected safely."""


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_plist(data: bytes, *, source: str) -> dict[str, Any]:
    try:
        value = plistlib.loads(data)
    except Exception as exc:  # plistlib raises several parse-related exception types
        raise InspectionError(f"Cannot parse {source}: {exc}") from exc
    if not isinstance(value, dict):
        raise InspectionError(f"Expected dictionary in {source}, got {type(value).__name__}")
    return value


def normalized_member_names(archive: zipfile.ZipFile) -> list[str]:
    return [str(PurePosixPath(info.filename)) for info in archive.infolist() if not info.is_dir()]


def find_app_info_plist(names: list[str]) -> str:
    candidates = [
        name
        for name in names
        if name.startswith("Payload/")
        and name.count("/") == 2
        and name.endswith(".app/Info.plist")
    ]
    if not candidates:
        raise InspectionError("No Payload/*.app/Info.plist was found in the IPA.")
    if len(candidates) > 1:
        raise InspectionError(f"Multiple app bundles were found: {', '.join(candidates)}")
    return candidates[0]


def cpu_name(cpu_type: int, cpu_subtype: int) -> str:
    base = CPU_TYPES.get(cpu_type, f"unknown({cpu_type})")
    if cpu_type == 12:
        subtype = cpu_subtype & 0x00FFFFFF
        return ARM_SUBTYPES.get(subtype, f"{base}-subtype-{subtype}")
    return base


def parse_thin_macho(data: bytes, *, base_offset: int = 0) -> dict[str, Any]:
    if len(data) < base_offset + 28:
        raise InspectionError("Mach-O executable is too small to contain a valid header.")

    magic = data[base_offset : base_offset + 4]
    if magic not in MACHO_MAGICS:
        raise InspectionError(f"Unsupported Mach-O magic: {magic.hex()}")
    endian_name, bits = MACHO_MAGICS[magic]
    endian = "<" if endian_name == "little" else ">"
    header_size = 28 if bits == 32 else 32
    if len(data) < base_offset + header_size:
        raise InspectionError("Truncated Mach-O header.")

    cpu_type = struct.unpack_from(f"{endian}i", data, base_offset + 4)[0]
    cpu_subtype = struct.unpack_from(f"{endian}i", data, base_offset + 8)[0]
    ncmds = struct.unpack_from(f"{endian}I", data, base_offset + 16)[0]
    sizeofcmds = struct.unpack_from(f"{endian}I", data, base_offset + 20)[0]
    command_offset = base_offset + header_size
    command_end = command_offset + sizeofcmds
    if command_end > len(data):
        raise InspectionError("Mach-O load commands extend beyond the executable data.")

    dylibs: list[str] = []
    encryption_commands: list[dict[str, int]] = []
    cursor = command_offset
    for _ in range(ncmds):
        if cursor + 8 > command_end:
            raise InspectionError("Truncated Mach-O load command header.")
        command, command_size = struct.unpack_from(f"{endian}II", data, cursor)
        if command_size < 8 or cursor + command_size > command_end:
            raise InspectionError("Invalid Mach-O load command size.")

        if command in DYLIB_COMMANDS and command_size >= 24:
            name_offset = struct.unpack_from(f"{endian}I", data, cursor + 8)[0]
            name_start = cursor + name_offset
            name_end_limit = cursor + command_size
            if cursor <= name_start < name_end_limit:
                terminator = data.find(b"\0", name_start, name_end_limit)
                if terminator == -1:
                    terminator = name_end_limit
                dylibs.append(data[name_start:terminator].decode("utf-8", errors="replace"))

        if command in {LC_ENCRYPTION_INFO, LC_ENCRYPTION_INFO_64} and command_size >= 20:
            cryptoff, cryptsize, cryptid = struct.unpack_from(f"{endian}III", data, cursor + 8)
            encryption_commands.append(
                {"cryptoff": cryptoff, "cryptsize": cryptsize, "cryptid": cryptid}
            )

        cursor += command_size

    return {
        "bits": bits,
        "endianness": endian_name,
        "cpu_type": cpu_type,
        "cpu_subtype": cpu_subtype,
        "architecture": cpu_name(cpu_type, cpu_subtype),
        "linked_dylibs": sorted(set(dylibs)),
        "encryption_commands": encryption_commands,
    }


def parse_macho(data: bytes) -> dict[str, Any]:
    if len(data) < 4:
        raise InspectionError("Executable is too small to be a Mach-O file.")
    magic = data[:4]

    if magic in MACHO_MAGICS:
        slices = [parse_thin_macho(data)]
        container = "thin"
    elif magic in FAT_MAGICS:
        endian_name, fat_bits = FAT_MAGICS[magic]
        endian = "<" if endian_name == "little" else ">"
        if len(data) < 8:
            raise InspectionError("Truncated universal Mach-O header.")
        count = struct.unpack_from(f"{endian}I", data, 4)[0]
        entry_size = 20 if fat_bits == 32 else 32
        table_end = 8 + count * entry_size
        if count > 64 or table_end > len(data):
            raise InspectionError("Invalid universal Mach-O architecture table.")

        slices = []
        for index in range(count):
            offset = 8 + index * entry_size
            if fat_bits == 32:
                _, _, slice_offset, slice_size, _ = struct.unpack_from(
                    f"{endian}iiIII", data, offset
                )
            else:
                _, _, slice_offset, slice_size, _, _ = struct.unpack_from(
                    f"{endian}iiQQII", data, offset
                )
            if slice_offset + slice_size > len(data):
                raise InspectionError("Universal Mach-O slice extends beyond file data.")
            slices.append(parse_thin_macho(data[slice_offset : slice_offset + slice_size]))
        container = "universal"
    else:
        raise InspectionError(f"Executable is not a recognised Mach-O file ({magic.hex()}).")

    encryption_values = [
        command["cryptid"]
        for item in slices
        for command in item["encryption_commands"]
    ]
    if encryption_values:
        appears_decrypted: bool | None = all(value == 0 for value in encryption_values)
    else:
        appears_decrypted = None

    return {
        "container": container,
        "architectures": slices,
        "appears_decrypted": appears_decrypted,
        "decryption_note": (
            "All LC_ENCRYPTION_INFO cryptid values are zero."
            if appears_decrypted is True
            else "At least one LC_ENCRYPTION_INFO cryptid is non-zero."
            if appears_decrypted is False
            else "No LC_ENCRYPTION_INFO command was found; decryption status is inconclusive."
        ),
    }


def selected_store_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    allowed = (
        "itemId",
        "itemName",
        "bundleVersion",
        "softwareVersionBundleId",
        "genre",
        "artistName",
    )
    return {key: metadata[key] for key in allowed if key in metadata}


def summarize_resources(names: list[str], app_root: str) -> dict[str, Any]:
    app_files = [name for name in names if name.startswith(app_root)]
    extension_counts: Counter[str] = Counter()
    ipad_markers = 0
    retina_markers = 0
    for name in app_files:
        suffix = PurePosixPath(name).suffix.lower() or "<no-extension>"
        extension_counts[suffix] += 1
        lower = name.lower()
        if "~ipad" in lower or "-ipad" in lower or "/ipad" in lower:
            ipad_markers += 1
        if "@2x" in lower:
            retina_markers += 1

    return {
        "file_count": len(app_files),
        "top_extensions": dict(extension_counts.most_common(20)),
        "files_with_ipad_name_markers": ipad_markers,
        "files_with_retina_name_markers": retina_markers,
    }


def inspect_ipa(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise InspectionError(f"IPA does not exist or is not a file: {path}")
    if path.suffix.lower() != ".ipa":
        raise InspectionError("Expected a file with the .ipa extension.")

    try:
        with zipfile.ZipFile(path) as archive:
            bad_member = archive.testzip()
            if bad_member is not None:
                raise InspectionError(f"IPA ZIP integrity check failed at {bad_member}")

            names = normalized_member_names(archive)
            info_path = find_app_info_plist(names)
            app_root = info_path[: -len("Info.plist")]
            info = load_plist(archive.read(info_path), source=info_path)

            executable_name = info.get("CFBundleExecutable")
            if not isinstance(executable_name, str) or not executable_name:
                raise InspectionError("Info.plist does not contain CFBundleExecutable.")
            executable_path = f"{app_root}{executable_name}"
            if executable_path not in names:
                raise InspectionError(f"App executable was not found: {executable_path}")
            executable = archive.read(executable_path)

            store_metadata: dict[str, Any] = {}
            for candidate in ("iTunesMetadata.plist", f"{app_root}iTunesMetadata.plist"):
                if candidate in names:
                    store_metadata = selected_store_metadata(
                        load_plist(archive.read(candidate), source=candidate)
                    )
                    break

            report = {
                "schema_version": 1,
                "ipa": {
                    "file_name": path.name,
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_path(path),
                    "zip_member_count": len(names),
                },
                "application": {
                    "bundle_name": info.get("CFBundleName"),
                    "display_name": info.get("CFBundleDisplayName"),
                    "bundle_identifier": info.get("CFBundleIdentifier"),
                    "short_version": info.get("CFBundleShortVersionString"),
                    "bundle_version": info.get("CFBundleVersion"),
                    "minimum_os_version": info.get("MinimumOSVersion"),
                    "device_family": info.get("UIDeviceFamily"),
                    "executable_name": executable_name,
                    "executable_size_bytes": len(executable),
                    "executable_sha256": sha256_bytes(executable),
                },
                "store_metadata": store_metadata,
                "macho": parse_macho(executable),
                "resources": summarize_resources(names, app_root),
            }
            return report
    except zipfile.BadZipFile as exc:
        raise InspectionError(f"IPA is not a valid ZIP archive: {exc}") from exc
    except KeyError as exc:
        raise InspectionError(f"IPA member disappeared while reading: {exc}") from exc


def write_report(report: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output is None:
        sys.stdout.write(text)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    print(f"Report written to {output}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ipa", type=Path, help="Path to a user-owned decrypted IPA")
    parser.add_argument("--output", type=Path, help="Write the JSON report to this path")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        report = inspect_ipa(args.ipa.resolve())
        write_report(report, args.output.resolve() if args.output else None)
    except InspectionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
