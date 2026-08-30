# Two-factor authentication codes are rejected

If a 2FA code from an authenticator app is always marked "invalid":

1. Check the device's clock is set to automatic/network time. 2FA codes
   are time-based, and a clock even a minute off will cause every code
   to fail.
2. Make sure the code is being entered before it expires (codes typically
   rotate every 30 seconds).
3. If codes were set up on a device that was later reset, the 2FA secret
   needs to be regenerated from account settings.

If none of this helps, the account may need 2FA disabled and re-enrolled
from scratch on the server side.
