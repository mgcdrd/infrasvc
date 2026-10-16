postgresql
==========

Installs a native PostgreSQL server from the PGDG repository and manages its
listener, TLS, and host-based auth through a `conf.d` drop-in and a fully
templated `pg_hba.conf`. Optionally bootstraps roles and databases.

Built for dedicated database hosts — including Proxmox LXC containers, where
running the official Postgres container under an unprivileged LXC is awkward.
For the containerised alternative see the inline Docker Compose path in
`deployments/keycloak`.

Tested on: Debian 12/13, Rocky Linux 9/10


Requirements
------------

- `become: true` and `gather_facts: true`.
- Internet or a local mirror for the PGDG repository (or set
  `postgresql_manage_repo: false` and provide the packages yourself).
- Role/database bootstrap (`postgresql_roles`, `postgresql_databases`,
  `postgresql_privileges`) needs the **`community.postgresql`** collection and
  local `peer` access for the `postgres` OS user — keep the default
  `local all all peer` row in `postgresql_hba_entries`.


Role Variables
--------------

### Variable reference

| Variable | Default | Required | Description |
|---|---|---|---|
| `postgresql_version` | `"18"` | No | Major PostgreSQL version |
| `postgresql_manage_repo` | `true` | No | Manage the PGDG repository |
| `postgresql_packages_extra` | `[]` | No | Extra packages installed alongside the server, e.g. "postgresql{{ postgresql_version }}-plpython3" (RHEL) or "postgresql-plpython3-{{ postgresql_version }}" (Debian) |
| `postgresql_listen_addresses` | `"localhost"` | No | Value written to listen_addresses |
| `postgresql_port` | `5432` | No | Listen port |
| `postgresql_settings` | `{}` | No | Arbitrary extra GUCs written to the managed conf.d drop-in as key = 'value' |
| `postgresql_ssl` | `false` | No | Turn on server-side TLS |
| `postgresql_ssl_dir` | `""` | No | Private directory the cert and key are copied into so user `postgres` can read them without loosening perms on the acme tree |
| `postgresql_ssl_cert_file` | `""` | If `postgresql_ssl` | Path to the certificate PEM |
| `postgresql_ssl_key_file` | `""` | If `postgresql_ssl` | Path to the private key PEM |
| `postgresql_ssl_ca_file` | `""` | No | `ssl_ca_file` for client-certificate verification |
| `postgresql_ssl_min_protocol_version` | `"TLSv1.2"` | No | `ssl_min_protocol_version` |
| `postgresql_manage_cert` | `false` | No | Issue the certificate with mgcdrd.infrabase.acme_sh from inside this role |
| `postgresql_acme_certs` | `[]` | If `postgresql_manage_cert` | Passed to `acme_sh_certs` when `postgresql_manage_cert` is true |
| `postgresql_hba_entries` | *(list, 3 items)* | No | pg_hba.conf is rendered entirely from this list — order is preserved and nothing else is kept |
| `postgresql_roles` | `[]` | No | Roles to create; each takes `name`, `password` (use a `vault_` var), `role_attr_flags`, `state` |
| `postgresql_databases` | `[]` | No | Databases to create; each takes `name`, `owner`, `encoding`, `lc_collate`, `lc_ctype`, `template`, `state` |
| `postgresql_privileges` | `[]` | No | Grants passed to `community.postgresql.postgresql_privs`; each takes `roles`, `database`, `privs`, `type`, `objs`, `schema`, `state` |


### Roles / databases / privileges

Applied only when non-empty.

OS-family differences
---------------------

| | RHEL (PGDG) | Debian (PGDG) |
|---|---|---|
| Service unit | `postgresql-{{ version }}` | `postgresql@{{ version }}-main` |
| Data dir | `/var/lib/pgsql/{{ version }}/data` | `/var/lib/postgresql/{{ version }}/main` |
| Config dir | the data dir | `/etc/postgresql/{{ version }}/main` |
| Cluster init | explicit `postgresql-{{ version }}-setup initdb` | automatic (`pg_createcluster` on package install) |
| Appstream conflict | `dnf module disable postgresql` on EL9 only | n/a |


Notes
-----

- `pg_hba.conf` is regenerated from `postgresql_hba_entries` on every run.
  Anything added by hand is removed.
- Changing `listen_addresses`, `port` or the `ssl*` settings triggers a
  **restart**; `pg_hba.conf` and cert-file changes trigger a **reload**.
  Handlers are flushed at the end of `configure.yml` so a following bootstrap
  connects against the new config.
- Hardening: the drop-in and `pg_hba` template do not open anything wider than
  loopback by default. Scope remote rows to specific client CIDRs. Avoid the
  common `host all postgres 0.0.0.0/0 scram-sha-256` shortcut — grant only the
  application role from the application hosts, e.g.
  `{ type: host, database: keycloak, user: keycloak, address: "10.0.0.11/32", method: scram-sha-256 }`.
- `postgresql_manage_repo: false` skips the repo but still expects the
  versioned package names to resolve.


Example
-------

```yaml
- name: Native PostgreSQL for Keycloak
  hosts: kc_pgsql
  become: true
  gather_facts: true
  roles:
    - role: mgcdrd.infrabase.postgresql
      vars:
        postgresql_version: "18"
        postgresql_listen_addresses: "localhost,{{ ansible_default_ipv4.address }}"
        postgresql_ssl: true
        postgresql_ssl_cert_file: /etc/ssl/acme/db1.example.com/fullchain.pem
        postgresql_ssl_key_file: /etc/ssl/acme/db1.example.com/key.pem
        postgresql_hba_entries:
          - { type: local, database: all, user: all, method: peer }
          - { type: host, database: all, user: all, address: "127.0.0.1/32", method: scram-sha-256 }
          - { type: host, database: keycloak, user: keycloak, address: "10.0.0.11/32", method: scram-sha-256 }
          - { type: host, database: keycloak, user: keycloak, address: "10.0.0.12/32", method: scram-sha-256 }
        postgresql_roles:
          - name: keycloak
            password: "{{ vault_keycloak_db_password }}"
            role_attr_flags: LOGIN
        postgresql_databases:
          - name: keycloak
            owner: keycloak
```


License
-------

GPL-3.0-or-later
