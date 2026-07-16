# Changelog

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
