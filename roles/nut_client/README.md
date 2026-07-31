nut_client
==========

Installs and configures NUT (Network UPS Tools) in secondary/client mode:
`upsmon` polling one or more remote `upsd` servers over the network. No
local driver, no `upsd` — this host never owns a UPS directly.

This role is the "client" half of a two-role pair — the UPS-attached server
side lives in `mgcdrd.infrasvc.nut_server`. In the lab, this role runs on the
responder VM that watches `deluge`'s `upsd` remotely, deliberately outside
the k8s cluster it will eventually help drain. See the design doc for the
full topology and rationale: wiki `enterpriseServices/Power/UPS_NUT_Monitoring`.

Tested on: Debian 12/13, Rocky Linux 9/10 (EL via EPEL). Not yet run for
real — the responder VM doesn't exist yet; written from the design doc.


Requirements
------------

`become: true` and `gather_facts: true` are required. Targets NUT 2.8+, same
as `nut_server`. On RedHat, the role enables EPEL itself.


Role Variables
--------------

All variables are prefixed `nut_client_`. See `defaults/main.yml` for the
full list.

```yaml
nut_client_monitors:
  - ups_name:         apc
    ups_host:         deluge.example.com   # or the nut_server host's inventory hostname
    power_value:       1
    monuser:           monuser
    monuser_password:  "{{ vault_nut_monuser_password }}"
    role:               secondary          # always secondary for this role

nut_client_deadtime: 60   # generous by default — see Notes
```

### NOTIFYCMD

```yaml
nut_client_notifycmd:    /usr/local/bin/nut-notify.sh   # deployed by this role
nut_client_notify_hook:  ""                             # optional extra script, see below
nut_client_shutdowncmd:  ""                              # deliberately unset, see Notes
```

The deployed `nut-notify.sh` always logs to syslog (`logger -t nut-notify`),
then calls `nut_client_notify_hook` (if set and executable) with the same
args and `NOTIFYTYPE` env var. That's the hook point `mgcdrd.infrasvc.ups_shed`
uses to start/stop its threshold-polling timer on `ONBATT`/`ONLINE` — this
role stays generic and doesn't know anything about tiered shed logic itself.


Example Playbook
-----------------

```yaml
- name: NUT client (UPS status responder)
  hosts: nut_client
  gather_facts: true
  become: true
  roles:
    - mgcdrd.infrasvc.nut_client
  vars:
    nut_client_monitors:
      - ups_name:         apc
        ups_host:         deluge.lab.provenzawt.dev
        power_value:      1
        monuser:          monuser
        monuser_password: "{{ vault_nut_monuser_password }}"
        role:             secondary
```


Notes
-----

- **`nut_client_deadtime` defaults to 60s**, well above NUT's own default
  (15s), because this monitor is expected to cross a network/VLAN boundary
  to reach `upsd` (deluge sits on its own isolated VLAN in the lab). A short
  DEADTIME risks reading a transient link blip as a genuine power event and
  false-triggering downstream automation once that's built.
- **No real shutdown wiring yet.** This role only installs and configures
  NUT itself. The threshold-based tiered shed logic (poll `battery.charge`,
  map to Ansible playbook runs at ~70%/~40%/~20%) described in the design
  doc is explicitly out of scope here — see that page's "Status / open
  items" checklist for what's still pending (responder VM creation, router
  ACL, `svc-ups-shutdown` identity, k8s RBAC, the actual tier playbooks).
- **File permissions**: same rationale as `nut_server` — `upsmon.conf`
  contains the `monuser` password and is deployed group-readable by
  `nut_client_group` (default `nut`), matching what NUT's packaged upsmon
  process needs, not root-only.


License
-------

GPL-3.0-or-later
