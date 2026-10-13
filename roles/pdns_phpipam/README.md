pdns_phpipam
============

Deploys a PowerDNS (Authoritative + Recursor + DNSDist) and phpIPAM stack via
Docker Compose. The role handles directory layout, configuration templating, secret
generation, and service lifecycle.

**Stack components:**

| Container | Image | Purpose |
|-----------|-------|---------|
| `mariadb` | mariadb:12-noble | Shared database backend |
| `auth` | powerdns/pdns-auth-50 | Authoritative DNS server |
| `recursor` | powerdns/pdns-recursor-54 | Recursive resolver |
| `dnsdist` | powerdns/dnsdist-20 | DNS load balancer / front door (port 53) |
| `phpipam-web` | phpipam/phpipam-www | IP address management web UI |

DNSDist routes queries for your domain and its reverse zone to Auth, and all other
queries to Recursor.

Tested on: Debian 12/13, Rocky Linux 9/10


Requirements
------------

- Docker and Docker Compose v2 must be installed on the target host
  (use `mgcdrd.infrabase.docker` if needed).
- `become: true` is required — Docker socket and directory operations need root.
- `gather_facts: true` is required for OS-family-aware package operations.


Role Variables
--------------

### Variable reference

| Variable | Default | Required | Description |
|---|---|---|---|
| `pdns_phpipam_base_dir` | `/srv` | No | Base directory on the host |
| `pdns_phpipam_runtime_dir` | `"{{ pdns_phpipam_base_dir }}/phpipam"` | No | Runtime directory for the compose stack |
| `pdns_phpipam_mariadb_dir` | `"{{ pdns_phpipam_runtime_dir }}/mariadb"` | No | MariaDB data directory |
| `pdns_phpipam_auth_dir` | `"{{ pdns_phpipam_runtime_dir }}/pdns_auth"` | No | PowerDNS Authoritative config directory |
| `pdns_phpipam_recu_dir` | `"{{ pdns_phpipam_runtime_dir }}/pdns_recursor"` | No | PowerDNS Recursor config directory |
| `pdns_phpipam_dist_dir` | `"{{ pdns_phpipam_runtime_dir }}/pdns_dnsdist"` | No | dnsdist config directory |
| `pdns_phpipam_docker_network_name` | `dns_net` | No | Docker network name |
| `pdns_phpipam_docker_network_cidr` | `"10.5.0.0/16"` | No | Docker network CIDR |
| `pdns_phpipam_docker_network_gateway` | `"10.5.0.1"` | No | Docker network gateway |
| `pdns_phpipam_docker_network_mariadb` | `"10.5.0.2"` | No | Fixed IP of the MariaDB container |
| `pdns_phpipam_docker_network_auth` | `"10.5.0.3"` | No | Fixed IP of the PowerDNS Authoritative container |
| `pdns_phpipam_docker_network_recu` | `"10.5.0.4"` | No | Fixed IP of the PowerDNS Recursor container |
| `pdns_phpipam_docker_network_dist` | `"10.5.0.5"` | No | Fixed IP of the dnsdist container |
| `pdns_phpipam_docker_network_ipam_web` | `"10.5.0.6"` | No | Fixed IP of the phpIPAM web container |
| `pdns_phpipam_docker_network_nginx` | `"10.5.0.7"` | No | Fixed IP of the nginx TLS container |
| `pdns_phpipam_mariadb_pdns_db` | `pdns` | No | PowerDNS database name |
| `pdns_phpipam_mariadb_pdns_user` | `pdns` | No | PowerDNS database user |
| `pdns_phpipam_mariadb_ipam_db` | `ipam` | No | phpIPAM database name |
| `pdns_phpipam_mariadb_ipam_user` | `ipam` | No | phpIPAM database user |
| `pdns_phpipam_domain` | `"lab.example.com"` | Yes | Primary forward DNS zone |
| `pdns_phpipam_domain_ip_rev` | *(lab-specific; see defaults)* | Yes | Reverse zone prefix for the network (first three octets) |
| `pdns_phpipam_auth_api_port` | `0` | If `you want to run mgcdrd` | Host port exposing PowerDNS Authoritative's HTTP API; `0` does not expose it |
| `pdns_phpipam_recu_api_port` | `0` | No | Host port exposing the Recursor's HTTP API; `0` does not expose it |
| `pdns_phpipam_dist_api_port` | `0` | No | Host port exposing dnsdist's HTTP API; `0` does not expose it |
| `pdns_phpipam_ssl_enabled` | `false` | No | Add an nginx container that terminates TLS in front of phpIPAM web |
| `pdns_phpipam_ssl_cert_dir` | `""` | If `pdns_phpipam_ssl_enabled` | Path to the `acme_sh` cert directory, e.g. `/etc/ssl/acme/dns.lab.example.com` |
| `pdns_phpipam_ssl_hostname` | `""` | No | `ServerName` and TLS SNI; empty uses `inventory_hostname` |
| `pdns_phpipam_ssl_dir` | `"{{ pdns_phpipam_runtime_dir }}/nginx"` | No | Host directory the nginx SSL config is written to |
| `pdns_phpipam_ca_certs_dir` | `""` | No | Host CA bundle directory mounted into phpIPAM web; empty auto-detects by OS family |
| `pdns_phpipam_ipam_site_title` | `"Acme IPAM"` | No | phpIPAM site title |
| `pdns_phpipam_ipam_site_admname` | `"Sysadmin"` | No | phpIPAM admin display name |
| `pdns_phpipam_ipam_site_admemail` | `"admin@{{ pdns_phpipam_domain }}"` | No | phpIPAM admin email |
| `pdns_phpipam_ipam_site_domain` | `"example.com"` | No | phpIPAM site domain |
| `pdns_phpipam_ipam_site_url` | `"http://dns.{{ pdns_phpipam_domain }}"` | No | phpIPAM site URL |
| `pdns_phpipam_ipam_site_passwd_minlength` | `8` | No | Minimum phpIPAM password length |
| `pdns_phpipam_ipam_site_passwd_maxlength` | `0` | No | Maximum phpIPAM password length; `0` is unlimited |
| `pdns_phpipam_ipam_site_passwd_minnumbers` | `0` | No | Minimum digits in a phpIPAM password |
| `pdns_phpipam_ipam_site_passwd_minletters` | `0` | No | Minimum letters in a phpIPAM password |
| `pdns_phpipam_ipam_site_passwd_minlowcase` | `0` | No | Minimum lowercase letters in a phpIPAM password |
| `pdns_phpipam_ipam_site_passwd_minupcase` | `0` | No | Minimum uppercase letters in a phpIPAM password |
| `pdns_phpipam_ipam_site_passwd_minsymbols` | `0` | No | Minimum symbols in a phpIPAM password |
| `pdns_phpipam_ipam_site_passwd_maxsymbols` | `0` | No | Maximum symbols in a phpIPAM password; `0` is unlimited |
| `pdns_phpipam_ipam_site_passwd_allowedsymbols` | `"#,_,-,!,[,],=,~,@"` | No | Symbols allowed in a phpIPAM password |
| `pdns_phpipam_ipam_init_api_enable` | `true` | No | Enable the phpIPAM API at first init |
| `pdns_phpipam_ipam_init_api_string` | `""` | No | phpIPAM API app-id string used at init |
| `pdns_phpipam_ipam_ldap_create` | `false` | No | Create a phpIPAM LDAP auth method at init |
| `pdns_phpipam_ipam_ldap_dcs` | `"ldap1.acme.com;ldap2.acme.com"` | If `pdns_phpipam_ipam_ldap_create` | LDAP servers, semicolon-separated |
| `pdns_phpipam_ipam_ldap_basedn` | `"cn=users,dc=acme,dc=com"` | If `pdns_phpipam_ipam_ldap_create` | LDAP base DN |
| `pdns_phpipam_ipam_ldap_userdn` | `""` | No | LDAP user DN |
| `pdns_phpipam_ipam_ldap_uidattr` | `"uid"` | No | LDAP username attribute |
| `pdns_phpipam_ipam_ldap_security` | `"ssl"` | No | LDAP transport security: `ssl`, `tls`, or `none` |
| `pdns_phpipam_ipam_ldap_port` | `636` | No | LDAP port |
| `pdns_phpipam_ipam_ldap_bindname` | `"uid=serviceaccount,cn=users,dc=acme,dc=com"` | If `pdns_phpipam_ipam_ldap_create` | LDAP bind DN |
| `pdns_phpipam_ipam_ldap_bindpw` | `"basicpassword"` | If `pdns_phpipam_ipam_ldap_create` | LDAP bind password; the default is a placeholder, override from Vault |
| `pdns_phpipam_ipam_ldap_descr` | `"blank"` | No | Description of the LDAP auth method |
| `pdns_phpipam_galera_enabled` | `false` | No | Configure the MariaDB container for Galera multi-master replication |
| `pdns_phpipam_galera_cluster_name` | `"pdns_galera"` | No | Galera cluster name |
| `pdns_phpipam_galera_cluster_address` | `""` | If `pdns_phpipam_galera_enabled` | `gcomm://` address; `gcomm://` alone bootstraps the first node, later nodes use the full member list. Set per host |
| `pdns_phpipam_galera_sst_user` | `"sst_user"` | No | Galera SST user |
| `pdns_phpipam_galera_sst_password` | `""` | If `pdns_phpipam_galera_enabled` | Galera SST password |
| `pdns_phpipam_mariadb_only` | `false` | No | Deploy only the MariaDB container (Galera quorum nodes with no DNS or IPAM) |
| `pdns_phpipam_mariadb_root_passwd` | `""` | No | MariaDB root password; empty auto-generates and persists it to `pdns_phpipam_secrets_dir` |
| `pdns_phpipam_mariadb_pdns_passwd` | `""` | No | PowerDNS DB user password; empty auto-generates |
| `pdns_phpipam_mariadb_ipam_passwd` | `""` | No | phpIPAM DB user password; empty auto-generates |
| `pdns_phpipam_auth_api_key` | `""` | No | PowerDNS Authoritative API key; empty auto-generates |
| `pdns_phpipam_auth_web_passwd` | `""` | No | PowerDNS Authoritative web password; empty auto-generates |
| `pdns_phpipam_recursor_api_key` | `""` | No | Recursor API key; empty auto-generates |
| `pdns_phpipam_dnsdist_api_key` | `""` | No | dnsdist API key; empty auto-generates |
| `pdns_phpipam_dnsdist_web_passwd` | `""` | No | dnsdist web password; empty auto-generates |
| `pdns_phpipam_secrets_dir` | `{{ playbook_dir }}/secrets/<host>/pdns_phpipam` | No | Controller directory where auto-generated secrets are persisted and reused; keep it out of git |


