# Changelog

## 1.0.4

- Added `youtube.readonly` alongside `youtube.upload` so the authorized channel can be read with `channels.list(mine=True)`.
- Forces a complete browser consent flow on reconnect and asks Google to show the account chooser.
- Detects and removes legacy upload-only tokens before they can produce a 403 insufficient-permissions error.
- Reuses valid credentials after restart, refreshes expired access tokens and requests a new login for invalid or revoked refresh tokens.
- Keeps OAuth tokens in Windows Credential Locker and removes both the stored credential and known legacy token files on disconnect.
- Replaces raw insufficient-scope API errors with clear disconnect-and-reconnect instructions while retaining technical log details.
- Added OAuth scope, refresh, restart persistence, disconnect cleanup and friendly-error regression coverage.
- Added a Stop Generation button that safely ends a thumbnail folder batch after the current image.
- Fixed the Thumbnail Generator preview so the complete 16:9 output remains visible when the window or preview area changes size.
- Updated and migrated the Chief Keef Type Beat description with Dakuza contact details, dynamic collaborator credits and publication-year search terms.
- Added optional PNG/JPG watermark placement at the bottom-left or bottom-right with adjustable scale and safe edge margin.
- Added detail-preserving monochrome, red-tone, blue-tone and custom-color thumbnail filters with adjustable strength.

## 1.0.3

- Removed the legacy automatically generated `{ARTIST}`, beat-name, producer and year tag list from existing and new presets while preserving every custom tag list.
- Added a live YouTube tag-usage counter and blocks saving presets above YouTube's 500-character calculation.
- Added exactly three automatic description hashtags derived from the Artist field or preset name: artist, artist type beat and artist type beat plus publication year.
- Preserved dynamic `Prod. Dakuza & Collaborator` credits in generated descriptions.
- Added a per-preset Made for kids switch with an explicit comments-enabled/comments-disabled status.
- Forced every combo box to use a Qt-owned dark popup with a black background and white text on Windows.
- Added metadata, migration, audience-payload and Windows UI coverage for the new behavior.

## 1.0.2

- Added automatic debounced live preview updates for crop, zoom, blur, darkness, saturation and size controls.
- Added a dedicated background selector with artwork blur/darkening or a freely selectable solid color.
- Added random preview selection from Source Folder, a New Random Preview button and Generate Random Thumbnail.
- Kept Generate Thumbnail(s) as the full-folder batch action.
- Changed all combo-box popup menus to a black background with readable white text.
- Added feedback for actions that need a selected video or history row.
- Added automated wiring coverage for every named button plus Windows UI tests for the new thumbnail controls.

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
