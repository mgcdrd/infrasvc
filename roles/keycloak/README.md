keycloak
========

Deploys Keycloak (Quarkus) with a PostgreSQL backend and acme.sh TLS, one of
two ways:

- **`docker`** (default) — a single Keycloak service via Docker Compose.
  `host` or `bridge` networking. Active/passive with keepalived (`KC_CACHE`
  stays `local`).
- **`native`** — the Keycloak distribution tarball under a hardened systemd
  unit. Infinispan clusters over `cache-stack=jdbc-ping` (database-based
  discovery, no multicast), which is what makes cross-node caching work
  inside an unprivileged LXC container. Binds `:443` directly via
  `CAP_NET_BIND_SERVICE`; adds no firewalld rules.

`tasks/main.yml` is a dispatcher — it asserts the inputs then imports
`install-docker.yml` or `install-native.yml`.

Tested on: Debian 12/13, Rocky Linux 9/10


Requirements
------------

- `become: true` and `gather_facts: true`.
- `docker` mode: nothing extra — the role pulls in `mgcdrd.infrabase.docker`.
  firewalld must be running when `keycloak_network_mode: host`.
- `native` mode: `keycloak_release` set to a full `X.Y.Z`; a PGDG-reachable
  PostgreSQL at `postgres_host`; internet (or mirror) for the distribution
  tarball and Java. Java 21 is installed by the role — from `bookworm-backports`
  on Debian 12, distro packages elsewhere, or Adoptium when
  `keycloak_java_package_method: adoptium`.
- `mgcdrd.infrabase.acme_sh` credentials for `keycloak_acme_challenge` unless
  `keycloak_manage_tls: false`.


Role Variables
--------------

### Dispatch

| Variable | Default | Description |
|---|---|---|
| `keycloak_install_method` | `docker` | `docker` or `native` |
| `keycloak_manage_tls` | `true` | Issue the cert with `acme_sh` from this role. `false` when TLS is placed by other means. |

### Common

| Variable | Default | Description |
|---|---|---|
| `keycloak_hostname` | `""` | External FQDN (VIP) — **required**. Used in the cert, `KC_HOSTNAME` / `hostname`. |
| `keycloak_https_port` | `8443` docker / `443` native | HTTPS bind port. |
| `keycloak_mgmt_port` | `9000` | Management/health port. |
| `postgres_host` | `""` | PostgreSQL FQDN or IP — **required**. |
| `postgres_port` / `postgres_db` | `5432` / `keycloak` | |
| `keycloak_db_user` / `keycloak_db_password` | `{{ vault_keycloak_db_* }}` | DB credentials Keycloak itself authenticates with — no ownership, scoped to `USAGE,CREATE` on `public`. |
| `postgres_admin_user` / `postgres_admin_password` | `postgres` / `{{ vault_postgres_admin_password }}` | Bootstrap account that creates/owns the database. Not used by this role — consumed by the deployment's provisioning phase (`postgres_admin_password` is docker-mode only). |
| `keycloak_admin_user` / `keycloak_admin_password` | `{{ vault_keycloak_admin_* }}` | First-start bootstrap admin. |

### acme shaping (both modes)

| Variable | Default | Description |
|---|---|---|
| `keycloak_acme_challenge` | `dns_cf` | `dns_cf`, `dns_pdns`, `standalone`, … |
| `keycloak_acme_complete_chain` | `false` | `true` roots the deployed chain with a pinned CA (Google Public CA). acme_sh then deploys `ca.pem` and no `fullchain.pem`; the role picks the right filename automatically. |
| `keycloak_acme_root_cn` / `_root_fingerprint` / `_root_urls` | `""` / `""` / `[]` | Pinned root, when `keycloak_acme_complete_chain`. |

CA selection (`acme_sh_ca`), EAB (`acme_sh_eab_*`), and the Cloudflare /
PowerDNS credentials are `acme_sh` role variables — set them at the
deployment/inventory level.

### docker mode

| Variable | Default | Description |
|---|---|---|
| `keycloak_version` | `26.4` | Container image tag. |
| `keycloak_image` | `quay.io/keycloak/keycloak` | |
| `keycloak_network_mode` | `host` | `host` or `bridge`. |
| `keycloak_http_port` / `keycloak_jgroups_port` / `keycloak_jgroups_fd_port` | `8080` / `7800` / `57600` | Bind ports (bridge mode publishes them). |
| `keycloak_base_dir` | `/srv/docker/keycloak` | Compose project directory. |
| `keycloak_shared_storage` | `nfs` | `nfs` or `local` — themes/truststores. |
| `keycloak_nfs_server` / `keycloak_nfs_path` / `keycloak_nfs_mount` / `keycloak_nfs_opts` | | NFS mount (nfs mode). |
| `keycloak_extra_env` | `{}` | Extra `KC_*` env merged into the service. |

