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
