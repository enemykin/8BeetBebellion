"""Test sandbox isolation, including SQLite WAL saves and excluded files."""
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts.run_test_session import copy_offline_saves


class TestSaveIsolation(unittest.TestCase):
    def test_copies_campaign_saves_and_live_database_without_other_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, destination = root / 'source', root / 'test/Documents'
            source.mkdir()
            (source / 'Player.p').write_bytes(b'fixture-save')
            (source / 'account-token').write_bytes(b'fixture-do-not-copy')
            (source / 'asset.png').write_bytes(b'fixture-do-not-copy')
            (source / 'Player.apartment').symlink_to(source / 'account-token')
            with sqlite3.connect(source / 'Player.sqlite') as db:
                db.execute('PRAGMA journal_mode=WAL')
                db.execute('CREATE TABLE state (coins INTEGER)')
                db.execute('INSERT INTO state VALUES (42)')
                db.commit()
                copy_offline_saves(source, destination)
                with sqlite3.connect(destination / 'Player.sqlite') as copied:
                    self.assertEqual(copied.execute('SELECT coins FROM state').fetchone(), (42,))
                    copied.execute('UPDATE state SET coins = 9999')
                self.assertEqual(db.execute('SELECT coins FROM state').fetchone(), (42,))
            self.assertEqual((destination / 'Player.p').read_bytes(), b'fixture-save')
            self.assertFalse((destination / 'account-token').exists())
            self.assertFalse((destination / 'asset.png').exists())
            self.assertFalse((destination / 'Player.apartment').exists())


if __name__ == '__main__':
    unittest.main()
