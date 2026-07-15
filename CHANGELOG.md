# Changelog

## 1.0.1

- Fixed background tasks that could be collected before starting.
- Fixed internet status remaining on `Checking internet`.
- Fixed Connect Channel and Connect YouTube Channel appearing unresponsive.
- Fixed Generate Preview, Generate Thumbnail(s), metadata generation and other background actions.
- Added a guided Google OAuth Desktop JSON file picker and validation.
- Made connectivity detection more robust and prevented false offline status from blocking uploads.
- Added an in-place update installer that preserves settings, presets and upload history.
- Closed SQLite connections explicitly so Windows never keeps test or data files locked.
- Made the Windows build fail immediately when any external build or test command fails.
