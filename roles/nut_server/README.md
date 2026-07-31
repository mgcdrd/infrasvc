nut_server
==========

Installs and configures NUT (Network UPS Tools) in primary/server mode: the
local driver talking to a USB-attached UPS, `upsd` serving status to network
clients, and (by default) a local `upsmon` monitoring that same `upsd`.

This role is the "primary" half of a two-role pair — the network client side
lives in `mgcdrd.infrasvc.nut_client`, meant for a separate host that watches
this one's `upsd` remotely. See the design doc for the full topology and
rationale: wiki `enterpriseServices/Power/UPS_NUT_Monitoring`.

Tested on: Debian 12/13, Rocky Linux 9/10 (EL via EPEL). Not yet run against
real hardware — written from the design doc, pending the actual UPS-attached
host being reachable by Ansible.


Requirements
------------

`become: true` and `gather_facts: true` are required. Targets NUT 2.8+, as
shipped in Debian 12/13 and EPEL 9/10 — the role relies on the modern
`nut-driver-enumerator.service` unit, common to both distros since that
version, rather than per-distro driver unit names.

On RedHat, the role enables EPEL itself (`epel-release` via `dnf`) since NUT
isn't in the base Rocky repos.


Role Variables
--------------

All variables are prefixed `nut_server_`. See `defaults/main.yml` for the
full list. Most commonly overridden:

```yaml
nut_server_ups_name: apc                    # ups.conf section name, referenced by clients as apc@<host>
nut_server_driver:   usbhid-ups             # NUT driver — usbhid-ups covers most APC USB models
nut_server_port:     auto                   # USB devices: 'auto' is normally correct

nut_server_listen_addresses:                # upsd.conf LISTEN lines
  - address: 0.0.0.0
    port:    3493

nut_server_admin_password:   "{{ vault_nut_admin_password }}"
nut_server_monuser_password: "{{ vault_nut_monuser_password }}"
```

### Local monitor

```yaml
nut_server_local_monitor: true   # this host also runs upsmon against its own upsd
```

Set `false` to skip installing/configuring the local monitor entirely (server
role only — driver + upsd, no upsmon). Kept `SYSLOG`-only regardless; this
role does not perform any shed/shutdown orchestration — see `nut_client`'s
README and the design doc for where that logic actually lives.


Example Playbook
-----------------

```yaml
- name: NUT server (UPS-attached host)
  hosts: nut_server
  gather_facts: true
  become: true
  roles:
    - mgcdrd.infrasvc.nut_server
  vars:
    nut_server_ups_name:         apc
    nut_server_admin_password:   "{{ vault_nut_admin_password }}"
    nut_server_monuser_password: "{{ vault_nut_monuser_password }}"
```


Notes
-----

- **Firewall / source scoping**: this role does not manage firewall rules.
  `upsd`'s port (3493/tcp) needs opening via `mgcdrd.infrabase.firewall`
  (or the OS firewall directly) same as any other deployment — see that
  role's known limitation: no source-IP scoping. If the client crosses a
  network/VLAN boundary (as in the lab's deluge → responder-VM topology),
  restrict the source at the router/switch ACL instead; the host firewall
  alone can't scope it.
- **File permissions**: NUT's packaged services run as the `nut` user after
  opening the USB device as root. Config files containing secrets
  (`upsd.users`, `upsmon.conf`) are deployed group-readable by `nut_server_group`
  (default `nut`), not root-only — root-only would break the daemon.
- **`upsd.users` `upsmon` directive**: both local and remote monitors share
  the same `monuser` account; the `primary`/`secondary` distinction that
  actually matters for shutdown authority is set per-client in each host's
  own `upsmon.conf` `MONITOR` line, not here.


License
-------

GPL-3.0-or-later
