# UPLOAD PLUGG User Guide

## Prepare filenames

Keep finished videos together as MP4 files. A plain file such as `Hellcat.mp4` becomes beat name `Hellcat`. A final parenthetical producer such as `Hellcat (Stixx).mp4` becomes beat `Hellcat` and collaborator `Stixx`. Other parentheses remain visible and trigger a review warning. The original file is never renamed or moved.

## Create an upload batch

1. Open **Upload Generator** and choose the video folder.
2. Choose 1–30 videos and a sorting mode. Natural order places `1`, `2`, `10` correctly.
3. Select a preset and press **Scan Folder**.
4. Review/edit Beat Name, Collaborator and Generated Title directly in the table.
5. Edit the full description and your own comma-separated YouTube tags in the details panel.
6. Press **Generate Metadata** whenever you want to reset rows from the active preset.

The default title is `[FREE] Chief Keef Type Beat - "{BEAT_NAME}"`. The Chief Keef description contains Dakuza's Instagram and email, plus `Must credit: [{PRODUCER_CREDITS}]`. That produces `[Prod. Dakuza]` alone or `[Prod. Dakuza & Stixx]` with a collaborator. `{YEAR}` keeps the description's search-term year aligned with the scheduled publication date. UPLOAD PLUGG adds `#ChiefKeef #ChiefKeefTypeBeat #ChiefKeefTypeBeat{YEAR}` automatically above the description. The Presets page accepts your own YouTube tag list, shows its 500-character usage and does not add generic tags automatically. Keep **Made for kids** off for normal type beats so YouTube comments remain available.

## Thumbnails

Use **Thumbnail Generator** to choose an artwork image or folder and an output folder. The default layout creates a 1920 × 1080 JPG with a centered square and dark blurred sides. Alternative modes crop to 16:9, fit the full image over a background, or use solid sides. The preview always fits the complete 16:9 result inside its panel. During a folder run, **Stop Generation** finishes the image currently being written and then stops before the next one. Existing outputs are renamed automatically instead of overwritten.

The color-filter menu provides Original, Monochrome, Red Tones, Blue Tones and Change Color. These filters retain brightness and image detail while remapping the color family; Filter strength blends the filtered result with the original. An optional transparent PNG or JPG logo can be placed at Bottom Left or Bottom Right. Watermark size is relative to the free side area of the 1920 × 1080 canvas, and Edge margin keeps it away from the outer corner. A bottom-right logo stays anchored to that corner and grows upward and leftward.

In Upload Generator, choose **Random Thumbnails**, select a folder, and UPLOAD PLUGG assigns each selected video a different image until the pool is exhausted. A new shuffled cycle starts only when necessary. Source images remain unchanged; PNGs or oversized files are converted to temporary upload copies.

## Schedule

Enable weekdays, select a future start date, time and IANA timezone, then press **Calculate Schedule**. The initial Dakuza preset uses Tuesday, Thursday, Friday and Sunday at 18:00 Europe/Berlin. One chronological slot is assigned to each selected row. Daylight-saving offsets are calculated through the timezone database.

YouTube scheduling uses private upload plus the supported `publishAt` field. Confirm the timestamps in the table before upload.

## Validate and Dry Run

**Validate Batch** checks files, titles, descriptions, placeholders, tags, thumbnails and dates. Errors block uploads; warnings remain visible. **Run Dry Test** performs local preparation and exports JSON, CSV or text. A Dry Run never contacts YouTube to upload a video.

## Start uploads

Connect and confirm the channel, then select **Start Uploads**. The first connection after updating from an older upload-only authorization requires a complete browser login so Google can grant upload and read-only channel access together. Valid authorization is restored automatically after later app restarts. Use **Disconnect Channel** to remove the stored authorization before selecting another Google account.

Review video count, total size, dates, thumbnail count, duplicates and limitations. Confirm explicitly. Uploads run sequentially with resumable chunks and retry transient failures. The computer stays awake, but UPLOAD PLUGG never shuts it down or restarts it.

Minimize to the tray to keep working. Tray actions open the app, pause/resume the queue, cancel, show progress or exit. If a video fails, the next video can continue and the failure remains in history.

## After upload

Open **Upload History** to copy/open links and export records. End screens, cards, monetization and Studio checks are manual because the official upload API does not configure them. Open the generated Studio edit link and complete those items before final publication.
