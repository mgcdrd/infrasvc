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
  The account named in `foreman_realm_principal` must already exist in IPA
  with a role granting host-management privileges (the equivalent of the
  `realm-proxy` user that `foreman-prepare-realm` creates) — the role fetches
  its keytab into `/etc/foreman-proxy/freeipa.keytab`.
- If `foreman_custom_certs: true`, the cert files must exist on the host before
  the role runs (e.g. provisioned by `acme_sh` with `complete_chain: true` —
  `foreman_cert_ca_path` must be a chain that validates to a self-contained
  root or `katello-certs-check` rejects it). They are passed via the Katello
  certs module (`--certs-server-*`). The role also deploys
  `/usr/local/sbin/foreman-cert-renewal.sh`, which re-runs the installer with
  `--certs-update-server --certs-update-server-ca` — point the acme renewal
  hook at it so renewed certs propagate into Katello.
- The installer takes 15–30 minutes on first run. The install task uses
  `async: 7200 / poll: 30` and is skipped on subsequent runs if
  `/root/.foreman-installer-success` exists (written only after a fully
  successful installer run).
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
| `firewall` | firewalld port openings only |
| `ipa` | IPA keytab pre-enrollment only |
| `certs` | Custom cert pre-flight check only |
| `install` | Installer script render + run only |


Preflight behaviour
-------------------

The role detects and reverses Katello client enrollment artifacts that would
interfere with a clean install:

- Unregisters from any previous Katello server (`subscription-manager
  unregister && clean`) if the host has an active registration
- Removes `katello-ca-consumer*` if present
- Disables the `subscription-manager` DNF plugin
- Re-enables `baseos appstream extras crb` via `dnf config-manager`
- Checks available space on `/var/lib/pulp`, `/var/lib/containers`, and
  `/var/lib/pgsql` — **fails** if below minimums, since a Katello install
  onto an undersized `/var` dies partway through. Thresholds
  (`foreman_storage_min_pulp_gb: 290`, `..._containers_gb: 28`,
  `..._pgsql_gb: 18`) sit below the recommended LV sizes (300/40/30) to
  absorb filesystem overhead — a fresh 300G xfs reports ~298G available.
  Set `foreman_skip_storage_check: true` to bypass entirely.


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
  `/root/.foreman-installer-success`, which is written only after the
  installer exits 0. A failed or partial run leaves the marker absent, so
  re-running the role retries the installer (`foreman-installer` itself is
  idempotent). To force a re-run after success, remove the marker.
- **Installer duration**: The first run takes 15–30 minutes. The `async` task
  polls every 30 seconds and times out after 2 hours.
- **Custom certs and Katello**: server certs are passed with
  `--certs-server-cert/-key/-ca-cert` (the certs module), *not*
  `--foreman-server-ssl-*`. The latter leaves the smart proxy and Pulp
  trusting the internal CA while Apache serves the custom cert, which breaks
  proxy self-registration (installer exit code 6).
- **OpenVox**: Puppet server is no longer supported for Foreman integration as
  of 3.19 — the role installs `openvox8-release` (from `yum.voxpupuli.org`) and
  `openvox-server`, replacing the old `yum.puppet.com` / `puppetserver` packages.
  The OpenVox GPG key (`GPG-KEY-openvox.pub`) is imported before the release
  RPM — the dnf module rejects URL-installed RPMs signed with unknown keys.
  Installer flags are unchanged (`--foreman-proxy-puppet`, `--puppet-server`,
  `--puppet-autosign-entries`, etc.) since Foreman still uses Puppet-prefixed
  flag names for OpenVox integration. Client hosts use the `openvox-agent`
  package on EL; Puppet agent 7 remains a legacy-compatible alternative.
- **Hardened /tmp**: with `noexec` on `/tmp` (CIS), puppetserver's JRuby
  cannot extract and exec its native libs and crashes with "Failed to load
  feature test for posix: can't find user for 0". The role creates an
  exec-allowed JVM tmpdir (`foreman_puppetserver_tmpdir`, default
  `/opt/puppetlabs/server/data/puppetserver/tmp`) and passes it via
  `--puppet-server-jvm-extra-args "-Djava.io.tmpdir=..."`.
- **Firewall**: `foreman-installer` does not manage firewalld, and hardened
  hosts default-deny. The role opens the Katello documented set when firewalld
  is running: `http`, `https`, `puppetmaster` services (plus `dhcp`/`tftp`
  when enabled) and ports `8000/tcp` (provisioning templates), `9090/tcp`
  (smart proxy API).
- **Containerized installer**: The 3.19 `foremanctl` (containerized) path does
  not yet document DHCP, TFTP, DNS, Discovery, OpenSCAP, or Realm support.
  This role uses the traditional `foreman-installer-katello` path intentionally.


License
-------

GPL-3.0-or-later
