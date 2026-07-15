# Known Limitations

## Official API boundaries

- YouTube end screens, cards, "import from latest video", monetization review and Studio checks are not configured by this project's official YouTube Data API integration. They remain manual post-upload tasks.
- Remote collision checks can compare recent titles only and can miss videos or produce false positives. Title similarity is never treated as definitive proof of a duplicate.
- API quota and the channel's upload/custom-thumbnail eligibility are controlled by Google.
- Google may force uploads from unaudited API projects to private status even when scheduling metadata is supplied.
- A running upload resumes through the current resumable session. After a crash/restart, the queue is recovered but the remote session may have expired, so the affected video can require a new upload session.

## First release boundaries

- One connected channel is supported at a time.
- Uploads are sequential. Two-upload parallel mode is intentionally not exposed in 1.0.0 because sequential operation is safer for quota, retries and creator review.
- Video folders are scanned only at their top level; subfolders are not included.
- "Windows Explorer order" is not a stable filesystem concept. Natural numeric order is the default, with explicit name/date/manual choices available.
- The thumbnail crop keeps a configurable center strategy but does not perform AI subject detection.
- Update checking is disabled until a real signed update endpoint exists.
- UI and documentation are English-only.

## Environment verification

Core logic tests run cross-platform. The supplied development environment is Linux and cannot perform a real Windows installer build, system-tray notification verification, Windows Credential Manager test, DPAPI behavior check or `SetThreadExecutionState` check. OAuth and live uploads also require the user's private credential and channel. These are covered by the opt-in manual plan rather than falsely reported as passed.

