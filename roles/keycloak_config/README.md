# keycloak_config

Configures Keycloak post-deployment via the REST API. Requires Keycloak to be
running and healthy before this role is invoked.

## What it does

### Master realm
- Configures LDAP user federation (read-only, group sync included)
- Assigns the Keycloak `admin` realm role to specified LDAP groups

### Lab realm
- Creates the realm with configurable session and token lifetimes
- Configures LDAP user federation (same server, independent provider)
- Creates the `kubernetes` OIDC client with:
  - Groups claim protocol mapper (adds `groups` to the ID and access token)
  - `preferred_username` claim mapper
  - `cluster-admin` client role
- Assigns the `cluster-admin` client role to specified LDAP groups

## Prerequisites

- `mgcdrd.infrasvc.keycloak` role has run and Keycloak is healthy
- `community.general` >= 7.0.0 (keycloak_user_federation, keycloak_realm)
- Network access from the target host to the Keycloak API

## Usage

This role is invoked as Phase 4 in `deployments/keycloak/site.yml` with
`run_once: true`. It runs on the first keycloak host and makes API calls
to `localhost` (the `keycloak_config_auth_url` default).

```yaml
ansible-playbook site.yml --tags kc_config
```

## Key variables

| Variable | Default | Description |
|---|---|---|
| `keycloak_config_auth_url` | `https://localhost:8443` | Keycloak API URL |
| `keycloak_ldap_url` | `""` | LDAP server URL |
| `keycloak_ldap_bind_dn` | `""` | LDAP bind DN |
| `keycloak_ldap_bind_credential` | `vault_keycloak_ldap_bind_credential` | LDAP bind password |
| `keycloak_ldap_users_dn` | `""` | User search base |
| `keycloak_ldap_groups_dn` | `""` | Group search base |
| `keycloak_ldap_vendor` | `ad` | `ad` or `other` |
| `keycloak_ldap_username_ldap_attribute` | `sAMAccountName` | Username attribute |
| `keycloak_master_admin_groups` | `[]` | LDAP groups → Keycloak admin |
| `keycloak_lab_realm_name` | `lab` | Lab realm name |
| `keycloak_lab_admin_groups` | `[]` | LDAP groups → k8s cluster-admin |
| `keycloak_k8s_client_id` | `kubernetes` | OIDC client ID |

## Secrets

All credentials reference Vault variables:

| Vault variable | Purpose |
|---|---|
| `vault_keycloak_admin_user` | Keycloak admin username |
| `vault_keycloak_admin_password` | Keycloak admin password |
| `vault_keycloak_ldap_bind_credential` | LDAP bind password |

## Extensibility — running subsets later

Each configuration area is gated by a boolean variable and a tag. You can
re-run individual sections after initial deployment without touching the rest.

| Gate variable | Default | Tag | What it controls |
|---|---|---|---|
| `keycloak_configure_master` | `true` | `kc_master` | Master realm LDAP federation + admin group bindings |
| `keycloak_configure_lab` | `true` | `kc_lab` | Lab realm creation, LDAP, k8s client, group bindings |

Run only master realm tasks:
```bash
ansible-playbook site.yml --tags kc_config,kc_master
```

Run only lab realm tasks:
```bash
ansible-playbook site.yml --tags kc_config,kc_lab
```

Skip config entirely (deploy or update Keycloak without touching realm config):
```bash
ansible-playbook site.yml --tags keycloak   # skips kc_config phase
```

To add new realms or clients in the future, extend `tasks/main.yml` with a
new `include_tasks` entry gated by its own variable and tag — existing config
tasks are idempotent and will not conflict.


## k8s API server flags

After running this role, configure the k8s API server with:

```
--oidc-issuer-url=https://<keycloak_hostname>/realms/<keycloak_lab_realm_name>
--oidc-client-id=kubernetes
--oidc-username-claim=preferred_username
--oidc-groups-claim=groups
```