### Required

```yaml
pdns_phpipam_domain: "lab.example.com"       # Authoritative DNS zone
pdns_phpipam_domain_ip_rev: "10.100.10"      # Reverse zone octets (no trailing .in-addr.arpa)
```

### Directories

```yaml
pdns_phpipam_base_dir: /srv
pdns_phpipam_runtime_dir: "{{ pdns_phpipam_base_dir }}/phpipam"

# Derived from runtime_dir — override individually if needed:
pdns_phpipam_mariadb_dir: "{{ pdns_phpipam_runtime_dir }}/mariadb"
pdns_phpipam_auth_dir:    "{{ pdns_phpipam_runtime_dir }}/pdns_auth"
pdns_phpipam_recu_dir:    "{{ pdns_phpipam_runtime_dir }}/pdns_recursor"
pdns_phpipam_dist_dir:    "{{ pdns_phpipam_runtime_dir }}/pdns_dnsdist"
```

### API Port Exposure

By default all service APIs are internal to the Docker network and unreachable
from the host.  Set any of the following to a host port number to expose that
API on the host.  Required if you intend to run `mgcdrd.infrasvc.pdns_records`
from a machine other than the Docker host.

```yaml
pdns_phpipam_auth_api_port: 0    # pdns-auth HTTP API  — container port 8081
pdns_phpipam_recu_api_port: 0    # pdns-recursor API   — container port 8082
pdns_phpipam_dist_api_port: 0    # dnsdist webserver   — container port 8083
```

