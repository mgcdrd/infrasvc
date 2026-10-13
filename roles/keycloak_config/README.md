# keycloak_config

Configures Keycloak post-deployment via the REST API. Requires Keycloak to be
running and healthy before this role is invoked.

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

Role Variables
--------------

### Variable reference

| Variable | Default | Required | Description |
|---|---|---|---|
| `keycloak_config_auth_url` | `https://localhost:<keycloak_https_port>` | No | URL the modules use to reach the Keycloak admin API; local by default so tasks on a Keycloak host skip the VIP |
| `keycloak_config_validate_certs` | `false` | No | Validate the Keycloak API TLS certificate |
| `keycloak_config_admin_user` | `{{ vault_keycloak_admin_user }}` | No | Admin user; inject from Vault |
| `keycloak_config_admin_password` | `{{ vault_keycloak_admin_password }}` | No | Admin password; inject from Vault |
| `keycloak_ldap_url` | `""` | Yes | LDAP server URL, `ldap://` or `ldaps://` |
| `keycloak_ldap_bind_dn` | `""` | Yes | DN of the bind account |
| `keycloak_ldap_bind_credential` | `{{ vault_keycloak_ldap_bind_credential }}` | Yes | Bind account password; inject from Vault |
| `keycloak_ldap_users_dn` | `""` | Yes | Base DN users are searched under |
| `keycloak_ldap_vendor` | `"ad"` | No | `ad`, or `other` for OpenLDAP/FreeIPA |
| `keycloak_ldap_edit_mode` | `"READ_ONLY"` | No | `READ_ONLY`, `WRITABLE`, or `UNSYNCED` |
| `keycloak_ldap_username_ldap_attribute` | `"sAMAccountName"` | No | LDAP attribute mapped to the username (`uid` for OpenLDAP/FreeIPA) |
| `keycloak_ldap_rdn_ldap_attribute` | `"cn"` | No | RDN attribute of user entries |
| `keycloak_ldap_uuid_ldap_attribute` | `"objectGUID"` | No | Unique ID attribute (`entryUUID` for OpenLDAP) |
| `keycloak_ldap_user_object_classes` | `"person, organizationalPerson, user"` | No | Object classes identifying user entries |
| `keycloak_ldap_search_scope` | `"2"` | No | `1` one level, `2` subtree |
| `keycloak_ldap_connection_timeout` | `5000` | No | Connection timeout in ms |
| `keycloak_ldap_read_timeout` | `10000` | No | Read timeout in ms |
| `keycloak_ldap_pagination` | `true` | No | Use paged LDAP results |
| `keycloak_ldap_connection_pooling` | `true` | No | Pool LDAP connections |
| `keycloak_ldap_start_tls` | `false` | No | Use StartTLS on the connection |
| `keycloak_ldap_use_truststore_spi` | `"ldapsOnly"` | No | When the Keycloak truststore is used for LDAP TLS: `ldapsOnly`, `always`, or `never` |
| `keycloak_ldap_sync_registrations` | `false` | No | Write users registered in Keycloak back to LDAP |
| `keycloak_ldap_full_sync_period` | `-1` | No | Seconds between full syncs; `-1` disables |
| `keycloak_ldap_changed_sync_period` | `-1` | No | Seconds between changed-user syncs; `-1` disables |
| `keycloak_ldap_groups_dn` | `""` | Yes | Base DN groups are searched under |
| `keycloak_ldap_group_object_classes` | `"group"` | No | Object classes identifying group entries (`groupOfNames` for OpenLDAP) |
| `keycloak_ldap_group_membership_attribute` | `"member"` | No | Group attribute listing its members |
| `keycloak_ldap_group_membership_attribute_type` | `"DN"` | No | `DN` or `UID` |
| `keycloak_ldap_groups_ldap_filter` | `""` | No | Optional LDAP filter limiting which groups are imported |
| `keycloak_ldap_groups_path` | `"/"` | No | Keycloak group path imported groups are created under |
| `keycloak_ldap_drop_non_existing_groups` | `false` | No | Drop Keycloak groups that no longer exist in LDAP |
| `keycloak_ldap_preserve_group_inheritance` | `true` | No | Keep LDAP group nesting as Keycloak subgroups |
| `keycloak_configure_master` | `true` | No | Configure the master realm; false skips the section |
| `keycloak_configure_lab` | `true` | No | Configure the lab realm (LDAP, k8s client, group bindings); false skips the section |
| `keycloak_master_admin_groups` | `[]` | No | LDAP groups granted the `admin` realm role on the master realm |
| `keycloak_lab_realm_name` | `"lab"` | No | Lab realm name |
| `keycloak_lab_realm_display` | `"Lab"` | No | Lab realm display name |
| `keycloak_lab_ssl_required` | `"external"` | No | Realm `sslRequired`: `none`, `external`, or `all` |
| `keycloak_lab_session_idle` | `1800` | No | SSO session idle timeout in seconds |
| `keycloak_lab_session_max` | `36000` | No | SSO session maximum lifespan in seconds |
| `keycloak_lab_token_lifespan` | `300` | No | Access token lifespan in seconds |
| `keycloak_lab_admin_groups` | `[]` | No | LDAP groups granted the Kubernetes cluster-admin role in the lab realm |
| `keycloak_lab_extra_groups` | `[]` | No | Additional LDAP groups to ensure exist in the lab realm |
| `keycloak_k8s_client_id` | `"kubernetes"` | No | OIDC client ID for Kubernetes |
| `keycloak_k8s_client_name` | `"Kubernetes"` | No | Display name of the Kubernetes client |
| `keycloak_k8s_public_client` | `true` | No | Public client with no secret (recommended for kubectl) |
| `keycloak_k8s_redirect_uris` | *(list, 1 items)* | No | Allowed redirect URIs for the Kubernetes client |
| `keycloak_k8s_web_origins` | *(list, 1 items)* | No | Allowed web origins for the Kubernetes client |

## Usage

This role is invoked as Phase 4 in `deployments/keycloak/site.yml` with
`run_once: true`. It runs on the first keycloak host and makes API calls
to `localhost` (the `keycloak_config_auth_url` default).

```yaml
ansible-playbook site.yml --tags kc_config
```

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
