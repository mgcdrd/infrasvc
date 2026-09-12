# ipa_server

Stands up FreeIPA itself — a fresh primary server (new domain, realm, and CA)
or a replica joined to an existing domain. A thin wrapper around the upstream
`freeipa.ansible_freeipa` collection that adds the lab's conventions: no
integrated DNS (PowerDNS stays authoritative), realm records pushed to the
PowerDNS API, secrets from Vault, Rocky Linux only.

Host enrolment for ordinary domain members is a different job — use
`mgcdrd.infrasvc.ipa_client`. Creating the least-privilege enrolment service
account is `mgcdrd.infrasvc.ipa_baseline`, run once after the primary is up.

## What it does

1. **Preflight** — asserts mode, RHEL-family OS, required vars, and that the
   PowerDNS API answers.
2. **Install detection** — `/etc/ipa/default.conf` present and `ipactl status`
   clean → the host is already a running server and every install step is
   skipped.
3. **Host DNS** — registers this server's A and PTR records in PowerDNS
   (`changetype: REPLACE`). FreeIPA is installed without `--setup-dns`, so
   PowerDNS must resolve the host first.
4. **Install** —
   - `primary`: `freeipa.ansible_freeipa.ipaserver` (self-signed CA,
     `--no-host-dns`, no DNS, firewalld left to the `firewall` role).
   - `replica`: `freeipa.ansible_freeipa.ipaclient` to enrol, then
     `freeipa.ansible_freeipa.ipareplica` to promote to a CA replica.
5. **Realm DNS** — writes the complete `_kerberos`/`_ldap`/`_kpasswd`/`_ntp`
   SRV set, the `_kerberos` realm TXT record, and the `ipa-ca` A record (one
   entry per server) into the forward zone via the PowerDNS API. The full set
   is written every run from `ipa_server_srv_hosts`, so it self-heals as
   replicas are added.
6. **ACME cert install script** (opt-in, `ipa_server_manage_acme_cert: true`)
   — deploys `/usr/local/sbin/acme.sh.renewal.sh`, templated with the
   Directory Manager password from Vault instead of hardcoded. The script
   roots an acme.sh-issued chain (`complete-le-chain.sh`), installs it as a
   trusted IPA CA cert, and pushes it as this server's httpd/LDAP TLS cert
   (`ipa-cacert-manage` / `ipa-certupdate` / `ipa-server-certinstall` /
   `ipactl restart`). It defaults to installing the cert issued for this
   host's own FQDN but takes an optional `CERTNAME` argument to install a
   different one from this host's `/root/.acme.sh/` store. acme.sh's own
   issuance, DNS challenge, and renewal cron are set up out-of-band — this
   only manages the reload script acme.sh calls on renewal.

## Prerequisites

- Rocky Linux 9 or 10. Debian is not supported as a server (enrol Debian
  hosts as members with `ipa_client`).
- `freeipa.ansible_freeipa` installed (add it to the deployment's
  `collections/requirements.yml`).
- The forward and reverse zones already exist in PowerDNS.
- `vault_ipa_admin_password`, `vault_ipa_dirman_password`, and
  `vault_ipa_pdns_api_key` fetched from Vault and passed in.
- For `replica` mode, `ipa_server_primary` set to a running server and that
  server's realm records already in PowerDNS.

## Usage

```yaml
- name: Install IPA primary
  hosts: ipa_primary_host
  become: true
  vars:
    ipa_server_mode: primary
    ipa_server_domain: "{{ domain }}"
    ipa_server_realm: "{{ kerberos_realm }}"
    ipa_server_srv_hosts: "{{ groups['ipa'] }}"
    ipa_server_pdns_api_url: "http://10.0.0.17:8081"
    ipa_server_dns_forward_zone: "{{ domain }}"
    ipa_server_dns_reverse_zone: "0.0.10.in-addr.arpa"
    vault_ipa_admin_password: "{{ lookup('...', 'ipa/domain_admin').password }}"
    vault_ipa_dirman_password: "{{ lookup('...', 'ipa/dirman').password }}"
    vault_ipa_pdns_api_key: "{{ lookup('...', 'pdns').api_key }}"
  roles:
    - mgcdrd.infrasvc.ipa_server

- name: Install IPA replicas
  hosts: ipa_replica
  become: true
  serial: 1
  vars:
    ipa_server_mode: replica
    ipa_server_primary: "{{ ipa_primary }}"
    # ...same domain/realm/DNS/Vault vars as above...
  roles:
    - mgcdrd.infrasvc.ipa_server
```

