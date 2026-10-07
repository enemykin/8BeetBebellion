// SPDX-License-Identifier: MIT
// Copyright (c) 2026 enemykin
#import <Cocoa/Cocoa.h>
#include <signal.h>
#include <sys/file.h>
#include <fcntl.h>
#include <unistd.h>

static volatile sig_atomic_t childPID;

static void forwardSignal(int signalNumber) {
    if (childPID > 0) kill(childPID, signalNumber);
}

static int fail(NSString *message, BOOL checkOnly, NSURL *input) {
    fprintf(stderr, "%s\n", message.UTF8String);
    if (!checkOnly) {
        [NSApplication sharedApplication];
        [NSApp setActivationPolicy:NSApplicationActivationPolicyAccessory];
        [NSApp activateIgnoringOtherApps:YES];
        NSString *iconPath = [[NSBundle mainBundle] pathForResource:@"AppIcon" ofType:@"icns"];
        NSImage *icon = iconPath ? [[NSImage alloc] initWithContentsOfFile:iconPath] : nil;
        if (icon) [NSApp setApplicationIconImage:icon];
        NSAlert *alert = [[NSAlert alloc] init];
        if (icon) alert.icon = icon;
        alert.messageText = @"8BeetBebellion";
        alert.informativeText = message;
        [alert addButtonWithTitle:@"Close"];
        if (input) [alert addButtonWithTitle:@"Open input folder"];
        if ([alert runModal] == NSAlertSecondButtonReturn && input)
            [[NSWorkspace sharedWorkspace] openURL:input];
    }
    return 1;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        BOOL checkOnly = argc == 2 && strcmp(argv[1], "--check") == 0;
        if (argc > 1 && !checkOnly)
            return fail(@"Unknown option. Use --check to validate the package without launching.", YES, nil);
        NSBundle *bundle = [NSBundle mainBundle];
        NSURL *root = bundle.bundleURL.URLByDeletingLastPathComponent;
        NSURL *input = [root URLByAppendingPathComponent:@"input" isDirectory:YES];
        NSURL *runtime = [root URLByAppendingPathComponent:@"runtime" isDirectory:YES];
        NSURL *reports = [root URLByAppendingPathComponent:@"reports" isDirectory:YES];
        NSFileManager *fm = [NSFileManager defaultManager];
        NSError *error = nil;
        for (NSURL *directory in @[input, runtime, reports]) {
            if (![fm createDirectoryAtURL:directory withIntermediateDirectories:YES attributes:nil error:&error])
                return fail([NSString stringWithFormat:@"Cannot prepare %@. Move the entire package to a writable folder.\n%@", directory.path, error.localizedDescription], checkOnly, nil);
        }
        NSDictionary *originalEnvironment = [NSProcessInfo processInfo].environment;
        NSString *override = originalEnvironment[@"BEBELLION_IPA"];
        NSURL *ipa = override.length ? [NSURL fileURLWithPath:override] :
            [input URLByAppendingPathComponent:@"8Bit Rebellion v1.4.5.ipa"];
        if (!override.length && ![fm fileExistsAtPath:ipa.path]) {
            NSArray<NSURL *> *files = [fm contentsOfDirectoryAtURL:input includingPropertiesForKeys:nil options:NSDirectoryEnumerationSkipsHiddenFiles error:&error];
            NSMutableArray<NSURL *> *candidates = [NSMutableArray array];
            for (NSURL *file in files) {
                if ([file.pathExtension.lowercaseString isEqualToString:@"ipa"])
                    [candidates addObject:file];
            }
            if (candidates.count == 1) ipa = candidates.firstObject;
            else if (candidates.count > 1)
                return fail(@"Several IPA files are in input. Keep only your iPhone 1.4.5 IPA there, or name it 8Bit Rebellion v1.4.5.ipa.", checkOnly, input);
        }
        NSNumber *regular = nil;
        [ipa getResourceValue:&regular forKey:NSURLIsRegularFileKey error:nil];
        if (!regular.boolValue || ![fm isReadableFileAtPath:ipa.path])
            return fail(@"Add your own decrypted iPhone 1.4.5 IPA to the input folder beside this application, then open the application again.", checkOnly, input);

        NSURL *macOS = [bundle.bundleURL URLByAppendingPathComponent:@"Contents/MacOS" isDirectory:YES];
        for (NSString *name in @[@"touchHLE", @"ffmpeg", @"ffplay"]) {
            if (![fm isExecutableFileAtPath:[macOS URLByAppendingPathComponent:name].path])
                return fail([NSString stringWithFormat:@"Missing bundled executable: %@. Unpack the complete release archive again.", name], checkOnly, nil);
        }
        for (NSString *name in @[@"touchHLE_dylibs", @"touchHLE_fonts", @"touchHLE_default_options.txt"]) {
            if (![fm fileExistsAtPath:[bundle.resourceURL URLByAppendingPathComponent:name].path])
                return fail([NSString stringWithFormat:@"Missing bundled resource: %@.", name], checkOnly, nil);
        }
        if (checkOnly) {
            printf("Package 0.3 is ready. IPA: %s\nRuntime: %s\n", ipa.path.UTF8String, runtime.path.UTF8String);
            return 0;
        }
        int lock = open([runtime URLByAppendingPathComponent:@"launcher.lock"].fileSystemRepresentation, O_CREAT | O_RDWR | O_CLOEXEC, 0600);
        if (lock < 0 || flock(lock, LOCK_EX | LOCK_NB) != 0) {
            if (lock >= 0) close(lock);
            return fail(@"The game is already running, or its runtime folder is not writable.", NO, nil);
        }
        NSDateFormatter *formatter = [[NSDateFormatter alloc] init];
        formatter.locale = [NSLocale localeWithLocaleIdentifier:@"en_US_POSIX"];
        formatter.dateFormat = @"yyyy-MM-dd_HH-mm-ss";
        NSString *logName = [NSString stringWithFormat:@"run-%@-%d.log", [formatter stringFromDate:[NSDate date]], getpid()];
        NSURL *logURL = [reports URLByAppendingPathComponent:logName];
        if (![fm createFileAtPath:logURL.path contents:nil attributes:nil]) {
            close(lock);
            return fail(@"Cannot create a startup log in reports. Move the package to a writable folder.", NO, nil);
        }
        NSFileHandle *log = [NSFileHandle fileHandleForWritingToURL:logURL error:&error];
        if (!log) { close(lock); return fail(error.localizedDescription, NO, nil); }
        NSMutableDictionary *environment = [originalEnvironment mutableCopy];
        for (NSString *key in originalEnvironment) {
            if ([key hasPrefix:@"DYLD_"] || [key hasPrefix:@"SDL_"] || [key hasPrefix:@"BEBELLION_TEST_"])
                [environment removeObjectForKey:key];
        }
        [environment removeObjectForKey:@"ALSOFT_DRIVERS"];
        if ([originalEnvironment[@"BEBELLION_MUTE"] isEqualToString:@"1"]) {
            environment[@"ALSOFT_DRIVERS"] = @"null";
            environment[@"SDL_AUDIODRIVER"] = @"dummy";
        }
        environment[@"PATH"] = [macOS.path stringByAppendingString:@":/usr/bin:/bin:/usr/sbin:/sbin"];
        environment[@"BEBELLION_DATA_DIR"] = runtime.path;
        NSTask *task = [[NSTask alloc] init];
        task.executableURL = [macOS URLByAppendingPathComponent:@"touchHLE"];
        task.currentDirectoryURL = runtime;
        task.environment = environment;
        task.arguments = @[ipa.path, @"--landscape-right", @"--landscape-content-layout",
            @"--tolerate-nil-dictionary-keys", @"--no-error-popup", @"--keyboard-game-controls",
            @"--button-to-touch=DPadLeft,40,290", @"--button-to-touch=DPadRight,135,290",
            @"--button-to-touch=A,455,290"];
        task.standardOutput = log;
        task.standardError = log;
        [log writeData:[[NSString stringWithFormat:@"8BeetBebellion 0.3\nStarted: %@\nIPA: %@\nRuntime: %@\n", [NSDate date], ipa.lastPathComponent, runtime.path] dataUsingEncoding:NSUTF8StringEncoding]];
        if (![task launchAndReturnError:&error]) {
            [log closeFile]; close(lock);
            return fail([NSString stringWithFormat:@"Could not start the emulator.\n%@\nLog: %@", error.localizedDescription, logURL.path], NO, nil);
        }
        childPID = task.processIdentifier;
        signal(SIGTERM, forwardSignal); signal(SIGINT, forwardSignal); signal(SIGHUP, forwardSignal);
        [task waitUntilExit];
        childPID = 0;
        int status = task.terminationStatus;
        [log writeData:[[NSString stringWithFormat:@"\nFinished: %@; exit status: %d\n", [NSDate date], status] dataUsingEncoding:NSUTF8StringEncoding]];
        [log closeFile]; close(lock);
        if (status != 0)
            return fail([NSString stringWithFormat:@"The game stopped unexpectedly (status %d).\nStartup log: %@", status, logURL.path], NO, nil);
        return 0;
    }
}