### SSL (nginx frontend)

Set `pdns_phpipam_ssl_enabled: true` to add an nginx container that terminates
TLS in front of phpipam-web.  Run `mgcdrd.infrabase.acme_sh` first to issue
the certificate, then point `pdns_phpipam_ssl_cert_dir` at the deployed cert
directory.

phpIPAM v1.6+ natively supports reverse-proxy deployments via
`IPAM_TRUST_X_FORWARDED=true` — the role sets this automatically when SSL is
enabled, so phpIPAM correctly enforces HTTPS behaviour even though the internal
connection from nginx to phpipam-web is HTTP on the private Docker network.

When SSL is enabled:
- nginx handles ports 80 (redirect to HTTPS) and 443 (TLS termination)
- phpipam-web is internal-only — no host port binding
- `IPAM_TRUST_X_FORWARDED=true` is set so phpIPAM sees the connection as HTTPS

```yaml
pdns_phpipam_ssl_enabled:  true
pdns_phpipam_ssl_cert_dir: "/etc/ssl/acme/dns.lab.example.com"  # required when enabled
pdns_phpipam_ssl_hostname: "dns.lab.example.com"                 # defaults to inventory_hostname
```

### Docker Network

```yaml
pdns_phpipam_docker_network_name: dns_net
pdns_phpipam_docker_network_cidr: "10.5.0.0/16"
pdns_phpipam_docker_network_gateway: "10.5.0.1"
pdns_phpipam_docker_network_mariadb:  "10.5.0.2"
pdns_phpipam_docker_network_auth:     "10.5.0.3"
pdns_phpipam_docker_network_recu:     "10.5.0.4"
pdns_phpipam_docker_network_dist:     "10.5.0.5"
pdns_phpipam_docker_network_ipam_web: "10.5.0.6"
```

