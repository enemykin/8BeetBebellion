# Compatibility log

Maintain this log in English after each reproducible investigation. Entries describe the evidence available at that time; later entries may supersede earlier conclusions. Referenced reports and screenshots are local and are not distributed with this repository.

## Initial reproduction — 2026-09-30

All runs below used the decrypted iPhone 1.4.5 IPA, SHA-256 `11f02cfc91e1f61246890302c643f454f9ed36c1115f9963a504a8b3ae3c0efc`, and touchHLE commit `b432f552d8a754c0274da5156f030ca3ac4d0218` on macOS arm64. After the baseline run, changes were applied locally.

| Stage reached | First blocker | Change / local evidence |
| --- | --- | --- |
| Loader, before UI | `dlsym()` failed on `_UIApplicationDidReceiveMemoryWarningNotification` | Clean build; `reports/first-run.log` |
| UIKit NIB loading | `UINavigationBar +alloc` unimplemented | Generic constant lookup in `dlsym()`; `reports/second-run.log` |
| NIB and Foundation initialization | Missing navigation classes, `NSCalendar`, `NSDateComponents`, `_NSGregorianCalendar` | Basic implementations and registration; `reports/third-run.log` through `reports/calendar-components-run.log` |
| Local SQLite, resources, XML and audio | Bundle lookup overload, `initWithPath:`, invalid ASCII, audio property `#frm` | Directory bundles, proper nil for invalid ASCII, audio frame length; bundle/audio run logs |
| Views and `COREUI_LOGIN` initialization | Dictionary enumeration, structure invocation signatures, object description, array initialization, arbitrary-bundle localization | Generic implementations; `reports/visual-check-run.log` |
| Landscape `GCView` / `GCEAGLView` | Nontrivial `CGContextClipToRect` | Clipping with saved CTM/state; landscape run logs |
| Splash and first GLES submissions | Upside-down image and white strip | Diagnostic orientation/frame/presentation traces |
| GLES layer attached by frame 100 | 160 of 480 logical pixels remained white | Geometry and owner/attachment traces |
| Full landscape frame at 38 and 68 seconds | Portrait geometry/projection against a landscape viewport | Initial optional `--landscape-content-layout` experiment; subsequently challenged by the user |
| First Tap to Start click | Ellipse rendering, then `setNeedsLayout` | Bitmap ellipse rendering and deferred view layout |

### Input verification

`reports/ipa-report.json` identified bundle `com.alife.linkinpark`, version 1.4.5, minimum iPhone OS 3.0 and two 32-bit ARM slices, armv6/armv7. Both `LC_ENCRYPTION_INFO` commands have `cryptid=0`. Executable SHA-256: `7a7d0f7c13f87efe3cf4a2999bdb67f4b2de7ce7019c473a3f64714708ae16cb`.

### Reproduction and first fix

The clean build used `cargo build --release --locked` with `CMAKE_POLICY_VERSION_MINIMUM=3.5` for external dependencies under CMake 4. A restricted run could not access a display (`reports/headless-run.log`); a graphical run reproduced the symbol failure. Full logs remain ignored under `reports/`.

The memory-warning notification already existed as an exported `HostConstant::NSString`. `dlsym()` called `create_proc_address()`, which searched only functions. The patch materializes constants once in guest memory and returns the same address through static and dynamic lookup. A check was added to TestApp; execution requires a separate iPhone OS SDK and was not confirmed.

After subsequent fixes, portrait startup created `GCView`/`GCEAGLView`, reached `COREUI_LOGIN >> updateProfanityWordList` and continued for more than 15 seconds without another panic. Landscape startup exposed the clipping gap; after that fix it also ran for more than 15 seconds.

The next screenshot showed an upside-down splash and a white strip. The artwork was 320×480, displayed in a 480×320 window. Startup selected LandscapeRight; the game then requested LandscapeLeft and redrew the splash. The first `EAGLContext presentRenderbuffer:` arrived after roughly 20–30 seconds. `find_fullscreen_eagl_layer` returned nil, so composition was used. The visible result after composition had not yet been verified. Temporary instrumentation was removed.

The game requested status-bar orientation 3, matching the SDK's device-orientation mapping. Window, drawable and viewport were 480×320, but composition and the first GLES buffer were 320×480. The GLES layer initially had no parent, then remained attached at frames 100, 300 and 600. Its temporary lack of a parent did not establish the white strip's cause.

With LandscapeLeft, the rightmost 320 of 960 physical pixels were almost white at 38 seconds; with LandscapeRight the strip appeared on the left. A 480×320 rotated layer contained 320×480 children. No correction had yet been proven. Automated diagnostics used `ALSOFT_DRIVERS=null`; normal sound was later restored at the user's request.

At this stage, four Python tool tests and 34 touchHLE unit tests passed. TestApp was unavailable without its SDK. Formatting and diff checks passed. UIKit navigation implementations remained minimal; `UINavigationItem initWithCoder:` did not decode its fields.

## Landscape frame: unsuccessful initial attempt — 2026-09-30

Disabling automatic root-view rotation turned the white third black. This was an intermediate result: only 640×640 of the 960×640 window contained the game. Expanding the EAGL drawable to 480×320 still left 320×480 parent layers. Both composition and direct presentation needed consistent transforms. The final diagnostic buffer retained a black bottom third because the game set a 480×320 viewport with `glOrthof(0, 320, 480, 0, …)`.

The initial layout experiment adjusted projection for that geometry. At frame 100, almost-black proportions in the three buffer bands changed from `[1.0, 0.111, 0.012]` to `[0.181, 0.027, 0.010]`, bottom to top. At 38 seconds there were no completely white/black bands occupying a third of the window. Edge correlation with the rotated reference screenshot was 0.954 after a 180° rotation. Screenshots were temporary, local evidence; no assets were committed.

A 68-second run showed a full 960×640 image at 38 and 68 seconds, with only three almost-black border rows. However, 97.5% of pixels were unchanged, so entry into the menu was unconfirmed. The process was stopped deliberately with no new panic. This result did not prove correct proportions or orientation.

## Orientation recheck — 2026-09-30

The user's test disproved the earlier conclusion: the layout experiment removed the strip by stretching the image and did not preserve its proportions. The initial full-screen splash transitioned into cropped or incorrectly oriented content. Menu and gameplay remained unconfirmed.

Image/layer dimensions were 320×480. A portrait-renderbuffer experiment kept composition at 320×480 while the viewport was 480×320, with landscape parents and portrait children in the same tree. Changing initial rotation, rotating the projection, and matching scissor to the portrait viewport did not produce a confirmed fix; roughly one third remained cropped.

Unverified experimental changes were removed. The diagnostic diff and continuation notes stayed in ignored reports. All runs were muted and stopped. The last confirmed stage was an incorrectly displayed splash.

## Texture rotation center — 2026-09-30

