# Release process notes

Suite-wide rules for packaging and shipping installers. They exist because
of real incidents, and each one is cheap to follow and expensive to learn
the hard way.

## Never re-publish a rebuilt version under the same tag

The suite's NSIS installers overwrite files only when the packed file is
newer than the installed one (NSIS defaults to `SetOverwrite ifnewer`, and
electron-builder's template does not change it). The mtimes packed into an
installer come from the build machine. An installer rebuilt after someone
installed the previous build carries older mtimes, so every file is
silently skipped: the installer runs to completion, the release notes are
right, and the machine keeps running the previous build without a single
warning.

Rules:

- A rebuilt package always ships under a **new version tag**. Deleting a
  draft and re-tagging the same version is only safe before anyone has
  installed the first build of it.
- When you must reinstall the same version over itself (testing a release),
  **uninstall first, then install**: a fresh install directory extracts
  every file regardless of mtimes. App data survives, because the suite's
  uninstallers do not delete user data.
- Verify what actually runs, not what was downloaded: when a "nothing
  changed" report arrives, compare the marker or hash of the installed
  build against the release's checksums before debugging anything else.

## First-paint reveal guard

Every Electron app of the suite creates its main window hidden and reveals
it on `ready-to-show`, which only fires when the first paint lands. A
stalled first paint (a stale GPU cache left by another build of the app is
enough) leaves the app running forever without a window, and the user sees
nothing come out of the installer. Each app either forces the reveal a few
seconds after the load settles, or uses an explicit show-on-demand model
where no window is expected at boot. When adding a window or a new app,
keep one of those two behaviors: a window that never painted must never be
the reason an app looks dead.
