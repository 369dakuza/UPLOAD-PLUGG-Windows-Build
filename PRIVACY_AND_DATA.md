# Privacy and Data

UPLOAD PLUGG is local-first creator software. It has no analytics endpoint, advertisement SDK, fabricated update server or developer-operated cloud database.

## Stored locally

`%LOCALAPPDATA%\UploadPlugg` contains:

- `config/settings.json`: UI preferences, presets, folders, schedule defaults, connected channel display metadata and thumbnail assignments.
- `upload_plugg.sqlite3`: recoverable queue, upload history, duplicate fingerprints, errors and post-upload state.
- `cache`: generated preview and upload-ready thumbnail copies.
- `logs`: rotating diagnostic logs.
- `exports`: user-created reports, history exports and support bundles.

OAuth access and refresh tokens are stored through Windows Credential Locker under `UPLOAD_PLUGG`, not in the install directory, `settings.json` or log files. The OAuth client JSON remains in `%LOCALAPPDATA%\UploadPlugg\config` and should be treated as private. It is covered by repository ignore rules and is never part of a normal source commit.

## Sent to Google/YouTube

When the user explicitly starts a real upload, the video bytes, title, description, tags, category, audience choice, scheduling metadata and optional thumbnail are sent to Google's official YouTube API endpoints using OAuth. The application requests `youtube.upload` for those uploads and `youtube.readonly` to retrieve the authorized channel identity and confirm the destination.

No Google password, YouTube password, browser cookie, recovery code or open Opera session is read or stored.

## Original files

Source MP4 videos and source images are opened read-only. UPLOAD PLUGG does not move, rename, delete, re-encode or modify them. Generated thumbnails go to the chosen output directory. Temporary compliant thumbnail copies go to the app cache.

## Exports and diagnostics

History and Dry Run exports omit OAuth tokens. The support-bundle builder includes platform metadata and redacted log text; patterns resembling tokens, client secrets and passwords are replaced. Review any diagnostic archive before sharing it because filenames, folder paths, titles or channel names may still be personally identifying.

## Deletion

Uninstallation preserves the local data folder to prevent accidental loss. To remove everything, first disconnect the channel, export needed records, uninstall, and delete `%LOCALAPPDATA%\UploadPlugg` manually. Revoking UPLOAD PLUGG from the Google Account security page invalidates server-side authorization as well.
