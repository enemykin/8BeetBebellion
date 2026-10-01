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
