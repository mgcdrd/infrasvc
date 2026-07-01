foreman_install
===============

Installs Foreman 3.x + Katello on Rocky Linux 9 using `foreman-installer-katello`.
Handles the full pre-installation sequence: repository setup, package installation,
IPA Kerberos pre-enrollment, optional custom certificate validation, and the
installer run itself.

The installer script is rendered from a Jinja2 template so all feature flags,
proxy options, and cert paths are driven by variables — no manual `foreman-installer`
invocations needed.

Tested on: Rocky Linux 9


Requirements
------------

- `become: true` and `gather_facts: true` are required.
- The host must be resolvable by its FQDN before the installer runs (Foreman
  registers itself by `ansible_fqdn`).
- If `foreman_realm_enable: true`, the host must already be IPA-enrolled
  (`ipa_client` role) before this role runs, and the IPA admin credentials
  must be available via `vault_ipa_admin_user` / `vault_ipa_admin_password`.
- If `foreman_custom_certs: true`, the cert files must exist on the host before
  the role runs (e.g. provisioned by `acme_sh`).
- The installer takes 15–30 minutes on first run. The install task uses
  `async: 3600 / poll: 30` and is skipped on subsequent runs if
  `/etc/foreman/settings.yaml` already exists.
- `community.general` and `community.hashi_vault` collections must be installed.


Role Variables
--------------

### Required (no defaults — must be set by caller)

```yaml
vault_foreman_admin_username: admin
vault_foreman_admin_password: "{{ vault_lookup }}"
vault_foreman_db_password:    "{{ vault_lookup }}"
foreman_org:      "My Organization"
foreman_location: LAB
```

### Versions

```yaml
foreman_version: "3.19"
foreman_katello_version: "4.21"
foreman_puppet_release: "openvox8"
```

### Installer feature flags

```yaml
foreman_installer_cli_enable:
  - ansible
  - discovery
  - openscap
  - puppet
  - tasks
  - templates

foreman_installer_plugin_enable:
  - ansible
  - bootdisk
  - discovery
  - openscap
  - proxmox
  - puppet
  - remote-execution
  - templates
  - vault

foreman_installer_proxy_plugin_enable:
  - ansible
  - discovery
  - openscap
  - remote-execution-script

foreman_installer_further_enable:
  - puppet
```

### DHCP

```yaml
foreman_dhcp_enable: false           # true to configure ISC DHCP via smart proxy
foreman_dhcp_provider: isc
foreman_dhcp_interface: eth0
foreman_dhcp_gateway: ""
foreman_dhcp_range_start: ""
foreman_dhcp_range_end: ""
foreman_dhcp_nameservers: []
```

### DNS (PowerDNS)

```yaml
foreman_dns_enable: false            # true to enable smart proxy DNS via PowerDNS
foreman_dns_provider: powerdns
foreman_pdns_api_url: "http://localhost:8081"
# vault_pdns_api_key must be set when foreman_dns_enable: true
```

### TFTP

```yaml
foreman_tftp_enable: true
foreman_tftp_listen_on: https
```

### IPA / Realm

```yaml
foreman_realm_enable: false
foreman_realm_pam_server: foreman
foreman_realm_ipa_authentication: "true"
foreman_realm_ipa_authentication_api: "false"
foreman_realm_proxy: "true"
foreman_realm_provider: freeipa
foreman_realm_principal: "svc-foreman-agent@EXAMPLE.COM"
foreman_realm_freeipa_remove_dns: "false"
foreman_ipa_controller: ""
# vault_ipa_admin_user / vault_ipa_admin_password required when enabled
```

### Custom web certificates

```yaml
foreman_custom_certs: false
foreman_cert_path:     "/root/.acme.sh/{{ foreman_hostname }}/{{ foreman_hostname }}.cer"
foreman_cert_key_path: "/root/.acme.sh/{{ foreman_hostname }}/{{ foreman_hostname }}.key"
foreman_cert_ca_path:  "/root/.acme.sh/{{ foreman_hostname }}/ca.cer"
```

### Internal cert metadata

```yaml
foreman_certs_city:     Raleigh
foreman_certs_country:  US
foreman_certs_org:      "My Organization"
foreman_certs_org_unit: IT
foreman_certs_state:    NC
```

### Puppet / OpenVox

```yaml
foreman_puppet_autosign_entries: "[*.example.com]"
```


Tags
----

| Tag | What it runs |
|-----|-------------|
| `foreman_install` | Entire role |
| `preflight` | Katello cleanup + repo restoration only |
| `repos` | Repository and GPG key setup only |
| `packages` | Package installation only |
| `ipa` | IPA keytab pre-enrollment only |
| `certs` | Custom cert pre-flight check only |
| `install` | Installer script render + run only |


Preflight behaviour
-------------------

The role detects and reverses Katello client enrollment artifacts that would
interfere with a clean install:

- Removes `katello-ca-consumer*` if present
- Disables the `subscription-manager` DNF plugin
- Re-enables `baseos appstream extras crb` via `dnf config-manager`
- Checks available space on `/var/lib/pulp` (300G), `/var/lib/containers` (30G),
  and `/var/lib/pgsql` (20G) — warns but does not fail if below minimums


Example Playbook
----------------

```yaml
- name: Install Foreman + Katello
  hosts: foreman
  become: true
  roles:
    - role: mgcdrd.infrasvc.foreman_install
  vars:
    foreman_org: "My Organization"
    foreman_location: LAB
    foreman_dhcp_enable: true
    foreman_dhcp_interface: eth0
    foreman_dhcp_gateway: 10.0.0.1
    foreman_dhcp_range_start: 10.0.0.100
    foreman_dhcp_range_end: 10.0.0.200
    foreman_dhcp_nameservers:
      - 10.0.2.53
    foreman_dns_enable: true
    foreman_pdns_api_url: "http://pdns.example.com:8081"
    foreman_realm_enable: true
    foreman_realm_principal: "svc-foreman-agent@EXAMPLE.COM"
    foreman_ipa_controller: ipa.example.com
    foreman_custom_certs: true
```


Notes
-----

- **Idempotency**: The installer run is gated on the absence of
  `/etc/foreman/settings.yaml`. Re-running the role after a successful install
  skips the installer but still applies preflight and repo tasks. To force
  re-installation, remove that file manually first.
- **Installer duration**: The first run takes 15–30 minutes. The `async` task
  polls every 30 seconds and times out after 1 hour.
- **OpenVox**: Puppet server is no longer supported for Foreman integration as
  of 3.19 — the role installs `openvox8-release` (from `yum.voxpupuli.org`) and
  `openvox-server`, replacing the old `yum.puppet.com` / `puppetserver` packages.
  Installer flags are unchanged (`--foreman-proxy-puppet`, `--puppet-server`,
  `--puppet-autosign-entries`, etc.) since Foreman still uses Puppet-prefixed
  flag names for OpenVox integration. Client hosts use the `openvox-agent`
  package on EL; Puppet agent 7 remains a legacy-compatible alternative.
- **Containerized installer**: The 3.19 `foremanctl` (containerized) path does
  not yet document DHCP, TFTP, DNS, Discovery, OpenSCAP, or Realm support.
  This role uses the traditional `foreman-installer-katello` path intentionally.


License
-------

GPL-3.0-or-later
