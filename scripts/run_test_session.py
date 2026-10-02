#!/usr/bin/env python3
"""Run test-only touchHLE with a disposable copy of offline game saves."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

PROJECT = Path(__file__).resolve().parents[1]
SAVE_FILES = {
    'Player.sqlite', 'Player.p', 'Player_optiondict', 'Player_Tutorial',
    'Player.apartment', 'localdefault', '8beet-poster-progress-v1',
}


def copy_offline_saves(source: Path, destination: Path) -> None:
    """Copy only known campaign saves; never copy a bundle or account files."""
    source = source.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    for name in SAVE_FILES:
        path = source / name
        if name != 'Player.sqlite' and path.is_file() and not path.is_symlink():
            shutil.copy2(path, destination / name)
    database = destination / 'Player.sqlite'
    if (source / 'Player.sqlite').is_file() and not (source / 'Player.sqlite').is_symlink():
        # A live SQLite WAL cannot be copied as a standalone database.
        import sqlite3
        with sqlite3.connect(f'{(source / "Player.sqlite").as_uri()}?mode=ro', uri=True) as src:
            with sqlite3.connect(database) as dst:
                src.backup(dst)


def main() -> int:
    vendor = PROJECT / 'vendor/touchHLE'
    binary = vendor / 'target/test-tools/release/touchHLE'
    ipa = Path(os.environ.get('BEBELLION_IPA', str(PROJECT / 'input/8Bit Rebellion v1.4.5.ipa'))).resolve()
    if not binary.is_file() or not ipa.is_file():
        print('Test binary or IPA missing. Build the test binary as described in docs/TEST_TOOLS.md.', file=sys.stderr)
        return 1
    reports = PROJECT / 'reports'
    reports.mkdir(exist_ok=True)
    session = Path(tempfile.mkdtemp(prefix='test-session-', dir=reports))
    documents = session / 'touchHLE_sandbox/com.alife.linkinpark/Documents'
    copy_offline_saves(vendor / 'touchHLE_sandbox/com.alife.linkinpark/Documents', documents)
    log_path = session / 'run.log'
    print(f'Test saves: {session}\nRun log: {log_path}', flush=True)
    print('F8: test menu. Restart this launcher to reset all changes to your normal saved progress.', flush=True)
    options = [str(binary), str(ipa), '--landscape-right', '--landscape-content-layout',
               '--tolerate-nil-dictionary-keys', '--no-error-popup', '--keyboard-game-controls',
               '--button-to-touch=DPadLeft,40,290', '--button-to-touch=DPadRight,135,290',
               '--button-to-touch=A,455,290']
    env = dict(os.environ, BEBELLION_TEST_DATA_DIR=str(session),
               BEBELLION_DISPLAY_SETTINGS_DIR=str(vendor))
    env.pop('ALSOFT_DRIVERS', None)
    with log_path.open('w') as log:
        log.write(f'Start: {datetime.now().astimezone().isoformat()}\n')
        log.flush()
        process = subprocess.Popen(options, cwd=vendor, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            assert process.stdout is not None
            for line in process.stdout:
                print(line, end='')
                log.write(line)
                log.flush()
            result = process.wait()
        except KeyboardInterrupt:
            process.send_signal(2)
            result = process.wait()
        log.write(f'Exit: {result}\n')
    print(f'Test run ended ({result}); normal saves were not changed. Evidence kept in {session}.')
    return result


if __name__ == '__main__':
    raise SystemExit(main())