### native mode

| Variable | Default | Description |
|---|---|---|
| `keycloak_release` | `""` | **Required** — full `X.Y.Z` GitHub release tag. |
| `keycloak_download_url` | GitHub release URL for `keycloak_release` | Override for a mirror. |
| `keycloak_download_checksum` | `""` | e.g. `sha256:<url-or-hash>`. |
| `keycloak_service_name` / `_user` / `_group` | `keycloak` | |
| `keycloak_install_dir` | `/opt/keycloak` | Symlink to `keycloak_versioned_dir` (`/opt/keycloak-<release>`). |
| `keycloak_systemd_hardening` | `true` | Emit the sandbox block in the unit. |
| `keycloak_java_package_method` | `distro` | `distro` or `adoptium`. |
| `keycloak_java_package` | `java-21-openjdk-headless` (RHEL) / `openjdk-21-jre-headless` (Debian) | Override for a newer JDK. |
| `keycloak_adoptium_package` | `temurin-21-jdk` | |
| `keycloak_http_enabled` | `false` | |
| `keycloak_https_protocols` | `TLSv1.3,TLSv1.2` | |
| `keycloak_hostname_strict` | `true` | |
| `keycloak_metrics_enabled` | `false` | |
| `keycloak_cache` / `keycloak_cache_stack` | `ispn` / `jdbc-ping` | Infinispan clustering. |
| `keycloak_cache_embedded_mtls_enabled` | `true` | mTLS on the JGroups transport. |
| `keycloak_cache_embedded_network_bind_address` | primary IPv4 | JGroups bind address. |
| `keycloak_db_sslmode` | `verify-full` | JDBC `sslmode`. |
| `keycloak_db_sslrootcert` | `{{ keycloak_install_dir }}/conf/truststores/db-ca.pem` | Path checked by `verify-full`. |
| `keycloak_truststore_files` | `[]` | Files dropped into `conf/truststores/`; each entry `name` + `content` or `src`. Use for the DB CA and LDAP CA. |
| `keycloak_extra_conf` | `{}` | Extra `key=value` lines appended to `keycloak.conf`. |


Templates
---------

| File | Mode | Purpose |
|---|---|---|
| `docker-compose.yml.j2` | docker | the Compose service |
| `keycloak.conf.j2` | native | server config; `kc.sh build` bakes the build-time options in |
| `keycloak.service.j2` | native | hardened unit — `ExecStart=kc.sh start --optimized`, `AmbientCapabilities=CAP_NET_BIND_SERVICE` |
| `keycloak.env.j2` | native | `KC_BOOTSTRAP_ADMIN_*` `EnvironmentFile` (first start only) |
| `keycloak/check_keycloak.sh.j2` | both | keepalived VRRP health check against `keycloak_mgmt_port` |


Handlers
--------

| Handler | Mode | Action |
|---|---|---|
| `keycloak compose restart` | docker | `docker_compose_v2 state: restarted` |
| `keycloak native build` | native | `kc.sh build`, then notifies `keycloak native restart` |
| `keycloak native restart` | native | `systemd_service state: restarted` |

In native mode `keycloak.conf` and the version symlink notify `keycloak native
build`; the unit notifies `keycloak native restart`. Handlers are flushed
before the service is started so an optimized build always precedes the start.


Notes
-----

- `keycloak_version` (`26.4`) is a floating container tag. Native needs an
  exact release — `keycloak_release: "26.4.0"` — for the tarball URL.
- Native mode does **not** use NFS shared storage; supply truststores via
  `keycloak_truststore_files`. Themes are the stock set unless you manage them
  yourself.
- Native mode adds no firewalld rules — port exposure is the `harden`
  deployment's job.
- Cert renewal reload: the Docker path restarts the container via compose; the
  native path runs `systemctl try-restart` (Quarkus does not hot-reload TLS).


Companion roles
---------------

- `mgcdrd.infrabase.acme_sh` — issues the TLS certificate.
- `mgcdrd.infrabase.postgresql` — the native PostgreSQL backend (wired in
  `deployments/keycloak` Phase 1, not by this role).
- `mgcdrd.infrasvc.keepalived` — floats the VIP; uses
  `keepalived_preset_keycloak` from this role's defaults.
- `mgcdrd.infrasvc.keycloak_config` — post-deploy realm/LDAP/OIDC config.

See `deployments/keycloak` for the full deployment.


License
-------

GPL-3.0-or-later