Following the corresponding [tapHLE presentation code](https://github.com/ephun/tapHLE/blob/trunk/crates/taphle/src/gles/present.rs), UV transformations were corrected to rotate/reflect around (0.5, 0.5). A test of four rotations, with and without reflection, verified a fixed center, in-range corners and preserved distances. The test and release build passed. This was a coordinate-transform correction, not proof of a game-specific display fix.

Two 12-second runs with identical LandscapeRight options and muted sound, without the experimental layout mode, retained 319 almost-white columns out of 960. Pixel agreement was 98.4%; mean absolute channel difference was 0.095/255. Logs: `reports/center-rotation-before.log` and `reports/center-rotation-after.log`. The strip persisted. Processes were stopped and temporary captures removed.

The separate tapHLE landscape-native approach remained a hypothesis. It changes base screen geometry and blocks later rotation requests; blindly copying it would not account for this game's portrait layers.

## Root-view dimensions and proportions — 2026-09-30

Tracing showed that GCView/GCEAGLView changed from 480×320 to 320×480 after reading their frame, and UIWindow automatically rotated the root view. No guest setFrame override or relevant autoresizing mask existed. Constructor/setFrame and single-portrait-root hypotheses were tested and rejected; experiments were removed. Evidence: root-view/root-init/root-draw and portrait-root logs.

Without layout mode, the first guest draw used a 320×480 viewport/projection, identity modelview and disabled scissor. The earlier correction changed only Y, producing a 320×320 projection against a 480×320 buffer and stretching X by 1.5. Both axes were corrected to 480×320. Tests check equal X/Y scale for both Y directions and retain checks for unrelated ranges.

A 20-second run occupied the full 960×640 area, with no completely white/black columns and two almost-black border rows. The formerly visible fragment matched without rescaling after a 180° rotation; edge correlation was 0.984. This supported corrected proportions for that fragment but did not replace user assessment of orientation. `reports/landscape-both-axes.log` records the run. The transition from UIKit artwork to GLES was still unverified.

## First Tap to Start click — 2026-09-30

A center click reproduced the missing `_CGContextFillEllipseInRect` export (`reports/landscape-both-axes-review.log`). Generic ellipse filling was implemented for bitmap contexts with CTM/clipping; a focused test checks both axes. The next run passed this call and stopped at `-[GCEAGLView setNeedsLayout]` (`reports/tap-to-start-after-ellipse.log`).

UIView gained `setNeedsLayout` and `layoutIfNeeded`, coalescing layout requests in the main loop and dynamically calling the subclass's `layoutSubviews`. After rebuilding, the automatic first click succeeded and the process ran for another 12 seconds without a panic before deliberate termination (`reports/tap-to-start-after-layout.log`). The visible post-click state was not yet confirmed. Automated runs were muted; the early rotations were tracked separately.

## Character selection, editor and early Loading — 2026-09-30

A manual run reached character selection and crashed on entry into the editor at `glNormalPointer` (`reports/manual-run-2026-09-30_17-44-12-39269.log`). The game passed invalid type 0x3; touchHLE's assertion killed the process. The type now reaches OpenGL 2.1, where it is validated as a GL error rather than an emulator panic. Landscape input coordinates were aligned with the actual frame.

The control run `reports/post-revert-editor-check.log` clicked Tap to Start and the female character, then remained active for another seven seconds. An earlier visual check showed the female character editor (`reports/female-selection-check.log`). The world was not yet confirmed.

Early Loading remained incorrect. Rotating the whole compositor improved one frame but broke the next; that experiment was reverted. Diagnostics recorded LandscapeRight → LandscapeLeft while window/viewport stayed 480×320 and the root composition layer remained 320×480. A correct layer transform was not yet established. Instrumentation was removed. Automated runs stayed muted; the normal launcher retained sound.

## Full-screen Loading after Tap to Start — 2026-09-30

Frame checks distinguished two loading images. The early LP logo still rotated incorrectly. The later LOADING screen was upside down and only 320 of 480 logical pixels wide, leaving a white region on the right (`reports/post-tap-loading-sequence.log`).

The later screen used a portrait bitmap CALayer inside a landscape container. Full-screen portrait-layer fitting was moved into Core Animation and also applied before bitmap CGContext drawing. Composition reads bitmap/CGImage rows top to bottom but EAGL rows bottom to top. After both corrections, LOADING filled the width with upright text (`reports/bitmap-row-order-check.log`). The adjustment depends on geometry/layout mode rather than an application or screen name.

`reports/bitmap-final-interaction-check.log` passed Tap to Start, displayed normal gender selection, and opened the PLAYER editor after a late female-character click. An initial trial click remained on selection; retrying after animation confirmed the transition. The early splash and editor controls remained separate tasks.

## After the editor: NSURL components — 2026-09-30

The manual run `reports/manual-run-2026-09-30_21-59-06-52490.log` reached Call connect to server and stopped at missing `-[NSURL host]`. Implementing host exposed missing port (`reports/post-url-host-save-check.log`). These were Foundation implementation gaps, not proof that the offline campaign required a live service.

Authority parsing was added without connecting to the network. Host returns a decoded hostname; port returns NSNumber for an explicitly specified valid port, otherwise nil. Tests cover credentials, ports, escaped hosts, IPv6 and serverless URLs. The next run passed both and stopped at `_CFStreamCreatePairWithSocketToHost` (`reports/post-url-host-port-check.log`).

CFStream now explicitly fails creation of unsupported socket streams, writing NULL to both outputs without inventing server replies. This exposed missing `NSMutableData replaceBytesInRange:withBytes:length:`. Generic range replacement was implemented with insertion/deletion/length-change tests. Relevant logs include post-cfstream-failure and post-data-replace.

After that fix, the game handled connection failure and requested `+[NSObject cancelPreviousPerformRequestsWithTarget:]`. Cancellation of all pending calls for the target on the current run loop was added. The next failure was insertion of an array with a nil key into NSMutableDictionary (`reports/post-cancel-perform-check.log`). Standard Foundation rejection remained the default. Adding four missing cookie constants did not resolve the nil key.

The optional `--tolerate-nil-dictionary-keys` mode logs and skips that malformed insertion to explore the offline path. The game passed it and opened a panel requiring UITextView input traits. Standard traits were added; evidence is in the offline-nil-key/post-text-view/post-text-input logs and the separate network record. The next run reached a null-page read shortly after movie-player initial playback time. Its cause was then unknown, and testing temporarily switched to iPad at the user's request.

## iPad 1.4.8 — 2026-09-30

`reports/ipa-report-1.4.8.json` identified bundle `com.alife.linkinparkipad`, version 1.4.8, and ARMv7/ARMv7s slices. Both have `cryptid=1`: the executable is encrypted. In `reports/ipad-1.4.8-first-run.log`, touchHLE selected iPad and ARMv7, then rejected the executable. Its iOS 6.0 minimum exceeds touchHLE's stated app range of iOS 4.0 and earlier, but further compatibility could not be tested without decryption. Neither resources nor executables were added to Git. The working target returned to decrypted iPhone 1.4.5, which the launcher selects by default.

## Return to iPhone: movies and media library — 2026-09-30

Saved game data reproduced the crash immediately after movie-player initial playback time (`reports/iphone-return-repro.log`). The movie view method was not called. The standard `_MPMoviePlayerDidExitFullscreenNotification` constant was missing; exporting it removed the null-page crash and exposed `setFullscreen:animated:`. Fullscreen state and enter/exit notifications were implemented. The next blocker was `+[MPMediaQuery artistsQuery]`.

An empty local library now provides query objects, empty items/collections, property predicates and filter storage. Artist, Title and AlbumTitle media keys were exported. Sequential media-query/key/predicate/filter runs passed their respective failures. The final filter run visibly reached **the playable world**, with a character in a room and responsive inventory/menu. Movement and campaign completion had not yet been tested.

Further checks exposed missing media-picker initializer, delegate, multiple-selection and prompt properties. These were added. `reports/iphone-media-picker-prompt-check.log` passed them and stopped at `-[GCCanvasController presentModalViewController:animated:]`, a UIViewController method still requiring implementation or routing. Automated runs were muted; normal manual launches had sound.

## Skipped cutscenes — 2026-10-01

The user reported a skipped movie after selecting the first district. The saved log showed init/play calls for `intro_v07.m4v`; touchHLE previously simulated completion after one second. The local IPA also contains two other m4v files. The intro metadata is MPEG-4 video, 480×320, AAC audio, 30.33 seconds. The files were not extracted for publication.

Initial playback streamed data from the guest filesystem into installed ffplay. Completion notification followed process exit; stop terminated playback, and playbackState reflected activity. Without ffplay, one-second simulated completion remained with a logged reason. A decoder check, release build and four project tests passed. A 50-second game control run stayed at the splash, so in-game playback/return were still unconfirmed. That version used a separate ffplay window.

At the user's request, video moved into the touchHLE window. ffmpeg decodes RGBA 480×320 frames at 30 fps for overlay before buffer swap. ffplay runs with `-nodisp -vn` for sound only. A short stream produced nine complete video frames and a successful audio process without a window. The release build, 43 touchHLE tests and four Python tests passed. Full in-game transition and synchronization still required manual testing.

## Skip a movie by touch — 2026-10-01

New mouse, finger or controller-mapped touches during video are intercepted by the window queue. Their press/release are not delivered to the game; touches begun before playback may still end normally. Skipping stops both decoder processes, removes the overlay and posts the normal completion notification. Two focused tests check suppression and preservation of a pre-existing release. Manual transition after skipping was initially pending.

## First district: rectangle containment and movie timing — 2026-10-01

`reports/manual-run-2026-10-01_10-01-32-72838.log` confirmed playback in the touchHLE window and skipping by touch. The game created two separate movie controllers for the same intro, played it twice, and both were skipped. Both calls preceded the City Center tutorial alert. The user and a [walkthrough](https://youtu.be/pkVAwxjw7xo) indicated that the movie should play on entering the first chosen district. Early/repeated play calls remained unexplained; caller-address tracing was planned. Playback was not moved to a district-selection event without proof of the guest path.

After City Center and Characters messages, touchHLE panicked on missing `_CGRectContainsRect`. Standard geometry support was implemented, including boundaries, negative sizes and CGRectNull. Two focused tests passed. The next blocker required another manual visit to an unopened district.

## Preliminary API and save audit — 2026-10-01

Static import inspection identified possible gaps such as CGRectIsEmpty and UITableViewCell. These are candidates, not confirmed blockers. Player.sqlite existed and passed integrity checking, but restart persistence was initially unverified.

Four mission updates failed with SQLite error 14 after an unsuccessful TMPDIR lookup: SQLite attempted to create a temporary file in the read-only guest root. The initial guest environment now supplies TMPDIR for the app's writable tmp folder; access() handles combined permission bits. See [SAVE_AND_API_AUDIT.md](SAVE_AND_API_AUDIT.md) for details and limits.

## Restart and AvatarComponent crash — 2026-10-01

The runs at 11:22:57 and 11:24:46 used guest tmp without further mission-update error 14. SQLite mission_state changed from 0 to 2; the user reported that character changes survived and restart skipped the editor. Player.p updated on a normal exit. This demonstrated part of save/restore, not persistence of every campaign state.

One run reached Casino Row, Characters and Coins tutorials, then read address 0x8 at ARMv7 instruction 0x432f8 in `-[AvatarComponent clearNPC]`. It read the first NPC node and attempted to handle an invalid list link. It was not a missing touchHLE export. Nearby network/nil-key errors did not establish causation. Another run passed Characters and exited normally, so the fault was not universal.

The user's screenshot showed grey Exit, Home and Chat while Media, Map, Mission and Options remained active. Guest analysis found that ApartmentComponent disables menu index 8 (btnLogout / Exit) when the current mission state is ≤2 and enables it when state is >2 or no mission exists. The local state was 2, consistent with the game rule. No save data was edited to test this. A later truncated log did not prove a new crash.

## District transitions and shop — 2026-10-01

The 12:21:40 run repeated the 0x432f8 crash. Analysis of clearNPC and std::list remove identified access to a freed list node: touchHLE zeroed freed memory, then the caller read its next link. Bundle `com.alife.linkinpark` now uses the existing mode that zeroes memory on the next allocation rather than free. Other games retain their original mode.

The 12:33:16 run passed that section and subsequent district transitions without another panic. The user later verified map transitions and **all internal entrances in all seven districts: Casino Row, City Center, The Beach, The West Side, Downtown, SoHo and The Park**. Shop purchases and acquired-item persistence require a separate test; the initial check had no currency.

## Keyboard controls — 2026-10-01

`--keyboard-game-controls` maps A/D or Left/Right and Space to independent direction/attack touches. The launcher uses the button positions from the user's 480×320 screenshot. Initial E activation was traced through DoorEntryComponent: when an eligible door icon is visible, enterDoor:Position: receives the active component's doorIndex and doorPos. This follows the game's own command without touching an arbitrary screen point. Field offsets and calls are restricted to the inspected bundle/version.

The 13:08:24 control run recorded two door calls, indices 0 and 2, each followed by a new panel without a panic in that section. Movement and attack were user-confirmed. E initially worked only with English layout; mapping moved to physical SDL scancodes, and Escape invokes SceneUIMenuBar nextMode. Tests cover direction aliases and physical-key behavior. At the user's request, activation then moved to W and Up; the user confirmed operation.

The user also reported that moving backward during an attack instead moved forward in either facing direction. Distinct touches were already used. Key/touch diagnostics were added pending reproduction; the later fix is recorded below.

## Tutorials, poster persistence and false center clicks — 2026-10-01

The user reported repeated tutorials and poster counts resetting after restart. SQLite mission_state=7 is a quest stage, not the poster count. IDs live in LPMission1.defacedPosterList while mission_data remains NULL. For 1.4.5, poster IDs are saved separately under Documents and restored through defacePoster:. Saved tutorial states 1 are converted to 2 before guest loadState can reset them to 0. The release build and test compilation passed; further manual verification followed.

The first poster fix still reset progress. Logs showed Restored 3 → Saved 0 during a panel change: a temporarily empty vector overwrote saved IDs. Synchronization now unions saved/current IDs, reapplies missing IDs to new mission instances and never saves a smaller list merely because of temporary clearing. The user confirmed persistence of count and defaced appearance after restart. Previously lost IDs cannot be recovered from mission_state.

Center clicks in the 16:34:51 / 16:36:16 runs were ordinary mouse down/up pairs near (240,159), without duplicate SDL finger events, yet eventually opened My Profile. In the 17:02:05 diagnostic run, (249,165) hit a UIActivityIndicatorView and became local (29,25); earlier clicks hit GCEAGLView unchanged. touchHLE lacked hidesWhenStopped, leaving a stopped indicator in hit testing.

The indicator now hides on initialization/stop and becomes visible on start when appropriate. The release build passed. In the 17:16:21 run, five center clicks all hit GCEAGLView unchanged and no My Profile appeared. The user confirmed that center double clicks no longer opened the menu/Profile. Detailed coordinate tracing was removed.

## Early LP splash — 2026-10-01

Default.png is portrait 320×480 artwork stored sideways. The game changes device orientation and then displays the same image through UIImageView. Fixed landscape layout made the initial splash flip while the UIKit copy was cropped by a layer/screen size mismatch.

Initial presentation now keeps the launch orientation with the inverse texture-coordinate transform. The compositor applies an exact quarter turn only to an unchanged full-screen layer whose decoded pixels match the launch image. Guest view geometry and input coordinates remain unchanged.

Two tests verify all four corners for both landscape orientations at iPhone/iPad sizes, and reject partial, shifted or transformed layers. Both passed, as did the release build. Actual window captures were checked from initial startup through Tap to Start. Evidence: `reports/splash-final-window-sequence-2026-10-01.log`. Temporary diagnostics were removed.

## Movement direction after an attack — 2026-10-01

The user's 17:53:31 run recorded Space down → Left down → Space up; both independent touches reached the game view with multi-touch enabled. UIKit did not lose the key or suppress the second touch.

PlayerAvatar moveLeft/RightShouldRun accept only states 0, 1, 2 and 20. During attack state 4, facing cannot change, but AvatarComponent sets isWalkHold and its next cycle chooses movement using the old isFaceRight value. Ending the attack touch also clears isWalkHold even while the direction touch remains active.

For 1.4.5, the held direction is reapplied after entering an allowed state through the game's own movement method. isWalkHold is restored only after that method accepts movement. The fix requires an active keyboard-direction touch in GCEAGLView and stops after release/focus loss. It does not interrupt the attack animation.

A unit test covers both directions and lost-hold restoration in allowed states. Scripted SDL input repeated both facing/attack/reverse sequences. `reports/movement-after-attack-sdl-2026-10-01.log` records state=0 with right=false and right=true after Space release, followed by direction releases and normal exit. The release build passed and temporary diagnostics/example code were removed. **The user confirmed that the fix works.**

## Double click on a map district — 2026-10-01

The 18:12:55 run panicked at objc/messages.rs:38 while sending selectLocation:5 to freed object 0x36bb34d0. Return address 0xcfa9c identifies MapComponent touchesEnded:Blocked: selecting The West Side. The user reported an accidental double click. The previous 18:11:58 run exited normally.

MapComponent.delegate is an assign field at offset 132. District transitions release the panel, but the map component retains its address until reassignment. For the inspected 1.4.5 bundle, the delegate is now retained throughout touch-event processing and released after the handlers return. Before another event, an expired pointer is cleared if the object no longer exists in the Objective-C runtime. General messaging behavior for freed objects is unchanged.

A scripted SDL run repeated two closely spaced clicks on The West Side. The district loaded and rendered correctly; `reports/map-double-click-west-side-2026-10-01.log` records clearing the expired delegate before the repeated touch, no panic and normal exit. The final release binary and patch were updated; the temporary example was removed. A user retest of this final build remains pending.

## Public repository preparation — 2026-10-01

Prepared English README, CHANGELOG and compatibility documentation. The publication branch starts with a clean history: agent instructions and every file under input are excluded. Generated reports, saved games, upstream checkouts, proprietary files and build output remain local. The previous local history is retained separately and is not pushed. The public repository contains only tools, source patch and documentation.

## Reversible local test menu and complete poster capacity — 2026-10-01

A separate `rebellion-test-tools` feature adds an F8 native test menu, with F5/F6/F7 shortcuts. Ordinary builds compile out the module, menu and hotkeys. `Test Bebellion.command` launches the separate binary with a fresh isolated sandbox populated only from known offline campaign saves. SQLite's backup API includes committed WAL data. Test purchases, rewards and achievements never overwrite normal progress; restarting the test launcher provides a complete rollback to the normal campaign baseline. The IPA and game resources are not copied into these sandboxes.

Guest analysis identified `PlayerConnector playerCreditUpdate:`, the profile refresh used by `PlayerMonitorComponent addCurrency:`, and `SceneUIComponent updateCoin`. The test action records the original balance once, requests 9999, then restores the exact original amount on repeat. Poster collection uses `defacePoster:`; undo restores the original vector elements/length, first-mission poster file, cached IDs and quest state. Normal quest dialogs can already have been triggered, so restarting the isolated session remains the complete rollback for all side effects.

District constructor analysis found Mission 1 poster IDs 0–23 (24 posters), and Mission 5 IDs 24–43 (20 posters). The existing first-mission persistence limit of 20 was therefore insufficient and is now 24, with a regression test for all IDs. The test action selects an active Mission 1 state 7 or Mission 5 state 1. The later Mission 5 branch has not been tested in a naturally reached campaign state.

`reports/cheat-current-build/run.log` records balance **343 → 9999 → 343**, poster count **8 → 24 → 8**, restoration of quest state 7 and normal exit. The restored poster file matches the normal save byte-for-byte. A separate test copy began with an empty Achievement table to exercise all award paths: IDs **22000–22015** were activated one at a time through `addAchievementWithID:WithCurrentNumber:`; all returned with `active=true`, without a panic. The normal save still had one achievement, while the test copy had 16. Existing dialogs can prevent an award; the tool keeps the same ID for a retry. The normal NEW ACHIEVEMENT popup was visually confirmed. This does not prove purchase behavior or full campaign completion.

Both ordinary and test release builds succeeded; the ordinary binary contains no test action strings. All 58 touchHLE library tests passed both with and without the feature, and all five project tests passed, including save isolation with a live WAL database, exclusion of unknown files and symlinks, and unchanged source data after test edits. The patch applies cleanly to the pinned upstream source.

## West Side double click: detached touch release — 2026-10-01

The user's `reports/manual-run-2026-10-01_23-25-28-29142.log` disproved completeness of the previous delegate fix. The new panic was `Layers ... have no common ancestor` in CALayer coordinate conversion. Guest return address **0x296578** is in `-[GCPanel adapter:touchesEnded:withEvent:]`, immediately after `locationInView:` on a touch's original view. A transition can remove that view from its window between press and release, while UITouch's strong reference keeps the view alive.

For the inspected 1.4.5 bundle, move/release events targeting an already detached view are now discarded. Release still removes the touch from the active registry and releases its ownership. General layer-conversion semantics and other games are unchanged; this avoids delivering stale input to the departed panel rather than fabricating a transform between unrelated layers.

`reports/map-release-verification/run.log` passed a close double click. The additional held-release check, `reports/map-held-release-verification/run.log`, held presses for 600 ms with no extra gap between clicks. It explicitly recorded **Discarding queued touch for detached 8-Bit Rebellion view**, rendered The West Side with the player and NPC, and exited normally without a panic. A manual retest of this new fix is still pending.

### Native menu inspection — 2026-10-02

The test actions were verified through their SDL shortcut events in the game. The native F8 menu is implemented, but the computer-use inspection tool timed out before a visual check could be confirmed. The temporary verification executables/source examples were removed from the source checkout; local logs remain under reports. Manual confirmation of the menu and the new map fix remains pending.

## User confirmation: test menu and West Side fix — 2026-10-02

The user confirmed that the cheat menu works and the West Side crash is resolved. This closes the pending manual checks for the native menu and the detached-touch fix. It does not add evidence for purchases, full campaign completion or the later Mission 5 poster branch. Earlier pending-check statements above describe the status at the time of those entries.

## Mouse-wheel and trackpad scrolling — 2026-10-02

The game's long lists use its OpenGL `Scrolltable`, rather than UIKit scroll views. The inspected 1.4.5 metadata and guest `drawWithOffsetX:OffsetY:`, `getOffsetY`, `setOffsetY:`, and ScrollbarPluggin cycle/move methods establish the viewport, current offset and lower bound. A bundle/version-gated draw hook records list rectangles and draw order for each presented frame. SDL wheel input, including fractional trackpad values and flipped direction, targets the last drawn live list under the pointer. The guest setter updates its offset within the game's bounds, cancelling existing inertia/scripted scrolling without synthesizing a touch or item activation. Hidden lists, non-scrollable lists, input outside the list, active mouse drags and video playback are skipped.

Visual verification used a separate local app wrapper and isolated offline saves. In Profile → Trophies, scrolling moved the displayed rows from **8-Bit Hunter / Pixel Warrior** to **LP Fan / Super Fan / 1 <3 LP**, and back. `reports/scroll-verification/visual-check.log` records offset **0 → -655 → 0**. An additional wheel event over the right-hand tab column caused no offset change. The wrapper's initial attempt lacked bundled touchHLE resources; resource links resolved that verification-only launch issue. Earlier scripted attempts delivered wheel events but did not open a long list, so they are not evidence of scrolling. Temporary diagnostic messages and source examples were removed. Physical trackpad hardware and other long lists still need user testing.

Both ordinary and test release binaries were rebuilt. All 59 touchHLE library tests passed with and without `rebellion-test-tools`; all five project tests passed. The regression checks cover fractional motion, both list bounds, invalid/non-scrollable offsets and suppression of wheel input during videos. The regenerated source patch applies cleanly to the pinned upstream revision.

## macOS Natural scrolling preference — 2026-10-02

The prior wheel handler always normalized SDL's `Flipped` flag, cancelling macOS natural scrolling. The pinned SDL Cocoa implementation forwards `NSEvent.deltaY` with `isDirectionInvertedFromDevice` as `Flipped`. Window creation now snapshots `com.apple.swipescrolldirection` from the user's global preferences using `/usr/bin/defaults read -g`; the handler normalizes the event's device direction and reapplies that snapshot. If reading fails, macOS keeps the OS-provided delta. Other platforms retain the previous normalized direction. No system preferences are modified. A regression test covers both setting values, both SDL direction flags, positive/negative fractional deltas, and the unreadable-setting fallback. The user's preference was read as **1 (enabled)** during this task. Restarting the game is required after changing the system preference.

The new test binary startup was checked in the isolated sandbox: `reports/scroll-natural-startup.log` records **macOS natural scrolling at startup: true**. Both release builds succeeded, all 60 library tests passed with and without test tools, all five project tests passed, and the patch applies cleanly to the pinned source. The system preference was not toggled during verification; enabled/disabled direction behavior is covered by regression tests.

## User confirmation and display settings planning — 2026-10-02

The user confirmed that scrolling now behaves correctly. Display settings are the next requested design topic. Existing `--scale-hack` scales both renderbuffer allocation and the window, while fullscreen presentation preserves the guest aspect ratio. A service menu for popular output-resolution presets is recorded on the roadmap; implementation has not started. The game uses a 480×320 landscape coordinate space (3:2), so 16:9 output presets require letterboxing to preserve geometry. Output dimensions and internal render scale should be separate settings.

## F9 Display Settings, first implementation — 2026-10-02

The ordinary and test builds now expose a native Display Settings menu on F9 for the inspected 1.4.5 bundle. It offers Original 480×320, 960×640, HD 1280×720, Full HD 1920×1080, QHD 2560×1440 and 4K 3840×2160; windowed/fullscreen mode; and independent internal render scale 1×–4×. Apply writes a validated versioned host preference file atomically. Cancel discards pending edits, including Reset to defaults. Settings take effect at the next launch. Missing or malformed preferences preserve launcher defaults. Live application remains the next development stage.

The output viewport preserves the game's 3:2 geometry. In windowed mode SDL creates the selected output surface; the desktop compositor can scale its visible window on Retina displays. Fullscreen uses the desktop display mode and centers the chosen output area, reducing it to fit when necessary. This first version does not switch the monitor's hardware mode. Higher render scale uses touchHLE's existing renderbuffer/viewport/scissor scaling and cannot add detail absent from the original sprites.

An isolated local wrapper verified the native F9 menu, all preset labels and render-quality choices. Apply saved **resolution=2 (1280×720), fullscreen=0, scale=2** in `reports/display-settings-check/8beet-display-settings-v1`; `reports/display-settings-check/run.log` records the save. Reopening showed the persisted choices. Reset followed by Cancel left the saved file unchanged. Restart rendered the title screen and playable room in HD with 2× rendering, preserved side borders, and accepted the start click at its new screen position. The original game saves and normal display preferences were untouched by this verification. Performance/visual checks for QHD/4K and Windows remain pending.

Display preferences are host settings shared by the normal and test launchers. `run_test_session.py` supplies a persistent display directory while keeping campaign saves in its fresh isolated sandbox, so restarting the test launcher can apply display changes without losing the selected resolution. Temporary verification source and wrapper are excluded from the distributed patch.

An additional launch with fullscreen=1 displayed the HD image centered on the desktop with preserved proportions. Both release builds succeeded; all 62 library tests passed in ordinary and test-feature configurations, including preference round trips, invalid files and HD/Full HD/4K viewport bounds. All five project tests passed. The source patch applies cleanly to the pinned upstream revision. No generated files, game assets or verification helpers are included.

## Live Display Settings application — 2026-10-02

F9 Apply now returns a settings event to the running environment. It resizes the SDL window or changes desktop fullscreen mode immediately, updates output geometry and internal scale, then persists the successful selection. Cancel still discards pending edits. Failed application displays an error; failure to save is reported separately from successful live application.

EAGL contexts now track logical renderbuffer dimensions, sharing the registry within each sharegroup. A scale change reallocates color/depth storage with the same buffer names and attachments, preserves the renderbuffer binding, and rescales existing viewport/scissor coordinates. GPU maximum dimensions are checked before allocation; allocation failures trigger restoration of previous storage and coordinates. SDL mode/size failures restore the prior window settings and request graphics rollback. The Core Animation composition target is invalidated when scale changes. Allocation tracking is gated to the inspected game bundle; ordinary and test builds both support live Apply.

The first reproduced live attempt failed because GLES1-on-GL2 lacked the MAX_RENDERBUFFER_SIZE_OES integer query (0x84e8); forwarding it fixes the panic, with a focused regression test. A subsequent run exposed a stale macOS rotation viewport offset after returning from fullscreen, causing a black window. Explicit display resizing now clears that offset and refreshes the window-height baseline. The failure logs remain locally at reports/display-live-check/first-apply-failure.log and reports/display-live-check/window-offset-failure.log.

After both fixes, reports/display-live-check/run.log records one uninterrupted game run: Original window 1× → HD window 2× → HD desktop fullscreen 4× → HD window 3× → Original window 1×. The room rendered with preserved 3:2 proportions at each step. Profile and Trophies clicks worked after resizing; the trophy list scrolled correctly with clipping at 3×. Reset and Apply restored 480×320 and 1× while retaining the open list and its scroll position. No panic occurred in this final run. Hand-written isolated preference fixtures preselected the intermediate presets before reopening F9; native Apply and Reset buttons performed the live changes. Campaign saves and normal display preferences were untouched; temporary wrapper/source helpers were removed.

Both release builds succeeded and all 64 library tests passed with and without rebellion-test-tools, including renderbuffer-limit query support and viewport/scissor scale conversion. All five project tests passed, and the distributed patch applies cleanly to the pinned upstream revision. QHD/4K performance, Windows behavior and forced GPU allocation-failure recovery have not been verified on hardware.

## Final review fixes: persistence retries and active display state — 2026-10-02

Poster synchronization previously advanced its in-memory cache even when atomic file replacement failed, suppressing subsequent writes until another poster was collected. The cache now tracks pending persistence separately: unchanged IDs are retried, and pending IDs survive the absence or replacement of the Mission 1 object. The test-tool poster undo marks its restored cache clean only after its successful file write. A regression test injects a failed writer, then a successful writer with unchanged IDs, and verifies that clean progress is not rewritten.

F9 previously reloaded disk preferences whenever opened. Successful live application followed by a failed save therefore showed stale values on the next opening. The menu now receives the active Options snapshot; disk preferences are read only at startup. A regression test verifies that active HD/fullscreen/3× settings override older defaults and that changing only window mode retains resolution and quality. No new GUI run was performed for these logic changes; the previously recorded live rendering sequence remains the rendering evidence.

Ordinary and test-feature library suites each pass 66 tests; all five project tests pass. Both release binaries were rebuilt and the complete source patch was checked against the pinned upstream revision.

## Release 0.3 review fixes: modal cutscene resume — 2026-10-02

The audio resume offset used elapsed wall-clock time while F9 blocked video consumption. A generated two-second clip demonstrated the failure: after a three-second blocked consumer interval, video remained buffered but the old audio offset produced no PCM samples. No game content was used and no sound was played.

Resume now uses the last presented frame at the game's fixed 30 fps. Opening F9 stops movie audio, dismissal restores it according to the mute setting, and queued video is consumed at normal frame intervals instead of fast-forwarding after the modal menu. A library regression verifies that queued frames do not advance the audio resume position. Finder metadata is excluded from corresponding-source packaging and filtered from the completed binary ZIP, including metadata created while inspecting staging. Ordinary and test-feature library suites each pass 73 tests; all nine project tests pass. A quiet isolated application run verifies F9 and both sound buttons and exits normally.

## Touch and D-Pad keyboard schemes — 2026-10-02

The user reported that D attacked/moved left and Space moved right under Control: Touch. The keyboard adapter used only the D-Pad button centers (40,290), (135,290) and (455,290). An isolated quiet run confirmed the Touch option. Local inspection of the user-supplied 1.4.5 AvatarComponent handler established that Touch walking uses the outer 110-pixel strips, while the central region below y=160 requests attack. Thus the previous right/attack coordinates selected the wrong actions. Metadata and analysis remain private under reports/control-analysis.txt.

The UIKit integration now reads AvatarComponent's live getControlMode setting; keyboard press/release and focus-loss cleanup choose the corresponding unscaled game coordinates. Touch targets are left (40,290), right (440,290) and attack (240,290). D-Pad retains the configured button centers, and mouse/touch input is unchanged. Guards restrict the setting lookup to the inspected bundle/version with keyboard controls enabled. A regression checks target regions through repeated live scheme changes; the existing direction/alias/attack recovery tests remain enabled.

Both library configurations pass 74 tests. The isolated application run switches Touch → D-Pad → Touch in Options without restarting, receives D/A/arrow/Space events in the gameplay view and exits normally. Its private evidence is under build/touch controls validation 0.3/reports/. UI automation uses short key presses; extended simultaneous key holds are not covered by that manual run. Normal campaign saves and game settings were not changed; all audio backends were forced silent.


## Background scrolling investigation — 2026-10-06

The user reported uneven background scrolling with output and internal rendering at 2×. An unchanged test binary was launched with isolated offline saves, isolated display preferences, muted audio, 960×640 windowed output and 2× internal rendering. The title, apartment and City Center were reached. The complete baseline log is `reports/background-scroll-check/baseline/run.log`. A live F9 change to 1× internal rendering retained the same output size. Median EAGL frame counts were **14.72 FPS at 2×** and **14.74 FPS at 1×** across the respective baseline segments. These segments include startup, transitions and idle gameplay; they are not a controlled continuous walking benchmark. The Core Animation FPS counter reports compositor activity, not newly rendered game frames.

Local inspection of the user-supplied ARMv7 executable identified **15.0 FPS** in `GameCanvas init`. `GCCanvasController run` reads its frame rate once, then repeats event dispatch, `cyclePanels`, drawing and a sleep calculated from 1/frameRate. A separate temporary trace build confirmed a runtime rate of **15.0**. In a 29-second idle City Center sample at 2×, median scene-draw and EAGL-presentation intervals were **67.55 ms** and **67.59 ms**; the scene-draw 95th percentile was **80.10 ms**. Actual compositor swaps were traced separately, at a median interval of **15.73 ms**. Thus compositor refresh does not supply intermediate world frames. The same sample used the EAGL CPU-readback/composition path, with median EAGL presentation work of **3.86 ms** and compositor work of **5.72 ms**; these partial timings are not a full rendering-capacity benchmark. Raw measurements and the selected sample window are in `reports/background-scroll-check/trace/frames.csv` and `trace-summary.json`.

`SceneComponent cycle` follows the player by converting its camera target from float to signed integer before calling `Scene setPositionWithX:Y:`; that method accepts integers and stores them as floats. This loses fractional camera positions before drawing. Low update frequency and whole-pixel camera steps are supported explanations for visible stepping, amplified by larger output. Continuous player walking was not captured: the available UI automation generated short press/release pairs that did not sustain movement across game ticks. The relative contribution of integer rounding during sustained walking remains unmeasured, and an improvement in scrolling has not been demonstrated.

Recommended prototype: separate visual redraws from the original 15 Hz simulation, targeting 60 Hz presentation with interpolated floating-point camera positions. Apply the corresponding camera transform consistently to parallax backgrounds and world entities while leaving HUD coordinates fixed. Simply raising the existing guest frame rate would also increase `cyclePanels` frequency and risks changing movement, combat and other per-cycle behavior. Interpolation between previous/current simulation states can add up to one original tick (about 67 ms) of visual delay; reversal, stopping and input response therefore need explicit comparison. Reset interpolation on district changes, teleports, pause/resume and live display changes. Expose a persistent **Smooth scrolling: On / Off** setting in F9, with Off restoring original rendering behavior. Extra redraws must be benchmarked at 2× before choosing the default; the current readback/composition path may require optimization. Acceptance requires continuous walks in both directions, stopping/reversing, scene-edge checks, transitions, and identical simulation speed with the option on and off.

Both isolated runs exited normally. Temporary instrumentation was removed and affected source files restored byte-for-byte; ordinary and test launcher binaries and the distributed compatibility patch were not replaced. The nine project tests pass. This records an investigation and proposed solution only; the scrolling TODO remains open.

## 2026-10-06 — optional 60 Hz presentation, original 15 Hz simulation

Implemented a presentation-only renderer for the inspected iPhone 1.4.5. The original `GameCanvas.frameRate` and controller remain at 15.0; no additional `cyclePanels`, scene cycle, movement, combat or animation updates are requested. UIKit requests the live GCEAGLView's existing drawRect delegate at fixed 60 Hz deadlines. Original draw requests are coalesced with these presentation frames. Missed deadlines are dropped without accumulating timing drift; the EAGL limiter is bypassed only for this opt-in renderer so it cannot delay the original controller behind a second frame limiter.

After each original scene cycle, host-only history samples the camera and each background layer's existing position. GLES draw scopes interpolate those positions over one original tick using fractional projection translations, restoring the guest matrix stack and matrix mode after every draw. Foreground/world scopes use the camera correction; background scopes use their own parallax displacement; HUD and menu scopes receive no correction. Guest positions are never overwritten. Scene changes, teleports, pauses and the F9 modal reset interpolation. This smooths camera/background movement; sprite animation frames and independent character motion still update at the original rate. Interpolation adds at most one original tick (about 67 ms) of visual delay.

F9 now has a persistent **Smooth scrolling** toggle (off by default); Apply enables/disables it during the current session. Legacy four-line display preferences remain valid and preserve resolution/render scale. The faster fullscreen-layer lookup skips empty transparent overlays only in this game/option path, while keeping drawable overlays and the normal compositor fallback. The source packager includes the new handwritten module.

An isolated offline run used a 960×640 window and render scale 2×, with sound forcibly muted. Native UI navigation reached the apartment, map and City Center. Temporary instrumentation recorded the unchanged controller value **15.000000** and, in a 20-second City Center window during concurrent release builds, a median draw interval **16.70 ms** (58.55 draws/s overall) and median original-cycle interval **67.78 ms** (14.06 cycles/s overall under that load). After disabling via F9, a 20-second window recorded **14.48** original cycles and game draws/s, with median interval **67.49 ms**; compositor refreshes were separate. These are measured rates, not a guarantee of exact wall-clock frequency under load.

A temporary integration fixture in the private sandbox invoked the game's own held-walk methods. It recorded 238 rightward steps of **+10** guest pixels and 253 leftward steps of **−10**, plus 237 rightward **+10** steps after disabling interpolation, and thousands of non-integer background presentation offsets. Stops and map/scene transitions were exercised. This validates presentation/logic separation and unchanged movement per tick; it does not constitute a full combat regression or a human assessment of perceived smoothness with a physically held keyboard key. Logs and CSV evidence remain under `reports/background-scroll-check/interpolated/`. All temporary tracing and movement-fixture source was removed before ordinary/test binaries were rebuilt. The rebuilt test binary was then launched without instrumentation in the same private ×2 sandbox, reached the apartment, and responded to Escape by opening the game menu; its final 15 one-second EAGL samples had a median of 59.98 FPS. It exited normally; the log is `reports/background-scroll-check/interpolated/clean-build-run.log`.

Validation: all **78** touchHLE library tests pass in both ordinary and `rebellion-test-tools` configurations with OpenAL's null driver, and all **9** project tests pass. Regression tests cover fractional/parallax interpolation, reversals, stopping, pauses/teleports, fixed presentation deadlines without drift/catch-up bursts, and backward-compatible display preference persistence.


## F9 input isolation — 2026-10-06

The user reported unsolicited rightward movement after disabling smooth scrolling. The native display modal previously left accepted UIKit touches and cached keyboard holds active; it could also consume releases or leave its own keyboard/mouse events queued for the game. A focused regression reproduced one restart path: SDL key repeat was treated as a fresh press after the cached held-key set was cleared (`reports/f9-input-regression-before.log`). A plain idle On → Off toggle in the isolated apartment did not reproduce the user's exact occurrence, so its precise original event sequence is not established.

Opening F9 now ends all accepted touches through the game's normal `touchesEnded:withEvent:` path, clears cached keyboard directions/attack keys and queued game input, and discards native keyboard/mouse/touch events both before the menu and after Apply/Cancel. Quit and lifecycle events are retained. SDL key repeats cannot revive a released hold; a fresh key press is required. SDL pumping runs on the parent stack. This applies to all F9 display actions, including the smooth-scrolling switch, without changing the simulation or interpolation.

An isolated muted ×2 run used a temporary internal SDL fixture to inject D-down without any corresponding D-up. F9 logged the termination of the accepted gameplay touch. Enabling smooth scrolling with Apply left the avatar stationary; a fresh A press changed its facing left and released normally. Disabling smooth scrolling with no held controls left the avatar stationary and facing left. The test does not emulate an OS-level held key, but exercises the actual SDL mapping, UIKit touch lifecycle and guest display-menu transition. Full private runtime evidence is `reports/f9-input-runtime.log`; temporary injection source was removed before final builds.

Validation: **80** library tests in each ordinary/test-tools configuration and **9** project tests pass. New regressions cover lost releases/repeats, left/right key aliases, attack release, pending mouse touches, preserving Quit, and accepting a fresh direction press after the modal. Both launch binaries were rebuilt without the temporary fixture. The clean test binary was relaunched, reached the apartment, opened F9, returned through Cancel, and exited normally (`reports/f9-input-clean-runtime.log`).


## Restrict intermediate frames to location scrolling — 2026-10-06

The user observed accelerated title-screen animations despite the original 15 Hz logic loop. An unchanged clean test binary with saved Smooth scrolling On reproduced **59.99 FPS** at the title. The complete log is `reports/background-scroll-check/interpolated/animation-baseline.log`. Local inspection found that `CoreUIPanel drawRect:inView:` itself increments and reverses the title fade/bounce alpha values; separating cycle frequency alone was therefore insufficient. The previous claim that all animation timing was preserved was too broad. Private analysis is in `reports/location-draw-animation-analysis.txt`.

Intermediate redraws now require a live Scene drawn by the current EAGL view and a camera displacement within the current original tick. Splash/title/loading/menu screens, stationary locations, expired scene history and reused non-world views cannot schedule them. Every original draw is executed, preserving its original animation side effects; up to three intermediate frames are inserted per original tick. Known void sprite stepping methods (MotionWelder/POD cycle and image next/previous frame) are suppressed only on the thread executing an intermediate frame, while ordinary simulation calls remain intact. Original EAGL presentations retain their normal limiter. F9 describes the 60 Hz target as scrolling only, with logic and animations at 15 Hz.

An isolated, muted 960×640/2× offline run reached the title, apartment, map and City Center. The title median draw interval became **67.22 ms**, with **zero** extra frames. During a 10-second rightward camera pan, rendering measured **59.19 Hz**, original draws **14.80 Hz**; a 9.74-second leftward pan measured **59.12 Hz** versus original draws **14.78 Hz**. These are actual measured frequencies under tracing load, not exact rate guarantees. All **1,298** observed intermediate sprite draw passes reused the same ordered sprite frame indices and cycle counters as their corresponding original pass; **zero** differed. Once scrolling stopped at a boundary, presentation returned to about 15 FPS. F9 terminated held input and Cancel returned normally. This validates the sampled location/title behavior; it does not cover every animation and combat effect in the campaign.

Raw traces and selected sample boundaries are private in `reports/animation-scope/frames.csv`, `checkpoints.json` and `summary.json`; the full traced runtime log is `reports/background-scroll-check/interpolated/animation-fixed-trace.log`. Temporary SDL input injection and tracing were removed before final ordinary/test-tools builds. All **82** library tests pass in both configurations, and all **9** project tests pass. New regressions cover title/no-Scene, idle camera, expired history, non-world view reuse, the three-frame cap and preserving original sprite steps.

The final clean test binary was relaunched with Smooth scrolling saved On: title EAGL samples stayed around 14.8–14.9 FPS, F9 displayed “logic and animations 15 Hz, scrolling target 60 Hz”, Cancel returned normally and the application exited cleanly. Its full log is `reports/background-scroll-check/interpolated/animation-fixed-clean.log`.


## Player translation synchronized with camera interpolation — 2026-10-06

The user reported jerky character movement against the smooth camera. An unchanged renderer with temporary, local tracing reproduced the cause at 960×640 output and 2× internal rendering: the player's POD position remained at x=250 while camera-only presentation offsets varied from about +10 to +2 pixels each original tick. Across 215 complete following-camera ticks, the median within-tick screen-position wobble was **7.68 guest pixels**. This was a presentation mismatch, independent of the original pose animation rate. The full baseline log is `reports/background-scroll-check/interpolated/player-before.log`; handwritten trace source and raw CSV remain private under `reports/player-interpolation/`.

Host-only player history now samples Avatar.m_position (offsets 12/16), current Scene (184), and AvatarComponent.m_currentPlayer (60) once per original draw. Player and camera histories share the camera snapshot timestamp so their interpolation phases match. Only the current player's beforeDraw/draw/afterDraw scopes receive the combined correction, covering body, shadow and attached emotions. Nested superclass scopes replace the correction rather than adding it twice. The BulletManager drawn later by drawPlayerAvatar retains its own camera correction. No guest position, collision state or POD animation coordinate is overwritten, and original simulation/animation methods remain at 15 Hz.

Intermediate world redraws also cover player movement at a stationary camera boundary. Title/loading/menu views and idle locations remain at 15 Hz; stale motion, scene/avatar replacement, teleport, pause and F9 resets retain their existing discontinuity handling. The F9 description now refers to location movement at a target of 60 Hz, and its saved Smooth scrolling switch controls both camera and player presentation.

A muted isolated run reached the apartment, City Center and hospital. In the traced result, all **249 rightward** and **47 leftward** complete following-camera ticks had **zero** within-tick screen-position wobble. Another **40 rightward** and **35 leftward** moving ticks with a fixed camera had no reversal within their interpolated trajectory. All **1,118** intermediate player POD draws retained the original draw's pose index; the corresponding player shadow scopes ran the same number of times. A 10-second rightward sample measured **58.21 draws/s** and **14.85 original draws/s**; a 5.5-second leftward sample measured **59.22** and **14.81**, respectively. Startup had no intermediate frames and a **67.44 ms** median draw interval. Selected ranges, counts and raw evidence are in `reports/player-interpolation/summary.json`, `before.csv`, `after.csv` and `checkpoints.json`. These are sampled measurements under tracing, not an exact 60 Hz guarantee or a full campaign/combat regression.

The long City Center pass triggered ordinary NPC damage, death and hospital respawn; the scene discontinuity reset interpolation. F9 was opened during an injected held-right touch, Smooth scrolling was applied Off and then On, and the player retained world x=900 across the intervening stationary modal/off interval. Subsequent fresh left input moved normally to the boundary. Off restored approximately 15 Hz EAGL presentation. The full runtime log is `reports/background-scroll-check/interpolated/player-after.log`. Temporary input/tracing source was removed before rebuilding both launch binaries; byte checks confirm neither hook is present in the source patch or the ordinary/test-tools executables.

Both library configurations pass **84** tests and all **9** project tests pass. New regressions cover phase cancellation in both directions, smooth translation with a fixed camera, preserving guest coordinates, and restricting player-driven extra frames to the live world. The complete compatibility patch applies to the pinned revision and reproduces the changed source files byte-for-byte.


The final clean test-tools executable was relaunched with Smooth scrolling saved On. Title presentation remained around 14.8–14.9 Hz, F9 showed “logic and animations 15 Hz, location movement target 60 Hz”, Cancel returned normally, the apartment rendered, Escape closed its menu, and the application exited normally. This final smoke test is recorded in `reports/background-scroll-check/interpolated/player-fixed-clean.log`.


## Door indicators and world bulletin screens synchronized with scrolling — 2026-10-06

The user reported jerky door-action indicators and the location screens that originally displayed chat. Temporary local tracing of the unchanged renderer reproduced a missing presentation correction: all **795 visible intermediate door draws** and **720 intermediate bulletin draws** had zero camera offset. Private inspection of the user-supplied executable established that DoorEntryComponent.draw and BulletinComponent.draw are separate from Scene.draw; the door computes its position from the current Scene, while the bulletin's motion welder caches its position in the original cycle. Neither draw scope inherited the world camera interpolation. The full baseline log is `reports/background-scroll-check/interpolated/overlays-before.log`.

Both component draw scopes now receive the same camera correction and frame timestamp as the world. Scene identity guards reject nil, unrelated or stale scenes, and the nested scope is restored after drawing. Guest coordinates and original animation/cycle methods are unchanged. The bulletin's enabled scissor rectangle also receives the matching framebuffer-pixel translation computed from the live orthographic projection and viewport. The original rectangle, projection stack and matrix mode are restored after each draw; HUD clipping remains untouched.

An isolated, muted 960×640 / 2× offline run reached City Center and walked right and left through the actual keyboard-to-SDL-to-UIKit path. All **96 visible intermediate door draws** received a camera correction; **666 of 717** intermediate bulletin draws did too, with zero correction expected during player movement at a stationary camera boundary. A second private run inserted a handwritten message into the local bulletin table to exercise its otherwise empty offline text clipping, without sending a network message. All **144 visible intermediate door draws** received a correction and **758 of 794** bulletin draws did. Across **53,583** clipped text draw calls, scissor X translations ranged from −20 to +20 framebuffer pixels and every original rectangle was restored exactly. Test text rendered in the location screen. These runs validate the sampled City Center overlay paths, not every door/screen or the whole campaign. Full logs are `overlays-after.log` and `overlays-message.log` in the same private runtime directory; raw traces, handwritten fixtures and counts are under `reports/world-overlays/`.

F9 now explicitly describes camera, character movement and world markers as targeting **60 FPS**, while game logic and sprite frame changes remain at the original **15 FPS**. Title, menus and idle locations retain 15 FPS. The updated native dialog was opened and Cancel returned normally.

Both ordinary and test-tools library configurations pass **87** tests, including scene guards and fractional scissor translation at 1×–4× in either direction. All **9** project tests pass. Temporary input, message and tracing hooks were removed before rebuilding both launch binaries; byte checks confirm their absence from the compatibility patch and executables. The complete patch applies to the pinned upstream revision and reproduces all **68** changed source files byte-for-byte.

The final clean test-tools binary was relaunched with Smooth scrolling saved On. Title presentation remained approximately 14.7–14.9 FPS, the native F9 dialog displayed the updated description, Cancel returned normally, the apartment loaded, and the application exited normally. Its complete log is `reports/background-scroll-check/interpolated/overlays-fixed-clean.log`.


## Grouped native F9 settings window — 2026-10-06

The previous F9 menu used a chain of SDL message boxes with action buttons and a persistent explanation block. An unchanged isolated run reproduced that layout and reached the game's original Options screen for comparison: its labels occupy the left column and controls the right. The complete baseline runtime log is `reports/background-scroll-check/interpolated/settings-before.log`.

F9 now opens one native Settings window on the two target desktop platforms. Video contains Resolution, Window mode, Render quality and Smooth scrolling; Audio contains Sound. Each row aligns a left-hand label with a right-hand dropdown. An adjacent circled information icon owns the native hover tooltip; explanations are absent from the default layout. Cancel and Apply are the only footer buttons. AppKit uses native popup controls and Win32 uses dropdown-list combo boxes, with native labels, fonts and tooltips; all text is handwritten, without game artwork or assets. The Windows implementation is present in source but has not been compiled or run on this Mac; Windows release validation remains open. Other upstream platforms retain their existing fallback menu.

The modal returns a single pending video/audio choice only on Apply. Cancel, Escape and window close discard both. Video failure leaves audio unchanged, and the existing render-buffer rollback and save diagnostics are retained. Unchanged video choices avoid redundant resizing. Sound applies after the modal closes, preserves the game's volume settings and persists through the existing host preference file. Cutscene audio resumes according to the final mute state. Existing F9 touch termination and queued-input cleanup surround the new modal. Native source and the shared option/tooltip definitions are included in the corresponding-source packager and compatibility patch.

An isolated offline macOS run, with null audio output and separate saves/preferences, verified all five dropdowns and their values, the two-column layout, Video/Audio grouping and the absence of permanent explanatory text. Native accessibility exposes every dropdown's option name and each icon's Help text. Resolution and audio edits were cancelled together and reverted to 960×640 / Muted on reopening. Apply changed render scale 2× → 3× together with Muted → On; logs and preference files confirmed both. Fullscreen was applied, the new window reopened there, and Windowed / 2× / Muted were restored together. Selecting Smooth scrolling Off followed by Escape retained On on reopening; the close button also returned normally. The apartment loaded and Apply returned to its active game view. Complete private runtime evidence is `reports/background-scroll-check/interpolated/settings-after.log`. No gameplay, input or tracing fixture was added.

All **88** library tests pass in both ordinary and test-tools configurations and all **9** project tests pass. The added regression covers cancelled mixed video/audio edits and invalid native choice indices, including negative/out-of-range values. Both release launch binaries are rebuilt, and the complete patch is checked against the pinned upstream source.

The rebuilt test-tools executable was relaunched without instrumentation. The final native F9 window loaded saved 960×640 / Windowed / 2× / Smooth scrolling On / Muted, exposed Video rows followed by Audio rows in accessibility order, Cancel returned to the title, and the application exited normally. Its full log is `reports/background-scroll-check/interpolated/settings-final.log`. The complete patch reproduces all **72** changed source files byte-for-byte against the pinned revision.


## Visible F9 hover help and conditional information icons — 2026-10-06

The user reported that the information icons displayed no visible help. The previous AppKit controls exposed their text through accessibility Help metadata, but that alone did not establish visible hover behavior in SDL's modal loop. The earlier statement about native hover tooltips was therefore insufficiently verified.

The macOS window now uses explicitly tracked information views and a nonactivating, mouse-transparent child help panel with wrapped text. A local pointer-event monitor handles movement across the modal and its child windows; switching icons hides the previous panel, leaving the icon hides help, and closing the modal removes the monitor and every help panel. Hover does not change selections or steal keyboard focus. Help remains only for Resolution (output size/proportions), Render quality (GPU work/source detail) and Smooth scrolling (60 FPS camera/player/world presentation versus original 15 FPS logic and sprite frame changes, plus idle/title behavior and interpolation delay). Window mode and Sound have no extra explanation and no information icon. Both native platform implementations create icons only when the shared help string is nonempty; the Windows source change is not runtime-validated on this Mac.

A clean isolated macOS run visually verified all three texts. Pointer motion from the Smooth scrolling icon into the adjacent blank area hid its panel; moving to Resolution replaced the Render quality explanation with a single new panel. Opening the Window mode dropdown also hid help. The window displayed exactly three information icons, and Escape returned to the title without changing settings. The run exited normally, with the complete private log at `reports/background-scroll-check/interpolated/settings-help-final.log`. Nine project tests pass, both release launch binaries build without warnings, and the complete source patch applies to the pinned revision and reproduces all 72 changed files byte-for-byte. No diagnostic input or tracing hooks were added.


## Magnified texture-atlas seams — 2026-10-06

The user's title-screen screenshot showed a thin rectangular grid at increased render quality, also reported throughout the game. An unchanged isolated macOS run reproduced it at 2×; switching the same screen to 1× removed the grid. Private numeric GLES traces identified packed image rectangles without protective atlas gutters and linear texture magnification. Linear sampling mixed neighboring packed images at their boundaries. The baseline runtime log is `reports/background-scroll-check/interpolated/texture-seams-baseline.log`; local numeric diagnostics remain under `reports/texture-seams/`.

For the supported iPhone 1.4.5 game at render scales greater than 1×, textured draws now temporarily replace linear magnification with nearest-pixel sampling. Both indexed and non-indexed draw paths restore the original texture parameter immediately afterward. Minification, geometry, UV coordinates, guest arrays, assets, game timing and smooth-scrolling behavior are unchanged. The original 1× filtering and other applications are unaffected. The GLES abstraction exposes the texture-parameter query in both backends. This focused solution keeps source texels distinct and removes atlas bleeding, at the cost of a visibly more pixelated appearance in illustrated backgrounds. README and F9 Render quality hover help explain that tradeoff.

A muted offline run with isolated saves/preferences visually verified the title at 2×, 4× and 3×, restoration of the original softer appearance at 1×, and a return to seam-free 2×. The apartment, map and City Center at 2× also rendered without the colored rectangular seam grid. Title and idle-location presentation remained approximately 14.8–14.9 FPS. These checks cover sampled screens on macOS, not every campaign texture or a Windows run. The application exited normally; the runtime log path was `reports/background-scroll-check/interpolated/texture-seams-final.log` (this path was subsequently reused during the follow-up Park investigation).

All **90** Rust library tests pass in ordinary and test-tools configurations, including regressions for 2×–4× magnification, original 1× behavior, other applications and existing nearest filtering. All **9** project tests pass. Diagnostic experiments were removed from source before final builds; no atlas data, shaders, executable excerpts or game assets are included in the compatibility patch.

Both release launch binaries were rebuilt without warnings. The complete compatibility patch applies to the pinned upstream revision and reproduces all **74** changed source files byte-for-byte. No temporary texture diagnostic or input-injection hooks remain in the source patch.


## Atlas edge sampling during movement in The Park — 2026-10-06

The user still observes intermittent lines near the building with the blue house icon at **1280×720, render quality 3×**. The previous title/apartment/map/City Center checks did not cover that route and setting. An isolated, muted offline run reached The Park and walked in both directions through the house, bulletin screen and Korp Stop area. Thin background boundaries remain observable in some sampled views; the specific intermittent facade artifact was not conclusively isolated. Logs: `reports/background-scroll-check/interpolated/park-seams-before.log`, `park-seams-filter-check.log`, `park-seams-coordinates.log` and `park-seams-guard-check.log`. Diagnostics contain numeric GLES geometry/UV/texture-size metadata only; no extracted texture images are added to the project.

Nearest magnification alone leaves coordinates on the exact boundaries of packed rectangles. The renderer now additionally insets eligible quad UV endpoints to the centers of their outermost source texels at 2×–4×. This prevents an edge sample from selecting an adjacent atlas image and keeps a linear filtering footprint inside the rectangle. A temporary host coordinate array is used only for the draw and the original pointer and stride are restored. Guest arrays, object geometry, game assets and simulation timing are preserved. Original 1× rendering is untouched. This is restricted to the supported game, client-memory FLOAT2 rectangles with integer texel boundaries, identity texture matrices, and the observed indexed quad / four-vertex strip or fan paths. Repeating, fractional, nonrectangular, buffer-backed and unfamiliar layouts retain their original coordinates. Texture dimensions are shared with the EAGL sharegroup and removed on deletion.

The guarded build was exercised on the title, apartment, map and the Park route at the reported setting. No conspicuous rectangular facade grid appeared in the sampled house views, but this is not proof that every intermittent line is resolved; faint boundaries in the sky remain observable. The TODO stays open for confirmation and any remaining seam diagnosis. Full movement intervals retained roughly **59.2–59.5 FPS**, with title/idle presentation roughly **14.8–14.9 FPS**. Transition intervals include partial movement/idle frame counts and are not steady-state performance measurements. Windows remains untested.

All **92** Rust library tests pass in ordinary and test-tools configurations. The new regressions cover nearest edge samples (including slight raster edge overshoot), mirrored rectangles, native-resolution texel-center samples, and unchanged unsupported UV shapes. All **9** project tests pass. Both release binaries were rebuilt without warnings after removing the temporary input fixture and A/B switch. The source patch applies to the pinned revision and reproduces all **75** changed source files byte-for-byte; the source packager includes the new handwritten atlas module. No game data or diagnostic hooks are included in the patch.


## Resolution/render-scale matrix and native-scale scrolling seams — 2026-10-06

Following the user's request to investigate independently, an isolated muted offline run reproduced a conspicuous orange/brown vertical stripe through the road and foreground grass beneath the house bench in The Park at **480×320 / 1×** and **960×640 / 1×**. It appeared during movement and disappeared when stopped. The previous UV guard was enabled only above native render scale, leaving fractional smooth-camera sampling at 1× exposed to adjacent packed images. Baseline logs and handwritten input/numeric fixtures are private under `reports/park-matrix/`; the full baseline runtime log is `reports/background-scroll-check/interpolated/park-matrix.log`.

Both indexed and non-indexed textured draw paths now enable the existing game-specific UV guard when Smooth scrolling is On, including 1×. Native-scale magnification remains linear; higher scales retain nearest magnification. Smooth scrolling Off at 1× keeps the original coordinate/filtering behavior. The new regression checks the linear sample footprint across 129 fractional phases. Original game assets, simulation, geometry and timing are unchanged.

All **24 F9 combinations** were applied and visually inspected, with movement exercised through the normal SDL keyboard-to-UIKit path. Scope is recorded below, rather than treating every setting as a completed house-route run:

| F9 output preset | 1× | 2× | 3× | 4× |
| --- | --- | --- | --- | --- |
| 480×320 | Park/house | Park/house | Park/house | Park/house |
| 960×640 | Park/house | Park/house | Park/house | Park/house |
| 1280×720 | Park/house | Park/house | Park/house | Park/house |
| 1920×1080 | Park/house | Park/house | Park/Juice Bar | Park/Juice Bar |
| 2560×1440 | Park/Juice Bar | Park/Juice Bar | Hospital transition | Hospital |
| 3840×2160 | Hospital | Hospital | Hospital | Hospital |

Extended Full HD / 3× attempts and the QHD / 3× attempt ended with ordinary combat death and hospital respawn; their measurements are not counted as successful Park verification. Full HD / 3× was repeated in the Park. The matrix therefore covers **18 Park combinations**, five hospital-interior combinations and one transition inspection. Higher output presets were inspected fullscreen after large windowed output proved partially clipped. The available Retina display limits physical output: selecting the 4K preset here is **not** a native 3840×2160 display test. It also does not validate Windows.

The previously reproduced long colored road/grass stripe was absent from the sampled guarded house views, including native scale. Faint boundaries in the sky, some illustrated-background joins (also faint title joins at 1280×720 / 3× in the clean smoke run) and the softer native-scale title presentation remain observable; no claim is made that every seam or every intermittent camera phase is fixed. The TODO remains open for those residual artifacts. Movement buckets commonly retained about **53–59 FPS** across the matrix, with original title/idle presentation around **15 FPS**. These short passes include direction reversals and partial/idle intervals; they do not establish precise comparative GPU performance. The fixed full runtime log is `reports/background-scroll-check/interpolated/park-matrix-fixed.log`; per-pass settings, duration, FPS and location annotations are in `reports/park-matrix/annotated-passes.jsonl`.

All **93** Rust library tests pass in ordinary and test-tools configurations and all **9** project tests pass. Temporary input hooks were removed before the final builds and patch validation. The complete compatibility patch applies to the pinned upstream source and reproduces all **75** changed files byte-for-byte. No game images or assets are added to the source patch or documentation.

Both release launch binaries were rebuilt without warnings. A final uninstrumented run loaded 1280×720 / 3× / Smooth scrolling On, retained title presentation at approximately 14.8–14.9 FPS, opened F9 and cancelled normally, loaded the apartment and exited. Complete log: `reports/background-scroll-check/interpolated/park-matrix-clean-smoke.log`. Final source, patch and all local launch executables were checked for absence of the temporary input hook.

## Residual seams: preserve the magnified texel grid — 2026-10-07

The previous half-source-texel UV inset protects packed boundaries, but it also compresses the texture's interior sample grid. With nearest magnification at integer render scales, some source columns/rows therefore occupy fewer or more render pixels than their neighbors. A numeric regression reproduces that distortion with the old inset on a 480-pixel image at 3×. The supported game's atlas guard now uses a **1/64 source-texel** inset for actually magnified nearest-filtered 2D quads. This retains protection against small raster-edge rounding errors while preserving uniform source-pixel widths at 1×–4×. Linear filtering retains its half-texel footprint guard.

Nearest magnification can coexist with linear minification. The small inset is therefore selected per quad using the client FLOAT2 vertices, affine model/projection matrices and actual render viewport. Minified, degenerate, perspective and unfamiliar vertex layouts retain the conservative half-texel inset. The projected source-axis spacing accounts for shearing. Game arrays, geometry, assets, simulation timing and filtering settings remain unchanged.

An isolated muted offline macOS run compared the Park playground view at **1280×720 / 1× / Smooth scrolling Off** with increased rendering. A faint straight transition in the sky remains visible in the original-rendering control too. That observation does **not** establish whether its cause is original artwork or another emulation issue. Fragment-clamp and manual-bilinear shader experiments did not remove the illustrated-background grid and were discarded. Private numeric readbacks of selected title texture rows/columns agreed with corresponding source PNG samples; those limited comparisons are not proof that all texture pixels or all remaining joins are correct. No extracted image files or game assets were added.

The final guard was exercised in actual Park movement at **960×640 / 4×**, **1280×720 / 2×**, and the reported **1280×720 / 3×**. Sampled views included the blue house icon, facade, benches, road, grass, playground and bulletin screen. No conspicuous colored facade/road stripe appeared in those views. Steady movement buckets remained approximately **59.2–59.5 FPS**; title/idle buckets remained approximately **14.8–14.9 FPS**. Loading, F9, direction changes, attacks and death/respawn intervals are not counted as steady performance. Earlier long attempts ended in ordinary combat death and were not successful route verification. These new passes do not repeat the full 24-setting matrix and do not validate Windows or native physical 4K output.

Faint illustrated-background boundaries are still observable, so the TODO remains open. This change corrects a demonstrated sampling defect; it is not a claim that every residual line is eliminated. Runtime logs and numeric per-pass records are private under reports/residual-seams/ and reports/background-scroll-check/interpolated/residual-seams-qualified-guard.log.

All **95** Rust library tests pass in ordinary and test-tools configurations, including uniform integer-scale texel widths, mirrored rectangles, raster-edge overshoot, linear minification and shearing. All **9** project tests pass. Both release binaries were rebuilt without warnings after restoring the original window/input source. The compatibility patch applies to the pinned upstream revision and reproduces all **75** changed source files byte-for-byte. Temporary input, readback and shader experiments are absent from the final source and patch.

A final uninstrumented test-tools smoke run verified the title at 1280×720 / 3× / Smooth scrolling On, normal F9 cancellation, apartment loading and normal exit. Title/idle presentation remained approximately 14.8–14.9 FPS. Complete private log: reports/background-scroll-check/interpolated/residual-seams-clean-smoke.log. Original diagnostic wrapper/preferences were restored afterward; normal campaign saves/preferences were not used by these runs.


## Project icon before IPA selection — 2026-10-07

The no-argument application picker previously selected touchHLE's upstream icon. Project builds now embed the existing, original eight-beet `native/app-icon.png` at build time and use it unchanged as the picker's SDL application icon. Both developer and source-release layouts are supported. No IPA, game icon or game assets are needed. A standalone upstream checkout without the project image retains its original branding. The native launcher's missing-IPA alert explicitly loads its existing bundled `AppIcon.icns` and assigns it to the alert and application.

An isolated empty application directory also exposed an existing picker panic: game compatibility hooks queried `CFBundleIdentifier` on its empty fake bundle. The fake bundle now identifies itself as `org.touchhle.app-picker`, avoiding game-only hooks. A focused regression covers this identity. The picker was opened without an IPA and its empty-directory message was observed; it then closed normally. Its pre-existing vertically inverted content was observed too and is outside this icon change. The full startup log is private at `reports/startup-icon/picker.log`. Native missing-IPA validation ran, but computer-use timeouts prevented visual verification of its alert.

All 9 project tests and all 96 Rust library tests pass (OpenAL tests use the null host-audio backend). The embedded PNG matches the project image byte-for-byte. The ordinary and test-tools release builds are refreshed. The complete source patch applies to the pinned upstream revision and reproduces all 77 changed source files. No release ZIP or published release was replaced.


## Guest icon size in the macOS Dock — 2026-10-07

After an IPA was loaded, SDL replaced the project startup icon with the guest icon. The supplied game's icon is 57×57 and previously filled the Dock canvas edge to edge. The macOS window setup now centers that image on a 71×71 transparent host canvas: its artwork occupies approximately 80% of the Dock slot. Original icon pixels, rounded corners, alpha and aspect ratio are retained. This transform applies only to the loaded application's macOS host icon; guest/picker thumbnail images and the project startup icon are unchanged. No game image is extracted or added to the patch.

Two handwritten pixel regressions verify the full transparent margin, unchanged source pixels including alpha, and centered non-square artwork without stretching. All 98 Rust library tests pass with the null host-audio backend and all 9 project tests pass. Both local release builds are refreshed. A normal release smoke run loaded the original supplied IPA from its existing path, reached the title screen and quit normally using an isolated data directory. Private log: `reports/dock-icon-size/run.log`. The computer-use screenshot shows the title window; no direct Dock screenshot was available, so the size check rests on the verified image canvas and unchanged SDL application-icon path. The compatibility patch applies and reproduces all 77 changed files.


## Final review: avoid unconditional rebuilds for the application icon — 2026-10-07

The final review found both candidate icon paths registered with Cargo even though one is absent in each supported layout. Cargo treats a watched missing file as dirty, reruns the build script, and rewrites the embedded PNG, causing unnecessary recompilation. The build now watches existing icon files only; if a candidate's immediate asset directory exists but its icon does not, it watches that directory for the file to appear. Missing directories are skipped, avoiding both missing-file fingerprints and recursive watches over build output. Checkout and source-release icon selection are retained.

Both ordinary and test-tools release builds completed successfully, and each configuration passed all 98 Rust library tests using OpenAL's null backend. All 9 project tests passed, including compilation and validation of the native launcher. A second consecutive ordinary release build completed in 0.18 seconds with no compilation. Its recorded Cargo fingerprint contains only existing paths. Private evidence is under `reports/final-review-fix/`. The compatibility patch applies to the pinned upstream revision and reproduces all 77 changed source files. Updated TODO entries record the startup/Dock icons and this review fix; residual seams, Windows and clean-device release validation remain open.
