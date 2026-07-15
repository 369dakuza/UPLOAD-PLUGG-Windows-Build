# Troubleshooting

## The app opens offline

This is expected. Folder scanning, templates, presets, scheduling, thumbnail generation, history, logs, validation and Dry Run remain available. Actual channel checks and uploads require internet access to Google services.

## No MP4 files are found

Confirm that the selected directory exists, files end in `.mp4`, and they are directly inside the selected folder. UPLOAD PLUGG does not recursively scan subfolders. Check that Windows can open the files and that another program has not removed them.

## OAuth credentials are missing

Follow `GOOGLE_OAUTH_SETUP.md`. The required file is `%LOCALAPPDATA%\UploadPlugg\config\client_secret.json`, created as a **Desktop app** credential.

## Browser authorization does not return

Allow the localhost callback through Windows Firewall, close stale authorization tabs, keep UPLOAD PLUGG running, and reconnect. Opera may be used automatically when it is the Windows default browser; no existing tab is automated.

## Upload remains private

An unaudited Google API project can be restricted to private uploads. This is a Google policy, not a scheduling bug. Review the project status in Google Cloud and the official YouTube API audit requirements.

## Upload fails or loses internet

Keep the app running. Transient timeouts and YouTube 500/502/503/504 responses use exponential retry with jitter. The current resumable session is reused during the running process. If the app or PC restarts, the queue is recovered, but a new remote session may be required because resumable URLs expire.

## Quota error

YouTube API operations consume the project's daily quota. Wait for quota reset or request a compliant quota increase in Google Cloud. Repeatedly retrying a permanent quota error will not help.

## Custom thumbnail fails

Verify that the channel is eligible for custom thumbnails. The API accepts JPG/PNG and currently documents a maximum upload size of 2 MB. UPLOAD PLUGG creates a compliant cached JPG; a damaged image or channel permission error still requires intervention.

## Scheduled time is rejected

Select a future time, ensure a valid timezone such as `Europe/Berlin`, and confirm that the video is private. Recalculate after daylight-saving changes or manual edits.

## Logs and support bundle

Use **Logs** for readable activity and **Settings → Export Support Bundle** for redacted diagnostics. Files are under `%LOCALAPPDATA%\UploadPlugg\logs`. Do not manually add `client_secret.json` or screenshots of Google security pages to a support bundle.

