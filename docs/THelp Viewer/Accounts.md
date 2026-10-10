# Admin-managed accounts and Passkeys

Production accounts are created by a signed-in administrator or with a valid
one-hour registration token. Administrators invite new members to enroll their
own Passkeys. Public registration without a token and password login do not exist. HELP browsing and global search
remain public. The Login dialog opened by the right-aligned Login action is a real WebAuthn
client. Server Terminal and its old ID/key workflow have been removed.

`thelpviewer/server/accounts.py` owns account storage and Passkey ceremonies;
`thelpviewer/server/routes/auth.py` owns the HTTP endpoints, origin checks and
session cookie. `app.py` only creates the store and registers the router.

## Local development without Passkeys

For the VS Code integrated browser, start the explicit local-only Docker mode:

```sh
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build --force-recreate viewer
```

Open `http://localhost:5448` (or the configured `THELP_PORT`) and reload the
page. The existing `/api/auth/session` request automatically signs in as
**Admin**, using a normal HttpOnly/SameSite session cookie. Existing local accounts
with the old default label are renamed without changing their IDs, sessions or
DOS storage; custom profile names are preserved.
No WebAuthn or frontend authentication bypass is involved. Signing out
invalidates that session, but the next session check/reload signs in again
while development auto-login is enabled.

The override sets `THELP_DEV_AUTO_LOGIN=1`, a local HTTP auth origin and an
empty public base URL. It **replaces**, rather than appends to, the public
port mapping with `127.0.0.1:<port>:<port>`; Docker Compose 2.24.4+ is needed
for `!override`. Use a current Docker Engine (28+), with no direct container
routing or public proxy/tunnel to this development service. The loopback
binding is the network security boundary; a `Host: localhost` header alone
does not prove that a caller is local. Other processes on this computer and
containers on the same Docker network must be trusted.

The server refuses this mode with a public/HTTPS auth origin or nonempty
`THELP_PUBLIC_BASE_URL`. Development auth requests also reject Forwarded/
X-Forwarded headers, nonmatching origins/hosts and cross-site fetches. These
checks supplement the loopback binding, not replace it. **Never use this
override on a public host or expose its port via Cloudflare.**

Development accounts, registration tokens and sessions are stored separately
in `var/development/accounts.sqlite3`; production remains `var/accounts.sqlite3`.
A development cookie cannot authenticate against the production store. The
local account ID persists, so its DOS overlay remains in `var/dos/users/<id>/`.
It does not inherit any production account's private disk. HELP/MIDI resources,
server settings and other non-account state still use the existing local `var/`.

Return to Passkey-only mode with:

```sh
docker compose -f docker-compose.yml up -d --force-recreate viewer
```

The normal Compose file explicitly disables auto-login. Development data is
retained but its sessions are not accepted in normal mode. For a non-Docker
development server, setting the flag is also possible, but bind the server
to `127.0.0.1` yourself and leave the public base URL empty.

### Administrator rebuild actions

Only a signed-in administrator sees **User name → Configuration → Rebuild
DOS C / Rebuild MIDI**, on production and in local development. The corresponding
`POST /api/admin/rebuild/{dos|midi}` endpoints require an active administrator
session, the configured Host and exact browser Origin, and reject cross-site
fetches. Production supports the TLS-terminating proxy; local auto-login still
rejects all proxy headers. Anonymous requests and ordinary members receive 403.
`GET` reports progress without starting
preparation or deleting anything. Closing a confirmation or choosing Cancel
does not issue POST. The progress dialog's Hide button hides the view, not
the server operation; selecting Rebuild again reconnects to an ongoing job.

DOS rebuild replaces only `var/dos/base/` and restarts normal initialisation
from `dos-prompt.json`. User overlays/media under `var/dos/users/` and source
archives under `var/dos/downloads/` are retained. The current browser saves and
closes its DOS window first; other tabs must restart their emulator. Stale
base IDs are rejected rather than writing against the new disk. Rebuilding
while DOS preparation is already running returns 409.

MIDI rebuild cooperatively stops the downloader at the next source/track
boundary, waiting for any in-flight HTTP/extraction/write to finish before
moving `var/midi/`. It then recreates tracks, covers and `library.sqlite3`
from `midi-sources.json`. Playback in the current browser stops first. No old
writer is allowed to recreate obsolete files after the reset. Fresh catalog
tracks can be prioritized/played as they download. A second simultaneous MIDI
rebuild returns 409; failed downloads are reported in progress/catalog status.

Old active directories move to unique `var/backups/dos-base-<id>/` and
`var/backups/midi-<id>/` backups; they are not overwritten or silently purged.
These backups are recoverable but retain their full disk usage. For manual
recovery, stop the server, move the failed/new directory aside and restore the
chosen backup to its original path before restarting. Do not merge generations
while a worker runs. Accounts, statistics, server settings and private disks
are not reset by either action. No automatic rollback is performed.

Colors is available through the system menu and every signed-in user's
Configuration menu, regardless of role. It remains a browser-local palette,
not a server-side/per-account synchronization feature.

