# Changelog

All entries in this file and the detailed compatibility log must be maintained in English. See [docs/COMPATIBILITY_LOG.md](docs/COMPATIBILITY_LOG.md) for the chronological investigation and local evidence references.

## 2026-10-01

### Added

- Keyboard movement on A/D and Left/Right, attack on Space, door activation on W/Up, and side-menu toggling on Escape. Physical key positions support English and Russian layouts.
- Cutscene decoding in the touchHLE window, audio without a second window, and skipping by mouse or touch.
- Local persistence for poster IDs and completed/displayed tutorial states in the inspected 1.4.5 bundle.
- Static API and save-state audits, plus a network evidence log.

### Fixed

- SQLite temporary-directory selection and combined access-mode checks, resolving observed mission update errors.
- NPC list traversal after freeing a node, using a narrowly scoped allocation compatibility mode.
- Missing Core Graphics rectangle containment support.
- Stopped activity indicators remaining in hit testing and redirecting center clicks into the menu/Profile.
- Early LP splash orientation and cropping, verified from startup to the title screen.
- Reversing direction during an attack and movement stopping when Space is released despite a direction key remaining held. Confirmed by the user.
- Map callbacks targeting an expired panel during double clicks. A scripted double click on The West Side loaded the district successfully; user verification of this final fix remains pending.
- Poster progress being overwritten by a temporarily empty vector during scene changes. Count and appearance persistence are user-confirmed.

### Validation and remaining work

- The user verified map transitions and all internal entrances in all seven districts.
- Purchases, home decoration and full campaign completion remain unverified.
- Mouse-wheel scrolling for long menus is on the roadmap.
- Prepared the public repository with English README/changelog and a clean publication history excluding agent instructions and all input files. Game assets, saves, runtime logs and builds remain local.

## 2026-09-30

### Added and fixed

- Pinned touchHLE at `b432f552d8a754c0274da5156f030ca3ac4d0218` and added IPA inspection/bootstrap tools.
- Dynamic lookup of exported constants through `dlsym()`, including the memory-warning notification requested by the game.
- Initial support for missing UIKit navigation/controller classes, calendars/date components, bundle resource lookup and Foundation collection/invocation operations.
- Core Graphics clipping and ellipse rendering, deferred UIView layout, and audio frame-length queries.
- Landscape screen/layer geometry, orthographic projection and bitmap row-order handling. The post-start Loading screen and character editor became usable.
- URL authority components, mutable-data replacement and delayed-call cancellation.
- Explicit failure for unavailable socket streams and an optional offline nil-dictionary-key compatibility mode.
- Movie-player notifications/fullscreen state, empty media queries and predicates, media keys and media-picker properties.

### Validation

- The decrypted iPhone 1.4.5 executable was inspected and the game reached the playable world.
- The local iPad 1.4.8 executable was encrypted and could not be tested beyond the loader.
- Failed orientation experiments and claims superseded by later user checks remain documented in the compatibility log.
