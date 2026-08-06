foreman_config
==============

Configures a running Foreman + Katello instance using the `theforeman.foreman`
collection. Manages the full post-install configuration lifecycle: content
(sync plans, products, repositories, lifecycle environments, content views,
activation keys), infrastructure (domains, subnets, architectures, compute
resources, compute profiles), provisioning (operating systems, partition tables,
installation media, global parameters), template sync from GitLab, host groups,
and AWX integration.

All configuration is data-driven — add or modify entries in the relevant lists
in `group_vars` and re-run the appropriate tag.

Tested on: Rocky Linux 9 (target host); any Ansible controller


Requirements
------------

- Foreman must be running and accessible at `foreman_url` before this role runs.
  Use `foreman_install` to get there.
- `theforeman.foreman`, `community.general`, and `community.hashi_vault`
  collections must be installed.
- The `foreman` OS user needs an SSH keypair deployed for GitLab access.
  `templates.yml` deploys a keypair stored in Vault (`vault_foreman_template_sync_ssh_private_key` /
  `..._public_key`) rather than generating a fresh one per host — this keeps
  the same public key valid across host rebuilds, so the GitLab deploy key
  only needs to be registered once instead of after every rebuild.
- `become: true` is required for deploying the SSH key and `hammer` calls.
  API calls go directly to Foreman and do not require privilege escalation.


Role Variables
--------------

### Connection (required)

```yaml
foreman_url:      "https://foreman.example.com"
foreman_hostname: "foreman.example.com"
foreman_username: admin
vault_foreman_admin_password: "{{ vault_lookup }}"
foreman_validate_certs: true
foreman_org:      "My Organization"
foreman_location: LAB
```

### Sync plans

```yaml
foreman_sync_plans:
  - name: Rocky 9
    org: "{{ foreman_org }}"
    interval: weekly
    enabled: true
    sync_date: "2025-04-15 03:00:00 UTC"
    state: present
```

### GPG content credentials

```yaml
foreman_gpg_keys:
  - name: RPM-GPG-KEY-Rocky-9
    file: RPM-GPG-KEY-Rocky-9    # looked up from this role's files/
```

Creates a Katello content credential per entry (`content_type: gpg_key`), read
from `files/<file>` via `lookup('file', ...)`. Reference it by `name` in a
`foreman_repos_rpm` entry's `gpg_key` key. Without a `gpg_key`, Katello syncs
the repo but sets `gpgcheck=0` in the `redhat.repo` it generates for content
hosts registered against it (CIS `ensure_gpgcheck_never_disabled`).

### Products and repositories

```yaml
foreman_repo_products:
  - name: Rocky 9
    org: "{{ foreman_org }}"
    sync_plan: Rocky 9
    state: present

foreman_repos_rpm:
  - name: Rocky 9 BaseOS
    product: Rocky 9
    url: https://dl.rockylinux.org/pub/rocky/9/BaseOS/x86_64/os/
    mirror_on_sync: true
    download_policy: on_demand    # or immediate
    gpg_key: RPM-GPG-KEY-Rocky-9  # optional — must match a foreman_gpg_keys name
    state: present

foreman_repos_deb:
  - name: Bookworm main
    product: Debian 12
    url: http://deb.debian.org/debian/
    deb_releases: bookworm
    deb_components: main
    mirror_on_sync: true
    download_policy: on_demand
    state: present
```

### Lifecycle environments and content views

```yaml
foreman_lifecycle_envs:
  - name: Development
    state: present
  - name: Production
    state: present

foreman_content_views:
  - name: Rocky 9 x86_64
    org: "{{ foreman_org }}"
    first_publish: true           # publish version 1.0 and promote on first run
    lifecycle_envs:
      - Development
      - Production
    repos:
      - name: Rocky 9 BaseOS
        product: Rocky 9
    state: present

foreman_activation_keys:
  - name: rocky9
    org: "{{ foreman_org }}"
    lifecycle_env: Development
    content_view: Rocky 9 x86_64
    unlimited_hosts: true
    auto_attach: true
    content_overrides:
      - label: My_Org_Rocky_9_Rocky_9_BaseOS
        override: enabled
    state: present
```

### Infrastructure

```yaml
foreman_domains:
  - name: example.com
    dns_proxy: "{{ foreman_hostname }}"    # smart proxy for forward A records (e.g. PowerDNS) — omit for none
    organizations: "{{ foreman_org }}"
    locations: LAB
    state: present

foreman_subnets:
  - name: Lab
    network: 10.0.0.0
    mask: 255.255.255.128
    gateway: 10.0.0.1
    boot_mode: DHCP
    tftp_proxy: "{{ foreman_hostname }}"
    dhcp_proxy: "{{ foreman_hostname }}"
    dns_proxy:  "{{ foreman_hostname }}"
    template_proxy: "{{ foreman_hostname }}"
    domains: ["example.com"]
    organizations: ["{{ foreman_org }}"]
    locations: [LAB]
    state: present

foreman_architectures:
  - name: x86_64
    state: present

foreman_compute_resources:
  - name: PVE2
    provider: proxmox
    url: https://pve2.example.com:8006/api2/json
    user: root@pam
    password: "{{ vault_pve2_password }}"
    ssl_verify_peer: true
    organizations: ["{{ foreman_org }}"]
    locations: LAB
    state: present
```

### Compute profiles

```yaml
foreman_compute_profiles:
  - name: PVE2 Default
    state: present
    compute_attributes:
      - compute_resource: PVE2
        vm_attrs:
          type: qemu
          node_id: pve2
          config_attributes:
            kvm: "1"
            bios: ovmf
            cpu_type: host
            sockets: "1"
            cores: "2"
            memory: "4096"
          interfaces_attributes:
            "0":
              id: net0
              model: virtio
              bridge: vmbr0
          volumes_attributes:
            "0":
              storage_type: hard_disk
              storage: truenas
              controller: virtio
              size: "32"
              id: virtio0
```

