# Private read-only deployment

This profile runs Krow on the authoritative VPS, not on the Mac. The Mac's
launch agent runs only an SSH forward. Provisioning requires the owner's approval;
these files do not deploy themselves. No store publication or browser policy is needed.

```text
Browser → Mac 127.0.0.1:8770 → verified SSH to davgent → VPS 127.0.0.1:8770
```

## Enforced boundaries

- `KROW_READ_ONLY=1` rejects every POST before parsing its body, requesting
  OAuth, or calling a fixer. GET external checks and `write=true` exports are also
  denied. Ordinary authenticated inspection and GET scans remain implemented.
- `serviceMode: read-only` reports that server-wide restriction separately from
  the connection diagnostic's `readOnly: true`. The latter alone is not a write gate.
- The base systemd profile uses a dynamic service identity, read-only code/filesystem,
  private state, loopback-only IP traffic, and a systemd credential file. It removes
  Workiva credentials from the process environment. This commissioning profile
  cannot access Workiva, even if the browser requests an inspection.
- The SSH forward binds explicitly to `127.0.0.1`, checks the known server key,
  disables agent forwarding, and fails if the local port is occupied. Launchd
  reconnects after tunnel exit. It does not run Python, agents, or Workiva jobs.

## Provisioned paths

| Host | Path / unit | Purpose |
| --- | --- | --- |
| VPS | `/opt/krow/releases/<git-commit>/` | Root-owned snapshot of reviewed tracked source; no `.env` or extension token |
| VPS | `/opt/krow/current` | Symlink to the adopted release |
| VPS | `/etc/krow/token` | Paired service token, root-owned mode 0600; never print or commit |
| VPS | `krow-readonly.service` | Installed from the adjacent unit file |
| VPS | `/var/lib/krow` | Private service state |
| Mac | `~/Library/LaunchAgents/com.krow.vps-tunnel.plist` | SSH transport only |
| Mac | `~/Library/Application Support/Krow/extension/` | Private paired extension folder; browser installation is separate |

Before creating these paths, check for an existing owner, service and listener.
Do not overwrite an older installation or revive a retired Mac service. Use a
commit-addressed `git archive`, compare extracted files with that commit, and
change the `current` symlink only after tests and review.

Generate a new pair inside a private directory with `scripts/configure_local.py`:
use `--env`, `--extension-config` and `--service-token-file` to choose explicit new
paths. The raw token file becomes the systemd credential; the JavaScript config
belongs only in the private extension folder. The command preserves an existing
pair, so it is not a token rotation tool. Transfer private files through verified
SSH, never a public artifact URL, repository, command argument or screenshot.

## Verify and recover

After authorized installation, check `systemctl is-active krow-readonly` and
`ss -ltn '( sport = :8770 )'` on the VPS. On the Mac check
`launchctl print gui/$(id -u)/com.krow.vps-tunnel` and the loopback listener.
An unauthenticated `/api/connection` must return 403. A paired request must report
`authorization: accepted`, `serviceMode: read-only`, `workivaCredentials: missing`
and `workivaAccess: not_tested`. An authenticated POST with an empty or malformed
body must return `code: read_only` without touching Workiva. Use a program that
reads the private config internally; do not put the token in curl arguments.

The included checker runs those exact probes and prints only redacted outcomes:

```bash
# VPS
sudo python3 /opt/krow/current/deploy/check_connection.py --token-file /etc/krow/token
# Mac, after private staging (not browser installation)
python3 "$HOME/Library/Application Support/Krow/check_connection.py" \
  --extension-config "$HOME/Library/Application Support/Krow/extension/local-config.js"
```

Restart the two new units independently and repeat the checks to verify recovery.
Do not restart unrelated services or change host keys. The owner-approved Mac
Chrome installation also passed worker-context connection/refusal probes before
and after extension reload; see the [private installation guide](../extension/PACKAGING.md).
Workiva credentials, network egress and a named sandbox inspection remain separate
approval and verification steps. The owner approved that scoped update on September
16; the old RCTC report-to-source read passed through the installed Mac broker.
This does not establish the in-page Workiva journey or general compatibility.

To reverse commissioning, stop and disable `krow-readonly.service` and boot out
`com.krow.vps-tunnel` on the Mac; disable that launchd label to prevent reload at
login. Preserve the release and private token unless deletion is explicitly wanted.
For an update rollback, stop the service, repoint `current` to the prior verified
release, restart, and repeat the connection/write-refusal checks. Do not regenerate
the pair or switch to a Mac backend as part of rollback.

## Owner-approved sandbox read access

The base unit remains connection-only. A credentialed test uses a separate private
systemd drop-in, never a broader default unit or credentials in source control.
Provision this only after approval of the workspace, file scope and private update.

