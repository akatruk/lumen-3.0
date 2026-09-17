# Google sign-in

Production accepts only Google sessions whose verified email appears in GOOGLE_ALLOWED_EMAILS (comma-separated exact email addresses, case-insensitive). Current list: andreykatruk@gmail.com. Password login and invite registration are disabled by GOOGLE_SSO_ONLY=true; existing password sessions cannot access private APIs. Existing project ownership is preserved when the verified Google email matches an existing account.

The server uses authorization code exchange, PKCE S256, a short-lived browser binding cookie and single-use database state. Identity is obtained directly from Google's userinfo endpoint with the server-exchanged access token; Google subject is stored separately. Provider credentials are server-only. OAuth callback query strings are excluded from nginx logs and uvicorn access logging is disabled.

Configure the existing Google OAuth web client in Google Cloud Console:

Authorized redirect URI:
https://lumen-fix.universalgravity.org/api/auth/google/callback

If the consent screen is in Testing, add andreykatruk@gmail.com as a test user. Only openid/email scopes are requested. Do not remove redirect URIs used by other projects.

Validation: frontend production build passed; 11 authentication/API tests passed locally and on the VM. Browser verified the Google button and real authorization redirect. After updating to the user-provided OAuth client, the real Google authorization flow opens the account chooser without redirect_uri_mismatch. Completing the sign-in requires the user to authenticate with Google; the account shown in the browser is signed out.

Google reference: https://developers.google.com/identity/protocols/oauth2/web-server
