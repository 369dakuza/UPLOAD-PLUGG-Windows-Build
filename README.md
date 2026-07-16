# UPLOAD PLUGG

UPLOAD PLUGG 1.1.1 is a Windows 10/11 64-bit desktop application for preparing and sequentially uploading finished type-beat videos to YouTube. It combines a local batch workflow, metadata templates, scheduling, duplicate warnings, upload history and an offline thumbnail generator in one premium dark-crimson interface.

**Powered by: Dakuza**

## What is included

- Official Google OAuth desktop flow with upload and read-only channel scopes, secure token refresh and complete disconnect; no Google password, cookies or recovery codes are requested.
- Crash-resistant, cancellable MP4 folder scan with fresh queue reconciliation, natural numeric ordering, editable beat/collaborator parsing and 1–30 item batches.
- Preset-based titles, custom 500-character YouTube tags, automatic artist hashtags and `Prod. Dakuza & Collaborator` credit generation.
- Per-preset Made for kids control; the default is off so comments remain available.
- Europe/Berlin scheduling with daylight-saving handling and per-item preview.
- Resumable sequential YouTube upload, exponential retry with jitter, custom thumbnail application and Windows keep-awake.
- 1920 × 1080 JPG generator with square-center/blurred-sides, crop, fit and solid-side modes, full-frame preview, cancellable folder batches, corner watermarks and tone-preserving color filters.
- Non-repeating randomized thumbnail pools, persistent queue, single/multi-row removal, SQLite history and local duplicate checks.
- Dry Run exports in JSON, CSV and readable text without any YouTube upload.
- Dashboard, upload generator, thumbnail generator, presets, schedule, history, logs and settings pages.
- Clean thread shutdown on window close, system-tray notifications, pause/resume/cancel controls and support-bundle export with secret redaction.
- PyInstaller standalone build, Inno Setup installer, icon, Windows metadata and automated tests.

## Quick start for development

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
$env:PYTHONPATH = "$PWD\src"
python run.py
```

For a normal end-user installer, run `build_windows.ps1`; see [BUILD_WINDOWS.md](BUILD_WINDOWS.md).

## Data location

Runtime data is stored in `%LOCALAPPDATA%\UploadPlugg\`, never inside Program Files. Source videos and artwork are never moved, renamed, deleted or modified. Only upload-ready thumbnail copies are written to the cache.

## Documentation

- [Installation](INSTALLATION.md)
- [Google OAuth setup](GOOGLE_OAUTH_SETUP.md)
- [Windows build](BUILD_WINDOWS.md)
- [User guide](USER_GUIDE.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Privacy and local data](PRIVACY_AND_DATA.md)
- [Known limitations](KNOWN_LIMITATIONS.md)
- [Test plan](TEST_PLAN.md)

## API design facts

The application uses `videos.insert` with a resumable media upload, `thumbnails.set`, and the supported `status.publishAt` scheduling field. Official references: [video resource](https://developers.google.com/youtube/v3/docs/videos), [resumable upload protocol](https://developers.google.com/youtube/v3/guides/using_resumable_upload_protocol), and [custom thumbnail upload](https://developers.google.com/youtube/v3/docs/thumbnails/set).

End screens, cards, YouTube Studio checks and monetization review are not exposed as supported operations by the YouTube Data API used here. UPLOAD PLUGG therefore records them as manual post-upload work and opens the YouTube Studio edit page instead of pretending they were applied.

## Verification status

The automated test suite covers metadata, preset migration, audience settings, button wiring, Windows popup styling, thumbnail processing, storage, scheduling and upload payload construction. Python syntax compilation and project checks pass. OAuth authorization and a live private YouTube upload require the owner's Google Cloud credentials and an opt-in test channel; exact steps are in `TEST_PLAN.md`.
