# Local test tools

The test menu is compiled only with the `rebellion-test-tools` Cargo feature. Ordinary builds omit its code, hotkeys and menu. It is restricted to the inspected offline iPhone 1.4.5 game. The regular launcher continues to use the ordinary release binary.

Build the separate test binary from the patched upstream checkout:

```bash
cd vendor/touchHLE
CMAKE_POLICY_VERSION_MINIMUM=3.5 CARGO_TARGET_DIR=target/test-tools cargo build --release --locked --features rebellion-test-tools
```

From the project root, double click **Test Bebellion.command**, or run:

```bash
python3 scripts/run_test_session.py
```

Each launch copies known offline campaign saves into a new ignored `reports/test-session-*` directory. It does not copy the IPA, bundle, account files or resources. SQLite uses its backup API so committed WAL data is included. The game then writes only into that test sandbox. Normal gameplay saves remain unchanged. Close the normal game before starting a test to obtain a consistent baseline across its different save files.

The user confirmed that the cheat menu works on 2026-10-02.

In the playable world, release movement/attack keys and press **F8** to open the menu. Laptop keyboards may require **Fn** with function keys. The menu and its equivalent shortcuts provide:

| Action | Shortcut | Behavior |
| --- | --- | --- |
| Coins: 9999 / undo | F5 | Saves the current balance once and sets it to 9999 through the game's currency update. Repeat to restore the original balance, including after spending coins. Repeat again to start a new test. |
| Posters: collect / undo | F6 | Collects every poster for the active quest through `defacePoster:`: Mission 1 has 24 IDs (0–23), state 7; Mission 5 has 20 IDs (24–43), state 1. Repeat to restore the original IDs, persisted poster file and quest state. Change district to refresh existing poster artwork. |
| Activate next achievement | F7 | Attempts one ID at a time, 22000–22015, through the game's ordinary award method. Existing achievements are skipped. The log records the ID before activation and checks its presence afterwards. If a dialog prevents activation, dismiss it and retry. |

Poster collection triggers normal quest dialogs. The live poster undo restores the count/IDs and quest state; already displayed dialogs or other quest side effects may remain in that session. **To undo every test change, including purchases, achievements, rewards and any crash effects, close the game and launch a new test session.** It starts from the normal campaign saves again. Previous test directories and logs remain available as local evidence. This is save-file isolation, not an emulator save state.

The Mission 1 action has been checked in the game. The later Mission 5 branch follows the inspected guest method and constructor IDs, but remains unverified in a naturally reached campaign state. Full campaign and purchase validation still require testing.

F9 Display Settings are host preferences and persist across normal/test launcher restarts. They are shared with the normal launcher; this does not share or modify campaign saves. The verification wrapper uses an isolated display configuration.