## Production registration and sessions

### Account profile

After sign-in, **User name → Account** opens a TVision profile dialog with first
name, last name, nickname, Email, read-only Username/Role and
Save/Cancel. Login remains the separate Passkey/registration dialog.
`PUT /api/auth/profile` accepts `email` and optional `first_name`,
`last_name`, `nickname`; it checks the configured host, exact Origin and current session,
rejects invalid/duplicate addresses and never accepts account IDs or roles.
Only the session owner's row is changed. A successful save refreshes the menu
and closes the dialog; Cancel/close does not save. Errors retain the entered text.

Each additional name is limited to 100 characters and rejects control characters.
Existing accounts gain blank optional fields; existing display names are not split
or replaced. Omitting a new field (or sending null) preserves it; an empty string
clears it. Neither nickname nor personal names are login identifiers. Registration
uses the same first-name, last-name, nickname and email fields as Add User.
These details are saved with the ceremony and committed only after successful
Passkey verification. Existing administrator-created profiles retain their
prepared details when enrolling a Passkey; users can edit them in Account afterward.
There is no separate editable Display name. The server derives the stored menu/
WebAuthn label from nickname, then first + last name, limited to 100 characters;
when all are blank it retains the existing label (or username for an empty legacy
label). Profile-edit endpoints reject a caller-supplied `display_name`. Account
IDs, usernames and existing Passkey-manager labels do not change.
Account, Users, Add User, Registration and Login attach a shared `TVEmailValidator` to `TVInputLine`.
Incomplete addresses are allowed while typing; Save/Register requires a complete
address using the same syntax as the server. Only administrator Users permits a
blank address for existing CLI/development accounts. Login accepts an email or
an existing 1–64-character letter/digit/dot/underscore/dash username (including
Unicode letters/digits). Email fields reject whitespace and control characters
while editing. This does not verify a mailbox.

The original username and internal account ID remain stable. Login accepts
either that username or the updated email (case-insensitively). Existing
Passkeys, sessions and DOS overlay paths are unchanged. An email edit does not
update labels already saved in the browser's Passkey manager or verify ownership
of the mailbox. Role is not editable in the profile; this is not a browser-based
account/permission administration interface.

### Registration

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

Open **Login → Register**, enter your name, email and this
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

A signed-in administrator sees **User name → Registration Token**. Its
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

## Administrator account management

**User menu → Users** lists all accounts. Select one to edit first name, last name,
nickname, email,
role (Member/Administrator), enabled state and private C capacity (1–256 MiB).
Leave capacity blank to inherit the server default, initially 64 MiB.
The capacity input uses the shared numeric `TVFilterValidator`: typing or
pasting non-digit text is rejected. Save and the server validate 1–256 MiB.
The list and profile show committed overlay usage, excluding shared software,
media and recovery generations. Account IDs, usernames and Passkeys are not
changed by these edits. Disabling revokes active sessions but retains files
and credentials. The founding administrator (the first registered account)
cannot be demoted or disabled, even if other administrators exist. Its identity
is stored permanently in SQLite; migration marks the original first account.
Name, email and capacity remain editable. The last active administrator is
also protected. There is no account deletion endpoint.
All user-management endpoints require an active administrator and writes
require the exact configured origin. Ordinary users can edit only their own
profile names/email; they cannot change role or capacity. Server Configuration also
shows read-only environment/path settings and confirmed rebuild controls, with
one blank character row between the runtime list and the rebuild/Users buttons.

The Users list spans 26 rows. Add User/Save and Refresh/Close form a 2×2 button
matrix in the right-hand column, below the profile fields.
A blank character row separates profile details from Add User/Save. The lower
Refresh/Close row and the list's extent are unchanged.

**Add user...** opens the shared registration-profile form without asking the
administrator for a token or creating a Passkey on their device. Enter first
name or nickname, optional last name, and a valid unique email. **Create** calls
`POST /api/admin/users`; role is fixed to Member, account is enabled, and capacity
inherits the server default. No session cookie is issued or replaced. The user
list refreshes automatically. The dialog displays a formatted one-hour invitation
in an input that can be selected/copied; **Done** closes it and clears the token.

Pass the email and token privately to the new user. They use **Login → Register**
in their own browser. The registration-options endpoint recognizes an existing
account plus its bound invitation, returns `enrollment: true` and its prepared
profile, and uses the existing `/api/auth/passkey/enroll/verify` ceremony. The
account ID, stored names and any DOS data are retained. The token is single-use,
expires after one hour, and cannot enroll another account. Disabled accounts
cannot enroll. Administrators remain signed in throughout account creation.

Creating a user requires the same administrator/session/Host/Origin checks as
editing one; caller-supplied roles, account IDs and quota overrides are rejected.
Invitation hashes are stored in the existing `invitations` table, separately
from unbound registration tokens. The invitation value is shown only at creation;
copy it before closing. Opening/cancelling Add User alone writes nothing. Closing
during an already submitted request does not undo server-side account creation.
