from __future__ import annotations

import plistlib
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.inspect_ipa import InspectionError, inspect_ipa, parse_macho


def build_test_macho(*, cryptid: int = 0) -> bytes:
    dylib_name = b"/System/Library/Frameworks/UIKit.framework/UIKit\0"
    dylib_size = 24 + len(dylib_name)
    dylib_size += (-dylib_size) % 4
    dylib_command = struct.pack(
        "<IIIIII",
        0x0C,  # LC_LOAD_DYLIB
        dylib_size,
        24,  # name offset
        0,
        0,
        0,
    ) + dylib_name
    dylib_command += b"\0" * (dylib_size - len(dylib_command))

    encryption_command = struct.pack(
        "<IIIII",
        0x21,  # LC_ENCRYPTION_INFO
        20,
        0,
        0,
        cryptid,
    )
    commands = dylib_command + encryption_command
    header = struct.pack(
        "<IiiIIII",
        0xFEEDFACE,
        12,  # CPU_TYPE_ARM
        9,  # ARM_SUBTYPE_ARM_V7
        2,  # MH_EXECUTE
        2,
        len(commands),
        0,
    )
    return header + commands


def build_test_ipa(path: Path, *, cryptid: int = 0) -> None:
    info = {
        "CFBundleName": "LP8BR",
        "CFBundleDisplayName": "8-Bit Rebellion!",
        "CFBundleIdentifier": "com.alife.linkinpark",
        "CFBundleShortVersionString": "1.4.5",
        "CFBundleVersion": "145",
        "CFBundleExecutable": "LP8BR",
        "MinimumOSVersion": "3.0",
        "UIDeviceFamily": [1, 2],
    }
    metadata = {
        "itemId": 362709717,
        "itemName": "Linkin Park 8-Bit Rebellion!",
        "softwareVersionBundleId": "com.alife.linkinpark",
        "appleId": "must-not-appear@example.invalid",
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Payload/LP8BR.app/Info.plist", plistlib.dumps(info))
        archive.writestr("Payload/LP8BR.app/LP8BR", build_test_macho(cryptid=cryptid))
        archive.writestr("Payload/LP8BR.app/background~ipad.png", b"fake")
        archive.writestr("Payload/LP8BR.app/icon@2x.png", b"fake")
        archive.writestr("iTunesMetadata.plist", plistlib.dumps(metadata))


class MachOTests(unittest.TestCase):
    def test_parses_armv7_and_decrypted_state(self) -> None:
        result = parse_macho(build_test_macho(cryptid=0))
        self.assertEqual(result["container"], "thin")
        self.assertTrue(result["appears_decrypted"])
        architecture = result["architectures"][0]
        self.assertEqual(architecture["architecture"], "armv7")
        self.assertIn(
            "/System/Library/Frameworks/UIKit.framework/UIKit",
            architecture["linked_dylibs"],
        )

    def test_detects_encrypted_binary(self) -> None:
        result = parse_macho(build_test_macho(cryptid=1))
        self.assertFalse(result["appears_decrypted"])


class IpaInspectionTests(unittest.TestCase):
    def test_generates_sanitized_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ipa = Path(temp_dir) / "game.ipa"
            build_test_ipa(ipa)
            report = inspect_ipa(ipa)

        self.assertEqual(report["application"]["bundle_identifier"], "com.alife.linkinpark")
        self.assertEqual(report["application"]["device_family"], [1, 2])
        self.assertEqual(report["store_metadata"]["itemId"], 362709717)
        self.assertNotIn("appleId", report["store_metadata"])
        self.assertEqual(report["resources"]["files_with_ipad_name_markers"], 1)
        self.assertEqual(report["resources"]["files_with_retina_name_markers"], 1)

    def test_rejects_non_ipa_extension(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "game.zip"
            path.write_bytes(b"not important")
            with self.assertRaises(InspectionError):
                inspect_ipa(path)


if __name__ == "__main__":
    unittest.main()
