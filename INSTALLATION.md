# Installing UPLOAD PLUGG

## Normal installer

1. Copy `UPLOAD_PLUGG_1.0.2_Update.exe` to the Windows 10 64-bit computer.
2. Double-click it and approve the Windows administrator prompt.
3. Keep the default destination `C:\Program Files\UPLOAD PLUGG`.
4. Optionally enable the desktop shortcut.
5. Finish installation and launch **UPLOAD PLUGG** from the Start Menu.

The installer includes Python and all required runtime libraries. The end user does not install Python and does not open a terminal.

If Windows SmartScreen appears for an unsigned private build, verify that the installer came from the person who built it, choose **More info**, and continue only if you trust that file. A production release should be signed with a trusted code-signing certificate.

## Portable build

Extract `UPLOAD_PLUGG_1.0.2_Portable.zip` into a normal writable folder and start `UPLOAD PLUGG.exe`. Do not launch the executable from inside the ZIP. The portable executable still stores personal runtime data in `%LOCALAPPDATA%\UploadPlugg` so updates do not overwrite settings or history.

## First launch

1. Open **Settings**.
2. Complete [GOOGLE_OAUTH_SETUP.md](GOOGLE_OAUTH_SETUP.md) if you want real uploads.
3. Put the downloaded desktop OAuth file at `%LOCALAPPDATA%\UploadPlugg\config\client_secret.json`.
4. Select **Connect YouTube Channel** and confirm the exact channel shown at the top.
5. Use **Upload Generator** for videos or **Thumbnail Generator** for offline image processing.

Without OAuth or internet, the application still supports scanning, templates, presets, schedules, thumbnails, history, validation and Dry Run.

## Updating

Close active uploads, run the newer installer over the current installation, and keep the same installation folder. Settings, queue, credentials, logs and history are outside Program Files and remain intact. Database migrations run when the new version starts.

## Uninstalling

Use **Windows Settings → Apps → UPLOAD PLUGG → Uninstall**. The program files and shortcuts are removed. Personal data in `%LOCALAPPDATA%\UploadPlugg` is intentionally preserved to prevent accidental history loss. Delete that folder manually only after exporting anything you need and disconnecting the channel.
