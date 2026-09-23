# Manual QA — password sign-in instead of Google

Target: https://lumen-fix.universalgravity.org/ on `142.93.248.163`.
Scope: the sign-in page no longer offers Continue with Google. Email and password sign-in is shown. A wrong password is rejected. No account is created during this check.

| # | Step | Expected |
| --- | --- | --- |
| 1 | Open `/api/health`. | HTTP 200 and `{"status":"ok"}`. |
| 2 | Open `/` while signed out. | There is no button named Continue with Google. Email address and Password fields are visible, with a Continue button. |
| 3 | Submit a wrong email and a 10-character password. | The request is rejected. The page stays on sign-in and does not enter the studio. |
| 4 | Switch to create-account and back. | The invitation field appears, then the form returns to email and password without the invitation field. |
