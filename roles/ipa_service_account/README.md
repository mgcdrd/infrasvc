# ipa_service_account

Issues an IPA Kerberos service principal (e.g. `HTTP/mokey.lab.provenzawt.dev`)
and its keytab for a service that is **not** an enrolled IPA client — a
containerized app with no persistent host identity, most commonly — and
stores the keytab in Vault. Generic and reusable: parameterize
`ipa_service_account_fqdn`/`ipa_service_account_principal_type`/
`ipa_service_account_vault_path` per caller.

Unlike `ipa_client`/`foreman_install`'s self-service `kinit -k -t
/etc/krb5.keytab host/...` pattern, there's no host keytab to bootstrap
from here, so this role kinits as a dedicated, least-privilege manager
account instead (bootstrapped on first use, same idea as `ipa_baseline`'s
enrollment account).

## What it does

1. Checks Vault for an existing keytab at `ipa_service_account_vault_path`
   — skips everything if found (idempotent on re-runs; the whole point,
   since re-issuing a keytab invalidates the old one everywhere it's
   deployed).
2. Bootstraps (if missing) a manager account holding the built-in **Host
   Administrators** and **Service Administrators** IPA privileges — add and
   manage hosts/services and their keytabs. Not `admins` group membership.
3. Uses that account (JSON-RPC, no CLI dependency) to ensure an IPA host
   entry (`--force`, since it's never actually enrolled) and the requested
   service principal exist.
4. `kinit`s as the manager account and shells out to `ipa-getkeytab` — this
   step has no RPC equivalent, so the host running this role needs the
   `freeipa-client` package (for `kinit`/`ipa-getkeytab`) and network
   access to the IPA server's Kerberos/LDAP ports, not just its HTTPS API.
5. Writes the keytab (base64) to Vault and removes the local temp copy.

## Important: keytab rotation

`ipa-getkeytab` **generates a new random key every time it's run** — there
is no way to retrieve an existing key's current value. Re-running this role
with `ipa_service_account_force_rotate: true` invalidates the keytab
already deployed to the consuming service; that service must be restarted
against the freshly written Vault secret immediately after.

## Prerequisites

- IPA admin credentials stored in Vault (`vault_ipa_admin_password`) —
  only needed the first time the manager account is bootstrapped.
- A Vault token with read/write access to
  `ipa_service_account_vault_kv_mount` at both
  `ipa_service_account_vault_manager_path` and
  `ipa_service_account_vault_path`.
- `freeipa-client` (or equivalent — provides `kinit`/`ipa-getkeytab`)
  installed wherever this role runs, with network reachability to the IPA
  server's HTTPS, Kerberos, and LDAP ports.

## Usage

Runs entirely via API calls plus one local `kinit`/`ipa-getkeytab` shell-out
— no SSH to the IPA server itself, and no SSH to the service the keytab is
for.

```yaml
- name: Issue mokey's HTTP keytab
  hosts: localhost
  gather_facts: false
  vars:
    ipa_service_account_server: "ipa2.lab.provenzawt.dev"
    ipa_service_account_fqdn: "mokey.lab.provenzawt.dev"
    ipa_service_account_principal_type: "HTTP"
    ipa_service_account_vault_url: "https://vault-web.lab.provenzawt.dev"
    ipa_service_account_vault_path: "mokey/http_keytab"
    vault_ipa_admin_password: "{{ lookup('community.hashi_vault.hashi_vault', 'kv1/data/ipa/admin').password }}"
  roles:
    - mgcdrd.infrasvc.ipa_service_account
```

## Variables

| Variable | Default | Description |
|---|---|---|
| `ipa_service_account_server` | `""` | IPA server FQDN (required) |
| `ipa_service_account_admin_principal` | `admin` | IPA admin username (manager bootstrap only) |
| `ipa_service_account_validate_certs` | `true` | Validate IPA TLS certificate |
| `ipa_service_account_manage_manager` | `true` | Bootstrap the manager account/role if missing |
| `ipa_service_account_manager_principal` | `svc-ipa-keytab-mgr` | Shared manager account username |
| `ipa_service_account_manager_role` | `IPA Keytab Issuer` | IPA role holding the privileges |
| `ipa_service_account_force_rotate_manager` | `false` | Regenerate the manager account's own password |
| `ipa_service_account_fqdn` | `""` | FQDN the service principal is issued for (required) |
| `ipa_service_account_principal_type` | `HTTP` | Kerberos service type |
| `ipa_service_account_force_rotate` | `false` | Reissue the keytab even if Vault already has one |
| `ipa_service_account_vault_url` | `""` | Vault API base URL (required) |
| `ipa_service_account_vault_token` | `$VAULT_TOKEN` | Vault auth token |
| `ipa_service_account_vault_kv_mount` | `kv1` | KV v2 engine mount point |
| `ipa_service_account_vault_manager_path` | `ipa/service-account-manager` | Path for the manager account's own credentials |
| `ipa_service_account_vault_path` | `""` | Path the issued keytab is written to (required, per-caller) |
| `vault_ipa_admin_password` | `""` | IPA admin password (required only for first-time manager bootstrap) |

## Vault paths

| Path | Fields | Written by |
|---|---|---|
| `kv1/ipa/service-account-manager` | `principal`, `password` | This role, once, shared across every caller |
| `kv1/<ipa_service_account_vault_path>` | `fqdn`, `principal`, `keytab_b64` | This role, per caller |
