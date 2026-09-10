# App crashes immediately on startup

If the app closes itself right after opening, before any screen loads:

1. Restart the device. A stale background process is the most common cause.
2. Update the app to the latest version; startup crashes are usually fixed
   in the next release once reported.
3. As a last resort, uninstall and reinstall the app. This clears any
   corrupted local cache that may be causing the crash.

If the crash still happens on the latest version right after a clean
install, this indicates a device-compatibility bug that needs to be
escalated to engineering with the device model and OS version.