### Operating systems

```yaml
foreman_operatingsystems_rh:
  - name: Rocky
    major: 9
    partition_tables: [EL Single Disk UEFI]
    install_media: [Rocky Linux]
    provisioning_templates:
      PXELinux: Kickstart default PXELinux
      provision: EL Base Script
      finish: Kickstart default finish
    state: present

foreman_operatingsystems_deb:
  - name: Debian
    release_name: Bookworm
    major: 12
    state: present

foreman_partition_table_os_families:
  - name: EL Single Disk UEFI
    family: Redhat

foreman_installation_media:
  - name: Rocky Linux
    os_family: Redhat
    operatingsystems: [Rocky 9]
    path: "{{ foreman_url }}/pulp/content/..."
    state: present

foreman_global_parameters:
  - name: allow-root-ssh
    type: boolean
    value: "true"
    state: present
```

### Template sync

```yaml
foreman_template_gitlab_host: gitlab.example.com
foreman_template_repo: "ssh://git@gitlab.example.com/hardening/foreman-templates.git"
foreman_template_import_associate: Always
foreman_template_import_branch: main
foreman_template_import_filter: "EL.*|el.*|freeipa.*"
foreman_template_import_force: true

foreman_template_settings:
  - name: template_sync_repo
    value: "ssh://git@gitlab.example.com/hardening/foreman-templates.git"
```

### Host groups

```yaml
foreman_hostgroups:
  - name: Rocky 9 Base
    org: "{{ foreman_org }}"
    locations: [LAB]
    lifecycle_env: Development
    content_view: Rocky 9 x86_64
    domain: example.com
    subnet: Lab
    realm: EXAMPLE.COM
    architecture: x86_64
    operatingsystem: Rocky 9
    medium: Rocky Linux
    ptable: EL Single Disk UEFI
    pxe_loader: PXELinux UEFI
    activation_keys: rocky9
    root_pass: "{{ vault_foreman_host_root_pass }}"
    state: present
```


### LDAP authentication (optional — IPA fallback)

The IPA-backed `External` auth source comes from `foreman_install`'s
`--foreman-ipa-authentication` installer flag (Kerberos SSO), not from
this role. Where FreeIPA isn't available (most customer sites), define a
plain LDAP auth source here instead, then point `foreman_usergroups`'
`auth_source` at its `name` instead of `External`.

```yaml
foreman_ldap_auth_sources:
  - name: Corporate LDAP
    host: ldap.example.com
    port: 636                        # default: 389
    account: "cn=foreman,ou=svc,dc=example,dc=com"
    account_password: "{{ vault_foreman_ldap_bind_password }}"
    base_dn: "dc=example,dc=com"
    groups_base: "ou=groups,dc=example,dc=com"
    attr_login: uid
    attr_firstname: givenName
    attr_lastname: sn
    attr_mail: mail
    onthefly_register: true
    usergroup_sync: true
    tls: true
    server_type: posix               # free_ipa | active_directory | posix
    ldap_group_membership: rfc4519   # posix | nis_netgroups | rfc4519 (not valid for active_directory)
    locations: [LAB]
    organizations: "{{ foreman_org }}"
    state: present
```

`account_password` is required when `onthefly_register` is used, and makes
the task non-idempotent (theforeman.foreman's own module behavior — it
can't read the password back to compare).

### User and group management

```yaml
foreman_usergroups:
  - name: ipa_group_name
    auth_source: External
    usergroup: foreman_group_name
    state: present
    isadmin: true
    # optional
    #roles:
    #  - roles in foreman to assign to the group
    #users:
    #  - internal users to assign to the group
    #usergroups:
    #  - internal groups to assign to the group
    #updated_name: "" # only when changing an existing 

```



### AWX integration (optional)

```yaml
foreman_awx_url: "https://awx.example.com"
foreman_awx_job_template_id: "42"
# vault_awx_host_config_key must be set
```

AWX tasks are skipped if `foreman_awx_url` is not defined.

Tags
----

| Tag | What it runs |
|-----|-------------|
| `foreman_config` | Entire role |
| `syncplans` | Sync plans only |
| `repos` | Products + repositories only |
| `lifecycle` | Lifecycle envs, content views, activation keys |
| `infra` | Domains, subnets, architectures, compute resources/profiles |
| `templates` | SSH key gen, GitLab host key, template settings + sync |
| `provisioning` | Operating systems, install media, partition tables, global params |
| `hostgroups` | Host groups only |
| `ldap_auth` | LDAP authentication sources only |
| `usergroups` | User and group management only |
| `awx` | AWX integration settings only |


Template sync notes
-------------------

The role deploys a persistent `ed25519` keypair for the `foreman` OS user from
Vault (generate it once with `ssh-keygen -t ed25519 -N '' -f <file>` and store
both halves at `<env>/foreman`'s `template_sync_ssh_private_key` /
`template_sync_ssh_public_key` keys). That public key must be registered on
GitLab (as a deploy key or user SSH key with at least Developer access to the
templates repo) once — it stays valid across every subsequent host rebuild,
since the role no longer generates a fresh key per host.

The GitLab host key is scanned automatically and written to
`/usr/share/foreman/.ssh/known_hosts`.


Operating system provisioning notes
------------------------------------

RHEL-family OSes are created in two passes. The first pass creates the OS record
without template or media associations (which may not exist yet). The second pass
re-applies with full associations. This avoids ordering failures when templates
and media are also being created in the same run.


License
-------

GPL-3.0-or-later
