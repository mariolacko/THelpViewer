# Admin-managed accounts and Passkeys

Accounts are created only with a valid one-hour registration token. Public
registration without a token and password login do not exist. HELP browsing and global search
remain public. The Login / Passkey dialog in the Help menu is a real WebAuthn
client, but signing in does **not yet** grant access to Server Terminal jobs;
their existing ID/key mechanism is separate until that workflow is redesigned.

`thelpviewer/server/accounts.py` owns account storage and Passkey ceremonies;
`thelpviewer/server/routes/auth.py` owns the HTTP endpoints, origin checks and
session cookie. `app.py` only creates the store and registers the router.

The account database is `THELP_STATE_DIR/accounts.sqlite3`, separate from the
global HELP index and visitor statistics. On the first server start with no
accounts, the server creates a one-hour first-admin token and prints it to its
logs. Retrieve it with:

```sh
docker compose logs viewer | grep 'first administrator registration token' | tail -n 1
```

Do not use `--tail` if the server has handled many requests since startup;
the token line may have scrolled out of the selected log range. A new token is
printed only while the account database contains no users.

Open **Help → Login / Passkey → Register**, enter your name, email and this
token, then confirm Passkey creation. This first account becomes administrator.
After the server confirms the account and signed-in session, an Information
MessageBox confirms registration; pressing OK closes both Register and Login.
If Register stays open with an error, saving a Passkey in the browser alone
does not confirm server registration.
The token is single-use and expires after one hour. Restart the server to
rotate an expired, unused bootstrap token, then use the **latest** token in the
logs; only its hash is stored in SQLite.
New tokens use a Windows-key-like `XXXXX-XXXXX-XXXXX-XXXXX-XXXXX` layout
(125 random bits). The registration input uppercases characters and inserts
hyphens automatically; a pasted new token also works without hyphens. Older
registration-token formats are rejected even if a token has not expired.
After deploying this change, restart the server to print a new bootstrap token
if no administrator exists; otherwise generate a new token while signed in as
administrator.

A signed-in administrator sees **Registration Token** in the Help menu. Its
Generate button issues a one-hour, single-use token to give privately to a new
user. The dialog lists unexpired, unused tokens with their expiry. Selecting a
row fills the token input for copying and enables **Delete**; deletion requires
confirmation and immediately revokes that token. Closing the confirmation
MessageBox or pressing Escape keeps the token valid. The list is available after
signing in again. Newly issued token values are encrypted in
`THELP_STATE_DIR/accounts.sqlite3` using a private key in
`THELP_STATE_DIR/registration-tokens.key`; back up both files together and
keep the key private. Tokens issued before this change stored only a hash:
they remain valid until use or expiry and can be deleted, but their full value
cannot be recovered. `GET /api/auth/registration-tokens` and
`DELETE /api/auth/registration-tokens/{token_hash}` require an administrator
session; the list response is marked `no-store`.
The new user registers their name, email and Passkey with that token and
becomes a regular member. Do not put a token in a URL or public log. The email
address is an account identifier, not yet a verified
mailbox; possession of the invitation token is the registration gate. Existing
pre-bootstrap CLI accounts remain supported; the first
legacy account becomes the administrator on database migration. An
administrator with shell access can still create a legacy username account:

```sh
docker compose exec viewer python -m thelpviewer.server.accounts create mario --name "Mario Lacko"
```

Its CLI enrollment token can be used through the retained API, but the normal
browser registration flow uses name, email and a one-hour registration token.
Later, sign in with email (or the username of a legacy account); no token or
password is needed. The server validates challenge, RP ID, origin, user
verification and signature with `py_webauthn`. Challenges are single-use and
expire after five minutes. Sessions use random opaque IDs, stored only as
hashes in SQLite and sent in HttpOnly, SameSite=Strict cookies. The cookie is
also Secure for HTTPS deployments. Sign Out invalidates the server session.

`THELP_AUTH_ORIGIN` must be the exact browser origin, including scheme and
port. The local Docker default is `http://localhost:5448`; browsers treat
localhost as a secure context for WebAuthn. For the public site set, for
example, `THELP_AUTH_ORIGIN=https://thelp.zdrojak.dev` in the deployment
`.env`, then run `docker compose up -d --force-recreate viewer`. A plain
`docker compose restart` does not reload changed environment variables.
When deploying Passkey code or changed Python requirements, add `--build`:
`docker compose up -d --build --force-recreate viewer`. Without a rebuilt image,
the bind-mounted code can run against an old image lacking `webauthn`; Passkey
requests then return JSON HTTP 503. Verify the installed package with
`docker compose exec -T viewer python -c 'import webauthn'`.
`THELP_PUBLIC_BASE_URL` controls canonical/sitemap links, not Passkey login;
without a matching `THELP_AUTH_ORIGIN`, `/api/auth/session` reports
`"enabled": false` and registration returns HTTP 503. Passkeys are bound
to their RP ID: a key enrolled on `localhost`
cannot sign in at `thelp.zdrojak.dev`.
If a browser reports a generic Passkey error, the registration dialog now
indicates whether it occurred while obtaining options, creating the Passkey,
or verifying it. The server also uses this HTTPS origin for generated public
links when `THELP_PUBLIC_BASE_URL` is unset and the request host matches, so
robots.txt does not advertise an HTTP sitemap behind a TLS-terminating proxy.

Before enabling the public origin, secure the Cloudflare-to-origin hop with
HTTPS and [Full (strict)](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/).
Cloudflare's [Origin CA](https://developers.cloudflare.com/ssl/origin-configuration/origin-ca/)
can provide the origin certificate. Browser-to-Cloudflare HTTPS alone is not
enough when the origin still uses plaintext HTTP. Configure Cloudflare rate
limits for the auth API before public rollout; the current application does
not yet provide account recovery or administrative account management in the
browser.

Email is not required for administrator-created accounts. If public
registration is added later, Cloudflare [Email Service](https://developers.cloudflare.com/email-service/get-started/send-emails/)
can send verification mail from FastAPI over its HTTPS REST API after domain
onboarding. Email Routing alone is for inbound forwarding, not outbound
registration messages.
