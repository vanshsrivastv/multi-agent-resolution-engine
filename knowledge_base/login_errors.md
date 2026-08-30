# Login fails with error 500

If the app crashes or shows error 500 when logging in, this is usually caused
by a corrupted local session cache.

Fix:
1. Log out completely (or clear the app's local storage/cookies).
2. Close the app fully and reopen it.
3. Try logging in again.

If the error persists after a fresh login attempt, the account's session
token may be stuck on the server side and needs a manual reset.