## Variables

| Variable | Default | Description |
|---|---|---|
| `ipa_server_mode` | `primary` | `primary` or `replica` |
| `ipa_server_domain` | `""` | IPA domain, lowercase (required) |
| `ipa_server_realm` | `""` | Kerberos realm, uppercase (required) |
| `ipa_server_primary` | `""` | Existing server FQDN to replicate from (required for `replica`) |
| `ipa_server_hostname` | `ansible_fqdn` | FQDN this server registers as |
| `ipa_server_setup_ca` | `true` | CA on this node (maps to `ipareplica_setup_ca`) |
| `ipa_server_mkhomedir` | `true` | Create home dirs on first login |
| `ipa_server_validate_certs` | `true` | Validate TLS on PowerDNS API calls |
| `ipa_server_register_dns` | `true` | Register this host's A/PTR in PowerDNS |
| `ipa_server_host_ip` | `ansible_host` / detected IPv4 | IP for the A / `ipa-ca` / PTR records |
| `ipa_server_manage_srv_records` | `true` | Push realm SRV/TXT/`ipa-ca` to PowerDNS |
| `ipa_server_srv_hosts` | `[ipa_server_hostname]` | All IPA server FQDNs for the SRV / `ipa-ca` records |
| `ipa_server_pdns_api_url` | `""` | PowerDNS API base URL |
| `ipa_server_pdns_server_id` | `localhost` | PowerDNS server ID |
| `ipa_server_dns_forward_zone` | `""` | Forward zone for A/SRV/TXT |
| `ipa_server_dns_reverse_zone` | `""` | Reverse zone for PTR |
| `ipa_server_dns_ttl` | `300` | DNS record TTL |
| `ipa_server_manage_acme_cert` | `false` | Deploy `/usr/local/sbin/acme.sh.renewal.sh` |
| `ipa_server_acme_cert_name` | `ipa_server_hostname` | Default acme.sh cert dir name the script installs |
| `vault_ipa_admin_password` | `""` | `admin@REALM` password (inject from Vault) |
| `vault_ipa_dirman_password` | `""` | Directory Manager password (inject from Vault) |
| `vault_ipa_pdns_api_key` | `""` | PowerDNS API key (inject from Vault) |

## OS support

| Family | Versions | Role |
|---|---|---|
| RedHat | Rocky Linux 9 / 10 | server + replica |
| Debian | 12 / 13 | not supported — use `ipa_client` for members |

## DNS records managed

Written to `ipa_server_dns_forward_zone` (all `changetype: REPLACE`):

| Name | Type | Content |
|---|---|---|
| `<host>` | A | this server's IP (`dns_host`) |
| `_kerberos._tcp` / `._udp` | SRV | `0 100 88 <host>.` per server |
| `_kerberos-master._tcp` / `._udp` | SRV | `0 100 88 <host>.` per server |
| `_kpasswd._tcp` / `._udp` | SRV | `0 100 464 <host>.` per server |
| `_ldap._tcp` | SRV | `0 100 389 <host>.` per server |
| `_ntp._udp` | SRV | `0 100 123 <host>.` per server |
| `_kerberos` | TXT | `"<realm>"` |
| `ipa-ca` | A | every IPA server IP |

Plus the PTR record in `ipa_server_dns_reverse_zone`.

## Notes

- No integrated DNS — `--setup-dns` is never passed. PowerDNS is authoritative;
  the realm records above replace what IPA's own DNS would have created.
- Self-signed IPA CA (`ipaserver_external_ca: false`). This is the Kerberos
  realm's CA and is unrelated to the ACME / web-PKI cert the acme.sh renewal
  script (above) installs for the httpd/LDAP endpoint.
- Firewalld is left to `mgcdrd.infrabase.firewall` (`firewall_zones` for the
  `ipa` group) — `ipaserver_setup_firewalld` is `false`.
- Re-running is cheap: the install-detection step short-circuits the heavy
  upstream roles once the server is up, but the DNS record push still runs so
  the realm set stays correct.