### Database Names and Users

```yaml
pdns_phpipam_mariadb_pdns_db:   pdns
pdns_phpipam_mariadb_pdns_user: pdns
pdns_phpipam_mariadb_ipam_db:   ipam
pdns_phpipam_mariadb_ipam_user: ipam
```

### phpIPAM Site Settings

```yaml
pdns_phpipam_ipam_site_title:    "Acme IPAM"
pdns_phpipam_ipam_site_admname:  "Sysadmin"
pdns_phpipam_ipam_site_admemail: "admin@{{ pdns_phpipam_domain }}"
pdns_phpipam_ipam_site_domain:   "example.com"
pdns_phpipam_ipam_site_url:      "http://dns.{{ pdns_phpipam_domain }}"

pdns_phpipam_ipam_site_passwd_minlength: 8
pdns_phpipam_ipam_site_passwd_maxlength: 0
pdns_phpipam_ipam_site_passwd_minnumbers: 0
pdns_phpipam_ipam_site_passwd_minletters: 0
pdns_phpipam_ipam_site_passwd_minlowcase: 0
pdns_phpipam_ipam_site_passwd_minupcase:  0
pdns_phpipam_ipam_site_passwd_minsymbols: 0
pdns_phpipam_ipam_site_passwd_maxsymbols: 0
pdns_phpipam_ipam_site_passwd_allowedsymbols: "#,_,-,!,[,],=,~,@"

# Create an API application named "ansible" during DB init (needed by phpipam_config role).
# Uses "user" token security — no app code required.
pdns_phpipam_ipam_init_api_enable: true
# Optional app code string. Leave "" for token-based auth (recommended).
pdns_phpipam_ipam_init_api_string: ""
```

