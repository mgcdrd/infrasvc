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
  (`ipa_client` role) before this role runs. The account named in
  `foreman_realm_principal` must already exist in IPA with a role granting
  host-management privileges (the equivalent of the `realm-proxy` user that
  `foreman-prepare-realm` creates) and must have a password set, available
  via `foreman_realm_agent_password`. The role kinits as that
  principal itself and self-service-fetches its own keytab into
  `/etc/foreman-proxy/freeipa.keytab` — no admin credentials are needed for
  that fetch.

  **Important**: self-service `ipa-getkeytab` can only *generate a new
  random key* for the principal — retrieving the *current* key (`-r`)
  needs elevated privilege this account deliberately doesn't have. That
  means every keytab fetch silently invalidates
  `foreman_realm_agent_password`, since the password no longer
  matches the freshly-rotated key. On a host that keeps its keytab file
  (a normal re-run) this never matters — the `when: not
  foreman_keytab_stat.stat.exists` guard means the fetch, and therefore
  the rotation, only happens once. But a **full VM rebuild** wipes that
  local file, so the next run fetches (and rotates) again, and the
  password stored in Vault from the *previous* fetch will be stale.

  Set `foreman_realm_vault_rotate: true` (plus `foreman_realm_vault_addr`,
  `foreman_realm_vault_kv_mount`, `foreman_realm_vault_path`, and
  `foreman_realm_vault_password_key`) to have the role handle this itself:
  after the keytab fetch it kinits as `foreman_ipa_admin_user`, runs `ipa
  passwd` against `foreman_realm_principal` to set a fresh random password,
  and writes that password back to Vault at the given path/key. This
  requires `foreman_ipa_admin_user` to hold an IPA role/privilege scoped to
  changing *only* that one account's password — it should not be a
  general-purpose admin account. With this left `false` (the default),
  fall back to the manual process: reset the account's password
  admin-assisted (self-service password *change* needs the current
  password, which you no longer have once it's gone stale) and update
  `foreman_realm_agent_password` accordingly before deploying against
  a freshly rebuilt host.
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

### Variable reference

| Variable | Default | Required | Description |
|---|---|---|---|
| `foreman_version` | `"3.19"` | No | Foreman release to install |
| `foreman_katello_version` | `"4.21"` | No | Katello release to install |
| `foreman_puppet_release` | `"openvox8"` | No | Puppet/OpenVox repo release |
| `foreman_installer_scenario` | `katello` | No | `foreman-installer` scenario |
| `foreman_skip_storage_check` | `false` | No | Skip the preflight check that `/var/lib/{pulp,containers,pgsql}` are large enough |
| `foreman_storage_min_pulp_gb` | `290` | No | Minimum available GB on the Pulp mount |
| `foreman_storage_min_containers_gb` | `28` | No | Minimum available GB on the containers mount |
| `foreman_storage_min_pgsql_gb` | `18` | No | Minimum available GB on the PostgreSQL mount |
| `foreman_hostname` | `"{{ ansible_fqdn }}"` | No | Foreman server FQDN |
| `foreman_url` | `"https://{{ foreman_hostname }}"` | No | Foreman base URL |
| `foreman_org` | `"My Organization"` | Yes | Initial organization; set in group_vars |
| `foreman_location` | `"Default Location"` | Yes | Initial location; set in group_vars |
| `foreman_installer_cli_enable` | *(list, 6 items)* | No | hammer CLI modules enabled (`--enable-foreman-cli-<item>`) |
| `foreman_installer_plugin_enable` | *(list, 9 items)* | No | Foreman plugins enabled |
| `foreman_installer_proxy_plugin_enable` | *(list, 4 items)* | No | Smart Proxy plugins enabled |
| `foreman_installer_further_enable` | *(list, 1 items)* | No | Additional packages enabled (`--enable-<item>`) |
| `foreman_dhcp_enable` | `false` | No | Manage DHCP on the smart proxy |
| `foreman_dhcp_provider` | `isc` | No | DHCP provider |
| `foreman_dhcp_interface` | `eth0` | No | Interface DHCP listens on |
| `foreman_dhcp_gateway` | `""` | If `foreman_dhcp_enable` | Gateway handed out by DHCP |
| `foreman_dhcp_range_start` | `""` | If `foreman_dhcp_enable` | First address of the DHCP range |
| `foreman_dhcp_range_end` | `""` | If `foreman_dhcp_enable` | Last address of the DHCP range |
| `foreman_dhcp_nameservers` | `[]` | No | DNS servers handed out by DHCP |
| `foreman_dns_enable` | `false` | No | Manage DNS on the smart proxy |
| `foreman_dns_provider` | `powerdns` | No | `powerdns` or `nsupdate` |
| `foreman_dns_forwarders` | `[]` | No | DNS forwarders |
| `foreman_admin_username` / `foreman_admin_password` | `""` | Yes | Initial admin account; also what `foreman_config` authenticates with |
| `foreman_db_password` | `""` | Yes | Foreman database password |
| `foreman_pdns_api_key` | `""` | If `foreman_dns_provider: powerdns` | PowerDNS API key |
| `foreman_realm_agent_password` | `""` | If `foreman_realm_enable` | Password of `foreman_realm_principal`, used for self-service keytab retrieval |
| `foreman_ipa_admin_user` / `foreman_ipa_admin_password` | `""` | If `foreman_realm_vault_rotate` | IPA account scoped to change only the realm principal's password |
| `foreman_pdns_api_url` | `"http://localhost:8081"` | No | PowerDNS API URL; the API key is `foreman_pdns_api_key` |
| `foreman_dns_nsupdate_server` | `""` | If `foreman_dns_provider: nsupdate` | DNS server that receives nsupdate updates |
| `foreman_tftp_enable` | `true` | No | Manage TFTP on the smart proxy |
| `foreman_tftp_listen_on` | `https` | No | Protocols TFTP serves: `http`, `https`, or `both` |
| `foreman_proxy_template_url` | `""` | No | Smart proxy template URL; empty uses the installer default (the proxy's own host and port) |
| `foreman_realm_enable` | `false` | No | Enable realm (FreeIPA) integration |
| `foreman_realm_pam_server` | `foreman` | No | PAM service name for realm authentication |
| `foreman_realm_ipa_authentication` | `"true"` | No | Enable IPA authentication (installer string boolean) |
| `foreman_realm_ipa_authentication_api` | `"false"` | No | Enable IPA authentication for the API (installer string boolean) |
| `foreman_realm_proxy` | `"true"` | No | Enable the realm smart-proxy feature (installer string boolean) |
| `foreman_realm_provider` | `freeipa` | No | Realm provider |
| `foreman_realm_principal` | `""` | If `foreman_realm_enable` | Kerberos principal the realm proxy uses |
| `foreman_realm_freeipa_remove_dns` | `"false"` | No | Remove DNS records when a realm host is deleted (installer string boolean) |
| `foreman_ipa_controller` | `""` | If `foreman_realm_enable` | IPA server the realm proxy talks to |
| `foreman_realm_vault_rotate` | `false` | No | Reset the realm principal's password after each keytab fetch and write it back to Vault, since `ipa-getkeytab` rotates the key |
| `foreman_realm_vault_addr` | `""` | If `foreman_realm_vault_rotate` | Vault address holding the realm principal's password |
| `foreman_realm_vault_kv_mount` | `""` | If `foreman_realm_vault_rotate` | KV mount for the password |
| `foreman_realm_vault_path` | `""` | If `foreman_realm_vault_rotate` | KV path for the password |
| `foreman_realm_vault_password_key` | `"realm_agent_password"` | No | Key within the secret holding the password |
| `foreman_puppet_autosign_entries` | `"[*.example.com]"` | No | Puppet autosign patterns |
| `foreman_puppetserver_tmpdir` | `/opt/puppetlabs/server/data/puppetserver/tmp` | No | JVM temp directory for puppetserver |
| `foreman_proxy_content_enable_ansible` | `true` | No | Enable the Ansible Pulp content type |
| `foreman_proxy_content_enable_deb` | `true` | No | Enable the deb Pulp content type |
| `foreman_proxy_content_enable_docker` | `false` | No | Enable the container Pulp content type |
| `foreman_proxy_content_enable_file` | `true` | No | Enable the file Pulp content type |
| `foreman_proxy_content_enable_ostree` | `true` | No | Enable the OSTree Pulp content type |
| `foreman_proxy_content_enable_python` | `true` | No | Enable the Python Pulp content type |
| `foreman_proxy_content_enable_yum` | `true` | No | Enable the yum Pulp content type |
| `foreman_proxy_content_pulpcore_mirror` | `false` | No | Mirror pulpcore content on the proxy |
| `foreman_proxy_openscap_ansible_module` | `true` | No | Install the OpenSCAP Ansible module on the proxy |
| `foreman_proxy_rex_script_enabled` | `true` | No | Enable remote execution (script provider) |
| `foreman_proxy_rex_script_cockpit_integration` | `false` | No | Enable the Cockpit integration for remote execution |
| `foreman_plugin_tasks_automatic_cleanup` | `true` | No | Clean up old tasks automatically |
| `foreman_plugin_tasks_backup` | `true` | No | Back up tasks before cleanup |
| `foreman_certs_city` | `Raleigh` | No | City for the internal certificates |
| `foreman_certs_country` | `US` | No | Country for the internal certificates |
| `foreman_certs_org` | `"My Organization"` | No | Organization for the internal certificates |
| `foreman_certs_org_unit` | `IT` | No | Organizational unit for the internal certificates |
| `foreman_certs_state` | `NC` | No | State for the internal certificates |
| `foreman_custom_certs` | `false` | No | Replace the self-signed web certificate with the files below |
| `foreman_cert_path` | `"/etc/ssl/acme/{{ foreman_hostname }}/cert.pem"` | If `foreman_custom_certs` | Web certificate path |
| `foreman_cert_key_path` | `"/etc/ssl/acme/{{ foreman_hostname }}/key.pem"` | If `foreman_custom_certs` | Web certificate key path |
| `foreman_cert_ca_path` | `"/etc/ssl/acme/{{ foreman_hostname }}/ca.pem"` | If `foreman_custom_certs` | CA chain path |
| `foreman_telemetry_logger_enabled` | `false` | No | Enable the logger telemetry sink |
| `foreman_telemetry_prometheus_enabled` | `false` | No | Enable the Prometheus telemetry endpoint |
| `foreman_telemetry_statsd_enabled` | `false` | No | Enable the statsd telemetry sink |


### Required (no defaults — must be set by caller)

```yaml
foreman_admin_username: admin
foreman_admin_password: "{{ lookup('community.hashi_vault.vault_kv2_get', vault_kv_env + '/foreman', engine_mount_point=vault_kv_infra_mount, url=vault_addr).secret.admin_password }}"
foreman_db_password:    "{{ lookup('community.hashi_vault.vault_kv2_get', vault_kv_env + '/foreman', engine_mount_point=vault_kv_infra_mount, url=vault_addr).secret.db_password }}"
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

### DNS

```yaml
foreman_dns_enable: false            # true to enable smart proxy DNS
foreman_dns_provider: powerdns       # powerdns or nsupdate
foreman_dns_forwarders: []           # non-managed-zone forwarders, either provider

# powerdns provider
foreman_pdns_api_url: "http://localhost:8081"
# foreman_pdns_api_key must be set when foreman_dns_provider: powerdns

# nsupdate provider
foreman_dns_nsupdate_server: ""      # nameserver to submit updates to, required when foreman_dns_provider: nsupdate
```

### TFTP

```yaml
foreman_tftp_enable: true
foreman_tftp_listen_on: https

# Smart proxy template URL (--foreman-proxy-template-url). Leave "" to use
# the installer default (the proxy's own hostname/port) — set this when the
# proxy should serve provisioning templates from a different URL (e.g. an
# HA/load-balanced endpoint).
foreman_proxy_template_url: ""
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
# foreman_realm_agent_password required when enabled (password for the
# foreman_realm_principal account, used for self-service keytab retrieval)

# Optional: have the role rotate foreman_realm_agent_password in Vault
# itself after a rebuild-triggered keytab fetch. See Requirements above.
foreman_realm_vault_rotate: false
foreman_realm_vault_addr: ""
foreman_realm_vault_kv_mount: ""
foreman_realm_vault_path: ""
foreman_realm_vault_password_key: "realm_agent_password"
# foreman_ipa_admin_user / foreman_ipa_admin_password required when
# foreman_realm_vault_rotate is true — must be scoped to change only
# foreman_realm_principal's password
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
- **Automatic retry for a known transient race**: a `Cert_key_bundle`
  Puppet resource occasionally evaluates before its own `Cert[...]`
  dependency has written the file it bundles, failing the whole run with
  rc=6 even though every other resource in the ~2200-step catalog
  converged. The role detects this specific signature (rc=6 +
  `Cert_key_bundle` + `No such file or directory`) and retries the
  installer once automatically. Any other rc=6 (e.g. genuine proxy
  self-registration failure) still fails immediately — it is not silently
  retried. The race can leave a mismatched Puppet agent keypair behind (a
  private key written but never paired with its signed public half), which
  `puppetserver ca setup` refuses to proceed past on a bare re-run
  (`Missing public key to match private key`). Before retrying, the role
  clears `/etc/puppetlabs/puppet/ssl` and `/etc/puppetlabs/puppetserver/ca`
  — safe pre-success, since no real CA/certs exist yet — so the retry
  regenerates both clean.
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
