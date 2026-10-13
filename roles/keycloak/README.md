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

### Variable reference

| Variable | Default | Required | Description |
|---|---|---|---|
| `keycloak_version` | `"26.4"` | No | Container image tag (floating, e.g. `26.4`); docker method only |
| `keycloak_image` | `"quay.io/keycloak/keycloak"` | No | Container image repository; docker method only |
| `keycloak_hostname` | `""` | Yes | External FQDN served by the keepalived VIP; used in the TLS cert and `KC_HOSTNAME` |
| `keycloak_network_mode` | `host` | Yes | `host` (container shares the host network; recommended) or `bridge` (published ports; cross-host clustering then needs `KC_CACHE_STACK=tcp` via `keycloak_extra_env`); docker method only |
| `keycloak_http_port` | `8080` | No | HTTP bind port; use an unprivileged port |
| `keycloak_https_port` | `443` native, `8443` docker | No | HTTPS bind port; firewalld forwards 443 to it |
| `keycloak_mgmt_port` | `9000` | No | Health and metrics endpoint port |
| `keycloak_jgroups_port` | `7800` | No | Infinispan JGroups cluster traffic port |
| `keycloak_jgroups_fd_port` | `57600` | No | JGroups failure-detection (FD_SOCK) port |
| `keycloak_base_dir` | `/srv/docker/keycloak` | No | Base directory on the host for the compose file; docker method only |
| `keycloak_shared_storage` | `nfs` | Yes | Where themes and truststores live: `nfs` (shared between HA nodes, needs the NFS vars) or `local` (under `keycloak_base_dir/data` on each node) |
| `keycloak_nfs_server` | `""` | If `keycloak_shared_storage: nfs` | NFS server address |
| `keycloak_nfs_path` | `""` | If `keycloak_shared_storage: nfs` | NFS export path |
| `keycloak_nfs_mount` | `/mnt/keycloak` | No | Local mount point for the NFS share |
| `keycloak_nfs_opts` | `"vers=3,_netdev"` | No | NFS mount options |
| `keycloak_data_subdirs` | *(list, 2 items)* | No | Subdirectories created under the data root |
| `acme_sh_cert_base_dir` | `/etc/ssl/acme` | No | Where `acme_sh` deploys certs; must match the `acme_sh` role's value |
| `keycloak_cert_dir` | `{{ acme_sh_cert_base_dir }}/{{ keycloak_hostname }}` | No | Directory holding this host's certificate |
| `postgres_version` | `"18"` | No | PostgreSQL image tag; docker method only |
| `postgres_image` | `"postgres"` | No | PostgreSQL image repository; docker method only |
| `postgres_db` | `keycloak` | No | Database name |
| `postgres_host` | `""` | Yes | FQDN or IP of the PostgreSQL host |
| `postgres_port` | `5432` | No | PostgreSQL port |
| `keycloak_db_user` | `{{ vault_keycloak_db_user }}` | No | Database user Keycloak connects as; inject from Vault |
| `keycloak_db_password` | `{{ vault_keycloak_db_password }}` | No | Password for `keycloak_db_user`; inject from Vault |
| `postgres_admin_user` | `postgres` | No | Admin account used to create the database and grant scoped access to `keycloak_db_user` |
| `postgres_admin_password` | `{{ vault_postgres_admin_password }}` | No | Password for the admin account; inject from Vault |
| `keycloak_admin_user` | `{{ vault_keycloak_admin_user }}` | No | Bootstrap admin username; only active on first start |
| `keycloak_admin_password` | `{{ vault_keycloak_admin_password }}` | No | Bootstrap admin password; only active on first start |
| `keycloak_extra_env` | `{}` | No | Additional `KC_*` environment variables merged into the compose service; docker method only |
| `keycloak_install_method` | `docker` | No | `docker` (Compose stack) or `native` (Quarkus tarball with a hardened systemd unit, e.g. for LXC) |
| `keycloak_manage_tls` | `true` | No | Issue the TLS certificate with `mgcdrd.infrabase.acme_sh`; set false when TLS terminates upstream |
| `keycloak_release` | `""` | If `keycloak_install_method: native` | Full `X.Y.Z` release (the GitHub tag); `keycloak_version` is a floating tag and will not resolve a tarball |
| `keycloak_download_url` | *(GitHub release URL for `keycloak_release`)* | No | Tarball URL for native installs; override for a mirror |
| `keycloak_download_checksum` | `""` | No | Checksum for the tarball, e.g. `sha256:https://…/keycloak-26.4.0.tar.gz.sha256` |
| `keycloak_service_name` | `keycloak` | No | systemd unit name (native) |
| `keycloak_service_user` | `keycloak` | No | Service user (native) |
| `keycloak_service_group` | `keycloak` | No | Service group (native) |
| `keycloak_install_dir` | `/opt/keycloak` | No | Install path, a symlink to the versioned directory (native) |
| `keycloak_versioned_dir` | `"/opt/keycloak-{{ keycloak_release }}"` | No | Versioned install directory (native) |
| `keycloak_systemd_hardening` | `true` | No | Emit the sandboxing block in the unit (native) |
| `keycloak_java_package_method` | `distro` | No | `distro` (OS OpenJDK 21 package) or `adoptium` (Eclipse Temurin); native only |
| `keycloak_java_package` | *(OS-specific OpenJDK 21 package)* | No | Distro JDK package; override for a newer JDK |
| `keycloak_adoptium_package` | `temurin-21-jdk` | No | Package installed when `keycloak_java_package_method: adoptium` |
| `keycloak_http_enabled` | `false` | No | Enable the plain HTTP listener in `keycloak.conf` (native) |
| `keycloak_https_protocols` | `"TLSv1.3,TLSv1.2"` | No | Allowed TLS protocols (native) |
| `keycloak_hostname_strict` | `true` | No | Enforce the configured hostname (native) |
| `keycloak_metrics_enabled` | `false` | No | Enable the metrics endpoint (native) |
| `keycloak_cache` | `ispn` | No | Infinispan cache mode (native); `jdbc-ping` discovery avoids multicast, which is what makes cross-node caching work in LXC |
| `keycloak_cache_stack` | `jdbc-ping` | No | Cache discovery stack (native) |
| `keycloak_cache_embedded_mtls_enabled` | `true` | No | mTLS on the JGroups transport (native) |
| `keycloak_cache_embedded_network_bind_address` | *(default IPv4 address, else `127.0.0.1`)* | No | JGroups bind address (native) |
| `keycloak_db_sslmode` | `verify-full` | No | Keycloak to PostgreSQL TLS mode in the JDBC URL (native) |
| `keycloak_db_sslrootcert` | `{{ keycloak_install_dir }}/conf/truststores/db-ca.pem` | No | CA file checked by `verify-full` (native) |
| `keycloak_truststore_files` | `[]` | No | Files placed in `{{ keycloak_install_dir }}/conf/truststores/` |
| `keycloak_extra_conf` | `{}` | No | Extra `key=value` lines appended to `keycloak.conf` (native) |
| `keycloak_acme_challenge` | `dns_cf` | No | `acme_sh` challenge type: `dns_cf`, `dns_pdns`, `standalone`, `webroot`, and so on |
| `keycloak_acme_complete_chain` | `false` | No | Root the deployed chain with a pinned root (needed for Google Public CA) |
| `keycloak_acme_root_cn` | `""` | No | Root CA common name for `complete_chain`; empty uses the `acme_sh` default |
| `keycloak_acme_root_fingerprint` | `""` | No | Root CA fingerprint for `complete_chain`; empty uses the `acme_sh` default |
| `keycloak_acme_root_urls` | `[]` | No | Root CA PEM URLs for `complete_chain`; empty uses the `acme_sh` default |
| `keepalived_preset_keycloak` | *(map, 11 lines)* | No | Keycloak keepalived preset, registered so the `keepalived` role finds it when `keepalived_vip_for` includes `keycloak` |


### acme shaping (both modes)

CA selection (`acme_sh_ca`), EAB (`acme_sh_eab_*`), and the Cloudflare /
PowerDNS credentials are `acme_sh` role variables — set them at the
deployment/inventory level.

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