### phpIPAM LDAP Authentication

Set `pdns_phpipam_ipam_ldap_create: true` to configure phpIPAM to authenticate
users against an LDAP/AD directory.  Use Ansible Vault for `ldap_bindpw`.

```yaml
pdns_phpipam_ipam_ldap_create:   false
pdns_phpipam_ipam_ldap_dcs:      "ldap1.acme.com;ldap2.acme.com"
pdns_phpipam_ipam_ldap_basedn:   "cn=users,dc=acme,dc=com"
pdns_phpipam_ipam_ldap_userdn:   ""
pdns_phpipam_ipam_ldap_uidattr:  "uid"
pdns_phpipam_ipam_ldap_security: "ssl"     # ssl, tls, or none
pdns_phpipam_ipam_ldap_port:     636
pdns_phpipam_ipam_ldap_bindname: "uid=serviceaccount,cn=users,dc=acme,dc=com"
pdns_phpipam_ipam_ldap_bindpw:   "basicpassword"
pdns_phpipam_ipam_ldap_descr:    "blank"
```

### Galera Clustering

Set `pdns_phpipam_galera_enabled: true` to configure the MariaDB container for
Galera multi-master replication. When enabled, the Galera ports (3306, 4567,
4568, 4444) are exposed on the host so cluster nodes can reach each other.

```yaml
pdns_phpipam_galera_enabled: false
pdns_phpipam_galera_cluster_name: "pdns_galera"
pdns_phpipam_galera_cluster_address: ""   # see bootstrap note below
```

Set `pdns_phpipam_galera_cluster_address` per-host in `host_vars`. For a
three-node cluster across dns1, dns2, dns3:

```yaml
# host_vars/dns1.lab.example.com.yml
pdns_phpipam_galera_cluster_address: "gcomm://10.0.0.11,10.0.0.18,10.0.0.3"

# host_vars/dns2.lab.example.com.yml
pdns_phpipam_galera_cluster_address: "gcomm://10.0.0.11,10.0.0.18,10.0.0.3"

# host_vars/dns3.lab.example.com.yml  (MariaDB-only node)
pdns_phpipam_galera_cluster_address: "gcomm://10.0.0.11,10.0.0.18,10.0.0.3"
```

**How Galera is activated**

The `MARIADB_GALERA_*` environment variables only take effect during first
container initialization (empty data directory). For existing databases, the
role mounts a `galera.cnf` at
`/etc/mysql/mariadb.conf.d/61-galera.cnf` inside the container, which
overrides the commented-out `60-galera.cnf` shipped with the image. This
approach works regardless of whether the data directory is new or existing.

The config includes `wsrep_provider_options = "ist.recv_bind=0.0.0.0"`, which
allows the IST receiver to bind to all interfaces inside the container. Without
this, the IST listener fails to bind to the host IP (which is not reachable
inside Docker), and Galera aborts the entire state transfer before the SST
donor script runs.

**Initial cluster bootstrap**

Galera requires one node to initialize the cluster before others can join. The
`gcomm://` address (empty) tells MariaDB to start as a fresh primary component
rather than trying to contact peers.

```bash
# Step 1 — bootstrap the first node only
ansible-playbook site.yml --limit dns1 \
  -e "pdns_phpipam_galera_cluster_address=gcomm://"

# Step 2 — bring up the remaining nodes with the full address list
ansible-playbook site.yml --limit dns2,dns3
```

After all nodes are up, dns1 keeps running normally. The `gcomm://` override
only affects startup — a running Galera node ignores the initial address.

**Full cluster recovery**

