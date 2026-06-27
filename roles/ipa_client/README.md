# ipa_client

Enrolls a host into FreeIPA. Handles DNS registration, IPA host pre-registration
via the enrollment service account (created by `ipa_baseline`), package installation,
and `ipa-client-install` execution.

Foreman provisioning remains the primary enrollment path. This role handles
everything Foreman doesn't cover: manual builds, post-provisioning DNS fixup,
and broken enrollment repair.

## What it does

1. **DNS** — Registers A and PTR records in PowerDNS via the API before any IPA
   operations. Runs unconditionally (idempotent REPLACE). Skip with
   `ipa_client_dns_register: false` if DNS is already managed elsewhere.

2. **Enrollment check** — Inspects `/etc/ipa/default.conf` and runs
   `sssctl domain-status` to determine current state:
   - Enrolled and healthy → no-op (all remaining tasks skipped)
   - Enrolled but SSSD broken → re-enroll with `--force-join`
   - Not enrolled → fresh enrollment

3. **Pre-registration** — Calls the IPA JSON-RPC API as `svc-ansible-enrollment`
   to create (or regenerate the OTP on) the host object. The OTP is held only
   in memory and never logged.

4. **Install** — Installs `freeipa-client` via `apt` (Debian) or `dnf` (RedHat).

5. **Enroll** — Runs `ipa-client-install --unattended` with the OTP. Adds
   `--force-join` for broken-enrollment repair runs.

## Prerequisites

- `ipa_baseline` must have been run to create `svc-ansible-enrollment` and
  populate Vault at `kv1/ipa/enrollment`.
- Enrollment credentials fetched from Vault and passed as
  `vault_ipa_enrollment_principal` / `vault_ipa_enrollment_password`.
- `vault_ipa_pdns_api_key` from Vault if DNS registration is enabled.

## Usage

```yaml
- name: Enroll host in IPA
  hosts: new_hosts
  become: true
  vars:
    ipa_client_servers:
      - ipa01.lab.example.com
      - ipa02.lab.example.com
    ipa_client_domain: lab.example.com
    ipa_client_realm: LAB.EXAMPLE.COM
    ipa_client_pdns_api_url: http://dns.lab.example.com:8081
    ipa_client_dns_forward_zone: lab.example.com
    ipa_client_dns_reverse_zone: 10.0.0.in-addr.arpa
    vault_ipa_enrollment_principal: "{{ lookup('...', 'kv1/data/ipa/enrollment').principal }}"
    vault_ipa_enrollment_password: "{{ lookup('...', 'kv1/data/ipa/enrollment').password }}"
    vault_ipa_pdns_api_key: "{{ lookup('...', 'kv1/data/pdns/api').key }}"
  roles:
    - mgcdrd.infrasvc.ipa_client
```

## Variables

| Variable | Default | Description |
|---|---|---|
| `ipa_client_servers` | `[]` | IPA server FQDNs (required) |
| `ipa_client_domain` | `""` | IPA domain, lowercase (required) |
| `ipa_client_realm` | `""` | Kerberos realm, uppercase (required) |
| `ipa_client_validate_certs` | `true` | Validate IPA TLS certificate |
| `ipa_client_host_ip` | `ansible_default_ipv4.address` | IP to register in DNS and IPA |
| `ipa_client_pdns_api_url` | `""` | PowerDNS API URL |
| `ipa_client_pdns_server_id` | `localhost` | PowerDNS server ID |
| `ipa_client_dns_forward_zone` | `""` | Forward DNS zone |
| `ipa_client_dns_reverse_zone` | `""` | Reverse DNS zone |
| `ipa_client_dns_ttl` | `300` | DNS record TTL |
| `ipa_client_dns_register` | `true` | Enable DNS registration |
| `vault_ipa_enrollment_principal` | `""` | Service account username (inject from Vault) |
| `vault_ipa_enrollment_password` | `""` | Service account password (inject from Vault) |
| `vault_ipa_pdns_api_key` | `""` | PowerDNS API key (inject from Vault) |

## Enrollment states

| `/etc/ipa/default.conf` | `sssctl domain-status` | Behaviour |
|---|---|---|
| Missing | N/A | Full enrollment (pre-register → install → enroll) |
| Present | rc=0 (healthy) | No-op — host already enrolled |
| Present | rc≠0 (broken) | Re-enroll with `--force-join` |

## OS support

| Family | Package manager | Package |
|---|---|---|
| Debian 12 / 13 | apt | `freeipa-client` |
| Rocky Linux 9 / 10 | dnf | `freeipa-client` |

## Notes

- `--no-dns-sshfp` is always passed to `ipa-client-install` to prevent IPA from
  attempting to register SSH fingerprints in DNS (DNS is managed by PowerDNS,
  not IPA).
- The OTP retrieved from the IPA API is held only in memory and suppressed from
  all Ansible output via `no_log: true`.
- `ipa_client_host_ip` should be set to the intended static IP when the host
  is still on a Foreman DHCP address at the time this role runs.
