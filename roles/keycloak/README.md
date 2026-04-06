keycloak
========

Deploys Keycloak via Docker Compose with TLS (via acme.sh), PostgreSQL
backend, and configurable host or bridge network mode. Designed for
dedicated infrastructure VMs running an active/passive HA pair with
keepalived.

Tested on: Debian 12/13, Rocky Linux 9/10


Requirements
------------

- `become: true` and `gather_facts: true` are required.
- Docker must be installed before this role runs (use `mgcdrd.infrabase.docker`).
- `mgcdrd.infrabase.acme_sh` must have run first to issue the TLS certificate.
- firewalld must be installed and running when `keycloak_network_mode: host`
  (required for port-forwarding rules).


Role Variables
--------------

### Core

| Variable | Default | Description |
|---|---|---|
| `keycloak_version` | `26.4` | Keycloak container image tag |
| `keycloak_hostname` | `""` | External FQDN — used in `KC_HOSTNAME` and cert path |
| `keycloak_base_dir` | `/srv/docker/keycloak` | Base directory for compose file and data |

### Network mode

| Variable | Default | Description |
|---|---|---|
| `keycloak_network_mode` | `host` | `host` or `bridge` — see **Network mode** below |
| `keycloak_http_port` | `8080` | HTTP bind port |
| `keycloak_https_port` | `8443` | HTTPS bind port |
| `keycloak_mgmt_port` | `9000` | Management/health port |
| `keycloak_jgroups_port` | `7800` | Infinispan JGroups port (bridge mode) |
| `keycloak_jgroups_fd_port` | `57600` | Infinispan failure-detection port (bridge mode) |

### TLS

| Variable | Default | Description |
|---|---|---|
| `keycloak_cert_dir` | `{{ acme_sh_cert_base_dir }}/{{ keycloak_hostname }}` | Directory containing `fullchain.pem` and `key.pem` |
| `acme_sh_cert_base_dir` | `/etc/ssl/acme` | Base path where acme.sh deploys certs |

### Database

| Variable | Default | Description |
|---|---|---|
| `postgres_host` | `""` | PostgreSQL FQDN or IP — **required** |
| `postgres_db` | `keycloak` | Database name |
| `keycloak_db_user` | `{{ vault_keycloak_db_user }}` | Database username (inject via Vault) |
| `keycloak_db_password` | `{{ vault_keycloak_db_password }}` | Database password (inject via Vault) |

### Admin bootstrap

| Variable | Default | Description |
|---|---|---|
| `keycloak_admin_user` | `{{ vault_keycloak_admin_user }}` | Initial admin username |
| `keycloak_admin_password` | `{{ vault_keycloak_admin_password }}` | Initial admin password |

### Shared storage (themes, truststores)

| Variable | Default | Description |
|---|---|---|
| `keycloak_shared_storage` | `nfs` | `nfs` or `local` |
| `keycloak_nfs_server` | `""` | NFS server IP/hostname (`nfs` mode) |
| `keycloak_nfs_path` | `""` | NFS export path (`nfs` mode) |
| `keycloak_nfs_mount` | `/mnt/keycloak` | Mount point on the host |

### Extra environment

| Variable | Default | Description |
|---|---|---|
| `keycloak_extra_env` | `{}` | Additional `KC_*` environment variables passed to the container |


Network mode
------------

### `host` (default — recommended for dedicated VMs)

The container shares the host network namespace. Keycloak binds on
`keycloak_http_port` (8080) and `keycloak_https_port` (8443) directly on the
host IP. Because uid 1000 cannot bind privileged ports, the role adds
firewalld port-forwarding rules:

- `80` → `keycloak_http_port`
- `443` → `keycloak_https_port`

`KC_HOSTNAME_PORT` is set to `443` so Keycloak generates correct redirect URLs.

`KC_CACHE: local` is set — cross-node Infinispan clustering is not used. The
active/passive model relies on keepalived moving the VIP when the active node
fails.

### `bridge`

The container gets an isolated Docker bridge network. All ports
(`http`, `https`, `mgmt`, `jgroups`, `jgroups_fd`) are published. No
firewalld forwarding rules are added. Use when container isolation is required
or the nodes are not dedicated.


Secrets
-------

All secrets reference Vault variables and must be injected via AWX credential
or `ansible-vault` at runtime:

| Variable | Purpose |
|---|---|
| `vault_keycloak_db_user` | PostgreSQL username |
| `vault_keycloak_db_password` | PostgreSQL password |
| `vault_keycloak_admin_user` | Keycloak bootstrap admin username |
| `vault_keycloak_admin_password` | Keycloak bootstrap admin password |
| `vault_acme_cf_token` | Cloudflare API token for DNS01 cert issuance |


Example Playbook
----------------

```yaml
- name: keycloak - Deploy Keycloak
  hosts: keycloak
  become: true
  gather_facts: true
  tags: [keycloak]
  roles:
    - mgcdrd.infrabase.docker
    - mgcdrd.infrabase.acme_sh
    - mgcdrd.infrasvc.keycloak
  vars:
    keycloak_hostname: "infra-kc.example.com"
    keycloak_network_mode: host
    postgres_host: "db1.example.com"
    acme_sh_email: "admin@example.com"
    acme_sh_cf_token: "{{ vault_acme_cf_token }}"
    acme_sh_certs:
      - domains:
          - "infra-kc.example.com"
        challenge: dns_cf
        reload_cmd: >-
          chown -R 1000:1000 /etc/ssl/acme/infra-kc.example.com &&
          test -f /srv/docker/keycloak/docker-compose.yml &&
          docker compose -f /srv/docker/keycloak/docker-compose.yml restart keycloak || true
        state: present
```


Companion Roles
---------------

- `mgcdrd.infrabase.acme_sh` — issues the TLS certificate. Must run before
  this role so `keycloak_cert_dir` contains valid cert files.
- `mgcdrd.infrasvc.keepalived` — floats the VIP across active/passive nodes.
  Configure the health check script against `keycloak_mgmt_port` (9000).
- `mgcdrd.infrasvc.keycloak_config` — configures Keycloak post-deploy via
  REST API (LDAP federation, realms, k8s OIDC client).

See `deployments/keycloak` for the full deployment that wires all roles together.


License
-------

GPL-3.0-or-later
