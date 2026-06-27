# ipa_baseline

One-time bootstrap role that creates the least-privilege IPA service account
used by `ipa_client` for host pre-registration, and stores its credentials in
HashiCorp Vault.

Run this once after IPA is stood up. Re-run with `ipa_baseline_force_rotate: true`
after a Vault DR restore to regenerate and re-sync the enrollment secret.

## What it does

1. Checks Vault for existing enrollment credentials — skips IPA operations if
   found (fully idempotent on re-runs).
2. Creates the `Ansible Host Enrollment` role in IPA (if missing) and assigns
   the built-in `Host Enrollment` privilege to it. This grants exactly two
   IPA permissions: `System: Add Hosts` and `System: Manage Host Enrollment
   Password`. Nothing else.
3. Creates the `svc-ansible-enrollment` user (if missing) with a generated
   32-character password. Sets `krbPasswordExpiration` to a far-future date
   so the account is not subject to the forced-change-on-first-login that IPA
   applies to admin-set passwords.
4. Adds the user to the role.
5. Writes `principal` and `password` to Vault at
   `kv1/data/ipa/enrollment`.

## Prerequisites

- IPA admin credentials stored in Vault at `kv1/ipa/admin` with fields
  `principal` and `password`.
- A Vault token with read access to `kv1/ipa/admin` and write access to
  `kv1/ipa/enrollment`. Pass via `VAULT_TOKEN` environment variable or
  `ipa_baseline_vault_token`.
- Network access to the IPA HTTPS API and Vault API from the host running
  the play.

## Usage

This role makes only API calls — it does not require SSH access to the IPA
server. Run it against `localhost` or any host with network access to both
IPA and Vault.

```yaml
- name: Bootstrap IPA enrollment service account
  hosts: localhost
  gather_facts: false
  vars:
    ipa_baseline_server: "ipa01.lab.example.com"
    ipa_baseline_vault_url: "https://vault.example.com"
    vault_ipa_admin_password: "{{ lookup('community.hashi_vault.hashi_vault', 'kv1/data/ipa/admin').password }}"
  roles:
    - mgcdrd.infrasvc.ipa_baseline
```

## Variables

| Variable | Default | Description |
|---|---|---|
| `ipa_baseline_server` | `""` | Primary IPA server FQDN (required) |
| `ipa_baseline_admin_principal` | `admin` | IPA admin username |
| `ipa_baseline_validate_certs` | `true` | Validate IPA TLS certificate |
| `ipa_baseline_enrollment_principal` | `svc-ansible-enrollment` | Service account username |
| `ipa_baseline_enrollment_role` | `Ansible Host Enrollment` | IPA role to create |
| `ipa_baseline_force_rotate` | `false` | Regenerate password and overwrite Vault entry |
| `ipa_baseline_vault_url` | `""` | Vault API base URL (required) |
| `ipa_baseline_vault_token` | `$VAULT_TOKEN` | Vault auth token |
| `ipa_baseline_vault_kv_mount` | `kv1` | KV v2 engine mount point |
| `ipa_baseline_vault_enrollment_path` | `ipa/enrollment` | Path within KV mount |
| `vault_ipa_admin_password` | `""` | IPA admin password (required, inject from Vault) |

## Vault paths

| Path | Fields | Written by |
|---|---|---|
| `kv1/ipa/admin` | `principal`, `password` | Created manually before first run |
| `kv1/ipa/enrollment` | `principal`, `password` | Written by this role |

## DR / rotation

After restoring Vault data from backup, the enrollment secret at
`kv1/ipa/enrollment` already exists and this role will no-op. If Vault data
was lost and the IPA user still exists, run with `ipa_baseline_force_rotate: true`
to generate a new password, update the IPA account, and write the new secret
to Vault.