If all Galera nodes go down simultaneously, the cluster must be bootstrapped
again. Check `/var/lib/mysql/grastate.dat` on each node — the one with
`safe_to_bootstrap: 1` (or the highest `seqno`) is the correct node to
bootstrap from. Run Step 1 on that node, then Step 2 on the rest.

### Secrets

Leave any secret as `""` (the default) to have the role auto-generate a random
value and persist it to `pdns_phpipam_secrets_dir` on the Ansible controller.
The same value is reused on all subsequent runs.

Set explicitly (via Ansible Vault) to supply your own values.

```yaml
pdns_phpipam_mariadb_root_passwd: ""
pdns_phpipam_mariadb_pdns_passwd: ""
pdns_phpipam_mariadb_ipam_passwd: ""
pdns_phpipam_auth_api_key:        ""
pdns_phpipam_auth_web_passwd:     ""
pdns_phpipam_recursor_api_key:    ""
pdns_phpipam_dnsdist_api_key:     ""
pdns_phpipam_dnsdist_web_passwd:  ""

# Controller-side path where auto-generated secrets are written.
# Add this directory to .gitignore.
pdns_phpipam_secrets_dir: "{{ playbook_dir }}/secrets/{{ inventory_hostname }}/pdns_phpipam"
```


Example Playbook
----------------

**Minimal — auto-generate all secrets:**

```yaml
- name: Deploy PowerDNS + phpIPAM
  hosts: dns_servers
  gather_facts: true
  become: true
  roles:
    - mgcdrd.infrasvc.pdns_phpipam
  vars:
    pdns_phpipam_domain: "lab.acme.com"
    pdns_phpipam_domain_ip_rev: "10.100.10"
    pdns_phpipam_ipam_site_title: "Acme IPAM"
    pdns_phpipam_ipam_site_url: "http://ipam.lab.acme.com"
```

**With Vault-managed secrets:**

```yaml
- name: Deploy PowerDNS + phpIPAM
  hosts: dns_servers
  gather_facts: true
  become: true
  roles:
    - mgcdrd.infrasvc.pdns_phpipam
  vars:
    pdns_phpipam_domain: "lab.acme.com"
    pdns_phpipam_domain_ip_rev: "10.100.10"
    pdns_phpipam_mariadb_root_passwd: "{{ vault_mariadb_root_passwd }}"
    pdns_phpipam_mariadb_pdns_passwd: "{{ vault_mariadb_pdns_passwd }}"
    pdns_phpipam_mariadb_ipam_passwd: "{{ vault_mariadb_ipam_passwd }}"
    pdns_phpipam_auth_api_key:        "{{ vault_pdns_auth_api_key }}"
    pdns_phpipam_recursor_api_key:    "{{ vault_pdns_recursor_api_key }}"
    pdns_phpipam_dnsdist_api_key:     "{{ vault_dnsdist_api_key }}"
    pdns_phpipam_dnsdist_web_passwd:  "{{ vault_dnsdist_web_passwd }}"
```

**Deploy Docker first, then the stack:**

```yaml
- name: Provision DNS host
  hosts: dns_servers
  gather_facts: true
  become: true
  roles:
    - mgcdrd.infrabase.docker
    - mgcdrd.infrasvc.pdns_phpipam
  vars:
    pdns_phpipam_domain: "lab.acme.com"
    pdns_phpipam_domain_ip_rev: "10.100.10"
```


Notes
-----

- MariaDB init scripts (`/docker-entrypoint-initdb.d/`) only run on the **first**
  container start when the data directory is empty. Re-running the role will not
  re-initialize the database.
- Config file changes to Auth, Recursor, and DNSDist trigger handler restarts of
  their respective containers. MariaDB and phpIPAM-web are not restarted
  automatically on config changes.
- The DNSDist `conf.d/_api.conf` is a Lua file loaded in addition to `dnsdist.yml`.
  The `dnsdist-resolver.lua` module is available for dynamic backend resolution.


License
-------

GPL-3.0-or-later