- Supply `/etc/krow/workiva.json` through `LoadCredential=workiva:/etc/krow/workiva.json`
  and `Environment=WORKIVA_CREDENTIALS_FILE=%d/workiva`. Its two string keys are
  `WORKIVA_CLIENT_ID` and `WORKIVA_CLIENT_SECRET`. Use the canonical workspace
  connector to resolve the pair internally; never print it or pass it in argv.
  Keep the source root-owned, mode 0600. A configured but unreadable/invalid file
  fails closed; it cannot fall back to another workspace's environment or `.env`.
- Set `WORKIVA_EXPECTED_ARID` to the verified decoded account identity
  (`Account/<id>`). The service checks every newly minted token before caching it
  and rechecks cached tokens before use. This checks an OAuth response received over verified TLS;
  it is not standalone verification of an arbitrary caller-supplied JWT.
- Supply a root-owned read-scope JSON through `LoadCredential=read-scope:...` and
  `Environment=WORKIVA_READ_SCOPE_FILE=%d/read-scope`. Keys are `documents`,
  `spreadsheets`, `tables`, `destinationLinks`, `sourceLinks`, and `anchors`; values
  are arrays of exact resource IDs. Omitted kinds deny all. Derive table IDs from
  the selected old files' metadata, not from a workspace-wide table inventory.
  External linked sources are denied unless separately within the approved scope.
  Missing, malformed, empty, or unknown-key scope files never mean unrestricted.
  Credential-file mode and read-only mode require this scope and an account pin
  before OAuth or any upstream GET, even if either variable name is omitted or
  misspelled. Only standard local mode without a credential/scope file retains
  unrestricted reads.
- Keep `IPAddressDeny=any` and localhost access. Add only the verified TLS API
  hostname's resolved IP addresses to `IPAddressAllow` in that private drop-in;
  use the existing loopback DNS resolver. Do not add a wildcard network grant.
  DNS rotation can require an authorized same-host allowlist refresh; failed
  connectivity must not silently widen egress. The HTTP client also refuses
  foreign-origin read URLs and all redirects, including same-host redirects.
  In the September 16 installation, rapidly changing IPv6 answers caused denied
  connection attempts to time out. The private drop-in now resets
  `RestrictAddressFamilies` to `AF_UNIX AF_INET` and allows only four freshly
  verified API IPv4 addresses plus the base localhost allowance. The same report
  read then completed in seconds. No wildcard network grant was added.
- Preserve `KROW_READ_ONLY=1`, the existing pair, base unit and previous release.
  Set `KROW_EXT_ID` to the existing private installation's ID. After adopting
  the reviewed release/drop-in, run the connection checker with
  `--expect-credentials present`; it also requires `workivaReadScope: valid` and
  `workivaAccountPin: present`. Then test the named old file through the
  installed extension. Credential presence is still not proof of Workiva access.

Rollback must restore **both code and isolation**: stop this service, move the
sandbox drop-in out of the unit directory, restore the previous `current` target,
daemon-reload and restart. Run the previous connection-only checker (credentials
missing and write refusals intact). Preserve the inactive root-only credential
files and prior extension package; do not rotate the pair. Restore the old Chrome
package and reload it if the UI update fails. Never run the old service with the
new credential/egress drop-in, since it lacks these read-scope guards.

## Rename cutover, October 8, 2026

The owner approved renaming Wingman to Krow and switching the live service. Release
`52f925dbf5ab5cfe05e4af756060abe23a5c1f4d` was extracted with `git archive` to
`/opt/krow/releases/`, all 165 files compared against the commit, and `/opt/krow/current` points to it.
The existing pair and sandbox credentials were copied unchanged from `/etc/wingman` to `/etc/krow`
(root, 0600); the sandbox drop-in was carried over with only paths and the extension-ID variable renamed.
`wingman-readonly.service` is stopped and disabled; `krow-readonly.service` serves 127.0.0.1:8770.
The checker returned the same redacted outcome before and after, and again after restarting each side:
connection accepted, read-only, credentials present, read scope valid, account pin present, repairs and
unauthorized requests rejected, Workiva access not tested.

On the Mac, the launch agent is now `com.krow.vps-tunnel` with identical SSH arguments; the old agent file
is kept as a backup outside `LaunchAgents`. The installed extension stays in its September folder,
`~/Library/Application Support/Wingman/extension/`, because an unpacked extension's ID comes from its
path; its files were replaced with the release package, hash-verified, and the pairing file's global was
renamed to `KROW_LOCAL_CONFIG` without regenerating the pair. The previous package is preserved as
`extension-before-krow-52f925d`. Chrome must reload the extension once (its old in-memory build uses the
previous token header and cannot reload itself), then refresh open Workiva tabs.

Rollback: stop and disable `krow-readonly`, enable and start `wingman-readonly` (its release, unit,
drop-in and `/etc/wingman` files are untouched), restore the Mac folder from `extension-before-krow-52f925d`
and the `com.wingman.vps-tunnel` launch agent from its backup, then reload the extension.
