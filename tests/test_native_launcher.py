"""Exercise the real macOS launcher with small handwritten child fixtures."""
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(platform.system() == "Darwin" and shutil.which("clang"), "macOS compiler required")
class NativeLauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compile_dir = tempfile.TemporaryDirectory(prefix="rebellion-launcher-")
        cls.binary = Path(cls.compile_dir.name) / "launcher"
        subprocess.run(["clang", "-fobjc-arc", "-Wall", "-Wextra", "-Werror",
                        "-framework", "Cocoa", str(ROOT / "native/launcher.m"),
                        "-o", str(cls.binary)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.compile_dir.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="8-Bit Rebellion! test ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        app = self.root / "8BeetBebellion.app/Contents"
        self.macos = app / "MacOS"
        resources = app / "Resources"
        self.macos.mkdir(parents=True)
        resources.mkdir()
        self.launcher = self.macos / "launcher"
        shutil.copy2(self.binary, self.launcher)
        (app / "Info.plist").write_bytes(plistlib.dumps({
            "CFBundleIdentifier": "com.enemykin.rebellion.launcher.fixture",
            "CFBundleExecutable": "launcher", "CFBundlePackageType": "APPL"}))
        for name in ("touchHLE_dylibs", "touchHLE_fonts", "touchHLE_default_options.txt"):
            (resources / name).write_text("handwritten resource fixture\n")
        for name in ("ffmpeg", "ffplay", "touchHLE"):
            file = self.macos / name
            file.write_text('#!/bin/sh\nprintf "runtime=%s\\npath=%s\\narg=%s\\n" "$BEBELLION_DATA_DIR" "$PATH" "$1"\nprintf "backend=%s/%s\\n" "$ALSOFT_DRIVERS" "$SDL_AUDIODRIVER"\n')
            file.chmod(0o755)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("BEBELLION_")}

    def invoke(self, *args):
        return subprocess.run([str(self.launcher), *args], env=self.env,
                              capture_output=True, text=True, timeout=10)

    def test_missing_ipa_explains_input_folder(self):
        result = self.invoke("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("input folder", result.stderr)

    def test_single_ipa_keeps_its_filename(self):
        (self.root / "input").mkdir()
        (self.root / "input/my game.ipa").write_bytes(b"handwritten fixture")
        result = self.invoke("--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("my game.ipa", result.stdout)

    def test_multiple_ipa_files_require_an_unambiguous_choice(self):
        (self.root / "input").mkdir()
        for name in ("one.ipa", "two.ipa"):
            (self.root / "input" / name).write_bytes(b"handwritten fixture")
        result = self.invoke("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Several IPA files", result.stderr)

    def test_child_uses_adjacent_runtime_and_bundled_tools(self):
        self.env["BEBELLION_MUTE"] = "1"
        (self.root / "input").mkdir()
        (self.root / "input/game.ipa").write_bytes(b"handwritten fixture")
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        logs = list((self.root / "reports").glob("run-*.log"))
        self.assertEqual(len(logs), 1)
        content = logs[0].read_text()
        self.assertIn(f"runtime={self.root / 'runtime'}", content)
        self.assertIn(f"path={self.macos}:/usr/bin:/bin:/usr/sbin:/sbin", content)
        self.assertIn(f"arg={(self.root / 'input/game.ipa').resolve()}", content)
        self.assertIn("backend=null/dummy", content)
        self.assertIn("exit status: 0", content)
