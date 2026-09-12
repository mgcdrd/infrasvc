foreman_host_network
=====================

Updates an existing Foreman host's interface — subnet, IP, and optionally
VLAN tag — via `theforeman.foreman.host`. Idempotent (the module handles
host/subnet lookup and interface matching internally, same as
`mgcdrd.infrasvc.foreman_config` uses it elsewhere in this collection).

Matches the interface to update by `identifier` if
`foreman_host_network_interface_identifier` is set, otherwise by `name`
— a managed primary interface's `name` equals the host's own FQDN
(confirmed against a live host record on this lab's Foreman, 2026-09-02).
Multi-NIC hosts should set the identifier explicitly (e.g. `ens18`).

**Important — VLAN tag caveat**

`foreman_host_network_vlan_tag` only reaches the actual hypervisor NIC if
the target host is **Compute-Resource-linked** in Foreman — meaning it was
provisioned through Foreman's own "New Host → Compute Resource" flow, so
Foreman knows which underlying VMID/node to push interface changes to
(`compute_resource_id` + `uuid` set on the host record).

Checked live against this lab's Foreman: **none of its hosts are
compute-resource-linked** — every one shows `provision_method: build` and
null `compute_resource_id`/`uuid`, because VMs here are cloned directly
via `mgcdrd.infrabase.proxmox_vm` against the PVE API, not through
Foreman's provisioning wizard. On a host like that, setting
`foreman_host_network_vlan_tag` only updates Foreman's own interface
record — it does **not** touch Proxmox. For the actual VLAN/bridge
change, call `mgcdrd.infrabase.proxmox_nic` directly (see the
`vm-migrate` deployment, which does exactly that).

If you're pointing this role at a customer environment where hosts *are*
compute-resource-linked, confirm that first (`GET /api/hosts/:id` and
check `compute_resource_id`/`uuid`) before relying on this field alone.

Requirements
------------

`theforeman.foreman` collection.

Foreman API credentials with rights to edit hosts. The read-only
inventory identity (`svc-ansible-inventory`, see
`inventory-common/foreman-inventory-env.sh`) is **not** sufficient — this
role writes. Use a dedicated identity scoped to Hosts edit, not the admin
account.

Role Variables
---------------

```yaml
foreman_host_network_url: "https://foreman.lab.provenzawt.dev"
foreman_host_network_username: ""
foreman_host_network_password: ""
foreman_host_network_validate_certs: true

foreman_host_network_host: ""          # Foreman host name (required)
foreman_host_network_subnet: ""        # Target Foreman subnet name (required)
foreman_host_network_ip: ""            # New IP for that interface (required)

# Override only for multi-NIC hosts where the interface to update isn't
# the one named after the host itself. Matches `identifier` (e.g. "ens18").
foreman_host_network_interface_identifier: ""

# See the VLAN tag caveat above before relying on this alone.
foreman_host_network_vlan_tag: ""
```

Example Playbook
-----------------

```yaml
- name: Repoint a host's Foreman record at its production subnet
  hosts: localhost
  gather_facts: false
  roles:
    - role: mgcdrd.infrasvc.foreman_host_network
      vars:
        foreman_host_network_username: "{{ vault_foreman_write_username }}"
        foreman_host_network_password: "{{ vault_foreman_write_password }}"
        foreman_host_network_host: kc1.lab.provenzawt.dev
        foreman_host_network_subnet: Lab
        foreman_host_network_ip: 10.100.10.50
```

Dependencies
------------

`theforeman.foreman` (already a dependency wherever `foreman_config` is
used).

License
-------

GPL-3.0-or-later
