# Test Plan

## Automated suite

Run from the project root:

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m unittest discover -s tests -v
```

The suite covers OAuth scope selection, full reconnect consent, legacy-token migration, refresh and disconnect cleanup, friendly insufficient-scope errors, filename parsing, collaborator extraction, Unicode, Chief Keef description migration, dynamic description years and producer credits, automatic artist hashtags, custom tag handling and legacy-tag migration, Made for kids upload payloads, unresolved placeholders, tag deduplication, dark Windows combo-box popups, button wiring, natural sorting, scan limits, SHA-256, chronological scheduling, Europe/Berlin DST transitions, UTC conversion, crop calculations, exact 1920 × 1080 JPG output, full-frame preview fitting, cancellable thumbnail batches, monochrome/red/blue/custom tone filtering, watermark corner anchors and margins, file-size compliance, overwrite protection, settings persistence, SQLite migration, duplicates, queue recovery, non-repeating thumbnail pools and the offline mock YouTube service.

## Manual Windows checklist

1. Install on a clean Windows 10 64-bit VM with no Python installed.
2. Confirm exact name **UPLOAD PLUGG** in installer, Program Files, Start Menu, desktop option, title bar, executable metadata and uninstall list.
3. Confirm permanent `Powered by: Dakuza` at the bottom of the sidebar and on Settings/About.
4. Disconnect network and verify all offline functions plus Dry Run remain usable.
5. Scan paths containing spaces, `äöüß`, accented characters and 30 tiny MP4 test fixtures.
6. Confirm `1`, `2`, `10` natural order, manual table edits, selection limit and queue recovery after restart.
7. Generate each thumbnail layout from portrait, square and landscape PNG/JPG sources; compare preview and output dimensions/size.
8. Randomize more videos than thumbnails and verify no repeat within each pool cycle.
9. Preview scheduling across the March and October Europe/Berlin clock transitions.
10. Confirm minimize-to-tray, notification behavior, pause/resume/cancel and active-upload exit warning.
11. Confirm keep-awake becomes active only during uploads and is released afterward.
12. Export history, Dry Run formats and support bundle; inspect for tokens/client secrets.

## Opt-in real YouTube checklist

Use a dedicated private test video and channel. Never run this automatically.

1. Complete `GOOGLE_OAUTH_SETUP.md` with a Desktop client and test user.
2. Connect and confirm that Google requests both upload access and read-only channel access.
3. Confirm the exact channel name and verify that `channels.list(part="snippet", mine=True)` does not produce a 403.
4. Restart UPLOAD PLUGG and confirm the same channel is restored without another login.
5. Disconnect, confirm the channel is cleared, then connect a different test account through Google's account chooser.
6. Upload one tiny video as private without a custom thumbnail.
7. Upload another private video with a generated JPG thumbnail below 2 MB.
8. Schedule a private test upload at least 30 minutes in the future; confirm `publishAt` in YouTube Studio.
9. Interrupt network during a larger private upload, restore it, and confirm in-process resumable retry.
10. Repeat the same file and confirm the local hash/filename/title duplicate warning can be skipped or overridden.
11. Force a harmless validation error such as an overlong title and confirm **Start Uploads** remains blocked.
12. Revoke OAuth access, trigger an authenticated action and confirm reconnect guidance.
13. Delete private test videos manually from YouTube Studio after recording results.

Record OS build, UPLOAD PLUGG version, credential project audit state, test time, expected result, actual result, screenshots and sanitized logs. Never attach the OAuth client JSON or token material.
