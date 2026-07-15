# Google OAuth Setup

UPLOAD PLUGG uses the official installed-application OAuth flow and the minimum upload scope. It never asks for a Google password.

## Create credentials

1. Open [Google Cloud Console](https://console.cloud.google.com/) and create or select a project.
2. Open **APIs & Services → Library**, find **YouTube Data API v3**, and enable it.
3. Open **Google Auth Platform** or **APIs & Services → OAuth consent screen**.
4. Configure the app name as `UPLOAD PLUGG`, add your support email and complete the required contact fields.
5. For private testing, keep the app in testing status and add the Google account that owns the target channel as a test user.
6. Open **Clients / Credentials → Create credentials → OAuth client ID**.
7. Choose **Desktop app**. Do not choose Web application.
8. Download the client JSON file.
9. In UPLOAD PLUGG, click **Connect YouTube Channel**.
10. Select the downloaded JSON file when the file picker opens. UPLOAD PLUGG validates and stores it in the correct local configuration folder automatically.

The included `config/oauth_client.example.json` documents the shape only; it is not a working credential and must never be uploaded to a public repository with real secrets.

## Connect the channel

1. In UPLOAD PLUGG, select **Connect YouTube Channel**.
2. Windows opens the default browser. If Opera is the default, it opens in Opera; the application does not control an existing tab.
3. Sign in to Google and choose the account/channel.
4. Review and grant the requested YouTube upload permission.
5. Return to UPLOAD PLUGG and verify the displayed connected channel name before uploading.

OAuth returns to a temporary localhost port. Windows Firewall may ask whether Python or UPLOAD PLUGG may accept a local connection. Allow local/private access for the callback. No external server is required.

## Token storage and disconnecting

The refresh token is stored through the operating system keyring. It is not written to logs, settings exports or support bundles. **Disconnect Channel** removes the stored authorization from UPLOAD PLUGG. You can also revoke access from your Google Account security page.

## Important Google restriction

Google states that videos uploaded by unverified API projects created after 28 July 2020 are restricted to private viewing until the API project passes a compliance audit. Scheduling is requested by uploading privately and setting `publishAt`, but an unaudited project may remain private. See the official [YouTube video resource documentation](https://developers.google.com/youtube/v3/docs/videos).

## Common OAuth errors

- **access_denied / app not verified:** add the account under test users or complete Google's verification process.
- **redirect_uri_mismatch:** recreate the credential as a Desktop app and keep `http://localhost` in its downloaded configuration.
- **No YouTube channel:** create a YouTube channel for that Google account or authorize the correct Brand Account.
- **Token refresh failed:** disconnect, delete/recreate the OAuth client if necessary, then reconnect.
